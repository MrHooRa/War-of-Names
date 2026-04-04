BEGIN;

CREATE TABLE IF NOT EXISTS mutaraha_word_bank (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word VARCHAR(50) NOT NULL,
    category VARCHAR(30) NOT NULL,
    letter_count INTEGER NOT NULL,
    first_letter VARCHAR(1) NOT NULL,
    difficulty VARCHAR(10) NOT NULL DEFAULT 'easy',
    status VARCHAR(10) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mutaraha_word UNIQUE (word, category)
);

CREATE INDEX IF NOT EXISTS idx_mutaraha_word_active ON mutaraha_word_bank (category, status) WHERE status = 'active';

COMMIT;
