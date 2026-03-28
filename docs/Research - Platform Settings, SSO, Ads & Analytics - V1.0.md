# Research Report: Platform Settings, SSO, Ads & Analytics
## War of Names — Deep Research for BRD Integration
### Date: 2026-03-28 | Status: Research Complete

---

## Table of Contents

1. [Platform Settings Architecture](#1-platform-settings-architecture)
2. [SSO (Single Sign-On) Integration](#2-sso-single-sign-on-integration)
3. [Ad Integration](#3-ad-integration)
4. [Analytics Integration](#4-analytics-integration)
5. [Priority Recommendations](#5-priority-recommendations)
6. [Saudi Arabia Regulatory Summary](#6-saudi-arabia-regulatory-summary)
7. [Sources](#7-sources)

---

## 1. Platform Settings Architecture

### 1.1 Settings Hierarchy Model

Based on research of Discord, Slack, Notion, and multi-tenant SaaS platforms, the recommended hierarchy for War of Names is:

```
Level 0: PLATFORM (global defaults)
  └── Level 1: COMPETITION (overrides platform defaults)
        └── Level 2: SEASON (overrides competition defaults)
              └── Level 3: CYCLE (overrides season defaults)
                    └── Level 4: USER PREFERENCES (display/notification only)
```

**What goes where:**

| Level | Setting Examples | Who Manages |
|-------|-----------------|-------------|
| **Platform** | Max competitions per admin, default point values, PDPL consent text, maintenance mode, rate limits, supported languages, global feature flags | Platform owner (super admin) |
| **Competition** | Attack cooldown, quiz duration, store enabled, bankruptcy threshold, protection rules, alias change rules, scoring multipliers, season auto-rotation | Competition admin |
| **Season/Cycle** | Active items, special event multipliers, quiz difficulty, distribution schedules, cycle-specific modifiers | Competition admin |
| **User Preferences** | Notification on/off, dark mode, language, sound effects, display density | Individual user |

**Resolution Algorithm (Discord-style cascade):**
```
effective_value = cycle_setting ?? season_setting ?? competition_setting ?? platform_default
```

If a setting is not defined at a more specific level, it inherits from the parent. This is the same model Discord uses for channel permissions: server-level defaults cascade to categories, then to channels, with explicit overrides at each level.

### 1.2 Database Schema for Settings

```sql
CREATE TABLE platform_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    value_type VARCHAR(20) NOT NULL,  -- 'string', 'integer', 'boolean', 'json', 'float'
    category VARCHAR(50) NOT NULL,     -- 'scoring', 'gameplay', 'security', 'display', 'compliance'
    description_ar TEXT,
    description_en TEXT,
    default_value JSONB NOT NULL,
    validation_rules JSONB,            -- {"min": 0, "max": 100, "enum": [...]}
    is_sensitive BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMPTZ,
    updated_by UUID REFERENCES users(id)
);

CREATE TABLE competition_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competition_id UUID NOT NULL REFERENCES competitions(id),
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    scope VARCHAR(20) NOT NULL DEFAULT 'competition',  -- 'competition', 'season', 'cycle'
    scope_id UUID,                     -- season_id or cycle_id when scope != 'competition'
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMPTZ,
    updated_by UUID REFERENCES users(id),
    UNIQUE(competition_id, key, scope, scope_id)
);

CREATE TABLE user_preferences (
    user_id UUID NOT NULL REFERENCES users(id),
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, key)
);

-- Audit trail for settings changes
CREATE TABLE settings_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(50) NOT NULL,
    setting_key VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    competition_id UUID,
    reason TEXT
);
```

### 1.3 Settings UI Design Patterns

**Recommended approach (based on Shopify, Discord, Notion patterns):**

1. **Grouped by Category** — Settings organized into logical tabs/sections:
   - Gameplay (scoring, attacks, protection)
   - Store & Items (pricing, availability)
   - Quiz (duration, difficulty, scheduling)
   - Notifications (templates, triggers)
   - Security (rate limits, session duration)
   - Compliance (consent text, data retention)

2. **Search Bar** — For competitions with 30+ settings, a search/filter is essential. Match against setting name, description, and category.

3. **Reset to Defaults** — Each setting shows the inherited/default value. A "reset" button removes the override and falls back to the parent level.

4. **Visual Indicators:**
   - Badge showing "overridden" when a setting differs from the parent level
   - Lock icon for platform-level settings that competition admins cannot change
   - Warning icon for settings that affect active seasons/cycles

5. **Instant Save with Confirmation** — Auto-save individual settings with a toast notification. For dangerous settings (bankruptcy threshold, scoring), require a confirmation dialog.

6. **JSON Mode Toggle** — Allow switching between form view and raw JSON for bulk editing (already partially implemented per the Admin Config BRD).

### 1.4 Feature Flags vs Settings

| Aspect | Feature Flags | Settings |
|--------|--------------|----------|
| **Purpose** | Control feature rollout, A/B tests, kill switches | Configure business rules and gameplay parameters |
| **Lifetime** | Temporary (remove after full rollout) | Permanent (core configuration) |
| **Who manages** | Developers/DevOps | Admins/competition owners |
| **Examples in War of Names** | `enable_new_quiz_engine`, `show_seasonal_event_ui`, `rollout_v2_scoring` | `attack_cooldown_minutes`, `quiz_question_count`, `bankruptcy_threshold` |
| **Storage** | Feature flag service or simple DB table | Settings tables with cascade |
| **Evaluation** | Boolean + targeting rules (user %, role, competition) | Typed values with validation |

**Recommendation for War of Names:** Use a lightweight feature flag table for developer-controlled rollouts. Do NOT mix feature flags with game settings.

```sql
CREATE TABLE feature_flags (
    key VARCHAR(100) PRIMARY KEY,
    enabled BOOLEAN DEFAULT FALSE,
    targeting_rules JSONB,  -- {"roles": ["admin"], "competition_ids": [...], "percentage": 50}
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- auto-cleanup reminder
);
```

**Tools considered:**
- **PostHog Feature Flags** (free tier, integrates with analytics) — recommended if using PostHog for analytics
- **GrowthBook** (open-source, self-hostable) — good standalone option
- **Custom table** (simplest) — sufficient for a small platform with <10 flags

### 1.5 Settings Migration Strategy

When adding new settings to existing deployments:

1. **Always use Alembic migrations** with default values:
   ```python
   # Example Alembic migration
   def upgrade():
       op.execute("""
           INSERT INTO platform_settings (key, value, value_type, category, default_value)
           VALUES ('new_setting_key', '"default_val"', 'string', 'gameplay', '"default_val"')
           ON CONFLICT (key) DO NOTHING;
       """)
   ```

2. **Backward-compatible approach:**
   - New settings ALWAYS have a default value
   - Application code uses `get_setting(key, fallback=DEFAULT)` pattern
   - Never require a setting that might not exist in older deployments
   - Migration script inserts defaults; existing competitions are unaffected

3. **Settings versioning:**
   - Each setting row has a `version` column (incremented on update)
   - `settings_audit` table provides full rollback history
   - Admin UI shows "last changed by X on Y" with a "revert to previous" option

4. **Bulk operations for season setup:**
   - Export competition settings as JSON template
   - Import template when creating new competitions (already partially implemented)
   - "Clone settings from Season X" for new seasons

**Implementation effort:** 2-3 days for the cascade resolver + UI improvements on top of existing settings infrastructure.

---

## 2. SSO (Single Sign-On) Integration

### 2.1 Provider Assessment for Saudi Gaming Audience

| Provider | Saudi Relevance | Effort | Priority |
|----------|----------------|--------|----------|
| **Google OAuth 2.0** | Very High — dominant email/Android provider in KSA | Low (well-documented) | P0 — do first |
| **Apple Sign In** | High — significant iPhone market share in KSA | Medium (more complex setup) | P1 |
| **Discord OAuth** | Medium — gaming community, growing in KSA | Low | P2 |
| **Twitter/X OAuth** | Medium — popular in Saudi social media | Low | P2 |
| **Nafath (National SSO)** | Very High for identity verification, but overkill for a gaming platform | High (license required from TCC) | P3 — only if identity verification needed |

### 2.2 Recommended Library: `fastapi-sso`

After evaluating authlib, python-social-auth, and fastapi-sso:

**Winner: `fastapi-sso` (v0.21.0+)**

- Purpose-built for FastAPI with async support
- Supports ALL needed providers: Google, Apple, Discord, Twitter/X, Facebook, GitHub
- Server-side OAuth state store (in-memory or Redis)
- Active maintenance (latest release in 2025)
- Simple API — one class per provider

```python
# Example: Google SSO with fastapi-sso
from fastapi_sso.sso.google import GoogleSSO

google_sso = GoogleSSO(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=f"{settings.BASE_URL}/auth/google/callback",
    allow_insecure_http=False
)

@router.get("/auth/google/login")
async def google_login():
    async with google_sso:
        return await google_sso.get_login_redirect()

@router.get("/auth/google/callback")
async def google_callback(request: Request):
    async with google_sso:
        user_info = await google_sso.verify_and_process(request)
        # user_info.email, user_info.display_name, user_info.provider, user_info.id
        # Link to existing account or create new one
```

**Alternative: `authlib` (v1.6.6)**
- More powerful (can build OAuth server too)
- Lower-level, more boilerplate
- Better if building a full OAuth authorization server later
- Use if `fastapi-sso` doesn't support a needed provider

**Not recommended: `python-social-auth`**
- Django-centric, awkward with FastAPI
- Legacy patterns, not fully async

### 2.3 Account Linking Strategy

War of Names currently uses username/password. SSO must be additive, not replacing existing auth.

**Database changes:**

```sql
CREATE TABLE user_oauth_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,         -- 'google', 'apple', 'discord', 'twitter'
    provider_user_id VARCHAR(255) NOT NULL, -- provider's unique user ID
    provider_email VARCHAR(255),
    provider_display_name VARCHAR(255),
    access_token_encrypted TEXT,           -- encrypted, for API calls if needed
    refresh_token_encrypted TEXT,
    linked_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    UNIQUE(provider, provider_user_id)
);

CREATE INDEX idx_oauth_links_user ON user_oauth_links(user_id);
CREATE INDEX idx_oauth_links_provider ON user_oauth_links(provider, provider_user_id);
```

**Linking flows:**

1. **New user signs up via SSO:**
   - Check if `provider_user_id` exists in `user_oauth_links` -> if yes, log them in
   - Check if `provider_email` matches existing user -> prompt to link accounts (enter existing password to confirm)
   - Otherwise, create new user account + oauth link (prompt for username/alias)

2. **Existing user adds SSO:**
   - From settings page, click "Link Google Account"
   - Complete OAuth flow
   - Store link in `user_oauth_links`
   - User can now login via either method

3. **SSO-only users (no password):**
   - Allow users to register via SSO without setting a password
   - If they later want to add password login, provide "Set Password" in settings
   - `users.password_hash` can be NULL for SSO-only accounts

**Security considerations:**
- Store OAuth tokens encrypted at rest (Fernet or AES-256)
- Never expose tokens to the frontend
- Validate `state` parameter to prevent CSRF (fastapi-sso handles this)
- Set short session lifetimes (30 min access token, 7 day refresh)
- Rate-limit OAuth callback endpoints

### 2.4 Apple Sign In — Web App Requirements

Apple Sign In for web apps requires:
- Apple Developer Account ($99/year)
- Services ID configured in Apple Developer portal
- Domain verification (place a file at `/.well-known/apple-developer-domain-association.txt`)
- Starting January 2026, developers in some regions must provide a server-to-server notification endpoint
- Apple may return a "private relay" email — store this and handle email forwarding
- Apple only sends user's name on the FIRST authorization — cache it immediately

### 2.5 Nafath (Saudi National SSO)

**What it is:** Saudi Arabia's national digital identity platform (28M+ digital identities). Nafath allows government and private applications to authenticate users via their national ID.

**Integration flow:**
1. Call `POST /ExtNafath/request` with national ID
2. Receive a random verification code
3. User enters code in Nafath mobile app to approve
4. Webhook callback confirms verification

**Requirements:**
- License from Technology Control Company (TCC)
- API access credentials
- Laravel package exists (`saudi-nafath-integration`), no Python package found — would need custom implementation

**Recommendation for War of Names:** NOT recommended for initial launch. Nafath is designed for identity verification (banking, government services), not gaming login. The licensing overhead and user friction (requiring national ID for a game) would hurt conversion. Consider only if the platform later requires age verification or real-identity validation for legal compliance.

### 2.6 SSO Should Be Optional

**Recommendation:** Keep username/password as the primary method. Offer SSO as a convenience option.

- Saudi users are accustomed to both methods
- Not all users have Google/Apple accounts linked to their preferred identity
- Gaming platforms benefit from pseudonymous accounts (aliases)
- SSO increases signup conversion by 20-35% (industry average) but should not be the only option

**Implementation effort:**
- Google OAuth: 1-2 days
- Apple Sign In: 2-3 days (more complex setup)
- Discord OAuth: 1 day
- Twitter/X OAuth: 1 day
- Account linking system: 2-3 days
- Total: ~8-10 days for all providers

---

## 3. Ad Integration

### 3.1 Ad Formats for Gaming Platforms

| Format | User Experience | Revenue (eCPM) | Recommendation for War of Names |
|--------|----------------|-----------------|--------------------------------|
| **Rewarded Ads** | User opts in, watches ad for in-game reward | $10-$20 | BEST FIT — "Watch ad for +50 bonus points" |
| **Interstitial** | Full-screen between actions | $14-$15 | OK — between quiz rounds or after battles |
| **Banner** | Persistent strip, low disruption | $1-$5 | AVOID — degrades competitive gaming UX |
| **Native/In-Feed** | Blends with content | $5-$10 | POSSIBLE — in lobby or leaderboard |

**Best placement strategy for War of Names:**
1. **After quiz completion** — interstitial while results load
2. **In lobby/waiting room** — native ad or banner (the lobby is already an immersive dark-themed screen)
3. **Rewarded ad for bonus** — "Watch to earn 50 bonus points" button on dashboard (opt-in, non-intrusive)
4. **Between seasons** — sponsored splash screen during off-season
5. **NEVER during active gameplay** — never interrupt attacks, store transactions, or quiz questions

### 3.2 Google AdSense in React SPA

**Library:** `@ctrl/react-adsense` (npm)

```jsx
import { Adsense } from '@ctrl/react-adsense';

// In a component:
<Adsense
  client="ca-pub-XXXXXXXXXX"
  slot="1234567890"
  style={{ display: 'block' }}
  format="auto"
  responsive="true"
/>
```

**Key constraints:**
- AdSense will NOT serve ads on localhost or development environments
- Site must be publicly accessible for approval
- Google removed the ability to block "Video Games" ad category (May 2025) — gaming ads will appear
- Google expanded gambling definition to include virtual currencies (2025) — review ad policies carefully
- SPA page changes require manual ad refresh or using AdSense auto-ads

**AdSense approval requirements:**
- Minimum content and traffic (typically 30+ pages, consistent traffic)
- No prohibited content
- Clear privacy policy (required for PDPL compliance anyway)
- Domain must be at least 3-6 months old (varies)

### 3.3 Alternative Ad Networks for Saudi Arabia

| Network | Saudi Support | Min Traffic | Notes |
|---------|--------------|-------------|-------|
| **Google AdSense** | Yes | ~1000 visits/day recommended | Standard choice |
| **Google Ad Manager** | Yes | No minimum | More control, serves AdSense + direct deals |
| **Meta Audience Network** | Yes | N/A | Integrates with Meta Pixel |
| **TikTok Ads** | Yes (34.6M KSA users) | N/A | Growing Saudi market |
| **Unity Ads / ironSource** | Yes | Game-focused | Better for mobile, limited web |

### 3.4 Saudi Arabia Ad Regulations

**Key regulatory bodies:**
- **GAMR** (General Authority for Media Regulation) — requires campaign approval before display
- **CITC** (Communications, Space and Technology Commission) — digital content platform regulations
- **SDAIA** (Saudi Data & AI Authority) — PDPL enforcement

**PDPL requirements for ad tracking:**
- Explicit consent before collecting personal data for ad targeting
- Inform users about purpose, scope, and duration of data collection
- Implement technical measures to protect data against unauthorized access
- Data processing must occur transparently
- Right to opt-out of personalized advertising

**GAMR content requirements:**
- No content promoting gambling (War of Names uses virtual points, not real money — should be safe)
- No content violating Islamic values or Saudi cultural norms
- No misleading advertising claims
- Ads targeting children have stricter rules

**Practical compliance steps:**
1. Implement a cookie consent banner (opt-in, not opt-out)
2. Include ads disclosure in privacy policy
3. Allow users to opt-out of personalized ads
4. Store consent records for audit

### 3.5 Ad Blockers in Saudi Arabia

- Globally, 29.5% of internet users use ad blockers (Q2 2025)
- Saudi Arabia is among the leading countries in MENA for mobile ad blocking
- Estimated 25-35% of Saudi web users use some form of ad blocking

**Mitigation strategies:**
- **Rewarded ads are ad-blocker resistant** — user actively chooses to watch
- **Server-side ad insertion** — harder to block but complex to implement
- **"Support us" messaging** — ask users to whitelist if ad blocker detected
- **DO NOT use anti-ad-block walls** — frustrates users, violates trust
- **Diversify revenue** — don't depend on ads as sole income (see 3.7)

### 3.6 Revenue Expectations

For a small Saudi gaming platform (1,000-10,000 monthly active users):

| Metric | Conservative | Optimistic |
|--------|-------------|------------|
| Monthly pageviews | 50,000 | 500,000 |
| Ad impressions (50% ad-blocker) | 25,000 | 250,000 |
| Average eCPM (Saudi Arabia) | $2-$5 | $5-$15 |
| **Monthly ad revenue** | **$50-$125** | **$1,250-$3,750** |
| Rewarded ads revenue (higher eCPM) | $100-$300 | $2,000-$5,000 |

**Conclusion:** Ad revenue alone will not sustain a small platform. Ads should be a supplementary income stream, not the primary business model.

### 3.7 Alternative Monetization Strategies

| Strategy | Effort | Revenue Potential | Fit for War of Names |
|----------|--------|-------------------|---------------------|
| **Sponsored competitions** | Medium | High — brands pay to host/name competitions | EXCELLENT — "بطولة [Brand] لحرب الأسماء" |
| **Premium items/cosmetics** | Low | Medium — cosmetic alias frames, badges | GOOD — doesn't affect gameplay |
| **Season pass** | Medium | Medium — unlock premium quiz packs, exclusive items | GOOD — adds value |
| **Brand partnerships** | High | High — sponsored items, branded rewards | EXCELLENT — native to game world |
| **Offer walls** | Low | Low-Medium — complete sponsored actions for points | OK — careful execution needed |
| **Competition entry fees** | Low | Low — small fee to join premium competitions | RISKY — could reduce participation |

**Recommendation:** Prioritize sponsored competitions and brand partnerships over traditional ads. Saudi brands are actively seeking gaming engagement channels. A single brand sponsorship deal could exceed months of ad revenue.

### 3.8 CSP (Content Security Policy) for Ad Scripts

Ad scripts (Google, Meta, TikTok) inject third-party code that conflicts with strict CSP headers.

**Recommended approach:**

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'strict-dynamic' 'nonce-{random}'
    https://pagead2.googlesyndication.com
    https://www.googletagmanager.com
    https://connect.facebook.net
    https://analytics.tiktok.com;
  img-src 'self' data: https:;
  connect-src 'self'
    https://www.google-analytics.com
    https://pagead2.googlesyndication.com
    https://www.facebook.com
    https://analytics.tiktok.com;
  frame-src https://googleads.g.doubleclick.net https://tpc.googlesyndication.com;
```

**Best practices:**
- Use `nonce`-based CSP (generated per request) rather than `'unsafe-inline'`
- Use `react-helmet-async` to manage CSP meta tags dynamically
- Isolate ad iframes where possible (Google already does this)
- Start with `Content-Security-Policy-Report-Only` to test before enforcing
- Use Google Tag Manager as a single script entry point to reduce CSP surface area

### 3.9 Tracking Pixel Integration

**Google Tag Manager (GTM):**
- Library: `react-gtm-module` (npm) or direct `<script>` in `index.html`
- Manages ALL tags (GA4, Meta Pixel, TikTok Pixel) from one dashboard
- SPA requires manual `dataLayer.push` on route changes

**Meta Pixel:**
- Library: `react-facebook-pixel` (npm)
- Track: Registration, CompetitionJoined, FirstAttack, StorePurchase
- Saudi reach: significant Facebook/Instagram user base

**TikTok Pixel:**
- Library: `react-pixel-tiktok` (npm)
- SPA: TikTok Pixel auto-detects URL changes in SPAs
- Saudi reach: 34.6M users, growing rapidly
- 18-35% decrease in conversion costs reported by advertisers using Pixel

**Implementation effort:**
- GTM setup: 0.5 days
- GA4 via GTM: 0.5 days
- Meta Pixel: 0.5 days
- TikTok Pixel: 0.5 days
- AdSense integration: 1-2 days
- CSP configuration: 0.5 days
- Total: ~4-5 days

---

## 4. Analytics Integration

### 4.1 Recommended Analytics Stack

**Tier 1 (Must-Have):** Google Analytics 4 + Google Tag Manager
**Tier 2 (Recommended):** PostHog (self-hosted or cloud)
**Tier 3 (Optional):** Umami or Plausible for PDPL-compliant basic analytics

### 4.2 GA4 in React SPA

**Library:** `react-ga4` (npm) or GTM-based (recommended)

**Key implementation details:**
- React SPAs don't trigger page reloads — GA4's Enhanced Measurement may not catch route changes
- Must disable automatic initial pageview to avoid double-counting
- Use `useLocation()` + `useEffect()` to manually fire pageviews on route change

```jsx
import ReactGA from 'react-ga4';

// Initialize (once, in App.jsx or main.jsx)
ReactGA.initialize('G-XXXXXXXXXX', {
  gtagOptions: { send_page_view: false }  // Prevent double-counting
});

// Track page views (in a layout component)
const location = useLocation();
useEffect(() => {
  ReactGA.send({ hitType: 'pageview', page: location.pathname });
}, [location]);
```

**2026 GA4 features:**
- Calculated Metrics — create custom formulas directly in GA4 UI (introduced early 2026)
- Enhanced AI insights for funnel analysis
- Improved SPA support in Enhanced Measurement

### 4.3 PostHog — Recommended Product Analytics

**Why PostHog for War of Names:**
- Open-source, self-hostable (PDPL compliance)
- All-in-one: analytics + session replay + feature flags + A/B tests
- Engineer-friendly (SQL access to data)
- Free tier: 1M events/month + 5K session recordings
- Self-hosted: free for up to ~300K events/month

**PostHog vs Mixpanel vs Amplitude:**

| Feature | PostHog | Mixpanel | Amplitude |
|---------|---------|----------|-----------|
| Self-hosted | Yes (open-source) | No | No |
| Free tier | 1M events/mo | 1M events/mo | 10K MTUs/mo |
| Session replay | Yes | Yes (2025) | Yes (2025) |
| Feature flags | Yes | Yes (2025) | Yes |
| A/B testing | Yes | Yes | Yes |
| SQL access | Yes | No | No |
| PDPL compliant (self-hosted) | Yes | Depends on DPA | Depends on DPA |
| Best for | Developer-led teams | Product managers | Enterprise analytics |

**Recommendation:** PostHog Cloud for initial launch (free tier sufficient), migrate to self-hosted if data sovereignty becomes a concern.

### 4.4 Privacy-Focused Alternatives

**Umami:**
- Fully open-source, MIT license
- Self-hosted, no cookies, no personal data
- Lightweight (~2KB script)
- Free to self-host (runs on any Node.js + PostgreSQL)
- PDPL compliant by design (no personal data collected)
- Limited to web analytics (no product analytics, no funnels)

**Plausible:**
- Open-source (AGPL), self-hostable
- No cookies, GDPR/PDPL compliant
- EU-hosted cloud option
- Community Edition free for self-hosting
- Better dashboard than Umami, but still basic compared to GA4

**Recommendation:** Use Umami or Plausible as a lightweight, always-on analytics layer that requires NO consent banner. Use GA4/PostHog for deeper analytics WITH consent.

### 4.5 Events to Track

**Registration & Onboarding Funnel:**
| Event | Properties | Priority |
|-------|-----------|----------|
| `page_view` | `path`, `referrer` | P0 |
| `registration_started` | `method` (form/google/apple) | P0 |
| `registration_completed` | `method`, `time_to_complete` | P0 |
| `first_login` | `method` | P0 |
| `competition_joined` | `competition_id`, `invite_code_used` | P0 |
| `profile_completed` | `has_alias`, `has_avatar` | P1 |

**Core Gameplay:**
| Event | Properties | Priority |
|-------|-----------|----------|
| `attack_initiated` | `competition_id`, `is_first_attack` | P0 |
| `attack_result` | `success`, `points_changed`, `item_used` | P0 |
| `quiz_started` | `session_id`, `question_count` | P0 |
| `quiz_completed` | `score`, `time_taken`, `correct_count` | P0 |
| `store_item_viewed` | `item_id`, `rarity` | P1 |
| `store_purchase` | `item_id`, `price`, `currency_type` | P0 |
| `item_used` | `item_id`, `effect_type`, `target` | P1 |

**Engagement & Retention:**
| Event | Properties | Priority |
|-------|-----------|----------|
| `daily_active` | `session_count`, `competitions_active` | P0 |
| `leaderboard_viewed` | `competition_id`, `user_rank` | P1 |
| `notification_received` | `type` | P2 |
| `notification_clicked` | `type`, `time_to_click` | P2 |
| `settings_changed` | `setting_key` | P2 |
| `dark_mode_toggled` | `new_value` | P2 |

**Funnel Analysis:**
```
Registration -> Join Competition -> First Quiz -> First Attack -> First Store Purchase -> Day 7 Return
```

### 4.6 Implementation Effort

| Component | Effort | Dependencies |
|-----------|--------|-------------|
| GA4 + GTM setup | 1 day | GTM account, GA4 property |
| PostHog integration | 1 day | PostHog account or self-hosted instance |
| Umami self-hosted | 0.5 days | Docker container |
| Event taxonomy implementation | 2 days | Backend event hooks |
| Funnel dashboard setup | 1 day | GA4/PostHog configured |
| Consent management | 1 day | PDPL compliance |
| **Total** | **~6-7 days** | |

---

## 5. Priority Recommendations

### Phase 1: Pre-Launch (Do Before MVP)

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| Settings cascade resolver (backend) | 2 days | High | Foundation for all game configuration |
| Settings UI improvements (grouped, search, reset) | 2 days | High | Admin experience |
| Feature flags table | 0.5 days | Medium | Developer convenience |
| Umami self-hosted (basic analytics) | 0.5 days | High | No consent needed, immediate insights |
| GA4 + GTM setup | 1 day | High | Industry standard, free |
| Cookie consent banner | 1 day | Required | PDPL compliance |
| **Total Phase 1** | **~7 days** | | |

### Phase 2: Post-Launch Growth (First 30 Days)

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| Google OAuth SSO | 2 days | High | Increases signup conversion 20-35% |
| Apple Sign In | 3 days | High | iPhone users in KSA |
| Account linking system | 2 days | Medium | Connects SSO to existing accounts |
| PostHog integration | 1 day | High | Product analytics, session replay |
| Event taxonomy (full) | 2 days | High | Data-driven decisions |
| **Total Phase 2** | **~10 days** | | |

### Phase 3: Monetization (After 1000+ MAU)

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| Rewarded ads (AdSense) | 2 days | Medium | Opt-in, non-intrusive |
| Meta Pixel + TikTok Pixel | 1 day | Medium | Campaign tracking |
| Discord OAuth | 1 day | Low-Medium | Gaming community |
| Twitter/X OAuth | 1 day | Low-Medium | Saudi social reach |
| CSP configuration for ads | 0.5 days | Required | Security |
| Sponsored competition framework | 3 days | High | Better ROI than ads |
| **Total Phase 3** | **~8-9 days** | | |

### Phase 4: Scale (After Proven PMF)

| Item | Effort | Impact | Notes |
|------|--------|--------|-------|
| PostHog self-hosted migration | 2 days | Medium | Data sovereignty |
| Settings versioning + rollback UI | 2 days | Medium | Admin safety net |
| A/B testing (PostHog) | 1 day | Medium | Optimize conversion |
| Nafath integration | 5+ days | Low | Only if identity verification required |
| Advanced ad formats (interstitial) | 2 days | Medium | Revenue optimization |
| **Total Phase 4** | **~12+ days** | | |

---

## 6. Saudi Arabia Regulatory Summary

### PDPL (Personal Data Protection Law)

- **Effective:** September 2024
- **Enforced by:** SDAIA (Saudi Data & AI Authority)
- **Key requirements for War of Names:**
  - Explicit consent before collecting personal data
  - Clear privacy policy in Arabic
  - Data minimization — only collect what's needed
  - Right to access, correct, and delete personal data
  - Data breach notification within 72 hours
  - If processing data outside KSA, additional safeguards required

### GAMR (General Authority for Media Regulation)

- All advertising campaigns require approval before display
- Interactive content must comply with Audiovisual Media Law
- Content must respect Saudi cultural values
- Special restrictions for content targeting children

### CITC (Communications, Space and Technology Commission)

- Digital content platforms may need registration/licensing
- Platform Compliance Officer may be required
- Cooperate with CITC on content moderation requests

### Practical Impact

| Area | Requirement | Implementation |
|------|-------------|---------------|
| Analytics | Consent before tracking | Cookie consent banner (opt-in) |
| Ads | GAMR approval for campaigns | Submit ad campaigns for review |
| Data storage | PDPL data protection | Encryption at rest, access controls |
| User rights | Right to deletion | Existing deletion request system (already built) |
| Privacy policy | Arabic, comprehensive | Update existing policy with ad/analytics disclosures |
| Age verification | If targeting minors | Age gate at registration (already discussed in Compliance BRD) |

---

## 7. Sources

### Platform Settings Architecture
- [Multi-Tenant SaaS Architecture Guide - WorkOS](https://workos.com/blog/developers-guide-saas-multi-tenant-architecture)
- [Multi-Tenant Architecture Guide - Clerk](https://clerk.com/blog/how-to-design-multitenant-saas-architecture)
- [Settings Design Pattern - UI Patterns](https://ui-patterns.com/patterns/settings)
- [How to Improve App Settings UX - Toptal](https://www.toptal.com/designers/ux/settings-ux)
- [Settings Page UI Examples - BricxLabs](https://bricxlabs.com/blogs/settings-page-ui-examples)
- [Feature Flags vs Configuration - PostHog](https://posthog.com/product-engineers/feature-flags-vs-configuration)
- [Feature Flags Best Practices 2025 - Kodekx](https://www.kodekx.com/blog/feature-flags-best-practices-2025)
- [Database Migrations in the Real World - JetBrains](https://blog.jetbrains.com/idea/2025/02/database-migrations-in-the-real-world/)
- [Discord Permission Hierarchy](https://support.discord.com/hc/en-us/articles/206141927-How-is-the-permission-hierarchy-structured)
- [Channel Permissions Settings 101 - Discord](https://support.discord.com/hc/en-us/articles/10543994968087-Channel-Permissions-Settings-101)

### SSO Integration
- [Social Login Integration Guide 2026 - InfluenceFlow](https://influenceflow.io/resources/social-login-integration-a-complete-2026-guide-for-businesses-and-developers/)
- [Top 5 Authentication Solutions for FastAPI 2026 - WorkOS](https://workos.com/blog/top-authentication-solutions-fastapi-2026)
- [FastAPI OAuth Client - Authlib Documentation](https://docs.authlib.org/en/latest/client/fastapi.html)
- [fastapi-sso - GitHub](https://github.com/tomasvotava/fastapi-sso)
- [fastapi-sso - PyPI](https://pypi.org/project/fastapi-sso/)
- [fastapi-discord - PyPI](https://pypi.org/project/fastapi-discord/)
- [Twitter OAuth 2.0 PKCE - Developer Documentation](https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code)
- [Apple Sign In REST API - Apple Developer](https://developer.apple.com/documentation/signinwithapplerestapi)
- [Configure Sign In with Apple for Web - Apple Developer](https://developer.apple.com/help/account/capabilities/configure-sign-in-with-apple-for-the-web/)
- [Account Linking Strategy - Auth0](https://community.auth0.com/t/automatic-migration-with-social-login-account-linking/59076)
- [SSO Migration Guide - Inteca](https://inteca.com/business-insights/sso-migration/)
- [Nafath Integration - Sohoby](https://sohoby.com/services/nafath-integration-saudi-arabia)
- [National Single Sign-On - GOV.SA](https://my.gov.sa/en/services/119727)
- [Saudi Digital Identities - Khaleej Weekly](https://khaleejweekly.com/saudi-arabia-digital-identities/)
- [Nafath API Documentation - Azakaw](https://documentation.azakaw.com/docs/apis/core/nafath)

### Ad Integration
- [Google AdSense in React SPA - DEV Community](https://dev.to/deuos/how-to-implement-google-adsense-into-reactjs-2025-5g3h)
- [AdSense for Single Page Apps - Jason Watmore](https://jasonwatmore.com/add-google-adsense-to-a-single-page-app-react-angular-vue-next-etc)
- [Rewarded Ads Performance 2026 - MAF](https://maf.ad/en/blog/rewarded-ads-stats/)
- [Gaming Ad Networks - Adpushup](https://www.adpushup.com/blog/gaming-ad-networks/)
- [In-Game Advertising Saudi Arabia - Statista](https://www.statista.com/outlook/dmo/digital-media/video-games/in-game-advertising/saudi-arabia)
- [Saudi Arabia Advertising Guide - Istizada](https://istizada.com/blog/saudi-arabia-advertising/)
- [Ad Blockers Usage Statistics 2026 - Cropink](https://cropink.com/ad-blockers-usage-statistics)
- [MENA Ad Blocking Trends - Arabian Marketer](https://arabianmarketer.ae/pakistan-ksa-uae-egypt-lead-ad-blocking-trends-in-mena/)
- [TikTok Pixel SPA Measurement](https://ads.tiktok.com/help/article/about-single-page-application-pageview-measurement-for-tiktok-pixel)
- [TikTok Ads Saudi Arabia - Affect](https://affectgroup.com/blog/tiktok-audience-size-and-demographics-in-saudi-arabia/)
- [CSP for React Apps - OneUpTime](https://oneuptime.com/blog/post/2026-01-15-content-security-policy-csp-react/view)
- [CSP in Single Page Applications - Auth0](https://auth0.com/blog/deploying-csp-in-spa/)
- [Mobile Game Monetization 2026 - Adapty](https://adapty.io/blog/mobile-game-monetization/)
- [Gaming Monetization Guide - Stripe](https://stripe.com/resources/more/gaming-monetization-explained)

### Analytics
- [GA4 in React - Mykola Aleksandrov](https://www.mykolaaleksandrov.dev/posts/2025/11/react-google-analytics-implementation/)
- [GA4 2026 Overview - Tatvic](https://www.tatvic.com/blog/everything-you-need-to-know-about-google-analytics-4-ga4-in-2025/)
- [Mixpanel vs Amplitude vs PostHog 2026 - Product Growth](https://productgrowth.in/insights/ai-ml/mixpanel-vs-amplitude-vs-posthog/)
- [Best Product Analytics Tools 2026 - Vision Labs](https://visionlabs.com/blog/best-product-analytics-tools/)
- [PostHog vs Mixpanel - PostHog](https://posthog.com/blog/posthog-vs-mixpanel)
- [Plausible Privacy-Focused Analytics](https://plausible.io/privacy-focused-web-analytics)
- [Umami vs Plausible Comparison - Vemetric](https://vemetric.com/blog/plausible-vs-umami)
- [Best GDPR-Compliant Analytics - PostHog](https://posthog.com/blog/best-gdpr-compliant-analytics-tools)
- [GTM for React SPA](https://www.analyticsmania.com/post/single-page-web-app-with-google-tag-manager/)
- [react-gtm-module - GitHub](https://github.com/dukeweezo/react-gtm-module)

### Saudi Arabia Regulations
- [Saudi PDPL Overview - PECB](https://pecb.com/en/article/saudi-arabias-data-privacy-law-in-practice-what-you-need-to-know-about-the-pdpl)
- [Data Protection Saudi Arabia 2025-2026 - ICLG](https://iclg.com/practice-areas/data-protection-laws-and-regulations/saudi-arabia)
- [Saudi PDPL First Anniversary - IAPP](https://iapp.org/news/a/saudi-pdpl-s-first-anniversary-amendments-enforcement-and-ongoing-developments)
- [Media & Entertainment Saudi Arabia 2025 - Chambers](https://practiceguides.chambers.com/practice-guides/media-entertainment-2025/saudi-arabia/trends-and-developments)
- [KSA Telecoms & Media 2025 - ICLG](https://iclg.com/practice-areas/telecoms-media-and-internet-laws-and-regulations/saudi-arabia)
- [Saudi Gaming Market - Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/middle-east-gaming-market)
- [Saudi Gaming Payment Trends - Antom](https://knowledge.antom.com/saudi-arabia-gaming-payment-trends-report-building-the-worlds-next-esports-powerhouse)
