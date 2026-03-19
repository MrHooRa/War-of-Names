import useNotifications from '../hooks/useNotifications'

const TYPE_ICONS = {
  attack_success: 'lucide:swords',
  attack_failure: 'lucide:shield-x',
  attack_received: 'lucide:alert-triangle',
  item_purchased: 'lucide:shopping-bag',
  quiz_opened: 'lucide:book-check',
  competition_joined: 'lucide:users',
  general: 'lucide:bell',
}

const TYPE_COLORS = {
  attack_success: 'text-brand-success',
  attack_failure: 'text-brand-danger',
  attack_received: 'text-brand-orange',
  item_purchased: 'text-brand-teal dark:text-brand-slate',
  quiz_opened: 'text-amber-500',
}

function timeAgo(isoString) {
  if (!isoString) return ''
  const diff = Date.now() - new Date(isoString).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'الآن'
  if (minutes < 60) return `منذ ${minutes} دقيقة`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `منذ ${hours} ساعة`
  const days = Math.floor(hours / 24)
  return `منذ ${days} يوم`
}

export default function NotificationsPage() {
  const { notifications, loading, error, unreadCount, markRead, markAllRead } = useNotifications()

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal dark:text-brand-slate animate-spin"></iconify-icon>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20 gap-4">
        <iconify-icon icon="lucide:alert-circle" class="text-4xl text-brand-danger"></iconify-icon>
        <p className="text-gray-600 dark:text-gray-400 font-bold">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-8 md:py-12 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <iconify-icon icon="lucide:bell" class="text-3xl text-brand-teal dark:text-brand-slate"></iconify-icon>
          <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">الإشعارات</h1>
          {unreadCount > 0 && (
            <span className="bg-brand-danger text-white text-xs font-black px-2.5 py-1 rounded-full">{unreadCount}</span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="text-sm font-bold text-brand-teal dark:text-brand-slate hover:underline"
          >
            تحديد الكل كمقروء
          </button>
        )}
      </div>

      {/* Empty state */}
      {notifications.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <iconify-icon icon="lucide:bell-off" class="text-6xl text-gray-300 dark:text-gray-700"></iconify-icon>
          <p className="text-gray-500 dark:text-gray-400 font-bold text-lg">لا توجد إشعارات بعد</p>
        </div>
      )}

      {/* Notifications list */}
      <div className="space-y-3">
        {notifications.map(n => {
          const icon = TYPE_ICONS[n.type] || TYPE_ICONS.general
          const color = TYPE_COLORS[n.type] || 'text-gray-400'

          return (
            <button
              key={n.id}
              onClick={() => !n.is_read && markRead(n.id)}
              className={`w-full text-right flex items-start gap-4 p-5 rounded-2xl border smooth-transition ${
                n.is_read
                  ? 'bg-gray-50 dark:bg-gray-800/30 border-gray-100 dark:border-gray-800 opacity-70'
                  : 'bg-white dark:bg-brand-card-dark border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md'
              }`}
            >
              <div className={`flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center ${
                n.is_read ? 'bg-gray-100 dark:bg-gray-800' : 'bg-brand-teal/10 dark:bg-brand-slate/20'
              }`}>
                <iconify-icon icon={icon} class={`text-xl ${n.is_read ? 'text-gray-400' : color}`}></iconify-icon>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h3 className={`font-heading font-black text-sm ${n.is_read ? 'text-gray-500 dark:text-gray-500' : 'text-gray-900 dark:text-white'}`}>
                    {n.title}
                  </h3>
                  {!n.is_read && (
                    <span className="flex-shrink-0 w-2.5 h-2.5 bg-brand-teal dark:bg-brand-slate rounded-full"></span>
                  )}
                </div>
                <p className={`text-sm ${n.is_read ? 'text-gray-400' : 'text-gray-600 dark:text-gray-400'}`}>{n.message}</p>
                <span className="text-xs text-gray-400 dark:text-gray-600 mt-1 block">{timeAgo(n.created_at)}</span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
