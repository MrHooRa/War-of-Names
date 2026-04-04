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
from app.core.utils import now_riyadh_naive
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
    await _seed_minigame_types(session)
    await _seed_mutaraha_words(session)
    await _seed_minigame_catalog_configs(session)  # NEW


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
        starts_at=now_riyadh_naive(),
    )
    session.add(season)

    cycle = Cycle(
        id=SEED_CYCLE_ID,
        season_id=SEED_SEASON_ID,
        label="الدورة الأولى",
        order_index=1,
        status=CycleStatus.ACTIVE,
        starts_at=now_riyadh_naive(),
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
        starts_at=now_riyadh_naive(),
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
    "protection_partial_same_attacker_enabled": uuid.UUID("00000000-0000-0000-0000-000000000059"),
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
    # Minigame engine settings
    "minigame_enabled": uuid.UUID("00000000-0000-0000-0000-000000000070"),
    "minigame_buy_in": uuid.UUID("00000000-0000-0000-0000-000000000071"),
    "minigame_daily_limit": uuid.UUID("00000000-0000-0000-0000-000000000072"),
    "minigame_same_opponent_limit": uuid.UUID("00000000-0000-0000-0000-000000000073"),
    "minigame_turn_duration_sec": uuid.UUID("00000000-0000-0000-0000-000000000074"),
    "minigame_overtime_enabled": uuid.UUID("00000000-0000-0000-0000-000000000075"),
    "minigame_grace_timer_sec": uuid.UUID("00000000-0000-0000-0000-000000000076"),
    "minigame_kill_switch": uuid.UUID("00000000-0000-0000-0000-000000000077"),
    # Mutaraha overrides / gameplay settings
    "mutaraha_enabled": uuid.UUID("00000000-0000-0000-0000-000000000078"),
    "mutaraha_buy_in": uuid.UUID("00000000-0000-0000-0000-000000000079"),
    "mutaraha_daily_limit": uuid.UUID("00000000-0000-0000-0000-000000000080"),
    "mutaraha_same_opponent_limit": uuid.UUID("00000000-0000-0000-0000-000000000081"),
    "mutaraha_turn_duration_sec": uuid.UUID("00000000-0000-0000-0000-000000000082"),
    "mutaraha_selection_duration_sec": uuid.UUID("00000000-0000-0000-0000-000000000083"),
    "mutaraha_overtime_enabled": uuid.UUID("00000000-0000-0000-0000-000000000084"),
    "mutaraha_overtime_turns": uuid.UUID("00000000-0000-0000-0000-000000000085"),
    "mutaraha_overtime_turn_sec": uuid.UUID("00000000-0000-0000-0000-000000000086"),
    "mutaraha_overtime_cost_multiplier": uuid.UUID("00000000-0000-0000-0000-000000000087"),
    "mutaraha_redraw_cost": uuid.UUID("00000000-0000-0000-0000-000000000088"),
    "mutaraha_grace_timer_sec": uuid.UUID("00000000-0000-0000-0000-000000000089"),
    "mutaraha_queue_timeout_sec": uuid.UUID("00000000-0000-0000-0000-000000000090"),
    "mutaraha_challenge_timeout_sec": uuid.UUID("00000000-0000-0000-0000-000000000091"),
    "mutaraha_cost_letter_check": uuid.UUID("00000000-0000-0000-0000-000000000092"),
    "mutaraha_cost_word_length": uuid.UUID("00000000-0000-0000-0000-000000000093"),
    "mutaraha_cost_letter_eliminate": uuid.UUID("00000000-0000-0000-0000-000000000094"),
    "mutaraha_cost_first_letter": uuid.UUID("00000000-0000-0000-0000-000000000095"),
    "mutaraha_cost_narrow_down": uuid.UUID("00000000-0000-0000-0000-000000000096"),
    "mutaraha_cost_wrong_guess": uuid.UUID("00000000-0000-0000-0000-000000000097"),
    "mutaraha_categories_enabled": uuid.UUID("00000000-0000-0000-0000-000000000098"),
    "mutaraha_disabled_words": uuid.UUID("00000000-0000-0000-0000-000000000099"),
    "mutaraha_words_per_draw": uuid.UUID("00000000-0000-0000-0000-000000000100"),
    "mutaraha_words_to_select": uuid.UUID("00000000-0000-0000-0000-000000000101"),
    "mutaraha_recent_match_word_limit": uuid.UUID("00000000-0000-0000-0000-000000000102"),
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
        {
            "id": SETTING_IDS["protection_partial_same_attacker_enabled"],
            "key": "protection_partial_same_attacker_enabled",
            "category": "protection",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "هل يكتسب الهدف حماية جزئية من نفس المهاجم بعد أول هجوم ناجح في الدورة؟",
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
        # ── Minigame Engine ──
        {
            "id": SETTING_IDS["minigame_enabled"],
            "key": "minigame_enabled",
            "category": "minigame",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": False},
            "description": "تفعيل الألعاب المصغرة في المسابقة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_buy_in"],
            "key": "minigame_buy_in",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 500},
            "allowed_values": {"min": 0, "max": 50000},
            "description": "مبلغ الدخول للعبة المصغرة (نقاط)",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_daily_limit"],
            "key": "minigame_daily_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 2},
            "allowed_values": {"min": 1, "max": 50},
            "description": "الحد الأقصى لعدد المباريات يومياً لكل لاعب",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_same_opponent_limit"],
            "key": "minigame_same_opponent_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 1},
            "allowed_values": {"min": 1, "max": 10},
            "description": "الحد الأقصى لمبارزة نفس الخصم في الدورة الواحدة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_turn_duration_sec"],
            "key": "minigame_turn_duration_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 30},
            "allowed_values": {"min": 10, "max": 120},
            "description": "مدة الدور بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_overtime_enabled"],
            "key": "minigame_overtime_enabled",
            "category": "minigame",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "تفعيل الوقت الإضافي عند التعادل",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_grace_timer_sec"],
            "key": "minigame_grace_timer_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 60},
            "allowed_values": {"min": 15, "max": 300},
            "description": "مهلة إعادة الاتصال بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["minigame_kill_switch"],
            "key": "minigame_kill_switch",
            "category": "minigame",
            "data_type": SettingDataType.STRING,
            "default_value": {"v": "off"},
            "allowed_values": {"options": ["off", "soft", "hard", "emergency"]},
            "description": "مفتاح إيقاف الألعاب المصغرة (off/soft/hard/emergency)",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_enabled"],
            "key": "mutaraha_enabled",
            "category": "minigame",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": False},
            "description": "تفعيل لعبة مطارحة في المسابقة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_buy_in"],
            "key": "mutaraha_buy_in",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 500},
            "allowed_values": {"min": 0, "max": 50000},
            "description": "مبلغ الدخول الخاص بلعبة مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_daily_limit"],
            "key": "mutaraha_daily_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 2},
            "allowed_values": {"min": 1, "max": 50},
            "description": "الحد اليومي لمباريات مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_same_opponent_limit"],
            "key": "mutaraha_same_opponent_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 1},
            "allowed_values": {"min": 1, "max": 10},
            "description": "الحد الأقصى لمبارزة نفس الخصم في مطارحة لكل دورة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_turn_duration_sec"],
            "key": "mutaraha_turn_duration_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 30},
            "allowed_values": {"min": 10, "max": 120},
            "description": "مدة الدور في مطارحة بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_selection_duration_sec"],
            "key": "mutaraha_selection_duration_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 45},
            "allowed_values": {"min": 10, "max": 180},
            "description": "مهلة اختيار الكلمات في مطارحة بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_overtime_enabled"],
            "key": "mutaraha_overtime_enabled",
            "category": "minigame",
            "data_type": SettingDataType.BOOLEAN,
            "default_value": {"v": True},
            "description": "تفعيل الوقت الإضافي في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_overtime_turns"],
            "key": "mutaraha_overtime_turns",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 3},
            "allowed_values": {"min": 1, "max": 10},
            "description": "عدد الأدوار الإضافية لكل لاعب في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_overtime_turn_sec"],
            "key": "mutaraha_overtime_turn_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 20},
            "allowed_values": {"min": 5, "max": 60},
            "description": "مدة الدور الإضافي في مطارحة بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_overtime_cost_multiplier"],
            "key": "mutaraha_overtime_cost_multiplier",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 2},
            "allowed_values": {"min": 1, "max": 10},
            "description": "مضاعف تكلفة الأدوات في الوقت الإضافي",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_redraw_cost"],
            "key": "mutaraha_redraw_cost",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 20},
            "allowed_values": {"min": 0, "max": 500},
            "description": "تكلفة إعادة سحب الكلمات في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_grace_timer_sec"],
            "key": "mutaraha_grace_timer_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 60},
            "allowed_values": {"min": 15, "max": 300},
            "description": "مهلة إعادة الاتصال الخاصة بمطارحة بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_queue_timeout_sec"],
            "key": "mutaraha_queue_timeout_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 120},
            "allowed_values": {"min": 10, "max": 900},
            "description": "أقصى انتظار في طابور مطارحة بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_challenge_timeout_sec"],
            "key": "mutaraha_challenge_timeout_sec",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 60},
            "allowed_values": {"min": 10, "max": 300},
            "description": "مهلة قبول تحدي مطارحة بالثواني",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_cost_letter_check"],
            "key": "mutaraha_cost_letter_check",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 20},
            "allowed_values": {"min": 0, "max": 500},
            "description": "تكلفة أداة كشف الحرف في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_cost_word_length"],
            "key": "mutaraha_cost_word_length",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 20},
            "allowed_values": {"min": 0, "max": 500},
            "description": "تكلفة أداة طول الكلمة في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_cost_letter_eliminate"],
            "key": "mutaraha_cost_letter_eliminate",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 40},
            "allowed_values": {"min": 0, "max": 500},
            "description": "تكلفة أداة حذف الحروف في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_cost_first_letter"],
            "key": "mutaraha_cost_first_letter",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 50},
            "allowed_values": {"min": 0, "max": 500},
            "description": "تكلفة أداة أول حرف في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_cost_narrow_down"],
            "key": "mutaraha_cost_narrow_down",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 60},
            "allowed_values": {"min": 0, "max": 500},
            "description": "تكلفة أداة التضييق في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_cost_wrong_guess"],
            "key": "mutaraha_cost_wrong_guess",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 50},
            "allowed_values": {"min": 0, "max": 500},
            "description": "عقوبة التخمين الخاطئ في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_categories_enabled"],
            "key": "mutaraha_categories_enabled",
            "category": "minigame",
            "data_type": SettingDataType.JSON,
            "default_value": {"v": []},
            "description": "الفئات المفعلة لبنك كلمات مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_disabled_words"],
            "key": "mutaraha_disabled_words",
            "category": "minigame",
            "data_type": SettingDataType.JSON,
            "default_value": {"v": []},
            "description": "معرفات الكلمات المعطلة في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_words_per_draw"],
            "key": "mutaraha_words_per_draw",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 10},
            "allowed_values": {"min": 2, "max": 30},
            "description": "عدد الكلمات المعروضة في كل سحب بمطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_words_to_select"],
            "key": "mutaraha_words_to_select",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 5},
            "allowed_values": {"min": 1, "max": 10},
            "description": "عدد الكلمات التي يختارها اللاعب في مطارحة",
            "is_per_competition": True,
        },
        {
            "id": SETTING_IDS["mutaraha_recent_match_word_limit"],
            "key": "mutaraha_recent_match_word_limit",
            "category": "minigame",
            "data_type": SettingDataType.INTEGER,
            "default_value": {"v": 5},
            "allowed_values": {"min": 1, "max": 20},
            "description": "عدد المباريات الأخيرة التي تُستبعد كلماتها من عروض مطارحة",
            "is_per_competition": True,
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


async def _seed_minigame_types(session: AsyncSession) -> None:
    """Seed minigame type registry with known game types."""
    from app.modules.minigames.models import MinigameType

    types_data = [
        {
            "id": "mutaraha",
            "name": "مطارحة",
            "description": "مبارزة كلمات 1v1 — خمّن كلمات خصمك قبل ما يخمّن كلماتك",
            "min_players": 2,
            "max_players": 2,
            "supports_overtime": True,
        },
    ]

    for td in types_data:
        existing = await session.get(MinigameType, td["id"])
        if existing:
            continue
        session.add(MinigameType(**td))

    await session.commit()

    # Register plugin in the in-memory registry
    from app.modules.minigames.registry import GameTypeRegistry
    from app.modules.minigames.mutaraha.plugin import MutarahaPlugin
    if GameTypeRegistry.get("mutaraha") is None:
        GameTypeRegistry.register(MutarahaPlugin())


async def _seed_minigame_catalog_configs(session: AsyncSession) -> None:
    """Seed presentation metadata for minigame catalog cards.

    Idempotent — uses session.get() by primary key and skips if the row
    already exists. Paired with migration 008_minigame_catalog_configs.sql
    for fresh deployments.
    """
    from app.core.enums import (
        MinigameCardVariant,
        MinigameCatalogAvailability,
        MinigameHeroVariant,
    )
    from app.modules.minigames.catalog_config_model import MinigameCatalogConfig

    configs_data = [
        {
            "game_type": "mutaraha",
            "short_description": "مبارزة كلمات 1v1 — فراسة واستنتاج",
            "icon_token": "lucide:swords",
            "accent_color": "#D84315",
            "hero_variant": MinigameHeroVariant.DUEL,
            "card_variant": MinigameCardVariant.STANDARD,
            "estimated_duration_sec": 300,
            "featured": True,
            "sort_order": 10,
            "availability_mode": MinigameCatalogAvailability.ACTIVE,
            "marketing_label": None,
            "expected_launch_at": None,
        },
    ]

    for cd in configs_data:
        existing = await session.get(MinigameCatalogConfig, cd["game_type"])
        if existing:
            continue
        session.add(MinigameCatalogConfig(**cd))

    await session.commit()


async def _seed_mutaraha_words(session: AsyncSession) -> None:
    """Seed مطارحة word bank with Saudi/Najdi Arabic words."""
    from app.modules.minigames.mutaraha.models import MutarahaWord

    words_data = [
        # ── حيوانات (animals) ──
        ("ضب", "animals", "easy"),
        ("وضيحي", "animals", "medium"),
        ("ثعلب", "animals", "easy"),
        ("ذيب", "animals", "easy"),
        ("صقر", "animals", "easy"),
        ("حبارى", "animals", "medium"),
        ("ورل", "animals", "medium"),
        ("قنفذ", "animals", "easy"),
        ("جربوع", "animals", "medium"),
        ("وبر", "animals", "medium"),
        ("غزال", "animals", "easy"),
        ("نسر", "animals", "easy"),
        ("حمام", "animals", "easy"),
        ("بومة", "animals", "easy"),
        ("ثعبان", "animals", "easy"),
        ("عقرب", "animals", "easy"),
        ("أرنب", "animals", "easy"),
        ("حرباء", "animals", "medium"),
        ("هدهد", "animals", "easy"),
        ("يربوع", "animals", "medium"),
        # ── نباتات (plants) ──
        ("سدر", "plants", "easy"),
        ("أرطى", "plants", "hard"),
        ("عرفج", "plants", "hard"),
        ("طلح", "plants", "medium"),
        ("رمان", "plants", "easy"),
        ("نخلة", "plants", "easy"),
        ("عشر", "plants", "medium"),
        ("حنظل", "plants", "medium"),
        ("سمر", "plants", "medium"),
        ("ريحان", "plants", "easy"),
        ("حبق", "plants", "medium"),
        ("تين", "plants", "easy"),
        ("عنب", "plants", "easy"),
        ("بطيخ", "plants", "easy"),
        ("ليمون", "plants", "easy"),
        ("خزامى", "plants", "medium"),
        ("قرض", "plants", "hard"),
        ("غاف", "plants", "hard"),
        ("سلم", "plants", "medium"),
        ("ضمران", "plants", "hard"),
        # ── مدن سعودية (saudi_cities) ──
        ("الرياض", "saudi_cities", "easy"),
        ("جدة", "saudi_cities", "easy"),
        ("أبها", "saudi_cities", "easy"),
        ("تبوك", "saudi_cities", "easy"),
        ("نجران", "saudi_cities", "medium"),
        ("حائل", "saudi_cities", "easy"),
        ("عنيزة", "saudi_cities", "medium"),
        ("بريدة", "saudi_cities", "medium"),
        ("شقراء", "saudi_cities", "medium"),
        ("الدرعية", "saudi_cities", "medium"),
        ("الخرج", "saudi_cities", "medium"),
        ("الزلفي", "saudi_cities", "hard"),
        ("المجمعة", "saudi_cities", "medium"),
        ("الدوادمي", "saudi_cities", "hard"),
        ("رفحاء", "saudi_cities", "hard"),
        ("ينبع", "saudi_cities", "easy"),
        ("الطائف", "saudi_cities", "easy"),
        ("المدينة", "saudi_cities", "easy"),
        ("مكة", "saudi_cities", "easy"),
        ("الجبيل", "saudi_cities", "medium"),
        # ── مدن عربية (arab_cities) ──
        ("صنعاء", "arab_cities", "easy"),
        ("دمشق", "arab_cities", "easy"),
        ("فاس", "arab_cities", "medium"),
        ("صلالة", "arab_cities", "medium"),
        ("بيروت", "arab_cities", "easy"),
        ("بغداد", "arab_cities", "easy"),
        ("عمان", "arab_cities", "easy"),
        ("تونس", "arab_cities", "easy"),
        ("مسقط", "arab_cities", "easy"),
        ("الدوحة", "arab_cities", "easy"),
        ("المنامة", "arab_cities", "medium"),
        ("طرابلس", "arab_cities", "medium"),
        ("الجزائر", "arab_cities", "easy"),
        ("القاهرة", "arab_cities", "easy"),
        ("الكويت", "arab_cities", "easy"),
        ("مراكش", "arab_cities", "medium"),
        ("أصيلة", "arab_cities", "hard"),
        ("صحار", "arab_cities", "hard"),
        ("حلب", "arab_cities", "easy"),
        ("عدن", "arab_cities", "easy"),
        # ── أكلات (foods) ──
        ("كبسة", "foods", "easy"),
        ("جريش", "foods", "medium"),
        ("مطبق", "foods", "medium"),
        ("مرقوق", "foods", "medium"),
        ("قرصان", "foods", "medium"),
        ("هريسة", "foods", "medium"),
        ("عريكة", "foods", "medium"),
        ("معصوب", "foods", "medium"),
        ("حنيني", "foods", "hard"),
        ("كليجا", "foods", "hard"),
        ("مطازيز", "foods", "hard"),
        ("سليق", "foods", "medium"),
        ("صالونة", "foods", "easy"),
        ("مندي", "foods", "easy"),
        ("حاشي", "foods", "medium"),
        ("ثريد", "foods", "medium"),
        ("دبيازة", "foods", "hard"),
        ("لقيمات", "foods", "easy"),
        ("بسبوسة", "foods", "easy"),
        ("معمول", "foods", "easy"),
        # ── ألقاب (nicknames) ──
        ("الصقر", "nicknames", "easy"),
        ("الفهد", "nicknames", "easy"),
        ("الشهم", "nicknames", "medium"),
        ("الهيبة", "nicknames", "medium"),
        ("الذيب", "nicknames", "easy"),
        ("العقيد", "nicknames", "medium"),
        ("الحربي", "nicknames", "medium"),
        ("الفارس", "nicknames", "easy"),
        ("الشيخ", "nicknames", "easy"),
        ("الأمير", "nicknames", "easy"),
        ("الليث", "nicknames", "medium"),
        ("الجسور", "nicknames", "medium"),
        ("النمر", "nicknames", "easy"),
        ("الباشا", "nicknames", "medium"),
        ("الخيال", "nicknames", "medium"),
        ("المغوار", "nicknames", "hard"),
        ("الطويل", "nicknames", "easy"),
        ("القناص", "nicknames", "medium"),
        ("الهلالي", "nicknames", "medium"),
        ("العتيبي", "nicknames", "medium"),
        # ── أسماء عربية (arabic_names) ──
        ("فيصل", "arabic_names", "easy"),
        ("تركي", "arabic_names", "easy"),
        ("نورة", "arabic_names", "easy"),
        ("سلطان", "arabic_names", "easy"),
        ("خالد", "arabic_names", "easy"),
        ("فهد", "arabic_names", "easy"),
        ("سعود", "arabic_names", "easy"),
        ("عبدالله", "arabic_names", "easy"),
        ("مشاري", "arabic_names", "medium"),
        ("ناصر", "arabic_names", "easy"),
        ("هيفاء", "arabic_names", "medium"),
        ("ريم", "arabic_names", "easy"),
        ("وليد", "arabic_names", "easy"),
        ("بدر", "arabic_names", "easy"),
        ("ثامر", "arabic_names", "medium"),
        ("دلال", "arabic_names", "medium"),
        ("طلال", "arabic_names", "easy"),
        ("ماجد", "arabic_names", "easy"),
        ("نواف", "arabic_names", "medium"),
        ("غادة", "arabic_names", "medium"),
        # ── أدوات تراثية (heritage) ──
        ("دلة", "heritage", "easy"),
        ("محماس", "heritage", "medium"),
        ("فنجال", "heritage", "medium"),
        ("مبخرة", "heritage", "medium"),
        ("سدو", "heritage", "hard"),
        ("بشت", "heritage", "medium"),
        ("شماغ", "heritage", "easy"),
        ("عقال", "heritage", "easy"),
        ("مسباح", "heritage", "medium"),
        ("هاون", "heritage", "medium"),
        ("قربة", "heritage", "medium"),
        ("ميسم", "heritage", "hard"),
        ("رحى", "heritage", "hard"),
        ("خرج", "heritage", "hard"),
        ("مهباج", "heritage", "hard"),
        ("دوشك", "heritage", "hard"),
        ("حصيرة", "heritage", "medium"),
        ("تنور", "heritage", "medium"),
        ("خوص", "heritage", "hard"),
        ("مروحة", "heritage", "easy"),
    ]

    # Check if already seeded
    from sqlalchemy import func, select
    count = await session.execute(select(func.count()).select_from(MutarahaWord))
    if count.scalar_one() > 0:
        return  # Already seeded

    for word, category, difficulty in words_data:
        entry = MutarahaWord(
            word=word,
            category=category,
            letter_count=len(word),
            first_letter=word[0] if word else "",
            difficulty=difficulty,
        )
        session.add(entry)

    await session.commit()
