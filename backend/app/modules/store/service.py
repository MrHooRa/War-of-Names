"""
Item effect executor — applies item effects to gameplay state.

This is the bridge between the store system and the gameplay engines.
Each EffectType maps to a handler that mutates game state (balance, protection,
alias, etc.) and returns a summary of what happened.

Effect trigger modes:
  - "activation"    — instant on item use (instant effects + timed active)
  - "next_success"  — pending until the player's next successful attack
  - "next_failure"  — pending until the player's next failed attack
  - "next_defense"  — pending until the player is attacked successfully
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import jsonb_safe
from app.core.enums import (
    AuditActorType,
    EffectType,
    LedgerDirection,
    LedgerEntryType,
    NotificationType,
    OwnedItemStatus,
    ProtectionType,
)
from app.modules.attacks.models import ProtectionRecord
from app.modules.competitions.models import AliasRecord, Membership
from app.modules.notifications.service import create_notification
from app.modules.scoring.models import LedgerEntry
from app.modules.store.models import ItemActivation, ItemEffect, OwnedItem

# ── Valid trigger modes ──────────────────────────────────────────────────
PENDING_TRIGGERS = {"next_success", "next_failure", "next_defense"}


# ── Effect handlers (instant — executed on item use) ─────────────────────

async def _handle_fixed_bonus(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """Grant a fixed point bonus to the user."""
    amount = effect.parameters.get("amount", 0)
    if amount <= 0:
        return {"type": "fixed_bonus", "skipped": True, "reason": "amount <= 0"}

    target = target_membership if effect.target_scope == "target" and target_membership else membership
    balance_before = target.current_balance
    balance_after = balance_before + amount

    ledger = LedgerEntry(
        membership_id=target.id,
        competition_id=target.competition_id,
        entry_type=LedgerEntryType.SYSTEM_REWARD,
        amount=amount,
        direction=LedgerDirection.CREDIT,
        balance_before=balance_before,
        balance_after=balance_after,
        source_type="item_activation",
        source_id=owned_item.id,
        reason=f"تأثير عنصر: مكافأة ثابتة",
    )
    session.add(ledger)
    target.current_balance = balance_after

    return {"type": "fixed_bonus", "amount": amount, "balance_after": balance_after}


async def _handle_state_change(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """Change a gameplay state (protection, bankruptcy clear, etc.)."""
    state_key = effect.parameters.get("state", "")
    state_value = effect.parameters.get("value", "")

    target = target_membership if effect.target_scope == "target" and target_membership else membership

    if state_key == "protection":
        old_protection = target.protection
        new_protection = ProtectionType(state_value) if state_value in ProtectionType.__members__.values() else ProtectionType.FULL

        target.protection = new_protection

        # Create ProtectionRecord for traceability
        duration = effect.duration_minutes
        now = datetime.utcnow()
        record = ProtectionRecord(
            membership_id=target.id,
            protection_type=new_protection,
            source_type="item_effect",
            source_id=owned_item.id,
            reason=f"تفعيل عنصر حماية",
            starts_at=now,
            ends_at=now + timedelta(minutes=duration) if duration else None,
        )
        session.add(record)

        return jsonb_safe({
            "type": "state_change",
            "state": "protection",
            "old_value": old_protection,
            "new_value": new_protection,
            "duration_minutes": duration,
        })

    if state_key == "bankruptcy" and state_value == "clear":
        if target.is_bankrupt:
            target.is_bankrupt = False
            return {"type": "state_change", "state": "bankruptcy", "old_value": True, "new_value": False}
        return {"type": "state_change", "state": "bankruptcy", "skipped": True, "reason": "not bankrupt"}

    return {"type": "state_change", "skipped": True, "reason": f"unknown state: {state_key}"}


async def _handle_negative_effect(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """Apply a negative effect to the target (point deduction, protection removal)."""
    sub_type = effect.parameters.get("sub_type", "")
    target = target_membership if target_membership else membership

    if sub_type == "deduct_points":
        amount = effect.parameters.get("amount", 0)
        if amount <= 0:
            return {"type": "negative_effect", "skipped": True}

        balance_before = target.current_balance
        balance_after = balance_before - amount

        ledger = LedgerEntry(
            membership_id=target.id,
            competition_id=target.competition_id,
            entry_type=LedgerEntryType.ATTACK_PENALTY,
            amount=amount,
            direction=LedgerDirection.DEBIT,
            balance_before=balance_before,
            balance_after=balance_after,
            source_type="item_activation",
            source_id=owned_item.id,
            reason=f"تأثير عنصر سلبي",
        )
        session.add(ledger)
        target.current_balance = balance_after
        return {"type": "negative_effect", "sub_type": "deduct_points", "amount": amount}

    if sub_type == "remove_protection":
        old = target.protection
        target.protection = ProtectionType.NONE
        return {"type": "negative_effect", "sub_type": "remove_protection", "old_value": old}

    if sub_type == "deduct_percentage":
        pct = effect.parameters.get("percentage", 0)
        amount = max(1, round(target.current_balance * pct / 100))
        balance_before = target.current_balance
        balance_after = balance_before - amount

        ledger = LedgerEntry(
            membership_id=target.id,
            competition_id=target.competition_id,
            entry_type=LedgerEntryType.ATTACK_PENALTY,
            amount=amount,
            direction=LedgerDirection.DEBIT,
            balance_before=balance_before,
            balance_after=balance_after,
            source_type="item_activation",
            source_id=owned_item.id,
            reason=f"تأثير عنصر: خصم {pct}%",
        )
        session.add(ledger)
        target.current_balance = balance_after
        return {"type": "negative_effect", "sub_type": "deduct_percentage", "percentage": pct, "amount": amount}

    return {"type": "negative_effect", "skipped": True, "reason": f"unknown sub_type: {sub_type}"}


async def _handle_allow_alias_change(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """
    Grant alias change permission.

    The permission is tracked via the ItemActivation record's effect_summary.
    The /api/me/alias endpoint checks for an unredeemed activation and
    marks it as redeemed after use.
    """
    return {"type": "allow_alias_change", "granted": True, "redeemed": False}


async def _handle_ratio_modifier(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """
    Register a ratio modifier (e.g. 1.5x attack reward).
    Stored as an active effect — the attack engine checks for these.
    """
    modifier = effect.parameters.get("modifier", 1.0)
    applies_to = effect.parameters.get("applies_to", "attack_reward")
    return {
        "type": "ratio_modifier",
        "modifier": modifier,
        "applies_to": applies_to,
        "duration_minutes": effect.duration_minutes,
    }


async def _handle_loss_reduction(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """Register a loss reduction effect (e.g. 50% less penalty on failed attack)."""
    reduction = effect.parameters.get("reduction", 0.5)
    return {
        "type": "loss_reduction",
        "reduction": reduction,
        "duration_minutes": effect.duration_minutes,
    }


async def _handle_action_prevention(
    session: AsyncSession,
    effect: ItemEffect,
    membership: Membership,
    owned_item: OwnedItem,
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> dict:
    """Prevent an action (attacks against this player) for a duration."""
    action = effect.parameters.get("action", "attack")
    target = target_membership if effect.target_scope == "target" and target_membership else membership

    if action == "attack":
        # Grant full protection
        target.protection = ProtectionType.FULL
        now = datetime.utcnow()
        record = ProtectionRecord(
            membership_id=target.id,
            protection_type=ProtectionType.FULL,
            source_type="item_effect",
            source_id=owned_item.id,
            reason=f"تأثير عنصر: منع الهجمات",
            starts_at=now,
            ends_at=now + timedelta(minutes=effect.duration_minutes) if effect.duration_minutes else None,
        )
        session.add(record)

    return {
        "type": "action_prevention",
        "action": action,
        "duration_minutes": effect.duration_minutes,
    }


# ── Handler dispatch table ───────────────────────────────────────────────

_EFFECT_HANDLERS = {
    EffectType.FIXED_BONUS: _handle_fixed_bonus,
    EffectType.STATE_CHANGE: _handle_state_change,
    EffectType.NEGATIVE_EFFECT: _handle_negative_effect,
    EffectType.ALLOW_ALIAS_CHANGE: _handle_allow_alias_change,
    EffectType.RATIO_MODIFIER: _handle_ratio_modifier,
    EffectType.LOSS_REDUCTION: _handle_loss_reduction,
    EffectType.ACTION_PREVENTION: _handle_action_prevention,
}


# ── Public API ───────────────────────────────────────────────────────────

async def execute_item_effects(
    session: AsyncSession,
    owned_item: OwnedItem,
    membership: Membership,
    effects: list[ItemEffect],
    *,
    target_membership: Membership | None = None,
    context: dict | None = None,
) -> list[dict]:
    """
    Execute all INSTANT effects for an item activation.

    Only effects with trigger_on="activation" are executed here.
    Pending effects (next_success, next_failure, next_defense) are stored
    as metadata by the use_item endpoint and applied later by the attack engine.

    Returns a list of result dicts, one per effect, describing what happened.
    Unhandled effect types are recorded but skipped gracefully.
    """
    results = []
    for effect in sorted(effects, key=lambda e: e.order_index):
        handler = _EFFECT_HANDLERS.get(effect.effect_type)
        if handler:
            result = await handler(
                session, effect, membership, owned_item,
                target_membership=target_membership,
                context=context,
            )
        else:
            result = {
                "type": str(effect.effect_type),
                "skipped": True,
                "reason": "no handler implemented",
            }
        results.append(result)
    return results


def build_pending_effect_entry(effect: ItemEffect) -> dict:
    """
    Build metadata dict for a pending (action-triggered) effect.
    This is stored in ItemActivation.effect_summary["pending_effects"]
    and read by the attack engine when the trigger fires.
    """
    return {
        "type": str(effect.effect_type.value),
        "trigger_on": effect.trigger_on,
        "parameters": effect.parameters or {},
        "target_scope": effect.target_scope or "self",
        "duration_minutes": effect.duration_minutes,
    }


async def get_active_item_effects(
    session: AsyncSession,
    membership_id: uuid.UUID,
    effect_type: EffectType | None = None,
) -> list[dict]:
    """
    Query active (non-expired) timed item effects for a membership.
    Checks ItemActivation records where the owned item is ACTIVATED and not expired.
    Returns the effect_summary dicts.
    """
    now = datetime.utcnow()
    query = (
        select(ItemActivation, OwnedItem)
        .join(OwnedItem, ItemActivation.owned_item_id == OwnedItem.id)
        .where(
            ItemActivation.membership_id == membership_id,
            ItemActivation.result_state == "success",
            OwnedItem.status == OwnedItemStatus.ACTIVATED,
        )
    )
    result = await session.execute(query)
    rows = result.all()

    active_effects = []
    for activation, owned in rows:
        # Skip if expired
        if owned.expires_at and owned.expires_at <= now:
            continue

        summary = activation.effect_summary or {}
        effects_applied = summary.get("effects_applied", [])
        for eff in effects_applied:
            if effect_type and eff.get("type") != str(effect_type):
                continue
            active_effects.append(eff)

    return active_effects


async def get_pending_item_effects(
    session: AsyncSession,
    membership_id: uuid.UUID,
    trigger_on: str | None = None,
) -> list[dict]:
    """
    Query pending (not yet triggered) item effects for a membership.

    Returns list of dicts enriched with owned_item_id + activation_id
    so the attack engine can consume them after the trigger fires.
    """
    now = datetime.utcnow()
    query = (
        select(ItemActivation, OwnedItem)
        .join(OwnedItem, ItemActivation.owned_item_id == OwnedItem.id)
        .where(
            ItemActivation.membership_id == membership_id,
            ItemActivation.result_state == "success",
            OwnedItem.status == OwnedItemStatus.PENDING,
        )
    )
    result = await session.execute(query)
    rows = result.all()

    pending = []
    for activation, owned in rows:
        # Skip if expired (pending items can have optional expiry)
        if owned.expires_at and owned.expires_at <= now:
            continue

        summary = activation.effect_summary or {}
        for peff in summary.get("pending_effects", []):
            if trigger_on and peff.get("trigger_on") != trigger_on:
                continue
            pending.append(jsonb_safe({
                "owned_item_id": owned.id,
                "activation_id": activation.id,
                **peff,
            }))

    return pending


async def consume_pending_effects(
    session: AsyncSession,
    owned_item_ids: list[uuid.UUID],
) -> None:
    """Mark pending items as consumed after their trigger fires."""
    now = datetime.utcnow()
    consumed = set()
    for oid in owned_item_ids:
        if oid in consumed:
            continue
        owned = await session.get(OwnedItem, oid)
        if owned and owned.status == OwnedItemStatus.PENDING:
            owned.status = OwnedItemStatus.CONSUMED
            owned.consumed_at = now
            consumed.add(oid)
