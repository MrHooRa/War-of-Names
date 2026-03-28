/**
 * Executes an attack and navigates to the result page.
 * Attacker is derived server-side from the JWT token.
 * Call `executeAttack(targetMembershipId, guessedAccountId)`.
 * Returns: { executing, error, executeAttack }
 */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { trackEvent } from '../lib/analytics'

export default function useAttackExecute(competitionId) {
  const navigate = useNavigate()
  const [state, setState] = useState({ executing: false, error: null })

  const executeAttack = useCallback(async (targetMembershipId, guessedAccountId) => {
    if (!competitionId) return
    setState({ executing: true, error: null })
    try {
      const json = await apiFetch(`/api/competitions/${competitionId}/attacks/execute`, {
        method: 'POST',
        body: JSON.stringify({
          target_membership_id: targetMembershipId,
          guessed_account_id: guessedAccountId,
        }),
      })
      const result = json.data
      trackEvent('attack_executed', { outcome: result.outcome })

      if (result.outcome === 'succeeded') {
        navigate('/battle/victory', { state: result })
      } else {
        navigate('/battle/defeat', { state: result })
      }
    } catch (err) {
      setState({ executing: false, error: err.message })
    }
  }, [competitionId, navigate])

  return { ...state, executeAttack }
}
