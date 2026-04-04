Implementation Plan — Minigames Catalog & Lobby
مشروع: حرب الأسماء — كاتالوج الألعاب المصغرة واللوبي
الإصدار: V1.0
التاريخ: 2026-04-04
الكاتب: Claude (بإشراف Salman)
النطاق: تنفيذ طبقة العرض فوق محرك الألعاب المصغرة

**المرجع:**
- [War of Names - Minigames Catalog & Lobby BRD - V1.0.md](War%20of%20Names%20-%20Minigames%20Catalog%20%26%20Lobby%20BRD%20-%20V1.0.md)
- [War of Names - Minigames Catalog & Lobby PRD - V1.0.md](War%20of%20Names%20-%20Minigames%20Catalog%20%26%20Lobby%20PRD%20-%20V1.0.md)

---

# 1. نظرة عامة

هذه الخطة تقسم بناء طبقة الكاتالوج واللوبي إلى **5 سبرنتات مستقلة**. كل سبرنت
يُنتج برمجيات قابلة للاختبار والتسليم بشكل مستقل.

## 1.1 الاعتماديات

المحرك الحالي جاهز ويدعم:
- N-player sessions مع `MinigameSessionParticipant`
- REST endpoints للـ challenge والـ queue
- WebSocket لوبي لكل لعبة
- `lobby_manager` في الذاكرة مع `get_lobby_state`
- `minigame_types` seed وإعدادات cascade

**ما ينقص** (محتوى هذه الخطة):
- `minigame_catalog_configs` table + seed
- `GET /api/competitions/{id}/minigames/catalog` (aggregation endpoint)
- `GET /api/competitions/{id}/minigames/{game_type}/lobby` (lobby detail endpoint)
- `WS /ws/competitions/{id}/minigames/catalog` (catalog realtime channel)
- Admin CRUD لـ catalog configs
- Frontend pages (كاتالوج + لوبي)
- Telemetry events

## 1.2 هيكل السبرنتات

| السبرنت | النطاق | المخرجات القابلة للاختبار |
|---------|--------|---------------------------|
| **Sprint A** | Data foundation | جدول `minigame_catalog_configs` + migration + seed + model + admin CRUD |
| **Sprint B** | Catalog aggregation service | pure aggregation logic + 6 batched queries + unit tests |
| **Sprint C** | REST endpoints | `GET /catalog`، `GET /{game_type}/lobby` + error handling |
| **Sprint D** | WebSocket catalog channel | realtime channel + reconciliation + reconnect |
| **Sprint E** | Frontend (React) | صفحة الكاتالوج + بطاقة اللعبة + صفحة اللوبي |

كل سبرنت يُنفّذ كخطة فرعية مستقلة. هذه الوثيقة تُحدد الخطوط العريضة — كل سبرنت
سيحصل على خطته التفصيلية عند البدء به.

## 1.3 ترتيب التنفيذ

```text
Sprint A (Data) → Sprint B (Aggregation) → Sprint C (REST)
    ↓
Sprint D (WebSocket) ← يعتمد على C
    ↓
Sprint E (Frontend) ← يعتمد على C و D
```

السبرنتات A و B و C تسلسلية (كل واحد يعتمد على السابق).
السبرنت D يبدأ بعد C. السبرنت E يبدأ بعد D.

---

# 2. Sprint A — Data Foundation

## 2.1 الهدف

إنشاء طبقة البيانات الكاملة لـ `minigame_catalog_configs` مع migration،
model، seed، و admin CRUD endpoints.

## 2.2 المرجع في BRD

- §11.3 الجدول الجديد
- §11.3.1 التعدادات
- §11.3.2 الفهارس
- §11.3.3 المصدر
- §11.4 Migration و seed
- §11.4.2 بيانات seed لـ مطارحة
- §11.4.3 الـ fallback

## 2.3 الملفات المتوقعة

```text
backend/
├── app/
│   └── modules/
│       └── minigames/
│           ├── catalog_config_model.py          # CREATE: MinigameCatalogConfig
│           ├── catalog_admin_service.py         # CREATE: CRUD logic
│           └── router.py                        # MODIFY: +4 admin endpoints
├── migrations/
│   └── 007_minigame_catalog_configs.sql         # CREATE
└── tests/
    └── test_minigame_engine/
        ├── test_catalog_config_model.py         # CREATE
        └── test_catalog_admin_service.py        # CREATE
```

