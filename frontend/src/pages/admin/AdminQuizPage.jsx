import { useState } from 'react'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

function StatusBadge({ status }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success', open: 'bg-brand-success/10 text-brand-success',
    draft: 'bg-gray-100 dark:bg-gray-800 text-gray-500', closed: 'bg-brand-danger/10 text-brand-danger',
    completed: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600', archived: 'bg-gray-100 text-gray-400',
    easy: 'bg-brand-success/10 text-brand-success', medium: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
    hard: 'bg-brand-danger/10 text-brand-danger',
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{status}</span>
}

export default function AdminQuizPage() {
  const [tab, setTab] = useState('sessions') // 'sessions' | 'questions' | 'groups'
  const { data: sessions, loading: loadingSessions, refetch: refetchSessions } = useAdminData('/api/admin/quiz-sessions')
  const { data: questions, loading: loadingQuestions } = useAdminData('/api/admin/questions')
  const { data: groups, loading: loadingGroups } = useAdminData('/api/admin/questions/groups')
  const [actionMsg, setActionMsg] = useState(null)

  async function handleSessionStatusChange(sessionId, newStatus) {
    try {
      await apiFetch(`/api/admin/quiz-sessions/${sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      setActionMsg('تم تحديث الجلسة')
      refetchSessions()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    }
  }

  const loading = tab === 'sessions' ? loadingSessions : tab === 'questions' ? loadingQuestions : loadingGroups

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">إدارة الأسئلة</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">بنك الأسئلة وجلسات الاختبار</p>
      </div>

      {actionMsg && (
        <div className="bg-brand-success/10 text-brand-success px-4 py-2 rounded-xl text-sm font-bold">{actionMsg}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit">
        {[
          { key: 'sessions', label: 'الجلسات', icon: 'lucide:play-circle' },
          { key: 'questions', label: 'الأسئلة', icon: 'lucide:help-circle' },
          { key: 'groups', label: 'المجموعات', icon: 'lucide:folder' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold smooth-transition ${
              tab === t.key
                ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <iconify-icon icon={t.icon} class="text-sm"></iconify-icon>
            {t.label}
          </button>
        ))}
      </div>

      {/* Sessions Tab */}
      {tab === 'sessions' && (
        <div className="space-y-4">
          {sessions?.map(s => (
            <div key={s.id} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="font-heading font-black text-gray-900 dark:text-white">{s.title}</h3>
                  <StatusBadge status={s.status} />
                </div>
                <div className="flex items-center gap-2">
                  {s.status === 'open' && (
                    <button onClick={() => handleSessionStatusChange(s.id, 'closed')} className="px-3 py-1 rounded-lg text-xs font-bold text-brand-danger hover:bg-brand-danger/10 smooth-transition">
                      إغلاق
                    </button>
                  )}
                  {s.status === 'closed' && (
                    <button onClick={() => handleSessionStatusChange(s.id, 'open')} className="px-3 py-1 rounded-lg text-xs font-bold text-brand-success hover:bg-brand-success/10 smooth-transition">
                      إعادة فتح
                    </button>
                  )}
                  {s.status === 'draft' && (
                    <button onClick={() => handleSessionStatusChange(s.id, 'open')} className="px-3 py-1 rounded-lg text-xs font-bold text-brand-success hover:bg-brand-success/10 smooth-transition">
                      فتح
                    </button>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">الأسئلة</div>
                  <div className="font-heading font-black text-gray-900 dark:text-white">{s.question_count}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">المشاركون</div>
                  <div className="font-heading font-black text-gray-900 dark:text-white">{s.participant_count}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">الإجابات</div>
                  <div className="font-heading font-black text-gray-900 dark:text-white">{s.total_submissions}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">صحيحة</div>
                  <div className="font-heading font-black text-brand-success">{s.correct_submissions}</div>
                </div>
              </div>
              <div className="mt-3 text-xs text-gray-400">
                النوع: {s.session_type} — مدة الإجابة: {s.answer_duration_seconds}ث
              </div>
            </div>
          ))}
          {(!sessions || sessions.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold">لا توجد جلسات</div>
          )}
        </div>
      )}

      {/* Questions Tab */}
      {tab === 'questions' && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">السؤال</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الصعوبة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">النقاط</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الإجابة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الحالة</th>
                </tr>
              </thead>
              <tbody>
                {questions?.map(q => (
                  <tr key={q.id} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="px-4 py-3">
                      <div className="font-bold text-gray-900 dark:text-white max-w-md truncate">{q.prompt}</div>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={q.difficulty} /></td>
                    <td className="px-4 py-3 font-heading font-black text-gray-900 dark:text-white">{q.score_value}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{q.correct_answer?.answer}</td>
                    <td className="px-4 py-3"><StatusBadge status={q.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(!questions || questions.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold">لا توجد أسئلة</div>
          )}
        </div>
      )}

      {/* Groups Tab */}
      {tab === 'groups' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {groups?.map(g => (
            <div key={g.id} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-heading font-black text-gray-900 dark:text-white">{g.title}</h3>
                <StatusBadge status={g.status} />
              </div>
              <p className="text-sm text-gray-500 mb-3">{g.description}</p>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span>{g.question_count} سؤال</span>
              </div>
            </div>
          ))}
          {(!groups || groups.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold col-span-2">لا توجد مجموعات</div>
          )}
        </div>
      )}
    </div>
  )
}
