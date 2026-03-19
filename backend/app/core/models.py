"""
Central model registry — Base class, helpers, and all model imports.

Every SQLAlchemy model in the project must be importable from here so that
``Base.metadata.create_all`` discovers all tables.
"""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def pg_enum(enum_cls: type[StrEnum], *, name: str) -> SAEnum:
    """Create a SQLAlchemy Enum mapped to a PostgreSQL ENUM type.

    Uses native PostgreSQL ENUMs. ``create_all`` will auto-create the type
    if it doesn't exist yet (idempotent via ``checkfirst=True`` default).
    The migration SQL in ``migrations/001_initial_schema.sql`` is the
    canonical schema reference for production.
    """
    return SAEnum(enum_cls, name=name, native_enum=True)


# ── Temporary placeholder (supports current frontend dashboard) ───────────
class GameInfo(Base):
    __tablename__ = "game_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    subtitle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_season: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    announcement: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Import all module models so Base.metadata sees them ───────────────────
# These imports must stay at the bottom to avoid circular dependencies.
from app.modules.auth.models import Account, AccountRole, Role  # noqa: E402, F401
from app.modules.competitions.models import (  # noqa: E402, F401
    AliasRecord,
    Competition,
    CompetitionInvite,
    Cycle,
    Membership,
    Season,
)
from app.modules.scoring.models import LedgerEntry  # noqa: E402, F401
from app.modules.attacks.models import (  # noqa: E402, F401
    AttackAttempt,
    AttackExposure,
    BankruptcyRecord,
    ProtectionRecord,
)
from app.modules.store.models import (  # noqa: E402, F401
    BoxOutcome,
    Distribution,
    ItemActivation,
    ItemDefinition,
    ItemEffect,
    OwnedItem,
    RewardDefinition,
    RewardGrant,
    StoreListing,
)
from app.modules.quiz.models import (  # noqa: E402, F401
    AnswerSubmission,
    Question,
    QuestionGroup,
    QuizSession,
    SessionQuestion,
)
from app.modules.notifications.models import Notification  # noqa: E402, F401
from app.modules.audit.models import AuditEvent  # noqa: E402, F401
from app.modules.settings.models import SettingDefinition, SettingValue  # noqa: E402, F401
from app.modules.media.models import ExportArtifact, ImportJob, MediaAsset  # noqa: E402, F401
