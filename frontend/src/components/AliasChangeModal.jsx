/**
 * AliasChangeModal — lets a player redeem their alias-change permission.
 *
 * Props:
 *  - activationId: string (the ItemActivation that granted the permission)
 *  - currentAlias: string
 *  - competitionId: string | null
 *  - onClose: () => void
 *  - onSuccess: (newAlias: string) => void
 */

import { useState } from 'react'
import { apiFetch } from '../lib/api'

export default function AliasChangeModal({ activationId, currentAlias, competitionId, onClose, onSuccess }) {
  const [newAlias, setNewAlias] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = newAlias.trim()
    if (trimmed.length < 2) {
      setError('اللقب يجب أن يكون حرفين على الأقل')
      return
    }
    if (trimmed === currentAlias) {
      setError('اللقب الجديد مطابق للقبك الحالي')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const qs = competitionId ? `?competition_id=${competitionId}` : ''
      const res = await apiFetch(`/api/me/change-alias${qs}`, {
        method: 'POST',
        body: JSON.stringify({ new_alias: trimmed, activation_id: activationId }),
      })
      onSuccess(res.data?.new_alias || trimmed)
    } catch (err) {
      setError(err.message || 'حدث خطأ أثناء تغيير اللقب')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <form
        onSubmit={handleSubmit}
        className="relative bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-3xl shadow-2xl w-full max-w-md p-8 space-y-6"
      >
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 mx-auto bg-brand-teal/10 dark:bg-brand-slate/20 rounded-2xl flex items-center justify-center">
            <iconify-icon icon="lucide:pen-line" class="text-2xl text-brand-teal dark:text-brand-slate"></iconify-icon>
          </div>
          <h2 className="font-heading font-black text-xl text-gray-900 dark:text-white">تغيير اللقب</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 font-bold">
            لقبك الحالي: <span className="text-brand-teal dark:text-brand-slate">{currentAlias}</span>
          </p>
        </div>

        {/* Input */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-gray-600 dark:text-gray-400">اللقب الجديد</label>
          <input
            type="text"
            value={newAlias}
            onChange={(e) => setNewAlias(e.target.value)}
            placeholder="اكتب لقبك الجديد..."
            maxLength={30}
            autoFocus
            className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 font-bold text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-brand-teal dark:focus:border-brand-slate focus:ring-2 focus:ring-brand-teal/20 smooth-transition"
          />
          <p className="text-[11px] text-gray-400 font-bold">حرفين على الأقل، 30 حرف كحد أقصى</p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/10 text-red-500 dark:text-red-400 px-4 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2">
            <iconify-icon icon="lucide:alert-circle" class="text-base"></iconify-icon>
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 font-bold text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 smooth-transition"
          >
            إلغاء
          </button>
          <button
            type="submit"
            disabled={loading || newAlias.trim().length < 2}
            className="flex-1 px-4 py-3 rounded-xl bg-brand-teal hover:bg-brand-teal-hover text-white font-heading font-black smooth-transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon="lucide:check"></iconify-icon>
            )}
            {loading ? 'جارٍ التغيير...' : 'تأكيد التغيير'}
          </button>
        </div>
      </form>
    </div>
  )
}
