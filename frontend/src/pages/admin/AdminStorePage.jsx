import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import useAdminData from '../../hooks/useAdminData'
import { apiFetch } from '../../lib/api'
import { useAdminCompetition } from '../../context/AdminCompetitionContext'
import { RARITY_ADMIN, RARITY_LABELS, RARITY_DOT_COLORS, RARITY_OPTIONS } from '../../config/rarity'
import { formatDate } from '../../lib/dates'

/* ────────── Constants ────────── */

const RARITY_COLORS = {
  common:    RARITY_ADMIN.common.border,
  rare:      RARITY_ADMIN.rare.border,
  epic:      RARITY_ADMIN.epic.border,
  legendary: RARITY_ADMIN.legendary.border,
  mythic:    RARITY_ADMIN.mythic.border,
}
const CATEGORY_LABELS = { weapon: 'سلاح', defense: 'دفاع', special: 'خاص' }
const USAGE_TYPE_LABELS = { consumable: 'استهلاكي', non_consumable: 'غير استهلاكي', time_limited: 'محدود الوقت', persistent: 'دائم' }
const STATUS_LABELS = { active: 'نشط', hidden: 'مخفي', expired: 'منتهي', sold_out: 'نفذ', draft: 'مسودة', disabled: 'معطل', archived: 'مؤرشف', consumed: 'مستهلك' }
const SOURCE_LABELS = { purchase: 'شراء', admin_grant: 'منحة إدارية', reward: 'مكافأة', distribution: 'توزيع' }
const SCOPE_LABELS = { self: 'الذات', target: 'الهدف', all: 'الجميع' }
const CATEGORY_OPTIONS = [
  { value: 'weapon', label: 'سلاح' }, { value: 'defense', label: 'دفاع' }, { value: 'special', label: 'خاص' },
]
const USAGE_TYPE_OPTIONS = [
  { value: 'consumable', label: 'استهلاكي' }, { value: 'non_consumable', label: 'غير استهلاكي' },
  { value: 'time_limited', label: 'محدود الوقت' }, { value: 'persistent', label: 'دائم' },
]

const inputClass = 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-gray-900 dark:text-white text-sm font-bold focus:outline-none focus:ring-2 focus:ring-brand-teal/30 focus:border-brand-teal smooth-transition'

/* ────────── Shared UI ────────── */

function StatusBadge({ status, map }) {
  const colors = {
    active: 'bg-brand-success/10 text-brand-success', hidden: 'bg-gray-100 dark:bg-gray-800 text-gray-500',
    expired: 'bg-brand-danger/10 text-brand-danger', sold_out: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600',
    draft: 'bg-gray-100 dark:bg-gray-800 text-gray-500', disabled: 'bg-gray-100 dark:bg-gray-800 text-gray-400',
    archived: 'bg-gray-100 dark:bg-gray-800 text-gray-400', consumed: 'bg-gray-100 dark:bg-gray-800 text-gray-400',
    common: RARITY_ADMIN.common.badge, rare: RARITY_ADMIN.rare.badge,
    epic: RARITY_ADMIN.epic.badge, legendary: RARITY_ADMIN.legendary.badge,
    mythic: RARITY_ADMIN.mythic.badge,
  }
  const label = map ? (map[status] || status) : (STATUS_LABELS[status] || status)
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${colors[status] || 'bg-gray-100 text-gray-500'}`}>{label}</span>
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color || 'bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate'}`}>
        <iconify-icon icon={icon} class="text-xl"></iconify-icon>
      </div>
      <div>
        <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest">{label}</div>
        <div className="font-heading font-black text-lg text-gray-900 dark:text-white">{value}</div>
      </div>
    </div>
  )
}

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
          <button onClick={onConfirm} disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-brand-danger text-white text-sm font-bold hover:bg-red-600 smooth-transition disabled:opacity-50">
            {loading ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon> : 'تأكيد'}
          </button>
          <button onClick={onCancel} disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50">
            إلغاء
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

/* ────────── Item Definition Form Modal ────────── */
function ItemFormModal({ item, onClose, onSaved }) {
  const isEdit = !!item
  const [form, setForm] = useState({
    name: item?.name || '', description: item?.description || '',
    rarity: item?.rarity || 'common', category: item?.category || 'weapon',
    usage_type: item?.usage_type || 'consumable', max_uses: item?.max_uses ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function updateField(field, value) { setForm(f => ({ ...f, [field]: value })) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setError('اسم العنصر مطلوب'); return }
    setSaving(true); setError(null)
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
          await apiFetch(`/api/admin/store/items/${item.id}`, { method: 'PATCH', body: JSON.stringify(patch) })
        }
      } else {
        await apiFetch('/api/admin/store/items', { method: 'POST', body: JSON.stringify(body) })
      }
      onSaved()
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }

  return (
    <ModalBackdrop onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">
            {isEdit ? 'تعديل العنصر' : 'إنشاء عنصر جديد'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 smooth-transition">
            <iconify-icon icon="lucide:x" class="text-xl"></iconify-icon>
          </button>
        </div>
        <div className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {error && <div className="bg-brand-danger/10 text-brand-danger px-4 py-2 rounded-xl text-sm font-bold">{error}</div>}
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">اسم العنصر *</label>
            <input type="text" value={form.name} onChange={e => updateField('name', e.target.value)} className={inputClass} placeholder="مثال: درع الحماية" />
          </div>
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الوصف</label>
            <textarea value={form.description} onChange={e => updateField('description', e.target.value)} rows={3} className={inputClass + ' resize-none'} placeholder="وصف مختصر للعنصر..." />
          </div>
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
                <input type="number" min="1" value={form.max_uses} onChange={e => updateField('max_uses', e.target.value)} className={inputClass} placeholder="غير محدود" />
              </div>
            </div>
          )}
        </div>
        <div className="flex gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button type="submit" disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
              : <iconify-icon icon={isEdit ? 'lucide:check' : 'lucide:plus'} class="text-sm"></iconify-icon>}
            {isEdit ? 'حفظ التغييرات' : 'إنشاء العنصر'}
          </button>
          <button type="button" onClick={onClose} disabled={saving}
            className="px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50">
            إلغاء
          </button>
        </div>
      </form>
    </ModalBackdrop>
  )
}

