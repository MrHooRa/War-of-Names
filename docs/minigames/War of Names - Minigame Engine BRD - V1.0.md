BRD — وثيقة المتطلبات التجارية والوظيفية لمحرك الألعاب المصغرة
مشروع: حرب الأسماء — محرك الألعاب المصغرة (Minigame Engine)
الإصدار: V1.0
التاريخ: 2026-03-30
الكاتب: Claude (بإشراف Salman)
اللغة الأساسية: العربية
نوع المنتج: Engine / Framework
النطاق: محرك مشترك يدعم تسجيل وتشغيل ألعاب مصغرة متعددة داخل منصة حرب الأسماء

---

# 1. الملخص التنفيذي

محرك الألعاب المصغرة هو بنية تحتية مشتركة تُمكّن من تسجيل وتشغيل ألعاب مصغرة متعددة داخل منصة حرب الأسماء. المحرك يوفر كل ما تحتاجه أي لعبة مصغرة دون أن تُعيد بناءه:

- نظام تسجيل الألعاب (Plugin Registry)
- دورة حياة الجلسات (Session Lifecycle)
- اللوبي والحضور المباشر (Lobby & Presence)
- التوفيق بين اللاعبين (Matchmaking)
- لوحة ترتيب لكل لعبة (Per-Game Leaderboard)
- جسر الاقتصاد مع دفتر النقاط (Economy Bridge → Ledger)
- إعدادات متدرجة (Settings Cascade)
- لوحة تحكم إدارية (Admin Framework)
- اتصال فوري عبر WebSocket (Real-Time Communication)
- مكافحة الاستغلال (Anti-Abuse Policy Engine)
- بروتوكول الموثوقية (Reliability Protocol)

كل لعبة مصغرة جديدة تُسجّل كـ Plugin وتُعرّف فقط منطقها الخاص (القواعد، الأدوات، شروط الفوز، التسوية). المحرك يتولى كل شيء آخر.

---

# 2. الهدف من الوثيقة

- تحديد معمارية محرك الألعاب المصغرة بالكامل
- توضيح العقد بين المحرك والألعاب (Plugin Contract)
- تحديد بروتوكولات الموثوقية: الإجراءات المصادق عليها، التزامن، التسوية، إعادة الاتصال
- تحديد نموذج التخزين، رسائل WebSocket، ومفاتيح الإيقاف
- تحديد سياسات مكافحة الاستغلال والمراقبة
- وضع أساس قابل للتوسع — اللعبة الثانية تُبنى بـ 20% من الجهد

---

# 3. المبادئ المعمارية

## 3.1 محركات لا سكريبتات

كل قدرة مشتركة تُبنى مرة واحدة في المحرك. اللعبة المصغرة لا تُعيد بناء اللوبي أو التوفيق أو التسوية — تستخدم ما يوفره المحرك.

## 3.2 الخادم هو المرجع الوحيد (Server-Authoritative)

كل منطق اللعبة يُنفذ على الخادم. العميل يُرسل أوامر (inputs)، الخادم يُعالج ويُعيد النتائج. لا نثق بأي حساب من العميل.

## 3.3 الدفتر هو مصدر الحقيقة المالية

كل عملية نقاط (شراء دخول، مكافأة فائز، غرامة انسحاب) تمر عبر `LedgerEntry`. لا تعديل مباشر على الرصيد.

## 3.4 كل تغيير حالة يُسجّل

سجل تدقيق (Audit Trail) لكل: إنشاء جلسة، إجراء لاعب، انتقال حالة، تسوية، تدخل إداري.

## 3.5 الإعدادات فوق الترميز الصلب

كل قيمة قابلة للتغيير (مدة الدور، تكلفة الأدوات، حد المباريات اليومي) تأتي من إعدادات مُهيكلة، ليست ثوابت في الكود.

---

# 4. طبقات المحرك

## 4.1 الطبقة المشتركة (Shared Engine Layer)

تخدم جميع الألعاب المصغرة. تُبنى مرة واحدة.

| المكوّن | المسؤولية |
|---------|----------|
| سجل الألعاب (Game Type Registry) | تسجيل كل لعبة كـ Plugin بواجهة موحدة |
| مدير الجلسات (Session Manager) | آلة الحالة: إنشاء → انتظار → جاهز → جارٍ → منتهي |
| نظام اللوبي (Lobby System) | حضور مباشر، عدد اللاعبين، نتائج حديثة |
| نظام التوفيق (Matchmaking) | تحدي مباشر + طابور تلقائي |
| لوحة الترتيب (Leaderboard) | ترتيب لكل لعبة لكل مسابقة |
| جسر الاقتصاد (Economy Bridge) | خصم الدخول، صرف المكافأة، غرامة الانسحاب |
| سلسلة الإعدادات (Settings Cascade) | عالمي → مسابقة → موسم → دورة |
| إطار الإدارة (Admin Framework) | قسم "الألعاب المصغرة" في لوحة التحكم |
| طبقة WebSocket | غرفة لكل جلسة نشطة، حضور اللوبي |
| محرك السياسات (Policy Engine) | حدود يومية، مصفوفة الخصوم، تسجيل المخاطر |
| بروتوكول الموثوقية (Reliability) | أرقام المراجعة، عدم التكرار، التسوية الآمنة |

## 4.2 طبقة اللعبة (Game Plugin Layer)

كل لعبة مصغرة تُعرّف فقط:

| المكوّن | ما تُعرّفه اللعبة |
|---------|------------------|
| قواعد اللعب | هيكل الأدوار، أنواع الإجراءات، شروط الفوز |
| التحقق من الإجراءات | أي إجراء مسموح في أي حالة |
| معالجة الإجراءات | ماذا يحدث عند تنفيذ إجراء (حساب تلميحات، فحص تخمينات) |
| التسجيل | كيف تُحسب المكافآت والعقوبات |
| مخطط الإعدادات | إعدادات خاصة باللعبة (عدد الأدوار، المؤقت، تكاليف الأدوات) |
| نماذج البيانات | جداول خاصة باللعبة (بنك الكلمات، الجولات، استخدام الأدوات) |

---

# 5. عقد اللعبة المصغرة (Plugin Contract)

## 5.1 تعريف اللعبة (GameTypePlugin)

```
GameTypePlugin {
  id: string                          // معرّف فريد: "mutaraha", "quiz_duel"
  name: string                        // اسم العرض: "مطارحة"
  description: string                 // وصف مختصر
  plugin_api_version: string          // إصدار واجهة المحرك: "1.0"
  settings_schema_version: string     // إصدار مخطط الإعدادات: "1.0"

  // أعلام القدرات
  supports_overtime: bool
  supports_spectators: bool
  supports_ranked: bool
  supports_team_mode: bool

  min_players: int
  max_players: int

  // خطافات دورة الحياة (Lifecycle Hooks)
  validate_settings(settings) → errors[]
  init_session_state(config) → initial_game_state
  validate_action(action, state) → valid | error
  apply_action(action, state) → new_state + side_effects[]
  evaluate_terminal(state) → terminal_result | null
  evaluate_overtime(state) → overtime_state | null
  compute_settlement(terminal_result) → settlement_instruction
  build_public_view(state, viewer_membership_id) → sanitized_state

  // خطافات الترحيل
  migrate_settings(old_version, new_version, data) → migrated_data
  migrate_session(old_version, new_version, data) → migrated_data
}
```