## 2.4 المهام عالية المستوى

### Task A-1: SQLAlchemy model

إنشاء `MinigameCatalogConfig` مع كل الحقول من BRD §11.3. enums كـ StrEnum
في `app/core/enums.py`:
- `MinigameHeroVariant`: duel, arena, solo, party, tournament
- `MinigameCardVariant`: standard, featured, compact, coming_soon_teaser
- `MinigameCatalogAvailability`: active, coming_soon, hidden, maintenance

### Task A-2: Migration 007

SQL migration يُنشئ:
- الجدول مع كل القيود
- الفهارس من §11.3.2
- صف seed لـ مطارحة (§11.4.2)

### Task A-3: Admin CRUD endpoints

4 endpoints في `router.py`:
- `GET /api/admin/minigames/catalog-configs` — list all
- `GET /api/admin/minigames/catalog-configs/{game_type}` — get one
- `PUT /api/admin/minigames/catalog-configs/{game_type}` — update (upsert)
- `DELETE /api/admin/minigames/catalog-configs/{game_type}` — remove (soft or hard TBD)

كل CRUD يتطلب `get_admin_account` dependency ويسجل audit event.

### Task A-4: Fallback loader helper

Pure function `resolve_catalog_config(game_type_row, config_row | None) -> dict`
يُرجع القيم الفعالة مع fallback رسمي من §11.4.3 عند غياب `config_row`.
يُستخدم في Sprint B.

### Task A-5: Tests

- Model tests: CRUD عبر ORM، unique constraint، enum validation
- Fallback function tests: غياب config → defaults صحيحة + telemetry warning
- Admin CRUD tests: auth boundary، validation errors بالعربية

## 2.5 معايير القبول

- [ ] Migration 007 تُنفذ نظيفة في Docker rebuild
- [ ] صف seed لـ مطارحة موجود بعد الـ migration
- [ ] 4 admin endpoints تعمل عبر curl/pytest
- [ ] Fallback function تعيد defaults صحيحة عند غياب config
- [ ] كل الاختبارات (model + fallback + admin) تمر
- [ ] لا يوجد N+1 في admin list endpoint (single SELECT)

---

# 3. Sprint B — Catalog Aggregation Service

## 3.1 الهدف

بناء طبقة الـ aggregation التي تدمج 6 مصادر بيانات في read model موحد لكل
بطاقة. يجب تحقيق p95 < 200ms عبر 6 استعلامات SQL ثابتة.

## 3.2 المرجع في BRD

- §7.1 Catalog Aggregation Service
- §8.1 Game Catalog Card read model
- §8.1.1 قواعد الحقول الحرجة
- §9 تنسيق عدد اللاعبين
- §10.1.1 قاعدة الظهور
- §15.1-15.5 منطق التجميع والأهلية والأداء

## 3.3 الملفات المتوقعة

```text
backend/app/modules/minigames/
├── catalog_service.py                        # CREATE: aggregation logic
├── catalog_read_model.py                     # CREATE: pure typed dicts
└── __init__.py                               # MODIFY: exports

backend/tests/test_minigame_engine/
├── test_catalog_service.py                   # CREATE
├── test_catalog_read_model.py                # CREATE
└── test_catalog_aggregation.py               # CREATE (integration)
```

## 3.4 المهام عالية المستوى

### Task B-1: Pure helper — `build_player_count_label`

```python
def build_player_count_label(min_players: int, max_players: int) -> str:
    # BRD §9.1
```

تطبيق القاعدة الرسمية من BRD §9.1 كـ pure function. اختبارات شاملة لكل
المجموعات الممكنة.

### Task B-2: Pure helper — `resolve_card_status`

```python
def resolve_card_status(
    *,
    availability_mode: str,
    kill_switch_level: str,
    my_active_session_id: UUID | None,
    in_queue: bool,
    player_balance: int,
    buy_in_amount: int,
    is_bankrupt: bool,
) -> tuple[str, str | None]:
    # Returns (status, availability_reason)
    # BRD §15.4 ordering
```

تطبيق ترتيب CTA من BRD §15.4 كـ pure function.

### Task B-3: Pure helper — `resolve_estimated_duration`

```python
def resolve_estimated_duration(
    *,
    leaderboard_avg_sec: float | None,
    leaderboard_match_count: int,
    config_duration_sec: int | None,
) -> tuple[int | None, str | None]:
    # Returns (duration, source)
    # BRD §8.1.1
```

