import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import useDashboard from '../hooks/useDashboard'
import { apiFetch } from '../lib/api'
import CycleCountdown from '../components/CycleCountdown'

const RARITY_COLORS = {
  common: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  rare: 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
  epic: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  legendary: 'bg-orange-50 text-brand-orange dark:bg-orange-900/20 dark:text-orange-400',
  mythic: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
}

export default function DashboardPage() {
  const { data, loading, error } = useDashboard()
  const [attacks, setAttacks] = useState([])
  const [inventory, setInventory] = useState([])
  const [usingItemId, setUsingItemId] = useState(null)
  const [itemMessage, setItemMessage] = useState(null)

  useEffect(() => {
    if (data) {
      const cid = data.competition_id
      const qs = cid ? `?competition_id=${cid}` : ''
      apiFetch(`/api/me/attacks${qs}`).then(r => { if (r.data) setAttacks(r.data) }).catch(() => {})
      apiFetch(`/api/me/inventory-details${qs}`).then(r => { if (r.data) setInventory(r.data) }).catch(() => {})
    }
  }, [data])

  async function handleUseItem(ownedItemId) {
    setUsingItemId(ownedItemId)
    setItemMessage(null)
    try {
      const cid = data?.competition_id
      const qs = cid ? `?competition_id=${cid}` : ''
      const res = await apiFetch(`/api/me/inventory/${ownedItemId}/use${qs}`, { method: 'POST' })
      setItemMessage({ type: 'success', text: res.message || 'تم استخدام العنصر بنجاح' })
      // Refresh inventory
      const inv = await apiFetch(`/api/me/inventory-details${qs}`)
      if (inv.data) setInventory(inv.data)
    } catch (err) {
      setItemMessage({ type: 'error', text: err.message })
    } finally {
      setUsingItemId(null)
      setTimeout(() => setItemMessage(null), 3000)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal dark:text-brand-slate animate-spin"></iconify-icon>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20 gap-4">
        <iconify-icon icon="lucide:alert-circle" class="text-4xl text-brand-danger"></iconify-icon>
        <p className="text-gray-600 dark:text-gray-400 font-bold">{error || 'لم يتم العثور على بيانات المنافسة. يرجى الانضمام أولاً.'}</p>
        <Link to="/join" className="text-brand-teal dark:text-brand-slate font-bold hover:underline">انضم للمنافسة</Link>
      </div>
    )
  }

  const avatarLetter = data.alias ? data.alias[0] : '?'

  return (
    <div className="flex-1 w-full max-w-7xl mx-auto px-4 py-8 md:py-12 space-y-8 relative z-10">

      {/* 1. Hero Section */}
      <section className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-[2rem] p-6 md:p-10 shadow-sm relative overflow-hidden group smooth-transition hover:shadow-md dark:hover:shadow-black/20">
        <div className="absolute -top-12 -right-12 w-64 h-64 bg-brand-teal/5 dark:bg-brand-slate/10 rounded-full blur-3xl group-hover:bg-brand-teal/10 transition-colors"></div>
        <div className="absolute -bottom-10 -left-10 w-48 h-48 bg-brand-orange/5 dark:bg-[#D84315]/10 rounded-full blur-2xl"></div>

        <div className="flex flex-col md:flex-row items-center gap-8 md:gap-12 relative z-10">
          {/* Avatar */}
          <div className="relative flex-shrink-0">
            <div className="w-40 h-40 md:w-48 md:h-48 bg-gradient-to-br from-brand-teal to-brand-teal-light dark:from-brand-slate dark:to-[#4f5c6e] rounded-3xl flex items-center justify-center text-white text-7xl font-black shadow-lg shadow-brand-teal/20 dark:shadow-none smooth-transition group-hover:scale-105">
              {avatarLetter}
            </div>
          </div>

          {/* Player Info */}
          <div className="flex-1 text-center md:text-right space-y-4">
            <div className="flex flex-col md:flex-row md:items-center gap-4 justify-center md:justify-start">
              <div className="flex items-center gap-3">
                <iconify-icon icon="lucide:crown" class="text-amber-500 text-4xl drop-shadow-sm"></iconify-icon>
                <h1 className="text-4xl lg:text-5xl font-display font-black text-gray-900 dark:text-white tracking-tight">{data.alias}</h1>
              </div>
            </div>

            <p className="text-gray-600 dark:text-gray-400 font-medium text-lg">{data.competition_name}</p>

            {/* Season / Cycle context */}
            {data.season_name && (
              <div className="flex flex-wrap items-center justify-center md:justify-start gap-3 text-sm">
                <span className="flex items-center gap-1.5 bg-brand-teal/10 dark:bg-brand-slate/10 text-brand-teal dark:text-brand-slate px-3 py-1.5 rounded-lg font-bold">
                  <iconify-icon icon="lucide:calendar-range" class="text-sm"></iconify-icon>
                  {data.season_name}
                </span>
                {data.cycle_label && (
                  <span className="flex items-center gap-1.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 rounded-lg font-bold">
                    <iconify-icon icon="lucide:repeat" class="text-sm"></iconify-icon>
                    {data.cycle_label}
                  </span>
                )}
              </div>
            )}

            {/* Cycle Countdown */}
            {data.cycle_ends_at && (
              <div className="flex justify-center md:justify-start">
                <CycleCountdown
                  cycleEndsAt={data.cycle_ends_at}
                  cycleLabel={data.cycle_label}
                  nextCycleLabel={data.next_cycle_label}
                />
              </div>
            )}

            <div className="pt-3 flex flex-wrap justify-center md:justify-start gap-4">
              <div className="flex items-center gap-2 bg-gray-50 dark:bg-gray-800/40 px-5 py-3 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md smooth-transition">
                <iconify-icon icon="lucide:trophy" class="text-brand-orange text-xl"></iconify-icon>
                <span className="font-bold text-gray-800 dark:text-white">المركز {data.rank}</span>
              </div>
              <div className="flex items-center gap-2 bg-gray-50 dark:bg-gray-800/40 px-5 py-3 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md smooth-transition">
                <iconify-icon icon="lucide:zap" class="text-brand-teal dark:text-brand-slate text-xl"></iconify-icon>
                <span className="font-bold text-gray-800 dark:text-white">{data.balance.toLocaleString('ar-SA')} نقطة</span>
              </div>
            </div>
          </div>

          {/* CTA Action — context-aware */}
          <div className="w-full md:w-auto mt-4 md:mt-0">
            {data.is_bankrupt ? (
              <div className="w-full md:w-auto bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 px-8 py-4 md:py-5 rounded-2xl font-heading font-black text-xl flex items-center justify-center gap-3 cursor-not-allowed">
                <iconify-icon icon="lucide:ghost" class="text-3xl"></iconify-icon>
                مفلس — لا يمكن الهجوم
              </div>
            ) : data.protection === 'full' ? (
              <Link to="/lobby" id="btn-start-battle" className="btn-press w-full md:w-auto bg-purple-100 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 px-8 py-4 md:py-5 rounded-2xl font-heading font-black text-xl flex items-center justify-center gap-3 smooth-transition hover:-translate-y-1">
                <iconify-icon icon="lucide:shield-check" class="text-3xl"></iconify-icon>
                محمي — الساحة
              </Link>
            ) : (
              <Link to="/lobby" id="btn-start-battle" className="btn-press w-full md:w-auto bg-gradient-to-r from-brand-orange to-[#e65100] hover:from-[#e65100] hover:to-[#ff5722] dark:from-[#D84315] dark:to-[#c63f13] text-white px-8 py-4 md:py-5 rounded-2xl font-heading font-black text-xl shadow-lg shadow-brand-orange/20 dark:shadow-[0_4px_12px_rgba(216,67,21,0.2)] flex items-center justify-center gap-3 smooth-transition hover:-translate-y-1">
                <iconify-icon icon="lucide:swords" class="text-3xl"></iconify-icon>
                ابدأ الهجوم
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* 2. Stats Grid */}
      <section className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-5 md:gap-7">
        {/* Stat 1: Attacks */}
        <div className="bg-white dark:bg-brand-card-dark p-8 md:p-10 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md dark:hover:shadow-black/20 smooth-transition flex flex-col items-center justify-center text-center group hover:-translate-y-1">
          <iconify-icon icon="lucide:swords" class="text-brand-teal dark:text-brand-slate mb-3 text-5xl group-hover:scale-110 smooth-transition drop-shadow-sm"></iconify-icon>
          <span className="text-gray-500 dark:text-gray-400 text-xs font-black uppercase tracking-widest mb-1">الهجمات</span>
          <div className="text-5xl md:text-6xl font-black text-gray-900 dark:text-white">{data.attacks_sent}</div>
        </div>
        {/* Stat 2: Win Rate */}
        <div className="bg-white dark:bg-brand-card-dark p-8 md:p-10 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md dark:hover:shadow-black/20 smooth-transition flex flex-col items-center justify-center text-center group hover:-translate-y-1">
          <iconify-icon icon="lucide:target" class="text-brand-success mb-3 text-5xl group-hover:scale-110 smooth-transition drop-shadow-sm"></iconify-icon>
          <span className="text-gray-500 dark:text-gray-400 text-xs font-black uppercase tracking-widest mb-1">نسبة الفوز</span>
          <div className="text-5xl md:text-6xl font-black text-gray-900 dark:text-white">{data.win_rate}%</div>
        </div>
        {/* Stat 3: Defenses */}
        <div className="bg-white dark:bg-brand-card-dark p-8 md:p-10 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md dark:hover:shadow-black/20 smooth-transition flex flex-col items-center justify-center text-center group hover:-translate-y-1">
          <iconify-icon icon="lucide:shield-check" class="text-brand-orange mb-3 text-5xl group-hover:scale-110 smooth-transition drop-shadow-sm"></iconify-icon>
          <span className="text-gray-500 dark:text-gray-400 text-xs font-black uppercase tracking-widest mb-1">الدفاعات</span>
          <div className="text-5xl md:text-6xl font-black text-gray-900 dark:text-white">{data.attacks_defended}</div>
        </div>
        {/* Stat 4: Received */}
        <div className="bg-white dark:bg-brand-card-dark p-8 md:p-10 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md dark:hover:shadow-black/20 smooth-transition flex flex-col items-center justify-center text-center group border-b-4 border-b-brand-danger hover:-translate-y-1">
          <iconify-icon icon="lucide:shield-x" class="text-brand-danger mb-3 text-5xl group-hover:scale-110 smooth-transition drop-shadow-sm"></iconify-icon>
          <span className="text-gray-500 dark:text-gray-400 text-xs font-black uppercase tracking-widest mb-1">تلقى هجوم</span>
          <div className="text-5xl md:text-6xl font-black text-brand-danger">{data.attacks_received}</div>
        </div>
      </section>

      {/* 3. Secondary Content Grid (2/3 + 1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* Left Column (lg:col-span-8) */}
        <div className="lg:col-span-8 space-y-8">

          {/* History Card */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-3xl overflow-hidden shadow-sm">
            <div className="px-8 py-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/20">
              <div className="flex items-center gap-3">
                <iconify-icon icon="lucide:history" class="text-2xl text-gray-400"></iconify-icon>
                <h3 className="font-heading font-black text-xl text-gray-900 dark:text-white">سجل المعارك الأخيرة</h3>
              </div>
            </div>
            {attacks.length === 0 ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400 font-bold">
                <p>لم تقم بأي هجوم بعد. ابدأ أولى معاركك!</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                {attacks.slice(0, 8).map(atk => {
                  const isAttacker = atk.role === 'attacker'
                  const won = (isAttacker && atk.outcome === 'succeeded') || (!isAttacker && atk.outcome === 'failed')
                  return (
                    <div key={atk.id} className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/30 smooth-transition">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${won ? 'bg-emerald-50 dark:bg-emerald-900/10 text-emerald-500' : 'bg-red-50 dark:bg-red-900/10 text-red-500'}`}>
                          <iconify-icon icon={won ? 'lucide:shield-check' : 'lucide:shield-x'}></iconify-icon>
                        </div>
                        <div>
                          <div className="text-sm font-bold text-gray-900 dark:text-white">
                            {isAttacker ? `هجوم على ${atk.opponent_alias}` : `هجوم من ${atk.opponent_alias}`}
                          </div>
                          <div className="text-xs text-gray-400">
                            {atk.created_at ? new Date(atk.created_at).toLocaleDateString('ar-SA') : ''}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {isAttacker ? (
                          atk.outcome === 'succeeded' ? (
                            <span className="font-heading font-black text-brand-success text-sm">+{atk.reward_amount}</span>
                          ) : (
                            <span className="font-heading font-black text-brand-danger text-sm">-{atk.penalty_amount}</span>
                          )
                        ) : (
                          atk.outcome === 'succeeded' ? (
                            <span className="font-heading font-black text-brand-danger text-sm">-{atk.reward_amount}</span>
                          ) : (
                            <span className="font-heading font-black text-brand-success text-sm">دفاع ناجح</span>
                          )
                        )}
                        <Link to={`/players/${atk.opponent_membership_id}`} className="text-xs text-brand-teal dark:text-brand-slate hover:underline">عرض</Link>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Quick Items / Collection */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-3xl p-8 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <iconify-icon icon="lucide:package" class="text-2xl text-brand-orange"></iconify-icon>
                <h3 className="font-heading font-black text-xl text-gray-900 dark:text-white">مخزني</h3>
                <span className="text-sm font-bold text-gray-400">({data.inventory_count} عنصر)</span>
              </div>
              <Link to="/store" className="text-sm font-bold text-brand-teal dark:text-brand-slate hover:underline">فتح المتجر</Link>
            </div>
            {itemMessage && (
              <div className={`px-4 py-2 rounded-xl text-sm font-bold mb-4 ${itemMessage.type === 'success' ? 'bg-brand-success/10 text-brand-success' : 'bg-brand-danger/10 text-brand-danger'}`}>
                {itemMessage.text}
              </div>
            )}
            {inventory.length === 0 ? (
              <div className="text-center py-6 text-gray-500 dark:text-gray-400 font-bold">
                <iconify-icon icon="lucide:package-open" class="text-4xl text-gray-300 dark:text-gray-600 mb-2"></iconify-icon>
                <p>المخزن فارغ — زُر المتجر واشترِ أدوات القتال!</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {inventory.slice(0, 6).map(item => (
                  <div key={item.id} className="flex flex-col gap-2 p-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-black ${RARITY_COLORS[item.rarity] || RARITY_COLORS.common}`}>
                        {item.rarity}
                      </span>
                      <span className="text-xs font-bold text-gray-700 dark:text-gray-300 truncate">{item.name}</span>
                    </div>
                    {item.status === 'available' && (
                      <button
                        onClick={() => handleUseItem(item.owned_item_id || item.id)}
                        disabled={usingItemId === (item.owned_item_id || item.id)}
                        className="w-full flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[11px] font-black bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate hover:bg-brand-teal/20 dark:hover:bg-brand-slate/20 smooth-transition disabled:opacity-50"
                      >
                        {usingItemId === (item.owned_item_id || item.id) ? (
                          <iconify-icon icon="lucide:loader-2" class="text-xs animate-spin"></iconify-icon>
                        ) : (
                          <iconify-icon icon="lucide:zap" class="text-xs"></iconify-icon>
                        )}
                        استخدام
                      </button>
                    )}
                    {item.status === 'activated' && (
                      <span className="w-full text-center text-[10px] font-black text-brand-success">مُفعّل</span>
                    )}
                  </div>
                ))}
                {inventory.length > 6 && (
                  <Link to="/store" className="flex items-center justify-center p-3 rounded-xl border border-dashed border-gray-200 dark:border-gray-700 text-xs font-bold text-brand-teal dark:text-brand-slate hover:bg-brand-teal/5 smooth-transition">
                    +{inventory.length - 6} عنصر آخر
                  </Link>
                )}
              </div>
            )}
          </div>

        </div>

        {/* Right Column (lg:col-span-4) */}
        <div className="lg:col-span-4 space-y-8">

          {/* Streak Card */}
          <div className="bg-gradient-to-r from-amber-500 to-brand-orange text-white rounded-3xl p-6 shadow-md relative overflow-hidden group smooth-transition hover:-translate-y-1">
            <div className="absolute -right-4 top-1/2 -translate-y-1/2 opacity-20">
              <iconify-icon icon="lucide:flame" class="text-8xl"></iconify-icon>
            </div>
            <div className="relative z-10 flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
                <iconify-icon icon="lucide:flame" class="text-3xl text-white drop-shadow-md"></iconify-icon>
              </div>
              <div>
                <div className="text-sm font-bold text-white/90 uppercase tracking-widest mb-1">هجمات ناجحة</div>
                <div className="font-heading font-black text-2xl drop-shadow-sm">{data.attacks_won} من {data.attacks_sent}</div>
              </div>
            </div>
          </div>

          {/* Quick Info */}
          <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-3xl p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-6">
              <iconify-icon icon="lucide:info" class="text-2xl text-brand-teal dark:text-brand-slate"></iconify-icon>
              <h3 className="font-heading font-black text-xl text-gray-900 dark:text-white">ملخص سريع</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                <span className="text-sm font-bold text-gray-600 dark:text-gray-400">الحماية</span>
                <span className="text-sm font-black text-gray-900 dark:text-white">{data.protection === 'none' ? 'بدون حماية' : data.protection === 'partial' ? 'حماية جزئية' : 'حماية كاملة'}</span>
              </div>
              <Link to="/notifications" className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800/60 smooth-transition">
                <span className="text-sm font-bold text-gray-600 dark:text-gray-400">الإشعارات</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-black text-gray-900 dark:text-white">{data.unread_notifications} غير مقروء</span>
                  {data.unread_notifications > 0 && (
                    <span className="w-2.5 h-2.5 bg-brand-danger rounded-full animate-pulse"></span>
                  )}
                </div>
              </Link>
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                <span className="text-sm font-bold text-gray-600 dark:text-gray-400">إجمالي المتسابقين</span>
                <span className="text-sm font-black text-gray-900 dark:text-white">{data.total_members}</span>
              </div>
              {data.season_name && (
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                  <span className="text-sm font-bold text-gray-600 dark:text-gray-400">الموسم</span>
                  <span className="text-sm font-black text-gray-900 dark:text-white">{data.season_name}</span>
                </div>
              )}
              {data.cycle_label && (
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
                  <span className="text-sm font-bold text-gray-600 dark:text-gray-400">الدورة</span>
                  <span className="text-sm font-black text-gray-900 dark:text-white">{data.cycle_label}</span>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

    </div>
  )
}
