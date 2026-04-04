BRD — وثيقة المتطلبات التجارية والوظيفية
مشروع: حرب الأسماء — كاتالوج الألعاب المصغرة واللوبي
الإصدار: V1.0
التاريخ: 2026-04-04
الكاتب: Codex (بإشراف Salman)
اللغة الأساسية: العربية
نوع المستند: Business Requirements Document (BRD)
النطاق: طبقة العرض والاكتشاف واللوبي فوق محرك الألعاب المصغرة

---

# 1. الملخص التنفيذي

هذه الوثيقة تحدد المتطلبات التجارية والوظيفية لطبقة **كاتالوج الألعاب المصغرة + لوبي اللعبة** داخل حرب الأسماء.

الطبقة الجديدة تقع فوق محرك الألعاب المصغرة الحالي، وتربط بين:

- سجل أنواع الألعاب `minigame_types`
- إعدادات المسابقة الفعلية
- الحضور الحي والنشاط المباشر
- إحصائيات اللاعب
- التحدي والطابور والعودة للمباراة

النتيجة المطلوبة:

- صفحة موحدة تعرض كل الألعاب بشكل غني بصرياً
- كل لعبة لها بطاقة واضحة
- **كل بطاقة تعرض عدد اللاعبين المدعوم**
- الدخول من البطاقة إلى لوبي اللعبة يتم عبر عقد API/WebSocket واضحة

---

# 2. الهدف من الوثيقة

- تعريف البنية الوظيفية والتقنية للكاتالوج واللوبي
- تحديد العقود بين الـ frontend والـ backend
- تحديد ما يجب أن يأتي من المحرك، وما يجب أن يُضاف فوقه
- تحديد مخطط بيانات الكاتالوج واللوبي
- تحديد رسائل الـ WebSocket اللازمة للتحديثات الحية
- تحديد حدود الإدارة والتحكم والعرض المستقبلي

---

# 3. العلاقة مع الوثائق الأخرى

هذه الوثيقة **تكمل** ولا تستبدل:

- `docs/minigames/War of Names - Minigame Engine BRD - V1.0.md`
- `docs/minigames/War of Names - Mutaraha (مطارحة) PRD - V1.0.md`
- `docs/Game Identity + Product Visual Direction + UX - BRD - V1.0.md`

توزيع المسؤولية:

- **Engine BRD**: كيف تعمل الجلسات، التوفيق، التسوية، والموثوقية
- **Game PRD**: كيف تعمل لعبة بعينها
- **Catalog/Lobby BRD**: كيف تُكتشف الألعاب وتُعرض وتُدخل اللاعب إلى التجربة

---

# 4. المبادئ المعمارية

## 4.1 طبقة عرض فوق المحرك

الكاتالوج واللوبي ليسا محركاً جديداً. هما طبقة قراءة وتجميع فوق المحرك الموجود.

## 4.2 REST للتحميل الأولي، WebSocket للحياة

- REST: اللقطة الأولى للكاتالوج واللوبي
- WebSocket: تحديث النشاط الحي والحالات المتغيرة

### 4.2.1 قاعدة التوفيق بين REST وWebSocket

لتفادي سباقات البيانات (race conditions) بين الـ snapshot والـ patches،
العميل **يجب** أن يتبع هذا الترتيب عند تحميل الكاتالوج:

1. افتح اتصال WebSocket واشترك في القناة
2. ابدأ buffer للـ patches الواردة (لا تطبّقها بعد)
3. أرسل `GET /catalog` للحصول على الـ snapshot الكامل
4. طبّق الـ snapshot على الحالة المحلية
5. طبّق الـ patches المخزّنة في الـ buffer بالترتيب (إذا كانت أحدث من الـ snapshot)
6. امسح الـ buffer وابدأ تطبيق الـ patches الجديدة مباشرة

### 4.2.2 قاعدة إعادة الاتصال

عند إعادة اتصال WebSocket (بعد انقطاع):

- العميل **يجب** أن يتخلى عن أي patches قديمة في الـ buffer
- العميل **يجب** أن يعيد جلب `GET /catalog` من البداية
- الخادم **يجب** أن يُرسل `catalog_state` كامل بعد الاشتراك الجديد، ليس patches
- هذا يضمن اتساقاً قوياً بعد الانقطاع على حساب بعض الـ bandwidth

### 4.2.3 نطاق كل شيء هو المسابقة

كل data (read models، counts، my_stats، presence) مُقيّد بالمسابقة الحالية
(`competition_id` في المسار). لاعب في عدة مسابقات يرى كاتالوج منفصل لكل مسابقة.
تبديل المسابقة في الواجهة = إعادة تحميل كامل (`GET /catalog` + إعادة اشتراك WebSocket).

## 4.3 player-count server-driven

عدد اللاعبين لا يأتي من نص ثابت في الواجهة. يجب أن يُشتق من:

- `min_players`
- `max_players`

ويُنسق في الواجهة تلقائياً.

## 4.4 game-card = read model

بطاقة اللعبة ليست model خام من `minigame_types`. هي **read model مجمّع** يدمج:

- تعريف اللعبة
- إعدادات المسابقة الحالية
- إحصائيات اللاعب
- النشاط الحي
- حالة الأهلية والدخول

---

# 5. النطاق الوظيفي

## 5.1 ما الذي يشمله هذا النظام؟

