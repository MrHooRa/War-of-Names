import { Link } from 'react-router-dom'

const SECTIONS = [
  {
    id: 'goal',
    icon: 'lucide:target',
    iconColor: 'text-brand-teal',
    glowColor: 'from-brand-teal/20',
    title: 'هدف اللعبة',
    subtitle: 'اكشف الأقنعة وتصدّر الموسم',
    content: [
      { text: 'كل لاعب يختار كنية (اسم مستعار) — هويتك الحقيقية سرية.' },
      { text: 'هاجم لاعبين آخرين بتخمين هويتهم الحقيقية. إذا أصبت، تربح نقاطاً ويخسر الهدف.' },
      { text: 'اللاعب الذي يملك أعلى رصيد نقاط عند نهاية الموسم يفوز بالمنافسة.' },
      { text: 'الفوز ليس فقط بالهجوم — بل بالتخطيط الذكي، وإدارة النقاط، واستخدام العناصر بحكمة.' },
    ],
  },
  {
    id: 'attacks',
    icon: 'lucide:swords',
    iconColor: 'text-brand-orange',
    glowColor: 'from-brand-orange/20',
    title: 'نظام الهجوم',
    subtitle: 'خمّن، اربح، أو ادفع الثمن',
    content: [
      { text: 'اختر هدفاً من لوحة المتصدرين، ثم خمّن هويته الحقيقية من قائمة الأسماء.', icon: 'lucide:user-search' },
      { text: 'هجوم ناجح ← تحصل على مكافأة نقاط ويخسر الهدف.', icon: 'lucide:check-circle', color: 'text-brand-success' },
      { text: 'هجوم فاشل ← تخسر أنت نقاطاً كعقوبة.', icon: 'lucide:x-circle', color: 'text-brand-danger' },
      { text: 'المكافأة تتناقص مع تكرار الهجوم على نفس الهدف (انحلال المكافأة). نوّع أهدافك!', icon: 'lucide:trending-down', color: 'text-amber-400' },
      { text: 'بعد 3 هجمات ناجحة على نفس اللاعب، يحصل على حماية كاملة من هجماتك.', icon: 'lucide:shield-check' },
    ],
  },
  {
    id: 'protection',
    icon: 'lucide:shield',
    iconColor: 'text-blue-400',
    glowColor: 'from-blue-500/20',
    title: 'الحماية والإفلاس',
    subtitle: 'دفاعاتك وحدود البقاء',
    content: [
      { label: 'بدون حماية', text: 'مكشوف للجميع — أي لاعب يستطيع مهاجمتك.', icon: 'lucide:shield-off', color: 'text-red-400' },
      { label: 'حماية جزئية', text: 'خسائرك عند التعرض لهجوم ناجح تنخفض 50٪.', icon: 'lucide:shield-half', color: 'text-amber-400' },
      { label: 'حماية كاملة', text: 'لا يمكن مهاجمتك نهائياً حتى نهاية الدورة.', icon: 'lucide:shield-check', color: 'text-brand-success' },
      { label: 'الإفلاس', text: 'إذا وصل رصيدك صفر، تُعلن مفلساً وتُكشف هويتك للجميع. لا يمكنك الهجوم أو استخدام العناصر حتى يعاد ضبط الدورة.', icon: 'lucide:skull', color: 'text-red-500' },
    ],
  },
  {
    id: 'items',
    icon: 'mdi:magic-staff',
    iconColor: 'text-purple-400',
    glowColor: 'from-purple-500/20',
    title: 'المتجر والعناصر',
    subtitle: 'تسلّح قبل المعركة',
    content: [
      { text: 'اشترِ أسلحة تزيد مكافأتك، ودروعاً تقلل خسائرك، وعناصر خاصة بمزايا فريدة.' },
      { text: 'العناصر لها ندرة مختلفة: عادي — نادر — ملحمي — أسطوري — فريد.' },
      { text: 'بعض العناصر محدودة الكمية — اشترِ قبل نفادها!' },
      { text: 'فعّل العناصر قبل الهجوم من المخزن. التأثيرات النشطة تظهر تلقائياً في شاشة الهجوم.' },
      { text: 'بعض العناصر تعمل فوراً عند التفعيل، وبعضها ينتظر حدثاً (نجاح الهجوم أو الدفاع) لتطبيق تأثيرها.' },
    ],
  },
  {
    id: 'quiz',
    icon: 'lucide:brain',
    iconColor: 'text-brand-teal',
    glowColor: 'from-brand-teal/20',
    title: 'الأسئلة والمسابقات',
    subtitle: 'طريقك الآخر للنقاط',
    content: [
      { text: 'يفتح المشرف جلسات أسئلة محددة بوقت — تظهر إشعارات عند بدئها.' },
      { text: 'كل سؤال له مدة محددة (عادة 30 ثانية). أجب بسرعة ودقة!' },
      { text: 'كل إجابة صحيحة تضيف نقاطاً مباشرة لرصيدك.' },
      { text: 'المسابقات مصدر مهم للنقاط، خاصة لمن يفضّل الحذر على المواجهة المباشرة.' },
    ],
  },
  {
    id: 'seasons',
    icon: 'lucide:calendar-range',
    iconColor: 'text-amber-400',
    glowColor: 'from-amber-500/20',
    title: 'المواسم والدورات',
    subtitle: 'هيكل الوقت في حرب الأسماء',
    content: [
      { label: 'المنافسة', text: 'الإطار الكبير الذي يضم المواسم والدورات واللاعبين.' },
      { label: 'الموسم', text: 'مرحلة كاملة من اللعب. الفائز هو من يتصدّر نهاية الموسم.' },
      { label: 'الدورة', text: 'فترة زمنية ضمن الموسم (مثل أسبوع). عند نهاية الدورة تُعاد الحمايات وتُرفع حالات الإفلاس — لكن الرصيد والكنية يبقيان.' },
      { text: 'كل دورة فرصة جديدة — حتى لو أفلست، ستعود في الدورة التالية.' },
    ],
  },
  {
    id: 'fairness',
    icon: 'lucide:scale',
    iconColor: 'text-brand-slate',
    glowColor: 'from-brand-slate/20',
    title: 'قواعد النزاهة',
    subtitle: 'لعبة عادلة للجميع',
    content: [
      { text: 'لا يمكنك مهاجمة نفسك.' },
      { text: 'لا يمكنك مهاجمة لاعب مفلس.' },
      { text: 'لا يمكنك مهاجمة لاعب بحماية كاملة.' },
      { text: 'المشرف يستطيع تعطيل الهجمات مؤقتاً (وقت السلم) إذا تطلب الأمر.' },
      { text: 'جميع العمليات المالية مسجّلة في دفتر حسابات لا يمكن تعديله.' },
      { text: 'المشرف يملك سجل تدقيق كامل لكل حدث في اللعبة.' },
    ],
  },
]

