/**
 * InviteLinkPage — Landing page for invite link join flow.
 *
 * Route: /invite/:token
 *
 * Flow:
 *  1. Validates the invite link token via GET /api/join/link/{token}
 *  2. Shows competition info and alias input
 *  3. If not logged in, redirects to login with return URL
 *  4. On submit, POST /api/join/link/{token} with alias
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { apiFetch } from '../lib/api'

export default function InviteLinkPage() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  const [competitionInfo, setCompetitionInfo] = useState(null)
  const [validating, setValidating] = useState(true)
  const [invalidReason, setInvalidReason] = useState('')
  const [alias, setAlias] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Validate the invite link on mount
  useEffect(() => {
    apiFetch(`/api/join/link/${token}`)
      .then(json => {
        if (json.data) {
          setCompetitionInfo(json.data)
          if (!json.data.joinable) {
            setInvalidReason('التسجيل مغلق في هذه المنافسة حالياً')
          }
        }
      })
      .catch(err => {
        const detail = err.data
        setInvalidReason(detail?.message || 'رابط الدعوة غير صالح أو منتهي الصلاحية')
      })
      .finally(() => setValidating(false))
  }, [token])

  async function handleJoin(e) {
    e.preventDefault()

    if (!isAuthenticated) {
      // Redirect to login, come back after
      localStorage.setItem('won_invite_return', `/invite/${token}`)
      navigate('/login')
      return
    }

    setError('')
    setLoading(true)
    try {
      await apiFetch(`/api/join/link/${token}`, {
        method: 'POST',
        body: JSON.stringify({ alias }),
      })
      navigate('/lobby', { replace: true })
    } catch (err) {
      const detail = err.data
      if (detail && detail.message) {
        setError(detail.message)
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  if (validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-light-bg dark:bg-brand-dark-bg">
        <div className="flex flex-col items-center gap-4">
          <iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon>
          <p className="text-gray-500 dark:text-gray-400 font-bold">جارٍ التحقق من رابط الدعوة...</p>
        </div>
      </div>
    )
  }

  if (invalidReason) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-light-bg dark:bg-brand-dark-bg px-4">
        <div className="w-full max-w-md bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 text-center">
          <iconify-icon icon="lucide:link-2-off" class="text-5xl text-brand-danger mb-4"></iconify-icon>
          <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white mb-3">رابط غير صالح</h1>
          <p className="text-gray-500 dark:text-gray-400 font-bold mb-6">{invalidReason}</p>
          <button
            onClick={() => navigate('/')}
            className="text-brand-teal font-bold hover:underline"
          >
            العودة للصفحة الرئيسية
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-light-bg dark:bg-brand-dark-bg px-4">
      <div className="w-full max-w-md bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 md:p-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-teal/10 dark:bg-brand-slate/10 text-brand-teal dark:text-brand-slate rounded-2xl mb-6">
            <iconify-icon icon="lucide:link" class="text-3xl"></iconify-icon>
          </div>
          <h1 className="font-display text-2xl md:text-3xl font-black text-gray-900 dark:text-white mb-3">
            دعوة للانضمام
          </h1>
          {competitionInfo && (
            <div className="bg-brand-teal/5 dark:bg-brand-slate/10 border border-brand-teal/20 dark:border-brand-slate/20 rounded-xl p-4 mt-4">
              <p className="font-heading font-bold text-brand-teal dark:text-brand-slate text-lg">
                {competitionInfo.name}
              </p>
              {competitionInfo.description && (
                <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">{competitionInfo.description}</p>
              )}
            </div>
          )}
        </div>

        <form onSubmit={handleJoin} className="space-y-6">
          <div className="space-y-2">
            <label className="font-heading text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">اللقب القتالي</label>
            <div className="relative">
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400">
                <iconify-icon icon="lucide:user" class="text-xl"></iconify-icon>
              </span>
              <input
                type="text"
                value={alias}
                onChange={e => setAlias(e.target.value)}
                placeholder="اختر لقبك القتالي..."
                required
                className="w-full bg-gray-50 dark:bg-gray-900/50 border border-gray-300 dark:border-gray-700 py-4 pr-12 pl-4 rounded-2xl font-bold focus:outline-none focus:ring-4 focus:ring-brand-teal/10 dark:focus:ring-brand-slate/20 focus:border-brand-teal dark:focus:border-brand-slate smooth-transition text-gray-900 dark:text-white placeholder:text-gray-400"
              />
            </div>
            <p className="text-[10px] text-gray-500 dark:text-gray-400 mr-2">سيظهر هذا اللقب للمنافسين الآخرين.</p>
          </div>

          {error && (
            <p className="text-brand-danger text-sm font-bold text-center py-3 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-800/30">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-press w-full bg-brand-teal hover:bg-brand-teal-hover text-white dark:bg-brand-slate/80 dark:hover:bg-brand-slate py-4 rounded-2xl font-heading font-black text-lg shadow-lg shadow-brand-teal/20 dark:shadow-brand-slate/20 flex items-center justify-center gap-2 smooth-transition disabled:opacity-60"
          >
            {loading ? (
              <>
                <iconify-icon icon="lucide:loader-2" class="text-xl animate-spin"></iconify-icon>
                جارٍ الانضمام...
              </>
            ) : !isAuthenticated ? (
              <>
                <iconify-icon icon="lucide:log-in" class="text-xl"></iconify-icon>
                تسجيل الدخول للانضمام
              </>
            ) : (
              <>
                <iconify-icon icon="lucide:swords" class="text-xl"></iconify-icon>
                انضمام للمنافسة
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
