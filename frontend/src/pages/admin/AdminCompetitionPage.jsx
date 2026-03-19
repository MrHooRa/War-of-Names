import { useState } from 'react'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

function StatusBadge({ status }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success',
    draft: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    paused: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
    completed: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
    registration_open: 'bg-brand-teal/10 text-brand-teal',
    registration_closed: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    archived: 'bg-gray-100 dark:bg-gray-800 text-gray-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>
      {status}
    </span>
  )
}

function CreateModal({ show, onClose, title, onSubmit, submitting, children }) {
  if (!show) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6 w-full max-w-md space-y-4">
        <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">{title}</h2>
        {children}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={submitting}
            className="px-4 py-2 rounded-xl text-sm font-heading font-black text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
          >
            إلغاء
          </button>
          <button
            onClick={onSubmit}
            disabled={submitting}
            className="px-5 py-2 bg-brand-teal hover:bg-brand-teal-hover text-white rounded-xl text-sm font-heading font-black smooth-transition disabled:opacity-50"
          >
            {submitting ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin text-base"></iconify-icon>
            ) : 'إنشاء'}
          </button>
        </div>
      </div>
    </div>
  )
}

function FormInput({ label, value, onChange, placeholder, type = 'text', required = false }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-bold text-gray-700 dark:text-gray-300">
        {label} {required && <span className="text-brand-danger">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-teal/30 focus:border-brand-teal smooth-transition"
      />
    </div>
  )
}

function FormSelect({ label, value, onChange, options }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-bold text-gray-700 dark:text-gray-300">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-teal/30 focus:border-brand-teal smooth-transition"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}

