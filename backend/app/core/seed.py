"""
One-shot idempotent seeder.

Creates minimal real DB records for the game to function:
  - 1 system Account (to own seeded records)
  - 1 active Competition
  - 1 active Season + Cycle
  - 1 CompetitionInvite (code: "WAR2026")
  - 4 store items with listings
  - Game settings (attack, quiz, store, scoring defaults)
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.enums import (
    AccountStatus,
    CompetitionStatus,
    CycleStatus,
    InviteStatus,
    InviteType,
    ItemRarity,
    ItemStatus,
    ItemUsageType,
    ListingStatus,
    QuestionDifficulty,
    QuestionStatus,
    QuestionType,
    SeasonStatus,
    SettingDataType,
    SettingScope,
    SessionStatus,
    SessionType,
)
from app.modules.auth.models import Account
from app.modules.competitions.models import Competition, CompetitionInvite, Cycle, Season
from app.modules.quiz.models import Question, QuestionGroup, QuizSession, SessionQuestion
from app.modules.settings.models import SettingDefinition, SettingValue
from app.modules.store.models import ItemDefinition, StoreListing

# Stable UUIDs for idempotent re-runs
SEED_SYSTEM_ACCOUNT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
SEED_ADMIN_ACCOUNT_ID = uuid.UUID("00000000-0000-0000-0000-000000000098")
SEED_COMPETITION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SEED_SEASON_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
SEED_CYCLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

# Store item UUIDs
ITEM_LETTER_BOMB_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
ITEM_SHIELD_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
ITEM_MAGIC_WAND_ID = uuid.UUID("00000000-0000-0000-0000-000000000012")
ITEM_HERO_SWORD_ID = uuid.UUID("00000000-0000-0000-0000-000000000013")

# Quiz UUIDs
QUIZ_GROUP_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
QUIZ_SESSION_ID = uuid.UUID("00000000-0000-0000-0000-000000000021")
QUIZ_Q1_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
QUIZ_Q2_ID = uuid.UUID("00000000-0000-0000-0000-000000000031")
QUIZ_Q3_ID = uuid.UUID("00000000-0000-0000-0000-000000000032")
QUIZ_Q4_ID = uuid.UUID("00000000-0000-0000-0000-000000000033")
QUIZ_Q5_ID = uuid.UUID("00000000-0000-0000-0000-000000000034")

INVITE_CODE = "WAR2026"


async def seed(session: AsyncSession) -> None:
    """Run all seed operations. Safe to call on every startup."""
    await _seed_system_account(session)
    await _seed_admin_account(session)
    await _seed_competition(session)
    await _seed_store_items(session)
    await _seed_quiz(session)
    await _seed_settings(session)


async def _seed_system_account(session: AsyncSession) -> None:
    existing = await session.get(Account, SEED_SYSTEM_ACCOUNT_ID)
    if existing:
        return
    account = Account(
        id=SEED_SYSTEM_ACCOUNT_ID,
        username="_system",
        real_name="النظام",
        password_hash=hash_password("system-not-for-login"),
        status=AccountStatus.ACTIVE,
    )
    session.add(account)
    await session.commit()


async def _seed_admin_account(session: AsyncSession) -> None:
    existing = await session.get(Account, SEED_ADMIN_ACCOUNT_ID)
    if existing:
        # Ensure admin + owner flags are set even on re-runs
        changed = False
        if not existing.is_admin:
            existing.is_admin = True
            changed = True
        if not existing.is_owner:
            existing.is_owner = True
            changed = True
        if changed:
            await session.commit()
        return
    account = Account(
        id=SEED_ADMIN_ACCOUNT_ID,
        username="admin",
        real_name="المشرف العام",
        password_hash=hash_password("Admin1234!"),
        status=AccountStatus.ACTIVE,
        is_admin=True,
        is_owner=True,
    )
    session.add(account)
    await session.commit()


async def _seed_competition(session: AsyncSession) -> None:
    existing = await session.get(Competition, SEED_COMPETITION_ID)
    if existing:
        return

    comp = Competition(
        id=SEED_COMPETITION_ID,
        name="موسم حرب الأسماء الأول",
        description="المنافسة الأولى — اكشف الأقنعة واربح النقاط!",
        status=CompetitionStatus.ACTIVE,
        registration_open=True,
        visibility="private",
        created_by=SEED_SYSTEM_ACCOUNT_ID,
    )
    session.add(comp)

    season = Season(
        id=SEED_SEASON_ID,
        competition_id=SEED_COMPETITION_ID,
        name="الموسم الأول",
        order_index=1,
        status=SeasonStatus.ACTIVE,
        starts_at=datetime.utcnow(),
    )
    session.add(season)

    cycle = Cycle(
        id=SEED_CYCLE_ID,
        season_id=SEED_SEASON_ID,
        label="الدورة الأولى",
        order_index=1,
        status=CycleStatus.ACTIVE,
        starts_at=datetime.utcnow(),
    )
    session.add(cycle)

    # Check if invite already exists
    invite_result = await session.execute(
        select(CompetitionInvite).where(CompetitionInvite.code == INVITE_CODE)
    )
    if not invite_result.scalars().first():
        invite = CompetitionInvite(
            competition_id=SEED_COMPETITION_ID,
            invite_type=InviteType.CODE,
            code=INVITE_CODE,
            status=InviteStatus.ACTIVE,
            max_uses=None,
        )
        session.add(invite)

    await session.commit()


async def _seed_store_items(session: AsyncSession) -> None:
    """Seed 4 store items matching the HTML prototype's store page."""
    existing = await session.get(ItemDefinition, ITEM_LETTER_BOMB_ID)
    if existing:
        return

    items = [
        ItemDefinition(
            id=ITEM_LETTER_BOMB_ID,
            name="قنبلة الحروف",
            description="تنفجر في ملف الخصم وتخفي 3 حروف من اسمه.",
            rarity=ItemRarity.RARE,
            status=ItemStatus.ACTIVE,
            category="weapon",
            usage_type=ItemUsageType.CONSUMABLE,
            max_uses=1,
            expires_after_minutes=60,
        ),
        ItemDefinition(
            id=ITEM_SHIELD_ID,
            name="درع الحماية",
            description="درع تكتيكي يمنع الهجمات المباشرة لمدة 3 ساعات.",
            rarity=ItemRarity.COMMON,
            status=ItemStatus.ACTIVE,
            category="defense",
            usage_type=ItemUsageType.TIME_LIMITED,
            max_uses=1,
            expires_after_minutes=180,
        ),
        ItemDefinition(
            id=ITEM_MAGIC_WAND_ID,
            name="عصا السحر",
            description="تنسخ أي عنصر يستخدمه خصمك وتضيفه لجردك.",
            rarity=ItemRarity.LEGENDARY,
            status=ItemStatus.ACTIVE,
            category="special",
            usage_type=ItemUsageType.CONSUMABLE,
            max_uses=1,
        ),
        ItemDefinition(
            id=ITEM_HERO_SWORD_ID,
            name="سيف البطل المطلق",
            description="يدمر درع أي خصم بشكل فوري ويخصم 50% من نقاطه. السلاح النهائي.",
            rarity=ItemRarity.MYTHIC,
            status=ItemStatus.ACTIVE,
            category="weapon",
            usage_type=ItemUsageType.CONSUMABLE,
            max_uses=1,
        ),
    ]
    session.add_all(items)
    await session.flush()

    listings = [
        StoreListing(
            item_definition_id=ITEM_LETTER_BOMB_ID,
            competition_id=SEED_COMPETITION_ID,
            season_id=SEED_SEASON_ID,
            status=ListingStatus.ACTIVE,
            price=1200,
            max_per_participant=3,
        ),
        StoreListing(
            item_definition_id=ITEM_SHIELD_ID,
            competition_id=SEED_COMPETITION_ID,
            season_id=SEED_SEASON_ID,
            status=ListingStatus.ACTIVE,
            price=850,
            max_per_participant=5,
        ),
        StoreListing(
            item_definition_id=ITEM_MAGIC_WAND_ID,
            competition_id=SEED_COMPETITION_ID,
            season_id=SEED_SEASON_ID,
            status=ListingStatus.ACTIVE,
            price=4500,
            max_per_participant=1,
            total_stock=5,
        ),
        StoreListing(
            item_definition_id=ITEM_HERO_SWORD_ID,
            competition_id=SEED_COMPETITION_ID,
            season_id=SEED_SEASON_ID,
            status=ListingStatus.ACTIVE,
            price=15000,
            max_per_participant=1,
            total_stock=1,
        ),
    ]
    session.add_all(listings)
    await session.commit()


