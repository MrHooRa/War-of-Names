/**
 * PlayerProfilePage — detailed view of a single competitor.
 *
 * Route: /players/:membershipId
 *
 * Shows:
 *  - Alias, balance, protection state, bankruptcy indicator
 *  - Attack exposure stats (how many times they've been hit, current decay stage)
 *  - Recent attacks received (last 10)
 *  - Attack button → opens AttackModal
 *
 * MVP: competitionId and attackerMembershipId are read from URL params / context.
 * For now both come from a single hardcoded competition context via useCompetitionContext.
 */

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import usePlayerProfile from '../hooks/usePlayerProfile'
import useCompetitionContext from '../hooks/useCompetitionContext'
import AttackModal from '../components/AttackModal'

const PROTECTION_LABELS = {
  none: { label: 'نشط', color: 'emerald' },
  partial: { label: 'محمي جزئياً', color: 'amber' },
  full: { label: 'محمي بالكامل', color: 'purple' },
}

function ProtectionBadge({ type }) {
  const cfg = PROTECTION_LABELS[type] ?? PROTECTION_LABELS.none
  const colors = {
    emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
    amber: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
    purple: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
  }
  return (
    <span className={`px-3 py-1 rounded-lg text-xs font-bold ${colors[cfg.color]}`}>
      {cfg.label}
    </span>
  )
}

