"""Request-level middleware and dependencies — IP ban enforcement & rate limiting."""

import time
from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select

from app.core.database import async_session
from app.modules.owner.models import IPBan

# ── In-memory rate limiter for auth endpoints ─────────────────────────────
_rate_limits: dict[str, list[float]] = defaultdict(list)  # IP -> [timestamps]
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # max requests per window for auth endpoints


async def rate_limit_auth(request: Request) -> None:
    """Rate limit authentication endpoints (login, register).

    Uses a simple sliding-window counter keyed by client IP.
    Raises HTTP 429 if the limit is exceeded.
    """
    ip = request.client.host if request.client else "unknown"
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
    now = datetime.utcnow()
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

    client_ip = request.client.host if request.client else None
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