- صفحة كاتالوج الألعاب المصغرة
- صفحة لوبي لكل لعبة
- read models الخاصة بالبطاقات واللوبي
- تهيئة العرض للألعاب المتاحة/القادمة/المعطلة
- تحديثات النشاط المباشر
- إظهار الحالة الخاصة باللاعب: queued / in_match / eligible

## 5.2 ما الذي لا يشمله؟

- منطق المباراة نفسها
- منطق اللعبة الخاصة
- spectator mode الكامل
- tournament bracket UX
- deep gameplay analytics

---

# 6. Information Architecture

## 6.1 المسارات (Routes)

المسارات المقترحة للواجهة:

```text
/competitions/{competition_id}/minigames
    → صفحة الكاتالوج

/competitions/{competition_id}/minigames/{game_type}
    → لوبي اللعبة

/competitions/{competition_id}/minigames/{game_type}/leaderboard
    → ترتيب اللعبة (اختياري إذا انفصلت الصفحة)

/competitions/{competition_id}/minigames/sessions/{session_id}
    → استعادة المباراة أو تفاصيل الجلسة
```

## 6.2 التدرج الملاحي

```text
Dashboard
  → Minigames Catalog
    → Game Lobby
      → Match Arena
        → Result
          → Back to Lobby
            → Back to Catalog
```

---

# 7. مكوّنات النظام

## 7.1 Catalog Aggregation Service

خدمة تبني response واحداً للكاتالوج عبر دمج:

- `minigame_types`
- إعدادات اللعبة الفعالة في المسابقة
- leaderboard stats الخاصة باللاعب
- نشاط اللوبي الحالي
- الجلسات النشطة الحالية للاعب

## 7.2 Lobby Detail Service

خدمة تبني اللقطة الأولى للّوبي وتُرجع:

- معلومات اللعبة
- player-count label
- buy-in
- lobby snapshot
- recent results
- leaderboard preview
- personal stats
- الحالة الحالية للاعب

## 7.3 Catalog Realtime Channel

قناة خفيفة تبث updates للكاتالوج كله، حتى لا يضطر العميل لفتح WebSocket لكل بطاقة.

## 7.4 Game Lobby Channel

القناة الحالية الخاصة باللوبي لكل لعبة تبقى المرجع للنشاط الداخلي للّوبي.

---

# 8. عقود القراءة (Read Models)

## 8.1 Game Catalog Card

```json
{
  "game_type": "mutaraha",
  "name": "مطارحة",
  "short_description": "مبارزة كلمات 1v1",
  "description": "خمّن كلمات خصمك قبل ما يخمّن كلماتك",
  "icon": "lucide:swords",
  "accent_color": "#D84315",
  "hero_variant": "duel",
  "card_variant": "standard",
  "min_players": 2,
  "max_players": 2,
  "player_count_label": "1v1",
  "estimated_duration_sec": 300,
  "estimated_duration_source": "stats",
  "buy_in_amount": 500,
  "status": "playable",
  "availability_reason": null,
  "expected_launch_at": null,
  "presence_count": 3,
  "queue_count": 1,
  "active_matches_count": 1,
  "recent_results_count": 5,
  "supports_overtime": true,
  "supports_spectators": false,
  "supports_ranked": false,
  "supports_team_mode": false,
  "featured": true,
  "sort_order": 10,
  "correlation_id": "uuid-v4",
  "my_state": {
    "queued": false,
    "in_active_match": false,
    "active_session_id": null,
    "active_session_phase": null
  },
  "my_stats": {
    "wins": 5,
    "losses": 2,
    "current_streak": 3,
    "best_streak": 4,
    "total_matches": 7,
    "win_rate": 0.714,
    "has_history": true
  }
}
```

### 8.1.1 قواعد الحقول الحرجة

#### `hero_variant` و`card_variant`

تعدادات مغلقة (انظر §11.3.1). الواجهة تربط كل قيمة بمكوّن React مخصص.
الخادم لا يُرجع قيماً خارج التعداد — في حال وجود قيمة غير صالحة في DB،
يُستبدل بالقيمة الافتراضية (`arena` / `standard`) ويُسجّل تحذير.

#### `estimated_duration_sec` و`estimated_duration_source`

المصدر يُحسب بالترتيب التالي:

1. إذا كان `minigame_leaderboards.avg_match_duration_sec` موجود للمسابقة ويتجاوز **10 مباريات مكتملة**:
   - `estimated_duration_sec` = المتوسط المُجمّع عبر كل اللاعبين
   - `estimated_duration_source` = `"stats"`
2. وإلا إذا كانت القيمة موجودة في `minigame_catalog_configs.estimated_duration_sec`:
   - `estimated_duration_sec` = القيمة المحفوظة
   - `estimated_duration_source` = `"config"`
3. وإلا:
   - `estimated_duration_sec` = `null`
   - `estimated_duration_source` = `null`
   - الواجهة تُخفي سطر "المدة" من البطاقة

#### `my_stats` عند عدم وجود سجل

إذا لم يلعب اللاعب هذه اللعبة في هذه المسابقة قط، `my_stats` **يُرجع دائماً** بالشكل:

```json
{
  "wins": 0,
  "losses": 0,
  "current_streak": 0,
  "best_streak": 0,
  "total_matches": 0,
  "win_rate": 0.0,
  "has_history": false
}
```

