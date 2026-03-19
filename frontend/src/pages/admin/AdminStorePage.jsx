import React, { useState } from 'react'
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

const RARITY_DOT_COLORS = {
  common: '#94A3B8',
  rare: '#0D47A1',
  epic: '#64748B',
  legendary: '#D84315',
  mythic: '#7C3AED',
}

const RARITY_OPTIONS = [
  { value: 'common', label: 'عادي' },
  { value: 'rare', label: 'نادر' },
  { value: 'epic', label: 'ملحمي' },
  { value: 'legendary', label: 'أسطوري' },
  { value: 'mythic', label: 'خرافي' },
]

const CATEGORY_OPTIONS = [
  { value: 'weapon', label: 'سلاح' },
  { value: 'defense', label: 'دفاع' },
  { value: 'special', label: 'خاص' },
]

const USAGE_TYPE_OPTIONS = [
  { value: 'consumable', label: 'استهلاكي' },
  { value: 'non_consumable', label: 'غير استهلاكي' },
  { value: 'time_limited', label: 'محدود الوقت' },
  { value: 'persistent', label: 'دائم' },
]

const EFFECT_TYPE_OPTIONS = [
  { value: 'ratio_modifier', label: 'معدّل نسبي' },
  { value: 'fixed_bonus', label: 'مكافأة ثابتة' },
  { value: 'loss_reduction', label: 'تقليل الخسارة' },
  { value: 'action_block', label: 'منع إجراء' },
  { value: 'state_change', label: 'تغيير حالة' },
  { value: 'alias_change', label: 'تغيير الاسم المستعار' },
  { value: 'identity_reveal', label: 'كشف الهوية' },
  { value: 'shield_grant', label: 'منح درع' },
  { value: 'score_transfer', label: 'نقل نقاط' },
  { value: 'cooldown_reset', label: 'إعادة تعيين المهلة' },
  { value: 'visibility_toggle', label: 'تبديل الرؤية' },
  { value: 'bonus_multiplier', label: 'مضاعف مكافأة' },
  { value: 'immunity', label: 'حصانة' },
]

const TARGET_SCOPE_OPTIONS = [
  { value: 'self', label: 'الذات' },
  { value: 'target', label: 'الهدف' },
  { value: 'all', label: 'الجميع' },
]

const COMPETITION_ID = '00000000-0000-0000-0000-000000000001'

/* ────────── Modal Backdrop ────────── */
function ModalBackdrop({ children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white dark:bg-brand-card-dark rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {children}
      </div>
    </div>
  )
}

