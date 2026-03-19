-- ============================================================================
-- War of Names (حرب الأسماء) — Initial Database Schema
-- Migration: 001_initial_schema
-- Database: PostgreSQL 16
-- ============================================================================
-- This schema implements the full domain model derived from:
--   - War of Names - Main - BRD - V1.0
--   - War of Names - Tech BRD - V1.0
--   - War of Names - API&Database BRD - V1.0
-- ============================================================================

BEGIN;

-- ============================================================================
-- 0. EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- ============================================================================
-- 1. ENUM TYPES
-- ============================================================================

-- Identity & Access
CREATE TYPE account_status    AS ENUM ('active', 'suspended', 'disabled', 'archived');

-- Competition Structure
CREATE TYPE competition_status AS ENUM ('draft', 'registration_open', 'registration_closed', 'active', 'paused', 'completed', 'archived');
CREATE TYPE invite_type        AS ENUM ('code', 'link');
CREATE TYPE invite_status      AS ENUM ('active', 'expired', 'disabled', 'exhausted');
CREATE TYPE season_status      AS ENUM ('draft', 'active', 'paused', 'completed', 'archived');
CREATE TYPE cycle_status       AS ENUM ('draft', 'active', 'paused', 'completed', 'archived');

-- Membership & Gameplay
CREATE TYPE membership_status  AS ENUM ('active', 'pending', 'suspended', 'removed', 'archived');
CREATE TYPE protection_type    AS ENUM ('none', 'partial', 'full');

-- Scoring & Ledger
CREATE TYPE ledger_entry_type  AS ENUM (
    'initial_balance', 'question_reward', 'distribution',
    'attack_reward', 'attack_penalty', 'item_purchase',
    'compensation', 'bankruptcy_recovery', 'system_reward',
    'admin_adjustment', 'box_result'
);
CREATE TYPE ledger_direction   AS ENUM ('credit', 'debit');

-- Attack & Protection
CREATE TYPE attack_outcome     AS ENUM ('succeeded', 'failed', 'blocked', 'rejected', 'cancelled');
CREATE TYPE bankruptcy_state   AS ENUM ('active', 'recovering', 'cleared');

-- Store / Items / Rewards
CREATE TYPE item_rarity          AS ENUM ('common', 'rare', 'epic', 'legendary', 'mythic');
CREATE TYPE item_status          AS ENUM ('draft', 'active', 'disabled', 'archived');
CREATE TYPE item_usage_type      AS ENUM ('consumable', 'non_consumable', 'time_limited', 'persistent');
CREATE TYPE item_acquisition_type AS ENUM ('purchase', 'reward', 'distribution', 'admin_grant', 'box');
CREATE TYPE effect_type          AS ENUM (
    'ratio_modifier', 'fixed_bonus', 'loss_reduction', 'action_prevention',
    'state_change', 'grant_item', 'grant_box', 'modify_distribution',
    'allow_alias_change', 'negative_effect', 'time_limited_effect',
    'cycle_effect', 'season_effect'
);
CREATE TYPE listing_status       AS ENUM ('active', 'hidden', 'expired', 'sold_out');
CREATE TYPE owned_item_status    AS ENUM ('available', 'activated', 'consumed', 'expired');
CREATE TYPE reward_type          AS ENUM ('points', 'item', 'box', 'bundle');
CREATE TYPE reward_grant_status  AS ENUM ('pending', 'claimed', 'opened', 'expired');
CREATE TYPE distribution_type    AS ENUM ('points', 'items', 'boxes', 'mixed');
CREATE TYPE distribution_target  AS ENUM ('all_participants', 'specific', 'conditional', 'group');
CREATE TYPE distribution_status  AS ENUM ('draft', 'scheduled', 'executing', 'completed', 'failed', 'cancelled');

-- Questions & Quiz
CREATE TYPE question_type       AS ENUM ('multiple_choice', 'true_false');
CREATE TYPE question_status     AS ENUM ('draft', 'active', 'archived');
CREATE TYPE question_difficulty AS ENUM ('easy', 'medium', 'hard');
CREATE TYPE session_type        AS ENUM ('live', 'timed_window');
CREATE TYPE session_status      AS ENUM ('draft', 'scheduled', 'open', 'closed', 'completed', 'cancelled');
CREATE TYPE answer_eval_status  AS ENUM ('submitted', 'evaluated', 'timed_out');

-- Notifications
CREATE TYPE notification_type AS ENUM (
    'account_created', 'competition_joined', 'registration_opened', 'registration_closed',
    'cycle_started', 'cycle_ended', 'quiz_opened', 'attack_received',
    'attack_success', 'attack_failure', 'protection_activated',
    'bankruptcy_triggered', 'bankruptcy_ended', 'item_purchased',
    'item_received', 'box_received', 'box_opened', 'distribution_received',
    'admin_change', 'admin_alert', 'general'
);
CREATE TYPE notification_priority AS ENUM ('low', 'normal', 'high', 'urgent');