function RuleItem({ item }) {
  return (
    <div className="flex items-start gap-3 group">
      <div className={`w-8 h-8 rounded-lg bg-gray-100 dark:bg-white/5 flex items-center justify-center flex-shrink-0 mt-0.5 group-hover:bg-gray-200 dark:group-hover:bg-white/10 smooth-transition ${item.color || ''}`}>
        <iconify-icon
          icon={item.icon || 'lucide:check'}
          class={`text-base ${item.color || 'text-brand-teal'}`}
        ></iconify-icon>
      </div>
      <div className="flex-1 min-w-0">
        {item.label && (
          <span className="font-heading font-black text-sm text-gray-900 dark:text-white block mb-0.5">{item.label}</span>
        )}
        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed font-medium">{item.text}</p>
      </div>
    </div>
  )
}

function RuleSection({ section, index }) {
  return (
    <section id={section.id} className="relative">
      {/* Section card */}
      <div className="relative bg-white dark:bg-white/[0.03] border border-gray-200 dark:border-white/[0.06] rounded-3xl p-6 md:p-10 overflow-hidden group hover:bg-gray-50 dark:hover:bg-white/[0.05] shadow-sm dark:shadow-none smooth-transition">
        {/* Glow */}
        <div className={`absolute -top-20 -right-20 w-64 h-64 bg-gradient-to-br ${section.glowColor} to-transparent rounded-full blur-3xl opacity-30 group-hover:opacity-50 smooth-transition`}></div>

        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-center gap-4 mb-2">
            <div className="w-12 h-12 bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl flex items-center justify-center">
              <iconify-icon icon={section.icon} class={`text-2xl ${section.iconColor}`}></iconify-icon>
            </div>
            <div>
              <span className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-[0.2em] block">
                {String(index + 1).padStart(2, '0')}
              </span>
              <h2 className="font-display font-black text-2xl md:text-3xl text-gray-900 dark:text-white leading-tight">
                {section.title}
              </h2>
            </div>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 font-bold mb-8 mr-16">{section.subtitle}</p>

          {/* Items */}
          <div className="space-y-4">
            {section.content.map((item, j) => (
              <RuleItem key={j} item={item} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default function RulesPage() {
  return (
    <div
      className="flex-1 w-full relative overflow-hidden bg-brand-light-bg dark:bg-[#0a0d14]"
    >
      {/* Dark-mode gradient overlay */}
      <div className="hidden dark:block absolute inset-0 pointer-events-none" style={{ background: 'linear-gradient(180deg, #0a0d14 0%, #111827 50%, #0a0d14 100%)' }}></div>

      {/* Hex background pattern */}
      <div
        className="absolute inset-0 opacity-40 dark:opacity-40 pointer-events-none hidden dark:block"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='103.92304845413264' viewBox='0 0 60 103.92304845413264' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.02'%3E%3Cpolygon points='30 103.92304845413264 0 86.60254037844386 0 51.96152422706632 30 34.64101615137754 60 51.96152422706632 60 86.60254037844386'/%3E%3Cpolygon points='30 51.96152422706632 0 34.64101615137754 0 0 30 -17.32050807568877 60 0 60 34.64101615137754'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          backgroundSize: '100px 173.2px',
        }}
      ></div>

      {/* Floating shapes (dark mode only) */}
      <div className="hidden dark:block absolute top-40 left-10 w-72 h-72 bg-brand-teal/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="hidden dark:block absolute bottom-60 right-10 w-80 h-80 bg-brand-orange/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="hidden dark:block absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-500/3 rounded-full blur-[150px] pointer-events-none"></div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 py-10 md:py-16 space-y-10">

        {/* ── Hero ── */}
        <header className="text-center space-y-6 mb-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-black text-gray-500 dark:text-gray-400 uppercase tracking-[0.15em]">
            <iconify-icon icon="lucide:book-open" class="text-brand-teal text-sm"></iconify-icon>
            دليل اللاعب
          </div>
          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-black text-gray-900 dark:text-white leading-[1.1] tracking-tight">
            قواعد
            <span className="block bg-gradient-to-l from-brand-teal via-brand-teal-light to-brand-teal bg-clip-text text-transparent">
              حرب الأسماء
            </span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400 font-medium text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
            كل ما تحتاج معرفته لتبدأ اللعب، تخطّط لهجماتك، وتتصدّر الموسم.
          </p>
        </header>

        {/* ── Quick Nav ── */}
        <nav className="flex flex-wrap justify-center gap-2 pb-4">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/[0.08] text-xs font-bold text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-white/10 hover:border-gray-300 dark:hover:border-white/20 smooth-transition"
            >
              <iconify-icon icon={s.icon} class={`text-sm ${s.iconColor}`}></iconify-icon>
              {s.title}
            </a>
          ))}
        </nav>

        {/* ── Sections ── */}
        <div className="space-y-6">
          {SECTIONS.map((section, i) => (
            <RuleSection key={section.id} section={section} index={i} />
          ))}
        </div>

        {/* ── CTA ── */}
        <div className="text-center space-y-6 pt-8 pb-4">
          <div className="w-16 h-px bg-gradient-to-l from-transparent via-gray-300 dark:via-gray-600 to-transparent mx-auto"></div>
          <p className="text-gray-600 dark:text-gray-400 font-bold text-lg">جاهز للمعركة؟</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/leaderboard"
              className="btn-press px-8 py-4 bg-brand-orange hover:bg-brand-orange/90 text-white font-heading font-black text-lg rounded-2xl shadow-lg shadow-brand-orange/20 flex items-center gap-3 smooth-transition hover:-translate-y-1"
            >
              <iconify-icon icon="lucide:swords" class="text-2xl"></iconify-icon>
              ابدأ الهجوم
            </Link>
            <Link
              to="/store"
              className="px-8 py-4 bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-gray-300 font-heading font-bold text-lg rounded-2xl hover:bg-gray-200 dark:hover:bg-white/10 hover:text-gray-900 dark:hover:text-white flex items-center gap-3 smooth-transition hover:-translate-y-1"
            >
              <iconify-icon icon="lucide:shopping-bag" class="text-2xl"></iconify-icon>
              تسوّق أدوات القتال
            </Link>
          </div>
        </div>

      </div>
    </div>
  )
}
