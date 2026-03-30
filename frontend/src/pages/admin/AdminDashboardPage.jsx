import { Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'
import { formatNumber } from '../../lib/numbers'

function StatCard({ icon, label, value, color = 'text-brand-teal dark:text-brand-slate', to }) {
  const inner = (
    <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 flex items-center gap-4 hover:shadow-md smooth-transition">
      <div className={`w-12 h-12 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center ${color}`}>
        <iconify-icon icon={icon} class="text-2xl"></iconify-icon>
      </div>
      <div>
        <div className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest">{label}</div>
        <div className="font-display text-2xl font-black text-gray-900 dark:text-white">{value}</div>
      </div>
    </div>
  )
  if (to) return <Link to={to}>{inner}</Link>
  return inner
}

function StatusBadge({ status }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success',
    open: 'bg-brand-success/10 text-brand-success',
    draft: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    paused: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
    completed: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
    succeeded: 'bg-brand-success/10 text-brand-success',
    failed: 'bg-brand-danger/10 text-brand-danger',
    blocked: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>
      {status}
    </span>
  )
}

export default function AdminDashboardPage() {
  const { data, loading, error } = useAdminData('/api/admin/dashboard')

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal dark:text-brand-slate animate-spin"></iconify-icon>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <iconify-icon icon="lucide:alert-circle" class="text-4xl text-brand-danger"></iconify-icon>
        <p className="text-gray-500 dark:text-gray-400 font-bold">{error}</p>
      </div>
    )
  }

  const d = data

  return (
    <div className="space-y-8 max-w-7xl">
      {/* Page Header */}
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">لوحة التحكم</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">نظرة عامة على حالة اللعبة</p>
      </div>

      {/* Active State Banner */}
      {d.active_competition && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <iconify-icon icon="lucide:trophy" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
              <span className="font-bold text-gray-700 dark:text-gray-300">{d.active_competition.name}</span>
              <StatusBadge status={d.active_competition.status} />
            </div>
            {d.active_season && (
              <>
                <span className="text-gray-300 dark:text-gray-700">|</span>
                <div className="flex items-center gap-2">
                  <iconify-icon icon="lucide:calendar" class="text-gray-400"></iconify-icon>
                  <span className="font-bold text-gray-600 dark:text-gray-400">{d.active_season.name}</span>
                  <StatusBadge status={d.active_season.status} />
                </div>
              </>
            )}
            {d.active_cycle && (
              <>
                <span className="text-gray-300 dark:text-gray-700">|</span>
                <div className="flex items-center gap-2">
                  <iconify-icon icon="lucide:repeat" class="text-gray-400"></iconify-icon>
                  <span className="font-bold text-gray-600 dark:text-gray-400">{d.active_cycle.label}</span>
                  <StatusBadge status={d.active_cycle.status} />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon="lucide:users" label="اللاعبون" value={d.total_members} to="/admin/players" />
        <StatCard icon="lucide:swords" label="الهجمات" value={d.total_attacks} color="text-brand-orange" to="/admin/attacks" />
        <StatCard icon="lucide:book-check" label="الإجابات" value={d.total_answers} color="text-amber-500" to="/admin/quiz" />
        <StatCard icon="lucide:shopping-bag" label="المشتريات" value={d.total_purchases} color="text-purple-500" to="/admin/store" />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon="lucide:user-plus" label="الحسابات" value={d.total_accounts} />
        <StatCard icon="lucide:target" label="هجمات ناجحة" value={d.successful_attacks} color="text-brand-success" />
        <StatCard icon="lucide:check-circle" label="إجابات صحيحة" value={d.correct_answers} color="text-brand-success" />
        <StatCard icon="lucide:alert-triangle" label="مفلسون" value={d.bankrupt_count} color="text-brand-danger" />
      </div>

      {/* Financial + Recent */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Financial Summary */}
        <div className="lg:col-span-4 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <iconify-icon icon="lucide:receipt" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            ملخص مالي
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-brand-success/5 rounded-xl">
              <span className="text-sm font-bold text-gray-600 dark:text-gray-400">إجمالي الإيداعات</span>
              <span className="font-heading font-black text-brand-success">+{formatNumber(d.total_credits)}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-brand-danger/5 rounded-xl">
              <span className="text-sm font-bold text-gray-600 dark:text-gray-400">إجمالي الخصومات</span>
              <span className="font-heading font-black text-brand-danger">-{formatNumber(d.total_debits)}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
              <span className="text-sm font-bold text-gray-600 dark:text-gray-400">إشعارات غير مقروءة</span>
              <span className="font-heading font-black text-gray-900 dark:text-white">{d.unread_notifications}</span>
            </div>
          </div>
        </div>

        {/* Recent Attacks */}
        <div className="lg:col-span-8 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
              <iconify-icon icon="lucide:swords" class="text-brand-orange"></iconify-icon>
              آخر الهجمات
            </h2>
            <Link to="/admin/attacks" className="text-xs font-bold text-brand-teal dark:text-brand-slate hover:underline">عرض الكل</Link>
          </div>
          {d.recent_attacks?.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">لا توجد هجمات بعد</p>
          ) : (
            <div className="space-y-2">
              {d.recent_attacks?.map(a => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl text-sm">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={a.outcome} />
                    <span className="font-bold text-gray-700 dark:text-gray-300">{a.attacker_alias}</span>
                    <iconify-icon icon="lucide:arrow-left" class="text-gray-400 text-xs"></iconify-icon>
                    <span className="font-bold text-gray-700 dark:text-gray-300">{a.target_alias}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {a.reward_amount > 0 && (
                      <span className="text-brand-success font-black text-xs">+{a.reward_amount}</span>
                    )}
                    {a.penalty_amount > 0 && (
                      <span className="text-brand-danger font-black text-xs">-{a.penalty_amount}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
