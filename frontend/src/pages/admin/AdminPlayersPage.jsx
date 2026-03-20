import { useState } from 'react'
import { Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

function StatusBadge({ status }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success',
    pending: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
    suspended: 'bg-brand-danger/10 text-brand-danger',
    removed: 'bg-gray-100 dark:bg-gray-800 text-gray-400',
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{status}</span>
}

export default function AdminPlayersPage() {
  const { data: players, loading, error, refetch } = useAdminData('/api/admin/players')
  const { data: accounts, loading: accLoading, refetch: refetchAccounts } = useAdminData('/api/admin/accounts')
  const [activeTab, setActiveTab] = useState('memberships')
  const [search, setSearch] = useState('')
  const [adjustModal, setAdjustModal] = useState(null) // { membershipId, alias }
  const [adjustAmount, setAdjustAmount] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [actionMsg, setActionMsg] = useState(null)

  const filtered = players?.filter(p =>
    !search || p.alias?.includes(search) || p.real_name?.includes(search) || p.username?.includes(search)
  ) || []

  const filteredAccounts = accounts?.filter(a =>
    !search || a.username?.includes(search) || a.real_name?.includes(search)
  ) || []

  async function handleAccountStatus(accountId, newStatus) {
    try {
      await apiFetch(`/api/admin/accounts/${accountId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      setActionMsg('تم تحديث حالة الحساب')
      refetchAccounts()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    }
  }

  async function handleAdjust() {
    if (!adjustAmount || !adjustReason) return
    try {
      await apiFetch(`/api/admin/players/${adjustModal.membershipId}/adjust-balance`, {
        method: 'POST',
        body: JSON.stringify({ amount: parseInt(adjustAmount), reason: adjustReason }),
      })
      setActionMsg('تم تعديل الرصيد بنجاح')
      setAdjustModal(null)
      setAdjustAmount('')
      setAdjustReason('')
      refetch()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    }
  }

  async function handleStatusChange(membershipId, newStatus) {
    try {
      await apiFetch(`/api/admin/players/${membershipId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      setActionMsg('تم تحديث الحالة')
      refetch()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">إدارة اللاعبين والحسابات</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {activeTab === 'memberships' ? `${players?.length || 0} عضوية` : `${accounts?.length || 0} حساب`}
          </p>
        </div>
      </div>

      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${
          actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'
        }`}>{actionMsg}</div>
      )}

      {/* Tabs: Memberships vs Accounts */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab('memberships')}
          className={`px-4 py-2 rounded-lg text-sm font-heading font-black smooth-transition ${
            activeTab === 'memberships'
              ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm'
              : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <iconify-icon icon="lucide:users" class="ml-1.5"></iconify-icon>
          العضويات
        </button>
        <button
          onClick={() => setActiveTab('accounts')}
          className={`px-4 py-2 rounded-lg text-sm font-heading font-black smooth-transition ${
            activeTab === 'accounts'
              ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm'
              : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <iconify-icon icon="lucide:user-cog" class="ml-1.5"></iconify-icon>
          الحسابات
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <iconify-icon icon="lucide:search" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"></iconify-icon>
        <input
          type="text"
          placeholder="بحث باللقب أو الاسم أو المستخدم..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full md:w-96 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
        />
      </div>

      {/* Accounts Tab */}
      {activeTab === 'accounts' && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الحساب</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الحالة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">العضويات</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">تاريخ الإنشاء</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filteredAccounts.map(a => (
                  <tr key={a.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-lg flex items-center justify-center text-brand-teal dark:text-brand-slate font-black text-sm">
                          {a.username?.[0] || '?'}
                        </div>
                        <div>
                          <div className="font-bold text-gray-900 dark:text-white">{a.username}</div>
                          <div className="text-[11px] text-gray-400">{a.real_name}{a.is_admin ? ' (مشرف)' : ''}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3 font-bold text-gray-700 dark:text-gray-300">{a.membership_count}</td>
                    <td className="px-4 py-3 text-xs text-gray-400 font-bold">{a.created_at ? new Date(a.created_at).toLocaleDateString('ar-SA') : '—'}</td>
                    <td className="px-4 py-3">
                      {!a.is_admin && (
                        <div className="flex items-center gap-1">
                          {a.status === 'active' && (
                            <button onClick={() => handleAccountStatus(a.id, 'suspended')} className="px-2 py-1 rounded-lg text-[11px] font-bold text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30 smooth-transition" title="تعليق الحساب">
                              <iconify-icon icon="lucide:pause-circle"></iconify-icon>
                            </button>
                          )}
                          {a.status === 'suspended' && (
                            <button onClick={() => handleAccountStatus(a.id, 'active')} className="px-2 py-1 rounded-lg text-[11px] font-bold text-brand-success hover:bg-brand-success/10 smooth-transition" title="إعادة تفعيل">
                              <iconify-icon icon="lucide:play-circle"></iconify-icon>
                            </button>
                          )}
                          {a.status !== 'disabled' && (
                            <button onClick={() => handleAccountStatus(a.id, 'disabled')} className="px-2 py-1 rounded-lg text-[11px] font-bold text-brand-danger hover:bg-brand-danger/10 smooth-transition" title="تعطيل الحساب">
                              <iconify-icon icon="lucide:x-circle"></iconify-icon>
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredAccounts.length === 0 && (
            <div className="text-center py-12 text-gray-400 font-bold">لا توجد حسابات</div>
          )}
        </div>
      )}

      {/* Players Table (Memberships tab) */}
      {activeTab === 'memberships' && <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">اللاعب</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الرصيد</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الحالة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الهجمات</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الحماية</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.membership_id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                  <td className="px-4 py-3">
                    <Link to={`/admin/members/${p.membership_id}`} className="flex items-center gap-3 group">
                      <div className="w-9 h-9 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-lg flex items-center justify-center text-brand-teal dark:text-brand-slate font-black text-sm">
                        {p.alias?.[0] || '?'}
                      </div>
                      <div>
                        <div className="font-bold text-gray-900 dark:text-white group-hover:text-brand-teal dark:group-hover:text-brand-slate smooth-transition">{p.alias || '—'}</div>
                        <div className="text-[11px] text-gray-400">{p.real_name} ({p.username})</div>
                      </div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-heading font-black ${p.is_bankrupt ? 'text-brand-danger' : 'text-gray-900 dark:text-white'}`}>
                      {p.balance?.toLocaleString('ar-SA')}
                    </span>
                    {p.is_bankrupt && <span className="text-[10px] text-brand-danger font-bold block">مفلس</span>}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3">
                    <span className="text-gray-700 dark:text-gray-300 font-bold">{p.attacks_won}/{p.attacks_sent}</span>
                    <span className="text-[10px] text-gray-400 block">تلقى: {p.attacks_received}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-bold ${p.protection === 'full' ? 'text-brand-success' : p.protection === 'partial' ? 'text-amber-500' : 'text-gray-400'}`}>
                      {p.protection === 'full' ? 'كاملة' : p.protection === 'partial' ? 'جزئية' : 'بدون'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setAdjustModal({ membershipId: p.membership_id, alias: p.alias })}
                        className="px-2 py-1 rounded-lg text-[11px] font-bold text-brand-teal hover:bg-brand-teal/10 smooth-transition"
                        title="تعديل الرصيد"
                      >
                        <iconify-icon icon="lucide:coins"></iconify-icon>
                      </button>
                      {p.status === 'active' && (
                        <button
                          onClick={() => handleStatusChange(p.membership_id, 'suspended')}
                          className="px-2 py-1 rounded-lg text-[11px] font-bold text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30 smooth-transition"
                          title="إيقاف مؤقت"
                        >
                          <iconify-icon icon="lucide:pause-circle"></iconify-icon>
                        </button>
                      )}
                      {p.status === 'suspended' && (
                        <button
                          onClick={() => handleStatusChange(p.membership_id, 'active')}
                          className="px-2 py-1 rounded-lg text-[11px] font-bold text-brand-success hover:bg-brand-success/10 smooth-transition"
                          title="إعادة تفعيل"
                        >
                          <iconify-icon icon="lucide:play-circle"></iconify-icon>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400 font-bold">لا يوجد لاعبون</div>
        )}
      </div>

      }

      {/* Adjust Balance Modal */}
      {adjustModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setAdjustModal(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4">تعديل رصيد {adjustModal.alias}</h3>
            <div className="space-y-3">
              <input
                type="number"
                placeholder="المبلغ (موجب = إيداع، سالب = خصم)"
                value={adjustAmount}
                onChange={e => setAdjustAmount(e.target.value)}
                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
              />
              <input
                type="text"
                placeholder="السبب"
                value={adjustReason}
                onChange={e => setAdjustReason(e.target.value)}
                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
              />
              <div className="flex gap-2 pt-2">
                <button onClick={handleAdjust} className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition">تطبيق</button>
                <button onClick={() => setAdjustModal(null)} className="px-4 py-2.5 rounded-xl font-bold text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
