/**
 * MainPage — The real game gateway (00-Main Page).
 *
 * Auth-aware entry point:
 *  - Not logged in → immersive splash with login/register CTAs
 *  - Logged in, no memberships → inline join-competition flow
 *  - Logged in, 1 active membership → auto-navigate to /lobby
 *  - Logged in, multiple memberships → server selection screen
 *
 * Always rendered at "/". No sessionStorage skip logic.
 */

import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import { apiFetch } from '../lib/api'

const LOGO_URL =
  'https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/bg-removed/d4b11575-1b23-40b6-85e7-6036632e88ce.png'

/* ── Background visual layer (shared by all states) ── */
function ImmersiveBackground({ centerGlowRef }) {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(21,27,41,1)_0%,rgba(10,13,20,1)_100%)]"></div>
      <div className="absolute inset-0 hex-bg opacity-30"></div>
      <div className="absolute top-0 -right-[5%] w-[700px] h-[700px] opacity-10 bg-shape">
        <svg viewBox="0 0 100 100" className="w-full h-full text-brand-teal fill-current drop-shadow-[0_0_80px_rgba(11,138,141,1)]">
          <polygon points="50 1, 93.3 25, 93.3 75, 50 99, 6.7 75, 6.7 25" />
        </svg>
      </div>
      <div className="absolute bottom-[-10%] -left-[10%] w-[900px] h-[900px] opacity-[0.08] bg-shape-reverse">
        <svg viewBox="0 0 100 100" className="w-full h-full text-brand-orange fill-current drop-shadow-[0_0_100px_rgba(216,67,21,1)]">
          <polygon points="50 1, 93.3 25, 93.3 75, 50 99, 6.7 75, 6.7 25" />
        </svg>
      </div>
      <div
        ref={centerGlowRef}
        className="absolute top-[35%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] blur-[120px] rounded-full trans-mid"
        style={{ backgroundColor: 'rgba(11, 138, 141, 0.1)' }}
      ></div>
    </div>
  )
}

/* ── Header strip (status + icons) ── */
function MinimalHeader({ isAuthenticated, onLogout, username }) {
  return (
    <header
      className="relative z-30 w-full p-6 flex justify-between items-center pointer-events-none"
      style={{ opacity: 0, animation: 'slideDownFade 0.5s ease 0.5s forwards' }}
    >
      <div className="flex items-center gap-3 bg-brand-surface/60 backdrop-blur-md px-5 py-2.5 rounded-2xl border border-white/5 shadow-lg pointer-events-auto">
        <div className="w-2.5 h-2.5 rounded-full bg-brand-emerald animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.8)]"></div>
        <span className="text-sm font-bold text-gray-200 tracking-wide">المركز الرئيسي متصل</span>
      </div>
      <div className="flex gap-4 pointer-events-auto">
        {isAuthenticated && (
          <>
            <span className="flex items-center gap-2 text-sm text-gray-400 font-bold">
              <iconify-icon icon="lucide:user" class="text-lg text-brand-teal"></iconify-icon>
              {username}
            </span>
            <button
              onClick={onLogout}
              className="w-12 h-12 flex items-center justify-center rounded-2xl bg-brand-surface/60 border border-white/5 text-gray-300 hover:text-white hover:border-brand-danger/50 transition-colors backdrop-blur-md"
              title="تسجيل الخروج"
            >
              <iconify-icon icon="lucide:log-out" class="text-xl"></iconify-icon>
            </button>
          </>
        )}
      </div>
    </header>
  )
}