async def _seed_quiz(session: AsyncSession) -> None:
    """Seed a question group, 5 questions, and an open quiz session."""
    existing = await session.get(QuestionGroup, QUIZ_GROUP_ID)
    if existing:
        return

    group = QuestionGroup(
        id=QUIZ_GROUP_ID,
        title="أسئلة الدورة الأولى",
        description="مجموعة أسئلة ثقافية عامة للموسم الأول",
        status=QuestionStatus.ACTIVE,
        competition_id=SEED_COMPETITION_ID,
    )
    session.add(group)
    await session.flush()

    questions_data = [
        {
            "id": QUIZ_Q1_ID,
            "prompt": "ما هو الاسم التاريخي الذي كان يطلق على المنطقة التي نشأت فيها أول حضارة زراعية في العالم؟",
            "options": {"choices": ["وادي الرافدين", "الهلال الخصيب", "بلاد فارس", "ضفاف النيل"], "correct": "الهلال الخصيب"},
            "correct_answer": {"answer": "الهلال الخصيب"},
            "score_value": 200,
            "difficulty": QuestionDifficulty.MEDIUM,
        },
        {
            "id": QUIZ_Q2_ID,
            "prompt": "كم عدد ألوان قوس قزح الأساسية؟",
            "options": {"choices": ["5", "6", "7", "8"], "correct": "7"},
            "correct_answer": {"answer": "7"},
            "score_value": 100,
            "difficulty": QuestionDifficulty.EASY,
        },
        {
            "id": QUIZ_Q3_ID,
            "prompt": "ما هي أكبر صحراء في العالم من حيث المساحة؟",
            "options": {"choices": ["الصحراء الكبرى", "صحراء القطب الجنوبي", "صحراء الربع الخالي", "صحراء غوبي"], "correct": "صحراء القطب الجنوبي"},
            "correct_answer": {"answer": "صحراء القطب الجنوبي"},
            "score_value": 300,
            "difficulty": QuestionDifficulty.HARD,
        },
        {
            "id": QUIZ_Q4_ID,
            "prompt": "ما هي العملة الرسمية لدولة اليابان؟",
            "options": {"choices": ["اليوان", "الين", "الوون", "الروبية"], "correct": "الين"},
            "correct_answer": {"answer": "الين"},
            "score_value": 100,
            "difficulty": QuestionDifficulty.EASY,
        },
        {
            "id": QUIZ_Q5_ID,
            "prompt": "أي كوكب يُعرف باسم الكوكب الأحمر؟",
            "options": {"choices": ["الزهرة", "المشتري", "المريخ", "زحل"], "correct": "المريخ"},
            "correct_answer": {"answer": "المريخ"},
            "score_value": 150,
            "difficulty": QuestionDifficulty.EASY,
        },
    ]

    for qd in questions_data:
        q = Question(
            id=qd["id"],
            group_id=QUIZ_GROUP_ID,
            question_type=QuestionType.MULTIPLE_CHOICE,
            prompt=qd["prompt"],
            options=qd["options"],
            correct_answer=qd["correct_answer"],
            score_value=qd["score_value"],
            difficulty=qd["difficulty"],
            status=QuestionStatus.ACTIVE,
        )
        session.add(q)
    await session.flush()

    # Create quiz session
    quiz_session = QuizSession(
        id=QUIZ_SESSION_ID,
        competition_id=SEED_COMPETITION_ID,
        season_id=SEED_SEASON_ID,
        cycle_id=SEED_CYCLE_ID,
        session_type=SessionType.TIMED_WINDOW,
        title="الجلسة الأولى — أسئلة ثقافية",
        status=SessionStatus.OPEN,
        starts_at=datetime.utcnow(),
        answer_duration_seconds=30,
        source_group_id=QUIZ_GROUP_ID,
        created_by=SEED_SYSTEM_ACCOUNT_ID,
    )
    session.add(quiz_session)
    await session.flush()

    # Link questions to session
    for i, qd in enumerate(questions_data, start=1):
        sq = SessionQuestion(
            session_id=QUIZ_SESSION_ID,
            question_id=qd["id"],
            delivery_order=i,
            effective_score_value=qd["score_value"],
            effective_prompt_snapshot=qd["prompt"],
            effective_options_snapshot=qd["options"],
        )
        session.add(sq)

    await session.commit()


