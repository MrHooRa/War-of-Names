/**
 * AdminCompetitionContext — Stores the currently selected competition for all admin pages.
 *
 * Loads competition list from /api/admin/competitions on mount.
 * Persists selection in localStorage.
 * All competition-scoped admin pages read from this context.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../lib/api'

const AdminCompCtx = createContext(null)

const STORAGE_KEY = 'admin_selected_competition'

export function AdminCompetitionProvider({ children }) {
  const [competitions, setCompetitions] = useState([])
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem(STORAGE_KEY))
  const [loading, setLoading] = useState(true)

  // Load competition list
  useEffect(() => {
    apiFetch('/api/admin/competitions')
      .then(json => {
        const list = json.data || []
        setCompetitions(list)
        // Auto-select first active competition if nothing selected
        if (!selectedId && list.length > 0) {
          const active = list.find(c => c.status === 'active') || list[0]
          setSelectedId(active.id)
          localStorage.setItem(STORAGE_KEY, active.id)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const selectCompetition = useCallback((id) => {
    setSelectedId(id)
    localStorage.setItem(STORAGE_KEY, id)
  }, [])

  const refreshCompetitions = useCallback(() => {
    return apiFetch('/api/admin/competitions')
      .then(json => {
        setCompetitions(json.data || [])
        return json.data
      })
      .catch(() => [])
  }, [])

  const selected = competitions.find(c => c.id === selectedId) || null

  return (
    <AdminCompCtx.Provider value={{
      competitions,
      selected,
      selectedId,
      selectCompetition,
      refreshCompetitions,
      loading,
    }}>
      {children}
    </AdminCompCtx.Provider>
  )
}

export function useAdminCompetition() {
  const ctx = useContext(AdminCompCtx)
  if (!ctx) throw new Error('useAdminCompetition must be used inside AdminCompetitionProvider')
  return ctx
}
