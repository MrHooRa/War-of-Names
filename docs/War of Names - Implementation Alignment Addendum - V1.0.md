# War of Names - Implementation Alignment Addendum - V1.0

## 1. معلومات الوثيقة

- **اسم الوثيقة:** Implementation Alignment Addendum
- **المشروع:** War of Names
- **الإصدار:** V1.0
- **اللغة الأساسية:** العربية
- **الغرض:** ضبط التنفيذ الحالي وربط الـ BRDs الأصلية بالواقع التنفيذي الفعلي للمشروع
- **نوع الوثيقة:** وثيقة حاكمة للتنفيذ والمراجعة التقنية والوظيفية
- **علاقتها بالوثائق الأصلية:** هذه الوثيقة **مكملة** للوثائق الأساسية وليست بديلة عنها

---

## 2. الهدف من هذه الوثيقة

هذه الوثيقة أُنشئت لمعالجة الفجوة بين:

1. **الرؤية والمتطلبات الأصلية** في BRD
2. **التصميم المعماري/الوظيفي** في Technical Spec و API/Database Spec
3. **التنفيذ الفعلي الحالي** في الكود والواجهات ولوحة التحكم

الغرض منها هو:

- تثبيت **الوضع الحقيقي الحالي للمشروع**
- توضيح **ما الذي يُعتبر مكتملًا فعلًا وما الذي لا يزال ناقصًا**
- منع تنفيذ خصائص “شكلها موجود لكن فعليًا غير مكتملة”
- تحديد **قواعد الإغلاق الحقيقي للخصائص**
- تحديد **ما الذي يحتاج Completion** وما الذي يحتاج **Refactor** وما الذي يحتاج **Rebuild from Core**
- مساعدة الـ Agent أو أي مطور على اتخاذ قرارات تنفيذية صحيحة بعقلية مهندس برمجيات، لا بعقلية “إخراج واجهة” أو “إغلاق تاسك شكلي”

---

## 3. الحالة الحالية الحقيقية للمشروع

### 3.1 التقييم الحالي
المشروع حاليًا في مرحلة:

**Late Alpha / Pre-Beta**

هذا يعني:

- يوجد أساس Full-Stack حقيقي
- يوجد تدفق لعب أساسي ظاهر
- يوجد تسجيل/دخول/عضويات/لوحات/بعض محركات اللعب
- يوجد لوحة تحكم إدارية بدأت تأخذ شكلًا صحيحًا
- لكن النظام **ليس MVP ناضجًا بعد**
- ولا يجوز اعتباره مكتملًا من حيث:
  - العمق الإداري
  - اكتمال محركات اللعبة
  - اكتمال دورة الحياة الزمنية
  - اكتمال ربط الإعدادات بالمحركات
  - اكتمال تأثيرات العناصر
  - اكتمال بعض الحلقات end-to-end

### 3.2 ما الذي يعنيه هذا عمليًا
المشروع **قابل للبناء عليه**، لكن ليس بشكل مفتوح بلا ضوابط.  
قبل التوسع في مزايا جديدة، يجب إغلاق عدد من الفجوات الأساسية حتى لا يتحول النظام إلى:

- صفحات كثيرة بمنطق ناقص
- CRUD سطحي
- إعدادات لا تؤثر فعليًا
- عناصر بلا تأثير حقيقي
- هيكل إداري مسطح لا يعكس الدومين

---

## 4. المبادئ التنفيذية الحاكمة لهذه المرحلة

### 4.1 لا يكفي وجود الصفحة
أي feature لا تعتبر مكتملة لمجرد أن:
- الصفحة موجودة
- الزر موجود
- الفورم يفتح
- البيانات تُعرض

الخاصية تعتبر مكتملة فقط إذا كانت:
- **DB-backed**
- **Backend-authoritative**
- **قابلة للاستخدام end-to-end**
- **مسجلة في السجلات المناسبة**
- **متوافقة مع حدود الدومين**
- **متكاملة مع بقية النظام**

