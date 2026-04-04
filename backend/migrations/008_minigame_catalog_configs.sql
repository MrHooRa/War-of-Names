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