Stats > config > null. Thresholds: leaderboard يحتاج ≥ 10 مباريات.

### Task B-4: Batched query loader — `CatalogDataLoader`

Class يحمّل كل البيانات اللازمة في 6 استعلامات ثابتة (BRD §15.5.1):

```python
class CatalogDataLoader:
    async def load_all(
        self,
        session: AsyncSession,
        *,
        competition_id: UUID,
        membership_id: UUID,
        season_id: UUID | None,
        cycle_id: UUID | None,
    ) -> CatalogRawData:
        # 6 queries, parallel where possible
```

`CatalogRawData` هو dataclass يحتوي كل النتائج الخام قبل التجميع.

### Task B-5: Aggregation function — `build_catalog_cards`

```python
def build_catalog_cards(
    raw: CatalogRawData,
    lobby_presence: dict[str, LobbyPresenceSnapshot],
    correlation_id: UUID,
) -> list[CatalogCardReadModel]:
    # Pure function, no DB, no async
```

يدمج `raw` مع بيانات اللوبي في الذاكرة ويُنتج قائمة read models.

### Task B-6: Main orchestrator — `get_catalog`

```python
async def get_catalog(
    session: AsyncSession,
    *,
    competition_id: UUID,
    membership_id: UUID,
    season_id: UUID | None,
    cycle_id: UUID | None,
) -> CatalogResponse:
    # Orchestrates loader + aggregator + lobby_manager calls
```

### Task B-7: Lobby detail service

بناء `get_lobby_detail(competition_id, game_type, membership_id)` لإرجاع
read model الكامل للوبي (BRD §8.2). يُعيد استخدام نفس الـ helpers من B-1 و B-3.

## 3.5 معايير القبول

- [ ] `build_player_count_label` pure + 100% coverage (4 حالات: 1-1، 2-2، N-N، A-B)
- [ ] `resolve_card_status` pure + تُطبّق كل فروع ترتيب BRD §15.4
- [ ] `resolve_estimated_duration` pure + تُطبّق الـ fallback chain
- [ ] `CatalogDataLoader.load_all` يُنفذ 6 استعلامات بالضبط (مُؤكد عبر mock أو query counting)
- [ ] `build_catalog_cards` pure + يُعالج الحالات الحرجة (has_history=false, null duration, hidden games excluded)
- [ ] `get_catalog` end-to-end test مع 3+ game types تُرجع read models صحيحة
- [ ] `get_lobby_detail` يُرجع LobbyPageReadModel (BRD §8.2)
- [ ] p95 latency مُقاسة محلياً عبر timing harness: < 200ms

---

# 4. Sprint C — REST Endpoints

## 4.1 الهدف

كشف `get_catalog` و `get_lobby_detail` عبر REST مع error handling كامل
ومسار تقادم واضح.

## 4.2 المرجع في BRD

- §12.1 endpoint الكاتالوج
- §12.2 endpoint لوبي اللعبة
- §12.4 صيغة الاستجابة للأخطاء
- §12.5 مسار التقادم

## 4.3 الملفات المتوقعة

```text
backend/app/modules/minigames/
├── router.py                                 # MODIFY: +2 endpoints

backend/tests/test_minigame_engine/
├── test_catalog_router.py                    # CREATE
└── test_lobby_detail_router.py               # CREATE
```

## 4.4 المهام عالية المستوى

### Task C-1: `GET /api/competitions/{competition_id}/minigames/catalog`

يدعو `catalog_service.get_catalog` ويُغلّف الاستجابة. يُنتج `correlation_id`
جديد لكل طلب ويُرجعه في الـ response.

Error handling (BRD §12.4):
- 401: JWT مفقود
- 403: ليس عضواً في المسابقة
- 403: kill switch = emergency
- 404: المسابقة غير موجودة
- 500: خطأ غير متوقع

### Task C-2: `GET /api/competitions/{competition_id}/minigames/{game_type}/lobby`

يدعو `catalog_service.get_lobby_detail`. نفس error handling + 404 إذا
`game_type` غير مسجل.

### Task C-3: تحديث وثائق الـ endpoints القديمة

