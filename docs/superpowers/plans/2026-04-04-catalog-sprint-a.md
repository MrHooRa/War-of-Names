# Catalog & Lobby — Sprint A: Data Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete data layer for `minigame_catalog_configs` — enums, SQLAlchemy model, SQL migration, seed data for مطارحة, a pure fallback resolver, and 4 admin CRUD endpoints with audit logging.

**Architecture:** A new table separate from `minigame_types` holds presentation metadata (icons, colors, sort order, availability mode). The model is registered in `core/models.py`. A pure resolver function provides defaults when a config row is missing. Admin CRUD uses the existing `get_admin_account` dependency and `write_audit` helper.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, PostgreSQL 16, FastAPI, pytest

**BRD Reference:** `docs/minigames/War of Names - Minigames Catalog & Lobby BRD - V1.0.md` — §11.3, §11.3.1, §11.3.2, §11.4, §11.4.2, §11.4.3

**Depends on:** All engine sprints (0-4) + N-player upgrade (Sprint A+B) + مطارحة plugin

---

## Sprint Scope

1. **3 new enums** in `app/core/enums.py`: `MinigameHeroVariant`, `MinigameCardVariant`, `MinigameCatalogAvailability`
2. **`MinigameCatalogConfig` SQLAlchemy model** registered in `core/models.py`
3. **SQL migration 008** with table, indexes, seed row, fallback-safe
4. **مطارحة seed row** via existing `_seed_minigame_types` function (idempotent)
5. **Pure `resolve_catalog_config` function** with fallback defaults per BRD §11.4.3
6. **4 admin CRUD endpoints** (list, get, upsert, delete) with audit logging
7. **Tests** for pure resolver + enum + model shape

**NOT in Sprint A:** Aggregation logic (Sprint B), REST catalog endpoint (Sprint C), WebSocket (Sprint D), Frontend (Sprint E).

---

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── enums.py                              # MODIFY: +3 enums
│   │   └── models.py                             # MODIFY: register new model
│   ├── modules/
│   │   └── minigames/
│   │       ├── catalog_config_model.py           # CREATE: MinigameCatalogConfig
│   │       ├── catalog_config_resolver.py        # CREATE: pure fallback function
│   │       └── router.py                         # MODIFY: +4 admin endpoints
│   └── core/
│       └── seed.py                               # MODIFY: seed مطارحة config row
├── migrations/
│   └── 008_minigame_catalog_configs.sql          # CREATE
└── tests/
    └── test_minigame_engine/
        ├── test_catalog_enums.py                 # CREATE
        └── test_catalog_config_resolver.py       # CREATE
```

---

## Task 1: Catalog Enums

**Files:**
- Modify: `backend/app/core/enums.py`
- Create: `backend/tests/test_minigame_engine/test_catalog_enums.py`

Three new `StrEnum` classes for variant and availability fields.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_catalog_enums.py`:

```python
"""Verify catalog enums exist and have expected members."""

from app.core.enums import (
    MinigameHeroVariant,
    MinigameCardVariant,
    MinigameCatalogAvailability,
)


def test_hero_variants():
    values = {v.value for v in MinigameHeroVariant}
    assert values == {"duel", "arena", "solo", "party", "tournament"}


def test_card_variants():
    values = {v.value for v in MinigameCardVariant}
    assert values == {"standard", "featured", "compact", "coming_soon_teaser"}


def test_availability_modes():
    values = {v.value for v in MinigameCatalogAvailability}
    assert values == {"active", "coming_soon", "hidden", "maintenance"}


def test_hero_variant_specific_members():
    assert MinigameHeroVariant.DUEL.value == "duel"
    assert MinigameHeroVariant.ARENA.value == "arena"
    assert MinigameHeroVariant.SOLO.value == "solo"
    assert MinigameHeroVariant.PARTY.value == "party"
    assert MinigameHeroVariant.TOURNAMENT.value == "tournament"


def test_card_variant_specific_members():
    assert MinigameCardVariant.STANDARD.value == "standard"
    assert MinigameCardVariant.FEATURED.value == "featured"
    assert MinigameCardVariant.COMPACT.value == "compact"
    assert MinigameCardVariant.COMING_SOON_TEASER.value == "coming_soon_teaser"


def test_availability_specific_members():
    assert MinigameCatalogAvailability.ACTIVE.value == "active"
    assert MinigameCatalogAvailability.COMING_SOON.value == "coming_soon"
    assert MinigameCatalogAvailability.HIDDEN.value == "hidden"
    assert MinigameCatalogAvailability.MAINTENANCE.value == "maintenance"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_enums.py -v`
