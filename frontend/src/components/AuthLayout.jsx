/**
 * Auth layout for Register (03) and Join Competition (04) pages.
 * Simple centered layout with logo header and minimal footer.
 * Source: Front-end/War of Names - Main Template - 1.0/03-.html, 04-.html
 */

import { Link } from 'react-router-dom'

const LOGO_URL = '/main-logo-v1.png'

export default function AuthLayout({ children, showLogo = true }) {
  return (
    <div className="min-h-screen flex flex-col relative bg-pattern-main bg-brand-light-bg dark:bg-brand-dark-bg font-body transition-colors duration-300">
      <a href="#main-content" className="skip-link">تخط إلى المحتوى</a>
      {/* Logo Header */}
      {showLogo && (
        <header className="w-full pt-12 pb-8 flex justify-center safe-area-pt" style={{ viewTransitionName: 'brand' }}>
          <Link to="/" className="block smooth-transition hover:opacity-80 hover:scale-105 transform">
            <img
              src={LOGO_URL}
              alt="حرب الأسماء"
              className="w-[160px] md:w-[200px] object-contain drop-shadow-sm"
              width="200"
              height="100"
            />
          </Link>
        </header>
      )}

      {/* Main Content */}
      <main
        id="main-content"
        tabIndex="-1"
        className="flex-1 flex flex-col items-center px-4 pb-12 md:pb-16"
        style={{ viewTransitionName: 'main-content' }}
      >
        {children}
      </main>

      {/* Minimal Footer */}
      <footer className="py-8 px-6 text-center">
        <p className="text-xs font-bold text-gray-400 dark:text-gray-600 uppercase tracking-widest">
          جميع الحقوق محفوظة © 2026 حرب الأسماء
        </p>
      </footer>
    </div>
  )
}