## 5.2 شرح خطافات دورة الحياة

| الخطاف | متى يُستدعى | ماذا يفعل |
|--------|-------------|----------|
| `validate_settings` | عند حفظ إعدادات اللعبة من لوحة الإدارة | يتحقق من صحة القيم (مثل: عدد الأدوار > 0) |
| `init_session_state` | عند إنشاء جلسة جديدة | يُنشئ الحالة الأولية للعبة (اختيارات فارغة، دور 0) |
| `validate_action` | عند استلام إجراء من لاعب | يتحقق: هل الإجراء مسموح الآن؟ (مثل: هل هذا دور اللاعب؟) |
| `apply_action` | بعد التحقق بنجاح | يُنفذ الإجراء ويُحدّث الحالة (مثل: كشف حرف، تسجيل تخمين) |
| `evaluate_terminal` | بعد كل إجراء | يفحص: هل اللعبة انتهت؟ (مثل: خمّن كل 5 كلمات) |
| `evaluate_overtime` | عند انتهاء الأدوار العادية بتعادل | يُقرر هل ندخل الوقت الإضافي وبأي إعدادات |
| `compute_settlement` | عند الوصول لحالة نهائية | يحسب: من الفائز، كم يربح، كم يخسر الخاسر |
| `build_public_view` | عند إرسال الحالة للاعب | يُخفي المعلومات السرية (كلمات الخصم المخفية) |

## 5.3 أعلام القدرات (Capability Flags)

| العلم | الوصف | التأثير |
|-------|------|--------|
| `supports_overtime` | اللعبة تدعم وقتاً إضافياً | المحرك يستدعي `evaluate_overtime` عند التعادل |
| `supports_spectators` | تدعم المشاهدة (مستقبلي) | المحرك يفتح مقاعد مشاهدة في الغرفة |
| `supports_ranked` | تدعم التصنيف بالمهارة | المحرك يستخدم ELO في التوفيق |
| `supports_team_mode` | تدعم فرق (مستقبلي) | المحرك يُدير تشكيل الفرق |

## 5.4 إصدارات العقد والترحيل

```
plugin_api_version: "1.0"
  — المحرك يتحقق من التوافق عند التسجيل
  — إذا أصدر المحرك "2.0" واللعبة ما زالت "1.0"، يُفعّل طبقة التوافق

settings_schema_version: "1.0"
  — عند تحديث المخطط، يُستدعى migrate_settings
  — الجلسات النشطة تستمر بالإعدادات القديمة
  — الجلسات الجديدة تستخدم المخطط المُحدّث
```

---

# 6. آلة حالة الجلسة (Session State Machine)

## 6.1 الحالات

```
CREATED ──→ WAITING ──→ READY ──→ IN_PROGRESS ──→ COMPLETED
   │            │          │           │                │
   │            │          │           ├──→ OVERTIME ───┘
   │            │          │           │
   │            │          │           ├──→ PAUSED ──→ (resume or abandon)
   │            │          │           │
   └────────────┴──────────┴───────────┴──→ CANCELLED
                                       │
                                       └──→ ABANDONED
```

## 6.2 تعريف كل حالة

| الحالة | الوصف | من يُفعّلها | المدة القصوى |
|--------|------|------------|-------------|
| `CREATED` | سجل الجلسة أُنشئ، المُتحدي أرسل الدعوة | النظام | 120 ثانية |
| `WAITING` | بانتظار خصم (طابور) أو بانتظار القبول (تحدي) | النظام | 120 ثانية |
| `READY` | كلا اللاعبين متصلان، العد التنازلي يعمل | النظام | 5 ثوانٍ |
| `IN_PROGRESS` | اللعبة جارية، الأدوار تتناوب | النظام | يعتمد على إعدادات اللعبة |
| `OVERTIME` | تعادل، أدوار إضافية بقواعد مشددة | اللعبة (evaluate_overtime) | يعتمد على إعدادات اللعبة |
| `PAUSED` | لاعب انقطع، مهلة إعادة الاتصال تعمل | النظام | 60 ثانية (قابل للتعديل) |
| `COMPLETED` | انتهت طبيعياً مع فائز/خاسر أو تعادل | اللعبة (evaluate_terminal) | نهائية |
| `CANCELLED` | ألغيت بواسطة المشرف أو النظام | المشرف/النظام | نهائية |
| `ABANDONED` | لاعب انقطع ولم يعد خلال المهلة | النظام | نهائية |

## 6.3 قواعد الانتقال

| من | إلى | الشرط |
|----|-----|------|
| `CREATED` | `WAITING` | الدعوة أُرسلت أو اللاعب دخل الطابور |
| `CREATED` | `CANCELLED` | انتهت المهلة أو إلغاء يدوي |
| `WAITING` | `READY` | الخصم قَبِل أو التوفيق التلقائي وجد خصماً |
| `WAITING` | `CANCELLED` | انتهت المهلة أو اللاعب ألغى |
| `READY` | `IN_PROGRESS` | انتهى العد التنازلي (٣...٢...١) |
| `READY` | `CANCELLED` | لاعب انقطع قبل البدء |
| `IN_PROGRESS` | `COMPLETED` | `evaluate_terminal` أعاد نتيجة نهائية |
| `IN_PROGRESS` | `OVERTIME` | الأدوار انتهت + تعادل + `supports_overtime` |
| `IN_PROGRESS` | `PAUSED` | لاعب انقطع |
| `IN_PROGRESS` | `ABANDONED` | لاعب انقطع + انتهت مهلة الإيقاف |
| `IN_PROGRESS` | `CANCELLED` | تدخل إداري |
| `OVERTIME` | `COMPLETED` | `evaluate_terminal` أعاد نتيجة نهائية |
| `OVERTIME` | `ABANDONED` | لاعب انقطع + انتهت المهلة |
| `PAUSED` | `IN_PROGRESS` | اللاعب أعاد الاتصال |
| `PAUSED` | `ABANDONED` | انتهت مهلة الإيقاف |

## 6.4 ضمانات الحالة النهائية

- **مسار نهائي واحد فقط**: بمجرد الوصول لـ `COMPLETED` أو `CANCELLED` أو `ABANDONED`، لا يمكن أي انتقال آخر. كل الإجراءات تُرفض.
- **تسوية واحدة فقط**: التسوية المالية تُنفّذ مرة واحدة فقط لكل جلسة (قيد فريد على `session_id` في جدول التسويات).

## 6.5 المراحل الداخلية للعبة (Plugin Sub-Phases)

حالة `IN_PROGRESS` في المحرك تشمل عدة مراحل داخلية تُديرها اللعبة عبر `game_state.game_phase`. مثال: مطارحة تستخدم مراحل `word_selection → battle → overtime → finished` داخل `IN_PROGRESS`.

قواعد التفاعل مع المحرك:

- المؤقتات الداخلية (مثل مهلة اختيار الكلمات) تُديرها اللعبة عبر `turn_started_at` + `turn_duration_ms`
- عند الانقطاع: حالة PAUSED في المحرك تُجمّد كل المؤقتات — بما فيها مؤقتات اللعبة الداخلية
- عند إعادة الاتصال: المحرك يُستأنف المؤقتات — اللعبة تحسب الوقت المتبقي من `(turn_started_at + duration) - now()`
- المرحلة الداخلية لا تؤثر على آلة حالة المحرك — المحرك يرى فقط IN_PROGRESS

