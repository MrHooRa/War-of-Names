/**
 * AttackModal — the core guessing interface.
 *
 * Props:
 *  - targetMembershipId: UUID of the player being attacked
 *  - targetAlias: display name of the target
 *  - myMembershipId: UUID of the current user's membership (for UI filtering only)
 *  - competitionId: UUID of the competition
 *  - onClose: () => void
 */

import { useState, useEffect } from 'react'
import useAttackPreview from '../hooks/useAttackPreview'
import useAttackExecute from '../hooks/useAttackExecute'
import useMemberIdentities from '../hooks/useMemberIdentities'

/**
 * Categorize active_modifiers from backend into offensive / defensive / situational
 * based on Arabic keyword matching in the modifier text.
 */
function categorizeModifiers(modifiers) {
  const offensive = []
  const defensive = []
  const situational = []

  for (const mod of modifiers) {
    if (mod.includes('مكافأة') || mod.includes('عند النجاح') || mod.includes('زيادة')) {
      offensive.push(mod)
    } else if (mod.includes('خسارة') || mod.includes('عند الفشل') || mod.includes('تقليل') || mod.includes('درع') || mod.includes('دفاعي')) {
      defensive.push(mod)
    } else {
      situational.push(mod)
    }
  }

  return { offensive, defensive, situational }
}

function ModifierGroup({ items, icon, iconColor, bgColor, borderColor, label }) {
  if (!items.length) return null
  return (
    <div className={`${bgColor} border ${borderColor} rounded-xl p-3 space-y-1.5`}>
      <div className="flex items-center gap-2 mb-1">
        <iconify-icon icon={icon} class={`text-sm ${iconColor}`}></iconify-icon>
        <span className={`text-[10px] font-black ${iconColor} uppercase tracking-widest`}>{label}</span>
      </div>
      {items.map((mod, i) => (
        <div key={i} className="flex items-center gap-2 text-xs font-bold text-gray-700 dark:text-gray-300">
          <iconify-icon icon="lucide:sparkles" class={`text-[10px] ${iconColor} flex-shrink-0`}></iconify-icon>
          <span>{mod}</span>
        </div>
      ))}
    </div>
  )
}

function DecayIndicator({ stage }) {
  if (stage === null || stage === undefined || stage === 0) return null
  const dots = Math.min(stage, 5)
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/5 dark:bg-amber-500/10 border border-amber-500/20 rounded-xl">
      <iconify-icon icon="lucide:trending-down" class="text-sm text-amber-500 flex-shrink-0"></iconify-icon>
      <span className="text-[11px] font-bold text-amber-600 dark:text-amber-400">
        مرحلة الانحلال {stage} — المكافأة مخفّضة
      </span>
      <div className="flex gap-0.5 mr-auto">
        {Array(dots).fill(0).map((_, i) => (
          <div key={i} className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
        ))}
        {Array(Math.max(0, 5 - dots)).fill(0).map((_, i) => (
          <div key={i} className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600"></div>
        ))}
      </div>
    </div>
  )
}

