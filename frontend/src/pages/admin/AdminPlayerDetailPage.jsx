import { useParams, Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'

function StatusBadge({ status }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success', succeeded: 'bg-brand-success/10 text-brand-success',
    failed: 'bg-brand-danger/10 text-brand-danger', available: 'bg-brand-teal/10 text-brand-teal',
    consumed: 'bg-gray-100 dark:bg-gray-800 text-gray-400', suspended: 'bg-brand-danger/10 text-brand-danger',
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{status}</span>
}

const ENTRY_TYPE_LABELS = {
  initial_balance: 'رصيد أولي', question_reward: 'مكافأة سؤال', attack_reward: 'مكافأة هجوم',
  attack_penalty: 'خسارة هجوم', item_purchase: 'شراء عنصر', admin_adjustment: 'تعديل إداري',
  distribution: 'توزيع', compensation: 'تعويض', system_reward: 'مكافأة نظام',
}

export default function AdminPlayerDetailPage() {
  const { membershipId } = useParams()
  const { data: player, loading, error } = useAdminData(`/api/admin/players/${membershipId}`)

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  if (error || !player) {
    return <div className="text-center py-20 text-gray-500 font-bold">{error || 'لم يتم العثور على اللاعب'}</div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Back + Header */}
      <div className="flex items-center gap-4">
        <Link to="/admin/players" className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition">
          <iconify-icon icon="lucide:arrow-right" class="text-lg"></iconify-icon>
        </Link>
        <div>
          <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">{player.alias || player.username}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{player.real_name} — @{player.username}</p>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">الرصيد</div>
          <div className={`font-display text-3xl font-black ${player.is_bankrupt ? 'text-brand-danger' : 'text-gray-900 dark:text-white'}`}>
            {player.balance?.toLocaleString('ar-SA')}
          </div>
          {player.is_bankrupt && <span className="text-xs text-brand-danger font-bold">مفلس</span>}
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">الحالة</div>
          <StatusBadge status={player.status} />
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">الحماية</div>
          <div className="font-heading font-black text-gray-900 dark:text-white">{player.protection}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-5 text-center">
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">المخزن</div>
          <div className="font-heading font-black text-gray-900 dark:text-white">{player.inventory?.length || 0} عنصر</div>
        </div>
      </div>

      {/* Ledger + Attacks Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ledger */}
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:receipt" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            سجل النقاط
          </h2>
          {player.ledger?.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-6">لا توجد حركات</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {player.ledger?.map(le => (
                <div key={le.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl text-sm">
                  <div>
                    <div className="font-bold text-gray-700 dark:text-gray-300">{ENTRY_TYPE_LABELS[le.entry_type] || le.entry_type}</div>
                    <div className="text-[11px] text-gray-400">{le.reason}</div>
                  </div>
                  <div className="text-left">
                    <div className={`font-heading font-black ${le.direction === 'credit' ? 'text-brand-success' : 'text-brand-danger'}`}>
                      {le.direction === 'credit' ? '+' : '-'}{le.amount}
                    </div>
                    <div className="text-[10px] text-gray-400">{le.balance_before} → {le.balance_after}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Attacks */}
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:swords" class="text-brand-orange"></iconify-icon>
            سجل الهجمات
          </h2>
          {player.attacks?.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-6">لا توجد هجمات</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {player.attacks?.map(a => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl text-sm">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={a.outcome} />
                    <span className="font-bold text-gray-700 dark:text-gray-300">
                      {a.role === 'attacker' ? `→ ${a.target_alias}` : `← ${a.attacker_alias}`}
                    </span>
                  </div>
                  <div>
                    {a.reward_amount > 0 && <span className="text-brand-success font-black text-xs">+{a.reward_amount}</span>}
                    {a.penalty_amount > 0 && <span className="text-brand-danger font-black text-xs">-{a.penalty_amount}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Inventory */}
      {player.inventory?.length > 0 && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:package" class="text-purple-500"></iconify-icon>
            المخزن
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {player.inventory.map(item => (
              <div key={item.id} className="p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl text-center">
                <div className="font-bold text-sm text-gray-700 dark:text-gray-300">{item.name}</div>
                <div className="flex items-center justify-center gap-2 mt-1">
                  <StatusBadge status={item.status} />
                  <span className="text-[10px] text-gray-400">{item.rarity}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