-- Audit
CREATE TYPE audit_actor_type AS ENUM ('system', 'admin', 'participant');

-- Settings
CREATE TYPE setting_scope     AS ENUM ('global', 'competition', 'season', 'cycle');
CREATE TYPE setting_data_type AS ENUM ('integer', 'decimal', 'boolean', 'string', 'json');

-- Media & Import/Export
CREATE TYPE media_storage_type AS ENUM ('local', 'external_url', 'cloud');
CREATE TYPE media_content_type AS ENUM ('image', 'document', 'spreadsheet', 'other');
CREATE TYPE import_status      AS ENUM ('pending', 'validating', 'preview', 'importing', 'completed', 'failed');
CREATE TYPE import_type        AS ENUM ('questions', 'participants', 'other');
CREATE TYPE export_status      AS ENUM ('generating', 'completed', 'failed', 'expired');


-- ============================================================================
-- 2. IDENTITY & ACCESS
-- ============================================================================

-- 2.1 Accounts — Global platform user identity
CREATE TABLE accounts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username       VARCHAR(50)  NOT NULL,
    real_name      VARCHAR(100) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    status         account_status NOT NULL DEFAULT 'active',
    locale         VARCHAR(10)  NOT NULL DEFAULT 'ar',
    last_login_at  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_accounts_username UNIQUE (username)
);

CREATE INDEX idx_accounts_status ON accounts (status);

-- 2.2 Roles — Platform permission model (future-ready for multi-role)
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50)  NOT NULL,
    description TEXT,
    permissions JSONB        NOT NULL DEFAULT '[]',
    is_system   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_roles_name UNIQUE (name)
);

-- 2.3 Account Roles — Junction table
CREATE TABLE account_roles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role_id    UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by UUID REFERENCES accounts(id) ON DELETE SET NULL,

    CONSTRAINT uq_account_roles UNIQUE (account_id, role_id)
);


-- ============================================================================
-- 3. COMPETITION STRUCTURE
-- ============================================================================

-- 3.1 Competitions — Top-level gameplay container
CREATE TABLE competitions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(150) NOT NULL,
    description       TEXT,
    status            competition_status NOT NULL DEFAULT 'draft',
    registration_open BOOLEAN      NOT NULL DEFAULT FALSE,
    visibility        VARCHAR(20)  NOT NULL DEFAULT 'private'
                      CHECK (visibility IN ('public', 'private', 'hidden')),
    created_by        UUID         NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_competitions_status ON competitions (status);
CREATE INDEX idx_competitions_created_by ON competitions (created_by);

-- 3.2 Competition Invites — Join mechanism (codes / links)
CREATE TABLE competition_invites (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id UUID         NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    invite_type    invite_type  NOT NULL,
    code           VARCHAR(50)  NOT NULL,
    status         invite_status NOT NULL DEFAULT 'active',
    max_uses       INT,                          -- NULL = unlimited
    use_count      INT          NOT NULL DEFAULT 0,
    expires_at     TIMESTAMPTZ,
    created_by     UUID         REFERENCES accounts(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_invite_code UNIQUE (code),
    CONSTRAINT chk_invite_uses CHECK (max_uses IS NULL OR use_count <= max_uses)
);

CREATE INDEX idx_invites_competition ON competition_invites (competition_id);
CREATE INDEX idx_invites_code ON competition_invites (code) WHERE status = 'active';

-- 3.3 Seasons — Long-duration structured phase of a competition
CREATE TABLE seasons (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id UUID          NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    name           VARCHAR(100)  NOT NULL,
    order_index    INT           NOT NULL DEFAULT 1,
    status         season_status NOT NULL DEFAULT 'draft',
    starts_at      TIMESTAMPTZ,
    ends_at        TIMESTAMPTZ,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),

    CONSTRAINT chk_season_dates CHECK (ends_at IS NULL OR ends_at > starts_at)
);

CREATE INDEX idx_seasons_competition ON seasons (competition_id);
CREATE INDEX idx_seasons_status ON seasons (competition_id, status);

-- 3.4 Cycles — Shorter operational window within a season
CREATE TABLE cycles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id   UUID         NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    label       VARCHAR(100) NOT NULL,
    order_index INT          NOT NULL DEFAULT 1,
    status      cycle_status NOT NULL DEFAULT 'draft',
    starts_at   TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT chk_cycle_dates CHECK (ends_at IS NULL OR ends_at > starts_at)
);

CREATE INDEX idx_cycles_season ON cycles (season_id);
CREATE INDEX idx_cycles_status ON cycles (season_id, status);


