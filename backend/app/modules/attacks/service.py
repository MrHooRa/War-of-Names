"""
Attack engine service layer.

All authoritative attack logic lives here:
  - eligibility checks
  - preview calculation (reward decay staging)
  - execute (ledger writes, exposure tracking, bankruptcy check)

Settings are read from the DB via the settings resolver with cascade logic.
Item effects are checked before calculations:
  - Timed active effects (ACTIVATED items with duration)
  - Pending one-time effects (PENDING items waiting for trigger)
Pending effects are consumed after the matching action fires.
BankruptcyRecord is created when bankruptcy is triggered.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import jsonb_safe
from app.core.enums import (
    AttackOutcome,
    BankruptcyState,
    EffectType,
    LedgerDirection,
    LedgerEntryType,
    NotificationPriority,
    NotificationType,
    ProtectionType,
)
from app.modules.attacks.models import AttackAttempt, AttackExposure, BankruptcyRecord
from app.modules.auth.models import Account
from app.modules.competitions.models import Membership
from app.modules.notifications.service import create_notification
from app.modules.scoring.models import LedgerEntry
from app.modules.settings.service import get_settings_batch
from app.modules.store.service import (
    get_active_item_effects,
    get_pending_item_effects,
    consume_pending_effects,
)

# ── Fallback defaults (used only if DB settings are missing) ─────────────
_FALLBACK_BASE_REWARD = 500
_FALLBACK_DECAY_FACTOR = 0.8
_FALLBACK_BASE_PENALTY = 100
_FALLBACK_MAX_ATTACKS_PER_CYCLE = 3
_FALLBACK_BANKRUPTCY_THRESHOLD = 0


# ── Internal helpers ──────────────────────────────────────────────────────

def _calc_reward(base_reward: int, decay_factor: float, stage: int) -> int:
    """Reward decays geometrically with each successful attack stage."""
    return max(1, round(base_reward * (decay_factor ** stage)))


async def _load_attack_settings(
    session: AsyncSession,
    competition_id: uuid.UUID,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> dict:
    """Load all attack-related settings from DB with full cascade (cycle→season→competition→global)."""
    settings = await get_settings_batch(
        session,
        [
            "attack_enabled",
            "attack_base_reward",
            "attack_decay_factor",
            "attack_base_penalty",
            "attack_max_per_cycle",
            "score_bankruptcy_threshold",
        ],
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
    )
    # attack_enabled defaults to False (disabled) if not set
    raw_enabled = settings.get("attack_enabled")
    attack_enabled = bool(raw_enabled) if raw_enabled is not None else False

    return {
        "attack_enabled": attack_enabled,
        "base_reward": int(settings.get("attack_base_reward") or _FALLBACK_BASE_REWARD),
        "decay_factor": float(settings.get("attack_decay_factor") or _FALLBACK_DECAY_FACTOR),
        "base_penalty": int(settings.get("attack_base_penalty") or _FALLBACK_BASE_PENALTY),
        "max_attacks_per_cycle": int(settings.get("attack_max_per_cycle") or _FALLBACK_MAX_ATTACKS_PER_CYCLE),
        "bankruptcy_threshold": int(settings.get("score_bankruptcy_threshold") if settings.get("score_bankruptcy_threshold") is not None else _FALLBACK_BANKRUPTCY_THRESHOLD),
    }


async def _get_or_create_exposure(
    session: AsyncSession,
    membership_id: uuid.UUID,
    season_id: uuid.UUID,
    cycle_id: uuid.UUID,
) -> AttackExposure:
    result = await session.execute(
        select(AttackExposure).where(
            AttackExposure.membership_id == membership_id,
            AttackExposure.cycle_id == cycle_id,
        )
    )
    exposure = result.scalars().first()
    if not exposure:
        exposure = AttackExposure(
            membership_id=membership_id,
            season_id=season_id,
            cycle_id=cycle_id,
        )
        session.add(exposure)
        await session.flush()
    return exposure


async def _write_ledger(
    session: AsyncSession,
    membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    season_id: uuid.UUID,
    cycle_id: uuid.UUID,
    entry_type: LedgerEntryType,
    direction: LedgerDirection,
    amount: int,
    balance_before: int,
    source_id: uuid.UUID,
    reason: str,
) -> int:
    """Write a ledger entry and return the new balance."""
    if direction == LedgerDirection.CREDIT:
        balance_after = balance_before + amount
    else:
        balance_after = balance_before - amount

    entry = LedgerEntry(
        membership_id=membership_id,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        entry_type=entry_type,
        amount=amount,
        direction=direction,
        balance_before=balance_before,
        balance_after=balance_after,
        source_type="attack_attempt",
        source_id=source_id,
        reason=reason,
    )
    session.add(entry)
    return balance_after


async def _create_bankruptcy_record(
    session: AsyncSession,
    membership_id: uuid.UUID,
    cycle_id: uuid.UUID,
    trigger_source_id: uuid.UUID,
    reason: str,
) -> BankruptcyRecord:
    """Create a BankruptcyRecord when a player goes bankrupt."""
    record = BankruptcyRecord(
        membership_id=membership_id,
        cycle_id=cycle_id,
        status=BankruptcyState.ACTIVE,
        trigger_reason=reason,
        trigger_source_id=trigger_source_id,
    )
    session.add(record)
    return record


# ── Modifier resolution ──────────────────────────────────────────────────

async def _get_attack_modifiers(
    session: AsyncSession,
    attacker_membership_id: uuid.UUID,
    target_membership_id: uuid.UUID,
) -> dict:
    """
    Check active AND pending item effects that modify attack calculations.

    Returns a structured dict:
      - reward_multiplier / penalty_multiplier: always-active (timed) modifiers
      - on_success: pending modifiers applied only on successful attack
      - on_failure: pending modifiers applied only on failed attack
      - on_defense: defender's pending modifiers applied to their loss on attack success
      - sources: audit trail of all modifier sources
    """
    modifiers = {
        "reward_multiplier": 1.0,
        "penalty_multiplier": 1.0,
        "on_success": {
            "reward_multiplier": 1.0,
            "reward_bonus": 0,
            "items_to_consume": [],
        },
        "on_failure": {
            "penalty_multiplier": 1.0,
            "penalty_reduction": 0,
            "items_to_consume": [],
        },
        "on_defense": {
            "loss_multiplier": 1.0,
            "loss_reduction": 0,
            "items_to_consume": [],
        },
        "sources": [],
    }

    # ── 1. Always-active timed effects (ACTIVATED items) ──────────────

    # Attacker's reward multipliers
    attacker_ratio = await get_active_item_effects(
        session, attacker_membership_id, EffectType.RATIO_MODIFIER
    )
    for eff in attacker_ratio:
        if eff.get("applies_to") == "attack_reward":
            modifiers["reward_multiplier"] *= eff.get("modifier", 1.0)
            modifiers["sources"].append({"type": "ratio_modifier", "mode": "timed", "from": "attacker"})

    # Attacker's loss reduction
    attacker_loss = await get_active_item_effects(
        session, attacker_membership_id, EffectType.LOSS_REDUCTION
    )
    for eff in attacker_loss:
        reduction = eff.get("reduction", 0)
        modifiers["penalty_multiplier"] *= (1.0 - reduction)
        modifiers["sources"].append({"type": "loss_reduction", "mode": "timed", "from": "attacker"})

    # ── 2. Attacker's pending one-time effects (PENDING items) ────────

    # On success triggers: next_success
    success_pending = await get_pending_item_effects(
        session, attacker_membership_id, trigger_on="next_success"
    )
    for peff in success_pending:
        eff_type = peff.get("type", "")
        params = peff.get("parameters", {})
        oid = peff.get("owned_item_id")

        if eff_type == str(EffectType.RATIO_MODIFIER):
            if params.get("applies_to") == "attack_reward":
                modifiers["on_success"]["reward_multiplier"] *= params.get("modifier", 1.0)
        elif eff_type == str(EffectType.FIXED_BONUS):
            modifiers["on_success"]["reward_bonus"] += params.get("amount", 0)

        if oid:
            modifiers["on_success"]["items_to_consume"].append(oid)
        modifiers["sources"].append({"type": eff_type, "mode": "pending", "trigger": "next_success", "from": "attacker"})

    # On failure triggers: next_failure
    failure_pending = await get_pending_item_effects(
        session, attacker_membership_id, trigger_on="next_failure"
    )
    for peff in failure_pending:
        eff_type = peff.get("type", "")
        params = peff.get("parameters", {})
        oid = peff.get("owned_item_id")

        if eff_type == str(EffectType.LOSS_REDUCTION):
            modifiers["on_failure"]["penalty_multiplier"] *= (1.0 - params.get("reduction", 0))
        elif eff_type == str(EffectType.RATIO_MODIFIER):
            if params.get("applies_to") == "attack_penalty":
                modifiers["on_failure"]["penalty_multiplier"] *= params.get("modifier", 1.0)
        elif eff_type == str(EffectType.FIXED_BONUS):
            modifiers["on_failure"]["penalty_reduction"] += params.get("amount", 0)

        if oid:
            modifiers["on_failure"]["items_to_consume"].append(oid)
        modifiers["sources"].append({"type": eff_type, "mode": "pending", "trigger": "next_failure", "from": "attacker"})

    # ── 3. Defender's pending effects (next_defense) ──────────────────

    defense_pending = await get_pending_item_effects(
        session, target_membership_id, trigger_on="next_defense"
    )
    for peff in defense_pending:
        eff_type = peff.get("type", "")
        params = peff.get("parameters", {})
        oid = peff.get("owned_item_id")

        if eff_type == str(EffectType.LOSS_REDUCTION):
            modifiers["on_defense"]["loss_multiplier"] *= (1.0 - params.get("reduction", 0))
        elif eff_type == str(EffectType.FIXED_BONUS):
            modifiers["on_defense"]["loss_reduction"] += params.get("amount", 0)

        if oid:
            modifiers["on_defense"]["items_to_consume"].append(oid)
        modifiers["sources"].append({"type": eff_type, "mode": "pending", "trigger": "next_defense", "from": "target"})

    return modifiers


# ── Public service functions ──────────────────────────────────────────────

async def get_attack_preview(
    session: AsyncSession,
    attacker_membership_id: uuid.UUID,
    target_membership_id: uuid.UUID,
    competition_id: uuid.UUID,
    season_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> dict:
    """
    Returns preview data: eligibility, estimated reward/penalty, current stage.
    Does NOT write anything to the database.
    """
    cfg = await _load_attack_settings(session, competition_id, season_id, cycle_id)
    base_penalty = cfg["base_penalty"]

    # Global / scoped attack-enabled check
    if not cfg["attack_enabled"]:
        return {
            "can_attack": False,
            "blocking_reason": "الهجمات معطّلة حالياً من قِبل الإدارة",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    # Load attacker
    attacker = await session.get(Membership, attacker_membership_id)
    if not attacker or str(attacker.competition_id) != str(competition_id):
        return {
            "can_attack": False,
            "blocking_reason": "المهاجم غير موجود في هذه المنافسة",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    if attacker.is_bankrupt:
        return {
            "can_attack": False,
            "blocking_reason": "لا يمكن الهجوم وأنت في حالة إفلاس",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    # Load target
    target = await session.get(Membership, target_membership_id)
    if not target or str(target.competition_id) != str(competition_id):
        return {
            "can_attack": False,
            "blocking_reason": "الهدف غير موجود",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    if target.is_bankrupt:
        return {
            "can_attack": False,
            "blocking_reason": "لا يمكن مهاجمة لاعب مفلس",
            "target_alias": target.current_alias,
            "target_protection": target.protection,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    if target.protection == ProtectionType.FULL:
        return {
            "can_attack": False,
            "blocking_reason": "الهدف محمي بالكامل — بلغ الحد الأقصى من الهجمات لهذه الدورة",
            "target_alias": target.current_alias,
            "target_protection": target.protection,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    # PARTIAL protection: attack allowed, but target loses less (noted in modifiers)
    has_partial_protection = target.protection == ProtectionType.PARTIAL

    if str(attacker_membership_id) == str(target_membership_id):
        return {
            "can_attack": False,
            "blocking_reason": "لا يمكنك مهاجمة نفسك",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": base_penalty,
            "target_current_stage": 0,
        }

    # Get exposure to determine current reward stage (scoped to current cycle)
    exposure_filters = [AttackExposure.membership_id == target_membership_id]
    if cycle_id:
        exposure_filters.append(AttackExposure.cycle_id == cycle_id)
    result = await session.execute(
        select(AttackExposure).where(
            *exposure_filters,
        ).order_by(AttackExposure.updated_at.desc()).limit(1)
    )
    exposure = result.scalars().first()
    current_stage = exposure.current_reward_stage if exposure else 0
    base_reward = _calc_reward(cfg["base_reward"], cfg["decay_factor"], current_stage)

    # Check for all modifiers (active + pending)
    modifiers = await _get_attack_modifiers(session, attacker_membership_id, target_membership_id)

    # Estimated reward: timed active * pending on-success
    estimated_reward = base_reward
    if modifiers["reward_multiplier"] != 1.0:
        estimated_reward = max(1, round(estimated_reward * modifiers["reward_multiplier"]))
    on_success_reward = estimated_reward
    if modifiers["on_success"]["reward_multiplier"] != 1.0:
        on_success_reward = max(1, round(on_success_reward * modifiers["on_success"]["reward_multiplier"]))
    on_success_reward += modifiers["on_success"]["reward_bonus"]

    # Estimated penalty: timed active * pending on-failure
    estimated_penalty = max(0, round(base_penalty * modifiers["penalty_multiplier"]))
    on_failure_penalty = estimated_penalty
    if modifiers["on_failure"]["penalty_multiplier"] != 1.0:
        on_failure_penalty = max(0, round(on_failure_penalty * modifiers["on_failure"]["penalty_multiplier"]))
    on_failure_penalty = max(0, on_failure_penalty - modifiers["on_failure"]["penalty_reduction"])

    # Build active modifiers info for the player
    active_modifiers = []

    # Always-active timed modifiers
    if modifiers["reward_multiplier"] != 1.0:
        pct = round((modifiers["reward_multiplier"] - 1) * 100)
        direction = "زيادة" if pct > 0 else "تقليل"
        active_modifiers.append(f"{direction} مكافأة الهجوم بنسبة {abs(pct)}٪")
    if modifiers["penalty_multiplier"] != 1.0:
        pct = round((1 - modifiers["penalty_multiplier"]) * 100)
        active_modifiers.append(f"تقليل خسارة الفشل بنسبة {pct}٪")

    # Pending on-success modifiers
    if modifiers["on_success"]["reward_multiplier"] != 1.0 or modifiers["on_success"]["reward_bonus"] > 0:
        parts = []
        if modifiers["on_success"]["reward_multiplier"] != 1.0:
            pct = round((modifiers["on_success"]["reward_multiplier"] - 1) * 100)
            parts.append(f"+{pct}٪ مكافأة")
        if modifiers["on_success"]["reward_bonus"] > 0:
            parts.append(f"+{modifiers['on_success']['reward_bonus']} نقطة")
        active_modifiers.append(f"عند النجاح: {' و'.join(parts)} (مرة واحدة)")

    # Pending on-failure modifiers
    if modifiers["on_failure"]["penalty_multiplier"] != 1.0 or modifiers["on_failure"]["penalty_reduction"] > 0:
        parts = []
        if modifiers["on_failure"]["penalty_multiplier"] != 1.0:
            pct = round((1 - modifiers["on_failure"]["penalty_multiplier"]) * 100)
            parts.append(f"-{pct}٪ خسارة")
        if modifiers["on_failure"]["penalty_reduction"] > 0:
            parts.append(f"-{modifiers['on_failure']['penalty_reduction']} نقطة")
        active_modifiers.append(f"عند الفشل: {' و'.join(parts)} (مرة واحدة)")

    # Defender's pending modifiers (shown if target has defense items)
    if modifiers["on_defense"]["loss_multiplier"] != 1.0 or modifiers["on_defense"]["loss_reduction"] > 0:
        active_modifiers.append("الهدف لديه درع دفاعي نشط")

    # PARTIAL protection indicator
    if has_partial_protection:
        active_modifiers.append("الهدف محمي جزئياً — خسارته مخفّضة بنسبة 50٪")

    return {
        "can_attack": True,
        "blocking_reason": None,
        "target_alias": target.current_alias,
        "target_protection": target.protection,
        "estimated_reward": on_success_reward,
        "estimated_penalty": on_failure_penalty,
        "target_current_stage": current_stage,
        "active_modifiers": active_modifiers,
    }


async def execute_attack(
    session: AsyncSession,
    attacker_membership_id: uuid.UUID,
    target_membership_id: uuid.UUID,
    guessed_account_id: uuid.UUID,
    competition_id: uuid.UUID,
    season_id: uuid.UUID,
    cycle_id: uuid.UUID,
) -> dict:
    """
    Execute the attack:
    1. Load settings from DB
    2. Re-check eligibility (idempotency guard)
    3. Check active + pending item effect modifiers
    4. Compare guess to target's real account_id
    5. Write ledger entries for reward/penalty (with modifiers applied)
    6. Consume pending items that matched the outcome
    7. Update AttackExposure, check max_attacks
    8. Check bankruptcy for both parties (create BankruptcyRecord)
    9. Persist AttackAttempt record
    """
    cfg = await _load_attack_settings(session, competition_id, season_id, cycle_id)

    # Global / scoped attack-enabled check
    if not cfg["attack_enabled"]:
        return {
            "outcome": AttackOutcome.BLOCKED,
            "reward_amount": 0,
            "penalty_amount": 0,
            "attacker_balance_after": 0,
            "target_balance_after": None,
            "target_real_name": None,
            "message": "الهجمات معطّلة حالياً من قِبل الإدارة",
            "attempt_id": uuid.uuid4(),
        }

    # Load both memberships
    attacker = await session.get(Membership, attacker_membership_id)
    target = await session.get(Membership, target_membership_id)

    # Eligibility guard
    if not attacker or not target:
        return {
            "outcome": AttackOutcome.REJECTED,
            "reward_amount": 0,
            "penalty_amount": 0,
            "attacker_balance_after": 0,
            "target_balance_after": None,
            "target_real_name": None,
            "message": "بيانات الهجوم غير صالحة",
            "attempt_id": uuid.uuid4(),
        }

    if attacker.is_bankrupt:
        return {
            "outcome": AttackOutcome.BLOCKED,
            "reward_amount": 0,
            "penalty_amount": 0,
            "attacker_balance_after": attacker.current_balance,
            "target_balance_after": None,
            "target_real_name": None,
            "message": "الهجوم مرفوض — المهاجم في حالة إفلاس",
            "attempt_id": uuid.uuid4(),
        }

    if target.protection == ProtectionType.FULL or target.is_bankrupt:
        return {
            "outcome": AttackOutcome.BLOCKED,
            "reward_amount": 0,
            "penalty_amount": 0,
            "attacker_balance_after": attacker.current_balance,
            "target_balance_after": None,
            "target_real_name": None,
            "message": "الهجوم مرفوض — الهدف محمي",
            "attempt_id": uuid.uuid4(),
        }

    # PARTIAL protection: attack proceeds but target deduction halved
    has_partial_protection = target.protection == ProtectionType.PARTIAL

    # Load active + pending item effect modifiers
    modifiers = await _get_attack_modifiers(session, attacker_membership_id, target_membership_id)

    # Determine outcome
    correct = str(guessed_account_id) == str(target.account_id)
    outcome = AttackOutcome.SUCCEEDED if correct else AttackOutcome.FAILED

    attacker_balance_after = attacker.current_balance
    target_balance_after: int | None = None
    reward_amount = 0
    penalty_amount = 0
    target_real_name: str | None = None

    # Create the AttackAttempt record first (for source_id in ledger)
    attempt = AttackAttempt(
        attacker_id=attacker_membership_id,
        target_id=target_membership_id,
        competition_id=competition_id,
        season_id=season_id,
        cycle_id=cycle_id,
        guessed_account_id=guessed_account_id,
        outcome=outcome,
        reward_amount=0,
        penalty_amount=0,
        modifiers_applied=jsonb_safe(modifiers) if modifiers["sources"] else {},
    )
    session.add(attempt)
    await session.flush()  # get attempt.id

    if outcome == AttackOutcome.SUCCEEDED:
        # Get/create target's exposure to find current stage
        exposure = await _get_or_create_exposure(
            session, target_membership_id, season_id, cycle_id
        )
        stage = exposure.current_reward_stage
        reward = _calc_reward(cfg["base_reward"], cfg["decay_factor"], stage)

        # Apply always-active reward modifier (timed)
        if modifiers["reward_multiplier"] != 1.0:
            reward = max(1, round(reward * modifiers["reward_multiplier"]))

        # Apply pending on-success reward modifiers (one-time)
        if modifiers["on_success"]["reward_multiplier"] != 1.0:
            reward = max(1, round(reward * modifiers["on_success"]["reward_multiplier"]))
        reward += modifiers["on_success"]["reward_bonus"]

        reward_amount = max(1, reward)

        # Credit attacker
        attacker_balance_after = await _write_ledger(
            session,
            membership_id=attacker_membership_id,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
            entry_type=LedgerEntryType.ATTACK_REWARD,
            direction=LedgerDirection.CREDIT,
            amount=reward_amount,
            balance_before=attacker.current_balance,
            source_id=attempt.id,
            reason=f"هجوم ناجح على {target.current_alias or 'لاعب'}",
        )
        attacker.current_balance = attacker_balance_after

        # Calculate target deduction (may be reduced by defender's pending effects)
        target_deduction = reward_amount
        # PARTIAL protection: halve the target's loss
        if has_partial_protection:
            target_deduction = max(0, round(target_deduction * 0.5))
        if modifiers["on_defense"]["loss_multiplier"] != 1.0:
            target_deduction = max(0, round(target_deduction * modifiers["on_defense"]["loss_multiplier"]))
        target_deduction = max(0, target_deduction - modifiers["on_defense"]["loss_reduction"])

        # Debit target
        target_balance_after = await _write_ledger(
            session,
            membership_id=target_membership_id,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
            entry_type=LedgerEntryType.ATTACK_PENALTY,
            direction=LedgerDirection.DEBIT,
            amount=target_deduction,
            balance_before=target.current_balance,
            source_id=attempt.id,
            reason=f"تعرض للكشف من قِبل مهاجم",
        )
        target.current_balance = target_balance_after

        # Advance exposure stage
        exposure.successful_attack_count += 1
        exposure.current_reward_stage += 1
        if exposure.successful_attack_count >= cfg["max_attacks_per_cycle"]:
            exposure.max_attacks_reached = True
            target.protection = ProtectionType.FULL

        # Reveal real name
        target_account = await session.get(Account, target.account_id)
        target_real_name = target_account.real_name if target_account else None

        # Update attempt
        attempt.reward_amount = reward_amount

        # Consume attacker's on-success pending items
        if modifiers["on_success"]["items_to_consume"]:
            await consume_pending_effects(session, modifiers["on_success"]["items_to_consume"])

        # Consume defender's on-defense pending items
        if modifiers["on_defense"]["items_to_consume"]:
            await consume_pending_effects(session, modifiers["on_defense"]["items_to_consume"])

        # Check target bankruptcy
        if target.current_balance <= cfg["bankruptcy_threshold"] and not target.is_bankrupt:
            target.is_bankrupt = True
            await _create_bankruptcy_record(
                session,
                membership_id=target_membership_id,
                cycle_id=cycle_id,
                trigger_source_id=attempt.id,
                reason=f"إفلاس بسبب هجوم ناجح — الرصيد: {target.current_balance}",
            )
            await create_notification(
                session,
                recipient_id=target.account_id,
                notification_type=NotificationType.BANKRUPTCY_TRIGGERED,
                title="إفلاس!",
                message=f"رصيدك وصل إلى {target.current_balance} — أنت الآن في حالة إفلاس",
                membership_id=target_membership_id,
                priority=NotificationPriority.URGENT,
                reference_type="attack_attempt",
                reference_id=attempt.id,
                deep_link="/dashboard",
            )

        # Notify target of FULL protection activation
        if exposure.max_attacks_reached and target.protection == ProtectionType.FULL:
            await create_notification(
                session,
                recipient_id=target.account_id,
                notification_type=NotificationType.PROTECTION_ACTIVATED,
                title="حماية كاملة!",
                message="بلغت الحد الأقصى من الهجمات — أنت الآن محمي بالكامل لبقية الدورة",
                membership_id=target_membership_id,
                priority=NotificationPriority.HIGH,
                reference_type="cycle",
                reference_id=cycle_id,
                deep_link="/dashboard",
            )

    else:  # FAILED
        penalty = cfg["base_penalty"]

        # Apply always-active loss reduction (timed)
        if modifiers["penalty_multiplier"] != 1.0:
            penalty = max(0, round(penalty * modifiers["penalty_multiplier"]))

        # Apply pending on-failure modifiers (one-time)
        if modifiers["on_failure"]["penalty_multiplier"] != 1.0:
            penalty = max(0, round(penalty * modifiers["on_failure"]["penalty_multiplier"]))
        penalty = max(0, penalty - modifiers["on_failure"]["penalty_reduction"])

        penalty_amount = penalty

        # Debit attacker
        attacker_balance_after = await _write_ledger(
            session,
            membership_id=attacker_membership_id,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
            entry_type=LedgerEntryType.ATTACK_PENALTY,
            direction=LedgerDirection.DEBIT,
            amount=penalty,
            balance_before=attacker.current_balance,
            source_id=attempt.id,
            reason=f"هجوم فاشل على {target.current_alias or 'لاعب'}",
        )
        attacker.current_balance = attacker_balance_after
        attempt.penalty_amount = penalty_amount

        # Consume attacker's on-failure pending items
        if modifiers["on_failure"]["items_to_consume"]:
            await consume_pending_effects(session, modifiers["on_failure"]["items_to_consume"])

        # Check attacker bankruptcy
        if attacker.current_balance <= cfg["bankruptcy_threshold"] and not attacker.is_bankrupt:
            attacker.is_bankrupt = True
            await _create_bankruptcy_record(
                session,
                membership_id=attacker_membership_id,
                cycle_id=cycle_id,
                trigger_source_id=attempt.id,
                reason=f"إفلاس بسبب خسارة هجوم — الرصيد: {attacker.current_balance}",
            )
            await create_notification(
                session,
                recipient_id=attacker.account_id,
                notification_type=NotificationType.BANKRUPTCY_TRIGGERED,
                title="إفلاس!",
                message=f"رصيدك وصل إلى {attacker.current_balance} — أنت الآن في حالة إفلاس",
                membership_id=attacker_membership_id,
                priority=NotificationPriority.URGENT,
                reference_type="attack_attempt",
                reference_id=attempt.id,
                deep_link="/dashboard",
            )

    # ── Notifications ──────────────────────────────────────────────────────
    if outcome == AttackOutcome.SUCCEEDED:
        # Notify attacker of success
        await create_notification(
            session,
            recipient_id=attacker.account_id,
            notification_type=NotificationType.ATTACK_SUCCESS,
            title="هجوم ناجح!",
            message=f"كشفت هوية {target.current_alias or 'لاعب'} وحصلت على {reward_amount} نقطة",
            membership_id=attacker_membership_id,
            priority=NotificationPriority.HIGH,
            reference_type="attack_attempt",
            reference_id=attempt.id,
            deep_link="/dashboard",
        )
        # Notify target of being attacked
        await create_notification(
            session,
            recipient_id=target.account_id,
            notification_type=NotificationType.ATTACK_RECEIVED,
            title="تعرضت لهجوم!",
            message=f"تم كشف هويتك وخسرت {reward_amount} نقطة",
            membership_id=target_membership_id,
            priority=NotificationPriority.HIGH,
            reference_type="attack_attempt",
            reference_id=attempt.id,
            deep_link="/dashboard",
        )
    else:
        # Notify attacker of failure
        await create_notification(
            session,
            recipient_id=attacker.account_id,
            notification_type=NotificationType.ATTACK_FAILURE,
            title="هجوم فاشل",
            message=f"فشل هجومك على {target.current_alias or 'لاعب'} وخسرت {penalty_amount} نقطة",
            membership_id=attacker_membership_id,
            priority=NotificationPriority.NORMAL,
            reference_type="attack_attempt",
            reference_id=attempt.id,
            deep_link="/dashboard",
        )

    await session.commit()
    await session.refresh(attempt)

    message_map = {
        AttackOutcome.SUCCEEDED: f"هجوم ناجح! كشفت هوية الهدف وحصلت على {reward_amount} نقطة",
        AttackOutcome.FAILED: f"هجوم فاشل! خسرت {penalty_amount} نقطة",
    }

    return {
        "outcome": outcome,
        "reward_amount": reward_amount,
        "penalty_amount": penalty_amount,
        "attacker_balance_after": attacker_balance_after,
        "target_balance_after": target_balance_after,
        "target_real_name": target_real_name if outcome == AttackOutcome.SUCCEEDED else None,
        "message": message_map.get(outcome, "تمت المعالجة"),
        "attempt_id": attempt.id,
    }
