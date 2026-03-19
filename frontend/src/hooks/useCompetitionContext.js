import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'

export default function useCompetitionContext() {
  const [state, setState] = useState({
    competitionId: null,
    seasonId: null,
    cycleId: null,
    membershipId: null,
    alias: null,
    balance: null,
    rank: null,
    protection: null,
    is_bankrupt: false,
    loading: true,
    error: null,
  })

  useEffect(() => {
    apiFetch('/api/me/competition-context')
      .then(json => {
        const d = json.data
        setState({
          competitionId: d?.competition_id ?? null,
          seasonId: d?.season_id ?? null,
          cycleId: d?.cycle_id ?? null,
          membershipId: d?.membership_id ?? null,
          alias: d?.alias ?? null,
          balance: d?.balance ?? null,
          rank: d?.rank ?? null,
          protection: d?.protection ?? null,
          is_bankrupt: d?.is_bankrupt ?? false,
          loading: false,
          error: null,
        })
      })
      .catch(err => {
        setState(s => ({ ...s, loading: false, error: err.message }))
      })
  }, [])

  return state
}
