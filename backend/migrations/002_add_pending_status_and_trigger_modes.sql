-- ============================================================================
-- War of Names — Migration 002
-- Add 'pending' / 'PENDING' to owned_item_status enum
-- Expand trigger_on CHECK constraint for action-triggered effects (if exists)
-- ============================================================================

-- 1. Add 'PENDING' to the owned_item_status enum type.
--    create_all uses uppercase member NAMES as PostgreSQL labels.
--    The initial SQL migration uses lowercase VALUES.
--    We add both so this migration works regardless of DB origin.
ALTER TYPE owned_item_status ADD VALUE IF NOT EXISTS 'PENDING';
ALTER TYPE owned_item_status ADD VALUE IF NOT EXISTS 'pending';

-- 2. Drop the old CHECK constraint on item_effects.trigger_on if it exists
--    (only present if DB was created from 001_initial_schema.sql, not create_all).
ALTER TABLE item_effects DROP CONSTRAINT IF EXISTS item_effects_trigger_on_check;
