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
 * Format a date string or Date object as a localized date (no time).
 * Example: "١٤ مارس ٢٠٢٦"
 */
export function formatDate(isoOrDate) {
  if (!isoOrDate) return ''
  const d = typeof isoOrDate === 'string' ? new Date(isoOrDate) : isoOrDate
  if (isNaN(d.getTime())) return ''
  return d.toLocaleDateString(LOCALE, { timeZone: TIMEZONE })
}

/**
 * Format a date string or Date object as a localized date + time.
 * Example: "١٤ مارس ٢٠٢٦ ٠٣:٤٥ م"
 */
export function formatDateTime(isoOrDate) {
  if (!isoOrDate) return ''
  const d = typeof isoOrDate === 'string' ? new Date(isoOrDate) : isoOrDate
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString(LOCALE, { timeZone: TIMEZONE })
}

/**
 * Relative time-ago string in Arabic.
 * Example: "منذ ٥ دقائق"
 */
export function timeAgo(isoString) {
  if (!isoString) return ''
  const diff = Date.now() - new Date(isoString).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'الآن'
  if (minutes < 60) return `منذ ${minutes} دقيقة`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `منذ ${hours} ساعة`
  const days = Math.floor(hours / 24)
  return `منذ ${days} يوم`
}
