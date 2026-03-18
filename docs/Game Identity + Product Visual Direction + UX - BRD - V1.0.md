# Design / Identity / UX BRD

**مشروع:** لعبة / منصة "حرب الأسماء"
**المستند:** Game Identity + Product Visual Direction + UX/UI Foundation
**الإصدار:** V2.0 — مبني بالكامل من الواجهات المنفذة فعليًا
**النطاق:** توثيق الهوية البصرية والتجريبية المعتمدة كما ظهرت في النماذج الأولية المنفذة يدويًا
**المصدر:** 11 ملف HTML في `/Front-end/War of Names - Main Template - 1.0/`

---

## 1) الهدف من هذا المستند

هذا المستند يوثق الهوية البصرية والتصميمية لمنصة "حرب الأسماء" كما تم تنفيذها فعليًا في النماذج الأولية. كل قرار تصميمي مذكور هنا مُستخرج مباشرة من الكود المنفذ — وليس توجهًا نظريًا أو مقترحًا. هذا المستند هو المرجع الرسمي عند بناء تطبيق React.

---

## 2) جرد الشاشات المنفذة (Screen Inventory)

| # | الملف | العنوان | النوع | الوصف |
|---|-------|---------|-------|-------|
| 02 | `02-navigation-updated.html` | قائمة المتسابقين | داخل اللعبة | لوحة الترتيب مع بحث وفلاتر وبطاقات لاعبين |
| 03 | `03-.html` | إنشاء حساب لاعب | تدفق المصادقة | نموذج تسجيل مع مراحل تقدم |
| 04 | `04-.html` | انضم للمسابقة | تدفق المصادقة | إدخال كود الدعوة واختيار اللقب |
| 05 | `05-player-dashboard-unified-navigation-linked.html` | لوحة التحكم | داخل اللعبة | لوحة اللاعب: إحصائيات، سجل معارك، مخزن، تحديات |
| 06 | `06-.html` | المتجر التكتيكي | داخل اللعبة | عرض العناصر مع تصنيفات + شريط الجرد الجانبي |
| 07 | `07-.html` | جلسة الاختبار | داخل اللعبة | واجهة أسئلة مع مؤقت ومساعدات وخيارات |
| 08 | `08-battle-result-linked-navigation.html` | نصر ساحق! | نتيجة معركة | شاشة فوز بعد هجوم ناجح |
| 09 | `09-lobby-linked.html` | Lobby | واجهة خاصة | واجهة انتظار غامرة بالكامل (داكنة فقط) |
| 10 | `10-battle-result-defeat-text-modified.html` | هزيمة! | نتيجة معركة | شاشة خسارة بعد هجوم فاشل |
| 11 | `11-.html` | مرجع المتجر الشامل | مرجعي | وثيقة مرجعية لكل عناصر المتجر ونظام الندرة |
| 12 | `12-.html` | مرجع المتجر الشامل | مرجعي | نسخة موسعة من مرجع المتجر |

---

## 3) نظام الألوان المعتمد (Color System)

### 3.1 الألوان الأساسية للعلامة (Brand Core)

هذه الألوان ثابتة في Tailwind config عبر جميع الشاشات القياسية:

| Token | القيمة | الدور |
|-------|--------|-------|
| `brand-teal` | `#0B8A8D` | اللون الأساسي للأفعال في الوضع الفاتح |
| `brand-teal-hover` | `#067a79` | حالة الهوفر للأساسي |
| `brand-teal-light` | `#17a2b8` | نسخة أفتح للتدرجات والتأكيدات الثانوية |
| `brand-slate` | `#64748B` | اللون الأساسي للأفعال في الوضع الداكن |
| `brand-orange` | `#D84315` | الخطر، الهجوم، الإلحاح، العناصر الأسطورية |
| `brand-dark` | `#1F2937` | خلفية البطاقات في الوضع الداكن |
| `brand-light-bg` | `#F8F9FA` | خلفية الصفحة في الوضع الفاتح |
| `brand-dark-bg` | `#111827` | خلفية الصفحة في الوضع الداكن |
| `brand-card-dark` | `#1F2937` | سطح البطاقات في الوضع الداكن |
| `brand-success` | `#10B981` | النجاح، الفوز، الحالة النشطة |
| `brand-danger` | `#EF4444` | الخسارة، الخطأ، الحالات الحرجة |

### 3.2 استراتيجية الألوان المزدوجة (Dual-Tone Strategy)

