/**
 * OwnerDashboardPage — Owner-only control panel.
 *
 * Sections:
 *  1. Platform Stats Grid
 *  2. Admin Management (promote/demote)
 *  3. IP Ban Management (add/remove)
 *  4. Quick Actions (backup, link to admin)
 */

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'

/* ── Stat Card ── */
function StatCard({ icon, label, value, color = 'brand-teal' }) {
  const colorMap = {
    'brand-teal': 'bg-brand-teal/10 dark:bg-brand-teal/20 text-brand-teal',
    'purple': 'bg-purple-500/10 dark:bg-purple-500/20 text-purple-500',
    'amber': 'bg-amber-500/10 dark:bg-amber-500/20 text-amber-500',
    'brand-danger': 'bg-brand-danger/10 dark:bg-brand-danger/20 text-brand-danger',
    'brand-success': 'bg-brand-success/10 dark:bg-brand-success/20 text-brand-success',
    'brand-orange': 'bg-brand-orange/10 dark:bg-brand-orange/20 text-brand-orange',
    'brand-slate': 'bg-brand-slate/10 dark:bg-brand-slate/20 text-brand-slate',
    'blue': 'bg-blue-500/10 dark:bg-blue-500/20 text-blue-500',
  }
  return (
    <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 shadow-sm hover:shadow-md smooth-transition group hover:-translate-y-0.5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorMap[color] || colorMap['brand-teal']}`}>
          <iconify-icon icon={icon} class="text-xl"></iconify-icon>
        </div>
        <span className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest">{label}</span>
      </div>
      <div className="text-3xl font-black text-gray-900 dark:text-white">{value ?? '—'}</div>
    </div>
  )
}

/* ── IP Ban Modal ── */
function IpBanModal({ onClose, onCreated }) {
  const [ip, setIp] = useState('')
  const [reason, setReason] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const body = { ip_address: ip, reason }
      if (expiresAt) body.expires_at = expiresAt
      await apiFetch('/api/owner/ip-bans', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-brand-danger/10 rounded-xl flex items-center justify-center">
            <iconify-icon icon="lucide:shield-ban" class="text-xl text-brand-danger"></iconify-icon>
          </div>
          <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white">حظر IP جديد</h3>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">عنوان IP</label>
            <input
              type="text"
              value={ip}
              onChange={e => setIp(e.target.value)}
              placeholder="192.168.1.1"
              required
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              dir="ltr"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">السبب</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="سبب الحظر..."
              required
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/30"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">تاريخ انتهاء الحظر (اختياري)</label>
            <input
              type="datetime-local"
              value={expiresAt}
              onChange={e => setExpiresAt(e.target.value)}
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              dir="ltr"
            />
          </div>

          {error && (
            <p className="text-brand-danger text-sm font-bold text-center py-2 bg-red-500/10 rounded-xl border border-red-500/20">
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 bg-brand-danger hover:bg-red-600 text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50"
            >
              {saving ? (
                <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
              ) : (
                <iconify-icon icon="lucide:shield-ban"></iconify-icon>
              )}
              تنفيذ الحظر
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
            >
              إلغاء
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Main Dashboard ── */
export default function OwnerDashboardPage() {
  const [stats, setStats] = useState(null)
  const [admins, setAdmins] = useState([])
  const [bans, setBans] = useState([])
  const [loading, setLoading] = useState(true)
  const [showBanModal, setShowBanModal] = useState(false)
  const [actionLoading, setActionLoading] = useState(null) // account_id being acted on
  const [actionMsg, setActionMsg] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, adminsRes, bansRes] = await Promise.all([
        apiFetch('/api/owner/dashboard'),
        apiFetch('/api/owner/admins'),
        apiFetch('/api/owner/ip-bans'),
      ])
      if (statsRes.data) setStats(statsRes.data)
      if (adminsRes.data) setAdmins(adminsRes.data)
      if (bansRes.data) setBans(bansRes.data)
    } catch {
      // Individual failures handled silently; partial data is OK
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  async function handlePromote(accountId) {
    setActionLoading(accountId)
    setActionMsg(null)
    try {
      await apiFetch(`/api/owner/admins/${accountId}/promote`, { method: 'POST' })
      setActionMsg({ type: 'success', text: 'تمت الترقية بنجاح' })
      fetchAll()
    } catch (err) {
      setActionMsg({ type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
      setTimeout(() => setActionMsg(null), 3000)
    }
  }

  async function handleDemote(accountId) {
    setActionLoading(accountId)
    setActionMsg(null)
    try {
      await apiFetch(`/api/owner/admins/${accountId}/demote`, { method: 'POST' })
      setActionMsg({ type: 'success', text: 'تم التخفيض بنجاح' })
      fetchAll()
    } catch (err) {
      setActionMsg({ type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
      setTimeout(() => setActionMsg(null), 3000)
    }
  }

  async function handleUnban(banId) {
    setActionLoading(`ban-${banId}`)
    setActionMsg(null)
    try {
      await apiFetch(`/api/owner/ip-bans/${banId}`, { method: 'DELETE' })
      setActionMsg({ type: 'success', text: 'تم إلغاء الحظر' })
      fetchAll()
    } catch (err) {
      setActionMsg({ type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
      setTimeout(() => setActionMsg(null), 3000)
    }
  }

  async function handleBackup() {
    setActionMsg(null)
    try {
      const res = await fetch('/api/owner/backup', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('won_token')}`,
        },
      })
      if (!res.ok) throw new Error('فشل تحميل النسخة الاحتياطية')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `won-backup-${new Date().toISOString().slice(0, 10)}.sql`
      a.click()
      URL.revokeObjectURL(url)
      setActionMsg({ type: 'success', text: 'تم تحميل النسخة الاحتياطية' })
    } catch (err) {
      setActionMsg({ type: 'error', text: err.message })
    }
    setTimeout(() => setActionMsg(null), 3000)
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-4xl text-purple-500 animate-spin"></iconify-icon>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">

      {/* ═══ Header ═══ */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-purple-500/15 dark:bg-purple-500/20 rounded-2xl flex items-center justify-center">
            <iconify-icon icon="lucide:crown" class="text-3xl text-purple-600 dark:text-purple-400"></iconify-icon>
          </div>
          <div>
            <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">لوحة المالك</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">إدارة المنصة والمشرفين</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link
            to="/admin"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold bg-amber-500/10 dark:bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 smooth-transition"
          >
            <iconify-icon icon="lucide:shield-check"></iconify-icon>
            لوحة المشرف
          </Link>
        </div>
      </div>

      {/* Action message */}
      {actionMsg && (
        <div className={`px-4 py-3 rounded-xl text-sm font-bold ${actionMsg.type === 'error' ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>
          {actionMsg.text}
        </div>
      )}

      {/* ═══ 1. Platform Stats Grid ═══ */}
      <section>
        <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <iconify-icon icon="lucide:bar-chart-3" class="text-purple-500"></iconify-icon>
          إحصائيات المنصة
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon="lucide:users" label="الحسابات" value={stats?.total_accounts} color="purple" />
          <StatCard icon="lucide:trophy" label="المنافسات" value={stats?.total_competitions} color="amber" />
          <StatCard icon="lucide:trophy" label="منافسات نشطة" value={stats?.active_competitions} color="brand-success" />
          <StatCard icon="lucide:user-check" label="العضويات" value={stats?.total_memberships} color="brand-teal" />
          <StatCard icon="lucide:swords" label="الهجمات" value={stats?.total_attacks} color="brand-orange" />
          <StatCard icon="lucide:brain" label="جلسات الأسئلة" value={stats?.total_quiz_sessions} color="blue" />
          <StatCard icon="lucide:ghost" label="المفلسون" value={stats?.total_bankrupt_players} color="brand-danger" />
          <StatCard icon="lucide:bell" label="إشعارات غير مقروءة" value={stats?.unread_notifications} color="brand-slate" />
        </div>
      </section>

      {/* ═══ 2. Admin Management ═══ */}
      <section className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <iconify-icon icon="lucide:shield-check" class="text-xl text-purple-500"></iconify-icon>
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">إدارة المشرفين</h2>
          <span className="text-sm font-bold text-gray-400 dark:text-gray-500">({admins.length})</span>
        </div>

        {admins.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400 font-bold">
            لا توجد حسابات مشرفين
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/40">
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">المستخدم</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">الاسم الحقيقي</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">الحالة</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">الدور</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">إجراء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {admins.map(admin => (
                  <tr key={admin.account_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                    <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">{admin.username}</td>
                    <td className="px-6 py-4 text-gray-600 dark:text-gray-400">{admin.real_name || '—'}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-black ${admin.status === 'active' ? 'bg-brand-success/10 text-brand-success' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${admin.status === 'active' ? 'bg-brand-success' : 'bg-gray-400'}`}></span>
                        {admin.status === 'active' ? 'نشط' : admin.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {admin.is_owner ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black bg-purple-500/10 text-purple-600 dark:text-purple-400">
                          <iconify-icon icon="lucide:crown" class="text-xs"></iconify-icon>
                          مالك
                        </span>
                      ) : admin.is_admin ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black bg-amber-500/10 text-amber-600 dark:text-amber-400">
                          <iconify-icon icon="lucide:shield-check" class="text-xs"></iconify-icon>
                          مشرف
                        </span>
                      ) : (
                        <span className="text-xs font-bold text-gray-400">متسابق</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {admin.is_owner ? (
                        <span className="text-xs text-gray-400 font-bold">—</span>
                      ) : admin.is_admin ? (
                        <button
                          onClick={() => handleDemote(admin.account_id)}
                          disabled={actionLoading === admin.account_id}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black bg-brand-danger/10 text-brand-danger hover:bg-brand-danger/20 smooth-transition disabled:opacity-50"
                        >
                          {actionLoading === admin.account_id ? (
                            <iconify-icon icon="lucide:loader-2" class="animate-spin text-xs"></iconify-icon>
                          ) : (
                            <iconify-icon icon="lucide:arrow-down" class="text-xs"></iconify-icon>
                          )}
                          تخفيض
                        </button>
                      ) : (
                        <button
                          onClick={() => handlePromote(admin.account_id)}
                          disabled={actionLoading === admin.account_id}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition disabled:opacity-50"
                        >
                          {actionLoading === admin.account_id ? (
                            <iconify-icon icon="lucide:loader-2" class="animate-spin text-xs"></iconify-icon>
                          ) : (
                            <iconify-icon icon="lucide:arrow-up" class="text-xs"></iconify-icon>
                          )}
                          ترقية
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ═══ 3. IP Ban Management ═══ */}
      <section className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <iconify-icon icon="lucide:shield-ban" class="text-xl text-brand-danger"></iconify-icon>
            <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">حظر IP</h2>
            <span className="text-sm font-bold text-gray-400 dark:text-gray-500">({bans.length})</span>
          </div>
          <button
            onClick={() => setShowBanModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-black bg-brand-danger/10 text-brand-danger hover:bg-brand-danger/20 smooth-transition"
          >
            <iconify-icon icon="lucide:plus"></iconify-icon>
            حظر IP جديد
          </button>
        </div>

        {bans.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400 font-bold">
            <iconify-icon icon="lucide:shield-check" class="text-3xl text-gray-300 dark:text-gray-600 mb-2"></iconify-icon>
            <p>لا توجد عناوين محظورة حالياً</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/40">
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">عنوان IP</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">السبب</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">تاريخ الحظر</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">ينتهي</th>
                  <th className="text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest">إجراء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {bans.map(ban => (
                  <tr key={ban.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                    <td className="px-6 py-4 font-bold text-gray-900 dark:text-white font-mono" dir="ltr">{ban.ip_address}</td>
                    <td className="px-6 py-4 text-gray-600 dark:text-gray-400">{ban.reason}</td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-xs" dir="ltr">
                      {ban.created_at ? new Date(ban.created_at).toLocaleDateString('ar-SA') : '—'}
                    </td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-xs" dir="ltr">
                      {ban.expires_at ? new Date(ban.expires_at).toLocaleDateString('ar-SA') : 'دائم'}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleUnban(ban.id)}
                        disabled={actionLoading === `ban-${ban.id}`}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition disabled:opacity-50"
                      >
                        {actionLoading === `ban-${ban.id}` ? (
                          <iconify-icon icon="lucide:loader-2" class="animate-spin text-xs"></iconify-icon>
                        ) : (
                          <iconify-icon icon="lucide:shield-off" class="text-xs"></iconify-icon>
                        )}
                        إلغاء الحظر
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ═══ 4. Quick Actions ═══ */}
      <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button
          onClick={handleBackup}
          className="flex items-center gap-4 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 shadow-sm hover:shadow-md smooth-transition group hover:-translate-y-0.5 text-right"
        >
          <div className="w-12 h-12 bg-purple-500/10 dark:bg-purple-500/20 rounded-xl flex items-center justify-center group-hover:bg-purple-500/20 smooth-transition">
            <iconify-icon icon="lucide:hard-drive-download" class="text-2xl text-purple-600 dark:text-purple-400"></iconify-icon>
          </div>
          <div>
            <h3 className="font-heading font-black text-gray-900 dark:text-white">تصدير نسخة احتياطية</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">تحميل نسخة من قاعدة البيانات</p>
          </div>
        </button>

        <Link
          to="/admin"
          className="flex items-center gap-4 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 shadow-sm hover:shadow-md smooth-transition group hover:-translate-y-0.5"
        >
          <div className="w-12 h-12 bg-amber-500/10 dark:bg-amber-500/20 rounded-xl flex items-center justify-center group-hover:bg-amber-500/20 smooth-transition">
            <iconify-icon icon="lucide:shield-check" class="text-2xl text-amber-600 dark:text-amber-400"></iconify-icon>
          </div>
          <div>
            <h3 className="font-heading font-black text-gray-900 dark:text-white">لوحة المشرف</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">الانتقال إلى لوحة تحكم المشرف</p>
          </div>
        </Link>
      </section>

      {/* IP Ban Modal */}
      {showBanModal && (
        <IpBanModal
          onClose={() => setShowBanModal(false)}
          onCreated={() => { setShowBanModal(false); fetchAll() }}
        />
      )}
    </div>
  )
}