إضافة deprecation notice في docstrings لـ `GET /api/minigames` يوضح أنها
تُستخدم الآن للاستكشاف العالمي، والكاتالوج المُقيّد على الـ `/catalog` الجديد.
لا تُحذف — تبقى موثقة ومدعومة.

### Task C-4: Integration tests

اختبارات حقيقية ضد Docker:
- مسابقة بها 3 game types (2 active، 1 coming_soon، 1 hidden)
- لاعب له جلسة `IN_PROGRESS` في لعبة واحدة
- لاعب له إحصائيات في لعبة أخرى
- لاعب بدون رصيد كافٍ لثالثة

التحقق من أن:
- البطاقات المرئية: 3 (الـ hidden لا يظهر)
- البطاقات فيها `active_session_id` صحيح
- `my_stats.has_history` صحيح
- `status` صحيح لكل حالة
- `correlation_id` موجود ومُختلف لكل طلب

## 4.5 معايير القبول

- [ ] `GET /catalog` يُرجع 200 + JSON صحيح للاعب عضو
- [ ] `GET /catalog` يُرجع 403 عربياً للاعب غير عضو
- [ ] `GET /catalog` يُرجع 404 عربياً لمسابقة غير موجودة
- [ ] `GET /catalog` يُضمّن `correlation_id` في الاستجابة
- [ ] `GET /catalog` يحترم availability rules (hidden لا يظهر، maintenance يظهر)
- [ ] `GET /{game_type}/lobby` يعمل + يُرجع `LobbyPageReadModel`
- [ ] p95 latency في Docker < 200ms
- [ ] جميع الاختبارات الموجودة لا تزال تمر

---

# 5. Sprint D — WebSocket Catalog Channel

## 5.1 الهدف

بناء قناة realtime للكاتالوج مع authentication، heartbeat، reconcileation
rules، وإعادة الاتصال.

## 5.2 المرجع في BRD

- §4.2.1 قاعدة التوفيق
- §4.2.2 قاعدة إعادة الاتصال
- §13.1 قناة الكاتالوج (كامل)
- §13.1.1-13.1.8 جميع التفاصيل

## 5.3 الملفات المتوقعة

```text
backend/app/modules/minigames/
├── ws_router.py                              # MODIFY: +catalog channel handler
├── catalog_presence.py                       # CREATE: catalog subscription tracking
└── catalog_broadcaster.py                    # CREATE: patch broadcast logic

backend/tests/test_minigame_engine/
└── test_catalog_ws.py                        # CREATE
```

## 5.4 المهام عالية المستوى

### Task D-1: `CatalogSubscriptionManager`

In-memory tracker مشابه لـ `LobbyManager`:
- subscribe(competition_id, membership_id, websocket)
- unsubscribe(competition_id, membership_id)
- broadcast_to_competition(competition_id, message)
- get_subscriber_count(competition_id)
- capacity enforcement (500 per channel)

### Task D-2: WebSocket endpoint

```python
@ws_router.websocket("/ws/competitions/{competition_id}/minigames/catalog")
async def catalog_ws(...):
    # JWT auth, membership check, subscribe, message loop
```

يُطبّق بروتوكول §13.1: auth، heartbeat، close codes، reconnect-safe.

### Task D-3: Catalog broadcaster integration

إضافة hooks في `lobby_manager` لإطلاق `catalog_update` patches عندما:
- لاعب ينضم للوبي (presence_count++)
- لاعب يغادر (presence_count--)
- لاعب يدخل queue (queue_count++)
- لاعب يغادر queue (queue_count--)
- session تبدأ (active_matches_count++)
- session تنتهي (active_matches_count-- + recent_results_count++)

الـ broadcaster يُرسل patches فقط للحقول القابلة للتغيير (BRD §13.1.7).

### Task D-4: Full `catalog_state` rebroadcast على الاشتراك/إعادة الاتصال

عند `catalog_subscribe`، الخادم يُعيد بناء الكاتالوج الكامل (أو يأخذه من cache)
ويُرسله. على إعادة الاتصال، نفس السلوك — ليس patches (BRD §4.2.2).

### Task D-5: Tests

- Unit tests لـ `CatalogSubscriptionManager`
- Integration tests لدورة subscribe → receive state → receive patch → unsubscribe
- Reconnection tests: انقطاع → إعادة اتصال → استلام state كامل
- Auth tests: JWT مفقود → close 4001
- Capacity tests: 501st connection → close 4013

## 5.5 معايير القبول

