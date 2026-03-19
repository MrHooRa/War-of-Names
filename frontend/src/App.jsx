import { useState, useEffect } from 'react'
import AppLayout from './components/AppLayout'

export default function App() {
  const [gameInfo, setGameInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/game-info')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setGameInfo(data.data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <AppLayout
      activeItem="home"
      seasonText={gameInfo?.current_season}
    >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-8">
        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-10 h-10 border-4 border-brand-teal/20 border-t-brand-teal rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-500 dark:text-gray-400 font-bold text-sm">جاري التحميل...</p>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="max-w-md mx-auto mt-12 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6 text-center">
            <iconify-icon icon="lucide:alert-triangle" class="text-3xl text-brand-danger mb-3"></iconify-icon>
            <p className="font-bold text-brand-danger mb-1">فشل الاتصال بالخادم</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">{error}</p>
          </div>
        )}

        {/* Success — Dashboard hero section matching template style */}
        {gameInfo && (
          <>
            {/* Announcement banner — from template pattern */}
            {gameInfo.announcement && (
              <div className="bg-brand-teal/5 dark:bg-brand-slate/10 border border-brand-teal/10 dark:border-brand-slate/20 rounded-2xl p-4 mb-6 flex items-center gap-3">
                <div className="w-9 h-9 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <iconify-icon icon="lucide:megaphone" class="text-brand-teal dark:text-brand-slate text-lg"></iconify-icon>
                </div>
                <p className="text-sm font-bold text-gray-700 dark:text-gray-300">
                  {gameInfo.announcement}
                </p>
              </div>
            )}

            {/* Hero card — matches template dashboard hero structure */}
            <div className="bg-white dark:bg-brand-card-dark rounded-3xl border border-gray-200 dark:border-gray-800 shadow-sm p-6 md:p-8 mb-6">
              <div className="flex flex-col md:flex-row items-center gap-6">
                {/* Player avatar area — from template */}
                <div className="w-20 h-20 bg-brand-teal/10 dark:bg-brand-slate/20 border-2 border-brand-teal/20 dark:border-brand-slate/30 rounded-2xl flex items-center justify-center">
                  <iconify-icon icon="lucide:swords" class="text-4xl text-brand-teal dark:text-brand-slate"></iconify-icon>
                </div>

                <div className="text-center md:text-right flex-1">
                  <h1 className="font-display text-2xl md:text-3xl font-black text-gray-900 dark:text-white mb-1">
                    {gameInfo.title}
                  </h1>
                  {gameInfo.subtitle && (
                    <p className="text-gray-500 dark:text-gray-400 font-bold text-sm md:text-base">
                      {gameInfo.subtitle}
                    </p>
                  )}
                </div>

                {/* Status badge — from template pattern */}
                <div className="flex items-center gap-3">
                  {gameInfo.current_season && (
                    <span className="bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate px-4 py-2 rounded-xl text-sm font-black">
                      {gameInfo.current_season}
                    </span>
                  )}
                  <span
                    className={`px-4 py-2 rounded-xl text-sm font-black text-white ${
                      gameInfo.status === 'active'
                        ? 'bg-brand-success'
                        : 'bg-brand-danger'
                    }`}
                  >
                    {gameInfo.status === 'active' ? 'نشط' : 'متوقف'}
                  </span>
                </div>
              </div>
            </div>

            {/* Stats grid — matching template dashboard pattern */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-brand-card-dark rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm p-5 text-center smooth-transition hover:shadow-md hover:-translate-y-0.5">
                <iconify-icon icon="lucide:database" class="text-2xl text-brand-teal dark:text-brand-slate mb-2"></iconify-icon>
                <p className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-1">قاعدة البيانات</p>
                <p className="font-heading text-lg font-black text-brand-success">متصلة</p>
              </div>
              <div className="bg-white dark:bg-brand-card-dark rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm p-5 text-center smooth-transition hover:shadow-md hover:-translate-y-0.5">
                <iconify-icon icon="lucide:server" class="text-2xl text-brand-teal dark:text-brand-slate mb-2"></iconify-icon>
                <p className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-1">الخادم</p>
                <p className="font-heading text-lg font-black text-brand-success">يعمل</p>
              </div>
              <div className="bg-white dark:bg-brand-card-dark rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm p-5 text-center smooth-transition hover:shadow-md hover:-translate-y-0.5">
                <iconify-icon icon="lucide:layout-dashboard" class="text-2xl text-brand-teal dark:text-brand-slate mb-2"></iconify-icon>
                <p className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-1">الواجهة</p>
                <p className="font-heading text-lg font-black text-brand-success">متصلة</p>
              </div>
              <div className="bg-white dark:bg-brand-card-dark rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm p-5 text-center smooth-transition hover:shadow-md hover:-translate-y-0.5">
                <iconify-icon icon="lucide:container" class="text-2xl text-brand-teal dark:text-brand-slate mb-2"></iconify-icon>
                <p className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-1">Docker</p>
                <p className="font-heading text-lg font-black text-brand-success">يعمل</p>
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  )
}