---

# 7. بروتوكول الإجراءات المصادق عليها (Authoritative Action Protocol)

## 7.1 غلاف الإجراء (Action Envelope)

كل إجراء من اللاعب يُغلّف بهذا الشكل:

```
ActionEnvelope {
  action_id: UUID                    // مُعرّف فريد للإجراء (يولّده العميل)
  session_id: UUID                   // أي جلسة
  actor_membership_id: int           // من يتصرف
  action_type: string                // "guess", "tool_letter_check", إلخ
  payload: JSON                      // بيانات خاصة بالإجراء
  client_seq: int                    // عداد تصاعدي من العميل
  state_revision: int                // آخر رقم مراجعة عرفه العميل
  sent_at: timestamp                 // ساعة العميل (للتتبع فقط، لا للسلطة)
}
```

## 7.2 قواعد التحقق على الخادم

| القاعدة | الآلية | عند الفشل |
|--------|-------|----------|
| **عدم التكرار** | `action_id` يُخزّن في `action_receipts`. التكرار يُعيد الاستجابة المخزنة | إعادة الاستجابة السابقة |
| **رفض القديم** | `state_revision < server_revision` | خطأ `STALE_STATE` + لقطة الحالة الحالية |
| **التسلسل** | `client_seq` يجب أن يكون تصاعدياً لكل لاعب في كل جلسة | خطأ `INVALID_SEQUENCE` |
| **سلطة الدور** | الخادم يتحقق أن الإجراء من اللاعب صاحب الدور الحالي | خطأ `NOT_YOUR_TURN` |
| **صلاحية الحالة** | الإجراء يُمرّر لـ `validate_action` الخاص باللعبة | خطأ مع رسالة عربية |
| **حد المعدل** | حد أقصى لعدد الإجراءات في الثانية لكل لاعب | خطأ `RATE_LIMITED` |

## 7.3 تدفق معالجة الإجراء

```
1. العميل يُرسل ActionEnvelope عبر WebSocket
2. الخادم يتحقق: action_id فريد؟ state_revision صحيح؟ client_seq تصاعدي؟
3. الخادم يستدعي plugin.validate_action(action, current_state)
4. إذا صحيح: plugin.apply_action(action, current_state) → new_state + side_effects
5. state_revision يزداد بـ 1
6. الخادم يُخزّن:
   — الحالة الجديدة في minigame_sessions (مع القفل المتفائل)
   — الحدث في minigame_session_events
   — الإيصال في minigame_action_receipts
7. الخادم يُرسل action_ack للاعب + state_patch لكلا اللاعبين
8. الخادم يستدعي plugin.evaluate_terminal(new_state)
9. إذا انتهت: انتقال إلى COMPLETED → تشغيل التسوية
```

---

# 8. التزامن واتساق الحالة (Concurrency & State Consistency)

## 8.1 نموذج حالة الجلسة

```
SessionState {
  revision: int               // يزداد مع كل تغيير (إجراء أو انتقال)
  current_turn: enum          // PLAYER_1 | PLAYER_2
  turn_number: int            // عداد الأدوار الكلي
  phase: SessionPhase         // موقع آلة الحالة
  game_state: JSON            // حالة خاصة باللعبة (يُديرها الـ Plugin)
  settings_snapshot: JSON     // لقطة الإعدادات الفعالة عند إنشاء الجلسة
  turn_started_at: timestamp  // بداية الدور الحالي (لحساب المؤقت)
  updated_at: timestamp       // ساعة الخادم
}
```

## 8.2 القفل المتفائل (Optimistic Locking)

كل عملية كتابة على الجلسة تستخدم:

```sql
UPDATE minigame_sessions
SET state = $new_state, revision = revision + 1
WHERE id = $session_id AND revision = $expected_revision
```

إذا لم تتطابق المراجعة → الكتابة تفشل → إعادة المحاولة أو رفض الإجراء.

## 8.3 ضمان المسار النهائي الواحد

```
— الحالات النهائية: COMPLETED, CANCELLED, ABANDONED
— بمجرد الوصول لحالة نهائية:
  1. كل الإجراءات تُرفض (الخادم يتحقق من phase قبل أي معالجة)
  2. لا يمكن أي انتقال آخر
  3. التسوية تُنفّذ مرة واحدة (قيد فريد)
```

---

# 9. التسوية الآمنة (Settlement Safety)

## 9.1 آلة حالة التسوية

```
PENDING_SETTLEMENT ──→ SETTLED
        │                   │
        │                   └──→ (مكتمل، غير قابل للتغيير)
        │
        └──→ FAILED ──→ RECONCILED
                  │
                  └──→ FAILED (إعادة محاولة، حد أقصى 3)
```

## 9.2 نموذج التسوية

```
SessionSettlement {
  id: UUID
  session_id: UUID (فريد — تسوية واحدة لكل جلسة)
  winner_membership_id: int
  loser_membership_id: int
  winner_payout: int              // المبلغ النهائي للفائز
  loser_penalty: int              // المبلغ المخصوم من الخاسر
  settlement_state: PENDING | SETTLED | FAILED | RECONCILED
  ledger_entry_ids: int[]         // مراجع لسجلات الدفتر
  correlation_id: UUID            // معرّف التتبع الشامل
  settled_at: timestamp
  failure_reason: string
  retry_count: int (حد أقصى 3)
  created_at: timestamp
}
```

## 9.3 ضمانات التسوية

| الضمان | الآلية |
|--------|-------|
| **عدم التسوية الجزئية** | صندوق المعاملات (Transactional Outbox): دفتر + تدقيق + إشعارات في معاملة واحدة |
| **عدم التسوية المزدوجة** | قيد فريد على `session_id` في جدول التسويات |
| **قابلية إعادة التشغيل** | وظيفة التسوية مفتاحها `session_id` — تشغيلها مرتين على نفس الجلسة لا يُنتج أثراً مزدوجاً |
| **معالجة الفشل** | عند فشل التسوية: تسجيل في `dead_letter`، إعادة محاولة بتراجع أُسي (حد 3)، تنبيه المشرف |

## 9.4 أنواع التسوية

| السيناريو | تسوية الفائز | تسوية الخاسر |
|----------|-------------|-------------|
| فوز طبيعي | +مبلغ الدخول - تكاليف الأدوات | -مبلغ الدخول |
| انسحاب (الخاسر) | +كامل مبلغ الدخول | -مبلغ الدخول |
| هجر (الخاسر) | +كامل مبلغ الدخول | -مبلغ الدخول |
| إلغاء إداري | +استرداد الدخول | +استرداد الدخول |
| انقطاع الاثنين | +استرداد الدخول | +استرداد الدخول |

---

# 10. بروتوكول الانقطاع وإعادة الاتصال (Disconnect/Reconnect)

## 10.1 تدفق الانقطاع

```
1. الخادم يكتشف انقطاع WebSocket
2. الجلسة تنتقل إلى PAUSED
3. مؤقت الدور يتجمد
4. مؤقت المهلة يبدأ (grace_timer، افتراضي 60 ثانية)
5. الخصم يرى: "الخصم انقطع... ⏳" مع عد تنازلي
```

