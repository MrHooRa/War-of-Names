import { useState, useEffect } from 'react'
import useCompetitionContext from '../hooks/useCompetitionContext'
import useStore from '../hooks/useStore'
import useInventory from '../hooks/useInventory'
import useBuyItem from '../hooks/useBuyItem'
import { apiFetch } from '../lib/api'
import InventoryItemCard from '../components/InventoryItemCard'
import { RARITY_CONFIG, CATEGORY_ICONS, CATEGORY_COLORS, CATEGORY_GLOW } from '../config/rarity'

const RARITY_ORDER = { common: 0, rare: 1, epic: 2, legendary: 3, mythic: 4 }

function StoreItem({ listing, onBuy, buying, playerBalance }) {
  const rarity = RARITY_CONFIG[listing.rarity] || RARITY_CONFIG.common
  const icon = CATEGORY_ICONS[listing.category] || 'lucide:package'
  const iconColor = CATEGORY_COLORS[listing.category] || 'text-gray-500'
  const glowBg = CATEGORY_GLOW[listing.category] || 'bg-gray-400'
  const isMythic = listing.rarity === 'mythic'
  const isLegendary = listing.rarity === 'legendary'
  const outOfStock = listing.stock_remaining !== null && listing.stock_remaining <= 0
  const cantAfford = playerBalance !== null && listing.price > playerBalance

  return (
    <div className={`group bg-white dark:bg-brand-card-dark border ${rarity.border} ${rarity.ring} ${rarity.glow} rounded-2xl hover:shadow-md dark:hover:shadow-black/20 smooth-transition flex flex-col min-h-[360px] p-5 ${isMythic ? 'sm:col-span-2 xl:col-span-3 xl:w-4/5 xl:mx-auto relative overflow-hidden' : 'relative overflow-hidden'}`}>
      {/* High-tier ambient glow */}
      {isMythic && (
        <div className="absolute inset-0 bg-red-500 opacity-[0.03] dark:opacity-[0.06] blur-3xl rounded-full group-hover:opacity-[0.06] dark:group-hover:opacity-[0.12] smooth-transition"></div>
      )}
      {isLegendary && (
        <div className="absolute inset-0 bg-amber-400 opacity-[0.02] dark:opacity-[0.04] blur-3xl rounded-full group-hover:opacity-[0.04] dark:group-hover:opacity-[0.08] smooth-transition"></div>
      )}

      <div className="flex-1 flex flex-col items-center text-center relative z-10">
        {!isMythic && (
          <div className="relative bg-gray-50 dark:bg-gray-800/50 w-full aspect-[4/3] rounded-xl flex items-center justify-center mb-5 overflow-hidden">
            <div className={`absolute inset-0 ${glowBg} opacity-5 dark:opacity-[0.03] blur-xl rounded-full group-hover:opacity-15 dark:group-hover:opacity-10 smooth-transition`}></div>
            <iconify-icon icon={icon} class={`text-6xl ${iconColor} group-hover:scale-110 smooth-transition relative z-10`}></iconify-icon>
            <span className={`absolute top-3 right-3 ${rarity.badge} text-[10px] font-black px-2.5 py-1 rounded shadow-sm`}>{rarity.label}</span>
          </div>
        )}

        {isMythic && (
          <>
            <div className="mb-6 mt-2 relative">
              <iconify-icon icon="mdi:sword-cross" class="text-7xl md:text-8xl text-red-500 group-hover:scale-110 smooth-transition drop-shadow-[0_0_15px_rgba(220,38,38,0.3)]"></iconify-icon>
            </div>
            <div className="mb-4">
              <span className={`text-[10px] font-black ${rarity.badge} px-4 py-1.5 rounded-full border border-red-400/20`}>{rarity.label}</span>
            </div>
          </>
        )}

        <h3 className={`font-heading font-black ${isMythic ? 'text-2xl md:text-3xl' : 'text-xl'} text-gray-900 dark:text-white`}>
          {listing.name}
        </h3>
        <p className={`${isMythic ? 'text-sm md:text-base' : 'text-sm'} font-medium text-gray-500 dark:text-gray-400 mt-2 leading-relaxed px-1 ${isMythic ? 'max-w-lg' : ''}`}>
          {listing.description}
        </p>

        {/* Effect Summaries */}
        {listing.effects?.length > 0 && (
          <div className={`mt-3 w-full space-y-1.5 ${isMythic ? 'max-w-md mx-auto' : ''}`}>
            {listing.effects.map((eff, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-1.5 bg-brand-teal/5 dark:bg-brand-slate/10 rounded-lg">
                <iconify-icon icon="lucide:sparkles" class={`text-xs ${rarity.accent} flex-shrink-0`}></iconify-icon>
                <span className="text-xs font-bold text-gray-600 dark:text-gray-300">{eff}</span>
              </div>
            ))}
          </div>
        )}

        {!isMythic && listing.stock_remaining !== null && (
          <div className="mt-auto pt-5 w-full">
            <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-700 w-full flex justify-between items-center">
              <span className="text-[11px] font-heading font-bold text-gray-500 dark:text-gray-400 uppercase">المتبقي</span>
              <span className={`text-xs font-bold ${listing.stock_remaining <= 3 ? 'text-brand-danger' : 'text-amber-500'}`}>{listing.stock_remaining} وحدة</span>
            </div>
          </div>
        )}
      </div>

      {/* Buy CTA */}
      <button
        onClick={() => onBuy(listing.listing_id)}
        disabled={buying || outOfStock || cantAfford}
        className={`btn-press ${isMythic
          ? 'w-full md:w-2/3 mx-auto font-heading font-black text-lg py-4 rounded-xl flex items-center justify-center gap-2 smooth-transition mt-8 relative z-10'
          : 'w-full font-heading font-bold py-3 rounded-xl flex items-center justify-center gap-2 smooth-transition mt-4'
        } ${cantAfford && !outOfStock
          ? 'bg-amber-50 dark:bg-amber-900/10 border-2 border-amber-400/40 text-amber-600 dark:text-amber-400 cursor-not-allowed opacity-80'
          : outOfStock
            ? (isMythic
              ? 'bg-gradient-to-r from-red-600 to-amber-500 text-white shadow-lg shadow-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed'
              : 'bg-brand-teal text-white dark:bg-brand-slate dark:text-white disabled:opacity-50 disabled:cursor-not-allowed')
            : (isMythic
              ? 'bg-gradient-to-r from-red-600 to-amber-500 text-white hover:from-red-700 hover:to-amber-600 shadow-lg shadow-red-500/20'
              : 'bg-brand-teal text-white dark:bg-brand-slate dark:text-white hover:bg-brand-teal-hover dark:hover:bg-brand-slate/80')
        } disabled:cursor-not-allowed`}
      >
        {buying ? (
          <iconify-icon icon="lucide:loader-2" class="text-lg animate-spin"></iconify-icon>
        ) : outOfStock ? (
          <iconify-icon icon="lucide:x-circle" class={isMythic ? 'text-2xl' : 'text-lg'}></iconify-icon>
        ) : cantAfford ? (
          <iconify-icon icon="lucide:wallet" class={isMythic ? 'text-2xl' : 'text-lg'}></iconify-icon>
        ) : (
          <iconify-icon icon="lucide:shopping-cart" class={isMythic ? 'text-2xl' : 'text-lg'}></iconify-icon>
        )}
        {outOfStock ? 'نفذت الكمية' : cantAfford ? 'رصيد غير كافٍ' : `${listing.price.toLocaleString('ar-SA')} نقطة`}
      </button>
    </div>
  )
}


