# -*- coding: utf-8 -*-
"""带重试、反爬兜底与编码修复的抓取器。

针对旧脚本日志里的三类失败做了处理：
  1. 超时 / 连接重置  -> 指数退避重试（默认 3 次）
  2. 412 Precondition -> 先补 Referer + 预热 Cookie 重试，仍失败标记 blocked
  3. 乱码             -> 依次尝试 header charset / meta charset / utf-8 / gb18030
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional

import requests

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

META_CHARSET = re.compile(rb'<meta[^>]+charset=["\']?\s*([a-zA-Z0-9_\-]+)', re.I)


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int = 0
    html: str = ""
    error_kind: str = ""
    error: str = ""
    attempts: int = 0
    elapsed: float = 0.0
    encoding: str = ""
    final_url: str = ""

    def as_dict(self) -> Dict:
        return {
            "url": self.url,
            "ok": self.ok,
            "status": self.status,
            "error_kind": self.error_kind,
            "error": self.error[:300],
            "attempts": self.attempts,
            "elapsed": round(self.elapsed, 3),
            "encoding": self.encoding,
            "bytes": len(self.html),
        }


class Fetcher:
    def __init__(self, timeout: int = 20, retries: int = 3, backoff: float = 1.2,
                 proxy: Optional[str] = None, sleep: float = 0.4):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self._warmed = set()

    def _headers(self, url: str, extra: Optional[Dict[str, str]] = None,
                 referer: str = "") -> Dict[str, str]:
        h = {
            "User-Agent": random.choice(UA_POOL),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
        }
        if referer:
            h["Referer"] = referer
        if extra:
            h.update(extra)
        return h

    def _decode(self, resp: requests.Response, forced: str = ""):
        raw = resp.content
        if forced:
            try:
                return raw.decode(forced, "replace"), forced
            except LookupError:
                pass
        ctype = resp.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w\-]+)", ctype, re.I)
        candidates = []
        if m:
            candidates.append(m.group(1))
        mm = META_CHARSET.search(raw[:4096])
        if mm:
            candidates.append(mm.group(1).decode("ascii", "ignore"))
        candidates += ["utf-8", "gb18030", "gbk"]
        for enc in candidates:
            try:
                text = raw.decode(enc)
                if enc.lower().replace("-", "") in ("gbk", "gb2312"):
                    text = raw.decode("gb18030", "replace")
                return text, enc
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", "ignore"), "utf-8*"

    def _warm(self, url: str) -> None:
        """访问一次站点根目录拿 Cookie，绕过部分 WAF 的来源校验。"""
        host = re.sub(r"^(https?://[^/]+).*$", r"\1", url)
        if host in self._warmed:
            return
        self._warmed.add(host)
        try:
            self.session.get(host, headers=self._headers(host), timeout=min(10, self.timeout))
        except Exception:
            pass

    def get(self, url: str, extra_headers: Optional[Dict[str, str]] = None,
            encoding: str = "", referer: str = "") -> FetchResult:
        t0 = time.time()
        last = FetchResult(url=url, ok=False)
        for attempt in range(1, self.retries + 1):
            last.attempts = attempt
            try:
                resp = self.session.get(
                    url,
                    headers=self._headers(url, extra_headers, referer),
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                last.status = resp.status_code
                last.final_url = resp.url
                if resp.status_code == 200:
                    text, enc = self._decode(resp, encoding)
                    last.ok, last.html, last.encoding = True, text, enc
                    last.elapsed = time.time() - t0
                    if self.sleep:
                        time.sleep(self.sleep * random.uniform(0.7, 1.3))
                    return last
                if resp.status_code in (412, 403, 406):
                    if attempt == 1:
                        self._warm(url)
                        time.sleep(self.backoff)
                        continue
                    last.error_kind = "blocked"
                    last.error = "HTTP %d（反爬拦截）" % resp.status_code
                elif resp.status_code == 404:
                    last.error_kind = "not_found"
                    last.error = "HTTP 404"
                    break
                elif 500 <= resp.status_code < 600:
                    last.error_kind = "server"
                    last.error = "HTTP %d" % resp.status_code
                else:
                    last.error_kind = "http"
                    last.error = "HTTP %d" % resp.status_code
            except requests.exceptions.Timeout:
                last.error_kind = "timeout"
                last.error = "请求超时"
            except requests.exceptions.SSLError as e:
                last.error_kind = "ssl"
                last.error = "SSL 错误: %s" % e
            except requests.exceptions.ConnectionError as e:
                last.error_kind = "conn"
                last.error = "连接失败: %s" % e
            except Exception as e:  # pragma: no cover
                last.error_kind = "other"
                last.error = repr(e)
            if attempt < self.retries:
                time.sleep(self.backoff ** attempt + random.uniform(0, 0.5))
        last.elapsed = time.time() - t0
        return last

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass
