# -*- coding: utf-8 -*-
"""院校源注册表。

每个源可覆盖抓取策略：
    render=True  该站必须走浏览器渲染（JS 列表 / 强反爬）
    headers={}   额外请求头
    encoding=""  强制编码
    referer=""   指定 Referer（部分站点校验来源页）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Source:
    school: str
    urls: List[str]
    region: str = ""
    tags: List[str] = field(default_factory=list)
    render: bool = False
    encoding: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    referer: str = ""


def _s(school, urls, region="", **kw):
    return Source(school=school, urls=urls, region=region, **kw)


SOURCES: List[Source] = [
    _s("四川大学", ["https://yz.scu.edu.cn/", "https://yz.scu.edu.cn/zsxx/newslist/a/gg/1"], "四川"),
    _s("贵州大学", ["https://gs.gzu.edu.cn/"], "贵州"),
    _s("西南石油大学", ["https://www.swpu.edu.cn/gs/zsgz/tzgg.htm"], "四川"),
    _s("西南交通大学", ["https://yz.swjtu.edu.cn/"], "四川", render=True),
    _s("西南大学", ["https://yz.swu.edu.cn/", "https://yz.swu.edu.cn/zsxx/sszs/zsjz.htm"], "重庆"),
    _s("贵州师范大学", ["https://yjsc.gznu.edu.cn/zsgl/ssyjs.htm"], "贵州"),
    _s("贵州医科大学", ["https://yjsxy.gmc.edu.cn/zsxx/sszs.htm"], "贵州"),
    _s("贵州中医药大学", ["https://yjs.gzy.edu.cn/"], "贵州", render=True),
    _s("贵阳学院", ["https://yjsy.gyu.edu.cn/"], "贵州"),
    _s("贵州民族大学", ["https://yjsy.gzmu.edu.cn/tzgg"], "贵州"),
    _s("广西民族大学", ["https://yjs.gxmzu.edu.cn/zsgz/sszs.htm"], "广西"),
    _s("西南民族大学", ["https://yjsglxt.swun.edu.cn/index/tzgg.htm"], "四川", render=True),
    _s("桂林电子科技大学", ["https://www.guet.edu.cn/yjszs/4230/list.htm"], "广西"),
    _s("桂林理工大学", ["https://yjsy.glut.edu.cn/xwgl/sszs.htm"], "广西"),
    _s("广西大学", ["https://yjsc.gxu.edu.cn/zsgz/sszs.htm"], "广西"),
    _s("广西科技大学", ["https://www.gxust.edu.cn/yjs/zsgz.htm"], "广西"),
    _s("云南大学", ["http://www.grs.ynu.edu.cn/zsgz/qrzssyjs.htm"], "云南"),
    _s("昆明理工大学", ["https://www.kmust.edu.cn/zsjy/ssyjszs.htm"], "云南"),
    _s("重庆大学", ["https://yz.cqu.edu.cn/"], "重庆"),
    _s("重庆邮电大学", ["https://yjs.cqupt.edu.cn/zsxx/zsjz.htm"], "重庆", render=True),
    _s("研招网", ["https://yz.chsi.com.cn/"], "全国"),
    _s("教育部", ["http://www.moe.gov.cn/"], "全国"),
]

SCHOOLS = [s.school for s in SOURCES]
BY_SCHOOL = {s.school: s for s in SOURCES}
