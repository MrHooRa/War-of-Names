# Phase 4: In-Game Promotion Engine + Sponsor System — BRD

**Version:** 1.0
**Date:** 2026-03-29
**Status:** Design

---

## 1. Executive Summary

Build an internal LiveOps promotion engine and brand sponsorship system for War of Names. **Zero third-party ads.** The platform promotes its OWN content (store items, events, seasons, player-generated moments) and offers premium brand sponsorship experiences with cinematic visual treatment.

**Three pillars:**
1. **Promotion Engine** — Admin-created internal banners promoting game content
2. **Sponsor System** — Brand sponsorship management with cinematic competition experiences
3. **Player Controls** — Full user control to toggle all/specific promotions

**Revenue model:** Sponsorship deals (SAR 500-5,000+/month per sponsor), not ad impressions. Google Analytics is used purely for product improvement — no ad monetization.

---

## 2. Promotion Engine

### 2.1 What It Is

An internal content promotion system — like Fortnite's item shop announcements or Clash Royale's event banners. Admin creates banners that appear contextually throughout the game. All content is internal to the platform.

**Example promotions:**
- "يا عياااال ترا المتجر في اغراض جديدة خراافية!" → CTA: navigate to store
- "اللقب سمبوسة يقول لكم اتحداكم تعرفون من انا هههه" → CTA: navigate to leaderboard
- "الموسم بيخلص بعد 3 أيام، ألحقوا!" → CTA: navigate to dashboard
- "هذا العنصر درع الحماية عليه خصم 30% اضغط للشراء!" → CTA: deeplink to store item
- "الموسم الثاني برعاية STC — انضم الآن!" → Sponsored banner

### 2.2 Promotion Placements

| Placement | Location | Max Slots | Layout |
|-----------|----------|-----------|--------|
| `banner_top` | Top of dashboard, below header | 1 | Compact horizontal strip |
| `banner_bottom` | Bottom of leaderboard page | 1 | Standard card |
| `news_feed` | Dedicated promotions tab/section in dashboard | 3 | Stacked cards |
| `splash` | Full-screen on login (once per session) | 1 | Full-screen hero |
| `interstitial` | Between screens (post-battle, post-quiz) | 1 | Centered modal card |
| `floating_fab` | Small floating badge near bottom nav | 1 | Mini pill/badge |
| `store_featured` | Featured slot at top of store page | 1 | Hero card with media |

**Hard NO placements (never):**
- During quiz (timed!)
- During attack flow
- Lobby / immersive screens
- Inside modals or dialogs
- Notification panel
- Admin/owner panels

### 2.3 Promotion Data Model

**Extends the existing `Announcement` model** — the current model already has title, subtitle, body, style, scope, CTA, timing, and dismissibility. The promotion engine adds: placement, priority, media, interaction tracking, sponsor linkage, and user-level controls.

#### `promotions` table (new — separate from announcements)

```
id                  UUID PRIMARY KEY
title               VARCHAR(200)         — "أغراض جديدة في المتجر!"
subtitle            VARCHAR(300)         — optional secondary text
body                TEXT                 — optional rich body text

-- Media
media_url           VARCHAR(500)         — banner image URL (nullable)
media_type          ENUM(image, lottie, none)  — default: none

-- Display
placement           ENUM(banner_top, banner_bottom, news_feed, splash,
                         interstitial, floating_fab, store_featured)
layout              ENUM(compact, standard, hero, fullscreen)
style               ENUM(info, success, warning, danger, celebration, seasonal, sponsor)
priority            INTEGER DEFAULT 50   — 1=highest, 100=lowest

-- Scope (same pattern as existing announcements)
scope               ENUM(global, competition, season, cycle)
competition_id      UUID FK → competitions (nullable)
season_id           UUID FK → seasons (nullable)
cycle_id            UUID FK → cycles (nullable)

-- CTA
cta_label           VARCHAR(100)         — "اذهب للمتجر"
cta_url             VARCHAR(500)         — "/store" or "/store/item/{id}"
cta_type            ENUM(navigate, deeplink, dismiss)  — default: navigate

-- Behavior
is_active           BOOLEAN DEFAULT true
is_dismissible      BOOLEAN DEFAULT true
max_impressions     INTEGER              — per user, NULL = unlimited
cooldown_hours      INTEGER DEFAULT 0    — hours before re-showing after dismiss

-- Timing
starts_at           TIMESTAMPTZ          — nullable = immediate
ends_at             TIMESTAMPTZ          — nullable = indefinite

-- Sponsor linkage
sponsor_id          UUID FK → sponsors (nullable)
is_sponsored        BOOLEAN DEFAULT false

-- Metadata
created_by          UUID FK → accounts
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

#### `promotion_interactions` table (new)

Tracks every impression, click, and dismiss — feeds analytics and enforces `max_impressions`/`cooldown_hours`.

```
id                  UUID PRIMARY KEY
promotion_id        UUID FK → promotions
account_id          UUID FK → accounts
interaction_type    ENUM(impression, click, dismiss)
context             JSONB                — {"page": "dashboard", "placement": "banner_top"}
created_at          TIMESTAMPTZ
```

**Dedup logic:** The API endpoint checks if an identical `(promotion_id, account_id, interaction_type)` row exists within the last 60 seconds before inserting. This is an application-level check, not a DB constraint — allows the same user to see the same promotion across multiple sessions.

#### `promotion_dismissals` table (new)

Lightweight table to track which promotions a user has dismissed — used by the player-facing API to filter out dismissed promotions.

```
id                  UUID PRIMARY KEY
promotion_id        UUID FK → promotions
account_id          UUID FK → accounts
dismissed_at        TIMESTAMPTZ
```

**Unique constraint:** `(promotion_id, account_id)`

### 2.4 Priority Resolution

When multiple promotions target the same placement, the API returns the highest-priority one:

```
1. Filter: is_active=true, within starts_at/ends_at window, scope matches
2. Exclude: dismissed by this user (unless cooldown_hours elapsed)
3. Exclude: max_impressions exceeded for this user
4. Sort: is_sponsored DESC, priority ASC, created_at DESC
5. Return: top N based on placement capacity (1 for most, 3 for news_feed)
```

### 2.5 Promotion API Endpoints

#### Player-facing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/promotions` | Active promotions for current user (filtered by scope, timing, dismissals, limits) |
| POST | `/api/promotions/{id}/impression` | Record impression (idempotent per minute) |
| POST | `/api/promotions/{id}/click` | Record click interaction |
| POST | `/api/promotions/{id}/dismiss` | Dismiss promotion for this user |

