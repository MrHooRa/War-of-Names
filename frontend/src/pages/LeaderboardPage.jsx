/**
 * LeaderboardPage — ranked list of all active competitors.
 * Wired to GET /api/competitions/{comp_id}/leaderboard
 * Attack buttons navigate to /players/:membershipId
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import useLeaderboard from '../hooks/useLeaderboard'
import useCompetitionContext from '../hooks/useCompetitionContext'

function RankBadge({ rank }) {
  if (rank === 1) return <div className="rank-badge-1 w-11 h-11 flex items-center justify-center rounded-xl font-display font-black text-xl shadow-sm">{rank}</div>
  if (rank === 2) return <div className="rank-badge-2 w-11 h-11 flex items-center justify-center rounded-xl font-display font-black text-xl shadow-sm">{rank}</div>
  if (rank === 3) return <div className="rank-badge-3 w-11 h-11 flex items-center justify-center rounded-xl font-display font-black text-xl shadow-sm">{rank}</div>
  return <div className="w-11 h-11 bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 flex items-center justify-center rounded-xl font-display font-black text-xl">{rank}</div>
}

function StatusBadge({ protection, is_bankrupt }) {
  if (is_bankrupt) return (
    <span className="bg-red-50 text-red-500 dark:bg-red-900/10 dark:text-red-400 px-3 py-1 rounded-md text-[11px] font-bold flex items-center gap-1.5">
      <iconify-icon icon="lucide:ghost"></iconify-icon> مفلس
    </span>
  )
  if (protection === 'full') return (
    <span className="bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400 px-3 py-1 rounded-md text-[11px] font-bold flex items-center gap-1.5">
      <iconify-icon icon="lucide:shield-check"></iconify-icon> محمي
    </span>
  )
  if (protection === 'partial') return (
    <span className="bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400 px-3 py-1 rounded-md text-[11px] font-bold">
      محمي جزئياً
    </span>
  )
  return (
    <span className="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400 px-3 py-1 rounded-md text-[11px] font-bold flex items-center gap-2">
      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span> نشط
    </span>
  )
}

function PlayerRow({ player, myMembershipId }) {
  const isSelf = player.membership_id === myMembershipId
  const canAttack = !isSelf && !player.is_bankrupt && player.protection !== 'full'
  const avatarLetter = player.alias.charAt(0)

  return (
    <div className={`bg-white dark:bg-brand-card-dark border border-gray-100 dark:border-gray-800 rounded-2xl shadow-sm hover:shadow-md dark:shadow-none dark:hover:shadow-lg dark:hover:shadow-black/20 p-5 md:px-8 smooth-transition hover:-translate-y-1 ${player.is_bankrupt ? 'opacity-60' : ''}`}>
      <div className="grid grid-cols-1 md:grid-cols-12 items-center gap-5 md:gap-0">

        {/* Rank + mobile alias */}
        <div className="col-span-1 flex items-center gap-4">
          <RankBadge rank={player.rank} />
          <Link to={`/players/${player.membership_id}`} className="md:hidden font-heading text-lg font-black text-gray-900 dark:text-white hover:text-brand-teal dark:hover:text-brand-slate smooth-transition">{player.alias}</Link>
        </div>

        {/* Avatar + alias (desktop) */}
        <div className="col-span-4 flex items-center gap-4">
          <div className="hidden md:flex relative">
            <div className="w-12 h-12 bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate rounded-xl flex items-center justify-center">
              <span className="font-black text-xl">{avatarLetter}</span>
            </div>
            {player.rank === 1 && (
              <div className="absolute -top-2 -right-2 bg-amber-400 text-amber-900 w-6 h-6 rounded-full flex items-center justify-center shadow-sm border-2 border-white dark:border-brand-card-dark">
                <iconify-icon icon="lucide:crown" class="text-[10px]"></iconify-icon>
              </div>
            )}
          </div>
          <div className="hidden md:block">
            <Link to={`/players/${player.membership_id}`} className={`font-heading font-black text-lg hover:text-brand-teal dark:hover:text-brand-slate smooth-transition block ${player.is_bankrupt ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}`}>
              {player.alias}
            </Link>
            {isSelf && <p className="text-[11px] font-bold text-brand-teal dark:text-brand-slate">أنت</p>}
          </div>
        </div>

        {/* Balance */}
        <div className="col-span-2 text-center">
          <div className="md:hidden text-[10px] font-bold uppercase text-gray-400 mb-1">النقاط</div>
          <span className="font-display text-2xl font-black text-gray-900 dark:text-white">
            {player.balance.toLocaleString('ar-EG')}
          </span>
        </div>

        {/* Status */}
        <div className="col-span-2 flex justify-center">
          <StatusBadge protection={player.protection} is_bankrupt={player.is_bankrupt} />
        </div>

        {/* Rank number placeholder (no attack count from leaderboard) */}
        <div className="col-span-1 text-center hide-mobile font-bold text-lg text-gray-400">—</div>

        {/* Action */}
        <div className="col-span-2 flex justify-end">
          {isSelf ? (
            <Link
              to="/dashboard"
              className="btn-press bg-brand-teal/10 dark:bg-brand-slate/20 text-brand-teal dark:text-brand-slate w-full md:w-auto md:px-8 py-2.5 rounded-xl font-heading font-bold text-sm text-center tracking-wider smooth-transition hover:bg-brand-teal hover:text-white"
            >
              لوحتك
            </Link>
          ) : canAttack ? (
            <Link
              to={`/players/${player.membership_id}`}
              className="btn-press bg-brand-teal hover:bg-brand-teal-hover text-white dark:bg-brand-orange/80 dark:hover:bg-brand-orange w-full md:w-auto md:px-8 py-2.5 rounded-xl smooth-transition font-heading font-bold text-sm text-center tracking-wider shadow-sm hover:shadow"
            >
              هجوم
            </Link>
          ) : (
            <button disabled className="opacity-60 cursor-not-allowed bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 w-full md:w-auto md:px-8 py-2.5 rounded-xl font-heading font-bold text-sm tracking-wider">
              {player.is_bankrupt ? 'انتهى' : 'مغلق'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function LeaderboardPage() {
  const [search, setSearch] = useState('')
  const { competitionId, membershipId: myMembershipId } = useCompetitionContext()
  const { players, loading, error, refetch } = useLeaderboard(competitionId)

  const myPlayer = players.find(p => p.membership_id === myMembershipId)

  const filtered = players.filter(p =>
    p.alias.includes(search)
  )

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto px-4 py-8 md:py-14 space-y-10 relative z-10">

      {/* Page Title & My Stats Bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-3">
          <h1 className="font-display text-4xl md:text-5xl font-black text-gray-900 dark:text-white leading-tight tracking-tight">
            قائمة المتسابقين
          </h1>
          <p className="text-gray-500 dark:text-gray-400 font-medium text-lg">
            تنافس مع أفضل المحاربين وارتقِ في التصنيف
          </p>
        </div>

        {/* Desktop: My rank card */}
        {myPlayer && (
          <div className="hidden md:flex bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm p-6 items-center gap-8 min-w-[420px]">
            <div className="flex flex-col items-center">
              <span className="text-[0.7rem] font-bold text-gray-400 dark:text-gray-500 mb-1 uppercase tracking-widest">مركزك</span>
              <div className="font-display text-5xl font-black text-brand-teal dark:text-brand-slate">{myPlayer.rank}</div>
            </div>
            <div className="h-12 w-px bg-gray-200 dark:bg-gray-700"></div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="font-heading text-xl font-black text-gray-900 dark:text-white">{myPlayer.alias}</span>
                <StatusBadge protection={myPlayer.protection} is_bankrupt={myPlayer.is_bankrupt} />
              </div>
              <div className="flex items-center gap-5 text-sm">
                <div className="flex items-center gap-1.5 font-bold text-gray-600 dark:text-gray-300">
                  <iconify-icon icon="lucide:zap" class="text-brand-teal dark:text-brand-slate text-lg"></iconify-icon>
                  {myPlayer.balance.toLocaleString('ar-EG')}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mobile: my sticky rank */}
      {myPlayer && (
        <div className="md:hidden sticky top-[80px] z-40 bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm p-4 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-xl flex items-center justify-center font-heading font-black text-2xl text-brand-teal dark:text-brand-slate">
                {myPlayer.rank}
              </div>
              <div>
                <div className="text-gray-400 text-[10px] font-bold uppercase tracking-widest">مركزك الحالي</div>
                <div className="text-gray-900 dark:text-white font-heading text-base font-black">{myPlayer.alias}</div>
              </div>
            </div>
            <div className="text-brand-teal dark:text-brand-slate font-black text-lg flex items-center gap-1">
              <iconify-icon icon="lucide:zap"></iconify-icon>
              {myPlayer.balance.toLocaleString('ar-EG')}
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch">
        <div className="flex-1 relative shadow-sm rounded-xl overflow-hidden bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 focus-within:border-brand-teal dark:focus-within:border-brand-slate focus-within:ring-2 focus-within:ring-brand-teal/20 smooth-transition">
          <iconify-icon icon="lucide:search" class="absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 text-xl"></iconify-icon>
          <input
            type="text"
            placeholder="ابحث عن متسابق..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-full bg-transparent py-3.5 pr-14 pl-6 font-medium focus:outline-none text-gray-800 dark:text-gray-200 text-base placeholder-gray-400"
          />
        </div>
        <button onClick={refetch} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 px-5 rounded-xl shadow-sm flex items-center justify-center text-gray-500 hover:text-brand-teal dark:hover:text-brand-slate smooth-transition">
          <iconify-icon icon="lucide:refresh-cw" class="text-xl"></iconify-icon>
        </button>
      </div>

      {/* List */}
      <div className="space-y-4">
        <div className="hidden md:grid grid-cols-12 px-8 py-2 text-[0.75rem] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
          <div className="col-span-1">الترتيب</div>
          <div className="col-span-4">المتسابق</div>
          <div className="col-span-2 text-center">النقاط</div>
          <div className="col-span-2 text-center">الحالة</div>
          <div className="col-span-1 text-center">—</div>
          <div className="col-span-2 text-left">الإجراء</div>
        </div>

        <div className="space-y-4">
          {loading ? (
            Array(5).fill(0).map((_, i) => (
              <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />
            ))
          ) : error ? (
            <div className="text-center py-12 text-brand-danger font-bold">{error}</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 text-gray-400 font-bold">لا يوجد متسابقون</div>
          ) : (
            filtered.map((player) => (
              <PlayerRow key={player.membership_id} player={player} myMembershipId={myMembershipId} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
