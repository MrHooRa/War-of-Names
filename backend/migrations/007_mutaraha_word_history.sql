BEGIN;

CREATE TABLE IF NOT EXISTS mutaraha_player_word_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES minigame_sessions(id) ON DELETE CASCADE,
    membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES mutaraha_word_bank(id) ON DELETE CASCADE,
    word VARCHAR(50) NOT NULL,
    category VARCHAR(30) NOT NULL,
    used_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mutaraha_word_history UNIQUE (session_id, membership_id, word_id)
);

CREATE INDEX IF NOT EXISTS idx_mutaraha_word_history_membership_used_at
    ON mutaraha_player_word_history (membership_id, used_at DESC);

CREATE INDEX IF NOT EXISTS idx_mutaraha_word_history_session
    ON mutaraha_player_word_history (session_id);

COMMIT;
