/**
 * AdminSeasonsPage — Season/cycle management with full lifecycle operations.
 * Seasons belong to the selected competition.
 * Cycles are nested under their season.
 * Supports: create, edit, status transitions, start/end/advance cycles, broadcast.
 */

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'
import { formatDate } from '../../lib/dates'

const STATUS_COLORS = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  active: 'bg-brand-success/10 text-brand-success',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400',
  completed: 'bg-purple-100 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400',
  archived: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
}

const STATUS_LABELS = {
  draft: 'مسودة', active: 'نشط',
  paused: 'متوقف', completed: 'مكتمل', archived: 'مؤرشف',
}

function StatusBadge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-lg text-[10px] font-black ${STATUS_COLORS[status] || STATUS_COLORS.draft}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function ResultBanner({ result, onDismiss }) {
  if (!result) return null
  const details = result.details || []
  return (
    <div className="bg-brand-success/10 border border-brand-success/20 rounded-xl p-4 flex items-start gap-3">
      <iconify-icon icon="lucide:check-circle" class="text-xl text-brand-success mt-0.5"></iconify-icon>
      <div className="flex-1">
        <div className="font-bold text-brand-success mb-1">{result.title}</div>
        <div className="text-sm font-bold text-gray-600 dark:text-gray-400 space-y-0.5">
          {details.map((d, i) => <div key={i}>{d}</div>)}
        </div>
      </div>
      <button onClick={onDismiss} className="mr-auto text-gray-400 hover:text-gray-600">
        <iconify-icon icon="lucide:x" class="text-lg"></iconify-icon>
      </button>
    </div>
  )
}

function formatResultDetails(data) {
  const details = []
  if (data.protections_cleared != null) details.push(`الحمايات المُلغاة: ${data.protections_cleared}`)
  if (data.bankruptcies_cleared != null) details.push(`حالات الإفلاس المُلغاة: ${data.bankruptcies_cleared}`)
  if (data.members_notified != null) details.push(`الأعضاء المُشعَرون: ${data.members_notified}`)
  return details
}