- الحقل `has_history` يسمح للواجهة بالتمييز بين "لم يلعب قط" (إخفاء السطر وإظهار
  `جرّب مطارحة!`) و"لديه سجل" (إظهار `سجلي: X-Y`).
- `win_rate` **لا يُحسب عبر القسمة المباشرة** — القاعدة:

```text
win_rate = wins / total_matches   if total_matches > 0
win_rate = 0.0                    if total_matches == 0
```

هذا يمنع القسمة على صفر ويضمن نوعاً ثابتاً (`float`) دائماً.

#### `my_state.active_session_phase`

قيمة ضمن `{in_progress, overtime, paused, null}`. تسمح للواجهة
بعرض ملصق مختلف على زر "ارجع للمباراة" (مثل "مباراتك متوقفة" لـ `paused`).
القواعد في §15.3.

#### `expected_launch_at`

- `null` لكل البطاقات ما عدا `coming_soon`
- قيمة ISO-8601 للبطاقات القادمة إذا حددها المشرف
- الواجهة تعرضها كنص نسبي ("قريباً — خلال أسبوعين") عند توفرها
- غير إلزامية — `coming_soon` بدون تاريخ يظهر فقط كـ "قريباً"

#### `correlation_id`

UUID يُولّد عند كل طلب `GET /catalog` ويُمرّر في:

- الاستجابة نفسها
- أي `catalog_state` / `catalog_update` على WebSocket لنفس الجلسة
- أحداث الـ telemetry المرتبطة (§18)

يُمكّن ربط المشاهدات والضغطات بنفس طلب الكاتالوج للتحليل.

## 8.2 Lobby Page Read Model

```json
{
  "game": {
    "game_type": "mutaraha",
    "name": "مطارحة",
    "description": "خمّن كلمات خصمك قبل ما يخمّن كلماتك",
    "icon": "lucide:swords",
    "accent_color": "#D84315",
    "min_players": 2,
    "max_players": 2,
    "player_count_label": "1v1",
    "buy_in_amount": 500,
    "estimated_duration_sec": 300
  },
  "my_state": {
    "queued": false,
    "in_active_match": false,
    "active_session_id": null
  },
  "my_stats": {},
  "lobby": {
    "players": [],
    "queue_size": 1,
    "active_matches": [],
    "recent_results": []
  },
  "leaderboard_preview": [],
  "how_to_play": {
    "summary_steps": [
      "اختر كلماتك",
      "استنتج كلمات الخصم",
      "اخمن قبل أن يخمنك"
    ]
  }
}
```

---

# 9. تنسيق عدد اللاعبين

## 9.1 القاعدة

واجهة الكاتالوج واللوبي **ملزمة** باستخدام هذه القاعدة:

```text
if min_players == 2 and max_players == 2:
    "1v1"
elif min_players == max_players:
    "{max_players} لاعبين"
else:
    "{min_players}-{max_players} لاعبين"
```

## 9.2 ملاحظات

- النص يجب أن يُبنى من القيم الحقيقية القادمة من الخادم
- لا يسمح بكتابة player-count كنص حر داخل الـ frontend
- إذا غابت القيم، يتم إخفاء CTA وتسجيل خطأ telemetry

---

# 10. حالات البطاقة واللوبي

## 10.1 حالات الكاتالوج

| الحالة | المعنى | الظهور في الكاتالوج | السلوك |
|--------|--------|----------------------|--------|
| `playable` | اللعبة متاحة واللاعب مؤهل | ظاهرة | CTA فعال |
| `queued` | اللاعب في طابور هذه اللعبة | ظاهرة | CTA = أنت في الطابور |
| `in_match` | اللاعب لديه جلسة نشطة | ظاهرة | CTA = ارجع للمباراة |
| `insufficient_balance` | اللاعب لا يملك الرصيد المطلوب | ظاهرة | CTA معطل + reason |
| `disabled_competition` | اللعبة موقوفة في المسابقة | **مخفية** | لا تظهر أصلاً |
| `maintenance` | kill switch أو صيانة | **ظاهرة كبطاقة مقفلة** | CTA معطل + reason ودّي بالعربي |
| `coming_soon` | اللعبة ظاهرة تسويقياً فقط | ظاهرة | CTA = `قريباً` |
| `hidden` | مُخفية تماماً بقرار إداري | **مخفية** | لا تظهر أصلاً |

### 10.1.1 قاعدة الظهور الرسمية

- `disabled_competition` و`hidden` → البطاقة لا تُرجع من `GET /catalog` نهائياً
- `maintenance` → البطاقة **تظهر** كبطاقة مقفلة مع سبب واضح بالعربي (مثل "صيانة مؤقتة — نرجع قريباً") — اللاعب الذي رأى اللعبة أمس يحتاج يشوفها اليوم حتى لو معطلة
- `coming_soon` → البطاقة تظهر كـ teaser مع CTA `قريباً` و(اختيارياً) `expected_launch_at`
- كل الحالات الأخرى → بطاقة عادية مع CTA مناسب حسب §15.4

## 10.2 حالات اللوبي

| الحالة | المعنى |
|--------|--------|
| `idle` | اللاعب في اللوبي ولم يدخل queue |
| `queued` | اللاعب بانتظار match |
| `challenging` | أرسل تحدياً |
| `challenged` | استلم تحدياً |
| `in_match` | لديه جلسة نشطة |
| `reconnect_available` | لديه جلسة موقوفة قابلة للاستعادة |

