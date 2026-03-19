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

export default function AdminCompetitionPage() {
  const { data: competitions, loading, error, refetch } = useAdminData('/api/admin/competitions')
  const [selectedId, setSelectedId] = useState(null)
  const { data: detail, loading: detailLoading, refetch: refetchDetail } = useAdminData(
    selectedId ? `/api/admin/competitions/${selectedId}` : null
  )
  const [actionMsg, setActionMsg] = useState(null)

  // Auto-select first competition
  if (!selectedId && competitions?.length > 0) {
    setSelectedId(competitions[0].id)
  }

  async function handleStatusChange(type, id, newStatus) {
    const url = type === 'competition' ? `/api/admin/competitions/${id}` :
                type === 'season' ? `/api/admin/seasons/${id}` :
                `/api/admin/cycles/${id}`
    try {
      await apiFetch(url, { method: 'PATCH', body: JSON.stringify({ status: newStatus }) })
      setActionMsg('تم التحديث بنجاح')
      refetchDetail()
      refetch()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    }
  }

  async function toggleRegistration(compId, current) {
    try {
      await apiFetch(`/api/admin/competitions/${compId}`, {
        method: 'PATCH',
        body: JSON.stringify({ registration_open: !current }),
      })
      setActionMsg('تم تحديث التسجيل')
      refetchDetail()
      refetch()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
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
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">إدارة المنافسة</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">المنافسات، المواسم، الدورات</p>
      </div>

      {actionMsg && (
        <div className="bg-brand-success/10 text-brand-success px-4 py-2 rounded-xl text-sm font-bold">{actionMsg}</div>
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
              <div className="flex items-center gap-2">
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
              </div>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{detail.description}</p>
            <div className="flex gap-4 text-sm">
              <span className="font-bold text-gray-600 dark:text-gray-400">{detail.member_count} لاعب</span>
              <span className="font-bold text-gray-600 dark:text-gray-400">الرؤية: {detail.visibility}</span>
            </div>
          </div>

          {/* Invites */}
          {detail.invites?.length > 0 && (
            <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
              <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <iconify-icon icon="lucide:ticket" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                رموز الدعوة
              </h3>
              <div className="space-y-2">
                {detail.invites.map(inv => (
                  <div key={inv.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                    <div className="flex items-center gap-3">
                      <code className="bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate px-3 py-1 rounded-lg font-bold text-sm">{inv.code}</code>
                      <StatusBadge status={inv.status} />
                    </div>
                    <span className="text-xs text-gray-400">{inv.use_count} استخدام{inv.max_uses ? ` / ${inv.max_uses}` : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Seasons & Cycles */}
          {detail.seasons?.map(season => (
            <div key={season.id} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
                  <iconify-icon icon="lucide:calendar" class="text-amber-500"></iconify-icon>
                  {season.name}
                </h3>
                <div className="flex items-center gap-2">
                  <StatusBadge status={season.status} />
                  {season.status === 'active' && (
                    <button onClick={() => handleStatusChange('season', season.id, 'paused')} className="text-xs font-bold text-amber-600 hover:underline">إيقاف مؤقت</button>
                  )}
                  {season.status === 'paused' && (
                    <button onClick={() => handleStatusChange('season', season.id, 'active')} className="text-xs font-bold text-brand-success hover:underline">استئناف</button>
                  )}
                </div>
              </div>

              {/* Cycles */}
              <div className="space-y-2">
                {season.cycles?.map(cycle => (
                  <div key={cycle.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                    <div className="flex items-center gap-3">
                      <iconify-icon icon="lucide:repeat" class="text-gray-400"></iconify-icon>
                      <span className="font-bold text-sm text-gray-700 dark:text-gray-300">{cycle.label}</span>
                      <StatusBadge status={cycle.status} />
                    </div>
                    <div className="flex items-center gap-2">
                      {cycle.status === 'active' && (
                        <button onClick={() => handleStatusChange('cycle', cycle.id, 'completed')} className="text-xs font-bold text-blue-600 hover:underline">إنهاء</button>
                      )}
                      {cycle.status === 'draft' && (
                        <button onClick={() => handleStatusChange('cycle', cycle.id, 'active')} className="text-xs font-bold text-brand-success hover:underline">تفعيل</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