### 4.2 لا توجد “ميزات عرض فقط” في المناطق الحساسة
أي منطقة من هذه المناطق لا يجوز أن تبقى display-only:
- Admin management
- Settings
- Items
- Store listings
- Question bank
- Quiz sessions
- Attacks
- Inventory use
- Season/Cycle operations

### 4.3 كل منطق أعمال حساس يجب أن يكون في الـ Backend
الواجهة لا تحسم:
- الهجوم
- النقاط
- الحماية
- الإفلاس
- الشراء
- استخدام العنصر
- التصحيح
- eligibility
- state transitions

الواجهة فقط:
- تعرض
- تطلب
- تؤكد
- تُحدِّث الحالة المرئية بعد النتيجة

### 4.4 كل تعديل حساس يجب أن يكون قابلًا للتتبع
أي تعديل على:
- نقطة
- حالة عضوية
- إعداد
- عنصر
- جلسة
- دورة
- موسم
- مسابقة
- شراء
- استخدام عنصر

يجب أن يترك أثرًا واضحًا في:
- Ledger إذا كان ماليًا
- Audit إذا كان تشغيليًا أو إداريًا
- أو كلاهما حسب السياق

### 4.5 الإعدادات ليست شكلًا
أي setting لا تعتبر “مطبقة” ما لم تكن:
- موجودة في المخزن المناسب
- قابلة للجلب والتحرير
- مربوطة بالمحرك الفعلي
- مؤثرة في السلوك الحقيقي للنظام

---

## 5. الحدود الدومينية غير القابلة للتفاوض

هذه الحدود يجب أن تبقى محفوظة دائمًا، وأي اختراق لها يعتبر خللًا معماريًا:

### 5.1 Account != Membership
- **Account** = هوية المستخدم العامة على مستوى المنصة
- **Membership** = مشاركة ذلك الحساب داخل مسابقة محددة

### 5.2 Alias != Real Identity
- الاسم الحقيقي ليس هوية اللعب
- اللقب هو الهوية الظاهرة داخل المسابقة
- تغييرات اللقب لا تغير الهوية الحقيقية
- كشف الاسم الحقيقي يخضع لقواعد اللعبة فقط

### 5.3 Competition != Season != Cycle
- المسابقة root container
- الموسم تابع للمسابقة
- الدورة تابعة للموسم
- لا يجوز تسطيحها في واجهة الإدارة أو في البيانات

### 5.4 Balance != Ledger
- الرصيد الحالي ليس الحقيقة الوحيدة
- الحقيقة المالية هي Ledger
- أي تغيير مالي يجب أن يمر عبر Ledger

### 5.5 Ledger != Audit
- Ledger = أثر مالي
- Audit = أثر إداري/تشغيلي/تاريخي
- لا يجوز استبدال أحدهما بالآخر

### 5.6 Item Definition != Owned Item
- تعريف العنصر شيء
- امتلاك اللاعب للعنصر شيء آخر
- عرض العنصر في المتجر شيء آخر
- استخدام العنصر شيء آخر

### 5.7 Question Bank != Quiz Session
- بنك الأسئلة = محتوى تأليفي reusable
- الجلسة = runtime delivery event
- لا يجوز دمجهما في شاشة أو كيان واحد بشكل مسطح

### 5.8 Preview != Execution
- Preview لا يغير الحالة
- Execution هو الذي يغير الحالة
- لا يجوز خلطهما أو استخدام preview كتنفيذ مؤجل

### 5.9 Frontend != Source of Truth
- الواجهة ليست مرجعًا للحالة
- أي منطق حاسم فيها يعتبر خللًا

---

## 6. تعريف الاكتمال الحقيقي (Definition of Completion)

الخاصية لا تعتبر مكتملة إلا إذا تحققت الشروط التالية:

