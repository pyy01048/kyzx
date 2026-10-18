# -*- coding: utf-8 -*-
import pytest

from app import store
from app.web import app


@pytest.fixture()
def client():
    store.init_db()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["ok"] is True


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "研讯" in r.get_data(as_text=True)


def test_overview_shape(client):
    data = client.get("/api/overview").get_json()
    for key in ("total", "today_new", "sources", "health", "config"):
        assert key in data
    assert len(data["sources"]) == 22


def test_items_and_export(client):
    assert client.get("/api/items").status_code == 200
    r = client.get("/api/export.md")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["Content-Type"]
