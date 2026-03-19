import { Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'

function StatusBadge({ status }) {
  const colors = {
    succeeded: 'bg-brand-success/10 text-brand-success',
    failed: 'bg-brand-danger/10 text-brand-danger',
    blocked: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    rejected: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
  }
  const labels = { succeeded: 'ناجح', failed: 'فاشل', blocked: 'محظور', rejected: 'مرفوض' }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{labels[status] || status}</span>
}

export default function AdminAttacksPage() {
  const { data: attacks, loading, error } = useAdminData('/api/admin/attacks')

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  const succeeded = attacks?.filter(a => a.outcome === 'succeeded').length || 0
  const failed = attacks?.filter(a => a.outcome === 'failed').length || 0

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">سجل الهجمات</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {attacks?.length || 0} هجوم — {succeeded} ناجح، {failed} فاشل
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">إجمالي</div>
          <div className="font-display text-2xl font-black text-gray-900 dark:text-white">{attacks?.length || 0}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">ناجح</div>
          <div className="font-display text-2xl font-black text-brand-success">{succeeded}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">فاشل</div>
          <div className="font-display text-2xl font-black text-brand-danger">{failed}</div>
        </div>
      </div>

      {/* Attacks Table */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">النتيجة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">المهاجم</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">الهدف</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">المكافأة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">العقوبة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 dark:text-gray-400 text-[11px] uppercase tracking-widest">التوقيت</th>
              </tr>
            </thead>
            <tbody>
              {attacks?.map(a => (
                <tr key={a.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                  <td className="px-4 py-3"><StatusBadge status={a.outcome} /></td>
                  <td className="px-4 py-3">
                    <Link to={`/admin/players/${a.attacker_membership_id}`} className="hover:text-brand-teal smooth-transition">
                      <div className="font-bold text-gray-900 dark:text-white">{a.attacker_alias}</div>
                      <div className="text-[11px] text-gray-400">{a.attacker_real_name}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/admin/players/${a.target_membership_id}`} className="hover:text-brand-teal smooth-transition">
                      <div className="font-bold text-gray-900 dark:text-white">{a.target_alias}</div>
                      <div className="text-[11px] text-gray-400">{a.target_real_name}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    {a.reward_amount > 0 ? (
                      <span className="font-heading font-black text-brand-success">+{a.reward_amount}</span>
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {a.penalty_amount > 0 ? (
                      <span className="font-heading font-black text-brand-danger">-{a.penalty_amount}</span>
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {a.created_at ? new Date(a.created_at).toLocaleString('ar-SA') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {(!attacks || attacks.length === 0) && (
          <div className="text-center py-12 text-gray-400 font-bold">لا توجد هجمات بعد</div>
        )}
      </div>
    </div>
  )
}
