/**
 * Fetches the active quiz session with questions.
 * Returns: { quiz, loading, error, refetch }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function useQuiz() {
  const [state, setState] = useState({ quiz: null, loading: true, error: null })

  const fetchData = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const json = await apiFetch('/api/quiz/active')
      setState({ quiz: json.data ?? null, loading: false, error: null })
    } catch (err) {
      setState({ quiz: null, loading: false, error: err.message })
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  return { ...state, refetch: fetchData }
}
