/**
 * AdminPlayerDetailPage — Full operational workspace for a competition member.
 *
 * Sections:
 *   1. Identity & membership context (account link, alias, competition, season/cycle)
 *   2. Gameplay state (balance, rank, attacks, protection, bankruptcy)
 *   3. Inventory (owned items with status, grant/revoke actions)
 *   4. Ledger history
 *   5. Attack history
 *
 * Admin actions: adjust balance, change status, set protection, send alert,
 *   grant item, revoke item.
 */

import { useState, useCallback, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiFetch } from '../../lib/api'

const ENTRY_TYPE_LABELS = {
  initial_balance: 'رصيد أولي', question_reward: 'مكافأة سؤال', attack_reward: 'مكافأة هجوم',
  attack_penalty: 'خسارة هجوم', item_purchase: 'شراء عنصر', admin_adjustment: 'تعديل إداري',
  distribution: 'توزيع', compensation: 'تعويض', system_reward: 'مكافأة نظام', box_result: 'صندوق',
}

const STATUS_LABELS = {
  active: { text: 'نشط', color: 'bg-brand-success/10 text-brand-success' },
  suspended: { text: 'معلق', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400' },
  pending: { text: 'قيد الانتظار', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' },
  removed: { text: 'محذوف', color: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' },
  archived: { text: 'مؤرشف', color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
}

const ITEM_STATUS_LABELS = {
  available: { text: 'متوفر', color: 'bg-brand-success/10 text-brand-success' },
  activated: { text: 'مُفعّل', color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400' },
  pending: { text: 'قيد التفعيل', color: 'bg-amber-100 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400' },
  consumed: { text: 'مستهلك', color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
  expired: { text: 'منتهي', color: 'bg-red-100/50 text-red-400 dark:bg-red-900/10 dark:text-red-400' },
}

const RARITY_COLORS = {
  common: 'border-gray-300 dark:border-gray-600',
  rare: 'border-blue-400',
  epic: 'border-gray-500',
  legendary: 'border-brand-orange',
  mythic: 'border-purple-500',
}

const PROTECTION_OPTIONS = [
  { value: 'none', label: 'بدون حماية', icon: 'lucide:shield-off', color: 'text-gray-400', bg: 'hover:bg-gray-100 dark:hover:bg-gray-800' },
  { value: 'partial', label: 'حماية جزئية', icon: 'lucide:shield-half', color: 'text-amber-500', bg: 'hover:bg-amber-50 dark:hover:bg-amber-900/20' },
  { value: 'full', label: 'حماية كاملة', icon: 'lucide:shield-check', color: 'text-blue-500', bg: 'hover:bg-blue-50 dark:hover:bg-blue-900/20' },
]

export default function AdminPlayerDetailPage() {
  const { membershipId } = useParams()
  const [player, setPlayer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionMsg, setActionMsg] = useState(null)

  // Modal states
  const [adjustModal, setAdjustModal] = useState(false)
  const [adjustAmount, setAdjustAmount] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [adjusting, setAdjusting] = useState(false)

  const [alertModal, setAlertModal] = useState(false)
  const [alertTitle, setAlertTitle] = useState('')
  const [alertMessage, setAlertMessage] = useState('')
  const [alertPriority, setAlertPriority] = useState('normal')
  const [alerting, setAlerting] = useState(false)

  const [grantModal, setGrantModal] = useState(false)
  const [grantItems, setGrantItems] = useState([])
  const [grantItemId, setGrantItemId] = useState('')
  const [grantQuantity, setGrantQuantity] = useState('1')
  const [grantReason, setGrantReason] = useState('')
  const [granting, setGranting] = useState(false)

  const [revokeItem, setRevokeItem] = useState(null)
  const [revokeReason, setRevokeReason] = useState('')
  const [revoking, setRevoking] = useState(false)

  const [confirmAction, setConfirmAction] = useState(null)

  function showMsg(text, isError = false) {
    setActionMsg({ text, isError })
    setTimeout(() => setActionMsg(null), 3500)
  }

  const loadPlayer = useCallback(async () => {
    try {
      const json = await apiFetch(`/api/admin/players/${membershipId}`)
      setPlayer(json.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [membershipId])

  useEffect(() => { loadPlayer() }, [loadPlayer])

  // Load available items for grant modal
  async function openGrantModal() {
    setGrantModal(true)
    if (grantItems.length === 0) {
      try {
        const json = await apiFetch('/api/admin/store/items')
        setGrantItems((json.data || []).filter(i => i.status === 'active' || i.status === 'draft'))
      } catch {}
    }
  }

  async function handleAdjustBalance(e) {
    e.preventDefault()
    if (!adjustAmount) return
    setAdjusting(true)
    try {
      const res = await apiFetch(`/api/admin/players/${membershipId}/adjust-balance`, {
        method: 'POST',
        body: JSON.stringify({ amount: parseInt(adjustAmount), reason: adjustReason || 'تعديل إداري' }),
      })
      showMsg(res.message || 'تم تعديل الرصيد')
      setAdjustModal(false)
      setAdjustAmount('')
      setAdjustReason('')
      loadPlayer()
    } catch (err) {
      showMsg(err.message, true)
    }
    setAdjusting(false)
  }

  async function handleStatusChange(newStatus) {
    try {
      await apiFetch(`/api/admin/players/${membershipId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      showMsg(`تم تحديث الحالة إلى ${newStatus === 'active' ? 'نشط' : 'معلق'}`)
      loadPlayer()
    } catch (err) { showMsg(err.message, true) }
    setConfirmAction(null)
  }

  async function handleProtectionChange(protection) {
    try {
      const res = await apiFetch(`/api/admin/players/${membershipId}/protection`, {
        method: 'PATCH',
        body: JSON.stringify({ protection }),
      })
      showMsg(res.message || 'تم تحديث الحماية')
      loadPlayer()
    } catch (err) { showMsg(err.message, true) }
  }

  async function handleSendAlert(e) {
    e.preventDefault()
    if (!alertTitle.trim() || !alertMessage.trim()) return
    setAlerting(true)
    try {
      await apiFetch(`/api/admin/players/${membershipId}/send-alert`, {
        method: 'POST',
        body: JSON.stringify({ title: alertTitle.trim(), message: alertMessage.trim(), priority: alertPriority }),
      })
      showMsg('تم إرسال التنبيه بنجاح')
      setAlertModal(false)
      setAlertTitle('')
      setAlertMessage('')
      setAlertPriority('normal')
      loadPlayer()
    } catch (err) { showMsg(err.message, true) }
    setAlerting(false)
  }

  async function handleGrantItem(e) {
    e.preventDefault()
    if (!grantItemId) return
    setGranting(true)
    try {
      const res = await apiFetch(`/api/admin/players/${membershipId}/grant-item`, {
        method: 'POST',
        body: JSON.stringify({
          item_definition_id: grantItemId,
          quantity: parseInt(grantQuantity) || 1,
          reason: grantReason,
        }),
      })
      showMsg(res.message || 'تم منح العنصر')
      setGrantModal(false)
      setGrantItemId('')
      setGrantQuantity('1')
      setGrantReason('')
      loadPlayer()
    } catch (err) { showMsg(err.message, true) }
    setGranting(false)
  }

  async function handleRevokeItem(e) {
    e.preventDefault()
    if (!revokeItem) return
    setRevoking(true)
    try {
      const res = await apiFetch(`/api/admin/players/${membershipId}/revoke-item/${revokeItem.id}`, {
        method: 'POST',
        body: JSON.stringify({ reason: revokeReason }),
      })
      showMsg(res.message || 'تمت المصادرة')
      setRevokeItem(null)
      setRevokeReason('')
      loadPlayer()
    } catch (err) { showMsg(err.message, true) }
    setRevoking(false)
  }

  if (loading) return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  if (error || !player) return <div className="text-center py-20 text-gray-500 font-bold">{error || 'لم يتم العثور على اللاعب'}</div>

  const pst = STATUS_LABELS[player.status] || STATUS_LABELS.active

  return (
    <div className="space-y-6 max-w-7xl">
      {actionMsg && (
        <div className={`px-5 py-3 rounded-xl text-sm font-bold ${actionMsg.isError ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>
          {actionMsg.text}
        </div>
      )}

      {/* ══ Section 1: Identity & Membership Context ══ */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <Link to="/admin/members" className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition flex-shrink-0">
              <iconify-icon icon="lucide:arrow-right" class="text-lg"></iconify-icon>
            </Link>
            <div>
              <h1 className="font-display text-2xl md:text-3xl font-black text-gray-900 dark:text-white">{player.alias || player.username}</h1>
              <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400 mt-1 flex-wrap">
                <span className="font-bold">{player.real_name}</span>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <Link to={`/admin/accounts`} className="font-bold text-brand-teal dark:text-brand-slate hover:underline flex items-center gap-1">
                  <iconify-icon icon="lucide:user" class="text-sm"></iconify-icon>
                  @{player.username}
                </Link>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <span className="font-bold">{player.competition_name}</span>
                <span className={`text-xs font-black px-2 py-0.5 rounded-lg ${pst.color}`}>{pst.text}</span>
              </div>
              {(player.active_season || player.active_cycle) && (
                <div className="flex items-center gap-2 text-xs font-bold text-gray-400 mt-1">
                  <iconify-icon icon="lucide:calendar" class="text-sm"></iconify-icon>
                  {player.active_season?.name}
                  {player.active_cycle && <><span className="text-gray-300">›</span> {player.active_cycle.label}</>}
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => setAlertModal(true)} className="flex items-center gap-1.5 px-3 py-2 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded-xl font-bold text-sm smooth-transition">
              <iconify-icon icon="lucide:bell-ring" class="text-base"></iconify-icon>
              تنبيه
            </button>
            <button onClick={() => setAdjustModal(true)} className="flex items-center gap-1.5 px-3 py-2 bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate hover:bg-brand-teal/20 rounded-xl font-bold text-sm smooth-transition">
              <iconify-icon icon="lucide:coins" class="text-base"></iconify-icon>
              تعديل الرصيد
            </button>
            <button onClick={openGrantModal} className="flex items-center gap-1.5 px-3 py-2 bg-brand-success/10 text-brand-success hover:bg-brand-success/20 rounded-xl font-bold text-sm smooth-transition">
              <iconify-icon icon="lucide:gift" class="text-base"></iconify-icon>
              منح عنصر
            </button>
            {player.status === 'active' ? (
              <button onClick={() => setConfirmAction({ label: 'هل أنت متأكد من تعليق هذا اللاعب؟', action: () => handleStatusChange('suspended') })}
                className="flex items-center gap-1.5 px-3 py-2 bg-yellow-50 text-yellow-600 dark:bg-yellow-900/20 dark:text-yellow-400 hover:bg-yellow-100 rounded-xl font-bold text-sm smooth-transition">
                <iconify-icon icon="lucide:pause" class="text-base"></iconify-icon>
                تعليق
              </button>
            ) : (
              <button onClick={() => setConfirmAction({ label: 'هل أنت متأكد من تفعيل هذا اللاعب؟', action: () => handleStatusChange('active') })}
                className="flex items-center gap-1.5 px-3 py-2 bg-brand-success/10 text-brand-success hover:bg-brand-success/20 rounded-xl font-bold text-sm smooth-transition">
                <iconify-icon icon="lucide:play" class="text-base"></iconify-icon>
                تفعيل
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ══ Section 2: Gameplay State ══ */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 mb-1">الرصيد</div>
          <div className={`font-display text-2xl font-black ${player.is_bankrupt ? 'text-brand-danger' : 'text-gray-900 dark:text-white'}`}>
            {player.balance?.toLocaleString('ar-SA')}
          </div>
          {player.is_bankrupt && <span className="text-[10px] font-black text-brand-danger bg-brand-danger/10 px-1.5 py-0.5 rounded">مفلس</span>}
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 mb-1">الترتيب</div>
          <div className="font-display text-2xl font-black text-gray-900 dark:text-white">#{player.rank}</div>
          <div className="text-[10px] font-bold text-gray-400">من {player.total_active_members}</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 mb-1">الهجمات</div>
          <div className="font-heading font-black text-lg text-gray-900 dark:text-white">
            <span className="text-brand-success">{player.attacks_won}</span>
            <span className="text-gray-300 dark:text-gray-600 mx-1">/</span>
            <span>{player.attacks_sent}</span>
          </div>
          <div className="text-[10px] font-bold text-gray-400">{player.attacks_received} استُهدف</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 mb-2">الحماية</div>
          <div className="flex items-center justify-center gap-1">
            {PROTECTION_OPTIONS.map(opt => (
              <button key={opt.value} onClick={() => handleProtectionChange(opt.value)}
                className={`p-1.5 rounded-lg smooth-transition ${player.protection === opt.value ? 'bg-gray-200 dark:bg-gray-700 ring-2 ring-brand-teal/30' : `opacity-40 hover:opacity-80 ${opt.bg}`}`}
                title={opt.label}>
                <iconify-icon icon={opt.icon} class={`text-lg ${opt.color}`}></iconify-icon>
              </button>
            ))}
          </div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 mb-1">المخزون</div>
          <div className="font-heading font-black text-lg text-gray-900 dark:text-white">{player.inventory?.length || 0}</div>
          <div className="text-[10px] font-bold text-gray-400">عنصر</div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-4 text-center">
          <div className="text-[10px] font-black text-gray-400 mb-1">الإشعارات</div>
          <div className="font-heading font-black text-lg text-gray-900 dark:text-white">{player.notification_count || 0}</div>
          {player.unread_notifications > 0 && (
            <span className="text-[10px] font-black text-brand-danger">{player.unread_notifications} غير مقروء</span>
          )}
        </div>
      </div>

      {/* ══ Section 3: Inventory ══ */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white flex items-center gap-2">
            <iconify-icon icon="lucide:package" class="text-purple-500"></iconify-icon>
            المخزون
          </h2>
          <button onClick={openGrantModal} className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-success/10 text-brand-success hover:bg-brand-success/20 rounded-lg text-xs font-bold smooth-transition">
            <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
            منح عنصر
          </button>
        </div>

        {player.inventory?.length === 0 ? (
          <div className="text-center py-8 text-sm font-bold text-gray-400">
            <iconify-icon icon="lucide:package-open" class="text-3xl mb-2 block"></iconify-icon>
            لا توجد عناصر في المخزون
          </div>
        ) : (
          <div className="space-y-2">
            {player.inventory.map(item => {
              const ist = ITEM_STATUS_LABELS[item.status] || ITEM_STATUS_LABELS.available
              const canRevoke = item.status !== 'consumed' && item.status !== 'expired'
              return (
                <div key={item.id} className={`flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl border-r-4 ${RARITY_COLORS[item.rarity] || RARITY_COLORS.common}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="min-w-0">
                      <div className="font-bold text-sm text-gray-900 dark:text-white flex items-center gap-2">
                        {item.name}
                        {item.quantity > 1 && <span className="text-[10px] font-black bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded">x{item.quantity}</span>}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-gray-400 mt-0.5 flex-wrap">
                        <span className={`font-black px-1.5 py-0.5 rounded ${ist.color}`}>{ist.text}</span>
                        <span>{item.rarity}</span>
                        <span>{item.source_type === 'admin_grant' ? 'منحة إدارية' : item.source_type === 'purchase' ? 'شراء' : item.source_type}</span>
                        {item.uses_remaining != null && <span>استخدامات: {item.uses_remaining}</span>}
                        {item.expires_at && <span>ينتهي: {new Date(item.expires_at).toLocaleDateString('ar')}</span>}
                      </div>
                    </div>
                  </div>
                  {canRevoke && (
                    <button onClick={() => setRevokeItem(item)}
                      className="flex items-center gap-1 px-2.5 py-1.5 bg-brand-danger/10 text-brand-danger hover:bg-brand-danger/20 rounded-lg text-xs font-bold smooth-transition flex-shrink-0"
                      title="مصادرة العنصر">
                      <iconify-icon icon="lucide:trash-2" class="text-sm"></iconify-icon>
                      مصادرة
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ══ Section 4+5: Ledger + Attacks Grid ══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ledger */}
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:receipt" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
            سجل النقاط
          </h2>
          {player.ledger?.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-6">لا توجد حركات</p>
          ) : (
            <div className="space-y-2 max-h-[28rem] overflow-y-auto">
              {player.ledger?.map(le => (
                <div key={le.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl text-sm">
                  <div className="min-w-0">
                    <div className="font-bold text-gray-700 dark:text-gray-300">{ENTRY_TYPE_LABELS[le.entry_type] || le.entry_type}</div>
                    {le.reason && <div className="text-[11px] text-gray-400 truncate">{le.reason}</div>}
                    <div className="text-[10px] text-gray-400">{le.created_at ? new Date(le.created_at).toLocaleString('ar') : ''}</div>
                  </div>
                  <div className="text-left flex-shrink-0 mr-3">
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
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-800 rounded-2xl p-6">
          <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:swords" class="text-brand-orange"></iconify-icon>
            سجل الهجمات
          </h2>
          {player.attacks?.length === 0 ? (
            <p className="text-center text-gray-400 text-sm py-6">لا توجد هجمات</p>
          ) : (
            <div className="space-y-2 max-h-[28rem] overflow-y-auto">
              {player.attacks?.map(a => {
                const outColor = a.outcome === 'succeeded' ? 'bg-brand-success/10 text-brand-success' : a.outcome === 'failed' ? 'bg-brand-danger/10 text-brand-danger' : 'bg-gray-100 text-gray-500'
                const outLabel = a.outcome === 'succeeded' ? 'نجاح' : a.outcome === 'failed' ? 'فشل' : a.outcome
                return (
                  <div key={a.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl text-sm">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${outColor}`}>{outLabel}</span>
                      <span className="font-bold text-gray-700 dark:text-gray-300">
                        {a.role === 'attacker' ? `→ ${a.target_alias}` : `← ${a.attacker_alias}`}
                      </span>
                    </div>
                    <div className="flex-shrink-0">
                      {a.reward_amount > 0 && <span className="text-brand-success font-black text-xs ml-2">+{a.reward_amount}</span>}
                      {a.penalty_amount > 0 && <span className="text-brand-danger font-black text-xs ml-2">-{a.penalty_amount}</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* ══ Modals ══ */}

      {/* Adjust Balance Modal */}
      {adjustModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setAdjustModal(false)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4">تعديل رصيد — {player.alias}</h3>
            <form onSubmit={handleAdjustBalance} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">المبلغ (موجب = إضافة، سالب = خصم)</label>
                <input type="number" value={adjustAmount} onChange={e => setAdjustAmount(e.target.value)} required placeholder="500 أو -200"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input type="text" value={adjustReason} onChange={e => setAdjustReason(e.target.value)} placeholder="تعديل إداري"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={adjusting} className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
                  {adjusting ? 'جارٍ التعديل...' : 'تعديل الرصيد'}
                </button>
                <button type="button" onClick={() => setAdjustModal(false)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Send Alert Modal */}
      {alertModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setAlertModal(false)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <iconify-icon icon="lucide:bell-ring" class="text-purple-500"></iconify-icon>
              إرسال تنبيه — {player.alias}
            </h3>
            <form onSubmit={handleSendAlert} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">العنوان <span className="text-brand-danger">*</span></label>
                <input type="text" value={alertTitle} onChange={e => setAlertTitle(e.target.value)} required placeholder="عنوان التنبيه"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الرسالة <span className="text-brand-danger">*</span></label>
                <textarea value={alertMessage} onChange={e => setAlertMessage(e.target.value)} required placeholder="نص التنبيه..." rows={3}
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white resize-none" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الأولوية</label>
                <select value={alertPriority} onChange={e => setAlertPriority(e.target.value)}
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white">
                  <option value="low">منخفضة</option>
                  <option value="normal">عادية</option>
                  <option value="high">عالية</option>
                  <option value="urgent">عاجلة</option>
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={alerting} className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
                  {alerting ? 'جارٍ الإرسال...' : 'إرسال التنبيه'}
                </button>
                <button type="button" onClick={() => setAlertModal(false)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Grant Item Modal */}
      {grantModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setGrantModal(false)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <iconify-icon icon="lucide:gift" class="text-brand-success"></iconify-icon>
              منح عنصر — {player.alias}
            </h3>
            <form onSubmit={handleGrantItem} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">العنصر <span className="text-brand-danger">*</span></label>
                <select value={grantItemId} onChange={e => setGrantItemId(e.target.value)} required
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white">
                  <option value="">اختر العنصر...</option>
                  {grantItems.map(i => (
                    <option key={i.id} value={i.id}>{i.name} ({i.rarity})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">الكمية</label>
                <input type="number" value={grantQuantity} onChange={e => setGrantQuantity(e.target.value)} min="1" max="99"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input type="text" value={grantReason} onChange={e => setGrantReason(e.target.value)} placeholder="اختياري — سبب المنح"
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={granting} className="flex-1 bg-brand-success hover:bg-brand-success/90 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
                  {granting ? 'جارٍ المنح...' : 'منح العنصر'}
                </button>
                <button type="button" onClick={() => setGrantModal(false)} className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Revoke Item Modal */}
      {revokeItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setRevokeItem(null)}>
          <div className="bg-white dark:bg-brand-card-dark rounded-2xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
            <div className="text-center mb-4">
              <iconify-icon icon="lucide:alert-triangle" class="text-4xl text-brand-danger mb-2"></iconify-icon>
              <h3 className="font-heading font-black text-lg text-gray-900 dark:text-white">مصادرة عنصر</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                هل تريد مصادرة <span className="font-black text-gray-900 dark:text-white">{revokeItem.name}</span> من {player.alias}؟
              </p>
            </div>
            <form onSubmit={handleRevokeItem} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">السبب</label>
                <input type="text" value={revokeReason} onChange={e => setRevokeReason(e.target.value)} placeholder="سبب المصادرة..."
                  className="w-full bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 py-3 px-4 rounded-xl font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/10 focus:border-brand-teal dark:text-white" />
              </div>
              <div className="flex gap-3">
                <button type="submit" disabled={revoking} className="flex-1 bg-brand-danger hover:bg-brand-danger/90 text-white py-3 rounded-xl font-heading font-black smooth-transition disabled:opacity-60">
                  {revoking ? 'جارٍ المصادرة...' : 'تأكيد المصادرة'}
                </button>
                <button type="button" onClick={() => setRevokeItem(null)} className="flex-1 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
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
              <button onClick={confirmAction.action} className="flex-1 bg-brand-teal hover:bg-brand-teal-hover text-white py-3 rounded-xl font-heading font-black smooth-transition">تأكيد</button>
              <button onClick={() => setConfirmAction(null)} className="flex-1 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 smooth-transition">إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
