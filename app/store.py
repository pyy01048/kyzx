# -*- coding: utf-8 -*-
"""SQLite 持久层：通知条目、院校源健康度、采集批次。"""
from __future__ import annotations

import datetime
import sqlite3
from contextlib import contextmanager
from typing import Dict, Iterable, List, Optional

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    school       TEXT NOT NULL,
    title        TEXT NOT NULL,
    url          TEXT NOT NULL UNIQUE,
    publish_date TEXT DEFAULT '',
    score        INTEGER DEFAULT 0,
    tags         TEXT DEFAULT '',
    reasons      TEXT DEFAULT '',
    status       TEXT DEFAULT 'new',      -- new | review | starred | ignored
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    run_id       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_items_school ON items(school);
CREATE INDEX IF NOT EXISTS idx_items_seen ON items(first_seen);

CREATE TABLE IF NOT EXISTS sources (
    school     TEXT NOT NULL,
    url        TEXT NOT NULL,
    status     TEXT DEFAULT 'idle',       -- ok | blocked | timeout | error | idle
    http       INTEGER DEFAULT 0,
    error_kind TEXT DEFAULT '',
    error      TEXT DEFAULT '',
    elapsed    REAL DEFAULT 0,
    items      INTEGER DEFAULT 0,
    checked_at TEXT DEFAULT '',
    PRIMARY KEY (school, url)
);

CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT NOT NULL,
    finished_at   TEXT DEFAULT '',
    status        TEXT DEFAULT 'running',
    sources_total INTEGER DEFAULT 0,
    sources_ok    INTEGER DEFAULT 0,
    pages_total   INTEGER DEFAULT 0,
    pages_ok      INTEGER DEFAULT 0,
    raw_count     INTEGER DEFAULT 0,
    accepted      INTEGER DEFAULT 0,
    new_count     INTEGER DEFAULT 0,
    avg_elapsed   REAL DEFAULT 0
);
"""


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def start_run(sources_total: int) -> int:
    with connect() as c:
        cur = c.execute("INSERT INTO runs(started_at, sources_total) VALUES (?, ?)",
                        (now(), sources_total))
        return int(cur.lastrowid)


def finish_run(run_id: int, **kw) -> None:
    fields = ["status = ?", "finished_at = ?"]
    vals: List = [kw.get("status", "done"), now()]
    for k in ("sources_ok", "pages_total", "pages_ok", "raw_count",
              "accepted", "new_count", "avg_elapsed"):
        if k in kw:
            fields.append("%s = ?" % k)
            vals.append(kw[k])
    vals.append(run_id)
    with connect() as c:
        c.execute("UPDATE runs SET %s WHERE id = ?" % ", ".join(fields), vals)


def save_source(school: str, url: str, status: str, http: int = 0,
                error_kind: str = "", error: str = "", elapsed: float = 0.0,
                items: int = 0) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO sources(school,url,status,http,error_kind,error,elapsed,items,checked_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(school,url) DO UPDATE SET
                 status=excluded.status, http=excluded.http,
                 error_kind=excluded.error_kind, error=excluded.error,
                 elapsed=excluded.elapsed, items=excluded.items,
                 checked_at=excluded.checked_at""",
            (school, url, status, http, error_kind, error[:300], elapsed, items, now()))


def insert_item(school: str, title: str, url: str, publish_date: str, score: int,
                tags: Iterable[str], reasons: Iterable[str], run_id: int,
                status: str = "new") -> bool:
    ts = now()
    with connect() as c:
        cur = c.execute(
            """INSERT OR IGNORE INTO items
               (school,title,url,publish_date,score,tags,reasons,status,first_seen,last_seen,run_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (school, title, url, publish_date, score, ",".join(tags),
             " | ".join(reasons), status, ts, ts, run_id))
        return cur.rowcount > 0


def query_items(school: str = "", status: str = "", q: str = "", tag: str = "",
                limit: int = 200, offset: int = 0) -> List[Dict]:
    sql = "SELECT * FROM items WHERE 1=1"
    vals: List = []
    if school:
        sql += " AND school = ?"
        vals.append(school)
    if status:
        sql += " AND status = ?"
        vals.append(status)
    if tag:
        sql += " AND tags LIKE ?"
        vals.append("%" + tag + "%")
    if q:
        sql += " AND (title LIKE ? OR school LIKE ?)"
        vals += ["%" + q + "%", "%" + q + "%"]
    sql += " ORDER BY (publish_date = '') ASC, publish_date DESC, score DESC, id DESC LIMIT ? OFFSET ?"
    vals += [limit, offset]
    with connect() as c:
        return [dict(r) for r in c.execute(sql, vals)]


def update_status(item_id: int, status: str) -> bool:
    with connect() as c:
        cur = c.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))
        return cur.rowcount > 0


def stats() -> Dict:
    today = datetime.date.today().isoformat()
    with connect() as c:
        total = c.execute("SELECT COUNT(*) n FROM items").fetchone()["n"]
        today_new = c.execute("SELECT COUNT(*) n FROM items WHERE first_seen LIKE ?",
                              (today + "%",)).fetchone()["n"]
        review = c.execute("SELECT COUNT(*) n FROM items WHERE status='review'").fetchone()["n"]
        schools = c.execute("SELECT COUNT(DISTINCT school) n FROM items").fetchone()["n"]
        src_total = c.execute("SELECT COUNT(*) n FROM sources").fetchone()["n"]
        src_ok = c.execute("SELECT COUNT(*) n FROM sources WHERE status='ok'").fetchone()["n"]
        last = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        avg_score = c.execute("SELECT AVG(score) v FROM items").fetchone()["v"] or 0
        by_school = [dict(r) for r in c.execute(
            """SELECT school, COUNT(*) n, MAX(publish_date) latest
               FROM items GROUP BY school ORDER BY n DESC""")]
        trend = [dict(r) for r in c.execute(
            """SELECT substr(first_seen,1,10) d, COUNT(*) n FROM items
               GROUP BY d ORDER BY d DESC LIMIT 14""")]
    return {
        "total": total,
        "today_new": today_new,
        "review": review,
        "schools": schools,
        "sources_total": src_total,
        "sources_ok": src_ok,
        "avg_score": round(avg_score, 1),
        "last_run": dict(last) if last else None,
        "by_school": by_school,
        "trend": list(reversed(trend)),
    }


def source_health() -> List[Dict]:
    with connect() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM sources ORDER BY (status='ok') ASC, school")]
    return rows
