"""Landing link endpoints — redirect, conversion tracking, and admin CRUD."""

import html
import secrets
import string
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_admin_account, get_current_account
from app.core.database import async_session
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, CompetitionInvite
from app.modules.landing.models import LandingLink

router = APIRouter(tags=["landing"])
AdminAccount = Annotated[Account, Depends(get_admin_account)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


async def _get_platform_branding() -> tuple[str, str]:
    """Fetch platform_name and og_image_url from settings."""
    from app.modules.settings.service import get_settings_batch
    async with async_session() as session:
        vals = await get_settings_batch(session, ["platform_name", "og_image_url"])
    name = vals.get("platform_name") or "حرب الأسماء"
    og_image = vals.get("og_image_url") or "/assets/og-image.png"
    return name, og_image


def _generate_token(length: int = 8) -> str:
    """Generate a short URL-safe token (base62)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Invite OG preview for social media bots ────────────────────────────


def _build_invite_preview_html(competition_name: str | None, token: str, platform_name: str, og_image_url: str) -> str:
    """Build minimal HTML with OG meta tags for social media bot crawlers."""
    # Escape all dynamic values for safe HTML attribute insertion
    platform_name = html.escape(platform_name)
    og_image_url = html.escape(og_image_url)
    if competition_name:
        competition_name = html.escape(competition_name)
        title = f"انضم لمنافسة {competition_name} — {platform_name}"
        description = f"لقد تمت دعوتك للانضمام إلى منافسة {competition_name} في {platform_name}!"
        og_title = f"انضم لمنافسة {competition_name} — {platform_name}"
        twitter_title = f"انضم لمنافسة {competition_name}"
        redirect_url = f"/invite/{token}"
    else:
        title = f"{platform_name} — أقوى منافسة عربية"
        description = "اكشف الأقنعة وهاجم الخصوم في أقوى منافسة عربية!"
        og_title = f"{platform_name} — أقوى منافسة عربية"
        twitter_title = platform_name
        redirect_url = "/invite/{token}".format(token=token) if token else "/"

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{og_title}">
  <meta property="og:description" content="لقد تمت دعوتك! اكشف الأقنعة وهاجم الخصوم في أقوى منافسة عربية.">
  <meta property="og:image" content="{og_image_url}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="ar_SA">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{twitter_title}">
  <meta name="twitter:image" content="{og_image_url}">
  <meta http-equiv="refresh" content="0;url={redirect_url}">
</head>
<body>
  <p>جارٍ التحويل...</p>
</body>
</html>"""


@router.get("/api/invite-preview/{token}", response_class=HTMLResponse)
async def invite_preview_html(token: str):
    """Return minimal HTML with OG meta tags for social media bot crawlers."""
    platform_name, og_image_url = await _get_platform_branding()

    async with async_session() as session:
        result = await session.execute(
            select(CompetitionInvite).where(CompetitionInvite.code == token.strip())
        )
        invite = result.scalars().first()

        competition_name: str | None = None
        if invite:
            comp = await session.get(Competition, invite.competition_id)
            if comp:
                competition_name = comp.name

    return HTMLResponse(content=_build_invite_preview_html(competition_name, token, platform_name, og_image_url))


# ── Landing link OG preview for social media bots ──────────────────────


@router.get("/api/landing-preview/{token}", response_class=HTMLResponse)
async def landing_preview_html(token: str):
    """Return minimal HTML with OG meta tags for /l/{token} landing links."""
    platform_name, og_image_url = await _get_platform_branding()

    async with async_session() as session:
        result = await session.execute(
            select(LandingLink).where(LandingLink.token == token.strip())
        )
        link = result.scalars().first()

        competition_name: str | None = None
        if link and link.competition_id:
            comp = await session.get(Competition, link.competition_id)
            if comp:
                competition_name = comp.name

    # Escape dynamic values for safe HTML insertion
    platform_name = html.escape(platform_name)
    og_image_url = html.escape(og_image_url)
    if competition_name:
        competition_name = html.escape(competition_name)
        title = f"انضم لمنافسة {competition_name} — {platform_name}"
        description = f"لقد تمت دعوتك للانضمام إلى منافسة {competition_name} في {platform_name}!"
        twitter_title = f"انضم لمنافسة {competition_name}"
    else:
        title = f"{platform_name} — أقوى منافسة عربية"
        description = "اكشف الأقنعة وهاجم الخصوم في أقوى منافسة عربية!"
        twitter_title = platform_name

    content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="لقد تمت دعوتك! اكشف الأقنعة وهاجم الخصوم في أقوى منافسة عربية.">
  <meta property="og:image" content="{og_image_url}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="ar_SA">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{twitter_title}">
  <meta name="twitter:image" content="{og_image_url}">
  <meta http-equiv="refresh" content="0;url=/l/{token}">
</head>
<body>
  <p>جارٍ التحويل...</p>
</body>
</html>"""
    return HTMLResponse(content=content)


# ── Public redirect ─────────────────────────────────────────────────────


@router.get("/l/{token}")
async def redirect_landing_link(token: str):
    """Public — resolve tracked link, count click, redirect to landing page."""
    async with async_session() as session:
        result = await session.execute(
            select(LandingLink).where(LandingLink.token == token.strip())
        )
        link = result.scalars().first()

        if not link or not link.is_active:
            # Fallback: redirect to landing page without tracking
            return RedirectResponse(url="/landing.html", status_code=302)

        # Increment click counter
        link.total_clicks += 1
        link.last_clicked_at = datetime.utcnow()
        await session.commit()

        destination = link.destination_path or "/landing.html"
        # Ensure destination points to the actual static file
        if destination == "/landing":
            destination = "/landing.html"
        separator = "&" if "?" in destination else "?"
        redirect_url = f"{destination}{separator}ref={link.token}"

    return RedirectResponse(url=redirect_url, status_code=302)


# ── Conversion tracking ─────────────────────────────────────────────────


class ConvertRequest(BaseModel):
    ref_token: str

    @field_validator("ref_token")
    @classmethod
    def clean_token(cls, v: str) -> str:
        return v.strip()


@router.post("/api/landing-links/convert")
async def track_conversion(body: ConvertRequest, account: CurrentAccount):
    """Increment total_joins for a landing link after successful join.

    Called by the frontend after the user completes the join flow,
    if a ref token was stored from the landing page visit.
    """
    async with async_session() as session:
        result = await session.execute(
            select(LandingLink).where(
                LandingLink.token == body.ref_token,
                LandingLink.is_active == True,
            )
        )
        link = result.scalars().first()
        if not link:
            # Silently ignore invalid tokens — not an error for the user
            return {"success": True, "tracked": False}

        link.total_joins += 1
        await session.commit()

    return {"success": True, "tracked": True}


# ── Admin CRUD ──────────────────────────────────────────────────────────


class CreateLandingLinkRequest(BaseModel):
    label: str
    destination_path: str = "/landing.html"
    competition_id: uuid.UUID | None = None

    @field_validator("label")
    @classmethod
    def clean_label(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1 or len(v) > 200:
            raise ValueError("التسمية يجب أن تكون بين 1-200 حرف")
        return v


@router.post("/api/admin/landing-links")
async def create_landing_link(body: CreateLandingLinkRequest, account: AdminAccount):
    """Admin — create a new tracked landing link."""
    async with async_session() as session:
        # Generate unique token (retry on collision)
        for _ in range(5):
            token = _generate_token()
            existing = await session.execute(
                select(LandingLink.id).where(LandingLink.token == token)
            )
            if not existing.scalars().first():
                break
        else:
            raise HTTPException(
                status_code=500,
                detail="فشل إنشاء رمز فريد — حاول مرة أخرى",
            )

        link = LandingLink(
            token=token,
            label=body.label,
            destination_path=body.destination_path,
            competition_id=body.competition_id,
            created_by=account.id,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)

    return {
        "success": True,
        "data": _serialize_link(link),
        "message": "تم إنشاء رابط التتبع بنجاح",
    }


@router.get("/api/admin/landing-links")
async def list_landing_links(account: AdminAccount):
    """Admin — list all tracked landing links."""
    async with async_session() as session:
        result = await session.execute(
            select(LandingLink).order_by(LandingLink.created_at.desc())
        )
        links = result.scalars().all()

    return {
        "success": True,
        "data": [_serialize_link(link) for link in links],
    }


@router.patch("/api/admin/landing-links/{link_id}")
async def update_landing_link(
    link_id: uuid.UUID,
    account: AdminAccount,
    label: str | None = None,
    is_active: bool | None = None,
):
    """Admin — update a landing link's label or active state."""
    async with async_session() as session:
        link = await session.get(LandingLink, link_id)
        if not link:
            raise HTTPException(status_code=404, detail="الرابط غير موجود")

        if label is not None:
            link.label = label.strip()
        if is_active is not None:
            link.is_active = is_active

        await session.commit()
        await session.refresh(link)

    return {
        "success": True,
        "data": _serialize_link(link),
        "message": "تم تحديث الرابط بنجاح",
    }


# ── Helpers ──────────────────────────────────────────────────────────────


def _serialize_link(link: LandingLink) -> dict:
    return {
        "id": str(link.id),
        "token": link.token,
        "label": link.label,
        "destination_path": link.destination_path,
        "competition_id": str(link.competition_id) if link.competition_id else None,
        "created_by": str(link.created_by) if link.created_by else None,
        "is_active": link.is_active,
        "total_clicks": link.total_clicks,
        "total_joins": link.total_joins,
        "last_clicked_at": link.last_clicked_at.isoformat() if link.last_clicked_at else None,
        "created_at": link.created_at.isoformat() if link.created_at else None,
        "share_url": f"/l/{link.token}",
    }
