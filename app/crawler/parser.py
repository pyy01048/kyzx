# -*- coding: utf-8 -*-
"""列表页解析：从任意院校列表页里抽出「标题 + 链接 + 发布日期 + 上下文」。

相比旧版纯正则的两个关键改进：
  * 日期从锚点**所在行**（li/tr/div）取，而不是只从标题文字里取，
    解决了「标题不含年份 → 真实通知被漏掉」的问题；
  * 兼容 <li title="...">、图片链接、以及被截断的省略标题。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

DATE_PATTERNS = [
    re.compile(r"(20\d{2})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})"),
    re.compile(r"(20\d{2})\s*[-/.年]\s*(\d{1,2})\s*月?"),
    re.compile(r"(?<!\d)(\d{1,2})\s*[-/.]\s*(\d{1,2})(?!\d)"),
]

JUNK_HREF = re.compile(
    r"(javascript:|^#|mailto:|tel:|\.(?:jpg|jpeg|png|gif|zip|rar|doc|docx|xls|xlsx|ppt|pptx)$)", re.I)
JUNK_TEXT = re.compile(r"^(首页|上一页|下一页|尾页|更多|more|返回|登录|注册|English|EN|搜索)$", re.I)
NAV_WORDS = ("首页", "学院概况", "招生工作", "培养工作", "学位工作", "联系我们", "下载中心",
             "党建", "师资", "科学研究", "学科建设", "友情链接", "管理系统", "English")

NAV_TAGS = {"nav", "header", "footer"}
NAV_ATTR = re.compile(
    r"(^|[-_])(nav|navbar|menu|sidebar|side|crumb|breadcrumb|topbar|header|footer|quick|search|login)([-_]|$)",
    re.I)

STRIP_PREFIX = re.compile(r"^[\s\[【(（]*(置顶|顶|新|hot|new|推荐)[\]】)）]*\s*", re.I)
STRIP_INDEX = re.compile(r"^\s*\d{1,3}[.、)）]\s*")
# 部分站点把「阅读数 + 日期」一起塞进锚点文字，如「29 2026.09 招生章程」
STRIP_LEAD_META = re.compile(
    r"^\s*\d{1,4}\s+(\d{4}[./-]\d{1,2}([./-]\d{1,2})?|\d{1,2}[./-]\d{1,2})\s+")
STRIP_TAIL = re.compile(r"\s*[\(（\[【]?\s*20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\s*[\)）\]】]?\s*$")
STRIP_TAIL_MD = re.compile(r"\s*[\(（\[【]?\s*\d{4}[-/.]\d{1,2}\s*[\)）\]】]?\s*$")
WS = re.compile(r"[\s\u3000\xa0]+")


@dataclass
class Candidate:
    school: str
    title: str
    url: str
    publish_date: str = ""
    context: str = ""
    page_url: str = ""

    def as_dict(self):
        return {
            "school": self.school,
            "title": self.title,
            "url": self.url,
            "publish_date": self.publish_date,
            "context": self.context[:200],
            "page_url": self.page_url,
        }


def normalize_title(raw: str) -> str:
    t = WS.sub(" ", (raw or "")).strip()
    t = STRIP_PREFIX.sub("", t)
    t = STRIP_INDEX.sub("", t)
    t = STRIP_LEAD_META.sub("", t)
    t = STRIP_TAIL.sub("", t)
    t = STRIP_TAIL_MD.sub("", t)
    t = t.strip(" 　-—_|·•,，。;；:：")
    return t


def parse_date(text: str) -> str:
    if not text:
        return ""
    for idx, pat in enumerate(DATE_PATTERNS):
        m = pat.search(text)
        if not m:
            continue
        g = m.groups()
        if idx == 0:
            y, mo, d = g
        elif idx == 1:
            y, mo = g
            d = "01"
        else:
            continue  # 无年份的月日无法可靠定位年份，丢弃避免误判
        try:
            y, mo, d = int(y), int(mo), int(d)
            if not (1 <= mo <= 12 and 1 <= d <= 31):
                continue
            return "%04d-%02d-%02d" % (y, mo, d)
        except ValueError:
            continue
    return ""


def canonical_url(url: str) -> str:
    try:
        p = urlparse(url)
    except Exception:
        return url
    path = re.sub(r"/{2,}", "/", p.path or "/")
    path = re.sub(r"/index\.(?:html?|shtml?)$", "/", path, flags=re.I)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = re.sub(r"(^|&)(utm_[^&]*|from=[^&]*|spm=[^&]*)", r"\1", p.query or "").strip("&")
    return urlunparse((p.scheme or "http", p.netloc.lower(), path, "", query, ""))


def _in_nav(a) -> bool:
    """判断锚点是否位于导航/页脚等非内容区域。"""
    for p in a.parents:
        name = getattr(p, "name", "")
        if name in NAV_TAGS:
            return True
        if name == "body":
            break
        cls = p.get("class") or []
        attrs = " ".join(cls) + " " + (p.get("id") or "")
        if attrs.strip() and NAV_ATTR.search(attrs):
            return True
    return False


def _row_text(a) -> str:
    """取锚点所在行文本，用于找发布日期。

    从父节点逐层向上，**优先返回第一个含日期的祖先**：
    很多院校用 <tr><td>标题</td><td>2026-10-15</td></tr> 的表格布局，
    只取最近的父节点（td）看不到日期，这正是旧版「标题没写年份就漏抓」的根因。
    """
    fallback = ""
    node = a.parent
    for _ in range(6):
        if node is None:
            break
        txt = WS.sub(" ", node.get_text(" ", strip=True))
        if len(txt) <= 400 and parse_date(txt):
            return txt
        if not fallback and len(txt) <= 300:
            fallback = txt
        node = node.parent
    return fallback or WS.sub(" ", a.get_text(" ", strip=True))


def extract_candidates(html: str, page_url: str, school: str) -> List[Candidate]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()

    seen = set()
    out: List[Candidate] = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or JUNK_HREF.search(href):
            continue
        if _in_nav(a):
            continue
        raw_text = WS.sub(" ", a.get_text(" ", strip=True))
        if not raw_text:
            raw_text = a.get("title") or ""
        if not raw_text:
            img = a.find("img")
            if img is not None:
                raw_text = img.get("alt") or img.get("title") or ""
        title = normalize_title(raw_text)
        if not title or len(title) < 6 or len(title) > 120:
            continue
        if JUNK_TEXT.match(title) or title in NAV_WORDS:
            continue
        if sum(1 for w in NAV_WORDS if w in title) >= 2:
            continue
        url = canonical_url(urljoin(page_url, href))
        if url in seen:
            continue
        seen.add(url)
        ctx = _row_text(a)
        out.append(Candidate(
            school=school,
            title=title,
            url=url,
            publish_date=parse_date(ctx) or parse_date(title),
            context=ctx,
            page_url=page_url,
        ))
    return out
