import { useState, useEffect } from 'react'
import { getConsent, setConsent } from '../lib/analytics'

export default function ConsentBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Show banner if user hasn't decided yet
    const consent = getConsent()
    if (consent === null) {
      // Delay 2s so it doesn't interrupt first impression
      const timer = setTimeout(() => setVisible(true), 2000)
      return () => clearTimeout(timer)
    }
  }, [])

  if (!visible) return null

  function handleAccept() {
    setConsent(true)
    setVisible(false)
  }

  function handleReject() {
    setConsent(false)
    setVisible(false)
  }

  return (
    <div className="fixed bottom-16 md:bottom-4 left-4 right-4 z-[55] flex justify-center pointer-events-none">
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-xl p-4 max-w-lg w-full pointer-events-auto">
        <div className="flex items-start gap-3">
          <iconify-icon icon="lucide:shield-check" class="text-2xl text-brand-teal dark:text-brand-slate flex-shrink-0 mt-0.5"></iconify-icon>
          <div className="flex-1">
            <p className="text-sm font-bold text-gray-900 dark:text-white mb-1">نستخدم تقنيات تحليل لتحسين تجربتك</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              نستخدم أدوات تحليل لفهم كيفية استخدام المنصة وتحسينها. يمكنك الموافقة أو الرفض.
            </p>
            <div className="flex gap-2">
              <button onClick={handleAccept}
                className="px-4 py-1.5 rounded-lg bg-brand-teal text-white text-xs font-bold hover:bg-brand-teal-hover smooth-transition">
                قبول
              </button>
              <button onClick={handleReject}
                className="px-4 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition">
                رفض
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
