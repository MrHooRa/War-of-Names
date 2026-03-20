/**
 * Fetches the current user's inventory, scoped to the active competition.
 * Returns: { items, maxCapacity, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'

export default function useInventory() {
  const [state, setState] = useState({ items: [], maxCapacity: 10, loading: true, error: null })

  const fetchData = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const activeComp = localStorage.getItem(STORAGE_KEY)
      const url = activeComp
        ? `/api/me/inventory?competition_id=${activeComp}`
        : '/api/me/inventory'
      const json = await apiFetch(url)
      const data = json.data ?? {}
      setState({
        items: data.items ?? [],
        maxCapacity: data.max_capacity ?? 10,
        loading: false,
        error: null,
      })
    } catch (err) {
      setState({ items: [], maxCapacity: 10, loading: false, error: err.message })
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
