import { useState } from 'react'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'

function StatusBadge({ status }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success', hidden: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    expired: 'bg-brand-danger/10 text-brand-danger', sold_out: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
    draft: 'bg-gray-100 dark:bg-gray-800 text-gray-500', disabled: 'bg-gray-100 dark:bg-gray-800 text-gray-400',
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{status}</span>
}

const RARITY_COLORS = {
  common: 'border-gray-300 dark:border-gray-600',
  rare: 'border-blue-500',
  epic: 'border-gray-500',
  legendary: 'border-brand-orange',
  mythic: 'border-purple-500',
}

export default function AdminStorePage() {
  const [tab, setTab] = useState('listings')
  const { data: listings, loading: loadingListings, refetch: refetchListings } = useAdminData('/api/admin/store/listings')
  const { data: items, loading: loadingItems } = useAdminData('/api/admin/store/items')
  const [actionMsg, setActionMsg] = useState(null)

  async function toggleListingStatus(listingId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'hidden' : 'active'
    try {
      await apiFetch(`/api/admin/store/listings/${listingId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      setActionMsg('تم التحديث')
      refetchListings()
      setTimeout(() => setActionMsg(null), 2000)
    } catch (err) {
      setActionMsg(`خطأ: ${err.message}`)
    }
  }

  const loading = tab === 'listings' ? loadingListings : loadingItems

  if (loading) {
    return <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">إدارة المتجر</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">العناصر والعروض</p>
      </div>

      {actionMsg && (
        <div className="bg-brand-success/10 text-brand-success px-4 py-2 rounded-xl text-sm font-bold">{actionMsg}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit">
        <button
          onClick={() => setTab('listings')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold smooth-transition ${
            tab === 'listings' ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm' : 'text-gray-500'
          }`}
        >
          <iconify-icon icon="lucide:store" class="text-sm"></iconify-icon>
          عروض المتجر
        </button>
        <button
          onClick={() => setTab('items')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold smooth-transition ${
            tab === 'items' ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm' : 'text-gray-500'
          }`}
        >
          <iconify-icon icon="lucide:box" class="text-sm"></iconify-icon>
          تعريفات العناصر
        </button>
      </div>

      {/* Listings Tab */}
      {tab === 'listings' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {listings?.map(l => (
            <div key={l.listing_id} className={`bg-white dark:bg-brand-card-dark border-2 rounded-2xl p-5 ${RARITY_COLORS[l.item_rarity] || 'border-gray-200 dark:border-gray-700'}`}>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-heading font-black text-gray-900 dark:text-white">{l.item_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <StatusBadge status={l.status} />
                    <span className="text-[11px] font-bold text-gray-400">{l.item_rarity}</span>
                  </div>
                </div>
                <button
                  onClick={() => toggleListingStatus(l.listing_id, l.status)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold smooth-transition ${
                    l.status === 'active'
                      ? 'text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30'
                      : 'text-brand-success hover:bg-brand-success/10'
                  }`}
                >
                  {l.status === 'active' ? 'إخفاء' : 'تفعيل'}
                </button>
              </div>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">السعر</div>
                  <div className="font-heading font-black text-brand-teal dark:text-brand-slate">{l.price}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">المبيعات</div>
                  <div className="font-heading font-black text-gray-900 dark:text-white">{l.sold_count}</div>
                </div>
                <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  <div className="text-[10px] font-black text-gray-400 uppercase">المخزون</div>
                  <div className="font-heading font-black text-gray-900 dark:text-white">{l.total_stock ?? '∞'}</div>
                </div>
              </div>
              {l.max_per_participant && (
                <div className="mt-2 text-[11px] text-gray-400">الحد الأقصى لكل لاعب: {l.max_per_participant}</div>
              )}
            </div>
          ))}
          {(!listings || listings.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold col-span-2">لا توجد عروض</div>
          )}
        </div>
      )}

      {/* Items Tab */}
      {tab === 'items' && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">العنصر</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الندرة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">النوع</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الفئة</th>
                <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الحالة</th>
              </tr>
            </thead>
            <tbody>
              {items?.map(item => (
                <tr key={item.id} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="px-4 py-3">
                    <div className="font-bold text-gray-900 dark:text-white">{item.name}</div>
                    <div className="text-[11px] text-gray-400 max-w-xs truncate">{item.description}</div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.rarity} /></td>
                  <td className="px-4 py-3 text-gray-500">{item.usage_type}</td>
                  <td className="px-4 py-3 text-gray-500">{item.category}</td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {(!items || items.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold">لا توجد عناصر</div>
          )}
        </div>
      )}
    </div>
  )
}
