# -*- coding: utf-8 -*-
"""去重：URL 规范化 + 标题 SimHash 近似判重。

跨院校重复（同一份教育部文件被多校转载）与同站不同栏目重复都能识别。
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Tuple

from .parser import canonical_url

PUNCT = re.compile(r"[\s\u3000\xa0,，。.、；;：:！!？?“”\"'（）()\[\]【】<>《》\-—_/\\|·•]+")


def normalize(text: str) -> str:
    return PUNCT.sub("", (text or "").lower())


def _shingles(text: str, n: int = 3) -> List[str]:
    t = normalize(text)
    if len(t) <= n:
        return [t] if t else []
    return [t[i:i + n] for i in range(len(t) - n + 1)]


def simhash(text: str, bits: int = 64) -> int:
    weights = [0] * bits
    for sh in _shingles(text):
        h = int(hashlib.md5(sh.encode("utf-8")).hexdigest()[:16], 16)
        for i in range(bits):
            weights[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i in range(bits):
        if weights[i] > 0:
            out |= (1 << i)
    return out


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def jaccard(a: str, b: str) -> float:
    sa, sb = set(_shingles(a)), set(_shingles(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class Deduper:
    """内存索引；条目量大时可换成持久化索引。"""

    def __init__(self, distance: int = 3, jaccard_threshold: float = 0.82):
        self.distance = distance
        self.jaccard_threshold = jaccard_threshold
        self._urls: Dict[str, int] = {}
        self._hashes: List[Tuple[int, str, str]] = []

    def add(self, url: str, title: str, key: str) -> None:
        self._urls[canonical_url(url)] = 1
        self._hashes.append((simhash(title), key, title))

    def seen_url(self, url: str) -> bool:
        return canonical_url(url) in self._urls

    def find_dup(self, url: str, title: str) -> str:
        if self.seen_url(url):
            return "url"
        h = simhash(title)
        for hh, key, other in self._hashes:
            if hamming(h, hh) <= self.distance:
                return key
            # 标题被加上「（更新）」「（修订）」这类后缀时 SimHash 距离会变大，
            # 用 3-gram Jaccard 兜住这种真实重复。
            if jaccard(title, other) >= self.jaccard_threshold:
                return key
        return ""

    def build(self, rows: Iterable[Tuple[str, str, str]]) -> "Deduper":
        for url, title, key in rows:
            self.add(url, title, key)
        return self
