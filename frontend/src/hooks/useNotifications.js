/**
 * Fetches notifications for the current user, scoped to the active competition.
 * Returns: { notifications, loading, error, unreadCount, refetch, markRead, markAllRead }
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'

export default function useNotifications() {
  const [state, setState] = useState({ notifications: [], loading: true, error: null })

  const fetchData = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const activeComp = localStorage.getItem(STORAGE_KEY)
      const url = activeComp
        ? `/api/me/notifications?competition_id=${activeComp}`
        : '/api/me/notifications'
      const json = await apiFetch(url)
      setState({ notifications: json.data ?? [], loading: false, error: null })
    } catch (err) {
      setState({ notifications: [], loading: false, error: err.message })
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const markRead = useCallback(async (notificationId) => {
    try {
      await apiFetch(`/api/me/notifications/${notificationId}/read`, { method: 'POST' })
      setState(s => ({
        ...s,
        notifications: s.notifications.map(n =>
          n.id === notificationId ? { ...n, is_read: true } : n
        ),
      }))
    } catch { /* ignore */ }
  }, [])

  const markAllRead = useCallback(async () => {
    try {
      await apiFetch('/api/me/notifications/read-all', { method: 'POST' })
      setState(s => ({
        ...s,
        notifications: s.notifications.map(n => ({ ...n, is_read: true })),
      }))
    } catch { /* ignore */ }
  }, [])

  const unreadCount = state.notifications.filter(n => !n.is_read).length

  return { ...state, unreadCount, refetch: fetchData, markRead, markAllRead }
}
