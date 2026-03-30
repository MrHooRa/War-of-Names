/**
 * AdminSettingsPage — Competition-scoped settings.
 * Shows effective values for the selected competition with source indicators
 * (default / global / competition override). Allows overriding at competition level
 * and resetting overrides to fall back to global defaults.
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'

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

const SOURCE_LABELS = {
  default: { text: 'افتراضي', color: 'bg-gray-100 dark:bg-gray-800 text-gray-500' },
  global: { text: 'عام', color: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' },
  competition: { text: 'مخصص', color: 'bg-brand-teal/10 text-brand-teal dark:text-brand-slate' },
}

function SettingInput({ dataType, value, onChange }) {
  if (dataType === 'boolean') {
    return (
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`relative w-12 h-6 rounded-full smooth-transition flex-shrink-0 ${value ? 'bg-brand-teal' : 'bg-gray-300 dark:bg-gray-600'}`}
      >
        <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow smooth-transition ${value ? 'left-0.5' : 'left-[calc(100%-22px)]'}`} />
      </button>
    )
  }

  if (dataType === 'integer') {
    return (
      <input
        type="number"
        step="1"
        value={value ?? ''}
        onChange={e => onChange(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
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
        onChange={e => onChange(e.target.value === '' ? '' : parseFloat(e.target.value))}
        className="w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white text-left focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
      />
    )
  }

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
  const { selected, selectedId } = useAdminCompetition()
  const [settings, setSettings] = useState([])
  const [loading, setLoading] = useState(true)
  const [editedValues, setEditedValues] = useState({})
  const [dirtyKeys, setDirtyKeys] = useState(new Set())
  const [saving, setSaving] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  const loadSettings = useCallback(() => {
    if (!selectedId) return
    setLoading(true)
    apiFetch(`/api/admin/competitions/${selectedId}/settings`)
      .then(json => {
        const data = json.data || []
        setSettings(data)
        const initial = {}
        data.forEach(s => {
          initial[s.key] = s.effective_value?.v ?? ''
        })
        setEditedValues(initial)
        setDirtyKeys(new Set())
      })
      .catch(() => setSettings([]))
      .finally(() => setLoading(false))
  }, [selectedId])

  useEffect(() => { loadSettings() }, [loadSettings])

  const grouped = useMemo(() => {
    const groups = {}
    settings.forEach(s => {
      const cat = s.category || 'other'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(s)
    })
    return groups
  }, [settings])

  const categoryOrder = ['attack', 'score', 'quiz', 'store', 'protection']
  const visibleCategories = categoryOrder.filter(c => grouped[c]?.length > 0)
  Object.keys(grouped).forEach(c => {
    if (!visibleCategories.includes(c)) visibleCategories.push(c)
  })

  function showMsg(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 4000)
  }

  function handleChange(key, newValue) {
    setEditedValues(prev => ({ ...prev, [key]: newValue }))
    const setting = settings.find(s => s.key === key)
    const serverValue = setting?.effective_value?.v ?? ''
    setDirtyKeys(prev => {
      const next = new Set(prev)
      if (newValue === serverValue) next.delete(key)
      else next.add(key)
      return next
    })
  }

  async function handleSave() {
    if (dirtyKeys.size === 0) return
    setSaving(true)
    const keys = Array.from(dirtyKeys)
    const results = await Promise.allSettled(
      keys.map(key =>
        apiFetch(`/api/admin/competitions/${selectedId}/settings/${key}`, {
          method: 'PATCH',
          body: JSON.stringify({ value: { v: editedValues[key] } }),
        })
      )
    )
    const failed = results.filter(r => r.status === 'rejected')
    if (failed.length === 0) {
      showMsg('تم حفظ الإعدادات المخصصة بنجاح')
    } else {
      showMsg(`تم حفظ ${keys.length - failed.length}، فشل ${failed.length}`)
    }
    setSaving(false)
    loadSettings()
  }

  async function handleResetOverride(key) {
    try {
      await apiFetch(`/api/admin/competitions/${selectedId}/settings/${key}`, {
        method: 'DELETE',
      })
      showMsg('تم إلغاء التخصيص — يستخدم القيمة العامة الآن')
      loadSettings()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <iconify-icon icon="lucide:settings" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
        <p className="font-bold text-gray-500 dark:text-gray-400">اختر منافسة من القائمة الجانبية لعرض إعداداتها</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
      </div>
    )
  }

  const hasDirty = dirtyKeys.size > 0

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">إعدادات المنافسة</h1>
          <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
            {selected.name} — تجاوز القيم الافتراضية لهذه المنافسة
          </p>
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
            حفظ التخصيصات
            <span className="bg-white/20 px-1.5 py-0.5 rounded-md text-xs">{dirtyKeys.size}</span>
          </button>
        )}
      </div>

      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${
          actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'
        }`}>{actionMsg}</div>
      )}

      {/* Info banner */}
      <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-2xl px-4 py-3 text-sm">
        <div className="flex items-start gap-2">
          <iconify-icon icon="lucide:info" class="text-blue-500 mt-0.5 flex-shrink-0"></iconify-icon>
          <div className="font-bold text-blue-700 dark:text-blue-300">
            الإعدادات المعروضة هي القيم الفعلية لهذه المنافسة. يمكنك تجاوز أي قيمة عامة بقيمة مخصصة، أو إلغاء التخصيص للعودة للقيمة الافتراضية.
          </div>
        </div>
      </div>

      {/* Settings by category */}
      {settings.length > 0 ? (
        visibleCategories.map(category => {
          const catSettings = grouped[category]
          if (!catSettings || catSettings.length === 0) return null
          return (
            <div key={category} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
              <h2 className="font-heading font-black text-base text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <iconify-icon icon={CATEGORY_ICONS[category] || 'lucide:settings-2'} class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                {CATEGORY_LABELS[category] || category}
              </h2>
              <div className="space-y-3">
                {catSettings.map(setting => {
                  const isDirty = dirtyKeys.has(setting.key)
                  const src = SOURCE_LABELS[setting.source] || SOURCE_LABELS.default
                  const isOverridden = setting.source === 'competition'
                  return (
                    <div
                      key={setting.key}
                      className={`p-3 rounded-xl smooth-transition ${
                        isDirty ? 'bg-brand-teal/5 dark:bg-brand-teal/10 ring-1 ring-brand-teal/20'
                        : isOverridden ? 'bg-brand-teal/[0.03] dark:bg-brand-slate/[0.05]'
                        : 'bg-gray-50 dark:bg-gray-800/40'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <label className="font-bold text-sm text-gray-700 dark:text-gray-300">{setting.description}</label>
                            <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${src.color}`}>{src.text}</span>
                          </div>
                          <span className="text-[11px] text-gray-400 dark:text-gray-500 font-mono">{setting.key}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {isOverridden && !isDirty && (
                            <button
                              onClick={() => handleResetOverride(setting.key)}
                              aria-label={`إلغاء تخصيص ${setting.description}`}
                              className="text-xs font-bold text-gray-400 hover:text-brand-danger px-2 py-1 rounded-lg hover:bg-brand-danger/10 smooth-transition"
                              title="إلغاء التخصيص"
                            >
                              <iconify-icon icon="lucide:rotate-ccw" class="text-sm"></iconify-icon>
                            </button>
                          )}
                          {isDirty && (
                            <button
                              onClick={() => {
                                const sv = setting.effective_value?.v ?? ''
                                setEditedValues(prev => ({ ...prev, [setting.key]: sv }))
                                setDirtyKeys(prev => { const n = new Set(prev); n.delete(setting.key); return n })
                              }}
                              aria-label={`التراجع عن تعديل ${setting.description}`}
                              className="text-gray-400 hover:text-brand-danger smooth-transition"
                              title="تراجع"
                            >
                              <iconify-icon icon="lucide:undo-2" class="text-sm"></iconify-icon>
                            </button>
                          )}
                          <SettingInput
                            dataType={setting.data_type}
                            value={editedValues[setting.key]}
                            onChange={val => handleChange(setting.key, val)}
                          />
                        </div>
                      </div>
                      {/* Value trace: show where each layer comes from */}
                      {(setting.global_value || setting.default_value) && (
                        <div className="flex items-center gap-3 mt-2 text-[10px] font-bold text-gray-400">
                          {setting.default_value && (
                            <span>الافتراضي: <span className="text-gray-500 dark:text-gray-400 font-mono">{JSON.stringify(setting.default_value?.v)}</span></span>
                          )}
                          {setting.global_value && (
                            <span>العام: <span className="text-blue-500 font-mono">{JSON.stringify(setting.global_value?.v)}</span></span>
                          )}
                          {setting.competition_value && (
                            <span>المخصص: <span className="text-brand-teal dark:text-brand-slate font-mono">{JSON.stringify(setting.competition_value?.v)}</span></span>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })
      ) : (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-8 text-center">
          <iconify-icon icon="lucide:settings" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="font-bold text-gray-500 dark:text-gray-400">لا توجد إعدادات قابلة للتعديل</p>
        </div>
      )}
    </div>
  )
}
