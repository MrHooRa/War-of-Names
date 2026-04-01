-- ============================================================
-- Migration 003: Minigame Engine tables
-- BRD: docs/minigames/War of Names - Minigame Engine BRD - V1.0.md
-- ============================================================

BEGIN;

-- ── New ENUM types ───────────────────────────────────────────

CREATE TYPE minigame_type_status AS ENUM ('active', 'disabled', 'deprecated');
CREATE TYPE minigame_session_phase AS ENUM ('created', 'waiting', 'ready', 'in_progress', 'overtime', 'paused', 'completed', 'cancelled', 'abandoned');
CREATE TYPE minigame_match_type AS ENUM ('challenge', 'queue');
CREATE TYPE minigame_settlement_state AS ENUM ('pending', 'settled', 'failed', 'reconciled');
CREATE TYPE minigame_turn_side AS ENUM ('player_1', 'player_2');

-- ── Extend existing ledger_entry_type ────────────────────────

ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_buy_in';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_payout';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_forfeit';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_refund';
ALTER TYPE ledger_entry_type ADD VALUE IF NOT EXISTS 'minigame_cancel_penalty';

-- ── minigame_types ───────────────────────────────────────────

CREATE TABLE minigame_types (
    id              VARCHAR(64) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    plugin_api_version      VARCHAR(10) NOT NULL DEFAULT '1.0',
    settings_schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    min_players     INTEGER NOT NULL DEFAULT 2,
    max_players     INTEGER NOT NULL DEFAULT 2,
    supports_overtime   BOOLEAN NOT NULL DEFAULT FALSE,
    supports_spectators BOOLEAN NOT NULL DEFAULT FALSE,
    supports_ranked     BOOLEAN NOT NULL DEFAULT FALSE,
    supports_team_mode  BOOLEAN NOT NULL DEFAULT FALSE,
    status          minigame_type_status NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- ── minigame_sessions ────────────────────────────────────────

CREATE TABLE minigame_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_type               VARCHAR(64) NOT NULL REFERENCES minigame_types(id) ON DELETE RESTRICT,
    competition_id          UUID NOT NULL REFERENCES competitions(id) ON DELETE RESTRICT,
    season_id               UUID REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id                UUID REFERENCES cycles(id) ON DELETE SET NULL,
    phase                   minigame_session_phase NOT NULL DEFAULT 'created',
    revision                INTEGER NOT NULL DEFAULT 0,
    player_1_membership_id  UUID NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    player_2_membership_id  UUID REFERENCES memberships(id) ON DELETE RESTRICT,
    match_type              minigame_match_type NOT NULL,
    current_turn            minigame_turn_side,
    turn_number             INTEGER NOT NULL DEFAULT 0,
    game_state              JSONB NOT NULL DEFAULT '{}'::jsonb,
    settings_snapshot       JSONB NOT NULL DEFAULT '{}'::jsonb,
    buy_in_amount           INTEGER NOT NULL DEFAULT 0,
    reconnect_token_p1      VARCHAR(128),
    reconnect_token_p2      VARCHAR(128),
    terminal_reason         VARCHAR(100),
    winner_membership_id    UUID REFERENCES memberships(id) ON DELETE SET NULL,
    turn_started_at         TIMESTAMP WITHOUT TIME ZONE,
    turn_duration_ms        INTEGER NOT NULL DEFAULT 30000,
    grace_timer_ms          INTEGER NOT NULL DEFAULT 60000,
    correlation_id          UUID NOT NULL DEFAULT gen_random_uuid(),
    started_at              TIMESTAMP WITHOUT TIME ZONE,
    completed_at            TIMESTAMP WITHOUT TIME ZONE,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_mg_buy_in CHECK (buy_in_amount >= 0),
    CONSTRAINT chk_mg_revision CHECK (revision >= 0),
    CONSTRAINT chk_mg_turn_number CHECK (turn_number >= 0)
);

CREATE INDEX idx_mg_sessions_active
    ON minigame_sessions (game_type, competition_id)
    WHERE phase NOT IN ('completed', 'cancelled', 'abandoned');

-- ── minigame_session_events ──────────────────────────────────

CREATE TABLE minigame_session_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    revision                INTEGER NOT NULL,
    event_type              VARCHAR(20) NOT NULL,
    actor_type              VARCHAR(20) NOT NULL,
    actor_membership_id     UUID,
    action_type             VARCHAR(50),
    payload                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    result                  JSONB NOT NULL DEFAULT '{}'::jsonb,
    from_phase              VARCHAR(20),
    to_phase                VARCHAR(20),
    correlation_id          UUID NOT NULL,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mg_events_session ON minigame_session_events (session_id, revision);

-- ── minigame_action_receipts ─────────────────────────────────

CREATE TABLE minigame_action_receipts (
    action_id               UUID PRIMARY KEY,
    session_id              UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    actor_membership_id     UUID NOT NULL,
    client_seq              INTEGER NOT NULL,
    response                JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mg_action_seq UNIQUE (session_id, actor_membership_id, client_seq)
);

-- ── minigame_session_settlements ─────────────────────────────

CREATE TABLE minigame_session_settlements (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE RESTRICT,
    winner_membership_id    UUID,
    loser_membership_id     UUID,
    winner_payout           INTEGER NOT NULL DEFAULT 0,
    loser_penalty           INTEGER NOT NULL DEFAULT 0,
    settlement_state        minigame_settlement_state NOT NULL DEFAULT 'pending',
    ledger_entry_ids        UUID[],
    correlation_id          UUID NOT NULL,
    settled_at              TIMESTAMP WITHOUT TIME ZONE,
    failure_reason          TEXT,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mg_settlement_session UNIQUE (session_id),
    CONSTRAINT chk_mg_retry_count CHECK (retry_count >= 0 AND retry_count <= 3)
);

-- ── minigame_leaderboards ────────────────────────────────────

CREATE TABLE minigame_leaderboards (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_type               VARCHAR(64) NOT NULL REFERENCES minigame_types(id) ON DELETE CASCADE,
    competition_id          UUID NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    membership_id           UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    wins                    INTEGER NOT NULL DEFAULT 0,
    losses                  INTEGER NOT NULL DEFAULT 0,
    current_streak          INTEGER NOT NULL DEFAULT 0,
    best_streak             INTEGER NOT NULL DEFAULT 0,
    total_matches           INTEGER NOT NULL DEFAULT 0,
    avg_tools_used          DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    avg_match_duration_sec  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    elo_rating              INTEGER,
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mg_leaderboard UNIQUE (game_type, competition_id, membership_id)
);

-- ── minigame_policy_rules ────────────────────────────────────

CREATE TABLE minigame_policy_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_type               VARCHAR(64),
    competition_id          UUID REFERENCES competitions(id) ON DELETE CASCADE,
    scope                   VARCHAR(30) NOT NULL,
    action                  VARCHAR(30) NOT NULL,
    limit_value             INTEGER NOT NULL,
    window                  VARCHAR(20) NOT NULL,
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

COMMIT;
