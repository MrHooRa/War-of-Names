from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.core.database import async_session, check_db_connection, engine
from app.core.models import Base, GameInfo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    async with async_session() as session:
        result = await session.execute(select(GameInfo).limit(1))
        info = result.scalars().first()

    if not info:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Game info not found"},
        )

    return {
        "success": True,
        "data": {
            "title": info.title,
            "subtitle": info.subtitle,
            "current_season": info.current_season,
            "status": info.status,
            "announcement": info.announcement,
        },
    }
