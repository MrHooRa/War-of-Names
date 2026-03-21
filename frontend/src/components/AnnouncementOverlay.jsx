/**
 * AnnouncementOverlay — cinematic modal overlay for admin announcements.
 *
 * Fetches active announcements from /api/announcements, respects
 * dismissed state via localStorage, and renders a premium overlay
 * per announcement with style-driven theming.
 *
 * Styles: info (teal), success (green), warning (amber), danger (red), celebration (purple+gold)
 */

import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'

const DISMISSED_KEY = 'won_dismissed_announcements'

function getDismissed() {
  try {
    return JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]')
  } catch {
    return []
  }
}

function dismissAnnouncement(id) {
  const dismissed = getDismissed()
  if (!dismissed.includes(id)) {
    dismissed.push(id)
    localStorage.setItem(DISMISSED_KEY, JSON.stringify(dismissed))
  }
}

const STYLE_CONFIG = {
  info: {
    icon: 'lucide:megaphone',
    iconColor: 'text-brand-teal',
    bg: 'from-brand-teal/10 to-transparent',
    border: 'border-brand-teal/20',
    accent: 'bg-brand-teal',
    ctaBg: 'bg-brand-teal hover:bg-brand-teal-hover',
  },
  success: {
    icon: 'lucide:party-popper',
    iconColor: 'text-brand-success',
    bg: 'from-brand-success/10 to-transparent',
    border: 'border-brand-success/20',
    accent: 'bg-brand-success',
    ctaBg: 'bg-brand-success hover:bg-emerald-600',
  },
  warning: {
    icon: 'lucide:alert-triangle',
    iconColor: 'text-amber-500',
    bg: 'from-amber-500/10 to-transparent',
    border: 'border-amber-500/20',
    accent: 'bg-amber-500',
    ctaBg: 'bg-amber-500 hover:bg-amber-600',
  },
  danger: {
    icon: 'lucide:shield-alert',
    iconColor: 'text-brand-danger',
    bg: 'from-brand-danger/10 to-transparent',
    border: 'border-brand-danger/20',
    accent: 'bg-brand-danger',
    ctaBg: 'bg-brand-danger hover:bg-red-600',
  },
  celebration: {
    icon: 'lucide:crown',
    iconColor: 'text-purple-500',
    bg: 'from-purple-500/10 via-amber-500/5 to-transparent',
    border: 'border-purple-500/20',
    accent: 'bg-gradient-to-r from-purple-500 to-amber-500',
    ctaBg: 'bg-purple-600 hover:bg-purple-700',
  },
}

function AnnouncementModal({ announcement, onDismiss }) {
  const style = STYLE_CONFIG[announcement.style] || STYLE_CONFIG.info
  const isCelebration = announcement.style === 'celebration'

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 animate-[fadeIn_0.2s_ease]"
      onClick={(e) => {
        if (e.target === e.currentTarget && announcement.is_dismissible) onDismiss()
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-white dark:bg-brand-card-dark rounded-2xl shadow-2xl dark:shadow-black/40 overflow-hidden animate-[slideUpFade_0.4s_cubic-bezier(0.16,1,0.3,1)]">
        {/* Top accent bar */}
        <div className={`h-1.5 w-full ${style.accent}`} />

        {/* Gradient header glow */}
        <div className={`absolute top-0 left-0 right-0 h-32 bg-gradient-to-b ${style.bg} pointer-events-none`} />

        <div className="relative p-6 md:p-8">
          {/* Icon */}
          <div className="flex justify-center mb-5">
            <div className={`w-16 h-16 rounded-2xl ${style.accent} bg-opacity-10 flex items-center justify-center`}>
              <iconify-icon icon={style.icon} class={`text-3xl ${style.iconColor}`}></iconify-icon>
            </div>
          </div>

          {/* Title */}
          <h2 className="font-heading font-black text-2xl md:text-3xl text-gray-900 dark:text-white text-center leading-tight">
            {announcement.title}
          </h2>

          {/* Subtitle */}
          {announcement.subtitle && (
            <p className="text-center text-sm font-bold text-gray-500 dark:text-gray-400 mt-2">
              {announcement.subtitle}
            </p>
          )}

          {/* Body */}
          {announcement.body && (
            <div className="mt-5 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-line">
                {announcement.body}
              </p>
            </div>
          )}

          {/* CTA + Dismiss */}
          <div className="mt-6 flex flex-col gap-3">
            {announcement.cta_label && announcement.cta_url && (
              <a
                href={announcement.cta_url}
                className={`btn-press w-full py-3 rounded-xl font-heading font-bold text-base text-white ${style.ctaBg} smooth-transition flex items-center justify-center gap-2 shadow-sm`}
              >
                <iconify-icon icon="lucide:external-link" class="text-base"></iconify-icon>
                {announcement.cta_label}
              </a>
            )}

            {announcement.is_dismissible && (
              <button
                onClick={onDismiss}
                className="w-full py-3 rounded-xl font-heading font-bold text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
              >
                فهمت، أغلق
              </button>
            )}
          </div>
        </div>

        {/* Celebration sparkles */}
        {isCelebration && (
          <div className="absolute top-4 left-4 right-4 flex justify-between pointer-events-none opacity-30">
            <iconify-icon icon="lucide:sparkles" class="text-xl text-amber-400 animate-pulse"></iconify-icon>
            <iconify-icon icon="lucide:sparkles" class="text-lg text-purple-400 animate-pulse" style={{ animationDelay: '0.5s' }}></iconify-icon>
            <iconify-icon icon="lucide:sparkles" class="text-xl text-amber-400 animate-pulse" style={{ animationDelay: '1s' }}></iconify-icon>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AnnouncementOverlay() {
  const [announcements, setAnnouncements] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    const competitionId = localStorage.getItem('won_active_competition')
    const params = new URLSearchParams()
    if (competitionId) params.set('competition_id', competitionId)

    apiFetch(`/api/announcements?${params}`)
      .then(res => {
        if (!res.data?.length) return
        const dismissed = getDismissed()
        const visible = res.data.filter(a => !dismissed.includes(a.id))
        setAnnouncements(visible)
      })
      .catch(() => {})
  }, [])

  if (!announcements.length || currentIndex >= announcements.length) return null

  const current = announcements[currentIndex]

  function handleDismiss() {
    dismissAnnouncement(current.id)
    setCurrentIndex(i => i + 1)
  }

  return <AnnouncementModal announcement={current} onDismiss={handleDismiss} />
}
