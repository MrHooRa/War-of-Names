import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'

export default function useDashboard() {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    apiFetch('/api/me/dashboard')
      .then(json => setState({ data: json.data, loading: false, error: null }))
      .catch(err => setState({ data: null, loading: false, error: err.message }))
  }, [])

  return state
}