---

# 11. البيانات والمخزن

## 11.1 ما الموجود حالياً ويمكن إعادة استخدامه؟

الموجود حالياً:

- `minigame_types`
- `minigame_sessions`
- `minigame_session_participants`
- `minigame_leaderboards`
- إعدادات اللعبة عبر settings cascade
- lobby state in memory

## 11.2 ما الذي ينقص للكاتالوج؟

النموذج الحالي لا يكفي لتجربة كاتالوج غنية بصرياً. نحتاج طبقة metadata للعرض.

## 11.3 جدول جديد: `minigame_catalog_configs`

```text
minigame_catalog_configs {
  game_type: string PK/FK → minigame_types.id ON DELETE CASCADE
  short_description: string NOT NULL
  icon_token: string NOT NULL               -- lucide-compatible token
  accent_color: string NOT NULL             -- hex color
  hero_variant: enum NOT NULL               -- انظر 11.3.1
  card_variant: enum NOT NULL               -- انظر 11.3.1
  estimated_duration_sec: int               -- اختياري، انظر I-3
  featured: bool NOT NULL DEFAULT false
  sort_order: int NOT NULL DEFAULT 100
  availability_mode: enum NOT NULL          -- active, coming_soon, hidden, maintenance
  marketing_label: string                   -- nullable
  expected_launch_at: timestamp             -- nullable، لـ coming_soon فقط
  created_at: timestamp
  updated_at: timestamp
}
```

### 11.3.1 تعدادات الـ variants

```text
hero_variant ∈ { duel, arena, solo, party, tournament }
card_variant ∈ { standard, featured, compact, coming_soon_teaser }
availability_mode ∈ { active, coming_soon, hidden, maintenance }
```

### 11.3.2 الفهارس المطلوبة

```sql
CREATE INDEX idx_catalog_sort ON minigame_catalog_configs (availability_mode, sort_order);
CREATE INDEX idx_catalog_featured ON minigame_catalog_configs (featured) WHERE featured = true;
```

### 11.3.3 المصدر

- `minigame_types` يبقى تعريفاً تشغيلياً عاماً (player counts، plugin metadata).
- metadata الجمالية والتسويقية تعيش في `minigame_catalog_configs`.

## 11.4 الهجرة والبيانات الأولية

### 11.4.1 الهجرة

يجب إنشاء migration SQL جديدة تُضيف:
1. الجدول كاملاً
2. الفهارس في §11.3.2
3. صف أولي لـ `mutaraha` (القيم في §11.4.2)

### 11.4.2 بيانات الـ seed الأولية (مطارحة)

```json
{
  "game_type": "mutaraha",
  "short_description": "مبارزة كلمات 1v1 — فراسة واستنتاج",
  "icon_token": "lucide:swords",
  "accent_color": "#D84315",
  "hero_variant": "duel",
  "card_variant": "standard",
  "estimated_duration_sec": 300,
  "featured": true,
  "sort_order": 10,
  "availability_mode": "active",
  "marketing_label": null,
  "expected_launch_at": null
}
```

### 11.4.3 الـ Fallback عند غياب الصف

إذا طُلبت بطاقة لعبة ليس لها صف في `minigame_catalog_configs` (يحدث فقط إذا أُضيف نوع لعبة بدون seed)، الخادم يُرجع قيماً افتراضية:

```text
short_description = minigame_types.description أو ""
icon_token = "lucide:gamepad-2"
accent_color = "#64748B"   (brand-slate)
hero_variant = "arena"
card_variant = "standard"
availability_mode = "hidden"
```

هذا يمنع انهيار الـ endpoint لكنه يُسجّل تحذيراً في الـ telemetry باسم `catalog_config_missing`.

---

# 12. واجهات REST المطلوبة

## 12.1 Endpoint جديد للكاتالوج

```text
GET /api/competitions/{competition_id}/minigames/catalog
```

يرجع:

- قائمة بطاقات الألعاب بعد الدمج
- scoped على العضوية الحالية والمسابقة الحالية

السبب:

الـ endpoint الحالي `GET /api/minigames` يعرض تعريفات static فقط، ولا يكفي لبناء الكاتالوج الحقيقي لأنه لا يتضمن:

- buy-in الفعلي للمسابقة
- my_stats
- my_state
- live counts
- status resolution

## 12.2 Endpoint جديد لتفاصيل اللوبي

```text
GET /api/competitions/{competition_id}/minigames/{game_type}/lobby
```

يرجع:

- snapshot كامل للّوبي
- game meta
- my stats
- leaderboard preview

## 12.3 Endpoints موجودة يعاد استخدامها

```text
GET    /api/minigames                                                          (محتفظ بها — انظر 12.5)
GET    /api/minigames/{game_type}                                              (محتفظ بها)
GET    /api/competitions/{competition_id}/minigames/{game_type}/leaderboard
GET    /api/competitions/{competition_id}/minigames/{game_type}/stats
GET    /api/competitions/{competition_id}/minigames/{game_type}/sessions
POST   /api/competitions/{competition_id}/minigames/{game_type}/queue
DELETE /api/competitions/{competition_id}/minigames/{game_type}/queue
POST   /api/competitions/{competition_id}/minigames/{game_type}/challenge
POST   /api/competitions/{competition_id}/minigames/{game_type}/challenge/{session_id}/respond
```

