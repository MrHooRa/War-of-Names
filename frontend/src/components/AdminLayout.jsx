/**
 * Admin Layout — Restructured with Platform vs Competition domain hierarchy.
 *
 * Platform Level: Dashboard, Accounts, Platform Settings
 * Competition Level: Overview, Members, Seasons, Attacks, Quiz, Store, Ledger, Notifications, Settings
 *
 * Includes competition selector dropdown in the sidebar.
 */

import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthContext } from '../context/AuthContext'
import { useAdminCompetition } from '../context/AdminCompetitionContext'

const PLATFORM_NAV = [
  {
    label: 'المنصة',
    items: [
      { to: '/admin', icon: 'lucide:layout-dashboard', label: 'لوحة التحكم', end: true },
      { to: '/admin/accounts', icon: 'lucide:users-round', label: 'الحسابات' },
      { to: '/admin/platform-settings', icon: 'lucide:globe', label: 'إعدادات المنصة' },
    ],
  },
]

const COMPETITION_NAV = [
  {
    label: 'المنافسة',
    items: [
      { to: '/admin/competition', icon: 'lucide:trophy', label: 'نظرة عامة' },
      { to: '/admin/members', icon: 'lucide:users', label: 'الأعضاء' },
      { to: '/admin/seasons', icon: 'lucide:calendar-range', label: 'المواسم والدورات' },
    ],
  },
  {
    label: 'اللعب',
    items: [
      { to: '/admin/attacks', icon: 'lucide:swords', label: 'الهجمات' },
      { to: '/admin/quiz', icon: 'lucide:book-open', label: 'الأسئلة والجلسات' },
      { to: '/admin/store', icon: 'lucide:shopping-bag', label: 'المتجر والعناصر' },
    ],
  },
  {
    label: 'البيانات',
    items: [
      { to: '/admin/ledger', icon: 'lucide:receipt', label: 'دفتر النقاط' },
      { to: '/admin/notifications', icon: 'lucide:bell', label: 'الإشعارات' },
      { to: '/admin/settings', icon: 'lucide:settings', label: 'إعدادات المنافسة' },
    ],
  },
]