/* ── State: Guest splash (not logged in) ── */
function GuestView({ ctaBtnRef, centerGlowRef }) {
  const navigate = useNavigate()

  useEffect(() => {
    const btn = ctaBtnRef.current
    const glow = centerGlowRef.current
    if (!btn) return
    const onEnter = () => {
      document.body.classList.add('lobby-active')
      if (glow) glow.style.backgroundColor = 'rgba(216, 67, 21, 0.25)'
    }
    const onLeave = () => {
      document.body.classList.remove('lobby-active')
      if (glow) glow.style.backgroundColor = 'rgba(11, 138, 141, 0.1)'
    }
    btn.addEventListener('mouseenter', onEnter)
    btn.addEventListener('mouseleave', onLeave)
    return () => {
      btn.removeEventListener('mouseenter', onEnter)
      btn.removeEventListener('mouseleave', onLeave)
      document.body.classList.remove('lobby-active')
    }
  }, [ctaBtnRef, centerGlowRef])

  return (
    <>
      {/* Top badge */}
      <div
        className="inline-flex items-center gap-2 bg-brand-orange/10 border border-brand-orange/30 text-brand-orange px-5 py-2 rounded-full text-sm font-bold mb-8 shadow-[0_0_15px_rgba(216,67,21,0.2)]"
        style={{ opacity: 0, animation: 'slideDownFade 0.5s ease 0.8s forwards' }}
      >
        <span className="text-lg leading-none">أقوى لعبة تنافسية لعام 2026</span>
      </div>

      {/* Mega CTA — Login */}
      <div
        className="relative w-full sm:w-auto z-40"
        style={{ opacity: 0, animation: 'fadeInScale 0.8s cubic-bezier(0.16,1,0.3,1) 1s forwards' }}
      >
        <iconify-icon icon="mdi:star-four-points" class="absolute -top-6 -left-8 text-amber-300 text-3xl animate-float-slow drop-shadow-[0_0_10px_rgba(252,211,77,0.8)]"></iconify-icon>
        <iconify-icon icon="mdi:star-four-points" class="absolute top-1/2 -right-10 text-brand-teal-light-lobby text-2xl animate-float-fast drop-shadow-[0_0_10px_rgba(0,217,233,0.8)]"></iconify-icon>
        <iconify-icon icon="mdi:sparkles" class="absolute -bottom-4 -left-4 text-brand-orange text-xl animate-float-medium drop-shadow-[0_0_10px_rgba(216,67,21,0.8)]"></iconify-icon>

        <button
          ref={ctaBtnRef}
          onClick={() => navigate('/login')}
          className="btn-mega-cta relative block w-full sm:w-[450px] overflow-hidden rounded-[2rem] bg-gradient-to-br from-brand-teal to-brand-orange p-[2px] focus:outline-none focus:ring-4 focus:ring-brand-orange/50 transition-all duration-300 hover:scale-[1.08] active:scale-95 group cursor-pointer border-0"
        >
          <div className="absolute inset-0 rounded-[2rem] glow-pulse opacity-70 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="relative h-full w-full bg-gradient-to-br from-[#0B8A8D] to-[#D84315] rounded-[calc(2rem-2px)] px-12 py-6 flex flex-col items-center justify-center gap-2 overflow-hidden float-animation">
            <div className="absolute inset-0 w-[200%] h-full shimmer-effect pointer-events-none"></div>
            <div className="relative z-10 flex items-center justify-center gap-4 text-white">
              <iconify-icon icon="mdi:rocket" class="text-4xl drop-shadow-lg group-hover:-translate-y-1 group-hover:translate-x-1 transition-transform duration-300"></iconify-icon>
              <span className="font-heading font-black text-3xl md:text-4xl tracking-wide drop-shadow-md">ابدأ اللعبة الآن</span>
            </div>
          </div>
        </button>
      </div>

      {/* Secondary link — register */}
      <div
        className="mt-8 flex flex-col items-center gap-4"
        style={{ animation: 'slideUpFade 0.8s ease 1.2s forwards', opacity: 0 }}
      >
        <p className="text-gray-400 text-sm font-bold">
          ليس لديك حساب؟{' '}
          <Link to="/register" className="text-brand-teal hover:text-white transition-colors font-black underline underline-offset-4">
            سجّل الآن
          </Link>
        </p>
      </div>
    </>
  )
}

/* ── State: Logged in but no memberships — inline join ── */
function JoinView() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ invite_code: '', alias: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleJoin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await apiFetch('/api/join', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      navigate('/lobby', { replace: true })
    } catch (err) {
      // Parse structured error if available
      const detail = err.data
      if (detail && detail.message) {
        setError(detail.message)
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="w-full max-w-lg"
      style={{ opacity: 0, animation: 'fadeInScale 0.6s cubic-bezier(0.16,1,0.3,1) 0.6s forwards' }}
    >
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 md:p-10 shadow-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-brand-teal/20 text-brand-teal rounded-2xl mb-4">
            <iconify-icon icon="lucide:swords" class="text-3xl"></iconify-icon>
          </div>
          <h2 className="font-heading font-black text-2xl text-white mb-2">انضم للمنافسة</h2>
          <p className="text-gray-400 font-bold text-sm">أدخل كود الدعوة واختر لقبك القتالي</p>
        </div>

        <form onSubmit={handleJoin} className="space-y-5">
          {/* Invite Code */}
          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-300 mr-1">كود الدعوة</label>
            <div className="relative">
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500">
                <iconify-icon icon="lucide:key" class="text-lg"></iconify-icon>
              </span>
              <input
                type="text"
                value={form.invite_code}
                onChange={e => setForm(f => ({ ...f, invite_code: e.target.value }))}
                placeholder="مثال: WAR2026"
                required
                className="w-full bg-white/5 border border-white/10 py-3.5 pr-11 pl-4 rounded-xl font-bold tracking-widest uppercase focus:outline-none focus:ring-2 focus:ring-brand-teal/40 focus:border-brand-teal transition-all text-white placeholder:text-gray-500 placeholder:tracking-normal placeholder:normal-case"
              />
            </div>
          </div>

          {/* Alias */}
          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-300 mr-1">اللقب القتالي</label>
            <div className="relative">
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500">
                <iconify-icon icon="lucide:user" class="text-lg"></iconify-icon>
              </span>
              <input
                type="text"
                value={form.alias}
                onChange={e => setForm(f => ({ ...f, alias: e.target.value }))}
                placeholder="اختر لقبك..."
                required
                className="w-full bg-white/5 border border-white/10 py-3.5 pr-11 pl-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/40 focus:border-brand-teal transition-all text-white placeholder:text-gray-500"
              />
            </div>
            <p className="text-[10px] text-gray-500 mr-2">سيظهر هذا اللقب للمنافسين — لا أحد يعرف من أنت!</p>
          </div>

          {error && (
            <p className="text-brand-danger text-sm font-bold text-center py-3 bg-red-500/10 rounded-xl border border-red-500/20">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-press w-full bg-gradient-to-r from-brand-teal to-brand-teal-hover hover:from-brand-teal-hover hover:to-brand-teal text-white py-4 rounded-xl font-heading font-black text-lg shadow-lg shadow-brand-teal/20 flex items-center justify-center gap-3 transition-all disabled:opacity-60"
          >
            {loading ? (
              <>
                <iconify-icon icon="lucide:loader-2" class="text-xl animate-spin"></iconify-icon>
                جارٍ الانضمام...
              </>
            ) : (
              <>
                <iconify-icon icon="lucide:swords" class="text-xl"></iconify-icon>
                انضمام للحرب
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

/* ── State: Multiple memberships — server selection ── */
function ServerSelectView({ memberships, onJoinAnother }) {
  const navigate = useNavigate()

  const activeMemberships = memberships.filter(m => m.status === 'active')
  const inactiveMemberships = memberships.filter(m => m.status !== 'active')

  function enterCompetition(membership) {
    // Store selected competition context then navigate
    localStorage.setItem('won_active_competition', membership.competition_id)
    navigate('/lobby', { replace: true })
  }

  return (
    <div
      className="w-full max-w-2xl"
      style={{ opacity: 0, animation: 'fadeInScale 0.6s cubic-bezier(0.16,1,0.3,1) 0.6s forwards' }}
    >
      <div className="text-center mb-8">
        <h2 className="font-heading font-black text-2xl text-white mb-2">اختر الخادم</h2>
        <p className="text-gray-400 font-bold text-sm">اختر المنافسة التي تريد الدخول إليها</p>
      </div>

      <div className="space-y-4">
        {activeMemberships.map(m => (
          <button
            key={m.membership_id}
            onClick={() => enterCompetition(m)}
            className="w-full bg-white/5 backdrop-blur-xl border border-white/10 hover:border-brand-teal/40 rounded-2xl p-6 text-right transition-all group cursor-pointer"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-heading font-black text-lg text-white group-hover:text-brand-teal transition-colors">
                  {m.competition_name}
                </h3>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                  <span className="flex items-center gap-1.5">
                    <iconify-icon icon="lucide:user" class="text-brand-teal"></iconify-icon>
                    {m.alias}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <iconify-icon icon="lucide:coins" class="text-amber-400"></iconify-icon>
                    {m.balance?.toLocaleString()} نقطة
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-brand-emerald shadow-[0_0_8px_rgba(16,185,129,0.6)]"></span>
                <iconify-icon icon="lucide:chevron-left" class="text-2xl text-gray-500 group-hover:text-brand-teal transition-colors"></iconify-icon>
              </div>
            </div>
          </button>
        ))}

        {inactiveMemberships.map(m => (
          <div
            key={m.membership_id}
            className="w-full bg-white/5 backdrop-blur-xl border border-white/5 rounded-2xl p-6 text-right opacity-50"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-heading font-bold text-lg text-gray-400">
                  {m.competition_name}
                </h3>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span>{m.alias}</span>
                  <span className="bg-gray-700 px-2 py-0.5 rounded text-xs font-bold">
                    {m.status === 'suspended' ? 'معلّق' : m.status === 'removed' ? 'مُزال' : m.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Join another competition */}
      <div className="mt-8 text-center">
        <button
          onClick={onJoinAnother}
          className="inline-flex items-center gap-2 text-brand-teal font-bold text-sm hover:underline transition-colors"
        >
          <iconify-icon icon="lucide:plus" class="text-lg"></iconify-icon>
          انضمام لمنافسة أخرى
        </button>
      </div>
    </div>
  )
}

/* ── Main Page Component ── */
export default function MainPage() {
  const navigate = useNavigate()
  const { isAuthenticated, logout, currentUser } = useAuth()
  const ctaBtnRef = useRef(null)
  const centerGlowRef = useRef(null)

  const [memberships, setMemberships] = useState(null) // null = loading, [] = none
  const [checkingMemberships, setCheckingMemberships] = useState(true)
  const [showJoinForm, setShowJoinForm] = useState(false)

  // If logged in, check memberships
  useEffect(() => {
    if (!isAuthenticated) {
      setCheckingMemberships(false)
      return
    }

    apiFetch('/api/me/memberships')
      .then(json => {
        const mems = json.data || []
        setMemberships(mems)

        // Auto-navigate if user has exactly 1 active membership
        const activeMems = mems.filter(m => m.status === 'active')
        if (activeMems.length === 1) {
          localStorage.setItem('won_active_competition', activeMems[0].competition_id)
          navigate('/lobby', { replace: true })
        }
      })
      .catch(() => {
        setMemberships([])
      })
      .finally(() => setCheckingMemberships(false))
  }, [isAuthenticated, navigate])

  function handleLogout() {
    localStorage.removeItem('won_active_competition')
    logout()
    navigate('/', { replace: true })
  }

  // Loading state while checking memberships
  if (isAuthenticated && checkingMemberships) {
    return (
      <div className="min-h-screen flex flex-col relative" style={{ backgroundColor: '#0a0d14', color: '#FFFFFF' }}>
        <ImmersiveBackground centerGlowRef={centerGlowRef} />
        <div className="relative z-20 flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <img src={LOGO_URL} alt="حرب الأسماء" className="h-32 w-auto object-contain animate-pulse" />
            <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
          </div>
        </div>
      </div>
    )
  }

  // Determine which view to show
  const activeMems = (memberships || []).filter(m => m.status === 'active')
  const hasMultiple = activeMems.length > 1
  const hasNone = !memberships || memberships.length === 0 || showJoinForm

  return (
    <div
      className="min-h-screen flex flex-col relative"
      style={{ backgroundColor: '#0a0d14', color: '#FFFFFF', overflowX: 'hidden', WebkitFontSmoothing: 'antialiased' }}
    >
      <ImmersiveBackground centerGlowRef={centerGlowRef} />
      <MinimalHeader
        isAuthenticated={isAuthenticated}
        onLogout={handleLogout}
        username={currentUser?.username}
      />

      <main className="relative z-20 flex-1 flex flex-col items-center justify-center w-full max-w-7xl mx-auto px-4 py-12 md:py-8">
        {/* Central Logo — always shown */}
        <div className="relative flex flex-col items-center z-30 mb-12 md:mb-16">
          <img
            src={LOGO_URL}
            alt="شعار حرب الأسماء"
            className="h-[clamp(7rem,18vw,14rem)] w-auto object-contain object-center animate-fade-in-scale trans-mid will-change-transform"
            style={{ width: 492, height: 244 }}
          />
        </div>

        {/* Content area — depends on auth state */}
        <div className="relative w-full max-w-2xl flex flex-col items-center text-center">
          {!isAuthenticated ? (
            <GuestView ctaBtnRef={ctaBtnRef} centerGlowRef={centerGlowRef} />
          ) : hasMultiple && !showJoinForm ? (
            /* Multiple memberships — show server selection */
            <ServerSelectView
              memberships={memberships}
              onJoinAnother={() => setShowJoinForm(true)}
            />
          ) : memberships && memberships.length > 0 && !activeMems.length && !showJoinForm ? (
            /* Logged in with memberships but none active (all suspended/archived) */
            <div className="w-full max-w-lg" style={{ opacity: 0, animation: 'fadeInScale 0.6s cubic-bezier(0.16,1,0.3,1) 0.6s forwards' }}>
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 md:p-10 shadow-2xl text-center">
                <iconify-icon icon="lucide:lock" class="text-5xl text-gray-400 mb-4"></iconify-icon>
                <h2 className="font-heading font-black text-xl text-white mb-2">العضوية غير نشطة</h2>
                <p className="text-gray-400 font-bold text-sm mb-6">عضويتك في المنافسة معلقة حالياً. تواصل مع المشرف لإعادة التفعيل.</p>
                <button onClick={handleLogout} className="text-sm text-brand-teal font-bold hover:underline">تسجيل الخروج</button>
              </div>
            </div>
          ) : (
            /* No memberships or "join another" clicked — show join flow */
            <JoinView />
          )}
        </div>
      </main>
    </div>
  )
}