## 10.2 تدفق إعادة الاتصال

```
1. عند بدء الجلسة، كل لاعب يحصل على reconnect_token (صالح طوال الجلسة)
2. العميل يُرسل: reconnect_claim { session_id, reconnect_token, last_known_revision }
3. الخادم يتحقق من التوكن
   ملاحظة: رمز إعادة الاتصال (reconnect_token) يُضمّن في رسالة game_state الأولى التي تُرسل عند بدء الجلسة. هذا يضمن أن العميل يحصل على التوكن مع أول لقطة حالة.
4. الخادم يُرسل لقطة كاملة للحالة من last_known_revision
5. مؤقت المهلة يُلغى، مؤقت الدور يُستأنف
6. اللعبة تستمر طبيعياً
```

## 10.3 سيناريوهات خاصة

| السيناريو | النتيجة |
|----------|--------|
| لاعب واحد ينقطع + لا يعود خلال المهلة | الجلسة `ABANDONED`، المنقطع يخسر الدخول |
| كلا اللاعبين ينقطعان | مهلة تعمل لكليهما. أول من يعود: اللعبة تستأنف. لا أحد يعود: `CANCELLED`، استرداد للاثنين |
| الخادم يُعاد تشغيله وسط المباراة | حالة الجلسة محفوظة في قاعدة البيانات (تُحفظ مع كل إجراء). الجلسات النشطة تُحمّل من DB عند إعادة التشغيل. إعادة اتصال WebSocket تُفعّل لكل المشاركين. مؤقت الدور يُعاد حسابه: `(turn_started_at + duration) - now()` |
| انقطاع أثناء التسوية | التسوية تكتمل بغض النظر عن حالة الاتصال (عملية خادم بحتة) |

## 10.4 ما يُحفظ ومتى

| الحدث | ما يُحفظ | أين |
|-------|---------|-----|
| كل إجراء | الحالة الكاملة + الحدث + الإيصال | PostgreSQL |
| كل انتقال حالة | الحالة + سبب الانتقال | PostgreSQL |
| حضور اللوبي | من متصل الآن | Redis (عابر) |
| حالة الجلسة الساخنة | نسخة سريعة القراءة | Redis (cache) |

---

# 11. نظام اللوبي والحضور (Lobby & Presence)

## 11.1 المفهوم

كل لعبة مصغرة لها لوبي مباشر — فضاء حي يرى فيه اللاعبون من موجود ومن يلعب ونتائج المباريات الأخيرة. ليس مجرد زر "ابحث عن خصم".

## 11.2 بيانات اللوبي

```
LobbyState {
  game_type: string
  competition_id: int
  online_players: [
    {
      membership_id: int,
      alias: string,
      status: "idle" | "in_queue" | "in_match" | "challenging",
      stats: { wins: int, losses: int, streak: int, win_rate: float }
    }
  ]
  active_matches: int                    // عدد المباريات الجارية الآن
  recent_results: [                      // آخر 5 نتائج
    { winner_alias, loser_alias, duration_sec, finished_at }
  ]
}
```

## 11.3 مؤشرات جذب اللاعبين

| المؤشر | أين يظهر | الغرض |
|--------|---------|------|
| نبضة/توهج على أيقونة اللعبة | صفحة الألعاب المصغرة الرئيسية | يجذب اللاعبين عندما يكون اللوبي نشطاً |
| "٣ لاعبين في اللوبي الآن 🟢" | بطاقة اللعبة | يُخبر اللاعب أن هناك من ينتظر |
| شريط نتائج حديثة | داخل اللوبي | يُظهر أن المباريات تحدث فعلاً |

## 11.4 التواصل

- الحضور يُدار عبر Redis (عابر)
- تحديثات اللوبي عبر WebSocket: `lobby_state` (كامل عند الدخول) + `lobby_update` (تفاضلي)
- عند دخول اللوبي: اشتراك في غرفة `lobby:{game_type}:{competition_id}`
- عند الخروج: إلغاء الاشتراك

---

# 12. نظام التوفيق (Matchmaking)

## 12.1 وضعان

### التحدي المباشر (Challenge)

```
1. اللاعب يرى الخصوم في اللوبي (الحالة: idle)
2. يضغط "تحدي" بجانب لقب الخصم
3. النظام يُنشئ جلسة بحالة CREATED
4. الخصم يتلقى إشعاراً داخل اللوبي (ليس في الإشعارات العامة)
5. الخصم لديه 60 ثانية للقبول أو الرفض
6. قبول → WAITING → READY → بدء اللعبة
7. رفض أو انتهاء المهلة → CANCELLED (بدون عقوبة)
```

### الطابور التلقائي (Queue)

```
1. اللاعب يضغط "مستعد للمبارزة"
2. يدخل طابور التوفيق (حالته تتغير في اللوبي لـ "in_queue")
3. الطابور مجهول — لا يُظهر من ينتظر بالتحديد
4. النظام يُطابق أول لاعبين متاحين (FIFO)
5. التطابق → جلسة WAITING → READY → بدء اللعبة
6. إذا لم يُوجد خصم خلال 120 ثانية: إشعار "لا يوجد خصوم متاحين حالياً"
```

## 12.2 سياسات التوفيق

```
MatchmakingPolicy {
  // عدالة الطابور
  queue_order: FIFO
  max_queue_wait: 120 sec

  // مكافحة الاستغلال
  same_opponent_cooldown: cycle          // لا إعادة مبارزة نفس الخصم في نفس الدورة
  // ملاحظة: same_opponent_cooldown في المحرك هو الحد الأقصى العام. كل لعبة يمكن أن تُعرّف حدها الخاص
  // (مثل mutaraha_same_opponent_limit) الذي يجب أن يكون ≤ حد المحرك. المحرك يتحقق من حده أولاً، ثم يستشير اللعبة.
  rematch_cooldown: 24 hours
  daily_cap: 2 per player                // قابل للتعديل من المشرف
  min_balance: configurable              // يجب أن يملك ثمن الدخول

  // مكافحة التلصص
  queue_anonymity: true                  // الطابور لا يكشف هوية المنتظرين
  challenge_recipient_hidden: true       // لا أحد يرى التحديات المعلقة

  // عقوبات الإلغاء حسب المرحلة
  cancel_in_queue: free
  cancel_after_accept: -50 pts
  cancel_mid_game: forfeit (كامل الدخول)

  // تصنيف المهارة (اختياري، يُفعّله المشرف)
  rating_system: ELO
  initial_rating: 1000
  k_factor: 32
  match_by_rating: false (معطل افتراضياً — المجموعات الصغيرة)
}
```

قاعدة الأسبقية: كلا القيدين يُطبّقان بالتوازي — الأكثر تقييداً يسري. في الممارسة: `same_opponent_cooldown: cycle` مع حد اللعبة 1 لكل دورة يعني عدم إمكانية إعادة المبارزة مع نفس الخصم في نفس الدورة نهائياً، مما يجعل `rematch_cooldown: 24h` غير مؤثر في هذا السيناريو. لكنه يبقى مفيداً لألعاب مصغرة مستقبلية تسمح بأكثر من مبارزة واحدة مع نفس الخصم.

---

