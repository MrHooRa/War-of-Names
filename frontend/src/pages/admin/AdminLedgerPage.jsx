import { useState } from 'react'
import { Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'

const ENTRY_TYPE_LABELS = {
  initial_balance: 'رصيد أولي', question_reward: 'مكافأة سؤال', attack_reward: 'مكافأة هجوم',
  attack_penalty: 'خسارة هجوم', item_purchase: 'شراء عنصر', admin_adjustment: 'تعديل إداري',
  distribution: 'توزيع', compensation: 'تعويض', system_reward: 'مكافأة نظام',
}

const ENTRY_TYPE_COLORS = {
  initial_balance: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
  question_reward: 'bg-brand-success/10 text-brand-success',
  attack_reward: 'bg-brand-success/10 text-brand-success',
  attack_penalty: 'bg-brand-danger/10 text-brand-danger',
  item_purchase: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600',
  admin_adjustment: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
  distribution: 'bg-brand-teal/10 text-brand-teal',
  compensation: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
  system_reward: 'bg-brand-teal/10 text-brand-teal',
}

export default function AdminLedgerPage() {
  const [filterType, setFilterType] = useState('')
  const [filterDirection, setFilterDirection] = useState('')
  const url = `/api/admin/ledger?${filterType ? `entry_type=${filterType}&` : ''}${filterDirection ? `direction=${filterDirection}` : ''}`
  const { data: entries, loading } = useAdminData(url)

  const totalCredits = entries?.filter(e => e.direction === 'credit').reduce((s, e) => s + e.amount, 0) || 0
  const totalDebits = entries?.filter(e => e.direction === 'debit').reduce((s, e) => s + e.amount, 0) || 0

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">سجل النقاط</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{entries?.length || 0} حركة</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي الإيداعات</div>
          <div className="font-display text-2xl font-black text-brand-success">+{totalCredits.toLocaleString('ar-SA')}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي الخصومات</div>
          <div className="font-display text-2xl font-black text-brand-danger">-{totalDebits.toLocaleString('ar-SA')}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">صافي الحركة</div>
          <div className={`font-display text-2xl font-black ${totalCredits - totalDebits >= 0 ? 'text-brand-success' : 'text-brand-danger'}`}>
            {(totalCredits - totalDebits).toLocaleString('ar-SA')}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
        >
          <option value="">كل الأنواع</option>
          {Object.entries(ENTRY_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filterDirection}
          onChange={e => setFilterDirection(e.target.value)}
          className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
        >
          <option value="">كل الاتجاهات</option>
          <option value="credit">إيداع</option>
          <option value="debit">خصم</option>
        </select>
      </div>

      {/* Ledger Table */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">النوع</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">اللاعب</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">المبلغ</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الرصيد</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">السبب</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">التوقيت</th>
              </tr>
            </thead>
            <tbody>
              {entries?.map(e => (
                <tr key={e.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${ENTRY_TYPE_COLORS[e.entry_type] || 'bg-gray-100 text-gray-500'}`}>
                      {ENTRY_TYPE_LABELS[e.entry_type] || e.entry_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/admin/players/${e.membership_id}`} className="hover:text-brand-teal smooth-transition">
                      <div className="font-bold text-gray-900 dark:text-white">{e.alias || '—'}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-heading font-black ${e.direction === 'credit' ? 'text-brand-success' : 'text-brand-danger'}`}>
                      {e.direction === 'credit' ? '+' : '-'}{e.amount}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {e.balance_before} → {e.balance_after}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{e.reason || '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {e.created_at ? new Date(e.created_at).toLocaleString('ar-SA') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {(!entries || entries.length === 0) && (
          <div className="text-center py-12 text-gray-400 font-bold">لا توجد حركات</div>
        )}
      </div>
    </div>
  )
}