-- ============================================================================
-- 4. MEMBERSHIP & GAMEPLAY IDENTITY
-- ============================================================================

-- 4.1 Memberships — One account participating in one competition
CREATE TABLE memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID              NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    competition_id  UUID              NOT NULL REFERENCES competitions(id) ON DELETE RESTRICT,
    status          membership_status NOT NULL DEFAULT 'pending',

    -- Denormalized fields for query performance (authoritative source: ledger + alias_records)
    current_alias   VARCHAR(100),
    current_balance INT               NOT NULL DEFAULT 0,
    is_bankrupt     BOOLEAN           NOT NULL DEFAULT FALSE,
    protection      protection_type   NOT NULL DEFAULT 'none',

    joined_at       TIMESTAMPTZ       NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ       NOT NULL DEFAULT now(),

    CONSTRAINT uq_membership UNIQUE (account_id, competition_id)
);

CREATE INDEX idx_memberships_account     ON memberships (account_id);
CREATE INDEX idx_memberships_competition ON memberships (competition_id);
CREATE INDEX idx_memberships_status      ON memberships (competition_id, status);

-- 4.2 Alias Records — Alias history per membership
CREATE TABLE alias_records (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id UUID         NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    alias_value   VARCHAR(100) NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    reason        VARCHAR(200),
    season_id     UUID         REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id      UUID         REFERENCES cycles(id) ON DELETE SET NULL,
    starts_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    ends_at       TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_alias_membership ON alias_records (membership_id);
CREATE INDEX idx_alias_active     ON alias_records (membership_id) WHERE is_active = TRUE;


-- ============================================================================
-- 5. SCORING & FINANCIAL TRACE
-- ============================================================================

-- 5.1 Ledger Entries — Authoritative financial trace of all point changes
CREATE TABLE ledger_entries (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id  UUID              NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    competition_id UUID              NOT NULL REFERENCES competitions(id) ON DELETE RESTRICT,
    season_id      UUID              REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id       UUID              REFERENCES cycles(id) ON DELETE SET NULL,
    entry_type     ledger_entry_type NOT NULL,
    amount         INT               NOT NULL,
    direction      ledger_direction  NOT NULL,
    balance_before INT               NOT NULL,
    balance_after  INT               NOT NULL,
    source_type    VARCHAR(50),      -- 'attack', 'quiz', 'purchase', 'distribution', 'admin', 'system'
    source_id      UUID,             -- FK to the triggering record
    reason         TEXT,
    actor_id       UUID              REFERENCES accounts(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ       NOT NULL DEFAULT now(),

    CONSTRAINT chk_ledger_amount CHECK (amount >= 0),
    CONSTRAINT chk_ledger_balance CHECK (
        (direction = 'credit' AND balance_after = balance_before + amount) OR
        (direction = 'debit'  AND balance_after = balance_before - amount)
    )
);

CREATE INDEX idx_ledger_membership  ON ledger_entries (membership_id);
CREATE INDEX idx_ledger_competition ON ledger_entries (competition_id);
CREATE INDEX idx_ledger_cycle       ON ledger_entries (cycle_id);
CREATE INDEX idx_ledger_type        ON ledger_entries (entry_type);
CREATE INDEX idx_ledger_created     ON ledger_entries (created_at);
CREATE INDEX idx_ledger_source      ON ledger_entries (source_type, source_id);


-- ============================================================================
-- 6. ATTACK & PROTECTION ENGINE
-- ============================================================================

-- 6.1 Attack Attempts — One attack action
CREATE TABLE attack_attempts (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attacker_id        UUID           NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    target_id          UUID           NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    competition_id     UUID           NOT NULL REFERENCES competitions(id) ON DELETE RESTRICT,
    season_id          UUID           NOT NULL REFERENCES seasons(id) ON DELETE RESTRICT,
    cycle_id           UUID           NOT NULL REFERENCES cycles(id) ON DELETE RESTRICT,
    guessed_account_id UUID           NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    outcome            attack_outcome NOT NULL,
    reward_amount      INT            NOT NULL DEFAULT 0,
    penalty_amount     INT            NOT NULL DEFAULT 0,
    modifiers_applied  JSONB          NOT NULL DEFAULT '{}',
    blocking_reason    TEXT,
    executed_at        TIMESTAMPTZ    NOT NULL DEFAULT now(),
    created_at         TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT chk_attack_self CHECK (attacker_id <> target_id)
);

CREATE INDEX idx_attacks_attacker    ON attack_attempts (attacker_id);
CREATE INDEX idx_attacks_target      ON attack_attempts (target_id);
CREATE INDEX idx_attacks_cycle       ON attack_attempts (cycle_id);
CREATE INDEX idx_attacks_competition ON attack_attempts (competition_id);
CREATE INDEX idx_attacks_outcome     ON attack_attempts (outcome);
CREATE INDEX idx_attacks_executed    ON attack_attempts (executed_at);

-- 6.2 Protection Records — Protection state changes and history
CREATE TABLE protection_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id   UUID            NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    protection_type protection_type NOT NULL,
    source_type     VARCHAR(50)     NOT NULL,  -- 'attack_triggered', 'item', 'admin', 'system'
    source_id       UUID,
    season_id       UUID            REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id        UUID            REFERENCES cycles(id) ON DELETE SET NULL,
    reason          TEXT,
    starts_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    ends_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_protection_membership ON protection_records (membership_id);
CREATE INDEX idx_protection_active     ON protection_records (membership_id, ends_at)
    WHERE ends_at IS NULL;

-- 6.3 Attack Exposure Tracking — Target saturation per cycle
CREATE TABLE attack_exposure (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id          UUID    NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    season_id              UUID    NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    cycle_id               UUID    NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    successful_attack_count INT    NOT NULL DEFAULT 0,
    current_reward_stage   INT    NOT NULL DEFAULT 0,
    max_attacks_reached    BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_attack_exposure UNIQUE (membership_id, cycle_id),
    CONSTRAINT chk_exposure_count CHECK (successful_attack_count >= 0)
);

-- 6.4 Bankruptcy Records — Bankruptcy activation and recovery
CREATE TABLE bankruptcy_records (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id     UUID             NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    cycle_id          UUID             NOT NULL REFERENCES cycles(id) ON DELETE RESTRICT,
    status            bankruptcy_state NOT NULL DEFAULT 'active',
    trigger_reason    TEXT,
    trigger_source_id UUID,
    triggered_at      TIMESTAMPTZ      NOT NULL DEFAULT now(),
    active_until      TIMESTAMPTZ,
    resolved_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX idx_bankruptcy_membership ON bankruptcy_records (membership_id);
CREATE INDEX idx_bankruptcy_active     ON bankruptcy_records (membership_id, status)
    WHERE status = 'active';


-- ============================================================================
-- 7. STORE / ITEM / REWARD ENGINE
-- ============================================================================

-- 7.1 Item Definitions — Master definition of an item type
CREATE TABLE item_definitions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  VARCHAR(150) NOT NULL,
    description           TEXT,
    rarity                item_rarity          NOT NULL DEFAULT 'common',
    status                item_status          NOT NULL DEFAULT 'draft',
    category              VARCHAR(50),
    acquisition_type      item_acquisition_type NOT NULL DEFAULT 'purchase',
    usage_type            item_usage_type      NOT NULL DEFAULT 'consumable',
    max_uses              INT,                  -- NULL = unlimited for non-consumables
    is_stackable          BOOLEAN              NOT NULL DEFAULT FALSE,
    expires_after_minutes INT,                  -- NULL = no expiry
    scope_competition_id  UUID                 REFERENCES competitions(id) ON DELETE SET NULL,
    visibility            VARCHAR(20)          NOT NULL DEFAULT 'visible'
                          CHECK (visibility IN ('visible', 'hidden', 'admin_only')),
    created_at            TIMESTAMPTZ          NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ          NOT NULL DEFAULT now()
);

CREATE INDEX idx_items_status  ON item_definitions (status);
CREATE INDEX idx_items_rarity  ON item_definitions (rarity);
CREATE INDEX idx_items_scope   ON item_definitions (scope_competition_id);

-- 7.2 Item Effects — Configurable effect logic per item
CREATE TABLE item_effects (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_definition_id UUID        NOT NULL REFERENCES item_definitions(id) ON DELETE CASCADE,
    effect_type        effect_type NOT NULL,
    parameters         JSONB       NOT NULL DEFAULT '{}',
    target_scope       VARCHAR(20) NOT NULL DEFAULT 'self'
                       CHECK (target_scope IN ('self', 'target', 'all')),
    duration_minutes   INT,
    is_stackable       BOOLEAN     NOT NULL DEFAULT FALSE,
    trigger_on         VARCHAR(20) NOT NULL DEFAULT 'activation'
                       CHECK (trigger_on IN ('purchase', 'activation', 'auto')),
    order_index        INT         NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_effects_item ON item_effects (item_definition_id);

-- 7.3 Store Listings — Item availability for purchase
CREATE TABLE store_listings (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_definition_id   UUID           NOT NULL REFERENCES item_definitions(id) ON DELETE CASCADE,
    competition_id       UUID           NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    season_id            UUID           REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id             UUID           REFERENCES cycles(id) ON DELETE SET NULL,
    status               listing_status NOT NULL DEFAULT 'active',
    price                INT            NOT NULL,
    max_per_participant  INT,           -- NULL = unlimited
    total_stock          INT,           -- NULL = unlimited
    sold_count           INT            NOT NULL DEFAULT 0,
    available_from       TIMESTAMPTZ,
    available_until      TIMESTAMPTZ,
    eligibility_rules    JSONB          NOT NULL DEFAULT '{}',
    created_at           TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT chk_listing_price CHECK (price > 0),
    CONSTRAINT chk_listing_stock CHECK (total_stock IS NULL OR sold_count <= total_stock)
);

CREATE INDEX idx_listings_competition ON store_listings (competition_id);
CREATE INDEX idx_listings_item        ON store_listings (item_definition_id);
CREATE INDEX idx_listings_status      ON store_listings (competition_id, status);

-- 7.4 Owned Items — Participant inventory
CREATE TABLE owned_items (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id      UUID              NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    item_definition_id UUID              NOT NULL REFERENCES item_definitions(id) ON DELETE RESTRICT,
    source_type        VARCHAR(30)       NOT NULL,   -- 'purchase', 'reward', 'distribution', 'admin_grant', 'box'
    source_id          UUID,
    quantity           INT               NOT NULL DEFAULT 1,
    uses_remaining     INT,
    status             owned_item_status NOT NULL DEFAULT 'available',
    acquired_at        TIMESTAMPTZ       NOT NULL DEFAULT now(),
    activated_at       TIMESTAMPTZ,
    expires_at         TIMESTAMPTZ,
    consumed_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ       NOT NULL DEFAULT now(),

    CONSTRAINT chk_owned_quantity CHECK (quantity > 0)
);

CREATE INDEX idx_owned_membership ON owned_items (membership_id);
CREATE INDEX idx_owned_item       ON owned_items (item_definition_id);
CREATE INDEX idx_owned_status     ON owned_items (membership_id, status);

-- 7.5 Item Activations — Usage/activation records
CREATE TABLE item_activations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owned_item_id        UUID        NOT NULL REFERENCES owned_items(id) ON DELETE RESTRICT,
    membership_id        UUID        NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    target_membership_id UUID        REFERENCES memberships(id) ON DELETE SET NULL,
    result_state         VARCHAR(20) NOT NULL DEFAULT 'success'
                         CHECK (result_state IN ('success', 'denied', 'expired')),
    effect_summary       JSONB       NOT NULL DEFAULT '{}',
    denial_reason        TEXT,
    activated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_activations_owned ON item_activations (owned_item_id);
CREATE INDEX idx_activations_membership ON item_activations (membership_id);

-- 7.6 Reward Definitions — Reward logic independent of store
CREATE TABLE reward_definitions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(150) NOT NULL,
    reward_type    reward_type  NOT NULL,
    content        JSONB        NOT NULL,   -- what the reward contains
    rules          JSONB        NOT NULL DEFAULT '{}',  -- conditions, probability distributions
    competition_id UUID         REFERENCES competitions(id) ON DELETE SET NULL,
    status         VARCHAR(20)  NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'disabled', 'archived')),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_rewards_competition ON reward_definitions (competition_id);

-- 7.7 Reward Grants — A reward actually granted to a participant
CREATE TABLE reward_grants (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id        UUID                NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    reward_definition_id UUID                REFERENCES reward_definitions(id) ON DELETE SET NULL,
    source_type          VARCHAR(30)         NOT NULL,  -- 'distribution', 'admin', 'achievement', 'system'
    source_id            UUID,
    status               reward_grant_status NOT NULL DEFAULT 'pending',
    granted_at           TIMESTAMPTZ         NOT NULL DEFAULT now(),
    claimed_at           TIMESTAMPTZ,
    expires_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ         NOT NULL DEFAULT now()
);

CREATE INDEX idx_grants_membership ON reward_grants (membership_id);
CREATE INDEX idx_grants_status     ON reward_grants (membership_id, status);

-- 7.8 Box Outcomes — Result of opening a box/reward container
CREATE TABLE box_outcomes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reward_grant_id  UUID        REFERENCES reward_grants(id) ON DELETE SET NULL,
    owned_item_id    UUID        REFERENCES owned_items(id) ON DELETE SET NULL,
    membership_id    UUID        NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    outcome_type     VARCHAR(20) NOT NULL
                     CHECK (outcome_type IN ('points', 'item', 'nothing', 'bundle')),
    outcome_content  JSONB       NOT NULL DEFAULT '{}',
    ledger_entry_id  UUID,       -- FK added after ledger_entries exists (already above)
    granted_item_id  UUID        REFERENCES owned_items(id) ON DELETE SET NULL,
    opened_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_box_membership ON box_outcomes (membership_id);

-- 7.9 Distributions — Scheduled or manual grants
CREATE TABLE distributions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id UUID                NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    season_id      UUID                REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id       UUID                REFERENCES cycles(id) ON DELETE SET NULL,
    name           VARCHAR(150)        NOT NULL,
    dist_type      distribution_type   NOT NULL,
    target_type    distribution_target NOT NULL,
    target_rules   JSONB               NOT NULL DEFAULT '{}',
    content        JSONB               NOT NULL DEFAULT '{}',
    status         distribution_status NOT NULL DEFAULT 'draft',
    scheduled_at   TIMESTAMPTZ,
    executed_at    TIMESTAMPTZ,
    result_summary JSONB,
    created_by     UUID                NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    created_at     TIMESTAMPTZ         NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ         NOT NULL DEFAULT now()
);