Expected: FAIL — `ImportError: cannot import name 'MinigameHeroVariant'`

- [ ] **Step 3: Add enums to `backend/app/core/enums.py`**

Find the existing `MinigameTypeStatus` class (around line 365) and add three new classes after it:

```python
class MinigameHeroVariant(StrEnum):
    DUEL = "duel"
    ARENA = "arena"
    SOLO = "solo"
    PARTY = "party"
    TOURNAMENT = "tournament"


class MinigameCardVariant(StrEnum):
    STANDARD = "standard"
    FEATURED = "featured"
    COMPACT = "compact"
    COMING_SOON_TEASER = "coming_soon_teaser"


class MinigameCatalogAvailability(StrEnum):
    ACTIVE = "active"
    COMING_SOON = "coming_soon"
    HIDDEN = "hidden"
    MAINTENANCE = "maintenance"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_enums.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/core/enums.py backend/tests/test_minigame_engine/test_catalog_enums.py && git commit -m "feat(minigames): add catalog enums — hero variant, card variant, availability mode

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `MinigameCatalogConfig` SQLAlchemy Model

**Files:**
- Create: `backend/app/modules/minigames/catalog_config_model.py`
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Create the model file**

Create `backend/app/modules/minigames/catalog_config_model.py`:

```python
"""Presentation metadata for minigame catalog cards.

Separate from MinigameType (which holds operational metadata) so that
marketing/UX fields can evolve independently of the engine contract.

BRD reference: §11.3
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    MinigameCardVariant,
    MinigameCatalogAvailability,
    MinigameHeroVariant,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


class MinigameCatalogConfig(Base):
    __tablename__ = "minigame_catalog_configs"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="chk_mg_catalog_sort_order"),
        CheckConstraint(
            "estimated_duration_sec IS NULL OR estimated_duration_sec > 0",
            name="chk_mg_catalog_duration_positive",
        ),
    )

    # Primary key — 1:1 with minigame_types.id
    game_type: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("minigame_types.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Presentation content
    short_description: Mapped[str] = mapped_column(String(200), nullable=False)
    icon_token: Mapped[str] = mapped_column(String(100), nullable=False)
    accent_color: Mapped[str] = mapped_column(String(7), nullable=False)  # #RRGGBB

    # Layout variants (enums)
    hero_variant: Mapped[MinigameHeroVariant] = mapped_column(
        pg_enum(MinigameHeroVariant, name="minigame_hero_variant"),
        nullable=False,
        default=MinigameHeroVariant.ARENA,
    )
    card_variant: Mapped[MinigameCardVariant] = mapped_column(
        pg_enum(MinigameCardVariant, name="minigame_card_variant"),
        nullable=False,
        default=MinigameCardVariant.STANDARD,
    )

    # Optional metadata
    estimated_duration_sec: Mapped[int | None] = mapped_column()
    featured: Mapped[bool] = mapped_column(nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)

    # Availability + marketing
    availability_mode: Mapped[MinigameCatalogAvailability] = mapped_column(
        pg_enum(MinigameCatalogAvailability, name="minigame_catalog_availability"),
        nullable=False,
        default=MinigameCatalogAvailability.ACTIVE,
    )
    marketing_label: Mapped[str | None] = mapped_column(String(100))
    expected_launch_at: Mapped[datetime | None] = mapped_column()

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)
```

- [ ] **Step 2: Register the model in `core/models.py`**

Read `backend/app/core/models.py` to find the minigames import block (around line 78).

After `from app.modules.minigames.mutaraha.models import MutarahaWord  # noqa: E402, F401`, add:

```python
from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: E402, F401
```

- [ ] **Step 3: Verify the model is importable**

Run:
```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/catalog_config_model.py').read()); print('syntax ok')"
```

- [ ] **Step 4: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_config_model.py backend/app/core/models.py && git commit -m "feat(minigames): add MinigameCatalogConfig model — presentation metadata for catalog cards

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: SQL Migration 008

**Files:**
- Create: `backend/migrations/008_minigame_catalog_configs.sql`

The migration creates the table, indexes, and the مطارحة seed row in one transaction.

- [ ] **Step 1: Create the migration**

Create `backend/migrations/008_minigame_catalog_configs.sql`:

```sql
-- ============================================================
-- Migration 008: Minigame Catalog Configs
-- BRD: docs/minigames/War of Names - Minigames Catalog & Lobby BRD - V1.0.md §11.3
-- ============================================================

BEGIN;

-- ── New ENUM types ───────────────────────────────────────────

DO $$ BEGIN
    CREATE TYPE minigame_hero_variant AS ENUM ('duel', 'arena', 'solo', 'party', 'tournament');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE minigame_card_variant AS ENUM ('standard', 'featured', 'compact', 'coming_soon_teaser');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE minigame_catalog_availability AS ENUM ('active', 'coming_soon', 'hidden', 'maintenance');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ── minigame_catalog_configs table ──────────────────────────

CREATE TABLE IF NOT EXISTS minigame_catalog_configs (
    game_type           VARCHAR(64) PRIMARY KEY
                        REFERENCES minigame_types(id) ON DELETE CASCADE,
    short_description   VARCHAR(200) NOT NULL,
    icon_token          VARCHAR(100) NOT NULL,
    accent_color        VARCHAR(7) NOT NULL,
    hero_variant        minigame_hero_variant NOT NULL DEFAULT 'arena',
    card_variant        minigame_card_variant NOT NULL DEFAULT 'standard',
    estimated_duration_sec INTEGER,
    featured            BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order          INTEGER NOT NULL DEFAULT 100,
    availability_mode   minigame_catalog_availability NOT NULL DEFAULT 'active',
    marketing_label     VARCHAR(100),
    expected_launch_at  TIMESTAMP WITHOUT TIME ZONE,
    created_at          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_mg_catalog_sort_order CHECK (sort_order >= 0),
    CONSTRAINT chk_mg_catalog_duration_positive CHECK (
        estimated_duration_sec IS NULL OR estimated_duration_sec > 0
    )
);

-- ── Indexes (BRD §11.3.2) ───────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_catalog_sort
    ON minigame_catalog_configs (availability_mode, sort_order);

CREATE INDEX IF NOT EXISTS idx_catalog_featured
    ON minigame_catalog_configs (featured) WHERE featured = true;

-- ── Seed row: مطارحة (BRD §11.4.2) ──────────────────────────

INSERT INTO minigame_catalog_configs (
    game_type,
    short_description,
    icon_token,
    accent_color,
    hero_variant,
    card_variant,
    estimated_duration_sec,
    featured,
    sort_order,
    availability_mode,
    marketing_label,
    expected_launch_at
)
SELECT
    'mutaraha',
    'مبارزة كلمات 1v1 — فراسة واستنتاج',
    'lucide:swords',
    '#D84315',
    'duel'::minigame_hero_variant,
    'standard'::minigame_card_variant,
    300,
    true,
    10,
    'active'::minigame_catalog_availability,
    NULL,
    NULL
WHERE EXISTS (SELECT 1 FROM minigame_types WHERE id = 'mutaraha')
ON CONFLICT (game_type) DO NOTHING;

COMMIT;
```

- [ ] **Step 2: Verify migration SQL syntax**

Run:
```bash
cd backend && python -c "
with open('migrations/008_minigame_catalog_configs.sql') as f:
    sql = f.read()
assert 'CREATE TABLE IF NOT EXISTS minigame_catalog_configs' in sql
assert 'BEGIN;' in sql
assert 'COMMIT;' in sql
assert 'ON DELETE CASCADE' in sql
assert 'idx_catalog_sort' in sql
assert 'idx_catalog_featured' in sql
assert \"'mutaraha'\" in sql
print('migration 008 looks good')
"
```

- [ ] **Step 3: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/migrations/008_minigame_catalog_configs.sql && git commit -m "feat(minigames): SQL migration 008 — minigame_catalog_configs table + مطارحة seed

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Seed مطارحة Catalog Config (Python Idempotent Seeder)

**Files:**
- Modify: `backend/app/core/seed.py`

The SQL migration handles fresh deployments. This step adds an idempotent Python seeder that runs at startup alongside the existing `_seed_minigame_types` so dev databases stay in sync.

- [ ] **Step 1: Add `_seed_minigame_catalog_configs` function in `seed.py`**

Find `_seed_minigame_types` (around line 1060) and add a new function immediately after it:

```python
async def _seed_minigame_catalog_configs(session: AsyncSession) -> None:
    """Seed presentation metadata for minigame catalog cards.

    Idempotent — uses session.get() by primary key and skips if the row
    already exists. Paired with migration 008_minigame_catalog_configs.sql
    for fresh deployments.
    """
    from app.core.enums import (
        MinigameCardVariant,
        MinigameCatalogAvailability,
        MinigameHeroVariant,
    )
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig

    configs_data = [
        {
            "game_type": "mutaraha",
            "short_description": "مبارزة كلمات 1v1 — فراسة واستنتاج",
            "icon_token": "lucide:swords",
            "accent_color": "#D84315",
            "hero_variant": MinigameHeroVariant.DUEL,
            "card_variant": MinigameCardVariant.STANDARD,
            "estimated_duration_sec": 300,
            "featured": True,
            "sort_order": 10,
            "availability_mode": MinigameCatalogAvailability.ACTIVE,
            "marketing_label": None,
            "expected_launch_at": None,
        },
    ]

    for cd in configs_data:
        existing = await session.get(MinigameCatalogConfig, cd["game_type"])
        if existing:
            continue
        session.add(MinigameCatalogConfig(**cd))

    await session.commit()
```

- [ ] **Step 2: Call the seeder from the main `seed()` function**

Find the main `seed()` function (top of the file, around line 78) and add the new call after `_seed_mutaraha_words`:

```python
    await _seed_minigame_types(session)
    await _seed_mutaraha_words(session)
    await _seed_minigame_catalog_configs(session)  # NEW
```

- [ ] **Step 3: Syntax check**

Run:
```bash
cd backend && python -c "import ast; ast.parse(open('app/core/seed.py').read()); print('seed.py syntax ok')"
```

- [ ] **Step 4: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/core/seed.py && git commit -m "feat(minigames): Python seeder for minigame_catalog_configs — مطارحة presentation metadata

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Pure Fallback Resolver

**Files:**
- Create: `backend/app/modules/minigames/catalog_config_resolver.py`
- Create: `backend/tests/test_minigame_engine/test_catalog_config_resolver.py`

A pure function that builds the effective catalog metadata from a `(MinigameType, MinigameCatalogConfig | None)` pair. When the config is missing, it returns BRD §11.4.3 defaults and records a telemetry warning.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_minigame_engine/test_catalog_config_resolver.py`:

```python
"""Test the pure catalog config resolver.