- [ ] JWT auth يعمل + close codes صحيحة
- [ ] `catalog_state` يُرسل عند subscribe وعلى reconnect
- [ ] `catalog_update` patches تحتوي فقط الحقول المسموح بها (BRD §13.1.7)
- [ ] heartbeat يعمل + timeout بعد 90s
- [ ] lobby events تُطلق patches في الوقت الفعلي (< 1s latency)
- [ ] capacity limit يُنفذ (4013)
- [ ] جميع close codes بالعربية

---

# 6. Sprint E — Frontend (React)

## 6.1 الهدف

بناء صفحة الكاتالوج وصفحة اللوبي بلغة React + Tailwind، RTL كاملة،
مع محاكاة سينمائية مطابقة للهوية البصرية.

## 6.2 المرجع في PRD

- §8 هيكل التجربة
- §9 صفحة كاتالوج الألعاب المصغرة
- §10 مواصفات بطاقة اللعبة
- §11 المتطلبات الجمالية
- §12 لوبي اللعبة
- §13 رحلات المستخدم
- §15 المحتوى والنبرة
- §16 التحليلات المطلوبة

## 6.3 الملفات المتوقعة

```text
frontend/src/
├── pages/
│   ├── MinigamesCatalogPage.tsx              # CREATE
│   └── MinigameLobbyPage.tsx                 # CREATE
├── components/
│   └── minigames/
│       ├── GameCard.tsx                      # CREATE
│       ├── GameCardBadge.tsx                 # CREATE (player count badge)
│       ├── CatalogFilters.tsx                # CREATE
│       ├── LobbyHeader.tsx                   # CREATE
│       ├── LobbyDecisionArea.tsx             # CREATE
│       ├── LobbyActivityStrip.tsx            # CREATE
│       ├── MyStatsBlock.tsx                  # CREATE
│       └── HowToPlayModal.tsx                # CREATE
├── hooks/
│   ├── useCatalog.ts                         # CREATE (REST + WebSocket)
│   └── useLobbyDetail.ts                     # CREATE
├── lib/
│   ├── minigame-telemetry.ts                 # CREATE
│   └── minigame-ws.ts                        # CREATE (subscribe manager)
└── types/
    └── minigame-catalog.ts                   # CREATE (TS types matching BRD §8)
```

## 6.4 المهام عالية المستوى

### Task E-1: TS types + API client

توليد أنواع TypeScript تطابق read models في BRD §8.1 و §8.2. بناء API client
صغير يُعالج `GET /catalog` و `GET /lobby`.

### Task E-2: `useCatalog` hook — REST+WS reconciliation

```typescript
function useCatalog(competitionId: string): CatalogState {
  // 1. Open WebSocket, buffer patches
  // 2. Fetch REST snapshot
  // 3. Apply snapshot to state
  // 4. Apply buffered patches
  // 5. Subscribe to new patches
  // On disconnect: clear buffer, refetch + resubscribe
}
```

ينفّذ بالضبط قاعدة BRD §4.2.1.

### Task E-3: `GameCard` component

يعرض:
- أيقونة + اسم في بداية السطر (RTL)
- player-count badge في نهاية السطر
- وصف قصير
- النشاط المباشر (presence, active matches)
- المدة والدخول
- إحصائياتي (مخفية إذا `has_history: false`)
- CTA مناسب لكل `status`

7 حالات بطاقة (BRD §10.1):
- playable, queued, in_match, insufficient_balance, maintenance, coming_soon (مع أو بدون `expected_launch_at`)

### Task E-4: `MinigamesCatalogPage`

- عنوان + وصف
- شريط "نشط الآن" (اختياري)
- فلاتر chips (الكل، نشط الآن، منفرد، 1v1، جماعي، قريباً)
- شبكة البطاقات (1/2/3 أعمدة responsive)
- featured game يأخذ full-width

### Task E-5: `MinigameLobbyPage`

ينفذ PRD §12:
- header بالهوية البصرية
- منطقة القرار (queue / challenge / resume)
- شريط النشاط المباشر
- إحصائياتي
- preview الترتيب
- زر "كيف تلعب" → modal

### Task E-6: Telemetry

