/**
 * Purchases an item from the store.
 * Call `buyItem(listingId)` to execute.
 * Returns: { buying, error, result, buyItem }
 */

import { useState, useCallback } from 'react'
import { apiFetch } from '../lib/api'
import { trackEvent } from '../lib/analytics'

export default function useBuyItem(competitionId) {
  const [state, setState] = useState({ buying: false, error: null, result: null })

  const buyItem = useCallback(async (listingId) => {
    if (!competitionId || !listingId) return
    setState({ buying: true, error: null, result: null })
    try {
      const json = await apiFetch(`/api/competitions/${competitionId}/store/${listingId}/buy`, {
        method: 'POST',
      })
      trackEvent('item_purchased', { price: json.data?.price })
      setState({ buying: false, error: null, result: json.data })
      return json
    } catch (err) {
      setState({ buying: false, error: err.message, result: null })
      return null
    }
  }, [competitionId])

  return { ...state, buyItem }
}
