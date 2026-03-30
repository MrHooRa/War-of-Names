"""Request-level middleware and dependencies — IP ban enforcement & rate limiting."""

import re
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from sqlalchemy import select

from app.core.database import async_session
from app.core.utils import now_riyadh_naive
from app.modules.owner.models import IPBan

# ── In-memory rate limiter for auth endpoints ─────────────────────────────
_rate_limits: dict[str, list[float]] = defaultdict(list)  # IP -> [timestamps]
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # max requests per window for auth endpoints


def get_client_ip(request: Request) -> str | None:
    """Resolve the best-effort client IP from proxy headers or socket info."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        client_ip = real_ip.strip()
        if client_ip:
            return client_ip

    return request.client.host if request.client else None


def _parse_browser(user_agent: str) -> tuple[str | None, str | None]:
    patterns = [
        ("Edge", r"Edg/([0-9.]+)"),
        ("Opera", r"OPR/([0-9.]+)"),
        ("Samsung Internet", r"SamsungBrowser/([0-9.]+)"),
        ("Chrome", r"Chrome/([0-9.]+)"),
        ("Firefox", r"Firefox/([0-9.]+)"),
        ("Safari", r"Version/([0-9.]+).*Safari/"),
    ]
    for browser_name, pattern in patterns:
        match = re.search(pattern, user_agent)
        if match:
            return browser_name, match.group(1)
    return None, None


def _parse_os(user_agent: str) -> tuple[str | None, str | None]:
    windows_match = re.search(r"Windows NT ([0-9.]+)", user_agent)
    if windows_match:
        version_map = {
            "10.0": "10/11",
            "6.3": "8.1",
            "6.2": "8",
            "6.1": "7",
        }
        version = windows_match.group(1)
        return "Windows", version_map.get(version, version)

    android_match = re.search(r"Android ([0-9.]+)", user_agent)
    if android_match:
        return "Android", android_match.group(1)

    ios_match = re.search(r"(?:iPhone|CPU (?:iPhone )?OS|iPad; CPU OS) ([0-9_]+)", user_agent)
    if ios_match:
        return "iOS", ios_match.group(1).replace("_", ".")

    mac_match = re.search(r"Mac OS X ([0-9_]+)", user_agent)
    if mac_match:
        return "macOS", mac_match.group(1).replace("_", ".")

    if "Linux" in user_agent:
        return "Linux", None

    return None, None


def _detect_device_type(user_agent: str) -> str:
    lowered = user_agent.lower()
    if any(token in lowered for token in ("bot", "crawler", "spider")):
        return "bot"
    if "ipad" in lowered or "tablet" in lowered:
        return "tablet"
    if any(token in lowered for token in ("mobile", "iphone", "android")):
        return "mobile"
    return "desktop"


def get_client_metadata(request: Request) -> dict:
    """Return best-effort client metadata for audit/security events."""
    user_agent = request.headers.get("user-agent", "").strip()
    browser_name, browser_version = _parse_browser(user_agent)
    os_name, os_version = _parse_os(user_agent)

    return {
        "ip_address": get_client_ip(request),
        "user_agent": user_agent or None,
        "browser_name": browser_name,
        "browser_version": browser_version,
        "os_name": os_name,
        "os_version": os_version,
        "device_type": _detect_device_type(user_agent),
    }


async def rate_limit_auth(request: Request) -> None:
    """Rate limit authentication endpoints (login, register).

    Uses a simple sliding-window counter keyed by client IP.
    Raises HTTP 429 if the limit is exceeded.
    """
    ip = get_client_ip(request) or "unknown"
    now = time.monotonic()
    # Clean old entries outside the window
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="عدد محاولات كبير — حاول لاحقاً",
        )
    _rate_limits[ip].append(now)

# ── In-memory cache for banned IPs ──────────────────────────────────────────
_banned_ips: set[str] = set()
_cache_expires_at: float = 0.0
_CACHE_TTL_SECONDS = 60


async def _refresh_ban_cache() -> None:
    """Reload active IP bans from the database."""
    global _banned_ips, _cache_expires_at
    now = now_riyadh_naive()
    async with async_session() as session:
        result = await session.execute(
            select(IPBan.ip_address).where(
                (IPBan.expires_at == None) | (IPBan.expires_at > now)  # noqa: E711
            )
        )
        _banned_ips = {row[0] for row in result.fetchall()}
    _cache_expires_at = time.monotonic() + _CACHE_TTL_SECONDS


def invalidate_ip_ban_cache() -> None:
    """Force the next check to reload from DB (call after ban create/delete)."""
    global _cache_expires_at
    _cache_expires_at = 0.0


async def check_ip_ban(request: Request) -> None:
    """FastAPI dependency that checks if the client IP is banned.

    Caches the ban list for 60 seconds to avoid DB hits on every request.
    Raises HTTP 403 if the IP is currently banned.
    """
    if time.monotonic() >= _cache_expires_at:
        await _refresh_ban_cache()

    client_ip = get_client_ip(request)
    if client_ip and client_ip in _banned_ips:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="تم حظر عنوان IP الخاص بك",
        )


# ── In-memory cache for maintenance mode ──────────────────────────────────
_maintenance_enabled: bool = False
_maintenance_message: str = "المنصة قيد الصيانة — نعود قريباً"
_maintenance_cache_expires_at: float = 0.0
_MAINTENANCE_CACHE_TTL = 30  # seconds


async def _refresh_maintenance_cache() -> None:
    """Reload maintenance mode settings from the database."""
    global _maintenance_enabled, _maintenance_message, _maintenance_cache_expires_at
    from app.modules.settings.service import get_setting

    async with async_session() as session:
        mode = await get_setting(session, "maintenance_mode")
        msg = await get_setting(session, "maintenance_message")
    _maintenance_enabled = bool(mode) if mode is not None else False
    if msg:
        _maintenance_message = msg
    _maintenance_cache_expires_at = time.monotonic() + _MAINTENANCE_CACHE_TTL


async def is_maintenance_mode() -> bool:
    """Return True if maintenance mode is currently enabled (cached)."""
    if time.monotonic() >= _maintenance_cache_expires_at:
        await _refresh_maintenance_cache()
    return _maintenance_enabled


async def get_maintenance_message() -> str:
    """Return the current maintenance message (cached)."""
    if time.monotonic() >= _maintenance_cache_expires_at:
        await _refresh_maintenance_cache()
    return _maintenance_message


def invalidate_maintenance_cache() -> None:
    """Force the next request to reload maintenance settings from DB."""
    global _maintenance_cache_expires_at
    _maintenance_cache_expires_at = 0.0