/* ────────── Listing Form Modal (Create + Edit) ────────── */
function ListingFormModal({ items, listing, competitionId, onClose, onSaved }) {
  const isEdit = !!listing
  const [form, setForm] = useState({
    item_definition_id: listing?.item_id || items?.[0]?.id || '',
    price: listing?.price ?? '',
    total_stock: listing?.total_stock ?? '',
    max_per_participant: listing?.max_per_participant ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function updateField(field, value) { setForm(f => ({ ...f, [field]: value })) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!isEdit && !form.item_definition_id) { setError('يجب اختيار عنصر'); return }
    if (!form.price || Number(form.price) <= 0) { setError('السعر مطلوب'); return }
    setSaving(true); setError(null)

    try {
      if (isEdit) {
        const patch = {}
        if (Number(form.price) !== listing.price) patch.price = Number(form.price)
        if (form.total_stock !== '' && form.total_stock !== null) {
          if (Number(form.total_stock) !== listing.total_stock) patch.total_stock = Number(form.total_stock)
        }
        if (Object.keys(patch).length > 0) {
          await apiFetch(`/api/admin/store/listings/${listing.listing_id}`, { method: 'PATCH', body: JSON.stringify(patch) })
        }
      } else {
        const body = { item_definition_id: form.item_definition_id, competition_id: competitionId, price: Number(form.price) }
        if (form.total_stock !== '') body.total_stock = Number(form.total_stock)
        if (form.max_per_participant !== '') body.max_per_participant = Number(form.max_per_participant)
        await apiFetch('/api/admin/store/listings', { method: 'POST', body: JSON.stringify(body) })
      }
      onSaved()
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }

  return (
    <ModalBackdrop onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">
            {isEdit ? 'تعديل العرض' : 'إنشاء عرض جديد'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 smooth-transition">
            <iconify-icon icon="lucide:x" class="text-xl"></iconify-icon>
          </button>
        </div>
        <div className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {error && <div className="bg-brand-danger/10 text-brand-danger px-4 py-2 rounded-xl text-sm font-bold">{error}</div>}
          {!isEdit && (
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">العنصر *</label>
              <select value={form.item_definition_id} onChange={e => updateField('item_definition_id', e.target.value)} className={inputClass}>
                <option value="" disabled>اختر عنصراً...</option>
                {items?.map(item => (
                  <option key={item.id} value={item.id}>{item.name} ({RARITY_LABELS[item.rarity] || item.rarity})</option>
                ))}
              </select>
            </div>
          )}
          {isEdit && (
            <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: RARITY_DOT_COLORS[listing.item_rarity] }} />
              <span className="font-bold text-gray-900 dark:text-white">{listing.item_name}</span>
              <StatusBadge status={listing.item_rarity} map={RARITY_LABELS} />
            </div>
          )}
          <div>
            <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">السعر (نقاط) *</label>
            <input type="number" min="1" value={form.price} onChange={e => updateField('price', e.target.value)} className={inputClass} placeholder="مثال: 100" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">المخزون الكلي</label>
              <input type="number" min="1" value={form.total_stock} onChange={e => updateField('total_stock', e.target.value)} className={inputClass} placeholder="غير محدود" />
            </div>
            {!isEdit && (
              <div>
                <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الحد لكل لاعب</label>
                <input type="number" min="1" value={form.max_per_participant} onChange={e => updateField('max_per_participant', e.target.value)} className={inputClass} placeholder="غير محدود" />
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button type="submit" disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
              : <iconify-icon icon={isEdit ? 'lucide:check' : 'lucide:plus'} class="text-sm"></iconify-icon>}
            {isEdit ? 'حفظ التغييرات' : 'إنشاء العرض'}
          </button>
          <button type="button" onClick={onClose} disabled={saving}
            className="px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50">
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
  const [effectTypes, setEffectTypes] = useState(null)
  const [loadingTypes, setLoadingTypes] = useState(true)
  const [selectedType, setSelectedType] = useState(effect?.effect_type || '')
  const [params, setParams] = useState(effect?.parameters || {})
  const [targetScope, setTargetScope] = useState(effect?.target_scope || 'self')
  const [triggerOn, setTriggerOn] = useState(effect?.trigger_on || 'activation')
  const [durationMinutes, setDurationMinutes] = useState(effect?.duration_minutes ?? '')
  const [isStackable, setIsStackable] = useState(effect?.is_stackable ?? false)
  const [orderIndex, setOrderIndex] = useState(effect?.order_index ?? 0)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState([])

  React.useEffect(() => {
    apiFetch('/api/admin/store/effect-types')
      .then(res => {
        setEffectTypes(res.data)
        if (!selectedType && res.data.length > 0) setSelectedType(res.data[0].value)
      })
      .catch(() => setErrors(['فشل في تحميل أنواع التأثيرات']))
      .finally(() => setLoadingTypes(false))
  }, [])

  const currentType = effectTypes?.find(t => t.value === selectedType)

  function handleTypeChange(newType) {
    setSelectedType(newType)
    const type = effectTypes?.find(t => t.value === newType)
    if (type) {
      const defaults = {}
      type.fields.forEach(f => { if (f.default !== undefined) defaults[f.key] = f.default })
      setParams(defaults)
      if (type.allowed_scopes?.length > 0 && !type.allowed_scopes.includes(targetScope)) setTargetScope(type.allowed_scopes[0])
      const firstTrigger = type.allowed_triggers?.[0] || 'activation'
      setTriggerOn(firstTrigger)
      if (!type.requires_duration_for?.includes(firstTrigger)) setDurationMinutes('')
    }
  }

  function shouldShowField(field) {
    if (!field.show_when) return true
    return Object.entries(field.show_when).every(([k, v]) => params[k] === v)
  }

  async function handleSubmit(e) {
    e.preventDefault(); setSaving(true); setErrors([])
    const coercedParams = { ...params }
    currentType?.fields?.forEach(f => {
      if ((f.type === 'number' || f.type === 'decimal') && coercedParams[f.key] !== undefined && coercedParams[f.key] !== '')
        coercedParams[f.key] = Number(coercedParams[f.key])
    })
    const body = {
      effect_type: selectedType, parameters: coercedParams, target_scope: targetScope,
      trigger_on: triggerOn, is_stackable: isStackable, order_index: Number(orderIndex),
    }
    if (durationMinutes !== '') body.duration_minutes = Number(durationMinutes)

    try {
      if (isEdit) {
        await apiFetch(`/api/admin/store/items/${itemId}/effects/${effect.id}`, { method: 'PATCH', body: JSON.stringify(body) })
      } else {
        await apiFetch(`/api/admin/store/items/${itemId}/effects`, { method: 'POST', body: JSON.stringify(body) })
      }
      onSaved()
    } catch (err) {
      setErrors(err.data?.errors || [err.message || 'حدث خطأ'])
    } finally { setSaving(false) }
  }

  function renderField(field) {
    if (!shouldShowField(field)) return null
    const value = params[field.key] ?? field.default ?? ''
    if (field.type === 'select' && field.options) {
      return (
        <div key={field.key}>
          <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">{field.label} {field.required && '*'}</label>
          <select value={value} onChange={e => setParams(p => ({ ...p, [field.key]: e.target.value }))} className={inputClass}>
            <option value="">— اختر —</option>
            {field.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      )
    }
    return (
      <div key={field.key}>
        <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">{field.label} {field.required && '*'}</label>
        <input type="number" value={value} onChange={e => setParams(p => ({ ...p, [field.key]: e.target.value }))}
          min={field.min} max={field.max} step={field.type === 'decimal' ? '0.01' : '1'} className={inputClass} dir="ltr" />
      </div>
    )
  }

  return (
    <ModalBackdrop onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-display font-black text-lg text-gray-900 dark:text-white">{isEdit ? 'تعديل التأثير' : 'إضافة تأثير'}</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 smooth-transition">
            <iconify-icon icon="lucide:x" class="text-xl"></iconify-icon>
          </button>
        </div>
        <div className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {errors.length > 0 && (
            <div className="bg-brand-danger/10 text-brand-danger px-4 py-3 rounded-xl text-sm font-bold space-y-1">
              {errors.map((err, i) => <div key={i}>{err}</div>)}
            </div>
          )}
          {loadingTypes ? (
            <div className="flex items-center justify-center py-8">
              <iconify-icon icon="lucide:loader-2" class="text-2xl text-brand-teal animate-spin"></iconify-icon>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">نوع التأثير *</label>
                <select value={selectedType} onChange={e => handleTypeChange(e.target.value)} className={inputClass}>
                  {effectTypes?.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                {currentType?.description && <p className="text-[11px] text-gray-400 mt-1">{currentType.description}</p>}
              </div>
              {currentType?.fields?.length > 0 && (
                <div className="space-y-3 p-3 bg-gray-50 dark:bg-gray-800/30 rounded-xl border border-gray-100 dark:border-gray-700/50">
                  <div className="text-[10px] font-black text-gray-400 uppercase tracking-widest">معاملات التأثير</div>
                  {currentType.fields.map(renderField)}
                </div>
              )}
              {currentType?.trigger_options?.length > 1 && (
                <div>
                  <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">وضع التشغيل *</label>
                  <select value={triggerOn} onChange={e => {
                    setTriggerOn(e.target.value)
                    if (!currentType?.requires_duration_for?.includes(e.target.value)) setDurationMinutes('')
                  }} className={inputClass}>
                    {currentType.trigger_options.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">نطاق الهدف</label>
                  <select value={targetScope} onChange={e => setTargetScope(e.target.value)} className={inputClass}>
                    {(currentType?.allowed_scopes || ['self', 'target', 'all']).map(s => (
                      <option key={s} value={s}>{SCOPE_LABELS[s] || s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">
                    المدة (دقائق) {currentType?.requires_duration_for?.includes(triggerOn) && '*'}
                  </label>
                  <input type="number" min="1" value={durationMinutes} onChange={e => setDurationMinutes(e.target.value)} className={inputClass}
                    placeholder={currentType?.requires_duration_for?.includes(triggerOn) ? 'مطلوب' : 'اختياري'} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-black text-gray-500 dark:text-gray-400 mb-1.5">الترتيب</label>
                  <input type="number" min="0" value={orderIndex} onChange={e => setOrderIndex(e.target.value)} className={inputClass} />
                </div>
                <div className="flex items-end pb-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={isStackable} onChange={e => setIsStackable(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-brand-teal focus:ring-brand-teal/30" />
                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">قابل للتراكم</span>
                  </label>
                </div>
              </div>
            </>
          )}
        </div>
        <div className="flex gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button type="submit" disabled={saving || loadingTypes}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition disabled:opacity-50">
            {saving ? <iconify-icon icon="lucide:loader-2" class="animate-spin"></iconify-icon>
              : <iconify-icon icon={isEdit ? 'lucide:check' : 'lucide:plus'} class="text-sm"></iconify-icon>}
            {isEdit ? 'حفظ التغييرات' : 'إضافة التأثير'}
          </button>
          <button type="button" onClick={onClose} disabled={saving}
            className="px-4 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-gray-700 smooth-transition disabled:opacity-50">
            إلغاء
          </button>
        </div>
      </form>
    </ModalBackdrop>
  )
}

/* ════════════════════════════════════════════════════════════════
   TAB: Item Catalog (كتالوج العناصر)
   ════════════════════════════════════════════════════════════════ */
function ItemCatalogTab({ items, refetchItems, flashMessage }) {
  const [showItemForm, setShowItemForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [archivingItem, setArchivingItem] = useState(null)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [revokingItem, setRevokingItem] = useState(null)
  const [revokeLoading, setRevokeLoading] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [itemDetail, setItemDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [showEffectForm, setShowEffectForm] = useState(false)
  const [editingEffect, setEditingEffect] = useState(null)

  async function handleArchiveItem() {
    if (!archivingItem) return
    setArchiveLoading(true)
    try {
      const res = await apiFetch(`/api/admin/store/items/${archivingItem.id}`, { method: 'DELETE' })
      const deactivated = res.data?.listings_deactivated || 0
      const remaining = res.data?.owned_items_remaining || 0
      let msg = `تم أرشفة «${archivingItem.name}»`
      if (deactivated > 0) msg += ` — تم إخفاء ${deactivated} عرض`
      if (remaining > 0) msg += ` — ${remaining} نسخة لا تزال مملوكة للاعبين`
      flashMessage(msg)
      setArchivingItem(null)
      refetchItems()
    } catch (err) { flashMessage(`خطأ: ${err.message}`) }
    finally { setArchiveLoading(false) }
  }

  async function handleBulkRevoke() {
    if (!revokingItem) return
    setRevokeLoading(true)
    try {
      const res = await apiFetch(`/api/admin/store/items/${revokingItem.id}/revoke-all`, {
        method: 'POST', body: JSON.stringify({ reason: 'مصادرة جماعية بعد أرشفة العنصر' }),
      })
      flashMessage(`تمت مصادرة ${res.data?.revoked_count || 0} نسخة من ${res.data?.players_affected || 0} لاعب`)
      setRevokingItem(null)
      refetchItems()
    } catch (err) { flashMessage(`خطأ: ${err.message}`) }
    finally { setRevokeLoading(false) }
  }

  function handleItemSaved() {
    setShowItemForm(false)
    flashMessage(editingItem ? 'تم تعديل العنصر' : 'تم إنشاء العنصر')
    setEditingItem(null)
    refetchItems()
  }

  async function toggleExpand(itemId) {
    if (expandedId === itemId) { setExpandedId(null); return }
    setExpandedId(itemId)
    setLoadingDetail(true)
    try {
      const res = await apiFetch(`/api/admin/store/items/${itemId}`)
      setItemDetail(res.data)
    } catch (err) {
      flashMessage(`خطأ: ${err.message}`)
      setExpandedId(null)
    } finally { setLoadingDetail(false) }
  }

  async function reloadDetail() {
    if (!expandedId) return
    try {
      const res = await apiFetch(`/api/admin/store/items/${expandedId}`)
      setItemDetail(res.data)
    } catch {}
  }

  function handleEffectSaved() {
    setShowEffectForm(false)
    setEditingEffect(null)
    flashMessage(editingEffect ? 'تم تعديل التأثير' : 'تم إضافة التأثير')
    reloadDetail()
  }

  async function handleDeleteEffect(effectId) {
    try {
      await apiFetch(`/api/admin/store/items/${expandedId}/effects/${effectId}`, { method: 'DELETE' })
      flashMessage('تم حذف التأثير')
      reloadDetail()
    } catch (err) { flashMessage(`خطأ: ${err.message}`) }
  }

  return (
    <>
      {/* Header + Create */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500 dark:text-gray-400 font-bold">
          تعريفات العناصر الأساسية — القوالب التي يُبنى عليها عروض المتجر
        </p>
        <button onClick={() => { setEditingItem(null); setShowItemForm(true) }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition">
          <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
          إنشاء عنصر
        </button>
      </div>

      {/* Cards Grid */}
      {(!items || items.length === 0) ? (
        <div className="text-center py-16">
          <iconify-icon icon="lucide:box" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="font-bold text-gray-400">لا توجد عناصر — أنشئ عنصراً جديداً للبدء</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {items.map(item => (
            <div key={item.id} className={`bg-white dark:bg-brand-card-dark border-2 rounded-2xl overflow-hidden smooth-transition ${RARITY_COLORS[item.rarity] || 'border-gray-200 dark:border-gray-700'} ${item.status === 'archived' ? 'opacity-50' : ''}`}>
              {/* Card Header */}
              <div className="p-4 pb-3">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: RARITY_DOT_COLORS[item.rarity] || '#94A3B8' }} />
                    <h3 className="font-heading font-black text-gray-900 dark:text-white truncate">{item.name}</h3>
                  </div>
                  <div className="flex items-center gap-0.5 flex-shrink-0">
                    <button onClick={() => { setEditingItem(item); setShowItemForm(true) }}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-brand-teal hover:bg-brand-teal/10 smooth-transition" title="تعديل">
                      <iconify-icon icon="lucide:pencil" class="text-sm"></iconify-icon>
                    </button>
                    {item.status !== 'archived' ? (
                      <button onClick={() => setArchivingItem(item)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30 smooth-transition" title="أرشفة — إيقاف البيع">
                        <iconify-icon icon="lucide:archive" class="text-sm"></iconify-icon>
                      </button>
                    ) : item.owned_count > 0 ? (
                      <button onClick={() => setRevokingItem(item)}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-brand-danger hover:bg-brand-danger/10 smooth-transition" title="مصادرة من جميع اللاعبين">
                        <iconify-icon icon="lucide:user-x" class="text-sm"></iconify-icon>
                      </button>
                    ) : null}
                  </div>
                </div>
                {item.description && (
                  <p className="text-xs text-gray-400 mb-2 line-clamp-2">{item.description}</p>
                )}
                {/* Meta badges */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  <StatusBadge status={item.rarity} map={RARITY_LABELS} />
                  <StatusBadge status={item.status} />
                  {item.category && <span className="px-2 py-0.5 rounded-md text-[11px] font-black bg-gray-100 dark:bg-gray-800 text-gray-500">{CATEGORY_LABELS[item.category] || item.category}</span>}
                  <span className="px-2 py-0.5 rounded-md text-[11px] font-black bg-gray-100 dark:bg-gray-800 text-gray-500">{USAGE_TYPE_LABELS[item.usage_type] || item.usage_type}</span>
                </div>
                {/* Stats row */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">التأثيرات</div>
                    <div className="font-heading font-black text-sm text-brand-teal dark:text-brand-slate">{item.effect_count || 0}</div>
                  </div>
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">العروض</div>
                    <div className="font-heading font-black text-sm text-gray-900 dark:text-white">{item.listing_count || 0}</div>
                  </div>
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">مملوك</div>
                    <div className="font-heading font-black text-sm text-gray-900 dark:text-white">{item.owned_count || 0}</div>
                  </div>
                </div>
              </div>

              {/* Effects toggle */}
              <button onClick={() => toggleExpand(item.id)}
                className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 border-t text-xs font-bold smooth-transition ${
                  expandedId === item.id
                    ? 'bg-brand-teal/5 dark:bg-brand-slate/5 text-brand-teal dark:text-brand-slate border-brand-teal/20 dark:border-brand-slate/20'
                    : 'bg-gray-50/50 dark:bg-gray-800/20 text-gray-400 border-gray-100 dark:border-gray-800 hover:text-brand-teal dark:hover:text-brand-slate'
                }`}>
                <iconify-icon icon="lucide:sparkles" class="text-xs"></iconify-icon>
                التأثيرات ({item.effect_count || 0})
                <iconify-icon icon={expandedId === item.id ? 'lucide:chevron-up' : 'lucide:chevron-down'} class="text-xs"></iconify-icon>
              </button>

              {/* Expanded effects panel */}
              {expandedId === item.id && (
                <div className="border-t border-gray-100 dark:border-gray-800 p-4 bg-gray-50/50 dark:bg-gray-800/20 space-y-3">
                  {loadingDetail ? (
                    <div className="flex items-center justify-center py-4">
                      <iconify-icon icon="lucide:loader-2" class="text-xl text-brand-teal animate-spin"></iconify-icon>
                    </div>
                  ) : itemDetail ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">التأثيرات المرفقة</span>
                        <button onClick={() => { setEditingEffect(null); setShowEffectForm(true) }}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-brand-teal/10 text-brand-teal hover:bg-brand-teal/20 smooth-transition">
                          <iconify-icon icon="lucide:plus" class="text-xs"></iconify-icon>
                          إضافة
                        </button>
                      </div>
                      {itemDetail.effects?.length === 0 ? (
                        <p className="text-xs text-gray-400 text-center py-2">لا توجد تأثيرات</p>
                      ) : (
                        <div className="space-y-2">
                          {itemDetail.effects.map(eff => (
                            <div key={eff.id} className="flex items-center justify-between p-2.5 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-xl">
                              <div className="flex items-center gap-2 flex-wrap min-w-0">
                                <span className="px-2 py-0.5 rounded-md text-[11px] font-black bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate whitespace-nowrap">
                                  {eff.effect_type}
                                </span>
                                <span className="text-[11px] text-gray-600 dark:text-gray-300 font-bold truncate">
                                  {eff.summary || JSON.stringify(eff.parameters)}
                                </span>
                                <span className="text-[10px] text-gray-400">{SCOPE_LABELS[eff.target_scope] || eff.target_scope}</span>
                              </div>
                              <div className="flex items-center gap-0.5 flex-shrink-0">
                                <button onClick={() => { setEditingEffect(eff); setShowEffectForm(true) }}
                                  className="p-1 rounded text-gray-400 hover:text-brand-teal smooth-transition" title="تعديل">
                                  <iconify-icon icon="lucide:pencil" class="text-xs"></iconify-icon>
                                </button>
                                <button onClick={() => handleDeleteEffect(eff.id)}
                                  className="p-1 rounded text-gray-400 hover:text-brand-danger smooth-transition" title="حذف">
                                  <iconify-icon icon="lucide:trash-2" class="text-xs"></iconify-icon>
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showItemForm && <ItemFormModal item={editingItem} onClose={() => { setShowItemForm(false); setEditingItem(null) }} onSaved={handleItemSaved} />}

      {archivingItem && (
        <ConfirmDialog
          title="أرشفة العنصر"
          message={
            `هل أنت متأكد من أرشفة «${archivingItem.name}»؟` +
            (archivingItem.listing_count > 0
              ? `\n\nسيتم إخفاء ${archivingItem.listing_count} عرض نشط تلقائياً — لن يتمكن اللاعبون من شرائه بعد الآن.`
              : '') +
            (archivingItem.owned_count > 0
              ? `\n\n${archivingItem.owned_count} نسخة مملوكة للاعبين ستبقى في مخزونهم. يمكنك مصادرتها لاحقاً إذا أردت.`
              : '') +
            '\n\nلا يمكن التراجع عن هذا الإجراء.'
          }
          onConfirm={handleArchiveItem}
          onCancel={() => setArchivingItem(null)}
          loading={archiveLoading}
        />
      )}

      {revokingItem && (
        <ConfirmDialog
          title="مصادرة جماعية"
          message={`هل أنت متأكد من مصادرة جميع نسخ «${revokingItem.name}» من مخزون اللاعبين؟\n\nسيتم إزالة ${revokingItem.owned_count} نسخة نشطة وإبلاغ كل لاعب متأثر.\n\nسجلات الشراء والاستخدام السابقة لن تتأثر.`}
          onConfirm={handleBulkRevoke}
          onCancel={() => setRevokingItem(null)}
          loading={revokeLoading}
        />
      )}

      {showEffectForm && expandedId && <EffectFormModal itemId={expandedId} effect={editingEffect} onClose={() => { setShowEffectForm(false); setEditingEffect(null) }} onSaved={handleEffectSaved} />}
    </>
  )
}

/* ════════════════════════════════════════════════════════════════
   TAB: Store Listings (عروض المتجر)
   ════════════════════════════════════════════════════════════════ */
function StoreListingsTab({ listings, items, competitionId, refetchListings, flashMessage }) {
  const [showListingForm, setShowListingForm] = useState(false)
  const [editingListing, setEditingListing] = useState(null)
  const [deletingListing, setDeletingListing] = useState(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  async function toggleStatus(listingId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'hidden' : 'active'
    try {
      await apiFetch(`/api/admin/store/listings/${listingId}`, { method: 'PATCH', body: JSON.stringify({ status: newStatus }) })
      flashMessage('تم التحديث')
      refetchListings()
    } catch (err) { flashMessage(`خطأ: ${err.message}`) }
  }

  async function handleDeleteListing() {
    if (!deletingListing) return
    setDeleteLoading(true)
    try {
      await apiFetch(`/api/admin/store/listings/${deletingListing.listing_id}`, { method: 'DELETE' })
      flashMessage('تم إخفاء العرض')
      setDeletingListing(null)
      refetchListings()
    } catch (err) { flashMessage(`خطأ: ${err.message}`) }
    finally { setDeleteLoading(false) }
  }

  function handleListingSaved() {
    setShowListingForm(false)
    flashMessage(editingListing ? 'تم تعديل العرض' : 'تم إنشاء العرض')
    setEditingListing(null)
    refetchListings()
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500 dark:text-gray-400 font-bold">
          عروض المتجر النشطة في المنافسة — ما يراه اللاعبون ويشترونه
        </p>
        <button onClick={() => { setEditingListing(null); setShowListingForm(true) }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-teal text-white text-sm font-bold hover:bg-brand-teal-hover smooth-transition">
          <iconify-icon icon="lucide:plus" class="text-sm"></iconify-icon>
          إنشاء عرض
        </button>
      </div>

      {(!listings || listings.length === 0) ? (
        <div className="text-center py-16">
          <iconify-icon icon="lucide:store" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="font-bold text-gray-400">لا توجد عروض — أنشئ عرضاً من كتالوج العناصر</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {listings.map(l => (
            <div key={l.listing_id} className={`bg-white dark:bg-brand-card-dark border-2 rounded-2xl overflow-hidden ${RARITY_COLORS[l.item_rarity] || 'border-gray-200 dark:border-gray-700'}`}>
              <div className="p-5">
                {/* Header row */}
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: RARITY_DOT_COLORS[l.item_rarity] || '#94A3B8' }} />
                      <h3 className="font-heading font-black text-gray-900 dark:text-white truncate">{l.item_name}</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={l.status} />
                      <StatusBadge status={l.item_rarity} map={RARITY_LABELS} />
                      {l.item_category && <span className="text-[10px] font-bold text-gray-400">{CATEGORY_LABELS[l.item_category] || l.item_category}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-0.5 flex-shrink-0">
                    <button onClick={() => { setEditingListing(l); setShowListingForm(true) }}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-brand-teal hover:bg-brand-teal/10 smooth-transition" title="تعديل السعر/المخزون">
                      <iconify-icon icon="lucide:pencil" class="text-sm"></iconify-icon>
                    </button>
                    <button onClick={() => toggleStatus(l.listing_id, l.status)}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-bold smooth-transition ${
                        l.status === 'active'
                          ? 'text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30'
                          : 'text-brand-success hover:bg-brand-success/10'
                      }`}>
                      {l.status === 'active' ? 'إخفاء' : 'تفعيل'}
                    </button>
                    <button onClick={() => setDeletingListing(l)}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-brand-danger hover:bg-brand-danger/10 smooth-transition" title="حذف">
                      <iconify-icon icon="lucide:trash-2" class="text-sm"></iconify-icon>
                    </button>
                  </div>
                </div>

                {l.item_description && (
                  <p className="text-xs text-gray-400 mb-3 line-clamp-2">{l.item_description}</p>
                )}

                {/* Stats grid */}
                <div className="grid grid-cols-4 gap-2 text-sm">
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">السعر</div>
                    <div className="font-heading font-black text-brand-teal dark:text-brand-slate">{l.price}</div>
                  </div>
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">المبيعات</div>
                    <div className="font-heading font-black text-gray-900 dark:text-white">{l.sold_count || 0}</div>
                  </div>
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">المخزون</div>
                    <div className="font-heading font-black text-gray-900 dark:text-white">{l.total_stock ?? '∞'}</div>
                  </div>
                  <div className="p-2 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                    <div className="text-[10px] font-black text-gray-400 uppercase">المتبقي</div>
                    <div className={`font-heading font-black ${l.remaining_stock === 0 ? 'text-brand-danger' : 'text-gray-900 dark:text-white'}`}>
                      {l.remaining_stock ?? '∞'}
                    </div>
                  </div>
                </div>
                {l.max_per_participant && (
                  <div className="mt-2 text-[11px] text-gray-400 flex items-center gap-1">
                    <iconify-icon icon="lucide:user" class="text-[10px]"></iconify-icon>
                    الحد الأقصى لكل لاعب: {l.max_per_participant}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {showListingForm && <ListingFormModal items={items} listing={editingListing} competitionId={competitionId} onClose={() => { setShowListingForm(false); setEditingListing(null) }} onSaved={handleListingSaved} />}
      {deletingListing && <ConfirmDialog title="إخفاء العرض من المتجر" message={`هل أنت متأكد من إخفاء عرض «${deletingListing.item_name}»؟\n\nلن يظهر العرض في المتجر بعد الآن، لكن العناصر المباعة سابقاً ستبقى عند اللاعبين.`} onConfirm={handleDeleteListing} onCancel={() => setDeletingListing(null)} loading={deleteLoading} />}
    </>
  )
}

/* ════════════════════════════════════════════════════════════════
   TAB: Ownership (ملكية اللاعبين)
   ════════════════════════════════════════════════════════════════ */
function OwnershipTab({ ownership, loading }) {
  const [filter, setFilter] = useState('all') // all | active | consumed

  const filtered = ownership?.filter(o => {
    if (filter === 'active') return o.status === 'active'
    if (filter === 'consumed') return o.status === 'consumed' || o.status === 'expired'
    return true
  }) || []

  return (
    <>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <p className="text-sm text-gray-500 dark:text-gray-400 font-bold">
          نظرة شاملة على العناصر المملوكة للاعبين في هذه المنافسة
        </p>
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
          {[
            { key: 'all', label: 'الكل' },
            { key: 'active', label: 'نشط' },
            { key: 'consumed', label: 'مستهلك' },
          ].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-md text-xs font-bold smooth-transition ${filter === f.key ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm' : 'text-gray-500'}`}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <iconify-icon icon="lucide:loader-2" class="text-3xl text-brand-teal animate-spin"></iconify-icon>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <iconify-icon icon="lucide:package-open" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
          <p className="font-bold text-gray-400">
            {filter !== 'all' ? 'لا توجد عناصر بهذه الحالة' : 'لا توجد عناصر مملوكة بعد'}
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">اللاعب</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">العنصر</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">المصدر</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الكمية</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">الحالة</th>
                  <th className="text-right px-4 py-3 font-black text-gray-500 text-[11px] uppercase tracking-widest">التاريخ</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(o => (
                  <tr key={o.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/20 smooth-transition">
                    <td className="px-4 py-3">
                      <Link to={`/admin/players/${o.membership_id}`} className="hover:text-brand-teal dark:hover:text-brand-slate smooth-transition">
                        <div className="font-bold text-gray-900 dark:text-white">{o.player_alias || '—'}</div>
                        <div className="text-[11px] text-gray-400">@{o.player_username}</div>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: RARITY_DOT_COLORS[o.item_rarity] || '#94A3B8' }} />
                        <div>
                          <div className="font-bold text-gray-900 dark:text-white">{o.item_name}</div>
                          <div className="text-[10px] text-gray-400">{RARITY_LABELS[o.item_rarity] || o.item_rarity} • {CATEGORY_LABELS[o.item_category] || o.item_category}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-md text-[11px] font-black ${
                        o.source_type === 'admin_grant' ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-600' :
                        o.source_type === 'purchase' ? 'bg-brand-teal/10 text-brand-teal' :
                        'bg-gray-100 dark:bg-gray-800 text-gray-500'
                      }`}>
                        {SOURCE_LABELS[o.source_type] || o.source_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-heading font-black text-gray-900 dark:text-white">
                      {o.quantity}{o.uses_remaining != null && <span className="text-[10px] text-gray-400 font-normal mr-1">({o.uses_remaining} استخدام)</span>}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={o.status} /></td>
                    <td className="px-4 py-3 text-[11px] text-gray-400 whitespace-nowrap">
                      {o.acquired_at ? formatDate(o.acquired_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/40 text-[11px] text-gray-400 font-bold border-t border-gray-100 dark:border-gray-800">
            إجمالي: {filtered.length} عنصر
          </div>
        </div>
      )}
    </>
  )
}

/* ════════════════════════════════════════════════════════════════
   MAIN PAGE
   ════════════════════════════════════════════════════════════════ */
export default function AdminStorePage() {
  const { selected, selectedId } = useAdminCompetition()
  const [tab, setTab] = useState('catalog')
  const { data: items, loading: loadingItems, refetch: refetchItems } = useAdminData('/api/admin/store/items')
  const { data: listings, loading: loadingListings, refetch: refetchListings } = useAdminData(
    selectedId ? `/api/admin/store/listings?competition_id=${selectedId}` : null
  )
  const { data: ownership, loading: loadingOwnership, refetch: refetchOwnership } = useAdminData(
    selectedId ? `/api/admin/store/ownership?competition_id=${selectedId}` : null
  )
  const [actionMsg, setActionMsg] = useState(null)

  function flashMessage(msg) {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 2500)
  }

  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <iconify-icon icon="lucide:shopping-bag" class="text-4xl text-gray-300 dark:text-gray-600 mb-3"></iconify-icon>
        <p className="font-bold text-gray-500 dark:text-gray-400">اختر منافسة من القائمة الجانبية لإدارة المتجر</p>
      </div>
    )
  }

  // Summary stats
  const totalItems = items?.length || 0
  const activeItems = items?.filter(i => i.status === 'active').length || 0
  const activeListings = listings?.filter(l => l.status === 'active').length || 0
  const totalSold = listings?.reduce((sum, l) => sum + (l.sold_count || 0), 0) || 0
  const itemsInCirculation = ownership?.filter(o => o.status === 'active').length || 0

  const tabs = [
    { key: 'catalog', label: 'كتالوج العناصر', icon: 'lucide:box', count: totalItems },
    { key: 'listings', label: 'عروض المتجر', icon: 'lucide:store', count: activeListings },
    { key: 'ownership', label: 'ملكية اللاعبين', icon: 'lucide:users', count: itemsInCirculation },
  ]

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div>
        <h1 className="font-heading font-black text-2xl text-gray-900 dark:text-white">إدارة المتجر</h1>
        <p className="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1">{selected.name} — العناصر والعروض والملكية</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon="lucide:box" label="العناصر" value={`${activeItems} / ${totalItems}`} />
        <StatCard icon="lucide:store" label="عروض نشطة" value={activeListings} color="bg-brand-success/10 text-brand-success" />
        <StatCard icon="lucide:shopping-cart" label="إجمالي المبيعات" value={totalSold} color="bg-blue-50 dark:bg-blue-900/20 text-blue-500" />
        <StatCard icon="lucide:package" label="عناصر متداولة" value={itemsInCirculation} color="bg-purple-50 dark:bg-purple-900/20 text-purple-500" />
      </div>

      {/* Action message */}
      {actionMsg && (
        <div className={`px-4 py-2 rounded-xl text-sm font-bold ${actionMsg.startsWith('خطأ') ? 'bg-brand-danger/10 text-brand-danger' : 'bg-brand-success/10 text-brand-success'}`}>
          {actionMsg}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold smooth-transition ${
              tab === t.key ? 'bg-white dark:bg-brand-card-dark text-brand-teal dark:text-brand-slate shadow-sm' : 'text-gray-500'
            }`}>
            <iconify-icon icon={t.icon} class="text-sm"></iconify-icon>
            {t.label}
            <span className={`text-[10px] px-1.5 py-0.5 rounded-md font-black ${
              tab === t.key ? 'bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate' : 'bg-gray-200 dark:bg-gray-700 text-gray-400'
            }`}>{t.count}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'catalog' && (
        loadingItems ? (
          <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
        ) : (
          <ItemCatalogTab items={items} refetchItems={refetchItems} flashMessage={flashMessage} />
        )
      )}

      {tab === 'listings' && (
        loadingListings ? (
          <div className="flex items-center justify-center py-20"><iconify-icon icon="lucide:loader-2" class="text-4xl text-brand-teal animate-spin"></iconify-icon></div>
        ) : (
          <StoreListingsTab listings={listings} items={items} competitionId={selectedId} refetchListings={refetchListings} flashMessage={flashMessage} />
        )
      )}

      {tab === 'ownership' && (
        <OwnershipTab ownership={ownership} loading={loadingOwnership} />
      )}
    </div>
  )
}
