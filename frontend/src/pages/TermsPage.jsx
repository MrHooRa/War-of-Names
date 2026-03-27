import { Link } from 'react-router-dom'

const LAST_UPDATED = '2026-03-27'

const SECTIONS = [
  {
    id: 'intro',
    title: 'مقدمة',
    content: (
      <>
        <p>
          مرحباً بك في منصة <strong>حرب الأسماء</strong> (يُشار إليها لاحقاً بـ"المنصة" أو "الخدمة").
          تُشغَّل هذه المنصة وتُدار بالكامل من المملكة العربية السعودية، وتخضع للأنظمة واللوائح المعمول
          بها في المملكة.
        </p>
        <p>
          باستخدامك للمنصة أو بإنشاء حساب فيها فإنك تُقرّ بأنك قرأت هذه الشروط والأحكام وفهمتها
          وتوافق على الالتزام بها. إذا كنت لا توافق على أي من هذه الشروط، يُرجى عدم استخدام المنصة.
        </p>
        <p>
          نحتفظ بحق تعديل هذه الشروط في أي وقت. سيُعلَن عن التعديلات الجوهرية عبر إشعار داخل
          المنصة أو عبر البريد الإلكتروني المسجّل. استمرارك في استخدام المنصة بعد نشر التعديلات يُعدّ
          قبولاً لها.
        </p>
      </>
    ),
  },
  {
    id: 'definitions',
    title: 'التعريفات',
    content: (
      <ul className="list-disc list-inside space-y-2">
        <li><strong>"المنصة"</strong> أو <strong>"الخدمة"</strong>: تطبيق حرب الأسماء الإلكتروني وجميع الصفحات والوظائف المرتبطة به.</li>
        <li><strong>"المستخدم"</strong> أو <strong>"المتسابق"</strong>: أي شخص يُنشئ حساباً أو يستخدم المنصة بأي شكل.</li>
        <li><strong>"المشرف"</strong>: الشخص أو الأشخاص المخوّلون بإدارة المنافسات والتحكم في إعدادات المنصة.</li>
        <li><strong>"المنافسة"</strong>: إطار اللعب الرئيسي الذي ينضم إليه المتسابقون عبر رمز دعوة.</li>
        <li><strong>"الكنية"</strong> (الاسم المستعار): الهوية المؤقتة التي يختارها المتسابق داخل المنافسة.</li>
        <li><strong>"النقاط"</strong>: العملة الداخلية للمنصة المستخدمة في التصنيف والشراء والهجوم.</li>
        <li><strong>"المتجر"</strong>: القسم الذي يتيح شراء عناصر افتراضية باستخدام النقاط.</li>
        <li><strong>"الهجوم"</strong>: محاولة تخمين الهوية الحقيقية للاعب آخر بناءً على كنيته.</li>
      </ul>
    ),
  },
  {
    id: 'eligibility',
    title: 'أهلية الاستخدام وشروط الحساب',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>يجب ألا يقل عمر المستخدم عن 13 عاماً لإنشاء حساب. إذا كان عمرك أقل من 18 عاماً، فإنك تُقرّ بأنك حصلت على إذن ولي أمرك.</li>
          <li>يلتزم المستخدم بتقديم معلومات صحيحة ودقيقة عند التسجيل، وتحديثها عند الحاجة.</li>
          <li>كل مستخدم مسؤول عن الحفاظ على سرية بيانات تسجيل الدخول الخاصة به. أي نشاط يحدث تحت حسابك يُعدّ مسؤوليتك.</li>
          <li>يُحظر إنشاء أكثر من حساب واحد لنفس الشخص في نفس المنافسة.</li>
          <li>يُحظر مشاركة الحساب أو نقله إلى شخص آخر.</li>
          <li>تحتفظ المنصة بحق تعليق أو إنهاء أي حساب يُخالف هذه الشروط دون إشعار مسبق.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'fair-play',
    title: 'سياسة اللعب النظيف',
    content: (
      <>
        <p>تلتزم منصة حرب الأسماء بتوفير بيئة عادلة وممتعة لجميع المتسابقين. ولتحقيق ذلك يُحظر ما يلي:</p>
        <ul className="list-disc list-inside space-y-2 mt-3">
          <li><strong>التواطؤ:</strong> التنسيق مع لاعبين آخرين للتلاعب بنتائج الهجمات أو تبادل المعلومات المحظورة (كالكشف عن الهويات الحقيقية).</li>
          <li><strong>الاستغلال التقني:</strong> استخدام أدوات آلية (بوتات) أو أي برمجيات خارجية للتفاعل مع المنصة أو استخراج بياناتها.</li>
          <li><strong>التحايل على الأنظمة:</strong> استغلال ثغرات أو أخطاء برمجية للحصول على ميزة غير مشروعة. يجب الإبلاغ عن أي ثغرة يتم اكتشافها فوراً.</li>
          <li><strong>انتحال الهوية:</strong> التظاهر بأنك شخص آخر (حقيقي أو وهمي) بشكل مضلّل خارج سياق آلية الكنيات.</li>
          <li><strong>التحرش أو الإساءة:</strong> أي سلوك يتضمن تهديداً أو تنمّراً أو مضايقة لأي مستخدم آخر عبر المنصة أو خارجها بسبب أحداث داخل اللعبة.</li>
          <li><strong>التلاعب بالحسابات:</strong> إنشاء حسابات وهمية (smurf accounts) أو استخدام حسابات متعددة لتحقيق أي ميزة.</li>
        </ul>
        <p className="mt-3">
          تحتفظ الإدارة بحق التحقيق في أي مخالفة مشتبه بها، واتخاذ الإجراءات المناسبة التي قد تشمل:
          الإنذار، خصم النقاط، التعليق المؤقت، أو الحظر الدائم من المنافسة أو المنصة.
        </p>
      </>
    ),
  },
  {
    id: 'content-rules',
    title: 'قواعد المحتوى',
    content: (
      <>
        <p>يلتزم المستخدم بأن يكون المحتوى الذي يُدخله (بما في ذلك الكنيات والرسائل) متوافقاً مع الآتي:</p>
        <ul className="list-disc list-inside space-y-2 mt-3">
          <li>عدم احتواء المحتوى على ألفاظ بذيئة أو مسيئة أو عنصرية أو طائفية.</li>
          <li>عدم الإساءة للدين الإسلامي أو أي دين آخر، أو الرموز الوطنية، أو القيادة السعودية.</li>
          <li>عدم نشر معلومات شخصية لأي مستخدم آخر دون إذنه الصريح.</li>
          <li>عدم نشر محتوى إباحي أو جنسي أو يتضمن عنفاً مفرطاً.</li>
          <li>عدم نشر روابط ضارة أو برمجيات خبيثة أو محتوى احتيالي.</li>
          <li>الالتزام بأنظمة مكافحة الجرائم المعلوماتية في المملكة العربية السعودية.</li>
        </ul>
        <p className="mt-3">
          تحتفظ الإدارة بحق حذف أي محتوى مخالف دون إشعار مسبق، وقد يُعرّض المخالف حسابه للتعليق أو الإنهاء.
        </p>
      </>
    ),
  },
  {
    id: 'virtual-items',
    title: 'العناصر الافتراضية والنقاط',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>النقاط والعناصر الافتراضية في المنصة ليست عملة حقيقية ولا تحمل قيمة نقدية خارج المنصة.</li>
          <li>لا يمكن استبدال النقاط أو العناصر بمال حقيقي أو تحويلها أو بيعها أو نقلها خارج المنصة.</li>
          <li>تحتفظ الإدارة بحق تعديل أسعار العناصر أو خصائصها أو إزالتها في أي وقت لتحقيق التوازن في اللعبة.</li>
          <li>لا يُعدّ أي رصيد نقاط أو عنصر افتراضي حقاً مكتسباً لا يمكن تعديله.</li>
          <li>عند انتهاء الموسم أو إعادة ضبط الدورة، قد تتغير الأرصدة وفق قواعد اللعبة المُعلنة.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'ip',
    title: 'الملكية الفكرية',
    content: (
      <>
        <p>
          جميع حقوق الملكية الفكرية المتعلقة بالمنصة — بما في ذلك التصميم، والشعار، والأيقونات،
          والنصوص البرمجية، وآليات اللعب، والمحتوى الأصلي — هي ملك حصري لمنصة حرب الأسماء
          ومحمية بموجب أنظمة حماية الملكية الفكرية في المملكة العربية السعودية والاتفاقيات الدولية ذات الصلة.
        </p>
        <ul className="list-disc list-inside space-y-2 mt-3">
          <li>يُحظر نسخ أو إعادة إنتاج أو توزيع أي جزء من المنصة دون إذن كتابي مسبق.</li>
          <li>يُحظر استخدام العلامة التجارية "حرب الأسماء" أو شعارها لأي غرض تجاري دون ترخيص.</li>
          <li>يحتفظ المستخدم بملكية المحتوى الذي يُنشئه (مثل الكنيات)، لكنه يمنح المنصة ترخيصاً غير حصري لاستخدامه ضمن نطاق تشغيل الخدمة.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'liability',
    title: 'حدود المسؤولية',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>تُقدَّم المنصة "كما هي" (as is) دون أي ضمانات صريحة أو ضمنية بشأن الاستمرارية أو الخلو من الأخطاء.</li>
          <li>لا تتحمل المنصة المسؤولية عن أي أضرار مباشرة أو غير مباشرة ناتجة عن استخدام الخدمة أو عدم القدرة على استخدامها.</li>
          <li>لا تتحمل المنصة المسؤولية عن أي خلافات تنشأ بين المستخدمين داخل المنافسة أو خارجها.</li>
          <li>لا تتحمل المنصة المسؤولية عن فقدان البيانات الناتج عن أعطال تقنية أو قوة قاهرة.</li>
          <li>المستخدم يتحمل المسؤولية الكاملة عن أي نشاط يتم عبر حسابه.</li>
          <li>في جميع الأحوال، تكون مسؤولية المنصة القصوى محدودة بما يسمح به النظام السعودي.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'termination',
    title: 'إنهاء الحساب',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>يحق للمستخدم حذف حسابه في أي وقت من خلال إعدادات الحساب أو بالتواصل مع الإدارة.</li>
          <li>تحتفظ المنصة بحق تعليق أو إنهاء حساب أي مستخدم — مع أو بدون إشعار مسبق — في حالة مخالفة هذه الشروط أو الأنظمة المعمول بها.</li>
          <li>عند إنهاء الحساب، يفقد المستخدم حق الوصول إلى جميع بياناته ونقاطه وعناصره داخل المنصة.</li>
          <li>قد تحتفظ المنصة ببعض البيانات بعد حذف الحساب وفقاً لمتطلبات النظام أو لأغراض أمنية مشروعة، وذلك بما يتوافق مع نظام حماية البيانات الشخصية.</li>
          <li>إنهاء الحساب لا يُعفي المستخدم من أي التزامات أو مسؤوليات نشأت قبل الإنهاء.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'governing-law',
    title: 'القانون الحاكم وتسوية النزاعات',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>تخضع هذه الشروط وتُفسَّر وفقاً لأنظمة ولوائح المملكة العربية السعودية.</li>
          <li>
            تشمل الأنظمة المعمول بها — على سبيل المثال لا الحصر — نظام التعاملات الإلكترونية، ونظام
            مكافحة الجرائم المعلوماتية، ونظام حماية البيانات الشخصية (PDPL)، ونظام التجارة الإلكترونية.
          </li>
          <li>في حالة نشوء أي نزاع، يسعى الطرفان أولاً إلى حله ودياً عبر التواصل المباشر خلال مدة لا تتجاوز ثلاثين (30) يوماً.</li>
          <li>إذا تعذّر الحل الودي، يُحال النزاع إلى الجهات القضائية المختصة في المملكة العربية السعودية.</li>
          <li>تكون المحاكم السعودية المختصة هي صاحبة الولاية الحصرية للنظر في أي نزاع ينشأ عن هذه الشروط أو يتعلق بها.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'contact',
    title: 'التواصل معنا',
    content: (
      <>
        <p>لأي استفسارات أو ملاحظات بخصوص شروط الاستخدام، يمكنك التواصل معنا عبر:</p>
        <ul className="list-disc list-inside space-y-2 mt-3">
          <li>البريد الإلكتروني: <span className="text-brand-teal dark:text-brand-slate font-bold" dir="ltr">support@warofnames.com</span></li>
        </ul>
        <p className="mt-3">سنبذل قصارى جهدنا للرد على استفساراتك في أقرب وقت ممكن.</p>
      </>
    ),
  },
]

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-brand-light-bg dark:bg-brand-dark-bg bg-pattern-main font-body transition-colors duration-300">

      {/* Header */}
      <header className="w-full pt-12 pb-6 flex justify-center">
        <Link to="/" className="block smooth-transition hover:opacity-80 hover:scale-105 transform">
          <img
            src="/main-logo-v1.png"
            alt="حرب الأسماء"
            className="w-[140px] md:w-[180px] object-contain drop-shadow-sm"
          />
        </Link>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 pb-20">

        {/* Page Title */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-teal/10 dark:bg-brand-slate/10 text-xs font-black text-brand-teal dark:text-brand-slate uppercase tracking-widest mb-4">
            <iconify-icon icon="lucide:file-text" class="text-sm"></iconify-icon>
            وثيقة قانونية
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-black text-gray-900 dark:text-white mb-3">
            شروط الاستخدام
          </h1>
          <p className="text-gray-500 dark:text-gray-400 font-medium">
            آخر تحديث: {new Date(LAST_UPDATED).toLocaleDateString('ar-SA', { year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>

        {/* Quick Nav */}
        <nav className="flex flex-wrap justify-center gap-2 mb-10">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="px-3 py-1.5 rounded-lg bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 text-xs font-bold text-gray-600 dark:text-gray-400 hover:text-brand-teal dark:hover:text-brand-slate hover:border-brand-teal/30 dark:hover:border-brand-slate/30 smooth-transition"
            >
              {s.title}
            </a>
          ))}
        </nav>

        {/* Sections */}
        <div className="space-y-6">
          {SECTIONS.map((section, i) => (
            <section
              key={section.id}
              id={section.id}
              className="bg-white dark:bg-brand-card-dark border border-gray-200 dark:border-gray-700 rounded-2xl p-6 md:p-8 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-4">
                <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-teal/10 dark:bg-brand-slate/10 text-brand-teal dark:text-brand-slate text-xs font-black">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h2 className="font-display font-black text-xl md:text-2xl text-gray-900 dark:text-white">
                  {section.title}
                </h2>
              </div>
              <div className="text-gray-700 dark:text-gray-300 leading-relaxed text-[15px] space-y-3 font-medium">
                {section.content}
              </div>
            </section>
          ))}
        </div>

        {/* Footer links */}
        <div className="mt-10 text-center space-y-4">
          <div className="flex items-center justify-center gap-4 text-sm font-bold">
            <Link to="/privacy" className="text-brand-teal dark:text-brand-slate hover:underline">
              سياسة الخصوصية
            </Link>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <Link to="/rules" className="text-brand-teal dark:text-brand-slate hover:underline">
              قواعد اللعبة
            </Link>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <Link to="/" className="text-brand-teal dark:text-brand-slate hover:underline">
              الرئيسية
            </Link>
          </div>
          <p className="text-xs font-bold text-gray-400 dark:text-gray-600 uppercase tracking-widest">
            جميع الحقوق محفوظة &copy; 2026 حرب الأسماء
          </p>
        </div>

      </main>
    </div>
  )
}