export default function PlayerProfilePage() {
  const { membershipId } = useParams()
  const { competitionId, membershipId: myMembershipId } = useCompetitionContext()
  const { profile, loading, error } = usePlayerProfile(competitionId, membershipId)
  const [showAttackModal, setShowAttackModal] = useState(false)

  if (loading) {
    return (
      <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-12 space-y-6">
        {Array(3).fill(0).map((_, i) => (
          <div key={i} className="h-32 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />
        ))}
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-24 gap-4">
        <iconify-icon icon="lucide:user-x" class="text-5xl text-gray-300 dark:text-gray-700"></iconify-icon>
        <p className="text-gray-500 font-bold">{error || 'اللاعب غير موجود'}</p>
        <Link to="/leaderboard" className="text-brand-teal font-bold hover:underline">
          العودة للقائمة
        </Link>
      </div>
    )
  }

  const isSelf = myMembershipId === membershipId
  const canAttack = !isSelf && !profile.is_bankrupt && profile.protection !== 'full'

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-8 md:py-14 space-y-6">

      {/* Back link */}
      <Link to="/leaderboard" className="inline-flex items-center gap-2 text-sm font-bold text-gray-400 hover:text-brand-teal smooth-transition">
        <iconify-icon icon="lucide:arrow-right" class="text-base"></iconify-icon>
        العودة للمتصدرين
      </Link>

      {/* Hero Card */}
      <div className="bg-white dark:bg-brand-card-dark border border-gray-100 dark:border-gray-800 rounded-3xl p-8 shadow-sm flex flex-col md:flex-row items-center gap-6">
        {/* Avatar */}
        <div className={`w-20 h-20 rounded-2xl flex items-center justify-center font-black text-4xl shrink-0 ${
          profile.is_bankrupt
            ? 'bg-gray-100 dark:bg-gray-800 text-gray-300 dark:text-gray-600'
            : 'bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate'
        }`}>
          {profile.alias.charAt(0)}
        </div>

        <div className="flex-1 text-center md:text-right space-y-2">
          <div className="flex flex-wrap justify-center md:justify-start items-center gap-2">
            <h1 className={`font-heading text-2xl font-black ${profile.is_bankrupt ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}`}>
              {profile.alias}
            </h1>
            {profile.is_bankrupt ? (
              <span className="bg-red-50 text-red-500 dark:bg-red-900/10 dark:text-red-400 px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1">
                <iconify-icon icon="lucide:ghost"></iconify-icon> مفلس
              </span>
            ) : (
              <ProtectionBadge type={profile.protection} />
            )}
          </div>

          {/* Real name if bankrupt */}
          {profile.real_name && (
            <p className="text-sm font-bold text-brand-danger">الهوية المكشوفة: {profile.real_name}</p>
          )}

          <div className="flex flex-wrap justify-center md:justify-start gap-4 text-sm font-bold text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1">
              <iconify-icon icon="lucide:zap" class="text-brand-teal dark:text-brand-slate"></iconify-icon>
              {profile.balance.toLocaleString('ar-EG')} نقطة
            </span>
            <span className="flex items-center gap-1">
              <iconify-icon icon="lucide:target"></iconify-icon>
              تعرض لـ {profile.exposure.successful_attack_count} هجمة ناجحة
            </span>
          </div>
        </div>

        {/* Self profile indicator */}
        {isSelf && (
          <div className="flex flex-col items-center gap-2">
            <span className="px-4 py-2 rounded-xl bg-brand-teal/10 text-brand-teal dark:bg-brand-slate/10 dark:text-brand-slate text-sm font-black flex items-center gap-2">
              <iconify-icon icon="lucide:user-check" class="text-base"></iconify-icon>
              ملفي الشخصي
            </span>
            <Link
              to="/settings"
              className="text-xs font-bold text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate smooth-transition flex items-center gap-1"
            >
              <iconify-icon icon="lucide:settings" class="text-xs"></iconify-icon>
              إعدادات الحساب
            </Link>
          </div>
        )}
        {/* Attack button */}
        {!isSelf && (
          <button
            onClick={() => setShowAttackModal(true)}
            disabled={!canAttack}
            className={`btn-press px-8 py-3.5 rounded-2xl font-heading font-black text-base smooth-transition flex items-center gap-2 shadow-sm ${
              canAttack
                ? 'bg-brand-orange hover:bg-brand-orange/90 text-white shadow-brand-orange/20 hover:shadow-md'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
            }`}
          >
            <iconify-icon icon="lucide:swords" class="text-xl"></iconify-icon>
            {canAttack ? 'هجوم' : 'مغلق'}
          </button>
        )}
      </div>

      {/* Exposure stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-brand-card-dark border border-gray-100 dark:border-gray-800 rounded-2xl p-5 text-center shadow-sm">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">هجمات ناجحة عليه</div>
          <div className="font-display text-3xl font-black text-gray-900 dark:text-white">
            {profile.exposure.successful_attack_count}
          </div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-100 dark:border-gray-800 rounded-2xl p-5 text-center shadow-sm">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">مرحلة الانحلال</div>
          <div className="font-display text-3xl font-black text-brand-teal dark:text-brand-slate">
            {profile.exposure.current_reward_stage}
          </div>
        </div>
        <div className="bg-white dark:bg-brand-card-dark border border-gray-100 dark:border-gray-800 rounded-2xl p-5 text-center shadow-sm">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">الحالة</div>
          <div className="text-sm font-black mt-2">
            {profile.exposure.max_attacks_reached
              ? <span className="text-purple-500">محمي</span>
              : <span className="text-emerald-500">مكشوف</span>
            }
          </div>
        </div>
      </div>

      {/* Recent attacks received */}
      {profile.recent_attacks.length > 0 && (
        <div className="bg-white dark:bg-brand-card-dark border border-gray-100 dark:border-gray-800 rounded-3xl p-6 shadow-sm">
          <h2 className="font-heading font-black text-base text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
            <iconify-icon icon="lucide:history" class="text-lg text-gray-400"></iconify-icon>
            آخر الهجمات الواردة
          </h2>
          <div className="space-y-3">
            {profile.recent_attacks.map((atk) => (
              <div key={atk.attempt_id} className="flex items-center justify-between py-2 border-b border-gray-50 dark:border-gray-800 last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${
                    atk.outcome === 'succeeded'
                      ? 'bg-red-50 text-red-500 dark:bg-red-900/10'
                      : 'bg-emerald-50 text-emerald-500 dark:bg-emerald-900/10'
                  }`}>
                    <iconify-icon icon={atk.outcome === 'succeeded' ? 'lucide:zap' : 'lucide:shield'}></iconify-icon>
                  </div>
                  <span className="text-sm font-bold text-gray-600 dark:text-gray-300">
                    {atk.outcome === 'succeeded' ? 'هجوم ناجح — تكشّف' : 'هجوم فاشل — نجا'}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-sm font-bold">
                  {atk.reward_amount > 0 && (
                    <span className="text-red-500">-{atk.reward_amount}</span>
                  )}
                  <span className="text-gray-300 dark:text-gray-600 text-xs">
                    {new Date(atk.executed_at).toLocaleDateString('ar-SA')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Attack Modal */}
      {showAttackModal && (
        <AttackModal
          targetMembershipId={membershipId}
          targetAlias={profile.alias}
          myMembershipId={myMembershipId}
          competitionId={competitionId}
          onClose={() => setShowAttackModal(false)}
        />
      )}
    </div>
  )
}