# Stable UUIDs for settings
SETTING_IDS = {
    "attack_base_reward": uuid.UUID("00000000-0000-0000-0000-000000000040"),
    "attack_decay_factor": uuid.UUID("00000000-0000-0000-0000-000000000041"),
    "attack_base_penalty": uuid.UUID("00000000-0000-0000-0000-000000000042"),
    "attack_max_per_cycle": uuid.UUID("00000000-0000-0000-0000-000000000043"),
    "score_initial_balance": uuid.UUID("00000000-0000-0000-0000-000000000044"),
    "score_bankruptcy_threshold": uuid.UUID("00000000-0000-0000-0000-000000000045"),
    "quiz_default_duration": uuid.UUID("00000000-0000-0000-0000-000000000046"),
    "store_max_inventory": uuid.UUID("00000000-0000-0000-0000-000000000047"),
    "protection_full_attack_count": uuid.UUID("00000000-0000-0000-0000-000000000048"),
    "attack_enabled": uuid.UUID("00000000-0000-0000-0000-000000000049"),
    # New settings from BRD section 5.2
    "attack_self_penalty_on_fail": uuid.UUID("00000000-0000-0000-0000-000000000050"),
    "attack_cooldown_seconds": uuid.UUID("00000000-0000-0000-0000-000000000051"),
    "protection_partial_reduction": uuid.UUID("00000000-0000-0000-0000-000000000052"),
    "protection_duration_hours": uuid.UUID("00000000-0000-0000-0000-000000000053"),
    "bankruptcy_recovery_balance": uuid.UUID("00000000-0000-0000-0000-000000000054"),
    "quiz_max_sessions_per_cycle": uuid.UUID("00000000-0000-0000-0000-000000000055"),
    "store_purchase_cooldown_minutes": uuid.UUID("00000000-0000-0000-0000-000000000056"),
    "identity_reveal_on_bankruptcy": uuid.UUID("00000000-0000-0000-0000-000000000057"),
    "season_auto_advance_cycles": uuid.UUID("00000000-0000-0000-0000-000000000058"),
    # Platform settings
    "platform_name": uuid.UUID("00000000-0000-0000-0000-000000000060"),
    "platform_description": uuid.UUID("00000000-0000-0000-0000-000000000061"),
    "maintenance_mode": uuid.UUID("00000000-0000-0000-0000-000000000062"),
    "maintenance_message": uuid.UUID("00000000-0000-0000-0000-000000000063"),
    "registration_enabled": uuid.UUID("00000000-0000-0000-0000-000000000064"),
    "google_analytics_id": uuid.UUID("00000000-0000-0000-0000-000000000065"),
    "platform_logo_url": uuid.UUID("00000000-0000-0000-0000-000000000066"),
    "google_ads_id": uuid.UUID("00000000-0000-0000-0000-000000000067"),
    "ad_consent_required": uuid.UUID("00000000-0000-0000-0000-000000000068"),
    "og_image_url": uuid.UUID("00000000-0000-0000-0000-000000000069"),
}


