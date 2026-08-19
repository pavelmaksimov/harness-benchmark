from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from fastapi.testclient import TestClient

DB_ENV = "HEALTHCHECKS_DB_PATH"
CLOCK_ENV = "HEALTHCHECKS_NOW"

@dataclass
class Session:
    email: str
    token: str
    api_key: str
    project_id: str | None = None

def error_code(response):
    doc = response.json()
    assert "detail" not in doc
    assert set(doc) == {"error"}
    assert isinstance(doc["error"].get("code"), str)
    assert isinstance(doc["error"].get("message"), str)
    return doc["error"]["code"]

def register(client: TestClient, email="alice@example.org", password="secret-value") -> Session:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    doc = r.json()
    lr = client.post("/auth/login", json={"email": email, "password": password})
    assert lr.status_code == 200, lr.text
    token = lr.json()["access_token"]
    api_key = doc.get("api_key") or doc.get("project", {}).get("api_key")
    assert api_key
    project = doc.get("project")
    pid = doc.get("project_id") or (project.get("id") if isinstance(project, dict) else None)
    return Session(email, token, api_key, pid)

def api(s: Session): return {"X-Api-Key": s.api_key}
def bearer(s: Session): return {"Authorization": f"Bearer {s.token}"}

def make_check(client: TestClient, s: Session, **overrides):
    body = {"name":"backup","timeout":3600,"grace":60}
    body.update(overrides)
    r = client.post("/checks", headers=api(s), json=body)
    assert r.status_code == 201, r.text
    return r.json()

def workspace_pythonpath_env():
    env = os.environ.copy()
    cwd = Path.cwd().resolve()
    if (cwd / "healthchecks_app").is_dir():
        parts = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
        cwd_str = str(cwd)
        if cwd_str not in parts:
            env["PYTHONPATH"] = os.pathsep.join([cwd_str, *parts])
    return env
