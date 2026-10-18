# -*- coding: utf-8 -*-
"""命令行跑一轮采集（给 Windows 计划任务 / cron 用）。

    conda run -n pyy python scripts/monitor_once.py
    conda run -n pyy python scripts/monitor_once.py --legacy "D:\\咨询"
    conda run -n pyy python scripts/monitor_once.py --school 四川大学 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import pipeline, store  # noqa: E402
from app.config import LEGACY_ROOT  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="研讯 · 单次采集")
    ap.add_argument("--school", default="", help="只采某个院校")
    ap.add_argument("--limit", type=int, default=0, help="只采前 N 个源，调试用")
    ap.add_argument("--legacy", default="", help="同时按旧格式写 markdown 的根目录")
    ap.add_argument("--dry-run", action="store_true", help="不写数据库")
    args = ap.parse_args()

    store.init_db()
    if args.dry_run:
        from app.crawler.fetcher import Fetcher
        from app.crawler.parser import extract_candidates
        from app.crawler.sources import SOURCES
        import datetime
        from app.crawler.classifier import classify

        f = Fetcher()
        for src in SOURCES[: args.limit or len(SOURCES)]:
            r = f.get(src.urls[0])
            if not r.ok:
                print("ERR", src.school, r.error_kind, r.error)
                continue
            cands = extract_candidates(r.html, r.final_url, src.school)
            hits = [c for c in cands if classify(c.title, c.context, c.publish_date).accepted]
            print("%-12s 解析 %3d 命中 %2d" % (src.school, len(cands), len(hits)))
        f.close()
        return 0

    root = args.legacy or (str(LEGACY_ROOT) if LEGACY_ROOT.is_dir() else "")
    res = pipeline.run_once(school=args.school, limit=args.limit, legacy_root=root)
    print(json.dumps({k: v for k, v in res.items() if k != "items"},
                     ensure_ascii=False, indent=2))
    for it in res.get("items", [])[:20]:
        print(" +", it["school"], it["title"], it["url"])
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
