import { useState, useEffect } from 'react'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

export default function AdminSettingsPage() {
  const { data: settings, loading, refetch } = useAdminData('/api/admin/settings/game-info')
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (settings) {
      setForm(settings)
      setDirty(false)
    }
  }, [settings])

  function updateField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
    setDirty(true)
  }

  async function handleSave() {
    setSaving(true)
    try {
      await apiFetch('/api/admin/settings/game-info', {
        method: 'PUT',
        body: JSON.stringify(form),
      })
      setActionMsg('تم حفظ الإعدادات بنجاح')
      setDirty(false)
      refetch()
      setTimeout(() => setActionMsg(null), 3000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  // Group settings by prefix for organized display
  const groups = {}
  Object.entries(form).forEach(([key, value]) => {
    const prefix = key.split('_')[0]
    const groupMap = {
      attack: 'إعدادات الهجوم',
      quiz: 'إعدادات الأسئلة',
      store: 'إعدادات المتجر',
      score: 'إعدادات النقاط',
      protection: 'إعدادات الحماية',
      bankruptcy: 'إعدادات الإفلاس',
      distribution: 'إعدادات التوزيع',
      notification: 'إعدادات الإشعارات',
    }
    const groupName = groupMap[prefix] || 'إعدادات عامة'
    if (!groups[groupName]) groups[groupName] = []
    groups[groupName].push({ key, value })
  })

  // If settings is empty or null, show a note
  const hasSettings = Object.keys(form).length > 0

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">الإعدادات</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">إعدادات المنافسة والقواعد</p>
        </div>
        {dirty && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal-hover text-white px-5 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50"
          >
            {saving ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon="lucide:save"></iconify-icon>
            )}
            حفظ التغييرات
          </button>
        )}
      </div>

      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>
          {actionMsg}
        </div>
      )}

      {!hasSettings ? (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-8 text-center">
          <iconify-icon icon="lucide:settings" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="text-gray-500 dark:text-gray-400 font-bold">لا توجد إعدادات قابلة للتعديل بعد</p>
          <p className="text-sm text-gray-400 mt-1">سيتم عرض الإعدادات هنا بمجرد إنشاء منافسة نشطة</p>
        </div>
      ) : (
        Object.entries(groups).map(([groupName, fields]) => (
          <div key={groupName} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
            <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <iconify-icon icon="lucide:settings-2" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
              {groupName}
            </h2>
            <div className="space-y-4">
              {fields.map(({ key, value }) => (
                <div key={key} className="flex items-center justify-between gap-4 p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                  <label className="font-bold text-sm text-gray-700 dark:text-gray-300 flex-shrink-0">
                    {key.replace(/_/g, ' ')}
                  </label>
                  {typeof value === 'boolean' ? (
                    <button
                      onClick={() => updateField(key, !value)}
                      className={`relative w-12 h-6 rounded-full smooth-transition ${value ? 'bg-brand-teal' : 'bg-gray-300 dark:bg-gray-600'}`}
                    >
                      <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow smooth-transition ${value ? 'left-0.5' : 'left-[calc(100%-22px)]'}`} />
                    </button>
                  ) : typeof value === 'number' ? (
                    <input
                      type="number"
                      value={value}
                      onChange={e => updateField(key, parseFloat(e.target.value) || 0)}
                      className="w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white text-left focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                    />
                  ) : (
                    <input
                      type="text"
                      value={value || ''}
                      onChange={e => updateField(key, e.target.value)}
                      className="w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
