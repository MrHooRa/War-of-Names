/**
 * OwnerDashboardPage — Owner-only control panel.
 *
 * Sections:
 *  1. Platform Stats Grid
 *  2. Platform Health (DB + Scheduler)
 *  3. Admin Management (create, edit, reset password, promote/demote, disable)
 *  4. Deletion Requests
 *  5. IP Ban Management (add/remove)
 *  6. Quick Actions (backup, link to admin)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'

/* ─────────────────────────────────────────────────────────────────────── */
/*  Shared UI Components                                                  */
/* ─────────────────────────────────────────────────────────────────────── */

const INPUT_CLS = 'w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/30'
const TH_CLS = 'text-right px-6 py-3 font-black text-gray-500 dark:text-gray-400 text-xs uppercase tracking-widest'

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
      <div className="text-3xl font-black text-gray-900 dark:text-white">{value ?? '---'}</div>
    </div>
  )
}

/* ── Modal Overlay ── */
function ModalOverlay({ children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

/* ── Modal Header ── */
function ModalHeader({ icon, iconColor, title }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div className={`w-10 h-10 ${iconColor} rounded-xl flex items-center justify-center`}>
        <iconify-icon icon={icon} class="text-xl"></iconify-icon>
      </div>
      <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white">{title}</h3>
    </div>
  )
}

/* ── Confirmation Dialog ── */
function ConfirmDialog({ title, message, confirmLabel, confirmColor = 'bg-brand-danger hover:bg-red-600', onConfirm, onClose, loading }) {
  return (
    <ModalOverlay onClose={onClose}>
      <ModalHeader icon="lucide:alert-triangle" iconColor="bg-brand-danger/10 text-brand-danger" title={title} />
      <p className="text-sm text-gray-600 dark:text-gray-400 font-bold mb-6">{message}</p>
      <div className="flex gap-3">
        <button
          onClick={onConfirm}
          disabled={loading}
          className={`flex-1 flex items-center justify-center gap-2 ${confirmColor} text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50`}
        >
          {loading && <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>}
          {confirmLabel}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
        >
          إلغاء
        </button>
      </div>
    </ModalOverlay>
  )
}

/* ── Status label helper ── */
function statusLabel(s) {
  const map = { active: 'نشط', suspended: 'معلّق', disabled: 'معطّل', archived: 'مؤرشف' }
  return map[s] || s
}
function statusBadge(s) {
  const cls = s === 'active'
    ? 'bg-brand-success/10 text-brand-success'
    : s === 'disabled' || s === 'archived'
      ? 'bg-brand-danger/10 text-brand-danger'
      : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
  const dotCls = s === 'active' ? 'bg-brand-success' : s === 'disabled' || s === 'archived' ? 'bg-brand-danger' : 'bg-gray-400'
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-black ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotCls}`}></span>
      {statusLabel(s)}
    </span>
  )
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  IP Ban Modal                                                          */
/* ─────────────────────────────────────────────────────────────────────── */

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
    <ModalOverlay onClose={onClose}>
      <ModalHeader icon="lucide:shield-ban" iconColor="bg-brand-danger/10 text-brand-danger" title="حظر IP جديد" />
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">عنوان IP</label>
          <input type="text" value={ip} onChange={e => setIp(e.target.value)} placeholder="192.168.1.1" required className={INPUT_CLS} dir="ltr" />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">السبب</label>
          <input type="text" value={reason} onChange={e => setReason(e.target.value)} placeholder="سبب الحظر..." required className={INPUT_CLS} />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">تاريخ انتهاء الحظر (اختياري)</label>
          <input type="datetime-local" value={expiresAt} onChange={e => setExpiresAt(e.target.value)} className={INPUT_CLS} dir="ltr" />
        </div>
        {error && (
          <p className="text-brand-danger text-sm font-bold text-center py-2 bg-red-500/10 rounded-xl border border-red-500/20">{error}</p>
        )}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="flex-1 flex items-center justify-center gap-2 bg-brand-danger hover:bg-red-600 text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon> : <iconify-icon icon="lucide:shield-ban"></iconify-icon>}
            تنفيذ الحظر
          </button>
          <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
        </div>
      </form>
    </ModalOverlay>
  )
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  Create Admin Modal                                                    */
/* ─────────────────────────────────────────────────────────────────────── */

function CreateAdminModal({ onClose, onCreated }) {
  const [username, setUsername] = useState('')
  const [realName, setRealName] = useState('')
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await apiFetch('/api/owner/admins/create', {
        method: 'POST',
        body: JSON.stringify({ username, real_name: realName, password, is_admin: true }),
      })
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <ModalHeader icon="lucide:user-plus" iconColor="bg-purple-500/10 text-purple-500" title="إنشاء مشرف جديد" />
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">اسم المستخدم</label>
          <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="admin_name" required minLength={2} className={INPUT_CLS} dir="ltr" />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">الاسم الحقيقي</label>
          <input type="text" value={realName} onChange={e => setRealName(e.target.value)} placeholder="الاسم الكامل" required minLength={2} className={INPUT_CLS} />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">كلمة المرور</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="6 أحرف على الأقل" required minLength={6} className={INPUT_CLS} dir="ltr" />
        </div>
        {error && (
          <p className="text-brand-danger text-sm font-bold text-center py-2 bg-red-500/10 rounded-xl border border-red-500/20">{error}</p>
        )}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="flex-1 flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon> : <iconify-icon icon="lucide:user-plus"></iconify-icon>}
            إنشاء المشرف
          </button>
          <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
        </div>
      </form>
    </ModalOverlay>
  )
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  Reset Password Modal                                                  */
/* ─────────────────────────────────────────────────────────────────────── */

function ResetPasswordModal({ account, onClose, onDone }) {
  const [newPassword, setNewPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await apiFetch(`/api/owner/admins/${account.id}/reset-password`, {
        method: 'PATCH',
        body: JSON.stringify({ new_password: newPassword }),
      })
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <ModalHeader icon="lucide:key-round" iconColor="bg-amber-500/10 text-amber-500" title="إعادة تعيين كلمة المرور" />
      <p className="text-sm text-gray-500 dark:text-gray-400 font-bold mb-4">
        الحساب: <span className="text-gray-900 dark:text-white">{account.username}</span>
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">كلمة المرور الجديدة</label>
          <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="6 أحرف على الأقل" required minLength={6} className={INPUT_CLS} dir="ltr" />
        </div>
        {error && (
          <p className="text-brand-danger text-sm font-bold text-center py-2 bg-red-500/10 rounded-xl border border-red-500/20">{error}</p>
        )}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="flex-1 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon> : <iconify-icon icon="lucide:key-round"></iconify-icon>}
            إعادة تعيين
          </button>
          <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
        </div>
      </form>
    </ModalOverlay>
  )
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  Edit Account Modal                                                    */
/* ─────────────────────────────────────────────────────────────────────── */

function EditAccountModal({ account, onClose, onDone }) {
  const [username, setUsername] = useState(account.username)
  const [realName, setRealName] = useState(account.real_name || '')
  const [accountStatus, setAccountStatus] = useState(account.status)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const body = {}
      if (username !== account.username) body.username = username
      if (realName !== account.real_name) body.real_name = realName
      if (accountStatus !== account.status) body.status = accountStatus
      await apiFetch(`/api/owner/admins/${account.id}/update`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      })
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <ModalHeader icon="lucide:pencil" iconColor="bg-blue-500/10 text-blue-500" title="تعديل الحساب" />
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">اسم المستخدم</label>
          <input type="text" value={username} onChange={e => setUsername(e.target.value)} required minLength={2} className={INPUT_CLS} dir="ltr" />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">الاسم الحقيقي</label>
          <input type="text" value={realName} onChange={e => setRealName(e.target.value)} required minLength={2} className={INPUT_CLS} />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">الحالة</label>
          <select value={accountStatus} onChange={e => setAccountStatus(e.target.value)} className={INPUT_CLS}>
            <option value="active">نشط</option>
            <option value="suspended">معلّق</option>
            <option value="disabled">معطّل</option>
            <option value="archived">مؤرشف</option>
          </select>
        </div>
        {error && (
          <p className="text-brand-danger text-sm font-bold text-center py-2 bg-red-500/10 rounded-xl border border-red-500/20">{error}</p>
        )}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="flex-1 flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon> : <iconify-icon icon="lucide:check"></iconify-icon>}
            حفظ التعديلات
          </button>
          <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
        </div>
      </form>
    </ModalOverlay>
  )
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  Main Dashboard                                                        */
/* ─────────────────────────────────────────────────────────────────────── */

export default function OwnerDashboardPage() {
  const [stats, setStats] = useState(null)
  const [admins, setAdmins] = useState([])
  const [allAccounts, setAllAccounts] = useState([])
  const [bans, setBans] = useState([])
  const [deletionRequests, setDeletionRequests] = useState([])
  const [loading, setLoading] = useState(true)

  // Modals
  const [showBanModal, setShowBanModal] = useState(false)
  const [showCreateAdminModal, setShowCreateAdminModal] = useState(false)
  const [resetPasswordTarget, setResetPasswordTarget] = useState(null)
  const [editTarget, setEditTarget] = useState(null)
  const [disableConfirm, setDisableConfirm] = useState(null)

  // UI state
  const [actionLoading, setActionLoading] = useState(null)
  const [actionMsg, setActionMsg] = useState(null)
  const [accountSearch, setAccountSearch] = useState('')
  const [showAllAccounts, setShowAllAccounts] = useState(false)
  const [openDropdown, setOpenDropdown] = useState(null)
  const dropdownRef = useRef(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpenDropdown(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  /* ── Data Fetching ── */

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, adminsRes, bansRes, deletionRes] = await Promise.all([
        apiFetch('/api/owner/dashboard'),
        apiFetch('/api/owner/admins'),
        apiFetch('/api/owner/ip-bans'),
        apiFetch('/api/owner/deletion-requests').catch(() => ({ data: [] })),
      ])
      if (statsRes.data) setStats(statsRes.data)
      if (adminsRes.data) setAdmins(adminsRes.data)
      if (bansRes.data) setBans(bansRes.data)
      if (deletionRes.data) setDeletionRequests(deletionRes.data)
    } catch {
      // Individual failures handled silently; partial data is OK
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  // Fetch all accounts when toggled on or search changes
  useEffect(() => {
    if (!showAllAccounts) return
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      try {
        const res = await apiFetch(`/api/owner/accounts?search=${encodeURIComponent(accountSearch)}`, { signal: controller.signal })
        if (res.data) setAllAccounts(res.data)
      } catch { /* ignored */ }
    }, 300)
    return () => { clearTimeout(timer); controller.abort() }
  }, [showAllAccounts, accountSearch])

  /* ── Action helpers ── */

  function flash(type, text) {
    setActionMsg({ type, text })
    setTimeout(() => setActionMsg(null), 3000)
  }

  async function handlePromote(accountId) {
    setActionLoading(accountId)
    try {
      await apiFetch(`/api/owner/admins/${accountId}/promote`, { method: 'PATCH' })
      flash('success', 'تمت الترقية بنجاح')
      fetchAll()
    } catch (err) { flash('error', err.message) }
    finally { setActionLoading(null) }
  }

  async function handleDemote(accountId) {
    setActionLoading(accountId)
    try {
      await apiFetch(`/api/owner/admins/${accountId}/demote`, { method: 'PATCH' })
      flash('success', 'تم التخفيض بنجاح')
      fetchAll()
    } catch (err) { flash('error', err.message) }
    finally { setActionLoading(null) }
  }

  async function handleDisable(accountId) {
    setActionLoading(accountId)
    try {
      await apiFetch(`/api/owner/admins/${accountId}/remove`, { method: 'DELETE' })
      flash('success', 'تم تعطيل الحساب')
      setDisableConfirm(null)
      fetchAll()
    } catch (err) { flash('error', err.message) }
    finally { setActionLoading(null) }
  }

  async function handleUnban(banId) {
    setActionLoading(`ban-${banId}`)
    try {
      await apiFetch(`/api/owner/ip-bans/${banId}`, { method: 'DELETE' })
      flash('success', 'تم إلغاء الحظر')
      fetchAll()
    } catch (err) { flash('error', err.message) }
    finally { setActionLoading(null) }
  }

  async function handleApproveDeletion(accountId) {
    setActionLoading(`del-${accountId}`)
    try {
      await apiFetch(`/api/owner/deletion-requests/${accountId}/approve`, { method: 'POST' })
      flash('success', 'تمت الموافقة على الحذف')
      fetchAll()
    } catch (err) { flash('error', err.message) }
    finally { setActionLoading(null) }
  }

  async function handleRejectDeletion(accountId) {
    setActionLoading(`del-${accountId}`)
    try {
      await apiFetch(`/api/owner/deletion-requests/${accountId}/reject`, { method: 'POST' })
      flash('success', 'تم رفض طلب الحذف')
      fetchAll()
    } catch (err) { flash('error', err.message) }
    finally { setActionLoading(null) }
  }

  async function handleBackup() {
    try {
      const res = await fetch('/api/owner/backup', {
        headers: { Authorization: `Bearer ${localStorage.getItem('won_token')}` },
      })
      if (!res.ok) throw new Error('فشل تحميل النسخة الاحتياطية')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `won-backup-${new Date().toISOString().slice(0, 10)}.json.gz`
      a.click()
      URL.revokeObjectURL(url)
      flash('success', 'تم تحميل النسخة الاحتياطية')
    } catch (err) {
      flash('error', err.message)
    }
  }

  /* ── Determine which account list to display ── */
  const displayAccounts = showAllAccounts ? allAccounts : admins

  /* ── Loading ── */

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
        <div className={`px-4 py-3 rounded-xl text-sm font-bold flex items-center gap-2 ${actionMsg.type === 'error' ? 'bg-brand-danger/10 text-brand-danger border border-brand-danger/20' : 'bg-brand-success/10 text-brand-success border border-brand-success/20'}`}>
          <iconify-icon icon={actionMsg.type === 'error' ? 'lucide:alert-circle' : 'lucide:check-circle-2'} class="text-base"></iconify-icon>
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
          <StatCard icon="lucide:trophy" label="منافسات نشطة" value={stats?.total_active_competitions} color="brand-success" />
          <StatCard icon="lucide:user-check" label="العضويات" value={stats?.total_memberships} color="brand-teal" />
          <StatCard icon="lucide:swords" label="الهجمات" value={stats?.total_attacks} color="brand-orange" />
          <StatCard icon="lucide:brain" label="جلسات الأسئلة" value={stats?.total_quiz_sessions} color="blue" />
        </div>
      </section>

      {/* ═══ 2. Platform Health ═══ */}
      <section className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <iconify-icon icon="lucide:heart-pulse" class="text-xl text-purple-500"></iconify-icon>
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">صحة المنصة</h2>
        </div>
        <div className="p-6 space-y-5">
          {/* DB + Scheduler status row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Database connection */}
            <div className="flex items-center gap-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl p-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stats?.system?.db_connected ? 'bg-brand-success/10' : 'bg-brand-danger/10'}`}>
                <iconify-icon icon="lucide:database" class={`text-xl ${stats?.system?.db_connected ? 'text-brand-success' : 'text-brand-danger'}`}></iconify-icon>
              </div>
              <div>
                <p className="text-sm font-black text-gray-900 dark:text-white">قاعدة البيانات</p>
                <p className={`text-xs font-bold ${stats?.system?.db_connected ? 'text-brand-success' : 'text-brand-danger'}`}>
                  {stats?.system?.db_connected ? 'متصلة' : 'غير متصلة'}
                </p>
              </div>
              <div className={`mr-auto w-3 h-3 rounded-full ${stats?.system?.db_connected ? 'bg-brand-success animate-pulse' : 'bg-brand-danger'}`}></div>
            </div>
            {/* Scheduler status */}
            <div className="flex items-center gap-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl p-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stats?.system?.scheduler_running ? 'bg-brand-success/10' : 'bg-brand-danger/10'}`}>
                <iconify-icon icon="lucide:timer" class={`text-xl ${stats?.system?.scheduler_running ? 'text-brand-success' : 'text-brand-danger'}`}></iconify-icon>
              </div>
              <div>
                <p className="text-sm font-black text-gray-900 dark:text-white">المجدول</p>
                <p className={`text-xs font-bold ${stats?.system?.scheduler_running ? 'text-brand-success' : 'text-brand-danger'}`}>
                  {stats?.system?.scheduler_running ? 'يعمل' : 'متوقف'}
                </p>
              </div>
              <div className={`mr-auto w-3 h-3 rounded-full ${stats?.system?.scheduler_running ? 'bg-brand-success animate-pulse' : 'bg-brand-danger'}`}></div>
            </div>
          </div>

          {/* Scheduler jobs */}
          {stats?.system?.scheduler_jobs?.length > 0 && (
            <div>
              <h3 className="text-sm font-black text-gray-600 dark:text-gray-400 mb-3 flex items-center gap-2">
                <iconify-icon icon="lucide:list-checks" class="text-purple-400"></iconify-icon>
                المهام المجدولة
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {stats.system.scheduler_jobs.map(job => (
                  <div key={job.id} className="bg-gray-50 dark:bg-gray-800/40 rounded-xl p-3 border border-gray-100 dark:border-gray-700/50">
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-2 h-2 rounded-full bg-brand-success animate-pulse"></div>
                      <span className="text-xs font-black text-gray-900 dark:text-white truncate">{job.name || job.id}</span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-bold">التشغيل التالي: </span>
                      {job.next_run_time
                        ? new Date(job.next_run_time).toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                        : '---'}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 font-mono" dir="ltr">{job.trigger}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ═══ 3. Admin Management ═══ */}
      <section className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex items-center gap-3 flex-1">
            <iconify-icon icon="lucide:shield-check" class="text-xl text-purple-500"></iconify-icon>
            <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">إدارة الحسابات</h2>
            <span className="text-sm font-bold text-gray-400 dark:text-gray-500">({displayAccounts.length})</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Toggle: Show all accounts vs admins only */}
            <button
              onClick={() => { setShowAllAccounts(v => !v); setAccountSearch('') }}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-black smooth-transition border ${showAllAccounts ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20' : 'bg-gray-50 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700'}`}
            >
              <iconify-icon icon={showAllAccounts ? 'lucide:users' : 'lucide:shield-check'} class="text-xs"></iconify-icon>
              {showAllAccounts ? 'جميع الحسابات' : 'المشرفون فقط'}
            </button>

            {/* Create admin */}
            <button
              onClick={() => setShowCreateAdminModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-black bg-purple-600 text-white hover:bg-purple-700 smooth-transition"
            >
              <iconify-icon icon="lucide:user-plus" class="text-xs"></iconify-icon>
              إنشاء مشرف جديد
            </button>
          </div>
        </div>

        {/* Search bar (visible when showing all accounts) */}
        {showAllAccounts && (
          <div className="px-6 py-3 border-b border-gray-100 dark:border-gray-800">
            <div className="relative">
              <iconify-icon icon="lucide:search" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm"></iconify-icon>
              <input
                type="text"
                value={accountSearch}
                onChange={e => setAccountSearch(e.target.value)}
                placeholder="بحث باسم المستخدم أو الاسم الحقيقي..."
                className="w-full bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700 rounded-xl pr-10 pl-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500/30"
              />
            </div>
          </div>
        )}

        {displayAccounts.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400 font-bold">
            {showAllAccounts ? 'لا توجد حسابات مطابقة' : 'لا توجد حسابات مشرفين'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/40">
                  <th className={TH_CLS}>المستخدم</th>
                  <th className={TH_CLS}>الاسم الحقيقي</th>
                  <th className={TH_CLS}>الحالة</th>
                  <th className={TH_CLS}>الدور</th>
                  <th className={TH_CLS}>إجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {displayAccounts.map(acct => (
                  <tr key={acct.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                    <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">{acct.username}</td>
                    <td className="px-6 py-4 text-gray-600 dark:text-gray-400">{acct.real_name || '---'}</td>
                    <td className="px-6 py-4">{statusBadge(acct.status)}</td>
                    <td className="px-6 py-4">
                      {acct.is_owner ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black bg-purple-500/10 text-purple-600 dark:text-purple-400">
                          <iconify-icon icon="lucide:crown" class="text-xs"></iconify-icon>
                          مالك
                        </span>
                      ) : acct.is_admin ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black bg-amber-500/10 text-amber-600 dark:text-amber-400">
                          <iconify-icon icon="lucide:shield-check" class="text-xs"></iconify-icon>
                          مشرف
                        </span>
                      ) : (
                        <span className="text-xs font-bold text-gray-400">متسابق</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {acct.is_owner ? (
                        <span className="text-xs text-gray-400 font-bold">---</span>
                      ) : (
                        <div className="relative" ref={openDropdown === acct.id ? dropdownRef : undefined}>
                          <button
                            onClick={() => setOpenDropdown(openDropdown === acct.id ? null : acct.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition"
                          >
                            <iconify-icon icon="lucide:more-horizontal" class="text-sm"></iconify-icon>
                            إجراءات
                          </button>

                          {openDropdown === acct.id && (
                            <div className="absolute left-0 top-full mt-1 z-30 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg py-1 min-w-[180px]">
                              {/* Promote / Demote */}
                              {acct.is_admin ? (
                                <button
                                  onClick={() => { setOpenDropdown(null); handleDemote(acct.id) }}
                                  disabled={actionLoading === acct.id}
                                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-black text-brand-danger hover:bg-red-50 dark:hover:bg-red-500/10 smooth-transition"
                                >
                                  <iconify-icon icon="lucide:arrow-down" class="text-sm"></iconify-icon>
                                  تخفيض من مشرف
                                </button>
                              ) : (
                                <button
                                  onClick={() => { setOpenDropdown(null); handlePromote(acct.id) }}
                                  disabled={actionLoading === acct.id}
                                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-black text-brand-success hover:bg-green-50 dark:hover:bg-green-500/10 smooth-transition"
                                >
                                  <iconify-icon icon="lucide:arrow-up" class="text-sm"></iconify-icon>
                                  ترقية لمشرف
                                </button>
                              )}

                              {/* Reset password */}
                              <button
                                onClick={() => { setOpenDropdown(null); setResetPasswordTarget(acct) }}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-black text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-500/10 smooth-transition"
                              >
                                <iconify-icon icon="lucide:key-round" class="text-sm"></iconify-icon>
                                إعادة تعيين كلمة المرور
                              </button>

                              {/* Edit */}
                              <button
                                onClick={() => { setOpenDropdown(null); setEditTarget(acct) }}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-black text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 smooth-transition"
                              >
                                <iconify-icon icon="lucide:pencil" class="text-sm"></iconify-icon>
                                تعديل
                              </button>

                              {/* Disable */}
                              <div className="border-t border-gray-100 dark:border-gray-700 my-1"></div>
                              <button
                                onClick={() => { setOpenDropdown(null); setDisableConfirm(acct) }}
                                className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-black text-brand-danger hover:bg-red-50 dark:hover:bg-red-500/10 smooth-transition"
                              >
                                <iconify-icon icon="lucide:user-x" class="text-sm"></iconify-icon>
                                تعطيل الحساب
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ═══ 4. Deletion Requests ═══ */}
      <section className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <iconify-icon icon="lucide:trash-2" class="text-xl text-brand-danger"></iconify-icon>
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">طلبات حذف الحسابات</h2>
          <span className="text-sm font-bold text-gray-400 dark:text-gray-500">({deletionRequests.length})</span>
        </div>

        {deletionRequests.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400 font-bold">
            <iconify-icon icon="lucide:inbox" class="text-3xl text-gray-300 dark:text-gray-600 mb-2 block mx-auto"></iconify-icon>
            <p>لا توجد طلبات حذف معلقة</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/40">
                  <th className={TH_CLS}>المستخدم</th>
                  <th className={TH_CLS}>الاسم الحقيقي</th>
                  <th className={TH_CLS}>حالة الحساب</th>
                  <th className={TH_CLS}>السبب</th>
                  <th className={TH_CLS}>تاريخ الطلب</th>
                  <th className={TH_CLS}>إجراء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {deletionRequests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                    <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">{req.username}</td>
                    <td className="px-6 py-4 text-gray-600 dark:text-gray-400">{req.real_name || '---'}</td>
                    <td className="px-6 py-4">{req.account_status ? statusBadge(req.account_status) : '---'}</td>
                    <td className="px-6 py-4 text-gray-600 dark:text-gray-400 text-xs max-w-[200px] truncate">{req.reason}</td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-xs" dir="ltr">
                      {req.requested_at ? new Date(req.requested_at).toLocaleDateString('ar-SA') : '---'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApproveDeletion(req.account_id)}
                          disabled={actionLoading === `del-${req.account_id}`}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-black bg-brand-danger/10 text-brand-danger hover:bg-brand-danger/20 smooth-transition disabled:opacity-50"
                        >
                          {actionLoading === `del-${req.account_id}` ? (
                            <iconify-icon icon="lucide:loader-2" class="animate-spin text-xs"></iconify-icon>
                          ) : (
                            <iconify-icon icon="lucide:check" class="text-xs"></iconify-icon>
                          )}
                          موافقة
                        </button>
                        <button
                          onClick={() => handleRejectDeletion(req.account_id)}
                          disabled={actionLoading === `del-${req.account_id}`}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-black bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50"
                        >
                          <iconify-icon icon="lucide:x" class="text-xs"></iconify-icon>
                          رفض
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ═══ 5. IP Ban Management ═══ */}
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
            <iconify-icon icon="lucide:shield-check" class="text-3xl text-gray-300 dark:text-gray-600 mb-2 block mx-auto"></iconify-icon>
            <p>لا توجد عناوين محظورة حالياً</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/40">
                  <th className={TH_CLS}>عنوان IP</th>
                  <th className={TH_CLS}>السبب</th>
                  <th className={TH_CLS}>تاريخ الحظر</th>
                  <th className={TH_CLS}>ينتهي</th>
                  <th className={TH_CLS}>إجراء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {bans.map(ban => (
                  <tr key={ban.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                    <td className="px-6 py-4 font-bold text-gray-900 dark:text-white font-mono" dir="ltr">{ban.ip_address}</td>
                    <td className="px-6 py-4 text-gray-600 dark:text-gray-400">{ban.reason}</td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-xs" dir="ltr">
                      {ban.created_at ? new Date(ban.created_at).toLocaleDateString('ar-SA') : '---'}
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

      {/* ═══ 6. Quick Actions ═══ */}
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

      {/* ═══ Modals ═══ */}

      {showBanModal && (
        <IpBanModal
          onClose={() => setShowBanModal(false)}
          onCreated={() => { setShowBanModal(false); fetchAll() }}
        />
      )}

      {showCreateAdminModal && (
        <CreateAdminModal
          onClose={() => setShowCreateAdminModal(false)}
          onCreated={() => { setShowCreateAdminModal(false); flash('success', 'تم إنشاء حساب المشرف بنجاح'); fetchAll() }}
        />
      )}

      {resetPasswordTarget && (
        <ResetPasswordModal
          account={resetPasswordTarget}
          onClose={() => setResetPasswordTarget(null)}
          onDone={() => { setResetPasswordTarget(null); flash('success', 'تم إعادة تعيين كلمة المرور بنجاح') }}
        />
      )}

      {editTarget && (
        <EditAccountModal
          account={editTarget}
          onClose={() => setEditTarget(null)}
          onDone={() => { setEditTarget(null); flash('success', 'تم تحديث بيانات الحساب بنجاح'); fetchAll() }}
        />
      )}

      {disableConfirm && (
        <ConfirmDialog
          title="تعطيل الحساب"
          message={`هل أنت متأكد من تعطيل حساب "${disableConfirm.username}"؟ سيتم إلغاء صلاحيات المشرف وتعطيل الحساب.`}
          confirmLabel="تعطيل"
          onConfirm={() => handleDisable(disableConfirm.id)}
          onClose={() => setDisableConfirm(null)}
          loading={actionLoading === disableConfirm.id}
        />
      )}
    </div>
  )
}