**GET `/api/promotions` response shape:**

```json
{
  "success": true,
  "data": {
    "banner_top": { ... } | null,
    "banner_bottom": { ... } | null,
    "news_feed": [ ... ],
    "splash": { ... } | null,
    "interstitial": { ... } | null,
    "floating_fab": { ... } | null,
    "store_featured": { ... } | null
  }
}
```

Returns promotions **grouped by placement** — the frontend simply renders whatever is present for each slot. If null, the slot is empty (no wasted space).

#### Admin CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/promotions` | List all promotions (with interaction stats) |
| POST | `/api/admin/promotions` | Create promotion |
| PATCH | `/api/admin/promotions/{id}` | Update promotion |
| DELETE | `/api/admin/promotions/{id}` | Delete promotion |
| GET | `/api/admin/promotions/{id}/stats` | Detailed interaction stats (impressions, clicks, CTR, dismissals) |

### 2.6 Player Controls

Players can control which promotions they see. This is stored per-account in a `promotion_preferences` setting (JSONB in user profile or a dedicated table).

**Options available to players (in account settings):**

| Toggle | Effect |
|--------|--------|
| "إيقاف جميع العروض الترويجية" | Hides ALL promotions across all placements |
| "إيقاف العروض المنبثقة فقط" | Hides splash + interstitial only (least intrusive toggle) |
| "إيقاف المحتوى المدعوم فقط" | Hides only sponsor-tagged promotions |

**Implementation:** A `promotion_preferences` JSONB column on the `accounts` table:

```json
{
  "all_disabled": false,
  "popups_disabled": false,
  "sponsored_disabled": false
}
```

Default: all false (promotions enabled). The player-facing API respects these preferences when resolving promotions.

---

## 3. Sponsor System

### 3.1 What It Is

Brand sponsors pay to be associated with competitions, seasons, or events. Their branding is woven into the game experience — not slapped on as a banner ad. The goal is premium integration that makes the game feel MORE polished, not cheaper.

### 3.2 Sponsor Data Model

#### `sponsors` table (new)

```
id                  UUID PRIMARY KEY
name                VARCHAR(200)         — "STC" or "موبايلي"
name_ar             VARCHAR(200)         — Arabic display name
logo_url            VARCHAR(500)         — SVG/PNG logo
logo_light_url      VARCHAR(500)         — logo variant for light backgrounds (nullable)
logo_dark_url       VARCHAR(500)         — logo variant for dark backgrounds (nullable)
brand_color         VARCHAR(7)           — primary hex color, e.g. "#4B0082"
brand_color_secondary VARCHAR(7)         — secondary hex (nullable)
website_url         VARCHAR(500)         — sponsor website (nullable)
tagline             VARCHAR(300)         — "الراعي الرسمي" or custom
is_active           BOOLEAN DEFAULT true
contract_starts     DATE                 — contract period start
contract_ends       DATE                 — contract period end
created_by          UUID FK → accounts
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

#### `sponsor_assignments` table (new)

Links a sponsor to a competition, season, or cycle — determines where the cinematic branding appears.

```
id                  UUID PRIMARY KEY
sponsor_id          UUID FK → sponsors
scope               ENUM(competition, season, cycle)
competition_id      UUID FK → competitions (nullable)
season_id           UUID FK → seasons (nullable)
cycle_id            UUID FK → cycles (nullable)
tier                ENUM(title, presenting, supporting)
display_config      JSONB                — override defaults per assignment
is_active           BOOLEAN DEFAULT true
created_by          UUID FK → accounts
created_at          TIMESTAMPTZ
```

**Sponsorship tiers:**

| Tier | Arabic | What they get |
|------|--------|---------------|
| `title` | الراعي الرئيسي | Full cinematic experience — splash, lobby variant, leaderboard header, share cards, competition name includes sponsor |
| `presenting` | الراعي الرسمي | Splash on first entry, logo in competition header, leaderboard footer |
| `supporting` | داعم | Logo in competition footer only, mentioned in news feed |

### 3.3 Sponsor API Endpoints

#### Owner panel (sponsors are platform-level, managed by owner)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/owner/sponsors` | List all sponsors |
| POST | `/api/owner/sponsors` | Create sponsor (with logo upload) |
| PATCH | `/api/owner/sponsors/{id}` | Update sponsor |
| DELETE | `/api/owner/sponsors/{id}` | Deactivate sponsor |
| GET | `/api/owner/sponsors/{id}/stats` | Sponsor performance (impressions, clicks across all assignments) |

