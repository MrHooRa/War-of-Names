/**
 * Date formatting utilities — Riyadh timezone (Asia/Riyadh, UTC+3).
 *
 * All user-facing timestamps in War of Names display in Riyadh time,
 * regardless of the user's browser timezone.
 *
 * Backend stores UTC internally (correct). This module handles the
 * UTC → Riyadh conversion at the display layer.
 */

const TIMEZONE = 'Asia/Riyadh'
const LOCALE = 'ar-SA'

/**
 * Parse backend timestamps safely.
 * Backend stores naive UTC (no Z suffix) — we append Z so JS treats them as UTC.
 */
function parseUTC(isoOrDate) {
  if (!isoOrDate) return null
  if (isoOrDate instanceof Date) return isoOrDate
  // Append Z if no timezone indicator at the END of the string.
  // Must not match date separators (2026-03-27 has dashes mid-string).
  const s = String(isoOrDate)
  const hasTimezone = /Z$|[+-]\d{2}:\d{2}$|[+-]\d{4}$/.test(s)
  const d = new Date(hasTimezone ? s : s + 'Z')
  return isNaN(d.getTime()) ? null : d
}

/**
 * Format a date string or Date object as a localized date (no time).
 * Example: "١٤ مارس ٢٠٢٦"
 */
export function formatDate(isoOrDate) {
  const d = parseUTC(isoOrDate)
  if (!d) return ''
  return d.toLocaleDateString(LOCALE, { timeZone: TIMEZONE })
}

/**
 * Format a date string or Date object as a localized date + time.
 * Example: "١٤ مارس ٢٠٢٦ ٠٣:٤٥ م"
 */
export function formatDateTime(isoOrDate) {
  const d = parseUTC(isoOrDate)
  if (!d) return ''
  return d.toLocaleString(LOCALE, { timeZone: TIMEZONE })
}

/**
 * Relative time-ago string in Arabic.
 * Example: "منذ ٥ دقائق"
 */
export function timeAgo(isoString) {
  const d = parseUTC(isoString)
  if (!d) return ''
  const diff = Date.now() - d.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'الآن'
  if (minutes < 60) return `منذ ${minutes} دقيقة`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `منذ ${hours} ساعة`
  const days = Math.floor(hours / 24)
  return `منذ ${days} يوم`
}
