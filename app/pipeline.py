# -*- coding: utf-8 -*-
"""采集流水线：抓取 -> 解析 -> 打分 -> 去重 -> 入库 -> 导出。

一次 run 的统计口径：
    pages_total / pages_ok   页面级成功率（健康度）
    raw_count                解析出的候选条目数
    accepted                 通过阈值的条目数（命中率 = accepted / raw_count）
    new_count                真正入库的新条目数（去重后）
"""
from __future__ import annotations

import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .config import (CONCURRENCY, FETCH_RETRIES, FETCH_TIMEOUT, PROXY,
                     SCORE_THRESHOLD, TARGET_YEARS)
from .crawler.classifier import classify
from .crawler.dedup import Deduper
from .crawler.fetcher import Fetcher
from .crawler.parser import extract_candidates
from .crawler.sources import SOURCES
from . import store


@dataclass
class RunState:
    running: bool = False
    run_id: int = 0
    started_at: str = ""
    finished_at: str = ""
    total: int = 0
    done: int = 0
    current: str = ""
    pages_ok: int = 0
    pages_total: int = 0
    raw_count: int = 0
    accepted: int = 0
    new_count: int = 0
    errors: List[Dict] = field(default_factory=list)
    log: List[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def push(self, msg: str):
        with self.lock:
            self.log.append("[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg))
            self.log = self.log[-200:]

    def as_dict(self) -> Dict:
        with self.lock:
            pct = round(self.done / self.total * 100) if self.total else 0
            return {
                "running": self.running, "run_id": self.run_id,
                "started_at": self.started_at, "finished_at": self.finished_at,
                "total": self.total, "done": self.done, "percent": pct,
                "current": self.current, "pages_ok": self.pages_ok,
                "pages_total": self.pages_total, "raw_count": self.raw_count,
                "accepted": self.accepted, "new_count": self.new_count,
                "errors": self.errors[-12:], "log": self.log[-40:],
            }


STATE = RunState()


def _existing_index():
    """返回 (url 集合, [(url, title)])，用于跨批次去重。

    只按 URL 去重不够：同一份通知换个链接、标题加个「（更新）」就会重复入库，
    所以每轮开始前用历史标题预热 SimHash 索引。
    """
    with store.connect() as c:
        rows = [(r["url"], r["title"]) for r in c.execute("SELECT url, title FROM items")]
    return {u for u, _ in rows}, rows


def _legacy_export(items: List[Dict], root: str) -> Optional[str]:
    """按旧脚本格式写一份 markdown，保证老习惯不断档。"""
    import os
    if not root or not os.path.isdir(root):
        return None
    today = datetime.date.today().isoformat()
    day_dir = os.path.join(root, today)
    os.makedirs(day_dir, exist_ok=True)
    by_school: Dict[str, List[Dict]] = {}
    for it in items:
        by_school.setdefault(it["school"], []).append(it)
    for school, rows in by_school.items():
        path = os.path.join(day_dir, school + ".md")
        with open(path, "a", encoding="utf-8") as f:
            f.write("# %s · %s考研通知\n\n抓取时间：%s（研讯自动监控）\n\n" % (
                school, "/".join(TARGET_YEARS), store.now()))
            for r in rows:
                f.write("- [%s](%s)\n" % (r["title"], r["url"]))
            f.write("\n")
    return day_dir


def _fetch_source(src, fetcher: Fetcher, state: RunState, today, deduper: Deduper,
                  existing: set) -> Dict:
    found: List[Dict] = []
    ok_pages = 0
    for url in src.urls:
        state.current = "%s · %s" % (src.school, url)
        res = fetcher.get(url, extra_headers=src.headers, encoding=src.encoding,
                          referer=src.referer or url)
        state.pages_total += 1
        if not res.ok:
            state.errors.append({"school": src.school, "url": url,
                                 "kind": res.error_kind, "error": res.error})
            store.save_source(src.school, url, res.error_kind or "error", res.status,
                              res.error_kind, res.error, res.elapsed, 0)
            state.push("✗ %s %s（%s）" % (src.school, res.error_kind, res.error[:60]))
            continue
        ok_pages += 1
        state.pages_ok += 1
        cands = extract_candidates(res.html, res.final_url or url, src.school)
        state.raw_count += len(cands)
        hits = 0
        for c in cands:
            v = classify(c.title, c.context, c.publish_date, today=today,
                         target_years=TARGET_YEARS, threshold=SCORE_THRESHOLD)
            if not v.accepted:
                continue
            hits += 1
            if c.url in existing:
                continue
            dup = deduper.find_dup(c.url, c.title)
            if dup:
                continue
            deduper.add(c.url, c.title, c.url)
            found.append({
                "school": src.school, "title": c.title, "url": c.url,
                "publish_date": c.publish_date, "score": v.score,
                "tags": v.tags, "reasons": v.reasons,
            })
        state.accepted += hits
        store.save_source(src.school, url, "ok", res.status, "", "", res.elapsed, hits)
        state.push("✓ %s 解析 %d 条，命中 %d 条" % (src.school, len(cands), hits))
    state.done += 1
    return {"school": src.school, "items": found, "pages_ok": ok_pages}


def run_once(school: str = "", limit: int = 0, legacy_root: str = "") -> Dict:
    if STATE.running:
        return {"ok": False, "error": "已有采集任务在运行"}
    store.init_db()
    today = datetime.date.today()
    targets = [s for s in SOURCES if not school or s.school == school]
    if limit:
        targets = targets[:limit]

    STATE.running = True
    STATE.run_id = store.start_run(len(targets))
    STATE.started_at = store.now()
    STATE.finished_at = ""
    STATE.total = len(targets)
    STATE.done = 0
    STATE.current = ""
    STATE.pages_ok = STATE.pages_total = 0
    STATE.raw_count = STATE.accepted = STATE.new_count = 0
    STATE.errors = []
    STATE.log = []
    STATE.push("开始采集：%d 个院校源，阈值 %d 分，目标年份 %s" % (
        len(targets), SCORE_THRESHOLD, "/".join(TARGET_YEARS)))

    t0 = time.time()
    fetcher = Fetcher(timeout=FETCH_TIMEOUT, retries=FETCH_RETRIES, proxy=PROXY or None)
    existing, history = _existing_index()
    deduper = Deduper().build([(u, t, u) for u, t in history])
    all_new: List[Dict] = []
    sources_ok = 0

    try:
        with ThreadPoolExecutor(max_workers=max(1, CONCURRENCY)) as pool:
            futures = [pool.submit(_fetch_source, s, fetcher, STATE, today, deduper, existing)
                       for s in targets]
            for fut in as_completed(futures):
                try:
                    r = fut.result()
                except Exception as e:  # pragma: no cover
                    STATE.push("! 源异常：%r" % (e,))
                    continue
                if r["pages_ok"]:
                    sources_ok += 1
                for it in r["items"]:
                    if store.insert_item(it["school"], it["title"], it["url"],
                                         it["publish_date"], it["score"], it["tags"],
                                         it["reasons"], STATE.run_id,
                                         status="new" if it["score"] >= 60 else "review"):
                        all_new.append(it)
                        existing.add(it["url"])
    finally:
        fetcher.close()

    elapsed = time.time() - t0
    STATE.new_count = len(all_new)
    STATE.finished_at = store.now()
    STATE.running = False
    STATE.current = ""

    store.finish_run(STATE.run_id, status="done", sources_ok=sources_ok,
                     pages_total=STATE.pages_total, pages_ok=STATE.pages_ok,
                     raw_count=STATE.raw_count, accepted=STATE.accepted,
                     new_count=STATE.new_count,
                     avg_elapsed=round(elapsed / max(1, len(targets)), 2))

    exported = _legacy_export(all_new, legacy_root) if legacy_root else None
    STATE.push("完成：新增 %d 条，页面成功 %d/%d，用时 %.1fs" % (
        STATE.new_count, STATE.pages_ok, STATE.pages_total, elapsed))
    return {
        "ok": True, "run_id": STATE.run_id, "new": STATE.new_count,
        "accepted": STATE.accepted, "raw": STATE.raw_count,
        "pages_ok": STATE.pages_ok, "pages_total": STATE.pages_total,
        "elapsed": round(elapsed, 2), "exported": exported,
        "items": all_new,
    }


def run_async(**kw) -> bool:
    if STATE.running:
        return False
    threading.Thread(target=run_once, kwargs=kw, daemon=True).start()
    return True
