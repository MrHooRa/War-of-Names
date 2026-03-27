import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import useQuiz from '../hooks/useQuiz'
import useSubmitAnswer from '../hooks/useSubmitAnswer'

const OPTION_LETTERS = ['أ', 'ب', 'ج', 'د']

export default function QuizPage() {
  const { quiz, loading, error } = useQuiz()
  const { submitting, result: answerResult, submitAnswer } = useSubmitAnswer()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedOption, setSelectedOption] = useState(null)
  const [totalEarned, setTotalEarned] = useState(0)
  const [answered, setAnswered] = useState({})
  const [timer, setTimer] = useState(-1)
  const [timedOut, setTimedOut] = useState(false)
  const timerRef = useRef(null)

  const questions = quiz?.questions ?? []
  const totalQuestions = questions.length

  // Seed answered state from server-reported already_answered flags & skip to first unanswered
  useEffect(() => {
    if (!questions.length) return
    const preAnswered = {}
    let firstUnanswered = questions.length // default: all done
    for (let i = 0; i < questions.length; i++) {
      if (questions[i].already_answered) {
        preAnswered[questions[i].session_question_id] = { is_correct: null, points_awarded: 0, pre_answered: true }
      } else if (firstUnanswered === questions.length) {
        firstUnanswered = i
      }
    }
    if (Object.keys(preAnswered).length > 0) {
      setAnswered(prev => ({ ...preAnswered, ...prev }))
      setCurrentIndex(firstUnanswered)
    }
  }, [questions.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const currentQ = questions[currentIndex]

  // Timer countdown
  useEffect(() => {
    if (!currentQ || answered[currentQ.session_question_id]) return
    setTimedOut(false)
    const duration = quiz?.answer_duration_seconds || 30
    setTimer(duration)
    timerRef.current = setInterval(() => {
      setTimer(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current)
  }, [currentIndex, currentQ, answered, quiz?.answer_duration_seconds])

  // Auto-advance when time runs out
  useEffect(() => {
    if (timer !== 0 || !currentQ || answered[currentQ.session_question_id] || timedOut) return
    setTimedOut(true)
    const autoAdvanceTimer = setTimeout(() => {
      handleNext()
    }, 2000)
    return () => clearTimeout(autoAdvanceTimer)
  }, [timer, currentQ, answered, timedOut]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAnswer(option) {
    if (!currentQ || submitting || answered[currentQ.session_question_id] || timedOut) return
    setSelectedOption(option)
    clearInterval(timerRef.current)

    const data = await submitAnswer(quiz.session_id, currentQ.session_question_id, option)
    if (data) {
      setAnswered(prev => ({ ...prev, [currentQ.session_question_id]: data }))
      if (data.is_correct) {
        setTotalEarned(prev => prev + data.points_awarded)
      }
    }
  }

  function handleNext() {
    setTimedOut(false)
    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex(prev => prev + 1)
      setSelectedOption(null)
    } else {
      // Last question — advance past to show completion screen
      setCurrentIndex(totalQuestions)
    }
  }

  // No quiz
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal dark:text-brand-slate animate-spin"></iconify-icon>
      </div>
    )
  }

  if (error || !quiz) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20 gap-4">
        <iconify-icon icon="lucide:book-x" class="text-5xl text-gray-300 dark:text-gray-700"></iconify-icon>
        <p className="text-gray-500 dark:text-gray-400 font-bold">{error || 'لا توجد جلسة أسئلة نشطة حالياً'}</p>
        <Link to="/dashboard" className="text-brand-teal dark:text-brand-slate font-bold hover:underline">العودة للرئيسية</Link>
      </div>
    )
  }

  // Quiz complete
  if (currentIndex >= totalQuestions || (totalQuestions > 0 && Object.keys(answered).length === totalQuestions)) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20 gap-6">
        <div className="relative">
          <div className="absolute inset-0 bg-brand-teal/15 blur-3xl rounded-full"></div>
          <iconify-icon icon="lucide:trophy" class="relative text-7xl text-brand-teal dark:text-brand-slate"></iconify-icon>
        </div>
        <h1 className="font-display text-4xl font-black text-gray-900 dark:text-white">انتهت الجلسة!</h1>
        <p className="text-gray-500 dark:text-gray-400 font-bold text-lg">حصلت على {totalEarned.toLocaleString('ar-SA')} نقطة</p>
        <Link to="/dashboard" className="btn-press bg-brand-teal hover:bg-brand-teal-hover text-white px-8 py-4 rounded-2xl font-heading font-black text-lg shadow-lg smooth-transition">
          العودة للرئيسية
        </Link>
      </div>
    )
  }

  const currentResult = answered[currentQ?.session_question_id]
  const timerPercent = (Math.max(0, timer) / (quiz.answer_duration_seconds || 30)) * 100
  const circumference = 2 * Math.PI * 28

  return (
    <div className="flex-1 flex flex-col items-center justify-center w-full max-w-4xl mx-auto px-4 py-6 md:py-12">

      {/* Progress & Score */}
      <div className="w-full mb-10">
        <div className="flex justify-between items-end mb-4">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-black text-gray-500 dark:text-gray-500 uppercase tracking-widest">التقدم</span>
            <div className="font-heading text-2xl font-black text-gray-900 dark:text-white">
              السؤال {String(currentIndex + 1).padStart(2, '0')} <span className="text-gray-400 dark:text-gray-600 font-bold text-lg">/ {String(totalQuestions).padStart(2, '0')}</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-[10px] font-black text-gray-500 dark:text-gray-500 uppercase tracking-widest">النقاط المكتسبة</span>
            <div className="flex items-center gap-2 text-brand-teal dark:text-brand-slate">
              <span className="font-display text-2xl font-black">+{totalEarned.toLocaleString('ar-SA')}</span>
              <iconify-icon icon="lucide:zap" class="text-2xl"></iconify-icon>
            </div>
          </div>
        </div>
        <div className="h-3 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full bg-brand-teal dark:bg-brand-slate rounded-full progress-glow smooth-transition" style={{ width: `${((currentIndex + 1) / totalQuestions) * 100}%` }}></div>
        </div>
      </div>

      {/* Question Card */}
      <div className="w-full relative">
        {/* Timer */}
        {!currentResult && !timedOut && (
          <div className="absolute -top-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center">
            <div className="relative w-16 h-16 bg-white dark:bg-brand-card-dark rounded-full shadow-md border-2 border-gray-300 dark:border-gray-700 flex items-center justify-center">
              <svg className="absolute inset-0 w-full h-full -rotate-90">
                <circle cx="32" cy="32" r="28" fill="transparent" stroke="currentColor" strokeWidth="4" className="text-gray-200 dark:text-gray-800" />
                <circle
                  cx="32" cy="32" r="28" fill="transparent" stroke="currentColor" strokeWidth="4" strokeLinecap="round"
                  className="text-brand-teal"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference - (circumference * timerPercent) / 100}
                  style={{ transition: 'stroke-dashoffset 1s linear' }}
                />
              </svg>
              <span className="font-display text-xl font-black text-gray-900 dark:text-white">{Math.max(0, timer)}</span>
            </div>
          </div>
        )}

        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-3xl shadow-xl p-8 md:p-14 text-center pt-16">
          <h2 className="font-display text-2xl md:text-3xl font-black text-gray-900 dark:text-white leading-relaxed mb-10">
            {currentQ.prompt}
          </h2>

          {/* Options Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {currentQ.options.map((option, i) => {
              const isSelected = selectedOption === option
              const isCorrect = currentResult?.correct_answer === option
              const isWrong = currentResult && isSelected && !currentResult.is_correct

              let classes = 'bg-white dark:bg-gray-800/50 border-2 border-gray-200 dark:border-gray-700 hover:border-brand-teal dark:hover:border-brand-slate hover:bg-gray-50 dark:hover:bg-gray-800'
              let letterClasses = 'bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-500'

              if (currentResult) {
                if (isCorrect) {
                  classes = 'bg-brand-success/5 border-2 border-brand-success'
                  letterClasses = 'bg-brand-success border-brand-success text-white'
                } else if (isWrong) {
                  classes = 'bg-brand-danger/5 border-2 border-brand-danger'
                  letterClasses = 'bg-brand-danger border-brand-danger text-white'
                } else {
                  classes = 'bg-gray-50 dark:bg-gray-800/30 border-2 border-gray-100 dark:border-gray-800 opacity-50'
                }
              } else if (isSelected) {
                classes = 'bg-brand-teal/5 dark:bg-brand-slate/10 border-2 border-brand-teal dark:border-brand-slate'
                letterClasses = 'bg-brand-teal dark:bg-brand-slate border-brand-teal dark:border-brand-slate text-white'
              }

              return (
                <button
                  key={i}
                  onClick={() => handleAnswer(option)}
                  disabled={!!currentResult || submitting || timedOut}
                  className={`btn-press group relative flex items-center justify-between p-5 rounded-2xl smooth-transition text-right shadow-sm ${classes} disabled:cursor-default`}
                >
                  <span className={`font-heading text-lg font-bold ${currentResult && isCorrect ? 'text-brand-success' : currentResult && isWrong ? 'text-brand-danger' : 'text-gray-800 dark:text-gray-300'}`}>
                    {option}
                  </span>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold smooth-transition ${letterClasses}`}>
                    {currentResult && isCorrect ? (
                      <iconify-icon icon="lucide:check" class="text-sm"></iconify-icon>
                    ) : currentResult && isWrong ? (
                      <iconify-icon icon="lucide:x" class="text-sm"></iconify-icon>
                    ) : (
                      OPTION_LETTERS[i]
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Timed out feedback */}
      {timedOut && !currentResult && (
        <div className="mt-8 flex flex-col items-center gap-4">
          <div className="flex items-center gap-3 text-amber-500 font-heading font-black text-xl">
            <iconify-icon icon="lucide:timer-off" class="text-2xl"></iconify-icon>
            انتهى الوقت!
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 font-bold">سيتم الانتقال للسؤال التالي تلقائياً...</p>
        </div>
      )}

      {/* Next / Result feedback */}
      {currentResult && (
        <div className="mt-8 flex flex-col items-center gap-4">
          {currentResult.is_correct ? (
            <div className="flex items-center gap-3 text-brand-success font-heading font-black text-xl">
              <iconify-icon icon="lucide:award" class="text-2xl"></iconify-icon>
              إجابة صحيحة! +{currentResult.points_awarded} نقطة
            </div>
          ) : (
            <div className="flex items-center gap-3 text-brand-danger font-heading font-black text-xl">
              <iconify-icon icon="lucide:x-circle" class="text-2xl"></iconify-icon>
              إجابة خاطئة! الإجابة الصحيحة: {currentResult.correct_answer}
            </div>
          )}

          {currentIndex < totalQuestions - 1 ? (
            <button
              onClick={handleNext}
              className="btn-press bg-brand-teal hover:bg-brand-teal-hover text-white px-12 py-4 rounded-2xl font-heading font-black text-xl shadow-lg hover:shadow-brand-teal/20 flex items-center gap-3 smooth-transition"
            >
              <span>السؤال التالي</span>
              <iconify-icon icon="lucide:arrow-left"></iconify-icon>
            </button>
          ) : (
            <Link
              to="/dashboard"
              className="btn-press bg-brand-teal hover:bg-brand-teal-hover text-white px-12 py-4 rounded-2xl font-heading font-black text-xl shadow-lg hover:shadow-brand-teal/20 flex items-center gap-3 smooth-transition"
            >
              <span>إنهاء الجلسة</span>
              <iconify-icon icon="lucide:check-circle" class="text-xl"></iconify-icon>
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