1. **يوجد نموذج بيانات صحيح**
2. **يوجد API أو Backend contract صحيح**
3. **يوجد منطق أعمال مكتمل**
4. **توجد واجهة أو تدفق استخدام فعلي**
5. **النتيجة تنعكس في DB**
6. **السجل المناسب يُكتب**
7. **الحالة بعد التنفيذ تُعرض بشكل صحيح**
8. **الحالات الخطأ والرفض والقيود مغطاة**
9. **لا يوجد hardcoded logic حاسم في الواجهة**
10. **الخاصية متوافقة مع حدود الدومين**

### 6.1 تعريف “Shallow Feature”
الميزة تعتبر سطحية إذا كان فيها واحد أو أكثر من التالي:
- Create modal فقط بدون إدارة فعلية
- List view بدون actions حقيقية
- Setting يتغير بصريًا ولا يؤثر فعليًا
- عنصر يُعرض ويُشترى لكن “ماله تأثير”
- Session تُنشأ لكن منطقها ناقص
- Attack page موجودة لكن state reconciliation ناقص
- صفحة profile موجودة لكن لا تعرض history الحقيقي
- Admin page فيها CRUD شكلي بدون workflow حقيقي

### 6.2 تعريف “Needs Rebuild”
الميزة تعتبر تحتاج Rebuild عندما:
- يكون الهيكل المفاهيمي نفسه خاطئ
- تم دمج حدود دومينية مختلفة في شاشة/كيان واحد
- الاعتماد الحالي سيؤدي إلى تضخم مشاكل لاحقًا
- أصبح الترقيع أخطر من إعادة البناء المنضبط

---

## 7. أولويات الإكمال الحالية (Canonical Completion Priorities)

هذه الأولويات حاكمة للمرحلة الحالية، ويجب تقديمها على أي توسع جديد:

### Priority 1 — Item Effect Execution
يجب تحويل العناصر من:
- تعريفات مرئية
إلى:
- تأثيرات فعلية قابلة للتنفيذ والتحقق والتتبع

هذا يتضمن:
- effect model
- eligibility
- use flow
- state change
- ledger/audit linkage
- admin configurability

### Priority 2 — Settings Wiring
الإعدادات الموجودة يجب أن تُربط فعليًا بالمحركات التالية:
- Attack Engine
- Protection/Bankruptcy logic
- Quiz/session timing
- Store rules
- Cycle transitions
- Season/competition behavior

### Priority 3 — Cycle Lifecycle Automation
بما أن المشروع يعتمد على دورة أسبوعية/تشغيلية، يجب أن تكون الدورة كيانًا فعليًا له:
- start
- end
- activate
- deactivate
- rollover effects
- protection clearing
- bankruptcy reset/recovery where applicable
- notifications

### Priority 4 — Admin Operational Depth
لوحة الإدارة يجب أن تنتقل من:
- flat CRUD
إلى:
- operational workspace architecture

### Priority 5 — Attack / Protection / Bankruptcy Consolidation
منطق:
- eligibility
- exposure count
- decay
- protection stages
- bankruptcy activation
- bankruptcy clearing
يجب أن يكون موحدًا وقابلًا للتفسير

### Priority 6 — Questions / Banks / Sessions Alignment
يجب التأكد أن تنفيذ الأسئلة يحترم الفرق بين:
- type
- definition
- group/bank
- session
- delivered question
- answer submission

### Priority 7 — Audit Completeness
كل الإجراءات الحساسة، خصوصًا الإدارية، يجب أن تكون قابلة للتتبع بشكل كامل وواضح

---

## 8. التسلسل التشغيلي الصحيح للإدارة (Admin Operational Hierarchy)

هذه النقطة حاسمة، وهي توجيه تنفيذي ملزم.

### 8.1 المستوى الأول: Platform Level
هذا المستوى يخص المنصة ككل، وليس مسابقة محددة.

يشمل:
- Accounts / Users
- Platform Settings
- Website Config
- Global Notifications overview
- Global Logs / Audit exploration
- Media / Imports / Exports
- Role groundwork future-readiness

