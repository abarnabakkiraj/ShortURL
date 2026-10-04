"""Shared test setup.

The environment variables are forced BEFORE the app is imported, so the tests always run
against an in-memory SQLite database and can never touch the real PostgreSQL database.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters-long"
os.environ["BASE_URL"] = "http://localhost:8000"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["TRUST_PROXY_HEADERS"] = "false"
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

assert engine.dialect.name == "sqlite", "Tests must never run against a real database"

PASSWORD = "StrongPass123"


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_user(client: TestClient, email: str = "alice@example.com", name: str = "Alice") -> dict[str, str]:
    """Register + log in a user and return ready-to-use auth headers."""
    response = client.post("/api/auth/register", json={"name": name, "email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return make_user(client)


@pytest.fixture
def other_headers(client):
    return make_user(client, email="bob@example.com", name="Bob")


def create_url(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {"original_url": "https://example.com/some/very/long/path?x=1"} | overrides
    response = client.post("/api/urls", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
