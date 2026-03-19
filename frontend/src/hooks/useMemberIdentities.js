/**
 * Fetches all member identities for the attack modal's guess dropdown.
 * Each identity contains: membership_id, alias, account_id, real_name
 * Returns: { identities, loading, error }
 */

import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'

export default function useMemberIdentities(competitionId) {
  const [state, setState] = useState({ identities: [], loading: true, error: null })

  useEffect(() => {
    if (!competitionId) return
    async function load() {
      try {
        const json = await apiFetch(`/api/competitions/${competitionId}/members/identities`)
        setState({ identities: json.data ?? [], loading: false, error: null })
      } catch (err) {
        setState({ identities: [], loading: false, error: err.message })
      }
    }
    load()
  }, [competitionId])

  return state
}
