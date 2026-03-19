/**
 * Shared layout extracted from the HTML template.
 * Source: Front-end/War of Names - Main Template - 1.0/05-player-dashboard-unified-navigation-linked.html
 *
 * This component replicates the exact header, mobile nav, and page shell
 * used across pages 02, 05, 06, 08, 10 of the template.
 *
 * Props:
 *  - activeItem: which nav item is highlighted ('home' | 'leaderboard' | 'shop' | 'rules' | 'profile')
 *  - seasonText: season label displayed next to the logo (from API)
 *  - children: page content
 */

const LOGO_URL =
  'https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/bg-removed/d4b11575-1b23-40b6-85e7-6036632e88ce.png'

function toggleDarkMode() {
  const html = document.documentElement
  html.classList.toggle('dark')
  localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light')
}

function NavLink({ href, id, label, active }) {
  return (
    <a
      href={href}
      id={id}
      className={`px-5 py-2.5 text-sm rounded-lg smooth-transition ${
        active
          ? 'bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate font-black'
          : 'text-gray-600 dark:text-gray-300 hover:text-brand-teal dark:hover:text-brand-slate hover:bg-gray-50 dark:hover:bg-gray-800/50 font-bold'
      }`}
    >
      {label}
    </a>
  )
}

export default function AppLayout({ activeItem = 'home', seasonText, children }) {
  return (
    <div className="min-h-screen bg-brand-light-bg dark:bg-brand-dark-bg transition-colors duration-300">
      {/* ===== Desktop Header — exact match of template ===== */}
      <header
        className="sticky top-0 z-50 bg-white dark:bg-brand-card-dark border-b border-gray-200 dark:border-gray-800 p-4 md:px-6 md:py-4 transition-colors duration-300 shadow-sm"
        style={{ viewTransitionName: 'main-nav' }}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between flex-row-reverse">
          {/* Logo & Branding */}
          <div className="flex items-center gap-4">
            <a href="/" id="nav-logo-link" className="block smooth-transition hover:opacity-80">
              <img
                src={LOGO_URL}
                alt="شعار حرب الأسماء"
                className="w-[130px] md:w-[150px] object-contain drop-shadow-sm"
              />
            </a>
            <div className="hidden lg:flex flex-col items-start border-r border-gray-200 dark:border-gray-700 pr-5">
              <div className="text-xs font-bold mt-1.5 text-gray-500 dark:text-gray-400">
                {seasonText || '...'}
              </div>
            </div>
          </div>

          {/* Global Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <NavLink href="/" id="nav-home" label="الرئيسية" active={activeItem === 'home'} />
            <NavLink href="/leaderboard" id="nav-leaderboard" label="المتصدرين" active={activeItem === 'leaderboard'} />
            <NavLink href="/shop" id="nav-shop" label="المتجر" active={activeItem === 'shop'} />
            <NavLink href="/rules" id="nav-rules" label="قواعد اللعبة" active={activeItem === 'rules'} />
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

            {/* User Mini Profile */}
            <a href="/profile" id="nav-profile-btn" className="flex items-center gap-3 group smooth-transition hover:-translate-y-0.5">
              <div className="hidden md:flex flex-col text-left">
                <span className="font-heading text-xs text-gray-500 dark:text-gray-400">المحارب الذهبي</span>
                <span className="font-heading text-sm font-black text-brand-teal dark:text-brand-slate">8,450 نقطة</span>
              </div>
              <div className="w-11 h-11 bg-brand-teal/10 dark:bg-brand-slate/20 border border-brand-teal/20 dark:border-brand-slate/30 rounded-xl flex items-center justify-center text-brand-teal dark:text-brand-slate font-black text-xl shadow-sm">
                م
              </div>
            </a>
          </div>
        </div>
      </header>

      {/* ===== Main Content ===== */}
      <main
        className="bg-pattern-main min-h-[calc(100vh-80px)] pb-20 md:pb-0"
        style={{ viewTransitionName: 'main-content' }}
      >
        {children}
      </main>

      {/* ===== Mobile Bottom Nav — exact match of template ===== */}
      <nav
        className="md:hidden fixed bottom-0 w-full bg-white dark:bg-brand-card-dark border-t border-gray-100 dark:border-gray-800 flex justify-around items-center py-2 px-2 z-50 transition-colors duration-300 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] dark:shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.2)]"
        style={{ viewTransitionName: 'mobile-nav' }}
      >
        <a
          href="/"
          id="mobile-nav-home"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'home'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:home" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">الرئيسية</span>
        </a>

        <a
          href="/leaderboard"
          id="mobile-nav-leaderboard-btn"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'leaderboard'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:trophy" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">المتصدرين</span>
        </a>

        <button
          id="mobile-nav-attack"
          className="flex flex-col items-center justify-center w-12 h-12 bg-brand-teal text-white dark:bg-brand-orange/80 rounded-full -mt-6 border-[3px] border-brand-light-bg dark:border-brand-dark-bg shadow-sm smooth-transition active:scale-95"
        >
          <iconify-icon icon="lucide:swords" class="text-2xl"></iconify-icon>
        </button>

        <a
          href="/shop"
          id="mobile-nav-shop-btn"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'shop'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:shopping-bag" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">المتجر</span>
        </a>

        <a
          href="/profile"
          id="mobile-nav-profile"
          className={`flex flex-col items-center gap-1 smooth-transition ${
            activeItem === 'profile'
              ? 'text-brand-teal dark:text-brand-slate'
              : 'text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate'
          }`}
        >
          <iconify-icon icon="lucide:user" class="text-[1.3rem]"></iconify-icon>
          <span className="text-[9px] font-bold">حسابي</span>
        </a>
      </nav>
    </div>
  )
}
