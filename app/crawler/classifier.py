# -*- coding: utf-8 -*-
"""相关度打分：把「关键词硬匹配」换成可解释的加权打分。

旧逻辑的漏抓与误抓来源：
  * 只认标题里出现 2027/2028 -> 大量真实通知被丢（日期在别的节点）；
  * 「硕士」单字命中即算相关 -> 讲座、招聘、本科通知全部进来；
  * 没有年份冲突判断 -> 2026 年的旧公告只要标题带 2027 也能混入。

新逻辑：强/中/弱三级词表 + 年份冲突惩罚 + 负向词惩罚 + 时效衰减，
输出 0~100 分与命中理由，低于阈值的进入「待复核」而不是直接丢弃。
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import List, Sequence

STRONG = {
    "招生简章": 30, "招生章程": 30, "专业目录": 28, "招生专业目录": 30,
    "考试大纲": 28, "参考书目": 26, "初试科目": 26, "科目调整": 26, "改考": 24,
    "推免": 22, "免试": 18, "调剂": 22, "复试": 20, "分数线": 22, "复试线": 24,
    "拟录取": 24, "录取名单": 22, "网上报名": 24, "报名公告": 24, "报考": 16,
    "招生计划": 22, "招生人数": 18, "硕士研究生": 18, "博士研究生": 4,
}
MEDIUM = {
    "招生": 12, "硕士": 10, "研究生": 8, "简章": 10, "目录": 8, "大纲": 10,
    "通知": 6, "公告": 6, "公告栏": 4, "安排": 4, "工作": 3, "细则": 8,
    "办法": 6, "方案": 5, "说明": 4, "名单": 8, "公示": 8,
}
NEGATIVE = {
    "招聘": -28, "人事": -22, "采购": -26, "中标": -26, "招标": -26, "成交": -22,
    "博士后": -20, "本科招生": -22, "专升本": -26, "成人教育": -24, "继续教育": -22,
    "自考": -24, "培训": -16, "讲座": -18, "会议": -12, "论坛": -12, "竞赛": -16,
    "奖学金": -14, "助学金": -12, "贷款": -12, "宿舍": -10, "招标公告": -26,
    "教师": -16, "辅导员": -16, "附属": -10, "幼儿园": -20, "小学": -20,
}
TAGS = [
    ("招生简章", ("招生简章", "招生章程", "简章")),
    ("专业目录", ("专业目录", "招生专业", "招生计划")),
    ("考试科目", ("初试科目", "科目调整", "改考", "考试大纲", "参考书目")),
    ("推免", ("推免", "免试", "夏令营")),
    ("复试调剂", ("复试", "调剂", "分数线", "复试线")),
    ("录取", ("拟录取", "录取名单", "录取结果")),
    ("报名", ("报名", "网报", "报考")),
]

YEAR_RE = re.compile(r"(20\d{2})\s*年?")
TARGET_YEARS = ("2027", "2028")


@dataclass
class Verdict:
    score: int
    accepted: bool
    reasons: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    year: str = ""

    def as_dict(self):
        return {"score": self.score, "accepted": self.accepted,
                "reasons": self.reasons, "tags": self.tags, "year": self.year}


def _hits(text: str, table) -> List[str]:
    return [w for w in table if w in text]


def _recency(publish_date: str, today: datetime.date, window: int = 120) -> int:
    if not publish_date:
        return 0
    try:
        d = datetime.date.fromisoformat(publish_date)
    except ValueError:
        return 0
    delta = (today - d).days
    if delta < -7:          # 未来日期，可能是页面写错
        return -6
    if delta <= 14:
        return 8
    if delta <= 45:
        return 4
    if delta <= window:
        return 0
    return -12


def classify(title: str, context: str = "", publish_date: str = "",
             today: datetime.date | None = None,
             target_years: Sequence[str] = TARGET_YEARS,
             threshold: int = 45) -> Verdict:
    today = today or datetime.date.today()
    text = "%s %s" % (title or "", context or "")
    score = 0
    reasons: List[str] = []

    # 标题里写死的年份若不在目标年份内，直接判负：这类多是往年公告，
    # 靠关键词叠加分数很容易被误捞进来。
    title_years = YEAR_RE.findall(title or "")
    if title_years and not any(y in target_years for y in title_years):
        return Verdict(score=0, accepted=False,
                       reasons=["年份冲突：标题为 %s，不在目标年份内" % title_years[0]], tags=[],
                       year=title_years[0])

    strong = _hits(text, STRONG)
    if strong:
        add = min(sum(STRONG[w] for w in strong), 46)
        score += add
        reasons.append("命中核心词：" + "、".join(strong[:4]))

    medium = _hits(title, MEDIUM)
    if medium:
        score += min(sum(MEDIUM[w] for w in medium), 22)
        reasons.append("主题词：" + "、".join(medium[:4]))

    years = YEAR_RE.findall(text)
    year = ""
    if years:
        target_hit = [y for y in years if y in target_years]
        if target_hit:
            year = target_hit[0]
            score += 18
            reasons.append("目标年份 %s" % year)
        else:
            score -= 14
            reasons.append("年份冲突（%s）" % years[0])
    elif "招生" in text or "硕士" in text:
        score += 2
        reasons.append("未标注年份，按栏目推断")

    neg = _hits(text, NEGATIVE)
    if neg:
        score += sum(NEGATIVE[w] for w in neg)
        reasons.append("负向词：" + "、".join(neg[:3]))

    score += _recency(publish_date, today)

    # 无日期 + 短标题，多半是栏目名或导航链接，不是一条通知
    if not publish_date and len(title or "") <= 8:
        score -= 30
        reasons.append("无日期且标题过短，疑似栏目名")

    tags = [name for name, kws in TAGS if any(k in text for k in kws)]
    score = max(0, min(100, score))
    return Verdict(score=score, accepted=score >= threshold, reasons=reasons,
                   tags=tags, year=year)


def batch_classify(items, today=None, threshold=45):
    for it in items:
        v = classify(it.title, it.context, it.publish_date, today=today, threshold=threshold)
        it.score = v.score
        it.accepted = v.accepted
        it.reasons = v.reasons
        it.tags = v.tags
    return items
