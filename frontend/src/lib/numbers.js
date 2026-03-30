const NUMBER_LOCALE = 'ar-SA'
const formatterCache = new Map()

function getFormatter(options = {}) {
  const cacheKey = JSON.stringify(options)
  let formatter = formatterCache.get(cacheKey)
  if (!formatter) {
    formatter = new Intl.NumberFormat(NUMBER_LOCALE, options)
    formatterCache.set(cacheKey, formatter)
  }
  return formatter
}

export function formatNumber(value, options) {
  if (value === null || value === undefined || value === '') return ''
  const numeric = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(numeric)) return ''
  return getFormatter(options).format(numeric)
}

export { NUMBER_LOCALE }
