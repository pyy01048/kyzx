# -*- coding: utf-8 -*-
"""运行配置，全部可用环境变量覆盖，方便 conda / Docker / CI 三套环境复用。"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _p(env: str, default: str) -> Path:
    return Path(os.environ.get(env) or default).expanduser()


DATA_DIR = _p("YANXUN_DATA", str(BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = _p("YANXUN_DB", str(DATA_DIR / "yanxun.db"))
EXPORT_DIR = _p("YANXUN_EXPORT", str(DATA_DIR / "exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.environ.get("YANXUN_HOST", "127.0.0.1")
PORT = int(os.environ.get("YANXUN_PORT", "8000"))

TARGET_YEARS = tuple(os.environ.get("YANXUN_YEARS", "2027,2028").split(","))
SCORE_THRESHOLD = int(os.environ.get("YANXUN_THRESHOLD", "45"))
FETCH_TIMEOUT = int(os.environ.get("YANXUN_TIMEOUT", "20"))
FETCH_RETRIES = int(os.environ.get("YANXUN_RETRIES", "3"))
PROXY = os.environ.get("YANXUN_PROXY", "")
CONCURRENCY = int(os.environ.get("YANXUN_CONCURRENCY", "4"))

# 旧脚本的输出目录：保持兼容，采集结果仍可落成 markdown
LEGACY_ROOT = _p("KAOYAN_ROOT", r"D:\咨询")
