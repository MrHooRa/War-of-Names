"""
All domain enum types — mirroring PostgreSQL ENUMs from 001_initial_schema.sql.
"""

from enum import StrEnum


# ── Identity & Access ──────────────────────────────────────────────────────
class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    ARCHIVED = "archived"


# ── Competition Structure ──────────────────────────────────────────────────
class CompetitionStatus(StrEnum):
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class InviteType(StrEnum):
    CODE = "code"
    LINK = "link"


class InviteStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"
    EXHAUSTED = "exhausted"


class SeasonStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CycleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ── Membership & Gameplay ──────────────────────────────────────────────────
class MembershipStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    REMOVED = "removed"
    ARCHIVED = "archived"


class ProtectionType(StrEnum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


# ── Scoring & Ledger ──────────────────────────────────────────────────────
class LedgerEntryType(StrEnum):
    INITIAL_BALANCE = "initial_balance"
    QUESTION_REWARD = "question_reward"
    DISTRIBUTION = "distribution"
    ATTACK_REWARD = "attack_reward"
    ATTACK_PENALTY = "attack_penalty"
    ITEM_PURCHASE = "item_purchase"
    COMPENSATION = "compensation"
    BANKRUPTCY_RECOVERY = "bankruptcy_recovery"
    SYSTEM_REWARD = "system_reward"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    BOX_RESULT = "box_result"
    # ── Minigame entries ──
    MINIGAME_BUY_IN = "minigame_buy_in"
    MINIGAME_PAYOUT = "minigame_payout"
    MINIGAME_FORFEIT = "minigame_forfeit"
    MINIGAME_REFUND = "minigame_refund"
    MINIGAME_CANCEL_PENALTY = "minigame_cancel_penalty"


class LedgerDirection(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


# ── Attack & Protection ───────────────────────────────────────────────────
class AttackOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BankruptcyState(StrEnum):
    ACTIVE = "active"
    RECOVERING = "recovering"
    CLEARED = "cleared"


# ── Store / Items / Rewards ───────────────────────────────────────────────
class ItemRarity(StrEnum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class ItemStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class ItemUsageType(StrEnum):
    CONSUMABLE = "consumable"
    NON_CONSUMABLE = "non_consumable"
    TIME_LIMITED = "time_limited"
    PERSISTENT = "persistent"


class ItemAcquisitionType(StrEnum):
    PURCHASE = "purchase"
    REWARD = "reward"
    DISTRIBUTION = "distribution"
    ADMIN_GRANT = "admin_grant"
    BOX = "box"


class EffectType(StrEnum):
    RATIO_MODIFIER = "ratio_modifier"
    FIXED_BONUS = "fixed_bonus"
    LOSS_REDUCTION = "loss_reduction"
    ACTION_PREVENTION = "action_prevention"
    STATE_CHANGE = "state_change"
    GRANT_ITEM = "grant_item"
    GRANT_BOX = "grant_box"
    MODIFY_DISTRIBUTION = "modify_distribution"
    ALLOW_ALIAS_CHANGE = "allow_alias_change"
    NEGATIVE_EFFECT = "negative_effect"
    TIME_LIMITED_EFFECT = "time_limited_effect"
    CYCLE_EFFECT = "cycle_effect"
    SEASON_EFFECT = "season_effect"


class ListingStatus(StrEnum):
    ACTIVE = "active"
    HIDDEN = "hidden"
    EXPIRED = "expired"
    SOLD_OUT = "sold_out"


class OwnedItemStatus(StrEnum):
    AVAILABLE = "available"
    ACTIVATED = "activated"
    PENDING = "pending"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class RewardType(StrEnum):
    POINTS = "points"
    ITEM = "item"
    BOX = "box"
    BUNDLE = "bundle"


class RewardGrantStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    OPENED = "opened"
    EXPIRED = "expired"


class DistributionType(StrEnum):
    POINTS = "points"
    ITEMS = "items"
    BOXES = "boxes"
    MIXED = "mixed"


class DistributionTarget(StrEnum):
    ALL_PARTICIPANTS = "all_participants"
    SPECIFIC = "specific"
    CONDITIONAL = "conditional"
    GROUP = "group"


class DistributionStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Questions & Quiz ──────────────────────────────────────────────────────
class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"


class QuestionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class QuestionDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SessionType(StrEnum):
    LIVE = "live"
    TIMED_WINDOW = "timed_window"


class SessionStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AnswerEvalStatus(StrEnum):
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    TIMED_OUT = "timed_out"


# ── Notifications ─────────────────────────────────────────────────────────
class NotificationType(StrEnum):
    ACCOUNT_CREATED = "account_created"
    COMPETITION_JOINED = "competition_joined"
    REGISTRATION_OPENED = "registration_opened"
    REGISTRATION_CLOSED = "registration_closed"
    CYCLE_STARTED = "cycle_started"
    CYCLE_ENDED = "cycle_ended"
    QUIZ_OPENED = "quiz_opened"
    ATTACK_RECEIVED = "attack_received"
    ATTACK_SUCCESS = "attack_success"
    ATTACK_FAILURE = "attack_failure"
    PROTECTION_ACTIVATED = "protection_activated"
    BANKRUPTCY_TRIGGERED = "bankruptcy_triggered"
    BANKRUPTCY_ENDED = "bankruptcy_ended"
    ITEM_PURCHASED = "item_purchased"
    ITEM_RECEIVED = "item_received"
    BOX_RECEIVED = "box_received"
    BOX_OPENED = "box_opened"
    DISTRIBUTION_RECEIVED = "distribution_received"
    ADMIN_CHANGE = "admin_change"
    ADMIN_ALERT = "admin_alert"
    GENERAL = "general"


class NotificationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ── Audit ─────────────────────────────────────────────────────────────────
class AuditActorType(StrEnum):
    SYSTEM = "system"
    ADMIN = "admin"
    PARTICIPANT = "participant"


# ── Settings ──────────────────────────────────────────────────────────────
class SettingScope(StrEnum):
    GLOBAL = "global"
    COMPETITION = "competition"
    SEASON = "season"
    CYCLE = "cycle"


class SettingDataType(StrEnum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    STRING = "string"
    JSON = "json"


# ── Media & Import/Export ─────────────────────────────────────────────────
class MediaStorageType(StrEnum):
    LOCAL = "local"
    EXTERNAL_URL = "external_url"
    CLOUD = "cloud"


class MediaContentType(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    OTHER = "other"


class ImportStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    PREVIEW = "preview"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportType(StrEnum):
    QUESTIONS = "questions"
    PARTICIPANTS = "participants"
    OTHER = "other"


class ExportStatus(StrEnum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


# ── Minigame Engine ──────────────────────────────────────────────────────

class MinigameSessionPhase(StrEnum):
    CREATED = "created"
    WAITING = "waiting"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    OVERTIME = "overtime"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"


class MinigameMatchType(StrEnum):
    CHALLENGE = "challenge"
    QUEUE = "queue"


class MinigameSettlementState(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    RECONCILED = "reconciled"


class MinigameTypeStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class MinigameHeroVariant(StrEnum):
    DUEL = "duel"
    ARENA = "arena"
    SOLO = "solo"
    PARTY = "party"
    TOURNAMENT = "tournament"


class MinigameCardVariant(StrEnum):
    STANDARD = "standard"
    FEATURED = "featured"
    COMPACT = "compact"
    COMING_SOON_TEASER = "coming_soon_teaser"


class MinigameCatalogAvailability(StrEnum):
    ACTIVE = "active"
    COMING_SOON = "coming_soon"
    HIDDEN = "hidden"
    MAINTENANCE = "maintenance"
