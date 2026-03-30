"""Owner panel endpoints — platform overview, admin management, IP bans, backup, user data export."""

import gzip
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.core.auth import get_current_account, hash_password
from app.core.database import async_session, check_db_connection
from app.core.enums import AccountStatus, AuditActorType, CompetitionStatus, LedgerDirection
from app.core.middleware import invalidate_ip_ban_cache
from app.core.utils import now_riyadh
from app.config import settings
from app.modules.attacks.models import AttackAttempt
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import write_audit
from app.modules.auth.export_service import build_account_export
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, Membership
from app.modules.owner.models import IPBan
from app.modules.quiz.models import QuizSession
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

    # Scheduler jobs summary
    scheduler_jobs = []
    if scheduler and scheduler.running:
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            scheduler_jobs.append({
                "id": job.id,
                "name": job.name or job.id,
                "next_run_time": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger),
            })

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
                "scheduler_jobs": scheduler_jobs,
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


# ── List ALL accounts (for admin management with search) ─────────────────

@router.get("/accounts")
async def list_all_accounts(
    owner: OwnerAccount,
    search: str = Query(default="", description="Search by username or real_name"),
):
    """List all accounts (admins and non-admins) with optional search filter."""
    async with async_session() as session:
        query = select(Account).order_by(Account.created_at)
        if search.strip():
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Account.username.ilike(pattern),
                    Account.real_name.ilike(pattern),
                )
            )
        result = await session.execute(query)
        accounts = result.scalars().all()

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
            for a in accounts
        ],
    }


# ── Create admin account directly ────────────────────────────────────────

class CreateAdminBody(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    real_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    is_admin: bool = True


@router.post("/admins/create", status_code=201)
async def create_admin_account(body: CreateAdminBody, owner: OwnerAccount):
    """Create a new admin account directly (owner-only)."""
    async with async_session() as session:
        # Check for duplicate username
        existing = await session.execute(
            select(Account).where(Account.username == body.username)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="اسم المستخدم مستخدم بالفعل")

        account = Account(
            id=uuid.uuid4(),
            username=body.username,
            real_name=body.real_name,
            password_hash=hash_password(body.password),
            status=AccountStatus.ACTIVE,
            is_admin=body.is_admin,
        )
        session.add(account)
        await session.flush()

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="admin_account_created",
            summary=f"إنشاء حساب مشرف جديد: {body.username}",
            after_state={
                "username": body.username,
                "real_name": body.real_name,
                "is_admin": body.is_admin,
            },
        )
        await session.commit()

    return {
        "success": True,
        "message": f"تم إنشاء حساب المشرف: {body.username}",
        "data": {"id": str(account.id), "username": account.username},
    }


# ── Reset admin password ─────────────────────────────────────────────────

class ResetPasswordBody(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


@router.patch("/admins/{account_id}/reset-password")
async def reset_admin_password(account_id: uuid.UUID, body: ResetPasswordBody, owner: OwnerAccount):
    """Reset the password of any account (owner-only)."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if account.is_owner and account.id != owner.id:
            raise HTTPException(status_code=400, detail="لا يمكن إعادة تعيين كلمة مرور مالك آخر")

        account.password_hash = hash_password(body.new_password)

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="password_reset_by_owner",
            summary=f"إعادة تعيين كلمة مرور الحساب: {account.username}",
        )
        await session.commit()

    return {"success": True, "message": f"تم إعادة تعيين كلمة مرور: {account.username}"}


# ── Update admin details ─────────────────────────────────────────────────

class UpdateAdminBody(BaseModel):
    real_name: str | None = None
    username: str | None = None
    is_admin: bool | None = None
    status: str | None = None


@router.patch("/admins/{account_id}/update")
async def update_admin_details(account_id: uuid.UUID, body: UpdateAdminBody, owner: OwnerAccount):
    """Update account details (owner-only)."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if account.is_owner and account.id != owner.id:
            raise HTTPException(status_code=400, detail="لا يمكن تعديل حساب مالك آخر")

        before = {
            "username": account.username,
            "real_name": account.real_name,
            "is_admin": account.is_admin,
            "status": account.status.value if hasattr(account.status, "value") else account.status,
        }

        if body.username is not None and body.username != account.username:
            # Check uniqueness
            dup = await session.execute(
                select(Account).where(Account.username == body.username, Account.id != account_id)
            )
            if dup.scalars().first():
                raise HTTPException(status_code=400, detail="اسم المستخدم مستخدم بالفعل")
            account.username = body.username

        if body.real_name is not None:
            account.real_name = body.real_name

        if body.is_admin is not None:
            if account.is_owner:
                raise HTTPException(status_code=400, detail="لا يمكن تغيير صلاحيات المالك")
            account.is_admin = body.is_admin

        if body.status is not None:
            try:
                account.status = AccountStatus(body.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"حالة غير صالحة: {body.status}")

        after = {
            "username": account.username,
            "real_name": account.real_name,
            "is_admin": account.is_admin,
            "status": account.status.value if hasattr(account.status, "value") else account.status,
        }

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="account_updated_by_owner",
            summary=f"تعديل بيانات الحساب: {account.username}",
            before_state=before,
            after_state=after,
        )
        await session.commit()

    return {"success": True, "message": f"تم تحديث بيانات الحساب: {account.username}"}