### 8.2 المستوى الثاني: Competition Level
المسابقة يجب أن تُعامل كـ:
**Operational Container / Workspace / Profile**

يشمل:
- Competition Profile
- Competition Overview
- Registration State
- Visibility
- Join Mode
- Invites
- Competition-level settings
- Linked Seasons
- Competition Members overview
- Competition-scoped operational pages

### 8.3 المستوى الثالث: Season Level
الموسم ليس كيانًا إداريًا صامتًا.  
هو هوية تشغيلية ولعبية.

يشمل:
- Season name / identity
- Season status
- Season overview
- Season leaderboard context
- Season settings
- Season-scoped content visibility
- Season-scoped store / question relevance if applicable
- Season-scoped player state summaries

### 8.4 المستوى الرابع: Cycle Level
الدورة جزء تشغيلي داخل الموسم، وليست كيانًا منفصلًا بلا سياق.

يشمل:
- Cycle timeline
- Cycle active/ended/paused state
- Cycle rollover actions
- Protection expiry handling
- Bankruptcy reset/recovery handling
- Cycle notifications
- Scheduled operational effects

### 8.5 قاعدة إدارية حاكمة
أي واجهة إدارة يجب أن توضح بوضوح:
- على أي scope تعمل؟
- هل هذا Platform أم Competition أم Season أم Cycle؟
- هل التعديل هنا يخص الحساب أم العضوية أم الموسم أم الدورة؟

لا يجوز خلط هذه المستويات في نفس الصفحة أو نفس الجدول بلا فصل واضح.

---

## 9. قواعد تشغيل الحسابات والعضويات

### 9.1 Accounts
الحساب يجب أن يبقى:
- global
- مستقلًا عن أي مسابقة
- يحمل real identity و auth state و global status

### 9.2 Memberships
العضوية يجب أن تكون:
- competition-scoped
- حاملة للقب والحالة والنقاط والجرد والتاريخ داخل المسابقة

### 9.3 Player State
أي شيء يخص اللعب يجب أن يكون:
- membership-scoped غالبًا
- season/cycle-aware عند الحاجة

### 9.4 ما يجب أن يظهر في الإدارة
#### في شاشة الحساب:
- من هو المستخدم؟
- هل هو admin؟
- هل حسابه فعال؟
- ما المسابقات المنضم لها؟
- ملخص عضوياته

#### في شاشة العضوية:
- اللقب
- النقاط
- الحالة
- التاريخ
- الموسم/الدورة الحالية
- attack state
- bankruptcy/protection state
- inventory summary

---

## 10. قواعد تنفيذ المسابقة / الموسم / الدورة

### 10.1 Competition as Workspace
المسابقة ليست مجرد سجل CRUD.  
يجب أن تُدار كمساحة تشغيل لها:
- profile
- settings
- invites
- members
- seasons
- status controls

### 10.2 Season as Live Identity
الموسم يجب أن ينعكس داخل اللعبة نفسها:
- الاسم
- الحالة
- badge/label
- current context in dashboard/lobby/header where relevant

### 10.3 Cycle as Operational Engine
الدورة يجب أن تفعل أحداثًا حقيقية عند:
- البداية
- النهاية
- الانتقال

### 10.4 مثال على أحداث نهاية الدورة
نهاية الدورة يجب أن تكون قادرة على تشغيل:
- إزالة/انتهاء حمايات مؤقتة
- إنهاء/تسوية حالات مرتبطة بالدورة
- إعادة تمكين حالات معينة
- إشعار “بدأت دورة جديدة”
- قفل/فتح windows حسب الإعدادات
- تحديث current cycle context

---

## 11. قواعد الأسئلة والجلسات

### 11.1 Question Types
أنواع الأسئلة metadata/configuration، وليست sessions.

### 11.2 Question Definitions
السؤال المؤلف reusable content.

### 11.3 Question Group / Bank
المجموعة حاوية منطقية لإعادة الاستخدام والتنظيم.

