/* Arabic interface. Translates the interface (navigation, headings, buttons, labels, filters, placeholders, tooltips, notices)
   — never what people wrote (posts, messages, names, product descriptions). English is restored exactly when switched back. */
(function () {
  var C = window.dxCore; if (!C) return;
  var D = {
    /* navigation & top bar */
    'Home': 'الرئيسية', 'Market': 'السوق', 'Marketplace': 'السوق', 'Network': 'الشبكة', 'My Network': 'شبكتي', 'Messages': 'الرسائل', 'Alerts': 'التنبيهات',
    'Notifications': 'الإشعارات', 'Jobs': 'الوظائف', 'Groups': 'المجموعات', 'Training': 'التدريب', 'Profile': 'الملف الشخصي', 'My profile': 'ملفي', 'My Profile': 'ملفي',
    'Saved': 'المحفوظات', 'Company Directory': 'دليل الشركات', 'Companies': 'الشركات', 'Sign Out': 'تسجيل الخروج', 'Sign out': 'تسجيل الخروج', 'Theme': 'المظهر',
    'Appearance': 'المظهر', 'Search': 'بحث', 'Search Drugbox': 'ابحث في Drugbox', 'Search Drugbox...': 'ابحث في Drugbox...', 'Search everything': 'ابحث في كل شيء',
    'Search everything (Ctrl+K)': 'ابحث في كل شيء (Ctrl+K)', 'Search people, listings, jobs, groups, posts or type a command…': 'ابحث عن أشخاص أو إعلانات أو وظائف أو مجموعات أو منشورات، أو اكتب أمرًا…',
    'Requests & deals': 'الطلبات والصفقات', 'Requests and deals': 'الطلبات والصفقات', 'Your shortcuts': 'اختصاراتك', 'Navigation': 'التنقل', 'Drugbox home': 'رئيسية Drugbox',
    'Privacy · Terms ·': 'الخصوصية · الشروط ·', '⚙️ Admin': '⚙️ الإدارة', 'Admin': 'مدير', 'Menu': 'القائمة', 'All pages': 'كل الصفحات', 'VIP company — paid plan': 'شركة VIP — خطة مدفوعة',
    'Scrollable list': 'قائمة قابلة للتمرير', 'Button': 'زر', 'Chat': 'محادثة', '● LIVE': '● مباشر', 'Live Now': 'مباشر الآن',
    /* splash & login */
    'Tap to skip': 'اضغط للتخطي', 'Skip →': 'تخطي ←', 'Continue': 'متابعة', 'B2B Pharma Professional Network': 'الشبكة المهنية لقطاع الدواء',
    'PHARMA PROFESSIONAL NETWORK': 'الشبكة المهنية للدواء', 'PHARMA / COSMETICS / MEDICAL DEVICES': 'دواء / مستحضرات تجميل / أجهزة طبية',
    'The professional network for pharma, cosmetics & medical devices.': 'الشبكة المهنية للدواء ومستحضرات التجميل والأجهزة الطبية.',
    'Raw materials — APIs, excipients, cosmetic actives': 'خامات — مواد فعالة وسواغات ومواد تجميل فعالة', 'Registrations — EDA, SFDA, DHA, MOHAP': 'تسجيلات — هيئة الدواء المصرية وSFDA وDHA وMOHAP',
    'Contract manufacturing — CMO / Toll': 'تصنيع لدى الغير — CMO / Toll', 'Jobs — QA, Regulatory, Medical Rep': 'وظائف — جودة وتسجيل ومندوب طبي', 'Training — GMP, Regulatory, Formulation': 'تدريب — GMP وتسجيل وتركيبات',
    'Join': 'انضم', 'pharma professionals — from new graduates to industry veterans': 'متخصص في الدواء — من حديثي التخرج حتى خبراء الصناعة', 'Professionals': 'متخصص', 'Countries': 'دولة',
    'Welcome back': 'أهلًا بعودتك', 'Sign in to your Drugbox account': 'سجّل الدخول إلى حسابك في Drugbox', 'Email': 'البريد الإلكتروني', 'Password': 'كلمة المرور',
    'Sign In →': 'تسجيل الدخول ←', "Don't have an account?": 'ليس لديك حساب؟', 'Create one': 'أنشئ حسابًا', 'DEMO ACCOUNT · tap to fill': 'حساب تجريبي · اضغط للملء',
    'Create Account →': 'إنشاء الحساب ←', 'Already have an account?': 'لديك حساب بالفعل؟', 'Sign in': 'تسجيل الدخول', 'Full name': 'الاسم الكامل', 'Company': 'الشركة', 'Role': 'الدور',
    'Dr. Your Name': 'د. اسمك', 'Min. 8 characters': '8 أحرف على الأقل', 'Your pharma company': 'شركتك', 'you@company.com': 'you@company.com',
    /* home */
    'FOR YOU': 'لك', 'Buyers looking for what you sell': 'مشترون يبحثون عمّا تبيعه', 'Open requests that match your products — answer first, win first.': 'طلبات مفتوحة تطابق منتجاتك — من يرد أولًا يكسب أولًا.',
    'Sell': 'أبيع', 'Buy': 'أشتري', 'Find a job': 'أبحث عن وظيفة', 'Hire': 'أوظّف', 'Regulatory': 'تسجيل', 'I am here to': 'أنا هنا لكي',
    'Post supply': 'انشر عرضًا', 'Boost a listing': 'روّج لإعلان', 'Scores use your profile, skills and My Intents.': 'تُحسب النسب من ملفك ومهاراتك وأهدافك.', 'Edit my intents': 'عدّل أهدافي',
    'Photo': 'صورة', 'File': 'ملف', 'Product': 'منتج', 'Job': 'وظيفة', '📌 Pinned': '📌 مثبّت', 'Like': 'إعجاب', 'Comment': 'تعليق', 'Repost': 'إعادة نشر', 'Send': 'إرسال', 'Share': 'مشاركة',
    'Add a comment…': 'اكتب تعليقًا…', 'general': 'عام', 'regulatory': 'تسجيل', 'market': 'سوق', 'innovation': 'ابتكار', 'job': 'وظيفة',
    'Profile viewers': 'من زار ملفك', 'Search appearances': 'مرات الظهور في البحث', '🔖 Saved items': '🔖 العناصر المحفوظة', 'Who viewed your profile': 'من شاهد ملفك', 'Upcoming Events': 'فعاليات قادمة',
    'Trending in Pharma': 'الأكثر تداولًا في الدواء', 'Connections': 'الاتصالات', 'Profile views': 'مشاهدات الملف', 'Post impressions': 'مرات ظهور المنشورات',
    /* marketplace */
    'MARKETPLACE': 'السوق', 'Trade with people you trust.': 'تاجر مع من تثق بهم.', 'From first-time exporters to 40-year industry veterans.': 'من المصدّرين الجدد حتى خبراء الصناعة منذ 40 عامًا.',
    'Browse Marketplace': 'تصفح السوق', 'Create Listing': 'أنشئ إعلانًا', 'My Listings': 'إعلاناتي', 'My Intents': 'أهدافي', 'Boost': 'ترويج', 'Featured': 'مميّز',
    'Supply': 'عرض', 'Demand': 'طلب', 'Licenses': 'تراخيص', 'CMO/Toll': 'تصنيع لدى الغير', 'Equipment': 'معدات', 'Services': 'خدمات', 'Category': 'الفئة', 'None': 'لا شيء',
    '🟢 Supply': '🟢 عرض', '🟠 Demand': '🟠 طلب', '🏭 CMO': '🏭 تصنيع لدى الغير', '⚙️ Equipment': '⚙️ معدات', '📋 License': '📋 ترخيص', '🛠️ Service': '🛠️ خدمة', '💼 Job': '💼 وظيفة', '🎓 Training': '🎓 تدريب',
    'Sort by': 'الترتيب حسب', 'Most Relevant': 'الأكثر صلة', '🔥 Most Viewed': '🔥 الأكثر مشاهدة', '🆕 Newest': '🆕 الأحدث', '💰 Price ↑': '💰 السعر ↑',
    'Sector': 'القطاع', '💄 Cosmetics': '💄 تجميل', '🥗 Supplements': '🥗 مكملات', '🏥 Medical Devices': '🏥 أجهزة طبية', 'Certifications': 'الشهادات', 'Country': 'الدولة',
    '🇪🇬 Egypt': '🇪🇬 مصر', '🇦🇪 UAE': '🇦🇪 الإمارات', '🇸🇦 Saudi Arabia': '🇸🇦 السعودية', '🇮🇳 India': '🇮🇳 الهند', '🇨🇳 China': '🇨🇳 الصين',
    'Showing': 'عرض', 'listings match your filters': 'إعلان يطابق الفلاتر', 'Supplier quality': 'جودة المورّد', '✓ Verified only': '✓ الموثّقون فقط', '⚡ Fast responder': '⚡ سريع الرد', '🏆 Top rated': '🏆 الأعلى تقييمًا',
    'Company listings': 'إعلانات الشركات', 'Post surplus': 'انشر فائضًا', 'Sponsored Listings': 'إعلانات ممولة', 'Featured placements — top visibility': 'أماكن مميزة — أعلى ظهور',
    'Sponsored': 'ممول', '⭐ Sponsored': '⭐ ممول', 'SPONSORED · FEATURED': 'ممول · مميز', 'SPONSORED · BOOST': 'ممول · ترويج', 'Contact Supplier →': 'تواصل مع المورّد ←', 'Request Quote →': 'اطلب عرض سعر ←',
    'Quick view': 'عرض سريع', 'Inquire': 'استفسر', 'Contact': 'تواصل', 'Contact →': 'تواصل ←', 'Quote →': 'عرض سعر ←', 'Offer →': 'قدّم عرضًا ←', 'Make an offer': 'قدّم عرضًا',
    'For Sale': 'للبيع', 'Looking to Buy': 'مطلوب للشراء', 'Price on request': 'السعر عند الطلب', 'Recently verified': 'موثّق حديثًا', 'Per product': 'لكل منتج', 'View all →': 'عرض الكل ←',
    '🛠️ Professional Services': '🛠️ خدمات مهنية', '+ Offer Service': '+ قدّم خدمة', '💼 Jobs & Careers': '💼 الوظائف والمسار المهني', '+ Post a Job': '+ انشر وظيفة', '⭐ Boost Your Listing': '⭐ روّج لإعلانك',
    'Upgrade Now': 'رقِّ الآن', '⭐ Featured Suppliers': '⭐ موردون مميزون', '🟠 Demand Board': '🟠 لوحة الطلبات', 'Submit quotes to open requests': 'قدّم عروضًا للطلبات المفتوحة', 'URGENT': 'عاجل', 'OPEN': 'مفتوح',
    'Need Service': 'مطلوب خدمة', '💼 Latest Jobs': '💼 أحدث الوظائف', 'Free': 'مجاني', 'New': 'جديد', 'Expert': 'خبير', 'Providing': 'يقدّم', 'available': 'متوفر', 'certified': 'معتمد',
    '📦 In stock': '📦 متوفر', '✓ Halal': '✓ حلال', 'Feature': 'الميزة', '🆓 Free': '🆓 مجاني', 'Compare': 'قارن', 'Save': 'حفظ', '🔖 Save': '🔖 حفظ', 'Saved!': 'تم الحفظ!', 'Select': 'اختر',
    /* jobs */
    'CAREERS': 'الوظائف', 'Full-time': 'دوام كامل', 'Part-time': 'دوام جزئي', 'Contract': 'عقد', 'Remote': 'عن بُعد', 'Remote ok': 'عن بُعد متاح', 'Remote possible': 'العمل عن بُعد ممكن',
    'All Jobs': 'كل الوظائف', 'All Levels': 'كل المستويات', 'Employment Type': 'نوع التوظيف', 'Seniority': 'المستوى', 'Apply Now →': 'قدّم الآن ←', 'Hiring': 'نوظّف', 'Looking for a Job': 'يبحث عن عمل',
    'Contact Candidate →': 'تواصل مع المرشح ←', 'Add to whitelist': 'أضف للقائمة البيضاء', 'Whitelist': 'القائمة البيضاء', 'Block (blacklist)': 'حظر (القائمة السوداء)', 'Blacklist': 'القائمة السوداء',
    'Write a public review': 'اكتب تقييمًا علنيًا', 'Write a review': 'اكتب تقييمًا', 'Write a work reference (worked with you)': 'اكتب شهادة عمل (عمل معك)', 'Work reference': 'شهادة عمل',
    'Public rating by candidates': 'تقييم علني من المرشحين', 'Public rating by companies': 'تقييم علني من الشركات', 'No jobs match these filters': 'لا توجد وظائف مطابقة لهذه الفلاتر',
    'Tick more employment types or countries.': 'اختر أنواع توظيف أو دولًا أكثر.', 'Clear filters': 'امسح الفلاتر', 'Junior': 'مبتدئ', 'Mid': 'متوسط', 'Senior': 'خبير', 'Intermediate': 'متوسط', 'Beginner': 'مبتدئ',
    /* groups */
    'COMMUNITIES': 'المجتمعات', 'Your Groups': 'مجموعاتك', 'All Groups': 'كل المجموعات', 'Create Group': 'أنشئ مجموعة', 'Create New Group': 'أنشئ مجموعة جديدة', '+ Join': '+ انضم', '✓ Joined': '✓ منضم',
    'DISCUSS': 'نقاش', 'DEAL ROOM': 'غرفة صفقات', 'Private': 'خاصة', 'Public': 'عامة', 'Deal Rooms': 'غرف الصفقات', 'Discussion': 'نقاش', 'Pharma': 'دواء', 'By Country': 'حسب الدولة',
    'What is this group about?': 'ما موضوع هذه المجموعة؟', 'Type the group name to confirm': 'اكتب اسم المجموعة للتأكيد',
    /* messages & notifications */
    '🔍 Search conversations...': '🔍 ابحث في المحادثات...', 'Type a message...': 'اكتب رسالة...', 'sent you a connection request': 'أرسل لك طلب اتصال', 'Accept': 'قبول', 'Decline': 'رفض',
    '+ Connect': '+ اتصال', 'Connect': 'اتصال', 'View profile': 'عرض الملف', 'TODAY': 'اليوم', 'Today': 'اليوم', 'Yesterday': 'أمس',
    /* saved & profile */
    'Saved Posts': 'المنشورات المحفوظة', 'No saved posts yet': 'لا توجد منشورات محفوظة بعد', 'Tap the bookmark icon on any post to save it': 'اضغط على أيقونة الحفظ في أي منشور لحفظه',
    'Activity': 'النشاط', 'About': 'نبذة', 'Experience': 'الخبرة', 'Skills': 'المهارات', 'Certificates': 'الشهادات', 'Edit profile': 'عدّل الملف', 'Message': 'رسالة',
    /* directory, company page, workspace */
    'COMPANY DIRECTORY': 'دليل الشركات', 'Find any pharma company in Egypt': 'اعثر على أي شركة دواء في مصر', 'Add or claim your company': 'أضف شركتك أو طالب بها', 'How results are ordered': 'كيف تُرتَّب النتائج',
    'Search companies': 'ابحث عن شركات', 'Order': 'الترتيب', 'Best match': 'الأكثر تطابقًا', 'All': 'الكل', 'All companies': 'كل الشركات', 'Manufacturer': 'مصنّع', 'CMO / Toll': 'تصنيع لدى الغير',
    'API & excipients': 'مواد فعالة وسواغات', 'Packaging': 'تعبئة وتغليف', 'Labs & testing': 'معامل وتحاليل', 'Distribution': 'توزيع', 'Regulatory & consulting': 'تسجيل واستشارات',
    'Cosmetics': 'مستحضرات تجميل', 'Supplements': 'مكملات', 'Can manufacture': 'يمكنه تصنيع', 'Governorate': 'المحافظة', 'Certified:': 'حاصل على:', 'Paid placement · does not affect the order below': 'مكان مدفوع · لا يؤثر على الترتيب أدناه',
    'View page': 'عرض الصفحة', 'Request a quote': 'اطلب عرض سعر', 'Your company': 'شركتك', 'Yours': 'لك', 'No track record yet': 'لا يوجد سجل تعاملات بعد', 'Verified': 'موثّقة', '✓ Verified': '✓ موثّقة',
    'Unclaimed': 'لم يطالب بها أحد', 'Active': 'نشطة', 'Active this week': 'نشطة هذا الأسبوع', 'Dormant': 'خاملة', 'Open company page': 'افتح صفحة الشركة', 'Directory health': 'صحة الدليل',
    'Overview': 'نظرة عامة', 'Products': 'المنتجات', 'Sites': 'المواقع', 'Listings': 'الإعلانات', 'Reviews': 'التقييمات', 'Team': 'الفريق', 'Deals': 'الصفقات', 'Suppliers': 'الموردون',
    'Reports & reviews': 'البلاغات والتقييمات', 'Plan & verification': 'الخطة والتوثيق', 'Page': 'الصفحة', 'COMPANY WORKSPACE': 'مساحة عمل الشركة', 'View public page': 'اعرض الصفحة العامة',
    'Open company workspace': 'افتح مساحة عمل الشركة', 'Profile PDF': 'ملف الشركة PDF', 'QR': 'رمز QR', 'Report wrong information': 'أبلغ عن معلومة خاطئة', 'Looking for': 'تبحث عن', 'Credentials': 'الاعتمادات',
    'People': 'الأشخاص', 'Sales': 'المبيعات', 'Quality': 'الجودة', 'Management': 'الإدارة', 'HR': 'الموارد البشرية', 'Head office': 'المقر الرئيسي', 'Certificate document': 'وثيقة الشهادة',
    'Shown on the public page': 'تظهر في الصفحة العامة', 'Registration holder and manufacturer': 'صاحب التسجيل والمصنّع', 'Finished dosage': 'مستحضر نهائي', 'Toll manufacturing': 'تصنيع لدى الغير',
    'Remove': 'إزالة', 'Close': 'إغلاق', 'Cancel': 'إلغاء', 'Open': 'فتح', 'Booked': 'محجوز', 'Your move': 'دورك', 'Sent': 'المرسلة', 'Received': 'الواردة',
    'Quote request': 'طلب عرض سعر', 'Surplus offer': 'عرض فائض', 'Group order': 'طلب جماعي', 'Service request': 'طلب خدمة', 'Qualification questionnaire': 'استبيان تأهيل', 'Dossier request': 'طلب ملف', 'Job application': 'طلب توظيف',
    'Company · Confirmed by the organisation': 'شركة · مؤكدة من الجهة', 'Verified: registry and tax card checked': 'موثّقة: تم التحقق من السجل التجاري والبطاقة الضريبية',
    'about, products, sites, contact': 'النبذة والمنتجات والمواقع والتواصل', 'Live listing analytics': 'إحصائيات الإعلان المباشرة', 'EDA licensed': 'مرخّصة من هيئة الدواء المصرية',
    /* lite mode */
    'This action needs the full app': 'هذا الإجراء يحتاج التطبيق الكامل', 'Read-only preview': 'عرض للقراءة فقط',

    /* ticker & hero copy */
    'Supply:': 'عرض:', 'Demand:': 'طلب:', 'License:': 'ترخيص:', 'CMO:': 'تصنيع:', 'Equipment:': 'معدات:', 'Job:': 'وظيفة:', 'Deal:': 'صفقة:', 'New job:': 'وظيفة جديدة:', 'New service:': 'خدمة جديدة:', 'Deal closed:': 'صفقة مكتملة:',
    'Supply, demand and regulation.': 'عرض وطلب وتسجيل.', 'Every offer, RFQ and EDA circular from the people you trade with. Read it, answer it, and close the deal before the market moves on.': 'كل عرض وطلب تسعير ومنشور من هيئة الدواء من الناس الذين تتعامل معهم. اقرأه ورد عليه وأغلق الصفقة قبل أن يتحرك السوق.',
    'professionals — graduates, specialists and industry veterans': 'متخصص — خريجون ومتخصصون وخبراء صناعة', 'Home — Pharma Today': 'الرئيسية — الدواء اليوم', 'PHARMA': 'الدواء', 'JOBS': 'الوظائف',
    'Companies that match what Quadra Pharm is looking for': 'شركات تطابق ما تبحث عنه كوادرا فارم', "What's on your mind, Haytham?": 'بماذا تفكر يا هيثم؟',
    'The B2B Pharma': 'منصة تجارة الدواء', 'Trading Hub': 'بين الشركات', '⬡ Drugbox Marketplace': '⬡ سوق Drugbox', 'Source · Supply · License · Manufacture · Services · Hire · Train': 'توريد · عرض · ترخيص · تصنيع · خدمات · توظيف · تدريب',
    'Free Listings — Supply': 'إعلانات مجانية — عرض', '📊 Free vs Sponsored — What\u2019s the difference?': '📊 مجاني أم ممول — ما الفرق؟', "📊 Free vs Sponsored — What's the difference?": '📊 مجاني أم ممول — ما الفرق؟',
    '📍 Listing placement': '📍 مكان الإعلان', 'Bottom of list': 'آخر القائمة', 'Top of page always': 'أعلى الصفحة دائمًا', '📸 Media & description': '📸 الصور والوصف', 'Basic text only': 'نص أساسي فقط', 'Image + full desc': 'صورة ووصف كامل',
    '✓ Trust badges': '✓ شارات الثقة', 'All certs shown': 'كل الشهادات ظاهرة', '⭐ Seller rating': '⭐ تقييم البائع', 'Stars + deal count': 'نجوم وعدد الصفقات', '📊 Analytics dashboard': '📊 لوحة الإحصائيات', 'Views, inquiries, CTR': 'المشاهدات والاستفسارات ونسبة النقر',
    '🔔 Demand alerts': '🔔 تنبيهات الطلبات', 'Instant notifications': 'إشعارات فورية', '👁 Avg monthly views': '👁 متوسط المشاهدات الشهرية', '📨 Avg inquiries/month': '📨 متوسط الاستفسارات شهريًا',
    '✓ Top placement always': '✓ مكان في الأعلى دائمًا', '✓ Full media & description': '✓ صور ووصف كامل', '✓ Analytics dashboard': '✓ لوحة إحصائيات', '✓ Demand alerts': '✓ تنبيهات الطلبات', '✓ Verified seller badge': '✓ شارة البائع الموثّق',
    'Reach 150,000+ pharmacists & scientists across the Gulf & Africa. Get 8× more views.': 'اوصل لأكثر من 150,000 صيدلي وعالم في الخليج وأفريقيا. واحصل على مشاهدات أكثر 8 مرات.',
    'Expiring in 3 days': 'ينتهي خلال 3 أيام', 'Per country': 'لكل دولة', 'Per dossier': 'لكل ملف', 'Per formula': 'لكل تركيبة', '/day': '/يوم', 'Free consultation · Cairo & online': 'استشارة مجانية · القاهرة وأونلاين',
    'Per product · Free consult': 'لكل منتج · استشارة مجانية', 'HOT': 'رائج', 'Dossier': 'ملف', 'Stability': 'ثبات', 'Audit': 'تدقيق', 'Scale-up': 'تكبير الإنتاج', 'EDA Experience': 'خبرة بهيئة الدواء', 'EDA Certified': 'معتمد من هيئة الدواء',
    'HPLC Expert': 'خبير HPLC', 'Remote ok': 'عن بُعد متاح', 'registrations': 'تسجيلات', 'New batch.': 'دفعة جديدة.', 'accepted.': 'مقبول.', 'DMF filed': 'DMF مودع',
    'Pharma · Cosmetics · Medical Devices · Regulatory · Production · Sales': 'دواء · تجميل · أجهزة طبية · تسجيل · إنتاج · مبيعات',
    'Regulatory · Registration · QA Consulting · Dossier Preparation · Lab Testing': 'تسجيل · تسجيل منتجات · استشارات جودة · إعداد ملفات · تحاليل معملية',
    /* directory & company */
    'Search by name, product, active ingredient or what a plant can manufacture — in Arabic or English.': 'ابحث بالاسم أو المنتج أو المادة الفعالة أو ما يمكن للمصنع تصنيعه — بالعربي أو الإنجليزي.',
    'They offer:': 'يقدّمون:', 'Distributor': 'موزّع', 'Page completeness': 'اكتمال الصفحة', 'Add your logo': 'أضف شعارك', 'Describe the company': 'اكتب نبذة عن الشركة', 'Add your sites (plants, warehouses)': 'أضف مواقعك (مصانع ومخازن)',
    'Add products': 'أضف منتجات', 'Add phone or email': 'أضف هاتفًا أو بريدًا', 'Invite your team': 'ادعُ فريقك', 'Add certificates with expiry dates': 'أضف الشهادات بتواريخ انتهائها', 'Get verified (free)': 'وثّق شركتك (مجانًا)',
    'Add the Arabic company name': 'أضف اسم الشركة بالعربي', 'At a glance': 'نظرة سريعة', 'Waiting for you': 'بانتظارك', 'Open requests': 'طلبات مفتوحة', 'Completed orders': 'طلبات مكتملة', 'On time': 'في الموعد',
    'Your page shows as': 'تظهر صفحتك كـ', 'this week.': 'هذا الأسبوع.', 'Distributor — Upper Egypt': 'موزّع — الصعيد', 'Export partner — GCC': 'شريك تصدير — الخليج', 'API supplier — Metformin': 'مورّد مادة فعالة — ميتفورمين',
    'Member:': 'عضو:', 'site': 'موقع', 'sites': 'مواقع', 'Warehouse': 'مخزن', 'Factory': 'مصنع', 'Lab': 'معمل', 'Office': 'مكتب', 'Giza plant': 'مصنع الجيزة', 'Honor': 'تكريم',
    /* jobs */
    'Pharma, cosmetics & medical device careers across Egypt & the GCC': 'وظائف الدواء والتجميل والأجهزة الطبية في مصر والخليج', "I'm Hiring": 'أنا أوظّف', "I'm Job Hunting": 'أبحث عن عمل', 'Your next role is here.': 'وظيفتك القادمة هنا.',
    'Graduates, specialists and senior leaders — hiring and being hired.': 'خريجون ومتخصصون وقيادات — يوظّفون ويتوظّفون.', 'open positions across Egypt & GCC': 'وظيفة متاحة في مصر والخليج', 'jobs posted this week': 'وظيفة نُشرت هذا الأسبوع',
    'candidates available now': 'مرشح متاح الآن', 'Production': 'الإنتاج', 'Sales & Marketing': 'المبيعات والتسويق', 'R&D / Formulation': 'البحث والتطوير / التركيبات', '📋 Regulatory': '📋 التسجيل', '🔬 QA/QC': '🔬 الجودة', '🏭 Production': '🏭 الإنتاج',
    '📈 Sales & Marketing': '📈 المبيعات والتسويق', '🧪 R&D / Formulation': '🧪 البحث والتطوير / التركيبات', 'Apply': 'قدّم', 'Department': 'القسم', 'Location': 'الموقع', 'Years of experience': 'سنوات الخبرة',
    /* profile & network */
    'Chairman & CEO': 'رئيس مجلس الإدارة والرئيس التنفيذي', 'People you may know': 'أشخاص قد تعرفهم', 'Invitations': 'الدعوات', 'Manage my network': 'إدارة شبكتي', 'Followers': 'المتابعون', 'Following': 'تتابعهم',
    'Posts': 'المنشورات', 'Mutual connections': 'اتصالات مشتركة', 'See all': 'عرض الكل', 'Show more': 'اعرض المزيد', 'Show less': 'اعرض أقل', 'More': 'المزيد',
    

    /* jobs (2) */
    'Seniority Level': 'المستوى الوظيفي', 'Executive': 'تنفيذي', 'Senior Mgmt': 'إدارة عليا', 'Mid-Level': 'مستوى متوسط', 'Entry Level': 'مبتدئ', 'Hiring for your team?': 'توظف لفريقك؟', 'Post a Job': 'انشر وظيفة',
    'Available Candidates': 'مرشحون متاحون', 'Verified professionals actively looking': 'متخصصون موثّقون يبحثون الآن', 'Top rated': 'الأعلى تقييمًا', 'Honor list': 'قائمة الشرف', 'Warning list': 'قائمة التحذير',
    'Preferred only': 'المفضّلون فقط', 'My lists': 'قوائمي', 'Certified': 'معتمد', 'GCC Market': 'سوق الخليج', 'Skincare R&D': 'تطوير منتجات العناية بالبشرة',
    /* network */
    'NETWORK': 'الشبكة', 'Every generation of pharma, connected.': 'كل أجيال الدواء، متصلة.', 'People You May Know': 'أشخاص قد تعرفهم', 'Pending': 'قيد الانتظار', 'Pending Invitations': 'دعوات معلّقة',
    /* groups (2) */
    'Communities that get things done.': 'مجتمعات تُنجز.', 'of your groups have new posts today': 'من مجموعاتك بها منشورات جديدة اليوم', 'unread across your groups': 'غير مقروء في مجموعاتك',
    '🔥 Trending now': '🔥 رائج الآن', 'Quiet today': 'هادئة اليوم', 'Your Group Activity Score': 'مؤشر نشاطك في المجموعات', 'Posts read': 'منشورات مقروءة', 'Connections made': 'اتصالات جديدة',
    'Knowledge sharing groups': 'مجموعات تبادل المعرفة', 'Buy/sell focused groups': 'مجموعات البيع والشراء', 'Suggested for You': 'مقترحة لك', 'Active daily': 'نشطة يوميًا', 'New group · launching strong': 'مجموعة جديدة · انطلاقة قوية',
    '🔥 #1 ACTIVE': '🔥 الأكثر نشاطًا', 'Deal Room': 'غرفة صفقات',
    /* messages (2) */
    'View Listing →': 'اعرض الإعلان ←', '📄 Request COA': '📄 اطلب شهادة التحليل', '📋 Ask for samples': '📋 اطلب عينات', '💰 Negotiate price': '💰 تفاوض على السعر', '📅 Schedule a call': '📅 حدّد مكالمة', '✅ Accept quote': '✅ اقبل العرض',
    'Online now': 'متصل الآن', 'Unread': 'غير مقروء', 'You:': 'أنت:',
    /* notifications (2) */
    'Mark all read': 'تعليم الكل كمقروء', 'Clear all': 'مسح الكل', 'Reactions': 'التفاعلات', 'Comments': 'التعليقات', 'and 2 others liked your post': 'و2 آخرون أعجبهم منشورك',
    /* profile (2) */
    '📷 Edit cover': '📷 عدّل الغلاف', '✏️ Edit Profile': '✏️ عدّل الملف', 'Profile strength': 'قوة الملف', 'Certificate wall': 'حائط الشهادات', 'WHO-GMP Certified Facility': 'منشأة حاصلة على WHO-GMP',
    'Renew this year · 2026': 'تُجدَّد هذا العام · 2026', 'Expired · 2025': 'منتهية · 2025', 'EDA Manufacturing License': 'ترخيص تصنيع من هيئة الدواء', 'Egyptian Drug Authority': 'هيئة الدواء المصرية', 'Valid · Ongoing': 'سارية · مستمرة',
    'Profile insights': 'إحصائيات الملف', 'last 7 days · only you can see this': 'آخر 7 أيام · يراها أنت فقط', 'Who viewed you': 'من شاهدك', 'Manufacturers': 'مصنّعون', 'Distributors & importers': 'موزعون ومستوردون',
    'Regulatory consultants': 'مستشارو تسجيل', 'Recruiters': 'مسؤولو توظيف', 'Other': 'أخرى', 'Searches that found you': 'عمليات بحث وصلت إليك', 'Recent viewers': 'زوار حديثون', 'My companies': 'شركاتي',
    'Create a company page': 'أنشئ صفحة شركة', 'People also viewed': 'شاهدوا أيضًا',
    /* months & places kept; months translated */
    'Jan': 'يناير', 'Feb': 'فبراير', 'Mar': 'مارس', 'Apr': 'أبريل', 'May': 'مايو', 'Jun': 'يونيو', 'Jul': 'يوليو', 'Aug': 'أغسطس', 'Sep': 'سبتمبر', 'Oct': 'أكتوبر', 'Nov': 'نوفمبر', 'Dec': 'ديسمبر',
    'Cairo': 'القاهرة', 'Giza': 'الجيزة', 'Alexandria': 'الإسكندرية', 'Dubai': 'دبي', 'Riyadh': 'الرياض', 'Egypt': 'مصر', 'UAE': 'الإمارات', 'Saudi': 'السعودية', 'Saudi Arabia': 'السعودية', 'India': 'الهند', 'China': 'الصين',
    'Cairo, Egypt': 'القاهرة، مصر', 'Giza, Egypt': 'الجيزة، مصر', 'Alexandria, Egypt': 'الإسكندرية، مصر', 'Dubai, UAE': 'دبي، الإمارات', 'Hyderabad, India': 'حيدر آباد، الهند',
    

    'Mentors, peers and the next wave of talent in one place.': 'مرشدون وزملاء والجيل القادم من المواهب في مكان واحد.', 'Discuss, share deals and learn from each other.': 'ناقش وشارك الصفقات وتعلّم من الآخرين.',
    'Sorted by activity — most active first': 'مرتبة حسب النشاط — الأكثر نشاطًا أولًا', 'Reach 150,000+ pharma professionals across the Gulf & Africa': 'اوصل لأكثر من 150,000 متخصص في الدواء في الخليج وأفريقيا',
    'My Groups': 'مجموعاتي', 'SUPPLY': 'عرض', 'SERVICE': 'خدمة', 'DEMAND': 'طلب', 'LICENSE': 'ترخيص', 'EQUIPMENT': 'معدات', 'TRAINING': 'تدريب', 'Updated quote:': 'عرض محدّث:', 'Online': 'متصل',
    'Deal Rooms — Egypt & GCC': 'غرف الصفقات — مصر والخليج',
    

    'Any': 'أي', 'All governorates': 'كل المحافظات', 'Any certificate': 'أي شهادة', 'Any dosage form': 'أي شكل صيدلي', 'All types': 'كل الأنواع', 'Any time': 'أي وقت', 'Newest': 'الأحدث', 'Most complete': 'الأكثر اكتمالًا',
    'Company, product or ingredient — e.g. ميتفورمين or Metformin': 'شركة أو منتج أو مادة فعالة — مثلًا ميتفورمين أو Metformin', 'Verified first': 'الموثّقة أولًا', 'Track record': 'سجل التعاملات', 'Rating': 'التقييم', 'Name': 'الاسم',
    

    '⭐ Boost your listing — reach 150,000+ pharmacists & scientists across the Gulf & Africa': '⭐ روّج لإعلانك — اوصل لأكثر من 150,000 صيدلي وعالم في الخليج وأفريقيا',
    'Boost your listing — reach 150,000+ pharmacists & scientists across the Gulf & Africa': 'روّج لإعلانك — اوصل لأكثر من 150,000 صيدلي وعالم في الخليج وأفريقيا',
    'Sponsored listings get 8× more views and 5× more inquiries than free listings': 'الإعلانات الممولة تحصل على مشاهدات أكثر 8 مرات واستفسارات أكثر 5 مرات من الإعلانات المجانية',
    

    /* deals */
    'Accept quote': 'اقبل العرض', 'Accepted': 'مقبول', 'Applied': 'تم التقديم', 'Closed': 'مغلقة', 'Confirm order': 'أكّد الطلب', 'Confirm received': 'أكّد الاستلام', 'Delivered': 'تم التسليم',
    'Delivery terms': 'شروط التسليم', 'Mark shipped': 'تم الشحن', 'Order confirmed': 'تم تأكيد الطلب', 'Quantity': 'الكمية', 'Quote received': 'وصل العرض', 'Shipped': 'تم الشحن',
    'Timeline': 'التسلسل الزمني', 'Unit': 'الوحدة', 'You are the sender': 'أنت المرسل', 'You are the receiver': 'أنت المستقبل', 'Send quote': 'أرسل عرضًا', 'Request sent': 'تم إرسال الطلب',
    'Counter-offer': 'عرض مضاد', 'Rate the supplier': 'قيّم المورّد', 'Rated': 'تم التقييم', 'Proposal sent': 'تم إرسال المقترح', 'In progress': 'قيد التنفيذ', 'Offer sent': 'تم إرسال العرض',
    'Simulate their reply (demo)': 'محاكاة ردهم (تجريبي)', 'Open deal': 'افتح الصفقة', 'Your move': 'دورك', 'Waiting for them': 'بانتظارهم', 'All types': 'كل الأنواع',
    

    'COMPLIANCE PASSPORT': 'جواز الامتثال', 'VERIFICATION LEVEL': 'مستوى التوثيق', 'Documents & certificates': 'المستندات والشهادات', 'Registered': 'مسجّلة', 'Licensed': 'مرخّصة', 'Inspected': 'مفتَّشة', 'Not verified': 'غير موثّقة',
    'Commercial registry': 'السجل التجاري', 'Tax card': 'البطاقة الضريبية', 'EDA / industrial licence': 'ترخيص الهيئة / الترخيص الصناعي', 'Product documents': 'مستندات المنتجات', 'Sites': 'المواقع',
    'Verified': 'موثّق', 'Self-declared': 'مُصرَّح به', 'Under review': 'قيد المراجعة', 'Expires soon': 'ينتهي قريبًا', 'Expired': 'منتهي', 'Not provided': 'غير مقدَّم', 'Request': 'اطلب', 'Requested': 'تم الطلب',
    'Add document': 'أضف مستندًا', 'Add a compliance document': 'إضافة مستند امتثال', 'Document': 'المستند', 'Product / site': 'المنتج / الموقع', 'Number / reference': 'الرقم / المرجع', 'Valid to (optional)': 'صالح حتى (اختياري)',
    'Shown as self-declared until Drugbox checks the document.': 'يظهر كمُصرَّح به حتى تراجعه Drugbox.', 'Commercial registry and tax card checked by Drugbox': 'السجل التجاري والبطاقة الضريبية روجعا من Drugbox',
    'EDA or industrial licence on file': 'ترخيص الهيئة أو الترخيص الصناعي مسجّل', 'At least one site with a valid GMP-type certificate': 'موقع واحد على الأقل بشهادة GMP سارية',
    'Top level reached. Keep certificates current to stay here.': 'وصلت لأعلى مستوى. حافظ على سريان الشهادات لتبقى فيه.',

    'Levels: 1 Registered — registry & tax card checked · 2 Licensed — EDA / industrial licence · 3 Inspected — a site with a valid GMP-type certificate. Self-declared documents are shown as provided by the company.': 'المستويات: 1 مسجّلة — روجع السجل التجاري والبطاقة الضريبية · 2 مرخّصة — ترخيص الهيئة / الترخيص الصناعي · 3 مفتَّشة — موقع بشهادة GMP سارية. المستندات المُصرَّح بها تظهر كما قدّمتها الشركة.',

    'Company video': 'فيديو الشركة', 'My video introduction': 'فيديو التعريف بي', 'Video introduction': 'فيديو تعريفي', 'Add a company video': 'أضف فيديو للشركة', 'Add a video introduction': 'أضف فيديو تعريفي',
    'Replace video': 'استبدل الفيديو', 'Remove': 'احذف', 'Video saved': 'تم حفظ الفيديو', 'Video removed': 'تم حذف الفيديو', 'Checking the video…': 'جارٍ فحص الفيديو…', 'Remove this video?': 'حذف هذا الفيديو؟',
    'Show buyers your site, team and quality in a short video (up to 3 minutes).': 'اعرض للمشترين موقعك وفريقك وجودتك في فيديو قصير (حتى 3 دقائق).',
    'Introduce yourself to employers and partners in a short video (up to 90 seconds).': 'عرّف نفسك لأصحاب العمل والشركاء في فيديو قصير (حتى 90 ثانية).',
    'Use an MP4, WebM or MOV video': 'استخدم فيديو MP4 أو WebM أو MOV', 'This video could not be read — try MP4 (H.264)': 'تعذّرت قراءة الفيديو — جرّب MP4 (H.264)',

    'Pay with': 'ادفع بـ', 'Card': 'كارت بنكي', 'Vodafone Cash & wallets': 'فودافون كاش والمحافظ', 'Fawry': 'فوري', 'InstaPay': 'إنستاباي',
    'Visa · Mastercard · Meeza': 'فيزا · ماستركارد · ميزة', 'Pay at any Fawry outlet or in the myFawry app': 'ادفع في أي منفذ فوري أو من تطبيق myFawry', 'Transfer, then send us the receipt': 'حوّل وابعت لنا الإيصال',
    'Pay at Fawry': 'الدفع عن طريق فوري', 'Fawry reference number': 'الرقم المرجعي لفوري', 'Pay with InstaPay': 'الدفع بإنستاباي', 'Send to': 'حوّل إلى',
    'Transfer number *': 'رقم التحويل *', 'Receipt (screenshot or PDF)': 'الإيصال (صورة أو PDF)', 'Send for confirmation': 'أرسل للتأكيد', 'Listing to promote': 'الإعلان المراد تمييزه',
    'Opening the secure Paymob page…': 'جارٍ فتح صفحة الدفع الآمنة من Paymob…', 'Thank you — we confirm InstaPay transfers within one working day': 'شكرًا — نؤكد تحويلات إنستاباي خلال يوم عمل',
    'Payment received — it is active now': 'تم استلام الدفع — الاشتراك مفعّل الآن', 'Payments': 'المدفوعات', 'Confirm payment': 'تأكيد الدفع', 'Not received': 'لم يصل',
    'Go to any Fawry outlet, or open myFawry → Pay with reference.': 'اذهب لأي منفذ فوري أو افتح myFawry ← الدفع بالرقم المرجعي.', 'Give the reference number and pay the amount.': 'أعطِ الرقم المرجعي وادفع المبلغ.',
    'It activates automatically once Fawry confirms — we notify you.': 'يتفعّل تلقائيًا بمجرد تأكيد فوري — وسنخطرك.', 'Choose the listing to promote': 'اختر الإعلان المراد تمييزه',
    /* notices */
    'Welcome back, Haytham!': 'أهلًا بعودتك يا هيثم!', 'Post shared': 'تم نشر المنشور', 'Saved': 'تم الحفظ', 'Copied': 'تم النسخ', 'Deleted': 'تم الحذف', 'Undo': 'تراجع'
  };
  var UNITS = { m: ['دقيقة', 'دقائق'], h: ['ساعة', 'ساعات'], d: ['يوم', 'أيام'], w: ['أسبوع', 'أسابيع'], min: ['دقيقة', 'دقائق'] };
  function unit(n, u) { var p = UNITS[u] || [u, u]; return +n >= 3 && +n <= 10 ? p[1] : p[0]; }
  var WORDS = { comments: 'تعليق', comment: 'تعليق', reposts: 'إعادة نشر', repost: 'إعادة نشر', members: 'عضو', member: 'عضو', posts: 'منشور', post: 'منشور', views: 'مشاهدة', view: 'مشاهدة',
    connections: 'اتصال', listings: 'إعلان', listing: 'إعلان', companies: 'شركة', company: 'شركة', providers: 'مقدّم خدمة', clients: 'عميل', inquiries: 'استفسار', results: 'نتيجة', sites: 'مواقع', site: 'موقع', clients2: 'عميل',
    'open positions': 'وظيفة متاحة', 'requests received': 'طلبات واردة', 'request received': 'طلب وارد', 'new posts today': 'منشورات جديدة اليوم', 'new posts this week': 'منشورات جديدة هذا الأسبوع', 'deals closed': 'صفقة مكتملة' };
  var PATTERNS = [
    [/^(\d+)\s*(m|min|h|d|w) ago$/i, function (m) { return 'منذ ' + m[1] + ' ' + unit(m[1], m[2].toLowerCase()); }],
    [/^(\d+)(min|h|d) ago(.*)$/i, function (m) { return 'منذ ' + m[1] + ' ' + unit(m[1], m[2].toLowerCase()) + tr(m[3]); }],
    [/^([\d,.]+K?)\s+(comments?|reposts?|members?|posts?|views?|connections?|listings?|companies|company|providers|clients|inquiries|results|sites?|open positions|requests received|request received|new posts today|new posts this week|deals closed)$/i, function (m) { return m[1] + ' ' + WORDS[m[2].toLowerCase()]; }],
    [/^(.+?)\s*\((\d+)\)$/, function (m) { var h = D[m[1]] || D[m[1].trim()]; return h ? h + ' (' + m[2] + ')' : null; }],
    [/^(Surplus stock|Licensing dossiers|Group buying)\s*\((\d+)\)$/, function (m) { return ({ 'Surplus stock': 'مخزون فائض', 'Licensing dossiers': 'ملفات ترخيص', 'Group buying': 'شراء جماعي' })[m[1]] + ' (' + m[2] + ')'; }],
    [/^expires (\d{4}-\d{2})$/, function (m) { return 'تنتهي ' + m[1]; }], [/^expired (\d{4}-\d{2})$/, function (m) { return 'انتهت ' + m[1]; }],
    [/^Source: (.+) · updated (.+)$/, function (m) { return 'المصدر: ' + (D[m[1]] || m[1]) + ' · حُدّث ' + m[2]; }],
    [/^Open (.+)’s profile$/, function (m) { return 'افتح ملف ' + m[1]; }], [/^Open (.+)$/, function (m) { return D[m[1]] ? 'افتح ' + D[m[1]] : null; }],
    [/^You joined (.+)$/, function (m) { return 'انضممت إلى ' + m[1]; }], [/^You left (.+)$/, function (m) { return 'غادرت ' + m[1]; }]
  ];
  PATTERNS.push(
    [/^▶ Video intro · (\d+:\d+)$/, function (m) { return '▶ فيديو تعريفي · ' + m[1]; }],
    [/^Keep it under (3 minutes|90 seconds) \(this one is (\d+:\d+)\)$/, function (m) { return 'اجعله أقل من ' + (m[1] === '3 minutes' ? '3 دقائق' : '90 ثانية') + ' (هذا ' + m[2] + ')'; }],
    [/^The video is larger than (\d+) MB$/, function (m) { return 'الفيديو أكبر من ' + m[1] + ' ميجابايت'; }],
    [/^Level (\d) · (Registered|Licensed|Inspected)$/, function (m) { return 'المستوى ' + m[1] + ' · ' + D[m[2]]; }],
    [/^Next: (.+)\.$/, function (m) { return 'التالي: ' + (D[m[1]] || m[1]) + '.'; }],
    [/^(\d+\+?|\d+[–-]\d+) yrs( exp)?$/, function (m) { return m[1] + ' سنوات' + (m[2] ? ' خبرة' : ''); }],
    [/^(\d+) years? experience$/, function (m) { return m[1] + ' سنة خبرة'; }], [/^✓ (\d+) years experience$/, function (m) { return '✓ ' + m[1] + ' سنة خبرة'; }],
    [/^(👁|📨)\s*([\d,]+) (views|inquiries)$/, function (m) { return m[1] + ' ' + m[2] + ' ' + (m[3] === 'views' ? 'مشاهدة' : 'استفسار'); }],
    [/^~([\d,]+) (views|inquiries)( \((\d+)×\))?$/, function (m) { return '~' + m[1] + ' ' + (m[2] === 'views' ? 'مشاهدة' : 'استفسار') + (m[3] ? ' (' + m[4] + '×)' : ''); }],
    [/^(\d+)× avg reach$/, function (m) { return 'وصول أعلى ' + m[1] + '× من المتوسط'; }],
    [/^Matches: (.+)$/, function (m) { return 'تطابق: ' + m[1].split(' · ').map(function (x) { return D[x] || x; }).join(' · '); }],
    [/^(\d+) profiles$/, function (m) { return m[1] + ' ملفات'; }], [/^#(\d+) top-rated candidate$/, function (m) { return 'المرشح #' + m[1] + ' الأعلى تقييمًا'; }],
    [/^(\d+) warnings?$/, function (m) { return m[1] + ' تحذير'; }], [/^(\d+) new posts?$/, function (m) { return m[1] + ' منشورات جديدة'; }],
    [/^(\d+) new requests today$/, function (m) { return m[1] + ' طلبات جديدة اليوم'; }], [/^(\d+) quote requests today$/, function (m) { return m[1] + ' طلبات تسعير اليوم'; }],
    [/^(\d+) unread$/, function (m) { return m[1] + ' غير مقروء'; }], [/^(\d+) UNREAD \/ (\d+) TOTAL$/, function (m) { return m[1] + ' غير مقروء / ' + m[2] + ' إجمالي'; }],
    [/^(\d+) on record$/, function (m) { return m[1] + ' مسجلة'; }], [/^(\d+) SAVED POSTS$/, function (m) { return m[1] + ' منشور محفوظ'; }],
    [/^(\d+) CONNECTIONS \/ (\d+) PENDING$/, function (m) { return m[1] + ' اتصالات / ' + m[2] + ' معلّقة'; }], [/^View all (\d+) →$/, function (m) { return 'عرض الكل (' + m[1] + ') ←'; }],
    [/^New group · ([\d,]+) members already$/, function (m) { return 'مجموعة جديدة · ' + m[1] + ' عضو بالفعل'; }], [/^💡 (\d+) of your connections are members$/, function (m) { return '💡 ' + m[1] + ' من اتصالاتك أعضاء'; }],
    [/^Honor ×(\d+)$/, function (m) { return 'تكريم ×' + m[1]; }], [/^Today, (.+)$/, function (m) { return 'اليوم، ' + m[1]; }],
    [/^(\d+) new posts · (\d+) buyers active right now$/, function (m) { return m[1] + ' منشورات جديدة · ' + m[2] + ' مشترين نشطين الآن'; }],
    [/^🇪🇬 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇪🇬 ' + q : null; }], [/^🇦🇪 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇦🇪 ' + q : null; }],
    [/^🇮🇳 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇮🇳 ' + q : null; }], [/^🇸🇦 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇸🇦 ' + q : null; }]
  );
  var DAYS = { SUNDAY: 'الأحد', MONDAY: 'الاثنين', TUESDAY: 'الثلاثاء', WEDNESDAY: 'الأربعاء', THURSDAY: 'الخميس', FRIDAY: 'الجمعة', SATURDAY: 'السبت' };
  var CAPS = { 'MARKET POSTS': 'منشورات سوق', 'REGULATORY UPDATES': 'تحديثات تسجيل', LISTINGS: 'إعلان', SUPPLY: 'عرض', DEMAND: 'طلب', SUPPLIERS: 'مورّد', CONNECTIONS: 'اتصالات', PENDING: 'معلّقة', UNREAD: 'غير مقروء', TOTAL: 'إجمالي' };
  PATTERNS.push(
    [/^[A-Za-z0-9 .,K]+( \/ [A-Za-z0-9 .,K]+)+$/, function (m) { var ok = 0, out = m[0].split(' / ').map(function (seg) { seg = seg.trim(); var U = seg.toUpperCase(); if (DAYS[U]) { ok++; return DAYS[U]; } var x = /^([\d.,]+K?) ([A-Za-z ]+)$/.exec(seg); if (x && CAPS[x[2].toUpperCase()]) { ok++; return x[1] + ' ' + CAPS[x[2].toUpperCase()]; } return seg; }).join(' / '); return ok ? out : null; }],
    [/^trending — (\d+) posts in (\d+)h$/, function (m) { return 'رائج — ' + m[1] + ' منشورًا خلال ' + m[2] + ' ساعة'; }],
    [/^💡 You have (\d+) active (.+) listings — buyers post here daily$/, function (m) { return '💡 لديك ' + m[1] + ' إعلانات ' + m[2] + ' نشطة — المشترون ينشرون هنا يوميًا'; }],
    [/^⚡ Replies in <(\d+)h$/, function (m) { return '⚡ يرد خلال أقل من ' + m[1] + ' ساعة'; }],
    [/^✅ (\d+)% response rate · avg\. (.+) reply(.*)$/, function (m) { return '✅ نسبة الرد ' + m[1] + '% · متوسط الرد ' + m[2].replace(/min$/, ' دقيقة').replace(/h$/, ' ساعة') + tr(m[3]); }],
    [/^● Online · (.+)$/, function (m) { return '● متصل · ' + m[1]; }],
    [/^reacted to your post about (.+)$/, function (m) { return 'تفاعل مع منشورك عن ' + m[1]; }], [/^💡 Matches your "(.+)" sector tag$/, function (m) { return '💡 يطابق قطاع "' + m[1] + '" في ملفك'; }]
  );
  var QTYPE = { 'Quote request': 'طلب عرض سعر', 'Service request': 'طلب خدمة', 'Surplus offer': 'عرض فائض', 'Dossier request': 'طلب ملف', 'Job application': 'طلب توظيف', 'Qualification questionnaire': 'استبيان تأهيل', 'Group order': 'طلب جماعي', 'Requests & deals': 'الطلبات والصفقات' };
  PATTERNS.push(
    [/^(Quote request|Service request|Surplus offer|Dossier request|Job application|Qualification questionnaire|Group order|Requests & deals) — (.+)$/, function (m) { return QTYPE[m[1]] + ' — ' + m[2]; }],
    [/^(\d+) waiting for you$/, function (m) { return m[1] + ' بانتظارك'; }],
    [/^·?\s*(Accept quote|Confirm order|Mark shipped|Send quote|Confirm received)$/, function (m) { return '· ' + D[m[1]]; }],
    [/^Send quote: (.+) · valid (\d+) days$/, function (m) { return 'أرسل عرضًا: ' + m[1] + ' · صالح ' + m[2] + ' يومًا'; }],
    [/^· valid (\d+) days \(to ([^)]+)\)(.*)$/, function (m) { return '· صالح ' + m[1] + ' يومًا (حتى ' + m[2] + ')' + m[3]; }]
  );
  var ARROWS = { '→': '←', '←': '→' };
  function put(raw, t, r) {   /* keep the original's surrounding spaces even when its inner spacing differs */
    if (raw.indexOf(t) >= 0) return raw.replace(t, r);
    var m = /^(\s*)[\s\S]*?(\s*)$/.exec(raw); return (m ? m[1] : '') + r + (m ? m[2] : '');
  }
  function tr(s) {
    if (!s) return s; var raw = s, t = s.replace(/\s+/g, ' ').trim(); if (!t) return s;
    if (D[t]) return put(raw, t, D[t]);
    for (var i = 0; i < PATTERNS.length; i++) { var m = PATTERNS[i][0].exec(t); if (m) { var r = PATTERNS[i][1](m); if (r) return put(raw, t, r); } }
    if (t.indexOf(' · ') > 0) { var parts = t.split(' · '), hit = 0; parts = parts.map(function (p) { var q = tr(p); if (q !== p) hit++; return q; }); if (hit) return put(raw, t, parts.join(' · ')); }
    var pre = /^([A-Za-z][A-Za-z &/]+:)\s+(.+)$/.exec(t); if (pre && D[pre[1]]) return put(raw, t, D[pre[1]] + ' ' + pre[2]);
    /* leading icons / trailing arrows around a known phrase */
    var mm = /^([^A-Za-z]*?)([A-Za-z][^→←]*?)(\s*[→←])?$/.exec(t);
    if (mm && D[mm[2].trim()]) return put(raw, t, mm[1] + D[mm[2].trim()] + (mm[3] ? ' ' + ARROWS[mm[3].trim()] : ''));
    return s;
  }
  window.dxT = tr;
  /* the original (English) text of an element, whatever the interface language — so logic never depends on the language shown */

  /* never translate what people wrote */
  var SKIP = 'script,style,svg,input,textarea,[contenteditable],.post-body,.post-text,.pb-text,.msg-text,.bubble,.mx-msg,.cmt-text,.dx-entity,.lc-title,.sp-title,.sc-title,.jc-title,.gcard-title,.gcard-desc,.dl-title,[data-noi18n]';   /* whole blocks people wrote */
  var SKIP_SELF = '.post-name,.sugg-name,.dr-card h3,.hb-card h3,.cp-name,.dr-name,.mg-name,.profile-name,.dx-mine-name';   /* a name's own words stay; badges inside it are translated */
  var ORIG = new WeakMap(), LAST = new WeakMap(), LASTA = new WeakMap(), ATTR = ['placeholder', 'title', 'aria-label'];   /* LAST = what we wrote, so our own output is never translated again */
  window.dxOrigText = function (el) { if (!el) return ''; var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), o = ''; while (w.nextNode()) { var n = w.currentNode; o += ORIG.has(n) ? ORIG.get(n) : n.nodeValue; } return o; };
  function isAr() { return document.documentElement.lang === 'ar'; }
  function walk(root) {
    if (!root || !isAr()) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentElement; return !p || p.closest(SKIP) || p.matches(SKIP_SELF) || !/[A-Za-z]/.test(n.nodeValue) ? 2 : 1; } });
    var list = []; while (w.nextNode()) list.push(w.currentNode);
    list.forEach(function (n) { var v = n.nodeValue; if (LAST.get(n) === v) return;   /* already our translation */
      var t = tr(v); if (t !== v) { ORIG.set(n, v); LAST.set(n, t); n.nodeValue = t; } else if (ORIG.has(n)) { ORIG.delete(n); LAST.delete(n); } });   /* a new value from the app becomes the new original */
    (root.querySelectorAll ? root.querySelectorAll('[placeholder],[title],[aria-label]') : []).forEach(function (el) {
      if (el.closest('[data-noi18n]')) return;
      ATTR.forEach(function (a) { var v = el.getAttribute(a); if (!v || !/[A-Za-z]/.test(v)) return; var m = LASTA.get(el) || {}; if (m[a] === v) return; var t = tr(v); if (t !== v) { el.setAttribute('data-i18n-' + a, v); m[a] = t; LASTA.set(el, m); el.setAttribute(a, t); } });
    });
  }
  function restore() {
    var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); while (w.nextNode()) { var n = w.currentNode; if (ORIG.has(n)) { n.nodeValue = ORIG.get(n); ORIG.delete(n); } } LAST = new WeakMap(); LASTA = new WeakMap();
    ATTR.forEach(function (a) { document.querySelectorAll('[data-i18n-' + a + ']').forEach(function (el) { el.setAttribute(a, el.getAttribute('data-i18n-' + a)); el.removeAttribute('data-i18n-' + a); }); });
  }
  /* new content (dialogs, notices, lists) is translated as it appears */
  var pending = null;
  new MutationObserver(function (muts) {
    if (!isAr()) return;
    muts.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType === 1) (pending = pending || []).push(n); else if (n.nodeType === 3 && n.parentElement) (pending = pending || []).push(n.parentElement); }); if (m.type === 'characterData' && m.target.parentElement) (pending = pending || []).push(m.target.parentElement); });
    if (pending && !walk.__t) walk.__t = requestAnimationFrame(function () { var p = pending; pending = null; walk.__t = 0; p.forEach(function (n) { if (n.isConnected) walk(n); }); });
  }).observe(document.body, { childList: true, subtree: true, characterData: true });
  function setLang(lang) {
    window.LANG = lang;
    document.documentElement.lang = lang; document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    try { localStorage.setItem('dx_lang', lang); } catch (e) {}
    var b = document.getElementById('langBtn'); if (b) b.textContent = lang === 'ar' ? 'English' : 'العربية';
    if (lang === 'ar') walk(document.body); else restore();
  }
  window.toggleLang = function () { setLang(isAr() ? 'en' : 'ar'); if (window.DBK) window.DBK.toast(isAr() ? 'تم التبديل إلى العربية' : 'Switched to English'); };
  window.dxSetLang = setLang;
  C.onRender('i18n', function () { if (isAr()) walk(document.body); });
  var saved = null; try { saved = localStorage.getItem('dx_lang'); } catch (e) {}
  if (saved === 'ar') setLang('ar');
})();
