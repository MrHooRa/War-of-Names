/**
 * Shared layout — Header + Footer + Mobile Nav.
 * Source: Front-end/War of Names - Main Template - 1.0/ (pages 02, 05, 06, 08, 10)
 *
 * Props:
 *  - activeItem: 'home' | 'leaderboard' | 'shop' | 'rules' | 'profile' | 'battle'
 *  - seasonText: season label from API (displayed next to logo)
 *  - children: page content
 */

import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuthContext } from '../context/AuthContext'
import useCompetitionContext from '../hooks/useCompetitionContext'
import CompetitionSwitcher from './CompetitionSwitcher'
import { apiFetch } from '../lib/api'
import { toggleTheme } from '../lib/theme'
import AnnouncementOverlay from './AnnouncementOverlay'

const LOGO_URL =
  'https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/bg-removed/d4b11575-1b23-40b6-85e7-6036632e88ce.png'

function NavLink({ to, id, label, active }) {
  return (
    <Link
      to={to}
      id={id}
      className={`px-5 py-2.5 text-sm rounded-lg smooth-transition ${
        active
          ? 'bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate font-black'
          : 'text-gray-600 dark:text-gray-300 hover:text-brand-teal dark:hover:text-brand-slate hover:bg-gray-50 dark:hover:bg-gray-800/50 font-bold'
      }`}
    >
      {label}
    </Link>
  )
}

