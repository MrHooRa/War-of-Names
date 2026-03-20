import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { apiFetch } from '../lib/api'

export default function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', real_name: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const json = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      login(json.data)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col items-center px-4 pb-20">
      <div className="w-full max-w-lg">

        {/* Progress Indicator */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex-1 flex flex-col gap-2">
            <div className="flex justify-between items-end mb-1">
              <span className="text-xs font-heading font-black text-brand-teal dark:text-brand-slate uppercase tracking-widest">المرحلة الأولى</span>
              <span className="text-[10px] font-bold text-gray-400">50% مكتمل</span>
            </div>
            <div className="h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full bg-brand-teal dark:bg-brand-slate w-1/2 rounded-full"></div>
            </div>
          </div>
        </div>

        {/* Registration Card */}
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl shadow-xl p-8 md:p-10 relative overflow-hidden">
          <Link to="/" className="absolute top-6 left-6 z-20 text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate smooth-transition flex items-center gap-1.5 text-sm font-bold bg-gray-50 dark:bg-gray-800/50 hover:bg-brand-teal/10 dark:hover:bg-brand-slate/20 px-3 py-1.5 rounded-lg border border-transparent hover:border-brand-teal/20 dark:hover:border-brand-slate/20">
            <iconify-icon icon="lucide:arrow-right" class="text-lg"></iconify-icon>
            <span className="hidden sm:inline">رجوع</span>
          </Link>

          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-teal/5 dark:bg-brand-slate/5 rounded-full -translate-y-1/2 translate-x-1/2"></div>

          <div className="relative">
            <h1 className="font-display text-3xl font-black text-gray-800 dark:text-white mb-2">
              إنشاء حساب لاعب
            </h1>
            <p className="text-gray-500 dark:text-gray-400 font-medium mb-8">
              أدخل بياناتك الأساسية للبدء في رحلة الغزو والسيطرة
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Username */}
              <div className="space-y-2">
                <label htmlFor="username" className="block text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">اسم المستخدم (المعرف)</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand-teal smooth-transition">
                    <iconify-icon icon="lucide:at-sign" class="text-lg"></iconify-icon>
                  </div>
                  <input
                    type="text"
                    id="username"
                    value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    placeholder="warrior_2024"
                    required
                    className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 pr-11 pl-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:focus:border-brand-slate dark:focus:ring-brand-slate/20 transition-all text-gray-800 dark:text-white placeholder:text-gray-400"
                  />
                </div>
                <p className="text-[10px] text-gray-400 mr-1">هذا هو اسم حسابك لتتمكن من الدخول</p>
              </div>

              {/* Real Name */}
              <div className="space-y-2">
                <label htmlFor="fullname" className="block text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">الاسم الحقيقي أو المعروف</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand-teal smooth-transition">
                    <iconify-icon icon="lucide:user" class="text-lg"></iconify-icon>
                  </div>
                  <input
                    type="text"
                    id="fullname"
                    value={form.real_name}
                    onChange={e => setForm(f => ({ ...f, real_name: e.target.value }))}
                    placeholder="سلطان بن محمد"
                    required
                    className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 pr-11 pl-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:focus:border-brand-slate dark:focus:ring-brand-slate/20 transition-all text-gray-800 dark:text-white placeholder:text-gray-400"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-bold text-gray-700 dark:text-gray-300 mr-1">كلمة المرور</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand-teal smooth-transition">
                    <iconify-icon icon="lucide:lock" class="text-lg"></iconify-icon>
                  </div>
                  <input
                    type="password"
                    id="password"
                    value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    placeholder="••••••••"
                    required
                    className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3.5 pr-11 pl-12 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:focus:border-brand-slate dark:focus:ring-brand-slate/20 transition-all text-gray-800 dark:text-white placeholder:text-gray-400"
                  />
                  <button type="button" className="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-400 hover:text-brand-teal transition-colors">
                    <iconify-icon icon="lucide:eye" class="text-lg"></iconify-icon>
                  </button>
                </div>
              </div>

              {error && (
                <p className="text-brand-danger text-sm font-bold text-center py-3 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-800/30">
                  {error}
                </p>
              )}

              {/* Submit Action */}
              <div className="pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-press w-full bg-brand-teal hover:bg-brand-teal-hover text-white dark:bg-brand-slate dark:hover:bg-brand-slate/80 py-4 rounded-xl font-heading font-black text-lg shadow-lg shadow-brand-teal/20 hover:shadow-md transition-all flex items-center justify-center gap-3 disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <iconify-icon icon="lucide:loader-2" class="text-xl animate-spin"></iconify-icon>
                      جارٍ التسجيل...
                    </>
                  ) : (
                    <>
                      الخطوة التالية
                      <iconify-icon icon="lucide:chevron-left" class="text-xl"></iconify-icon>
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Login Link */}
            <div className="mt-10 text-center">
              <p className="text-gray-500 dark:text-gray-400 font-bold">
                لديك حساب بالفعل؟
                <Link to="/login" className="text-brand-teal dark:text-brand-slate hover:text-brand-teal-hover hover:underline mr-1 smooth-transition inline-flex items-center gap-1">
                  سجل دخولك من هنا
                  <iconify-icon icon="lucide:arrow-left" class="text-sm rtl:rotate-180"></iconify-icon>
                </Link>
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
