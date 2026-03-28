/**
 * AdminLedgerPage — Competition-scoped point ledger.
 * Filters ledger entries by the currently selected competition.
 */

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'
import { formatDateTime } from '../../lib/dates'

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
  const { selected, selectedId } = useAdminCompetition()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [filterDirection, setFilterDirection] = useState('')

  const loadEntries = useCallback(() => {
    if (!selectedId) return
    setLoading(true)
    const params = new URLSearchParams()
    params.set('competition_id', selectedId)
    if (filterType) params.set('entry_type', filterType)
    if (filterDirection) params.set('direction', filterDirection)
    apiFetch(`/api/admin/ledger?${params}`)
      .then(json => setEntries(json.data || []))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [selectedId, filterType, filterDirection])

  useEffect(() => { loadEntries() }, [loadEntries])

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <iconify-icon icon="lucide:receipt" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
        <p className="font-bold text-gray-500 dark:text-gray-400">اختر منافسة من القائمة الجانبية لعرض سجل النقاط</p>
      </div>
    )
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  const totalCredits = entries.filter(e => e.direction === 'credit').reduce((s, e) => s + e.amount, 0)
  const totalDebits = entries.filter(e => e.direction === 'debit').reduce((s, e) => s + e.amount, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">سجل النقاط</h1>
        <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
          {selected.name} — {entries.length} حركة
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي الإيداعات</div>
          <div className="font-heading font-black text-2xl text-brand-success">+{totalCredits.toLocaleString()}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي الخصومات</div>
          <div className="font-heading font-black text-2xl text-brand-danger">-{totalDebits.toLocaleString()}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">صافي الحركة</div>
          <div className={`font-heading font-black text-2xl ${totalCredits - totalDebits >= 0 ? 'text-brand-success' : 'text-brand-danger'}`}>
            {(totalCredits - totalDebits).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
        >
          <option value="">كل الأنواع</option>
          {Object.entries(ENTRY_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filterDirection}
          onChange={e => setFilterDirection(e.target.value)}
          className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
        >
          <option value="">كل الاتجاهات</option>
          <option value="credit">إيداع</option>
          <option value="debit">خصم</option>
        </select>
      </div>

      {/* Ledger Table */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800">
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">النوع</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">اللاعب</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">المبلغ</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">الرصيد</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">السبب</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">التوقيت</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {entries.map(e => (
                <tr key={e.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 smooth-transition">
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${ENTRY_TYPE_COLORS[e.entry_type] || 'bg-gray-100 text-gray-500'}`}>
                      {ENTRY_TYPE_LABELS[e.entry_type] || e.entry_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/admin/members/${e.membership_id}`} className="font-bold text-brand-teal dark:text-brand-slate hover:underline">
                      {e.player_alias || e.alias || '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-heading font-black ${e.direction === 'credit' ? 'text-brand-success' : 'text-brand-danger'}`}>
                      {e.direction === 'credit' ? '+' : '-'}{e.amount}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-xs font-bold text-gray-400">
                    {e.balance_before} → {e.balance_after}
                  </td>
                  <td className="px-4 py-3 text-xs font-bold text-gray-500 max-w-xs truncate">{e.reason || '—'}</td>
                  <td className="px-4 py-3 text-xs font-bold text-gray-400">
                    {e.created_at ? formatDateTime(e.created_at) : '—'}
                  </td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-4 py-10 text-center font-bold text-gray-400">لا توجد حركات</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
