import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { apiFetch } from '../lib/api'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const json = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      login(json.data)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col items-center px-4 pb-20">
      <div className="w-full max-w-lg">

        {/* Logo */}
        <div className="flex justify-center mb-8">
          <img src="/main-logo-v1.png" alt="حرب الأسماء" className="w-48 h-auto drop-shadow-lg" />
        </div>

        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 md:p-10 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-teal/5 dark:bg-brand-slate/5 rounded-full -translate-y-1/2 translate-x-1/2"></div>

          <div className="relative">
            <h1 className="font-display text-3xl font-black text-gray-800 dark:text-white mb-2">
              تسجيل الدخول
            </h1>
            <p className="text-gray-500 dark:text-gray-400 font-medium mb-8">
              ادخل إلى ساحة المعركة
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Username */}
              <div className="space-y-2">
                <label htmlFor="login-username" className="block text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">اسم المستخدم</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand-teal smooth-transition">
                    <iconify-icon icon="lucide:at-sign" class="text-lg"></iconify-icon>
                  </div>
                  <input
                    type="text"
                    id="login-username"
                    value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    placeholder="warrior_2024"
                    required
                    className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 pr-11 pl-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:focus:border-brand-slate dark:focus:ring-brand-slate/20 transition-all text-gray-800 dark:text-white placeholder:text-gray-400"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label htmlFor="login-password" className="block text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">كلمة المرور</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand-teal smooth-transition">
                    <iconify-icon icon="lucide:lock" class="text-lg"></iconify-icon>
                  </div>
                  <input
                    type="password"
                    id="login-password"
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    placeholder="••••••••"
                    required
                    className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 pr-11 pl-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:focus:border-brand-slate dark:focus:ring-brand-slate/20 transition-all text-gray-800 dark:text-white placeholder:text-gray-400"
                  />
                </div>
              </div>

              {error && (
                <p className="text-brand-danger text-sm font-bold text-center py-3 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-800/30">
                  {error}
                </p>
              )}

              {/* Submit */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-press w-full bg-brand-teal hover:bg-brand-teal-hover text-white dark:bg-brand-slate dark:hover:bg-brand-slate/80 py-4 rounded-xl font-heading font-black text-lg shadow-lg shadow-brand-teal/20 hover:shadow-md transition-all flex items-center justify-center gap-3 disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <iconify-icon icon="lucide:loader-2" class="text-xl animate-spin"></iconify-icon>
                      جارٍ الدخول...
                    </>
                  ) : (
                    <>
                      <iconify-icon icon="lucide:log-in" class="text-xl"></iconify-icon>
                      دخول
                    </>
                  )}
                </button>
              </div>

              <p className="text-center text-sm text-gray-500 dark:text-gray-400 pt-2">
                ليس لديك حساب؟{' '}
                <Link to="/register" className="text-brand-teal dark:text-brand-slate font-bold hover:underline">سجّل الآن</Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