## 12.4 صيغة الاستجابة للأخطاء

كل endpoint جديد يستخدم نفس نمط الأخطاء الموجود في المشروع — `HTTPException` مع
رسالة عربية في `detail`:

| الكود | السيناريو | الرسالة |
|-------|-----------|---------|
| `401` | JWT مفقود أو منتهي | `يرجى تسجيل الدخول أولاً` |
| `403` | اللاعب ليس عضواً في المسابقة | `أنت لست عضواً في هذه المسابقة` |
| `403` | kill switch في حالة emergency | `الألعاب المصغرة معطلة حالياً` |
| `404` | المسابقة غير موجودة | `المسابقة غير موجودة` |
| `404` | `game_type` غير موجود | `نوع اللعبة غير موجود` |
| `429` | تجاوز حد المعدل | `الرجاء الانتظار قليلاً` |
| `500` | خطأ خادم داخلي | `حدث خطأ غير متوقع` |

صيغة الاستجابة الموحدة (كل الـ envelope النجاح/الفشل يتبع نمط المشروع الحالي):

```json
// النجاح
{ "detail": "..." }   // لـ 2xx هذا حقل response model خاص بالـ endpoint

// الفشل
{ "detail": "رسالة عربية واضحة" }
```

## 12.5 مسار التقادم (Deprecation Path)

### 12.5.1 ما يبقى

- `GET /api/minigames` → **يبقى** كـ endpoint عالمي لاكتشاف أنواع الألعاب
  المسجّلة على مستوى المنصة. لا يعتمد على `competition_id`. لا يُرجع
  metadata عرض أو live counts — فقط قائمة أنواع الألعاب من `minigame_types`.
  يُستخدم في: الإدارة، الأدوات الإدارية، deep linking عام.

- `GET /api/minigames/{game_type}` → يبقى لنفس السبب (تفاصيل نوع لعبة عالمياً).

### 12.5.2 ما الجديد

- `GET /api/competitions/{id}/minigames/catalog` → **النسخة الغنية المُقيّدة**
  بالمسابقة. هذا هو الـ endpoint الرئيسي لصفحة الكاتالوج في الواجهة.

### 12.5.3 قاعدة الاستخدام

- الواجهة الرئيسية (كاتالوج اللاعب) → `GET /catalog`
- لوحة الإدارة → `GET /api/minigames` + `GET /api/admin/minigames`
- لا يوجد تقادم فوري؛ الـ endpoints القديمة تبقى موثّقة ومدعومة في V1 وV1.1.

---

# 13. واجهات WebSocket المطلوبة

## 13.1 قناة الكاتالوج

```text
WS /ws/competitions/{competition_id}/minigames/catalog?token={JWT}
```

### 13.1.1 المصادقة

- JWT يُمرّر عبر query parameter `token` (نفس النمط الحالي في `ws_router.py`)
- عند غياب التوكن أو فشل التحقق: إغلاق الاتصال بكود `4001` والرسالة "يرجى تسجيل الدخول"
- بعد التحقق من JWT، الخادم يُحل الـ membership لـ `competition_id`
- إذا اللاعب ليس عضواً نشطاً في المسابقة: إغلاق بكود `4003` والرسالة "أنت لست عضواً في هذه المسابقة"

### 13.1.2 Heartbeat والبقاء

- العميل يُرسل `{"type": "heartbeat"}` كل 30 ثانية
- الخادم يرد بـ `{"type": "heartbeat_ack"}`
- إذا لم يصل heartbeat خلال 90 ثانية: الخادم يُغلق الاتصال بكود `4008` والرسالة "انقطع الاتصال"

### 13.1.3 إعادة الاتصال

- عند فقد الاتصال، العميل يُعيد الاتصال ويُعيد إرسال `catalog_subscribe`
- بعد إعادة الاتصال الناجح، الخادم يُعيد إرسال `catalog_state` الكامل (وليس patches) — العميل يُعيد البناء من الصفر
- العميل يجب ألا يعتمد على patches تم تفويتها أثناء الانقطاع

### 13.1.4 السعة

- حد أقصى 500 مشترك متزامن لكل قناة `(competition_id, game_type-less catalog)` في V1
- تجاوز الحد: إغلاق آخر محاولة اتصال بكود `4013` والرسالة "الخادم ممتلئ — حاول لاحقاً"

### 13.1.5 رسائل العميل

```json
{ "type": "catalog_subscribe" }
{ "type": "catalog_unsubscribe" }
{ "type": "heartbeat" }
```

### 13.1.6 رسائل الخادم

#### `catalog_state`

اللقطة الكاملة عند الدخول (وعند إعادة الاتصال):

```json
{
  "type": "catalog_state",
  "correlation_id": "uuid",
  "games": [
    {
      "game_type": "mutaraha",
      "presence_count": 3,
      "queue_count": 1,
      "active_matches_count": 1,
      "status": "playable"
    }
  ]
}
```

#### `catalog_update`

تحديث تفاضلي محدود بحقول قابلة للتغيير فقط:

```json
{
  "type": "catalog_update",
  "correlation_id": "uuid",
  "game_type": "mutaraha",
  "patch": {
    "presence_count": 4,
    "queue_count": 2,
    "active_matches_count": 1,
    "status": "playable",
    "availability_reason": null
  }
}
```

