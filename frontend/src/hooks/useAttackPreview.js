/**
 * Fetches an attack preview (eligibility + estimated reward/penalty).
 * Attacker is derived server-side from the JWT token.
 * Call `fetchPreview(targetMembershipId)` explicitly.
 * Returns: { preview, loading, error, fetchPreview }
 */

import { useState, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function useAttackPreview(competitionId) {
  const [state, setState] = useState({ preview: null, loading: false, error: null })

  const fetchPreview = useCallback(async (targetMembershipId) => {
    if (!competitionId || !targetMembershipId) return
    setState({ preview: null, loading: true, error: null })
    try {
      const json = await apiFetch(`/api/competitions/${competitionId}/attacks/preview`, {
        method: 'POST',
        body: JSON.stringify({
          target_membership_id: targetMembershipId,
        }),
      })
      setState({ preview: json.data ?? null, loading: false, error: null })
    } catch (err) {
      setState({ preview: null, loading: false, error: err.message })
    }
  }, [competitionId])

  return { ...state, fetchPreview }
}
