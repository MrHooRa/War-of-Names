/**
 * CompetitionSwitcher — Dropdown to switch between joined competitions/servers.
 *
 * Shows current competition name + season/cycle info.
 * Dropdown lists all joined competitions with alias and balance.
 * On switch: updates localStorage, reloads page to refresh all context.
 *
 * Props:
 *  - variant: 'light' | 'dark' (styling variant for AppLayout vs LobbyPage)
 */

import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../lib/api'
import { formatNumber } from '../lib/numbers'

const STORAGE_KEY = 'won_active_competition'

export default function CompetitionSwitcher({ variant = 'light' }) {
  const [memberships, setMemberships] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const ref = useRef(null)

  const currentId = localStorage.getItem(STORAGE_KEY)

  useEffect(() => {
    apiFetch('/api/me/memberships')
      .then(json => setMemberships(json.data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const activeMems = memberships.filter(m => m.status === 'active')
  const current = activeMems.find(m => m.competition_id === currentId) || activeMems[0]

  if (loading || activeMems.length === 0) return null

  // Single competition — just show label, no dropdown
  if (activeMems.length === 1) {
    const isDark = variant === 'dark'
    return (
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm font-bold ${
        isDark
          ? 'bg-white/5 border border-white/10 text-gray-300'
          : 'bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
      }`}>
        <iconify-icon icon="lucide:server" class="text-base opacity-60"></iconify-icon>
        <span className="truncate max-w-[160px]">{current?.competition_name}</span>
      </div>
    )
  }

  function switchTo(mem) {
    if (mem.competition_id === currentId) {
      setOpen(false)
      return
    }
    localStorage.setItem(STORAGE_KEY, mem.competition_id)
    setOpen(false)
    // Reload to refresh all contexts
    window.location.reload()
  }

  const isDark = variant === 'dark'

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-bold smooth-transition ${
          isDark
            ? 'bg-white/5 border border-white/10 text-gray-200 hover:border-brand-teal/40 hover:bg-white/10'
            : 'bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:border-brand-teal dark:hover:border-brand-slate hover:bg-gray-100 dark:hover:bg-gray-700'
        }`}
      >
        <iconify-icon icon="lucide:server" class={`text-base ${isDark ? 'text-brand-teal' : 'text-brand-teal dark:text-brand-slate'}`}></iconify-icon>
        <span className="truncate max-w-[160px]">{current?.competition_name || 'اختر الخادم'}</span>
        <iconify-icon icon={open ? 'lucide:chevron-up' : 'lucide:chevron-down'} class="text-sm opacity-60"></iconify-icon>
      </button>

      {open && (
        <div className={`absolute top-full mt-2 w-72 rounded-2xl shadow-xl border z-[60] overflow-hidden ${
          isDark
            ? 'bg-[#151b29] border-white/10'
            : 'bg-white dark:bg-brand-card-dark border-gray-200 dark:border-gray-700'
        }`}>
          <div className={`px-4 py-2.5 text-[11px] font-bold uppercase tracking-widest border-b ${
            isDark
              ? 'text-gray-500 border-white/5'
              : 'text-gray-400 dark:text-gray-500 border-gray-100 dark:border-gray-800'
          }`}>
            المنافسات المنضمّة
          </div>
          <div className="max-h-64 overflow-y-auto">
            {activeMems.map(mem => {
              const isActive = mem.competition_id === currentId
              return (
                <button
                  key={mem.membership_id}
                  onClick={() => switchTo(mem)}
                  className={`w-full text-right px-4 py-3 smooth-transition flex items-center gap-3 ${
                    isDark
                      ? isActive
                        ? 'bg-brand-teal/10 text-white'
                        : 'text-gray-300 hover:bg-white/5'
                      : isActive
                        ? 'bg-brand-teal/5 dark:bg-brand-slate/10 text-gray-900 dark:text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                  }`}
                >
                  {isActive && (
                    <span className="w-2 h-2 rounded-full bg-brand-emerald shrink-0 shadow-[0_0_6px_rgba(16,185,129,0.6)]"></span>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-heading font-bold text-sm truncate">{mem.competition_name}</div>
                    <div className={`flex items-center gap-3 mt-0.5 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400 dark:text-gray-500'}`}>
                      <span>{mem.alias}</span>
                      <span className="flex items-center gap-1">
                        <iconify-icon icon="lucide:coins" class="text-amber-400 text-[10px]"></iconify-icon>
                        {formatNumber(mem.balance)}
                      </span>
                    </div>
                  </div>
                  {isActive && (
                    <iconify-icon icon="lucide:check" class={`text-sm ${isDark ? 'text-brand-teal' : 'text-brand-teal dark:text-brand-slate'}`}></iconify-icon>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