CREATE INDEX idx_dist_competition ON distributions (competition_id);
CREATE INDEX idx_dist_status      ON distributions (status);
CREATE INDEX idx_dist_scheduled   ON distributions (scheduled_at) WHERE status = 'scheduled';


-- ============================================================================
-- 8. QUESTION BANK & QUIZ DELIVERY
-- ============================================================================

-- 8.1 Question Groups — Reusable logical collection
CREATE TABLE question_groups (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title          VARCHAR(200) NOT NULL,
    description    TEXT,
    status         question_status NOT NULL DEFAULT 'draft',
    competition_id UUID         REFERENCES competitions(id) ON DELETE SET NULL,   -- NULL = global
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_qgroups_competition ON question_groups (competition_id);

-- 8.2 Questions — Reusable question content
CREATE TABLE questions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id           UUID                NOT NULL REFERENCES question_groups(id) ON DELETE CASCADE,
    question_type      question_type       NOT NULL,
    prompt             TEXT                NOT NULL,
    options            JSONB,              -- array of option objects for MCQ
    correct_answer     JSONB               NOT NULL,
    score_value        INT                 NOT NULL DEFAULT 10,
    difficulty         question_difficulty NOT NULL DEFAULT 'medium',
    category           VARCHAR(100),
    media_id           UUID,               -- FK to media_assets (added below)
    external_media_url TEXT,
    status             question_status     NOT NULL DEFAULT 'active',
    display_order      INT                 NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ         NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ         NOT NULL DEFAULT now(),

    CONSTRAINT chk_question_score CHECK (score_value > 0)
);

