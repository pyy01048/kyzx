# -*- coding: utf-8 -*-
from app.crawler.parser import canonical_url, extract_candidates, normalize_title, parse_date

LIST_HTML = """
<html><body>
<div class="nav"><a href="/">首页</a><a href="/yjsy">研究生院</a></div>
<ul class="news">
  <li><a href="/info/1008/5401.htm">云南大学2027年接收推荐免试研究生章程</a>
      <span class="date">2026-10-14</span></li>
  <li><span class="date">2026-10-12</span>
      <a href="/info/1008/5402.htm" title="2027年硕士研究生招生考试参考书目">2027年硕士研究生招生考试参考书目</a></li>
  <li><a href="/info/1008/5403.htm">关于做好硕士研究生招生工作的通知</a>
      <span>2026-10-11</span></li>
  <li><a href="javascript:void(0)">返回顶部</a></li>
</ul>
</body></html>
"""


def test_date_from_sibling_node():
    cands = extract_candidates(LIST_HTML, "http://www.grs.ynu.edu.cn/zsgz/qrzssyjs.htm", "云南大学")
    by_url = {c.url: c for c in cands}
    first = by_url["http://www.grs.ynu.edu.cn/info/1008/5401.htm"]
    # 旧脚本只看标题文字，拿不到这个日期
    assert first.publish_date == "2026-10-14"


def test_nav_and_js_links_filtered():
    cands = extract_candidates(LIST_HTML, "http://www.grs.ynu.edu.cn/", "云南大学")
    urls = [c.url for c in cands]
    assert all("javascript" not in u for u in urls)
    assert not any(c.title in ("首页", "研究生院") for c in cands)
    assert len(cands) == 3


def test_title_normalization():
    assert normalize_title("  [置顶] 2027年硕士研究生招生简章 2026-10-12 ") == "2027年硕士研究生招生简章"
    assert normalize_title("1. 2027年专业目录") == "2027年专业目录"
    # 阅读数 + 日期被一起塞进锚点文字的情况
    assert normalize_title("29 2026.09 西南大学2027年硕士研究生招生章程") == "西南大学2027年硕士研究生招生章程"


def test_parse_date_formats():
    assert parse_date("发布时间：2026年9月30日") == "2026-09-30"
    assert parse_date("2026/09/30") == "2026-09-30"
    assert parse_date("09-30") == ""          # 无年份不猜


def test_canonical_url():
    assert canonical_url("https://yz.scu.edu.cn/zsxx/index.htm") == "https://yz.scu.edu.cn/zsxx"
    assert canonical_url("https://a.edu.cn/n/1?utm_source=x&id=2") == "https://a.edu.cn/n/1?id=2"