### 11.4 Quiz Session
الجلسة runtime event:
- لها توقيت
- حالة
- مصدر أسئلة
- جمهور
- scoring behavior

### 11.5 Session Question
يجب أن تبقى conceptual separation قائمة بين:
- source question
- delivered session question
خصوصًا إذا احتجنا snapshotting لاحقًا

### 11.6 Answer Submission
الإجابة كيان runtime منفصل:
- submitted answer
- correctness
- awarded points
- ledger linkage

### 11.7 قاعدة تنفيذية
واجهة الإدارة الخاصة بالأسئلة لا يجوز أن تكون مجرد:
- Questions tab
- Sessions tab
بدون احترام هذه الحدود

---

## 12. قواعد المتجر والعناصر والمخزون

### 12.1 Item Definition
العنصر يجب أن يكون تعريفًا قابلًا للإدارة، لا مجرد بطاقة جميلة.

### 12.2 Item Effects
أي عنصر يجب أن يمتلك:
- effect type
- effect parameters
- target scope
- duration semantics
- usage semantics
- acquisition type
- stacking/use limits عند الحاجة

### 12.3 Store Listing
ظهور العنصر في المتجر شيء مستقل عن تعريفه.

### 12.4 Ownership / Inventory
امتلاك العنصر عند اللاعب شيء مستقل عن تعريفه وبيعه.

### 12.5 Usage
استخدام العنصر حدث مستقل يجب أن:
- يُتحقق منه
- يُنفذ في backend
- يُسجل
- يغير الحالة
- ينعكس في الواجهة

### 12.6 قاعدة حاكمة
أي عنصر لا يملك أثرًا فعليًا قابلًا للتنفيذ والتحقق، لا يعتبر مكتملًا حتى لو:
- ظهر في المتجر
- تم شراؤه
- دخل الجرد

---

## 13. قواعد الربط بين الإعدادات والمحركات

### 13.1 لا توجد إعدادات “ديكورية”
إذا كانت setting ظاهرة للمشرف، يجب أن تكون إحدى الحالتين:
1. مربوطة فعليًا بمحرك
2. معلمة بوضوح أنها غير مفعلة بعد

لكن لا يجوز تقديمها كأنها فعالة وهي ليست كذلك.

### 13.2 أمثلة Settings يجب أن تكون موصولة
- attack_base_reward
- attack_decay_factor
- attack_base_penalty
- attack_max_per_cycle
- score_initial_balance
- score_bankruptcy_threshold
- protection_full_attack_count
- quiz_default_duration
- store_max_inventory

### 13.3 قاعدة تنفيذية
أي Change في setting يجب أن ينعكس فعليًا في:
- behavior
- validation
- outcome
- admin traceability

---

## 14. مصفوفة القرار: Complete / Refactor / Rebuild

### 14.1 Keep / Complete
هذه المناطق غالبًا يمكن البناء عليها مع إكمال:
- Auth baseline
- Account settings baseline
- Leaderboard baseline
- Profile routing baseline
- Attack preview/execute baseline
- Notification baseline
- Frontend shell / routing baseline
- Docker/full-stack baseline

### 14.2 Needs Refactor
هذه المناطق تحتاج refactor منضبط:
- Admin navigation IA
- Competition/member scoping in admin
- Settings display/edit structure
- Battle history/profile data aggregation
- Store admin structure
- Quiz admin structure

### 14.3 Needs Core Build / Rebuild
هذه المناطق يجب اعتبارها غير مكتملة جذريًا حتى لو بدا ظاهرها موجودًا:
- Item effects execution model
- Store semantics beyond display/purchase
- Cycle lifecycle automation
- Full settings-to-engine wiring
- Protection/bankruptcy final coherence if still fragmented
- Deep audit coverage if ناقص
- Invite management depth if بقي سطحيًا

---

## 15. قواعد العمل الإلزامية للـ Agent / المطور

