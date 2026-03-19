export default function RulesPage() {
  const rules = [
    {
      icon: 'lucide:user-check',
      title: 'الانضمام والهوية',
      items: [
        'كل متسابق ينضم برمز دعوة ويختار اسمًا مستعارًا (كنية)',
        'هويتك الحقيقية سرية — لا يعرفها إلا المشرف',
        'اكتشاف هوية لاعب آخر = مكافأة نقاط!',
      ],
    },
    {
      icon: 'lucide:swords',
      title: 'نظام الهجوم',
      items: [
        'اختر هدفًا وخمّن هويته الحقيقية من قائمة الأسماء',
        'هجوم ناجح → تحصل مكافأة ويخسر الهدف نقاطًا',
        'هجوم فاشل → تخسر نقاطًا أنت',
        'بعد 3 هجمات ناجحة على نفس اللاعب يحصل على حماية كاملة',
      ],
    },
    {
      icon: 'lucide:trending-down',
      title: 'انحلال المكافأة',
      items: [
        'المكافأة تنخفض مع كل هجوم ناجح على نفس الهدف',
        'أول هجوم يعطي المكافأة الكاملة، والتالي أقل',
        'هذا يشجع على تنويع الأهداف',
      ],
    },
    {
      icon: 'lucide:shield',
      title: 'الحماية والإفلاس',
      items: [
        'لا حماية = مكشوف للهجمات',
        'حماية جزئية = دفاعات محدودة',
        'حماية كاملة = لا يمكن مهاجمتك',
        'إذا وصل رصيدك صفر = إفلاس وتُكشف هويتك للجميع',
      ],
    },
    {
      icon: 'lucide:shopping-bag',
      title: 'المتجر والعناصر',
      items: [
        'اشترِ أسلحة ودروعًا وعناصر خاصة بالنقاط',
        'العناصر لها ندرة مختلفة: عادي، نادر، ملحمي، أسطوري، خرافي',
        'بعض العناصر محدودة العدد — اشترِ قبل نفادها!',
      ],
    },
    {
      icon: 'lucide:book-open',
      title: 'الأسئلة والمسابقات',
      items: [
        'جلسات أسئلة محددة بوقت — أجب بسرعة!',
        'كل إجابة صحيحة تمنحك نقاطًا',
        'مدة الإجابة عادة 30 ثانية',
      ],
    },
  ]

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto px-4 py-8 md:py-14 space-y-6">

      <div>
        <h1 className="font-display text-3xl font-black text-gray-900 dark:text-white">قواعد اللعبة</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">كل ما تحتاج معرفته عن حرب الأسماء</p>
      </div>

      <div className="space-y-4">
        {rules.map((section, i) => (
          <div key={i} className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6">
            <h2 className="font-heading font-black text-lg text-gray-900 dark:text-white mb-4 flex items-center gap-3">
              <div className="w-10 h-10 bg-brand-teal/10 dark:bg-brand-slate/20 rounded-xl flex items-center justify-center">
                <iconify-icon icon={section.icon} class="text-xl text-brand-teal dark:text-brand-slate"></iconify-icon>
              </div>
              {section.title}
            </h2>
            <ul className="space-y-2 mr-2">
              {section.items.map((item, j) => (
                <li key={j} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <iconify-icon icon="lucide:check" class="text-brand-success mt-0.5 flex-shrink-0"></iconify-icon>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
