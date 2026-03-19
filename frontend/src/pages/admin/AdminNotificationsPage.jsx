import useAdminData from '../../hooks/useAdminData'

const TYPE_CONFIG = {
  ATTACK_SUCCESS: { icon: 'lucide:swords', color: 'text-brand-success', bg: 'bg-brand-success/10', label: 'هجوم ناجح' },
  ATTACK_FAILURE: { icon: 'lucide:shield-off', color: 'text-brand-danger', bg: 'bg-brand-danger/10', label: 'هجوم فاشل' },
  ATTACK_RECEIVED: { icon: 'lucide:shield-alert', color: 'text-amber-600', bg: 'bg-amber-100 dark:bg-amber-900/30', label: 'تعرض لهجوم' },
  ITEM_PURCHASED: { icon: 'lucide:shopping-bag', color: 'text-purple-600', bg: 'bg-purple-100 dark:bg-purple-900/30', label: 'شراء' },
  QUIZ_OPENED: { icon: 'lucide:check-circle', color: 'text-blue-600', bg: 'bg-blue-100 dark:bg-blue-900/30', label: 'إجابة سؤال' },
  BALANCE_ADJUSTED: { icon: 'lucide:coins', color: 'text-brand-teal', bg: 'bg-brand-teal/10', label: 'تعديل رصيد' },
  SYSTEM: { icon: 'lucide:bell', color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-gray-800', label: 'نظام' },
}

const PRIORITY_COLORS = {
  LOW: 'text-gray-400',
  NORMAL: 'text-gray-600 dark:text-gray-300',
  HIGH: 'text-amber-600',
  URGENT: 'text-brand-danger',
}

export default function AdminNotificationsPage() {
  const { data: notifications, loading } = useAdminData('/api/admin/notifications')

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  const unreadCount = notifications?.filter(n => !n.is_read).length || 0
  const totalCount = notifications?.length || 0

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">الإشعارات</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {totalCount} إشعار — {unreadCount} غير مقروء
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي</div>
          <div className="font-display text-2xl font-black text-gray-900 dark:text-white">{totalCount}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">غير مقروء</div>
          <div className="font-display text-2xl font-black text-brand-teal">{unreadCount}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">هجمات</div>
          <div className="font-display text-2xl font-black text-brand-orange">
            {notifications?.filter(n => n.notification_type?.startsWith('ATTACK')).length || 0}
          </div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">مشتريات</div>
          <div className="font-display text-2xl font-black text-purple-600">
            {notifications?.filter(n => n.notification_type === 'ITEM_PURCHASED').length || 0}
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className="space-y-2">
        {notifications?.map(n => {
          const config = TYPE_CONFIG[n.notification_type] || TYPE_CONFIG.SYSTEM
          return (
            <div
              key={n.id}
              className={`bg-white dark:bg-brand-card-dark border rounded-2xl p-4 smooth-transition ${
                n.is_read
                  ? 'border-gray-200 dark:border-gray-700'
                  : 'border-brand-teal/30 dark:border-brand-slate/30'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${config.bg}`}>
                  <iconify-icon icon={config.icon} class={`text-lg ${config.color}`}></iconify-icon>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <h3 className={`font-bold text-sm ${n.is_read ? 'text-gray-600 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                        {n.title}
                      </h3>
                      {!n.is_read && <span className="w-2 h-2 bg-brand-teal rounded-full flex-shrink-0"></span>}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className={`text-[10px] font-black ${PRIORITY_COLORS[n.priority] || 'text-gray-400'}`}>
                        {n.priority}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-black ${config.bg} ${config.color}`}>
                        {config.label}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{n.message}</p>
                  <div className="flex items-center gap-3 mt-2 text-[11px] text-gray-400">
                    {n.recipient_username && (
                      <span className="flex items-center gap-1">
                        <iconify-icon icon="lucide:user" class="text-xs"></iconify-icon>
                        {n.recipient_username}
                      </span>
                    )}
                    <span>{n.created_at ? new Date(n.created_at).toLocaleString('ar-SA') : '—'}</span>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
        {(!notifications || notifications.length === 0) && (
          <div className="text-center py-12 text-gray-400 font-bold">لا توجد إشعارات</div>
        )}
      </div>
    </div>
  )
}