# ── Disable (deactivate) admin account ───────────────────────────────────

@router.delete("/admins/{account_id}/remove")
async def remove_admin_account(account_id: uuid.UUID, owner: OwnerAccount):
    """Deactivate an admin account (set status=disabled)."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if account.id == owner.id:
            raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك بنفسك")
        if account.is_owner:
            raise HTTPException(status_code=400, detail="لا يمكن تعطيل حساب مالك")

        before = {
            "status": account.status.value if hasattr(account.status, "value") else account.status,
            "is_admin": account.is_admin,
        }
        account.status = AccountStatus.DISABLED
        account.is_admin = False
        after = {
            "status": account.status.value,
            "is_admin": account.is_admin,
        }

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="account_disabled_by_owner",
            summary=f"تعطيل الحساب: {account.username}",
            before_state=before,
            after_state=after,
        )
        await session.commit()

    return {"success": True, "message": f"تم تعطيل الحساب: {account.username}"}


# ═══════════════════════════════════════════════════════════════════════════
# 3. DELETION REQUESTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/deletion-requests")
async def list_deletion_requests(owner: OwnerAccount):
    """List pending account deletion requests from audit events."""
    async with async_session() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.subject_type == "account",
                AuditEvent.event_type.in_(
                    ("deletion_requested", "deletion_rejected", "deletion_approved")
                ),
            )
            .order_by(AuditEvent.created_at.desc())
        )
        events = result.scalars().all()

        pending_events = []
        seen_accounts: set[uuid.UUID] = set()
        for event in events:
            account_id = event.subject_id
            if not account_id or account_id in seen_accounts:
                continue
            seen_accounts.add(account_id)
            if event.event_type == "deletion_requested":
                pending_events.append(event)

        # Enrich with account info
        requests_data = []
        for e in pending_events:
            account = await session.get(Account, e.subject_id) if e.subject_id else None
            requests_data.append({
                "id": str(e.id),
                "account_id": str(e.subject_id) if e.subject_id else None,
                "username": account.username if account else "—",
                "real_name": account.real_name if account else "—",
                "account_status": (
                    account.status.value if account and hasattr(account.status, "value") else
                    account.status if account else None
                ),
                "reason": e.reason or (e.after_state or {}).get("reason", "—"),
                "requested_at": e.created_at.isoformat() if e.created_at else None,
            })

    return {"success": True, "data": requests_data}


@router.post("/deletion-requests/{account_id}/approve")
async def approve_deletion_request(account_id: uuid.UUID, owner: OwnerAccount):
    """Approve an account deletion request (archives the account)."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")
        if account.is_owner:
            raise HTTPException(status_code=400, detail="لا يمكن حذف حساب مالك")

        latest_deletion_event_result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.subject_type == "account",
                AuditEvent.subject_id == account.id,
                AuditEvent.event_type.in_(
                    ("deletion_requested", "deletion_rejected", "deletion_approved")
                ),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )
        latest_deletion_event = latest_deletion_event_result.scalars().first()
        if not latest_deletion_event or latest_deletion_event.event_type != "deletion_requested":
            raise HTTPException(status_code=400, detail="لا يوجد طلب حذف معلق لهذا الحساب")

        before = {
            "status": account.status.value if hasattr(account.status, "value") else account.status,
        }
        account.status = AccountStatus.ARCHIVED
        account.is_admin = False
        after = {"status": account.status.value, "is_admin": False}

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="deletion_approved",
            summary=f"الموافقة على حذف الحساب: {account.username}",
            before_state=before,
            after_state=after,
            related_type="audit_event",
            related_id=latest_deletion_event.id,
        )
        await session.commit()

    return {"success": True, "message": f"تمت الموافقة على حذف حساب: {account.username}"}


