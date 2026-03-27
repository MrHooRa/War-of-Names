"""Owner panel endpoints — platform overview, admin management, IP bans, backup, user data export."""

import gzip
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session, check_db_connection
from app.core.enums import AuditActorType, CompetitionStatus
from app.core.middleware import invalidate_ip_ban_cache
from app.config import settings
from app.modules.attacks.models import AttackAttempt
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import write_audit
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Membership
from app.modules.notifications.models import Notification
from app.modules.owner.models import IPBan
from app.modules.quiz.models import AnswerSubmission, QuizSession
from app.modules.scoring.models import LedgerEntry

router = APIRouter(prefix="/api/owner", tags=["owner"])


# ── Owner dependency ─────────────────────────────────────────────────────────

async def get_owner_account(
    account: Annotated[Account, Depends(get_current_account)],
) -> Account:
    """FastAPI dependency — resolves to Account only if user is an owner."""
    if not account.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحيات المالك",
        )
    return account


OwnerAccount = Annotated[Account, Depends(get_owner_account)]


# ═══════════════════════════════════════════════════════════════════════════
# 1. DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def owner_dashboard(owner: OwnerAccount):
    """Platform overview — aggregate counts, system info, recent admin actions."""
    async with async_session() as session:
        total_accounts = (await session.execute(select(func.count(Account.id)))).scalar() or 0
        total_competitions = (await session.execute(select(func.count(Competition.id)))).scalar() or 0
        total_active_competitions = (await session.execute(
            select(func.count(Competition.id)).where(Competition.status == CompetitionStatus.ACTIVE)
        )).scalar() or 0
        total_memberships = (await session.execute(select(func.count(Membership.id)))).scalar() or 0
        total_attacks = (await session.execute(select(func.count(AttackAttempt.id)))).scalar() or 0
        total_quiz_sessions = (await session.execute(select(func.count(QuizSession.id)))).scalar() or 0

        # Recent admin actions (last 10)
        recent_audit_result = await session.execute(
            select(AuditEvent)
            .where(AuditEvent.actor_type == AuditActorType.ADMIN)
            .order_by(AuditEvent.created_at.desc())
            .limit(10)
        )
        recent_events = [
            {
                "id": str(e.id),
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "event_type": e.event_type,
                "subject_type": e.subject_type,
                "summary": e.summary,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recent_audit_result.scalars().all()
        ]

    # System info
    db_connected = await check_db_connection()
    from app.core.scheduler import scheduler
    scheduler_running = scheduler.running if scheduler else False

    return {
        "success": True,
        "data": {
            "total_accounts": total_accounts,
            "total_competitions": total_competitions,
            "total_active_competitions": total_active_competitions,
            "total_memberships": total_memberships,
            "total_attacks": total_attacks,
            "total_quiz_sessions": total_quiz_sessions,
            "system": {
                "db_connected": db_connected,
                "scheduler_running": scheduler_running,
            },
            "recent_admin_actions": recent_events,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. ADMIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/admins")
async def list_admins(owner: OwnerAccount):
    """List all admin accounts."""
    async with async_session() as session:
        result = await session.execute(
            select(Account).where(Account.is_admin == True).order_by(Account.created_at)  # noqa: E712
        )
        admins = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(a.id),
                "username": a.username,
                "real_name": a.real_name,
                "is_admin": a.is_admin,
                "is_owner": a.is_owner,
                "status": a.status.value if hasattr(a.status, "value") else a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in admins
        ],
    }


@router.patch("/admins/{account_id}/promote")
async def promote_to_admin(account_id: uuid.UUID, owner: OwnerAccount):
    """Promote an account to admin."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if account.is_admin:
            raise HTTPException(status_code=400, detail="هذا الحساب مشرف بالفعل")

        before = {"is_admin": account.is_admin}
        account.is_admin = True
        after = {"is_admin": account.is_admin}

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="admin_promoted",
            summary=f"ترقية {account.username} إلى مشرف",
            before_state=before,
            after_state=after,
        )
        await session.commit()

    return {"success": True, "message": f"تم ترقية {account.username} إلى مشرف"}


@router.patch("/admins/{account_id}/demote")
async def demote_admin(account_id: uuid.UUID, owner: OwnerAccount):
    """Demote an admin account."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if not account.is_admin:
            raise HTTPException(status_code=400, detail="هذا الحساب ليس مشرفاً")
        if account.id == owner.id:
            raise HTTPException(status_code=400, detail="لا يمكنك إزالة صلاحياتك بنفسك")
        if account.is_owner:
            raise HTTPException(status_code=400, detail="لا يمكن إزالة صلاحيات مالك آخر")

        before = {"is_admin": account.is_admin}
        account.is_admin = False
        after = {"is_admin": account.is_admin}

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="admin_demoted",
            summary=f"إزالة صلاحيات المشرف من {account.username}",
            before_state=before,
            after_state=after,
        )
        await session.commit()

    return {"success": True, "message": f"تم إزالة صلاحيات المشرف من {account.username}"}