### 13.1.7 الحقول القابلة للتعديل عبر patch

الحقول التالية فقط يمكن تحديثها عبر `catalog_update`:

```text
presence_count
queue_count
active_matches_count
recent_results_count
status
availability_reason
```

أي تغيير خارج هذه القائمة (مثل `buy_in_amount`، `my_stats`، `featured`) يتطلب
أن يُعيد العميل جلب `GET /catalog` الكامل أو انتظار `catalog_state` جديد.

### 13.1.8 رموز الإغلاق

| الكود | المعنى |
|-------|--------|
| `4001` | فشل المصادقة — JWT مفقود أو منتهي |
| `4003` | ليس عضواً في المسابقة |
| `4008` | انتهت مهلة heartbeat |
| `4013` | القناة ممتلئة |

## 13.2 قناة لوبي اللعبة

القناة الحالية تبقى:

```text
WS /ws/minigames/{game_type}/lobby
```

وتستمر باستخدام:

- `lobby_state`
- `lobby_update`
- `queue_status`
- `challenge_received`
- `challenge_sent`
- `transition_event`

---

# 14. مصادر البيانات لكل عنصر في البطاقة

| عنصر البطاقة | المصدر |
|-------------|--------|
| اسم اللعبة | `minigame_types.name` |
| الوصف المختصر | `minigame_catalog_configs.short_description` |
| عدد اللاعبين | `minigame_types.min_players/max_players` |
| player_count_label | طبقة التجميع |
| رسوم الدخول | settings cascade |
| النشاط المباشر | lobby manager + active sessions |
| إحصائياتي | `minigame_leaderboards` |
| حالة CTA | aggregator logic |
| featured/sort order | catalog config |

---

# 15. منطق التجميع (Aggregation Logic)

## 15.1 منطق الأهلية

لكل لعبة، يجب حساب:

- هل نوع اللعبة active؟
- هل اللعبة enabled في هذه المسابقة؟
- هل kill switch يمنع الإنشاء/التوفيق؟
- هل رصيد اللاعب يكفي؟
- هل اللاعب داخل queue لهذه اللعبة؟
- هل اللاعب داخل session نشطة لهذه اللعبة؟

## 15.2 منطق النشاط (Live Counts)

لكل لعبة، يجب حساب:

- `presence_count` — عدد اللاعبين الموجودين في اللوبي حالياً
- `queue_count` — عدد اللاعبين في طابور التوفيق
- `active_matches_count` — عدد الجلسات في `IN_PROGRESS` أو `OVERTIME` أو `PAUSED`
- `recent_results_count` — عدد النتائج في آخر 60 دقيقة

### 15.2.1 نطاق العدّ (Scope)

كل العدّادات **مُقيّدة بالمسابقة الحالية** (`competition_id` المرر في الـ URL).
`presence_count` يأتي من `lobby_manager` في الذاكرة (مفتاح `{game_type}:{competition_id}`).
لاعب عضو في 3 مسابقات وموجود في لوبي مطارحة في مسابقتين يُحتسب **مرة في كل مسابقة** — لا تجميع عابر للمسابقات.

## 15.3 تحديد "الجلسة النشطة" للاعب (active_session_id)

الحقل `my_state.active_session_id` في البطاقة يُحدَّد بالقاعدة التالية:

### 15.3.1 المراحل المؤهلة للاستئناف

```text
phases_eligible_for_resume = { IN_PROGRESS, OVERTIME, PAUSED }
```

- `IN_PROGRESS` / `OVERTIME` → جلسة جارية، CTA = `ارجع للمباراة`
- `PAUSED` → جلسة مُجمّدة (أحد اللاعبين انقطع)، CTA = `ارجع للمباراة`

### 15.3.2 المراحل غير المؤهلة

`CREATED` / `WAITING` / `READY` لا تُعتبر "جلسة نشطة" لأغراض CTA الاستئناف —
اللاعب لم يدخل المباراة بعد. هذه الجلسات تظهر كتحديات معلقة في اللوبي،
ليس كمباريات جارية في الكاتالوج.

### 15.3.3 قاعدة كسر التعادل

إذا وُجدت عدة جلسات مؤهلة لنفس `(player, game_type)` (حالة نادرة جداً):

1. تُفضّل `IN_PROGRESS` على `OVERTIME` على `PAUSED`
2. ضمن نفس المرحلة، تُفضّل الأحدث (`updated_at DESC`)
3. الجلسة الأولى فقط تُستخدم لـ `active_session_id`

### 15.3.4 الاستعلام المطلوب

```sql
SELECT s.id
FROM minigame_sessions s
JOIN minigame_session_participants p ON p.session_id = s.id
WHERE p.membership_id = :membership_id
  AND s.game_type = :game_type
  AND s.competition_id = :competition_id
  AND s.phase IN ('in_progress', 'overtime', 'paused')
ORDER BY
  CASE s.phase
    WHEN 'in_progress' THEN 1
    WHEN 'overtime' THEN 2
    WHEN 'paused' THEN 3
  END,
  s.updated_at DESC
LIMIT 1;
```

## 15.4 منطق CTA

الترتيب:

