# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**War of Names (حرب الأسماء)** — A seasonal alias-based competition web platform where participants join closed competitions under aliases, attack each other by guessing real identities, answer quiz questions, earn points, and use items from an in-game store. An admin manages everything via a control panel. All scoring and game logic is fully automated.

## Tech Stack

- **Frontend:** React + Vite
- **Backend:** Python API
- **Database:** PostgreSQL
- **Deployment:** Docker-based
- **Language:** Arabic-first UI (RTL), mobile-responsive

## Architecture Principles

- Frontend and backend are fully separated; frontend handles display/interaction/basic validation only.
- All authoritative business logic runs exclusively on the backend.
- The database is the single source of truth for all state.
- Every financial/point operation goes through a Ledger. Every admin/state mutation goes through an Audit Trail.
- All configurable rules must be manageable via structured settings, not hardcoded.
- Engines/modules must be built as reusable frameworks, not one-off solutions.
- No duplicated logic across layers. No direct state updates bypassing the business layer.

## System Modules

The platform is composed of these interconnected engines:

1. **Authentication & Accounts** — platform-level identity, registration, login
2. **Competitions & Memberships** — creating/joining competitions via invite codes, membership management
3. **Seasons & Cycles** — temporal structuring of competitions into seasons and cycles
4. **Alias & Identity Layer** — each participant has a real name + alias within a competition; alias visibility rules are central to gameplay
5. **Scoring & Ledger Engine** — all point changes flow through a double-entry-style ledger; no direct balance mutations
6. **Attack Engine** — participants guess another player's real identity behind their alias; success/failure has point consequences with modifiers
7. **Protection & Bankruptcy State Engine** — shields, bankruptcy thresholds, state transitions
8. **Store / Item / Reward Engine** — purchasable and distributable items with effects on gameplay
9. **Distribution Engine** — scheduled or event-driven point/item distributions
10. **Question Bank & Quiz Session Engine** — timed quiz sessions as a scoring mechanism
11. **Notification Engine** — in-app notifications for game events
12. **Admin Control Panel** — full management of all modules
13. **Audit & Operational Logs** — every significant event is tracked
14. **Settings & Configuration Engine** — runtime-configurable rules per competition

## User Roles

- **Admin (مشرف):** Full access — creates competitions, manages all modules, views all data and logs
- **Participant (متسابق):** Joins competitions, interacts via alias, attacks, answers questions, uses store items, sees own data
- **Visitor:** Not in MVP scope

## API Design Contracts

- Responses use a consistent envelope: success flag, data payload, user-safe message, error codes, pagination
- Permission boundaries per endpoint: public, authenticated, competition participant, admin
- State-changing operations must return: outcome status, user-visible effect, state references for frontend refresh
- Frontend must never compute authoritative business outcomes

## Current Project State

This project is in **pre-development / design phase**. No React app or Python backend exists yet. The repository currently contains:
- **HTML prototypes** in `/Front-end/War of Names - Main Template - 1.0/` — static screens (numbered 02–12) using Tailwind CDN demonstrating navigation, player dashboard, lobby, battle results, etc.
- **BRD documents** in `/docs/` — the authoritative specs for all implementation work

When building the React app, translate the patterns from the HTML prototypes into proper React components; do not carry over the CDN-based Tailwind approach.

## Established Design System

Extracted from the HTML prototypes — these tokens must be encoded into the Tailwind config of the React app:

**Brand Colors:**
```
brand-teal:       #0B8A8D  (primary action)
brand-teal-hover: #067a79
brand-teal-light: #17a2b8
brand-orange:     #D84315  (danger / attack)
brand-slate:      #64748B
brand-dark:       #1F2937
brand-light-bg:   #F8F9FA  (light mode background)
brand-dark-bg:    #111827  (dark mode background)
brand-card-dark:  #1F2937
brand-success:    #10B981
brand-danger:     #EF4444
```

**Typography:**
- `font-display` / `font-body`: Cairo (weights 400, 600, 700, 800, 900)
- `font-heading`: Changa (weights 400, 600, 700, 800)

**Icons:** Iconify (`iconify-icon` web component, v1.0.7)

**RTL:** All screens use `<html lang="ar" dir="rtl">`. Every layout decision must account for RTL direction.

**Page Transitions:** The prototypes use the CSS View Transitions API (`view-transition-name` on nav/brand/content regions) for navigation animations. Apply the same pattern in the React app via the View Transitions API or a compatible library.

## Key BRD Documents

All specifications live in `/docs/`:
- `War of Names - Main - BRD - V1.0.md` — Full business requirements, game mechanics, and module descriptions
- `War of Names - Tech BRD - V1.0.md` — Technical/functional spec: modules, user flows, screens, permissions, execution phases
- `War of Names - API&Database BRD - V1.0.md` — API contract structure, database schema concepts, payload expectations
- `Game Identity + Product Visual Direction + UX - BRD - V1.0.md` — Visual identity, design language, UX/UI foundations, RTL considerations

## Design Context

The complete design system was extracted from the hand-crafted HTML prototypes in `/Front-end/War of Names - Main Template - 1.0/`. These prototypes are the **authoritative source of truth** for all visual and interaction design — never modify them.

**Full design documentation:**
- `.impeccable.md` (project root) — Design context for Impeccable skills: users, brand personality, aesthetic direction, design tokens, layout, principles
- `docs/Game Identity + Product Visual Direction + UX - BRD - V1.0.md` — Comprehensive design BRD: every color, component, animation, layout pattern, and page template documented from the prototypes

**Key design decisions:**
- **Dual-tone color strategy:** brand-teal (#0B8A8D) is primary in light mode; brand-slate (#64748B) takes over as primary accent in dark mode
- **Dark mode** uses `darkMode: 'class'` with localStorage persistence and a toggle button
- **7 page templates** documented: Registration, Join Competition, Player Dashboard, Leaderboard, Store, Quiz Session, Battle Result — plus the unique Lobby
- **Lobby (09)** is a fully dark-only immersive screen with its own color palette, hexagon SVG backgrounds, rotating shapes, magnetic hover JS, and spring easing curves — no standard header/footer/nav
- **Rarity system:** 5 tiers (Common #94A3B8, Rare #0D47A1, Epic #64748B, Legendary #D84315, Mythic #7C3AED) with escalating CSS animations
- **Shape language:** Hexagons as signature motif, rounded pills for controls, chamfered clip-path cards for special elements
- **Mobile-first** with fixed bottom nav featuring an elevated FAB attack button in the center
