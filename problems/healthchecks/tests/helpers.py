from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient

DB_ENV = "HEALTHCHECKS_DB_PATH"
CLOCK_ENV = "HEALTHCHECKS_NOW"


@dataclass
class Session:
    email: str
    token: str
    api_key: str
    project_id: str


def error_code(response, status: int | None = None):
    if status is not None:
        assert response.status_code == status, response.text
    doc = response.json()
    assert "detail" not in doc
    assert set(doc) == {"error"}
    assert {"code", "message", "details"} <= set(doc["error"])
    assert isinstance(doc["error"].get("code"), str) and doc["error"]["code"]
    assert isinstance(doc["error"].get("message"), str) and doc["error"]["message"]
    return doc["error"]["code"]


def parse_ts(value: str) -> datetime:
    assert isinstance(value, str)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def register(client: TestClient, email="alice@example.org", password="secret-value") -> Session:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    doc = r.json()
    api_key = doc.get("api_key") or doc.get("project", {}).get("api_key")
    project_id = doc.get("project_id") or doc.get("project", {}).get("id")
    assert isinstance(api_key, str) and api_key
    assert isinstance(project_id, str) and project_id

    lr = client.post("/auth/login", json={"email": email, "password": password})
    assert lr.status_code == 200, lr.text
    login = lr.json()
    assert isinstance(login.get("access_token"), str) and login["access_token"]
    normalized = doc.get("email", email.strip().lower())
    return Session(normalized, login["access_token"], api_key, project_id)


def api(s: Session):
    return {"X-Api-Key": s.api_key}


def bearer(s: Session):
    return {"Authorization": f"Bearer {s.token}"}


def make_check(client: TestClient, s: Session, **overrides):
    body = {"name": "backup", "timeout": 3600, "grace": 60}
    body.update(overrides)
    r = client.post("/checks", headers=api(s), json=body)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert isinstance(doc.get("uuid"), str) and doc["uuid"]
    return doc


def get_check(client: TestClient, s: Session, uuid: str):
    r = client.get(f"/checks/{uuid}", headers=api(s))
    assert r.status_code == 200, r.text
    return r.json()


def extract_items(response):
    assert response.status_code == 200, response.text
    doc = response.json()
    if isinstance(doc, list):
        return doc
    for key in ("items", "checks", "pings", "projects", "periods"):
        if isinstance(doc.get(key), list):
            return doc[key]
    raise AssertionError(f"response does not contain a list: {doc!r}")


def assert_items(response):
    assert response.status_code == 200, response.text
    doc = response.json()
    assert set(doc) == {"items"}, doc
    assert isinstance(doc["items"], list)
    return doc["items"]


def ping_items(client: TestClient, s: Session, uuid: str, **params):
    r = client.get(f"/checks/{uuid}/pings", headers=api(s), params=params)
    return extract_items(r)


def rotate_project_key(client: TestClient, s: Session, project_id: str, kind: str) -> str:
    r = client.post(f"/projects/{project_id}/keys/{kind}/rotate", headers=bearer(s))
    assert r.status_code == 200, r.text
    doc = r.json()
    key = doc.get("key") or doc.get("api_key") or doc.get(f"{kind}_key")
    assert isinstance(key, str) and key
    return key


def absolute_path(url_or_path: str) -> str:
    parsed = urlparse(url_or_path)
    if parsed.scheme:
        value = parsed.path
        if parsed.query:
            value += "?" + parsed.query
        return value
    return url_or_path


def assert_db_does_not_contain(db_path: Path, *plaintext: str):
    files = [db_path] + [p for p in db_path.parent.glob(db_path.name + "*") if p != db_path]
    raw = b"".join(p.read_bytes() for p in files if p.is_file())
    for value in plaintext:
        assert value.encode() not in raw, f"plaintext secret leaked into SQLite: {value!r}"
