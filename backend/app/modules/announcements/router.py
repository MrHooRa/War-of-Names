"""Announcement endpoints — admin CRUD + player-facing active announcements."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update

from app.core.auth import get_admin_account, get_current_account
from app.core.database import async_session
from app.core.enums import AuditActorType
from app.modules.announcements.models import Announcement, AnnouncementScope, AnnouncementStyle
from app.modules.audit.service import write_audit
from app.modules.auth.models import Account

router = APIRouter(tags=["announcements"])

AdminAccount = Annotated[Account, Depends(get_admin_account)]
AuthAccount = Annotated[Account, Depends(get_current_account)]


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateAnnouncementRequest(BaseModel):
    title: str
    subtitle: str | None = None
    body: str | None = None
    style: AnnouncementStyle = AnnouncementStyle.INFO
    scope: AnnouncementScope = AnnouncementScope.GLOBAL
    competition_id: uuid.UUID | None = None
    season_id: uuid.UUID | None = None
    cycle_id: uuid.UUID | None = None
    cta_label: str | None = None
    cta_url: str | None = None
    is_dismissible: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class UpdateAnnouncementRequest(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    body: str | None = None
    style: AnnouncementStyle | None = None
    scope: AnnouncementScope | None = None
    competition_id: uuid.UUID | None = None
    season_id: uuid.UUID | None = None
    cycle_id: uuid.UUID | None = None
    cta_label: str | None = None
    cta_url: str | None = None
    is_active: bool | None = None
    is_dismissible: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


def _serialize(ann: Announcement) -> dict:
    return {
        "id": str(ann.id),
        "title": ann.title,
        "subtitle": ann.subtitle,
        "body": ann.body,
        "style": ann.style,
        "scope": ann.scope,
        "competition_id": str(ann.competition_id) if ann.competition_id else None,
        "season_id": str(ann.season_id) if ann.season_id else None,
        "cycle_id": str(ann.cycle_id) if ann.cycle_id else None,
        "cta_label": ann.cta_label,
        "cta_url": ann.cta_url,
        "is_active": ann.is_active,
        "is_dismissible": ann.is_dismissible,
        "starts_at": ann.starts_at.isoformat() if ann.starts_at else None,
        "ends_at": ann.ends_at.isoformat() if ann.ends_at else None,
        "created_at": ann.created_at.isoformat() if ann.created_at else None,
        "updated_at": ann.updated_at.isoformat() if ann.updated_at else None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN CRUD
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/api/admin/announcements")
async def admin_list_announcements(admin: AdminAccount):
    """List all announcements (active and inactive) for admin management."""
    async with async_session() as session:
        result = await session.execute(
            select(Announcement).order_by(Announcement.created_at.desc())
        )
        announcements = result.scalars().all()
        return {
            "success": True,
            "data": [_serialize(a) for a in announcements],
        }


@router.post("/api/admin/announcements")
async def admin_create_announcement(admin: AdminAccount, req: CreateAnnouncementRequest):
    """Create a new announcement."""
    async with async_session() as session:
        ann = Announcement(
            title=req.title,
            subtitle=req.subtitle,
            body=req.body,
            style=req.style,
            scope=req.scope,
            competition_id=req.competition_id,
            season_id=req.season_id,
            cycle_id=req.cycle_id,
            cta_label=req.cta_label,
            cta_url=req.cta_url,
            is_dismissible=req.is_dismissible,
            starts_at=req.starts_at,
            ends_at=req.ends_at,
            created_by=admin.id,
        )
        session.add(ann)
        await session.flush()

        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="announcement",
            subject_id=ann.id,
            event_type="announcement.created",
            summary=f"أنشأ إعلان: {req.title}",
        )
        await session.commit()
        await session.refresh(ann)

        return {
            "success": True,
            "message": "تم إنشاء الإعلان بنجاح",
            "data": _serialize(ann),
        }


@router.patch("/api/admin/announcements/{announcement_id}")
async def admin_update_announcement(
    admin: AdminAccount,
    announcement_id: uuid.UUID,
    req: UpdateAnnouncementRequest,
):
    """Update an existing announcement."""
    async with async_session() as session:
        result = await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        ann = result.scalars().first()
        if not ann:
            raise HTTPException(status_code=404, detail="الإعلان غير موجود")

        changes = req.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=400, detail="لا توجد تغييرات")

        before = {k: getattr(ann, k) for k in changes}
        for key, value in changes.items():
            setattr(ann, key, value)
        ann.updated_at = datetime.utcnow()

        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="announcement",
            subject_id=ann.id,
            event_type="announcement.updated",
            summary=f"حدّث إعلان: {ann.title}",
            before_state=before,
            after_state=changes,
        )
        await session.commit()
        await session.refresh(ann)

        return {
            "success": True,
            "message": "تم تحديث الإعلان بنجاح",
            "data": _serialize(ann),
        }


@router.delete("/api/admin/announcements/{announcement_id}")
async def admin_delete_announcement(admin: AdminAccount, announcement_id: uuid.UUID):
    """Delete an announcement permanently."""
    async with async_session() as session:
        result = await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        ann = result.scalars().first()
        if not ann:
            raise HTTPException(status_code=404, detail="الإعلان غير موجود")

        title = ann.title
        await session.delete(ann)

        await write_audit(
            session,
            actor_id=admin.id,
            actor_type=AuditActorType.ADMIN,
            subject_type="announcement",
            subject_id=announcement_id,
            event_type="announcement.deleted",
            summary=f"حذف إعلان: {title}",
        )
        await session.commit()

        return {
            "success": True,
            "message": "تم حذف الإعلان بنجاح",
        }


# ═══════════════════════════════════════════════════════════════════════════
# PLAYER-FACING — active announcements
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/api/announcements")
async def get_active_announcements(
    account: AuthAccount,
    competition_id: uuid.UUID | None = Query(None),
    season_id: uuid.UUID | None = Query(None),
    cycle_id: uuid.UUID | None = Query(None),
):
    """Return currently active announcements visible to this player.

    Filters by scope: global announcements always show, plus
    competition/season/cycle-specific ones when IDs are provided.
    Respects starts_at/ends_at timing windows.
    """
    now = datetime.utcnow()
    async with async_session() as session:
        query = (
            select(Announcement)
            .where(Announcement.is_active == True)  # noqa: E712
        )
        result = await session.execute(query.order_by(Announcement.created_at.desc()))
        all_active = result.scalars().all()

    visible = []
    for ann in all_active:
        # Timing filter
        if ann.starts_at and ann.starts_at > now:
            continue
        if ann.ends_at and ann.ends_at < now:
            continue

        # Scope filter
        if ann.scope == AnnouncementScope.GLOBAL:
            visible.append(ann)
        elif ann.scope == AnnouncementScope.COMPETITION and ann.competition_id and competition_id:
            if ann.competition_id == competition_id:
                visible.append(ann)
        elif ann.scope == AnnouncementScope.SEASON and ann.season_id and season_id:
            if ann.season_id == season_id:
                visible.append(ann)
        elif ann.scope == AnnouncementScope.CYCLE and ann.cycle_id and cycle_id:
            if ann.cycle_id == cycle_id:
                visible.append(ann)

    return {
        "success": True,
        "data": [_serialize(a) for a in visible],
    }
