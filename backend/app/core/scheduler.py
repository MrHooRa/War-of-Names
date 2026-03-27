"""Background scheduler — automates cycle transitions, quiz lifecycle, and expirations.

Uses APScheduler with IntervalTrigger jobs that poll the DB every 1-2 minutes.
Each job runs independently using async_session() (no request context needed).

Jobs:
  1. Cycle auto-start/end (+ season start/end)
  2. Quiz session auto-open/close
  3. Item expiration
  4. Protection expiration
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_

from app.core.database import async_session
from app.core.enums import (
    CycleStatus,
    MembershipStatus,
    NotificationType,
    OwnedItemStatus,
    ProtectionType,
    SeasonStatus,
    SessionStatus,
)
from app.modules.competitions.models import Competition, Cycle, Membership, Season
from app.modules.quiz.models import QuizSession
from app.modules.store.models import OwnedItem
from app.modules.attacks.models import ProtectionRecord
from app.modules.notifications.service import create_notification

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()


# ── Job 1: Cycle & Season Auto-Transitions ──────────────────────────────────


async def job_cycle_transitions():
    """Auto-start draft cycles and auto-end active cycles based on timestamps."""
    now = datetime.utcnow()
    try:
        async with async_session() as session:
            # Import here to avoid circular imports
            from app.modules.competitions.cycle_service import start_cycle, end_cycle

            # Auto-START: draft cycles whose starts_at has arrived
            draft_result = await session.execute(
                select(Cycle).where(
                    Cycle.status == CycleStatus.DRAFT,
                    Cycle.starts_at != None,  # noqa: E711
                    Cycle.starts_at <= now,
                )
            )
            for cycle in draft_result.scalars().all():
                season = await session.get(Season, cycle.season_id)
                if season and season.status == SeasonStatus.ACTIVE:
                    logger.info(f"Auto-starting cycle: {cycle.label} (id={cycle.id})")
                    await start_cycle(session, cycle, season)

            # Auto-END: active cycles whose ends_at has passed
            active_result = await session.execute(
                select(Cycle).where(
                    Cycle.status == CycleStatus.ACTIVE,
                    Cycle.ends_at != None,  # noqa: E711
                    Cycle.ends_at <= now,
                )
            )
            for cycle in active_result.scalars().all():
                season = await session.get(Season, cycle.season_id)
                if season:
                    logger.info(f"Auto-ending cycle: {cycle.label} (id={cycle.id})")
                    await end_cycle(session, cycle, season)

            await session.commit()
    except Exception:
        logger.exception("Error in job_cycle_transitions")


async def job_season_transitions():
    """Auto-start draft seasons and auto-end active seasons based on timestamps."""
    now = datetime.utcnow()
    try:
        async with async_session() as session:
            from app.modules.competitions.cycle_service import start_season, end_season

            # Auto-START: draft seasons whose starts_at has arrived
            draft_result = await session.execute(
                select(Season).where(
                    Season.status == SeasonStatus.DRAFT,
                    Season.starts_at != None,  # noqa: E711
                    Season.starts_at <= now,
                )
            )
            for season in draft_result.scalars().all():
                logger.info(f"Auto-starting season: {season.name} (id={season.id})")
                await start_season(session, season, season.competition_id)

            # Auto-END: active seasons whose ends_at has passed
            active_result = await session.execute(
                select(Season).where(
                    Season.status == SeasonStatus.ACTIVE,
                    Season.ends_at != None,  # noqa: E711
                    Season.ends_at <= now,
                )
            )
            for season in active_result.scalars().all():
                logger.info(f"Auto-ending season: {season.name} (id={season.id})")
                await end_season(session, season, season.competition_id)

            await session.commit()
    except Exception:
        logger.exception("Error in job_season_transitions")


# ── Job 2: Quiz Session Auto-Open/Close ─────────────────────────────────────


async def job_quiz_lifecycle():
    """Auto-open scheduled quiz sessions and auto-close expired ones."""
    now = datetime.utcnow()
    try:
        async with async_session() as session:
            # Auto-OPEN: scheduled sessions whose starts_at has arrived
            scheduled_result = await session.execute(
                select(QuizSession).where(
                    QuizSession.status == SessionStatus.SCHEDULED,
                    QuizSession.starts_at != None,  # noqa: E711
                    QuizSession.starts_at <= now,
                )
            )
            for quiz in scheduled_result.scalars().all():
                logger.info(f"Auto-opening quiz session: {quiz.title} (id={quiz.id})")
                quiz.status = SessionStatus.OPEN

                # Notify all active members
                members_result = await session.execute(
                    select(Membership).where(
                        Membership.competition_id == quiz.competition_id,
                        Membership.status == MembershipStatus.ACTIVE,
                    )
                )
                for m in members_result.scalars().all():
                    await create_notification(
                        session,
                        recipient_id=m.account_id,
                        notification_type=NotificationType.QUIZ_OPENED,
                        title="جلسة أسئلة جديدة!",
                        message=f"تم فتح جلسة أسئلة: {quiz.title}",
                        membership_id=m.id,
                        reference_type="quiz_session",
                        reference_id=quiz.id,
                        deep_link="/quiz",
                    )

            # Auto-CLOSE: open sessions whose ends_at has passed
            open_result = await session.execute(
                select(QuizSession).where(
                    QuizSession.status == SessionStatus.OPEN,
                    QuizSession.ends_at != None,  # noqa: E711
                    QuizSession.ends_at <= now,
                )
            )
            for quiz in open_result.scalars().all():
                logger.info(f"Auto-closing quiz session: {quiz.title} (id={quiz.id})")
                quiz.status = SessionStatus.CLOSED

            await session.commit()
    except Exception:
        logger.exception("Error in job_quiz_lifecycle")


# ── Job 3: Item Expiration ──────────────────────────────────────────────────


async def job_expire_items():
    """Expire owned items whose expires_at has passed."""
    now = datetime.utcnow()
    try:
        async with async_session() as session:
            result = await session.execute(
                select(OwnedItem).where(
                    OwnedItem.status.in_([OwnedItemStatus.AVAILABLE, OwnedItemStatus.ACTIVATED]),
                    OwnedItem.expires_at != None,  # noqa: E711
                    OwnedItem.expires_at <= now,
                )
            )
            expired_count = 0
            for item in result.scalars().all():
                item.status = OwnedItemStatus.EXPIRED
                expired_count += 1

            if expired_count > 0:
                logger.info(f"Expired {expired_count} items")
                await session.commit()
    except Exception:
        logger.exception("Error in job_expire_items")


# ── Job 4: Protection Expiration ────────────────────────────────────────────


async def job_expire_protections():
    """Reset protection on memberships whose ProtectionRecord has expired."""
    now = datetime.utcnow()
    try:
        async with async_session() as session:
            # Find expired protection records
            expired_records = await session.execute(
                select(ProtectionRecord).where(
                    ProtectionRecord.ends_at != None,  # noqa: E711
                    ProtectionRecord.ends_at <= now,
                )
            )
            membership_ids_to_reset = set()
            for record in expired_records.scalars().all():
                membership_ids_to_reset.add(record.membership_id)

            # Reset protection on affected memberships (only if still protected)
            reset_count = 0
            for mid in membership_ids_to_reset:
                membership = await session.get(Membership, mid)
                if membership and membership.protection != ProtectionType.NONE:
                    # Check if there are any still-active protection records
                    active_result = await session.execute(
                        select(ProtectionRecord).where(
                            ProtectionRecord.membership_id == mid,
                            and_(
                                ProtectionRecord.ends_at != None,  # noqa: E711
                                ProtectionRecord.ends_at > now,
                            ),
                        ).limit(1)
                    )
                    if not active_result.scalars().first():
                        membership.protection = ProtectionType.NONE
                        reset_count += 1

            if reset_count > 0:
                logger.info(f"Reset protection on {reset_count} memberships")
                await session.commit()
    except Exception:
        logger.exception("Error in job_expire_protections")


# ── Scheduler Setup ─────────────────────────────────────────────────────────


def setup_scheduler():
    """Configure all scheduler jobs. Call once at startup."""
    # Cycle/season transitions — check every 60 seconds
    scheduler.add_job(job_cycle_transitions, "interval", seconds=60, id="cycle_transitions",
                      max_instances=1, replace_existing=True)
    scheduler.add_job(job_season_transitions, "interval", seconds=60, id="season_transitions",
                      max_instances=1, replace_existing=True)

    # Quiz lifecycle — check every 30 seconds (more time-sensitive)
    scheduler.add_job(job_quiz_lifecycle, "interval", seconds=30, id="quiz_lifecycle",
                      max_instances=1, replace_existing=True)

    # Expirations — check every 5 minutes (less urgent)
    scheduler.add_job(job_expire_items, "interval", seconds=300, id="expire_items",
                      max_instances=1, replace_existing=True)
    scheduler.add_job(job_expire_protections, "interval", seconds=300, id="expire_protections",
                      max_instances=1, replace_existing=True)

    logger.info("Scheduler configured with 5 jobs")


def start_scheduler():
    """Start the scheduler."""
    setup_scheduler()
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
