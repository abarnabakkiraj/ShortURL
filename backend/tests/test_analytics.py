from datetime import datetime, timedelta, timezone

from app.models import Click, Url
from app.services import analytics_service
from tests.conftest import create_url

IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
CHROME_WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def visit(client, short_code, **headers):
    return client.get(f"/{short_code}", headers=headers, follow_redirects=False)


def test_click_is_recorded_with_visitor_details(client, auth_headers, db):
    created = create_url(client, auth_headers)
    visit(client, created["short_code"], **{"User-Agent": IPHONE_UA, "Referer": "https://twitter.com/some/post"})

    click = db.query(Click).one()
    assert click.url_id == created["id"]
    assert click.device_type == "Mobile"
    assert click.browser == "Mobile Safari"
    assert click.operating_system == "iOS"
    assert click.referrer == "https://twitter.com/some/post"
    assert click.user_agent == IPHONE_UA
    assert click.ip_address
    assert click.clicked_at is not None
    assert db.get(Url, created["id"]).click_count == 1


def test_every_click_is_counted(client, auth_headers):
    created = create_url(client, auth_headers)
    for _ in range(3):
        visit(client, created["short_code"])
    assert client.get(f"/api/urls/{created['id']}", headers=auth_headers).json()["click_count"] == 3


def test_redirect_still_works_if_click_recording_fails(client, auth_headers, db, monkeypatch):
    created = create_url(client, auth_headers)

    def explode(*_args, **_kwargs):
        raise RuntimeError("analytics storage is down")

    monkeypatch.setattr(analytics_service, "_build_click", explode)
    response = visit(client, created["short_code"])
    assert response.status_code == 307
    assert db.query(Click).count() == 0


def test_forged_proxy_headers_are_ignored_by_default(client, auth_headers, db):
    created = create_url(client, auth_headers)
    visit(client, created["short_code"], **{"X-Forwarded-For": "1.2.3.4", "CF-IPCountry": "FR"})
    click = db.query(Click).one()
    assert click.ip_address != "1.2.3.4"
    assert click.country is None


def test_summary_counts_by_period(client, auth_headers, db):
    created = create_url(client, auth_headers)
    visit(client, created["short_code"])  # today
    now = datetime.now(timezone.utc)
    for days_ago in (3, 20, 40):
        db.add(Click(url_id=created["id"], clicked_at=now - timedelta(days=days_ago)))
    db.commit()

    response = client.get(f"/api/analytics/{created['id']}/summary", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "url_id": created["id"],
        "total_clicks": 4,
        "clicks_today": 1,
        "clicks_this_week": 2,
        "clicks_this_month": 3,
    }


def test_timeline_fills_missing_days_with_zero(client, auth_headers, db):
    created = create_url(client, auth_headers)
    visit(client, created["short_code"])
    db.add(Click(url_id=created["id"], clicked_at=datetime.now(timezone.utc) - timedelta(days=2)))
    db.commit()

    response = client.get(f"/api/analytics/{created['id']}/timeline?days=7", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    points = body["points"]
    assert len(points) == 7
    assert [point["clicks"] for point in points] == [0, 0, 0, 0, 1, 0, 1]
    assert points[-1]["date"] == datetime.now(timezone.utc).date().isoformat()


def test_timeline_validates_days(client, auth_headers):
    created = create_url(client, auth_headers)
    assert client.get(f"/api/analytics/{created['id']}/timeline?days=0", headers=auth_headers).status_code == 422
    assert client.get(f"/api/analytics/{created['id']}/timeline?days=9999", headers=auth_headers).status_code == 422


def test_full_analytics_breakdowns(client, auth_headers):
    created = create_url(client, auth_headers)
    visit(client, created["short_code"], **{"User-Agent": IPHONE_UA, "Referer": "https://twitter.com/a"})
    visit(client, created["short_code"], **{"User-Agent": IPHONE_UA, "Referer": "https://twitter.com/b"})
    visit(client, created["short_code"], **{"User-Agent": CHROME_WINDOWS_UA})

    response = client.get(f"/api/analytics/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["url"]["id"] == created["id"]
    assert body["summary"]["total_clicks"] == 3
    assert body["devices"] == [{"name": "Mobile", "count": 2}, {"name": "Desktop", "count": 1}]
    assert body["browsers"] == [{"name": "Mobile Safari", "count": 2}, {"name": "Chrome", "count": 1}]
    assert body["operating_systems"] == [{"name": "iOS", "count": 2}, {"name": "Windows", "count": 1}]
    assert body["referrers"] == [{"name": "twitter.com", "count": 2}, {"name": "Direct", "count": 1}]
    assert len(body["timeline"]) == 30
    assert body["timeline"][-1]["clicks"] == 3


def test_analytics_for_url_without_clicks(client, auth_headers):
    created = create_url(client, auth_headers)
    body = client.get(f"/api/analytics/{created['id']}", headers=auth_headers).json()
    assert body["summary"]["total_clicks"] == 0
    assert body["devices"] == [] and body["referrers"] == []
    assert all(point["clicks"] == 0 for point in body["timeline"])


def test_analytics_requires_authentication(client, auth_headers):
    created = create_url(client, auth_headers)
    for path in ("", "/summary", "/timeline"):
        assert client.get(f"/api/analytics/{created['id']}{path}").status_code == 401
    assert client.get("/api/analytics/top-urls").status_code == 401


def test_cannot_read_another_users_analytics(client, auth_headers, other_headers):
    created = create_url(client, auth_headers)
    visit(client, created["short_code"])
    for path in ("", "/summary", "/timeline"):
        response = client.get(f"/api/analytics/{created['id']}{path}", headers=other_headers)
        assert response.status_code == 404


def test_analytics_for_nonexistent_url(client, auth_headers):
    assert client.get("/api/analytics/424242", headers=auth_headers).status_code == 404


def test_top_urls_are_sorted_by_clicks_and_scoped_to_user(client, auth_headers, other_headers):
    quiet = create_url(client, auth_headers, custom_alias="quiet")
    popular = create_url(client, auth_headers, custom_alias="popular")
    unused = create_url(client, auth_headers, custom_alias="unused")
    foreign = create_url(client, other_headers, custom_alias="foreign")
    visit(client, quiet["short_code"])
    for _ in range(3):
        visit(client, popular["short_code"])
    for _ in range(5):
        visit(client, foreign["short_code"])

    response = client.get("/api/analytics/top-urls", headers=auth_headers)
    assert response.status_code == 200
    assert [item["short_code"] for item in response.json()] == ["popular", "quiet"]
    assert unused["short_code"] not in [item["short_code"] for item in response.json()]
