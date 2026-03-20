from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.core.database import async_session, check_db_connection, engine
from app.core.models import Base, GameInfo
from app.core.seed import seed
from app.modules.auth.router import router as auth_router
from app.modules.competitions.router import router as competitions_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.attacks.router import router as attacks_router
from app.modules.leaderboard.router import router as leaderboard_router
from app.modules.store.router import router as store_router
from app.modules.quiz.router import router as quiz_router
from app.modules.admin.router import router as admin_router
from app.modules.notifications.router import router as notifications_router
from app.modules.landing.router import router as landing_router


async def _apply_schema_patches(conn):
    """Apply incremental schema patches that create_all cannot handle.

    PostgreSQL ALTER TYPE ... ADD VALUE is a no-op if the value already exists
    (IF NOT EXISTS).

    Note: create_all uses uppercase enum NAMES (e.g. 'AVAILABLE') as PostgreSQL
    labels, while the initial SQL migration uses lowercase VALUES ('available').
    We add both casings so the patch works regardless of how the DB was created.
    """
    from sqlalchemy import text

    # 002: Add 'PENDING' to owned_item_status enum (uppercase — matches create_all)
    await conn.execute(text(
        "ALTER TYPE owned_item_status ADD VALUE IF NOT EXISTS 'PENDING'"
    ))
    # Also add lowercase in case the DB was created from the SQL migration
    await conn.execute(text(
        "ALTER TYPE owned_item_status ADD VALUE IF NOT EXISTS 'pending'"
    ))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Apply schema patches that create_all cannot handle (enum additions, constraint changes)
    async with engine.begin() as conn:
        await _apply_schema_patches(conn)

    # Seed game_info if empty
    async with async_session() as session:
        result = await session.execute(select(GameInfo))
        if not result.scalars().first():
            session.add(
                GameInfo(
                    title="حرب الأسماء",
                    subtitle="من سيكشف الأقنعة أولاً؟",
                    current_season="الموسم الأول",
                    status="active",
                    announcement="مرحباً بكم في حرب الأسماء! الموسم الأول يبدأ قريباً",
                )
            )
            await session.commit()

    # Run seeder (idempotent)
    async with async_session() as session:
        await seed(session)

    yield
    await engine.dispose()


app = FastAPI(
    title="War of Names API",
    description="حرب الأسماء — Seasonal alias-based competition platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(competitions_router)
app.include_router(dashboard_router)
app.include_router(attacks_router)
app.include_router(leaderboard_router)
app.include_router(store_router)
app.include_router(quiz_router)
app.include_router(notifications_router)
app.include_router(admin_router)
app.include_router(landing_router)


# --- Health ---


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/db")
async def health_db():
    connected = await check_db_connection()
    if connected:
        return {"status": "ok", "database": "connected"}
    return JSONResponse(
        status_code=503,
        content={"status": "error", "database": "unreachable"},
    )


# --- Game Info ---


@app.get("/api/game-info")
async def get_game_info():
    from app.modules.competitions.models import Competition, Season, Cycle

    async with async_session() as session:
        result = await session.execute(select(GameInfo).limit(1))
        info = result.scalars().first()

        # Find the active season/cycle from the first active competition
        active_season_name = None
        active_cycle_label = None
        comp_result = await session.execute(
            select(Competition).where(Competition.status == "active").limit(1)
        )
        active_comp = comp_result.scalars().first()
        if active_comp:
            season_result = await session.execute(
                select(Season).where(Season.competition_id == active_comp.id, Season.status == "active").limit(1)
            )
            active_season = season_result.scalars().first()
            if active_season:
                active_season_name = active_season.name
                cycle_result = await session.execute(
                    select(Cycle).where(Cycle.season_id == active_season.id, Cycle.status == "active").limit(1)
                )
                active_cycle = cycle_result.scalars().first()
                if active_cycle:
                    active_cycle_label = active_cycle.label

    if not info:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Game info not found"},
        )

    # Build season text: prefer real season/cycle, fall back to static current_season
    season_text = info.current_season
    if active_season_name:
        season_text = active_season_name
        if active_cycle_label:
            season_text = f"{active_season_name} — {active_cycle_label}"

    return {
        "success": True,
        "data": {
            "title": info.title,
            "subtitle": info.subtitle,
            "current_season": season_text,
            "status": info.status,
            "announcement": info.announcement,
            "active_season": active_season_name,
            "active_cycle": active_cycle_label,
        },
    }
