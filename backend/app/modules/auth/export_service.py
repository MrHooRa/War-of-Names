"""Account data export helpers for PDPL access/portability requests."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attacks.models import AttackAttempt
from app.modules.auth.models import Account
from app.modules.competitions.models import AliasRecord, Membership
from app.modules.notifications.models import Notification
from app.modules.quiz.models import AnswerSubmission
from app.modules.scoring.models import LedgerEntry
from app.modules.store.models import ItemDefinition, OwnedItem


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


async def build_account_export(
    session: AsyncSession,
    account_id: uuid.UUID,
) -> dict | None:
    """Build a machine-readable export payload for one account."""
    account = await session.get(Account, account_id)
    if not account:
        return None

    memberships_result = await session.execute(
        select(Membership)
        .where(Membership.account_id == account_id)
        .order_by(Membership.joined_at.asc())
    )
    membership_rows = memberships_result.scalars().all()
    membership_ids = [m.id for m in membership_rows]

    alias_history_by_membership: dict[uuid.UUID, list[dict]] = {}
    if membership_ids:
        alias_result = await session.execute(
            select(AliasRecord)
            .where(AliasRecord.membership_id.in_(membership_ids))
            .order_by(AliasRecord.created_at.asc())
        )
        for alias in alias_result.scalars().all():
            alias_history_by_membership.setdefault(alias.membership_id, []).append({
                "id": str(alias.id),
                "alias": alias.alias_value,
                "is_active": alias.is_active,
                "reason": alias.reason,
                "season_id": str(alias.season_id) if alias.season_id else None,
                "cycle_id": str(alias.cycle_id) if alias.cycle_id else None,
                "starts_at": alias.starts_at.isoformat() if alias.starts_at else None,
                "ends_at": alias.ends_at.isoformat() if alias.ends_at else None,
                "created_at": alias.created_at.isoformat() if alias.created_at else None,
            })

    memberships = [
        {
            "id": str(m.id),
            "competition_id": str(m.competition_id),
            "current_alias": m.current_alias,
            "status": _enum_value(m.status),
            "current_balance": m.current_balance,
            "is_bankrupt": m.is_bankrupt,
            "protection": _enum_value(m.protection),
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            "alias_history": alias_history_by_membership.get(m.id, []),
        }
        for m in membership_rows
    ]

    attacks = []
    if membership_ids:
        attacks_result = await session.execute(
            select(AttackAttempt)
            .where(
                or_(
                    AttackAttempt.attacker_id.in_(membership_ids),
                    AttackAttempt.target_id.in_(membership_ids),
                )
            )
            .order_by(AttackAttempt.created_at.asc())
        )
        attacks = [
            {
                "id": str(a.id),
                "competition_id": str(a.competition_id),
                "season_id": str(a.season_id),
                "cycle_id": str(a.cycle_id),
                "attacker_membership_id": str(a.attacker_id),
                "target_membership_id": str(a.target_id),
                "participation_role": "attacker" if a.attacker_id in membership_ids else "target",
                "guessed_account_id": str(a.guessed_account_id) if a.guessed_account_id else None,
                "outcome": _enum_value(a.outcome),
                "reward_amount": a.reward_amount,
                "penalty_amount": a.penalty_amount,
                "modifiers_applied": a.modifiers_applied,
                "blocking_reason": a.blocking_reason,
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in attacks_result.scalars().all()
        ]

    quiz_answers = []
    if membership_ids:
        answers_result = await session.execute(
            select(AnswerSubmission)
            .where(AnswerSubmission.membership_id.in_(membership_ids))
            .order_by(AnswerSubmission.submitted_at.asc())
        )
        quiz_answers = [
            {
                "id": str(ans.id),
                "session_id": str(ans.session_id),
                "session_question_id": str(ans.session_question_id),
                "membership_id": str(ans.membership_id),
                "submitted_answer": ans.submitted_answer,
                "status": _enum_value(ans.status),
                "is_correct": ans.is_correct,
                "points_awarded": ans.points_awarded,
                "submitted_at": ans.submitted_at.isoformat() if ans.submitted_at else None,
                "evaluated_at": ans.evaluated_at.isoformat() if ans.evaluated_at else None,
                "created_at": ans.created_at.isoformat() if ans.created_at else None,
            }
            for ans in answers_result.scalars().all()
        ]

    inventory = []
    if membership_ids:
        inventory_result = await session.execute(
            select(OwnedItem, ItemDefinition)
            .join(ItemDefinition, OwnedItem.item_definition_id == ItemDefinition.id)
            .where(OwnedItem.membership_id.in_(membership_ids))
            .order_by(OwnedItem.acquired_at.asc())
        )
        inventory = [
            {
                "owned_item_id": str(owned.id),
                "membership_id": str(owned.membership_id),
                "item_definition_id": str(owned.item_definition_id),
                "item_name": item.name,
                "item_description": item.description,
                "status": _enum_value(owned.status),
                "quantity": owned.quantity,
                "uses_remaining": owned.uses_remaining,
                "source_type": owned.source_type,
                "source_id": str(owned.source_id) if owned.source_id else None,
                "acquired_at": owned.acquired_at.isoformat() if owned.acquired_at else None,
                "activated_at": owned.activated_at.isoformat() if owned.activated_at else None,
                "expires_at": owned.expires_at.isoformat() if owned.expires_at else None,
                "consumed_at": owned.consumed_at.isoformat() if owned.consumed_at else None,
            }
            for owned, item in inventory_result.all()
        ]

    notifs_result = await session.execute(
        select(Notification)
        .where(Notification.recipient_id == account_id)
        .order_by(Notification.created_at.asc())
    )
    notifications = [
        {
            "id": str(n.id),
            "notification_type": _enum_value(n.notification_type),
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "priority": _enum_value(n.priority),
            "membership_id": str(n.membership_id) if n.membership_id else None,
            "reference_type": n.reference_type,
            "reference_id": str(n.reference_id) if n.reference_id else None,
            "deep_link": n.deep_link,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "read_at": n.read_at.isoformat() if n.read_at else None,
        }
        for n in notifs_result.scalars().all()
    ]

    ledger_entries = []
    if membership_ids:
        ledger_result = await session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.membership_id.in_(membership_ids))
            .order_by(LedgerEntry.created_at.asc())
        )
        ledger_entries = [
            {
                "id": str(le.id),
                "membership_id": str(le.membership_id),
                "competition_id": str(le.competition_id),
                "season_id": str(le.season_id) if le.season_id else None,
                "cycle_id": str(le.cycle_id) if le.cycle_id else None,
                "entry_type": _enum_value(le.entry_type),
                "amount": le.amount,
                "direction": _enum_value(le.direction),
                "balance_before": le.balance_before,
                "balance_after": le.balance_after,
                "source_type": le.source_type,
                "source_id": str(le.source_id) if le.source_id else None,
                "reason": le.reason,
                "actor_id": str(le.actor_id) if le.actor_id else None,
                "created_at": le.created_at.isoformat() if le.created_at else None,
            }
            for le in ledger_result.scalars().all()
        ]

    return {
        "account": {
            "id": str(account.id),
            "username": account.username,
            "real_name": account.real_name,
            "status": _enum_value(account.status),
            "is_admin": account.is_admin,
            "is_owner": account.is_owner,
            "locale": account.locale,
            "consent_at": account.consent_at.isoformat() if account.consent_at else None,
            "last_login_at": account.last_login_at.isoformat() if account.last_login_at else None,
            "created_at": account.created_at.isoformat() if account.created_at else None,
        },
        "memberships": memberships,
        "attacks": attacks,
        "quiz_answers": quiz_answers,
        "inventory": inventory,
        "notifications": notifications,
        "ledger_entries": ledger_entries,
    }
