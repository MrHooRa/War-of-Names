/**
 * AdminAttacksPage — Competition-scoped attack log.
 * Filters attacks by the currently selected competition.
 */

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'
import { formatDateTime } from '../../lib/dates'

function StatusBadge({ status }) {
  const colors = {
    succeeded: 'bg-brand-success/10 text-brand-success',
    failed: 'bg-brand-danger/10 text-brand-danger',
    blocked: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    rejected: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
  }
  const labels = { succeeded: 'ناجح', failed: 'فاشل', blocked: 'محظور', rejected: 'مرفوض' }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{labels[status] || status}</span>
}

export default function AdminAttacksPage() {
  const { selected, selectedId } = useAdminCompetition()
  const [attacks, setAttacks] = useState([])
  const [loading, setLoading] = useState(true)

  const loadAttacks = useCallback(() => {
    if (!selectedId) return
    setLoading(true)
    apiFetch(`/api/admin/attacks?competition_id=${selectedId}`)
      .then(json => setAttacks(json.data || []))
      .catch(() => setAttacks([]))
      .finally(() => setLoading(false))
  }, [selectedId])

  useEffect(() => { loadAttacks() }, [loadAttacks])

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <iconify-icon icon="lucide:swords" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
        <p className="font-bold text-gray-500 dark:text-gray-400">اختر منافسة من القائمة الجانبية لعرض الهجمات</p>
      </div>
    )
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  const succeeded = attacks.filter(a => a.outcome === 'succeeded').length
  const failed = attacks.filter(a => a.outcome === 'failed').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">سجل الهجمات</h1>
        <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
          {selected.name} — {attacks.length} هجوم — {succeeded} ناجح، {failed} فاشل
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي</div>
          <div className="font-heading font-black text-2xl text-gray-900 dark:text-white">{attacks.length}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">ناجح</div>
          <div className="font-heading font-black text-2xl text-brand-success">{succeeded}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">فاشل</div>
          <div className="font-heading font-black text-2xl text-brand-danger">{failed}</div>
        </div>
      </div>

      {/* Attacks Table */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800">
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">النتيجة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">المهاجم</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">الهدف</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">المكافأة</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">العقوبة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">التوقيت</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {attacks.map(a => (
                <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 smooth-transition">
                  <td className="px-4 py-3"><StatusBadge status={a.outcome} /></td>
                  <td className="px-4 py-3">
                    <Link to={`/admin/members/${a.attacker_membership_id}`} className="hover:text-brand-teal smooth-transition">
                      <div className="font-bold text-gray-900 dark:text-white">{a.attacker_alias}</div>
                      <div className="text-[11px] font-bold text-gray-400">{a.attacker_real_name}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/admin/members/${a.target_membership_id}`} className="hover:text-brand-teal smooth-transition">
                      <div className="font-bold text-gray-900 dark:text-white">{a.target_alias}</div>
                      <div className="text-[11px] font-bold text-gray-400">{a.target_real_name}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {a.reward_amount > 0 ? (
                      <span className="font-heading font-black text-brand-success">+{a.reward_amount}</span>
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {a.penalty_amount > 0 ? (
                      <span className="font-heading font-black text-brand-danger">-{a.penalty_amount}</span>
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs font-bold text-gray-400">
                    {a.created_at ? formatDateTime(a.created_at) : '—'}
                  </td>
                </tr>
              ))}
              {attacks.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-4 py-10 text-center font-bold text-gray-400">لا توجد هجمات بعد</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
