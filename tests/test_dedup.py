# -*- coding: utf-8 -*-
from app.crawler.dedup import Deduper, hamming, jaccard, simhash


def test_near_duplicate_detected():
    a = "2027年硕士研究生招生简章"
    b = "2027年硕士研究生招生简章（更新）"
    assert jaccard(a, b) >= 0.82


def test_unrelated_titles_far_apart():
    a = "2027年硕士研究生招生简章"
    b = "关于开展校园消防安全演练的通知"
    assert hamming(simhash(a), simhash(b)) > 10


def test_deduper_blocks_same_url_and_near_title():
    d = Deduper()
    d.add("https://a.edu.cn/1", "2027年硕士研究生招生简章", "a1")
    assert d.find_dup("https://a.edu.cn/1?utm_source=x", "别的标题") == "url"
    assert d.find_dup("https://b.edu.cn/2", "2027年硕士研究生招生简章（更新）") == "a1"
    assert d.find_dup("https://c.edu.cn/3", "校园招聘会通知") == ""
