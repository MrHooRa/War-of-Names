import { useState } from 'react'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

const ACTIVE_COMPETITION_ID = '00000000-0000-0000-0000-000000000001'

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

function ModalOverlay({ children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-5"
        onClick={e => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

function ModalTitle({ icon, children }) {
  return (
    <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
      <iconify-icon icon={icon} class="text-brand-teal dark:text-brand-slate text-xl"></iconify-icon>
      {children}
    </h2>
  )
}

function FieldLabel({ children }) {
  return <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">{children}</label>
}

function TextInput({ value, onChange, placeholder, type = 'text', ...rest }) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/30 smooth-transition"
      {...rest}
    />
  )
}

function SelectInput({ value, onChange, children }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/30 smooth-transition"
    >
      {children}
    </select>
  )
}

function ModalActions({ onCancel, onSubmit, submitLabel, submitting }) {
  return (
    <div className="flex items-center justify-end gap-3 pt-2">
      <button
        type="button"
        onClick={onCancel}
        className="bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-xl px-4 py-2 text-sm font-bold smooth-transition hover:bg-gray-200 dark:hover:bg-gray-700"
      >
        إلغاء
      </button>
      <button
        type="submit"
        onClick={onSubmit}
        disabled={submitting}
        className="bg-brand-teal text-white rounded-xl px-5 py-2.5 font-heading font-black text-sm smooth-transition hover:bg-brand-teal-hover disabled:opacity-50 flex items-center gap-2"
      >
        {submitting && <iconify-icon icon="lucide:loader-2" class="text-sm animate-spin"></iconify-icon>}
        <iconify-icon icon="lucide:save" class="text-sm"></iconify-icon>
        {submitLabel}
      </button>
    </div>
  )
}

function CreateButton({ icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 bg-brand-teal text-white rounded-xl px-4 py-2.5 font-heading font-black text-sm smooth-transition hover:bg-brand-teal-hover"
    >
      <iconify-icon icon={icon} class="text-base"></iconify-icon>
      {label}
    </button>
  )
}

function ConfirmDeleteModal({ title, message, onCancel, onConfirm, deleting }) {
  return (
    <ModalOverlay onClose={onCancel}>
      <ModalTitle icon="lucide:alert-triangle">{title}</ModalTitle>
      <p className="text-sm text-gray-600 dark:text-gray-400">{message}</p>
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onCancel}
          className="bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-xl px-4 py-2 text-sm font-bold smooth-transition hover:bg-gray-200 dark:hover:bg-gray-700"
        >
          إلغاء
        </button>
        <button
          onClick={onConfirm}
          disabled={deleting}
          className="bg-brand-danger text-white rounded-xl px-5 py-2.5 font-heading font-black text-sm smooth-transition hover:bg-red-600 disabled:opacity-50 flex items-center gap-2"
        >
          {deleting && <iconify-icon icon="lucide:loader-2" class="text-sm animate-spin"></iconify-icon>}
          <iconify-icon icon="lucide:trash-2" class="text-sm"></iconify-icon>
          حذف
        </button>
      </div>
    </ModalOverlay>
  )
}

// ─── Create Question Group Modal ──────────────────────────────────────────────
function CreateGroupModal({ onClose, onSuccess }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit() {
    if (!title.trim()) { setError('عنوان المجموعة مطلوب'); return }
    setSubmitting(true); setError(null)
    try {
      await apiFetch('/api/admin/questions/groups', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim(), description: description.trim() || undefined }),
      })
      onSuccess('تم إنشاء المجموعة بنجاح')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <ModalTitle icon="lucide:folder-plus">إنشاء مجموعة أسئلة</ModalTitle>
      {error && <div className="bg-brand-danger/10 text-brand-danger px-3 py-2 rounded-xl text-sm font-bold">{error}</div>}
      <div>
        <FieldLabel>عنوان المجموعة *</FieldLabel>
        <TextInput value={title} onChange={setTitle} placeholder="مثال: أسئلة الجولة الأولى" />
      </div>
      <div>
        <FieldLabel>الوصف</FieldLabel>
        <TextInput value={description} onChange={setDescription} placeholder="وصف اختياري للمجموعة" />
      </div>
      <ModalActions onCancel={onClose} onSubmit={handleSubmit} submitLabel="إنشاء المجموعة" submitting={submitting} />
    </ModalOverlay>
  )
}

