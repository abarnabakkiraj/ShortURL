from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Url, User
from app.schemas import UrlCreate, UrlOut
from app.services import analytics_service, url_service

router = APIRouter(prefix="/api/urls", tags=["URLs"])
redirect_router = APIRouter(tags=["Redirect"])


@router.post("", response_model=UrlOut, status_code=status.HTTP_201_CREATED)
def create_short_url(
    data: UrlCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Url:
    return url_service.create_url(db, current_user, data)


@router.get("", response_model=list[UrlOut])
def list_my_urls(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Url]:
    return url_service.list_urls(db, current_user, limit, offset)


@router.get("/{url_id}", response_model=UrlOut)
def get_url(url_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Url:
    return url_service.get_user_url(db, current_user, url_id)


@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url(url_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    url_service.delete_url(db, current_user, url_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@redirect_router.get(
    "/{short_code}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_class=RedirectResponse,
    summary="Redirect to the original URL",
)
def redirect_to_original(short_code: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    url = url_service.resolve_redirect_target(db, short_code)
    # Read these first: committing the click expires the ORM object.
    url_id, target = url.id, url.original_url
    analytics_service.record_click(db, url_id, request)
    # 307 (temporary) is not cached by browsers, so every visit reaches us and gets counted.
    return RedirectResponse(target, status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Cache-Control": "no-store"})
