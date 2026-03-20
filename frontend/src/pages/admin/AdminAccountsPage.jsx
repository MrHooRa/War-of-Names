/**
 * AdminAccountsPage — Platform-level user/account management.
 * Separated from competition membership management.
 * Shows: username, real_name, status, is_admin, membership count, linked competitions.
 */

import { useState, useEffect } from 'react'
import { apiFetch } from '../../lib/api'

const STATUS_LABELS = {
  active: { text: 'نشط', color: 'bg-brand-success/10 text-brand-success' },
  suspended: { text: 'معلق', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400' },
  disabled: { text: 'معطل', color: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' },
  archived: { text: 'مؤرشف', color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
}

export default function AdminAccountsPage() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedAccount, setSelectedAccount] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

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
    } catch {}
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
    } catch {}
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
                <th className="text-center px-4 py-3 font-black text-gray-500 dark:text-gray-400">التسجيل</th>
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
                      {a.created_at ? new Date(a.created_at).toLocaleDateString('ar') : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {!a.is_admin && (
                        <div className="flex items-center justify-center gap-1">
                          {a.status === 'active' ? (
                            <button
                              onClick={e => { e.stopPropagation(); updateAccountStatus(a.id, 'suspended') }}
                              className="text-xs font-bold text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 px-2 py-1 rounded-lg smooth-transition"
                            >
                              تعليق
                            </button>
                          ) : (
                            <button
                              onClick={e => { e.stopPropagation(); updateAccountStatus(a.id, 'active') }}
                              className="text-xs font-bold text-brand-success hover:bg-green-50 dark:hover:bg-green-900/20 px-2 py-1 rounded-lg smooth-transition"
                            >
                              تفعيل
                            </button>
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

      {/* Account detail panel */}
      {selectedAccount && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">
              تفاصيل الحساب — {selectedAccount.username}
            </h2>
            <button onClick={() => setSelectedAccount(null)} className="text-gray-400 hover:text-gray-600">
              <iconify-icon icon="lucide:x" class="text-lg"></iconify-icon>
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
              <div className="text-xs font-bold text-gray-400 mb-1">الاسم الحقيقي</div>
              <div className="font-bold text-gray-900 dark:text-white">{selectedAccount.real_name}</div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
              <div className="text-xs font-bold text-gray-400 mb-1">الحالة</div>
              <div className="font-bold text-gray-900 dark:text-white">{selectedAccount.status}</div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
              <div className="text-xs font-bold text-gray-400 mb-1">تاريخ التسجيل</div>
              <div className="font-bold text-gray-900 dark:text-white text-sm">
                {selectedAccount.created_at ? new Date(selectedAccount.created_at).toLocaleDateString('ar') : '—'}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3">
              <div className="text-xs font-bold text-gray-400 mb-1">آخر دخول</div>
              <div className="font-bold text-gray-900 dark:text-white text-sm">
                {selectedAccount.last_login_at ? new Date(selectedAccount.last_login_at).toLocaleDateString('ar') : '—'}
              </div>
            </div>
          </div>

          {/* Linked memberships */}
          {selectedAccount.memberships?.length > 0 && (
            <div>
              <h3 className="font-heading font-bold text-sm text-gray-600 dark:text-gray-400 mb-3">العضويات في المنافسات</h3>
              <div className="space-y-2">
                {selectedAccount.memberships.map(m => (
                  <div key={m.membership_id} className="flex items-center justify-between bg-gray-50 dark:bg-gray-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <iconify-icon icon="lucide:trophy" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                      <div>
                        <div className="font-bold text-gray-900 dark:text-white text-sm">{m.competition_name}</div>
                        <div className="text-xs font-bold text-gray-400">اللقب: {m.alias || '—'}</div>
                      </div>
                    </div>
                    <div className="text-left">
                      <div className="font-black text-brand-teal dark:text-brand-slate text-sm">{m.balance?.toLocaleString()} نقطة</div>
                      <div className="text-xs font-bold text-gray-400">{m.status}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
