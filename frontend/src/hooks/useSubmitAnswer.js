/**
 * Submits an answer to a quiz question.
 * Call `submitAnswer(sessionId, sessionQuestionId, answer)`.
 * Returns: { submitting, error, result, submitAnswer }
 */

import { useState, useCallback } from 'react'
import { apiFetch } from '../lib/api'

export default function useSubmitAnswer() {
  const [state, setState] = useState({ submitting: false, error: null, result: null })

  const submitAnswer = useCallback(async (sessionId, sessionQuestionId, answer) => {
    setState({ submitting: true, error: null, result: null })
    try {
      const json = await apiFetch(`/api/quiz/${sessionId}/answer`, {
        method: 'POST',
        body: JSON.stringify({
          session_question_id: sessionQuestionId,
          answer,
        }),
      })
      setState({ submitting: false, error: null, result: json.data })
      return json.data
    } catch (err) {
      setState({ submitting: false, error: err.message, result: null })
      return null
    }
  }, [])

  return { ...state, submitAnswer }
}
