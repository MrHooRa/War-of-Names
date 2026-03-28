/**
 * Fetches notifications for the current user, scoped to the active competition.
 * Supports pagination with limit/offset and a loadMore() function.
 * Returns: { notifications, loading, error, unreadCount, total, hasMore, loadMore, refetch, markRead, markAllRead }
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../lib/api'

const STORAGE_KEY = 'won_active_competition'
const PAGE_SIZE = 20

export default function useNotifications() {
  const [state, setState] = useState({
    notifications: [],
    loading: true,
    error: null,
    total: 0,
    offset: 0,
  })
  const loadingMore = useRef(false)

  const fetchData = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const activeComp = localStorage.getItem(STORAGE_KEY)
      let url = `/api/me/notifications?limit=${PAGE_SIZE}&offset=0`
      if (activeComp) url += `&competition_id=${activeComp}`
      const json = await apiFetch(url)
      setState({
        notifications: json.data ?? [],
        loading: false,
        error: null,
        total: json.total ?? 0,
        offset: PAGE_SIZE,
      })
    } catch (err) {
      setState({ notifications: [], loading: false, error: err.message, total: 0, offset: 0 })
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const loadMore = useCallback(async () => {
    if (loadingMore.current) return
    loadingMore.current = true
    try {
      const activeComp = localStorage.getItem(STORAGE_KEY)
      let url = `/api/me/notifications?limit=${PAGE_SIZE}&offset=${state.offset}`
      if (activeComp) url += `&competition_id=${activeComp}`
      const json = await apiFetch(url)
      setState(s => ({
        ...s,
        notifications: [...s.notifications, ...(json.data ?? [])],
        total: json.total ?? s.total,
        offset: s.offset + PAGE_SIZE,
      }))
    } catch { /* ignore */ }
    finally { loadingMore.current = false }
  }, [state.offset])

  const markRead = useCallback(async (notificationId) => {
    try {
      await apiFetch(`/api/me/notifications/${notificationId}/read`, { method: 'POST' })
      setState(s => ({
        ...s,
        notifications: s.notifications.map(n =>
          n.id === notificationId ? { ...n, is_read: true } : n
        ),
      }))
      window.dispatchEvent(new CustomEvent('notifications-updated'))
    } catch { /* ignore */ }
  }, [])

  const markAllRead = useCallback(async () => {
    try {
      await apiFetch('/api/me/notifications/read-all', { method: 'POST' })
      setState(s => ({
        ...s,
        notifications: s.notifications.map(n => ({ ...n, is_read: true })),
      }))
      window.dispatchEvent(new CustomEvent('notifications-updated'))
    } catch { /* ignore */ }
  }, [])

  const unreadCount = state.notifications.filter(n => !n.is_read).length
  const hasMore = state.notifications.length < state.total

  return { ...state, unreadCount, hasMore, loadMore, refetch: fetchData, markRead, markAllRead }
}
