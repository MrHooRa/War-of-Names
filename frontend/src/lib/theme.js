export const THEME_STORAGE_KEY = 'theme'

const THEME_COLORS = {
  light: '#F8F9FA',
  dark: '#111827',
}

function normalizeTheme(theme) {
  return theme === 'dark' ? 'dark' : 'light'
}

export function getStoredTheme() {
  try {
    return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY))
  } catch {
    return 'light'
  }
}

export function applyTheme(theme) {
  const resolvedTheme = normalizeTheme(theme)
  const isDark = resolvedTheme === 'dark'
  const root = document.documentElement

  root.classList.toggle('dark', isDark)
  root.dataset.theme = resolvedTheme
  root.style.colorScheme = resolvedTheme

  const themeColorMeta = document.querySelector('meta[name="theme-color"]')
  if (themeColorMeta) {
    themeColorMeta.setAttribute('content', THEME_COLORS[resolvedTheme])
  }

  return resolvedTheme
}

export function syncStoredTheme() {
  return applyTheme(getStoredTheme())
}

export function setTheme(theme) {
  const resolvedTheme = applyTheme(theme)
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, resolvedTheme)
  } catch {}
  return resolvedTheme
}

export function toggleTheme() {
  const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light'
  return setTheme(currentTheme === 'dark' ? 'light' : 'dark')
}