قرار تصميمي جوهري: **اللون الأساسي يتغير بين الوضعين:**
- **الوضع الفاتح:** `brand-teal` (#0B8A8D) هو لون الأفعال الأساسية
- **الوضع الداكن:** `brand-slate` (#64748B) يحل محل التيل كلون أساسي

هذا يظهر في كل مكان: الأزرار، الروابط، البادجات، أيقونات التنقل، المؤشرات.

**تطبيقات عملية:**
```
bg-brand-teal dark:bg-brand-slate           // أزرار أساسية
text-brand-teal dark:text-brand-slate       // نصوص مميزة
bg-brand-teal/10 dark:bg-brand-slate/20     // خلفيات خفيفة
border-brand-teal/20 dark:border-brand-slate/30  // حدود
```

### 3.3 ألوان الحالات داخل اللعبة (State Colors)

مُستخرجة من الشاشات المنفذة فعليًا:

| الحالة | العربي | اللون الفاتح | اللون الداكن | مثال الاستخدام |
|--------|--------|-------------|-------------|----------------|
| نشط | نشط | `emerald-600` مع نقطة `animate-pulse` | `emerald-400` | بادج الحالة في الليدربورد |
| محمي | محمي | `purple-600` مع أيقونة درع | `purple-400` | بادج حماية، زر هجوم معطل |
| مفلس | مفلس | `red-500` مع أيقونة شبح | `red-900` | صف معتم بـ `opacity-60` وخط مشطوب |
| انتظار | انتظار | `amber-600` | `amber-400` | بادج بسيط بدون أيقونة |
| فوز | نصر ساحق | `brand-success` (#10B981) | نفسه | شاشة النصر الكاملة |
| خسارة | هزيمة | `brand-danger` (#EF4444) | نفسه | شاشة الهزيمة الكاملة |

### 3.4 ألوان نظام الندرة (Rarity Colors)

من ملف المتجر المرجعي (11-.html):

| الندرة | العربي | اللون | المعالجة البصرية |
|--------|--------|-------|-----------------|
| عادي (Common) | عادي | `#94A3B8` | بادج رمادي بسيط |
| نادر (Rare) | نادر | `#0D47A1` | بادج داكن، بدج أسود |
| ملحمي (Epic) | ملحمي | `#64748B` | ظل خفيف `glow-epic` |
| أسطوري (Legendary) | أسطوري | `#D84315` | نبض متوهج `pulse-glow` مستمر |
| خرافي (Mythic) | خرافي | `#7C3AED` | توهج مكثف `pulse-glow-mythic` مع `scale(1.02)` |

### 3.5 ألوان الترتيب (Rank Badge Gradients)

من شاشة الليدربورد (02):

| المركز | التدرج الفاتح | التدرج الداكن |
|--------|--------------|--------------|
| #1 ذهبي | `135deg, #FDE68A → #F59E0B` | `135deg, #F59E0B → #B45309` |
| #2 فضي | `135deg, #E5E7EB → #9CA3AF` | `135deg, #9CA3AF → #4B5563` |
| #3 برونزي | `135deg, #FDBA74 → #D97706` | `135deg, #D97706 → #92400E` |
| #4+ عادي | خلفية `gray-50` | خلفية `gray-800/50` |

### 3.6 ألوان إضافية في شاشة اللوبي (Lobby-Specific)

شاشة اللوبي (09) تستخدم مجموعة موسعة للأزرار الملونة:

| Token | القيمة | الاستخدام |
|-------|--------|-----------|
| `brand-bg` | `#0a0d14` | خلفية اللوبي الأساسية |
| `brand-surface` | `#151b29` | سطح عناصر اللوبي |
| `brand-teal-light` | `#00D9E9` | نسخة ساطعة للتوهج في اللوبي |
| `brand-purple` | `#9333EA` | زر الليدربورد في اللوبي |
| `brand-blue` | `#3B82F6` | زر القواعد في اللوبي |
| `brand-emerald` | `#10B981` | مؤشر الاتصال |
| `brand-border` | `#2A3142` | حدود اللوبي |

---

## 4) نظام الخطوط المعتمد (Typography System)

### 4.1 عائلات الخطوط

| الدور في Tailwind | الخط | مصدر التحميل |
|-------------------|------|-------------|
| `font-display` | Cairo | Google Fonts |
| `font-heading` | Changa | Google Fonts |
| `font-body` | Cairo | Google Fonts |

### 4.2 الأوزان المستخدمة

- **Cairo:** 400, 600, 700, 800, 900
- **Changa:** 400, 600, 700, 800

### 4.3 التطبيق العملي كما ظهر في الشاشات

| الموقع | الخط | الوزن | الأحجام النموذجية |
|--------|------|-------|-------------------|
| عناوين الصفحات الرئيسية | `font-display` | `font-black` (900) | `text-4xl md:text-5xl` أو `text-5xl md:text-7xl` |
| عناوين البطاقات والأقسام | `font-heading` | `font-black` (800) | `text-lg` أو `text-xl` |
| أسماء الأزرار والإجراءات | `font-heading` | `font-bold` أو `font-black` | `text-sm` أو `text-lg` |
| نص الجسم والوصف | `font-body` (inherited) | `font-medium` أو `font-bold` | `text-sm` أو `text-base` |
| التسميات الصغيرة والبادجات | `font-heading` أو `font-display` | `font-black` أو `font-bold` | `text-[10px]` أو `text-xs` |
| الأرقام الكبيرة (نقاط/مراكز) | `font-display` | `font-black` | `text-2xl` إلى `text-6xl` |
| نص المساعدة | (inherited) | `font-bold` | `text-[10px]` |

### 4.4 أنماط نصية بارزة

- **تسميات uppercase مع tracking:** `text-[10px] font-black uppercase tracking-widest` — تُستخدم فوق الإحصائيات الكبيرة
- **النقاط كأرقام:** دائمًا بـ `font-display font-black` بأحجام كبيرة
- **التأكيد بالحجم لا بالزخرفة:** لا يوجد underline أو italic في العناوين — التأكيد بالحجم والوزن فقط

---

## 5) نظام الأيقونات (Icon System)

### 5.1 المكتبة

**Iconify** عبر web component:
```html
<script src="https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js"></script>
```

### 5.2 مجموعات الأيقونات المستخدمة

| المجموعة | الاستخدام | أمثلة |
|----------|-----------|-------|
| `lucide:*` | أيقونات الواجهة الأساسية | `lucide:swords`, `lucide:trophy`, `lucide:zap`, `lucide:shield-check`, `lucide:home`, `lucide:search`, `lucide:moon`, `lucide:sun`, `lucide:user`, `lucide:arrow-left`, `lucide:chevron-left`, `lucide:crown`, `lucide:flame`, `lucide:target`, `lucide:history`, `lucide:package`, `lucide:shopping-bag`, `lucide:shopping-cart`, `lucide:help-circle`, `lucide:timer`, `lucide:award`, `lucide:ghost`, `lucide:gift`, `lucide:lightbulb`, `lucide:bell`, `lucide:settings`, `lucide:book-open`, `lucide:at-sign`, `lucide:lock`, `lucide:eye`, `lucide:key`, `lucide:check`, `lucide:x-circle`, `lucide:trending-down`, `lucide:plus`, `lucide:trash-2`, `lucide:dollar-sign`, `lucide:sliders-horizontal` |
| `mdi:*` | أيقونات عناصر اللعبة | `mdi:bomb`, `mdi:shield-outline`, `mdi:magic-staff`, `mdi:sword-cross`, `mdi:flare` |

### 5.3 أحجام الأيقونات النموذجية

| السياق | الحجم |
|--------|-------|
| داخل زر التنقل السفلي | `text-[1.3rem]` |
| داخل أزرار ونصوص | `text-lg` أو `text-xl` |
| أيقونات إحصائيات كبيرة | `text-3xl` إلى `text-5xl` |
| أيقونات بطاقات عناصر المتجر | `text-6xl` |
| أيقونة شاشة النتيجة الرئيسية | `text-4xl md:text-5xl` |

---

## 6) أنماط الخلفيات والأنسجة (Background Patterns)

### 6.1 النمط الرئيسي للصفحات `.bg-pattern-main`

خطوط قطرية دقيقة بزاوية 45 درجة — تظهر في كل الشاشات القياسية:

```css
/* الوضع الفاتح */
background-image: repeating-linear-gradient(
  45deg,
  rgba(31, 41, 55, 0.02) 0,
  rgba(31, 41, 55, 0.02) 2px,
  transparent 2px,
  transparent 12px
);

/* الوضع الداكن */
background-image: repeating-linear-gradient(
  45deg,
  rgba(229, 231, 235, 0.02) 0,
  rgba(229, 231, 235, 0.02) 2px,
  transparent 2px,
  transparent 12px
);
```

### 6.2 نمط الفوتر `.bg-footer-pattern`

خطوط قطرية عكسية (-45 درجة) على خلفية داكنة:

```css
background-color: #1F2937;
background-image: repeating-linear-gradient(
  -45deg,
  transparent, transparent 15px,
  rgba(255, 255, 255, 0.02) 15px,
  rgba(255, 255, 255, 0.02) 30px
);
```

### 6.3 أشكال ضبابية ديكورية

البطاقات الكبيرة تحتوي على دوائر ضبابية ديكورية في الزوايا:
```html
<div class="absolute top-0 right-0 w-32 h-32 bg-brand-teal/5 dark:bg-brand-slate/5
     rounded-full -translate-y-1/2 translate-x-1/2"></div>
<div class="absolute bottom-0 left-0 w-24 h-24 bg-brand-orange/5
     rounded-full blur-xl -ml-12 -mb-12"></div>
```

### 6.4 خلفية اللوبي — نمط السداسيات (Hexagon Pattern)

شاشة اللوبي (09) تستخدم خلفية سداسية SVG فريدة:
```css
.hex-bg {
  background-image: url("data:image/svg+xml,...hexagon SVG...");
  background-size: 100px 173.2px;
}
```
مع أشكال SVG سداسية دوارة كعناصر خلفية متحركة.

---

## 7) نظام التخطيط والتنقل (Layout & Navigation)

### 7.1 الاتجاه العام

كل الشاشات تستخدم `<html lang="ar" dir="rtl">`.

الهيكل العام مبني بـ `flex-row-reverse` في الهيدر لعكس الترتيب مع الحفاظ على توافق RTL:
```html
<div class="max-w-7xl mx-auto flex items-center justify-between flex-row-reverse">
```

### 7.2 الهيكل العام للصفحة

```
┌─────────────────────────────────────────┐
│  Header (sticky top-0 z-50)             │  view-transition-name: main-header/main-nav
│  ┌─────────┬──────────┬──────────────┐  │
│  │ Controls│   Nav    │  Logo+Season │  │  (flex-row-reverse)
│  └─────────┴──────────┴──────────────┘  │
├─────────────────────────────────────────┤
│  Main Content                           │  view-transition-name: main-content
│  max-w-5xl / max-w-7xl mx-auto          │
│  px-4 py-8 md:py-12                     │
│  space-y-8 / space-y-10                 │
├─────────────────────────────────────────┤
│  Footer                                 │  view-transition-name: footer (بعض الشاشات)
│  bg-footer-pattern py-12                │
├─────────────────────────────────────────┤
│  Mobile Bottom Nav (md:hidden)          │  view-transition-name: mobile-nav
│  fixed bottom-0 z-50                    │
└─────────────────────────────────────────┘
```

### 7.3 التنقل العلوي (Desktop Header)

```html
<header class="sticky top-0 z-50 bg-white dark:bg-brand-card-dark
  border-b border-gray-200 dark:border-gray-800
  p-4 md:px-6 md:py-4 transition-colors duration-300 shadow-sm">
```

**العناصر (من اليمين لليسار في RTL):**
1. **الشعار + الموسم:** شعار الصورة (130px/150px) مع نص الموسم الحالي
2. **روابط التنقل:** الرئيسية، المتصدرين، المتجر، قواعد اللعبة
3. **أدوات المستخدم:** زر تبديل الثيم + ملف المستخدم المصغر (اسم + نقاط + حرف أول)

**حالة الرابط النشط:**
```
bg-brand-teal/10 dark:bg-brand-slate/20
text-brand-teal dark:text-brand-slate font-black
```

**حالة الرابط العادي:**
```
text-gray-600 dark:text-gray-300
hover:text-brand-teal dark:hover:text-brand-slate
hover:bg-gray-50 dark:hover:bg-gray-800/50 font-bold
```

### 7.4 التنقل السفلي (Mobile Bottom Nav)

```html
<nav class="md:hidden fixed bottom-0 w-full bg-white dark:bg-brand-card-dark
  border-t border-gray-100 dark:border-gray-800
  flex justify-around items-center py-2 px-2 z-50
  shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]
  dark:shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.2)]">
```

**5 عناصر:**
1. الرئيسية (`lucide:home`)
2. المتصدرين (`lucide:trophy`)
3. **زر الهجوم (FAB مرتفع)** (`lucide:swords`)
4. المتجر (`lucide:shopping-bag`)
5. حسابي (`lucide:user`)

**زر الهجوم المركزي — التصميم الفريد:**
```html
<button class="flex flex-col items-center justify-center
  w-12 h-12 bg-brand-teal text-white dark:bg-brand-orange/80
  rounded-full -mt-6
  border-[3px] border-brand-light-bg dark:border-brand-dark-bg
  shadow-sm active:scale-95">
  <iconify-icon icon="lucide:swords" class="text-2xl"></iconify-icon>
</button>
```

**ملاحظة مهمة:** في الوضع الداكن، زر الهجوم يتحول من تيل إلى برتقالي (`dark:bg-brand-orange/80`).

### 7.5 عروض المحتوى (Content Widths)

| الشاشة | العرض |
|--------|-------|
| الليدربورد (02) | `max-w-5xl` |
| لوحة اللاعب (05) | `max-w-7xl` |
| المتجر (06) | `max-w-7xl` |
| جلسة الأسئلة (07) | `max-w-4xl` |
| نتائج المعارك (08, 10) | `max-w-4xl` |
| شاشات المصادقة (03, 04) | `max-w-lg` |

---

## 8) نظام البطاقات والأسطح (Card & Surface System)

### 8.1 البطاقة القياسية

```html
<div class="bg-white dark:bg-brand-card-dark
  border border-gray-200 dark:border-gray-700
  rounded-2xl shadow-sm
  hover:shadow-md dark:hover:shadow-black/20
  smooth-transition hover:-translate-y-1">
```

### 8.2 البطاقة الكبيرة (Hero/Section Cards)

```html
<div class="bg-white dark:bg-brand-card-dark
  border border-gray-200 dark:border-gray-700
  rounded-3xl shadow-sm p-6 md:p-10
  relative overflow-hidden">
```

### 8.3 بطاقة المصادقة (Auth Cards)

```html
<div class="bg-white dark:bg-brand-card-dark
  border border-gray-200 dark:border-gray-800
  rounded-3xl shadow-xl p-8 md:p-10
  relative overflow-hidden">
```

### 8.4 بطاقة عنصر المتجر

```html
<div class="group bg-white dark:bg-brand-card-dark
  border border-gray-200 dark:border-gray-700
  rounded-2xl shadow-sm hover:shadow-md
  smooth-transition flex flex-col min-h-[360px] p-5">
```

### 8.5 بطاقة العنصر الفريد (Special Featured Item)

```html
<div class="group bg-white dark:bg-[#151c2b]
  border-2 border-brand-orange/20 dark:border-brand-orange/30
  rounded-2xl shadow-sm p-6 sm:p-8
  sm:col-span-2 xl:col-span-3
  relative overflow-hidden">
```

### 8.6 نظام انحناء الزوايا (Border Radius Scale)

| الاستخدام | الفئة | القيمة |
|-----------|-------|--------|
| بادجات صغيرة | `rounded-md` | 6px |
| أزرار التنقل | `rounded-lg` | 8px |
| أزرار، حقول إدخال، عناصر صغيرة | `rounded-xl` | 12px |
| بطاقات قياسية | `rounded-2xl` | 16px |
| بطاقات كبيرة، أقسام رئيسية | `rounded-3xl` | 24px |
| بطاقة Hero (لوحة اللاعب) | `rounded-[2rem]` | 32px |

### 8.7 Chamfered Cards (بطاقات مشطوفة)

تُستخدم كأسلوب بصري مميز في بعض العناصر:
```css
.chamfer-card {
  clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px),
    calc(100% - 12px) 100%, 0 100%, 0 12px);
}
.chamfer-btn {
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px),
    calc(100% - 8px) 100%, 0 100%, 0 8px);
}
```

---

## 9) نظام الأزرار (Button System)

### 9.1 الزر الأساسي (Primary)

```html
<button class="btn-press bg-brand-teal hover:bg-brand-teal-hover text-white
  dark:bg-brand-slate/80 dark:hover:bg-brand-slate
  py-4 rounded-xl font-heading font-black text-lg
  shadow-lg shadow-brand-teal/20
  smooth-transition">
```

### 9.2 زر الهجوم (Attack/Danger)

```html
<a class="btn-press bg-brand-teal hover:bg-brand-teal-hover text-white
  dark:bg-brand-orange/80 dark:hover:bg-brand-orange
  py-2.5 rounded-xl font-heading font-bold text-sm tracking-wider
  shadow-sm hover:shadow smooth-transition">
  هجوم
</a>
```

### 9.3 زر CTA كبير (Hero Action)

```html
<a class="btn-press bg-gradient-to-r from-brand-orange to-[#e65100]
  hover:from-[#e65100] hover:to-[#ff5722]
  text-white px-8 py-4 md:py-5 rounded-2xl
  font-heading font-black text-xl
  shadow-lg shadow-brand-orange/20
  flex items-center justify-center gap-3
  smooth-transition hover:-translate-y-1">
  <iconify-icon icon="lucide:swords" class="text-3xl"></iconify-icon>
  ابدأ الهجوم
</a>
```

### 9.4 الزر الثانوي (Secondary/Outlined)

```html
<a class="btn-press bg-white dark:bg-brand-card-dark
  border-2 border-gray-200 hover:border-brand-teal
  dark:border-gray-700 dark:hover:border-brand-teal
  text-gray-700 hover:text-brand-teal
  py-4 md:py-5 rounded-2xl font-heading font-black text-lg
  shadow-sm hover:shadow-md smooth-transition">
```

### 9.5 الزر المعطل (Disabled)

```html
<button disabled class="opacity-60 cursor-not-allowed
  bg-gray-100 dark:bg-gray-800
  text-gray-400 dark:text-gray-500
  py-2.5 rounded-xl font-heading font-bold text-sm">
  مغلق
</button>
```

### 9.6 زر شراء في المتجر

```html
<button class="btn-press w-full bg-brand-teal dark:bg-brand-slate/20
  text-white dark:text-brand-slate
  font-heading font-bold py-3 rounded-xl
  flex items-center justify-center gap-2
  hover:bg-brand-teal-hover dark:hover:bg-brand-slate/30
  smooth-transition border dark:border-brand-slate/30">
  <iconify-icon icon="lucide:shopping-cart"></iconify-icon>
  1,200 نقطة
</button>
```

### 9.7 سلوك الضغط (Press Behavior)

```css
.btn-press:active {
  transform: scale(0.98) translateY(2px);
}
```

---

## 10) نظام الحركة والانتقالات (Motion & Animation System)

### 10.1 الانتقال القياسي

```css
.smooth-transition {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
```

### 10.2 انتقالات العرض (View Transitions API)

```css
@view-transition { navigation: auto; }
```

**العناصر الثابتة (بدون حركة):**
```css
::view-transition-old(main-header),
::view-transition-new(main-header),
::view-transition-old(mobile-nav),
::view-transition-new(mobile-nav) {
  animation: none;
  mix-blend-mode: normal;
}
```

**المحتوى الرئيسي (اختفاء/ظهور مع إزاحة):**
```css
::view-transition-old(main-content) {
  animation: 0.2s-0.25s ease-out both fade-out;
}
::view-transition-new(main-content) {
  animation: 0.25s-0.3s ease-in 0.1s both fade-in;
}

@keyframes fade-out {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-10px); }
}
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### 10.3 أسماء View Transition المستخدمة

| الاسم | الشاشات | السلوك |
|-------|---------|--------|
| `main-header` | الليدربورد | ثابت (بدون حركة) |
| `main-nav` | اللوحة، المتجر، الأسئلة، النتائج | ثابت (بدون حركة) |
| `mobile-nav` | جميع الشاشات الداخلية | ثابت (بدون حركة) |
| `main-content` | جميع الشاشات | اختفاء/ظهور متحرك |
| `brand` | شاشات المصادقة (03, 04) | ثابت (الشعار) |
| `footer` | نتائج المعارك | ثابت |

### 10.4 حركات الهوفر

| العنصر | الحركة |
|--------|--------|
| البطاقات | `hover:-translate-y-1` |
| أزرار الهيدر | `hover:-translate-y-0.5` |
| أيقونات الإحصائيات | `group-hover:scale-110` |
| أيقونات عناصر المتجر | `group-hover:scale-110` |
| البطاقات (shadow) | `hover:shadow-md dark:hover:shadow-black/20` |

### 10.5 حركات خاصة

| الحركة | الاستخدام |
|--------|-----------|
| `floating` (3s ease-in-out infinite) | أيقونة شاشة النتيجة (فوز/هزيمة) |
| `animate-pulse` | نقطة الحالة "نشط" |
| `animate-bounce` | أيقونة الهدية في المتجر، توست الإجابة الصحيحة |
| `shimmer` (3s infinite linear) | بادج الندرة الفريدة |
| `progress-glow` | شريط تقدم الأسئلة (box-shadow brand-teal) |

### 10.6 حركات اللوبي (خاصة)

شاشة اللوبي تستخدم نظام حركة متقدم:

| الحركة | الوصف | التوقيت |
|--------|-------|---------|
| `slideDownFade` | الهيدر ينزلق من الأعلى | 0.8s cubic-bezier(0.16, 1, 0.3, 1) |
| `fadeInScale` | الشعار يظهر مع تكبير وتوهج | 1s cubic-bezier(0.16, 1, 0.3, 1) |
| `rotateShape` | سداسيات الخلفية تدور | 45s linear infinite |
| `rotateShapeReverse` | سداسيات عكسية | 55s linear infinite |
| `shimmerSlide` | لمعان الأزرار عند الهوفر | 3s infinite linear |
| Magnetic hover | الأزرار تتبع مؤشر الماوس | JS-driven, 0.10 multiplier |

**منحنيات التوقيت المخصصة للوبي:**
```
spring: cubic-bezier(0.175, 0.885, 0.32, 1.275)
smooth: cubic-bezier(0.25, 1, 0.5, 1)
```

---

## 11) استراتيجية الوضع الداكن (Dark Mode Strategy)

### 11.1 آلية التفعيل

```javascript
tailwind.config = { darkMode: 'class' }
```
يُخزن في `localStorage.theme` ويُقرأ عند تحميل الصفحة.

### 11.2 جدول التحويل

| العنصر | الوضع الفاتح | الوضع الداكن |
|--------|-------------|-------------|
| خلفية الصفحة | `bg-brand-light-bg` (#F8F9FA) | `bg-brand-dark-bg` (#111827) |
| خلفية البطاقة | `bg-white` | `bg-brand-card-dark` (#1F2937) |
| حدود البطاقة | `border-gray-200` | `border-gray-700` أو `border-gray-800` |
| النص الرئيسي | `text-gray-800` أو `text-gray-900` | `text-gray-200` أو `text-white` |
| النص الثانوي | `text-gray-500` | `text-gray-400` |
| اللون الأساسي | `brand-teal` | `brand-slate` |
| خلفية الإدخال | `bg-gray-100` أو `bg-gray-50` | `bg-gray-900/50` أو `bg-gray-800` |
| الظلال | `shadow-sm/md` | `shadow-none` أو `shadow-black/20` |
| الهيدر | `bg-white` | `bg-brand-card-dark` |
| الفوتر | `bg-[#1F2937]` | `bg-[#0f141f]` |
| زر الهجوم (جوال) | `bg-brand-teal` | `bg-brand-orange/80` |

### 11.3 نمط التلوين الشفاف (Opacity-based Coloring)

في الوضع الداكن، الألوان المميزة تُستخدم بشفافية أعلى:
```
الفاتح: bg-brand-teal/10
الداكن: dark:bg-brand-slate/20   (شفافية أعلى للتعويض)
```

---

## 12) نظام حقول الإدخال (Form Input System)

### 12.1 حقل الإدخال القياسي

```html
<input class="w-full bg-gray-100 dark:bg-gray-900/50
  border border-gray-200 dark:border-gray-700
  py-3.5 pr-11 pl-4 rounded-xl font-bold
  focus:outline-none focus:ring-2
  focus:ring-brand-teal/10 focus:border-brand-teal
  dark:focus:border-brand-slate dark:focus:ring-brand-slate/20
  transition-all
  text-gray-800 dark:text-white
  placeholder:text-gray-400">
```

### 12.2 حقل بحث (Search Input)

```html
<div class="relative bg-white dark:bg-brand-card-dark
  border border-gray-200 dark:border-gray-700
  focus-within:border-brand-teal dark:focus-within:border-brand-slate
  focus-within:ring-2 focus-within:ring-brand-teal/20
  rounded-xl shadow-sm overflow-hidden">
  <iconify-icon icon="lucide:search"
    class="absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 text-xl">
  </iconify-icon>
  <input class="w-full bg-transparent py-3.5 pr-14 pl-6 font-medium
    focus:outline-none text-gray-800 dark:text-gray-200 placeholder-gray-400">
</div>
```

### 12.3 أيقونة داخل الحقل

الأيقونة تُوضع بشكل مطلق (absolute) داخل `relative` wrapper مع `pointer-events-none`، وتتلون عند التركيز عبر `group-focus-within:text-brand-teal`.

---

## 13) نظام البادجات والحالات (Badge & Status System)

### 13.1 بادج الحالة "نشط"

```html
<span class="bg-emerald-50 text-emerald-600
  dark:bg-emerald-900/20 dark:text-emerald-400
  px-3 py-1 rounded-md text-[11px] font-bold
  flex items-center gap-2">
  <span class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
  نشط
</span>
```

### 13.2 بادج "محمي"

```html
<span class="bg-purple-50 text-purple-600
  dark:bg-purple-900/20 dark:text-purple-400
  px-3 py-1 rounded-md text-[11px] font-bold
  flex items-center gap-1.5">
  <iconify-icon icon="lucide:shield-check"></iconify-icon>
  محمي
</span>
```

### 13.3 بادج "مفلس"

```html
<span class="bg-red-50 text-red-500
  dark:bg-red-900/10 dark:text-red-900
  px-3 py-1 rounded-md text-[11px] font-bold
  flex items-center gap-1.5">
  <iconify-icon icon="lucide:ghost"></iconify-icon>
  مفلس
</span>
```

### 13.4 بادج "انتظار"

```html
<span class="bg-amber-50 text-amber-600
  dark:bg-amber-900/20 dark:text-amber-400
  px-3 py-1 rounded-md text-[11px] font-bold">
  انتظار
</span>
```

### 13.5 بادج الندرة

```html
<!-- عادي -->
<span class="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300
  text-[10px] font-black px-2.5 py-1 rounded shadow-sm">عادي</span>

<!-- نادر -->
<span class="bg-gray-800 dark:bg-gray-900 text-white dark:text-gray-300
  text-[10px] font-black px-2.5 py-1 rounded shadow-sm">نادر</span>

<!-- أسطوري -->
<span class="bg-brand-teal text-white dark:bg-brand-slate
  text-[10px] font-black px-2.5 py-1 rounded shadow-sm">أسطوري</span>

<!-- فريد (مع تأثير لامع) -->
<span class="text-[10px] font-black rarity-unique-glow text-white
  px-4 py-1.5 rounded-full border border-brand-orange/20">عنصر فريد</span>
```

---

## 14) قوالب الصفحات المعتمدة (Page Templates)

### 14.1 القالب A — صفحة القائمة المرتبة (Ranked Collection)

**الشاشة:** الليدربورد (02)

**الهيكل:**
1. عنوان الصفحة مع إحصائيات سريعة (بطاقة المركز الحالي)
2. بطاقة "مركزك" للجوال (sticky)
3. شريط بحث + فلتر
4. تسميات أعمدة الجدول (desktop only)
5. قائمة بطاقات اللاعبين (grid 12 أعمدة على desktop)
6. زر "استكشاف المزيد"

### 14.2 القالب B — لوحة التحكم (Dashboard)

**الشاشة:** لوحة اللاعب (05)

**الهيكل:**
1. قسم Hero (بطاقة كبيرة: أفاتار + معلومات + CTA)
2. شبكة إحصائيات (2x2 على الجوال، 4 أعمدة على desktop)
3. تخطيط عمودين (8/4 على desktop): محتوى رئيسي + شريط جانبي
4. العمود الرئيسي: سجل المعارك + المخزن
5. العمود الجانبي: بطاقة السلسلة + تحديات اليوم

### 14.3 القالب C — المتجر (Store/Grid)

**الشاشة:** المتجر التكتيكي (06)

**الهيكل:**
1. عنوان الصفحة مع وصف
2. تخطيط 4 أعمدة (3 للمحتوى + 1 للجرد الجانبي)
3. تبويبات تصنيف + بحث
4. شبكة بطاقات العناصر (1-2-3 أعمدة حسب الشاشة)
5. عنصر مميز يمتد على عرض كامل
6. شريط جرد جانبي ثابت (sticky)
7. قسم نصائح تكتيكية

### 14.4 القالب D — نتيجة / مخرجات (Outcome)

**الشاشات:** الفوز (08)، الهزيمة (10)

**الهيكل:**
1. أيقونة كبيرة متحركة (floating) مع توهج ملون
2. عنوان ضخم (text-5xl md:text-7xl) ملون بلون النتيجة
3. نص وصفي
4. شبكة إحصائيتين (النقاط + المركز الجديد)
5. بطاقة رد فعل الخصم
6. أزرار إجراء (العودة + هجوم آخر)

### 14.5 القالب E — تدفق المصادقة (Auth Flow)

**الشاشات:** التسجيل (03)، الانضمام (04)

**الهيكل:**
1. شعار العلامة في الأعلى (brand view-transition)
2. مؤشر تقدم المراحل (شريط مئوي)
3. بطاقة مركزية واحدة (max-w-lg)
4. حقول إدخال مع أيقونات
5. زر إجراء أساسي
6. رابط بديل (تسجيل الدخول / الرجوع)
7. فوتر بسيط

### 14.6 القالب F — جلسة اللعب المركزة (Focused Play)

**الشاشة:** جلسة الأسئلة (07)

**الهيكل:**
1. هيدر التنقل العادي (مع نص "جلسة الأسئلة المباشرة")
2. شريط التقدم + النقاط المكتسبة
3. مؤقت عائم (SVG دائري) فوق البطاقة
4. بطاقة السؤال الكبيرة (rounded-3xl shadow-xl)
5. شبكة خيارات (2x2)
6. أزرار مساعدة (حذف إجابتين / تجميد الوقت)
7. زر "السؤال التالي"
8. توست إجابة صحيحة (fixed bottom-center)

### 14.7 القالب G — اللوبي الغامر (Immersive Lobby)

**الشاشة:** اللوبي (09)

**الهيكل:**
1. خلفية كاملة الشاشة (أشكال سداسية دوارة + توهجات)
2. هيدر بسيط (مؤشر اتصال + أيقونات إشعارات/إعدادات)
3. شعار مركزي كبير مع تأثير توهج
4. شبكة أزرار 4 بترتيب قوس (arc)
5. كل زر بلون مميز: تيل (صفحتي)، بنفسجي (الصدارة)، برتقالي (المتجر)، أزرق (القواعد)
6. تأثير مغناطيسي على الأزرار (JS)
7. لا يوجد فوتر ولا تنقل سفلي

---

## 15) أنماط المكونات المتكررة (Recurring Component Patterns)

### 15.1 بطاقة الإحصائية

```html
<div class="bg-white dark:bg-brand-card-dark p-8 md:p-10 rounded-2xl
  border border-gray-200 dark:border-gray-700 shadow-sm
  hover:shadow-md smooth-transition flex flex-col items-center
  justify-center text-center group hover:-translate-y-1">
  <iconify-icon icon="..." class="text-[color] mb-3 text-5xl
    group-hover:scale-110 smooth-transition drop-shadow-sm"></iconify-icon>
  <span class="text-gray-500 dark:text-gray-400 text-xs font-black
    uppercase tracking-widest mb-1">التسمية</span>
  <div class="text-5xl md:text-6xl font-black text-gray-900 dark:text-white">
    القيمة
  </div>
</div>
```

### 15.2 صف في سجل المعارك

```html
<div class="p-6 px-8 flex flex-col md:flex-row md:items-center
  justify-between gap-4 hover:bg-gray-50 dark:hover:bg-gray-800/30
  smooth-transition">
  <div class="flex items-center gap-5">
    <div class="w-14 h-14 rounded-2xl bg-[state-color]-50 dark:bg-[state-color]-900/20
      text-[state-color] flex items-center justify-center shadow-sm">
      <iconify-icon icon="..." class="text-2xl"></iconify-icon>
    </div>
    <div>
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-[state-color]"></span>
        <div class="font-bold text-gray-900 dark:text-white text-lg">الوصف</div>
      </div>
      <div class="text-sm font-bold text-gray-500 dark:text-gray-400 mt-1
        flex items-center gap-2">
        <iconify-icon icon="lucide:clock" class="text-xs"></iconify-icon>
        منذ 15 دقيقة
      </div>
    </div>
  </div>
  <div class="text-[state-color] font-black text-xl">+450 نقطة</div>
</div>
```

### 15.3 عنصر الجرد (Inventory Item)

```html
<div class="bg-white dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700
  p-3.5 rounded-xl shadow-sm
  hover:border-brand-teal dark:hover:border-brand-slate
  group smooth-transition">
  <!-- أيقونة + معلومات + كمية -->
  <div class="mt-3 flex gap-2">
    <button class="flex-1 btn-press bg-brand-teal/10 dark:bg-brand-slate/20
      text-brand-teal dark:text-brand-slate font-heading font-bold text-xs
      py-2 rounded-lg hover:bg-brand-teal hover:text-white smooth-transition">
      استخدام
    </button>
    <button class="w-10 h-10 flex items-center justify-center bg-gray-100
      dark:bg-gray-800 rounded-lg hover:bg-brand-danger hover:text-white
      text-gray-500 transition-colors">
      <iconify-icon icon="lucide:trash-2"></iconify-icon>
    </button>
  </div>
</div>
```

### 15.4 شريط التقدم (Progress Bar)

```html
<div class="h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
  <div class="h-full bg-brand-teal dark:bg-brand-slate w-[40%] rounded-full"></div>
</div>
```

**النسخة المتقدمة مع تدرج:**
```html
<div class="h-full bg-gradient-to-l from-brand-teal to-brand-teal-light
  dark:from-brand-slate dark:to-[#4f5c6e] rounded-full"></div>
```

### 15.5 إشعارات Toast

```html
<div class="fixed bottom-24 md:bottom-8 right-4 md:right-8 z-[100]">
  <div class="bg-white dark:bg-brand-card-dark
    border-l-4 border-brand-success rounded-xl shadow-lg
    p-4 flex items-center gap-4 min-w-[280px]">
    <div class="w-10 h-10 rounded-full bg-brand-success/10 text-brand-success
      flex items-center justify-center">
      <iconify-icon icon="lucide:check" class="text-xl"></iconify-icon>
    </div>
    <div>
      <div class="font-heading font-black text-gray-900 dark:text-white">العنوان</div>
      <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">التفاصيل</div>
    </div>
  </div>
</div>
```

### 15.6 زر تبديل الثيم

```html
<button class="w-11 h-11 bg-gray-50 dark:bg-gray-800
  border border-gray-200 dark:border-gray-700
  flex items-center justify-center rounded-xl text-xl
  text-gray-600 dark:text-gray-300
  hover:bg-gray-100 dark:hover:bg-gray-700
  smooth-transition hover:-translate-y-0.5 shadow-sm">
  <iconify-icon icon="lucide:moon" class="dark:hidden"></iconify-icon>
  <iconify-icon icon="lucide:sun" class="hidden dark:block"></iconify-icon>
</button>
```

### 15.7 خيارات الأسئلة (Quiz Options)

**الحالة العادية:**
```html
<button class="btn-press group relative flex items-center justify-between
  p-5 bg-white dark:bg-gray-800/50
  border-2 border-gray-200 dark:border-gray-700
  hover:border-brand-teal dark:hover:border-brand-slate
  hover:bg-gray-50 dark:hover:bg-gray-800
  rounded-2xl smooth-transition text-right shadow-sm hover:shadow-md">
```

**الحالة المحددة:**
```html
<button class="btn-press group relative flex items-center justify-between
  p-5 bg-brand-teal/5 dark:bg-brand-slate/10
  border-2 border-brand-teal dark:border-brand-slate
  rounded-2xl text-right shadow-sm">
  <!-- علامة صح -->
  <div class="absolute -top-2 -right-2 bg-brand-teal text-white
    w-5 h-5 rounded-full flex items-center justify-center shadow-sm">
    <iconify-icon icon="lucide:check" class="text-[10px]"></iconify-icon>
  </div>
</button>
```

---

## 16) الاستجابة والتصميم المتجاوب (Responsive Strategy)

### 16.1 نقاط الكسر المستخدمة

| النقطة | الكلاس | الاستخدام |
|--------|--------|-----------|
| جوال | (افتراضي) | التصميم الأساسي — الأولوية للمتسابق |
| متوسط | `md:` (768px) | إظهار التنقل العلوي، إخفاء السفلي |
| كبير | `lg:` (1024px) | تخطيطات متعددة الأعمدة |
| كبير جدًا | `xl:` (1280px) | شبكات أكثر كثافة |

### 16.2 أنماط التحويل بين الأحجام

| المكون | جوال | desktop |
|--------|------|---------|
| التنقل | bottom nav (fixed) | top horizontal nav (sticky) |
| بطاقة المركز | sticky أسفل الهيدر | inline في عنوان الصفحة |
| شبكة الإحصائيات | `grid-cols-2` | `grid-cols-4` |
| بطاقات المتجر | `grid-cols-1` | `sm:grid-cols-2 xl:grid-cols-3` |
| تخطيط Dashboard | عمود واحد | `lg:grid-cols-12` (8+4) |
| تخطيط المتجر | عمود واحد | `lg:grid-cols-4` (3+1) |
| خيارات الأسئلة | عمود واحد | `md:grid-cols-2` |
| أعمدة الجدول | مخفية (`.hide-mobile`) | مرئية |

### 16.3 قاعدة padding العامة

```
الصفحة: px-4 py-8 md:py-12
البطاقات: p-5 أو p-6 md:p-8 أو md:p-10
الهيدر: p-4 md:px-6 md:py-4
```

---

## 17) نبرة الواجهة والنصوص (Microcopy & Voice)

### 17.1 أمثلة فعلية من الشاشات المنفذة

| الموقع | النص | النبرة |
|--------|------|--------|
| وصف الليدربورد | "تنافس مع أفضل المحاربين وارتقِ في التصنيف" | تحفيزية واضحة |
| وصف الحساب | "أدخل بياناتك الأساسية للبدء في رحلة الغزو والسيطرة" | مرحة + لعبية |
| وصف الانضمام | "أدخل كود المسابقة واختر لقبك، لكن انتبه لحد يعرف من انت!" | شبابية + تحذير مرح |
| وصف المتجر | "تسلّح بأفضل العناصر لتسيطر على ساحة حرب الأسماء" | قتالية + تنافسية |
| نصر | "لقد تفوقت في المبارزة وأثبت أن اسمك هو الأقوى في الميدان" | فخر وانتصار |
| هزيمة | "للأسف خسرت هذه المعركة، حاول مرة أخرى وتحسّن من مستواك" | تشجيعية رغم الخسارة |
| رد الخصم (فوز) | "يا لك من ماكر! لم أكن أتوقع هذا الهجوم الخاطف.." | شخصية حية |
| رد الخصم (خسارة) | "لقد كنت خصماً سهلاً! يبدو أنك تحتاج إلى المزيد من التدريب" | استفزازية مضبوطة |
| سلسلة انتصارات | "5 أيام متتالية!" | حماسية |
| بحث عن كود | "ما عندك كود؟ دورلك على واحد" | لهجة نجدية خفيفة |
| البايو | "وسع وسع يا فقير انت وياه، الأوله دايييم لنا ....." | لهجة شعبية مرحة |
| إجابة صحيحة | "إجابة صحيحة! +250 نقطة مكافأة سرعة" | مباشرة + مكافأة |

### 17.2 القواعد المستنتجة

1. **العناوين والتسميات:** عربية فصحى واضحة
2. **الأوصاف والرسائل التفاعلية:** أقرب للعامية المفهومة مع لمسة لعبية
3. **ردود الأفعال داخل اللعبة:** شخصية حية وممتعة
4. **التحذيرات والأوضاع:** واضحة ومباشرة بلا غموض
5. **لمسة اللهجة النجدية:** موجودة لكنها خفيفة ومحسوبة

---

## 18) ملاحظات تقنية للتحويل إلى React

### 18.1 المكونات المشتركة القابلة لإعادة الاستخدام

من تحليل الشاشات، هذه المكونات تتكرر ويجب استخراجها:

1. **AppHeader** — الهيدر مع التنقل والمستخدم المصغر
2. **MobileBottomNav** — التنقل السفلي مع FAB الهجوم
3. **AppFooter** — الفوتر مع bg-footer-pattern
4. **ThemeToggle** — زر تبديل الثيم
5. **UserMiniProfile** — حرف أول + اسم + نقاط
6. **StatCard** — بطاقة إحصائية مع أيقونة ورقم
7. **PlayerRow** — صف لاعب في الليدربورد
8. **RankBadge** — بادج الترتيب (ذهبي/فضي/برونزي/عادي)
9. **StatusBadge** — بادج الحالة (نشط/محمي/مفلس/انتظار)
10. **RarityBadge** — بادج الندرة
11. **ItemCard** — بطاقة عنصر في المتجر
12. **InventoryItem** — عنصر في الجرد الجانبي
13. **ProgressBar** — شريط تقدم
14. **QuizOption** — خيار في الأسئلة
15. **BattleHistoryRow** — صف في سجل المعارك
16. **Toast** — إشعار مؤقت
17. **SearchInput** — حقل بحث مع أيقونة

### 18.2 Tailwind Config المطلوب

```js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'brand-teal': '#0B8A8D',
        'brand-teal-hover': '#067a79',
        'brand-teal-light': '#17a2b8',
        'brand-slate': '#64748B',
        'brand-orange': '#D84315',
        'brand-dark': '#1F2937',
        'brand-light-bg': '#F8F9FA',
        'brand-dark-bg': '#111827',
        'brand-card-dark': '#1F2937',
        'brand-success': '#10B981',
        'brand-danger': '#EF4444',
        // Rarity system
        'rarity-common': '#94A3B8',
        'rarity-rare': '#0D47A1',
        'rarity-epic': '#64748B',
        'rarity-legendary': '#D84315',
        'rarity-mythic': '#7C3AED',
        // Lobby-specific
        'brand-bg': '#0a0d14',
        'brand-surface': '#151b29',
        'brand-purple': '#9333EA',
        'brand-blue': '#3B82F6',
        'brand-emerald': '#10B981',
        'brand-border': '#2A3142',
      },
      fontFamily: {
        display: ['Cairo', 'sans-serif'],
        heading: ['Changa', 'sans-serif'],
        body: ['Cairo', 'sans-serif'],
      },
    },
  },
}
```

### 18.3 CSS مخصص يجب نقله

1. `.bg-pattern-main` — نمط الخطوط القطرية
2. `.bg-footer-pattern` — نمط الفوتر
3. `.smooth-transition` — الانتقال المعياري
4. `.btn-press:active` — سلوك الضغط
5. `.chamfer-card` / `.chamfer-btn` — قص الزوايا
6. Rank badge gradients — تدرجات بادجات الترتيب
7. View Transitions CSS — انتقالات الصفحات
8. `.floating` animation — لشاشات النتائج
9. `.rarity-unique-glow` — لمعان الندرة الفريدة
10. `.progress-glow` — توهج شريط التقدم
11. Lobby-specific animations — حركات اللوبي المتقدمة

### 18.4 ملاحظات RTL

- كل الـ `flex-row-reverse` في الهيدر مقصود لـ RTL
- الأيقونات الاتجاهية (`arrow-left`, `chevron-left`) تظهر "يسارية" لكنها في RTL تشير لليمين (الاتجاه الصحيح)
- حقول الإدخال تستخدم `pr-` للأيقونة (الجانب الأيمن في RTL هو البداية)
- `text-right` في بعض الأماكن هو الافتراضي في RTL

---

## 19) ملخص الهوية البصرية

| الجانب | القرار المعتمد |
|--------|---------------|
| اللون الأساسي | Teal (#0B8A8D) فاتح / Slate (#64748B) داكن |
| لون الخطر والهجوم | Orange (#D84315) |
| الخطوط | Cairo (عرض + جسم) + Changa (عناوين) |
| الأيقونات | Iconify (lucide + mdi) |
| الزوايا | مدورة بكثافة (12px-32px) |
| الأسطح | مسطحة مع حدود + ظلال خفيفة |
| الحركة | سريعة ومضبوطة (0.2s) مع لمسات خاصة |
| الاتجاه | RTL أولًا |
| الثيم | فاتح + داكن (class-based) |
| النبرة | عربية واضحة + لمسة شبابية مرحة |
| الشعار | صورة خارجية (Supabase storage) |
| الحالة | نشط/محمي/مفلس/انتظار — كل واحدة بلون ومؤشر مميز |
| الندرة | 5 مستويات بألوان وتأثيرات متصاعدة |