/* ────────── Confirm Dialog ────────── */
function ConfirmDialog({ title, message, onConfirm, onCancel, loading }) {
  return (
    <ModalBackdrop onClose={onCancel}>
      <div className="p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-danger/10 flex items-center justify-center">
            <iconify-icon icon="lucide:alert-triangle" class="text-brand-danger text-xl"></iconify-icon>
          </div>
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">{title}</h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{message}</p>
        <div className="flex gap-3 pt-2">
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-brand-danger text-white text-sm font-bold hover:bg-red-600 smooth-transition disabled:opacity-50"
          >
            {loading ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon> : 'تأكيد الحذف'}
          </button>
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50"
          >
            إلغاء
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

/* ────────── Item Form Modal ────────── */
function ItemFormModal({ item, onClose, onSaved }) {
  const isEdit = !!item
  const [form, setForm] = useState({
    name: item?.name || '',
    description: item?.description || '',
    rarity: item?.rarity || 'common',
    category: item?.category || 'weapon',
    usage_type: item?.usage_type || 'consumable',
    max_uses: item?.max_uses ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function updateField(field, value) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setError('اسم العنصر مطلوب'); return }
    setSaving(true)
    setError(null)

    const body = { ...form }
    if (body.max_uses === '' || body.max_uses === null) delete body.max_uses
    else body.max_uses = Number(body.max_uses)
    if (!body.description) delete body.description

    try {
      if (isEdit) {
        const patch = {}
        if (form.name !== item.name) patch.name = form.name
        if (form.description !== (item.description || '')) patch.description = form.description
        if (form.rarity !== item.rarity) patch.rarity = form.rarity
        if (form.category !== item.category) patch.category = form.category
        if (Object.keys(patch).length > 0) {
          await apiFetch(`/api/admin/store/items/${item.id}`, {
            method: 'PATCH',
            body: JSON.stringify(patch),
          })
        }
      } else {
        await apiFetch('/api/admin/store/items', {
          method: 'POST',
          body: JSON.stringify(body),
        })
      }
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const inputClass = 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/30 focus:border-brand-teal smooth-transition'

  return (
    <ModalBackdrop onClose={onClose}>
      <form onSubmit={handleSubmit}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">
            {isEdit ? 'تعديل العنصر' : 'إنشاء عنصر جديد'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 smooth-transition">
            <iconify-icon icon="lucide:x" class="text-xl"></iconify-icon>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {error && (
            <div className="bg-brand-danger/10 text-brand-danger px-4 py-2 rounded-xl text-sm font-bold">{error}</div>
          )}

          {/* Name */}
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">اسم العنصر *</label>
            <input
              type="text"
              value={form.name}
              onChange={e => updateField('name', e.target.value)}
              className={inputClass}
              placeholder="مثال: درع الحماية"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الوصف</label>
            <textarea
              value={form.description}
              onChange={e => updateField('description', e.target.value)}
              rows={3}
              className={inputClass + ' resize-none'}
              placeholder="وصف مختصر للعنصر..."
            />
          </div>

          {/* Rarity + Category row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الندرة</label>
              <select value={form.rarity} onChange={e => updateField('rarity', e.target.value)} className={inputClass}>
                {RARITY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الفئة</label>
              <select value={form.category} onChange={e => updateField('category', e.target.value)} className={inputClass}>
                {CATEGORY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {/* Usage type + Max uses row */}
          {!isEdit && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">نوع الاستخدام</label>
                <select value={form.usage_type} onChange={e => updateField('usage_type', e.target.value)} className={inputClass}>
                  {USAGE_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الحد الأقصى للاستخدام</label>
                <input
                  type="number"
                  min="1"
                  value={form.max_uses}
                  onChange={e => updateField('max_uses', e.target.value)}
                  className={inputClass}
                  placeholder="غير محدود"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition disabled:opacity-50"
          >
            {saving ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon={isEdit ? 'lucide:check' : 'lucide:plus'} class="text-sm"></iconify-icon>
            )}
            {isEdit ? 'حفظ التغييرات' : 'إنشاء العنصر'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50"
          >
            إلغاء
          </button>
        </div>
      </form>
    </ModalBackdrop>
  )
}

/* ────────── Listing Form Modal ────────── */
function ListingFormModal({ items, onClose, onSaved }) {
  const [form, setForm] = useState({
    item_definition_id: items?.[0]?.id || '',
    price: '',
    total_stock: '',
    max_per_participant: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function updateField(field, value) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.item_definition_id) { setError('يجب اختيار عنصر'); return }
    if (!form.price || Number(form.price) <= 0) { setError('السعر مطلوب'); return }
    setSaving(true)
    setError(null)

    const body = {
      item_definition_id: form.item_definition_id,
      competition_id: COMPETITION_ID,
      price: Number(form.price),
    }
    if (form.total_stock !== '') body.total_stock = Number(form.total_stock)
    if (form.max_per_participant !== '') body.max_per_participant = Number(form.max_per_participant)

    try {
      await apiFetch('/api/admin/store/listings', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const inputClass = 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/30 focus:border-brand-teal smooth-transition'

  return (
    <ModalBackdrop onClose={onClose}>
      <form onSubmit={handleSubmit}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">إنشاء عرض جديد</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 smooth-transition">
            <iconify-icon icon="lucide:x" class="text-xl"></iconify-icon>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {error && (
            <div className="bg-brand-danger/10 text-brand-danger px-4 py-2 rounded-xl text-sm font-bold">{error}</div>
          )}

          {/* Item Selection */}
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">العنصر *</label>
            <select value={form.item_definition_id} onChange={e => updateField('item_definition_id', e.target.value)} className={inputClass}>
              <option value="" disabled>اختر عنصراً...</option>
              {items?.map(item => (
                <option key={item.id} value={item.id}>
                  {item.name} ({RARITY_OPTIONS.find(r => r.value === item.rarity)?.label || item.rarity})
                </option>
              ))}
            </select>
          </div>

          {/* Price */}
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">السعر (نقاط) *</label>
            <input
              type="number"
              min="1"
              value={form.price}
              onChange={e => updateField('price', e.target.value)}
              className={inputClass}
              placeholder="مثال: 100"
            />
          </div>

          {/* Stock + Max per participant */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">المخزون الكلي</label>
              <input
                type="number"
                min="1"
                value={form.total_stock}
                onChange={e => updateField('total_stock', e.target.value)}
                className={inputClass}
                placeholder="غير محدود"
              />
            </div>
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الحد لكل لاعب</label>
              <input
                type="number"
                min="1"
                value={form.max_per_participant}
                onChange={e => updateField('max_per_participant', e.target.value)}
                className={inputClass}
                placeholder="غير محدود"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition disabled:opacity-50"
          >
            {saving ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
            )}
            إنشاء العرض
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50"
          >
            إلغاء
          </button>
        </div>
      </form>
    </ModalBackdrop>
  )
}

/* ────────── Effect Form Modal ────────── */
function EffectFormModal({ itemId, effect, onClose, onSaved }) {
  const isEdit = !!effect
  const [form, setForm] = useState({
    effect_type: effect?.effect_type || 'ratio_modifier',
    parameters: effect?.parameters ? JSON.stringify(effect.parameters, null, 2) : '{}',
    target_scope: effect?.target_scope || 'self',
    duration_minutes: effect?.duration_minutes ?? '',
    is_stackable: effect?.is_stackable ?? false,
    trigger_on: effect?.trigger_on || '',
    order_index: effect?.order_index ?? 0,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function updateField(field, value) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)

    let parsedParams
    try {
      parsedParams = JSON.parse(form.parameters)
    } catch {
      setError('صيغة المعاملات غير صحيحة (يجب أن تكون JSON)')
      setSaving(false)
      return
    }

    const body = {
      effect_type: form.effect_type,
      parameters: parsedParams,
      target_scope: form.target_scope,
      is_stackable: form.is_stackable,
      order_index: Number(form.order_index),
    }
    if (form.duration_minutes !== '') body.duration_minutes = Number(form.duration_minutes)
    if (form.trigger_on) body.trigger_on = form.trigger_on

    try {
      if (isEdit) {
        await apiFetch(`/api/admin/store/items/${itemId}/effects/${effect.id}`, {
          method: 'PATCH',
          body: JSON.stringify(body),
        })
      } else {
        await apiFetch(`/api/admin/store/items/${itemId}/effects`, {
          method: 'POST',
          body: JSON.stringify(body),
        })
      }
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const inputClass = 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/30 focus:border-brand-teal smooth-transition'

  return (
    <ModalBackdrop onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">
            {isEdit ? 'تعديل التأثير' : 'إضافة تأثير'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 smooth-transition">
            <iconify-icon icon="lucide:x" class="text-xl"></iconify-icon>
          </button>
        </div>

        <div className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {error && (
            <div className="bg-brand-danger/10 text-brand-danger px-4 py-2 rounded-xl text-sm font-bold">{error}</div>
          )}

          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">نوع التأثير *</label>
            <select value={form.effect_type} onChange={e => updateField('effect_type', e.target.value)} className={inputClass}>
              {EFFECT_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">المعاملات (JSON) *</label>
            <textarea
              value={form.parameters}
              onChange={e => updateField('parameters', e.target.value)}
              rows={3}
              className={inputClass + ' resize-none font-mono text-xs'}
              placeholder='{"ratio": 1.5}'
              dir="ltr"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">نطاق الهدف</label>
              <select value={form.target_scope} onChange={e => updateField('target_scope', e.target.value)} className={inputClass}>
                {TARGET_SCOPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">المدة (دقائق)</label>
              <input
                type="number"
                min="0"
                value={form.duration_minutes}
                onChange={e => updateField('duration_minutes', e.target.value)}
                className={inputClass}
                placeholder="دائم"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الترتيب</label>
              <input
                type="number"
                min="0"
                value={form.order_index}
                onChange={e => updateField('order_index', e.target.value)}
                className={inputClass}
              />
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_stackable}
                  onChange={e => updateField('is_stackable', e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-brand-teal focus:ring-brand-teal/30"
                />
                <span className="text-sm font-bold text-gray-700 dark:text-gray-300">قابل للتراكم</span>
              </label>
            </div>
          </div>
        </div>

        <div className="flex gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition disabled:opacity-50"
          >
            {saving ? (
              <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
            ) : (
              <iconify-icon icon={isEdit ? 'lucide:check' : 'lucide:plus'} class="text-sm"></iconify-icon>
            )}
            {isEdit ? 'حفظ التغييرات' : 'إضافة التأثير'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50"
          >
            إلغاء
          </button>
        </div>
      </form>
    </ModalBackdrop>
  )
}

/* ════════════════════════════════════════════════════
   Main Page
   ════════════════════════════════════════════════════ */
export default function AdminStorePage() {
  const [tab, setTab] = useState('listings')
  const { data: listings, loading: loadingListings, refetch: refetchListings } = useAdminData('/api/admin/store/listings')
  const { data: items, loading: loadingItems, refetch: refetchItems } = useAdminData('/api/admin/store/items')
  const [actionMsg, setActionMsg] = useState(null)

  // Modals state
  const [showItemForm, setShowItemForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deletingItem, setDeletingItem] = useState(null)
  const [showListingForm, setShowListingForm] = useState(false)
  const [deletingListing, setDeletingListing] = useState(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  // Item detail / effects state
  const [selectedItemId, setSelectedItemId] = useState(null)
  const [itemDetail, setItemDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [showEffectForm, setShowEffectForm] = useState(false)
  const [editingEffect, setEditingEffect] = useState(null)

  function flashMessage(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 2500)
  }

  async function toggleListingStatus(listingId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'hidden' : 'active'
    try {
      await apiFetch(`/api/admin/store/listings/${listingId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      })
      flashMessage('تم التحديث')
      refetchListings()
    } catch (err) {
      flashMessage(`خطأ: ${err.message}`)
    }
  }

  async function handleDeleteItem() {
    if (!deletingItem) return
    setDeleteLoading(true)
    try {
      await apiFetch(`/api/admin/store/items/${deletingItem.id}`, { method: 'DELETE' })
      flashMessage('تم أرشفة العنصر')
      setDeletingItem(null)
      refetchItems()
    } catch (err) {
      flashMessage(`خطأ: ${err.message}`)
    } finally {
      setDeleteLoading(false)
    }
  }

  async function handleDeleteListing() {
    if (!deletingListing) return
    setDeleteLoading(true)
    try {
      await apiFetch(`/api/admin/store/listings/${deletingListing.listing_id}`, { method: 'DELETE' })
      flashMessage('تم إخفاء العرض')
      setDeletingListing(null)
      refetchListings()
    } catch (err) {
      flashMessage(`خطأ: ${err.message}`)
    } finally {
      setDeleteLoading(false)
    }
  }

  function handleItemSaved() {
    setShowItemForm(false)
    setEditingItem(null)
    flashMessage(editingItem ? 'تم تعديل العنصر' : 'تم إنشاء العنصر')
    refetchItems()
  }

  function handleListingSaved() {
    setShowListingForm(false)
    flashMessage('تم إنشاء العرض')
    refetchListings()
  }

  async function loadItemDetail(itemId) {
    if (selectedItemId === itemId) { setSelectedItemId(null); return }
    setSelectedItemId(itemId)
    setLoadingDetail(true)
    try {
      const res = await apiFetch(`/api/admin/store/items/${itemId}`)
      setItemDetail(res.data)
    } catch (err) {
      flashMessage(`خطأ: ${err.message}`)
      setSelectedItemId(null)
    } finally {
      setLoadingDetail(false)
    }
  }

  async function reloadItemDetail() {
    if (!selectedItemId) return
    try {
      const res = await apiFetch(`/api/admin/store/items/${selectedItemId}`)
      setItemDetail(res.data)
    } catch {}
  }

  function handleEffectSaved() {
    setShowEffectForm(false)
    setEditingEffect(null)
    flashMessage(editingEffect ? 'تم تعديل التأثير' : 'تم إضافة التأثير')
    reloadItemDetail()
  }

  async function handleDeleteEffect(effectId) {
    try {
      await apiFetch(`/api/admin/store/items/${selectedItemId}/effects/${effectId}`, { method: 'DELETE' })
      flashMessage('تم حذف التأثير')
      reloadItemDetail()
    } catch (err) {
      flashMessage(`خطأ: ${err.message}`)
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

      {/* Tabs + Action Button */}
      <div className="flex items-center justify-between flex-wrap gap-3">
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

        {/* Create Button */}
        {tab === 'items' && (
          <button
            onClick={() => { setEditingItem(null); setShowItemForm(true) }}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition"
          >
            <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
            إنشاء عنصر
          </button>
        )}
        {tab === 'listings' && (
          <button
            onClick={() => setShowListingForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition"
          >
            <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
            إنشاء عرض
          </button>
        )}
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
                <div className="flex items-center gap-1">
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
                  <button
                    onClick={() => setDeletingListing(l)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-brand-danger hover:bg-brand-danger/10 smooth-transition"
                    title="حذف العرض"
                  >
                    <iconify-icon icon="lucide:trash-2" class="text-sm"></iconify-icon>
                  </button>
                </div>
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
                <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {items?.map(item => (
                <React.Fragment key={item.id}>
                <tr className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/20 smooth-transition">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: RARITY_DOT_COLORS[item.rarity] || '#94A3B8' }} />
                      <div>
                        <div className="font-bold text-gray-900 dark:text-white">{item.name}</div>
                        <div className="text-[11px] text-gray-400 max-w-xs truncate">{item.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={item.rarity} /></td>
                  <td className="px-4 py-3 text-gray-500">{item.usage_type}</td>
                  <td className="px-4 py-3 text-gray-500">{item.category}</td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => loadItemDetail(item.id)}
                        className={`p-1.5 rounded-lg smooth-transition ${selectedItemId === item.id ? 'text-brand-teal bg-brand-teal/10' : 'text-gray-400 hover:text-brand-teal hover:bg-brand-teal/10'}`}
                        title="التأثيرات"
                      >
                        <iconify-icon icon="lucide:sparkles" class="text-sm"></iconify-icon>
                      </button>
                      <button
                        onClick={() => { setEditingItem(item); setShowItemForm(true) }}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-brand-teal hover:bg-brand-teal/10 smooth-transition"
                        title="تعديل"
                      >
                        <iconify-icon icon="lucide:pencil" class="text-sm"></iconify-icon>
                      </button>
                      <button
                        onClick={() => setDeletingItem(item)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-brand-danger hover:bg-brand-danger/10 smooth-transition"
                        title="حذف"
                      >
                        <iconify-icon icon="lucide:trash-2" class="text-sm"></iconify-icon>
                      </button>
                    </div>
                  </td>
                </tr>
                {/* Expandable Effects Panel */}
                {selectedItemId === item.id && (
                  <tr>
                    <td colSpan={6} className="px-4 py-4 bg-gray-50/50 dark:bg-gray-800/20 border-b border-gray-100 dark:border-gray-800">
                      {loadingDetail ? (
                        <div className="flex items-center justify-center py-4">
                          <iconify-icon icon="lucide:loader-2" class="text-xl text-brand-teal animate-spin"></iconify-icon>
                        </div>
                      ) : itemDetail ? (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="font-heading font-black text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                              <iconify-icon icon="lucide:sparkles" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
                              التأثيرات ({itemDetail.effects?.length || 0})
                            </h4>
                            <button
                              onClick={() => { setEditingEffect(null); setShowEffectForm(true) }}
                              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-brand-teal/10 text-brand-teal hover:bg-brand-teal/20 smooth-transition"
                            >
                              <iconify-icon icon="lucide:plus" class="text-xs"></iconify-icon>
                              إضافة تأثير
                            </button>
                          </div>
                          {itemDetail.effects?.length === 0 ? (
                            <p className="text-xs text-gray-400 text-center py-3">لا توجد تأثيرات — أضف تأثيراً لهذا العنصر</p>
                          ) : (
                            <div className="space-y-2">
                              {itemDetail.effects.map(eff => (
                                <div key={eff.id} className="flex items-center justify-between p-3 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl">
                                  <div className="flex items-center gap-3">
                                    <span className="px-2 py-0.5 rounded-md text-[11px] font-black bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate">
                                      {EFFECT_TYPE_OPTIONS.find(o => o.value === eff.effect_type)?.label || eff.effect_type}
                                    </span>
                                    <span className="text-xs text-gray-500 font-mono" dir="ltr">{JSON.stringify(eff.parameters)}</span>
                                    <span className="text-[10px] text-gray-400">
                                      {TARGET_SCOPE_OPTIONS.find(o => o.value === eff.target_scope)?.label || eff.target_scope}
                                    </span>
                                    {eff.duration_minutes && (
                                      <span className="text-[10px] text-gray-400">{eff.duration_minutes} دقيقة</span>
                                    )}
                                    {eff.is_stackable && (
                                      <span className="text-[10px] text-brand-success font-bold">قابل للتراكم</span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <button
                                      onClick={() => { setEditingEffect(eff); setShowEffectForm(true) }}
                                      className="p-1 rounded text-gray-400 hover:text-brand-teal smooth-transition"
                                      title="تعديل"
                                    >
                                      <iconify-icon icon="lucide:pencil" class="text-xs"></iconify-icon>
                                    </button>
                                    <button
                                      onClick={() => handleDeleteEffect(eff.id)}
                                      className="p-1 rounded text-gray-400 hover:text-brand-danger smooth-transition"
                                      title="حذف"
                                    >
                                      <iconify-icon icon="lucide:trash-2" class="text-xs"></iconify-icon>
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
          {(!items || items.length === 0) && (
            <div className="text-center py-12 text-gray-400 font-bold">لا توجد عناصر</div>
          )}
        </div>
      )}

      {/* ── Modals ── */}

      {/* Item Create/Edit Modal */}
      {showItemForm && (
        <ItemFormModal
          item={editingItem}
          onClose={() => { setShowItemForm(false); setEditingItem(null) }}
          onSaved={handleItemSaved}
        />
      )}

      {/* Listing Create Modal */}
      {showListingForm && (
        <ListingFormModal
          items={items}
          onClose={() => setShowListingForm(false)}
          onSaved={handleListingSaved}
        />
      )}

      {/* Delete Item Confirm */}
      {deletingItem && (
        <ConfirmDialog
          title="حذف العنصر"
          message={`هل أنت متأكد من أرشفة "${deletingItem.name}"؟ لن يمكن استخدامه في عروض جديدة.`}
          onConfirm={handleDeleteItem}
          onCancel={() => setDeletingItem(null)}
          loading={deleteLoading}
        />
      )}

      {/* Delete Listing Confirm */}
      {deletingListing && (
        <ConfirmDialog
          title="حذف العرض"
          message={`هل أنت متأكد من إخفاء عرض "${deletingListing.item_name}"؟`}
          onConfirm={handleDeleteListing}
          onCancel={() => setDeletingListing(null)}
          loading={deleteLoading}
        />
      )}

      {/* Effect Create/Edit Modal */}
      {showEffectForm && selectedItemId && (
        <EffectFormModal
          itemId={selectedItemId}
          effect={editingEffect}
          onClose={() => { setShowEffectForm(false); setEditingEffect(null) }}
          onSaved={handleEffectSaved}
        />
      )}
    </div>
  )
}
