from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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
from app.modules.announcements.router import router as announcements_router
from app.modules.owner.router import router as owner_router


async def _normalize_enum_values(conn):
    """Normalize ALL UPPERCASE enum values to lowercase across ALL tables.

    pg_enum() uses enum VALUES (lowercase) as PG labels.
    Discovers all columns that use custom enum types and converts any
    UPPERCASE values to lowercase.
    """
    from sqlalchemy import text

    # Find all columns using custom enum types
    result = await conn.execute(text("""
        SELECT c.table_name, c.column_name, c.udt_name
        FROM information_schema.columns c
        JOIN pg_type t ON t.typname = c.udt_name
        WHERE t.typtype = 'e'
        AND c.table_schema = 'public'
        ORDER BY c.table_name, c.column_name
    """))
    columns = result.fetchall()

    # Cache enum labels per type
    enum_cache = {}
    for table, column, enum_name in columns:
        if enum_name not in enum_cache:
            r = await conn.execute(text(
                f"SELECT enumlabel FROM pg_enum WHERE enumtypid = "
                f"(SELECT oid FROM pg_type WHERE typname = '{enum_name}')"
            ))
            enum_cache[enum_name] = {row[0] for row in r.fetchall()}

        labels = enum_cache[enum_name]
        for label in list(labels):
            lower = label.lower()
            if label != lower and lower in labels:
                await conn.execute(text(
                    f'UPDATE "{table}" SET "{column}" = \'{lower}\' WHERE "{column}" = \'{label}\''
                ))


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

    # 006: Add is_owner column to accounts table
    await conn.execute(text(
        "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_owner BOOLEAN DEFAULT FALSE"
    ))

    # 007: Add consent_at column to accounts table (PDPL compliance)
    await conn.execute(text(
        "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS consent_at TIMESTAMP WITHOUT TIME ZONE"
    ))

    # 003: Add lowercase enum values for ALL PostgreSQL enum types.
    # create_all generates UPPERCASE labels (enum NAMES), but pg_enum() now
    # uses lowercase VALUES. Both must exist so data can be normalized.
    # Auto-discover all custom enum types and add lowercase for each UPPERCASE label.
    enum_types_result = await conn.execute(text(
        "SELECT t.typname, e.enumlabel FROM pg_type t "
        "JOIN pg_enum e ON e.enumtypid = t.oid "
        "WHERE t.typtype = 'e' ORDER BY t.typname"
    ))
    # Group labels by type
    from collections import defaultdict
    type_labels = defaultdict(set)
    for typname, label in enum_types_result.fetchall():
        type_labels[typname].add(label)

    # For each type, add lowercase version of each UPPERCASE label
    for typname, labels in type_labels.items():
        for label in list(labels):
            lower = label.lower()
            if label != lower and lower not in labels:
                await conn.execute(text(
                    f"ALTER TYPE {typname} ADD VALUE IF NOT EXISTS '{lower}'"
                ))



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Apply schema patches that create_all cannot handle (enum additions, constraint changes)
    async with engine.begin() as conn:
        await _apply_schema_patches(conn)

    # Normalize enum values to UPPERCASE (SQLAlchemy uses enum NAMES which are uppercase)
    # Must be separate transaction — PG requires COMMIT after ALTER TYPE ADD VALUE
    try:
        async with engine.begin() as conn:
            await _normalize_enum_values(conn)
    except Exception:
        pass  # Already normalized or not needed

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

    # Start background scheduler (cycle transitions, quiz lifecycle, expirations)
    from app.core.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
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
app.include_router(announcements_router)
app.include_router(owner_router)


# --- Global Exception Handler ---


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.debug:
        raise exc
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "حدث خطأ في الخادم", "detail": None},
    )


# --- Health ---


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/scheduler")
async def health_scheduler():
    from app.core.scheduler import scheduler
    jobs = [{"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None}
            for j in scheduler.get_jobs()]
    return {"status": "running" if scheduler.running else "stopped", "jobs": jobs}


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