# 13. جسر الاقتصاد (Economy Bridge)

## 13.1 المبدأ

كل عملية مالية في الألعاب المصغرة تمر عبر `LedgerEntry` الموجود. لا رصيد مباشر.

## 13.2 أنواع الدفتر الجديدة

```
LedgerEntryType (إضافات):
  MINIGAME_BUY_IN          // خصم مبلغ الدخول عند بدء الجلسة
  MINIGAME_PAYOUT          // صرف المكافأة للفائز
  MINIGAME_FORFEIT         // خصم الدخول عند الانسحاب/الهجر
  MINIGAME_REFUND          // استرداد عند الإلغاء الإداري
  MINIGAME_CANCEL_PENALTY  // غرامة الإلغاء بعد القبول
```

MINIGAME_CANCEL_PENALTY — خصم 50 نقطة من اللاعب الذي يُلغي بعد قبول التحدي (حالة READY). لا تعويض للخصم. النقاط تُزال من النظام (deflationary).

## 13.3 تدفق مالي نموذجي (Zero-Sum)

```
بداية الجلسة:
  — اللاعب 1: DEBIT 500 (MINIGAME_BUY_IN)
  — اللاعب 2: DEBIT 500 (MINIGAME_BUY_IN)

نهاية الجلسة (فوز طبيعي):
  — الفائز: CREDIT 1000 (MINIGAME_PAYOUT)
  — الخاسر: لا شيء إضافي (خسر الدخول فقط)

نهاية الجلسة (هجر):
  — الباقي (فائز): CREDIT 1000 (MINIGAME_PAYOUT)
  — المنقطع (خاسر): لا شيء إضافي (خسر الدخول)

إلغاء إداري:
  — اللاعب 1: CREDIT 500 (MINIGAME_REFUND)
  — اللاعب 2: CREDIT 500 (MINIGAME_REFUND)
```

## 13.4 قيود الاقتصاد

- الرصيد لا يمكن أن ينزل تحت 0 (القيد الحالي في النظام)
- اللاعب المفلس لا يمكنه الدخول في مبارزة
- مبلغ الدخول قابل للتعديل من المشرف (ليس مبرمجاً بقيمة ثابتة)

---

# 14. سلسلة الإعدادات (Settings Cascade)

## 14.1 ترتيب الحل (الأخير يفوز)

```
global_defaults
  → game_type_defaults
    → competition_override
      → season_override
        → cycle_override
```

## 14.2 محلل حتمي (Deterministic Resolver)

```python
def get_effective_settings(game_type, competition_id, season_id=None, cycle_id=None):
    """
    يُعيد لكل إعداد:
      - القيمة الفعالة
      - مستوى المصدر (أي طبقة حددت هذه القيمة)
      - معرّف المصدر
    """
    settings = {}
    for level in [global, game_type, competition, season, cycle]:
        overrides = load_overrides(level)
        for key, value in overrides:
            settings[key] = {
                "value": value,
                "source_level": level.name,
                "source_id": level.id
            }
    return settings
```

## 14.3 لقطة الإعدادات عند بدء الجلسة

- عند إنشاء جلسة: تُحفظ لقطة الإعدادات الفعالة في سجل الجلسة
- اللعبة تعمل بالقيم المحفوظة (محصّنة ضد تغييرات المشرف وسط المباراة)
- السجل يحتفظ بالمراجع للمصادر الأصلية (للتدقيق)

## 14.4 واجهة الشرح للمشرف

```
GET /api/admin/minigames/{type}/settings/explain
    ?competition_id=X&season_id=Y&cycle_id=Z

يُعيد لكل إعداد:
{
  "buy_in_amount": {
    "effective_value": 500,
    "source": "competition",
    "override_chain": [
      { "level": "global", "value": 500 },
      { "level": "competition", "value": 500 }  // ← هذا هو المصدر
    ]
  }
}
```

---

# 15. لوحة الترتيب لكل لعبة (Per-Game Leaderboard)

## 15.1 المبدأ

كل لعبة مصغرة لها لوحة ترتيب مستقلة داخل كل مسابقة. منفصلة تماماً عن لوحة ترتيب المسابقة الرئيسية.

## 15.2 نموذج الترتيب

```
MinigameLeaderboardEntry {
  game_type: string
  competition_id: int
  membership_id: int
  wins: int
  losses: int
  win_rate: float
  current_streak: int
  best_streak: int
  total_matches: int
  avg_tools_used: float           // متوسط الأدوات المستخدمة لكل فوز
  avg_match_duration_sec: float
  elo_rating: int (nullable)      // إذا كان التصنيف مُفعّلاً
  rank: int (محسوب)
  updated_at: timestamp
}
```

## 15.3 معيار الترتيب

الترتيب الافتراضي حسب عدد الانتصارات. كسر التعادل:

```
1. الأكثر انتصارات
2. أعلى نسبة فوز (مع حد أدنى 5 مباريات)
3. أطول سلسلة انتصارات
4. أقل متوسط أدوات مستخدمة (الكفاءة)
```

## 15.4 ألقاب الترتيب (اختياري)

| المركز | اللقب |
|--------|------|
| الأول | فارس المطارحة |
| الثاني | حامي الحلبة |
| الثالث | صاحب البصيرة |

الألقاب قابلة للتعديل من المشرف لكل لعبة.

---

# 16. إطار الإدارة (Admin Framework)

## 16.1 هيكل لوحة التحكم

```
لوحة التحكم
  └── الألعاب المصغرة (قسم جديد)
        ├── نظرة عامة (Overview)
        │     ├── قائمة الألعاب المسجلة مع حالتها
        │     ├── إحصائيات مجمّعة (مباريات اليوم، لاعبون نشطون)
        │     └── تنبيهات (تسويات فاشلة، dead letters)
        │
        ├── [اسم اللعبة] (لكل لعبة مسجلة)
        │     ├── الإعدادات
        │     │     ├── تفعيل/تعطيل
        │     │     ├── إعدادات خاصة باللعبة
        │     │     └── عرض سلسلة الإعدادات (أي قيمة من أين)
        │     │
        │     ├── المباريات
        │     │     ├── المباريات النشطة (مع إمكانية الإنهاء)
        │     │     ├── سجل المباريات (مع تفاصيل كل مباراة)
        │     │     └── تصفية: حسب الحالة، اللاعب، التاريخ
        │     │
        │     ├── لوحة الترتيب
        │     │     ├── عرض وتصدير
        │     │     └── تعديل الألقاب
        │     │
        │     └── الإحصائيات
        │           ├── مباريات/يوم، معدل الفوز، متوسط المدة
        │           ├── معدل الانسحاب والهجر
        │           └── نقاط الدخول/الخروج (تأثير على الاقتصاد)
        │
        └── السياسات العامة
              ├── حدود يومية
              ├── فترات التبريد
              ├── حد الرصيد الأدنى
              └── مفاتيح الإيقاف (Kill Switches)
```

## 16.2 أدوات المشرف لكل لعبة

