BEGIN;

-- ── New participants table ──
CREATE TABLE IF NOT EXISTS minigame_session_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE RESTRICT,
    slot_index INTEGER NOT NULL,
    reconnect_token VARCHAR(128),
    joined_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mg_participant UNIQUE (session_id, membership_id),
    CONSTRAINT uq_mg_participant_slot UNIQUE (session_id, slot_index),
    CONSTRAINT chk_mg_slot_range CHECK (slot_index >= 0 AND slot_index <= 7)
);

CREATE INDEX IF NOT EXISTS idx_mg_participants_session ON minigame_session_participants (session_id);
CREATE INDEX IF NOT EXISTS idx_mg_participants_membership ON minigame_session_participants (membership_id);

-- ── Migrate existing sessions: copy player_1/player_2 to participants ──
INSERT INTO minigame_session_participants (session_id, membership_id, slot_index, reconnect_token)
SELECT id, player_1_membership_id, 0, reconnect_token_p1
FROM minigame_sessions
WHERE player_1_membership_id IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO minigame_session_participants (session_id, membership_id, slot_index, reconnect_token)
SELECT id, player_2_membership_id, 1, reconnect_token_p2
FROM minigame_sessions
WHERE player_2_membership_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- ── Add new columns to minigame_sessions ──
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS num_players INTEGER NOT NULL DEFAULT 2;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS min_players INTEGER NOT NULL DEFAULT 2;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS max_players INTEGER NOT NULL DEFAULT 2;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS current_turn_index INTEGER;
ALTER TABLE minigame_sessions ADD COLUMN IF NOT EXISTS winner_slot_index INTEGER;

-- ── Migrate current_turn enum to index ──
UPDATE minigame_sessions SET current_turn_index = 0 WHERE current_turn = 'player_1';
UPDATE minigame_sessions SET current_turn_index = 1 WHERE current_turn = 'player_2';

-- ── Migrate winner to slot index ──
UPDATE minigame_sessions SET winner_slot_index = 0
WHERE winner_membership_id IS NOT NULL
  AND winner_membership_id = player_1_membership_id;
UPDATE minigame_sessions SET winner_slot_index = 1
WHERE winner_membership_id IS NOT NULL
  AND winner_membership_id = player_2_membership_id;

-- ── Update settlement table ──
ALTER TABLE minigame_session_settlements ADD COLUMN IF NOT EXISTS participant_results JSONB;
ALTER TABLE minigame_session_settlements ADD COLUMN IF NOT EXISTS total_pool INTEGER NOT NULL DEFAULT 0;

-- ── Migrate existing settlements to new format ──
UPDATE minigame_session_settlements SET participant_results = jsonb_build_array(
    jsonb_build_object('membership_id', winner_membership_id::text, 'rank', 1, 'payout', winner_payout),
    jsonb_build_object('membership_id', loser_membership_id::text, 'rank', 2, 'payout', 0)
)
WHERE winner_membership_id IS NOT NULL AND participant_results IS NULL;

UPDATE minigame_session_settlements SET total_pool = winner_payout + loser_penalty
WHERE total_pool = 0 AND winner_payout > 0;

-- ── Add num_players constraint ──
ALTER TABLE minigame_sessions DROP CONSTRAINT IF EXISTS chk_mg_num_players;
ALTER TABLE minigame_sessions ADD CONSTRAINT chk_mg_num_players CHECK (num_players >= 1 AND num_players <= 8);

-- ── Drop old columns (after data migration) ──
ALTER TABLE minigame_sessions DROP CONSTRAINT IF EXISTS chk_mg_distinct_players;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS player_1_membership_id;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS player_2_membership_id;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS reconnect_token_p1;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS reconnect_token_p2;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS current_turn;
ALTER TABLE minigame_sessions DROP COLUMN IF EXISTS winner_membership_id;

ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS winner_membership_id;
ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS loser_membership_id;
ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS winner_payout;
ALTER TABLE minigame_session_settlements DROP COLUMN IF EXISTS loser_penalty;

-- ── Drop unused enum type ──
DROP TYPE IF EXISTS minigame_turn_side;

COMMIT;
