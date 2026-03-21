import { Link, useLocation } from 'react-router-dom'

export default function NotFoundPage() {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-light-bg dark:bg-brand-dark-bg px-4">
      <div className="text-center max-w-md">
        <div className="mb-6">
          <span className="text-8xl font-heading font-black text-gray-200 dark:text-gray-800 select-none">404</span>
        </div>
        <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white mb-2">
          الصفحة غير موجودة
        </h1>
        <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mb-1">
          لا يوجد شيء على هذا العنوان:
        </p>
        <code className="text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-lg inline-block mb-8 direction-ltr" dir="ltr">
          {pathname}
        </code>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/dashboard"
            className="btn-press px-6 py-3 rounded-xl bg-brand-teal text-white font-heading font-bold text-sm hover:bg-brand-teal-hover smooth-transition flex items-center justify-center gap-2"
          >
            <iconify-icon icon="lucide:layout-dashboard" class="text-lg"></iconify-icon>
            صفحتي
          </Link>
          <Link
            to="/lobby"
            className="px-6 py-3 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-heading font-bold text-sm hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition flex items-center justify-center gap-2"
          >
            <iconify-icon icon="lucide:swords" class="text-lg"></iconify-icon>
            الساحة
          </Link>
        </div>
      </div>
    </div>
  )
}
