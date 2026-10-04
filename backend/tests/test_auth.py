from datetime import timedelta

from app.auth import create_access_token
from app.models import User
from tests.conftest import PASSWORD


def register(client, **overrides):
    payload = {"name": "Alice", "email": "alice@example.com", "password": PASSWORD} | overrides
    return client.post("/api/auth/register", json=payload)


def test_register_success(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"
    assert "password" not in body and "hashed_password" not in body


def test_password_is_stored_hashed(client, db):
    register(client)
    user = db.query(User).one()
    assert user.hashed_password != PASSWORD
    assert user.hashed_password.startswith("$2")  # bcrypt


def test_register_duplicate_email_is_rejected_case_insensitively(client):
    assert register(client).status_code == 201
    response = register(client, email="ALICE@example.com")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_invalid_email(client):
    response = register(client, email="not-an-email")
    assert response.status_code == 422
    assert "email" in response.json()["detail"]


def test_register_short_password(client):
    assert register(client, password="short").status_code == 422


def test_register_missing_fields(client):
    assert client.post("/api/auth/register", json={}).status_code == 422


def test_login_success_returns_jwt(client):
    register(client)
    response = client.post("/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"


def test_login_wrong_password(client):
    register(client)
    response = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "WrongPass123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_user(client):
    response = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_me_without_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"


def test_me_with_expired_token(client):
    register(client)
    expired = create_access_token(1, timedelta(seconds=-5))
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_token_for_deleted_user_is_rejected(client):
    token = create_access_token(9999)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
