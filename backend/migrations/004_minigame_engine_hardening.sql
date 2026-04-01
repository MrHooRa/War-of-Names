-- ============================================================
-- Migration 004: Minigame engine hardening
-- Adds missing integrity guard discovered in Sprint 0 review
-- ============================================================

BEGIN;

ALTER TABLE minigame_sessions
    ADD CONSTRAINT chk_mg_distinct_players
    CHECK (
        player_2_membership_id IS NULL
        OR player_1_membership_id <> player_2_membership_id
    );

COMMIT;
