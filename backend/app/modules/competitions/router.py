"""Competition join + context endpoints.

Join flows:
  POST /api/join          — join by invite code (resolves competition from code)
  POST /api/join/link/{t} — join by invite link token
  GET  /api/join/link/{t} — validate invite link, return competition info

Legacy (kept for backward compat):
  POST /api/competitions/{id}/join — join by competition ID + code

Context:
  GET  /api/competitions/active    — public: first active competition
  GET  /api/competitions/joinable  — public: all joinable competitions
  GET  /api/me/memberships         — authenticated: user's memberships
  GET  /api/me/competition-context — authenticated: active competition context
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select

from app.core.auth import get_current_account
from app.core.database import async_session
from app.core.enums import (
    CompetitionStatus,
    CycleStatus,
    MembershipStatus,
    SeasonStatus,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import (
    Competition,
    Cycle,
    Membership,
    Season,
)
from app.modules.competitions.invite_service import (
    resolve_competition_by_code,
    resolve_competition_by_token,
)
from app.modules.competitions.join_service import (
    JoinError,
    execute_join,
    validate_join,
)
from app.modules.competitions.schemas import JoinRequest

router = APIRouter(tags=["competitions"])
CurrentAccount = Annotated[Account, Depends(get_current_account)]


# ── Request schemas ──────────────────────────────────────────────────────


class JoinByCodeRequest(BaseModel):
    invite_code: str
    alias: str

    @field_validator("invite_code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("alias")
    @classmethod
    def clean_alias(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("اللقب يجب أن يكون بين 2-50 حرف")
        return v


class JoinByLinkRequest(BaseModel):
    alias: str

    @field_validator("alias")
    @classmethod
    def clean_alias(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("اللقب يجب أن يكون بين 2-50 حرف")
        return v


# ── Join by Code (primary flow) ──────────────────────────────────────────


@router.post("/api/join")
async def join_by_code(body: JoinByCodeRequest, account: CurrentAccount):
    """Join a competition using an invite code.

    The code resolves to a competition — user does NOT need to know the
    competition UUID.
    """
    async with async_session() as session:
        invite = await resolve_competition_by_code(session, body.invite_code)
        if not invite:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "invite_invalid",
                    "message": "رمز الدعوة غير صالح أو منتهي الصلاحية",
                },
            )

        comp = await session.get(Competition, invite.competition_id)
        if not comp:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "competition_not_found",
                    "message": "المنافسة المرتبطة بهذا الرمز غير موجودة",
                },
            )

        try:
            await validate_join(session, comp, invite, account.id, body.alias)
        except JoinError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={"error_code": e.error_code, "message": e.message},
            )

        result = await execute_join(session, comp, invite, account.id, body.alias)

    return {
        "success": True,
        "data": result,
        "message": f"أهلاً بك في المنافسة يا {body.alias}! رصيدك الابتدائي: {result['balance']} نقطة",
    }


# ── Join by Link ─────────────────────────────────────────────────────────


@router.get("/api/join/link/{token}")
async def validate_invite_link(token: str):
    """Validate an invite link and return competition info (public)."""
    async with async_session() as session:
        invite = await resolve_competition_by_token(session, token)
        if not invite:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "invite_invalid",
                    "message": "رابط الدعوة غير صالح أو منتهي الصلاحية",
                },
            )

        comp = await session.get(Competition, invite.competition_id)
        if not comp:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "competition_not_found",
                    "message": "المنافسة المرتبطة بهذا الرابط غير موجودة",
                },
            )

    joinable = (
        comp.registration_open
        and comp.status in (CompetitionStatus.ACTIVE, CompetitionStatus.REGISTRATION_OPEN)
    )

    return {
        "success": True,
        "data": {
            "competition_id": str(comp.id),
            "name": comp.name,
            "description": comp.description,
            "joinable": joinable,
            "status": comp.status.value if hasattr(comp.status, "value") else str(comp.status),
        },
    }


@router.post("/api/join/link/{token}")
async def join_by_link(token: str, body: JoinByLinkRequest, account: CurrentAccount):
    """Join a competition using an invite link token."""
    async with async_session() as session:
        invite = await resolve_competition_by_token(session, token)
        if not invite:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "invite_invalid",
                    "message": "رابط الدعوة غير صالح أو منتهي الصلاحية",
                },
            )

        comp = await session.get(Competition, invite.competition_id)
        if not comp:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "competition_not_found",
                    "message": "المنافسة المرتبطة بهذا الرابط غير موجودة",
                },
            )

        try:
            await validate_join(session, comp, invite, account.id, body.alias)
        except JoinError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={"error_code": e.error_code, "message": e.message},
            )

        result = await execute_join(session, comp, invite, account.id, body.alias)

    return {
        "success": True,
        "data": result,
        "message": f"أهلاً بك في المنافسة يا {body.alias}! رصيدك الابتدائي: {result['balance']} نقطة",
    }


# ── Legacy join (backward compat) ────────────────────────────────────────


@router.post("/api/competitions/{competition_id}/join")
async def join_competition_legacy(
    competition_id: uuid.UUID,
    body: JoinRequest,
    account: CurrentAccount,
):
    """Legacy join endpoint — requires competition ID + invite code.

    Delegates to the centralized join service.
    """
    async with async_session() as session:
        comp = await session.get(Competition, competition_id)
        if not comp:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "competition_not_found", "message": "المنافسة غير موجودة"},
            )

        invite = await resolve_competition_by_code(session, body.invite_code)
        if not invite or invite.competition_id != competition_id:
            raise HTTPException(
                status_code=400,
                detail={"error_code": "invite_invalid", "message": "رمز الدعوة غير صالح أو منتهي الصلاحية"},
            )

        try:
            await validate_join(session, comp, invite, account.id, body.alias)
        except JoinError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={"error_code": e.error_code, "message": e.message},
            )

        result = await execute_join(session, comp, invite, account.id, body.alias)

    return {
        "success": True,
        "data": result,
        "message": f"أهلاً بك في المنافسة يا {body.alias}! رصيدك الابتدائي: {result['balance']} نقطة",
    }


# ── Public discovery ─────────────────────────────────────────────────────


@router.get("/api/competitions/active")
async def get_active_competition():
    """Public — returns the first active competition accepting registrations."""
    async with async_session() as session:
        result = await session.execute(
            select(Competition).where(
                Competition.status.in_([
                    CompetitionStatus.ACTIVE,
                    CompetitionStatus.REGISTRATION_OPEN,
                ]),
                Competition.registration_open == True,
            ).limit(1)
        )
        comp = result.scalars().first()

    if not comp:
        return {"success": True, "data": None}

    return {
        "success": True,
        "data": {
            "competition_id": str(comp.id),
            "name": comp.name,
            "description": comp.description,
        },
    }


@router.get("/api/competitions/joinable")
async def list_joinable_competitions():
    """Public — returns all competitions currently accepting registrations."""
    async with async_session() as session:
        result = await session.execute(
            select(Competition).where(
                Competition.status.in_([
                    CompetitionStatus.ACTIVE,
                    CompetitionStatus.REGISTRATION_OPEN,
                ]),
                Competition.registration_open == True,
            ).order_by(Competition.created_at.desc())
        )
        comps = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "competition_id": str(c.id),
                "name": c.name,
                "description": c.description,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            }
            for c in comps
        ],
    }


# ── Authenticated context ────────────────────────────────────────────────


@router.get("/api/me/memberships")
async def list_my_memberships(account: CurrentAccount):
    """Returns all memberships for the current user with competition info."""
    async with async_session() as session:
        result = await session.execute(
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(Membership.account_id == account.id)
            .order_by(Membership.joined_at.desc())
        )
        rows = result.all()

    return {
        "success": True,
        "data": [
            {
                "membership_id": str(mem.id),
                "competition_id": str(comp.id),
                "competition_name": comp.name,
                "competition_status": comp.status.value if hasattr(comp.status, "value") else str(comp.status),
                "alias": mem.current_alias,
                "balance": mem.current_balance,
                "status": mem.status.value if hasattr(mem.status, "value") else str(mem.status),
                "is_bankrupt": mem.is_bankrupt,
                "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
            }
            for mem, comp in rows
        ],
    }


@router.get("/api/me/competition-context")
async def get_competition_context(
    account: CurrentAccount,
    competition_id: uuid.UUID | None = None,
):
    """Returns the active competition context for the current user.

    If competition_id query param is provided, use that; otherwise pick the
    first active membership.
    """
    async with async_session() as session:
        query = (
            select(Membership, Competition)
            .join(Competition, Membership.competition_id == Competition.id)
            .where(
                Membership.account_id == account.id,
                Membership.status == MembershipStatus.ACTIVE,
                Competition.status.in_([
                    CompetitionStatus.ACTIVE,
                    CompetitionStatus.REGISTRATION_OPEN,
                ]),
            )
        )
        if competition_id:
            query = query.where(Competition.id == competition_id)
        query = query.limit(1)
        mem_result = await session.execute(query)
        row = mem_result.first()
        if not row:
            return {"success": True, "data": None}

        membership, competition = row

        # Active season + cycle
        season = (await session.execute(
            select(Season).where(
                Season.competition_id == competition.id,
                Season.status == SeasonStatus.ACTIVE,
            ).limit(1)
        )).scalars().first()

        cycle = None
        if season:
            cycle = (await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status == CycleStatus.ACTIVE,
                ).limit(1)
            )).scalars().first()

        # Next cycle (upcoming after the current one)
        next_cycle = None
        if season and cycle:
            next_cycle_result = await session.execute(
                select(Cycle).where(
                    Cycle.season_id == season.id,
                    Cycle.status.in_([CycleStatus.DRAFT, CycleStatus.PAUSED]),
                    Cycle.order_index > cycle.order_index,
                ).order_by(Cycle.order_index).limit(1)
            )
            next_cycle = next_cycle_result.scalars().first()

        # Compute rank
        rank_result = await session.execute(
            select(func.count()).where(
                Membership.competition_id == competition.id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.current_balance > membership.current_balance,
            )
        )
        rank = (rank_result.scalar() or 0) + 1

    return {
        "success": True,
        "data": {
            "competition_id": str(competition.id),
            "competition_name": competition.name,
            "season_id": str(season.id) if season else None,
            "season_name": season.name if season else None,
            "cycle_id": str(cycle.id) if cycle else None,
            "cycle_label": cycle.label if cycle else None,
            "cycle_starts_at": cycle.starts_at.isoformat() if cycle and cycle.starts_at else None,
            "cycle_ends_at": cycle.ends_at.isoformat() if cycle and cycle.ends_at else None,
            "next_cycle_label": next_cycle.label if next_cycle else None,
            "next_cycle_starts_at": next_cycle.starts_at.isoformat() if next_cycle and next_cycle.starts_at else None,
            "membership_id": str(membership.id),
            "alias": membership.current_alias or account.username,
            "balance": membership.current_balance,
            "protection": membership.protection,
            "is_bankrupt": membership.is_bankrupt,
            "rank": rank,
        },
    }
