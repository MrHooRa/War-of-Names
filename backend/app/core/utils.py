"""Core utility helpers."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from app.config import PLATFORM_TZ


def now_riyadh() -> datetime:
    """Return the current datetime in Riyadh timezone (Asia/Riyadh, UTC+3)."""
    return datetime.now(PLATFORM_TZ)


def now_riyadh_naive() -> datetime:
    """Return the current Riyadh-local datetime without tzinfo.

    The current codebase stores and compares naive datetimes across most ORM
    models and runtime checks. This helper standardizes those values on Riyadh
    local time so scheduling and gameplay logic follow the BRD consistently
    without mixing naive and aware datetime objects.
    """
    return now_riyadh().replace(tzinfo=None)


def coerce_riyadh_naive(value: datetime | None) -> datetime | None:
    """Normalize any datetime to a naive Riyadh-local value."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(PLATFORM_TZ).replace(tzinfo=None)


def jsonb_safe(obj: Any) -> Any:
    """Recursively convert Python objects to JSON-serializable equivalents.

    Handles the types that commonly appear in SQLAlchemy models but are NOT
    natively serializable by ``json.dumps`` (which asyncpg calls internally
    when writing to JSONB columns):

    * ``uuid.UUID``  → ``str``
    * ``Enum``       → ``.value``
    * ``datetime``   → ISO-8601 string
    * ``date``       → ISO-8601 string
    * ``dict``       → recurse into values
    * ``list/tuple`` → recurse into elements (tuples become lists)
    * ``set``        → sorted list
    * Everything else is returned as-is (int, float, str, bool, None).
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, uuid.UUID):
        return str(obj)

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, date):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {k: jsonb_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [jsonb_safe(item) for item in obj]

    if isinstance(obj, set):
        return sorted(jsonb_safe(item) for item in obj)

    # Fallback: try str() so we never crash — but log a warning in debug.
    return str(obj)
