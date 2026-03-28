# War of Names — Platform Settings, SEO & Ads BRD
## Version 1.0

---

## 1. Purpose

This BRD covers three areas that make the platform **production-ready for growth**:
1. **Platform Settings** — configurable infrastructure settings beyond game rules
2. **SEO** — making the platform discoverable by Saudi users on Google, social media, and WhatsApp
3. **Ads & Analytics** — monetization readiness and user behavior tracking

References:
- `docs/Research - Platform Settings, SSO, Ads & Analytics - V1.0.md`
- `docs/Research - SEO & Digital Marketing - Arabic-First React SPA in KSA - V1.0.md`

---

## 2. Current State

### What EXISTS
- 19 game settings with multi-scope cascade (global → competition → season → cycle)
- GameInfo table (title, subtitle, announcement)
- Admin settings UI (2 pages: global + competition)
- Basic meta tags (description, theme-color)
- dns-prefetch for fonts and icons
- Security headers in nginx

### What's MISSING
- Platform-level settings (JWT, CORS, maintenance mode, branding)
- SEO (no sitemap, no robots.txt, no OG tags, no structured data, no pre-rendering)
- Analytics (no tracking at all)
- Ad infrastructure (no consent banner, no ad scripts, no pixel integration)
- Social sharing (invite links have no OG preview)

---

## 3. Platform Settings — Requirements

### 3.1 New Settings to Add

| Key | Category | Type | Default | Description |
|-----|----------|------|---------|-------------|
| `platform_name` | branding | STRING | "حرب الأسماء" | Platform display name |
| `platform_logo_url` | branding | STRING | "/assets/logo.png" | Logo URL |
| `platform_description` | branding | STRING | "أقوى لعبة تنافسية عربية" | SEO description |
| `maintenance_mode` | platform | BOOLEAN | false | Show maintenance page to all users |
| `maintenance_message` | platform | STRING | "" | Message shown during maintenance |
| `registration_enabled` | platform | BOOLEAN | true | Global registration switch |
| `google_analytics_id` | analytics | STRING | "" | GA4 Measurement ID (G-XXXXXXX) |
| `google_ads_id` | analytics | STRING | "" | Google Ads conversion ID |
| `ad_consent_required` | privacy | BOOLEAN | true | Show cookie/ad consent banner |
| `og_image_url` | seo | STRING | "/assets/og-image.png" | Default Open Graph image |

### 3.2 Environment Variable Additions

```env
# Add to .env.example
JWT_EXPIRE_HOURS=168          # 7 days default, configurable
CORS_ORIGINS=https://example.com,https://www.example.com
LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR
```

### 3.3 Maintenance Mode

When `maintenance_mode = true`:
- All player-facing API endpoints return 503 with `maintenance_message`
- Admin and owner endpoints continue working
- Frontend shows a maintenance page with the message
- Health endpoints remain accessible

---

## 4. SEO — Requirements

### 4.1 Public Pages to Index

| Page | URL | Title | Priority |
|------|-----|-------|----------|
| Landing | `/` | حرب الأسماء — أقوى لعبة تنافسية عربية | 1.0 |
| Rules | `/rules` | قواعد حرب الأسماء — كيف تلعب وتفوز | 0.8 |
| Terms | `/terms` | شروط الاستخدام — حرب الأسماء | 0.5 |
| Privacy | `/privacy` | سياسة الخصوصية — حرب الأسماء | 0.5 |
| Invite Preview | `/invite/:token` | انضم للمنافسة — حرب الأسماء | 0.7 |

### 4.2 Pages to NOT Index

All authenticated pages: `/dashboard`, `/leaderboard`, `/store`, `/quiz`, `/admin`, `/owner`, `/account`, `/notifications`, `/lobby`

### 4.3 robots.txt

```txt
User-agent: *
Allow: /
Allow: /rules
Allow: /terms
Allow: /privacy
Disallow: /dashboard
Disallow: /leaderboard
Disallow: /store
Disallow: /quiz
Disallow: /admin
Disallow: /owner
Disallow: /account
Disallow: /notifications
Disallow: /lobby
Disallow: /api/

Sitemap: https://yourdomain.com/sitemap.xml
```

