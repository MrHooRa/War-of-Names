/**
 * Analytics utility — manages consent-gated tracking.
 *
 * Umami: no consent needed (self-hosted, no cookies)
 * GA4: requires consent
 */

const CONSENT_KEY = 'won_analytics_consent'

export function getConsent() {
  const stored = localStorage.getItem(CONSENT_KEY)
  if (!stored) return null // not decided yet
  return JSON.parse(stored) // { accepted: bool, timestamp: string }
}

export function setConsent(accepted) {
  const consent = { accepted, timestamp: new Date().toISOString() }
  localStorage.setItem(CONSENT_KEY, JSON.stringify(consent))
  if (accepted) {
    loadGA4()
  }
  return consent
}

export function hasConsented() {
  const consent = getConsent()
  return consent?.accepted === true
}

// GA4 loader — only called after consent
function loadGA4() {
  const gaId = window.__ANALYTICS_GA4_ID
  if (!gaId || document.getElementById('ga4-script')) return

  const script = document.createElement('script')
  script.id = 'ga4-script'
  script.async = true
  script.src = `https://www.googletagmanager.com/gtag/js?id=${gaId}`
  document.head.appendChild(script)

  window.dataLayer = window.dataLayer || []
  window.gtag = function() { window.dataLayer.push(arguments) }
  window.gtag('js', new Date())
  window.gtag('config', gaId, { send_page_view: false })
}

// Track page view (works with both Umami and GA4)
export function trackPageView(path) {
  // Umami (no consent needed)
  if (window.umami) {
    window.umami.track(props => ({ ...props, url: path }))
  }
  // GA4 (consent required)
  if (hasConsented() && window.gtag) {
    window.gtag('event', 'page_view', { page_path: path })
  }
}

// Track custom event
export function trackEvent(name, data = {}) {
  if (window.umami) {
    window.umami.track(name, data)
  }
  if (hasConsented() && window.gtag) {
    window.gtag('event', name, data)
  }
}