| الأداة | الوصف |
|--------|------|
| تفعيل/تعطيل | تشغيل أو إيقاف اللعبة لمسابقة/موسم/دورة |
| إنهاء مباراة | إنهاء مباراة جارية بقرار إداري (مع استرداد) |
| حظر لاعب | حظر لاعب من لعبة مصغرة محددة دون حظره من المسابقة |
| تعديل الإعدادات | تغيير مبلغ الدخول، الحد اليومي، المؤقتات، إلخ |
| عرض التسويات | قائمة التسويات مع حالتها (ناجحة/فاشلة/مُعاد تسويتها) |
| إعادة محاولة تسوية | إعادة تشغيل تسوية فاشلة |
| عرض سجل الأحداث | قائمة كل الأحداث لجلسة محددة |

## 16.3 مفاتيح الإيقاف (Kill Switches)

ثلاثة مستويات:

| المستوى | الوصف | التأثير |
|---------|------|--------|
| `SOFT_DISABLE` | تعطيل ناعم | لا توفيق جديد. المباريات الجارية تستمر |
| `HARD_DISABLE` | تعطيل صلب | لا جلسات جديدة + تحذير للمباريات الجارية (5 دقائق للإنهاء) |
| `EMERGENCY_STOP` | إيقاف طوارئ | إلغاء فوري لكل الجلسات، استرداد كل المبالغ |

**النطاق:**
- المشرف: مفتاح لكل لعبة في مسابقته
- مالك المنصة: مفتاح عام لكل الألعاب المصغرة في كل المسابقات

---

# 17. اتصالات WebSocket

## 17.1 رسائل العميل → الخادم

| الرسالة | الحمولة | متى |
|---------|--------|-----|
| `lobby_join` | `{ game_type }` | لاعب يدخل لوبي لعبة |
| `lobby_leave` | `{ game_type }` | لاعب يغادر اللوبي |
| `challenge_send` | `{ target_membership_id }` | لاعب يتحدى خصماً |
| `challenge_respond` | `{ session_id, accept: bool }` | رد على تحدي |
| `queue_join` | `{}` | دخول طابور التوفيق |
| `queue_leave` | `{}` | خروج من الطابور |
| `action_submit` | `ActionEnvelope` | إجراء داخل المباراة |
| `reconnect_claim` | `{ session_id, reconnect_token, last_known_revision }` | إعادة اتصال |
| `heartbeat` | `{}` | نبضة (كل 30 ثانية) |

## 17.2 رسائل الخادم → العميل

| الرسالة | الحمولة | متى |
|---------|--------|-----|
| `lobby_state` | `{ players, active_matches, recent_results }` | عند دخول اللوبي (لقطة كاملة) |
| `lobby_update` | `{ type: "join"\|"leave"\|"result", data }` | تحديث تفاضلي للوبي |
| `challenge_received` | `{ from_alias, session_id, expires_at }` | تحدي وارد |
| `match_found` | `{ session_id, opponent_alias, opponent_stats }` | تم التوفيق |
| `game_state` | `{ full state snapshot }` | لقطة كاملة (عند البدء أو إعادة الاتصال) |
| `state_patch` | `{ revision, delta, turn_info }` | تحديث تفاضلي للحالة |
| `action_ack` | `{ action_id, success, result }` | تأكيد إجراء |
| `action_reject` | `{ action_id, reason, current_state }` | رفض إجراء |
| `transition_event` | `{ from_phase, to_phase, data }` | انتقال حالة |
| `timer_sync` | `{ remaining_ms, server_time }` | مزامنة المؤقت |
| `settlement_result` | `{ winner, payout, stats_update }` | نتيجة التسوية |
| `error` | `{ code, message_ar }` | خطأ مع رسالة عربية |

## 17.3 معرّف التتبع الشامل (Correlation ID)

```
correlation_id: UUID — يُولّد عند إنشاء الجلسة
يمر عبر: رسائل WebSocket، طلبات API، سجلات الدفتر،
          سجلات التدقيق، الإشعارات
يُمكّن من: تتبع كامل — "هذه الجلسة → هذه الإجراءات →
            هذه التسوية → هذه القيود المالية"
```

---

# 18. محرك السياسات ومكافحة الاستغلال (Policy Engine & Anti-Abuse)

## 18.1 جداول السياسات (قابلة للتعديل إدارياً)

```
PolicyRule {
  id: int
  game_type: string (nullable — null = يشمل كل الألعاب)
  scope: "per_player_daily" | "per_pair_cycle" | "per_player_cycle"
  action: "duel" | "challenge" | "queue"
  limit: int
  window: "24h" | "cycle" | "season"
  enabled: bool
}
```

## 18.2 مصفوفة الخصوم (Opponent Matrix)

```
OpponentRecord {
  player_1_membership_id: int
  player_2_membership_id: int
  game_type: string
  competition_id: int
  cycle_id: int
  match_count: int
  last_match_at: timestamp
}
```

النظام يمنع تجاوز الحد لكل زوج لاعبين في كل دورة.

## 18.3 تسجيل المخاطر التكيفي (Adaptive Risk Scoring)

```
إشارات المخاطر:
  - always_loses_to_same_player (وزن: 0.8)
  - instant_forfeit_pattern (وزن: 0.9)
  - only_duels_one_opponent (وزن: 0.7)
  - win_rate_statistical_anomaly (وزن: 0.6)

حد المخاطر: 0.75
  → فوق الحد: تقييد مؤقت (تبريد 2 ساعات)
  → تنبيه المشرف في لوحة التحكم
```

## 18.4 رموز الحظر

كل إجراء محظور يُسجّل مع رمز سبب:

```
DAILY_LIMIT              // تجاوز الحد اليومي
OPPONENT_COOLDOWN        // مبارزة نفس الخصم مؤخراً
INSUFFICIENT_BALANCE     // رصيد غير كافٍ
RISK_THROTTLE           // تقييد بسبب نقاط المخاطر
ADMIN_DISABLED          // اللعبة معطلة بقرار إداري
BANKRUPT                // اللاعب مفلس
MAINTENANCE             // صيانة عامة
PLAYER_BANNED           // محظور من هذه اللعبة
```

## 18.5 نوافذ الاستثناء

```
المشرف يمكنه إنشاء استثناءات مؤقتة:
ExceptionWindow {
  type: "unlimited_duels" | "reduced_buy_in" | "double_rewards"
  start_at: timestamp
  end_at: timestamp
  reason: "يوم البطولة" | "حدث خاص"
  created_by: admin_id
}
```

---

# 19. المراقبة والجاهزية التشغيلية (Observability & SRE)

## 19.1 المقاييس الإلزامية

| المقياس | الوصف | المصدر |
|--------|------|-------|
| `queue_wait_ms` | مدة الانتظار في الطابور حتى التوفيق | نظام التوفيق |
| `ready_to_start_ms` | مدة من التوفيق حتى بدء اللعبة | مدير الجلسات |
| `action_latency_ms` | مدة من استلام الإجراء حتى الرد | بروتوكول الإجراءات |
| `reconnect_success_rate` | نسبة الانقطاعات التي أعادت الاتصال بنجاح | بروتوكول الانقطاع |
| `abandon_rate` | نسبة الجلسات المنتهية بالهجر | مدير الجلسات |
| `payout_failure_rate` | نسبة التسويات الفاشلة | نظام التسوية |
| `avg_game_duration_ms` | متوسط مدة المباراة | مدير الجلسات |
| `concurrent_sessions` | الجلسات النشطة حالياً | مدير الجلسات |