CREATE INDEX idx_questions_group  ON questions (group_id);
CREATE INDEX idx_questions_status ON questions (status);
CREATE INDEX idx_questions_type   ON questions (question_type);

-- 8.3 Quiz Sessions — Actual playable scheduled question event
CREATE TABLE quiz_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id          UUID           NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    season_id               UUID           REFERENCES seasons(id) ON DELETE SET NULL,
    cycle_id                UUID           REFERENCES cycles(id) ON DELETE SET NULL,
    session_type            session_type   NOT NULL,
    title                   VARCHAR(200)   NOT NULL,
    status                  session_status NOT NULL DEFAULT 'draft',
    starts_at               TIMESTAMPTZ,
    ends_at                 TIMESTAMPTZ,
    answer_duration_seconds INT,
    source_group_id         UUID           REFERENCES question_groups(id) ON DELETE SET NULL,
    scoring_rules           JSONB          NOT NULL DEFAULT '{}',
    visibility_rules        JSONB          NOT NULL DEFAULT '{}',
    created_by              UUID           NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    created_at              TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT chk_session_dates CHECK (ends_at IS NULL OR ends_at > starts_at)
);

CREATE INDEX idx_sessions_competition ON quiz_sessions (competition_id);
CREATE INDEX idx_sessions_status      ON quiz_sessions (competition_id, status);
CREATE INDEX idx_sessions_starts      ON quiz_sessions (starts_at);