Verifies fallback defaults from BRD §11.4.3 when a config row is missing,
and passthrough of real values when present.
"""

from types import SimpleNamespace

from app.core.enums import (
    MinigameCardVariant,
    MinigameCatalogAvailability,
    MinigameHeroVariant,
)
from app.modules.minigames.catalog_config_resolver import (
    FALLBACK_ACCENT_COLOR,
    FALLBACK_CARD_VARIANT,
    FALLBACK_HERO_VARIANT,
    FALLBACK_ICON_TOKEN,
    FALLBACK_SHORT_DESCRIPTION_EMPTY,
    resolve_catalog_config,
)


def _game_type(description: str | None = None):
    return SimpleNamespace(id="demo", name="Demo", description=description)


def _config(**overrides):
    base = dict(
        game_type="demo",
        short_description="custom short",
        icon_token="lucide:custom",
        accent_color="#ABCDEF",
        hero_variant=MinigameHeroVariant.DUEL,
        card_variant=MinigameCardVariant.FEATURED,
        estimated_duration_sec=420,
        featured=True,
        sort_order=5,
        availability_mode=MinigameCatalogAvailability.ACTIVE,
        marketing_label="hot",
        expected_launch_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── Config present — passthrough ─────────────────────────────

def test_real_config_returned_as_is():
    gt = _game_type(description="ignored description")
    cfg = _config()

    result, warning = resolve_catalog_config(gt, cfg)

    assert warning is False
    assert result["short_description"] == "custom short"
    assert result["icon_token"] == "lucide:custom"
    assert result["accent_color"] == "#ABCDEF"
    assert result["hero_variant"] == "duel"
    assert result["card_variant"] == "featured"
    assert result["estimated_duration_sec"] == 420
    assert result["featured"] is True
    assert result["sort_order"] == 5
    assert result["availability_mode"] == "active"
    assert result["marketing_label"] == "hot"
    assert result["expected_launch_at"] is None


def test_enum_passthrough_accepts_plain_strings():
    """Resolver must also handle dict-ish inputs with string enum values."""
    gt = _game_type()
    cfg = SimpleNamespace(
        game_type="demo",
        short_description="s",
        icon_token="lucide:x",
        accent_color="#000000",
        hero_variant="arena",  # plain string
        card_variant="standard",
        estimated_duration_sec=None,
        featured=False,
        sort_order=50,
        availability_mode="active",
        marketing_label=None,
        expected_launch_at=None,
    )

    result, warning = resolve_catalog_config(gt, cfg)

    assert warning is False
    assert result["hero_variant"] == "arena"
    assert result["card_variant"] == "standard"


# ── Config missing — fallback ────────────────────────────────

def test_missing_config_returns_fallback_with_game_type_description():
    gt = _game_type(description="a game type description")

    result, warning = resolve_catalog_config(gt, None)

    assert warning is True
    assert result["short_description"] == "a game type description"
    assert result["icon_token"] == FALLBACK_ICON_TOKEN
    assert result["accent_color"] == FALLBACK_ACCENT_COLOR
    assert result["hero_variant"] == FALLBACK_HERO_VARIANT
    assert result["card_variant"] == FALLBACK_CARD_VARIANT
    assert result["availability_mode"] == "hidden"


def test_missing_config_with_null_description_uses_empty_string():
    gt = _game_type(description=None)

    result, warning = resolve_catalog_config(gt, None)

    assert warning is True
    assert result["short_description"] == FALLBACK_SHORT_DESCRIPTION_EMPTY


def test_fallback_sets_hidden_availability():
    """BRD §11.4.3 — missing config → hidden by default."""
    gt = _game_type()
    result, warning = resolve_catalog_config(gt, None)
    assert result["availability_mode"] == "hidden"
    assert warning is True


def test_fallback_sort_order_default():
    gt = _game_type()
    result, _ = resolve_catalog_config(gt, None)
    assert result["sort_order"] == 999  # pushed to end


def test_fallback_no_duration_no_featured():
    gt = _game_type()
    result, _ = resolve_catalog_config(gt, None)
    assert result["estimated_duration_sec"] is None
    assert result["featured"] is False
    assert result["marketing_label"] is None
    assert result["expected_launch_at"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_config_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the resolver**

Create `backend/app/modules/minigames/catalog_config_resolver.py`:

```python
"""Pure resolver that produces effective catalog metadata for a game type.