## 19.2 معرّف التتبع الشامل (Correlation ID)

- يُولّد عند إنشاء الجلسة
- يمر عبر كل: رسائل WebSocket، طلبات API، قيود الدفتر، سجلات التدقيق، الإشعارات
- يُمكّن المشرف من تتبع: "هذه الجلسة → ماذا حصل → لماذا هذه النتيجة"

## 19.3 معالجة الأحداث الميتة (Dead Letter Handling)

```
DeadLetterEntry {
  id: UUID
  event_type: "settlement" | "notification" | "audit"
  payload: JSON
  failure_reason: string
  retry_count: int
  max_retries: 3
  next_retry_at: timestamp (تراجع أُسي)
  status: "pending" | "retrying" | "exhausted" | "resolved"
  correlation_id: UUID
  created_at: timestamp
}
```

- الأحداث الفاشلة تُخزّن بدلاً من الضياع
- إعادة محاولة تلقائية بتراجع أُسي (30 ثانية، دقيقة، دقيقتين)
- بعد 3 محاولات: حالة `exhausted` + تنبيه المشرف
- المشرف يمكنه إعادة التشغيل يدوياً أو تأشير كـ `resolved`

---

# 20. نموذج التخزين (Storage Model)

## 20.1 PostgreSQL (دائم)

### minigame_types — سجل الألعاب المسجلة

```
minigame_types {
  id: string PK                      // "mutaraha"
  name: string                       // "مطارحة"
  description: string
  plugin_api_version: string
  settings_schema_version: string
  min_players: int
  max_players: int
  supports_overtime: bool
  supports_spectators: bool
  supports_ranked: bool
  supports_team_mode: bool
  status: "active" | "disabled" | "deprecated"
  created_at: timestamp
  updated_at: timestamp
}
```

### minigame_sessions — الجلسات

```
minigame_sessions {
  id: UUID PK
  game_type: string FK → minigame_types
  competition_id: int FK → competitions
  season_id: int FK → seasons (nullable)
  cycle_id: int FK → cycles (nullable)

  phase: session_phase ENUM
  revision: int (default 0)

  player_1_membership_id: int FK → memberships
  player_2_membership_id: int FK → memberships (nullable — null أثناء الانتظار)

  match_type: "challenge" | "queue"
  current_turn: "player_1" | "player_2" (nullable)
  turn_number: int (default 0)

  game_state: JSONB                   // حالة خاصة باللعبة
  settings_snapshot: JSONB            // لقطة الإعدادات الفعالة

  buy_in_amount: int

  reconnect_token_p1: string
  reconnect_token_p2: string

  terminal_reason: string (nullable)
  winner_membership_id: int (nullable)

  turn_started_at: timestamp (nullable)
  turn_duration_ms: int
  grace_timer_ms: int

  correlation_id: UUID

  started_at: timestamp (nullable)
  completed_at: timestamp (nullable)
  created_at: timestamp
  updated_at: timestamp

  -- ضمان المسار النهائي الواحد يُطبّق عبر:
  -- 1. القفل المتفائل (WHERE revision = expected) في كل عمليات الكتابة
  -- 2. قيد فريد على session_id في جدول التسويات (minigame_session_settlements)
  -- 3. التحقق من phase في طبقة التطبيق قبل أي انتقال
}
CREATE INDEX idx_sessions_active ON minigame_sessions(game_type, competition_id)
  WHERE phase NOT IN ('completed','cancelled','abandoned');
```

### minigame_session_events — سجل أحداث الجلسة (append-only)

```
minigame_session_events {
  id: BIGSERIAL PK
  session_id: UUID FK → minigame_sessions
  revision: int                        // رقم المراجعة عند هذا الحدث
  event_type: "action" | "transition" | "system"
  actor_type: "player" | "system" | "admin"
  actor_membership_id: int (nullable)

  action_type: string (nullable)       // "guess", "tool_letter_check"
  payload: JSONB
  result: JSONB

  from_phase: string (nullable)
  to_phase: string (nullable)

  correlation_id: UUID
  created_at: timestamp

  -- لا تعديل أو حذف — إضافة فقط
}
CREATE INDEX idx_events_session ON minigame_session_events(session_id, revision);
```

### minigame_action_receipts — إيصالات الإجراءات (عدم التكرار)

```
minigame_action_receipts {
  action_id: UUID PK                  // مفتاح عدم التكرار
  session_id: UUID FK → minigame_sessions
  actor_membership_id: int
  client_seq: int
  response: JSONB                     // الاستجابة المخزنة
  created_at: timestamp

  CONSTRAINT unique_action UNIQUE (action_id)
  CONSTRAINT unique_seq_per_player UNIQUE (session_id, actor_membership_id, client_seq)
}
```

### minigame_session_settlements — التسويات

```
minigame_session_settlements {
  id: UUID PK
  session_id: UUID FK UNIQUE → minigame_sessions  // تسوية واحدة لكل جلسة

  winner_membership_id: int (nullable)   // null عند الإلغاء
  loser_membership_id: int (nullable)

  winner_payout: int
  loser_penalty: int

  settlement_state: "pending" | "settled" | "failed" | "reconciled"
  ledger_entry_ids: int[]

  correlation_id: UUID
  settled_at: timestamp (nullable)
  failure_reason: string (nullable)
  retry_count: int (default 0)

  created_at: timestamp
  updated_at: timestamp
}
```

### minigame_leaderboards — لوحات الترتيب

```
minigame_leaderboards {
  id: SERIAL PK
  game_type: string FK → minigame_types
  competition_id: int FK → competitions
  membership_id: int FK → memberships

  wins: int (default 0)
  losses: int (default 0)
  win_rate: float (computed)
  current_streak: int (default 0)
  best_streak: int (default 0)
  total_matches: int (default 0)
  avg_tools_used: float (default 0)
  avg_match_duration_sec: float (default 0)
  elo_rating: int (nullable)

  updated_at: timestamp

  CONSTRAINT unique_player_game UNIQUE (game_type, competition_id, membership_id)
}
```

### minigame_policy_rules — قواعد السياسات

```
minigame_policy_rules {
  id: SERIAL PK
  game_type: string (nullable — null = كل الألعاب)
  competition_id: int (nullable — null = كل المسابقات)
  scope: string                         // "per_player_daily", "per_pair_cycle"
  action: string                        // "duel", "challenge", "queue"
  limit_value: int
  window: string                        // "24h", "cycle", "season"
  enabled: bool (default true)
  created_at: timestamp
  updated_at: timestamp
}
```

### minigame_opponent_matrix — مصفوفة الخصوم

```
minigame_opponent_matrix {
  id: SERIAL PK
  player_1_membership_id: int
  player_2_membership_id: int
  game_type: string
  competition_id: int
  cycle_id: int
  match_count: int (default 0)
  last_match_at: timestamp

  CONSTRAINT unique_pair UNIQUE (player_1_membership_id, player_2_membership_id,
                                  game_type, competition_id, cycle_id)
}
```

### minigame_dead_letters — الأحداث الميتة

```
minigame_dead_letters {
  id: UUID PK
  event_type: string
  payload: JSONB
  failure_reason: string
  retry_count: int (default 0)
  max_retries: int (default 3)
  next_retry_at: timestamp
  status: "pending" | "retrying" | "exhausted" | "resolved"
  correlation_id: UUID
  created_at: timestamp
  updated_at: timestamp
}
```

