import { useState, useEffect, useMemo } from 'react'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

const CATEGORY_LABELS = {
  attack: 'إعدادات الهجوم',
  score: 'إعدادات النقاط',
  quiz: 'إعدادات الأسئلة',
  store: 'إعدادات المتجر',
  protection: 'إعدادات الحماية',
}

const CATEGORY_ICONS = {
  attack: 'lucide:swords',
  score: 'lucide:coins',
  quiz: 'lucide:book-open',
  store: 'lucide:shopping-bag',
  protection: 'lucide:shield',
}

function SettingInput({ setting, value, onChange }) {
  const dataType = setting.data_type

  if (dataType === 'boolean') {
    return (
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`relative w-12 h-6 rounded-full smooth-transition flex-shrink-0 ${value ? 'bg-brand-teal' : 'bg-gray-300 dark:bg-gray-600'}`}
      >
        <span
          className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow smooth-transition ${value ? 'left-0.5' : 'left-[calc(100%-22px)]'}`}
        />
      </button>
    )
  }

  if (dataType === 'integer') {
    return (
      <input
        type="number"
        step="1"
        value={value ?? ''}
        onChange={e => {
          const raw = e.target.value
          onChange(raw === '' ? '' : parseInt(raw, 10))
        }}
        className="w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white text-left focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
      />
    )
  }

  if (dataType === 'decimal') {
    return (
      <input
        type="number"
        step="any"
        value={value ?? ''}
        onChange={e => {
          const raw = e.target.value
          onChange(raw === '' ? '' : parseFloat(raw))
        }}
        className="w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white text-left focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
      />
    )
  }

  // Default: string / text
  return (
    <input
      type="text"
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      className="w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
    />
  )
}

export default function AdminSettingsPage() {
  // Game info (existing endpoint — kept as a separate card)
  const { data: gameInfo, loading: gameInfoLoading } = useAdminData('/api/admin/settings/game-info')

  // New settings endpoint
  const { data: settingsRaw, loading: settingsLoading, error: settingsError, refetch } = useAdminData('/api/admin/settings')

  // Local editable values keyed by setting key
  const [editedValues, setEditedValues] = useState({})
  // Track which keys have been changed relative to server state
  const [dirtyKeys, setDirtyKeys] = useState(new Set())
  const [saving, setSaving] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  // When settingsRaw changes (initial load or refetch), reset edit state
  useEffect(() => {
    if (settingsRaw) {
      const initial = {}
      settingsRaw.forEach(s => {
        initial[s.key] = s.current_value?.v ?? s.default_value?.v ?? ''
      })
      setEditedValues(initial)
      setDirtyKeys(new Set())
    }
  }, [settingsRaw])

  // Group settings by category
  const grouped = useMemo(() => {
    if (!settingsRaw) return {}
    const groups = {}
    settingsRaw.forEach(setting => {
      const cat = setting.category || 'other'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(setting)
    })
    return groups
  }, [settingsRaw])

  // Ordered categories (show only those that have settings)
  const categoryOrder = ['attack', 'score', 'quiz', 'store', 'protection']
  const visibleCategories = categoryOrder.filter(c => grouped[c]?.length > 0)
  // Add any categories not in the predefined list
  Object.keys(grouped).forEach(c => {
    if (!visibleCategories.includes(c)) visibleCategories.push(c)
  })

  function handleChange(key, newValue) {
    setEditedValues(prev => ({ ...prev, [key]: newValue }))

    // Determine if it's actually dirty (different from server value)
    const serverSetting = settingsRaw.find(s => s.key === key)
    const serverValue = serverSetting?.current_value?.v ?? serverSetting?.default_value?.v ?? ''
    setDirtyKeys(prev => {
      const next = new Set(prev)
      if (newValue === serverValue) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  async function handleSave() {
    if (dirtyKeys.size === 0) return
    setSaving(true)
    setActionMsg(null)

    const keys = Array.from(dirtyKeys)
    const results = await Promise.allSettled(
      keys.map(key =>
        apiFetch(`/api/admin/settings/${key}`, {
          method: 'PATCH',
          body: JSON.stringify({ value: { v: editedValues[key] } }),
        })
      )
    )

    const failed = results.filter(r => r.status === 'rejected')
    if (failed.length === 0) {
      setActionMsg('تم حفظ جميع الإعدادات بنجاح')
      setDirtyKeys(new Set())
      refetch()
    } else if (failed.length < keys.length) {
      setActionMsg(`تم حفظ ${keys.length - failed.length} إعداد، فشل ${failed.length}`)
      refetch()
    } else {
      setActionMsg(`خطأ: فشل حفظ الإعدادات — ${failed[0].reason?.message || 'خطأ غير معروف'}`)
    }

    setSaving(false)
    setTimeout(() => setActionMsg(null), 4000)
  }

  const isLoading = settingsLoading || gameInfoLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal dark:text-brand-slate animate-spin"></iconify-icon>
      </div>
    )
  }

  if (settingsError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <iconify-icon icon="lucide:alert-circle" class="text-4xl text-brand-danger"></iconify-icon>
        <p className="text-gray-500 dark:text-gray-400 font-bold">{settingsError}</p>
      </div>
    )
  }

  const hasDirty = dirtyKeys.size > 0
  const hasSettings = settingsRaw && settingsRaw.length > 0

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">الإعدادات</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">إعدادات المنافسة والقواعد</p>
        </div>
        {hasDirty && (
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
            <span className="bg-white/20 px-1.5 py-0.5 rounded-md text-xs">{dirtyKeys.size}</span>
          </button>
        )}
      </div>

      {/* Action Message */}
      {actionMsg && (
        <div
          className={`px-4 py-2 rounded-xl text-sm font-bold ${
            actionMsg.startsWith('خطأ')
              ? 'bg-brand-danger/10 text-brand-danger'
              : 'bg-brand-success/10 text-brand-success'
          }`}
        >
          {actionMsg}
        </div>
      )}

      {/* Game Info Card (existing endpoint) */}
      {gameInfo && Object.keys(gameInfo).length > 0 && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:info" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            معلومات اللعبة
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(gameInfo).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                <span className="text-sm font-bold text-gray-600 dark:text-gray-400">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="font-heading font-black text-sm text-gray-900 dark:text-white">
                  {typeof value === 'boolean' ? (value ? 'نعم' : 'لا') : String(value ?? '—')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Settings by Category */}
      {!hasSettings ? (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-8 text-center">
          <iconify-icon icon="lucide:settings" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="text-gray-500 dark:text-gray-400 font-bold">لا توجد إعدادات قابلة للتعديل بعد</p>
          <p className="text-sm text-gray-400 mt-1">سيتم عرض الإعدادات هنا بمجرد إنشاء منافسة نشطة</p>
        </div>
      ) : (
        visibleCategories.map(category => {
          const settings = grouped[category]
          if (!settings || settings.length === 0) return null

          const label = CATEGORY_LABELS[category] || category
          const icon = CATEGORY_ICONS[category] || 'lucide:settings-2'

          return (
            <div
              key={category}
              className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6"
            >
              <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <iconify-icon icon={icon} class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                {label}
              </h2>
              <div className="space-y-3">
                {settings.map(setting => {
                  const isDirty = dirtyKeys.has(setting.key)
                  return (
                    <div
                      key={setting.key}
                      className={`flex items-center justify-between gap-4 p-3 rounded-xl smooth-transition ${
                        isDirty
                          ? 'bg-brand-teal/5 dark:bg-brand-teal/10 ring-1 ring-brand-teal/20'
                          : 'bg-gray-50 dark:bg-gray-800/40'
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <label className="block font-bold text-sm text-gray-700 dark:text-gray-300">
                          {setting.description}
                        </label>
                        <span className="text-[11px] text-gray-400 dark:text-gray-500 font-mono">
                          {setting.key}
                        </span>
                        {setting.is_per_competition && (
                          <span className="inline-block mr-2 text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1.5 py-0.5 rounded font-black">
                            لكل منافسة
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {isDirty && (
                          <button
                            type="button"
                            onClick={() => {
                              const serverValue = setting.current_value?.v ?? setting.default_value?.v ?? ''
                              setEditedValues(prev => ({ ...prev, [setting.key]: serverValue }))
                              setDirtyKeys(prev => {
                                const next = new Set(prev)
                                next.delete(setting.key)
                                return next
                              })
                            }}
                            className="text-gray-400 hover:text-brand-danger smooth-transition"
                            title="تراجع"
                          >
                            <iconify-icon icon="lucide:undo-2" class="text-sm"></iconify-icon>
                          </button>
                        )}
                        <SettingInput
                          setting={setting}
                          value={editedValues[setting.key]}
                          onChange={val => handleChange(setting.key, val)}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
