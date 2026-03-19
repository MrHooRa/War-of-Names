"""
Attack engine service layer.

All authoritative attack logic lives here:
  - eligibility checks
  - preview calculation (reward decay staging)
  - execute (ledger writes, exposure tracking, bankruptcy check)

Settings are hardcoded defaults for MVP; replace with DB settings lookup later.
"""

import uuid
import math
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    AttackOutcome,
    LedgerDirection,
    LedgerEntryType,
    NotificationPriority,
    NotificationType,
    ProtectionType,
)
from app.modules.attacks.models import AttackAttempt, AttackExposure
from app.modules.auth.models import Account
from app.modules.competitions.models import Membership
from app.modules.notifications.service import create_notification
from app.modules.scoring.models import LedgerEntry

# ── MVP hardcoded settings ────────────────────────────────────────────────
BASE_REWARD = 500          # points attacker gains on first successful attack on a target
DECAY_FACTOR = 0.8         # reward multiplier per subsequent successful attack on same target
BASE_PENALTY = 100         # points attacker loses on a failed attack
MAX_ATTACKS_PER_CYCLE = 3  # max times a target can be successfully attacked in a cycle
BANKRUPTCY_THRESHOLD = 0   # balance at or below this triggers bankruptcy


# ── Internal helpers ──────────────────────────────────────────────────────

def _calc_reward(stage: int) -> int:
    """Reward decays geometrically with each successful attack stage."""
    return max(1, round(BASE_REWARD * (DECAY_FACTOR ** stage)))


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


# ── Public service functions ──────────────────────────────────────────────

async def get_attack_preview(
    session: AsyncSession,
    attacker_membership_id: uuid.UUID,
    target_membership_id: uuid.UUID,
    competition_id: uuid.UUID,
) -> dict:
    """
    Returns preview data: eligibility, estimated reward/penalty, current stage.
    Does NOT write anything to the database.
    """
    # Load attacker
    attacker = await session.get(Membership, attacker_membership_id)
    if not attacker or str(attacker.competition_id) != str(competition_id):
        return {
            "can_attack": False,
            "blocking_reason": "المهاجم غير موجود في هذه المنافسة",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": BASE_PENALTY,
            "target_current_stage": 0,
        }

    if attacker.is_bankrupt:
        return {
            "can_attack": False,
            "blocking_reason": "لا يمكن الهجوم وأنت في حالة إفلاس",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": BASE_PENALTY,
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
            "estimated_penalty": BASE_PENALTY,
            "target_current_stage": 0,
        }

    if target.is_bankrupt:
        return {
            "can_attack": False,
            "blocking_reason": "لا يمكن مهاجمة لاعب مفلس",
            "target_alias": target.current_alias,
            "target_protection": target.protection,
            "estimated_reward": 0,
            "estimated_penalty": BASE_PENALTY,
            "target_current_stage": 0,
        }

    if target.protection == ProtectionType.FULL:
        return {
            "can_attack": False,
            "blocking_reason": "الهدف محمي بالكامل — بلغ الحد الأقصى من الهجمات لهذه الدورة",
            "target_alias": target.current_alias,
            "target_protection": target.protection,
            "estimated_reward": 0,
            "estimated_penalty": BASE_PENALTY,
            "target_current_stage": 0,
        }

    if str(attacker_membership_id) == str(target_membership_id):
        return {
            "can_attack": False,
            "blocking_reason": "لا يمكنك مهاجمة نفسك",
            "target_alias": None,
            "target_protection": ProtectionType.NONE,
            "estimated_reward": 0,
            "estimated_penalty": BASE_PENALTY,
            "target_current_stage": 0,
        }

    # Get exposure to determine current reward stage
    # Use dummy season/cycle for preview (exposure may not exist yet)
    result = await session.execute(
        select(AttackExposure).where(
            AttackExposure.membership_id == target_membership_id,
        ).order_by(AttackExposure.updated_at.desc()).limit(1)
    )
    exposure = result.scalars().first()
    current_stage = exposure.current_reward_stage if exposure else 0
    estimated_reward = _calc_reward(current_stage)

    return {
        "can_attack": True,
        "blocking_reason": None,
        "target_alias": target.current_alias,
        "target_protection": target.protection,
        "estimated_reward": estimated_reward,
        "estimated_penalty": BASE_PENALTY,
        "target_current_stage": current_stage,
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
    1. Re-check eligibility (idempotency guard)
    2. Compare guess to target's real account_id
    3. Write ledger entries for reward/penalty
    4. Update AttackExposure, check max_attacks
    5. Check bankruptcy for both parties
    6. Persist AttackAttempt record
    """
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
        modifiers_applied={},
    )
    session.add(attempt)
    await session.flush()  # get attempt.id

    if outcome == AttackOutcome.SUCCEEDED:
        # Get/create target's exposure to find current stage
        exposure = await _get_or_create_exposure(
            session, target_membership_id, season_id, cycle_id
        )
        stage = exposure.current_reward_stage
        reward = _calc_reward(stage)
        reward_amount = reward

        # Credit attacker
        attacker_balance_after = await _write_ledger(
            session,
            membership_id=attacker_membership_id,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
            entry_type=LedgerEntryType.ATTACK_REWARD,
            direction=LedgerDirection.CREDIT,
            amount=reward,
            balance_before=attacker.current_balance,
            source_id=attempt.id,
            reason=f"هجوم ناجح على {target.current_alias or 'لاعب'}",
        )
        attacker.current_balance = attacker_balance_after

        # Debit target
        target_balance_after = await _write_ledger(
            session,
            membership_id=target_membership_id,
            competition_id=competition_id,
            season_id=season_id,
            cycle_id=cycle_id,
            entry_type=LedgerEntryType.ATTACK_PENALTY,
            direction=LedgerDirection.DEBIT,
            amount=reward,
            balance_before=target.current_balance,
            source_id=attempt.id,
            reason=f"تعرض للكشف من قِبل مهاجم",
        )
        target.current_balance = target_balance_after

        # Advance exposure stage
        exposure.successful_attack_count += 1
        exposure.current_reward_stage += 1
        if exposure.successful_attack_count >= MAX_ATTACKS_PER_CYCLE:
            exposure.max_attacks_reached = True
            target.protection = ProtectionType.FULL

        # Reveal real name
        target_account = await session.get(Account, target.account_id)
        target_real_name = target_account.real_name if target_account else None

        # Update attempt
        attempt.reward_amount = reward_amount

        # Check target bankruptcy
        if target.current_balance <= BANKRUPTCY_THRESHOLD and not target.is_bankrupt:
            target.is_bankrupt = True

    else:  # FAILED
        penalty = BASE_PENALTY
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

        # Check attacker bankruptcy
        if attacker.current_balance <= BANKRUPTCY_THRESHOLD and not attacker.is_bankrupt:
            attacker.is_bankrupt = True

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
        AttackOutcome.SUCCEEDED: f"هجوم ناجح! كشفت هوية {target_real_name} وحصلت على {reward_amount} نقطة",
        AttackOutcome.FAILED: f"هجوم فاشل! خسرت {penalty_amount} نقطة",
    }

    return {
        "outcome": outcome,
        "reward_amount": reward_amount,
        "penalty_amount": penalty_amount,
        "attacker_balance_after": attacker_balance_after,
        "target_balance_after": target_balance_after,
        "target_real_name": target_real_name,
        "message": message_map.get(outcome, "تمت المعالجة"),
        "attempt_id": attempt.id,
    }