-- 8.4 Session Questions — Questions as delivered within a specific session
CREATE TABLE session_questions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id                  UUID NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_id                 UUID NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
    delivery_order              INT  NOT NULL DEFAULT 0,
    effective_score_value       INT  NOT NULL,
    effective_prompt_snapshot   TEXT NOT NULL,
    effective_options_snapshot  JSONB,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_session_question UNIQUE (session_id, question_id)
);

CREATE INDEX idx_sq_session ON session_questions (session_id);

-- 8.5 Answer Submissions — Participant answers
CREATE TABLE answer_submissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id       UUID              NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    session_id          UUID              NOT NULL REFERENCES quiz_sessions(id) ON DELETE RESTRICT,
    session_question_id UUID              NOT NULL REFERENCES session_questions(id) ON DELETE RESTRICT,
    submitted_answer    JSONB             NOT NULL,
    submitted_at        TIMESTAMPTZ       NOT NULL DEFAULT now(),
    status              answer_eval_status NOT NULL DEFAULT 'submitted',
    is_correct          BOOLEAN,
    points_awarded      INT               NOT NULL DEFAULT 0,
    evaluated_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ       NOT NULL DEFAULT now(),

    CONSTRAINT uq_answer_per_question UNIQUE (membership_id, session_question_id)
);

