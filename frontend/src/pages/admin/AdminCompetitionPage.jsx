/**
 * AdminCompetitionPage — Competition workspace/profile view.
 * Shows the currently selected competition as a real operational container:
 * identity, status, registration, invites, quick stats, and links to deeper sections.
 * Also allows creating new competitions (for the sidebar selector to pick up).
 */

import { useState, useCallback, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'

const STATUS_LABELS = {
  active: { text: 'نشطة', color: 'bg-brand-success/10 text-brand-success' },
  draft: { text: 'مسودة', color: 'bg-gray-100 dark:bg-gray-800 text-gray-500' },
  paused: { text: 'متوقفة', color: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' },
  completed: { text: 'منتهية', color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' },
  archived: { text: 'مؤرشفة', color: 'bg-gray-100 dark:bg-gray-800 text-gray-400' },
}

const QUICK_LINKS = [
  { to: '/admin/members', icon: 'lucide:users', label: 'الأعضاء', desc: 'إدارة عضويات المنافسة' },
  { to: '/admin/seasons', icon: 'lucide:calendar-range', label: 'المواسم والدورات', desc: 'الهيكل الزمني للمنافسة' },
  { to: '/admin/attacks', icon: 'lucide:swords', label: 'الهجمات', desc: 'عرض وإدارة الهجمات' },
  { to: '/admin/quiz', icon: 'lucide:book-open', label: 'الأسئلة', desc: 'بنك الأسئلة والجلسات' },
  { to: '/admin/store', icon: 'lucide:shopping-bag', label: 'المتجر', desc: 'العناصر والعروض' },
  { to: '/admin/settings', icon: 'lucide:settings', label: 'إعدادات المنافسة', desc: 'تجاوز القيم الافتراضية' },
]

export default function AdminCompetitionPage() {
  const { selected, selectedId, refreshCompetitions } = useAdminCompetition()
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  // Create competition modal
  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createDesc, setCreateDesc] = useState('')
  const [createVisibility, setCreateVisibility] = useState('private')
  const [creating, setCreating] = useState(false)

  // Edit competition modal
  const [showEdit, setShowEdit] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editVisibility, setEditVisibility] = useState('private')

  // Invite modal
  const [showInvite, setShowInvite] = useState(false)
  const [inviteCode, setInviteCode] = useState('')
  const [inviteMaxUses, setInviteMaxUses] = useState('')

  const [submitting, setSubmitting] = useState(false)

  function showMsg(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 3000)
  }

  const loadDetail = useCallback(() => {
    if (!selectedId) return
    setLoading(true)
    apiFetch(`/api/admin/competitions/${selectedId}`)
      .then(json => setDetail(json.data))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false))
  }, [selectedId])

  useEffect(() => { loadDetail() }, [loadDetail])

  async function handleStatusChange(newStatus) {
    try {
      await apiFetch(`/api/admin/competitions/${selectedId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      showMsg('تم تحديث الحالة')
      loadDetail()
      refreshCompetitions()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  async function toggleRegistration() {
    try {
      await apiFetch(`/api/admin/competitions/${selectedId}`, {
        method: 'PATCH',
        body: JSON.stringify({ registration_open: !detail.registration_open }),
      })
      showMsg('تم تحديث التسجيل')
      loadDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  async function handleCreateCompetition() {
    if (!createName.trim()) return
    setCreating(true)
    try {
      const body = { name: createName.trim() }
      if (createDesc.trim()) body.description = createDesc.trim()
      if (createVisibility) body.visibility = createVisibility
      await apiFetch('/api/admin/competitions', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      showMsg('تم إنشاء المنافسة — اخترها من القائمة الجانبية')
      setShowCreate(false)
      setCreateName('')
      setCreateDesc('')
      setCreateVisibility('private')
      refreshCompetitions()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
    setCreating(false)
  }

  function openEdit() {
    if (!detail) return
    setEditName(detail.name || '')
    setEditDesc(detail.description || '')
    setEditVisibility(detail.visibility || 'private')
    setShowEdit(true)
  }

  async function handleEditCompetition() {
    if (!editName.trim()) return
    setSubmitting(true)
    try {
      await apiFetch(`/api/admin/competitions/${selectedId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: editName.trim(),
          description: editDesc.trim() || null,
          visibility: editVisibility,
        }),
      })
      showMsg('تم تحديث المنافسة')
      setShowEdit(false)
      loadDetail()
      refreshCompetitions()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
    setSubmitting(false)
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
      showMsg('تم إنشاء رمز الدعوة')
      setShowInvite(false)
      setInviteCode('')
      setInviteMaxUses('')
      loadDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
    setSubmitting(false)
  }

  async function handleInviteAction(inviteId, action) {
    try {
      await apiFetch(`/api/admin/invites/${inviteId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: action }),
      })
      showMsg(action === 'disabled' ? 'تم تعطيل الدعوة' : 'تم تفعيل الدعوة')
      loadDetail()
    } catch (err) {
      showMsg(`خطأ: ${err.message}`)
    }
  }

  function copyInviteCode(code) {
    navigator.clipboard.writeText(code)
    showMsg('تم نسخ رمز الدعوة')
  }

  // ── No competition selected ──
  if (!selected) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <iconify-icon icon="lucide:trophy" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="font-bold text-gray-500 dark:text-gray-400 mb-4">اختر منافسة من القائمة الجانبية لعرض تفاصيلها</p>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-teal hover:bg-brand-teal-hover text-white rounded-xl font-heading font-black text-sm smooth-transition"
          >
            <iconify-icon icon="lucide:plus" class="text-base"></iconify-icon>
            إنشاء منافسة جديدة
          </button>
        </div>
        {renderCreateModal()}
      </div>
    )
  }

  if (loading || !detail) {
    return (
      <div className="flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
      </div>
    )
  }

  const st = STATUS_LABELS[detail.status] || STATUS_LABELS.draft
  const activeSeason = detail.seasons?.find(s => s.status === 'active')
  const activeCycle = activeSeason?.cycles?.find(c => c.status === 'active')

  return (
    <div className="space-y-6">
      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${
          actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'
        }`}>{actionMsg}</div>
      )}

      {/* ══ Competition Identity ══ */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">{detail.name}</h1>
              <span className={`text-xs font-black px-2.5 py-1 rounded-lg ${st.color}`}>{st.text}</span>
            </div>
            {detail.description && (
              <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mb-3">{detail.description}</p>
            )}
            <div className="flex items-center gap-4 text-sm flex-wrap">
              <span className="font-bold text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                <iconify-icon icon="lucide:users" class="text-base"></iconify-icon>
                {detail.member_count} عضو
              </span>
              <span className="font-bold text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                <iconify-icon icon="lucide:calendar-range" class="text-base"></iconify-icon>
                {detail.seasons?.length || 0} مواسم
              </span>
              <span className="font-bold text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                <iconify-icon icon={detail.visibility === 'private' ? 'lucide:lock' : 'lucide:globe'} class="text-base"></iconify-icon>
                {detail.visibility === 'private' ? 'خاصة' : 'عامة'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={openEdit}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 smooth-transition"
            >
              <iconify-icon icon="lucide:pencil" class="text-sm"></iconify-icon>
              تعديل
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold bg-brand-teal/10 text-brand-teal dark:text-brand-slate hover:bg-brand-teal/20 smooth-transition"
            >
              <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
              منافسة جديدة
            </button>
          </div>
        </div>

        {/* Status & Registration controls */}
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-800 flex-wrap">
          <button
            onClick={toggleRegistration}
            className={`px-3 py-1.5 rounded-lg text-xs font-black smooth-transition ${
              detail.registration_open
                ? 'bg-brand-success/10 text-brand-success hover:bg-brand-success/20'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            <iconify-icon icon={detail.registration_open ? 'lucide:door-open' : 'lucide:door-closed'} class="text-xs ml-1"></iconify-icon>
            التسجيل: {detail.registration_open ? 'مفتوح' : 'مغلق'}
          </button>

          <div className="h-5 w-px bg-gray-200 dark:bg-gray-700"></div>

          {detail.status === 'draft' && (
            <button onClick={() => handleStatusChange('active')} className="px-3 py-1.5 rounded-lg text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition">تفعيل المنافسة</button>
          )}
          {detail.status === 'active' && (
            <button onClick={() => handleStatusChange('paused')} className="px-3 py-1.5 rounded-lg text-xs font-black bg-amber-100 dark:bg-amber-900/20 text-amber-600 hover:bg-amber-200 smooth-transition">إيقاف مؤقت</button>
          )}
          {detail.status === 'paused' && (
            <>
              <button onClick={() => handleStatusChange('active')} className="px-3 py-1.5 rounded-lg text-xs font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition">استئناف</button>
              <button onClick={() => handleStatusChange('completed')} className="px-3 py-1.5 rounded-lg text-xs font-black bg-blue-100 dark:bg-blue-900/20 text-blue-600 hover:bg-blue-200 smooth-transition">إنهاء</button>
            </>
          )}
          {detail.status === 'completed' && (
            <button onClick={() => handleStatusChange('archived')} className="px-3 py-1.5 rounded-lg text-xs font-black bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200 smooth-transition">أرشفة</button>
          )}
        </div>
      </div>

      {/* ══ Active Context Banner ══ */}
      {(activeSeason || activeCycle) && (
        <div className="bg-brand-teal/5 dark:bg-brand-slate/10 border border-brand-teal/20 dark:border-brand-slate/20 rounded-2xl p-4">
          <div className="flex items-center gap-3 text-sm">
            <iconify-icon icon="lucide:play-circle" class="text-lg text-brand-teal dark:text-brand-slate flex-shrink-0"></iconify-icon>
            <div>
              <span className="font-black text-gray-900 dark:text-white">السياق النشط: </span>
              {activeSeason && <span className="font-bold text-brand-teal dark:text-brand-slate">{activeSeason.name}</span>}
              {activeCycle && (
                <>
                  <span className="text-gray-400 mx-1.5">›</span>
                  <span className="font-bold text-gray-600 dark:text-gray-300">{activeCycle.label}</span>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══ Quick Stats ══ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: 'lucide:users', label: 'الأعضاء', value: detail.member_count, color: 'text-brand-teal dark:text-brand-slate' },
          { icon: 'lucide:calendar-range', label: 'المواسم', value: detail.seasons?.length || 0, color: 'text-amber-500' },
          { icon: 'lucide:ticket', label: 'رموز الدعوة', value: detail.invites?.length || 0, color: 'text-blue-500' },
          { icon: 'lucide:eye', label: 'الرؤية', value: detail.visibility === 'private' ? 'خاصة' : 'عامة', color: 'text-gray-500' },
        ].map((stat, i) => (
          <div key={i} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <iconify-icon icon={stat.icon} class={`text-lg ${stat.color}`}></iconify-icon>
              <span className="text-xs font-black text-gray-400 dark:text-gray-500">{stat.label}</span>
            </div>
            <div className="font-heading font-black text-xl text-gray-900 dark:text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* ══ Invite Codes ══ */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
            <iconify-icon icon="lucide:ticket" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            رموز الدعوة
          </h2>
          <button
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-teal/10 hover:bg-brand-teal/20 text-brand-teal dark:text-brand-slate rounded-xl text-xs font-heading font-black smooth-transition"
          >
            <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
            رمز جديد
          </button>
        </div>
        <div className="space-y-2">
          {detail.invites?.length > 0 ? detail.invites.map(inv => {
            const invSt = inv.status === 'active'
              ? 'bg-brand-success/10 text-brand-success'
              : inv.status === 'disabled' ? 'bg-red-100 dark:bg-red-900/20 text-red-600' : 'bg-gray-100 text-gray-500'
            return (
              <div key={inv.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                <div className="flex items-center gap-3">
                  <code className="bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate px-3 py-1 rounded-lg font-bold text-sm">{inv.code}</code>
                  <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${invSt}`}>{inv.status}</span>
                  <span className="text-xs text-gray-400 font-bold">{inv.use_count} استخدام{inv.max_uses ? ` / ${inv.max_uses}` : ''}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyInviteCode(inv.code)}
                    className="w-7 h-7 flex items-center justify-center rounded-lg bg-brand-teal/10 text-brand-teal hover:bg-brand-teal/20 smooth-transition"
                    title="نسخ"
                  >
                    <iconify-icon icon="lucide:copy" class="text-sm"></iconify-icon>
                  </button>
                  {inv.status === 'active' ? (
                    <button onClick={() => handleInviteAction(inv.id, 'disabled')} className="px-2 py-1 rounded-lg text-[10px] font-black bg-brand-danger/10 text-brand-danger hover:bg-brand-danger/20 smooth-transition">تعطيل</button>
                  ) : inv.status === 'disabled' ? (
                    <button onClick={() => handleInviteAction(inv.id, 'active')} className="px-2 py-1 rounded-lg text-[10px] font-black bg-brand-success/10 text-brand-success hover:bg-brand-success/20 smooth-transition">تفعيل</button>
                  ) : null}
                </div>
              </div>
            )
          }) : (
            <p className="text-sm font-bold text-gray-400 text-center py-4">لا توجد رموز دعوة</p>
          )}
        </div>
      </div>

      {/* ══ Quick Navigation ══ */}
      <div>
        <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <iconify-icon icon="lucide:layout-grid" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
          أقسام المنافسة
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {QUICK_LINKS.map(link => (
            <Link
              key={link.to}
              to={link.to}
              className="flex items-center gap-3 p-4 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl hover:border-brand-teal/30 dark:hover:border-brand-slate/30 hover:shadow-sm smooth-transition group"
            >
              <div className="w-10 h-10 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-brand-teal/20 smooth-transition">
                <iconify-icon icon={link.icon} class="text-lg text-brand-teal dark:text-brand-slate"></iconify-icon>
              </div>
              <div className="min-w-0">
                <div className="font-bold text-sm text-gray-900 dark:text-white">{link.label}</div>
                <div className="text-xs font-bold text-gray-400 dark:text-gray-500">{link.desc}</div>
              </div>
              <iconify-icon icon="lucide:chevron-left" class="text-gray-300 dark:text-gray-600 mr-auto group-hover:text-brand-teal dark:group-hover:text-brand-slate smooth-transition"></iconify-icon>
            </Link>
          ))}
        </div>
      </div>

      {/* ══ Modals ══ */}
      {renderCreateModal()}
      {renderEditModal()}
      {renderInviteModal()}
    </div>
  )

  function renderCreateModal() {
    if (!showCreate) return null
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowCreate(false)}>
        <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
          <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white">إنشاء منافسة جديدة</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">اسم المنافسة <span className="text-brand-danger">*</span></label>
              <input type="text" value={createName} onChange={e => setCreateName(e.target.value)} placeholder="أدخل اسم المنافسة" className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الوصف</label>
              <input type="text" value={createDesc} onChange={e => setCreateDesc(e.target.value)} placeholder="وصف اختياري" className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الرؤية</label>
              <select value={createVisibility} onChange={e => setCreateVisibility(e.target.value)} className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white">
                <option value="private">خاصة</option>
                <option value="public">عامة</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={handleCreateCompetition} disabled={creating} className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
              {creating ? 'جارٍ الإنشاء...' : 'إنشاء'}
            </button>
            <button onClick={() => setShowCreate(false)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
          </div>
        </div>
      </div>
    )
  }

  function renderEditModal() {
    if (!showEdit) return null
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowEdit(false)}>
        <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
          <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white">تعديل المنافسة</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">اسم المنافسة <span className="text-brand-danger">*</span></label>
              <input type="text" value={editName} onChange={e => setEditName(e.target.value)} className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الوصف</label>
              <input type="text" value={editDesc} onChange={e => setEditDesc(e.target.value)} className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الرؤية</label>
              <select value={editVisibility} onChange={e => setEditVisibility(e.target.value)} className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white">
                <option value="private">خاصة</option>
                <option value="public">عامة</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={handleEditCompetition} disabled={submitting} className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
              {submitting ? 'جارٍ الحفظ...' : 'حفظ التعديلات'}
            </button>
            <button onClick={() => setShowEdit(false)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
          </div>
        </div>
      </div>
    )
  }

  function renderInviteModal() {
    if (!showInvite) return null
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowInvite(false)}>
        <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
          <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white">إنشاء رمز دعوة</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">رمز الدعوة <span className="text-brand-danger">*</span></label>
              <input type="text" value={inviteCode} onChange={e => setInviteCode(e.target.value)} placeholder="أدخل رمز الدعوة" className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الحد الأقصى للاستخدام</label>
              <input type="number" value={inviteMaxUses} onChange={e => setInviteMaxUses(e.target.value)} placeholder="اختياري — اتركه فارغاً لغير محدود" className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={handleCreateInvite} disabled={submitting} className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
              {submitting ? 'جارٍ الإنشاء...' : 'إنشاء'}
            </button>
            <button onClick={() => setShowInvite(false)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
          </div>
        </div>
      </div>
    )
  }
}
