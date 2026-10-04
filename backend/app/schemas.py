import re
from datetime import date, datetime, timezone
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, computed_field, field_validator

from app.config import get_settings

ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
# Paths the API already uses; an alias with one of these names could never be reached.
RESERVED_ALIASES = {
    "api", "docs", "redoc", "openapi", "openapi.json", "health", "favicon.ico",
    "login", "register", "dashboard", "analytics", "admin", "static",
}
MAX_URL_LENGTH = 2048


# ---------- Auth ----------
class UserCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes long")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- URLs ----------
class UrlCreate(BaseModel):
    original_url: str
    custom_alias: str | None = None
    expires_at: datetime | None = None

    @field_validator("original_url")
    @classmethod
    def validate_original_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter the URL you want to shorten")
        if len(value) > MAX_URL_LENGTH:
            raise ValueError(f"URL must be at most {MAX_URL_LENGTH} characters long")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must start with http:// or https://")
        if not parsed.hostname:
            raise ValueError("Enter a valid URL, for example https://example.com/page")
        return value

    @field_validator("custom_alias")
    @classmethod
    def validate_custom_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not ALIAS_PATTERN.fullmatch(value):
            raise ValueError("Alias must be 3-32 characters: letters, numbers, hyphens or underscores")
        if value.lower() in RESERVED_ALIASES:
            raise ValueError("This alias is reserved. Please choose another one")
        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        if value <= datetime.now(timezone.utc):
            raise ValueError("Expiry date must be in the future")
        return value


class UrlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: datetime | None
    is_active: bool
    click_count: int

    @computed_field
    @property
    def short_url(self) -> str:
        return f"{get_settings().base_url}/{self.short_code}"


# ---------- Analytics ----------
class AnalyticsSummary(BaseModel):
    url_id: int
    total_clicks: int
    clicks_today: int
    clicks_this_week: int
    clicks_this_month: int


class TimelinePoint(BaseModel):
    date: date
    clicks: int


class TimelineOut(BaseModel):
    url_id: int
    days: int
    points: list[TimelinePoint]


class BreakdownItem(BaseModel):
    name: str
    count: int


class AnalyticsOut(BaseModel):
    url: UrlOut
    summary: AnalyticsSummary
    timeline: list[TimelinePoint]
    devices: list[BreakdownItem]
    browsers: list[BreakdownItem]
    operating_systems: list[BreakdownItem]
    referrers: list[BreakdownItem]
    countries: list[BreakdownItem]