# ═══════════════════════════════════════════════════════════════════════════
# 3. IP BANS
# ═══════════════════════════════════════════════════════════════════════════

class IPBanCreate(BaseModel):
    ip_address: str
    reason: str | None = None
    expires_at: datetime | None = None


@router.get("/ip-bans")
async def list_ip_bans(owner: OwnerAccount):
    """List all IP bans."""
    async with async_session() as session:
        result = await session.execute(
            select(IPBan).order_by(IPBan.created_at.desc())
        )
        bans = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(b.id),
                "ip_address": b.ip_address,
                "reason": b.reason,
                "banned_by": str(b.banned_by) if b.banned_by else None,
                "expires_at": b.expires_at.isoformat() if b.expires_at else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bans
        ],
    }


@router.post("/ip-bans", status_code=201)
async def create_ip_ban(body: IPBanCreate, owner: OwnerAccount):
    """Create a new IP ban."""
    ip = body.ip_address.strip()
    if not ip:
        raise HTTPException(status_code=400, detail="عنوان IP مطلوب")

    async with async_session() as session:
        # Check for duplicate
        existing = await session.execute(
            select(IPBan).where(IPBan.ip_address == ip)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="عنوان IP محظور بالفعل")

        ban = IPBan(
            ip_address=ip,
            reason=body.reason,
            banned_by=owner.id,
            expires_at=body.expires_at,
        )
        session.add(ban)

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="ip_ban",
            subject_id=ban.id,
            event_type="ip_banned",
            summary=f"حظر عنوان IP: {ip}",
            after_state={"ip_address": ip, "reason": body.reason},
        )
        await session.commit()

    invalidate_ip_ban_cache()
    return {"success": True, "message": f"تم حظر عنوان IP: {ip}"}


@router.delete("/ip-bans/{ban_id}")
async def remove_ip_ban(ban_id: uuid.UUID, owner: OwnerAccount):
    """Remove an IP ban."""
    async with async_session() as session:
        ban = await session.get(IPBan, ban_id)
        if not ban:
            raise HTTPException(status_code=404, detail="الحظر غير موجود")

        ip = ban.ip_address
        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="ip_ban",
            subject_id=ban.id,
            event_type="ip_unbanned",
            summary=f"رفع الحظر عن عنوان IP: {ip}",
            before_state={"ip_address": ip, "reason": ban.reason},
        )
        await session.delete(ban)
        await session.commit()

    invalidate_ip_ban_cache()
    return {"success": True, "message": f"تم رفع الحظر عن عنوان IP: {ip}"}


