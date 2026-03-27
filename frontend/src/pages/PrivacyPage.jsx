import { Link } from 'react-router-dom'

const LAST_UPDATED = '2026-03-27'

const SECTIONS = [
  {
    id: 'intro',
    title: 'مقدمة',
    content: (
      <>
        <p>
          تلتزم منصة <strong>حرب الأسماء</strong> بحماية خصوصية مستخدميها وفقاً لنظام حماية البيانات
          الشخصية في المملكة العربية السعودية (PDPL — نظام حماية البيانات الشخصية الصادر بالمرسوم
          الملكي رقم م/19 وتاريخ 1443/02/09هـ) ولائحته التنفيذية.
        </p>
        <p>
          توضّح هذه السياسة كيفية جمع بياناتك الشخصية واستخدامها وتخزينها وحمايتها ومشاركتها
          عند استخدامك لمنصة حرب الأسماء. باستخدامك للمنصة أو بإنشاء حساب فيها فإنك توافق على
          ممارسات الخصوصية الموضّحة في هذه السياسة.
        </p>
        <p>
          نحتفظ بحق تحديث هذه السياسة بما يتوافق مع التطورات التنظيمية والتقنية. سيُعلَن عن
          أي تعديلات جوهرية عبر إشعار داخل المنصة.
        </p>
      </>
    ),
  },
  {
    id: 'data-collected',
    title: 'البيانات التي نجمعها',
    content: (
      <>
        <p className="mb-3">نجمع الأنواع التالية من البيانات:</p>

        <h3 className="font-heading font-bold text-gray-900 dark:text-white text-base mb-2">1. البيانات المُقدَّمة مباشرة من المستخدم</h3>
        <ul className="list-disc list-inside space-y-1.5 mb-4">
          <li>الاسم الحقيقي (الاسم الأول واسم العائلة) عند التسجيل.</li>
          <li>البريد الإلكتروني.</li>
          <li>كلمة المرور (تُخزَّن مُشفّرة ولا يمكن لأي شخص — بما في ذلك الإدارة — الاطلاع عليها بشكل نصي).</li>
          <li>الكنية (الاسم المستعار) المختارة داخل المنافسة.</li>
          <li>أي معلومات إضافية يختار المستخدم تقديمها طوعاً.</li>
        </ul>

        <h3 className="font-heading font-bold text-gray-900 dark:text-white text-base mb-2">2. البيانات المُجمَّعة تلقائياً</h3>
        <ul className="list-disc list-inside space-y-1.5 mb-4">
          <li>عنوان بروتوكول الإنترنت (IP Address).</li>
          <li>نوع المتصفح وإصداره ونظام التشغيل.</li>
          <li>معرّف الجهاز ومعلومات الجلسة.</li>
          <li>سجل النشاط داخل المنصة (الصفحات المزارة، أوقات الدخول والخروج).</li>
          <li>بيانات الأداء والتفاعل مع عناصر الواجهة.</li>
        </ul>

        <h3 className="font-heading font-bold text-gray-900 dark:text-white text-base mb-2">3. بيانات اللعب</h3>
        <ul className="list-disc list-inside space-y-1.5">
          <li>سجل الهجمات والدفاعات ونتائجها.</li>
          <li>رصيد النقاط وتاريخ المعاملات المالية الداخلية.</li>
          <li>العناصر المُشتراة والمُستخدَمة.</li>
          <li>نتائج جلسات الأسئلة.</li>
          <li>التصنيف والمركز في المنافسة.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'purpose',
    title: 'أغراض استخدام البيانات',
    content: (
      <>
        <p className="mb-3">نستخدم بياناتك الشخصية للأغراض التالية فقط:</p>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>تشغيل المنصة:</strong> إنشاء الحساب، المصادقة، إدارة الجلسات، وتشغيل آليات اللعب (الهجوم، المتجر، المسابقات).</li>
          <li><strong>أمن المنصة:</strong> كشف ومنع الاحتيال والتلاعب والوصول غير المصرّح به، وحماية حسابات المستخدمين.</li>
          <li><strong>تحسين الخدمة:</strong> تحليل أنماط الاستخدام لتحسين أداء المنصة وتجربة المستخدم.</li>
          <li><strong>التواصل:</strong> إرسال إشعارات متعلقة بالحساب والمنافسة والتحديثات الأمنية.</li>
          <li><strong>الامتثال القانوني:</strong> الوفاء بالالتزامات النظامية وفقاً لأنظمة المملكة العربية السعودية.</li>
          <li><strong>النزاهة:</strong> ضمان تطبيق قواعد اللعب النظيف ومنع الغش.</li>
        </ul>
        <p className="mt-3">
          لن نستخدم بياناتك لأي غرض آخر غير المذكور أعلاه دون الحصول على موافقتك المسبقة، وذلك
          وفقاً للمادة (5) من نظام حماية البيانات الشخصية.
        </p>
      </>
    ),
  },
  {
    id: 'storage',
    title: 'تخزين البيانات وحمايتها',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>تُخزَّن جميع البيانات الشخصية على خوادم آمنة تعمل بتقنيات تشفير حديثة (TLS/SSL للنقل، وتشفير كلمات المرور باستخدام خوارزميات bcrypt).</li>
          <li>يتم تطبيق ضوابط وصول صارمة تقصر الاطلاع على البيانات الشخصية على الأشخاص المخوّلين فقط وبالقدر الضروري لأداء مهامهم.</li>
          <li>نحرص على تخزين البيانات ومعالجتها داخل المملكة العربية السعودية. في حالة الحاجة إلى نقل البيانات خارج المملكة، سيتم ذلك وفقاً للمادة (29) من نظام حماية البيانات الشخصية وبعد الحصول على الموافقات اللازمة.</li>
          <li>نُجري مراجعات أمنية دورية لضمان سلامة البيانات واكتشاف أي ثغرات محتملة.</li>
          <li>في حالة حدوث أي اختراق أمني يؤثر على بياناتك الشخصية، سنُبلغ الجهات المختصة والمستخدمين المتضررين وفقاً للإجراءات المنصوص عليها في النظام.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'sharing',
    title: 'مشاركة البيانات مع أطراف ثالثة',
    content: (
      <>
        <p className="mb-3">لا نبيع بياناتك الشخصية ولا نؤجّرها لأي طرف ثالث. قد نشارك بيانات محدودة في الحالات التالية فقط:</p>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>مقدمو الخدمات التقنية:</strong> شركات الاستضافة وخدمات البنية التحتية السحابية اللازمة لتشغيل المنصة، وذلك بموجب اتفاقيات معالجة بيانات تضمن مستوى حماية مكافئ.</li>
          <li><strong>الالتزام القانوني:</strong> عند صدور أمر قضائي أو طلب رسمي من جهة حكومية مختصة في المملكة العربية السعودية.</li>
          <li><strong>حماية الحقوق:</strong> عند الضرورة لحماية حقوق المنصة أو سلامة المستخدمين أو منع الاحتيال.</li>
          <li><strong>البيانات المجمّعة:</strong> قد نشارك بيانات إحصائية مجمّعة لا تكشف هوية الأفراد (مثل: إجمالي عدد المستخدمين، متوسط عدد الهجمات) لأغراض تحليلية.</li>
        </ul>
        <p className="mt-3">
          في جميع حالات المشاركة، نلتزم بمبدأ الحد الأدنى من البيانات (data minimization)
          ولا نشارك إلا ما هو ضروري فقط لتحقيق الغرض المحدد.
        </p>
      </>
    ),
  },
  {
    id: 'game-data',
    title: 'خصوصية بيانات اللعب',
    content: (
      <>
        <p className="mb-3">نظراً لطبيعة لعبة حرب الأسماء القائمة على إخفاء الهوية، نولي اهتماماً خاصاً بخصوصية بيانات اللعب:</p>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>الكنية والهوية:</strong> كنية اللاعب مرئية لجميع المتسابقين في المنافسة، لكن الربط بين الكنية والهوية الحقيقية محمي ولا يُكشف إلا وفق آليات اللعبة (الهجوم الناجح أو الإفلاس).</li>
          <li><strong>سجل المعارك:</strong> نتائج الهجمات مرئية للأطراف المعنية (المهاجم والمدافع) وللمشرف.</li>
          <li><strong>الرصيد والتصنيف:</strong> رصيد النقاط والمركز في لوحة المتصدرين مرئي لجميع المتسابقين عبر الكنية فقط.</li>
          <li><strong>المشرف:</strong> يملك المشرف صلاحية الاطلاع على جميع بيانات اللعب لأغراض الإدارة وضمان النزاهة.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'cookies',
    title: 'ملفات تعريف الارتباط (Cookies) والتقنيات المشابهة',
    content: (
      <>
        <p className="mb-3">نستخدم التقنيات التالية:</p>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>ملفات الجلسة (Session Cookies):</strong> ضرورية لتشغيل المنصة والحفاظ على تسجيل الدخول. تُحذف عند إغلاق المتصفح أو انتهاء الجلسة.</li>
          <li><strong>رموز المصادقة (Auth Tokens):</strong> تُخزَّن محلياً لتمكين الوصول المستمر دون الحاجة لإعادة تسجيل الدخول.</li>
          <li><strong>التخزين المحلي (Local Storage):</strong> لحفظ تفضيلات العرض مثل الوضع الداكن/الفاتح.</li>
        </ul>
        <p className="mt-3">
          لا نستخدم ملفات تتبّع إعلانية أو أدوات تحليل تابعة لأطراف ثالثة تتتبّع سلوكك عبر مواقع أخرى.
        </p>
      </>
    ),
  },
  {
    id: 'retention',
    title: 'الاحتفاظ بالبيانات',
    content: (
      <>
        <ul className="list-disc list-inside space-y-2">
          <li>نحتفظ ببياناتك الشخصية طوال فترة نشاط حسابك واستخدامك للمنصة.</li>
          <li>عند حذف الحساب، نحذف بياناتك الشخصية القابلة للتعريف خلال ثلاثين (30) يوماً، ما لم يكن هناك التزام نظامي بالاحتفاظ بها لفترة أطول.</li>
          <li>سجلات المعاملات والتدقيق قد تُحفظ لفترة لا تتجاوز سنة واحدة بعد حذف الحساب لأغراض أمنية وقانونية.</li>
          <li>البيانات المجمّعة غير القابلة للتعريف (مثل الإحصائيات العامة) قد تُحفظ لفترات أطول لأغراض تحليلية.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'user-rights',
    title: 'حقوقك بموجب نظام حماية البيانات الشخصية',
    content: (
      <>
        <p className="mb-3">يكفل لك نظام حماية البيانات الشخصية السعودي الحقوق التالية:</p>
        <ul className="list-disc list-inside space-y-2">
          <li><strong>حق الاطلاع:</strong> الحصول على نسخة من بياناتك الشخصية التي نحتفظ بها (المادة 4).</li>
          <li><strong>حق التصحيح:</strong> طلب تصحيح أي بيانات غير دقيقة أو غير مكتملة (المادة 4).</li>
          <li><strong>حق الحذف:</strong> طلب حذف بياناتك الشخصية عندما لم تعد ضرورية للغرض الذي جُمعت من أجله (المادة 4).</li>
          <li><strong>حق سحب الموافقة:</strong> سحب موافقتك على معالجة بياناتك في أي وقت، مع مراعاة أن ذلك قد يؤثر على قدرتك على استخدام المنصة (المادة 6).</li>
          <li><strong>حق الاعتراض:</strong> الاعتراض على معالجة بياناتك في حالات معينة.</li>
          <li><strong>حق نقل البيانات:</strong> طلب نقل بياناتك إلى جهة أخرى بصيغة مقروءة آلياً (المادة 4).</li>
        </ul>
        <p className="mt-3">
          لممارسة أي من هذه الحقوق، يُرجى التواصل معنا عبر البريد الإلكتروني المذكور أدناه.
          سنستجيب لطلبك خلال ثلاثين (30) يوماً من تاريخ استلامه.
        </p>
      </>
    ),
  },
  {
    id: 'children',
    title: 'خصوصية الأطفال',
    content: (
      <>
        <p>
          لا تستهدف المنصة الأطفال دون سن الثالثة عشرة (13). إذا كان عمر المستخدم بين 13 و18 عاماً،
          يجب الحصول على موافقة ولي الأمر قبل التسجيل، وذلك وفقاً للمادة (10) من نظام حماية
          البيانات الشخصية.
        </p>
        <p>
          إذا علمنا أن طفلاً دون 13 عاماً قد سجّل في المنصة دون موافقة ولي أمره، سنتخذ الإجراءات
          اللازمة لحذف حسابه وبياناته في أقرب وقت.
        </p>
      </>
    ),
  },
  {
    id: 'contact',
    title: 'التواصل معنا',
    content: (
      <>
        <p>إذا كانت لديك أي أسئلة أو استفسارات حول سياسة الخصوصية، أو ترغب في ممارسة أي من حقوقك، يمكنك التواصل معنا عبر:</p>
        <ul className="list-disc list-inside space-y-2 mt-3">
          <li>البريد الإلكتروني: <span className="text-brand-teal dark:text-brand-slate font-bold" dir="ltr">privacy@warofnames.com</span></li>
        </ul>
        <p className="mt-3">
          كما يحق لك التقدم بشكاوى إلى الهيئة السعودية للبيانات والذكاء الاصطناعي (سدايا) بصفتها
          الجهة المختصة بالإشراف على تطبيق نظام حماية البيانات الشخصية.
        </p>
      </>
    ),
  },
]

export default function PrivacyPage() {
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
            <iconify-icon icon="lucide:shield-check" class="text-sm"></iconify-icon>
            وثيقة قانونية
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-black text-gray-900 dark:text-white mb-3">
            سياسة الخصوصية
          </h1>
          <p className="text-gray-500 dark:text-gray-400 font-medium">
            آخر تحديث: {new Date(LAST_UPDATED).toLocaleDateString('ar-SA', { year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-2 font-medium">
            متوافقة مع نظام حماية البيانات الشخصية السعودي (PDPL)
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
            <Link to="/terms" className="text-brand-teal dark:text-brand-slate hover:underline">
              شروط الاستخدام
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
