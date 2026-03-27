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

    Uses native PostgreSQL ENUMs with enum VALUES (lowercase) as labels.
    SQLAlchemy 2.x with StrEnum sends the .value (lowercase) when writing
    and must also accept lowercase when reading. We pass the values explicitly
    to ensure PG enum labels match what SQLAlchemy actually sends/reads.
    """
    return SAEnum(
        *(member.value for member in enum_cls),
        name=name,
        native_enum=True,
        create_constraint=False,
    )


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
from app.modules.landing.models import LandingLink  # noqa: E402, F401
from app.modules.announcements.models import Announcement  # noqa: E402, F401