### 4.4 sitemap.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://yourdomain.com/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://yourdomain.com/rules</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>
  <url><loc>https://yourdomain.com/terms</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://yourdomain.com/privacy</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
</urlset>
```

### 4.5 Meta Tags (Per Page)

Every public page must have:
```html
<title>{page title} — حرب الأسماء</title>
<meta name="description" content="{Arabic description, 120-160 chars}">
<meta property="og:title" content="{same as title}">
<meta property="og:description" content="{same as description}">
<meta property="og:image" content="{1200x630 image URL}">
<meta property="og:url" content="{canonical URL}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_SA">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{canonical URL}">
<html lang="ar" dir="rtl" hreflang="ar-SA">
```

**Implementation:** Use `react-helmet-async` for per-route meta tags.

### 4.6 Structured Data (JSON-LD)

Add to landing page:
```json
{
  "@context": "https://schema.org",
  "@type": ["WebApplication", "Game"],
  "name": "حرب الأسماء",
  "description": "منصة مسابقات تنافسية عربية — اكشف الأقنعة واربح النقاط",
  "url": "https://yourdomain.com",
  "applicationCategory": "Game",
  "operatingSystem": "Web",
  "inLanguage": "ar",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "SAR"
  }
}
```

### 4.7 Social Sharing (WhatsApp/Twitter/Discord)

Invite links MUST have OG tags for preview:
```
https://yourdomain.com/invite/ABC123
→ Shows: "انضم لمنافسة حرب الأسماء!" with game logo image
```

**Critical:** WhatsApp/Twitter/Discord bots do NOT execute JavaScript. The invite preview page must either:
1. Be server-rendered with meta tags in HTML, OR
2. Use nginx to inject meta tags for bot user-agents

**Recommended:** Nginx SSR proxy for bot user-agents on `/invite/:token`:
```nginx
# Detect social media crawlers
if ($http_user_agent ~* "facebookexternalhit|Twitterbot|WhatsApp|Discordbot|Slackbot|LinkedInBot|TelegramBot") {
    # Serve pre-rendered HTML with OG tags
    proxy_pass http://api:8000/api/invite-preview/$1;
}
```

### 4.8 Technical SEO

| Requirement | Status | Fix |
|-------------|--------|-----|
| HTTPS | ❌ Missing | Add Caddy or certbot in production |
| Canonical URLs | ❌ Missing | Add `<link rel="canonical">` per page |
| 301 redirects (www) | ❌ Missing | Nginx redirect www → non-www |
| Gzip compression | ✅ Exists | Already in nginx.conf |
| Core Web Vitals | ⚠️ Unknown | Run Lighthouse, target LCP < 2.5s |
| Image optimization | ❌ Missing | Convert logo to WebP, add Arabic alt tags |
| robots.txt | ❌ Missing | Create static file |
| sitemap.xml | ❌ Missing | Create static file |
| Favicon | ❌ Missing | Create and add to index.html |

---

## 5. Ads & Analytics — Requirements

### 5.1 Analytics Stack

| Tool | Purpose | Priority | Consent Required |
|------|---------|----------|-----------------|
| **Umami** (self-hosted) | Basic page views, no cookies | P0 | No |
| **Google Analytics 4** | Full analytics, funnels | P1 | Yes (PDPL) |
| **PostHog** | Product analytics, session replay | P2 | Yes |

### 5.2 Events to Track

| Event | When | Priority |
|-------|------|----------|
| `page_view` | Every navigation | P0 |
| `registration_complete` | After successful register | P0 |
| `competition_joined` | After joining via code/link | P0 |
| `first_attack` | First attack executed | P0 |
| `quiz_completed` | Quiz session finished | P1 |
| `item_purchased` | Store purchase | P1 |
| `invite_link_clicked` | Landing page from invite | P0 |
| `invite_link_converted` | Clicked → Registered → Joined | P0 |

### 5.3 Ad Formats

| Format | Where | Revenue Potential | UX Impact |
|--------|-------|-------------------|-----------|
| **Rewarded video** | Between quiz sessions | $10-20 eCPM | LOW (opt-in) |
| **Banner** | Below leaderboard on desktop | $1-3 eCPM | LOW |
| **Interstitial** | After attack result | $5-10 eCPM | MEDIUM |
| **Sponsored competition** | Custom branded competition | $500-5000/month | NONE |

**Recommendation:** Start with rewarded ads only. They have the highest revenue and lowest user friction.

### 5.4 Consent Banner (PDPL Required)

Before loading ANY tracking script (GA4, ads, pixels):
```
┌──────────────────────────────────────────────────┐
│  🍪 نستخدم تقنيات تحليل لتحسين تجربتك.         │
│                                                    │
│  [قبول]  [رفض]  [التفاصيل]                        │
└──────────────────────────────────────────────────┘
```

- Store consent in `localStorage` with timestamp
- Only load GA4/ad scripts AFTER consent
- Umami (self-hosted, no cookies) can run without consent
- Record consent choice in user profile for PDPL compliance

### 5.5 Google Ads Integration

```javascript
// Only load after consent
if (hasAdConsent) {
  // Google Ads conversion tracking
  gtag('config', 'AW-XXXXXXXXX');

  // Conversion event on registration
  gtag('event', 'conversion', {
    send_to: 'AW-XXXXXXXXX/CONVERSION_LABEL',
    value: 1.0,
    currency: 'SAR'
  });
}
```

### 5.6 CSP Headers Update for Ads

When ads are enabled, nginx CSP must allow:
```nginx
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.google-analytics.com https://pagead2.googlesyndication.com;
  img-src 'self' data: https://www.google-analytics.com https://pagead2.googlesyndication.com;
  connect-src 'self' https://www.google-analytics.com https://analytics.google.com;
  frame-src https://tpc.googlesyndication.com;
