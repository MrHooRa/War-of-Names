/**
 * Date formatting utilities — Riyadh timezone (Asia/Riyadh, UTC+3).
 *
 * All user-facing timestamps in War of Names display in Riyadh time,
 * regardless of the user's browser timezone.
 *
 * Backend now treats naive timestamps as Riyadh-local wall-clock values.
 * This module keeps browser parsing aligned with that contract.
 */

const TIMEZONE = 'Asia/Riyadh'
const LOCALE = 'ar-SA'
const RIYADH_OFFSET = '+03:00'
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/
const TIMEZONE_RE = /(?:Z|[+-]\d{2}:\d{2}|[+-]\d{4})$/

/**
 * Parse backend timestamps safely.
 * Naive timestamps are interpreted as Riyadh-local, not browser-local and not UTC.
 */
export function parseDateTime(isoOrDate) {
  if (!isoOrDate) return null
  if (isoOrDate instanceof Date) return isoOrDate
  const s = String(isoOrDate).trim()
  let normalized = s
  if (!TIMEZONE_RE.test(s)) {
    normalized = DATE_ONLY_RE.test(s)
      ? `${s}T00:00:00${RIYADH_OFFSET}`
      : `${s}${RIYADH_OFFSET}`
  }
  const d = new Date(normalized)
  return isNaN(d.getTime()) ? null : d
}

function getRiyadhParts(isoOrDate) {
  const d = parseDateTime(isoOrDate)
  if (!d) return null
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(d)

  return Object.fromEntries(
    parts
      .filter(part => part.type !== 'literal')
      .map(part => [part.type, part.value]),
  )
}

export function toDateTimeLocalValue(isoOrDate) {
  const parts = getRiyadhParts(isoOrDate)
  if (!parts) return ''
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`
}

/**
 * Format a date string or Date object as a localized date (no time).
 * Example: "١٤ مارس ٢٠٢٦"
 */
export function formatDate(isoOrDate) {
  const d = parseDateTime(isoOrDate)
  if (!d) return ''
  return d.toLocaleDateString(LOCALE, { timeZone: TIMEZONE })
}

/**
 * Format a date string or Date object as a localized date + time.
 * Example: "١٤ مارس ٢٠٢٦ ٠٣:٤٥ م"
 */
export function formatDateTime(isoOrDate) {
  const d = parseDateTime(isoOrDate)
  if (!d) return ''
  return d.toLocaleString(LOCALE, { timeZone: TIMEZONE })
}

/**
 * Relative time-ago string in Arabic.
 * Example: "منذ ٥ دقائق"
 */
export function timeAgo(isoString) {
  const d = parseDateTime(isoString)
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

export function timeRemaining(isoOrDate) {
  const d = parseDateTime(isoOrDate)
  if (!d) return null
  const diff = d.getTime() - Date.now()
  if (diff <= 0) return 'منتهي'
  const minutes = Math.floor(diff / 60000)
  if (minutes < 60) return `${minutes} دقيقة`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} ساعة`
  const days = Math.floor(hours / 24)
  return `${days} يوم`
}
