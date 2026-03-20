/**
 * AdminPlatformSettingsPage — Platform-level settings management.
 * Shows game info (title, subtitle, season text, announcement) and
 * global setting defaults that apply across all competitions.
 * Separated from competition-scoped settings (AdminSettingsPage).
 */

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

const GAME_INFO_LABELS = {
  title: 'عنوان اللعبة',
  subtitle: 'العنوان الفرعي',
  current_season: 'الموسم الحالي',
  announcement: 'الإعلان',
  status: 'حالة اللعبة',
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

export default function AdminPlatformSettingsPage() {
  // Game info
  const { data: gameInfo, loading: gameInfoLoading, refetch: refetchGameInfo } = useAdminData('/api/admin/settings/game-info')
  const [gameInfoEdits, setGameInfoEdits] = useState({})
  const [gameInfoDirty, setGameInfoDirty] = useState(false)
  const [savingGameInfo, setSavingGameInfo] = useState(false)

  // Global settings
  const { data: settingsRaw, loading: settingsLoading, refetch: refetchSettings } = useAdminData('/api/admin/settings')
  const [editedValues, setEditedValues] = useState({})
  const [dirtyKeys, setDirtyKeys] = useState(new Set())
  const [savingSettings, setSavingSettings] = useState(false)

  const [actionMsg, setActionMsg] = useState(null)

  // Initialize game info edits
  useEffect(() => {
    if (gameInfo) {
      setGameInfoEdits({ ...gameInfo })
      setGameInfoDirty(false)
    }
  }, [gameInfo])

  // Initialize settings edits
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

  const categoryOrder = ['attack', 'score', 'quiz', 'store', 'protection']
  const visibleCategories = categoryOrder.filter(c => grouped[c]?.length > 0)
  Object.keys(grouped).forEach(c => {
    if (!visibleCategories.includes(c)) visibleCategories.push(c)
  })

  function showMsg(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 4000)
  }

  function handleGameInfoChange(key, val) {
    setGameInfoEdits(prev => ({ ...prev, [key]: val }))
    setGameInfoDirty(true)
  }

  async function handleSaveGameInfo() {
    setSavingGameInfo(true)
    try {
      await apiFetch('/api/admin/settings/game-info', {
        method: 'PATCH',
        body: JSON.stringify(gameInfoEdits),
      })
      showMsg('تم حفظ معلومات اللعبة')
      setGameInfoDirty(false)
      refetchGameInfo()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
    setSavingGameInfo(false)
  }

  function handleSettingChange(key, newValue) {
    setEditedValues(prev => ({ ...prev, [key]: newValue }))
    const serverSetting = settingsRaw.find(s => s.key === key)
    const serverValue = serverSetting?.current_value?.v ?? serverSetting?.default_value?.v ?? ''
    setDirtyKeys(prev => {
      const next = new Set(prev)
      if (newValue === serverValue) next.delete(key)
      else next.add(key)
      return next
    })
  }

  async function handleSaveSettings() {
    if (dirtyKeys.size === 0) return
    setSavingSettings(true)
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
      showMsg('تم حفظ جميع الإعدادات بنجاح')
      setDirtyKeys(new Set())
      refetchSettings()
    } else {
      showMsg(`تم حفظ ${keys.length - failed.length}، فشل ${failed.length}`)
      refetchSettings()
    }
    setSavingSettings(false)
  }

  if (settingsLoading || gameInfoLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
      </div>
    )
  }

  const hasDirtySettings = dirtyKeys.size > 0

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">إعدادات المنصة</h1>
        <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
          معلومات اللعبة والإعدادات العامة الافتراضية لجميع المنافسات
        </p>
      </div>

      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${
          actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'
        }`}>{actionMsg}</div>
      )}

      {/* ══ Game Info ══ */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
            <iconify-icon icon="lucide:gamepad-2" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            معلومات اللعبة
          </h2>
          {gameInfoDirty && (
            <button
              onClick={handleSaveGameInfo}
              disabled={savingGameInfo}
              className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal-hover text-white px-4 py-2 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50"
            >
              {savingGameInfo ? (
                <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
              ) : (
                <iconify-icon icon="lucide:save"></iconify-icon>
              )}
              حفظ
            </button>
          )}
        </div>
        <div className="space-y-3">
          {['title', 'subtitle', 'current_season', 'announcement', 'status'].map(key => (
            <div key={key} className="flex items-center justify-between gap-4 p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
              <label className="font-bold text-sm text-gray-700 dark:text-gray-300 min-w-[120px]">
                {GAME_INFO_LABELS[key] || key}
              </label>
              <input
                type="text"
                value={gameInfoEdits[key] ?? ''}
                onChange={e => handleGameInfoChange(key, e.target.value)}
                className="flex-1 max-w-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm font-bold text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
              />
            </div>
          ))}
        </div>
      </div>

      {/* ══ Global Setting Defaults ══ */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
            <iconify-icon icon="lucide:sliders-horizontal" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            القيم الافتراضية للإعدادات
          </h2>
          <p className="text-xs font-bold text-gray-400 dark:text-gray-500 mt-1">
            القيم العامة التي تطبق على جميع المنافسات — يمكن تجاوزها لكل منافسة من إعدادات المنافسة
          </p>
        </div>
        {hasDirtySettings && (
          <button
            onClick={handleSaveSettings}
            disabled={savingSettings}
            className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal-hover text-white px-5 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-50"
          >
            {savingSettings ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon="lucide:save"></iconify-icon>
            )}
            حفظ الإعدادات
            <span className="bg-white/20 px-1.5 py-0.5 rounded-md text-xs">{dirtyKeys.size}</span>
          </button>
        )}
      </div>

      {settingsRaw && settingsRaw.length > 0 ? (
        visibleCategories.map(category => {
          const settings = grouped[category]
          if (!settings || settings.length === 0) return null
          return (
            <div key={category} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
              <h3 className="font-heading font-black text-base text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <iconify-icon icon={CATEGORY_ICONS[category] || 'lucide:settings-2'} class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                {CATEGORY_LABELS[category] || category}
              </h3>
              <div className="space-y-3">
                {settings.map(setting => {
                  const isDirty = dirtyKeys.has(setting.key)
                  return (
                    <div
                      key={setting.key}
                      className={`flex items-center justify-between gap-4 p-3 rounded-xl smooth-transition ${
                        isDirty ? 'bg-brand-teal/5 dark:bg-brand-teal/10 ring-1 ring-brand-teal/20' : 'bg-gray-50 dark:bg-gray-800/40'
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <label className="block font-bold text-sm text-gray-700 dark:text-gray-300">{setting.description}</label>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-gray-400 dark:text-gray-500 font-mono">{setting.key}</span>
                          {setting.is_per_competition && (
                            <span className="text-[10px] bg-amber-100 dark:bg-amber-900/30 text-amber-600 px-1.5 py-0.5 rounded font-black">
                              قابل للتجاوز لكل منافسة
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {isDirty && (
                          <button
                            type="button"
                            onClick={() => {
                              const sv = setting.current_value?.v ?? setting.default_value?.v ?? ''
                              setEditedValues(prev => ({ ...prev, [setting.key]: sv }))
                              setDirtyKeys(prev => { const n = new Set(prev); n.delete(setting.key); return n })
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
                          onChange={val => handleSettingChange(setting.key, val)}
                        />
                      </div>
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
          <p className="text-gray-500 dark:text-gray-400 font-bold">لا توجد إعدادات قابلة للتعديل بعد</p>
        </div>
      )}
    </div>
  )
}
