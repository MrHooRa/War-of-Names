/**
 * Shared layout — Header + Footer + Mobile Nav.
 * Source: Front-end/War of Names - Main Template - 1.0/ (pages 02, 05, 06, 08, 10)
 *
 * Props:
 *  - activeItem: 'home' | 'leaderboard' | 'shop' | 'rules' | 'profile' | 'battle'
 *  - seasonText: season label from API (displayed next to logo)
 *  - children: page content
 */

import { Link, useNavigate } from 'react-router-dom'
import { useAuthContext } from '../context/AuthContext'

const LOGO_URL =
  'https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/bg-removed/d4b11575-1b23-40b6-85e7-6036632e88ce.png'

function toggleDarkMode() {
  const html = document.documentElement
  html.classList.toggle('dark')
  localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light')
}

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

export default function AppLayout({ activeItem = 'home', seasonText, children }) {
  const navigate = useNavigate()
  const { currentUser, logout } = useAuthContext()
  const displayName = currentUser?.username || '?'
  const avatarLetter = displayName[0] || '?'

  return (
    <div className="min-h-screen flex flex-col bg-brand-light-bg dark:bg-brand-dark-bg transition-colors duration-300">
      {/* ===== Desktop Header ===== */}
      <header
        className="sticky top-0 z-50 bg-white dark:bg-brand-card-dark border-b border-gray-200 dark:border-gray-800 p-4 md:px-6 md:py-4 transition-colors duration-300 shadow-sm"
        style={{ viewTransitionName: 'main-nav' }}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between flex-row-reverse">
          {/* Logo & Branding */}
          <div className="flex items-center gap-4">
            <Link to="/" id="nav-logo-link" className="block smooth-transition hover:opacity-80">
              <img
                src={LOGO_URL}
                alt="شعار حرب الأسماء"
                className="w-[130px] md:w-[150px] object-contain drop-shadow-sm"
              />
            </Link>
            <div className="hidden lg:flex flex-col items-start border-r border-gray-200 dark:border-gray-700 pr-5">
              <div className="text-xs font-bold mt-1.5 text-gray-500 dark:text-gray-400">
                {seasonText || 'الموسم التنافسي الأول'}
              </div>
            </div>
          </div>

          {/* Global Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <NavLink to="/dashboard" id="nav-home" label="الرئيسية" active={activeItem === 'home'} />
            <NavLink to="/leaderboard" id="nav-leaderboard" label="المتصدرين" active={activeItem === 'leaderboard'} />
            <NavLink to="/store" id="nav-shop" label="المتجر" active={activeItem === 'shop'} />
            <NavLink to="/rules" id="nav-rules" label="قواعد اللعبة" active={activeItem === 'rules'} />
          </nav>

          {/* User Controls */}
          <div className="flex items-center gap-4 flex-row-reverse">
            {/* Theme Toggle */}
            <button
              onClick={toggleDarkMode}
              className="w-11 h-11 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center rounded-xl text-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 smooth-transition hover:-translate-y-0.5 shadow-sm"
            >
              <iconify-icon icon="lucide:moon" class="dark:hidden"></iconify-icon>
              <iconify-icon icon="lucide:sun" class="hidden dark:block"></iconify-icon>
            </button>

            {/* Admin Panel Link */}
            {currentUser?.is_admin && (
              <Link to="/admin" className="w-11 h-11 bg-brand-teal/10 dark:bg-brand-slate/20 border border-brand-teal/20 dark:border-brand-slate/30 flex items-center justify-center rounded-xl text-xl text-brand-teal dark:text-brand-slate hover:bg-brand-teal/20 dark:hover:bg-brand-slate/30 smooth-transition hover:-translate-y-0.5 shadow-sm" title="لوحة التحكم">
                <iconify-icon icon="lucide:shield-check"></iconify-icon>
              </Link>
            )}

            {/* Notifications */}
            <Link to="/notifications" className="relative w-11 h-11 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center rounded-xl text-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 smooth-transition hover:-translate-y-0.5 shadow-sm">
              <iconify-icon icon="lucide:bell"></iconify-icon>
            </Link>

            {/* User Mini Profile */}
            <Link to="/dashboard" id="nav-profile-btn" className="flex items-center gap-3 group smooth-transition hover:-translate-y-0.5">
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
            >
              <iconify-icon icon="lucide:log-out"></iconify-icon>
            </button>
          </div>
        </div>
      </header>

      {/* ===== Main Content ===== */}
      <main
        className="flex-1 bg-pattern-main pb-20 md:pb-0"
        style={{ viewTransitionName: 'main-content' }}
      >
        {children}
      </main>

      {/* ===== Footer — from templates 02, 05, 06 ===== */}
      <footer
        className="bg-footer-pattern py-12 px-6 mt-8"
        style={{ viewTransitionName: 'footer' }}
      >
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8 flex-row-reverse">
          <Link to="/" id="footer-logo-link" className="smooth-transition hover:opacity-80 block">
            <img
              src={LOGO_URL}
              alt="شعار حرب الأسماء"
              className="w-[110px] object-contain opacity-80"
            />
          </Link>
          <div className="flex flex-col items-center md:items-start gap-4">
            <div className="flex gap-6 font-medium text-sm text-gray-400">
              <a href="#terms" className="hover:text-white transition-all duration-200 ease-in-out">شروط الاستخدام</a>
              <a href="#privacy" className="hover:text-white transition-all duration-200 ease-in-out">سياسة الخصوصية</a>
            </div>
            <div className="text-sm text-gray-500">
              جميع الحقوق محفوظة © 2024 حرب الأسماء
            </div>
          </div>
        </div>
      </footer>

      {/* ===== Mobile Bottom Nav ===== */}
      <nav
        className="md:hidden fixed bottom-0 w-full bg-white dark:bg-brand-card-dark border-t border-gray-100 dark:border-gray-800 flex justify-around items-center py-2 px-2 z-50 transition-colors duration-300 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] dark:shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.2)]"
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
          <iconify-icon icon="lucide:home" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">الرئيسية</span>
        </Link>

        <Link
          to="/leaderboard"
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

        <button
          onClick={() => navigate('/lobby')}
          id="mobile-nav-attack"
          className="flex flex-col items-center justify-center w-12 h-12 bg-brand-teal text-white dark:bg-brand-orange/80 rounded-full -mt-6 border-[3px] border-brand-light-bg dark:border-brand-dark-bg shadow-sm smooth-transition active:scale-95"
        >
          <iconify-icon icon="lucide:swords" class="text-2xl"></iconify-icon>
        </button>

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
          to="/"
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