@router.post("/deletion-requests/{account_id}/reject")
async def reject_deletion_request(account_id: uuid.UUID, owner: OwnerAccount):
    """Reject an account deletion request."""
    async with async_session() as session:
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        latest_deletion_event_result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.subject_type == "account",
                AuditEvent.subject_id == account.id,
                AuditEvent.event_type.in_(
                    ("deletion_requested", "deletion_rejected", "deletion_approved")
                ),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )
        latest_deletion_event = latest_deletion_event_result.scalars().first()
        if not latest_deletion_event or latest_deletion_event.event_type != "deletion_requested":
            raise HTTPException(status_code=400, detail="لا يوجد طلب حذف معلق لهذا الحساب")

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account.id,
            event_type="deletion_rejected",
            summary=f"رفض طلب حذف الحساب: {account.username}",
            related_type="audit_event",
            related_id=latest_deletion_event.id,
        )
        await session.commit()

    return {"success": True, "message": f"تم رفض طلب حذف حساب: {account.username}"}


# ═══════════════════════════════════════════════════════════════════════════
# 4. SCHEDULER STATUS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/scheduler-status")
async def get_scheduler_status(owner: OwnerAccount):
    """Return status of all scheduler jobs with next run times."""
    from app.core.scheduler import scheduler

    if not scheduler or not scheduler.running:
        return {
            "success": True,
            "data": {"running": False, "jobs": []},
        }

    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name or job.id,
            "next_run_time": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
        })

    return {
        "success": True,
        "data": {"running": True, "jobs": jobs},
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. IP BANS
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
# 6. DATABASE BACKUP
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/backup")
async def trigger_backup(owner: OwnerAccount):
    """Export all tables as JSON backup (gzipped download)."""
    from app.core.database import engine
    from sqlalchemy import text, inspect

    backup_data = {"exported_at": now_riyadh().isoformat(), "tables": {}}

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
    timestamp = now_riyadh().strftime("%Y%m%d_%H%M%S")
    filename = f"war_of_names_backup_{timestamp}.json.gz"

    async def _stream():
        yield compressed

    return StreamingResponse(
        _stream(),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════════════
# 7. USER DATA EXPORT (PDPL COMPLIANCE)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/users/{account_id}/export-data")
async def export_user_data(account_id: uuid.UUID, owner: OwnerAccount):
    """Export all data for a user as JSON (PDPL compliance)."""
    async with async_session() as session:
        export_payload = await build_account_export(session, account_id)
        if not export_payload:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        await write_audit(
            session,
            actor_id=owner.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="account",
            subject_id=account_id,
            event_type="user_data_exported",
            summary=f"تصدير بيانات المستخدم: {export_payload['account']['username']}",
            related_type="account_export",
            related_id=account_id,
        )
        await session.commit()

    return {
        "success": True,
        "data": export_payload,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 8. LEDGER INTEGRITY CHECK
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/ledger-check")
async def check_ledger_integrity(owner: OwnerAccount):
    """Verify ledger integrity: sum(credits) - sum(debits) should equal current_balance per player."""
    async with async_session() as session:
        # Get all memberships with their current balance
        memberships_result = await session.execute(
            select(Membership)
        )
        memberships = memberships_result.scalars().all()

        mismatches = []
        total_checked = 0

        for mem in memberships:
            total_checked += 1

            # Sum credits
            credit_result = await session.execute(
                select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                    LedgerEntry.membership_id == mem.id,
                    LedgerEntry.direction == LedgerDirection.CREDIT,
                )
            )
            total_credits = credit_result.scalar()

            # Sum debits
            debit_result = await session.execute(
                select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                    LedgerEntry.membership_id == mem.id,
                    LedgerEntry.direction == LedgerDirection.DEBIT,
                )
            )
            total_debits = debit_result.scalar()

            expected_balance = total_credits - total_debits

            if expected_balance != mem.current_balance:
                mismatches.append({
                    "membership_id": str(mem.id),
                    "alias": mem.current_alias or "—",
                    "expected": expected_balance,
                    "actual": mem.current_balance,
                    "difference": expected_balance - mem.current_balance,
                })

    healthy = total_checked - len(mismatches)

    return {
        "success": True,
        "data": {
            "total_checked": total_checked,
            "healthy": healthy,
            "mismatches": mismatches,
        },
    }
