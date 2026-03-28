/**
 * Submits an answer to a quiz question.
 * Call `submitAnswer(sessionId, sessionQuestionId, answer)`.
 * Returns: { submitting, error, result, submitAnswer }
 */

import { useState, useCallback } from 'react'
import { apiFetch } from '../lib/api'
import { trackEvent } from '../lib/analytics'

const STORAGE_KEY = 'won_active_competition'

export default function useSubmitAnswer() {
  const [state, setState] = useState({ submitting: false, error: null, result: null })

  const submitAnswer = useCallback(async (sessionId, sessionQuestionId, answer) => {
    setState({ submitting: true, error: null, result: null })
    try {
      const activeComp = localStorage.getItem(STORAGE_KEY)
      const qs = activeComp ? `?competition_id=${activeComp}` : ''
      const json = await apiFetch(`/api/quiz/${sessionId}/answer${qs}`, {
        method: 'POST',
        body: JSON.stringify({
          session_question_id: sessionQuestionId,
          answer,
        }),
      })
      trackEvent('quiz_answer', { is_correct: json.data.is_correct })
      setState({ submitting: false, error: null, result: json.data })
      return json.data
    } catch (err) {
      setState({ submitting: false, error: err.message, result: null })
      return null
    }
  }, [])

  return { ...state, submitAnswer }
}