#### Admin panel (assignments per competition)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/competitions/{id}/sponsors` | List sponsor assignments for competition |
| POST | `/api/admin/competitions/{id}/sponsors` | Assign sponsor to competition/season/cycle |
| PATCH | `/api/admin/sponsor-assignments/{id}` | Update assignment |
| DELETE | `/api/admin/sponsor-assignments/{id}` | Remove assignment |

#### Public API (for frontend rendering)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/competitions/{id}/sponsor` | Get active title/presenting sponsor for a competition (public, for rendering) |

Response:

```json
{
  "success": true,
  "data": {
    "sponsor": {
      "name": "STC",
      "name_ar": "إس تي سي",
      "logo_url": "/media/sponsors/stc-logo.svg",
      "brand_color": "#4B0082",
      "tagline": "الراعي الرسمي"
    },
    "tier": "title",
    "display_config": {}
  }
}
```

Returns `null` data if no active sponsor. Frontend uses this to decide whether to render the cinematic experience.

---

## 4. Cinematic Sponsored Competition Experience

### 4.1 The Vision

When a brand is the **title sponsor** of a competition, the entire competition gets a premium visual upgrade. It should feel like entering a "tournament mode" — dramatic, polished, and immersive. The sponsor's brand is woven into the game's visual language, not placed on top of it.

**Design philosophy (from esports research):**
- **Earned, not interruption** — Attach sponsor moments to things players want to see (leaderboard reveals, battle results, season launches), not forced pauses
- **Monochrome/tone-matched logos** — Render sponsor logos in brand-teal or brand-slate, not their corporate colors. Gamers8 Riyadh does this — recoloring all sponsor logos into the event palette. Accepted and respected in the Saudi gaming scene
- **Environmental integration** — On mobile, use themed backgrounds and transition screens rather than persistent overlay logos (PUBG Mobile pattern)
- **80/20 rule** — 80% earned attention moments, 20% transition interruptions
- **Logo sizing** — Never exceed 15% of container width. Mobile: 20-36px height. Desktop: 36-64px height
- **Typography** — Always typeset sponsor text in the game's fonts (Cairo/Changa), never in the sponsor's corporate font

### 4.2 Cinematic Splash Screen

**When:** First time a player enters a sponsored competition per session.
**Duration:** 5.5 seconds total, skippable after 2 seconds.
**Mobile:** Full-screen, works on 360x780 (Galaxy S25) at 60fps.

#### Animation Sequence (Frame-by-Frame)

Inspired by Genshin Impact's escalating anticipation, BLAST Premier's geometric assembly, and Riot's monochrome-to-color reveal:

```
PHASE 1 — ATMOSPHERE (0.0s – 1.2s)
═══════════════════════════════════
0.00s  Screen fades to #0a0d14 (lobby dark)                    [opacity 0→1, 600ms ease-out]
0.10s  Film grain overlay activates                             [CSS steps(10), 4% opacity, transform-only]
0.30s  Vignette tightens from 50% → 30% spread                 [CSS @property --vignette-spread, 800ms ease-in]
0.40s  Hexagon particle field spawns — 200 particles on mobile, 500 on desktop
       Particles spawn from center, drift outward in hex-grid pattern
       Color: sponsor brand_color at 12% opacity               [Canvas 2D, bitmap-cached hexagons]
0.60s  Two counter-rotating hexagon shapes fade in (lobby's rotateShape/Reverse)
       Tinted in brand_color at 8% opacity                     [CSS transform rotate, 45s/55s linear infinite]
1.00s  Subtle aurora gradient begins drifting in background
       3 layered radial-gradients using brand_color + brand_color_secondary
                                                                [CSS @property color animation, 8s cycle]

PHASE 2 — REVEAL (1.2s – 3.0s)
═══════════════════════════════
1.20s  Competition name text assembles — word-by-word RTL stagger
       "بطولة" → "[Sponsor]" → "لحرب" → "الأسماء"
       Each word: translateY(40px)→0 + opacity 0→1 + blur(10px)→0
       Stagger: 100ms between words                             [Motion variants, spring stiffness:200 damping:20]
       Font: Changa 800, white, clamp(1.5rem, 5vw, 3rem)
       Text-shadow: 0 0 40px brand_color at 30% opacity

1.80s  Sponsor logo enters — hexagonal clip-path reveal
       Starts as collapsed hexagon (all points at center)
       Expands to full hexagonal frame containing the logo
       Logo rendered monochrome white, fades to brand_color     [CSS clip-path polygon animation, 800ms]
       Logo max-width: 160px mobile, 240px tablet, 300px desktop

2.00s  [SKIP BUTTON APPEARS] — "تخطي" at top-left
       44×44px minimum touch target, opacity 0.6
       Text: Cairo 500, 14px, white                             [fade-in 200ms]

2.30s  Tagline types in below logo — RTL character reveal
       "الراعي الرسمي" or custom sponsor tagline
       Font: Cairo 600, brand_color, clamp(0.875rem, 2.5vw, 1.25rem)
       Cursor blink on left side (RTL)                          [CSS width animation + border-left blink]

PHASE 3 — CLIMAX + EXIT (3.0s – 5.5s)
══════════════════════════════════════
3.00s  Hexagon pulse — all particles flash to brand_color 40% opacity then back
       Single radial shockwave expands from center               [Canvas 2D, 400ms ease-out]
       Screen shake: ±3px translate + ±0.3deg rotate, 400ms     [CSS keyframes on wrapper]
       Haptic feedback: [50, 30, 100] vibration pattern          [Vibration API, Android only]

3.50s  Vignette relaxes from 30% → 50%                          [800ms ease-out]
       Particle field slows, particles begin fading

4.50s  Everything fades out simultaneously
       All elements: opacity 1→0, 600ms ease-out
       Particles: scale down 1→0.5 while fading                 [Canvas 2D per-particle]

5.00s  View Transition to competition dashboard
       Old view: scale(1)→scale(0.95) + opacity→0 + blur(4px)
       New view: scale(1.05)→scale(1) + opacity 0→1             [View Transitions API with fallback]

5.50s  Complete — competition view fully visible
```

