# -*- coding: utf-8 -*-
"""Flask 应用：页面 + JSON API。"""
from __future__ import annotations

import datetime
from typing import Dict, List

from flask import Flask, Response, jsonify, render_template, request

from . import pipeline, store
from .config import (HOST, PORT, SCORE_THRESHOLD, TARGET_YEARS)
from .crawler.sources import SOURCES

app = Flask(__name__, static_folder="static", template_folder="templates")
app.json.ensure_ascii = False


def _schools_meta() -> List[Dict]:
    return [{"school": s.school, "region": s.region, "urls": s.urls,
             "render": s.render} for s in SOURCES]


@app.get("/")
def index():
    return render_template("index.html",
                           target_years="/".join(TARGET_YEARS),
                           threshold=SCORE_THRESHOLD)


@app.get("/api/overview")
def api_overview():
    st = store.stats()
    st["sources"] = _schools_meta()
    st["health"] = store.source_health()
    st["config"] = {"years": list(TARGET_YEARS), "threshold": SCORE_THRESHOLD}
    return jsonify(st)


@app.get("/api/items")
def api_items():
    rows = store.query_items(
        school=request.args.get("school", ""),
        status=request.args.get("status", ""),
        q=request.args.get("q", ""),
        tag=request.args.get("tag", ""),
        limit=min(int(request.args.get("limit", 120)), 500),
        offset=int(request.args.get("offset", 0)),
    )
    return jsonify({"count": len(rows), "items": rows})


@app.post("/api/items/<int:item_id>/status")
def api_item_status(item_id: int):
    body = request.get_json(silent=True) or {}
    status = body.get("status", "")
    if status not in ("new", "review", "starred", "ignored"):
        return jsonify({"ok": False, "error": "非法状态"}), 400
    return jsonify({"ok": store.update_status(item_id, status)})


@app.post("/api/run")
def api_run():
    body = request.get_json(silent=True) or {}
    if pipeline.STATE.running:
        return jsonify({"ok": False, "error": "任务进行中"}), 409
    started = pipeline.run_async(
        school=body.get("school", ""),
        limit=int(body.get("limit", 0) or 0),
        legacy_root=body.get("legacy_root", ""),
    )
    return jsonify({"ok": started})


@app.get("/api/run/status")
def api_run_status():
    return jsonify(pipeline.STATE.as_dict())


@app.get("/api/export.md")
def api_export():
    rows = store.query_items(limit=500)
    today = datetime.date.today().isoformat()
    lines = ["# %s 考研通知汇总（%s · 研讯）\n" % (today, "/".join(TARGET_YEARS))]
    by: Dict[str, List[Dict]] = {}
    for r in rows:
        by.setdefault(r["school"], []).append(r)
    for school, items in by.items():
        lines.append("## %s（%d 条）\n" % (school, len(items)))
        for it in items:
            lines.append("- [%s](%s) · %s · %d 分" % (
                it["title"], it["url"], it["publish_date"] or "未标注", it["score"]))
        lines.append("")
    body = "\n".join(lines)
    return Response(body, mimetype="text/markdown; charset=utf-8", headers={
        "Content-Disposition": "attachment; filename=yanxun-%s.md" % today})


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True, "time": store.now()})


def main():
    store.init_db()
    print("研讯 · 考研通知监控平台  http://%s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
