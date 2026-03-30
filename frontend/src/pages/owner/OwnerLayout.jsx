/**
 * OwnerLayout — Simple layout wrapper for the owner panel.
 * Purple-themed header with crown branding.
 */

import { Link, useNavigate, Outlet } from 'react-router-dom'
import { useAuthContext } from '../../context/AuthContext'
import { toggleTheme } from '../../lib/theme'

export default function OwnerLayout() {
  const { currentUser, logout } = useAuthContext()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-brand-dark-bg transition-colors duration-300">

      {/* ═══ Header ═══ */}
      <header className="sticky top-0 z-50 bg-white dark:bg-brand-card-dark border-b border-purple-200 dark:border-purple-900/40 px-4 md:px-6 py-3 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between flex-row-reverse">

          {/* Brand */}
          <Link to="/owner" className="flex items-center gap-3 group">
            <div className="w-10 h-10 bg-purple-500/15 dark:bg-purple-500/20 rounded-xl flex items-center justify-center group-hover:bg-purple-500/25 smooth-transition">
              <iconify-icon icon="lucide:crown" class="text-xl text-purple-600 dark:text-purple-400"></iconify-icon>
            </div>
            <div>
              <div className="font-heading font-black text-sm text-purple-700 dark:text-purple-300">لوحة المالك</div>
              <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500">حرب الأسماء</div>
            </div>
          </Link>

          {/* Controls */}
          <div className="flex items-center gap-3 flex-row-reverse">
            {/* Dark mode toggle */}
            <button
              onClick={toggleTheme}
              aria-label="تبديل الوضع الداكن"
              className="w-9 h-9 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition"
            >
              <iconify-icon icon="lucide:moon" class="text-sm dark:hidden"></iconify-icon>
              <iconify-icon icon="lucide:sun" class="text-sm hidden dark:block"></iconify-icon>
            </button>

            {/* Back to game */}
            <Link
              to="/dashboard"
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
            >
              <iconify-icon icon="lucide:arrow-right" class="text-lg"></iconify-icon>
              <span className="hidden sm:inline">العودة للعبة</span>
            </Link>

            {/* User info */}
            <div className="flex items-center gap-2 text-sm">
              <span className="font-bold text-gray-600 dark:text-gray-400">{currentUser?.username}</span>
              <div className="w-8 h-8 bg-purple-500/15 dark:bg-purple-500/20 rounded-lg flex items-center justify-center text-purple-600 dark:text-purple-400 font-black text-sm">
                {currentUser?.username?.[0] || '?'}
              </div>
            </div>

            {/* Logout */}
            <button
              onClick={() => { logout(); navigate('/login') }}
              className="w-9 h-9 rounded-lg flex items-center justify-center text-gray-400 hover:text-brand-danger hover:bg-brand-danger/10 smooth-transition"
              title="تسجيل الخروج"
            >
              <iconify-icon icon="lucide:log-out" class="text-sm"></iconify-icon>
            </button>
          </div>
        </div>
      </header>

      {/* ═══ Content ═══ */}
      <main className="flex-1 p-4 md:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