function ProtectionBadge({ protection }) {
  if (!protection || protection === 'none') return null
  const isPartial = protection === 'partial'
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border ${
      isPartial
        ? 'bg-amber-500/5 dark:bg-amber-500/10 border-amber-500/20'
        : 'bg-blue-500/5 dark:bg-blue-500/10 border-blue-500/20'
    }`}>
      <iconify-icon
        icon={isPartial ? 'lucide:shield-half' : 'lucide:shield-check'}
        class={`text-sm flex-shrink-0 ${isPartial ? 'text-amber-500' : 'text-blue-500'}`}
      ></iconify-icon>
      <span className={`text-[11px] font-bold ${isPartial ? 'text-amber-600 dark:text-amber-400' : 'text-blue-600 dark:text-blue-400'}`}>
        {isPartial ? 'الهدف محمي جزئياً — خسائره مخفّضة' : 'الهدف محمي بالكامل'}
      </span>
    </div>
  )
}

export default function AttackModal({
  targetMembershipId,
  targetAlias,
  myMembershipId,
  competitionId,
  onClose,
}) {
  const [search, setSearch] = useState('')
  const [selectedIdentity, setSelectedIdentity] = useState(null)

  const { identities, loading: identitiesLoading } = useMemberIdentities(competitionId)
  const { preview, loading: previewLoading, fetchPreview } = useAttackPreview(competitionId)
  const { executing, error: executeError, executeAttack } = useAttackExecute(competitionId)

  // Load preview when target is known (attacker derived server-side from JWT)
  useEffect(() => {
    if (targetMembershipId) {
      fetchPreview(targetMembershipId)
    }
  }, [targetMembershipId, fetchPreview])

  // Filter identities by search — exclude self from the guess list
  const filtered = identities.filter(
    (id) =>
      id.membership_id !== myMembershipId &&
      id.real_name.includes(search)
  )

  function handleConfirm() {
    if (!selectedIdentity) return
    executeAttack(targetMembershipId, selectedIdentity.account_id)
  }

  const canAttack = preview?.can_attack !== false
  const estimatedReward = preview?.estimated_reward ?? 0
  const estimatedPenalty = preview?.estimated_penalty ?? 0
  const modifiers = preview?.active_modifiers ?? []
  const hasModifiers = modifiers.length > 0
  const { offensive, defensive, situational } = categorizeModifiers(modifiers)
  const decayStage = preview?.target_current_stage ?? 0

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-full max-w-lg bg-white dark:bg-brand-card-dark rounded-3xl shadow-2xl border border-gray-100 dark:border-gray-800 overflow-hidden max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-orange/10 rounded-xl flex items-center justify-center text-brand-orange">
              <iconify-icon icon="lucide:swords" class="text-xl"></iconify-icon>
            </div>
            <div>
              <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white leading-tight">
                هجوم على {targetAlias}
              </h2>
              <p className="text-xs text-gray-400 font-medium">خمّن هويته الحقيقية</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 smooth-transition"
          >
            <iconify-icon icon="lucide:x" class="text-lg"></iconify-icon>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4 inventory-scroll">

          {/* ── Tactical Briefing ── */}
          {previewLoading ? (
            <div className="space-y-3">
              <div className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />
              <div className="h-10 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
            </div>
          ) : preview && !canAttack ? (
            <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-2xl p-5 flex items-center gap-4 text-red-600 dark:text-red-400">
              <div className="w-12 h-12 bg-red-100 dark:bg-red-900/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <iconify-icon icon="lucide:shield-off" class="text-2xl"></iconify-icon>
              </div>
              <div>
                <div className="font-heading font-black text-sm mb-0.5">لا يمكن الهجوم</div>
                <p className="font-bold text-sm">{preview.blocking_reason}</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Reward / Penalty cards */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-brand-teal/5 dark:bg-brand-teal/10 border border-brand-teal/20 rounded-2xl p-4 text-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-brand-teal/5 blur-xl rounded-full opacity-0 group-hover:opacity-100 smooth-transition"></div>
                  <div className="relative z-10">
                    <div className="flex items-center justify-center gap-1.5 mb-1.5">
                      <iconify-icon icon="lucide:trophy" class="text-sm text-brand-teal"></iconify-icon>
                      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">مكافأة الفوز</div>
                    </div>
                    <div className="font-display text-3xl font-black text-brand-teal">+{estimatedReward}</div>
                  </div>
                </div>
                <div className="bg-brand-orange/5 dark:bg-brand-orange/10 border border-brand-orange/20 rounded-2xl p-4 text-center relative overflow-hidden">
                  <div className="relative z-10">
                    <div className="flex items-center justify-center gap-1.5 mb-1.5">
                      <iconify-icon icon="lucide:alert-triangle" class="text-sm text-brand-orange"></iconify-icon>
                      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">خسارة الفشل</div>
                    </div>
                    <div className="font-display text-3xl font-black text-brand-orange">-{estimatedPenalty}</div>
                  </div>
                </div>
              </div>

              {/* Decay stage indicator */}
              <DecayIndicator stage={decayStage} />

              {/* Target protection indicator */}
              <ProtectionBadge protection={preview?.target_protection} />

              {/* ── Active Modifiers — categorized ── */}
              {hasModifiers && (
                <div className="space-y-2">
                  <ModifierGroup
                    items={offensive}
                    icon="lucide:zap"
                    iconColor="text-brand-teal dark:text-brand-teal"
                    bgColor="bg-brand-teal/5 dark:bg-brand-teal/10"
                    borderColor="border-brand-teal/15 dark:border-brand-teal/20"
                    label="تعزيزات هجومية"
                  />
                  <ModifierGroup
                    items={defensive}
                    icon="lucide:shield"
                    iconColor="text-blue-500 dark:text-blue-400"
                    bgColor="bg-blue-50 dark:bg-blue-900/10"
                    borderColor="border-blue-200 dark:border-blue-800/40"
                    label="عوامل دفاعية"
                  />
                  <ModifierGroup
                    items={situational}
                    icon="lucide:info"
                    iconColor="text-purple-500 dark:text-purple-400"
                    bgColor="bg-purple-50 dark:bg-purple-900/10"
                    borderColor="border-purple-200 dark:border-purple-800/40"
                    label="عوامل أخرى"
                  />
                </div>
              )}

              {/* No modifiers hint */}
              {!hasModifiers && canAttack && (
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800/30 rounded-xl border border-gray-100 dark:border-gray-700">
                  <iconify-icon icon="lucide:package" class="text-sm text-gray-400"></iconify-icon>
                  <span className="text-[11px] font-bold text-gray-400">
                    لا توجد تأثيرات نشطة — فعّل عناصر من المخزن قبل الهجوم لتعزيز فرصك
                  </span>
                </div>
              )}
            </div>
          )}

          {/* ── Identity search ── */}
          <div>
            <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-2">
              اختر الاسم الحقيقي
            </label>
            <div className="relative mb-3">
              <iconify-icon icon="lucide:search" class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg"></iconify-icon>
              <input
                type="text"
                placeholder="ابحث باسم..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl py-3 pr-11 pl-4 text-sm font-medium text-gray-800 dark:text-gray-200 focus:outline-none focus:border-brand-teal dark:focus:border-brand-slate smooth-transition"
              />
            </div>

            <div className="max-h-44 overflow-y-auto space-y-2 inventory-scroll">
              {identitiesLoading ? (
                Array(3).fill(0).map((_, i) => (
                  <div key={i} className="h-14 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
                ))
              ) : filtered.length === 0 ? (
                <p className="text-center text-sm text-gray-400 py-6">لا توجد نتائج</p>
              ) : (
                filtered.map((id) => (
                  <button
                    key={id.account_id}
                    onClick={() => setSelectedIdentity(id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border smooth-transition text-right ${
                      selectedIdentity?.account_id === id.account_id
                        ? 'bg-brand-teal/10 dark:bg-brand-teal/20 border-brand-teal/40 dark:border-brand-teal/30'
                        : 'bg-gray-50 dark:bg-gray-800/60 border-gray-100 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div className="w-10 h-10 rounded-xl bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 flex items-center justify-center font-black text-base text-gray-700 dark:text-gray-200 shrink-0">
                      {id.real_name.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-sm text-gray-900 dark:text-white truncate">{id.real_name}</div>
                    </div>
                    {selectedIdentity?.account_id === id.account_id && (
                      <iconify-icon icon="lucide:check-circle-2" class="text-brand-teal text-xl shrink-0"></iconify-icon>
                    )}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Execute error */}
          {executeError && (
            <p className="text-sm text-brand-danger font-bold text-center">{executeError}</p>
          )}
        </div>

        {/* ── Confirm button — pinned to bottom ── */}
        <div className="p-6 pt-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
          <button
            onClick={handleConfirm}
            disabled={!selectedIdentity || !canAttack || executing}
            className={`w-full py-4 rounded-2xl font-heading font-black text-base smooth-transition flex items-center justify-center gap-2 ${
              selectedIdentity && canAttack && !executing
                ? 'bg-brand-orange hover:bg-brand-orange/90 text-white shadow-lg shadow-brand-orange/20 btn-press'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
            }`}
          >
            {executing ? (
              <>
                <iconify-icon icon="lucide:loader-2" class="text-xl animate-spin"></iconify-icon>
                جارٍ الهجوم...
              </>
            ) : (
              <>
                <iconify-icon icon="lucide:swords" class="text-xl"></iconify-icon>
                {selectedIdentity ? `الهجوم بـ "${selectedIdentity.real_name}"` : 'اختر اسماً أولاً'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
