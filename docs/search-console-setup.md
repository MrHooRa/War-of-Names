# Google Search Console Setup Guide

## 1. Verify Domain Ownership
- Go to https://search.google.com/search-console
- Add property: https://yourdomain.com
- Verification method: DNS TXT record OR HTML file upload
- For HTML file: place in frontend/public/google{code}.html

## 2. Submit Sitemap
- In Search Console: Sitemaps → Add
- URL: https://yourdomain.com/sitemap.xml

## 3. Geo Targeting
- Settings → International Targeting
- Country: Saudi Arabia

## 4. Monitor
- Performance → Search Results
- Coverage → Check for crawl errors
- Mobile Usability → Verify all pages pass

## 5. OG Preview Testing
- Use https://cards-dev.twitter.com/validator for Twitter
- Use https://developers.facebook.com/tools/debug/ for Facebook/WhatsApp
- Share invite link on WhatsApp to verify preview shows correctly