#### Technical Implementation Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Orchestration | **Motion (Framer Motion)** `AnimatePresence` + `variants` | MIT license, 2.6kb min, spring physics, React-native, WAAPI-backed for 120fps |
| Particle field | **Canvas 2D** with bitmap-cached hexagons | 200 particles at 60fps on mobile without WebGL overhead |
| Hexagon clip-path | **CSS `clip-path: polygon()`** animation | GPU-accelerated, no JS needed |
| Aurora gradient | **CSS `@property`** color interpolation | True gradient color animation, compositor thread |
| Film grain | **CSS `transform` + `steps(10)`** on noise PNG | Transform-only = zero repaints |
| Vignette | **CSS `radial-gradient`** with `@property --vignette-spread` | Animatable custom property |
| Screen shake | **CSS `@keyframes`** on outermost wrapper | Transform-only, doesn't disrupt scroll |
| Text stagger | **Motion `staggerChildren`** with spring transition | Word-level splitting (not character — safe for Arabic connected script) |
| Page transition | **View Transitions API** with CSS fallback | Native browser, zero JS for the transition itself |
| Sound | **Web Audio API** — synthesized whoosh + impact + reveal | Zero audio file downloads |
| Haptics | **Vibration API** pattern `[50, 30, 100]` | Android progressive enhancement, no-op on iOS |

#### Sound Design (Web Audio API — No Files Needed)

```
0.40s  WHOOSH — sawtooth oscillator, freq 800→100 Hz over 300ms, lowpass filter 2000→200 Hz
       Synced with particle field spawn (movement sound)

1.20s  IMPACT — short noise burst 50ms, bandpass 200-400 Hz
       Synced with first word appearance (arrival accent)

1.80s  REVEAL TONE — sine wave chord (C5 + E5), 400ms attack, 800ms release
       Synced with logo hexagonal reveal (emotional pad)

3.00s  LOW BOOM — triangle wave 60 Hz, 200ms, gain 0.4
       Synced with hexagon pulse + screen shake (climax impact)
```

**Audio unlock:** AudioContext created on first user gesture (any tap/click). Splash audio only plays if context is unlocked — silent graceful degradation otherwise.

#### Performance Budget

| Metric | Target | Technique |
|--------|--------|-----------|
| JS execution per frame | < 8ms | Canvas bitmap cache, Motion WAAPI delegation |
| Composite layers | ≤ 4 | Only: particle canvas, hex shapes, text layer, vignette |
| Total animation JS | < 15kb | Motion tree-shaken + Canvas loop |
| Canvas particles (mobile) | 200 max | Bitmap-cached hexagons, OffscreenCanvas if supported |
| Canvas particles (desktop) | 500 max | Same technique, higher count |
| LCP impact | 0ms | Splash is an overlay, page content loads underneath |
| CLS impact | 0 | Full-viewport fixed overlay, no layout shift |
| Battery | Minimal | 5.5s max duration, auto-stops all rAF after exit |

#### `prefers-reduced-motion` Behavior

When the user has reduced motion enabled:
- Particle field: Static (no animation), show a still hexagon pattern at 8% opacity
- Film grain: Disabled
- Screen shake: Disabled
- All entrances: Simple opacity fade (200ms) instead of transforms
- Aurora gradient: Static, no drift
- Logo: Simple fade-in instead of clip-path reveal
- Text: All words appear simultaneously (no stagger)
- Vignette: Static at 40%
- Total duration reduced to 3 seconds (skip still available at 2s)
- Haptics and sound: Still fire (these are non-visual)

### 4.3 Branded Competition Header

When inside a sponsored competition, the competition header gets a subtle branded treatment.

**Standard (no sponsor):**
```
┌─────────────────────────────────────┐
│  موسم حرب الأسماء الأول             │
│  الموسم الأول — الدورة الأولى         │
└─────────────────────────────────────┘
```

**Title sponsor:**
```
┌─────────────────────────────────────┐
│  [Logo 24px]  الراعي الرسمي          │  ← bg: brand_color at 6% opacity
│  بطولة STC لحرب الأسماء             │  ← name includes sponsor
│  الموسم الأول — الدورة الأولى         │
└─────────────────────────────────────┘
```

**Presenting sponsor:**
```
┌─────────────────────────────────────┐
│  بطولة حرب الأسماء                  │
│  الموسم الأول — الدورة الأولى         │
│  ─────────────────────────          │
│  [Logo 20px]  برعاية Mobily          │  ← footer line only
└─────────────────────────────────────┘
```

**Implementation details:**
- Logo rendered monochrome (brand-slate in light mode, white in dark mode) — never full-color corporate logo
- Top bar tint: `bg-[brand_color]/[6-8]` — barely visible, matches the Riot Games pattern
- Border: `border-b` uses `brand_color` at 15% opacity
- Entrance: slides down 200ms ease-out on first render
- RTL: Logo on the right (start position), tagline to its left
- Font for "الراعي الرسمي": Cairo 400, 12px, brand_color at 70% opacity — weight is lighter than the competition name (following the esports hierarchy: event bold > sponsor medium)

