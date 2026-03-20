const TOKEN_KEY = 'won_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export async function apiFetch(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const res = await fetch(path, { ...options, headers })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    let data = null
    try {
      const err = await res.json()
      if (typeof err.detail === 'object' && err.detail !== null) {
        data = err.detail
        detail = err.detail.errors?.join('، ') || JSON.stringify(err.detail)
      } else {
        detail = err.detail || err.message || detail
      }
    } catch {}
    const error = new Error(detail)
    if (data) error.data = data
    throw error
  }

  return res.json()
}
