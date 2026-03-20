/**
 * AdminAccountsPage — Platform-level account management.
 * Clearly separates global account identity from competition-scoped memberships.
 * Shows: account info, linked memberships with operational state, linked competitions.
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'

const STATUS_LABELS = {
  active: { text: 'نشط', color: 'bg-brand-success/10 text-brand-success', icon: 'lucide:check-circle' },
  suspended: { text: 'معلق', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400', icon: 'lucide:pause-circle' },
  disabled: { text: 'معطل', color: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400', icon: 'lucide:x-circle' },
  archived: { text: 'مؤرشف', color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400', icon: 'lucide:archive' },
}

const PROTECTION_LABELS = {
  none: { text: 'بدون', color: 'text-gray-400' },
  partial: { text: 'جزئية', color: 'text-amber-500' },
  full: { text: 'كاملة', color: 'text-brand-success' },
}

const COMP_STATUS_LABELS = {
  active: { text: 'نشطة', color: 'bg-brand-success/10 text-brand-success' },
  draft: { text: 'مسودة', color: 'bg-gray-100 dark:bg-gray-800 text-gray-500' },
  paused: { text: 'متوقفة', color: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600' },
  completed: { text: 'منتهية', color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600' },
  archived: { text: 'مؤرشفة', color: 'bg-gray-100 dark:bg-gray-800 text-gray-400' },
}

export default function AdminAccountsPage() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedAccount, setSelectedAccount] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  function showMsg(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 3000)
  }

  useEffect(() => {
    apiFetch('/api/admin/accounts')
      .then(json => setAccounts(json.data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function loadAccountDetail(accountId) {
    if (selectedAccount?.id === accountId) {
      setSelectedAccount(null)
      return
    }
    setDetailLoading(true)
    try {
      const json = await apiFetch(`/api/admin/accounts/${accountId}`)
      setSelectedAccount(json.data)
    } catch {
      showMsg('خطأ: تعذّر تحميل تفاصيل الحساب')
    }
    setDetailLoading(false)
  }

  async function updateAccountStatus(accountId, newStatus) {
    try {
      await apiFetch(`/api/admin/accounts/${accountId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      setAccounts(prev => prev.map(a => a.id === accountId ? { ...a, status: newStatus } : a))
      if (selectedAccount?.id === accountId) {
        setSelectedAccount(prev => ({ ...prev, status: newStatus }))
      }
      showMsg('تم تحديث الحالة')
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  const filtered = accounts.filter(a =>
    !search || a.username.includes(search) || a.real_name.includes(search)
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${
          actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'
        }`}>{actionMsg}</div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">إدارة الحسابات</h1>
          <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
            الحسابات على مستوى المنصة — مستقلة عن العضويات في المنافسات
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm font-bold text-gray-500 dark:text-gray-400 bg-white dark:bg-brand-card-dark px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800">
          <iconify-icon icon="lucide:users-round" class="text-lg"></iconify-icon>
          {accounts.length} حساب
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none text-gray-400">
          <iconify-icon icon="lucide:search" class="text-lg"></iconify-icon>
        </div>
        <input
          type="text"
          placeholder="البحث باسم المستخدم أو الاسم الحقيقي..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 py-3 pr-11 pl-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
        />
      </div>

      {/* Accounts table */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800">
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">المستخدم</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400">الاسم الحقيقي</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">الحالة</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">العضويات</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">آخر دخول</th>
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">إجراءات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {filtered.map(a => {
                const st = STATUS_LABELS[a.status] || STATUS_LABELS.active
                return (
                  <tr
                    key={a.id}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-800/50 smooth-transition cursor-pointer ${selectedAccount?.id === a.id ? 'bg-brand-teal/5 dark:bg-brand-slate/5' : ''}`}
                    onClick={() => loadAccountDetail(a.id)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-lg flex items-center justify-center text-brand-teal dark:text-brand-slate font-black text-sm">
                          {a.username[0]}
                        </div>
                        <div>
                          <span className="font-bold text-gray-900 dark:text-white">{a.username}</span>
                          {a.is_admin && (
                            <span className="mr-2 text-[10px] font-black bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/20 dark:text-brand-slate px-1.5 py-0.5 rounded">مشرف</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-bold text-gray-700 dark:text-gray-300">{a.real_name}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-black px-2 py-1 rounded-lg ${st.color}`}>{st.text}</span>
                    </td>
                    <td className="px-4 py-3 text-center font-bold text-gray-600 dark:text-gray-400">{a.membership_count}</td>
                    <td className="px-4 py-3 text-center text-xs font-bold text-gray-400 dark:text-gray-500">
                      {a.last_login_at ? new Date(a.last_login_at).toLocaleDateString('ar') : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {!a.is_admin && (
                        <div className="flex items-center justify-center gap-1">
                          {a.status === 'active' ? (
                            <button
                              onClick={e => { e.stopPropagation(); updateAccountStatus(a.id, 'suspended') }}
                              className="text-xs font-bold text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 px-2 py-1 rounded-lg smooth-transition"
                            >تعليق</button>
                          ) : (
                            <button
                              onClick={e => { e.stopPropagation(); updateAccountStatus(a.id, 'active') }}
                              className="text-xs font-bold text-brand-success hover:bg-green-50 dark:hover:bg-green-900/20 px-2 py-1 rounded-lg smooth-transition"
                            >تفعيل</button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ══ Account Detail Panel ══ */}
      {detailLoading && (
        <div className="flex items-center justify-center py-8">
          <iconify-icon icon="lucide:loader-2" class="text-2xl text-brand-teal animate-spin"></iconify-icon>
        </div>
      )}

      {selectedAccount && !detailLoading && (
        <div className="space-y-5">

          {/* Section: Global Account Identity */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
                <iconify-icon icon="lucide:user-circle" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                هوية الحساب
              </h2>
              <button onClick={() => setSelectedAccount(null)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <iconify-icon icon="lucide:x" class="text-lg"></iconify-icon>
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">اسم المستخدم</div>
                <div className="font-bold text-gray-900 dark:text-white">{selectedAccount.username}</div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">الاسم الحقيقي</div>
                <div className="font-bold text-gray-900 dark:text-white">{selectedAccount.real_name}</div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">الحالة</div>
                <div className={`font-bold ${(STATUS_LABELS[selectedAccount.status] || STATUS_LABELS.active).color} inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs`}>
                  {(STATUS_LABELS[selectedAccount.status] || STATUS_LABELS.active).text}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">الدور</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {selectedAccount.is_admin ? (
                    <span className="text-brand-teal dark:text-brand-slate flex items-center gap-1">
                      <iconify-icon icon="lucide:shield" class="text-sm"></iconify-icon>
                      مشرف
                    </span>
                  ) : 'مستخدم عادي'}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">تاريخ التسجيل</div>
                <div className="font-bold text-gray-900 dark:text-white text-sm">
                  {selectedAccount.created_at ? new Date(selectedAccount.created_at).toLocaleDateString('ar') : '—'}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">آخر دخول</div>
                <div className="font-bold text-gray-900 dark:text-white text-sm">
                  {selectedAccount.last_login_at ? new Date(selectedAccount.last_login_at).toLocaleString('ar') : '—'}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">الإشعارات</div>
                <div className="font-bold text-gray-900 dark:text-white text-sm">
                  {selectedAccount.notification_count || 0}
                  {selectedAccount.unread_notification_count > 0 && (
                    <span className="mr-1 text-[10px] font-black bg-brand-danger/10 text-brand-danger px-1.5 py-0.5 rounded">
                      {selectedAccount.unread_notification_count} غير مقروء
                    </span>
                  )}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
                <div className="text-[10px] font-black text-gray-400 mb-1">عدد المنافسات</div>
                <div className="font-bold text-gray-900 dark:text-white text-sm">
                  {selectedAccount.competitions?.length || 0} منافسة
                </div>
              </div>
            </div>
          </div>

          {/* Section: Linked Competitions */}
          {selectedAccount.competitions?.length > 0 && (
            <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
              <h2 className="font-heading font-black text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2 mb-4">
                <iconify-icon icon="lucide:trophy" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                المنافسات المرتبطة
              </h2>
              <div className="flex flex-wrap gap-2">
                {selectedAccount.competitions.map(c => {
                  const cst = COMP_STATUS_LABELS[c.status] || COMP_STATUS_LABELS.draft
                  return (
                    <div key={c.id} className="flex items-center gap-2 bg-gray-50 dark:bg-gray-800/50 rounded-xl px-3 py-2">
                      <span className="font-bold text-sm text-gray-900 dark:text-white">{c.name}</span>
                      <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${cst.color}`}>{cst.text}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Section: Linked Memberships / Players */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
            <h2 className="font-heading font-black text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2 mb-4">
              <iconify-icon icon="lucide:swords" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
              العضويات في المنافسات ({selectedAccount.memberships?.length || 0})
            </h2>

            {selectedAccount.memberships?.length > 0 ? (
              <div className="space-y-3">
                {selectedAccount.memberships.map(m => {
                  const mst = STATUS_LABELS[m.status] || STATUS_LABELS.active
                  const prot = PROTECTION_LABELS[m.protection] || PROTECTION_LABELS.none
                  return (
                    <div key={m.membership_id} className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-black text-gray-900 dark:text-white">{m.competition_name}</span>
                            <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${(COMP_STATUS_LABELS[m.competition_status] || COMP_STATUS_LABELS.draft).color}`}>
                              {(COMP_STATUS_LABELS[m.competition_status] || COMP_STATUS_LABELS.draft).text}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-xs font-bold text-gray-500 dark:text-gray-400 flex-wrap">
                            <span className="flex items-center gap-1">
                              <iconify-icon icon="lucide:user" class="text-sm"></iconify-icon>
                              {m.alias || '—'}
                            </span>
                            <span className={`flex items-center gap-1 ${mst.color} px-1.5 py-0.5 rounded`}>
                              {mst.text}
                            </span>
                            <span>انضمام: {m.joined_at ? new Date(m.joined_at).toLocaleDateString('ar') : '—'}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-left">
                          <div className="grid grid-cols-3 gap-3 text-center">
                            <div>
                              <div className={`font-black text-sm ${m.is_bankrupt ? 'text-brand-danger' : 'text-brand-teal dark:text-brand-slate'}`}>
                                {m.balance?.toLocaleString()}
                              </div>
                              <div className="text-[10px] font-bold text-gray-400">الرصيد</div>
                            </div>
                            <div>
                              <div className="font-black text-sm text-gray-900 dark:text-white">
                                #{m.rank}
                              </div>
                              <div className="text-[10px] font-bold text-gray-400">الترتيب</div>
                            </div>
                            <div>
                              <div className="font-black text-sm text-gray-900 dark:text-white">
                                {m.attacks_won}/{m.attacks_sent}
                              </div>
                              <div className="text-[10px] font-bold text-gray-400">هجمات</div>
                            </div>
                          </div>
                          <Link
                            to={`/admin/members/${m.membership_id}`}
                            className="w-8 h-8 flex items-center justify-center rounded-lg bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/20 dark:text-brand-slate hover:bg-brand-teal/20 smooth-transition"
                            title="فتح ملف اللاعب"
                          >
                            <iconify-icon icon="lucide:external-link" class="text-sm"></iconify-icon>
                          </Link>
                        </div>
                      </div>

                      {/* State badges row */}
                      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200/50 dark:border-gray-700/50">
                        {m.is_bankrupt && (
                          <span className="text-[10px] font-black bg-brand-danger/10 text-brand-danger px-2 py-0.5 rounded flex items-center gap-1">
                            <iconify-icon icon="lucide:alert-triangle" class="text-xs"></iconify-icon>
                            مفلس
                          </span>
                        )}
                        <span className={`text-[10px] font-bold ${prot.color} flex items-center gap-1`}>
                          <iconify-icon icon="lucide:shield" class="text-xs"></iconify-icon>
                          حماية: {prot.text}
                        </span>
                        {m.item_count > 0 && (
                          <span className="text-[10px] font-bold text-gray-400 flex items-center gap-1">
                            <iconify-icon icon="lucide:package" class="text-xs"></iconify-icon>
                            {m.item_count} عنصر
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-6 text-sm font-bold text-gray-400 dark:text-gray-500">
                <iconify-icon icon="lucide:inbox" class="text-2xl mb-2 block"></iconify-icon>
                هذا الحساب ليس عضواً في أي منافسة
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
