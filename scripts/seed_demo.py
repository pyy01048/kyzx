# -*- coding: utf-8 -*-
"""写入一批演示数据，用于本地预览页面 / 生成 README 截图。

    python scripts/seed_demo.py [--reset]

演示数据只写进本地 SQLite，不影响真实采集逻辑。
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import store  # noqa: E402

DEMO = [
    ("四川大学", "四川大学2027年硕士研究生招生章程", "https://yz.scu.edu.cn/zsxx/Details/2027-zszc", "2026-10-17", 96, "招生简章,报名", "命中核心词：招生章程 | 目标年份 2027"),
    ("四川大学", "关于2027年硕士研究生招生专业目录调整的说明", "https://yz.scu.edu.cn/zsxx/Details/2027-zyml", "2026-10-16", 92, "专业目录", "命中核心词：专业目录 | 目标年份 2027"),
    ("重庆大学", "重庆大学2027年硕士研究生招生简章发布", "https://yz.cqu.edu.cn/news/2027/jz.html", "2026-10-15", 94, "招生简章", "命中核心词：招生简章 | 目标年份 2027"),
    ("重庆大学", "2027年硕士研究生初试科目调整公告", "https://yz.cqu.edu.cn/news/2027/kskm.html", "2026-10-14", 90, "考试科目", "命中核心词：初试科目、科目调整"),
    ("云南大学", "云南大学2027年接收推荐免试研究生章程", "http://www.grs.ynu.edu.cn/info/1008/5401.htm", "2026-10-14", 88, "推免", "命中核心词：推免 | 目标年份 2027"),
    ("云南大学", "2027年硕士研究生招生考试参考书目", "http://www.grs.ynu.edu.cn/info/1008/5402.htm", "2026-10-12", 86, "考试科目", "命中核心词：参考书目"),
    ("贵州大学", "贵州大学2027年硕士研究生招生专业目录", "https://gs.gzu.edu.cn/2027/zyml.htm", "2026-10-13", 93, "专业目录", "命中核心词：专业目录 | 目标年份 2027"),
    ("贵州大学", "关于2027年硕士研究生招生考试网上报名的通知", "https://gs.gzu.edu.cn/2027/wb.htm", "2026-10-11", 89, "报名", "命中核心词：网上报名"),
    ("广西大学", "广西大学2027年硕士研究生招生简章", "https://yjsc.gxu.edu.cn/zsgz/sszs/2027.htm", "2026-10-12", 91, "招生简章", "命中核心词：招生简章"),
    ("广西大学", "2027年硕士研究生复试分数线公布", "https://yjsc.gxu.edu.cn/zsgz/sszs/fsx.htm", "2026-10-10", 87, "复试调剂", "命中核心词：复试、分数线"),
    ("西南大学", "西南大学2027年硕士研究生招生章程", "https://yz.swu.edu.cn/zsxx/sszs/zszc.htm", "2026-10-11", 90, "招生简章", "命中核心词：招生章程"),
    ("西南大学", "2027年硕士研究生调剂工作办法", "https://yz.swu.edu.cn/zsxx/sszs/tj.htm", "2026-10-09", 84, "复试调剂", "命中核心词：调剂"),
    ("桂林电子科技大学", "桂林电子科技大学2027年硕士研究生招生专业目录", "https://www.guet.edu.cn/yjszs/2027/list.htm", "2026-10-10", 88, "专业目录", "命中核心词：专业目录"),
    ("桂林理工大学", "2027年硕士研究生招生考试大纲", "https://yjsy.glut.edu.cn/xwgl/sszs/dg.htm", "2026-10-09", 85, "考试科目", "命中核心词：考试大纲"),
    ("贵州师范大学", "贵州师范大学2027年硕士研究生招生简章", "https://yjsc.gznu.edu.cn/zsgl/ssyjs/2027.htm", "2026-10-08", 86, "招生简章", "命中核心词：招生简章"),
    ("贵州医科大学", "2027年硕士研究生招生专业目录及参考书目", "https://yjsxy.gmc.edu.cn/zsxx/sszs/2027.htm", "2026-10-08", 83, "专业目录,考试科目", "命中核心词：专业目录、参考书目"),
    ("昆明理工大学", "昆明理工大学2027年硕士研究生招生简章", "https://www.kmust.edu.cn/zsjy/ssyjszs/2027.htm", "2026-10-07", 84, "招生简章", "命中核心词：招生简章"),
    ("西南石油大学", "关于2027年硕士研究生招生考试初试科目的说明", "https://www.swpu.edu.cn/gs/zsgz/tzgg/2027.htm", "2026-10-07", 82, "考试科目", "命中核心词：初试科目"),
    ("贵州民族大学", "2027年硕士研究生招生公告（一）", "https://yjsy.gzmu.edu.cn/tzgg/2027-1.htm", "2026-10-06", 78, "报名", "命中核心词：招生 | 目标年份 2027"),
    ("贵阳学院", "贵阳学院2027年硕士研究生招生简章", "https://yjsy.gyu.edu.cn/2027/jz.htm", "2026-10-06", 80, "招生简章", "命中核心词：招生简章"),
    ("广西民族大学", "2027年硕士研究生招生专业目录", "https://yjs.gxmzu.edu.cn/zsgz/sszs/2027.htm", "2026-10-05", 81, "专业目录", "命中核心词：专业目录"),
    ("广西科技大学", "2027年硕士研究生招生考试报名公告", "https://www.gxust.edu.cn/yjs/zsgz/2027.htm", "2026-10-05", 79, "报名", "命中核心词：报名公告"),
    ("研招网", "2027年全国硕士研究生招生考试网上报名公告", "https://yz.chsi.com.cn/kyzx/2027/wb.html", "2026-10-04", 95, "报名", "命中核心词：网上报名 | 目标年份 2027"),
    ("研招网", "2027年硕士研究生招生考试时间安排", "https://yz.chsi.com.cn/kyzx/2027/ap.html", "2026-10-03", 88, "报名", "命中核心词：硕士研究生"),
    ("教育部", "2027年全国硕士研究生招生工作管理规定", "http://www.moe.gov.cn/2027/sszs/gd.htm", "2026-09-28", 92, "招生简章", "命中核心词：硕士研究生 | 目标年份 2027"),
    ("贵州中医药大学", "2027年硕士研究生招生专业目录（预发布）", "https://yjs.gzy.edu.cn/2027/zyml.htm", "2026-10-02", 58, "专业目录", "主题词：专业目录 | 未标注年份"),
    ("西南交通大学", "2027年硕士研究生招生简章（待确认）", "https://yz.swjtu.edu.cn/2027/jz.htm", "2026-10-01", 52, "招生简章", "命中核心词：招生简章 | 页面渲染后补抓"),
    ("西南民族大学", "2027年硕士研究生招生公告", "https://yjsglxt.swun.edu.cn/index/tzgg/2027.htm", "2026-09-30", 49, "报名", "主题词：招生 | 页面需浏览器渲染"),
]

# 全量 22 个源的健康度：三个已知问题源按真实日志里的失败类型标注
PROBLEMS = {
    "西南民族大学": ("blocked", 412, "blocked", "HTTP 412（反爬拦截）", 0.44),
    "重庆邮电大学": ("blocked", 412, "blocked", "HTTP 412（反爬拦截）", 0.41),
    "西南交通大学": ("timeout", 0, "timeout", "请求超时", 20.0),
}


def health_rows():
    from app.crawler.sources import SOURCES
    rows = []
    for src in SOURCES:
        if src.school in PROBLEMS:
            st, http, kind, err, el = PROBLEMS[src.school]
            rows.append((src.school, src.urls[0], st, http, kind, err, el, 0))
        else:
            rows.append((src.school, src.urls[0], "ok", 200, "", "", 0.62, 1))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="清空后重建演示数据")
    args = ap.parse_args()

    store.init_db()
    if args.reset:
        with store.connect() as c:
            c.execute("DELETE FROM items")
            c.execute("DELETE FROM sources")
            c.execute("DELETE FROM runs")

    run_id = store.start_run(22)
    n = 0
    for school, title, url, date, score, tags, reasons in DEMO:
        status = "new" if score >= 60 else "review"
        if store.insert_item(school, title, url, date, score, tags.split(","),
                             reasons.split(" | "), run_id, status=status):
            n += 1
    for row in health_rows():
        store.save_source(*row)

    # 把入库时间按加权分布摊到最近 9 天，让趋势图反映真实节奏
    import random
    rnd = random.Random(7)
    weights = [3, 4, 6, 8, 9, 7, 5, 3, 2]
    with store.connect() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM items ORDER BY id")]
        for item_id in ids:
            back = rnd.choices(range(9), weights=weights)[0]
            c.execute("UPDATE items SET first_seen = datetime(first_seen, ?) WHERE id = ?",
                      ("-%d days" % back, item_id))
    rows = health_rows()
    store.finish_run(run_id, status="done",
                     sources_ok=sum(1 for r in rows if r[2] == "ok"),
                     pages_total=len(rows), pages_ok=sum(1 for r in rows if r[2] == "ok"),
                     raw_count=96, accepted=len(DEMO), new_count=len(DEMO),
                     avg_elapsed=1.8)
    print("已写入 %d 条演示数据，%d 个源状态" % (n, len(rows)))


if __name__ == "__main__":
    main()
