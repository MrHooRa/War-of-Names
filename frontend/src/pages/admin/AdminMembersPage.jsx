/**
 * AdminMembersPage — Competition-scoped membership management.
 * Shows members of the currently selected competition only.
 * Displays: alias, real name, balance, protection, bankruptcy, status.
 * Actions: adjust balance, change status, view detail.
 */

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'

export default function AdminMembersPage() {
  const { selected, selectedId } = useAdminCompetition()
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [adjustModal, setAdjustModal] = useState(null) // { membership_id, alias }
  const [adjustAmount, setAdjustAmount] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [adjusting, setAdjusting] = useState(false)

  const loadMembers = useCallback(() => {
    if (!selectedId) return
    setLoading(true)
    apiFetch(`/api/admin/players?competition_id=${selectedId}`)
      .then(json => setMembers(json.data || []))
      .catch(() => setMembers([]))
      .finally(() => setLoading(false))
  }, [selectedId])

  useEffect(() => { loadMembers() }, [loadMembers])

  async function handleAdjustBalance(e) {
    e.preventDefault()
    if (!adjustModal || !adjustAmount) return
    setAdjusting(true)
    try {
      await apiFetch(`/api/admin/players/${adjustModal.membership_id}/adjust-balance`, {
        method: 'POST',
        body: JSON.stringify({
          amount: parseInt(adjustAmount),
          reason: adjustReason || 'تعديل إداري',
        }),
      })
      setAdjustModal(null)
      setAdjustAmount('')
      setAdjustReason('')
      loadMembers()
    } catch {}
    setAdjusting(false)
  }

  async function updateMemberStatus(membershipId, newStatus) {
    try {
      await apiFetch(`/api/admin/players/${membershipId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      loadMembers()
    } catch {}
  }

  const filtered = members.filter(m =>
    !search || (m.alias || '').includes(search) || (m.real_name || '').includes(search) || (m.username || '').includes(search)
  )

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <iconify-icon icon="lucide:users" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
        <p className="font-bold text-gray-500 dark:text-gray-400">اختر منافسة من القائمة الجانبية لعرض أعضائها</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">أعضاء المنافسة</h1>
          <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
            {selected.name} — العضويات والألقاب والأرصدة
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-500 dark:text-gray-400 bg-white dark:bg-brand-card-dark px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800">
            <iconify-icon icon="lucide:users" class="text-lg"></iconify-icon>
            {members.length} عضو
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400">
          <iconify-icon icon="lucide:search" class="text-lg"></iconify-icon>
        </div>
        <input
          type="text"
          placeholder="البحث باللقب أو الاسم الحقيقي..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 py-3 pr-11 pl-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
        </div>
      ) : (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[600px]">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-800">
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">اللقب</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">الاسم الحقيقي</th>
                  <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">الرصيد</th>
                  <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">الحماية</th>
                  <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">الحالة</th>
                  <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">هجمات</th>
                  <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">إجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filtered.map(m => (
                  <tr key={m.membership_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 smooth-transition">
                    <td className="px-4 py-3">
                      <Link to={`/admin/members/${m.membership_id}`} className="font-bold text-brand-teal dark:text-brand-slate hover:underline">
                        {m.alias || '—'}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-bold text-gray-700 dark:text-gray-300">{m.real_name || m.username}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-black ${m.is_bankrupt ? 'text-brand-danger' : 'text-brand-teal dark:text-brand-slate'}`}>
                        {(m.balance ?? m.current_balance ?? 0).toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {m.protection === 'full' ? (
                        <span className="text-xs font-black bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 px-2 py-0.5 rounded-lg">كاملة</span>
                      ) : m.protection === 'partial' ? (
                        <span className="text-xs font-black bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400 px-2 py-0.5 rounded-lg">جزئية</span>
                      ) : (
                        <span className="text-xs font-bold text-gray-400">—</span>
                      )}
                      {m.is_bankrupt && (
                        <span className="text-xs font-black bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400 px-2 py-0.5 rounded-lg mr-1">مفلس</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-black px-2 py-0.5 rounded-lg ${
                        m.status === 'active' ? 'bg-brand-success/10 text-brand-success'
                        : m.status === 'suspended' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                      }`}>
                        {m.status === 'active' ? 'نشط' : m.status === 'suspended' ? 'معلق' : m.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-xs font-bold text-gray-500 dark:text-gray-400">
                      {m.attacks_sent || 0}/{m.attacks_won || 0}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => setAdjustModal({ membership_id: m.membership_id, alias: m.alias })}
                          className="text-xs font-bold text-brand-teal dark:text-brand-slate hover:bg-brand-teal/10 dark:hover:bg-brand-slate/20 px-2 py-1 rounded-lg smooth-transition"
                          title="تعديل الرصيد"
                        >
                          <iconify-icon icon="lucide:coins" class="text-sm"></iconify-icon>
                        </button>
                        {m.status === 'active' ? (
                          <button
                            onClick={() => updateMemberStatus(m.membership_id, 'suspended')}
                            className="text-xs font-bold text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 px-2 py-1 rounded-lg smooth-transition"
                            title="تعليق العضوية"
                          >
                            <iconify-icon icon="lucide:pause" class="text-sm"></iconify-icon>
                          </button>
                        ) : (
                          <button
                            onClick={() => updateMemberStatus(m.membership_id, 'active')}
                            className="text-xs font-bold text-brand-success hover:bg-green-50 dark:hover:bg-green-900/20 px-2 py-1 rounded-lg smooth-transition"
                            title="تفعيل العضوية"
                          >
                            <iconify-icon icon="lucide:play" class="text-sm"></iconify-icon>
                          </button>
                        )}
                        <Link
                          to={`/admin/members/${m.membership_id}`}
                          className="text-xs font-bold text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 px-2 py-1 rounded-lg smooth-transition"
                          title="تفاصيل"
                        >
                          <iconify-icon icon="lucide:external-link" class="text-sm"></iconify-icon>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan="7" className="px-4 py-10 text-center font-bold text-gray-400">
                      لا يوجد أعضاء
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Adjust balance modal */}
      {adjustModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setAdjustModal(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4">
              تعديل رصيد — {adjustModal.alias}
            </h3>
            <form onSubmit={handleAdjustBalance} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">المبلغ (موجب = إضافة، سالب = خصم)</label>
                <input
                  type="number"
                  value={adjustAmount}
                  onChange={e => setAdjustAmount(e.target.value)}
                  required
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
                  placeholder="500 أو -200"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input
                  type="text"
                  value={adjustReason}
                  onChange={e => setAdjustReason(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
                  placeholder="تعديل إداري"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={adjusting}
                  className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60"
                >
                  {adjusting ? 'جارٍ التعديل...' : 'تعديل الرصيد'}
                </button>
                <button
                  type="button"
                  onClick={() => setAdjustModal(null)}
                  className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
                >
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
