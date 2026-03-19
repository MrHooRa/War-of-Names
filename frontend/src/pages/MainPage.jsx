/**
 * Main entry page — converted from:
 * Front-end/War of Names - Main Template - 1.0/00-Main Page.html
 *
 * Standalone dark page (no AppLayout). Sits before the lobby in the user journey.
 * Session logic: first render sets sessionStorage flag; on subsequent visits
 * to "/" in the same session, App.jsx redirects to /lobby automatically.
 */

import { useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const LOGO_URL =
  'https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/bg-removed/d4b11575-1b23-40b6-85e7-6036632e88ce.png'

export default function MainPage() {
  const navigate = useNavigate()
  const ctaBtnRef = useRef(null)
  const centerGlowRef = useRef(null)

  // Mark this session as having seen the main page
  useEffect(() => {
    sessionStorage.setItem('mainPageSeen', '1')
  }, [])

  // CTA hover → lobby-active body class + glow color (mirrors original JS)
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
  }, [])

  return (
    <div
      className="min-h-screen flex flex-col relative"
      style={{ backgroundColor: '#0a0d14', color: '#FFFFFF', overflowX: 'hidden', WebkitFontSmoothing: 'antialiased' }}
    >
      {/* ===== Background Visual Zone ===== */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Radial gradient base */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(21,27,41,1)_0%,rgba(10,13,20,1)_100%)]"></div>

        {/* Hex grid */}
        <div className="absolute inset-0 hex-bg opacity-30"></div>

        {/* Rotating teal hexagon — top right */}
        <div className="absolute top-0 -right-[5%] w-[700px] h-[700px] opacity-10 bg-shape">
          <svg viewBox="0 0 100 100" className="w-full h-full text-brand-teal fill-current drop-shadow-[0_0_80px_rgba(11,138,141,1)]">
            <polygon points="50 1, 93.3 25, 93.3 75, 50 99, 6.7 75, 6.7 25" />
          </svg>
        </div>

        {/* Rotating orange hexagon — bottom left */}
        <div className="absolute bottom-[-10%] -left-[10%] w-[900px] h-[900px] opacity-[0.08] bg-shape-reverse">
          <svg viewBox="0 0 100 100" className="w-full h-full text-brand-orange fill-current drop-shadow-[0_0_100px_rgba(216,67,21,1)]">
            <polygon points="50 1, 93.3 25, 93.3 75, 50 99, 6.7 75, 6.7 25" />
          </svg>
        </div>

        {/* Center focus glow */}
        <div
          ref={centerGlowRef}
          id="center-glow"
          className="absolute top-[35%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] blur-[120px] rounded-full trans-mid"
          style={{ backgroundColor: 'rgba(11, 138, 141, 0.1)' }}
        ></div>
      </div>

      {/* ===== Header (Minimal) ===== */}
      <header
        className="relative z-30 w-full p-6 flex justify-between items-center pointer-events-none"
        style={{ opacity: 0, animation: 'slideDownFade 0.5s ease 0.5s forwards' }}
      >
        {/* Status indicator */}
        <div className="flex items-center gap-3 bg-brand-surface/60 backdrop-blur-md px-5 py-2.5 rounded-2xl border border-white/5 shadow-lg pointer-events-auto">
          <div className="w-2.5 h-2.5 rounded-full bg-brand-emerald animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.8)]"></div>
          <span className="text-sm font-bold text-gray-200 tracking-wide">المركز الرئيسي متصل</span>
        </div>

        {/* Icon buttons */}
        <div className="flex gap-4 pointer-events-auto">
          <a
            href="#notifications"
            id="nav-notifications-link"
            className="w-12 h-12 flex items-center justify-center rounded-2xl bg-brand-surface/60 border border-white/5 text-gray-300 hover:text-white hover:border-brand-teal/50 transition-colors backdrop-blur-md relative"
          >
            <iconify-icon icon="lucide:bell" class="text-xl"></iconify-icon>
            <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-brand-orange"></span>
          </a>
          <a
            href="#settings"
            id="nav-settings-link"
            className="w-12 h-12 flex items-center justify-center rounded-2xl bg-brand-surface/60 border border-white/5 text-gray-300 hover:text-white hover:border-brand-teal/50 transition-colors backdrop-blur-md"
          >
            <iconify-icon icon="lucide:settings" class="text-xl"></iconify-icon>
          </a>
        </div>
      </header>

      {/* ===== Main Interactive Content ===== */}
      <main className="relative z-20 flex-1 flex flex-col items-center justify-center w-full max-w-7xl mx-auto px-4 py-12 md:py-8">

        {/* Central Logo */}
        <div className="relative flex flex-col items-center z-30 mb-12 md:mb-20">
          <img
            id="main-logo"
            src={LOGO_URL}
            alt="شعار حرب الأسماء"
            className="h-[clamp(8rem,20vw,16rem)] w-auto object-contain object-center animate-fade-in-scale trans-mid will-change-transform"
            style={{ width: 492, height: 244 }}
          />
        </div>

        {/* Mega CTA Section */}
        <div className="relative w-full max-w-2xl flex flex-col items-center text-center mt-4">

          {/* Top badge */}
          <div
            className="inline-flex items-center gap-2 bg-brand-orange/10 border border-brand-orange/30 text-brand-orange px-5 py-2 rounded-full text-sm font-bold mb-8 shadow-[0_0_15px_rgba(216,67,21,0.2)]"
            style={{ opacity: 0, animation: 'slideDownFade 0.5s ease 0.8s forwards' }}
          >
            <span className="text-lg leading-none">يهووووه أقوى لعبة لعام 2026 🔥</span>
          </div>

          {/* Mega Button */}
          <div
            className="relative w-full sm:w-auto z-40"
            style={{ opacity: 0, animation: 'fadeInScale 0.8s cubic-bezier(0.16,1,0.3,1) 1s forwards' }}
          >
            {/* Decorative stars */}
            <iconify-icon
              icon="mdi:star-four-points"
              class="absolute -top-6 -left-8 text-amber-300 text-3xl animate-float-slow drop-shadow-[0_0_10px_rgba(252,211,77,0.8)]"
            ></iconify-icon>
            <iconify-icon
              icon="mdi:star-four-points"
              class="absolute top-1/2 -right-10 text-brand-teal-light-lobby text-2xl animate-float-fast drop-shadow-[0_0_10px_rgba(0,217,233,0.8)]"
            ></iconify-icon>
            <iconify-icon
              icon="mdi:sparkles"
              class="absolute -bottom-4 -left-4 text-brand-orange text-xl animate-float-medium drop-shadow-[0_0_10px_rgba(216,67,21,0.8)]"
            ></iconify-icon>

            {/* The button — navigates to /lobby */}
            <button
              ref={ctaBtnRef}
              onClick={() => navigate('/lobby')}
              className="btn-mega-cta relative block w-full sm:w-[450px] overflow-hidden rounded-[2rem] bg-gradient-to-br from-brand-teal to-brand-orange p-[2px] focus:outline-none focus:ring-4 focus:ring-brand-orange/50 transition-all duration-300 hover:scale-[1.08] active:scale-95 group cursor-pointer border-0"
            >
              {/* Outer glow */}
              <div className="absolute inset-0 rounded-[2rem] glow-pulse opacity-70 group-hover:opacity-100 transition-opacity duration-300"></div>

              <div className="relative h-full w-full bg-gradient-to-br from-[#0B8A8D] to-[#D84315] rounded-[calc(2rem-2px)] px-12 py-6 flex flex-col items-center justify-center gap-2 overflow-hidden float-animation">
                {/* Shimmer */}
                <div className="absolute inset-0 w-[200%] h-full shimmer-effect pointer-events-none"></div>

                {/* Particle bg */}
                <div
                  className="absolute inset-0 opacity-30 mix-blend-overlay pointer-events-none"
                  style={{
                    backgroundImage: "url(\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuMDUiLz4KPC9zdmc+\")"
                  }}
                ></div>

                <div className="relative z-10 flex items-center justify-center gap-4 text-white">
                  <iconify-icon
                    icon="mdi:rocket"
                    class="text-4xl drop-shadow-lg group-hover:-translate-y-1 group-hover:translate-x-1 transition-transform duration-300"
                  ></iconify-icon>
                  <span className="font-heading font-black text-3xl md:text-4xl tracking-wide drop-shadow-md">
                    ابدأ اللعبة الآن
                  </span>
                </div>
              </div>
            </button>
          </div>

          {/* Bottom area (empty in template, reserved) */}
          <div
            className="mt-10 flex flex-col items-center gap-6"
            style={{ animation: 'slideUpFade 0.8s ease 1.2s forwards', opacity: 0 }}
          ></div>
        </div>
      </main>
    </div>
  )
}
