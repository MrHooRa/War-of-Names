import { Link } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import useCompetitionContext from '../hooks/useCompetitionContext'

export default function LobbyPage() {
  const containerRef = useRef(null)
  const centerGlowRef = useRef(null)
  const { seasonName, cycleLabel } = useCompetitionContext()

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const magnets = container.querySelectorAll('.magnetic-wrapper')
    const centerGlow = centerGlowRef.current

    // 1. Magnetic Hover Effect for Buttons
    const magnetHandlers = []

    magnets.forEach((magnet) => {
      const inner = magnet.querySelector('.magnetic-inner')

      const onMouseMove = (e) => {
        const rect = magnet.getBoundingClientRect()
        // Calculate distance from center of element
        const x = e.clientX - rect.left - rect.width / 2
        const y = e.clientY - rect.top - rect.height / 2

        // Apply transform: move slightly towards mouse + lift + scale
        // The max distance is controlled by the multiplier (0.10)
        inner.style.transform = `translate(${x * 0.1}px, ${y * 0.1 - 8}px) scale(1.05)`
      }

      const onMouseLeave = () => {
        // Reset transform
        inner.style.transform = 'translate(0px, 0px) scale(1)'
      }

      magnet.addEventListener('mousemove', onMouseMove)
      magnet.addEventListener('mouseleave', onMouseLeave)

      magnetHandlers.push({ el: magnet, onMouseMove, onMouseLeave })
    })

    // 2. Global Hover Reactions (Surrounding effects & Center Glow)
    const glowColors = {
      teal: 'rgba(11, 138, 141, 0.25)',
      purple: 'rgba(147, 51, 234, 0.25)',
      orange: 'rgba(216, 67, 21, 0.25)',
      blue: 'rgba(59, 130, 246, 0.25)',
    }
    const glowHandlers = []

    magnets.forEach((btn) => {
      const onMouseEnter = () => {
        document.body.classList.add('lobby-active')
        // Enhance background glow based on button's data attribute
        const color = btn.dataset.glowColor
        if (color && glowColors[color]) {
          centerGlow.style.backgroundColor = glowColors[color]
        }
      }

      const onMouseLeaveGlow = () => {
        document.body.classList.remove('lobby-active')
        centerGlow.style.backgroundColor = 'rgba(11, 138, 141, 0.1)' // Reset to default
      }

      btn.addEventListener('mouseenter', onMouseEnter)
      btn.addEventListener('mouseleave', onMouseLeaveGlow)

      glowHandlers.push({ el: btn, onMouseEnter, onMouseLeave: onMouseLeaveGlow })
    })

    // Apply stagger animation to buttons on load
    const staggerTimeout = setTimeout(() => {
      container.querySelectorAll('.magnetic-wrapper').forEach((el) => {
        el.style.opacity = '1'
      })
    }, 100)

    // Cleanup
    return () => {
      clearTimeout(staggerTimeout)
      document.body.classList.remove('lobby-active')

      magnetHandlers.forEach(({ el, onMouseMove, onMouseLeave }) => {
        el.removeEventListener('mousemove', onMouseMove)
        el.removeEventListener('mouseleave', onMouseLeave)
      })

      glowHandlers.forEach(({ el, onMouseEnter, onMouseLeave }) => {
        el.removeEventListener('mouseenter', onMouseEnter)
        el.removeEventListener('mouseleave', onMouseLeave)
      })
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className="min-h-screen flex flex-col relative"
      style={{ backgroundColor: '#0a0d14', color: '#FFFFFF' }}
    >
      {/* Background Visual Zone: Ambient Tavern/Club Vibe */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Warm ambient base */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(21,27,41,1)_0%,rgba(10,13,20,1)_100%)]"></div>

        {/* Main subtle hex grid */}
        <div className="absolute inset-0 hex-bg opacity-30"></div>

        {/* Dynamic Rotating Background Shapes */}
        <div className="absolute top-0 -right-[5%] w-[700px] h-[700px] opacity-10 bg-shape">
          <svg
            viewBox="0 0 100 100"
            className="w-full h-full text-brand-teal fill-current drop-shadow-[0_0_80px_rgba(11,138,141,1)]"
          >
            <polygon points="50 1, 93.3 25, 93.3 75, 50 99, 6.7 75, 6.7 25" />
          </svg>
        </div>
        <div className="absolute bottom-[-10%] -left-[10%] w-[900px] h-[900px] opacity-[0.08] bg-shape-reverse">
          <svg
            viewBox="0 0 100 100"
            className="w-full h-full text-brand-orange fill-current drop-shadow-[0_0_100px_rgba(216,67,21,1)]"
          >
            <polygon points="50 1, 93.3 25, 93.3 75, 50 99, 6.7 75, 6.7 25" />
          </svg>
        </div>

        {/* Center Focus Glow */}
        <div
          ref={centerGlowRef}
          className="absolute top-[35%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-brand-teal/10 blur-[120px] rounded-full trans-mid"
          id="center-glow"
        ></div>
      </div>

      {/* Header (Minimal) */}
      <header className="relative z-30 w-full p-6 flex justify-between items-center opacity-0 animate-[slideDownFade_0.5s_ease_0.5s_forwards] pointer-events-none">
        <div className="flex items-center gap-3 bg-brand-surface/60 backdrop-blur-md px-5 py-2.5 rounded-2xl border border-white/5 shadow-lg pointer-events-auto">
          <div className="w-2.5 h-2.5 rounded-full bg-brand-emerald animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.8)]"></div>
          <span className="text-sm font-bold text-gray-200 tracking-wide">
            {seasonName || 'المركز الرئيسي متصل'}
            {cycleLabel && <span className="text-gray-400 mr-2">— {cycleLabel}</span>}
          </span>
        </div>
        <div className="flex gap-4 pointer-events-auto">
          <Link
            to="/notifications"
            id="nav-notifications-link"
            className="w-12 h-12 flex items-center justify-center rounded-2xl bg-brand-surface/60 border border-white/5 text-gray-300 hover:text-white hover:border-brand-teal/50 transition-colors backdrop-blur-md relative"
          >
            <iconify-icon icon="lucide:bell" class="text-xl"></iconify-icon>
            <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-brand-orange"></span>
          </Link>
          <Link
            to="/account"
            id="nav-settings-link"
            className="w-12 h-12 flex items-center justify-center rounded-2xl bg-brand-surface/60 border border-white/5 text-gray-300 hover:text-white hover:border-brand-teal/50 transition-colors backdrop-blur-md"
          >
            <iconify-icon icon="lucide:settings" class="text-xl"></iconify-icon>
          </Link>
        </div>
      </header>

      {/* Main Interactive Content (Center) */}
      <main className="relative z-20 flex-1 flex flex-col items-center justify-center w-full max-w-7xl mx-auto px-4 py-12 md:py-8">
        {/* Central Interactive Logo */}
        <div className="relative flex flex-col items-center z-30 mb-12 md:mb-20">
          <img
            id="main-logo"
            src="https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/bg-removed/d4b11575-1b23-40b6-85e7-6036632e88ce.png"
            alt="شعار حرب الأسماء"
            className="h-[clamp(8rem,20vw,16rem)] w-auto object-contain object-center animate-fade-in-scale trans-mid will-change-transform"
            style={{ width: 492, height: 244 }}
          />
        </div>

        {/* The Soft Arc Buttons Grid */}
        {/* Uses flex with staggered Y translations on desktop to form an arc */}
        <div className="w-full max-w-5xl flex flex-col md:flex-row justify-center items-stretch md:items-start gap-4 md:gap-6">
          {/* Button 1: Profile (Far Left on Desktop - Slightly Raised) */}
          <div className="magnetic-wrapper w-full md:w-1/4 md:-translate-y-4 transition-transform duration-700 delay-100" data-glow-color="teal">
            <Link
              to="/dashboard"
              id="arc-btn-profile"
              className="magnetic-inner block w-full trans-fast rounded-[24px] focus:outline-none focus:ring-4 focus:ring-brand-teal/50"
            >
              <div className="relative overflow-hidden bg-gradient-to-br from-[#101b2b]/95 to-[#0a111a]/95 backdrop-blur-xl border border-brand-teal/30 p-5 md:py-8 rounded-[24px] shadow-lg group hover:border-brand-teal hover:shadow-[0_20px_40px_-10px_rgba(11,138,141,0.6)] trans-fast hover:bg-[#152336]/95">
                <div className="absolute inset-0 shimmer-bg opacity-0 group-hover:opacity-100 trans-fast pointer-events-none"></div>
                <div className="relative z-10 flex flex-col items-center text-center gap-4">
                  <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-brand-teal to-cyan-500 flex items-center justify-center shadow-inner group-hover:scale-110 trans-fast">
                    <iconify-icon icon="lucide:user" class="text-2xl md:text-3xl text-white drop-shadow-md"></iconify-icon>
                  </div>
                  <div>
                    <h3 className="font-heading font-black text-xl md:text-2xl text-white tracking-wide mb-1">صفحتي</h3>
                    <p className="text-gray-400 text-[11px] md:text-xs font-bold">إحصائياتك وإنجازاتك</p>
                  </div>
                </div>
              </div>
            </Link>
          </div>

          {/* Button 2: Leaderboard (Inner Left on Desktop - Lowered) */}
          <div className="magnetic-wrapper w-full md:w-1/4 md:translate-y-6 transition-transform duration-700 delay-200" data-glow-color="purple">
            <Link
              to="/leaderboard"
              id="arc-btn-leaderboard"
              className="magnetic-inner block w-full trans-fast rounded-[24px] focus:outline-none focus:ring-4 focus:ring-brand-purple/50"
            >
              <div className="relative overflow-hidden bg-gradient-to-br from-[#1b1429]/95 to-[#110c1a]/95 backdrop-blur-xl border border-brand-purple/30 p-5 md:py-8 rounded-[24px] shadow-lg group hover:border-brand-purple hover:shadow-[0_20px_40px_-10px_rgba(147,51,234,0.6)] trans-fast hover:bg-[#251b38]/95">
                <div className="absolute inset-0 shimmer-bg opacity-0 group-hover:opacity-100 trans-fast pointer-events-none"></div>
                <div className="relative z-10 flex flex-col items-center text-center gap-4">
                  <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-brand-purple to-fuchsia-500 flex items-center justify-center shadow-inner group-hover:scale-110 trans-fast">
                    <iconify-icon icon="lucide:trophy" class="text-2xl md:text-3xl text-white drop-shadow-md"></iconify-icon>
                  </div>
                  <div>
                    <h3 className="font-heading font-black text-xl md:text-2xl text-white tracking-wide mb-1">الصدارة</h3>
                    <p className="text-gray-400 text-[11px] md:text-xs font-bold">أفضل المحاربين</p>
                  </div>
                </div>
              </div>
            </Link>
          </div>

          {/* Button 3: Store (Inner Right on Desktop - Lowered) */}
          <div className="magnetic-wrapper w-full md:w-1/4 md:translate-y-6 transition-transform duration-700 delay-300" data-glow-color="orange">
            <Link
              to="/store"
              id="arc-btn-store"
              className="magnetic-inner block w-full trans-fast rounded-[24px] focus:outline-none focus:ring-4 focus:ring-brand-orange/50"
            >
              <div className="relative overflow-hidden bg-gradient-to-br from-[#291612]/95 to-[#1a0e0b]/95 backdrop-blur-xl border border-brand-orange/30 p-5 md:py-8 rounded-[24px] shadow-lg group hover:border-brand-orange hover:shadow-[0_20px_40px_-10px_rgba(216,67,21,0.6)] trans-fast hover:bg-[#361d18]/95">
                <div className="absolute inset-0 shimmer-bg opacity-0 group-hover:opacity-100 trans-fast pointer-events-none"></div>
                <div className="relative z-10 flex flex-col items-center text-center gap-4">
                  <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-brand-orange to-amber-500 flex items-center justify-center shadow-inner group-hover:scale-110 trans-fast">
                    <iconify-icon icon="lucide:shopping-bag" class="text-2xl md:text-3xl text-white drop-shadow-md"></iconify-icon>
                  </div>
                  <div>
                    <h3 className="font-heading font-black text-xl md:text-2xl text-white tracking-wide mb-1">المتجر</h3>
                    <p className="text-gray-400 text-[11px] md:text-xs font-bold">أسلحة ودروع تكتيكية</p>
                  </div>
                </div>
              </div>
            </Link>
          </div>

          {/* Button 4: Rules (Far Right on Desktop - Slightly Raised) */}
          <div className="magnetic-wrapper w-full md:w-1/4 md:-translate-y-4 transition-transform duration-700 delay-400" data-glow-color="blue">
            <a
              href="/rules"
              id="arc-btn-rules"
              className="magnetic-inner block w-full trans-fast rounded-[24px] focus:outline-none focus:ring-4 focus:ring-brand-blue/50"
            >
              <div className="relative overflow-hidden bg-gradient-to-br from-[#0c1a2e]/95 to-[#08111f]/95 backdrop-blur-xl border border-brand-blue/30 p-5 md:py-8 rounded-[24px] shadow-lg group hover:border-brand-blue hover:shadow-[0_20px_40px_-10px_rgba(59,130,246,0.6)] trans-fast hover:bg-[#122540]/95">
                <div className="absolute inset-0 shimmer-bg opacity-0 group-hover:opacity-100 trans-fast pointer-events-none"></div>
                <div className="relative z-10 flex flex-col items-center text-center gap-4">
                  <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-brand-blue to-cyan-500 flex items-center justify-center shadow-inner group-hover:scale-110 trans-fast">
                    <iconify-icon icon="lucide:book-open" class="text-2xl md:text-3xl text-white drop-shadow-md"></iconify-icon>
                  </div>
                  <div>
                    <h3 className="font-heading font-black text-xl md:text-2xl text-white tracking-wide mb-1">القواعد</h3>
                    <p className="text-gray-400 text-[11px] md:text-xs font-bold">دليل النجاة والانتصار</p>
                  </div>
                </div>
              </div>
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}
