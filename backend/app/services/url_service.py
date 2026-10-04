import secrets
import string
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Url, User
from app.schemas import UrlCreate

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 10


def generate_short_code(length: int = CODE_LENGTH) -> str:
    """Random URL-safe code from a cryptographically secure generator (62^7 combinations)."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def short_code_exists(db: Session, short_code: str) -> bool:
    return db.scalar(select(Url.id).where(Url.short_code == short_code)) is not None


def _insert_url(db: Session, user: User, data: UrlCreate, short_code: str) -> Url:
    url = Url(
        user_id=user.id,
        original_url=data.original_url,
        short_code=short_code,
        expires_at=data.expires_at,
    )
    db.add(url)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(url)
    return url


def create_url(db: Session, user: User, data: UrlCreate) -> Url:
    if data.custom_alias:
        if short_code_exists(db, data.custom_alias):
            raise HTTPException(status.HTTP_409_CONFLICT, "This alias is already taken")
        try:
            return _insert_url(db, user, data, data.custom_alias)
        except IntegrityError:  # someone claimed it between our check and the insert
            raise HTTPException(status.HTTP_409_CONFLICT, "This alias is already taken")

    for _ in range(MAX_GENERATION_ATTEMPTS):
        short_code = generate_short_code()
        if short_code_exists(db, short_code):
            continue
        try:
            return _insert_url(db, user, data, short_code)
        except IntegrityError:  # lost a race for the same code: try a new one
            continue
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Could not generate a unique short code. Please try again."
    )


def list_urls(db: Session, user: User, limit: int, offset: int) -> list[Url]:
    stmt = (
        select(Url)
        .where(Url.user_id == user.id)
        .order_by(Url.created_at.desc(), Url.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def get_user_url(db: Session, user: User, url_id: int) -> Url:
    """Fetch a URL owned by `user`. Other users' URLs look like they don't exist (404)."""
    url = db.scalar(select(Url).where(Url.id == url_id, Url.user_id == user.id))
    if url is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "URL not found")
    return url


def delete_url(db: Session, user: User, url_id: int) -> None:
    url = get_user_url(db, user, url_id)
    db.delete(url)
    db.commit()


def is_expired(url: Url) -> bool:
    if url.expires_at is None:
        return False
    expires_at = url.expires_at
    if expires_at.tzinfo is None:  # SQLite returns naive datetimes; we always store UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def resolve_redirect_target(db: Session, short_code: str) -> Url:
    """Find a short link and make sure it can currently be followed."""
    url = db.scalar(select(Url).where(Url.short_code == short_code))
    if url is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Short link not found")
    if not url.is_active:
        raise HTTPException(status.HTTP_410_GONE, "This short link has been disabled")
    if is_expired(url):
        raise HTTPException(status.HTTP_410_GONE, "This short link has expired")
    return url