// ─── Create / Edit Question Modal ─────────────────────────────────────────────
function QuestionModal({ question, groups, onClose, onSuccess }) {
  const isEdit = !!question
  const [groupId, setGroupId] = useState(question?.group_id || '')
  const [questionType, setQuestionType] = useState(question?.question_type || 'multiple_choice')
  const [prompt, setPrompt] = useState(question?.prompt || '')
  const [choices, setChoices] = useState(() => {
    if (question?.options?.choices?.length) return [...question.options.choices, ...Array(4 - question.options.choices.length).fill('')]
    return ['', '', '', '']
  })
  const [correctAnswer, setCorrectAnswer] = useState(question?.correct_answer?.answer || question?.options?.correct || '')
  const [scoreValue, setScoreValue] = useState(question?.score_value ?? 10)
  const [difficulty, setDifficulty] = useState(question?.difficulty || 'easy')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const isTrueFalse = questionType === 'true_false'
  const trueFalseChoices = ['صح', 'خطأ']

  function updateChoice(index, value) {
    setChoices(prev => prev.map((c, i) => (i === index ? value : c)))
  }

  function handleTypeChange(type) {
    setQuestionType(type)
    if (type === 'true_false') {
      setChoices(['صح', 'خطأ', '', ''])
      if (!['صح', 'خطأ'].includes(correctAnswer)) setCorrectAnswer('')
    } else {
      if (choices[0] === 'صح' && choices[1] === 'خطأ') setChoices(['', '', '', ''])
    }
  }

  async function handleSubmit() {
    if (!prompt.trim()) { setError('نص السؤال مطلوب'); return }
    if (!correctAnswer.trim()) { setError('الإجابة الصحيحة مطلوبة'); return }

    const filteredChoices = isTrueFalse ? trueFalseChoices : choices.map(c => c.trim()).filter(Boolean)
    if (filteredChoices.length < 2) { setError('أدخل خيارين على الأقل'); return }
    if (!filteredChoices.includes(correctAnswer.trim())) { setError('الإجابة الصحيحة يجب أن تكون أحد الخيارات'); return }

    setSubmitting(true); setError(null)
    try {
      const payload = {
        prompt: prompt.trim(),
        question_type: questionType,
        options: { choices: filteredChoices, correct: correctAnswer.trim() },
        correct_answer: { answer: correctAnswer.trim() },
        score_value: Number(scoreValue),
        difficulty,
      }

      if (isEdit) {
        await apiFetch(`/api/admin/questions/${question.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        onSuccess('تم تعديل السؤال بنجاح')
      } else {
        if (!groupId) { setError('اختر مجموعة الأسئلة'); setSubmitting(false); return }
        await apiFetch('/api/admin/questions', {
          method: 'POST',
          body: JSON.stringify({ ...payload, group_id: groupId }),
        })
        onSuccess('تم إنشاء السؤال بنجاح')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <ModalTitle icon={isEdit ? 'lucide:edit' : 'lucide:plus-circle'}>
        {isEdit ? 'تعديل السؤال' : 'إنشاء سؤال جديد'}
      </ModalTitle>
      {error && <div className="bg-brand-danger/10 text-brand-danger px-3 py-2 rounded-xl text-sm font-bold">{error}</div>}

      {!isEdit && (
        <div>
          <FieldLabel>المجموعة *</FieldLabel>
          <SelectInput value={groupId} onChange={setGroupId}>
            <option value="">-- اختر المجموعة --</option>
            {groups?.map(g => <option key={g.id} value={g.id}>{g.title}</option>)}
          </SelectInput>
        </div>
      )}

      {/* Question Type */}
      <div>
        <FieldLabel>نوع السؤال</FieldLabel>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handleTypeChange('multiple_choice')}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-bold smooth-transition border ${
              !isTrueFalse
                ? 'bg-brand-teal/10 text-brand-teal border-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate dark:border-brand-slate'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <iconify-icon icon="lucide:list" class="text-sm"></iconify-icon>
            اختيار من متعدد
          </button>
          <button
            type="button"
            onClick={() => handleTypeChange('true_false')}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-bold smooth-transition border ${
              isTrueFalse
                ? 'bg-brand-teal/10 text-brand-teal border-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate dark:border-brand-slate'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <iconify-icon icon="lucide:check-circle" class="text-sm"></iconify-icon>
            صح / خطأ
          </button>
        </div>
      </div>

      <div>
        <FieldLabel>نص السؤال *</FieldLabel>
        <TextInput value={prompt} onChange={setPrompt} placeholder="اكتب نص السؤال هنا" />
      </div>

      {/* Choices — dynamic based on type */}
      {isTrueFalse ? (
        <div>
          <FieldLabel>الإجابة الصحيحة *</FieldLabel>
          <div className="flex gap-3">
            {trueFalseChoices.map(c => (
              <button
                key={c}
                type="button"
                onClick={() => setCorrectAnswer(c)}
                className={`flex-1 py-3 rounded-xl text-sm font-black smooth-transition border-2 ${
                  correctAnswer === c
                    ? c === 'صح'
                      ? 'bg-brand-success/10 text-brand-success border-brand-success'
                      : 'bg-brand-danger/10 text-brand-danger border-brand-danger'
                    : 'bg-gray-50 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700 hover:bg-gray-100'
                }`}
              >
                <iconify-icon icon={c === 'صح' ? 'lucide:check' : 'lucide:x'} class="text-lg ml-1"></iconify-icon>
                {c}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <>
          <div>
            <FieldLabel>الخيارات (4 حقول) *</FieldLabel>
            <div className="space-y-2">
              {choices.map((c, i) => (
                <TextInput
                  key={i}
                  value={c}
                  onChange={v => updateChoice(i, v)}
                  placeholder={`الخيار ${i + 1}`}
                />
              ))}
            </div>
          </div>

          <div>
            <FieldLabel>الإجابة الصحيحة *</FieldLabel>
            <SelectInput value={correctAnswer} onChange={setCorrectAnswer}>
              <option value="">-- اختر الإجابة الصحيحة --</option>
              {choices.filter(c => c.trim()).map((c, i) => (
                <option key={i} value={c.trim()}>{c.trim()}</option>
              ))}
            </SelectInput>
          </div>
        </>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <FieldLabel>النقاط</FieldLabel>
          <TextInput type="number" value={scoreValue} onChange={v => setScoreValue(v)} placeholder="10" min="1" />
        </div>
        <div>
          <FieldLabel>الصعوبة</FieldLabel>
          <SelectInput value={difficulty} onChange={setDifficulty}>
            <option value="easy">سهل</option>
            <option value="medium">متوسط</option>
            <option value="hard">صعب</option>
          </SelectInput>
        </div>
      </div>

      <ModalActions onCancel={onClose} onSubmit={handleSubmit} submitLabel={isEdit ? 'حفظ التعديلات' : 'إنشاء السؤال'} submitting={submitting} />
    </ModalOverlay>
  )
}

// ─── Create Quiz Session Modal ────────────────────────────────────────────────
function CreateSessionModal({ groups, onClose, onSuccess }) {
  const [title, setTitle] = useState('')
  const [sourceGroupId, setSourceGroupId] = useState('')
  const [answerDuration, setAnswerDuration] = useState(30)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit() {
    if (!title.trim()) { setError('عنوان الجلسة مطلوب'); return }
    if (!sourceGroupId) { setError('اختر مجموعة الأسئلة'); return }
    setSubmitting(true); setError(null)
    try {
      await apiFetch('/api/admin/quiz-sessions', {
        method: 'POST',
        body: JSON.stringify({
          competition_id: ACTIVE_COMPETITION_ID,
          title: title.trim(),
          source_group_id: sourceGroupId,
          answer_duration_seconds: Number(answerDuration),
        }),
      })
      onSuccess('تم إنشاء الجلسة بنجاح')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalOverlay onClose={onClose}>
      <ModalTitle icon="lucide:play-circle">إنشاء جلسة اختبار</ModalTitle>
      {error && <div className="bg-brand-danger/10 text-brand-danger px-3 py-2 rounded-xl text-sm font-bold">{error}</div>}

      <div>
        <FieldLabel>عنوان الجلسة *</FieldLabel>
        <TextInput value={title} onChange={setTitle} placeholder="مثال: اختبار الجولة الأولى" />
      </div>

      <div>
        <FieldLabel>مجموعة الأسئلة *</FieldLabel>
        <SelectInput value={sourceGroupId} onChange={setSourceGroupId}>
          <option value="">-- اختر المجموعة --</option>
          {groups?.map(g => <option key={g.id} value={g.id}>{g.title} ({g.question_count} سؤال)</option>)}
        </SelectInput>
      </div>

      <div>
        <FieldLabel>مدة الإجابة (ثانية)</FieldLabel>
        <TextInput type="number" value={answerDuration} onChange={v => setAnswerDuration(v)} placeholder="30" min="5" />
      </div>

      <ModalActions onCancel={onClose} onSubmit={handleSubmit} submitLabel="إنشاء الجلسة" submitting={submitting} />
    </ModalOverlay>
  )
}

// ─── Main Page Component ──────────────────────────────────────────────────────
export default function AdminQuizPage() {
  const [tab, setTab] = useState('sessions') // 'sessions' | 'questions' | 'groups'
  const { data: sessions, loading: loadingSessions, refetch: refetchSessions } = useAdminData('/api/admin/quiz-sessions')
  const { data: questions, loading: loadingQuestions, refetch: refetchQuestions } = useAdminData('/api/admin/questions')
  const { data: groups, loading: loadingGroups, refetch: refetchGroups } = useAdminData('/api/admin/questions/groups')
  const [actionMsg, setActionMsg] = useState(null)

  // Modal states
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const [showCreateQuestion, setShowCreateQuestion] = useState(false)
  const [editingQuestion, setEditingQuestion] = useState(null) // question object or null
  const [deletingQuestion, setDeletingQuestion] = useState(null) // question object or null
  const [showCreateSession, setShowCreateSession] = useState(false)
  const [deletingSession, setDeletingSession] = useState(null) // session object or null
  const [isDeleting, setIsDeleting] = useState(false)
  const [editingGroup, setEditingGroup] = useState(null) // group object for inline editing
  const [editGroupTitle, setEditGroupTitle] = useState('')
  const [editGroupDesc, setEditGroupDesc] = useState('')
  const [savingGroup, setSavingGroup] = useState(false)

  function showSuccess(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 2500)
  }

  async function handleSessionStatusChange(sessionId, newStatus) {
    try {
      await apiFetch(`/api/admin/quiz-sessions/${sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      showSuccess('تم تحديث الجلسة')
      refetchSessions()
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
      setTimeout(() => setActionMsg(null), 3000)
    }
  }

  async function handleDeleteQuestion() {
    if (!deletingQuestion) return
    setIsDeleting(true)
    try {
      await apiFetch(`/api/admin/questions/${deletingQuestion.id}`, { method: 'DELETE' })
      setDeletingQuestion(null)
      showSuccess('تم حذف السؤال')
      refetchQuestions()
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
      setTimeout(() => setActionMsg(null), 3000)
    } finally {
      setIsDeleting(false)
    }
  }

  async function handleDeleteSession() {
    if (!deletingSession) return
    setIsDeleting(true)
    try {
      await apiFetch(`/api/admin/quiz-sessions/${deletingSession.id}`, { method: 'DELETE' })
      setDeletingSession(null)
      showSuccess('تم إلغاء الجلسة')
      refetchSessions()
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
      setTimeout(() => setActionMsg(null), 3000)
    } finally {
      setIsDeleting(false)
    }
  }

  function handleGroupCreated(msg) {
    setShowCreateGroup(false)
    showSuccess(msg)
    refetchGroups()
  }

  function handleQuestionSaved(msg) {
    setShowCreateQuestion(false)
    setEditingQuestion(null)
    showSuccess(msg)
    refetchQuestions()
  }

  function handleSessionCreated(msg) {
    setShowCreateSession(false)
    showSuccess(msg)
    refetchSessions()
  }

  function openEditGroup(group) {
    setEditingGroup(group)
    setEditGroupTitle(group.title)
    setEditGroupDesc(group.description || '')
  }

  async function handleSaveGroup() {
    if (!editingGroup || !editGroupTitle.trim()) return
    setSavingGroup(true)
    try {
      await apiFetch(`/api/admin/questions/groups/${editingGroup.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: editGroupTitle.trim(), description: editGroupDesc.trim() || undefined }),
      })
      setEditingGroup(null)
      showSuccess('تم تعديل المجموعة')
      refetchGroups()
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
      setTimeout(() => setActionMsg(null), 3000)
    } finally {
      setSavingGroup(false)
    }
  }

  async function handleArchiveGroup(groupId) {
    try {
      await apiFetch(`/api/admin/questions/groups/${groupId}`, { method: 'DELETE' })
      showSuccess('تم أرشفة المجموعة')
      refetchGroups()
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
      setTimeout(() => setActionMsg(null), 3000)
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
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>{actionMsg}</div>
      )}

      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
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

        {/* Create Buttons */}
        {tab === 'sessions' && <CreateButton icon="lucide:plus" label="إنشاء جلسة" onClick={() => setShowCreateSession(true)} />}
        {tab === 'questions' && <CreateButton icon="lucide:plus" label="إنشاء سؤال" onClick={() => setShowCreateQuestion(true)} />}
        {tab === 'groups' && <CreateButton icon="lucide:plus" label="إنشاء مجموعة" onClick={() => setShowCreateGroup(true)} />}
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
                  <button
                    onClick={() => setDeletingSession(s)}
                    className="px-3 py-1 rounded-lg text-xs font-bold text-brand-danger hover:bg-brand-danger/10 smooth-transition flex items-center gap-1"
                  >
                    <iconify-icon icon="lucide:trash-2" class="text-xs"></iconify-icon>
                    إلغاء
                  </button>
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
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">النوع</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الصعوبة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">النقاط</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الإجابة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الحالة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {questions?.map(q => (
                  <tr key={q.id} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="px-4 py-3">
                      <div className="font-bold text-gray-900 dark:text-white max-w-md truncate">{q.prompt}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${q.question_type === 'true_false' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600' : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600'}`}>
                        {q.question_type === 'true_false' ? 'صح/خطأ' : 'متعدد'}
                      </span>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={q.difficulty} /></td>
                    <td className="px-4 py-3 font-heading font-black text-gray-900 dark:text-white">{q.score_value}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{q.correct_answer?.answer}</td>
                    <td className="px-4 py-3"><StatusBadge status={q.status} /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setEditingQuestion(q)}
                          className="p-1.5 rounded-lg text-brand-teal hover:bg-brand-teal/10 smooth-transition"
                          title="تعديل"
                        >
                          <iconify-icon icon="lucide:edit" class="text-base"></iconify-icon>
                        </button>
                        <button
                          onClick={() => setDeletingQuestion(q)}
                          className="p-1.5 rounded-lg text-brand-danger hover:bg-brand-danger/10 smooth-transition"
                          title="حذف"
                        >
                          <iconify-icon icon="lucide:trash-2" class="text-base"></iconify-icon>
                        </button>
                      </div>
                    </td>
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
              {editingGroup?.id === g.id ? (
                /* Inline Edit Mode */
                <div className="space-y-3">
                  <input
                    type="text"
                    value={editGroupTitle}
                    onChange={e => setEditGroupTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                    placeholder="عنوان المجموعة"
                  />
                  <input
                    type="text"
                    value={editGroupDesc}
                    onChange={e => setEditGroupDesc(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-teal/30"
                    placeholder="الوصف (اختياري)"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleSaveGroup}
                      disabled={savingGroup}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-brand-teal text-white hover:bg-brand-teal-hover smooth-transition disabled:opacity-50"
                    >
                      {savingGroup && <iconify-icon icon="lucide:loader-2" class="text-xs animate-spin"></iconify-icon>}
                      <iconify-icon icon="lucide:check" class="text-xs"></iconify-icon>
                      حفظ
                    </button>
                    <button
                      onClick={() => setEditingGroup(null)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
                    >
                      إلغاء
                    </button>
                  </div>
                </div>
              ) : (
                /* Display Mode */
                <>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-heading font-black text-gray-900 dark:text-white">{g.title}</h3>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={g.status} />
                      <button
                        onClick={() => openEditGroup(g)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-brand-teal hover:bg-brand-teal/10 smooth-transition"
                        title="تعديل"
                      >
                        <iconify-icon icon="lucide:pencil" class="text-sm"></iconify-icon>
                      </button>
                      {g.status !== 'archived' && (
                        <button
                          onClick={() => handleArchiveGroup(g.id)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-brand-danger hover:bg-brand-danger/10 smooth-transition"
                          title="أرشفة"
                        >
                          <iconify-icon icon="lucide:archive" class="text-sm"></iconify-icon>
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-gray-500 mb-3">{g.description}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span>{g.question_count} سؤال</span>
                  </div>
                </>
              )}
            </div>
          ))}
          {(!groups || groups.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold col-span-2">لا توجد مجموعات</div>
          )}
        </div>
      )}

      {/* ─── Modals ─────────────────────────────────────────────────────────── */}

      {showCreateGroup && (
        <CreateGroupModal onClose={() => setShowCreateGroup(false)} onSuccess={handleGroupCreated} />
      )}

      {showCreateQuestion && (
        <QuestionModal groups={groups} onClose={() => setShowCreateQuestion(false)} onSuccess={handleQuestionSaved} />
      )}

      {editingQuestion && (
        <QuestionModal question={editingQuestion} groups={groups} onClose={() => setEditingQuestion(null)} onSuccess={handleQuestionSaved} />
      )}

      {deletingQuestion && (
        <ConfirmDeleteModal
          title="حذف السؤال"
          message={`هل أنت متأكد من حذف السؤال "${deletingQuestion.prompt}"؟ سيتم أرشفة السؤال.`}
          onCancel={() => setDeletingQuestion(null)}
          onConfirm={handleDeleteQuestion}
          deleting={isDeleting}
        />
      )}

      {showCreateSession && (
        <CreateSessionModal groups={groups} onClose={() => setShowCreateSession(false)} onSuccess={handleSessionCreated} />
      )}

      {deletingSession && (
        <ConfirmDeleteModal
          title="إلغاء الجلسة"
          message={`هل أنت متأكد من إلغاء الجلسة "${deletingSession.title}"؟`}
          onCancel={() => setDeletingSession(null)}
          onConfirm={handleDeleteSession}
          deleting={isDeleting}
        />
      )}
    </div>
  )
}
