from typing import Protocol

from fastapi import Request

from app.config import get_settings


class GeoLocator(Protocol):
    """Anything that can work out a visitor's country. Swap in a GeoIP database or API later."""

    def country_for(self, request: Request) -> str | None: ...


class HeaderGeoLocator:
    """Reads the country from a CDN/proxy header (e.g. Cloudflare's CF-IPCountry).

    It makes no network calls, so it can never slow down or break a redirect. The headers are
    only trusted when TRUST_PROXY_HEADERS=true, because clients can forge them otherwise.
    """

    HEADERS = ("cf-ipcountry", "x-country-code")
    UNKNOWN_VALUES = {"", "XX", "T1"}

    def country_for(self, request: Request) -> str | None:
        if not get_settings().trust_proxy_headers:
            return None
        for header in self.HEADERS:
            value = request.headers.get(header, "").strip().upper()
            if value not in self.UNKNOWN_VALUES:
                return value
        return None


geo_locator: GeoLocator = HeaderGeoLocator()
