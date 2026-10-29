import os
import sys
import tempfile
from pathlib import Path

# Configure the app BEFORE importing it: temp database, fixed secrets.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["JWT_SECRET"] = "test-secret-must-be-at-least-32-chars-long-for-hmac-sha256!"
os.environ["ADMIN_EMAIL"] = "admin@test.edu"
os.environ["ADMIN_PASSWORD"] = "AdminPass123"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as c:  # runs startup: creates tables + seeds admin
        yield c


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    main.FAILED_LOGINS.clear()
    yield
    main.FAILED_LOGINS.clear()


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return login(client, "admin@test.edu", "AdminPass123")


@pytest.fixture(scope="session")
def student_headers(client):
    r = client.post("/api/auth/register", json={
        "email": "student@test.edu", "full_name": "Test Student", "password": "Student123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ISSUE = {
    "title": "Broken fan in Room 204",
    "description": "The ceiling fan makes a loud noise and stops.",
    "category": "Electrical",
    "location": "Building A, Room 204",
    "reporter_name": "Aditya",
    "priority": "High",
}


@pytest.fixture()
def new_issue(client):
    r = client.post("/api/issues", json=ISSUE)
    assert r.status_code == 201, r.text
    return r.json()
