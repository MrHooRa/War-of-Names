import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'

export default function useDashboard() {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    const activeComp = localStorage.getItem(STORAGE_KEY)
    const url = activeComp
      ? `/api/me/dashboard?competition_id=${activeComp}`
      : '/api/me/dashboard'
    apiFetch(url)
      .then(json => setState({ data: json.data, loading: false, error: null }))
      .catch(err => setState({ data: null, loading: false, error: err.message }))
  }, [])

  return state
}
