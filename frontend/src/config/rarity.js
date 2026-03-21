/**
 * Rarity System — Single source of truth for the entire app.
 *
 * Official ladder (weakest → strongest):
 *   1. common  (عادي)    — gray/slate
 *   2. rare    (نادر)    — blue
 *   3. epic    (ملحمي)   — purple
 *   4. legendary (أسطوري) — gold/amber
 *   5. mythic  (فريد)    — golden-red / crimson-gold
 *
 * Every surface (store, inventory, dashboard, admin) imports from here.
 */

// ── Player-facing config (rich visuals) ─────────────────────────────────

export const RARITY_CONFIG = {
  common: {
    label: 'عادي',
    order: 1,
    // Badge
    badge:  'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
    // Card structure
    border: 'border-gray-200 dark:border-gray-700',
    ring:   '',
    glow:   '',
    // Accents
    accent: 'text-gray-400 dark:text-gray-500',
    dot:    '#94A3B8',
  },
  rare: {
    label: 'نادر',
    order: 2,
    badge:  'bg-blue-600 dark:bg-blue-700 text-white',
    border: 'border-blue-300 dark:border-blue-600/40',
    ring:   'ring-1 ring-blue-200/50 dark:ring-blue-600/20',
    glow:   'shadow-[0_0_20px_rgba(37,99,235,0.08)] dark:shadow-[0_0_20px_rgba(37,99,235,0.12)]',
    accent: 'text-blue-500 dark:text-blue-400',
    dot:    '#2563EB',
  },
  epic: {
    label: 'ملحمي',
    order: 3,
    badge:  'bg-purple-600 dark:bg-purple-700 text-white',
    border: 'border-purple-300/50 dark:border-purple-500/40',
    ring:   'ring-1 ring-purple-200/40 dark:ring-purple-500/20',
    glow:   'shadow-[0_0_24px_rgba(147,51,234,0.08)] dark:shadow-[0_0_24px_rgba(147,51,234,0.14)]',
    accent: 'text-purple-500 dark:text-purple-400',
    dot:    '#9333EA',
  },
  legendary: {
    label: 'أسطوري',
    order: 4,
    badge:  'bg-amber-500 dark:bg-amber-600 text-white',
    border: 'border-amber-400/40 dark:border-amber-500/40',
    ring:   'ring-1 ring-amber-300/30 dark:ring-amber-500/20',
    glow:   'shadow-[0_0_28px_rgba(245,158,11,0.1)] dark:shadow-[0_0_28px_rgba(245,158,11,0.16)]',
    accent: 'text-amber-500 dark:text-amber-400',
    dot:    '#F59E0B',
  },
  mythic: {
    label: 'فريد',
    order: 5,
    badge:  'bg-gradient-to-r from-red-600 to-amber-500 text-white',
    border: 'border-red-400/40 dark:border-red-500/40',
    ring:   'ring-1 ring-red-300/30 dark:ring-red-500/25',
    glow:   'shadow-[0_0_32px_rgba(220,38,38,0.1)] dark:shadow-[0_0_32px_rgba(220,38,38,0.18)]',
    accent: 'text-red-500 dark:text-red-400',
    dot:    '#DC2626',
  },
}

// ── Admin-facing config (calmer, operational) ───────────────────────────

export const RARITY_ADMIN = {
  common: {
    border:  'border-gray-300 dark:border-gray-600',
    badge:   'bg-gray-100 dark:bg-gray-800 text-gray-500',
  },
  rare: {
    border:  'border-blue-400 dark:border-blue-500/50',
    badge:   'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
  },
  epic: {
    border:  'border-purple-400 dark:border-purple-500/50',
    badge:   'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
  },
  legendary: {
    border:  'border-amber-400 dark:border-amber-500/50',
    badge:   'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400',
  },
  mythic: {
    border:  'border-red-400 dark:border-red-500/50',
    badge:   'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400',
  },
}

// ── Shared constants ────────────────────────────────────────────────────

export const RARITY_LABELS = {
  common: 'عادي', rare: 'نادر', epic: 'ملحمي', legendary: 'أسطوري', mythic: 'فريد',
}

export const RARITY_DOT_COLORS = {
  common: RARITY_CONFIG.common.dot,
  rare:   RARITY_CONFIG.rare.dot,
  epic:   RARITY_CONFIG.epic.dot,
  legendary: RARITY_CONFIG.legendary.dot,
  mythic: RARITY_CONFIG.mythic.dot,
}

export const RARITY_OPTIONS = [
  { value: 'common',    label: 'عادي' },
  { value: 'rare',      label: 'نادر' },
  { value: 'epic',      label: 'ملحمي' },
  { value: 'legendary', label: 'أسطوري' },
  { value: 'mythic',    label: 'فريد' },
]

export const CATEGORY_ICONS = {
  weapon:  'mdi:bomb',
  defense: 'mdi:shield-outline',
  special: 'mdi:magic-staff',
}

export const CATEGORY_COLORS = {
  weapon:  'text-brand-orange',
  defense: 'text-blue-500 dark:text-blue-400',
  special: 'text-brand-teal dark:text-brand-slate',
}

export const CATEGORY_GLOW = {
  weapon:  'bg-brand-orange',
  defense: 'bg-blue-500',
  special: 'bg-brand-teal',
}