1. إذا عنده session نشطة (حسب §15.3) → `ارجع للمباراة`
2. إذا queued → `أنت في الطابور`
3. إذا غير مؤهل مالياً → `رصيد غير كافٍ`
4. إذا disabled/maintenance → CTA معطل
5. إذا coming_soon → `قريباً`
6. غير ذلك → `ادخل اللوبي`

## 15.5 أداء التجميع (Performance)

الكاتالوج endpoint مُقيّد بهدف **p95 < 200ms** حتى مع 20 لعبة في المسابقة.
لتحقيق ذلك، الـ aggregator **لا يجوز** أن يُنفّذ استعلاماً لكل لعبة منفصلة (N+1).
بدلاً من ذلك، يجب تجميع الاستعلامات:

### 15.5.1 نمط الاستعلامات المُجمّعة

```text
Query 1 (واحد فقط):
  SELECT * FROM minigame_types WHERE status = 'active'

Query 2 (واحد فقط):
  SELECT * FROM minigame_catalog_configs

Query 3 (واحد فقط — settings cascade batch):
  get_settings_batch([
    "minigame_buy_in",
    "minigame_daily_limit",
    "minigame_enabled",
    "minigame_kill_switch"
  ], competition_id=..., season_id=..., cycle_id=...)

Query 4 (واحد فقط — live counts مُجمّعة):
  SELECT
    game_type,
    COUNT(*) FILTER (WHERE phase IN ('in_progress','overtime','paused')) AS active_matches,
    COUNT(*) FILTER (WHERE phase = 'completed' AND completed_at > NOW() - INTERVAL '60 minutes') AS recent_results
  FROM minigame_sessions
  WHERE competition_id = :competition_id
  GROUP BY game_type

Query 5 (واحد فقط — جلسات اللاعب النشطة):
  SELECT s.id, s.game_type, s.phase
  FROM minigame_sessions s
  JOIN minigame_session_participants p ON p.session_id = s.id
  WHERE p.membership_id = :my_membership_id
    AND s.competition_id = :competition_id
    AND s.phase IN ('in_progress','overtime','paused')

Query 6 (واحد فقط — إحصائيات اللاعب عبر كل الألعاب):
  SELECT * FROM minigame_leaderboards
  WHERE membership_id = :my_membership_id
    AND competition_id = :competition_id
```

العدّ الإجمالي: **6 استعلامات SQL ثابتة** بصرف النظر عن عدد الألعاب. `presence_count` و`queue_count` يأتيان من `lobby_manager` في الذاكرة (صفر استعلامات).

### 15.5.2 التخزين المؤقت المقبول

- metadata من `minigame_catalog_configs` و`minigame_types` يمكن تخزينها في الذاكرة لمدة 60 ثانية
- settings cascade يمكن تخزينها لمدة 30 ثانية
- live counts لا تُخزن — تأتي من الاستعلام مباشرة أو من `lobby_manager`
- `my_stats` و`my_state` لا تُخزن — شخصية ومتغيرة

### 15.5.3 هدف الأداء

| المؤشر | الهدف |
|--------|------|
| p50 latency لـ `GET /catalog` | < 80ms |
| p95 latency لـ `GET /catalog` | < 200ms |
| p99 latency لـ `GET /catalog` | < 400ms |
| استعلامات SQL لكل طلب | ≤ 6 |

---

# 16. متطلبات الواجهة الأمامية

## 16.1 Grid behavior

- موبايل: عمود واحد
- تابلت: عمودان
- Desktop: 3 أعمدة
- featured game يمكن أن تأخذ full-width أو double-width

## 16.2 Motion behavior

- live card pulse خفيف
- hover/press عمق بسيط
- queue card لا تومض بشكل مزعج
- التحديثات الحية لا تعيد رسم الصفحة كاملة

## 16.3 Performance behavior

- initial catalog load يجب أن يكون قابلاً للعرض بسرعة
- websocket updates يجب أن patch state بدلاً من full reload
- الصور/hero assets يجب أن تكون optional وليست blocking

---

# 17. الإدارة والتحكم

## 17.1 ما الذي يجب أن تديره لوحة الإدارة مستقبلاً؟

- ترتيب ظهور الألعاب
- featured game
- حالة اللعبة: active / coming soon / hidden / maintenance
- الوصف القصير
- أيقونة اللعبة
- accent color
- estimated duration

## 17.2 ما الذي لا يجب أن تديره الواجهة مباشرة؟

- `min_players` و `max_players` لا ينبغي أن تتحول إلى نص يدوي في الواجهة
- player-count label ليس حقلاً إدارياً؛ هو مشتق

---

# 18. التحليلات والـ telemetry

## 18.1 أحداث واجبة

```text
minigame_catalog_viewed
minigame_catalog_time_to_first_click_ms     -- لقياس "زمن القرار" من PRD §5.2
minigame_card_impression                    -- بطاقة دخلت viewport
minigame_card_dwell_ms                      -- مدة مشاهدة البطاقة قبل الإجراء
minigame_card_clicked
minigame_lobby_viewed
minigame_lobby_time_to_action_ms            -- من دخول اللوبي إلى أول ضغطة CTA
minigame_queue_join_clicked
minigame_queue_left
minigame_challenge_sent
minigame_challenge_received
minigame_challenge_accepted
minigame_challenge_declined
minigame_resume_clicked
minigame_how_to_play_opened                 -- يقيس "فهم اللعبة من أول زيارة"
minigame_catalog_config_missing             -- تحذير — §11.4.3
```

