import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { trackEvent } from '../lib/analytics'

export default function JoinPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ invite_code: '', alias: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.invite_code.trim() || form.invite_code.trim().length < 4) {
      setError('رمز الدعوة غير صالح')
      return
    }
    if (!form.alias.trim() || form.alias.trim().length < 2) {
      setError('اللقب يجب أن يكون حرفين على الأقل')
      return
    }
    setLoading(true)
    try {
      await apiFetch('/api/join', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      trackEvent('competition_joined', { alias: form.alias })
      // Track landing ref conversion (fire-and-forget)
      const landingRef = sessionStorage.getItem('won_landing_ref')
      if (landingRef) {
        apiFetch('/api/landing-links/convert', {
          method: 'POST',
          body: JSON.stringify({ ref_token: landingRef }),
        }).catch(() => {})
        sessionStorage.removeItem('won_landing_ref')
      }
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

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 md:p-10 relative overflow-hidden">

          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-teal/5 dark:bg-brand-slate/5 -mr-16 -mt-16 rounded-full blur-2xl"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-brand-orange/5 -ml-12 -mb-12 rounded-full blur-xl"></div>

          <div className="relative z-10">
            <div className="mb-10 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-teal/10 dark:bg-brand-slate/10 text-brand-teal dark:text-brand-slate rounded-2xl mb-6">
                <iconify-icon icon="lucide:swords" class="text-3xl"></iconify-icon>
              </div>
              <h1 className="font-display text-3xl md:text-4xl font-black text-gray-900 dark:text-white mb-3 tracking-tight">إنضم للحرب!</h1>
              <p className="text-gray-500 dark:text-gray-400 font-medium">
                أدخل كود المسابقة واختر لقبك، لكن انتبه لحد يعرف من انت!
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Invite Code */}
              <div className="space-y-2">
                <label htmlFor="invite-code" className="font-heading text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">
                  كود الدعوة
                </label>
                <div className="relative">
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 flex items-center">
                    <iconify-icon icon="lucide:key" class="text-xl"></iconify-icon>
                  </span>
                  <input
                    type="text"
                    id="invite-code"
                    name="invite_code"
                    autoComplete="off"
                    autoCapitalize="characters"
                    spellCheck={false}
                    dir="ltr"
                    value={form.invite_code}
                    onChange={e => setForm(f => ({ ...f, invite_code: e.target.value }))}
                    placeholder="مثال: WAR2026"
                    required
                    className="w-full bg-gray-50 dark:bg-gray-900/50 border border-gray-300 dark:border-gray-700 py-4 pr-12 pl-4 rounded-2xl font-bold tracking-widest uppercase focus:outline-none focus:ring-4 focus:ring-brand-teal/10 dark:focus:ring-brand-slate/20 focus:border-brand-teal dark:focus:border-brand-slate smooth-transition text-gray-900 dark:text-white placeholder:text-gray-400 placeholder:font-normal placeholder:tracking-normal"
                  />
                </div>
              </div>

              {/* Warrior Name (Alias) */}
              <div className="space-y-2">
                <label htmlFor="warrior-name" className="font-heading text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">اللقب</label>
                <div className="relative">
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 flex items-center">
                    <iconify-icon icon="lucide:user" class="text-xl"></iconify-icon>
                  </span>
                  <input
                    type="text"
                    id="warrior-name"
                    name="alias"
                    autoComplete="nickname"
                    value={form.alias}
                    onChange={e => setForm(f => ({ ...f, alias: e.target.value }))}
                    placeholder="اكتب اسمك القتالي هنا..."
                    required
                    className="w-full bg-gray-50 dark:bg-gray-900/50 border border-gray-300 dark:border-gray-700 py-4 pr-12 pl-4 rounded-2xl font-bold focus:outline-none focus:ring-4 focus:ring-brand-teal/10 dark:focus:ring-brand-slate/20 focus:border-brand-teal dark:focus:border-brand-slate smooth-transition text-gray-900 dark:text-white placeholder:text-gray-400 placeholder:font-normal"
                  />
                </div>
                <p className="text-[10px] text-gray-500 dark:text-gray-400 mr-2">سيظهر هذا اللقب للمنافسين الآخرين في هذه المسابقة فقط.</p>
              </div>

              {error && (
                <p role="alert" className="text-brand-danger text-sm font-bold text-center py-3 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-800/30">
                  {error}
                </p>
              )}

              {/* Submit */}
              <div className="pt-4">
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
                  ) : (
                    <>
                      انضمام للمسابقة
                      <iconify-icon icon="lucide:arrow-left" class="text-xl"></iconify-icon>
                    </>
                  )}
                </button>
              </div>
            </form>

            <div className="mt-8 pt-8 border-t border-gray-100 dark:border-gray-800 flex justify-center">
              <Link to="/register" className="flex items-center gap-2 text-brand-teal dark:text-brand-slate hover:underline font-bold text-sm smooth-transition">
                <iconify-icon icon="lucide:chevron-right"></iconify-icon>
                العودة للخطوة السابقة
              </Link>
            </div>
          </div>
        </div>

        <p className="mt-8 text-center text-sm font-bold text-gray-500 dark:text-gray-400">ما عندك كود؟ دورلك على واحد</p>
      </div>
    </div>
  )
}