### 4.4 Branded Leaderboard

**Title tier — Full treatment:**
- Header card: Animated gradient border using brand_color (CSS `@property` border-color animation, 4s cycle)
- "بطولة [Sponsor]" subtitle below leaderboard title — Cairo 500, brand_color at 60% opacity
- The #1 rank row: Subtle brand_color glow (`box-shadow: 0 0 20px brand_color at 10%`) — celebrating the leader in the sponsor's colors
- Sponsor logo watermark in the leaderboard footer — 5% opacity, centered, 40px height
- Logo "breathing" animation: opacity oscillates 0.03–0.06 over 4s (peripheral attention draw, BLAST pattern)

**Presenting tier — Subtle footer:**
- Sponsor logo (monochrome) + tagline in leaderboard footer
- Separated from content by a `border-t` in brand_color at 10% opacity
- No other visual changes

**Supporting tier:**
- Text-only mention: "بدعم من [Sponsor]" at bottom of leaderboard section
- Cairo 400, 11px, gray-500

### 4.5 Branded Share Cards

When a player shares results (attack result, quiz score, final ranking), the share image includes sponsor branding — this is "earned" integration because the player chose to share.

**Share card layout (OG image — 1200x630):**
```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   [Hexagon pattern bg — brand_color tinted at 5%]           │
│                                                              │
│              حرب الأسماء                                     │
│                                                              │
│              🎯 نتيجة الهجوم                                 │
│              [Alias] هاجم [Target]                           │
│              +500 نقطة                                       │
│                                                              │
│   ────────────────────────────────────────────────           │
│   [Logo 28px mono]  الراعي الرسمي  •  بطولة STC             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Implementation:**
- Backend-generated using a template (HTML → image service, or Canvas 2D on the server)
- Sponsor footer: single horizontal strip, logo + tagline + competition name
- Logo: Monochrome version, 28px height
- Separator dot (•) between elements — RTL-aware
- Background: Same hexagon pattern as splash, very subtle brand_color tint

### 4.6 Lobby Variant (Title Sponsor Only)

The lobby is the game's most immersive screen — a full dark-only environment with hexagons, rotating shapes, and magnetic hover. For a title sponsor, we subtly shift its color palette:

**Color treatment (following Gamers8 Riyadh approach):**
- 25-30% of hexagon SVG shapes in the background: fill shifts from default to `brand_color` at 8% opacity
- One of the two counter-rotating shapes: fill shifts to `brand_color` at 6% opacity
- The center logo glow: adds a secondary glow ring in `brand_color` at 10% opacity, 80px blur
- Sponsor logo watermark: positioned at absolute bottom center, 4% opacity, 48px height on mobile / 64px on desktop

**What does NOT change:**
- Button colors (teal, purple, orange, blue) — stay as-is
- Magnetic hover behavior — stays as-is
- Layout structure — zero changes
- Animation timing — same rotateShape 45s / rotateShapeReverse 55s

**Performance note:** The color shifts are CSS custom property changes only — no additional DOM elements, no additional composite layers. The watermark logo is a single `<img>` with `opacity: 0.04` and `pointer-events: none`.

### 4.7 Responsive Behavior (All Devices)

| Device | Viewport | Splash Particles | Logo Size | Text Size | Considerations |
|--------|----------|-----------------|-----------|-----------|----------------|
| Galaxy S25 (primary) | 360×780 | 200 | 160px | `clamp(1.25rem, 5vw, 1.75rem)` | Fixed bottom nav 56px, `100dvh` for mobile chrome |
| iPhone 15 | 393×852 | 200 | 160px | same | `env(safe-area-inset-*)` for notch |
| Small Android | 320×568 | 150 | 120px | `clamp(1rem, 5vw, 1.5rem)` | Tightest layout — reduce padding |
| iPad | 768×1024 | 350 | 240px | `clamp(1.5rem, 4vw, 2.5rem)` | Two-column layouts possible |
| Desktop | 1280+ | 500 | 300px | `clamp(2rem, 3vw, 3rem)` | Hover effects, mouse parallax on particles |

**Universal rules:**
- `100dvh` not `100vh` — accounts for mobile browser chrome
- Skip button: Always top-left, `min-width: 44px; min-height: 44px` (WCAG touch target)
- Logo: `max-width` responsive, `object-fit: contain`, never stretched or cropped
- Font sizing: `clamp()` for fluid typography — no breakpoint jumps
- Particle count: Auto-detected based on `navigator.hardwareConcurrency` and viewport size. If < 4 cores, use minimum count
- Canvas DPR: Capped at `Math.min(window.devicePixelRatio, 2)` — prevents 3x rendering on high-DPI devices

### 4.8 Cinematic Design System Tokens

All cinematic elements use these shared tokens for consistency:

```
── Timing ──────────────────────────────
--cinematic-fade-in:     600ms
--cinematic-fade-out:    400ms
--cinematic-spring:      cubic-bezier(0.175, 0.885, 0.32, 1.275)
--cinematic-smooth:      cubic-bezier(0.25, 1, 0.5, 1)
--cinematic-ease-out:    cubic-bezier(0.16, 1, 0.3, 1)
--cinematic-stagger:     100ms

