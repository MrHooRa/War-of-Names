/**
 * InventoryItemCard — shared premium inventory card used across:
 *  - Store sidebar inventory
 *  - Dashboard inventory section
 *
 * Rarity styling imported from config/rarity.js (single source of truth).
 *
 * Props:
 *  - item: inventory item object from /api/me/inventory
 *  - onUse: (ownedItemId) => void
 *  - using: boolean (loading state for this specific item)
 *  - compact: boolean (smaller variant for dashboard grid)
 */

import { RARITY_CONFIG, CATEGORY_ICONS, CATEGORY_COLORS, CATEGORY_GLOW } from '../config/rarity'

function ItemCTA({ item, onUse, using }) {
  // Activated — pulsing green badge
  if (item.status === 'activated') {
    return (
      <div className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-brand-success/10 dark:bg-brand-success/5 border border-brand-success/20">
        <span className="w-2 h-2 bg-brand-success rounded-full animate-pulse"></span>
        <span className="text-xs font-black text-brand-success">مُفعّل الآن</span>
      </div>
    )
  }

  // Pending — amber waiting state
  if (item.status === 'pending') {
    return (
      <div className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-amber-500/10 dark:bg-amber-500/5 border border-amber-500/20">
        <iconify-icon icon="lucide:clock" class="text-sm text-amber-500"></iconify-icon>
        <span className="text-xs font-black text-amber-600 dark:text-amber-400">ينتظر التفعيل</span>
      </div>
    )
  }

  // Blocked — show reason
  if (!item.can_use && item.denial_reason) {
    return (
      <div className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
        <iconify-icon icon="lucide:lock" class="text-sm text-gray-400"></iconify-icon>
        <span className="text-[11px] font-bold text-gray-400 truncate">{item.denial_reason}</span>
      </div>
    )
  }

  // Blocked — no reason (generic)
  if (!item.can_use) {
    return (
      <div className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
        <iconify-icon icon="lucide:lock" class="text-sm text-gray-400"></iconify-icon>
        <span className="text-xs font-bold text-gray-400">غير متاح</span>
      </div>
    )
  }

  // Usable — strong actionable button
  return (
    <button
      onClick={() => onUse(item.owned_item_id)}
      disabled={using}
      className="btn-press w-full py-2.5 rounded-xl font-heading font-bold text-sm bg-brand-teal text-white hover:bg-brand-teal-hover dark:bg-brand-teal dark:text-white dark:hover:bg-brand-teal-hover smooth-transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
    >
      {using ? (
        <>
          <iconify-icon icon="lucide:loader-2" class="text-base animate-spin"></iconify-icon>
          <span>جارٍ التفعيل...</span>
        </>
      ) : (
        <>
          <iconify-icon icon="lucide:zap" class="text-base"></iconify-icon>
          <span>استخدام</span>
        </>
      )}
    </button>
  )
}

export default function InventoryItemCard({ item, onUse, using, compact }) {
  const rarity = RARITY_CONFIG[item.rarity] || RARITY_CONFIG.common
  const icon = CATEGORY_ICONS[item.category] || 'lucide:package'
  const iconColor = CATEGORY_COLORS[item.category] || 'text-gray-500'
  const glow = CATEGORY_GLOW[item.category] || 'bg-gray-400'

  if (compact) {
    return (
      <div className={`group bg-white dark:bg-brand-card-dark border ${rarity.border} ${rarity.ring} ${rarity.glow} rounded-2xl hover:shadow-md dark:hover:shadow-black/20 smooth-transition flex flex-col p-4 overflow-hidden relative`}>
        {/* Icon area */}
        <div className="relative bg-gray-50 dark:bg-gray-800/50 w-full aspect-[5/3] rounded-xl flex items-center justify-center mb-3 overflow-hidden">
          <div className={`absolute inset-0 ${glow} opacity-5 dark:opacity-[0.03] blur-xl rounded-full group-hover:opacity-15 dark:group-hover:opacity-10 smooth-transition`}></div>
          <iconify-icon icon={icon} class={`text-4xl ${iconColor} group-hover:scale-110 smooth-transition relative z-10`}></iconify-icon>
          <span className={`absolute top-2 right-2 ${rarity.badge} text-[9px] font-black px-2 py-0.5 rounded shadow-sm`}>
            {rarity.label}
          </span>
          {item.quantity > 1 && (
            <span className="absolute top-2 left-2 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 text-[9px] font-black px-2 py-0.5 rounded shadow-sm border border-gray-200 dark:border-gray-700">
              ×{item.quantity}
            </span>
          )}
        </div>

        {/* Name */}
        <h4 className="font-heading font-black text-sm text-gray-900 dark:text-white truncate mb-1">{item.name}</h4>

        {/* Single effect summary */}
        {item.effects?.length > 0 && (
          <div className="flex items-center gap-1.5 mb-3">
            <iconify-icon icon="lucide:sparkles" class={`text-[10px] ${rarity.accent} flex-shrink-0`}></iconify-icon>
            <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400 truncate">{item.effects[0]}</span>
          </div>
        )}
        {!item.effects?.length && <div className="mb-3"></div>}

        {/* CTA */}
        <div className="mt-auto">
          <ItemCTA item={item} onUse={onUse} using={using} />
        </div>
      </div>
    )
  }

  // Default (sidebar) variant — slightly larger
  return (
    <div className={`group bg-white dark:bg-gray-800/30 border ${rarity.border} ${rarity.ring} ${rarity.glow} rounded-2xl hover:shadow-md dark:hover:shadow-black/20 smooth-transition p-4 overflow-hidden relative`}>
      <div className="flex gap-3">
        {/* Icon */}
        <div className="relative bg-gray-50 dark:bg-gray-800/50 w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 overflow-hidden">
          <div className={`absolute inset-0 ${glow} opacity-5 dark:opacity-[0.03] blur-lg`}></div>
          <iconify-icon icon={icon} class={`text-2xl ${iconColor} relative z-10`}></iconify-icon>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-heading font-bold text-sm text-gray-900 dark:text-white truncate">{item.name}</h4>
            <span className={`text-[9px] font-black ${rarity.badge} px-2 py-0.5 rounded flex-shrink-0`}>
              {rarity.label}
            </span>
          </div>
          <div className="flex items-center gap-3 text-[11px] font-bold text-gray-500 dark:text-gray-400">
            {item.quantity > 1 && (
              <span className="flex items-center gap-1">
                <iconify-icon icon="lucide:layers" class="text-[10px]"></iconify-icon>
                ×{item.quantity}
              </span>
            )}
            {item.uses_remaining !== null && item.uses_remaining !== undefined && (
              <span className="flex items-center gap-1">
                <iconify-icon icon="lucide:repeat" class="text-[10px]"></iconify-icon>
                {item.uses_remaining} استخدام
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Effects */}
      {item.effects?.length > 0 && (
        <div className="mt-2.5 space-y-1">
          {item.effects.slice(0, 2).map((eff, i) => (
            <div key={i} className="flex items-center gap-1.5 px-2.5 py-1 bg-brand-teal/5 dark:bg-brand-slate/10 rounded-lg">
              <iconify-icon icon="lucide:sparkles" class={`text-[10px] ${rarity.accent} flex-shrink-0`}></iconify-icon>
              <span className="text-[10px] font-bold text-gray-600 dark:text-gray-300 truncate">{eff}</span>
            </div>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="mt-3">
        <ItemCTA item={item} onUse={onUse} using={using} />
      </div>
    </div>
  )
}
