import { useState } from 'react'
import { useAuthContext } from '../context/AuthContext'
import { apiFetch } from '../lib/api'

export default function AccountSettingsPage() {
  const { currentUser } = useAuthContext()
  const [realName, setRealName] = useState(currentUser?.real_name || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [deletionRequested, setDeletionRequested] = useState(false)

  async function handleRequestDeletion() {
    if (!confirm('هل أنت متأكد من طلب حذف حسابك؟ هذا الإجراء لا يمكن التراجع عنه.')) return
    try {
      await apiFetch('/api/auth/me/request-deletion', { method: 'POST' })
      setDeletionRequested(true)
    } catch (err) {
      // Don't set deletionRequested on error — show the error instead
      alert(err.message || 'فشل إرسال الطلب')
    }
  }

  async function handleSaveProfile(e) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      await apiFetch('/api/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({ real_name: realName }),
      })
      setMessage({ type: 'success', text: 'تم تحديث الملف الشخصي بنجاح' })
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'كلمات المرور غير متطابقة' })
      return
    }
    setSaving(true)
    setMessage(null)
    try {
      await apiFetch('/api/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      })
      setMessage({ type: 'success', text: 'تم تغيير كلمة المرور بنجاح' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 w-full max-w-2xl mx-auto px-4 py-8 md:py-14 space-y-6">

      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">إعدادات الحساب</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">تعديل بيانات حسابك</p>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-xl text-sm font-bold ${message.type === 'error' ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>
          {message.text}
        </div>
      )}

      {/* Profile Info */}
      <form onSubmit={handleSaveProfile} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6 space-y-5">
        <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
          <iconify-icon icon="lucide:user" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
          الملف الشخصي
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">اسم المستخدم</label>
            <input
              type="text"
              value={currentUser?.username || ''}
              disabled
              className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-400 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">الاسم الحقيقي</label>
            <input
              type="text"
              value={realName}
              onChange={e => setRealName(e.target.value)}
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal-hover text-white px-5 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50"
          >
            {saving ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon="lucide:save"></iconify-icon>
            )}
            حفظ
          </button>
        </div>
      </form>

      {/* Change Password */}
      <form onSubmit={handleChangePassword} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6 space-y-5">
        <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
          <iconify-icon icon="lucide:lock" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
          تغيير كلمة المرور
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">كلمة المرور الحالية</label>
            <input
              type="password"
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">كلمة المرور الجديدة</label>
            <input
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
              required
              minLength={6}
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-600 dark:text-gray-400 mb-1">تأكيد كلمة المرور</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
              required
              minLength={6}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal-hover text-white px-5 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50"
          >
            {saving ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon="lucide:key"></iconify-icon>
            )}
            تغيير كلمة المرور
          </button>
        </div>
      </form>

      {/* Danger Zone */}
      <div className="mt-10 border-t border-red-200 dark:border-red-900/30 pt-8">
        <h2 className="text-lg font-heading font-black text-brand-danger mb-2">منطقة الخطر</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          بمجرد طلب حذف الحساب، سيتم مراجعته من قبل الإدارة. هذا الإجراء لا يمكن التراجع عنه.
        </p>
        <button
          onClick={handleRequestDeletion}
          disabled={deletionRequested}
          className="bg-brand-danger/10 text-brand-danger border border-brand-danger/20 hover:bg-brand-danger/20 px-6 py-3 rounded-xl font-bold smooth-transition disabled:opacity-50"
        >
          {deletionRequested ? 'تم إرسال طلب الحذف' : 'طلب حذف الحساب'}
        </button>
      </div>
    </div>
  )
}
