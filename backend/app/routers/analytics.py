from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Url, User
from app.schemas import AnalyticsOut, AnalyticsSummary, TimelineOut, UrlOut
from app.services import analytics_service, url_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# Registered before "/{url_id}" so "top-urls" is not parsed as an ID.
@router.get("/top-urls", response_model=list[UrlOut])
def top_urls(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Url]:
    return analytics_service.get_top_urls(db, current_user.id, limit)


@router.get("/{url_id}", response_model=AnalyticsOut)
def full_analytics(
    url_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsOut:
    url = url_service.get_user_url(db, current_user, url_id)
    return analytics_service.get_full_analytics(db, url, days)


@router.get("/{url_id}/summary", response_model=AnalyticsSummary)
def summary(
    url_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> AnalyticsSummary:
    url = url_service.get_user_url(db, current_user, url_id)
    return analytics_service.get_summary(db, url)


@router.get("/{url_id}/timeline", response_model=TimelineOut)
def timeline(
    url_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimelineOut:
    url = url_service.get_user_url(db, current_user, url_id)
    return TimelineOut(url_id=url.id, days=days, points=analytics_service.get_timeline(db, url, days))
