/**
 * Fetches the active quiz session with questions.
 * Returns: { quiz, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'

export default function useQuiz() {
  const [state, setState] = useState({ quiz: null, loading: true, error: null })

  const fetchData = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const activeComp = localStorage.getItem(STORAGE_KEY)
      const url = activeComp
        ? `/api/quiz/active?competition_id=${activeComp}`
        : '/api/quiz/active'
      const json = await apiFetch(url)
      setState({ quiz: json.data ?? null, loading: false, error: null })
    } catch (err) {
      setState({ quiz: null, loading: false, error: err.message })
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