CREATE INDEX idx_answers_membership ON answer_submissions (membership_id);
CREATE INDEX idx_answers_session    ON answer_submissions (session_id);


-- ============================================================================
-- 9. NOTIFICATIONS
-- ============================================================================

CREATE TABLE notifications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id      UUID                  NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    membership_id     UUID                  REFERENCES memberships(id) ON DELETE SET NULL,
    notification_type notification_type     NOT NULL,
    title             VARCHAR(200)          NOT NULL,
    message           TEXT                  NOT NULL,
    is_read           BOOLEAN               NOT NULL DEFAULT FALSE,
    priority          notification_priority NOT NULL DEFAULT 'normal',
    reference_type    VARCHAR(50),
    reference_id      UUID,
    deep_link         VARCHAR(500),
    created_at        TIMESTAMPTZ           NOT NULL DEFAULT now(),
    read_at           TIMESTAMPTZ
);

CREATE INDEX idx_notif_recipient   ON notifications (recipient_id);
CREATE INDEX idx_notif_unread      ON notifications (recipient_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notif_membership  ON notifications (membership_id);
CREATE INDEX idx_notif_created     ON notifications (created_at);


-- ============================================================================
-- 10. AUDIT & OPERATIONAL LOGS
-- ============================================================================

CREATE TABLE audit_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id      UUID             REFERENCES accounts(id) ON DELETE SET NULL,
    actor_type    audit_actor_type NOT NULL,
    subject_type  VARCHAR(50)      NOT NULL,   -- e.g. 'membership', 'competition', 'setting'
    subject_id    UUID,
    event_type    VARCHAR(100)     NOT NULL,   -- e.g. 'membership.suspended', 'attack.executed'
    summary       TEXT             NOT NULL,
    reason        TEXT,
    before_state  JSONB,
    after_state   JSONB,
    related_type  VARCHAR(50),
    related_id    UUID,
    ip_address    INET,
    created_at    TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_actor      ON audit_events (actor_id);
CREATE INDEX idx_audit_subject    ON audit_events (subject_type, subject_id);
CREATE INDEX idx_audit_event_type ON audit_events (event_type);
CREATE INDEX idx_audit_created    ON audit_events (created_at);


-- ============================================================================
-- 11. SETTINGS & CONFIGURATION ENGINE
-- ============================================================================

-- 11.1 Setting Definitions — Configurable option metadata
CREATE TABLE setting_definitions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key              VARCHAR(100)    NOT NULL,
    category         VARCHAR(50)     NOT NULL,
    data_type        setting_data_type NOT NULL,
    default_value    JSONB           NOT NULL,
    allowed_values   JSONB,          -- range or options
    description      TEXT,
    is_per_competition BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_setting_key UNIQUE (key)
);

CREATE INDEX idx_settings_category ON setting_definitions (category);

-- 11.2 Setting Values — Actual value at a specific scope
CREATE TABLE setting_values (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_definition_id UUID          NOT NULL REFERENCES setting_definitions(id) ON DELETE CASCADE,
    scope                 setting_scope NOT NULL,
    scope_id              UUID,         -- NULL for 'global' scope; competition/season/cycle ID otherwise
    value                 JSONB         NOT NULL,
    updated_by            UUID          REFERENCES accounts(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),

    CONSTRAINT uq_setting_value UNIQUE (setting_definition_id, scope, scope_id)
);

CREATE INDEX idx_sval_definition ON setting_values (setting_definition_id);
CREATE INDEX idx_sval_scope      ON setting_values (scope, scope_id);


-- ============================================================================
-- 12. MEDIA & IMPORT/EXPORT
-- ============================================================================

-- 12.1 Media Assets — Uploaded or externally linked media
CREATE TABLE media_assets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_type      media_storage_type NOT NULL,
    storage_path      TEXT,
    external_url      TEXT,
    media_type        media_content_type NOT NULL,
    original_filename VARCHAR(255),
    file_size_bytes   BIGINT,
    mime_type         VARCHAR(100),
    uploaded_by       UUID           REFERENCES accounts(id) ON DELETE SET NULL,
    status            VARCHAR(20)    NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active', 'archived', 'deleted')),
    created_at        TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- Now add the FK from questions.media_id → media_assets
ALTER TABLE questions
    ADD CONSTRAINT fk_questions_media
    FOREIGN KEY (media_id) REFERENCES media_assets(id) ON DELETE SET NULL;

