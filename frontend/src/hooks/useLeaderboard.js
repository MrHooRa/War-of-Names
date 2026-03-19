/**
 * Fetches the ranked leaderboard for a competition.
 * Returns: { players, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function useLeaderboard(competitionId) {
  const [state, setState] = useState({ players: [], loading: true, error: null })

  const fetchData = useCallback(async () => {
    if (!competitionId) return
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const json = await apiFetch(`/api/competitions/${competitionId}/leaderboard`)
      setState({ players: json.data ?? [], loading: false, error: null })
    } catch (err) {
      setState({ players: [], loading: false, error: err.message })
    }
  }, [competitionId])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
