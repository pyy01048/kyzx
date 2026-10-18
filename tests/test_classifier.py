# -*- coding: utf-8 -*-
import datetime

from app.crawler.classifier import classify

TODAY = datetime.date(2026, 10, 18)


def test_strong_keyword_with_year_accepted():
    v = classify("四川大学2027年硕士研究生招生章程", "", "2026-10-17", today=TODAY)
    assert v.accepted and v.score >= 60
    assert "招生简章" in v.tags


def test_year_conflict_rejected():
    v = classify("2026年硕士研究生招生简章", "", "2025-10-01", today=TODAY)
    assert not v.accepted
    assert any("年份冲突" in r for r in v.reasons)


def test_recruitment_noise_rejected():
    v = classify("2027年硕士研究生招生工作招聘公告", "", "2026-10-17", today=TODAY)
    assert not v.accepted


def test_date_comes_from_context():
    v = classify("关于做好硕士研究生招生工作的通知", "2026-10-11 研究生院", "2026-10-11", today=TODAY)
    assert v.score > 0
    assert v.accepted is False  # 信息不足，进复核而不是直接入库


def test_low_confidence_goes_to_review_band():
    v = classify("2027年招生通知公告", "", "2026-10-17", today=TODAY, threshold=45)
    assert v.accepted and 45 <= v.score < 60


def test_stale_notice_penalised():
    fresh = classify("2027年硕士研究生复试分数线", "", "2026-10-17", today=TODAY)
    stale = classify("2027年硕士研究生复试分数线", "", "2025-12-01", today=TODAY)
    assert fresh.score > stale.score
