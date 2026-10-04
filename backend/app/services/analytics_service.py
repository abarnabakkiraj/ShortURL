import logging
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlparse

from fastapi import Request
from sqlalchemy import func, literal_column, select, update
from sqlalchemy.orm import Session
from user_agents import parse as parse_user_agent

from app.config import get_settings
from app.models import Click, Url
from app.schemas import AnalyticsOut, AnalyticsSummary, BreakdownItem, TimelinePoint, UrlOut
from app.services.geo import geo_locator

logger = logging.getLogger(__name__)

UNKNOWN = "Unknown"
DIRECT = "Direct"
BREAKDOWN_LIMIT = 10


# ---------- Recording clicks ----------
def get_client_ip(request: Request) -> str | None:
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:45] or None
    return request.client.host if request.client else None


def _build_click(url_id: int, request: Request) -> Click:
    user_agent = request.headers.get("user-agent", "")
    parsed = parse_user_agent(user_agent)
    if parsed.is_bot:
        device_type = "Bot"
    elif parsed.is_mobile:
        device_type = "Mobile"
    elif parsed.is_tablet:
        device_type = "Tablet"
    elif parsed.is_pc:
        device_type = "Desktop"
    else:
        device_type = "Other"

    return Click(
        url_id=url_id,
        ip_address=get_client_ip(request),
        user_agent=user_agent[:512] or None,
        referrer=request.headers.get("referer", "")[:2048] or None,
        country=geo_locator.country_for(request),
        device_type=device_type,
        browser=(parsed.browser.family or "Other")[:64],
        operating_system=(parsed.os.family or "Other")[:64],
    )


def record_click(db: Session, url_id: int, request: Request) -> None:
    """Store one click and bump the URL's counter.

    A failure here is logged but never raised: a visitor must still be redirected
    even if analytics storage has a problem.
    """
    try:
        db.add(_build_click(url_id, request))
        db.execute(update(Url).where(Url.id == url_id).values(click_count=Url.click_count + 1))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not record click for url_id=%s", url_id)


# ---------- Reading analytics ----------
def _count_clicks(db: Session, url_id: int, since: datetime | None = None) -> int:
    stmt = select(func.count(Click.id)).where(Click.url_id == url_id)
    if since is not None:
        stmt = stmt.where(Click.clicked_at >= since)
    return db.scalar(stmt) or 0


def get_summary(db: Session, url: Url) -> AnalyticsSummary:
    now = datetime.now(timezone.utc)
    start_of_today = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    return AnalyticsSummary(
        url_id=url.id,
        total_clicks=_count_clicks(db, url.id),
        clicks_today=_count_clicks(db, url.id, start_of_today),
        clicks_this_week=_count_clicks(db, url.id, now - timedelta(days=7)),
        clicks_this_month=_count_clicks(db, url.id, now - timedelta(days=30)),
    )


def get_timeline(db: Session, url: Url, days: int) -> list[TimelinePoint]:
    """Clicks per UTC day for the last `days` days; days without clicks are returned as 0."""
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=days - 1)
    start = datetime.combine(first_day, time.min, tzinfo=timezone.utc)

    day = func.date(Click.clicked_at)
    rows = db.execute(
        select(day, func.count(Click.id))
        .where(Click.url_id == url.id, Click.clicked_at >= start)
        .group_by(day)
    ).all()
    # PostgreSQL returns date objects, SQLite returns strings: normalise both.
    counts = {row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0])): row[1] for row in rows}
    return [
        TimelinePoint(date=first_day + timedelta(days=offset), clicks=counts.get(first_day + timedelta(days=offset), 0))
        for offset in range(days)
    ]


def _breakdown(db: Session, url_id: int, column) -> list[BreakdownItem]:
    label = func.coalesce(column, literal_column(f"'{UNKNOWN}'"))
    total = func.count(Click.id)
    rows = db.execute(
        select(label, total)
        .where(Click.url_id == url_id)
        .group_by(label)
        .order_by(total.desc(), label)
        .limit(BREAKDOWN_LIMIT)
    ).all()
    return [BreakdownItem(name=name, count=count) for name, count in rows]


def _referrer_breakdown(db: Session, url_id: int) -> list[BreakdownItem]:
    """Group referrers by website (so /page-1 and /page-2 on one site count together)."""
    rows = db.execute(
        select(Click.referrer, func.count(Click.id)).where(Click.url_id == url_id).group_by(Click.referrer)
    ).all()
    counter: Counter[str] = Counter()
    for referrer, count in rows:
        host = (urlparse(referrer).netloc or referrer) if referrer else DIRECT
        counter[host] += count
    return [BreakdownItem(name=name, count=count) for name, count in counter.most_common(BREAKDOWN_LIMIT)]


def get_full_analytics(db: Session, url: Url, days: int) -> AnalyticsOut:
    return AnalyticsOut(
        url=UrlOut.model_validate(url),
        summary=get_summary(db, url),
        timeline=get_timeline(db, url, days),
        devices=_breakdown(db, url.id, Click.device_type),
        browsers=_breakdown(db, url.id, Click.browser),
        operating_systems=_breakdown(db, url.id, Click.operating_system),
        referrers=_referrer_breakdown(db, url.id),
        countries=_breakdown(db, url.id, Click.country),
    )


def get_top_urls(db: Session, user_id: int, limit: int) -> list[Url]:
    stmt = (
        select(Url)
        .where(Url.user_id == user_id, Url.click_count > 0)
        .order_by(Url.click_count.desc(), Url.id)
        .limit(limit)
    )
    return list(db.scalars(stmt))