زرع أحداث BRD §18 في الواجهة:
- `catalog_viewed` على mount
- `card_impression` عبر IntersectionObserver
- `card_clicked` على الضغطات
- `card_dwell_ms` عند الخروج من الـ viewport
- `catalog_time_to_first_click_ms` من mount إلى أول click
- `lobby_viewed`, `lobby_time_to_action_ms`
- `how_to_play_opened`
- `queue_join_clicked`, `challenge_sent`, `resume_clicked`

كل حدث يحمل `correlation_id` من الـ snapshot الحالي (BRD §18.3).

### Task E-7: Adversarial QA

تشغيل اختبارات browser adversarial:
- RTL layout sanity
- overflow على شاشة 360×780
- empty states لكل بطاقة
- WebSocket reconnect behavior
- dark mode contrast
- Arabic text rendering

## 6.5 معايير القبول

- [ ] الصفحة تفتح في < 1.5s على Docker محلي
- [ ] كل بطاقة تعرض `player_count_label` من الخادم (ليس نصاً يدوياً)
- [ ] فلاتر تعمل (solo, 1v1, جماعي)
- [ ] RTL layout صحيح على جميع البطاقات
- [ ] empty states واضحة (لاعب جديد، لعبة قادمة)
- [ ] WebSocket reconnect يُعيد البناء من الصفر
- [ ] Telemetry events تُسجّل مع `correlation_id`
- [ ] يعمل على Galaxy S25 (360×780)

---

# 7. الاختبارات الإجمالية

## 7.1 اختبارات الوحدة (Unit Tests)

كل سبرنت يُضيف اختبارات في `tests/test_minigame_engine/`:
- Sprint A: ~15 test (model + fallback + admin CRUD)
- Sprint B: ~25 test (pure helpers + aggregator)
- Sprint C: ~15 test (endpoint success/error paths)
- Sprint D: ~12 test (WS manager + broadcast)
- Sprint E: ~20 test (React components + hooks)

**الإجمالي المتوقع:** ~87 اختباراً جديداً

## 7.2 اختبارات التكامل

- Docker rebuild بعد Sprint A (migration check)
- End-to-end REST test بعد Sprint C (curl script)
- WebSocket dance test بعد Sprint D (playwright-compatible)
- Full UI smoke بعد Sprint E

## 7.3 اختبارات الأداء

بعد Sprint C:
- محاكاة 50 لاعب على مسابقة بها 5 game types
- قياس p50/p95/p99 لـ `GET /catalog`
- قياس عدد الاستعلامات الفعلي (يجب = 6)

---

# 8. المخاطر والتخفيف

| الخطر | الأثر | التخفيف |
|-------|------|--------|
| الـ migration تفشل على بيانات قديمة | فقد بيانات أو downtime | DEFAULT القيم، ON CONFLICT DO NOTHING في seed |
| p95 > 200ms بسبب N+1 | تجربة بطيئة | اختبار query count في CI + batched loaders |
| WebSocket patches تسبق الـ REST snapshot | حالة غير متسقة | client-side buffering (§4.2.1) + full refetch |
| `catalog_config_missing` ينتشر في production | بطاقات رمادية | seed لكل game type، telemetry alert |
| kill switch emergency يفكّ المشتركين | بدون تحذير | server يُرسل `catalog_state` مع status=maintenance قبل الإغلاق |

---

# 9. ما خارج النطاق

- **spectator mode**: لا في V1
- **tournament brackets**: لا في V1
- **recommendation ML**: لا في V1
- **deep gameplay analytics**: لا في V1
- **catalog search/filters متقدمة**: chips فقط في V1
- **cross-competition catalog**: V1 مُقيّد بالمسابقة الواحدة
- **catalog caching بـ Redis**: V1 in-memory فقط (single server)

---

# 10. الخلاصة

هذه الخطة تُقسّم بناء طبقة الكاتالوج واللوبي إلى 5 سبرنتات قابلة للاختبار.
كل سبرنت ينتج برمجيات قابلة للتسليم. الخطة تُعالج جميع الـ 20 gap الموثقة في
مراجعة BRD/PRD السابقة.

**خطوة البدء التالية:** فتح Sprint A بخطة تفصيلية (task-by-task plan) وتنفيذها
عبر subagent-driven development.

**الهدف الإجمالي:** بعد اكتمال كل السبرنتات، يكون لدى حرب الأسماء طبقة اكتشاف
كاملة للألعاب المصغرة — قابلة للتوسع لأي لعبة جديدة بدون بناء تجربة اكتشاف جديدة.
