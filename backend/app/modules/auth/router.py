"""Auth endpoints: register, login, me, update profile."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import create_access_token, get_current_account, hash_password, verify_password
from app.core.database import async_session
from app.core.enums import AuditActorType
from app.core.middleware import get_client_metadata, rate_limit_auth
from app.core.utils import now_riyadh_naive
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import write_audit
from app.modules.auth.export_service import build_account_export
from app.modules.auth.models import Account
from app.modules.auth.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.modules.auth.service import authenticate, register_account

router = APIRouter(prefix="/api/auth", tags=["auth"])

CurrentAccount = Annotated[Account, Depends(get_current_account)]


@router.post("/register", status_code=201, dependencies=[Depends(rate_limit_auth)])
async def register(body: RegisterRequest, request: Request):
    from app.modules.settings.service import get_setting

    async with async_session() as session:
        # Check global registration switch (same session as registration)
        reg_enabled = await get_setting(session, "registration_enabled")
        if reg_enabled is False:  # explicitly False, not None
            raise HTTPException(status_code=403, detail="التسجيل مغلق حالياً")

        client_metadata = get_client_metadata(request)
        try:
            account = await register_account(
                session,
                username=body.username,
                real_name=body.real_name,
                password=body.password,
                consent_accepted=body.consent_accepted,
                ip_address=client_metadata["ip_address"],
                client_context=client_metadata,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    token = create_access_token(str(account.id))
    return {
        "success": True,
        "data": TokenResponse(
            token=token,
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
            is_admin=account.is_admin,
            is_owner=account.is_owner,
        ).model_dump(),
    }


@router.post("/login", dependencies=[Depends(rate_limit_auth)])
async def login(body: LoginRequest, request: Request):
    async with async_session() as session:
        account = await authenticate(session, body.username, body.password)
        if account:
            account.last_login_at = now_riyadh_naive()
            client_metadata = get_client_metadata(request)
            await write_audit(
                session,
                actor_id=account.id,
                actor_type=AuditActorType.PARTICIPANT,
                subject_type="account",
                subject_id=account.id,
                event_type="login_succeeded",
                summary=f"تسجيل دخول ناجح: {account.username}",
                after_state={
                    "last_login_at": account.last_login_at.isoformat(),
                    "client_context": client_metadata,
                },
                ip_address=client_metadata["ip_address"],
            )
            await session.commit()
            await session.refresh(account)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة",
        )

    token = create_access_token(str(account.id))
    return {
        "success": True,
        "data": TokenResponse(
            token=token,
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
            is_admin=account.is_admin,
            is_owner=account.is_owner,
        ).model_dump(),
    }


@router.get("/me")
async def get_me(account: CurrentAccount):
    return {
        "success": True,
        "data": MeResponse(
            account_id=str(account.id),
            username=account.username,
            real_name=account.real_name,
            is_admin=account.is_admin,
            is_owner=account.is_owner,
        ).model_dump(),
    }


class UpdateProfileRequest(BaseModel):
    real_name: str | None = None
    current_password: str | None = None
    new_password: str | None = None


@router.patch("/me")
async def update_profile(body: UpdateProfileRequest, account: CurrentAccount):
    """Update current user's profile (real_name, password)."""
    async with async_session() as session:
        acct = await session.get(Account, account.id)
        if not acct:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        # Capture before-state for audit
        before_state = {"real_name": acct.real_name}
        changes = []

        if body.real_name is not None:
            if len(body.real_name.strip()) < 2:
                raise HTTPException(status_code=400, detail="الاسم الحقيقي يجب أن يكون حرفين على الأقل")
            if re.search(r"<[^>]+>", body.real_name.strip()):
                raise HTTPException(status_code=400, detail="الاسم لا يمكن أن يحتوي على رموز HTML")
            acct.real_name = body.real_name.strip()
            changes.append("real_name")

        if body.new_password:
            if not body.current_password:
                raise HTTPException(status_code=400, detail="يجب إدخال كلمة المرور الحالية")
            if not verify_password(body.current_password, acct.password_hash):
                raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
            if len(body.new_password) < 6:
                raise HTTPException(status_code=400, detail="كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل")
            acct.password_hash = hash_password(body.new_password)
            changes.append("password")

        # Audit trail for profile update
        if changes:
            after_state = {"real_name": acct.real_name, "fields_changed": changes}
            await write_audit(
                session,
                actor_id=account.id,
                actor_type=AuditActorType.PARTICIPANT,
                subject_type="account",
                subject_id=account.id,
                event_type="profile_updated",
                summary=f"تحديث الملف الشخصي: {', '.join(changes)}",
                before_state=before_state,
                after_state=after_state,
            )

        await session.commit()

    return {"success": True, "message": "تم تحديث الملف الشخصي بنجاح"}


@router.post("/me/request-deletion", status_code=201)
async def request_account_deletion(account: CurrentAccount):
    """Request account deletion — creates an audit event for owner review."""
    async with async_session() as session:
        # Only block when the latest deletion workflow event is an unresolved request.
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
        if latest_deletion_event and latest_deletion_event.event_type == "deletion_requested":
            raise HTTPException(status_code=400, detail="لديك طلب حذف معلق بالفعل")

        await write_audit(
            session,
            actor_id=account.id,
            actor_type=AuditActorType.PARTICIPANT,
            subject_type="account",
            subject_id=account.id,
            event_type="deletion_requested",
            summary=f"طلب حذف الحساب: {account.username}",
        )
        await session.commit()

    return {"success": True, "message": "تم تقديم طلب حذف الحساب. سيتم مراجعته من قبل الإدارة"}


@router.get("/me/export-data")
async def export_my_data(account: CurrentAccount):
    """Export the current user's personal/gameplay data in machine-readable form."""
    async with async_session() as session:
        export_payload = await build_account_export(session, account.id)
        if not export_payload:
            raise HTTPException(status_code=404, detail="الحساب غير موجود")

        await write_audit(
            session,
            actor_id=account.id,
            actor_type=AuditActorType.PARTICIPANT,
            subject_type="account",
            subject_id=account.id,
            event_type="self_data_exported",
            summary=f"تصدير البيانات الشخصية: {account.username}",
            related_type="account_export",
            related_id=account.id,
        )
        await session.commit()

    return {"success": True, "data": export_payload}
