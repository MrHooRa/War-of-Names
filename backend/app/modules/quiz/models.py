"""Question bank & quiz delivery models."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    AnswerEvalStatus,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
    SessionStatus,
    SessionType,
)
from app.core.models import Base, pg_enum
from app.core.utils import now_riyadh_naive


class QuestionGroup(Base):
    __tablename__ = "question_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[QuestionStatus] = mapped_column(
        pg_enum(QuestionStatus, name="question_status"), nullable=False, default=QuestionStatus.DRAFT
    )
    competition_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("competitions.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    questions = relationship("Question", back_populates="group", lazy="selectin")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (CheckConstraint("score_value > 0", name="chk_question_score"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("question_groups.id", ondelete="CASCADE"), nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        pg_enum(QuestionType, name="question_type"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB)
    correct_answer: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score_value: Mapped[int] = mapped_column(default=10)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        pg_enum(QuestionDifficulty, name="question_difficulty"), nullable=False, default=QuestionDifficulty.MEDIUM
    )
    category: Mapped[str | None] = mapped_column(String(100))
    media_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"))
    external_media_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[QuestionStatus] = mapped_column(
        pg_enum(QuestionStatus, name="question_status"), nullable=False, default=QuestionStatus.ACTIVE
    )
    display_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    group = relationship("QuestionGroup", back_populates="questions")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = (
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="chk_session_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cycles.id", ondelete="SET NULL"))
    session_type: Mapped[SessionType] = mapped_column(pg_enum(SessionType, name="session_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        pg_enum(SessionStatus, name="session_status"), nullable=False, default=SessionStatus.DRAFT
    )
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()
    answer_duration_seconds: Mapped[int | None] = mapped_column()
    source_group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("question_groups.id", ondelete="SET NULL"))
    scoring_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    visibility_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    updated_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive, onupdate=now_riyadh_naive)

    session_questions = relationship("SessionQuestion", back_populates="session", lazy="selectin")


class SessionQuestion(Base):
    __tablename__ = "session_questions"
    __table_args__ = (UniqueConstraint("session_id", "question_id", name="uq_session_question"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    delivery_order: Mapped[int] = mapped_column(default=0)
    effective_score_value: Mapped[int] = mapped_column(nullable=False)
    effective_prompt_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    effective_options_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)

    session = relationship("QuizSession", back_populates="session_questions")


class AnswerSubmission(Base):
    __tablename__ = "answer_submissions"
    __table_args__ = (
        UniqueConstraint("membership_id", "session_question_id", name="uq_answer_per_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_sessions.id", ondelete="RESTRICT"), nullable=False)
    session_question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_questions.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_answer: Mapped[dict] = mapped_column(JSONB, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
    status: Mapped[AnswerEvalStatus] = mapped_column(
        pg_enum(AnswerEvalStatus, name="answer_eval_status"), nullable=False, default=AnswerEvalStatus.SUBMITTED
    )
    is_correct: Mapped[bool | None] = mapped_column()
    points_awarded: Mapped[int] = mapped_column(default=0)
    evaluated_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=now_riyadh_naive)
