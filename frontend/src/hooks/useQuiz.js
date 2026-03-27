/**
 * Fetches quiz sessions and active quiz data.
 * Returns: { quiz, sessions, loading, error, refetch, selectSession }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'

export default function useQuiz() {
  const [state, setState] = useState({ quiz: null, sessions: [], loading: true, error: null })

  const fetchSessions = useCallback(async () => {
    const activeComp = localStorage.getItem(STORAGE_KEY)
    const url = activeComp
      ? `/api/quiz/sessions?competition_id=${activeComp}`
      : '/api/quiz/sessions'
    const json = await apiFetch(url)
    return json.data ?? []
  }, [])

  const fetchQuiz = useCallback(async (sessionId) => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const sessions = await fetchSessions()
      const activeComp = localStorage.getItem(STORAGE_KEY)
      const qs = sessionId ? `&session_id=${sessionId}` : ''
      const url = activeComp
        ? `/api/quiz/active?competition_id=${activeComp}${qs}`
        : `/api/quiz/active${qs ? '?' + qs.slice(1) : ''}`
      const json = await apiFetch(url)
      setState({ quiz: json.data ?? null, sessions, loading: false, error: null })
    } catch (err) {
      setState(s => ({ ...s, quiz: null, loading: false, error: err.message }))
    }
  }, [fetchSessions])

  useEffect(() => { fetchQuiz() }, [fetchQuiz])

  return { ...state, refetch: fetchQuiz, selectSession: (id) => fetchQuiz(id) }
}
