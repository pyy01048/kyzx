# -*- coding: utf-8 -*-
"""端到端：本地起一个假院校站点，跑完整采集流水线。"""
import http.server
import socketserver
import threading

import pytest

from app import pipeline, store
from app.crawler.sources import Source

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<ul class="list">
  <li><a href="/info/1001.htm">2027年硕士研究生招生章程</a><span>2026-10-17</span></li>
  <li><a href="/info/1002.htm">关于2027年硕士研究生招生专业目录的说明</a><span>2026-10-16</span></li>
  <li><a href="/info/1003.htm">2027年硕士研究生招生章程（更新）</a><span>2026-10-16</span></li>
  <li><a href="/info/1004.htm">学院2027年人才招聘公告</a><span>2026-10-15</span></li>
  <li><a href="/info/1005.htm">2026年硕士研究生招生简章</a><span>2025-10-15</span></li>
  <li><a href="/info/1006.htm">关于开展消防演练的通知</a><span>2026-10-14</span></li>
</ul></body></html>"""


@pytest.fixture(scope="module")
def fake_site():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d/list.htm" % port
    httpd.shutdown()


def test_pipeline_end_to_end(fake_site, monkeypatch):
    store.init_db()
    with store.connect() as c:
        c.execute("DELETE FROM items")

    fake = Source(school="测试大学", urls=[fake_site], region="测试")
    monkeypatch.setattr(pipeline, "SOURCES", [fake])

    res = pipeline.run_once()
    assert res["ok"] is True
    assert res["pages_ok"] == 1 and res["pages_total"] == 1
    # 招聘、旧年份、无关通知都不应入库；「（更新）」被判为重复
    titles = [it["title"] for it in res["items"]]
    assert "2027年硕士研究生招生章程" in titles
    assert not any("招聘" in t for t in titles)
    assert not any(t.startswith("2026年") for t in titles)
    assert not any("消防" in t for t in titles)
    assert len(titles) == len(set(titles))

    rows = store.query_items(school="测试大学")
    assert len(rows) == len(titles)
    assert all(r["score"] >= 45 for r in rows)
    assert all(r["url"].startswith("http://127.0.0.1") for r in rows)


def test_second_run_is_idempotent(fake_site, monkeypatch):
    fake = Source(school="测试大学", urls=[fake_site], region="测试")
    monkeypatch.setattr(pipeline, "SOURCES", [fake])
    before = len(store.query_items(school="测试大学", limit=500))
    res = pipeline.run_once()
    after = len(store.query_items(school="测试大学", limit=500))
    assert res["ok"] is True
    assert after == before  # 重复采集不会产生重复条目