## 20.2 Redis (عابر)

```
lobby:{game_type}:{competition_id}:presence    — مجموعة الحاضرين (SET)
lobby:{game_type}:{competition_id}:results     — آخر نتائج (LIST, حد 5)
matchmaking:{game_type}:{competition_id}:queue  — طابور التوفيق (LIST)
session:{session_id}:cache                      — حالة الجلسة الساخنة (HASH)
```

---

# 21. استراتيجية الاختبار (Test Strategy)

## 21.1 اختبارات عقد المحرك (Engine Contract Tests)

كل لعبة مسجلة يجب أن تجتاز:

```
- كل خطافات دورة الحياة تُعيد الأنواع الصحيحة
- init_session_state يُعيد حالة صالحة
- validate_action يرفض الإجراءات غير القانونية
- apply_action يُعيد حالة جديدة مع side_effects
- evaluate_terminal يُعيد null أثناء اللعب ونتيجة عند الانتهاء
- compute_settlement يُنتج تعليمات تسوية صالحة
- build_public_view لا يُسرّب معلومات سرية
```

## 21.2 اختبارات آلة الحالة

```
- كل مسار انتقال صالح يعمل
- كل انتقال غير صالح يُرفض (مثل: COMPLETED → IN_PROGRESS)
- الحالات النهائية نهائية فعلاً (لا تحولات إضافية)
- لا يمكن الوصول لحالتين نهائيتين من نفس الجلسة
```

## 21.3 اختبارات Fuzz

```
- action_id مكرر (يجب أن يكون عديم الأثر)
- client_seq غير متسلسل (يجب الرفض أو إعادة الترتيب)
- رسائل WebSocket سريعة متتالية (حد المعدل يعمل)
- أنواع إجراءات غير صالحة أثناء مرحلة خاطئة
```

## 21.4 اختبارات الفوضى (Chaos Tests)

```
- انقطاع أثناء التسوية → التسوية تكتمل عند إعادة الاتصال
- انقطاع أثناء الوقت الإضافي → مؤقت المهلة يعمل
- إعادة تشغيل الخادم وسط المباراة → الجلسة تُستعاد من قاعدة البيانات
- تسويات متزامنة لنفس الجلسة → واحدة فقط تنجح
```

---

# 22. واجهة API المشتركة

## 22.1 نقاط النهاية

```
# سجل الألعاب
GET    /api/minigames                                    → قائمة الألعاب المتاحة
GET    /api/minigames/{type}                             → تفاصيل لعبة

# اللوبي
WS     /ws/minigames/{type}/lobby                        → اتصال WebSocket للوبي

# الجلسات
POST   /api/competitions/{id}/minigames/{type}/challenge → إرسال تحدي
POST   /api/competitions/{id}/minigames/{type}/queue     → دخول الطابور
DELETE /api/competitions/{id}/minigames/{type}/queue      → خروج من الطابور
GET    /api/competitions/{id}/minigames/{type}/sessions   → سجل المباريات
GET    /api/competitions/{id}/minigames/{type}/sessions/{session_id} → تفاصيل جلسة

# اللعب المباشر
WS     /ws/minigames/sessions/{session_id}                → اتصال WebSocket للمباراة

# لوحة الترتيب
GET    /api/competitions/{id}/minigames/{type}/leaderboard → ترتيب اللعبة

# ملف اللاعب
GET    /api/competitions/{id}/minigames/{type}/stats       → إحصائياتي

# إدارة
GET    /api/admin/minigames                               → كل الألعاب (إدارة)
PATCH  /api/admin/minigames/{type}/settings               → تعديل إعدادات
GET    /api/admin/minigames/{type}/settings/explain       → شرح سلسلة الإعدادات
GET    /api/admin/minigames/{type}/sessions               → كل الجلسات (إدارة)
POST   /api/admin/minigames/{type}/sessions/{id}/cancel   → إلغاء جلسة
POST   /api/admin/minigames/{type}/sessions/{id}/settle   → إعادة تسوية
GET    /api/admin/minigames/{type}/dead-letters            → الأحداث الميتة
POST   /api/admin/minigames/{type}/dead-letters/{id}/retry → إعادة محاولة
PATCH  /api/admin/minigames/{type}/kill-switch             → مفتاح إيقاف
GET    /api/admin/minigames/{type}/metrics                 → مقاييس الأداء

# مالك المنصة
GET    /api/owner/minigames/word-banks                     → إدارة بنوك الكلمات
POST   /api/owner/minigames/word-banks                     → إضافة كلمات
PATCH  /api/owner/minigames/word-banks/{id}                → تعديل كلمة
DELETE /api/owner/minigames/word-banks/{id}                 → حذف كلمة
PATCH  /api/owner/minigames/{type}/kill-switch              → مفتاح إيقاف عام
```

---

# 23. النطاق والحدود

## 23.1 في النطاق (V1.0)

- سجل الألعاب (Plugin Registry) مع عقد كامل
- آلة حالة الجلسة مع كل الانتقالات
- بروتوكول الإجراءات المصادق عليها مع عدم التكرار
- القفل المتفائل وأرقام المراجعة
- التسوية الآمنة مع صندوق المعاملات
- بروتوكول الانقطاع وإعادة الاتصال
- نظام اللوبي مع الحضور المباشر
- التوفيق: تحدي مباشر + طابور تلقائي
- جسر الاقتصاد مع الدفتر
- لوحة ترتيب لكل لعبة
- سلسلة الإعدادات مع المحلل الحتمي
- إطار الإدارة في لوحة التحكم
- اتصالات WebSocket للوبي والمباراة
- محرك السياسات مع رموز الحظر
- مفاتيح الإيقاف (3 مستويات)
- استراتيجية الاختبار
- نموذج التخزين الكامل

## 23.2 خارج النطاق (مؤجل)

- الوضع غير المتزامن (Async mode) — مؤجل لمرحلة لاحقة
- وضع المشاهدة (Spectator mode) — لا حاجة حالياً
- وضع الفرق (Team mode) — مستقبلي
- تصنيف Glicko-2 — ELO بسيط أولاً
- تكامل مع عناصر المتجر — فصل تام حالياً

---

# 24. المراجع والأبحاث

تم بناء هذه الوثيقة بناءً على بحث معماري شامل موثّق في:

- `docs/Research - Minigame Engine Architecture - Platform Patterns - V1.0.md`

المنصات المدروسة: Roblox, Discord Activities, Telegram Mini Apps, WeChat Mini Games, Facebook Instant Games, Supercell, Jackbox Games, Colyseus, Nakama, AccelByte.

الأنماط المعمارية المعتمدة:
- Plugin/Registry Pattern (من Roblox + Unreal Engine 5)
- Hierarchical State Machine (من أدبيات تصميم الألعاب)
- Server-Authoritative Model (معيار صناعة الألعاب)
- Transactional Outbox (من هندسة الأنظمة الموزعة)
- Optimistic Locking (من إدارة قواعد البيانات)
- WebSocket Room Architecture (من Colyseus + Jackbox)
- Redis Sorted Sets for Leaderboards (من Nakama + AccelByte)
- ELO Rating System (من Chess.com + Lichess)