── Colors (dynamic, set from sponsor data) ──
--cinematic-brand:       var(--sponsor-brand-color, #0B8A8D)
--cinematic-brand-glow:  color-mix(in srgb, var(--cinematic-brand) 30%, transparent)
--cinematic-brand-tint:  color-mix(in srgb, var(--cinematic-brand) 8%, transparent)
--cinematic-bg:          #0a0d14
--cinematic-surface:     #151b29

── Sizing ──────────────────────────────
--cinematic-logo-max:    clamp(120px, 30vw, 300px)
--cinematic-title-size:  clamp(1.25rem, 5vw, 3rem)
--cinematic-tagline-size: clamp(0.75rem, 2.5vw, 1.25rem)
--cinematic-grain-opacity: 0.04
--cinematic-vignette-spread: 50%

── Particles ───────────────────────────
--cinematic-particle-count: 200    (mobile) / 500 (desktop)
--cinematic-particle-opacity: 0.12
--cinematic-particle-size: 3-8px
```

### 4.9 Audio & Haptics Details

#### Synthesized Sound (Web Audio API — Zero File Downloads)

| Cue | Timing | Oscillator | Frequency | Filter | Duration | Gain |
|-----|--------|-----------|-----------|--------|----------|------|
| Whoosh | 0.40s | Sawtooth | 800→100 Hz ramp | Lowpass 2000→200 Hz | 300ms | 0.25 |
| Impact | 1.20s | White noise burst | Broadband | Bandpass 200-400 Hz | 50ms | 0.35 |
| Reveal tone | 1.80s | Sine (C5=523 Hz + E5=659 Hz) | Chord | None | 400ms attack + 800ms release | 0.20 |
| Low boom | 3.00s | Triangle | 60 Hz | Lowpass 100 Hz | 200ms | 0.40 |

**Audio pipeline:**
```
Oscillator → BiquadFilter → GainNode → AudioContext.destination
```

**AudioContext lifecycle:**
1. Created on app init (starts `suspended`)
2. Resumed on first user gesture (`click`/`touchstart`)
3. Splash checks `audioCtx.state === 'running'` before playing
4. If still suspended → splash runs silent (graceful degradation)

#### Haptic Patterns (Vibration API)

| Moment | Pattern (ms) | Feel |
|--------|-------------|------|
| Particle spawn | `[20]` | Tiny tap |
| Logo reveal | `[30, 20, 30]` | Double tap |
| Hexagon pulse + shake | `[50, 30, 100]` | Build-up then impact |
| Splash exit | `[20]` | Soft close |

**Platform support:**
- Android Chrome/Firefox/Samsung Internet: Full support
- iOS Safari: **Not supported** — no-op, no error
- Feature detection: `if ('vibrate' in navigator) { ... }`

### 4.10 Accessibility Compliance

| Requirement | Implementation |
|-------------|----------------|
| WCAG 2.3.3 (AAA) Non-essential animation | All cinematic animations disabled under `prefers-reduced-motion: reduce` |
| WCAG Pause/Stop/Hide | Skip button at 2s, auto-completes at 5.5s |
| Touch targets ≥ 44px | Skip button: `min-width: 44px; min-height: 44px` |
| Focus management | After splash exits, focus moves to first interactive element in competition view |
| Screen reader | Splash is `role="dialog" aria-label="عرض الراعي الرسمي"`, skip button is `aria-label="تخطي العرض"` |
| Color contrast | All text on dark bg: white (#FFFFFF) on #0a0d14 = ratio 18.4:1 (AAA) |
| Photosensitivity | No flashing > 3 times/second. Hexagon pulse is a single 400ms event |

---

## 5. Analytics (GA4 — Product Only, No Ads)

### 5.1 Scope

Google Analytics 4 is used purely for product improvement. **No ad features.**

**Disable in GA4 settings:**
- Google Signals (cross-device ad tracking)
- Ads Personalization
- Google Ads linking
- All advertising features in data collection

**Enable:**
- Enhanced Measurement (page views, scrolls, outbound clicks)
- User-ID tracking (mapped to account IDs)
- Custom Dimensions for game-specific data

### 5.2 Event Schema for Promotions

The promotion engine feeds GA4 for measuring effectiveness:

```javascript
// Promotion seen by user
gtag('event', 'promotion_impression', {
  promotion_id: '<uuid>',
  promotion_title: 'أغراض جديدة في المتجر',
  placement: 'banner_top',
  is_sponsored: false
});

// Promotion clicked
gtag('event', 'promotion_click', {
  promotion_id: '<uuid>',
  placement: 'banner_top',
  cta_type: 'navigate',
  destination: '/store'
});

// Promotion dismissed
gtag('event', 'promotion_dismiss', {
  promotion_id: '<uuid>',
  placement: 'splash'
});

// Sponsor splash viewed
gtag('event', 'sponsor_splash_view', {
  sponsor_name: 'STC',
  competition_id: '<uuid>',
  was_skipped: true,
  view_duration_seconds: 2.3
});
```

### 5.3 Key Funnels

**Promotion Effectiveness:**
```
promotion_impression → promotion_click → [desired_action completed]
```

**Sponsor Splash Engagement:**
```
sponsor_splash_view → was_skipped? → competition_engagement_after
```

### 5.4 Consent Mode v2

The existing consent banner already gates GA4 loading. Add Consent Mode v2 defaults to ensure compliance:

```javascript
// Before any GA4 script loads
gtag('consent', 'default', {
  'analytics_storage': 'denied',
  'ad_storage': 'denied',
  'ad_user_data': 'denied',
  'ad_personalization': 'denied',
  'region': ['SA']
});

// After user accepts consent banner
gtag('consent', 'update', {
  'analytics_storage': 'granted'
  // ad_* stays denied — we don't use ads
});
```

Only `analytics_storage` is ever granted. All ad-related consent stays `denied` permanently.

---

## 6. Admin Experience

### 6.1 Promotion Management Screen

**List view:**
- Table/cards showing all promotions with: title, placement, style, status (active/scheduled/expired), impression count, CTR
- Filters: by placement, by scope, by status, by sponsor
- Quick toggles: activate/deactivate without opening edit form

**Create/Edit form:**
- Title, subtitle, body (rich text optional)
- Media upload (image banner, max 2MB, recommended 1200x400 for banners, 1080x1920 for splash)
- Placement selector (visual picker showing where each placement appears)
- Layout selector (compact/standard/hero/fullscreen)
- Style selector (color-coded: info=teal, success=green, warning=amber, danger=red, celebration=purple, seasonal=gradient, sponsor=brand_color)
- Scope selector (global, or linked to specific competition/season/cycle)
- CTA: label + URL + type (navigate/deeplink/dismiss)
- Timing: starts_at, ends_at (date-time pickers in Riyadh timezone)
- Behavior: is_dismissible toggle, max impressions per user, cooldown hours
- Sponsor: toggle "محتوى مدعوم" → select sponsor from dropdown

**Preview:** Live preview of how the promotion looks in the selected placement, on mobile and desktop viewports.

### 6.2 Sponsor Management Screen (Owner Panel)

**List view:**
- Card grid of sponsors with: logo, name, status, contract dates, active assignments count
- Contract status indicators: active (green), expiring soon (amber), expired (red)

**Create/Edit form:**
- Name (Arabic), name (English/brand)
- Logo upload: primary + light variant + dark variant
- Brand colors: primary + secondary (color picker)
- Website URL
- Tagline (default: "الراعي الرسمي")
- Contract period: start date, end date

**Assignment screen:**
- Select competition → select tier (title/presenting/supporting)
- Optional: scope to specific season or cycle
- Preview: "This is how it will look" — shows the cinematic splash, header, and leaderboard treatment with this sponsor's branding

### 6.3 Analytics Dashboard (Promotion Stats)

Per promotion:
- Impressions, unique users reached, clicks, CTR, dismissal rate
- Trend chart (impressions/clicks over time)
- Breakdown by placement

Per sponsor:
- Total impressions across all assignments
- Splash view count, skip rate, average view duration
- Exportable report for sharing with the sponsor (PDF or CSV)

---

## 7. Frontend Components

### 7.1 Component Tree

```
src/components/promotions/
├── PromoBannerTop.jsx          — compact horizontal strip for dashboard top
├── PromoBannerBottom.jsx       — standard card for leaderboard bottom
├── PromoNewsFeed.jsx           — stacked cards for news section
├── PromoSplash.jsx             — full-screen login splash
├── PromoInterstitial.jsx       — modal between screens
├── PromoFloatingFab.jsx        — mini pill near bottom nav
├── PromoStoreFeatured.jsx      — hero card for store page
├── PromoCard.jsx               — shared card component (used by most placements)
├── PromoDismissButton.jsx      — consistent dismiss UI
└── usePromotions.js            — hook: fetches, caches, tracks interactions

src/components/sponsors/
├── SponsorSplash.jsx           — cinematic full-screen experience
├── SponsorHeader.jsx           — branded competition header bar
├── SponsorLeaderboard.jsx      — branded leaderboard treatment
├── SponsorWatermark.jsx        — subtle logo watermark (lobby, footer)
├── SponsorShareCard.jsx        — branded result share template
└── useSponsor.js               — hook: fetches active sponsor for competition
```

### 7.2 `usePromotions` Hook

```javascript
// Fetches active promotions, grouped by placement
// Handles impression tracking, click tracking, dismissals
// Respects user preferences (all_disabled, popups_disabled, sponsored_disabled)

const { placements, trackImpression, trackClick, dismiss, loading } = usePromotions({
  competitionId,
  seasonId,
  cycleId
});

// placements.banner_top → single promotion object or null
// placements.news_feed → array of promotions
// placements.splash → single promotion or null (shown once per session)
```

### 7.3 `useSponsor` Hook

```javascript
// Fetches the active sponsor for a competition
// Returns null if no sponsor

const { sponsor, tier, loading } = useSponsor(competitionId);

// sponsor.name, sponsor.logo_url, sponsor.brand_color, sponsor.tagline
// tier: 'title' | 'presenting' | 'supporting' | null
```

### 7.4 PromoCard Component Variants

**Compact (banner_top):**
```
┌──────────────────────────────────────────────────┐
│ 🏪  أغراض جديدة خرافية في المتجر!   [اكتشف ←] [×]│
└──────────────────────────────────────────────────┘
```
- Single line, icon on right (RTL), CTA button on left, dismiss × on far left
- Height: 48px, full width, subtle gradient background matching style

**Standard (banner_bottom, news_feed):**
```
┌──────────────────────────────────────┐
│  [Optional banner image 16:5]        │
│                                      │
│  أغراض جديدة خرافية في المتجر!      │
│  ترا فيه أشياء ما شفتوها قبل 😱     │
│                                      │
│  [اذهب للمتجر ←]              [×]   │
└──────────────────────────────────────┘
```
- Card with optional image, title, subtitle, CTA button, dismiss
- Rounded corners, shadow, respects light/dark mode

**Hero (store_featured):**
```
┌──────────────────────────────────────┐
│                                      │
│  [Full-bleed media — image/gradient] │
│                                      │
│  ──────────────────────────────────  │
│  خصم 30% على درع الحماية!           │
│  لفترة محدودة — ينتهي خلال 12 ساعة   │
│  [اشتري الآن ←]                      │
│                                      │
│  [Sponsor logo] إعلان               │  ← only if is_sponsored
└──────────────────────────────────────┘
```

**Fullscreen (splash):**
- Uses the same visual language as the sponsor splash (section 4.2) but without sponsor branding
- Full viewport, hexagon particle background, centered content
- Always dismissible (skip button at top-left after 1 second)
- Shown once per session (tracked in sessionStorage)

### 7.5 Sponsored Promotion Badge

When a promotion has `is_sponsored: true`, it shows a subtle "إعلان" badge:
- Small pill: `bg-gray-100 dark:bg-gray-800 text-gray-500 text-xs`
- Positioned at bottom-left of the card
- If a sponsor is linked: `[Sponsor Logo 16px] إعلان`
- This is the ONLY visual distinction — sponsored content otherwise looks identical to internal content

### 7.6 Animation Specs (All Placements)

| Placement | Enter Animation | Exit Animation |
|-----------|-----------------|----------------|
| banner_top | slideDown 300ms smooth | slideUp 200ms |
| banner_bottom | fadeInUp 400ms spring | fadeOut 200ms |
| news_feed | staggered fadeInUp (100ms delay between cards) | fadeOut 150ms |
| splash | fadeIn 600ms + content sequence (see 4.2) | fadeOut 400ms |
| interstitial | scale(0.95)→scale(1) + fadeIn 300ms spring | scale(1)→scale(0.95) fadeOut 200ms |
| floating_fab | slideInLeft 300ms spring + subtle bounce | slideOutLeft 200ms |
| store_featured | fadeIn 400ms | fadeOut 200ms |

**`prefers-reduced-motion`:** All animations collapse to simple opacity fade (200ms).

---

## 8. RTL / Arabic Design Rules for Promotions

### 8.1 Layout

- All content flows right-to-left
- CTA buttons: icon on the LEFT of text (end position in RTL)
- Dismiss × button: top-LEFT corner (end position in RTL)
- Carousel (if used in news_feed): swipe LEFT for next
- Progress indicators: fill from RIGHT to LEFT

### 8.2 Typography

- Headlines: **Changa** 700-800, minimum 18px mobile
- Body: **Cairo** 400-600, minimum 14px mobile
- Arabic text takes ~25% more horizontal space — design with breathing room
- Never break Arabic words mid-word: `word-break: keep-all`
- Numbers render LTR automatically (Unicode BiDi algorithm handles this)

### 8.3 Sponsor Logo Placement

- In headers: Logo on the RIGHT (start position in RTL)
- In footers/watermarks: Logo on the LEFT (end position)
- In splash screen: Centered (no directional bias)
- Never place logo inside Arabic text flow — always in a dedicated container

---

## 9. Data Flow Summary

```
Admin creates promotion
        │
        ▼
  promotions table (DB)
        │
        ▼
Player opens app → GET /api/promotions
        │
        ▼
  Backend resolves: scope + timing + dismissals + limits + preferences
        │
        ▼
  Returns promotions grouped by placement
        │
        ▼
  Frontend renders in each slot
        │
        ├── User sees promotion → POST /impression → promotion_interactions
        ├── User clicks CTA → POST /click → promotion_interactions → navigate
        └── User dismisses → POST /dismiss → promotion_dismissals
                                                │
                                                ▼
                                        GA4 events (if consent)
```

```
Owner creates sponsor → sponsors table
        │
        ▼
Admin assigns sponsor to competition → sponsor_assignments table
        │
        ▼
Player enters competition → GET /api/competitions/{id}/sponsor
        │
        ▼
  Frontend checks tier:
        ├── title → full cinematic (splash + header + leaderboard + lobby + share)
        ├── presenting → splash + header + leaderboard footer
        └── supporting → footer mention only
```

---

## 10. Implementation Phases

### Phase 4A: Promotion Engine (Backend + Basic Frontend)
- Promotion models + migrations
- Promotion CRUD API (admin)
- Player-facing API with resolution logic
- Interaction tracking (impression, click, dismiss)
- Player preference toggles
- Basic PromoCard component + banner_top placement

### Phase 4B: All Promotion Placements
- All 7 placement components
- usePromotions hook with caching
- Session-scoped splash (shown once)
- Interstitial between post-battle/post-quiz screens
- Floating FAB component
- Store featured hero card

### Phase 4C: Sponsor System (Backend)
- Sponsor models + migrations
- Sponsor CRUD API (owner)
- Sponsor assignment API (admin)
- Public sponsor API for competition

### Phase 4D: Cinematic Sponsor Experience (Frontend)
- SponsorSplash component (full animation sequence)
- SponsorHeader branded bar
- SponsorLeaderboard treatment
- Lobby color variant for title sponsors
- SponsorShareCard template
- useSponsor hook

### Phase 4E: Analytics + Admin Dashboard
- GA4 event wiring for promotion interactions
- Consent Mode v2 defaults
- Admin promotion stats dashboard
- Sponsor performance reports
- Export functionality for sponsors

---

## 11. Not In Scope

- Third-party ads (Google AdSense, Meta Audience Network, TikTok Ads) — explicitly excluded
- ads.txt — not needed without third-party ad networks
- Ad blockers — not relevant since all content is first-party
- Real-money transactions — sponsor payments happen offline/externally
- Automated sponsor matching — manual curation by owner
- A/B testing of promotions — future iteration
- Push notifications for promotions — use existing notification engine instead
- Smart triggers (auto-creating promotions based on events) — future iteration; admin creates all promotions manually for now