export default function AdminSeasonsPage() {
  const { selected, selectedId } = useAdminCompetition()
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showSeasonForm, setShowSeasonForm] = useState(false)
  const [showCycleForm, setShowCycleForm] = useState(null)
  const [showBroadcastForm, setShowBroadcastForm] = useState(false)
  const [newSeasonName, setNewSeasonName] = useState('')
  const [newCycleLabel, setNewCycleLabel] = useState('')
  const [broadcastTitle, setBroadcastTitle] = useState('')
  const [broadcastMessage, setBroadcastMessage] = useState('')
  const [operatingCycle, setOperatingCycle] = useState(null)
  const [operatingSeason, setOperatingSeason] = useState(null)
  const [resultBanner, setResultBanner] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showArchivedSeasons, setShowArchivedSeasons] = useState(false)
  const [showArchivedCycles, setShowArchivedCycles] = useState({})

  // ── War/Peace (attack_enabled) ────────────────────────────────────
  const [attackEnabled, setAttackEnabled] = useState(null)
  const [attackToggling, setAttackToggling] = useState(false)

  // ── Bulk actions ──────────────────────────────────────────────────
  const [bulkModal, setBulkModal] = useState(null)   // 'deactivate' | 'give' | 'set' | 'reset' | null
  const [bulkAmount, setBulkAmount] = useState('')
  const [bulkReason, setBulkReason] = useState('')
  const [bulkRunning, setBulkRunning] = useState(false)

  const loadAttackSetting = useCallback(() => {
    if (!selectedId) return
    apiFetch(`/api/admin/competitions/${selectedId}/settings`)
      .then(json => {
        const setting = (json.data || []).find(s => s.key === 'attack_enabled')
        if (setting) setAttackEnabled(setting.effective_value?.v ?? false)
      })
      .catch(() => {})
  }, [selectedId])

  useEffect(() => { loadAttackSetting() }, [loadAttackSetting])

  async function toggleAttackEnabled() {
    const newValue = !attackEnabled
    setAttackToggling(true)
    try {
      await apiFetch(`/api/admin/competitions/${selectedId}/settings/attack_enabled`, {
        method: 'PATCH',
        body: JSON.stringify({ value: { v: newValue } }),
      })
      setAttackEnabled(newValue)
      setResultBanner({
        title: newValue ? 'تم تفعيل الهجمات — وقت الحرب' : 'تم إيقاف الهجمات — وقت السلام',
        details: [newValue ? 'يمكن للمتسابقين مهاجمة بعضهم الآن' : 'لن يتمكن أي متسابق من تنفيذ هجمات حتى يُعاد التفعيل'],
      })
    } catch { }
    setAttackToggling(false)
  }

  // ── Bulk action handlers ──────────────────────────────────────────

  async function bulkDeactivateAll() {
    setBulkRunning(true)
    try {
      const json = await apiFetch(`/api/admin/competitions/${selectedId}/bulk/deactivate-all`, { method: 'POST' })
      setResultBanner({ title: json.message, details: [`عدد المتأثرين: ${json.data?.deactivated_count || 0}`] })
      setBulkModal(null)
      loadDetail()
    } catch (err) { setResultBanner({ title: 'فشلت العملية', details: [err.message] }) }
    setBulkRunning(false)
  }

  async function bulkGivePoints(e) {
    e.preventDefault()
    if (!bulkAmount) return
    setBulkRunning(true)
    try {
      const json = await apiFetch(`/api/admin/competitions/${selectedId}/bulk/give-points`, {
        method: 'POST',
        body: JSON.stringify({ amount: parseInt(bulkAmount), reason: bulkReason || 'توزيع إداري' }),
      })
      setResultBanner({ title: json.message, details: [`عدد المتأثرين: ${json.data?.affected_count || 0}`] })
      setBulkModal(null)
      setBulkAmount('')
      setBulkReason('')
    } catch (err) { setResultBanner({ title: 'فشلت العملية', details: [err.message] }) }
    setBulkRunning(false)
  }

  async function bulkSetBalance(e) {
    e.preventDefault()
    if (!bulkAmount) return
    setBulkRunning(true)
    try {
      const json = await apiFetch(`/api/admin/competitions/${selectedId}/bulk/set-balance`, {
        method: 'POST',
        body: JSON.stringify({ amount: parseInt(bulkAmount), reason: bulkReason || 'تعيين رصيد إداري' }),
      })
      setResultBanner({ title: json.message, details: [`عدد المتأثرين: ${json.data?.affected_count || 0}`] })
      setBulkModal(null)
      setBulkAmount('')
      setBulkReason('')
    } catch (err) { setResultBanner({ title: 'فشلت العملية', details: [err.message] }) }
    setBulkRunning(false)
  }

  async function bulkResetBankrupt() {
    setBulkRunning(true)
    try {
      const json = await apiFetch(`/api/admin/competitions/${selectedId}/bulk/reset-bankrupt`, { method: 'POST' })
      setResultBanner({ title: json.message, details: [`عدد المتأثرين: ${json.data?.cleared_count || 0}`] })
      setBulkModal(null)
    } catch (err) { setResultBanner({ title: 'فشلت العملية', details: [err.message] }) }
    setBulkRunning(false)
  }

  const loadDetail = useCallback(() => {
    if (!selectedId) return
    setLoading(true)
    apiFetch(`/api/admin/competitions/${selectedId}`)
      .then(json => setDetail(json.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [selectedId])

  useEffect(() => { loadDetail() }, [loadDetail])

  // ── Season CRUD ─────────────────────────────────────────────────────

  async function createSeason(e) {
    e.preventDefault()
    if (!newSeasonName.trim()) return
    setSaving(true)
    try {
      await apiFetch('/api/admin/seasons', {
        method: 'POST',
        body: JSON.stringify({ competition_id: selectedId, name: newSeasonName.trim() }),
      })
      setNewSeasonName('')
      setShowSeasonForm(false)
      loadDetail()
    } catch {}
    setSaving(false)
  }

  async function startSeason(seasonId) {
    setOperatingSeason(seasonId)
    try {
      const json = await apiFetch(`/api/admin/seasons/${seasonId}/start`, { method: 'POST' })
      const data = json.data || {}
      const details = [`الأعضاء المُشعَرون: ${data.members_notified || 0}`]
      if (data.previous_seasons_completed > 0)
        details.unshift(`مواسم سابقة مكتملة: ${data.previous_seasons_completed}`)
      setResultBanner({ title: json.message || 'تم بدء الموسم بنجاح', details })
      loadDetail()
    } catch {}
    setOperatingSeason(null)
  }

  async function endSeason(seasonId) {
    setOperatingSeason(seasonId)
    try {
      const json = await apiFetch(`/api/admin/seasons/${seasonId}/end`, { method: 'POST' })
      const data = json.data || {}
      const details = [`الأعضاء المُشعَرون: ${data.members_notified || 0}`]
      if (data.cycles_ended?.length > 0)
        details.unshift(`دورات أُنهيت تلقائياً: ${data.cycles_ended.length}`)
      setResultBanner({ title: json.message || 'تم إنهاء الموسم بنجاح', details })
      loadDetail()
    } catch {}
    setOperatingSeason(null)
  }

  // ── Cycle CRUD ──────────────────────────────────────────────────────

  async function createCycle(e, seasonId) {
    e.preventDefault()
    if (!newCycleLabel.trim()) return
    setSaving(true)
    try {
      await apiFetch('/api/admin/cycles', {
        method: 'POST',
        body: JSON.stringify({ season_id: seasonId, label: newCycleLabel.trim() }),
      })
      setNewCycleLabel('')
      setShowCycleForm(null)
      loadDetail()
    } catch {}
    setSaving(false)
  }

  // ── Cycle Lifecycle Operations ──────────────────────────────────────

  async function startCycle(cycleId) {
    setOperatingCycle(cycleId)
    try {
      const json = await apiFetch(`/api/admin/cycles/${cycleId}/start`, { method: 'POST' })
      setResultBanner({
        title: json.message || 'تم بدء الدورة بنجاح',
        details: formatResultDetails(json.data || {}),
      })
      loadDetail()
    } catch {}
    setOperatingCycle(null)
  }

  async function pauseCycle(cycleId) {
    setOperatingCycle(cycleId)
    try {
      const json = await apiFetch(`/api/admin/cycles/${cycleId}/pause`, { method: 'POST' })
      setResultBanner({
        title: json.message || 'تم إيقاف الدورة مؤقتاً',
        details: ['يمكنك استئنافها لاحقاً باستخدام زر "بدء الدورة"'],
      })
      loadDetail()
    } catch {}
    setOperatingCycle(null)
  }

  async function endCycle(cycleId) {
    setOperatingCycle(cycleId)
    try {
      const json = await apiFetch(`/api/admin/cycles/${cycleId}/end`, { method: 'POST' })
      const data = json.data || {}
      const details = formatResultDetails(data)
      if (data.auto_started_next_cycle) details.unshift(`بدأت الدورة التالية تلقائياً: ${data.auto_started_next_cycle.label}`)
      setResultBanner({
        title: json.message || 'تم إنهاء الدورة بنجاح',
        details,
      })
      loadDetail()
    } catch {}
    setOperatingCycle(null)
  }

  async function advanceCycle(cycleId) {
    setOperatingCycle(cycleId)
    try {
      const json = await apiFetch(`/api/admin/cycles/${cycleId}/advance`, { method: 'POST' })
      const data = json.data || {}
      setResultBanner({
        title: json.message || 'تم الانتقال للدورة التالية',
        details: [
          `انتهت: ${data.ended?.label || '?'} (${data.ended?.members_notified || 0} مُشعَر)`,
          `بدأت: ${data.started?.label || '?'} (${data.started?.members_notified || 0} مُشعَر)`,
          `الحمايات المُلغاة: ${(data.ended?.protections_cleared || 0) + (data.started?.protections_cleared || 0)}`,
          `حالات الإفلاس المُلغاة: ${(data.ended?.bankruptcies_cleared || 0) + (data.started?.bankruptcies_cleared || 0)}`,
        ],
      })
      loadDetail()
    } catch {}
    setOperatingCycle(null)
  }

  // ── Broadcast ───────────────────────────────────────────────────────

  async function sendBroadcast(e) {
    e.preventDefault()
    if (!broadcastTitle.trim() || !broadcastMessage.trim()) return
    setSaving(true)
    try {
      const json = await apiFetch(`/api/admin/competitions/${selectedId}/broadcast`, {
        method: 'POST',
        body: JSON.stringify({ title: broadcastTitle.trim(), message: broadcastMessage.trim() }),
      })
      setResultBanner({
        title: json.message || 'تم إرسال الإعلان',
        details: [`الأعضاء المُشعَرون: ${json.data?.members_notified || 0}`],
      })
      setBroadcastTitle('')
      setBroadcastMessage('')
      setShowBroadcastForm(false)
    } catch {}
    setSaving(false)
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  function findActiveCycleInSeason(season) {
    return (season.cycles || []).find(c => c.status === 'active')
  }

  function canAdvance(cycle, season) {
    return (cycle.status === 'draft' || cycle.status === 'paused') && findActiveCycleInSeason(season)
  }

  async function archiveSeason(seasonId) {
    if (!confirm('هل أنت متأكد من أرشفة هذا الموسم؟ سيتم إخفاؤه من العرض الافتراضي.')) return
    setOperatingSeason(seasonId)
    try {
      await apiFetch(`/api/admin/seasons/${seasonId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'archived' }),
      })
      setResultBanner({ title: 'تم أرشفة الموسم بنجاح', details: ['يمكنك إظهاره لاحقاً من زر المواسم المؤرشفة'] })
      loadDetail()
    } catch (err) {
      setResultBanner({ title: 'فشلت الأرشفة', details: [err.message] })
    }
    setOperatingSeason(null)
  }

  async function deleteSeason(seasonId, seasonName) {
    if (!confirm(`حذف الموسم "${seasonName}"؟ سيُحذف فقط إذا لم يكن مرتبطاً بسجل لعب تاريخي.`)) return
    setOperatingSeason(seasonId)
    try {
      const json = await apiFetch(`/api/admin/seasons/${seasonId}`, { method: 'DELETE' })
      setResultBanner({ title: json.message || 'تم حذف الموسم', details: ['تمت إزالة الموسم نهائياً من المنافسة'] })
      loadDetail()
    } catch (err) {
      setResultBanner({ title: 'تعذر حذف الموسم', details: [err.message] })
    }
    setOperatingSeason(null)
  }

  async function archiveCycle(cycleId) {
    if (!confirm('أرشفة هذه الدورة؟ ستُخفى من العرض الافتراضي.')) return
    setOperatingCycle(cycleId)
    try {
      await apiFetch(`/api/admin/cycles/${cycleId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'archived' }),
      })
      setResultBanner({ title: 'تمت أرشفة الدورة', details: ['يمكنك إظهارها من زر الدورات المؤرشفة داخل الموسم'] })
      loadDetail()
    } catch (err) {
      setResultBanner({ title: 'فشلت الأرشفة', details: [err.message] })
    }
    setOperatingCycle(null)
  }

  async function deleteCycle(cycleId, cycleLabel) {
    if (!confirm(`حذف الدورة "${cycleLabel}"؟ سيُحذف فقط إذا لم تكن مرتبطة بسجل لعب تاريخي.`)) return
    setOperatingCycle(cycleId)
    try {
      const json = await apiFetch(`/api/admin/cycles/${cycleId}`, { method: 'DELETE' })
      setResultBanner({ title: json.message || 'تم حذف الدورة', details: ['تمت إزالة الدورة نهائياً من الموسم'] })
      loadDetail()
    } catch (err) {
      setResultBanner({ title: 'تعذر حذف الدورة', details: [err.message] })
    }
    setOperatingCycle(null)
  }

  // ── Render ──────────────────────────────────────────────────────────

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <iconify-icon icon="lucide:calendar-range" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
        <p className="font-bold text-gray-500 dark:text-gray-400">اختر منافسة لإدارة مواسمها ودوراتها</p>
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

  const seasons = detail?.seasons || []
  const archivedSeasonsCount = seasons.filter(season => season.status === 'archived').length
  const visibleSeasons = showArchivedSeasons ? seasons : seasons.filter(season => season.status !== 'archived')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">المواسم والدورات</h1>
          <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">
            {selected.name} — الهيكل الزمني والعمليات التشغيلية
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowArchivedSeasons(v => !v)}
            className={`text-xs font-bold px-3 py-2 rounded-xl smooth-transition ${
              showArchivedSeasons
                ? 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
            }`}
          >
            {showArchivedSeasons ? 'إخفاء المواسم المؤرشفة' : `عرض المؤرشفة (${archivedSeasonsCount})`}
          </button>
          <button
            onClick={() => setShowBroadcastForm(v => !v)}
            className="flex items-center gap-2 bg-brand-orange/10 hover:bg-brand-orange/20 text-brand-orange px-4 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition"
          >
            <iconify-icon icon="lucide:megaphone" class="text-lg"></iconify-icon>
            إعلان
          </button>
          <button
            onClick={() => setShowSeasonForm(true)}
            className="flex items-center gap-2 bg-brand-teal hover:bg-brand-teal-hover text-white px-4 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition"
          >
            <iconify-icon icon="lucide:plus" class="text-lg"></iconify-icon>
            موسم جديد
          </button>
        </div>
      </div>

      {/* Result banner */}
      <ResultBanner result={resultBanner} onDismiss={() => setResultBanner(null)} />

      {/* ══ War/Peace Control ══ */}
      {attackEnabled !== null && (
        <div className={`border rounded-2xl p-5 smooth-transition ${attackEnabled ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800' : 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800'}`}>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${attackEnabled ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30'}`}>
                <iconify-icon icon={attackEnabled ? 'lucide:swords' : 'lucide:shield-check'} class={`text-2xl ${attackEnabled ? 'text-red-500' : 'text-blue-500'}`}></iconify-icon>
              </div>
              <div>
                <div className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
                  {attackEnabled ? 'وقت الحرب' : 'وقت السلام'}
                  <span className={`w-2 h-2 rounded-full ${attackEnabled ? 'bg-red-500 animate-pulse' : 'bg-blue-500'}`}></span>
                </div>
                <p className="text-sm font-bold text-gray-500 dark:text-gray-400">
                  {attackEnabled ? 'الهجمات مفعّلة — يمكن للمتسابقين مهاجمة بعضهم' : 'الهجمات معطّلة — لا يمكن لأي متسابق تنفيذ هجوم'}
                </p>
              </div>
            </div>
            <button
              onClick={toggleAttackEnabled}
              disabled={attackToggling}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-60 ${
                attackEnabled
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-red-500 hover:bg-red-600 text-white'
              }`}
            >
              <iconify-icon icon={attackToggling ? 'lucide:loader-2' : attackEnabled ? 'lucide:shield-check' : 'lucide:swords'} class={`text-lg ${attackToggling ? 'animate-spin' : ''}`}></iconify-icon>
              {attackToggling ? 'جارٍ التبديل...' : attackEnabled ? 'إيقاف الهجمات (سلام)' : 'تفعيل الهجمات (حرب)'}
            </button>
          </div>
        </div>
      )}

      {/* ══ Bulk Operations ══ */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/20 rounded-xl flex items-center justify-center">
            <iconify-icon icon="lucide:zap" class="text-xl text-amber-600 dark:text-amber-400"></iconify-icon>
          </div>
          <div>
            <div className="font-heading font-black text-lg text-gray-900 dark:text-white">عمليات جماعية</div>
            <p className="text-xs font-bold text-gray-400">إجراءات تطبّق على جميع أعضاء المنافسة</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <button onClick={() => setBulkModal('deactivate')} className="flex flex-col items-center gap-2 p-4 bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl smooth-transition group">
            <iconify-icon icon="lucide:user-x" class="text-2xl text-red-500 group-hover:scale-110 smooth-transition"></iconify-icon>
            <span className="text-xs font-black text-red-600 dark:text-red-400">تعطيل الجميع</span>
          </button>
          <button onClick={() => { setBulkModal('give'); setBulkAmount(''); setBulkReason('') }} className="flex flex-col items-center gap-2 p-4 bg-brand-success/5 hover:bg-brand-success/10 border border-brand-success/20 rounded-xl smooth-transition group">
            <iconify-icon icon="lucide:coins" class="text-2xl text-brand-success group-hover:scale-110 smooth-transition"></iconify-icon>
            <span className="text-xs font-black text-brand-success">منح نقاط للجميع</span>
          </button>
          <button onClick={() => { setBulkModal('set'); setBulkAmount(''); setBulkReason('') }} className="flex flex-col items-center gap-2 p-4 bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl smooth-transition group">
            <iconify-icon icon="lucide:equal" class="text-2xl text-blue-500 group-hover:scale-110 smooth-transition"></iconify-icon>
            <span className="text-xs font-black text-blue-600 dark:text-blue-400">تعيين رصيد موحد</span>
          </button>
          <button onClick={() => setBulkModal('reset')} className="flex flex-col items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/10 hover:bg-amber-100 dark:hover:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl smooth-transition group">
            <iconify-icon icon="lucide:heart-pulse" class="text-2xl text-amber-500 group-hover:scale-110 smooth-transition"></iconify-icon>
            <span className="text-xs font-black text-amber-600 dark:text-amber-400">إعادة تعيين المفلسين</span>
          </button>
        </div>
      </div>

      {/* ══ Bulk Modals ══ */}

      {/* Deactivate All Confirm */}
      {bulkModal === 'deactivate' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setBulkModal(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-sm text-center" onClick={e => e.stopPropagation()}>
            <iconify-icon icon="lucide:alert-triangle" class="text-4xl text-red-500 mb-3"></iconify-icon>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-2">تعطيل جميع الأعضاء</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">سيتم تعليق جميع الأعضاء النشطين في المنافسة. هل أنت متأكد؟</p>
            <div className="flex gap-3">
              <button onClick={bulkDeactivateAll} disabled={bulkRunning} className="flex-1 bg-red-500 hover:bg-red-600 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60 flex items-center justify-center gap-2">
                {bulkRunning && <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>}
                {bulkRunning ? 'جارٍ التنفيذ...' : 'تأكيد التعطيل'}
              </button>
              <button onClick={() => setBulkModal(null)} className="flex-1 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Give Points Modal */}
      {bulkModal === 'give' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setBulkModal(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <iconify-icon icon="lucide:coins" class="text-brand-success"></iconify-icon>
              منح نقاط لجميع الأعضاء
            </h3>
            <form onSubmit={bulkGivePoints} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">المبلغ (موجب = إضافة، سالب = خصم)</label>
                <input type="number" value={bulkAmount} onChange={e => setBulkAmount(e.target.value)} required placeholder="500 أو -200"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input type="text" value={bulkReason} onChange={e => setBulkReason(e.target.value)} placeholder="توزيع إداري"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={bulkRunning} className="flex-1 bg-brand-success hover:bg-brand-success/90 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60 flex items-center justify-center gap-2">
                  {bulkRunning && <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>}
                  {bulkRunning ? 'جارٍ التنفيذ...' : 'تأكيد المنح'}
                </button>
                <button type="button" onClick={() => setBulkModal(null)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Set Balance Modal */}
      {bulkModal === 'set' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setBulkModal(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <iconify-icon icon="lucide:equal" class="text-blue-500"></iconify-icon>
              تعيين رصيد موحد لجميع الأعضاء
            </h3>
            <form onSubmit={bulkSetBalance} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الرصيد المطلوب</label>
                <input type="number" value={bulkAmount} onChange={e => setBulkAmount(e.target.value)} required placeholder="1000" min="0"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input type="text" value={bulkReason} onChange={e => setBulkReason(e.target.value)} placeholder="تعيين رصيد موحد"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={bulkRunning} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60 flex items-center justify-center gap-2">
                  {bulkRunning && <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>}
                  {bulkRunning ? 'جارٍ التنفيذ...' : 'تأكيد التعيين'}
                </button>
                <button type="button" onClick={() => setBulkModal(null)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Bankrupt Confirm */}
      {bulkModal === 'reset' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setBulkModal(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-sm text-center" onClick={e => e.stopPropagation()}>
            <iconify-icon icon="lucide:heart-pulse" class="text-4xl text-amber-500 mb-3"></iconify-icon>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-2">إعادة تعيين المفلسين</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">سيتم إزالة حالة الإفلاس عن جميع اللاعبين المفلسين. هل أنت متأكد؟</p>
            <div className="flex gap-3">
              <button onClick={bulkResetBankrupt} disabled={bulkRunning} className="flex-1 bg-amber-500 hover:bg-amber-600 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60 flex items-center justify-center gap-2">
                {bulkRunning && <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>}
                {bulkRunning ? 'جارٍ التنفيذ...' : 'تأكيد إعادة التعيين'}
              </button>
              <button onClick={() => setBulkModal(null)} className="flex-1 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Broadcast form */}
      {showBroadcastForm && (
        <div className="bg-white dark:bg-brand-card-dark border border-brand-orange/20 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <iconify-icon icon="lucide:megaphone" class="text-xl text-brand-orange"></iconify-icon>
            <span className="font-heading font-black text-gray-900 dark:text-white">إعلان لجميع الأعضاء</span>
          </div>
          <form onSubmit={sendBroadcast} className="space-y-3">
            <input
              type="text"
              value={broadcastTitle}
              onChange={e => setBroadcastTitle(e.target.value)}
              placeholder="عنوان الإعلان"
              required
              className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-2.5 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-orange/10 focus:border-brand-orange dark:text-white"
            />
            <textarea
              value={broadcastMessage}
              onChange={e => setBroadcastMessage(e.target.value)}
              placeholder="نص الإعلان..."
              required
              rows={3}
              className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-2.5 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-orange/10 focus:border-brand-orange dark:text-white resize-none"
            />
            <div className="flex items-center gap-2 justify-end">
              <button type="button" onClick={() => setShowBroadcastForm(false)} className="text-gray-400 hover:text-gray-600 px-3 py-2 text-sm font-bold">
                إلغاء
              </button>
              <button type="submit" disabled={saving} className="bg-brand-orange hover:bg-brand-orange/90 text-white px-5 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-60 flex items-center gap-2">
                <iconify-icon icon="lucide:send" class="text-sm"></iconify-icon>
                إرسال
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Create season form */}
      {showSeasonForm && (
        <div className="bg-white dark:bg-brand-card-dark border border-brand-teal/20 dark:border-brand-slate/20 rounded-2xl p-5">
          <form onSubmit={createSeason} className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">اسم الموسم</label>
              <input
                type="text"
                value={newSeasonName}
                onChange={e => setNewSeasonName(e.target.value)}
                placeholder="الموسم الثاني"
                required
                className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-2.5 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
              />
            </div>
            <button type="submit" disabled={saving} className="bg-brand-teal hover:bg-brand-teal-hover text-white px-5 py-2.5 rounded-xl font-heading font-black text-sm smooth-transition disabled:opacity-60">
              إنشاء
            </button>
            <button type="button" onClick={() => setShowSeasonForm(false)} className="text-gray-400 hover:text-gray-600 px-3 py-2.5">
              إلغاء
            </button>
          </form>
        </div>
      )}

      {/* Seasons list */}
      {visibleSeasons.length === 0 ? (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-10 text-center">
          <iconify-icon icon="lucide:calendar-plus" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="font-bold text-gray-500 dark:text-gray-400">
            {archivedSeasonsCount > 0 ? 'كل المواسم الحالية مؤرشفة' : 'لا توجد مواسم بعد. أنشئ موسماً جديداً للبدء.'}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {visibleSeasons.map(season => {
            const activeCycle = findActiveCycleInSeason(season)
            const archivedCyclesCount = (season.cycles || []).filter(cycle => cycle.status === 'archived').length
            const seasonShowsArchivedCycles = !!showArchivedCycles[season.id]
            const visibleCycles = seasonShowsArchivedCycles
              ? (season.cycles || [])
              : (season.cycles || []).filter(cycle => cycle.status !== 'archived')
            return (
              <div key={season.id} className={`bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden ${season.status === 'archived' ? 'opacity-60' : ''}`}>
                {/* Season header */}
                <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-xl flex items-center justify-center">
                      <iconify-icon icon="lucide:calendar-range" class="text-xl text-brand-teal dark:text-brand-slate"></iconify-icon>
                    </div>
                    <div>
                      <div className="font-heading font-black text-lg text-gray-900 dark:text-white">{season.name}</div>
                      <div className="text-xs font-bold text-gray-400 dark:text-gray-500 flex items-center gap-2 flex-wrap">
                        <StatusBadge status={season.status} />
                        {season.starts_at && <span>بدأ: {formatDate(season.starts_at)}</span>}
                        <span>{season.cycles?.length || 0} دورة</span>
                        {activeCycle && (
                          <span className="text-brand-success flex items-center gap-1">
                            <iconify-icon icon="lucide:radio" class="text-xs animate-pulse"></iconify-icon>
                            {activeCycle.label}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {(season.status === 'draft' || season.status === 'paused') && (
                      <button
                        onClick={() => startSeason(season.id)}
                        disabled={operatingSeason === season.id}
                        className="text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                      >
                        <iconify-icon icon={operatingSeason === season.id ? 'lucide:loader-2' : 'lucide:play'} class={`text-xs ${operatingSeason === season.id ? 'animate-spin' : ''}`}></iconify-icon>
                        {operatingSeason === season.id ? 'جارٍ البدء...' : 'بدء الموسم'}
                      </button>
                    )}
                    {season.status === 'active' && (
                      <button
                        onClick={() => endSeason(season.id)}
                        disabled={operatingSeason === season.id}
                        className="text-xs font-black bg-brand-orange/10 text-brand-orange hover:bg-brand-orange/20 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                      >
                        <iconify-icon icon={operatingSeason === season.id ? 'lucide:loader-2' : 'lucide:square'} class={`text-xs ${operatingSeason === season.id ? 'animate-spin' : ''}`}></iconify-icon>
                        {operatingSeason === season.id ? 'جارٍ الإنهاء...' : 'إنهاء الموسم'}
                      </button>
                    )}
                    {(season.status === 'completed' || season.status === 'paused') && (
                      <button
                        onClick={() => archiveSeason(season.id)}
                        disabled={operatingSeason === season.id}
                        className="text-xs font-bold text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1"
                      >
                        <iconify-icon icon="lucide:archive" class="text-xs"></iconify-icon>
                        أرشفة
                      </button>
                    )}
                    {season.status !== 'active' && (
                      <button
                        onClick={() => deleteSeason(season.id, season.name)}
                        disabled={operatingSeason === season.id}
                        className="text-xs font-bold text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                      >
                        <iconify-icon icon="lucide:trash-2" class="text-xs"></iconify-icon>
                        حذف
                      </button>
                    )}
                    <button
                      onClick={() => setShowArchivedCycles(prev => ({ ...prev, [season.id]: !prev[season.id] }))}
                      className={`text-xs font-bold px-3 py-1.5 rounded-lg smooth-transition ${
                        seasonShowsArchivedCycles
                          ? 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
                      }`}
                    >
                      {seasonShowsArchivedCycles ? 'إخفاء الدورات المؤرشفة' : `عرض المؤرشفة (${archivedCyclesCount})`}
                    </button>
                    {season.status !== 'completed' && season.status !== 'archived' && (
                      <button
                        onClick={() => { setShowCycleForm(season.id); setNewCycleLabel('') }}
                        className="text-xs font-bold text-brand-teal dark:text-brand-slate hover:bg-brand-teal/10 dark:hover:bg-brand-slate/20 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1"
                      >
                        <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
                        دورة
                      </button>
                    )}
                  </div>
                </div>

                {/* Create cycle form (inline) */}
                {showCycleForm === season.id && (
                  <div className="px-5 py-3 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
                    <form onSubmit={e => createCycle(e, season.id)} className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                      <input
                        type="text"
                        value={newCycleLabel}
                        onChange={e => setNewCycleLabel(e.target.value)}
                        placeholder="اسم الدورة (مثل: الأسبوع الثاني)"
                        required
                        className="flex-1 bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-2 px-3 rounded-lg font-bold text-sm focus:outline-none focus:border-brand-teal dark:text-white"
                      />
                      <button type="submit" disabled={saving} className="bg-brand-teal text-white px-4 py-2 rounded-lg font-bold text-sm disabled:opacity-60">إنشاء</button>
                      <button type="button" onClick={() => setShowCycleForm(null)} className="text-gray-400 hover:text-gray-600 text-sm font-bold">إلغاء</button>
                    </form>
                  </div>
                )}

                {/* Cycles list */}
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {visibleCycles.length === 0 ? (
                    <div className="px-5 py-6 text-center text-sm font-bold text-gray-400">
                      {archivedCyclesCount > 0 ? 'كل الدورات الحالية مؤرشفة' : 'لا توجد دورات في هذا الموسم'}
                    </div>
                  ) : (
                    visibleCycles.map(cycle => {
                      const isOperating = operatingCycle === cycle.id
                      const isActive = cycle.status === 'active'
                      const isDraft = cycle.status === 'draft'
                      const isPaused = cycle.status === 'paused'
                      const canStart = isDraft || isPaused
                      const showAdvance = canStart && !!activeCycle && activeCycle.id !== cycle.id

                      return (
                        <div key={cycle.id} className={`px-5 py-3 flex items-center justify-between flex-wrap gap-2 smooth-transition ${isActive ? 'bg-brand-success/5 dark:bg-brand-success/5' : 'hover:bg-gray-50 dark:hover:bg-gray-800/30'}`}>
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? 'bg-brand-success/10' : 'bg-gray-100 dark:bg-gray-800'}`}>
                              <iconify-icon icon={isActive ? 'lucide:radio' : 'lucide:repeat'} class={`text-sm ${isActive ? 'text-brand-success animate-pulse' : 'text-gray-500 dark:text-gray-400'}`}></iconify-icon>
                            </div>
                            <div>
                              <div className="font-bold text-gray-900 dark:text-white text-sm flex items-center gap-2">
                                {cycle.label}
                                {isActive && <span className="text-[10px] font-black text-brand-success">● نشطة الآن</span>}
                              </div>
                              <div className="text-xs font-bold text-gray-400 flex items-center gap-2 flex-wrap">
                                <StatusBadge status={cycle.status} />
                                {cycle.starts_at && <span>بدأ: {formatDate(cycle.starts_at)}</span>}
                                {cycle.ends_at && <span>انتهى: {formatDate(cycle.ends_at)}</span>}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {/* Start: for draft/paused cycles when no active cycle exists */}
                            {canStart && !activeCycle && (
                              <button
                                onClick={() => startCycle(cycle.id)}
                                disabled={isOperating}
                                className="text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                              >
                                <iconify-icon icon={isOperating ? 'lucide:loader-2' : 'lucide:play'} class={`text-xs ${isOperating ? 'animate-spin' : ''}`}></iconify-icon>
                                {isOperating ? 'جارٍ البدء...' : 'بدء الدورة'}
                              </button>
                            )}

                            {/* Advance: for draft/paused cycles when another cycle is active */}
                            {showAdvance && (
                              <button
                                onClick={() => advanceCycle(cycle.id)}
                                disabled={isOperating}
                                className="text-xs font-black bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-900/30 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                              >
                                <iconify-icon icon={isOperating ? 'lucide:loader-2' : 'lucide:skip-forward'} class={`text-xs ${isOperating ? 'animate-spin' : ''}`}></iconify-icon>
                                {isOperating ? 'جارٍ الانتقال...' : 'انتقال لهذه الدورة'}
                              </button>
                            )}

                            {/* Pause / End: for active cycles */}
                            {isActive && (
                              <>
                                <button
                                  onClick={() => pauseCycle(cycle.id)}
                                  disabled={isOperating}
                                  className="text-xs font-black bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400 hover:bg-yellow-200 dark:hover:bg-yellow-900/30 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                                >
                                  <iconify-icon icon={isOperating ? 'lucide:loader-2' : 'lucide:pause'} class={`text-xs ${isOperating ? 'animate-spin' : ''}`}></iconify-icon>
                                  إيقاف مؤقت
                                </button>
                                <button
                                  onClick={() => endCycle(cycle.id)}
                                  disabled={isOperating}
                                  className="text-xs font-black bg-brand-orange/10 text-brand-orange hover:bg-brand-orange/20 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                                >
                                  <iconify-icon icon={isOperating ? 'lucide:loader-2' : 'lucide:square'} class={`text-xs ${isOperating ? 'animate-spin' : ''}`}></iconify-icon>
                                  {isOperating ? 'جارٍ الإنهاء...' : 'إنهاء الدورة'}
                                </button>
                              </>
                            )}

                            {cycle.status === 'completed' && (
                              <span className="text-[10px] font-black text-gray-400 px-2 py-1">مكتملة</span>
                            )}
                            {!isActive && cycle.status !== 'archived' && (
                              <button
                                onClick={() => archiveCycle(cycle.id)}
                                disabled={isOperating}
                                className="text-xs font-bold text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                              >
                                <iconify-icon icon="lucide:archive" class="text-xs"></iconify-icon>
                                أرشفة
                              </button>
                            )}
                            {!isActive && (
                              <button
                                onClick={() => deleteCycle(cycle.id, cycle.label)}
                                disabled={isOperating}
                                className="text-xs font-bold text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 px-3 py-1.5 rounded-lg smooth-transition flex items-center gap-1 disabled:opacity-60"
                              >
                                <iconify-icon icon="lucide:trash-2" class="text-xs"></iconify-icon>
                                حذف
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