-- 12.2 Import Jobs — Bulk import operations
CREATE TABLE import_jobs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_type        import_type   NOT NULL,
    file_id            UUID          REFERENCES media_assets(id) ON DELETE SET NULL,
    actor_id           UUID          NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    status             import_status NOT NULL DEFAULT 'pending',
    validation_summary JSONB,
    result_summary     JSONB,
    target_group_id    UUID          REFERENCES question_groups(id) ON DELETE SET NULL,
    started_at         TIMESTAMPTZ,
    completed_at       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_imports_actor  ON import_jobs (actor_id);
CREATE INDEX idx_imports_status ON import_jobs (status);

-- 12.3 Export Artifacts — Generated exports
CREATE TABLE export_artifacts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    export_type  VARCHAR(50) NOT NULL,
    source_scope VARCHAR(50),
    source_id    UUID,
    file_id      UUID          REFERENCES media_assets(id) ON DELETE SET NULL,
    generated_by UUID          NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    status       export_status NOT NULL DEFAULT 'generating',
    generated_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_exports_status ON export_artifacts (status);


-- ============================================================================
-- 13. TEMPORARY: Game Info (for current frontend dashboard)
-- ============================================================================
-- This table supports the existing frontend placeholder and will be replaced
-- by competition/season context endpoints once those modules are built.

CREATE TABLE game_info (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(100) NOT NULL,
    subtitle       VARCHAR(200),
    current_season VARCHAR(100),
    status         VARCHAR(20)  NOT NULL DEFAULT 'active',
    announcement   TEXT
);


-- ============================================================================
-- 14. INITIAL SEED DATA
-- ============================================================================

-- 14.1 Default roles
INSERT INTO roles (name, description, permissions, is_system) VALUES
    ('admin',       'مشرف النظام — صلاحيات كاملة',  '["*"]',                                       TRUE),
    ('participant', 'متسابق — صلاحيات اللاعب الأساسية', '["competition.join","profile.edit","game.play"]', TRUE);

-- 14.2 Default setting definitions (core game settings)
INSERT INTO setting_definitions (key, category, data_type, default_value, description, is_per_competition) VALUES
    -- Attack settings
    ('attack.base_reward_ratio',        'attack',     'decimal', '0.10',  'نسبة المكافأة الأساسية من رصيد الهدف عند الهجوم الناجح', TRUE),
    ('attack.failed_penalty',           'attack',     'integer', '50',    'النقاط المخصومة عند فشل الهجوم',                        TRUE),
    ('attack.max_successful_per_target','attack',     'integer', '3',     'الحد الأقصى للهجمات الناجحة على نفس الهدف في الدورة',    TRUE),
    ('attack.reward_diminish_rate',     'attack',     'decimal', '0.50',  'نسبة تناقص مكافأة الهجمات المتتالية على نفس الهدف',      TRUE),
    ('attack.daily_limit',             'attack',     'integer', '5',     'الحد الأقصى للهجمات اليومية لكل لاعب',                   TRUE),

    -- Protection settings
    ('protection.partial_reduction',    'protection', 'decimal', '0.50',  'نسبة تقليل الضرر عند الحماية الجزئية',                   TRUE),
    ('protection.full_trigger_count',   'protection', 'integer', '3',     'عدد الهجمات الناجحة التي تفعّل الحماية الكاملة',          TRUE),
    ('protection.full_duration_hours',  'protection', 'integer', '24',    'مدة الحماية الكاملة بالساعات',                            TRUE),

    -- Bankruptcy settings
    ('bankruptcy.threshold',            'bankruptcy', 'integer', '0',     'الحد الأدنى للرصيد الذي يُفعّل الإفلاس',                 TRUE),
    ('bankruptcy.recovery_points',      'bankruptcy', 'integer', '100',   'نقاط التعافي عند بداية الدورة الجديدة',                   TRUE),

    -- Scoring settings
    ('scoring.initial_balance',         'scoring',    'integer', '1000',  'الرصيد الابتدائي للمتسابق عند الانضمام',                  TRUE),

    -- Cycle settings
    ('cycle.default_duration_days',     'cycle',      'integer', '7',     'المدة الافتراضية للدورة بالأيام',                         TRUE),
    ('cycle.auto_transition',           'cycle',      'boolean', 'false', 'الانتقال التلقائي بين الدورات',                           TRUE),

    -- Quiz settings
    ('quiz.default_answer_duration',    'quiz',       'integer', '30',    'المدة الافتراضية للإجابة بالثواني',                       TRUE),

    -- Store settings
    ('store.enabled',                   'store',      'boolean', 'true',  'تفعيل المتجر',                                           TRUE);

-- 14.3 Seed the game_info for existing frontend
INSERT INTO game_info (title, subtitle, current_season, status, announcement) VALUES
    ('حرب الأسماء', 'من سيكشف الأقنعة أولاً؟', 'الموسم الأول', 'active', 'مرحباً بكم في حرب الأسماء! الموسم الأول يبدأ قريباً');


COMMIT;