### 15.1 قبل أي تنفيذ جديد
يجب الإجابة على:
- ما الـ scope الذي تعمل عليه؟
- هل هذه feature جديدة أم closure لشيء موجود؟
- هل هذه الصفحة تعمل على Account أم Membership أم Competition أم Season أم Cycle؟
- ما المحرك الذي يجب أن يملك الحقيقة؟
- ما الذي يجب أن يسجل في Ledger؟
- ما الذي يجب أن يسجل في Audit؟

### 15.2 ممنوعات تنفيذية
يُمنع:
- اعتبار الصفحة المكتملة شكليًا feature مكتملة
- بناء CRUD بدون workflow حقيقي
- إضافة item بلا semantics
- إضافة setting بلا wiring
- خلط account و membership
- خلط competition و season و cycle
- تكرار business logic في frontend
- hardcoding IDs أو scopes أو values
- bypass للمحركات الأساسية

### 15.3 قواعد التسليم
أي تسليم يجب أن يوضح:
- ما الذي أصبح DB-backed
- ما الذي ما زال ناقصًا بوضوح
- هل هذه feature complete أم partial؟
- ما حالات الرفض والأخطاء المغطاة؟
- هل يوجد أثر في ledger؟
- هل يوجد أثر في audit؟
- ما الصفحات/التدفقات التي تأثرت؟

---

## 16. ما الذي يجب إصلاحه قبل التوسع

قبل التفكير في features إضافية كبيرة، يجب إغلاق هذه النقاط:

1. **Admin depth around competition/season/cycle**
2. **Membership vs account management clarity**
3. **Item effect engine**
4. **Inventory use flow**
5. **Settings wiring**
6. **Cycle lifecycle automation**
7. **Questions/session structure alignment**
8. **Battle history completeness**
9. **Invite generation/management depth**
10. **Audit completeness for sensitive admin operations**

---

## 17. القرار التنفيذي للمرحلة الحالية

### 17.1 ما يجب فعله الآن
المرحلة الحالية يجب أن تكون:
**Closure + Alignment + Hardening**

وليس:
- توسع features بشكل أفقي
- إضافة صفحات جديدة بلا إغلاق القديم
- تجميل واجهات فقط
- تقارير read-only جديدة

### 17.2 ما لا يجب فعله الآن
يجب تأجيل:
- خصائص تجميلية كثيرة
- تعقيد أدوار إدارية
- مزايا social/chat
- public view expansion
- analytics advanced
- advanced live features

إلى ما بعد إغلاق المحركات الأساسية الحالية.

---

## 18. الخلاصة التنفيذية

هذا المشروع يملك أساسًا قويًا من ناحية الرؤية والدومين والهيكل العام، لكن المرحلة الحالية تتطلب انضباطًا عاليًا في التنفيذ.

المشكلة الحالية ليست فقط “نواقص” بل:
- بعض الخصائص سُلمت بعمق غير كافٍ
- بعض الشاشات الإدارية تحتاج إعادة هيكلة مفاهيمية
- بعض المحركات الجوهرية ما زالت غير مغلقة
- بعض الإعدادات والعناصر موجودة شكليًا أكثر من كونها محركات حقيقية

لذلك، هذه الوثيقة تفرض ما يلي:

- لا تُعتبر الخاصية مكتملة إلا إذا كانت end-to-end
- لا تُقبل features سطحية في المناطق الحساسة
- يجب احترام الحدود الدومينية دائمًا
- يجب الانتقال من page-based thinking إلى engine/workflow thinking
- يجب تثبيت competition/season/cycle hierarchy إداريًا وتشغيليًا
- يجب تثبيت account vs membership boundaries في الواجهة والإدارة والـ backend
- يجب إغلاق item effects و settings wiring و cycle automation قبل أي توسع كبير

هذه الوثيقة هي المرجع التنفيذي الحاكم لأي Agent أو مطور يعمل على المرحلة الحالية من المشروع.