export default function AppLayout({ activeItem = 'home', children }) {
  const navigate = useNavigate()
  const { competitionId: routeCompetitionId } = useParams()
  const { currentUser, logout } = useAuthContext()
  const { seasonName, cycleLabel } = useCompetitionContext()
  const displayName = currentUser?.username || '?'
  const avatarLetter = displayName[0] || '?'
  const [unreadCount, setUnreadCount] = useState(0)
  const leaderboardHref = routeCompetitionId
    ? `/competitions/${routeCompetitionId}/leaderboard`
    : '/leaderboard'

  useEffect(() => {
    function fetchCount() {
      const activeComp = localStorage.getItem('won_active_competition')
      const url = activeComp
        ? `/api/me/notifications?competition_id=${activeComp}`
        : '/api/me/notifications'
      apiFetch(url)
        .then(r => {
          if (r.data) setUnreadCount(r.data.filter(n => !n.is_read).length)
        })
        .catch(() => {})
    }
    fetchCount()
    window.addEventListener('notifications-updated', fetchCount)
    return () => window.removeEventListener('notifications-updated', fetchCount)
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-brand-light-bg dark:bg-brand-dark-bg transition-colors duration-300">
      <a href="#main-content" className="skip-link">تخط إلى المحتوى</a>
      <AnnouncementOverlay />

      {/* ===== Desktop Header ===== */}
      <header
        className="sticky top-0 z-50 bg-white dark:bg-brand-card-dark border-b border-gray-200 dark:border-gray-800 p-4 md:px-6 md:py-4 transition-colors duration-300 shadow-sm safe-area-pt"
        style={{ viewTransitionName: 'main-nav' }}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between flex-row-reverse">
          {/* Logo & Branding */}
          <div className="flex items-center gap-4">
            <Link to="/lobby" id="nav-logo-link" className="block smooth-transition hover:opacity-80">
              <img
                src={LOGO_URL}
                alt="شعار حرب الأسماء"
                className="w-[130px] md:w-[150px] object-contain drop-shadow-sm"
                width="150"
                height="75"
              />
            </Link>
            <div className="hidden lg:flex items-center gap-3 border-r border-gray-200 dark:border-gray-700 pr-5">
              <CompetitionSwitcher variant="light" />
              {(seasonName || cycleLabel) && (
                <div className="text-xs font-bold text-gray-500 dark:text-gray-400">
                  {seasonName}
                  {cycleLabel && <span className="text-gray-400 dark:text-gray-500"> — {cycleLabel}</span>}
                </div>
              )}
            </div>
          </div>

          {/* Global Navigation */}
          <nav aria-label="التنقل الرئيسي" className="hidden md:flex items-center gap-1">
            <NavLink to="/lobby" id="nav-lobby" label="الساحة" active={activeItem === 'lobby'} />
            <NavLink to="/dashboard" id="nav-home" label="صفحتي" active={activeItem === 'home'} />
            <NavLink to={leaderboardHref} id="nav-leaderboard" label="المتصدرين" active={activeItem === 'leaderboard'} />
            <NavLink to="/store" id="nav-shop" label="المتجر" active={activeItem === 'shop'} />
            <NavLink to="/rules" id="nav-rules" label="القواعد" active={activeItem === 'rules'} />
          </nav>

          {/* User Controls */}
          <div className="flex items-center gap-4 flex-row-reverse">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              aria-label="تبديل الوضع الداكن"
              className="w-11 h-11 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center rounded-xl text-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 smooth-transition hover:-translate-y-0.5 shadow-sm"
            >
              <iconify-icon icon="lucide:moon" class="dark:hidden"></iconify-icon>
              <iconify-icon icon="lucide:sun" class="hidden dark:block"></iconify-icon>
            </button>

            {/* Owner Panel Link */}
            {currentUser?.is_owner && (
              <Link to="/owner" className="flex items-center gap-2 h-11 px-4 bg-purple-500/15 dark:bg-purple-500/20 border border-purple-500/30 dark:border-purple-400/30 rounded-xl text-purple-600 dark:text-purple-400 hover:bg-purple-500/25 dark:hover:bg-purple-500/30 smooth-transition hover:-translate-y-0.5 shadow-sm" title="لوحة المالك">
                <iconify-icon icon="lucide:crown" class="text-xl"></iconify-icon>
                <span className="text-sm font-black hidden sm:inline">المالك</span>
              </Link>
            )}

            {/* Admin Panel Link — visible for ALL admins including owners */}
            {currentUser?.is_admin && (
              <Link to="/admin" className="flex items-center gap-2 h-11 px-4 bg-amber-500/15 dark:bg-amber-500/20 border border-amber-500/30 dark:border-amber-400/30 rounded-xl text-amber-600 dark:text-amber-400 hover:bg-amber-500/25 dark:hover:bg-amber-500/30 smooth-transition hover:-translate-y-0.5 shadow-sm" title="لوحة التحكم">
                <iconify-icon icon="lucide:shield-check" class="text-xl"></iconify-icon>
                <span className="text-sm font-black hidden sm:inline">التحكم</span>
              </Link>
            )}

            {/* Notifications */}
            <Link to="/notifications" aria-label="الإشعارات" className="relative w-11 h-11 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center rounded-xl text-xl text-gray-600 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 smooth-transition hover:-translate-y-0.5 shadow-sm">
              <iconify-icon icon="lucide:bell"></iconify-icon>
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-brand-danger text-white ring-2 ring-white dark:ring-brand-dark-bg text-[10px] font-black rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Link>

            {/* User Mini Profile */}
            <Link
              to="/account"
              id="nav-profile-btn"
              aria-label="الذهاب إلى إعدادات الحساب"
              className="flex items-center gap-3 group smooth-transition hover:-translate-y-0.5"
            >
              <div className="hidden md:flex flex-col text-left">
                <span className="font-heading text-xs text-gray-500 dark:text-gray-400">{displayName}</span>
              </div>
              <div className="w-11 h-11 bg-brand-teal/10 dark:bg-brand-slate/20 border border-brand-teal/20 dark:border-brand-slate/30 rounded-xl flex items-center justify-center text-brand-teal dark:text-brand-slate font-black text-xl shadow-sm">
                {avatarLetter}
              </div>
            </Link>

            {/* Logout */}
            <button
              onClick={() => { logout(); navigate('/login') }}
              className="w-11 h-11 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center rounded-xl text-xl text-gray-600 dark:text-gray-300 hover:bg-brand-danger/10 hover:text-brand-danger dark:hover:bg-brand-danger/20 smooth-transition hover:-translate-y-0.5 shadow-sm"
              title="تسجيل الخروج"
              aria-label="تسجيل الخروج"
            >
              <iconify-icon icon="lucide:log-out"></iconify-icon>
            </button>
          </div>
        </div>
      </header>

      {/* ===== Main Content ===== */}
      <main
        id="main-content"
        tabIndex="-1"
        className="flex-1 bg-pattern-main pb-24 md:pb-0"
        style={{ viewTransitionName: 'main-content' }}
      >
        {children}
      </main>

      {/* ===== Footer ===== */}
      {/* Desktop: full footer */}
      <footer
        className="hidden md:block bg-footer-pattern py-12 px-6 mt-8"
        style={{ viewTransitionName: 'footer' }}
      >
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8 flex-row-reverse">
          <Link to="/lobby" id="footer-logo-link" className="smooth-transition hover:opacity-80 block">
            <img src={LOGO_URL} alt="شعار حرب الأسماء" className="w-[110px] object-contain opacity-80" width="110" height="55" />
          </Link>
          <div className="flex flex-col items-center md:items-start gap-4">
            <div className="flex gap-6 font-medium text-sm text-gray-400">
              <Link to="/terms" className="hover:text-white transition-all duration-200 ease-in-out">شروط الاستخدام</Link>
              <Link to="/privacy" className="hover:text-white transition-all duration-200 ease-in-out">سياسة الخصوصية</Link>
            </div>
            <div className="text-sm text-gray-500">
              جميع الحقوق محفوظة © 2026 حرب الأسماء - تطوير سلمان
            </div>
          </div>
        </div>
      </footer>
      {/* Mobile: minimal credit line above bottom nav */}
      <div className="md:hidden bg-gray-100 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-4 py-2 mb-14 flex items-center justify-between text-[10px] text-gray-400">
        <span>© 2026 حرب الأسماء — سلمان</span>
        <div className="flex gap-3">
          <Link to="/terms" className="hover:text-gray-600 dark:hover:text-gray-300">الشروط</Link>
          <Link to="/privacy" className="hover:text-gray-600 dark:hover:text-gray-300">الخصوصية</Link>
        </div>
      </div>

      {/* ===== Mobile Bottom Nav ===== */}
      <nav
        aria-label="التنقل السفلي"
        className="md:hidden fixed bottom-0 w-full bg-white dark:bg-brand-card-dark border-t border-gray-100 dark:border-gray-800 flex justify-around items-center py-2 px-2 z-50 transition-colors duration-300 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] dark:shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.2)] safe-area-pb"
        style={{ viewTransitionName: 'mobile-nav' }}
      >
        <Link
          to="/dashboard"
          id="mobile-nav-home"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'home'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:layout-dashboard" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">صفحتي</span>
        </Link>

        <Link
          to={leaderboardHref}
          id="mobile-nav-leaderboard-btn"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'leaderboard'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:trophy" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">المتصدرين</span>
        </Link>

        <Link
          to="/lobby"
          id="mobile-nav-attack"
          aria-label="ساحة المعركة"
          className="flex flex-col items-center justify-center w-12 h-12 bg-brand-teal text-white dark:bg-brand-orange/80 rounded-full -mt-6 border-[3px] border-brand-light-bg dark:border-brand-dark-bg shadow-sm smooth-transition active:scale-95"
        >
          <iconify-icon icon="lucide:swords" class="text-2xl"></iconify-icon>
        </Link>

        <Link
          to="/store"
          id="mobile-nav-shop-btn"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'shop'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:shopping-bag" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">المتجر</span>
        </Link>

        <Link
          to="/account"
          id="mobile-nav-profile"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'profile'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:user" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">حسابي</span>
        </Link>
      </nav>
    </div>
  )
}
