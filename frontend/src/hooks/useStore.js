/**
 * Fetches store listings for a competition.
 * Returns: { listings, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function useStore(competitionId) {
  const [state, setState] = useState({ listings: [], loading: true, error: null })

  const fetchData = useCallback(async () => {
    if (!competitionId) return
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const json = await apiFetch(`/api/competitions/${competitionId}/store`)
      setState({ listings: json.data ?? [], loading: false, error: null })
    } catch (err) {
      setState({ listings: [], loading: false, error: err.message })
    }
  }, [competitionId])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
