/**
 * CycleCountdown — Shows remaining time in the active cycle.
 * Displays a countdown badge when cycle_ends_at is set, plus next-cycle preview.
 */

import { useState, useEffect } from 'react'

function formatTimeLeft(ms) {
  if (ms <= 0) return null
  const totalSeconds = Math.floor(ms / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (days > 0) return `${days} يوم ${hours} ساعة`
  if (hours > 0) return `${hours} ساعة ${minutes} دقيقة`
  if (minutes > 0) return `${minutes}:${String(seconds).padStart(2, '0')}`
  return `${seconds} ثانية`
}

export default function CycleCountdown({ cycleEndsAt, cycleLabel, nextCycleLabel }) {
  const [timeLeft, setTimeLeft] = useState(null)

  useEffect(() => {
    if (!cycleEndsAt) return

    function tick() {
      const ms = new Date(cycleEndsAt).getTime() - Date.now()
      setTimeLeft(ms > 0 ? ms : 0)
    }

    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [cycleEndsAt])

  if (!cycleEndsAt || timeLeft === null) return null

  const formatted = formatTimeLeft(timeLeft)
  const isExpired = timeLeft <= 0
  const isUrgent = timeLeft > 0 && timeLeft < 3600000 // less than 1 hour

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-bold border smooth-transition ${
      isExpired
        ? 'bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-500'
        : isUrgent
          ? 'bg-brand-orange/10 border-brand-orange/20 text-brand-orange'
          : 'bg-brand-teal/10 dark:bg-brand-slate/10 border-brand-teal/20 dark:border-brand-slate/20 text-brand-teal dark:text-brand-slate'
    }`}>
      <iconify-icon
        icon={isExpired ? 'lucide:clock' : 'lucide:timer'}
        class={`text-lg ${isUrgent && !isExpired ? 'animate-pulse' : ''}`}
      ></iconify-icon>
      <div className="flex flex-col">
        {isExpired ? (
          <span>انتهت الدورة الحالية</span>
        ) : (
          <span>
            {cycleLabel && <span className="text-gray-500 dark:text-gray-400 ml-1">{cycleLabel} —</span>}
            باقي {formatted}
          </span>
        )}
        {nextCycleLabel && (
          <span className="text-[10px] text-gray-400 font-bold">
            الدورة التالية: {nextCycleLabel}
          </span>
        )}
      </div>
    </div>
  )
}
