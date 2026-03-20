import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'

export default function useCompetitionContext() {
  const [state, setState] = useState({
    competitionId: null,
    competitionName: null,
    seasonId: null,
    seasonName: null,
    cycleId: null,
    cycleLabel: null,
    cycleStartsAt: null,
    cycleEndsAt: null,
    nextCycleLabel: null,
    nextCycleStartsAt: null,
    membershipId: null,
    alias: null,
    balance: null,
    rank: null,
    protection: null,
    is_bankrupt: false,
    loading: true,
    error: null,
  })

  const fetchContext = useCallback(() => {
    const activeComp = localStorage.getItem(STORAGE_KEY)
    const url = activeComp
      ? `/api/me/competition-context?competition_id=${activeComp}`
      : '/api/me/competition-context'

    setState(s => ({ ...s, loading: true, error: null }))
    apiFetch(url)
      .then(json => {
        const d = json.data
        setState({
          competitionId: d?.competition_id ?? null,
          competitionName: d?.competition_name ?? null,
          seasonId: d?.season_id ?? null,
          seasonName: d?.season_name ?? null,
          cycleId: d?.cycle_id ?? null,
          cycleLabel: d?.cycle_label ?? null,
          cycleStartsAt: d?.cycle_starts_at ?? null,
          cycleEndsAt: d?.cycle_ends_at ?? null,
          nextCycleLabel: d?.next_cycle_label ?? null,
          nextCycleStartsAt: d?.next_cycle_starts_at ?? null,
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

  useEffect(() => { fetchContext() }, [fetchContext])

  return { ...state, refetchContext: fetchContext }
}
