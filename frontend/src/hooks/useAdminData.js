/**
 * Generic admin data fetcher.
 * useAdminData('/api/admin/dashboard') → { data, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function useAdminData(url) {
  const [state, setState] = useState({ data: null, loading: !!url, error: null })

  const fetchData = useCallback(async () => {
    if (!url) { setState({ data: null, loading: false, error: null }); return }
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const json = await apiFetch(url)
      setState({ data: json.data ?? null, loading: false, error: null })
    } catch (err) {
      setState({ data: null, loading: false, error: err.message })
    }
  }, [url])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