## 18.2 أبعاد التحليل

كل حدث يُسجّل مع هذه الأبعاد الأساسية:

```text
correlation_id                  (من 8.1.1)
competition_id
game_type                       (null لحدث catalog_viewed)
player_count_label              (1v1, 2-4 لاعبين، إلخ)
card_status                     (playable, queued, in_match, ...)
source_surface                  (dashboard, banner, promo, deep_link)
membership_id                   (للقياس الشخصي)
session_id                      (عندما يكون موجوداً)
```

## 18.3 ربط الـ correlation_id

- `correlation_id` يُولّد عند كل طلب `GET /catalog`
- يُرجع في الاستجابة + في كل رسائل WebSocket اللاحقة
- يُمرّر على كل حدث telemetry من الواجهة حتى `minigame_lobby_viewed`
- بعد دخول اللوبي، يُستبدل بـ `correlation_id` جديد من `GET /lobby`

## 18.4 قياس أهداف PRD §5.2

| هدف PRD | الحدث المستخدم للقياس |
|---------|------------------------|
| `زمن القرار < 8 ثوانٍ` | `minigame_catalog_time_to_first_click_ms` p50 |
| `CTR من البطاقة إلى اللوبي = 40%` | `minigame_card_clicked / minigame_card_impression` |
| `CTR من لوحة اللاعب إلى الكاتالوج = 25%` | `minigame_catalog_viewed` مع `source_surface=dashboard` |
| `التحويل من اللوبي إلى queue/challenge = 35%` | `(queue_join + challenge_sent) / minigame_lobby_viewed` |
| `فهم اللعبة من أول زيارة = 80%` | `1 - (minigame_how_to_play_opened / minigame_lobby_viewed)` تقريبياً، أو استبيان in-product |

---

# 19. الأمن والخصوصية

- الكاتالوج لا يكشف أسرار اللعب
- النشاط المباشر يُعرض على شكل counts أو aliases فقط حسب قواعد اللوبي
- الألعاب غير المفعلة لا تعطي العميل تفاصيل تشغيلية حساسة
- player eligibility reasons لا تكشف تفاصيل داخلية زائدة عن اللزوم

---

# 20. الأداء والتوسع

## 20.1 متطلبات V1

- عدد الألعاب قليل، لكن العقد يجب أن يتحمل 20+ لعبة مستقبلاً
- لا يجوز فتح socket منفصل لكل بطاقة
- يجب أن يكون هناك channel واحد للكاتالوج

## 20.2 متطلبات مستقبلية

- نقل catalog summary إلى Redis/pub-sub عند الانتقال إلى multi-node
- تجميع counts خارج request path إن لزم
- caching خفيف للـ catalog metadata

---

# 21. فجوات مع الوضع الحالي

الحالة الحالية في المحرك توفر جزءاً من المطلوب، لكنها لا تكفي وحدها للكاتالوج النهائي.

الفجوات الرئيسية:

1. `GET /api/minigames` لا يرجع read model غني للبطاقات
2. لا يوجد catalog-wide websocket summary
3. لا يوجد metadata presentation layer رسمي للبطاقات
4. لا يوجد endpoint موحد لتفاصيل lobby page
5. لا يوجد derived player-count label في response contracts الحالية

---

# 22. مراحل التنفيذ المقترحة

## المرحلة A — Read Model Foundation

- إضافة `minigame_catalog_configs`
- بناء catalog aggregation service
- بناء lobby detail service

## المرحلة B — API + WebSocket

- `GET /catalog`
- `GET /{game_type}/lobby`
- `WS /catalog`

## المرحلة C — Frontend

- بناء صفحة الكاتالوج
- بناء بطاقة اللعبة
- بناء صفحة لوبي اللعبة

## المرحلة D — Admin

- إدارة ترتيب البطاقات والحالة والهوية البصرية المختصرة

---

# 23. معايير القبول التقنية

## 23.1 الكاتالوج

- يوجد endpoint واحد يُرجع كل البيانات اللازمة للبطاقات
- كل عنصر card يُرجع `min_players`, `max_players`, و `player_count_label`
- status resolution يتم في الخادم
- live counts قابلة للتحديث دون refresh كامل

## 23.2 اللوبي

- يوجد endpoint موحد للتحميل الأولي للّوبي
- WebSocket اللوبي يبقي الصفحة محدثة
- queue/challenge/resume state ينعكس في الواجهة بشكل موحد

## 23.3 إدارة البيانات

- presentation metadata منفصلة عن core engine metadata
- لا يوجد نص player-count hardcoded في الواجهة
- fallback behavior واضح إذا نقصت metadata

---

# 24. الخلاصة

لكي تكون الألعاب المصغرة منتجاً واضحاً داخل حرب الأسماء، نحتاج طبقة كاتالوج ولوبي حقيقية، لا مجرد روابط لصفحات داخلية.

القراران الأهم في هذه الوثيقة هما:

1. **بطاقة اللعبة read model مجمّع وليست model خام**
2. **عدد اللاعبين يُعد معلومة product-critical ويجب أن يُرسل ويُعرض بشكل رسمي في كل بطاقة ولوبي**

هذا يضمن أن أي لعبة جديدة تضاف لاحقاً تدخل تلقائياً ضمن تجربة اكتشاف مفهومة وقابلة للتوسع.
