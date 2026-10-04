from datetime import datetime, timedelta, timezone

import pytest

from app.models import Click, Url
from app.services import url_service
from tests.conftest import create_url

ORIGINAL = "https://example.com/some/very/long/path?x=1"


def test_create_url_generates_short_code(client, auth_headers):
    data = create_url(client, auth_headers)
    assert len(data["short_code"]) == url_service.CODE_LENGTH
    assert data["short_code"].isalnum()
    assert data["short_url"] == f"http://localhost:8000/{data['short_code']}"
    assert data["original_url"] == ORIGINAL
    assert data["click_count"] == 0
    assert data["is_active"] is True


def test_create_url_with_custom_alias(client, auth_headers):
    data = create_url(client, auth_headers, custom_alias="my-portfolio_1")
    assert data["short_code"] == "my-portfolio_1"
    assert data["short_url"].endswith("/my-portfolio_1")


def test_blank_alias_falls_back_to_generated_code(client, auth_headers):
    data = create_url(client, auth_headers, custom_alias="   ")
    assert len(data["short_code"]) == url_service.CODE_LENGTH


def test_duplicate_alias_is_rejected(client, auth_headers, other_headers):
    create_url(client, auth_headers, custom_alias="taken")
    response = client.post("/api/urls", json={"original_url": ORIGINAL, "custom_alias": "taken"}, headers=other_headers)
    assert response.status_code == 409
    assert "already taken" in response.json()["detail"]


@pytest.mark.parametrize("alias", ["ab", "has space", "bad!chars", "x" * 33, "docs", "API", "über-alias"])
def test_invalid_alias_is_rejected(client, auth_headers, alias):
    response = client.post("/api/urls", json={"original_url": ORIGINAL, "custom_alias": alias}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "bad_url", ["", "not a url", "example.com", "javascript:alert(1)", "ftp://example.com/file", "https://", "http:///path"]
)
def test_invalid_url_is_rejected(client, auth_headers, bad_url):
    response = client.post("/api/urls", json={"original_url": bad_url}, headers=auth_headers)
    assert response.status_code == 422
    assert "original_url" in response.json()["detail"]


def test_missing_url_is_rejected(client, auth_headers):
    assert client.post("/api/urls", json={}, headers=auth_headers).status_code == 422


def test_past_expiry_is_rejected(client, auth_headers):
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = client.post("/api/urls", json={"original_url": ORIGINAL, "expires_at": past}, headers=auth_headers)
    assert response.status_code == 422


def test_create_url_requires_authentication(client):
    assert client.post("/api/urls", json={"original_url": ORIGINAL}).status_code == 401


def test_short_codes_are_unique(client, auth_headers):
    codes = {create_url(client, auth_headers)["short_code"] for _ in range(40)}
    assert len(codes) == 40


def test_collision_with_existing_code_triggers_a_new_one(client, auth_headers, monkeypatch):
    existing = create_url(client, auth_headers, custom_alias="collide")["short_code"]
    candidates = iter([existing, existing, "freshcode"])
    monkeypatch.setattr(url_service, "generate_short_code", lambda: next(candidates))

    data = create_url(client, auth_headers)
    assert data["short_code"] == "freshcode"


def test_list_urls_only_returns_own_urls_newest_first(client, auth_headers, other_headers):
    first = create_url(client, auth_headers)
    second = create_url(client, auth_headers)
    create_url(client, other_headers)

    response = client.get("/api/urls", headers=auth_headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second["id"], first["id"]]


def test_list_urls_requires_authentication(client):
    assert client.get("/api/urls").status_code == 401


def test_get_single_url(client, auth_headers):
    created = create_url(client, auth_headers)
    response = client.get(f"/api/urls/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["short_code"] == created["short_code"]


def test_cannot_access_another_users_url(client, auth_headers, other_headers):
    created = create_url(client, auth_headers)
    assert client.get(f"/api/urls/{created['id']}", headers=other_headers).status_code == 404
    assert client.delete(f"/api/urls/{created['id']}", headers=other_headers).status_code == 404
    # ...and the owner still has it
    assert client.get(f"/api/urls/{created['id']}", headers=auth_headers).status_code == 200


def test_get_nonexistent_url(client, auth_headers):
    assert client.get("/api/urls/99999", headers=auth_headers).status_code == 404


def test_delete_url_removes_it_and_its_clicks(client, auth_headers, db):
    created = create_url(client, auth_headers)
    client.get(f"/{created['short_code']}", follow_redirects=False)
    assert db.query(Click).count() == 1

    assert client.delete(f"/api/urls/{created['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/urls/{created['id']}", headers=auth_headers).status_code == 404
    db.expire_all()
    assert db.query(Url).count() == 0
    assert db.query(Click).count() == 0


# ---------- Redirect ----------
def test_redirect_to_original_url(client, auth_headers):
    created = create_url(client, auth_headers)
    response = client.get(f"/{created['short_code']}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == ORIGINAL


def test_redirect_works_for_custom_alias_without_login(client, auth_headers):
    create_url(client, auth_headers, custom_alias="portfolio")
    response = client.get("/portfolio", follow_redirects=False)
    assert response.status_code == 307


def test_redirect_unknown_code(client):
    response = client.get("/doesnotexist", follow_redirects=False)
    assert response.status_code == 404


def test_redirect_deleted_url(client, auth_headers):
    created = create_url(client, auth_headers)
    client.delete(f"/api/urls/{created['id']}", headers=auth_headers)
    assert client.get(f"/{created['short_code']}", follow_redirects=False).status_code == 404


def test_redirect_expired_url(client, auth_headers, db):
    created = create_url(client, auth_headers)
    url = db.get(Url, created["id"])
    url.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    response = client.get(f"/{created['short_code']}", follow_redirects=False)
    assert response.status_code == 410
    assert "expired" in response.json()["detail"]
    assert db.query(Click).count() == 0  # expired visits are not counted


def test_redirect_not_yet_expired_url(client, auth_headers):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    created = create_url(client, auth_headers, expires_at=future)
    assert client.get(f"/{created['short_code']}", follow_redirects=False).status_code == 307


def test_redirect_inactive_url(client, auth_headers, db):
    created = create_url(client, auth_headers)
    db.get(Url, created["id"]).is_active = False
    db.commit()
    assert client.get(f"/{created['short_code']}", follow_redirects=False).status_code == 410


def test_api_routes_are_not_shadowed_by_redirect_route(client):
    assert client.get("/api/health").json() == {"status": "ok", "database": "connected"}
    assert client.get("/docs").status_code == 200