function SidebarLink({ to, icon, label, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold smooth-transition ${
          isActive
            ? 'bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate'
            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 hover:text-gray-900 dark:hover:text-white'
        }`
      }
    >
      <iconify-icon icon={icon} class="text-lg flex-shrink-0"></iconify-icon>
      <span>{label}</span>
    </NavLink>
  )
}

function CompetitionSelector() {
  const { competitions, selected, selectCompetition } = useAdminCompetition()
  const [open, setOpen] = useState(false)

  if (competitions.length === 0) return null

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold bg-brand-teal/5 dark:bg-brand-slate/10 border border-brand-teal/20 dark:border-brand-slate/20 text-gray-800 dark:text-white hover:bg-brand-teal/10 dark:hover:bg-brand-slate/20 smooth-transition"
      >
        <div className="w-7 h-7 bg-brand-teal/20 dark:bg-brand-slate/30 rounded-lg flex items-center justify-center flex-shrink-0">
          <iconify-icon icon="lucide:trophy" class="text-sm text-brand-teal dark:text-brand-slate"></iconify-icon>
        </div>
        <div className="flex-1 text-right truncate">
          <div className="text-xs font-black text-gray-400 dark:text-gray-500 leading-none mb-0.5">المنافسة الحالية</div>
          <div className="text-sm font-bold truncate">{selected?.name || 'اختر منافسة'}</div>
        </div>
        <iconify-icon icon={open ? 'lucide:chevron-up' : 'lucide:chevron-down'} class="text-sm text-gray-400"></iconify-icon>
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 overflow-hidden">
          {competitions.map(c => (
            <button
              key={c.id}
              onClick={() => { selectCompetition(c.id); setOpen(false) }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-bold text-right hover:bg-gray-50 dark:hover:bg-gray-700/50 smooth-transition ${
                c.id === selected?.id ? 'bg-brand-teal/5 dark:bg-brand-slate/10 text-brand-teal dark:text-brand-slate' : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${c.status === 'active' ? 'bg-brand-success' : 'bg-gray-300 dark:bg-gray-600'}`}></span>
              <span className="truncate">{c.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { currentUser, logout } = useAuthContext()
  const { selected } = useAdminCompetition()
  const navigate = useNavigate()

  function toggleDarkMode() {
    const html = document.documentElement
    html.classList.toggle('dark')
    localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light')
  }

  return (
    <div className="min-h-screen flex bg-gray-50 dark:bg-brand-dark-bg transition-colors duration-300">

      {/* ═══ Sidebar ═══ */}
      <aside className={`fixed inset-y-0 right-0 z-40 w-[272px] bg-white dark:bg-brand-card-dark border-l border-gray-200 dark:border-gray-800 flex flex-col transition-transform duration-300 md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}`}>
        {/* Brand */}
        <div className="px-5 py-5 border-b border-gray-200 dark:border-gray-800">
          <Link to="/admin" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-xl flex items-center justify-center">
              <iconify-icon icon="lucide:shield-check" class="text-xl text-brand-teal dark:text-brand-slate"></iconify-icon>
            </div>
            <div>
              <div className="font-heading font-black text-sm text-gray-900 dark:text-white">لوحة التحكم</div>
              <div className="text-[10px] font-bold text-gray-400 dark:text-gray-500">حرب الأسماء</div>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
          {/* Platform section */}
          {PLATFORM_NAV.map((section) => (
            <div key={section.label}>
              <div className="px-3 mb-2 text-[10px] font-black text-gray-400 dark:text-gray-600 uppercase tracking-widest">
                {section.label}
              </div>
              <div className="space-y-0.5">
                {section.items.map((item) => (
                  <SidebarLink key={item.to} {...item} />
                ))}
              </div>
            </div>
          ))}

          {/* Competition selector */}
          <div className="pt-2 pb-1 border-t border-gray-200 dark:border-gray-800">
            <div className="px-3 mb-2 text-[10px] font-black text-brand-teal dark:text-brand-slate uppercase tracking-widest flex items-center gap-1.5">
              <iconify-icon icon="lucide:trophy" class="text-xs"></iconify-icon>
              سياق المنافسة
            </div>
            <div className="px-1 mb-3">
              <CompetitionSelector />
            </div>
          </div>

          {/* Competition-scoped navigation */}
          {selected && COMPETITION_NAV.map((section) => (
            <div key={section.label}>
              <div className="px-3 mb-2 text-[10px] font-black text-gray-400 dark:text-gray-600 uppercase tracking-widest">
                {section.label}
              </div>
              <div className="space-y-0.5">
                {section.items.map((item) => (
                  <SidebarLink key={item.to} {...item} />
                ))}
              </div>
            </div>
          ))}

          {!selected && (
            <div className="px-4 py-6 text-center">
              <iconify-icon icon="lucide:trophy" class="text-3xl text-gray-300 dark:text-gray-600"></iconify-icon>
              <p className="text-xs font-bold text-gray-400 dark:text-gray-600 mt-2">اختر منافسة لإدارتها</p>
            </div>
          )}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-gray-200 dark:border-gray-800">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-bold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
          >
            <iconify-icon icon="lucide:arrow-right" class="text-lg"></iconify-icon>
            <span>العودة للعبة</span>
          </Link>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ═══ Main area ═══ */}
      <div className="flex-1 md:mr-[272px] flex flex-col min-h-screen">

        {/* Top bar */}
        <header className="sticky top-0 z-20 bg-white/80 dark:bg-brand-card-dark/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 px-4 md:px-6 py-3">
          <div className="flex items-center justify-between">
            {/* Mobile hamburger */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden w-10 h-10 flex items-center justify-center rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
            >
              <iconify-icon icon="lucide:menu" class="text-xl"></iconify-icon>
            </button>

            {/* Competition context badge */}
            <div className="hidden md:flex items-center gap-2">
              <span className="text-xs font-black text-brand-teal dark:text-brand-slate bg-brand-teal/10 dark:bg-brand-slate/20 px-2.5 py-1 rounded-lg">مشرف</span>
              {selected && (
                <span className="text-xs font-bold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2.5 py-1 rounded-lg truncate max-w-[200px]">
                  {selected.name}
                </span>
              )}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-3">
              <button
                onClick={toggleDarkMode}
                className="w-9 h-9 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition"
              >
                <iconify-icon icon="lucide:moon" class="text-sm dark:hidden"></iconify-icon>
                <iconify-icon icon="lucide:sun" class="text-sm hidden dark:block"></iconify-icon>
              </button>

              <div className="flex items-center gap-2 text-sm">
                <span className="font-bold text-gray-600 dark:text-gray-400">{currentUser?.username}</span>
                <div className="w-8 h-8 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-lg flex items-center justify-center text-brand-teal dark:text-brand-slate font-black text-sm">
                  {currentUser?.username?.[0] || '?'}
                </div>
              </div>

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

        {/* Content */}
        <main className="flex-1 p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
