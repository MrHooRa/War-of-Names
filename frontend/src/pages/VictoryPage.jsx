import { Link, useLocation } from 'react-router-dom'

export default function VictoryPage() {
  const { state } = useLocation()
  const reward = state?.reward_amount ?? 0
  const targetRealName = state?.target_real_name ?? '???'
  const attackerBalanceAfter = state?.attacker_balance_after ?? null

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto px-4 py-12 md:py-20 flex flex-col items-center">
      <div className="w-full flex flex-col items-center text-center space-y-12">

        {/* Hero Section */}
        <div className="relative">
          <div className="absolute inset-0 bg-brand-success/15 dark:bg-brand-success/10 blur-3xl rounded-full"></div>
          <div className="relative floating">
            <div className="bg-gradient-to-br from-brand-success to-emerald-600 text-white w-24 h-24 md:w-32 md:h-32 rounded-full flex items-center justify-center shadow-xl shadow-brand-success/20 border-4 border-white dark:border-brand-card-dark mx-auto z-10 relative">
              <iconify-icon icon="lucide:swords" class="text-4xl md:text-5xl drop-shadow-md"></iconify-icon>
            </div>
          </div>
          <h1 className="font-display text-5xl md:text-7xl font-black text-brand-success mt-8 tracking-tight drop-shadow-sm uppercase">
            نصر ساحق!
          </h1>
          <p className="text-gray-500 dark:text-gray-400 font-medium text-lg md:text-xl mt-4 max-w-md mx-auto">
            لقد كشفت هوية {targetRealName} وأثبت أن اسمك هو الأقوى في الميدان.
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full">

          {/* Points Earned */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl p-8 shadow-sm hover:shadow-md dark:hover:shadow-black/20 flex flex-col items-center gap-4 smooth-transition hover:-translate-y-1 group">
            <span className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest group-hover:text-brand-teal transition-colors">النقاط المكتسبة</span>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 dark:bg-brand-teal/10 flex items-center justify-center text-brand-teal">
                <iconify-icon icon="lucide:zap" class="text-3xl"></iconify-icon>
              </div>
              <span className="font-display text-5xl md:text-6xl font-black text-gray-900 dark:text-white drop-shadow-sm">+{reward}</span>
            </div>
            <div className="h-px w-full bg-gray-100 dark:bg-gray-800 my-2"></div>
            <div className="flex justify-between w-full text-sm font-bold">
              <span className="text-gray-500 dark:text-gray-400">رصيدك الحالي:</span>
              <span className="text-brand-teal font-black">
                {attackerBalanceAfter !== null ? attackerBalanceAfter.toLocaleString('ar-EG') : '—'}
              </span>
            </div>
          </div>

          {/* Identity Revealed */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-3xl p-8 shadow-sm hover:shadow-md dark:hover:shadow-black/20 flex flex-col items-center gap-4 smooth-transition hover:-translate-y-1 group">
            <span className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest group-hover:text-amber-500 transition-colors">الهوية المكشوفة</span>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-500/10 flex items-center justify-center text-amber-500">
                <iconify-icon icon="lucide:user-check" class="text-3xl"></iconify-icon>
              </div>
              <span className="font-display text-3xl md:text-4xl font-black text-gray-900 dark:text-white drop-shadow-sm">{targetRealName}</span>
            </div>
            <div className="h-px w-full bg-gray-100 dark:bg-gray-800 my-2"></div>
            <div className="w-full text-center text-sm font-bold text-brand-success">
              تحقق التخمين بنجاح!
            </div>
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col md:flex-row gap-4 w-full pt-6">
          <Link to="/dashboard" className="flex-1 btn-press bg-brand-teal hover:bg-brand-teal-hover text-white py-4 md:py-5 rounded-2xl font-heading font-black text-lg shadow-lg shadow-brand-teal/20 smooth-transition text-center flex items-center justify-center gap-3">
            العودة للرئيسية
            <iconify-icon icon="lucide:arrow-left" class="text-xl"></iconify-icon>
          </Link>
          <Link to="/leaderboard" className="flex-1 btn-press bg-white dark:bg-brand-card-dark border-2 border-gray-200 hover:border-brand-teal dark:border-gray-700 dark:hover:border-brand-teal text-gray-700 hover:text-brand-teal dark:text-gray-300 dark:hover:text-brand-teal py-4 md:py-5 rounded-2xl font-heading font-black text-lg shadow-sm hover:shadow-md smooth-transition text-center flex items-center justify-center gap-3">
            قائمة المتصدرين
            <iconify-icon icon="lucide:trophy" class="text-xl"></iconify-icon>
          </Link>
        </div>
      </div>
    </div>
  )
}