# ═══════════════════════════════════════════════════════════════════════════
# 4. DATABASE BACKUP
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/backup")
async def trigger_backup(owner: OwnerAccount):
    """Export all tables as JSON backup (gzipped download)."""
    from app.core.database import engine
    from sqlalchemy import text, inspect

    backup_data = {"exported_at": datetime.utcnow().isoformat(), "tables": {}}

    async with engine.connect() as conn:
        # Get all table names
        table_names = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        for table in sorted(table_names):
            try:
                result = await conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = [dict(row._mapping) for row in result.fetchall()]
                # Convert non-serializable types
                from app.core.utils import jsonb_safe
                backup_data["tables"][table] = jsonb_safe(rows)
            except Exception:
                backup_data["tables"][table] = []

    import json
    raw = json.dumps(backup_data, ensure_ascii=False, default=str).encode("utf-8")
    compressed = gzip.compress(raw)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"war_of_names_backup_{timestamp}.json.gz"

    async def _stream():
        yield compressed

    return StreamingResponse(
        _stream(),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════════════
# 5. USER DATA EXPORT (PDPL COMPLIANCE)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/users/{account_id}/export-data")
async def export_user_data(account_id: uuid.UUID, owner: OwnerAccount):
    """Export all data for a user as JSON (PDPL compliance)."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        # Memberships
        memberships_result = await session.execute(
            select(Membership).where(Membership.account_id == account_id)
        )
        memberships = [
            {
                "id": str(m.id),
                "competition_id": str(m.competition_id),
                "alias": m.alias,
                "status": m.status.value if hasattr(m.status, "value") else m.status,
                "points_balance": m.points_balance,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memberships_result.scalars().all()
        ]

        # Attacks
        attacks_result = await session.execute(
            select(AttackAttempt).where(AttackAttempt.attacker_membership_id.in_(
                select(Membership.id).where(Membership.account_id == account_id)
            ))
        )
        attacks = [
            {
                "id": str(a.id),
                "attacker_membership_id": str(a.attacker_membership_id),
                "target_membership_id": str(a.target_membership_id),
                "guessed_account_id": str(a.guessed_account_id) if a.guessed_account_id else None,
                "outcome": a.outcome.value if hasattr(a.outcome, "value") else a.outcome,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in attacks_result.scalars().all()
        ]

        # Quiz answers
        answers_result = await session.execute(
            select(AnswerSubmission).where(AnswerSubmission.membership_id.in_(
                select(Membership.id).where(Membership.account_id == account_id)
            ))
        )
        quiz_answers = [
            {
                "id": str(ans.id),
                "session_question_id": str(ans.session_question_id),
                "membership_id": str(ans.membership_id),
                "selected_option": ans.selected_option,
                "is_correct": ans.is_correct,
                "points_awarded": ans.points_awarded,
                "created_at": ans.created_at.isoformat() if ans.created_at else None,
            }
            for ans in answers_result.scalars().all()
        ]

        # Notifications
        notifs_result = await session.execute(
            select(Notification).where(Notification.recipient_id == account_id)
        )
        notifications = [
            {
                "id": str(n.id),
                "notification_type": n.notification_type.value if hasattr(n.notification_type, "value") else n.notification_type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs_result.scalars().all()
        ]

        # Ledger entries
        ledger_result = await session.execute(
            select(LedgerEntry).where(LedgerEntry.membership_id.in_(
                select(Membership.id).where(Membership.account_id == account_id)
            ))
        )
        ledger_entries = [
            {
                "id": str(le.id),
                "membership_id": str(le.membership_id),
                "entry_type": le.entry_type.value if hasattr(le.entry_type, "value") else le.entry_type,
                "amount": le.amount,
                "direction": le.direction.value if hasattr(le.direction, "value") else le.direction,
                "balance_before": le.balance_before,
                "balance_after": le.balance_after,
                "reason": le.reason,
                "created_at": le.created_at.isoformat() if le.created_at else None,
            }
            for le in ledger_result.scalars().all()
        ]

    return {
        "success": True,
        "data": {
            "account": {
                "id": str(account.id),
                "username": account.username,
                "real_name": account.real_name,
                "status": account.status.value if hasattr(account.status, "value") else account.status,
                "is_admin": account.is_admin,
                "is_owner": account.is_owner,
                "locale": account.locale,
                "created_at": account.created_at.isoformat() if account.created_at else None,
            },
            "memberships": memberships,
            "attacks": attacks,
            "quiz_answers": quiz_answers,
            "notifications": notifications,
            "ledger_entries": ledger_entries,
        },
    }