export default function StorePage() {
  const { competitionId } = useCompetitionContext()
  const { listings, playerBalance, loading, error } = useStore(competitionId)
  const { items: inventoryItems, maxCapacity, loading: invLoading, refetch: refetchInventory } = useInventory()
  const { buying, error: buyError, buyItem } = useBuyItem(competitionId)
  const [toast, setToast] = useState(null)
  const [category, setCategory] = useState('all')
  const [sortBy, setSortBy] = useState('default')
  const [usingItem, setUsingItem] = useState(false)

  useEffect(() => {
    if (buyError) {
      setToast(buyError)
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [buyError])

  async function handleBuy(listingId) {
    const result = await buyItem(listingId)
    if (result) {
      setToast(result.message || 'تم الشراء بنجاح')
      refetchInventory()
    }
    setTimeout(() => setToast(null), 3000)
  }

  async function handleUseItem(ownedItemId) {
    setUsingItem(true)
    try {
      const qs = competitionId ? `?competition_id=${competitionId}` : ''
      const res = await apiFetch(`/api/me/inventory/${ownedItemId}/use${qs}`, { method: 'POST' })
      setToast(res.message || 'تم استخدام العنصر بنجاح')
      refetchInventory()
      setTimeout(() => setToast(null), 3000)
    } catch (err) {
      setToast(err.message || 'فشل استخدام العنصر')
      setTimeout(() => setToast(null), 3000)
    } finally {
      setUsingItem(false)
    }
  }

  const categoryFiltered = category === 'all'
    ? listings
    : listings.filter(l => l.category === category)

  const filtered = [...categoryFiltered].sort((a, b) => {
    if (sortBy === 'price_asc') return a.price - b.price
    if (sortBy === 'price_desc') return b.price - a.price
    if (sortBy === 'rarity_desc') return (RARITY_ORDER[b.rarity] || 0) - (RARITY_ORDER[a.rarity] || 0)
    if (sortBy === 'rarity_asc') return (RARITY_ORDER[a.rarity] || 0) - (RARITY_ORDER[b.rarity] || 0)
    return 0
  })

  const categories = [
    { key: 'all', label: 'الكل' },
    { key: 'weapon', label: 'الأسلحة' },
    { key: 'defense', label: 'الدروع' },
    { key: 'special', label: 'خاص' },
  ]

  return (
    <div className="flex-1 w-full max-w-7xl mx-auto px-4 py-8 md:py-12 space-y-10 relative z-10 pb-24 md:pb-12">

      {/* Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-3">
          <h1 className="font-display text-4xl md:text-5xl lg:text-6xl font-black text-gray-900 dark:text-white leading-none tracking-tight">
            المتجر التكتيكي
          </h1>
          <p className="text-gray-500 dark:text-gray-400 font-bold md:text-lg max-w-xl leading-relaxed">
            تسلّح بأفضل العناصر لتسيطر على ساحة حرب الأسماء، وضاعف فرصك في الفوز والهيمنة على المتصدرين.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Side: Tabs & Items */}
        <div className="lg:col-span-3 space-y-6">
          {/* Tabs */}
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            <nav className="flex bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 p-1.5 rounded-xl w-full md:w-auto overflow-x-auto no-scrollbar shadow-sm">
              {categories.map(c => {
                const count = c.key === 'all' ? listings.length : listings.filter(l => l.category === c.key).length
                return (
                  <button
                    key={c.key}
                    onClick={() => setCategory(c.key)}
                    className={`px-5 md:px-8 py-2.5 rounded-lg font-heading font-bold text-sm whitespace-nowrap smooth-transition ${
                      category === c.key
                        ? 'bg-brand-teal text-white dark:bg-brand-slate dark:text-white'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                    }`}
                  >
                    {c.label} <span className="text-[10px] opacity-80 ml-1 font-display">({count})</span>
                  </button>
                )
              })}
            </nav>
            <div className="flex items-center gap-3">
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 font-heading font-bold text-sm text-gray-700 dark:text-gray-300 shadow-sm smooth-transition focus:outline-none focus:ring-2 focus:ring-brand-teal/30 dark:focus:ring-brand-slate/30 cursor-pointer"
              >
                <option value="default">الترتيب الافتراضي</option>
                <option value="price_asc">السعر: من الأقل</option>
                <option value="price_desc">السعر: من الأعلى</option>
                <option value="rarity_desc">الندرة: من الأعلى</option>
                <option value="rarity_asc">الندرة: من الأقل</option>
              </select>
            </div>
          </div>

          {/* Items Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
            {loading ? (
              Array(4).fill(0).map((_, i) => (
                <div key={i} className="h-[360px] bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />
              ))
            ) : error ? (
              <div className="col-span-full text-center py-12 text-brand-danger font-bold">{error}</div>
            ) : filtered.length === 0 ? (
              <div className="col-span-full text-center py-12 text-gray-400 font-bold">لا توجد عناصر في هذه الفئة</div>
            ) : (
              filtered.map(listing => (
                <StoreItem
                  key={listing.listing_id}
                  listing={listing}
                  onBuy={handleBuy}
                  buying={buying}
                  playerBalance={playerBalance}
                />
              ))
            )}
          </div>

          {buyError && (
            <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-2xl p-4 text-red-600 dark:text-red-400 font-bold text-sm text-center">
              {buyError}
            </div>
          )}
        </div>

        {/* Right Side: Inventory Sidebar */}
        <aside className="lg:col-span-1">
          <div className="sticky top-[88px] z-20">
            <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm flex flex-col h-[600px] md:h-[calc(100vh-140px)] min-h-[500px] overflow-hidden">
              {/* Inventory Header */}
              <div className="p-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate flex items-center justify-center">
                    <iconify-icon icon="lucide:package" class="text-lg"></iconify-icon>
                  </div>
                  <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white">مخزني</h2>
                </div>
                <span className="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2.5 py-1 rounded-md font-bold text-[10px]">
                  {inventoryItems.length} عنصر
                </span>
              </div>

              {/* Scrollable Inventory Items */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 inventory-scroll">
                {invLoading ? (
                  Array(3).fill(0).map((_, i) => (
                    <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
                  ))
                ) : inventoryItems.length === 0 ? (
                  <div className="text-center py-8 text-gray-400 font-bold text-sm">
                    <iconify-icon icon="lucide:package-open" class="text-3xl text-gray-300 dark:text-gray-600 mb-2"></iconify-icon>
                    <p>المخزن فارغ — اشترِ عنصراً!</p>
                  </div>
                ) : (
                  inventoryItems.map(item => (
                    <InventoryItemCard key={item.owned_item_id} item={item} onUse={handleUseItem} using={usingItem} />
                  ))
                )}
              </div>

              {/* Capacity bar */}
              <div className="p-5 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30">
                <div className="flex justify-between text-[11px] font-heading font-bold mb-2 text-gray-500 dark:text-gray-400 uppercase">
                  <span>السعة المستخدمة</span>
                  <span>{inventoryItems.length} / {maxCapacity}</span>
                </div>
                <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-l from-brand-teal to-brand-teal-light rounded-full relative overflow-hidden"
                    style={{ width: `${Math.min(100, (inventoryItems.length / maxCapacity) * 100)}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 w-full h-full" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 8px, rgba(0,0,0,0.1) 8px, rgba(0,0,0,0.1) 16px)' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-24 md:bottom-8 right-4 md:right-8 z-[100] animate-[slideUpFade_0.3s_ease]">
          <div className="bg-white dark:bg-brand-card-dark border-l-4 border-brand-success rounded-xl shadow-lg p-4 flex items-center gap-4 min-w-[280px]">
            <div className="w-10 h-10 rounded-full bg-brand-success/10 text-brand-success flex items-center justify-center flex-shrink-0">
              <iconify-icon icon="lucide:check" class="text-xl"></iconify-icon>
            </div>
            <div>
              <div className="font-heading font-black text-gray-900 dark:text-white">تم الشراء بنجاح!</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{toast}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