" always;
```

---

## 6. Implementation Phases

### Phase 1: SEO Foundation (3-4 days)

1. Create `robots.txt` and `sitemap.xml` as static files
2. Add `react-helmet-async` for per-route meta tags
3. Add OG tags to all public pages
4. Create OG image (1200x630) with game branding
5. Add JSON-LD structured data to landing page
6. Add favicon
7. Create nginx bot-detection for invite link OG previews

### Phase 2: Analytics (2-3 days)

1. Deploy self-hosted Umami (Docker, no consent needed)
2. Add GA4 with consent banner
3. Implement event tracking for registration + join + attack funnels
4. Setup Google Search Console

### Phase 3: Platform Settings (2-3 days)

1. Seed new platform settings (branding, maintenance, analytics IDs)
2. Add maintenance mode middleware
3. Add public branding API endpoint
4. Externalize hardcoded platform name/logo

### Phase 4: Ad Readiness (2-3 days)

1. PDPL consent banner component
2. Google Ads script loader (consent-gated)
3. CSP header updates for ad scripts
4. Rewarded ad placement in quiz flow

---

## 7. Saudi Arabia Regulatory Notes

### PDPL (Data Protection)
- Analytics that use cookies or track across sites = consent required
- Self-hosted analytics without cookies (Umami) = no consent needed
- Must disclose tracking in Privacy Policy (already done ✅)

### CITC (Communications)
- No specific requirements for web analytics
- Advertising must not contain misleading claims
- SMS/WhatsApp marketing requires opt-in

### GAMR (Media)
- Game ads must comply with age rating
- No gambling/betting ads in games
- Ad content must not violate Saudi cultural values

---

## 8. Revenue Projections

| MAU | Ad Revenue | Sponsored | Total |
|-----|-----------|-----------|-------|
| 100 | $5-15/mo | — | $5-15 |
| 1,000 | $50-150/mo | $500/mo | $550-650 |
| 10,000 | $500-1,500/mo | $2,000/mo | $2,500-3,500 |
| 50,000 | $2,500-7,500/mo | $5,000/mo | $7,500-12,500 |

**Key insight:** For platforms under 10K MAU, sponsored competitions generate 3-5x more revenue than ads. Focus on partnerships over ad integration.

---

## References

- Research: Platform Settings, SSO, Ads & Analytics (internal)
- Research: SEO & Digital Marketing - Arabic-First React SPA (internal)
- Admin Config & Game Data BRD (internal)
- Compliance & Regulations BRD (internal)