async def _seed_settings(session: AsyncSession) -> None:
    """Seed game setting definitions with default values. Adds missing settings on re-run."""
    settings_data = [
        {
            "id": SETTING_IDS["attack_base_reward"],
            "key": "attack_base_reward",
            "category": "attack",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 500},
            "allowed_values": {"min": 0, "max": 100000},
            "description": "المكافأة الأساسية للهجوم الناجح",
        },
        {
            "id": SETTING_IDS["attack_decay_factor"],
            "key": "attack_decay_factor",
            "category": "attack",
            "data_type": SettingDataType.DECIMAL,
            "default_value": {"v": 0.8},
            "allowed_values": {"min": 0, "max": 1},
            "description": "معامل الانحلال للمكافأة (0-1)",
        },
        {
            "id": SETTING_IDS["attack_base_penalty"],
            "key": "attack_base_penalty",
            "category": "attack",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 100},
            "allowed_values": {"min": 0, "max": 100000},
            "description": "الخصم الأساسي عند فشل الهجوم",
        },
        {
            "id": SETTING_IDS["attack_max_per_cycle"],
            "key": "attack_max_per_cycle",
            "category": "attack",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 3},
            "allowed_values": {"min": 1, "max": 100},
            "description": "أقصى عدد هجمات ناجحة على لاعب في الدورة الواحدة",
        },
        {
            "id": SETTING_IDS["score_initial_balance"],
            "key": "score_initial_balance",
            "category": "score",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 1000},
            "allowed_values": {"min": 0, "max": 1000000},
            "description": "الرصيد الأولي لكل لاعب عند الانضمام",
        },
        {
            "id": SETTING_IDS["score_bankruptcy_threshold"],
            "key": "score_bankruptcy_threshold",
            "category": "score",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 0},
            "allowed_values": {"min": 0, "max": 1000000},
            "description": "حد الإفلاس (إذا انخفض الرصيد لهذا المبلغ أو أقل)",
        },
        {
            "id": SETTING_IDS["quiz_default_duration"],
            "key": "quiz_default_duration",
            "category": "quiz",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 30},
            "allowed_values": {"min": 5, "max": 300},
            "description": "المدة الافتراضية للإجابة على السؤال (ثواني)",
        },
        {
            "id": SETTING_IDS["store_max_inventory"],
            "key": "store_max_inventory",
            "category": "store",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 10},
            "allowed_values": {"min": 1, "max": 100},
            "description": "الحد الأقصى لعدد العناصر في مخزن اللاعب",
        },
        {
            "id": SETTING_IDS["protection_full_attack_count"],
            "key": "protection_full_attack_count",
            "category": "protection",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 3},
            "allowed_values": {"min": 1, "max": 50},
            "description": "عدد الهجمات الناجحة المطلوبة للحماية الكاملة",
        },
        {
            "id": SETTING_IDS["attack_enabled"],
            "key": "attack_enabled",
            "category": "attack",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": False},
            "description": "هل الهجمات مفعّلة (يبدأ معطلاً — يفعّله المشرف)",
        },
        # ── New settings from Admin Config BRD ──
        {
            "id": SETTING_IDS["attack_self_penalty_on_fail"],
            "key": "attack_self_penalty_on_fail",
            "category": "attack",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "هل يخسر المهاجم نقاطاً عند فشل الهجوم؟",
        },
        {
            "id": SETTING_IDS["attack_cooldown_seconds"],
            "key": "attack_cooldown_seconds",
            "category": "attack",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 5},
            "allowed_values": {"min": 0, "max": 3600},
            "description": "فترة الانتظار بين الهجمات (ثواني)",
        },
        {
            "id": SETTING_IDS["protection_partial_reduction"],
            "key": "protection_partial_reduction",
            "category": "protection",
            "data_type": SettingDataType.DECIMAL,
            "default_value": {"v": 0.5},
            "allowed_values": {"min": 0, "max": 1},
            "description": "نسبة تقليل الخسارة عند الحماية الجزئية",
        },
        {
            "id": SETTING_IDS["protection_duration_hours"],
            "key": "protection_duration_hours",
            "category": "protection",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 24},
            "allowed_values": {"min": 1, "max": 168},
            "description": "مدة الحماية الكاملة (ساعات)",
        },
        {
            "id": SETTING_IDS["bankruptcy_recovery_balance"],
            "key": "bankruptcy_recovery_balance",
            "category": "score",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 500},
            "allowed_values": {"min": 0, "max": 1000000},
            "description": "الرصيد الممنوح عند رفع الإفلاس في بداية الدورة",
        },
        {
            "id": SETTING_IDS["quiz_max_sessions_per_cycle"],
            "key": "quiz_max_sessions_per_cycle",
            "category": "quiz",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 5},
            "allowed_values": {"min": 1, "max": 50},
            "description": "أقصى عدد جلسات أسئلة لكل دورة",
        },
        {
            "id": SETTING_IDS["store_purchase_cooldown_minutes"],
            "key": "store_purchase_cooldown_minutes",
            "category": "store",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 0},
            "allowed_values": {"min": 0, "max": 1440},
            "description": "فترة الانتظار بين عمليات الشراء (دقائق) — 0 = بدون انتظار",
        },
        {
            "id": SETTING_IDS["identity_reveal_on_bankruptcy"],
            "key": "identity_reveal_on_bankruptcy",
            "category": "identity",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "هل يُكشف الاسم الحقيقي للمفلس؟",
        },
        {
            "id": SETTING_IDS["season_auto_advance_cycles"],
            "key": "season_auto_advance_cycles",
            "category": "season",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": False},
            "description": "هل تبدأ الدورة التالية تلقائياً عند انتهاء الحالية؟",
        },
        # ── Platform settings ──
        {
            "id": SETTING_IDS["platform_name"],
            "key": "platform_name",
            "category": "branding",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "حرب الأسماء"},
            "description": "اسم المنصة",
        },
        {
            "id": SETTING_IDS["platform_description"],
            "key": "platform_description",
            "category": "branding",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "أقوى لعبة تنافسية عربية"},
            "description": "وصف المنصة (SEO)",
        },
        {
            "id": SETTING_IDS["maintenance_mode"],
            "key": "maintenance_mode",
            "category": "platform",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": False},
            "description": "تفعيل وضع الصيانة",
        },
        {
            "id": SETTING_IDS["maintenance_message"],
            "key": "maintenance_message",
            "category": "platform",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "المنصة قيد الصيانة — نعود قريباً"},
            "description": "رسالة الصيانة",
        },
        {
            "id": SETTING_IDS["registration_enabled"],
            "key": "registration_enabled",
            "category": "platform",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "السماح بإنشاء حسابات جديدة",
        },
        {
            "id": SETTING_IDS["google_analytics_id"],
            "key": "google_analytics_id",
            "category": "analytics",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": ""},
            "description": "معرّف Google Analytics 4 (مثال: G-XXXXXXXXX)",
        },
        {
            "id": SETTING_IDS["platform_logo_url"],
            "key": "platform_logo_url",
            "category": "branding",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "/assets/logo.png"},
            "description": "رابط شعار المنصة",
        },
        {
            "id": SETTING_IDS["google_ads_id"],
            "key": "google_ads_id",
            "category": "analytics",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": ""},
            "description": "معرّف Google Ads (مثال: AW-XXXXXXXXX)",
        },
        {
            "id": SETTING_IDS["ad_consent_required"],
            "key": "ad_consent_required",
            "category": "privacy",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "إظهار بانر الموافقة على الإعلانات/ملفات تعريف الارتباط",
        },
        {
            "id": SETTING_IDS["og_image_url"],
            "key": "og_image_url",
            "category": "seo",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "/assets/og-image.png"},
            "description": "صورة Open Graph الافتراضية للمشاركة",
        },
    ]

    added = 0
    for sd in settings_data:
        existing = await session.get(SettingDefinition, sd["id"])
        if existing:
            # Patch allowed_values on existing definitions if missing
            new_av = sd.get("allowed_values")
            if new_av and existing.allowed_values != new_av:
                existing.allowed_values = new_av
            continue
        defn = SettingDefinition(**sd)
        session.add(defn)
        await session.flush()

        # Also seed global value for this new setting
        sv = SettingValue(
            setting_definition_id=sd["id"],
            scope=SettingScope.GLOBAL,
            value=sd["default_value"],
        )
        session.add(sv)
        added += 1

    await session.commit()
