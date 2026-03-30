/**
 * Fetches a single player profile within a competition.
 * Returns: { profile, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function usePlayerProfile(competitionId, membershipId) {
  const [state, setState] = useState({ profile: null, loading: true, error: null })

  const fetchData = useCallback(async () => {
    if (!competitionId || !membershipId) {
      setState({ profile: null, loading: false, error: null })
      return
    }
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const json = await apiFetch(`/api/competitions/${competitionId}/players/${membershipId}`)
      setState({ profile: json.data ?? null, loading: false, error: null })
    } catch (err) {
      setState({ profile: null, loading: false, error: err.message })
    }
  }, [competitionId, membershipId])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
