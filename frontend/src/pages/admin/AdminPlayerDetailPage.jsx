import { useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

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

const PROTECTION_OPTIONS = [
  { value: 'none', label: 'بدون حماية', icon: 'lucide:shield-off', color: 'text-gray-400' },
  { value: 'partial', label: 'حماية جزئية', icon: 'lucide:shield-half', color: 'text-yellow-500' },
  { value: 'full', label: 'حماية كاملة', icon: 'lucide:shield-check', color: 'text-blue-500' },
]

export default function AdminPlayerDetailPage() {
  const { membershipId } = useParams()
  const { data: player, loading, error, refetch } = useAdminData(`/api/admin/players/${membershipId}`)

  // Action states
  const [adjustModal, setAdjustModal] = useState(false)
  const [adjustAmount, setAdjustAmount] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [adjusting, setAdjusting] = useState(false)
  const [actionMessage, setActionMessage] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null) // { type, label, action }

  const showMessage = useCallback((type, text) => {
    setActionMessage({ type, text })
    setTimeout(() => setActionMessage(null), 3000)
  }, [])

  async function handleAdjustBalance(e) {
    e.preventDefault()
    if (!adjustAmount) return
    setAdjusting(true)
    try {
      const res = await apiFetch(`/api/admin/players/${membershipId}/adjust-balance`, {
        method: 'POST',
        body: JSON.stringify({
          amount: parseInt(adjustAmount),
          reason: adjustReason || 'تعديل إداري',
        }),
      })
      showMessage('success', res.message || 'تم تعديل الرصيد')
      setAdjustModal(false)
      setAdjustAmount('')
      setAdjustReason('')
      refetch()
    } catch (err) {
      showMessage('error', err.message)
    }
    setAdjusting(false)
  }

  async function handleStatusChange(newStatus) {
    try {
      await apiFetch(`/api/admin/players/${membershipId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      showMessage('success', `تم تحديث الحالة إلى ${newStatus === 'active' ? 'نشط' : 'معلق'}`)
      refetch()
    } catch (err) {
      showMessage('error', err.message)
    }
    setConfirmAction(null)
  }

  async function handleProtectionChange(protection) {
    try {
      const res = await apiFetch(`/api/admin/players/${membershipId}/protection`, {
        method: 'PATCH',
        body: JSON.stringify({ protection }),
      })
      showMessage('success', res.message || 'تم تحديث الحماية')
      refetch()
    } catch (err) {
      showMessage('error', err.message)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  if (error || !player) {
    return <div className="text-center py-20 text-gray-500 font-bold">{error || 'لم يتم العثور على اللاعب'}</div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Action Message Banner */}
      {actionMessage && (
        <div className={`px-5 py-3 rounded-xl text-sm font-bold ${actionMessage.type === 'success' ? 'bg-brand-success/10 text-brand-success' : 'bg-brand-danger/10 text-brand-danger'}`}>
          {actionMessage.text}
        </div>
      )}

      {/* Back + Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <Link to="/admin/members" className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition">
            <iconify-icon icon="lucide:arrow-right" class="text-lg"></iconify-icon>
          </Link>
          <div>
            <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">{player.alias || player.username}</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{player.real_name} — @{player.username}</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAdjustModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate hover:bg-brand-teal/20 dark:hover:bg-brand-slate/20 rounded-xl font-bold text-sm smooth-transition"
          >
            <iconify-icon icon="lucide:coins" class="text-lg"></iconify-icon>
            تعديل الرصيد
          </button>
          {player.status === 'active' ? (
            <button
              onClick={() => setConfirmAction({
                type: 'suspend',
                label: 'هل أنت متأكد من تعليق هذا اللاعب؟',
                action: () => handleStatusChange('suspended'),
              })}
              className="flex items-center gap-2 px-4 py-2.5 bg-yellow-50 text-yellow-600 dark:bg-yellow-900/20 dark:text-yellow-400 hover:bg-yellow-100 dark:hover:bg-yellow-900/30 rounded-xl font-bold text-sm smooth-transition"
            >
              <iconify-icon icon="lucide:pause" class="text-lg"></iconify-icon>
              تعليق
            </button>
          ) : (
            <button
              onClick={() => setConfirmAction({
                type: 'activate',
                label: 'هل أنت متأكد من تفعيل هذا اللاعب؟',
                action: () => handleStatusChange('active'),
              })}
              className="flex items-center gap-2 px-4 py-2.5 bg-brand-success/10 text-brand-success hover:bg-brand-success/20 rounded-xl font-bold text-sm smooth-transition"
            >
              <iconify-icon icon="lucide:play" class="text-lg"></iconify-icon>
              تفعيل
            </button>
          )}
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
          <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">الحماية</div>
          <div className="flex items-center justify-center gap-1">
            {PROTECTION_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => handleProtectionChange(opt.value)}
                className={`p-1.5 rounded-lg smooth-transition ${
                  player.protection === opt.value
                    ? 'bg-gray-200 dark:bg-gray-700 ring-2 ring-brand-teal/30'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-800 opacity-40 hover:opacity-80'
                }`}
                title={opt.label}
              >
                <iconify-icon icon={opt.icon} class={`text-lg ${opt.color}`}></iconify-icon>
              </button>
            ))}
          </div>
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

      {/* Adjust Balance Modal */}
      {adjustModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setAdjustModal(false)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4">
              تعديل رصيد — {player.alias}
            </h3>
            <form onSubmit={handleAdjustBalance} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">المبلغ (موجب = إضافة، سالب = خصم)</label>
                <input
                  type="number"
                  value={adjustAmount}
                  onChange={e => setAdjustAmount(e.target.value)}
                  required
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
                  placeholder="500 أو -200"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input
                  type="text"
                  value={adjustReason}
                  onChange={e => setAdjustReason(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white"
                  placeholder="تعديل إداري"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={adjusting}
                  className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60"
                >
                  {adjusting ? 'جارٍ التعديل...' : 'تعديل الرصيد'}
                </button>
                <button
                  type="button"
                  onClick={() => setAdjustModal(false)}
                  className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
                >
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setConfirmAction(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-sm text-center" onClick={e => e.stopPropagation()}>
            <iconify-icon icon="lucide:alert-triangle" class="text-4xl text-yellow-500 mb-3"></iconify-icon>
            <p className="font-bold text-gray-900 dark:text-white mb-6">{confirmAction.label}</p>
            <div className="flex gap-3">
              <button
                onClick={confirmAction.action}
                className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition"
              >
                تأكيد
              </button>
              <button
                onClick={() => setConfirmAction(null)}
                className="flex-1 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition"
              >
                إلغاء
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