When a MinigameCatalogConfig row exists, its values are returned as-is
(normalized to dict). When it is missing, a fallback dict is returned
per BRD §11.4.3 and a warning flag is set so the caller can emit a
`catalog_config_missing` telemetry event.

This module is a pure function module — no DB, no async, fully testable.
"""

from __future__ import annotations

from typing import Any


# BRD §11.4.3 fallback constants
FALLBACK_ICON_TOKEN = "lucide:gamepad-2"
FALLBACK_ACCENT_COLOR = "#64748B"  # brand-slate
FALLBACK_HERO_VARIANT = "arena"
FALLBACK_CARD_VARIANT = "standard"
FALLBACK_AVAILABILITY_MODE = "hidden"
FALLBACK_SORT_ORDER = 999
FALLBACK_SHORT_DESCRIPTION_EMPTY = ""


def _enum_value(value: Any) -> str:
    """Coerce a StrEnum member or raw string to its string value."""
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def resolve_catalog_config(
    game_type_row: Any,
    config_row: Any | None,
) -> tuple[dict[str, Any], bool]:
    """Return (resolved_config_dict, is_fallback).

    Args:
        game_type_row: A MinigameType-like object with `id`, `name`, `description`.
        config_row: A MinigameCatalogConfig instance, or None when missing.

    Returns:
        A tuple of:
          - resolved dict with all presentation fields populated
          - is_fallback flag (True when config_row was None)

    Fallback rules (BRD §11.4.3):
        short_description → game_type.description or "" when missing
        icon_token        → "lucide:gamepad-2"
        accent_color      → "#64748B" (brand-slate)
        hero_variant      → "arena"
        card_variant      → "standard"
        availability_mode → "hidden" (so fallback rows don't show until admin configures)
        sort_order        → 999 (pushed to end)
    """
    if config_row is None:
        return (
            {
                "short_description": (
                    getattr(game_type_row, "description", None)
                    or FALLBACK_SHORT_DESCRIPTION_EMPTY
                ),
                "icon_token": FALLBACK_ICON_TOKEN,
                "accent_color": FALLBACK_ACCENT_COLOR,
                "hero_variant": FALLBACK_HERO_VARIANT,
                "card_variant": FALLBACK_CARD_VARIANT,
                "estimated_duration_sec": None,
                "featured": False,
                "sort_order": FALLBACK_SORT_ORDER,
                "availability_mode": FALLBACK_AVAILABILITY_MODE,
                "marketing_label": None,
                "expected_launch_at": None,
            },
            True,
        )

    return (
        {
            "short_description": config_row.short_description,
            "icon_token": config_row.icon_token,
            "accent_color": config_row.accent_color,
            "hero_variant": _enum_value(config_row.hero_variant),
            "card_variant": _enum_value(config_row.card_variant),
            "estimated_duration_sec": config_row.estimated_duration_sec,
            "featured": config_row.featured,
            "sort_order": config_row.sort_order,
            "availability_mode": _enum_value(config_row.availability_mode),
            "marketing_label": config_row.marketing_label,
            "expected_launch_at": config_row.expected_launch_at,
        },
        False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_minigame_engine/test_catalog_config_resolver.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/catalog_config_resolver.py backend/tests/test_minigame_engine/test_catalog_config_resolver.py && git commit -m "feat(minigames): add pure catalog config resolver with fallback defaults

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Admin CRUD Endpoints

**Files:**
- Modify: `backend/app/modules/minigames/router.py`

Four endpoints under the `/api/admin/minigames/catalog-configs` prefix. All require `AdminAccount` and write audit events.

- [ ] **Step 1: Read the existing admin pattern**

Read lines 1266-1410 in `backend/app/modules/minigames/router.py` to understand the existing admin endpoint structure (kill switch endpoint). Reuse the same patterns: `AdminAccount` dependency, `write_audit` call, Arabic error messages.

- [ ] **Step 2: Add Pydantic request models**

Find the top of `router.py` (near existing `BaseModel` imports) and add:

```python
class CatalogConfigUpsertRequest(BaseModel):
    short_description: str
    icon_token: str
    accent_color: str
    hero_variant: str
    card_variant: str
    estimated_duration_sec: int | None = None
    featured: bool = False
    sort_order: int = 100
    availability_mode: str
    marketing_label: str | None = None
    expected_launch_at: datetime | None = None
```

Place it near other BaseModel classes in the file. Ensure `datetime` is imported at the top.

- [ ] **Step 3: Add the four endpoints**

Find the end of the admin endpoints section in `router.py` (after `admin_get_session_events` around line 1467) and append:

```python
# ─── Catalog Config Admin CRUD ───────────────────────────────────────────────

@router.get("/api/admin/minigames/catalog-configs")
async def admin_list_catalog_configs(admin: AdminAccount):
    """List all minigame catalog configs (admin only).

    Returns rows sorted by sort_order ASC, then game_type ASC for stable ordering.
    """
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415

    async with async_session() as session:
        result = await session.execute(
            select(MinigameCatalogConfig).order_by(
                MinigameCatalogConfig.sort_order.asc(),
                MinigameCatalogConfig.game_type.asc(),
            )
        )
        rows = result.scalars().all()

    return {
        "items": [
            {
                "game_type": row.game_type,
                "short_description": row.short_description,
                "icon_token": row.icon_token,
                "accent_color": row.accent_color,
                "hero_variant": (
                    row.hero_variant.value
                    if hasattr(row.hero_variant, "value")
                    else str(row.hero_variant)
                ),
                "card_variant": (
                    row.card_variant.value
                    if hasattr(row.card_variant, "value")
                    else str(row.card_variant)
                ),
                "estimated_duration_sec": row.estimated_duration_sec,
                "featured": row.featured,
                "sort_order": row.sort_order,
                "availability_mode": (
                    row.availability_mode.value
                    if hasattr(row.availability_mode, "value")
                    else str(row.availability_mode)
                ),
                "marketing_label": row.marketing_label,
                "expected_launch_at": (
                    row.expected_launch_at.isoformat() if row.expected_launch_at else None
                ),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    }


@router.get("/api/admin/minigames/catalog-configs/{game_type}")
async def admin_get_catalog_config(game_type: str, admin: AdminAccount):
    """Get a single catalog config by game_type.

    Returns 404 with an Arabic message when the row is missing.
    """
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415

    async with async_session() as session:
        row = await session.get(MinigameCatalogConfig, game_type)
        if row is None:
            raise HTTPException(status_code=404, detail="تهيئة الكاتالوج غير موجودة")

    return {
        "game_type": row.game_type,
        "short_description": row.short_description,
        "icon_token": row.icon_token,
        "accent_color": row.accent_color,
        "hero_variant": (
            row.hero_variant.value
            if hasattr(row.hero_variant, "value")
            else str(row.hero_variant)
        ),
        "card_variant": (
            row.card_variant.value
            if hasattr(row.card_variant, "value")
            else str(row.card_variant)
        ),
        "estimated_duration_sec": row.estimated_duration_sec,
        "featured": row.featured,
        "sort_order": row.sort_order,
        "availability_mode": (
            row.availability_mode.value
            if hasattr(row.availability_mode, "value")
            else str(row.availability_mode)
        ),
        "marketing_label": row.marketing_label,
        "expected_launch_at": (
            row.expected_launch_at.isoformat() if row.expected_launch_at else None
        ),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.put("/api/admin/minigames/catalog-configs/{game_type}")
async def admin_upsert_catalog_config(
    game_type: str,
    body: CatalogConfigUpsertRequest,
    admin: AdminAccount,
):
    """Create or update a catalog config (admin only).

    Validates that game_type exists in minigame_types.
    Enum values are validated against MinigameHeroVariant / MinigameCardVariant /
    MinigameCatalogAvailability. Invalid values return 400 with an Arabic message.
    """
    from app.core.enums import (  # noqa: PLC0415
        AuditActorType,
        MinigameCardVariant,
        MinigameCatalogAvailability,
        MinigameHeroVariant,
    )
    from app.modules.audit.service import write_audit  # noqa: PLC0415
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415
    from app.modules.minigames.models import MinigameType  # noqa: PLC0415

    # Validate enums — raises 400 with Arabic message on failure
    try:
        hero = MinigameHeroVariant(body.hero_variant)
    except ValueError:
        valid = ", ".join(v.value for v in MinigameHeroVariant)
        raise HTTPException(status_code=400, detail=f"قيمة hero_variant غير صالحة. القيم المسموحة: {valid}")

    try:
        card = MinigameCardVariant(body.card_variant)
    except ValueError:
        valid = ", ".join(v.value for v in MinigameCardVariant)
        raise HTTPException(status_code=400, detail=f"قيمة card_variant غير صالحة. القيم المسموحة: {valid}")

    try:
        availability = MinigameCatalogAvailability(body.availability_mode)
    except ValueError:
        valid = ", ".join(v.value for v in MinigameCatalogAvailability)
        raise HTTPException(status_code=400, detail=f"قيمة availability_mode غير صالحة. القيم المسموحة: {valid}")

    async with async_session() as session:
        # Verify the game_type exists
        game_type_row = await session.get(MinigameType, game_type)
        if game_type_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"نوع اللعبة '{game_type}' غير مسجل في المحرك",
            )

        existing = await session.get(MinigameCatalogConfig, game_type)
        was_created = existing is None
        before_state = None

        if existing is None:
            row = MinigameCatalogConfig(
                game_type=game_type,
                short_description=body.short_description,
                icon_token=body.icon_token,
                accent_color=body.accent_color,
                hero_variant=hero,
                card_variant=card,
                estimated_duration_sec=body.estimated_duration_sec,
                featured=body.featured,
                sort_order=body.sort_order,
                availability_mode=availability,
                marketing_label=body.marketing_label,
                expected_launch_at=body.expected_launch_at,
            )
            session.add(row)
        else:
            before_state = {
                "short_description": existing.short_description,
                "icon_token": existing.icon_token,
                "accent_color": existing.accent_color,
                "hero_variant": str(existing.hero_variant),
                "card_variant": str(existing.card_variant),
                "estimated_duration_sec": existing.estimated_duration_sec,
                "featured": existing.featured,
                "sort_order": existing.sort_order,
                "availability_mode": str(existing.availability_mode),
                "marketing_label": existing.marketing_label,
            }
            existing.short_description = body.short_description
            existing.icon_token = body.icon_token
            existing.accent_color = body.accent_color
            existing.hero_variant = hero
            existing.card_variant = card
            existing.estimated_duration_sec = body.estimated_duration_sec
            existing.featured = body.featured
            existing.sort_order = body.sort_order
            existing.availability_mode = availability
            existing.marketing_label = body.marketing_label
            existing.expected_launch_at = body.expected_launch_at
            row = existing

        after_state = {
            "short_description": row.short_description,
            "icon_token": row.icon_token,
            "accent_color": row.accent_color,
            "hero_variant": hero.value,
            "card_variant": card.value,
            "estimated_duration_sec": row.estimated_duration_sec,
            "featured": row.featured,
            "sort_order": row.sort_order,
            "availability_mode": availability.value,
            "marketing_label": row.marketing_label,
        }

        event_type = (
            "minigame_catalog_config_created"
            if was_created
            else "minigame_catalog_config_updated"
        )
        summary = (
            f"أنشأ تهيئة كاتالوج لـ {game_type}"
            if was_created
            else f"حدّث تهيئة كاتالوج لـ {game_type}"
        )

        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="minigame_catalog_config",
            subject_id=None,
            event_type=event_type,
            summary=summary,
            before_state=before_state,
            after_state=after_state,
        )
        await session.commit()

    return {"message": "تم الحفظ", "game_type": game_type, "created": was_created}


@router.delete("/api/admin/minigames/catalog-configs/{game_type}")
async def admin_delete_catalog_config(game_type: str, admin: AdminAccount):
    """Delete a catalog config row (admin only).

    Hard delete — the row is removed. The game remains in minigame_types and will
    fall back to defaults in the resolver until a new config is created.
    """
    from app.core.enums import AuditActorType  # noqa: PLC0415
    from app.modules.audit.service import write_audit  # noqa: PLC0415
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig  # noqa: PLC0415

    async with async_session() as session:
        row = await session.get(MinigameCatalogConfig, game_type)
        if row is None:
            raise HTTPException(status_code=404, detail="تهيئة الكاتالوج غير موجودة")

        before_state = {
            "short_description": row.short_description,
            "availability_mode": str(row.availability_mode),
        }

        await session.delete(row)
        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="minigame_catalog_config",
            subject_id=None,
            event_type="minigame_catalog_config_deleted",
            summary=f"حذف تهيئة كاتالوج لـ {game_type}",
            before_state=before_state,
            after_state=None,
        )
        await session.commit()

    return {"message": "تم الحذف", "game_type": game_type}
```

- [ ] **Step 4: Verify syntax**

Run:
```bash
cd backend && python -c "import ast; ast.parse(open('app/modules/minigames/router.py').read()); print('router syntax ok')"
```

- [ ] **Step 5: Commit**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add backend/app/modules/minigames/router.py && git commit -m "feat(minigames): admin CRUD endpoints for minigame_catalog_configs + audit

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Final Verification

- [ ] **Step 1: Run the full pure-test suite**

Run:
```bash
cd backend && python -m pytest \
  tests/test_minigame_engine/test_catalog_enums.py \
  tests/test_minigame_engine/test_catalog_config_resolver.py \
  tests/test_minigame_engine/test_enums.py \
  tests/test_minigame_engine/test_plugin_contract.py \
  tests/test_minigame_engine/test_registry.py \
  tests/test_minigame_engine/test_state_machine.py \
  tests/test_minigame_engine/test_session_service.py \
  tests/test_minigame_engine/test_settlement_service.py \
  tests/test_minigame_engine/test_policy_service.py \
  tests/test_minigame_engine/test_leaderboard_service.py \
  tests/test_minigame_engine/test_settings_helper.py \
  tests/test_minigame_engine/test_connection_manager.py \
  tests/test_minigame_engine/test_lobby_manager.py \
  tests/test_minigame_engine/test_mutaraha_tools.py \
  tests/test_minigame_engine/test_mutaraha_plugin.py \
  -v --tb=short 2>&1 | tail -10
```

Expected: All tests pass (previous 212 + 13 new = 225+).

- [ ] **Step 2: Final commit (plan document)**

```bash
cd "e:/Salman/مشاريع/War of Names" && git add docs/superpowers/plans/2026-04-04-catalog-sprint-a.md && git commit -m "docs: Catalog Sprint A detailed task-by-task plan

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Sprint A Deliverables Summary

| Task | Component | Tests |
|---|---|---|
| 1 | Catalog enums (3 StrEnum classes) | 6 |
| 2 | `MinigameCatalogConfig` model + registration | via import |
| 3 | SQL migration 008 | via Docker rebuild |
| 4 | Python seeder for مطارحة | via import |
| 5 | Pure fallback resolver | 7 |
| 6 | Admin CRUD endpoints (4) | via Docker integration |
| **Total** | **6 files created, 3 modified** | **13 new pure tests** |

## What Sprint B Will Build On This

Sprint B (Catalog Aggregation Service) will use:
- `MinigameCatalogConfig` model via batched `SELECT * FROM minigame_catalog_configs`
- `resolve_catalog_config()` as the fallback layer in `CatalogDataLoader`
- Enum values in `build_catalog_cards` for `hero_variant` and `card_variant` passthrough
- Admin CRUD to let the product team edit cards directly — no code changes required
