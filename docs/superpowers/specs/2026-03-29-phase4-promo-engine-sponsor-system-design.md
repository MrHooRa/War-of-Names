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

### 4.2 Cinematic Splash Screen

**When:** First time a player enters a sponsored competition per session.
**Duration:** 4-5 seconds, skippable after 2 seconds.
**Mobile:** Full-screen, works on 360x780 (Galaxy S25).

**Animation sequence:**

```
0.0s — Screen fades to dark (#0a0d14)
0.3s — Hexagon particle field fades in (using lobby's rotateShape animation)
       Particles use sponsor's brand_color at 15% opacity
0.8s — Competition name slides up from bottom with spring easing
       "بطولة [Sponsor] لحرب الأسماء"
       Font: Changa 800, white, text-shadow with brand_color glow
1.5s — Sponsor logo fades in and scales (fadeInScale) below competition name
       Logo surrounded by a subtle hexagonal frame in brand_color
2.0s — [Skip button appears] — "تخطي" at top-left, subtle
2.5s — Tagline fades in below logo
       "الراعي الرسمي" in brand_color, Cairo 600
3.5s — Hexagons pulse once in brand_color
4.5s — Everything fades out, transition to competition view
```

**Visual specs:**
- Background: Same as lobby (#0a0d14) with hexagon SVG pattern
- Hexagons: Animated with `rotateShape` (45s) + `rotateShapeReverse` (55s), tinted in sponsor's brand_color
- Logo: Max 200px wide on mobile, 300px on desktop, centered
- All text: Centered, white with brand_color accents
- Spring easing: `cubic-bezier(0.175, 0.885, 0.32, 1.275)`
- Skip button: Simple text, not a branded element

**Responsive behavior:**
- Mobile (< 640px): Logo 160px max, title text-2xl, tagline text-sm
- Tablet (640-1024px): Logo 240px max, title text-3xl, tagline text-base
- Desktop (> 1024px): Logo 300px max, title text-4xl, tagline text-lg

### 4.3 Branded Competition Header

When inside a sponsored competition, the competition header gets a subtle branded treatment:

**Standard (no sponsor):**
```
┌─────────────────────────────────────┐
│  موسم حرب الأسماء الأول             │
│  الموسم الأول — الدورة الأولى         │
└─────────────────────────────────────┘
```

**Sponsored (title tier):**
```
┌─────────────────────────────────────┐
│  [Sponsor Logo 24px]  الراعي الرسمي  │  ← subtle top bar with brand_color bg at 8% opacity
│  بطولة STC لحرب الأسماء             │  ← competition name includes sponsor
│  الموسم الأول — الدورة الأولى         │
└─────────────────────────────────────┘
```

**Implementation:**
- Top bar: `bg-[brand_color]/8` — barely visible tint
- Sponsor logo: Small (24px height), on the right (RTL), next to tagline
- Border: `border-b` uses `brand_color` at 20% opacity
- Works in both light and dark mode

### 4.4 Branded Leaderboard

The leaderboard page gets a sponsor treatment:

**Title tier:**
- Leaderboard header card: Subtle gradient border using `brand_color`
- "بطولة [Sponsor]" subtitle below the leaderboard title
- Sponsor logo watermark in the footer of the leaderboard section (low opacity)
- The #1 rank row has a subtle brand_color glow (celebrating the leader in the sponsor's colors)

**Presenting tier:**
- Sponsor logo + tagline in leaderboard footer only
- No other visual changes

### 4.5 Branded Share Cards

When a player shares their results (attack result, quiz score, final ranking), the share card includes the sponsor's branding:

**Share card layout (Open Graph image):**
```
┌──────────────────────────────────────┐
│   حرب الأسماء                        │
│                                      │
│   🎯 نتيجة الهجوم                    │
│   [Player alias] هاجم [Target]       │
│   +500 نقطة                          │
│                                      │
│   ──────────────────────────         │
│   [Sponsor Logo] الراعي الرسمي       │
└──────────────────────────────────────┘
```

This is a backend-generated OG image (or a frontend template captured as image). The sponsor's logo and tagline appear in a dedicated footer section — never mixed with the game content.

### 4.6 Lobby Variant (Title Sponsor Only)

When a competition has a **title sponsor**, the lobby screen gets a subtle color shift:

- Background hexagons: 30% of hexagons use `brand_color` instead of the default colors
- The rotating shapes: One of the shapes uses `brand_color` fill at 10% opacity
- Sponsor logo: Appears as a watermark at the bottom of the lobby (5% opacity), barely visible
- **No structural changes** — same layout, same buttons, same magnetic hover

This is the subtlest integration — players notice the color shift subconsciously without it feeling like an advertisement.

### 4.7 Responsive Behavior (All Devices)

Every cinematic element must work across:

| Device | Viewport | Considerations |
|--------|----------|----------------|
| Galaxy S25 (primary) | 360x780 | Fixed bottom nav (56px), limited width, touch targets ≥ 44px |
| iPhone 15 | 393x852 | Safe area insets, notch avoidance |
| iPad | 768x1024 | Two-column layouts possible, larger splash logo |
| Desktop | 1280+ | Max-width containers, hover effects activate |

**Key rules:**
- Splash screen: Always full-viewport (`100dvh`), uses `dvh` for mobile browser chrome
- Skip button: Always at top-left, minimum 44x44 touch target
- Logo: `max-width` responsive, never stretched
- Text: `clamp()` for fluid typography — `clamp(1.25rem, 4vw, 2.5rem)` for titles
- Hexagon animations: Reduce particle count on mobile (performance)
- All animations: Respect `prefers-reduced-motion` — disable rotations, keep fades

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