export default function AdminCompetitionPage() {
  const { data: competitions, loading, error, refetch } = useAdminData('/api/admin/competitions')
  const [selectedId, setSelectedId] = useState(null)
  const { data: detail, loading: detailLoading, refetch: refetchDetail } = useAdminData(
    selectedId ? `/api/admin/competitions/${selectedId}` : null
  )
  const [actionMsg, setActionMsg] = useState(null)

  // Modal states
  const [showCreateComp, setShowCreateComp] = useState(false)
  const [showCreateSeason, setShowCreateSeason] = useState(false)
  const [showCreateCycle, setShowCreateCycle] = useState(false)
  const [showCreateInvite, setShowCreateInvite] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Create Competition form
  const [compName, setCompName] = useState('')
  const [compDesc, setCompDesc] = useState('')
  const [compVisibility, setCompVisibility] = useState('private')

  // Create Season form
  const [seasonName, setSeasonName] = useState('')

  // Create Cycle form
  const [cycleLabel, setCycleLabel] = useState('')
  const [cycleSeasonId, setCycleSeasonId] = useState(null)

  // Create Invite form
  const [inviteCode, setInviteCode] = useState('')
  const [inviteMaxUses, setInviteMaxUses] = useState('')

  // Edit Competition modal
  const [showEditComp, setShowEditComp] = useState(false)
  const [editCompName, setEditCompName] = useState('')
  const [editCompDesc, setEditCompDesc] = useState('')
  const [editCompVisibility, setEditCompVisibility] = useState('private')

  // Auto-select first competition
  if (!selectedId && competitions?.length > 0) {
    setSelectedId(competitions[0].id)
  }

  function showMsg(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 2500)
  }

  async function handleStatusChange(type, id, newStatus) {
    const url = type === 'competition' ? `/api/admin/competitions/${id}` :
                type === 'season' ? `/api/admin/seasons/${id}` :
                `/api/admin/cycles/${id}`
    try {
      await apiFetch(url, { method: 'PATCH', body: JSON.stringify({ status: newStatus }) })
      showMsg('تم التحديث بنجاح')
      refetchDetail()
      refetch()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  async function toggleRegistration(compId, current) {
    try {
      await apiFetch(`/api/admin/competitions/${compId}`, {
        method: 'PATCH',
        body: JSON.stringify({ registration_open: !current }),
      })
      showMsg('تم تحديث التسجيل')
      refetchDetail()
      refetch()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  async function handleCreateCompetition() {
    if (!compName.trim()) return
    setSubmitting(true)
    try {
      const body = { name: compName.trim() }
      if (compDesc.trim()) body.description = compDesc.trim()
      if (compVisibility) body.visibility = compVisibility
      const res = await apiFetch('/api/admin/competitions', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      showMsg('تم إنشاء المنافسة بنجاح')
      setShowCreateComp(false)
      setCompName('')
      setCompDesc('')
      setCompVisibility('private')
      refetch()
      if (res.data?.id) setSelectedId(res.data.id)
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCreateSeason() {
    if (!seasonName.trim()) return
    setSubmitting(true)
    try {
      await apiFetch('/api/admin/seasons', {
        method: 'POST',
        body: JSON.stringify({ competition_id: selectedId, name: seasonName.trim() }),
      })
      showMsg('تم إنشاء الموسم بنجاح')
      setShowCreateSeason(false)
      setSeasonName('')
      refetchDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCreateCycle() {
    if (!cycleLabel.trim() || !cycleSeasonId) return
    setSubmitting(true)
    try {
      await apiFetch('/api/admin/cycles', {
        method: 'POST',
        body: JSON.stringify({ season_id: cycleSeasonId, label: cycleLabel.trim() }),
      })
      showMsg('تم إنشاء الدورة بنجاح')
      setShowCreateCycle(false)
      setCycleLabel('')
      setCycleSeasonId(null)
      refetchDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  function openEditComp() {
    if (!detail) return
    setEditCompName(detail.name || '')
    setEditCompDesc(detail.description || '')
    setEditCompVisibility(detail.visibility || 'private')
    setShowEditComp(true)
  }

  async function handleEditCompetition() {
    if (!editCompName.trim()) return
    setSubmitting(true)
    try {
      await apiFetch(`/api/admin/competitions/${selectedId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: editCompName.trim(),
          description: editCompDesc.trim() || null,
          visibility: editCompVisibility,
        }),
      })
      showMsg('تم تحديث المنافسة بنجاح')
      setShowEditComp(false)
      refetch()
      refetchDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleInviteAction(inviteId, action) {
    try {
      await apiFetch(`/api/admin/invites/${inviteId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: action }),
      })
      showMsg(action === 'disabled' ? 'تم تعطيل الدعوة' : 'تم تفعيل الدعوة')
      refetchDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  function copyInviteCode(code) {
    navigator.clipboard.writeText(code)
    showMsg('تم نسخ رمز الدعوة')
  }

  async function handleCreateInvite() {
    if (!inviteCode.trim()) return
    setSubmitting(true)
    try {
      const body = { competition_id: selectedId, code: inviteCode.trim() }
      if (inviteMaxUses && Number(inviteMaxUses) > 0) body.max_uses = Number(inviteMaxUses)
      await apiFetch('/api/admin/invites', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      showMsg('تم إنشاء رمز الدعوة بنجاح')
      setShowCreateInvite(false)
      setInviteCode('')
      setInviteMaxUses('')
      refetchDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  if (error) {
    return <div className="text-center py-20 text-gray-500 font-bold">{error}</div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">إدارة المنافسة</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">المنافسات، المواسم، الدورات</p>
        </div>
        <button
          onClick={() => setShowCreateComp(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-brand-teal hover:bg-brand-teal-hover text-white rounded-xl font-heading font-black text-sm smooth-transition"
        >
          <iconify-icon icon="lucide:plus" class="text-base"></iconify-icon>
          منافسة جديدة
        </button>
      </div>

      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${
          actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'
        }`}>{actionMsg}</div>
      )}

      {/* Competition List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {competitions?.map(c => (
          <button
            key={c.id}
            onClick={() => setSelectedId(c.id)}
            className={`text-right p-5 rounded-2xl border smooth-transition ${
              selectedId === c.id
                ? 'bg-brand-teal/5 dark:bg-brand-slate/10 border-brand-teal dark:border-brand-slate'
                : 'bg-white dark:bg-brand-card-dark border-gray-200 dark:border-gray-700 hover:shadow-md'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <StatusBadge status={c.status} />
              <span className="text-xs text-gray-400">{c.member_count} لاعب</span>
            </div>
            <h3 className="font-heading font-black text-gray-900 dark:text-white">{c.name}</h3>
            <p className="text-xs text-gray-500 mt-1">{c.season_count} مواسم</p>
          </button>
        ))}
      </div>

      {/* Competition Detail */}
      {selectedId && detail && !detailLoading && (
        <div className="space-y-6">
          {/* Overview */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading font-black text-xl text-gray-900 dark:text-white">{detail.name}</h2>
              <div className="flex items-center gap-2 flex-wrap">
                <StatusBadge status={detail.status} />
                <button
                  onClick={() => toggleRegistration(detail.id, detail.registration_open)}
                  className={`px-3 py-1 rounded-lg text-xs font-black smooth-transition ${
                    detail.registration_open
                      ? 'bg-brand-success/10 text-brand-success hover:bg-brand-success/20'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200'
                  }`}
                >
                  التسجيل: {detail.registration_open ? 'مفتوح' : 'مغلق'}
                </button>
                <button onClick={openEditComp} className="px-3 py-1 rounded-lg text-xs font-black bg-blue-50 dark:bg-blue-900/20 text-blue-600 hover:bg-blue-100 smooth-transition">
                  <iconify-icon icon="lucide:pencil" class="text-xs ml-1"></iconify-icon>
                  تعديل
                </button>
              </div>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{detail.description}</p>
            <div className="flex gap-4 text-sm mb-3">
              <span className="font-bold text-gray-600 dark:text-gray-400">{detail.member_count} لاعب</span>
              <span className="font-bold text-gray-600 dark:text-gray-400">الرؤية: {detail.visibility === 'private' ? 'خاص' : 'عام'}</span>
            </div>
            {/* Competition status controls */}
            <div className="flex gap-2 flex-wrap">
              {detail.status === 'draft' && (
                <button onClick={() => handleStatusChange('competition', detail.id, 'active')} className="px-3 py-1 rounded-lg text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition">تفعيل</button>
              )}
              {detail.status === 'active' && (
                <button onClick={() => handleStatusChange('competition', detail.id, 'paused')} className="px-3 py-1 rounded-lg text-xs font-black bg-amber-100 dark:bg-amber-900/20 text-amber-600 hover:bg-amber-200 smooth-transition">إيقاف مؤقت</button>
              )}
              {detail.status === 'paused' && (
                <>
                  <button onClick={() => handleStatusChange('competition', detail.id, 'active')} className="px-3 py-1 rounded-lg text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition">استئناف</button>
                  <button onClick={() => handleStatusChange('competition', detail.id, 'completed')} className="px-3 py-1 rounded-lg text-xs font-black bg-blue-100 dark:bg-blue-900/20 text-blue-600 hover:bg-blue-200 smooth-transition">إنهاء</button>
                </>
              )}
              {(detail.status === 'completed') && (
                <button onClick={() => handleStatusChange('competition', detail.id, 'archived')} className="px-3 py-1 rounded-lg text-xs font-black bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 smooth-transition">أرشفة</button>
              )}
            </div>
          </div>

          {/* Invites */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
                <iconify-icon icon="lucide:ticket" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                رموز الدعوة
              </h3>
              <button
                onClick={() => setShowCreateInvite(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-teal/10 hover:bg-brand-teal/20 text-brand-teal dark:text-brand-slate rounded-xl text-xs font-heading font-black smooth-transition"
              >
                <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
                رمز جديد
              </button>
            </div>
            <div className="space-y-2">
              {detail.invites?.length > 0 ? detail.invites.map(inv => (
                <div key={inv.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                  <div className="flex items-center gap-3">
                    <code className="bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate px-3 py-1 rounded-lg font-bold text-sm">{inv.code}</code>
                    <StatusBadge status={inv.status} />
                    <span className="text-xs text-gray-400">{inv.use_count} استخدام{inv.max_uses ? ` / ${inv.max_uses}` : ''}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => copyInviteCode(inv.code)}
                      title="نسخ الرمز"
                      className="w-7 h-7 flex items-center justify-center rounded-lg bg-brand-teal/10 text-brand-teal hover:bg-brand-teal/20 smooth-transition"
                    >
                      <iconify-icon icon="lucide:copy" class="text-sm"></iconify-icon>
                    </button>
                    {inv.status === 'active' ? (
                      <button
                        onClick={() => handleInviteAction(inv.id, 'disabled')}
                        className="px-2 py-1 rounded-lg text-[10px] font-black bg-brand-danger/10 text-brand-danger hover:bg-brand-danger/20 smooth-transition"
                      >تعطيل</button>
                    ) : inv.status === 'disabled' ? (
                      <button
                        onClick={() => handleInviteAction(inv.id, 'active')}
                        className="px-2 py-1 rounded-lg text-[10px] font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition"
                      >تفعيل</button>
                    ) : null}
                  </div>
                </div>
              )) : (
                <p className="text-sm text-gray-400 text-center py-3">لا توجد رموز دعوة</p>
              )}
            </div>
          </div>

          {/* Seasons & Cycles Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
              <iconify-icon icon="lucide:calendar" class="text-amber-500"></iconify-icon>
              المواسم والدورات
            </h3>
            <button
              onClick={() => setShowCreateSeason(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-teal/10 hover:bg-brand-teal/20 text-brand-teal dark:text-brand-slate rounded-xl text-xs font-heading font-black smooth-transition"
            >
              <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
              موسم جديد
            </button>
          </div>

          {/* Seasons & Cycles */}
          {detail.seasons?.length > 0 ? detail.seasons.map(season => (
            <div key={season.id} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
                  <iconify-icon icon="lucide:calendar" class="text-amber-500"></iconify-icon>
                  {season.name}
                </h3>
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={season.status} />
                  {season.status === 'draft' && (
                    <button onClick={() => handleStatusChange('season', season.id, 'active')} className="text-xs font-bold text-brand-success hover:underline">تفعيل</button>
                  )}
                  {season.status === 'active' && (
                    <>
                      <button onClick={() => handleStatusChange('season', season.id, 'paused')} className="text-xs font-bold text-amber-600 hover:underline">إيقاف مؤقت</button>
                      <button onClick={() => handleStatusChange('season', season.id, 'completed')} className="text-xs font-bold text-blue-600 hover:underline">إنهاء</button>
                    </>
                  )}
                  {season.status === 'paused' && (
                    <>
                      <button onClick={() => handleStatusChange('season', season.id, 'active')} className="text-xs font-bold text-brand-success hover:underline">استئناف</button>
                      <button onClick={() => handleStatusChange('season', season.id, 'completed')} className="text-xs font-bold text-blue-600 hover:underline">إنهاء</button>
                    </>
                  )}
                  {season.status === 'completed' && (
                    <button onClick={() => handleStatusChange('season', season.id, 'archived')} className="text-xs font-bold text-gray-500 hover:underline">أرشفة</button>
                  )}
                  <button
                    onClick={() => { setCycleSeasonId(season.id); setShowCreateCycle(true) }}
                    className="flex items-center gap-1 px-2.5 py-1 bg-brand-teal/10 hover:bg-brand-teal/20 text-brand-teal dark:text-brand-slate rounded-lg text-xs font-heading font-black smooth-transition"
                  >
                    <iconify-icon icon="lucide:plus" class="text-xs"></iconify-icon>
                    دورة
                  </button>
                </div>
              </div>

              {/* Cycles */}
              <div className="space-y-2">
                {season.cycles?.length > 0 ? season.cycles.map(cycle => (
                  <div key={cycle.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                    <div className="flex items-center gap-3">
                      <iconify-icon icon="lucide:repeat" class="text-gray-400"></iconify-icon>
                      <span className="font-bold text-sm text-gray-700 dark:text-gray-300">{cycle.label}</span>
                      <StatusBadge status={cycle.status} />
                    </div>
                    <div className="flex items-center gap-2">
                      {cycle.status === 'draft' && (
                        <button onClick={() => handleStatusChange('cycle', cycle.id, 'active')} className="text-xs font-bold text-brand-success hover:underline">تفعيل</button>
                      )}
                      {cycle.status === 'active' && (
                        <>
                          <button onClick={() => handleStatusChange('cycle', cycle.id, 'paused')} className="text-xs font-bold text-amber-600 hover:underline">إيقاف</button>
                          <button onClick={() => handleStatusChange('cycle', cycle.id, 'completed')} className="text-xs font-bold text-blue-600 hover:underline">إنهاء</button>
                        </>
                      )}
                      {cycle.status === 'paused' && (
                        <>
                          <button onClick={() => handleStatusChange('cycle', cycle.id, 'active')} className="text-xs font-bold text-brand-success hover:underline">استئناف</button>
                          <button onClick={() => handleStatusChange('cycle', cycle.id, 'completed')} className="text-xs font-bold text-blue-600 hover:underline">إنهاء</button>
                        </>
                      )}
                    </div>
                  </div>
                )) : (
                  <p className="text-sm text-gray-400 text-center py-3">لا توجد دورات</p>
                )}
              </div>
            </div>
          )) : (
            <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-8 text-center">
              <p className="text-sm text-gray-400">لا توجد مواسم بعد</p>
            </div>
          )}
        </div>
      )}

      {/* Create Competition Modal */}
      <CreateModal
        show={showCreateComp}
        onClose={() => { setShowCreateComp(false); setCompName(''); setCompDesc(''); setCompVisibility('private') }}
        title="إنشاء منافسة جديدة"
        onSubmit={handleCreateCompetition}
        submitting={submitting}
      >
        <FormInput label="اسم المنافسة" value={compName} onChange={setCompName} placeholder="أدخل اسم المنافسة" required />
        <FormInput label="الوصف" value={compDesc} onChange={setCompDesc} placeholder="وصف اختياري للمنافسة" />
        <FormSelect
          label="الرؤية"
          value={compVisibility}
          onChange={setCompVisibility}
          options={[
            { value: 'private', label: 'خاص' },
            { value: 'public', label: 'عام' },
          ]}
        />
      </CreateModal>

      {/* Create Season Modal */}
      <CreateModal
        show={showCreateSeason}
        onClose={() => { setShowCreateSeason(false); setSeasonName('') }}
        title="إنشاء موسم جديد"
        onSubmit={handleCreateSeason}
        submitting={submitting}
      >
        <FormInput label="اسم الموسم" value={seasonName} onChange={setSeasonName} placeholder="مثال: الموسم الأول" required />
      </CreateModal>

      {/* Create Cycle Modal */}
      <CreateModal
        show={showCreateCycle}
        onClose={() => { setShowCreateCycle(false); setCycleLabel(''); setCycleSeasonId(null) }}
        title="إنشاء دورة جديدة"
        onSubmit={handleCreateCycle}
        submitting={submitting}
      >
        <FormInput label="تسمية الدورة" value={cycleLabel} onChange={setCycleLabel} placeholder="مثال: الدورة الأولى" required />
      </CreateModal>

      {/* Edit Competition Modal */}
      <CreateModal
        show={showEditComp}
        onClose={() => setShowEditComp(false)}
        title="تعديل المنافسة"
        onSubmit={handleEditCompetition}
        submitting={submitting}
      >
        <FormInput label="اسم المنافسة" value={editCompName} onChange={setEditCompName} placeholder="اسم المنافسة" required />
        <FormInput label="الوصف" value={editCompDesc} onChange={setEditCompDesc} placeholder="وصف المنافسة" />
        <FormSelect
          label="الرؤية"
          value={editCompVisibility}
          onChange={setEditCompVisibility}
          options={[
            { value: 'private', label: 'خاص' },
            { value: 'public', label: 'عام' },
          ]}
        />
      </CreateModal>

      {/* Create Invite Modal */}
      <CreateModal
        show={showCreateInvite}
        onClose={() => { setShowCreateInvite(false); setInviteCode(''); setInviteMaxUses('') }}
        title="إنشاء رمز دعوة"
        onSubmit={handleCreateInvite}
        submitting={submitting}
      >
        <FormInput label="رمز الدعوة" value={inviteCode} onChange={setInviteCode} placeholder="أدخل رمز الدعوة" required />
        <FormInput label="الحد الأقصى للاستخدام" value={inviteMaxUses} onChange={setInviteMaxUses} placeholder="اختياري — اتركه فارغاً لغير محدود" type="number" />
      </CreateModal>
    </div>
  )
}
