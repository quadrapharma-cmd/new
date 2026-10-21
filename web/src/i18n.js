/* Arabic interface. Translates the interface (navigation, headings, buttons, labels, filters, placeholders, tooltips, notices)
   — never what people wrote (posts, messages, names, product descriptions). English is restored exactly when switched back. */
(function () {
  var C = window.dxCore; if (!C) return;
  var D = {
    /* navigation & top bar */
    'Home': 'الرئيسية', 'Market': 'السوق', 'Marketplace': 'السوق', 'Network': 'الشبكة', 'My Network': 'شبكتي', 'Messages': 'الرسائل', 'Alerts': 'الإشعارات',
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
    'Create Account →': 'إنشاء الحساب ←', 'Already have an account?': 'لديك حساب بالفعل؟', 'Sign in': 'تسجيل الدخول', 'Full name': 'الاسم الكامل', 'Company': 'الشركة', 'Role': 'المسمى الوظيفي',
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
    'Upgrade Now': 'ترقية الآن', '⭐ Featured Suppliers': '⭐ موردون مميزون', '🟠 Demand Board': '🟠 لوحة الطلبات', 'Submit quotes to open requests': 'قدّم عروضًا للطلبات المفتوحة', 'URGENT': 'عاجل', 'OPEN': 'مفتوح',
    'Need Service': 'مطلوب خدمة', '💼 Latest Jobs': '💼 أحدث الوظائف', 'Free': 'مجاني', 'New': 'جديد', 'Expert': 'خبير', 'Providing': 'يقدّم', 'available': 'متوفر', 'certified': 'معتمد',
    '📦 In stock': '📦 متوفر', '✓ Halal': '✓ حلال', 'Feature': 'الميزة', '🆓 Free': '🆓 مجاني', 'Compare': 'قارن', 'Save': 'حفظ', '🔖 Save': '🔖 حفظ', 'Saved!': 'تم الحفظ!', 'Select': 'اختر',
    /* jobs */
    'CAREERS': 'الوظائف', 'Full-time': 'دوام كامل', 'Part-time': 'دوام جزئي', 'Contract': 'عقد', 'Remote': 'عن بُعد', 'Remote ok': 'عن بُعد متاح', 'Remote possible': 'العمل عن بُعد ممكن',
    'All Jobs': 'كل الوظائف', 'All Levels': 'كل المستويات', 'Employment Type': 'نوع التوظيف', 'Seniority': 'المستوى', 'Apply Now →': 'قدّم الآن ←', 'Hiring': 'نوظّف', 'Looking for a Job': 'يبحث عن عمل',
    'Contact Candidate →': 'تواصل مع المرشح ←', 'Add to whitelist': 'أضف للقائمة البيضاء', 'Whitelist': 'القائمة البيضاء', 'Block (blacklist)': 'حظر (القائمة السوداء)', 'Blacklist': 'القائمة السوداء',
    'Write a public review': 'اكتب تقييمًا علنيًا', 'Write a review': 'اكتب تقييمًا', 'Write a work reference (worked with you)': 'اكتب شهادة عمل (عمل معك)', 'Work reference': 'شهادة عمل',
    'Public rating by candidates': 'تقييم علني من المرشحين', 'Public rating by companies': 'تقييم علني من الشركات', 'No jobs match these filters': 'لا توجد وظائف مطابقة لهذه الفلاتر',
    'Tick more employment types or countries.': 'اختر أنواع توظيف أو دولًا أكثر.', 'Clear filters': 'امسح الفلاتر', 'Junior': 'مبتدئ', 'Mid': 'متوسط', 'Senior': 'متمرّس', 'Intermediate': 'متوسط', 'Beginner': 'مبتدئ',
    /* groups */
    'COMMUNITIES': 'المجتمعات', 'Your Groups': 'مجموعاتك', 'All Groups': 'كل المجموعات', 'Create Group': 'أنشئ مجموعة', 'Create New Group': 'أنشئ مجموعة جديدة', '+ Join': '+ انضم', '✓ Joined': '✓ منضم',
    'DISCUSS': 'نقاش', 'DEAL ROOM': 'غرفة صفقات', 'Private': 'خاصة', 'Public': 'عامة', 'Deal Rooms': 'غرف الصفقات', 'Discussion': 'نقاش', 'Pharma': 'دواء', 'By Country': 'حسب الدولة',
    'What is this group about?': 'ما موضوع هذه المجموعة؟', 'Type the group name to confirm': 'اكتب اسم المجموعة للتأكيد',
    /* messages & notifications */
    '🔍 Search conversations...': '🔍 ابحث في المحادثات...', 'Type a message...': 'اكتب رسالة...', 'sent you a connection request': 'أرسل لك طلب اتصال', 'Accept': 'قبول', 'Decline': 'رفض',
    '+ Connect': '+ تواصل', 'Connect': 'تواصل', 'View profile': 'عرض الملف', 'TODAY': 'اليوم', 'Today': 'اليوم', 'Yesterday': 'أمس',
    /* saved & profile */
    'Saved Posts': 'المنشورات المحفوظة', 'No saved posts yet': 'لا توجد منشورات محفوظة بعد', 'Tap the bookmark icon on any post to save it': 'اضغط على أيقونة الحفظ في أي منشور لحفظه',
    'Activity': 'النشاط', 'About': 'نبذة', 'Experience': 'الخبرة', 'Skills': 'المهارات', 'Certificates': 'الشهادات', 'Edit profile': 'عدّل الملف', 'Message': 'مراسلة',
    /* directory, company page, workspace */
    'COMPANY DIRECTORY': 'دليل الشركات', 'Find any pharma company in Egypt': 'اعثر على أي شركة دواء في مصر', 'Add or claim your company': 'أضف شركتك أو طالب بها', 'How results are ordered': 'كيف تُرتَّب النتائج',
    'Search companies': 'ابحث عن شركات', 'Order': 'الترتيب', 'Best match': 'الأكثر تطابقًا', 'All': 'الكل', 'All companies': 'كل الشركات', 'Manufacturer': 'مصنّع', 'CMO / Toll': 'تصنيع لدى الغير',
    'API & excipients': 'مواد فعالة وسواغات', 'Packaging': 'تعبئة وتغليف', 'Labs & testing': 'معامل وتحاليل', 'Distribution': 'توزيع', 'Regulatory & consulting': 'تسجيل واستشارات',
    'Cosmetics': 'مستحضرات تجميل', 'Supplements': 'مكملات', 'Can manufacture': 'يمكنه تصنيع', 'Governorate': 'المحافظة', 'Certified:': 'حاصل على:', 'Paid placement · does not affect the order below': 'مكان مدفوع · لا يؤثر على الترتيب أدناه',
    'View page': 'عرض الصفحة', 'Request a quote': 'اطلب عرض سعر', 'Your company': 'شركتك', 'Yours': 'لك', 'No track record yet': 'لا يوجد سجل تعاملات بعد', '✓ Verified': '✓ موثّقة',
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
    'Reach 150,000+ pharmacists & scientists across the Gulf & Africa. Get 8× more views.': 'صِل إلى أكثر من 150,000 صيدلي وعالم في الخليج وأفريقيا. واحصل على مشاهدات أكثر 8 مرات.',
    'Expiring in 3 days': 'ينتهي خلال 3 أيام', 'Per country': 'لكل دولة', 'Per dossier': 'لكل ملف', 'Per formula': 'لكل تركيبة', '/day': '/يوم', 'Free consultation · Cairo & online': 'استشارة مجانية · القاهرة وأونلاين',
    'Per product · Free consult': 'لكل منتج · استشارة مجانية', 'HOT': 'رائج', 'Dossier': 'ملف', 'Stability': 'ثبات', 'Audit': 'تدقيق', 'Scale-up': 'تكبير الإنتاج', 'EDA Experience': 'خبرة بهيئة الدواء', 'EDA Certified': 'معتمد من هيئة الدواء',
    'HPLC Expert': 'خبير HPLC', 'registrations': 'تسجيلات', 'New batch.': 'تشغيلة جديدة.', 'accepted.': 'مقبول.', 'DMF filed': 'DMF مودع',
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
    'My connections': 'اتصالاتي', 'Sent requests': 'طلبات مرسلة', 'Search connections': 'ابحث في اتصالاتك', 'Back to My Network': 'العودة إلى شبكتي', 'Remove connection': 'إزالة الاتصال',
    'from your connections? They will not be notified.': 'من اتصالاتك؟ لن يصله أي إشعار.', 'Connection removed': 'تمت إزالة الاتصال', 'No connection matches your search': 'لا يوجد اتصال يطابق بحثك',
    'No connections yet — accept an invitation or connect with people you may know': 'لا توجد اتصالات بعد — اقبل دعوة أو تواصل مع أشخاص قد تعرفهم', 'No suggestions right now': 'لا توجد اقتراحات الآن',
    'Same company': 'نفس الشركة', '✓ Accept': '✓ قبول', 'started following you': 'بدأ متابعتك', 'Dismiss': 'إخفاء', 'Unfollowed': 'تم إلغاء المتابعة', '✓ Following': '✓ تتابعهم', 'Declined': 'تم الرفض', 'Withdraw request': 'اسحب الطلب',
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
    'Sorted by activity — most active first': 'مرتبة حسب النشاط — الأكثر نشاطًا أولًا', 'Reach 150,000+ pharma professionals across the Gulf & Africa': 'صِل إلى أكثر من 150,000 متخصص في الدواء في الخليج وأفريقيا',
    'My Groups': 'مجموعاتي', 'SUPPLY': 'عرض', 'SERVICE': 'خدمة', 'DEMAND': 'طلب', 'LICENSE': 'ترخيص', 'EQUIPMENT': 'معدات', 'TRAINING': 'تدريب', 'Updated quote:': 'عرض محدّث:', 'Online': 'متصل',
    'Deal Rooms — Egypt & GCC': 'غرف الصفقات — مصر والخليج',
    

    'Any': 'أي', 'All governorates': 'كل المحافظات', 'Any certificate': 'أي شهادة', 'Any dosage form': 'أي شكل صيدلي', 'All types': 'كل الأنواع', 'Any time': 'أي وقت', 'Newest': 'الأحدث', 'Most complete': 'الأكثر اكتمالًا',
    'Company, product or ingredient — e.g. ميتفورمين or Metformin': 'شركة أو منتج أو مادة فعالة — مثلًا ميتفورمين أو Metformin', 'Verified first': 'الموثّقة أولًا', 'Track record': 'سجل التعاملات', 'Rating': 'التقييم', 'Name': 'الاسم',
    

    '⭐ Boost your listing — reach 150,000+ pharmacists & scientists across the Gulf & Africa': '⭐ روّج لإعلانك — صِل إلى أكثر من 150,000 صيدلي وعالم في الخليج وأفريقيا',
    'Boost your listing — reach 150,000+ pharmacists & scientists across the Gulf & Africa': 'روّج لإعلانك — صِل إلى أكثر من 150,000 صيدلي وعالم في الخليج وأفريقيا',
    'Sponsored listings get 8× more views and 5× more inquiries than free listings': 'الإعلانات الممولة تحصل على مشاهدات أكثر 8 مرات واستفسارات أكثر 5 مرات من الإعلانات المجانية',
    

    /* deals */
    'Accept quote': 'اقبل العرض', 'Accepted': 'مقبول', 'Applied': 'تم التقديم', 'Closed': 'مغلقة', 'Confirm order': 'أكّد الطلب', 'Confirm received': 'أكّد الاستلام', 'Delivered': 'تم التسليم',
    'Delivery terms': 'شروط التسليم', 'Mark shipped': 'تم الشحن', 'Order confirmed': 'تم تأكيد الطلب', 'Quantity': 'الكمية', 'Quote received': 'وصل العرض', 'Shipped': 'تم الشحن',
    'Timeline': 'التسلسل الزمني', 'Unit': 'الوحدة', 'You are the sender': 'أنت المرسل', 'You are the receiver': 'أنت المستقبل', 'Services one per line': 'الخدمات (عنصر في كل سطر)', 'e.g. Metformin HCl': 'مثلًا Metformin HCl', 'e.g. R1-CEP 20XX-XXX': 'مثلًا R1-CEP 20XX-XXX', 'Send quote': 'أرسل عرضًا',
    /* the other deal actions (they also appear inside notifications: '<company>: <action> — <deal>') */
    'Revise quote': 'عدّل العرض', 'Withdraw': 'اسحب الطلب', 'Rate supplier': 'قيّم هذا المورّد', 'Send proposal': 'أرسل مقترحًا', 'Start work': 'ابدأ العمل', 'Mark delivered': 'سجّل التسليم', 'Accept offer': 'وافق على العرض', 'Accept counter-offer': 'اقبل العرض المضاد', 'Answer questionnaire': 'أجب عن الاستبيان', 'Approve supplier': 'اعتمد المورّد', 'Reject': 'ارفض', 'Sign NDA': 'وقّع اتفاقية السرية', 'Share details': 'شارك التفاصيل', 'Agree terms': 'وافق على الشروط', 'Shortlist': 'أضف للقائمة المختصرة', 'Invite to interview': 'ادعُ لمقابلة', 'Make offer': 'قدّم عرض عمل', 'Accept job offer': 'اقبل عرض العمل', 'Confirm group price': 'أكّد سعر المجموعة', 'Request sent': 'تم إرسال الطلب',
    'Counter-offer': 'عرض مضاد', 'Rate the supplier': 'قيّم المورّد', 'Rated': 'تم التقييم', 'Proposal sent': 'تم إرسال المقترح', 'In progress': 'قيد التنفيذ', 'Offer sent': 'تم إرسال العرض',
    'Simulate their reply (demo)': 'محاكاة ردهم (تجريبي)', 'Open deal': 'افتح الصفقة', 'Waiting for them': 'بانتظارهم',     

    'COMPLIANCE PASSPORT': 'جواز الامتثال', 'VERIFICATION LEVEL': 'مستوى التوثيق', 'Documents & certificates': 'المستندات والشهادات', 'Registered': 'مسجّلة', 'Licensed': 'مرخّصة', 'Inspected': 'مفتَّشة', 'Not verified': 'غير موثّقة',
    'Commercial registry': 'السجل التجاري', 'Tax card': 'البطاقة الضريبية', 'EDA / industrial licence': 'ترخيص الهيئة / الترخيص الصناعي', 'Product documents': 'مستندات المنتجات',     'Verified': 'موثّق', 'Self-declared': 'مُصرَّح به', 'Under review': 'قيد المراجعة', 'Expires soon': 'ينتهي قريبًا', 'Expired': 'منتهي', 'Not provided': 'غير مقدَّم', 'Request': 'اطلب', 'Requested': 'تم الطلب',
    'Add document': 'أضف مستندًا', 'Add a compliance document': 'إضافة مستند امتثال', 'Document': 'المستند', 'Product / site': 'المنتج / الموقع', 'Number / reference': 'الرقم / المرجع', 'Valid to (optional)': 'صالح حتى (اختياري)',
    'Shown as self-declared until Drugbox checks the document.': 'يظهر كمُصرَّح به حتى تراجعه Drugbox.', 'Commercial registry and tax card checked by Drugbox': 'السجل التجاري والبطاقة الضريبية روجعا من Drugbox',
    'EDA or industrial licence on file': 'ترخيص الهيئة أو الترخيص الصناعي مسجّل', 'At least one site with a valid GMP-type certificate': 'موقع واحد على الأقل بشهادة GMP سارية',
    'Top level reached. Keep certificates current to stay here.': 'وصلت لأعلى مستوى. حافظ على سريان الشهادات لتبقى فيه.',

    'Levels: 1 Registered — registry & tax card checked · 2 Licensed — EDA / industrial licence · 3 Inspected — a site with a valid GMP-type certificate. Self-declared documents are shown as provided by the company.': 'المستويات: 1 مسجّلة — روجع السجل التجاري والبطاقة الضريبية · 2 مرخّصة — ترخيص الهيئة / الترخيص الصناعي · 3 مفتَّشة — موقع بشهادة GMP سارية. المستندات المُصرَّح بها تظهر كما قدّمتها الشركة.',

    'Company video': 'فيديو الشركة', 'My video introduction': 'فيديو التعريف بي', 'Video introduction': 'فيديو تعريفي', 'Add a company video': 'أضف فيديو للشركة', 'Add a video introduction': 'أضف فيديو تعريفي',
    'Replace video': 'استبدل الفيديو', 'Video saved': 'تم حفظ الفيديو', 'Video removed': 'تم حذف الفيديو', 'Checking the video…': 'جارٍ فحص الفيديو…', 'Remove this video?': 'حذف هذا الفيديو؟',
    'Show buyers your site, team and quality in a short video (up to 3 minutes).': 'اعرض للمشترين موقعك وفريقك وجودتك في فيديو قصير (حتى 3 دقائق).',
    'Introduce yourself to employers and partners in a short video (up to 90 seconds).': 'عرّف نفسك لأصحاب العمل والشركاء في فيديو قصير (حتى 90 ثانية).',
    'Use an MP4, WebM or MOV video': 'استخدم فيديو MP4 أو WebM أو MOV', 'This video could not be read — try MP4 (H.264)': 'تعذّرت قراءة الفيديو — جرّب MP4 (H.264)',

    'Pay with': 'ادفع بـ', 'Card': 'بطاقة بنكية', 'Vodafone Cash & wallets': 'فودافون كاش والمحافظ', 'Fawry': 'فوري', 'InstaPay': 'إنستاباي',
    'Visa · Mastercard · Meeza': 'فيزا · ماستركارد · ميزة', 'Pay at any Fawry outlet or in the myFawry app': 'ادفع في أي منفذ فوري أو من تطبيق myFawry', 'Transfer, then send us the receipt': 'حوّل ثم أرسل لنا الإيصال',
    'Pay at Fawry': 'الدفع عن طريق فوري', 'Fawry reference number': 'الرقم المرجعي لفوري', 'Pay with InstaPay': 'الدفع بإنستاباي', 'Send to': 'حوّل إلى',
    'Transfer number *': 'رقم التحويل *', 'Receipt (screenshot or PDF)': 'الإيصال (صورة أو PDF)', 'Send for confirmation': 'أرسل للتأكيد', 'Listing to promote': 'الإعلان المراد تمييزه',
    'Opening the secure Paymob page…': 'جارٍ فتح صفحة الدفع الآمنة من Paymob…', 'Thank you — we confirm InstaPay transfers within one working day': 'شكرًا — نؤكد تحويلات إنستاباي خلال يوم عمل',
    'Payment received — it is active now': 'تم استلام الدفع — الاشتراك مفعّل الآن', 'Payments': 'المدفوعات', 'Confirm payment': 'تأكيد الدفع', 'Not received': 'لم يصل',
    'Go to any Fawry outlet, or open myFawry → Pay with reference.': 'اذهب لأي منفذ فوري أو افتح myFawry ← الدفع بالرقم المرجعي.', 'Give the reference number and pay the amount.': 'أعطِ الرقم المرجعي وادفع المبلغ.',
    'It activates automatically once Fawry confirms — we notify you.': 'يتفعّل تلقائيًا بمجرد تأكيد فوري — وسنخطرك.', 'Choose the listing to promote': 'اختر الإعلان المراد تمييزه',
    /* layers, dialogs and pages that had no Arabic yet (October 2026) */
    'Post deleted': 'تم حذف المنشور', 'Notifications cleared': 'تم مسح الإشعارات', 'Saved search deleted': 'تم حذف البحث المحفوظ', 'Listing deleted': 'تم حذف الإعلان', 'Gold partner': 'شريك ذهبي',
    'Silver partner': 'شريك فضي', 'Bronze partner': 'شريك برونزي', 'Drugbox partner levels': 'مستويات شركاء Drugbox',
    '3+ years on Drugbox · 50+ completed deals · rating 4.5 or higher': '3+ سنوات على Drugbox · 50+ صفقة مكتملة · تقييم 4.5 أو أعلى',
    '1+ year on Drugbox · 15+ completed deals · rating 4.2 or higher': 'سنة أو أكثر على Drugbox · 15+ صفقة مكتملة · تقييم 4.2 أو أعلى', 'Verified company · 3+ completed deals': 'شركة موثّقة · 3+ صفقات مكتملة',
    'Levels are earned, never bought: they are based on time on Drugbox, completed deals and users’ own reviews. VIP is a separate paid plan for company pages and is always shown as its own badge.': 'المستويات تُكتسب ولا تُشترى: تعتمد على مدة وجودك على Drugbox والصفقات المكتملة وتقييمات المستخدمين أنفسهم. أما VIP فهي باقة مدفوعة منفصلة لصفحات الشركات وتظهر دائمًا بشارة مستقلة.',
    'Valid': 'سارية', 'Renew this year': 'تُجدَّد هذا العام', 'Good Manufacturing Practice certified against World Health Organization standards.': 'ممارسات التصنيع الجيد معتمدة وفق معايير منظمة الصحة العالمية.',
    'Good Manufacturing Practice — the quality system every pharmaceutical plant must follow.': 'ممارسات التصنيع الجيد — نظام الجودة الذي يلتزم به كل مصنع أدوية.',
    'Certificate of Suitability from EDQM (Europe) proving an API meets the European Pharmacopoeia.': 'شهادة الملاءمة من EDQM (أوروبا) تثبت مطابقة المادة الفعالة لدستور الأدوية الأوروبي.',
    'Drug Master File — confidential file a supplier submits to regulators about how an API is made.': 'الملف الرئيسي للدواء — ملف سري يقدمه المورّد للجهات الرقابية عن طريقة تصنيع المادة الفعالة.',
    'United States Food and Drug Administration.': 'هيئة الغذاء والدواء الأمريكية.', 'European Directorate for the Quality of Medicines, which issues CEPs.': 'المديرية الأوروبية لجودة الأدوية، وهي التي تصدر شهادات CEP.',
    'Certificate of Analysis — the lab results for a specific batch.': 'شهادة التحليل — نتائج المعمل لتشغيلة محددة.', 'Minimum Order Quantity the supplier will accept.': 'الحد الأدنى لكمية الطلب التي يقبلها المورّد.',
    'Free On Board — the seller pays until the goods are loaded on the ship; the buyer pays freight and insurance.': 'التسليم على ظهر السفينة — يتحمل البائع التكاليف حتى تحميل البضاعة على السفينة، ويدفع المشتري الشحن والتأمين.',
    'Cost, Insurance and Freight — the seller pays shipping and insurance to the destination port.': 'التكلفة والتأمين والشحن — يدفع البائع الشحن والتأمين حتى ميناء الوصول.',
    'Ex Works — the buyer collects from the seller’s site and pays all transport.': 'تسليم أرض المصنع — يستلم المشتري من موقع البائع ويدفع كل تكاليف النقل.',
    'Delivered Duty Paid — the seller delivers to your door and pays import duties.': 'التسليم مع دفع الرسوم — يوصّل البائع البضاعة إلى بابك ويدفع رسوم الاستيراد.',
    'Cost and Freight — the seller pays shipping to the port; the buyer insures.': 'التكلفة والشحن — يدفع البائع الشحن حتى الميناء، ويتولى المشتري التأمين.',
    'Common Technical Document — the standard dossier format for registering medicines.': 'الوثيقة الفنية الموحدة — الصيغة القياسية لملفات تسجيل الأدوية.',
    'Egyptian Drug Authority — Egypt’s medicines regulator.': 'هيئة الدواء المصرية — الجهة المنظمة للأدوية في مصر.', 'Saudi Food and Drug Authority.': 'الهيئة العامة للغذاء والدواء السعودية.',
    'Dubai Health Authority.': 'هيئة الصحة بدبي.', 'UAE Ministry of Health and Prevention.': 'وزارة الصحة ووقاية المجتمع الإماراتية.',
    'Egypt’s National Food Safety Authority (supplements and food).': 'الهيئة القومية لسلامة الغذاء في مصر (المكملات والأغذية).',
    'Active Pharmaceutical Ingredient — the substance that makes the medicine work.': 'المادة الفعالة — المادة المسؤولة عن تأثير الدواء.',
    'Contract Manufacturing Organization — makes products for other companies.': 'شركة تصنيع لدى الغير — تصنّع منتجات لصالح شركات أخرى.',
    'Request for Quotation — a formal price request to suppliers.': 'طلب عرض سعر — طلب أسعار رسمي من المورّدين.',
    'High-Performance Liquid Chromatography — the main lab test for purity and assay.': 'كروماتوجرافيا السائل عالية الأداء — الاختبار المعملي الأساسي للنقاوة والمعايرة.',
    'International Council for Harmonisation — global technical guidelines for medicines.': 'المجلس الدولي للتنسيق — إرشادات فنية عالمية للأدوية.',
    'The GMP standard for cosmetics manufacturing.': 'معيار ممارسات التصنيع الجيد لمستحضرات التجميل.', 'Meets both the British and the United States Pharmacopoeia.': 'مطابق لدستوري الأدوية البريطاني والأمريكي.',
    'Toll manufacturing — a plant produces your product under your licence and formula.': 'التصنيع لدى الغير — مصنع ينتج منتجك بترخيصك وتركيبتك.', 'Open Messages to send': 'افتح الرسائل للإرسال',
    'Open chat': 'افتح المحادثة', 'Open full chat': 'افتح المحادثة كاملة', 'Minimize': 'تصغير', 'Write a message…': 'اكتب رسالة…', 'Message sent — see Messages for the reply': 'تم إرسال الرسالة — تابع الرد في الرسائل',
    'Sector:': 'القطاع:', 'Showing:': 'المعروض:', 'Remove filter': 'إزالة الفلتر', 'No listings match all these filters.': 'لا توجد إعلانات تطابق كل هذه الفلاتر.', 'Save this search': 'احفظ هذا البحث',
    'Alert me about new matches': 'نبّهني بالنتائج الجديدة', 'Instantly': 'فورًا', 'Daily': 'يوميًا', 'Weekly': 'أسبوعيًا', 'Off': 'إيقاف',
    'Alerts arrive in Notifications and, in the full version, by email or WhatsApp.': 'تصلك التنبيهات في الإشعارات، وفي النسخة الكاملة بالبريد الإلكتروني أو واتساب.', 'Save search': 'احفظ البحث',
    'Search saved': 'تم حفظ البحث', 'My marketplace filters': 'فلاتري في السوق', 'Delete saved search': 'احذف البحث المحفوظ', 'Saved searches': 'عمليات البحث المحفوظة',
    'New supply that fits your needs': 'عروض جديدة تناسب احتياجاتك', 'Verified suppliers with the grades and certificates you usually ask for.': 'مورّدون موثّقون بالدرجات والشهادات التي تطلبها عادة.',
    'Post a request': 'انشر طلبًا', 'Compare suppliers': 'قارن المورّدين', 'Regulatory updates for you': 'تحديثات تسجيل تهمك',
    'Circulars, checklists and discussions in your markets.': 'منشورات دورية وقوائم مراجعة ونقاشات في أسواقك.', 'Regulatory groups': 'مجموعات التسجيل', 'Regulatory jobs': 'وظائف التسجيل',
    'Jobs that match your profile': 'وظائف تناسب ملفك', 'Based on your skills, experience and preferred locations.': 'حسب مهاراتك وخبرتك والأماكن التي تفضلها.', 'Post my profile': 'انشر ملفي',
    'Improve my profile': 'حسّن ملفي', 'Candidates for your open roles': 'مرشحون لوظائفك المتاحة',
    'Available professionals ranked by fit and by what past employers say.': 'متخصصون متاحون مرتبون حسب الملاءمة وآراء أصحاب العمل السابقين.', 'Top-rated candidates': 'المرشحون الأعلى تقييمًا', 'Tool': 'أداة',
    'Community': 'مجتمع', 'The dossier checklist tool is coming in the regulatory tools batch': 'أداة قائمة مراجعة الملف قادمة ضمن أدوات التسجيل', 'Pages': 'الصفحات', 'Actions': 'إجراءات',
    'Company workspace': 'مساحة عمل الشركة', 'Switch to dark mode': 'التبديل إلى الوضع الداكن', 'Switch to light mode': 'التبديل إلى الوضع الفاتح', 'Larger text': 'نص أكبر',
    'Take the 3-step tour': 'الجولة التعريفية (3 خطوات)', 'Top-rated employers': 'أصحاب العمل الأعلى تقييمًا', 'People & companies': 'أشخاص وشركات', 'Buying requests': 'طلبات شراء', 'Request for quotation': 'طلب عرض سعر',
    'Candidates': 'مرشحون', 'Saved search · alerts': 'بحث محفوظ · تنبيهات', 'move': 'تنقّل', 'open': 'فتح', 'anytime': 'في أي وقت', 'Clear': 'مسح', 'Type': 'النوع', 'Price': 'السعر', 'Supplier': 'المورّد',
    'Lowest price': 'أقل سعر', 'Lowest': 'الأقل',
    'Prices are per the unit each supplier lists. Ask each supplier for a formal quote to compare like for like.': 'الأسعار حسب الوحدة التي يحددها كل مورّد. اطلب عرض سعر رسميًا من كل مورّد لتقارن بشكل عادل.',
    'Compare listings': 'مقارنة الإعلانات', 'You can compare up to 4 listings': 'يمكنك مقارنة 4 إعلانات بحد أقصى', 'On request': 'عند الطلب', 'Listing': 'إعلان', 'Price dropped 8%': 'انخفض السعر 8%',
    'connections': 'اتصالات', 'followers': 'متابعين', 'Hiring now': 'يوظّف الآن', 'Your pages': 'صفحاتك',
    'Every part of Drugbox lives here: your network, messages, the marketplace, jobs and training.': 'كل أقسام Drugbox هنا: شبكتك والرسائل والسوق والوظائف والتدريب.', 'Source and sell': 'اشترِ وبِع',
    'Post supply or demand, send RFQs and compare suppliers side by side in the Marketplace.': 'انشر عرضًا أو طلبًا، وأرسل طلبات عروض الأسعار، وقارن المورّدين جنبًا إلى جنب في السوق.', 'Make it yours': 'اجعله على ذوقك',
    'Complete your profile to be found by buyers and employers, and switch to dark mode or the Ramadan theme here.': 'أكمل ملفك ليجدك المشترون وأصحاب العمل، ومن هنا يمكنك التبديل إلى الوضع الداكن أو مظهر رمضان.',
    'Skip': 'تخطَّ', 'Done': 'تم', 'You are all set — welcome to Drugbox': 'كل شيء جاهز — أهلًا بك في Drugbox', 'Light': 'فاتح', 'Dark': 'داكن', 'Text size': 'حجم النص', 'Normal': 'عادي', 'Large': 'كبير', 'Larger': 'أكبر',
    'Season': 'المناسبة', 'Standard': 'افتراضي', 'Ramadan': 'رمضان', 'Eid': 'العيد', 'RAMADAN KAREEM': 'رمضان كريم', 'Ramadan Kareem from everyone at Drugbox': 'رمضان كريم من كل فريق Drugbox',
    'Profiles show Ramadan working hours — plan calls and deliveries around them.': 'الملفات تعرض مواعيد العمل في رمضان — رتّب المكالمات والتسليمات على أساسها.', 'EID MUBARAK': 'عيد مبارك',
    'Eid Mubarak from everyone at Drugbox': 'عيد مبارك من كل فريق Drugbox',
    'Wishing you and your teams a blessed Eid. Many offices close for the holiday — expect slower replies.': 'نتمنى لك ولفريقك عيدًا مباركًا. كثير من المكاتب تغلق في العطلة — توقّع ردودًا أبطأ.', 'Phone:': 'الهاتف:',
    'Open a conversation first': 'افتح محادثة أولًا', 'Profile photo updated': 'تم تحديث صورة الملف', 'Chemical structure': 'التركيب الكيميائي', 'FORMULA': 'الصيغة', 'MOLECULAR WEIGHT': 'الوزن الجزيئي', 'CLASS': 'الفئة',
    'Free base shown. Structure and values generated with RDKit from the published structure.': 'معروضة في صورة القاعدة الحرة. التركيب والقيم مولّدة بواسطة RDKit من التركيب المنشور.', 'Biguanide': 'بيجوانيد',
    'usually supplied as HCl salt': 'يُورَّد عادةً كملح HCl', 'Fluoroquinolone': 'فلوروكينولون', 'often supplied as HCl': 'يُورَّد غالبًا كـ HCl', 'Vitamin A': 'فيتامين أ', 'cosmetic active': 'مادة فعالة تجميلية',
    'Analgesic / antipyretic': 'مسكن / خافض للحرارة', 'Third-generation cephalosporin': 'سيفالوسبورين من الجيل الثالث', 'DPP-4 inhibitor': 'مثبط DPP-4', 'Secosteroid vitamin': 'فيتامين سيكوستيرويدي',
    'Aminopenicillin': 'أمينوبنسلين', 'Proton-pump inhibitor': 'مثبط مضخة البروتون', 'NSAID': 'مضاد التهاب غير ستيرويدي', 'Landed cost': 'التكلفة الواصلة', 'Choose a video file': 'اختر ملف فيديو',
    'The video could not be saved': 'تعذّر حفظ الفيديو', 'This video is no longer available': 'هذا الفيديو لم يعد متاحًا', 'This video could not be played': 'تعذّر تشغيل هذا الفيديو', 'Video': 'فيديو',
    'You haven’t posted yet — share an update, a product or a job with your network.': 'لم تنشر شيئًا بعد — شارك تحديثًا أو منتجًا أو وظيفة مع شبكتك.', 'Edit': 'تعديل', 'Share card': 'بطاقة مشاركة', '+ Follow': '+ متابعة',
    'Follow': 'متابعة', 'Questionnaire': 'استبيان', 'verified': 'موثّق', 'Certificate': 'شهادة', 'Phone': 'الهاتف', 'Website': 'الموقع الإلكتروني',
    'No listings here match your filters.': 'لا توجد إعلانات هنا تطابق الفلاتر.', 'Reset filters': 'إعادة ضبط الفلاتر', 'Send for verification': 'أرسل للتوثيق', 'Edit your company page': 'عدّل صفحة شركتك',
    'Edit company page': 'تعديل صفحة الشركة', 'Branding': 'الهوية', 'Upload logo': 'ارفع الشعار', 'Upload cover photo': 'ارفع صورة الغلاف', 'Brand colour': 'لون الهوية', 'Tagline': 'الشعار النصي', 'Description': 'الوصف',
    'Founded': 'سنة التأسيس', 'Team size': 'حجم الفريق', 'Add a product': 'أضف منتجًا', 'verified by Drugbox before they show': 'يوثّقها Drugbox قبل ظهورها', 'one per line': 'عنصر في كل سطر',
    'WhatsApp (digits)': 'واتساب (أرقام فقط)', 'Address': 'العنوان', 'Working hours': 'مواعيد العمل', 'Save and publish': 'احفظ وانشر', 'Request details': 'اطلب التفاصيل', 'now': 'الآن',
    'No reviews yet.': 'لا توجد تقييمات بعد.', 'Remove site': 'احذف الموقع', 'Verification — free, always': 'التوثيق — مجاني دائمًا',
    '✓ Verified: commercial registry and tax card checked.': '✓ موثّقة: تم التحقق من السجل التجاري والبطاقة الضريبية.', 'Verification and your track record can never be bought.': 'التوثيق وسجل تعاملاتك لا يُشتريان أبدًا.',
    'Sponsored placement (VIP)': 'ظهور مُموَّل (VIP)', 'Your company appears in the Sponsored row of the directory.': 'تظهر شركتك في صف الشركات المُموَّلة في الدليل.', 'Minimum batch': 'أقل تشغيلة',
    'Capacity': 'الطاقة الإنتاجية', 'Free production slots': 'فترات إنتاج متاحة', 'Free production slots — tap to change': 'فترات إنتاج متاحة — اضغط للتغيير', 'Live listings': 'إعلانات نشطة',
    'Time-limited offers in the Marketplace. The permanent catalogue is under Products.': 'عروض لفترة محدودة في السوق. الكتالوج الدائم موجود في المنتجات.', 'Open positions': 'وظائف متاحة',
    'Reviews from completed orders': 'تقييمات من طلبات مكتملة',
    'Only buyers who received an order can review. The company can reply or ask Drugbox to check a review.': 'يقيّم فقط المشترون الذين استلموا طلبًا. ويمكن للشركة الرد أو طلب مراجعة التقييم من Drugbox.',
    'Message on WhatsApp': 'راسل على واتساب', 'Address · directions': 'العنوان · الاتجاهات', 'Who answers': 'من يرد', 'nobody on Drugbox yet': 'لا أحد على Drugbox بعد', 'use the Contact tab': 'استخدم تبويب التواصل', 'Team member': 'عضو في الفريق', 'Quote requests go to': 'طلبات عروض الأسعار تذهب إلى', 'Send a message': 'أرسل رسالة',
    'Public page': 'الصفحة العامة', 'Logo, cover, about, products, services and contact.': 'الشعار والغلاف والنبذة والمنتجات والخدمات وبيانات التواصل.', 'Edit page': 'عدّل الصفحة',
    'View as visitors see it': 'اعرضها كما يراها الزوار', 'Arabic name': 'الاسم بالعربية', 'What we are looking for': 'ما نبحث عنه', 'Memberships': 'العضويات', 'Add membership': 'أضف عضوية',
    'Add manufacturing capabilities': 'أضف قدرات تصنيع', 'Edit capabilities': 'عدّل القدرات', 'Add a site': 'أضف موقعًا',
    'Roles decide who receives each kind of request. A person appears on the public page only after they agree (personal data law 151/2020).': 'الأدوار تحدد من يستلم كل نوع من الطلبات. لا يظهر الشخص في الصفحة العامة إلا بعد موافقته (قانون حماية البيانات الشخصية 151/2020).',
    'Hide me': 'أخفني', 'Waiting for their agreement — not shown publicly': 'بانتظار موافقته — لا يظهر للعامة', 'Invite a colleague': 'ادعُ زميلًا', 'Who receives what': 'من يستلم ماذا',
    'Nothing sent yet.': 'لم يُرسل شيء بعد.', 'No suppliers on the list yet.': 'لا يوجد مورّدون في القائمة بعد.', 'Your Marketplace listings': 'إعلاناتك في السوق', 'Post surplus stock': 'انشر مخزونًا فائضًا',
    'List a dossier for licensing': 'اعرض ملفًا للترخيص', 'Reports of wrong information': 'بلاغات عن معلومات خاطئة', 'No reports.': 'لا توجد بلاغات.', 'Activity log': 'سجل النشاط',
    'Who in your team did what.': 'من فعل ماذا في فريقك.', 'No activity yet.': 'لا يوجد نشاط بعد.', 'Supplier status: not on list': 'حالة المورّد: غير مدرج', 'Approved': 'معتمد', 'Under evaluation': 'قيد التقييم',
    'Suspended': 'موقوف', 'Choose…': 'اختر…', 'Name A–Z': 'الاسم أ–ي', 'Something else': 'شيء آخر', 'units': 'وحدات', 'cartons': 'كراتين', 'tablets': 'أقراص', 'batches': 'تشغيلات', 'pcs': 'قطعة', 'Tablets': 'أقراص',
    'Capsules': 'كبسولات', 'Sachets': 'أكياس', 'Syrups': 'شراب', 'Effervescent tablets': 'أقراص فوارة', 'Sterile injectables': 'حقن معقمة', 'Eye drops': 'قطرات عين', 'Creams': 'كريمات', 'Serums': 'سيرومات', 'Gels': 'جل',
    'Shampoos': 'شامبو', 'Sharqia': 'الشرقية', 'Qalyubia': 'القليوبية', 'Ismailia': 'الإسماعيلية', 'CIF — freight & insurance included': 'CIF — شامل الشحن والتأمين',
    'FOB — add freight & insurance': 'FOB — أضف الشحن والتأمين', 'Stability data (Zone IVb)': 'بيانات الثبات (المنطقة IVb)', 'GDP certificate': 'شهادة GDP', 'Requesting as': 'تطلب باسم', 'Goes to': 'يذهب إلى',
    'Quantity *': 'الكمية *', 'Deliver to *': 'التسليم إلى *', 'Needed by': 'مطلوب بحلول', 'Message *': 'الرسالة *', 'Send request': 'أرسل الطلب', 'City, country': 'المدينة، الدولة',
    'Specs, grade, certificates you need, payment terms…': 'المواصفات والدرجة والشهادات المطلوبة وشروط الدفع…', 'Claimed': 'تمت المطالبة بها', 'Pages ≥80% complete': 'صفحات مكتملة ≥80%',
    'Average completeness': 'متوسط الاكتمال', 'Requests answered': 'الطلبات المُجاب عنها', 'Dormant (60+ days)': 'خاملة (60+ يومًا)', 'Pages with outdated info': 'صفحات بمعلومات قديمة', 'Open reports': 'بلاغات مفتوحة',
    'Reviews under check': 'تقييمات قيد المراجعة', 'Outdated pages': 'صفحات قديمة', 'Basic': 'أساسي', 'Company page in the directory': 'صفحة الشركة في الدليل', 'Unlimited products and photos': 'منتجات وصور بلا حدود',
    'Cover photo and full branding': 'صورة غلاف وهوية كاملة', 'Quote, service and job requests': 'طلبات عروض الأسعار والخدمات والتوظيف', 'Page views and requests analytics': 'تحليلات مشاهدات الصفحة والطلبات',
    'Team seats for sales and HR': 'مقاعد للفريق في المبيعات والموارد البشرية', 'Recommended': 'موصى بها', '/month': '/شهريًا', 'Everything in Basic': 'كل مزايا الأساسية', 'VIP badge': 'شارة VIP',
    'Top of the directory (marked Sponsored)': 'أعلى الدليل (بعلامة مُموَّل)', 'Your own link: company.drugbox.app': 'رابط خاص بك: company.drugbox.app', 'Verification within 48 hours': 'توثيق خلال 48 ساعة',
    '3 Marketplace boosts every month': '3 ترويجات في السوق كل شهر', 'Monthly': 'شهري', 'Yearly': 'سنوي', 'Example prices in EGP — set by Drugbox.': 'أسعار توضيحية بالجنيه المصري — يحددها Drugbox.',
    'Next: company details': 'التالي: بيانات الشركة', 'Commercial registry number *': 'رقم السجل التجاري *', 'Registry document *': 'مستند السجل التجاري *', 'Tax card *': 'البطاقة الضريبية *',
    'Licence (EDA, pharmacy, distribution or industrial)': 'الترخيص (هيئة الدواء، صيدلية، توزيع أو صناعي)', 'Needed to buy or sell medicines on Drugbox.': 'مطلوب لشراء الأدوية أو بيعها على Drugbox.',
    'Download QR (SVG)': 'تنزيل رمز QR (SVG)', 'Trade-show mode': 'وضع المعارض', 'Exit trade-show mode': 'الخروج من وضع المعارض',
    'Print it on business cards, exhibition stands, cartons or trucks — it opens your company page.': 'اطبعه على الكروت الشخصية وأجنحة المعارض والكراتين والسيارات — يفتح صفحة شركتك.', 'Where': 'أين',
    'What is wrong? *': 'ما الخطأ؟ *', 'Correct information (if you know it)': 'المعلومة الصحيحة (إن كنت تعرفها)', 'Send report': 'أرسل البلاغ',
    'Unused raw materials, packaging and near-expiry stock at a discount — turn frozen stock into cash.': 'خامات ومواد تعبئة غير مستخدمة ومخزون قريب الانتهاء بخصم — حوّل المخزون الراكد إلى سيولة.',
    'Dossiers for licensing': 'ملفات للترخيص',
    'Registered products and CTD dossiers companies will license, sell or co-market. Details are shared after a confidentiality agreement.': 'منتجات مسجلة وملفات CTD تعرضها الشركات للترخيص أو البيع أو التسويق المشترك. تُشارك التفاصيل بعد اتفاقية سرية.',
    'Sell dossier': 'بيع الملف', 'Co-marketing': 'تسويق مشترك', 'License out': 'ترخيص للغير', 'Product *': 'المنتج *', 'Supplier *': 'المورّد *', 'Target quantity *': 'الكمية المستهدفة *', 'Your share *': 'حصتك *',
    'Target price': 'السعر المستهدف', 'Start group': 'ابدأ المجموعة', 'Start a buying group': 'ابدأ مجموعة شراء', 'Landed cost calculator': 'حاسبة التكلفة الواصلة', 'Price per unit (US$)': 'سعر الوحدة (دولار)',
    'Incoterm': 'شرط التسليم (Incoterm)', 'Exchange rate (EGP per US$)': 'سعر الصرف (جنيه لكل دولار)', 'Customs duty (%)': 'الرسوم الجمركية (%)', 'VAT (%)': 'ضريبة القيمة المضافة (%)',
    'Bank / LC fees (%)': 'مصاريف البنك / الاعتماد المستندي (%)', 'Clearance & port (EGP)': 'التخليص والميناء (جنيه)', 'Inland transport (EGP)': 'النقل الداخلي (جنيه)', 'Customs value (CIF)': 'القيمة الجمركية (CIF)',
    'Customs duty': 'الرسوم الجمركية', 'VAT': 'ضريبة القيمة المضافة', 'Bank / LC fees': 'مصاريف البنك / الاعتماد المستندي', 'Clearance & port': 'التخليص والميناء', 'Inland transport': 'النقل الداخلي',
    'An estimate to compare offers. Duty depends on the HS code and exemptions — confirm with your customs broker. Enter today’s exchange rate.': 'تقدير للمقارنة بين العروض. الرسوم تعتمد على البند الجمركي (HS) والإعفاءات — تأكد من مستخلصك الجمركي. أدخل سعر الصرف اليوم.',
    'Compare quotes': 'قارن العروض', 'Terms': 'الشروط', 'Supplier rating': 'تقييم المورّد', 'Status': 'الحالة', 'Act as': 'التصرف باسم', 'Manage my companies': 'إدارة شركاتي', '🚪 Leave Group': '🚪 غادر المجموعة',
    'members': 'عضو', 'Download image': 'تنزيل الصورة', 'Copy caption': 'نسخ النص', 'Caption': 'النص', 'Exit ✕': 'خروج ✕', 'Scan to see our page, certificates and products': 'امسح الرمز لترى صفحتنا وشهاداتنا ومنتجاتنا',
    '1200 × 630 — the size WhatsApp and LinkedIn show in full. For LinkedIn, download the image and paste the caption.': '1200 × 630 — المقاس الذي يعرضه واتساب ولينكدإن كاملًا. للينكدإن: نزّل الصورة والصق النص.',
    'Contact & Details': 'التواصل والتفاصيل', 'Languages': 'اللغات', 'Licenses & Certifications': 'التراخيص والشهادات', 'Open to work': 'متاح للعمل', 'OPEN TO WORK': 'متاح للعمل', 'Enter a web address like example.com': 'اكتب عنوان موقع مثل example.com',
    'An account with this email already exists — sign in instead': 'يوجد حساب بهذا البريد الإلكتروني — سجّل الدخول بدلًا من ذلك', 'Profile saved! ✅': 'تم حفظ الملف ✅',
    'Edit Profile': 'تعديل الملف', 'Headline': 'العنوان المهني', 'Bio': 'نبذة', 'Save Changes': 'حفظ التغييرات', 'No notifications': 'لا توجد إشعارات', 'New message': 'رسالة جديدة', 'Attach file': 'إرفاق ملف',
    'Attach photo': 'إرفاق صورة', 'This conversation is about this listing': 'هذه المحادثة بخصوص هذا الإعلان',
    /* Messages: the conversation menu, block / report, ✎ New message (S-03, J-SOCIAL-40) */
    'Mute Notifications': 'كتم الإشعارات', 'Unmute Notifications': 'إلغاء الكتم', 'Pin Conversation': 'تثبيت المحادثة', 'Save to Favorites': 'حفظ في المفضلة',
    'Clear Chat History': 'مسح سجل المحادثة', 'Report Conversation': 'الإبلاغ عن المحادثة', 'Report conversation': 'الإبلاغ عن المحادثة', 'Block': 'حظر',
    'You blocked this contact': 'لقد حظرت هذا الشخص', 'Report sent — our team reviews it within 24 h': 'تم إرسال البلاغ — يراجعه فريقنا خلال 24 ساعة',
    'Spam or scam': 'رسائل مزعجة أو احتيال', 'Counterfeit / unlicensed product': 'منتج مقلّد / غير مرخّص', 'Harassment': 'مضايقة أو إساءة', 'Conversation pinned': 'تم تثبيت المحادثة',
    'They won\u2019t be able to message you, and you won\u2019t be able to message them. You can unblock them later from this menu.': 'لن يستطيع مراسلتك ولن تستطيع مراسلته. يمكنك إلغاء الحظر لاحقًا من هذه القائمة.',
    "They won't be able to message you, and you won't be able to message them. You can unblock them later from this menu.": 'لن يستطيع مراسلتك ولن تستطيع مراسلته. يمكنك إلغاء الحظر لاحقًا من هذه القائمة.',
    'Message reports': 'بلاغات الرسائل', 'Action taken': 'تم اتخاذ إجراء', 'Dismiss': 'تجاهل', 'Dismiss this report?': 'تجاهل هذا البلاغ؟',
    'Nothing changes for the reported member.': 'لن يتغير شيء بالنسبة للعضو المُبلَّغ عنه.', 'Name of a person or company': 'اسم شخص أو شركة', 'Write your message…': 'اكتب رسالتك…',
    'Notifications muted': 'الإشعارات مكتومة', 'Choose a conversation': 'اختر محادثة', 'No conversations or messages match': 'لا توجد محادثات أو رسائل مطابقة', 'Choose a photo (JPG, PNG, WebP or GIF)': 'اختر صورة (JPG أو PNG أو WebP أو GIF)',
    'This file type can\'t be sent — use PDF, Word, Excel, ZIP or an image': 'لا يمكن إرسال هذا النوع من الملفات — استخدم PDF أو Word أو Excel أو ZIP أو صورة', 'Files can be up to 20 MB': 'الحد الأقصى لحجم الملف 20 ميجابايت', 'Could not send the report — please try again': 'تعذّر إرسال البلاغ — حاول مرة أخرى', 'Could not save — please try again': 'تعذّر الحفظ — حاول مرة أخرى',
    'Knowledge communities & deal-rooms for pharma, cosmetics & device professionals': 'مجتمعات معرفة وغرف صفقات لمتخصصي الدواء والتجميل والأجهزة الطبية',
    'Matched to your listings and connections — not just popularity': 'مختارة حسب إعلاناتك واتصالاتك — لا حسب الشهرة فقط',
    'Groups where suppliers and buyers actively trade — not just talk': 'مجموعات يتاجر فيها المورّدون والمشترون فعلًا — لا مجرد كلام', 'Learn from people who’ve done it.': 'تعلّم من أهل الخبرة.',
    'Learn from people who\'ve done it.': 'تعلّم من أهل الخبرة.', 'GMP, regulatory and formulation — taught by practitioners.': 'التصنيع الجيد والتسجيل والتركيبات — يقدمها ممارسون.',
    'Pharmaceutical regulatory and manufacturing courses': 'دورات في التسجيل والتصنيع الدوائي', 'Enroll Now': 'سجّل الآن', 'Advanced': 'متقدم', 'Admin Panel': 'لوحة الإدارة', '🛡️ Review': '🛡️ المراجعة',
    '📊 Dashboard': '📊 لوحة المعلومات', '🎨 Design': '🎨 التصميم', '📢 Ticker': '📢 الشريط الإخباري', '🏭 Sponsors': '🏭 الرعاة', '👥 Users': '👥 المستخدمون', '💬 Market Board': '💬 لوحة السوق', '⚙️ Settings': '⚙️ الإعدادات',
    '← Back to Site': '→ العودة للموقع', 'Dashboard': 'لوحة المعلومات', 'Welcome back — here\'s what\'s happening on Drugbox': 'أهلًا بعودتك — هذا ما يحدث على Drugbox', 'Total Users': 'إجمالي المستخدمين',
    'Total Posts': 'إجمالي المنشورات', 'Enquiries': 'الاستفسارات', '👥 Latest Members': '👥 أحدث الأعضاء',
    'Join Drugbox': 'انضم إلى Drugbox', '12,000+ pharma professionals are waiting': 'أكثر من 12,000 متخصص في الدواء في انتظارك', 'Full Name *': 'الاسم الكامل *', 'Email *': 'البريد الإلكتروني *', 'Password *': 'كلمة المرور *',
    'Connect with manufacturers, suppliers & regulatory experts across Egypt, the GCC and beyond.': 'تواصل مع المصنّعين والمورّدين وخبراء التسجيل في مصر والخليج وخارجهما.',
    'Regulatory Affairs': 'الشؤون التنظيمية', 'Quality Control / QA': 'مراقبة الجودة / ضمان الجودة', 'Sales & Business Dev': 'المبيعات وتطوير الأعمال', 'CEO / Management': 'الإدارة العليا',
    'Next': 'التالي', 'new posts today': 'منشورات جديدة اليوم', 'Surplus stock': 'مخزون فائض', 'Delete': 'حذف', 'WhatsApp': 'واتساب',
    'Checked by Drugbox within 48 hours (VIP). Never shown to other users. Your page stays live meanwhile.': 'يراجعها Drugbox خلال 48 ساعة (VIP). لا تظهر لأي مستخدم آخر، وتبقى صفحتك منشورة في أثناء ذلك.',
    'Checked by Drugbox within 2 working days. Never shown to other users. Your page stays live meanwhile.': 'يراجعها Drugbox خلال يومي عمل. لا تظهر لأي مستخدم آخر، وتبقى صفحتك منشورة في أثناء ذلك.',
    /* notices */
    /* groups: create and invite (N-9) */
    'Invite': 'ادعُ', 'Invite people': 'ادعُ أشخاصًا', 'Emails or names *': 'البريد الإلكتروني أو الأسماء *', 'Personal note': 'ملاحظة شخصية', 'Optional': 'اختياري', 'Send invites': 'أرسل الدعوات',
    'one per line or separated by commas': 'واحد في كل سطر أو مفصولة بفواصل', 'Group created': 'تم إنشاء المجموعة', 'Group created! 👥': 'تم إنشاء المجموعة! 👥',
    'Group created — invite your first members': 'تم إنشاء المجموعة — ادعُ أول أعضائها', 'Give your group a name': 'اكتب اسمًا لمجموعتك', 'Add the group name': 'اكتب اسم المجموعة',
    'Invite someone other than yourself': 'ادعُ شخصًا غيرك',
    'Create a Group': 'أنشئ مجموعة', 'Group name': 'اسم المجموعة', 'Group type': 'نوع المجموعة', 'Privacy': 'الخصوصية', 'Manage Group': 'إدارة المجموعة', 'DISCUSSION': 'نقاش', 'NEW': 'جديد',
    'Buy/sell, RFQs & quotes': 'بيع وشراء وطلبات وعروض أسعار', 'Knowledge sharing, Q&A': 'تبادل المعرفة وأسئلة وأجوبة', 'e.g. Sterile Manufacturing Egypt': 'مثال: التصنيع المعقم في مصر',
    'Anyone can find, view, and join': 'يمكن لأي شخص أن يجدها ويطّلع عليها وينضم إليها', 'Members must be approved or invited': 'العضوية بالموافقة أو بالدعوة',
    'Created just now': 'أُنشئت الآن', 'you are the admin': 'أنت المدير',
    /* form checks (sign in, sign up, posts, listings, groups) */
    'Email is required': 'البريد الإلكتروني مطلوب', 'Password is required': 'كلمة المرور مطلوبة', 'Name is required': 'الاسم مطلوب',
    /* the name rule (live: sign-up, Edit Profile, the database's refusal — 0038) */
    'A name cannot contain numbers': 'لا يمكن أن يحتوي الاسم على أرقام', 'A name can be up to 120 characters': 'الاسم 120 حرفًا على الأكثر',
    'An accent or vowel mark must sit on a letter, once (at most 3 marks on one letter)': 'علامة التشكيل أو النبرة يجب أن تكون على حرف، مرة واحدة (3 علامات على الأكثر للحرف الواحد)',
    "This name cannot be used — a name can only have letters, spaces and . - ' ( ) , / ،": "لا يمكن استخدام هذا الاسم — الاسم يقبل الحروف والمسافات و \u2066. - ' ( ) , /\u2069 ، فقط",
    'Please update your name — it has characters Drugbox no longer allows, so other members see a warning next to it.': 'من فضلك عدّل اسمك — فيه حروف لم يعد Drugbox يسمح بها، لذلك يرى الأعضاء الآخرون تحذيرًا بجانبه.',
    'Update my name': 'عدّل اسمي',
    'Password must be at least 8 characters': 'كلمة المرور يجب ألا تقل عن 8 أحرف', 'Title is required': 'العنوان مطلوب', 'Title required': 'العنوان مطلوب',
    'Details are required': 'التفاصيل مطلوبة', 'Product name required': 'اسم المنتج مطلوب', 'Product name is required': 'اسم المنتج مطلوب',
    'Group name required': 'اسم المجموعة مطلوب', 'Group name is required': 'اسم المجموعة مطلوب',
    'Please write at least 20 characters': 'اكتب 20 حرفًا على الأقل', 'Please write at least 40 characters of facts': 'اكتب 40 حرفًا على الأقل من الوقائع',
    'Welcome back, Haytham!': 'أهلًا بعودتك يا هيثم!', 'Post shared': 'تم نشر المنشور', 'Copied': 'تم النسخ', 'Deleted': 'تم الحذف', 'Undo': 'تراجع',
    'Discard your changes?': 'تجاهل تعديلاتك؟', 'Your edits to this page are not saved yet.': 'تعديلاتك على هذه الصفحة لم تُحفظ بعد.', 'Keep editing': 'متابعة التعديل', 'Discard changes': 'تجاهل التعديلات', 'Main navigation': 'التنقل الرئيسي',
    /* groups — the inside of a group (groups.js): tabs, members, about, listings, dialogs and notices */
    'Members': 'الأعضاء', 'Member': 'عضو', 'Sub-Admin': 'مشرف', 'You': 'أنت', 'Connected': 'متصل', 'Search members': 'ابحث في الأعضاء', 'Group sections': 'أقسام المجموعة', 'Member options': 'خيارات العضو',
    'Created the group': 'أنشأ المجموعة', 'Joined just now': 'انضم الآن', 'No member matches your search.': 'لا يوجد عضو يطابق بحثك.',
    '🔒 The full member list is visible to members only.': '🔒 قائمة الأعضاء الكاملة متاحة للأعضاء فقط.', 'About this group': 'عن هذه المجموعة', 'Created': 'تاريخ الإنشاء',
    'Markets': 'الأسواق', 'Topics': 'الموضوعات', 'Group rules': 'قواعد المجموعة', 'Admins': 'المديرون', 'by': 'بواسطة', 'No rules yet.': 'لا توجد قواعد بعد.',
    'Join Group': 'انضم إلى المجموعة', 'Request to join': 'اطلب الانضمام', 'Accept invitation': 'اقبل الدعوة', '🔒 Request': '🔒 اطلب الانضمام',
    '⏳ Requested': '⏳ تم الطلب', '✉️ Accept': '✉️ اقبل الدعوة', 'Invitation from': 'دعوة من', 'Invitation only': 'بالدعوة فقط',
    '👀 You’re viewing a preview. Join to post, comment and react.': '👀 أنت تشاهد معاينة. انضم لتنشر وتعلّق وتتفاعل.', '🔒 This is a private group': '🔒 هذه مجموعة خاصة',
    '✉️ You’re invited to this private group': '✉️ أنت مدعو إلى هذه المجموعة الخاصة', 'Accept the invitation to see the discussions, members and listings.': 'اقبل الدعوة لترى النقاشات والأعضاء والإعلانات.',
    'Your request was sent. An admin will review it — you’ll get a notification.': 'تم إرسال طلبك. سيراجعه أحد المديرين — وسيصلك إشعار.',
    'Only members can see the discussions, members and listings. Ask to join and an admin will review your request.': 'النقاشات والأعضاء والإعلانات متاحة للأعضاء فقط. اطلب الانضمام وسيراجع أحد المديرين طلبك.',
    'Loading posts…': 'جارٍ تحميل المنشورات…', 'Group discussions open here soon.': 'نقاشات المجموعة ستُفتح هنا قريبًا.', 'No posts yet': 'لا توجد منشورات بعد',
    'Start the first discussion in this group.': 'ابدأ أول نقاش في هذه المجموعة.', 'Join to start the first discussion.': 'انضم لتبدأ أول نقاش.', 'Pin to top': 'ثبّت في الأعلى', 'Unpin': 'ألغِ التثبيت',
    'Remove post': 'أزل المنشور', 'edited': 'معدّل', 'The photo was too large to keep in this browser.': 'الصورة أكبر من أن تُحفظ في هذا المتصفح.',
    'Requests & offers': 'الطلبات والعروض', 'Only members of this deal room see these and can answer.': 'لا يراها ولا يرد عليها إلا أعضاء غرفة الصفقات هذه.', 'Post RFQ / offer': 'انشر طلب شراء / عرضًا',
    'Loading listings…': 'جارٍ تحميل الإعلانات…', 'No requests or offers yet': 'لا توجد طلبات أو عروض بعد', 'Post the first RFQ or offer for this group.': 'انشر أول طلب شراء أو عرض في هذه المجموعة.',
    'Join to post the first request.': 'انضم لتنشر أول طلب.', 'Offers & surplus': 'العروض والفائض', 'Your request': 'طلبك', 'Your offer': 'عرضك', 'Surplus': 'فائض', 'Quoted': 'تم إرسال العرض',
    'No pending reports': 'لا توجد بلاغات معلّقة', 'Post by': 'منشور من', 'Dismiss report': 'تجاهل البلاغ', 'Remove post & warn user': 'أزل المنشور وحذّر العضو', 'Remove from group': 'أزل من المجموعة',
    'Members & Roles': 'الأعضاء والأدوار', 'Reports': 'البلاغات', 'Promote to Admin': 'ترقية إلى مدير', 'Promote to Sub-Admin': 'ترقية إلى مشرف', 'Demote to Member': 'إرجاع إلى عضو',
    'Leave this group?': 'مغادرة هذه المجموعة؟', 'Leave': 'غادر', 'Leave group?': 'مغادرة المجموعة؟', 'You will stop seeing posts from': 'لن ترى بعد الآن منشورات',
    'Share this post': 'شارك هذا المنشور', 'Repost to your feed': 'أعد النشر في صفحتك الرئيسية', 'Your connections see it on Home, with a link to this group.': 'يراه المتصلون بك في الرئيسية، مع رابط لهذه المجموعة.',
    '🔒 Posts in a private group can’t be reposted outside it.': '🔒 لا يمكن إعادة نشر منشورات مجموعة خاصة خارجها.', 'Copy link': 'انسخ الرابط',
    'Only members of the group can open it.': 'لا يفتحه إلا أعضاء المجموعة.', 'Anyone on Drugbox can open it.': 'يستطيع أي شخص على Drugbox فتحه.',
    'Report this post': 'أبلغ عن هذا المنشور', 'The group admins review reports. The author is not told who reported.': 'يراجع مديرو المجموعة البلاغات، ولا يُبلَّغ الكاتب بهوية المُبلِّغ.',
    'Spam or unrelated ad': 'محتوى مزعج أو إعلان لا علاقة له', 'Unverified or counterfeit product': 'منتج غير موثّق أو مغشوش', 'Misleading information': 'معلومات مضللة',
    'Harassment or hate': 'تحرش أو خطاب كراهية', 'Breaks the group rules': 'مخالف لقواعد المجموعة', 'Details (optional)': 'التفاصيل (اختياري)', 'What should the admins know?': 'ما الذي يجب أن يعرفه المديرون؟',
    'Edit post': 'تعديل المنشور', 'Your post *': 'منشورك *', 'Remove this post?': 'إزالة هذا المنشور؟',
    'It breaks the group rules and will be removed for everyone.': 'المنشور يخالف قواعد المجموعة وسيُزال للجميع.', 'Cancel your request?': 'إلغاء طلبك؟',
    'You can ask to join': 'يمكنك أن تطلب الانضمام إلى', 'again later.': 'مرة أخرى لاحقًا.', 'Cancel request': 'ألغِ الطلب', 'Keep it': 'أبقِه',
    'Post an RFQ or offer': 'انشر طلب شراء أو عرضًا', 'Type *': 'النوع *', 'Looking to buy (RFQ)': 'مطلوب للشراء (طلب عرض سعر)', 'For sale': 'للبيع',
    'Product or service *': 'المنتج أو الخدمة *', 'e.g. Metformin HCl BP — 2 MT': 'مثال: Metformin HCl BP — 2 طن', 'Details *': 'التفاصيل *',
    'Specs, certificates (GMP, CEP, DMF), quantity, delivery': 'المواصفات والشهادات (GMP وCEP وDMF) والكمية والتسليم', 'Price (offers)': 'السعر (للعروض)',
    'e.g. $5.10/kg or On request': 'مثال: ‎$5.10/كجم أو عند الطلب', 'Post to the group': 'انشر في المجموعة', 'Send a quote': 'أرسل عرض سعر', 'For': 'بخصوص', 'Price *': 'السعر *',
    'e.g. $5.20/kg CIF Alexandria': 'مثال: ‎$5.20/كجم CIF الإسكندرية', 'Lead time *': 'مدة التوريد *', 'e.g. 3 weeks': 'مثال: 3 أسابيع',
    'Certificates, validity, payment terms': 'الشهادات ومدة الصلاحية وشروط الدفع', 'They will lose access to this group.': 'سيفقد الوصول إلى هذه المجموعة.',
    'Post in this group': 'انشر في هذه المجموعة', 'Share a request, an offer or market news with the group…': 'شارك طلبًا أو عرضًا أو أخبار السوق مع المجموعة…',
    'Ask a question or share an update with the group…': 'اطرح سؤالًا أو شارك خبرًا مع المجموعة…', 'Create Post': 'إنشاء منشور', 'Post': 'انشر', 'Add:': 'أضف:',
    'General': 'عام', 'Innovation': 'ابتكار', 'Share an update, market insight, or regulatory news...': 'شارك خبرًا أو رؤية عن السوق أو مستجدًا تنظيميًا...',
    'Request cancelled': 'تم إلغاء الطلب', 'Comment posted!': 'تم نشر التعليق!', 'Post published! ✅': 'تم نشر المنشور! ✅', 'Link copied!': 'تم نسخ الرابط!', 'Post saved! 🔖': 'تم حفظ المنشور! 🔖',
    'Post removed from saved': 'أُزيل المنشور من المحفوظات', 'Post deleted': 'تم حذف المنشور', 'Post removed from the group': 'أُزيل المنشور من المجموعة', 'Post updated': 'تم تحديث المنشور',
    'Pinned to the top of the group': 'تم التثبيت أعلى المجموعة', 'Post unpinned': 'تم إلغاء تثبيت المنشور', 'Reposted to your feed': 'تمت إعادة النشر في صفحتك الرئيسية',
    'Thanks — the group admins will review this post': 'شكرًا — سيراجع مديرو المجموعة هذا المنشور', 'Only members can do that — ask to join first': 'هذا متاح للأعضاء فقط — اطلب الانضمام أولًا',
    'Join the group to post, comment and react': 'انضم إلى المجموعة لتنشر وتعلّق وتتفاعل', 'Comments can be up to 3,000 characters': 'التعليق حتى 3,000 حرف',
    'Posts can be up to 5,000 characters': 'المنشور حتى 5,000 حرف', 'Post cannot be empty': 'لا يمكن نشر منشور فارغ', 'Posted to the group': 'تم النشر في المجموعة',
    'Group settings saved': 'تم حفظ إعدادات المجموعة', 'Group archived — restore it anytime from settings': 'تمت أرشفة المجموعة — يمكنك استعادتها في أي وقت من الإعدادات',
    'Connection request sent!': 'تم إرسال طلب الاتصال!', 'Already connected': 'متصل بالفعل', 'No reactions yet': 'لا توجد تفاعلات بعد', 'Could not save — try again': 'تعذّر الحفظ — حاول مرة أخرى',
    'You are the admin': 'أنت المدير', 'New group': 'مجموعة جديدة', 'Notifications off': 'الإشعارات متوقفة', 'Notifications turned off for this group': 'تم إيقاف إشعارات هذه المجموعة',
    "You'll be notified about new posts": 'ستصلك إشعارات بالمنشورات الجديدة', 'Group posts are not available yet': 'منشورات المجموعات غير متاحة بعد',
    'Posting in groups opens soon': 'النشر في المجموعات متاح قريبًا', 'Posting listings in groups opens soon': 'نشر الإعلانات في المجموعات متاح قريبًا', 'Quotes in groups open soon': 'عروض الأسعار في المجموعات متاحة قريبًا',
    'Could not publish — try again': 'تعذّر النشر — حاول مرة أخرى', 'Could not post — try again': 'تعذّر النشر — حاول مرة أخرى', 'Could not send — try again': 'تعذّر الإرسال — حاول مرة أخرى',
    'Could not update your membership — try again': 'تعذّر تحديث عضويتك — حاول مرة أخرى', 'Open Messages to contact the seller': 'افتح الرسائل لتتواصل مع البائع', 'Loading members…': 'جارٍ تحميل الأعضاء…',
    'Approve requests': 'الموافقة على الطلبات', 'Archive / delete group': 'أرشفة المجموعة أو حذفها', 'Archive Group': 'أرشفة المجموعة', 'Archive Instead': 'أرشفة بدلًا من الحذف',
    'Cannot delete group': 'لا يحذف المجموعة', 'Danger Zone': 'منطقة الخطر', 'Delete Forever': 'احذف نهائيًا', 'Delete Permanently': 'حذف نهائي', 'Edit settings & roles': 'تعديل الإعدادات والأدوار',
    'Hides the group from discovery. History is kept and can be restored anytime.': 'تُخفى المجموعة من الاستكشاف، ويُحفظ تاريخها ويمكن استعادتها في أي وقت.', 'Invite connections': 'دعوة المتصلين به',
    'No moderation rights': 'بلا صلاحيات إشراف', 'Post & comment': 'النشر والتعليق', 'Promote → Sub-Admin': 'الترقية إلى مشرف', 'Remove any member': 'إزالة أي عضو', 'RECOMMENDED': 'موصى به', 'ARCHIVED': 'مؤرشفة',
    'Reply': 'رد', '1st': 'درجة 1', '2nd': 'درجة 2', 'just now': 'الآن', 'You joined': 'انضممت إلى',
    /* groups — the live app (adapter D3b): more posts, join requests, reports, settings and what the database refuses */
    'Show more posts': 'اعرض المزيد من المنشورات', 'Could not load more posts — try again': 'تعذّر تحميل المزيد من المنشورات — حاول مرة أخرى',
    'Join requests': 'طلبات الانضمام', 'asked to join': 'طلب الانضمام', 'Approve': 'وافق', 'No pending requests': 'لا توجد طلبات معلّقة', 'Request declined': 'تم رفض الطلب',
    'Report dismissed': 'تم تجاهل البلاغ', 'Liking comments is not available yet': 'الإعجاب بالتعليقات غير متاح بعد',
    'Sub-admins are not available yet — make them an admin or keep them a member': 'المشرفون غير متاحين بعد — اجعله مديرًا أو أبقه عضوًا',
    'Archiving groups is not available yet — you can delete the group instead': 'أرشفة المجموعات غير متاحة بعد — يمكنك حذف المجموعة بدلًا من ذلك',
    'One rule per line — e.g. Documents first: every offer shows its GMP certificate': 'قاعدة في كل سطر — مثال: المستندات أولًا: كل عرض يُظهر شهادة GMP الخاصة به',
    'This group is no longer available — open the Groups page again': 'هذه المجموعة لم تعد متاحة — افتح صفحة المجموعات مرة أخرى', 'This member is no longer available': 'هذا العضو لم يعد متاحًا',
    'Only the group’s admins can remove members': 'إزالة الأعضاء متاحة لمديري المجموعة فقط', 'Only the group’s admins can change roles': 'تغيير الأدوار متاح لمديري المجموعة فقط',
    'Only the group’s admins can change its settings': 'تغيير إعدادات المجموعة متاح لمديريها فقط', 'You are not a member of this group': 'أنت لست عضوًا في هذه المجموعة',
    'This post could not be changed': 'تعذّر تعديل هذا المنشور', 'This post could not be removed': 'تعذّرت إزالة هذا المنشور', 'This report was already answered': 'تم الرد على هذا البلاغ بالفعل',
    'This is not available yet': 'هذا غير متاح بعد', 'Group not found': 'المجموعة غير موجودة', 'Only the group\'s admins can answer join requests': 'الرد على طلبات الانضمام متاح لمديري المجموعة فقط',
    'There is no pending request from this person': 'لا يوجد طلب معلّق من هذا الشخص', 'Only the group\'s admins can pin a post': 'تثبيت المنشورات متاح لمديري المجموعة فقط',
    'Only a post of this group can be pinned in it': 'لا يُثبَّت في المجموعة إلا منشور منها', 'You have 20 requests waiting for an answer — please wait for the groups to reply': 'لديك 20 طلبًا تنتظر الرد — انتظر حتى ترد المجموعات',
    /* Home feed actions (feedacts.js): reactions, Save, Copy link, Report; Admin → Review → Reported posts */
    'Support': 'دعم', 'Celebrate': 'تهنئة', 'Insightful': 'مفيد', 'Appreciation': 'تقدير', 'Curious': 'فضول', '🔖 Saved': '🔖 محفوظ', 'Report': 'إبلاغ',
    '🔗 Copy link': '🔗 انسخ الرابط', '🚩 Report': '🚩 إبلاغ', 'Loading…': 'جارٍ التحميل…', '(you)': '(أنت)',
    'Drugbox reviews every report. The author is not told who reported.': 'يراجع فريق Drugbox كل بلاغ، ولا يُبلَّغ صاحب المنشور بمن أبلغ.',
    'What should Drugbox know?': 'ما الذي يجب أن يعرفه فريق Drugbox؟', 'Thanks — Drugbox will review this post': 'شكرًا — سيراجع فريق Drugbox هذا المنشور',
    'You already reported this post — Drugbox is reviewing it': 'سبق أن أبلغت عن هذا المنشور — فريق Drugbox يراجعه', 'Could not send the report — try again': 'تعذّر إرسال البلاغ — حاول مرة أخرى',
    'This post is no longer available': 'هذا المنشور لم يعد متاحًا', 'Could not load the reactions': 'تعذّر تحميل التفاعلات', 'You cannot report your own post': 'لا يمكنك الإبلاغ عن منشورك',
    'Reported posts': 'منشورات مُبلَّغ عنها', 'Remove this post?': 'إزالة هذا المنشور؟', 'Dismiss': 'تجاهل', 'Dismiss this report?': 'تجاهل هذا البلاغ؟', 'The post stays up.': 'يبقى المنشور منشورًا.',
    'The author is told it was removed and why. Every reporter is told the outcome.': 'يُبلَّغ صاحب المنشور بإزالته وسببه، ويُبلَّغ كل من أبلغ بالنتيجة.',
    'Note for the author (optional)': 'ملاحظة لصاحب المنشور (اختياري)', 'Nothing waiting here.': 'لا شيء في الانتظار هنا.'
  };
  /* phase 1b round 2: interface words the Arabic reader still saw in English (profile empty states, the Jobs tools, chat header,
     Drugbox's own notices, the block refusal) */
  Object.assign(D, {
    'reacted to your post': 'تفاعل مع منشورك', "You can't message this person": 'لا يمكنك مراسلة هذا الشخص', 'You can’t message this person': 'لا يمكنك مراسلة هذا الشخص',
    'Last seen recently': 'آخر ظهور منذ قليل', '● Online': '● متصل الآن',
    'Drugbox reviewed your report and removed the post.': 'راجع فريق Drugbox بلاغك وأزال المنشور.', 'Drugbox reviewed your report — the post stays up.': 'راجع فريق Drugbox بلاغك — المنشور باقٍ.',
    'Professionals open to work': 'متخصصون متاحون للعمل', 'No bio yet.': 'لا توجد نبذة بعد.', 'No experience added.': 'لم تُضف خبرات بعد.', 'Education': 'التعليم', 'EDUCATION': 'التعليم',
    'No education added.': 'لم يُضف تعليم بعد.', 'Looking for your next role?': 'تبحث عن وظيفتك القادمة؟', 'Sorted by most recent': 'مرتبة من الأحدث',
    'Ranked only by users’ own public reviews, with a fair average so a single 5★ can’t beat many strong reviews.': 'الترتيب حسب تقييمات المستخدمين العلنية فقط، بمتوسط عادل حتى لا يتفوق تقييم واحد بخمس نجوم على تقييمات قوية كثيرة.',
    '🏅 Public. Written by companies the person actually worked for.': '🏅 علنية. تكتبها شركات عمل لديها الشخص فعلًا.',
    '⚠️ Visible to': '⚠️ تظهر', 'verified employers only': 'لأصحاب العمل الموثّقين فقط',
    '. Every warning is written by a company that employed the person, backed by evidence reviewed by Drugbox, shows the person’s reply, and expires after 2 years. Disputed warnings are hidden until resolved.':
      '. كل تحذير تكتبه شركة وظّفت الشخص، ومعه دليل يراجعه فريق Drugbox، ويظهر معه رد الشخص، وينتهي بعد سنتين. التحذيرات المعترض عليها تُخفى حتى يُبت فيها.',
    'Preferred candidates appear first, and their applications to your jobs go straight to your shortlist. You get an alert when they apply or become available.': 'يظهر المرشحون المفضّلون أولًا، وتذهب طلباتهم لوظائفك مباشرة إلى قائمتك المختصرة. يصلك تنبيه عندما يتقدمون أو يصبحون متاحين.',
    'Your favourite companies’ jobs appear first, and you get an alert when they post.': 'تظهر وظائف شركاتك المفضّلة أولًا، ويصلك تنبيه عندما تنشر.',
    'No one yet. Use ⭐ on a card.': 'لا أحد بعد. استخدم ⭐ على أي بطاقة.', 'No one blocked.': 'لم تحظر أحدًا.', 'Nothing here yet.': 'لا شيء هنا بعد.', 'No reviews yet': 'لا توجد تقييمات بعد',
    'My lists — candidates': 'قوائمي — المرشحون', 'My lists — companies': 'قوائمي — الشركات', '🏆 Top-rated employers': '🏆 أصحاب العمل الأعلى تقييمًا', '🏆 Top-rated candidates': '🏆 المرشحون الأعلى تقييمًا',
    '🏅 Honor list': '🏅 قائمة الشرف', '⚠️ Warning list': '⚠️ قائمة التحذير', '⭐ Whitelist': '⭐ القائمة المفضّلة', '⛔ Blacklist': '⛔ القائمة المحظورة', 'Unblock': 'إلغاء الحظر',
    'No reply yet — the person has been notified and can reply or dispute.': 'لا رد بعد — أُبلغ الشخص ويمكنه الرد أو الاعتراض.', 'Pending review by Drugbox': 'بانتظار مراجعة Drugbox',
    'Honorable records are published on the person’s profile and the public Honor list.': 'تُنشر السجلات المشرّفة في ملف الشخص وفي قائمة الشرف العلنية.',
    'Full-Time': 'دوام كامل', 'full-time': 'دوام كامل', 'contract': 'عقد', 'part-time': 'دوام جزئي', 'Part-time': 'دوام جزئي', 'Halal': 'حلال', 'No company matches.': 'لا توجد شركة مطابقة.',
    '/unit': '/للوحدة', 'No courses yet.': 'لا توجد دورات بعد.'
  });
  var PATTERNS_EXTRA = [
    /* Drugbox's notice to the author of a removed post: the post's words and the moderator's note stay as written */
    [/^Drugbox removed your post “([\s\S]*)” — reason: (spam or an unrelated ad|an unverified or counterfeit product|misleading information|harassment or hate|it breaks the Drugbox rules)\.(?: Note: ([\s\S]+))?$/, function (m) {
      var why = { 'spam or an unrelated ad': 'رسائل مزعجة أو إعلان غير ذي صلة', 'an unverified or counterfeit product': 'منتج غير موثّق أو مغشوش', 'misleading information': 'معلومات مضللة', 'harassment or hate': 'تحرش أو كراهية', 'it breaks the Drugbox rules': 'مخالفة قواعد Drugbox' }[m[2]];
      return 'أزال فريق Drugbox منشورك “' + m[1] + '” — السبب: ' + why + '.' + (m[3] ? ' ملاحظة: ' + m[3] : ''); }],
    [/^MOQ: (.+)$/, function (m) { return 'الحد الأدنى للطلب: ' + m[1]; }]
  ];
  var UNITS = { m: ['دقيقة', 'دقائق'], h: ['ساعة', 'ساعات'], d: ['يوم', 'أيام'], w: ['أسبوع', 'أسابيع'], min: ['دقيقة', 'دقائق'] };
  function unit(n, u) { return plural(n, UNITS[u] || [u, u]); }
  /* the ONE rule for a noun after a number, everywhere: forms = [singular, plural, dual?]. Arabic counts 3–10 with the plural
     (and 103–110, 203–210…: the last two digits decide); 1, 11–99, 100–102… take the singular (20 دورة, 11 عضو, 100 عضو);
     2 takes the dual when one is given, else — as in everyday writing with a digit — the plural */
  function plural(n, forms) { var x = /K$/i.test(String(n)) ? 1000 : parseFloat(String(n).replace(/,/g, '')), m = x % 100;
    return x === 2 ? (forms[2] || DUAL[forms[0]] || forms[1]) : x === Math.floor(x) && m >= 3 && m <= 10 ? forms[1] : forms[0]; }
  /* 2 takes the dual (X-03): "2 يومان", "2 سنتان خبرة", "2 عضوان" — every singular a count uses here, and the layers' own (dxArPlural) */
  var DUAL = { 'أسبوع': 'أسبوعان', 'إعادة نشر': 'إعادتا نشر', 'إعلان': 'إعلانان', 'اتصال': 'اتصالان', 'اتصال مشترك': 'اتصالان مشتركان', 'استفسار': 'استفساران',
    'تحديث تسجيل': 'تحديثا تسجيل', 'تحذير': 'تحذيران', 'تعليق': 'تعليقان', 'جديد': 'جديدان', 'دقيقة': 'دقيقتان', 'دورة': 'دورتان', 'ساعة': 'ساعتان', 'سنة': 'سنتان',
    'شخص': 'شخصان', 'شركة': 'شركتان', 'شهر': 'شهران', 'صفقة مكتملة': 'صفقتان مكتملتان', 'طلب': 'طلبان', 'طلب تسعير اليوم': 'طلبا تسعير اليوم',
    'طلب جديد اليوم': 'طلبان جديدان اليوم', 'طلب مكتمل': 'طلبان مكتملان', 'طلب وارد': 'طلبان واردان', 'عرض': 'عرضان', 'عضو': 'عضوان', 'عضو آخر': 'عضوان آخران',
    'عضو حقيقي': 'عضوان حقيقيان', 'عميل': 'عميلان', 'متخصص': 'متخصصان', 'مشاهدة': 'مشاهدتان', 'مشترٍ نشط': 'مشتريان نشطان', 'مقدّم خدمة': 'مقدّما خدمة',
    'ملف': 'ملفان', 'منشور': 'منشوران', 'منشور جديد': 'منشوران جديدان', 'منشور جديد اليوم': 'منشوران جديدان اليوم', 'منشور جديد هذا الأسبوع': 'منشوران جديدان هذا الأسبوع',
    'منشور سوق': 'منشورا سوق', 'منشور محفوظ': 'منشوران محفوظان', 'مورّد': 'مورّدان', 'موقع': 'موقعان', 'نتيجة': 'نتيجتان', 'نشط': 'نشطان', 'وظيفة': 'وظيفتان',
    'وظيفة متاحة': 'وظيفتان متاحتان', 'يوم': 'يومان' };
  window.dxArPlural = plural;   /* the same rule for the layers that write Arabic counts themselves */
  var WORDS = { comments: ['تعليق', 'تعليقات'], reposts: ['إعادة نشر', 'إعادات نشر'], members: ['عضو', 'أعضاء'], posts: ['منشور', 'منشورات'], views: ['مشاهدة', 'مشاهدات'],
    connections: ['اتصال', 'اتصالات'], listings: ['إعلان', 'إعلانات'], companies: ['شركة', 'شركات'], providers: ['مقدّم خدمة', 'مقدّمي خدمة'], clients: ['عميل', 'عملاء'], inquiries: ['استفسار', 'استفسارات'],
    results: ['نتيجة', 'نتائج'], sites: ['موقع', 'مواقع'], profiles: ['ملف', 'ملفات'], warnings: ['تحذير', 'تحذيرات'],
    'open positions': ['وظيفة متاحة', 'وظائف متاحة'], 'requests received': ['طلب وارد', 'طلبات واردة'], 'new posts today': ['منشور جديد اليوم', 'منشورات جديدة اليوم'],
    'new posts this week': ['منشور جديد هذا الأسبوع', 'منشورات جديدة هذا الأسبوع'], 'deals closed': ['صفقة مكتملة', 'صفقات مكتملة'], 'new posts': ['منشور جديد', 'منشورات جديدة'],
    'new requests today': ['طلب جديد اليوم', 'طلبات جديدة اليوم'], 'quote requests today': ['طلب تسعير اليوم', 'طلبات تسعير اليوم'], listing: ['إعلان', 'إعلانات'],
    /* X-03: the Jobs strip and the Home card count with the same rule — and say the dual for 2 */
    'open positions across egypt & gcc': ['وظيفة متاحة في مصر والخليج', 'وظائف متاحة في مصر والخليج', 'وظيفتان متاحتان في مصر والخليج'],
    'jobs posted this week': ['وظيفة نُشرت هذا الأسبوع', 'وظائف نُشرت هذا الأسبوع', 'وظيفتان نُشرتا هذا الأسبوع'],
    'candidates available now': ['مرشح متاح الآن', 'مرشحين متاحين الآن', 'مرشحان متاحان الآن'],
    'professionals — graduates, specialists and industry veterans': ['متخصص — خريجون ومتخصصون وخبراء صناعة', 'متخصصين — خريجون ومتخصصون وخبراء صناعة', 'متخصصان — خريجون ومتخصصون وخبراء صناعة'],
    'pharma professionals — from new graduates to industry veterans': ['متخصص في الدواء — من حديثي التخرج حتى خبراء الصناعة', 'متخصصين في الدواء — من حديثي التخرج حتى خبراء الصناعة', 'متخصصان في الدواء — من حديثي التخرج حتى خبراء الصناعة'] };
  function word(n, w) { w = w.toLowerCase().replace(/^request received$/, 'requests received').replace(/^company$/, 'companies'); var f = WORDS[w] || WORDS[w + 's']; return f ? n + ' ' + plural(n, f) : null; }
  var __cn = null;   /* company names, for the 'Open <company>' tooltip; rebuilt when the directory list changes */
  function coName(n) { var X = window.dxDir; if (!X || !X.companies) return false; var l = X.companies(); if (!__cn || __cn.l !== l) { __cn = { l: l, s: new Set() }; l.forEach(function (c) { __cn.s.add(c.name); }); } return __cn.s.has(n); }
  var PATTERNS = [
    [/^and ([\d,]+) more$/, function (m) { return 'و' + m[1] + ' آخرون'; }], [/^([\d,]+) people reacted$/, function (m) { return 'تفاعل ' + m[1] + ' ' + plural(m[1], ['شخص', 'أشخاص']); }],
    [/^(\d+)\s*(m|min|h|d|w) ago$/i, function (m) { return 'منذ ' + m[1] + ' ' + unit(m[1], m[2].toLowerCase()); }],
    [/^(\d+)(min|h|d) ago(.*)$/i, function (m) { return 'منذ ' + m[1] + ' ' + unit(m[1], m[2].toLowerCase()) + tr(m[3]); }],
    [/^([\d,.]+K?)\s+(comments?|reposts?|members?|posts?|views?|connections?|listings?|companies|company|providers|clients|inquiries|results|sites?|open positions|requests received|request received|new posts today|new posts this week|deals closed)$/i, function (m) { return word(m[1], m[2]); }],
    [/^(.+?)\s*\((\d+)\)$/, function (m) { var h = D[m[1]] || D[m[1].trim()]; return h ? h + ' (' + m[2] + ')' : null; }],
    [/^(Surplus stock|Licensing dossiers|Group buying)\s*\((\d+)\)$/, function (m) { return ({ 'Surplus stock': 'مخزون فائض', 'Licensing dossiers': 'ملفات ترخيص', 'Group buying': 'شراء جماعي' })[m[1]] + ' (' + m[2] + ')'; }],
    [/^expires (\d{4}-\d{2})$/, function (m) { return 'تنتهي ' + m[1]; }], [/^expired (\d{4}-\d{2})$/, function (m) { return 'انتهت ' + m[1]; }],
    [/^Source: (.+) · updated (.+)$/, function (m) { return 'المصدر: ' + (D[m[1]] || m[1]) + ' · حُدّث ' + gbIn(m[2]); }],
    [/^Open (.+)’s profile$/, function (m) { return 'افتح ملف ' + m[1]; }], [/^Open (.+)$/, function (m) { return D[m[1]] ? 'افتح ' + D[m[1]] : coName(m[1]) ? 'افتح صفحة ' + m[1] : null; }],
    [/^listed (.+)$/, function (m) { return 'أدرج ' + m[1]; }], [/^commented: (.+)$/, function (m) { return 'علّق: ' + m[1]; }],   /* activity and notification verbs; the quoted words stay as written */
    [/^\((.+?)\)\. Questionnaires go to (.+); job applications to (.+)\.$/, function (m) { return '(' + (D[m[1]] || m[1]) + '). الاستبيانات تذهب إلى ' + m[2] + '؛ وطلبات التوظيف إلى ' + m[3] + '.'; }],
    [/^You joined (.+)$/, function (m) { return 'انضممت إلى ' + m[1]; }], [/^You left (.+)$/, function (m) { return 'غادرت ' + m[1]; }],
    [/^Invites sent to (\d+) (person|people)$/, function (m) { var n = +m[1]; return n === 1 ? 'تم إرسال الدعوة إلى شخص واحد' : n === 2 ? 'تم إرسال الدعوات إلى شخصين' : 'تم إرسال الدعوات إلى ' + n + ' ' + (n <= 10 ? 'أشخاص' : 'شخصًا'); }],   /* groups (N-9) */
    [/^invited you to join the private group "(.+)"$/, function (m) { return 'دعاك للانضمام إلى المجموعة الخاصة "' + m[1] + '"'; }],   /* live notification (N-8) */
    [/^Welcome to Drugbox, (.+)!$/, function (m) { return 'أهلًا بك في Drugbox يا \u2068' + m[1] + '\u2069!'; }],   /* the sign-up toast, demo and live (N-13); the name isolated */
    [/^Welcome back, (.+)!$/, function (m) { return 'أهلًا بعودتك يا \u2068' + m[1] + '\u2069!'; }],   /* the sign-in toast, live (S-03 fix 4): any member's name, isolated */
    [/^Not found on Drugbox: (.+)$/, function (m) { return 'غير موجود على Drugbox: ' + m[1]; }],
    [/^No Drugbox member found for (.+) — use the name on their Drugbox profile$/, function (m) { return 'لا يوجد عضو في Drugbox باسم ' + m[1] + ' — استخدم الاسم المكتوب في ملفه على Drugbox'; }],
    [/^Unread \((\d+)\)$/, function (m) { return 'غير مقروء (' + m[1] + ')'; }],   /* the Messages filter, recounted (J-SOCIAL-38) */
    [/^No member called (.+) — choose someone from the list$/, function (m) { return 'لا يوجد عضو باسم ' + m[1] + ' — اختر شخصًا من القائمة'; }],   /* ✎ New message (S-03) */
    [/^Several members are called (.+) — choose one from the list$/, function (m) { return 'أكثر من عضو باسم ' + m[1] + ' — اختر واحدًا من القائمة'; }],
    [/^Choose (.+) from the list to be sure who receives it$/, function (m) { return 'اختر ' + m[1] + ' من القائمة لتتأكد من المستلم'; }],
    /* the name rule's refusals (live: sign-up, Edit Profile, the database — 0039_names_rule_4): what they quote is isolated (U+2068 …
       U+2069), kept in the Arabic sentence so a Latin, Greek or Cyrillic character or name keeps its place */
    [/^A name can only have letters, spaces and \. - ' \( \) , \/ ، — remove “\u2068([^]*)\u2069” \(\u2068(U\+[0-9A-F]+)\u2069\)$/, function (m) { return "الاسم يقبل الحروف والمسافات و \u2066. - ' ( ) , /\u2069 ، فقط — احذف «\u2068" + m[1] + '\u2069» (\u2068' + m[2] + '\u2069)'; }],
    [/^Write a name in Latin, Arabic, Greek or Cyrillic letters — “\u2068([^]*)\u2069” \(\u2068(U\+[0-9A-F]+)\u2069\) is not one of them$/, function (m) { return 'اكتب الاسم بحروف عربية أو لاتينية أو يونانية أو سيريلية — «\u2068' + m[1] + '\u2069» (\u2068' + m[2] + '\u2069) ليس منها'; }],
    [/^The letter “\u2068([^]*)\u2069” \(\u2068(U\+[0-9A-F]+)\u2069\) is not supported in names yet$/, function (m) { return 'الحرف «\u2068' + m[1] + '\u2069» (\u2068' + m[2] + '\u2069) غير مدعوم في الأسماء بعد'; }],
    [/^“\u2068([^]*)\u2069” is not a word — join it to the word next to it \(remove the space\)$/, function (m) { return '«\u2068' + m[1] + '\u2069» ليست كلمة — ألصقها بالكلمة المجاورة (احذف المسافة)'; }],
    [/^Put what follows the name in parentheses — write “\u2068([^]*)\u2069”$/, function (m) { return 'ضع ما يلي الاسم بين قوسين — اكتب «\u2068' + m[1] + '\u2069»'; }],
    [/^Write each word of a name in one alphabet — “\u2068([^]*)\u2069” mixes alphabets$/, function (m) { return 'اكتب كل كلمة من الاسم بأبجدية واحدة — «\u2068' + m[1] + '\u2069» تخلط بين أبجديات'; }],
    [/^Remove the mark added to “\u2068([^]*)\u2069” \(\u2068(U\+[0-9A-F]+)\u2069\) — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ$/, function (m) { return 'احذف العلامة المضافة إلى «\u2068' + m[1] + '\u2069» (\u2068' + m[2] + '\u2069) — يقبل Drugbox الحرف ذا العلامة مكتوبًا كحرف واحد، مثل \u2066é، ü، ñ\u2069'; }],
    [/^🚫 Block (.+)$/, function (m) { return '🚫 حظر ' + m[1]; }], [/^✅ Unblock (.+)$/, function (m) { return '✅ إلغاء الحظر عن ' + m[1]; }],   /* the conversation menu (J-SOCIAL-40) */
    [/^Block (.+)\?$/, function (m) { return 'حظر ' + m[1] + '؟'; }], [/^(.+) blocked$/, function (m) { return 'تم حظر ' + m[1]; }], [/^(.+) unblocked$/, function (m) { return 'تم إلغاء الحظر عن ' + m[1]; }],
    [/^Notifications muted for (.+)$/, function (m) { return 'تم كتم إشعارات ' + m[1]; }], [/^Notifications on for (.+)$/, function (m) { return 'تم تشغيل إشعارات ' + m[1]; }],
    [/^(.+) reported (.+)$/, function (m) { return m[1] + ' أبلغ عن ' + m[2]; }],
    /* live: messaging a company from its page (B-05) */
    [/^Nobody at (.+) answers messages on Drugbox yet — (?:call, email or WhatsApp them from the Contact tab|use the phone, email or WhatsApp on its Contact tab)$/, function (m) { return 'لا أحد في ' + m[1] + ' يرد على الرسائل على Drugbox بعد — اتصل بهم أو راسلهم بالبريد أو واتساب من تبويب التواصل'; }],
    [/^You answer (.+)’s messages yourself$/, function (m) { return 'أنت من يرد على رسائل ' + m[1]; }],
    [/^messaged (.+?): (".*")$/, function (m) { return 'راسل ' + (m[1] === 'your company' ? 'شركتك' : m[1]) + ': ' + m[2]; }]
  ];
  PATTERNS.push(
    [/^▶ Video intro · (\d+:\d+)$/, function (m) { return '▶ فيديو تعريفي · ' + m[1]; }],
    [/^Keep it under (3 minutes|90 seconds) \(this one is (\d+:\d+)\)$/, function (m) { return 'اجعله أقل من ' + (m[1] === '3 minutes' ? '3 دقائق' : '90 ثانية') + ' (هذا ' + m[2] + ')'; }],
    [/^The video is larger than (\d+) MB$/, function (m) { return 'الفيديو أكبر من ' + m[1] + ' ميجابايت'; }],
    [/^Level (\d) · (Registered|Licensed|Inspected)$/, function (m) { return 'المستوى ' + m[1] + ' · ' + D[m[2]]; }],
    [/^Next: (.+)\.$/, function (m) { return 'التالي: ' + (D[m[1]] || m[1]) + '.'; }],
    [/^(\d+\+?|\d+[–-]\d+) yrs( exp)?$/, function (m) { return m[1] + ' ' + plural(m[1].split(/[–-]/).pop(), ['سنة', 'سنوات']) + (m[2] ? ' خبرة' : ''); }],
    [/^(\d+) years? experience$/, function (m) { return m[1] + ' ' + plural(m[1], ['سنة', 'سنوات']) + ' خبرة'; }], [/^✓ (\d+) years experience$/, function (m) { return '✓ ' + m[1] + ' ' + plural(m[1], ['سنة', 'سنوات']) + ' خبرة'; }],
    [/^(👁|📨)\s*([\d,]+) (views|inquiries)$/, function (m) { return m[1] + ' ' + m[2] + ' ' + (m[3] === 'views' ? 'مشاهدة' : 'استفسار'); }],
    [/^~([\d,]+) (views|inquiries)( \((\d+)×\))?$/, function (m) { return '~' + m[1] + ' ' + plural(m[1], m[2] === 'views' ? ['مشاهدة', 'مشاهدات'] : ['استفسار', 'استفسارات']) + (m[3] ? ' (' + m[4] + '×)' : ''); }],
    [/^(\d+)× avg reach$/, function (m) { return 'وصول أعلى ' + m[1] + '× من المتوسط'; }],
    [/^Matches: (.+)$/, function (m) { return 'تطابق: ' + m[1].split(' · ').map(function (x) { return D[x] || x; }).join(' · '); }],
    [/^(\d+) profiles$/, function (m) { return word(m[1], 'profiles'); }], [/^#(\d+) top-rated candidate$/, function (m) { return 'المرشح #' + m[1] + ' الأعلى تقييمًا'; }],
    [/^(\d+) warnings?$/, function (m) { return word(m[1], 'warnings'); }], [/^(\d+) new posts?$/, function (m) { return word(m[1], 'new posts'); }],
    [/^(\d+) new requests today$/, function (m) { return word(m[1], 'new requests today'); }], [/^(\d+) quote requests today$/, function (m) { return word(m[1], 'quote requests today'); }],
    [/^(\d+) unread$/, function (m) { return m[1] + ' غير مقروء'; }], [/^(\d+) UNREAD \/ (\d+) TOTAL$/, function (m) { return m[1] + ' غير مقروء / ' + m[2] + ' إجمالي'; }],
    [/^(\d+) on record$/, function (m) { return m[1] + ' مسجلة'; }], [/^(\d+) SAVED POSTS$/, function (m) { return m[1] + ' ' + plural(m[1], ['منشور محفوظ', 'منشورات محفوظة']); }],
    [/^(\d+) mutual connections?$/, function (m) { return +m[1] === 1 ? 'اتصال مشترك واحد' : m[1] + ' ' + plural(m[1], ['اتصال مشترك', 'اتصالات مشتركة']); }],
    [/^(\d+) CONNECTIONS \/ (\d+) PENDING$/, function (m) { return m[1] + ' ' + plural(m[1], ['اتصال', 'اتصالات']) + ' / ' + m[2] + ' معلّقة'; }], [/^View all (\d+) →$/, function (m) { return 'عرض الكل (' + m[1] + ') ←'; }],
    [/^New group · ([\d,]+) members already$/, function (m) { return 'مجموعة جديدة · ' + m[1] + ' ' + plural(m[1], ['عضو', 'أعضاء']) + ' بالفعل'; }], [/^💡 (\d+) of your connections are members$/, function (m) { return '💡 ' + m[1] + ' من اتصالاتك أعضاء'; }],
    [/^Honor ×(\d+)$/, function (m) { return 'تكريم ×' + m[1]; }], [/^Today, (.+)$/, function (m) { return 'اليوم، ' + m[1]; }],
    [/^(\d+) new posts · (\d+) buyers active right now$/, function (m) { return m[1] + ' ' + plural(m[1], ['منشور جديد', 'منشورات جديدة']) + ' · ' + m[2] + ' ' + plural(m[2], ['مشترٍ نشط', 'مشترين نشطين']) + ' الآن'; }],
    [/^🇪🇬 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇪🇬 ' + q : null; }], [/^🇦🇪 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇦🇪 ' + q : null; }],
    [/^🇮🇳 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇮🇳 ' + q : null; }], [/^🇸🇦 (.+)$/, function (m) { var q = tr(m[1]); return q !== m[1] ? '🇸🇦 ' + q : null; }]
  );
  var DAYS = { SUNDAY: 'الأحد', MONDAY: 'الاثنين', TUESDAY: 'الثلاثاء', WEDNESDAY: 'الأربعاء', THURSDAY: 'الخميس', FRIDAY: 'الجمعة', SATURDAY: 'السبت' };
  var CAPS = { COURSES: 'دورات', REGULATORY: 'التسجيل', FORMULATION: 'التركيبات', 'MARKET POSTS': 'منشورات سوق', 'REGULATORY UPDATES': 'تحديثات تسجيل', LISTINGS: 'إعلان', SUPPLY: 'عرض', DEMAND: 'طلب', SUPPLIERS: 'مورّد', CONNECTIONS: 'اتصالات', PENDING: 'معلّقة', UNREAD: 'غير مقروء', TOTAL: 'إجمالي' };
  /* after a number a counted word takes the number's form (20 دورة, 5 دورات); PENDING, UNREAD, TOTAL describe and stay */
  var CAPS_N = { COURSES: ['دورة', 'دورات'], 'MARKET POSTS': ['منشور سوق', 'منشورات سوق'], 'REGULATORY UPDATES': ['تحديث تسجيل', 'تحديثات تسجيل'], LISTINGS: ['إعلان', 'إعلانات'],
    SUPPLY: ['عرض', 'عروض'], DEMAND: ['طلب', 'طلبات'], SUPPLIERS: ['مورّد', 'مورّدين'], CONNECTIONS: ['اتصال', 'اتصالات'] };
  PATTERNS.push(
    [/^[A-Za-z0-9 .,K]+( \/ [A-Za-z0-9 .,K]+)+$/, function (m) { var ok = 0, out = m[0].split(' / ').map(function (seg) { seg = seg.trim(); var U = seg.toUpperCase(); if (DAYS[U]) { ok++; return DAYS[U]; } var x = /^([\d.,]+K?) ([A-Za-z ]+)$/.exec(seg); if (x && CAPS[x[2].toUpperCase()]) { ok++; var w = x[2].toUpperCase(); return x[1] + ' ' + (CAPS_N[w] ? plural(x[1], CAPS_N[w]) : CAPS[w]); } if (CAPS[U] && !/\d/.test(U)) { ok++; return CAPS[U]; } return seg; }).join(' / '); return ok ? out : null; }],
    [/^trending — (\d+) posts in (\d+)h$/, function (m) { return 'رائج — ' + m[1] + ' ' + plural(m[1], ['منشور', 'منشورات']) + ' خلال ' + m[2] + ' ' + unit(m[2], 'h'); }],
    [/^💡 You have (\d+) active (.+) listings — buyers post here daily$/, function (m) { return '💡 لديك ' + m[1] + ' ' + plural(m[1], ['إعلان', 'إعلانات']) + ' ' + m[2] + ' ' + plural(m[1], ['نشط', 'نشطة']) + ' — المشترون ينشرون هنا يوميًا'; }],
    [/^⚡ Replies in <(\d+)h$/, function (m) { return '⚡ يرد خلال أقل من ' + m[1] + ' ' + unit(m[1], 'h'); }],
    [/^✅ (\d+)% response rate · avg\. (.+) reply(.*)$/, function (m) { return '✅ نسبة الرد ' + m[1] + '% · متوسط الرد ' + m[2].replace(/min$/, ' دقيقة').replace(/h$/, ' ساعة') + tr(m[3]); }],
    [/^● Online · (.+)$/, function (m) { return '● متصل · ' + m[1]; }],
    [/^reacted to your post about (.+)$/, function (m) { return 'تفاعل مع منشورك عن ' + m[1]; }], [/^💡 Matches your "(.+)" sector tag$/, function (m) { return '💡 يطابق قطاع "' + m[1] + '" في ملفك'; }]
  );
  var QTYPE = { 'Quote request': 'طلب عرض سعر', 'Service request': 'طلب خدمة', 'Surplus offer': 'عرض فائض', 'Dossier request': 'طلب ملف', 'Job application': 'طلب توظيف', 'Qualification questionnaire': 'استبيان تأهيل', 'Group order': 'طلب جماعي', 'Requests & deals': 'الطلبات والصفقات' };
  PATTERNS.push(
    [/^(Quote request|Service request|Surplus offer|Dossier request|Job application|Qualification questionnaire|Group order|Requests & deals) — (.+)$/, function (m) { return QTYPE[m[1]] + ' — ' + m[2]; }],
    [/^(Quote request|Service request|Surplus offer|Dossier request|Job application|Qualification questionnaire|Group order) → (.+)$/, function (m) { return QTYPE[m[1]] + ' ← ' + m[2]; }],
    [/^Surplus · (.+) · batch (.+)$/, function (m) { return 'فائض · ' + m[1] + ' · تشغيلة ' + m[2]; }], [/^(.+) · to (\d{4}-\d{2}(?:-\d{2})?)$/, function (m) { return m[1] + ' · حتى ' + m[2]; }],
    [/^(\d+) waiting for you$/, function (m) { return m[1] + ' بانتظارك'; }],
    [/^·?\s*(Accept quote|Confirm order|Mark shipped|Send quote|Confirm received)$/, function (m) { return '· ' + D[m[1]]; }],
    [/^Send quote: (.+) · valid (\d+) days$/, function (m) { return 'أرسل عرضًا: ' + m[1] + ' · صالح ' + m[2] + ' ' + unit(m[2], 'd'); }],
    [/^· valid (\d+) days \(to ([^)]+)\)(.*)$/, function (m) { return '· صالح ' + m[1] + ' ' + unit(m[1], 'd') + ' (حتى ' + gbIn(m[2]) + ')' + m[3]; }]
  );
  /* dates the app prints with the browser's default toLocaleString() (e.g. 10/3/2026, 1:36:27 AM) are re-written in Arabic */
  var DLOC = (function () { try { return Intl.DateTimeFormat().formatToParts(new Date(2001, 10, 22)).filter(function (p) { return /day|month|year/.test(p.type); }).map(function (p) { return p.type; }); } catch (e) { return ['month', 'day', 'year']; } })();
  function arDate(m) {
    var v = {}; DLOC.forEach(function (k, i) { v[k] = +m[i + 1]; }); if (!(v.month >= 1 && v.month <= 12 && v.day >= 1 && v.day <= 31)) return null;
    var h = m[4] == null ? null : m[7] ? +m[4] % 12 + (/PM/i.test(m[7]) ? 12 : 0) : +m[4], d = new Date(v.year, v.month - 1, v.day, h || 0, +(m[5] || 0), +(m[6] || 0));
    try { return window.dxFmtDate(d, h != null); } catch (e) { return null; }
  }
  window.dxFmtDate = function (d, withTime, lang) {   /* one formatter for dates in the interface language (Latin digits, like the rest of the Arabic UI);
     layers pass lang 'en' to write the English original (e.g. "2 Oct 2026, 13:36"), which the pattern below turns into Arabic and back */
    d = d instanceof Date ? d : new Date(d); var ar = (lang || document.documentElement.lang) === 'ar';
    var o = { year: 'numeric', month: 'short', day: 'numeric' }; if (withTime) { o.hour = 'numeric'; o.minute = '2-digit'; }
    return new Intl.DateTimeFormat(ar ? 'ar-EG-u-nu-latn' : 'en-GB', o).format(d);
  };
  var DATE = '(\\d{1,2})/(\\d{1,2})/(\\d{4})(?:,? (\\d{1,2}):(\\d{2})(?::(\\d{2}))?\\s?(AM|PM)?)?';
  var GB = '(\\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec) (\\d{4})(?:, (\\d{1,2}):(\\d{2}))?';   /* dxFmtDate(d, time, 'en') */
  function gbDate(m) { var d = new Date(+m[3], 'JanFebMarAprMayJunJulAugSepOctNovDec'.indexOf(m[2].slice(0, 3)) / 3, +m[1], +(m[4] || 0), +(m[5] || 0)); try { return window.dxFmtDate(d, m[4] != null, 'ar'); } catch (e) { return null; } }
  function gbIn(s) { var m = new RegExp('^' + GB + '$').exec(s); return m && gbDate(m) || s; }
  var MON = { Jan: 'يناير', Feb: 'فبراير', Mar: 'مارس', Apr: 'أبريل', May: 'مايو', Jun: 'يونيو', Jul: 'يوليو', Aug: 'أغسطس', Sep: 'سبتمبر', Oct: 'أكتوبر', Nov: 'نوفمبر', Dec: 'ديسمبر' };
  var WDAY = { Sat: 'السبت', Sun: 'الأحد', Mon: 'الاثنين', Tue: 'الثلاثاء', Wed: 'الأربعاء', Thu: 'الخميس', Fri: 'الجمعة' };
  var UNIT = { kg: 'كجم', g: 'جم', pc: 'قطعة', pcs: 'قطعة', unit: 'وحدة', tablet: 'قرص', box: 'علبة', L: 'لتر', mL: 'مل', MT: 'طن' };
  PATTERNS.push(
    [new RegExp('^' + DATE + '$'), arDate], [new RegExp('^sent ' + DATE + '$'), function (m) { var d = arDate(m); return d ? 'أُرسل ' + d : null; }],
    [new RegExp('^' + GB + '$'), gbDate], [new RegExp('^sent ' + GB + '$'), function (m) { var d = gbDate(m); return d ? 'أُرسل ' + d : null; }],
    [/^(\d+) completed orders?$/, function (m) { return m[1] + ' ' + plural(m[1], ['طلب مكتمل', 'طلبات مكتملة']); }], [/^(\d+)% on time$/, function (m) { return m[1] + '% في الموعد'; }],
    [/^replies in ~(<1|\d+)h$/, function (m) { return m[1] === '<1' ? 'يرد خلال أقل من ساعة' : 'يرد خلال ~' + m[1] + ' ' + unit(m[1], 'h'); }], [/^valid to (\d{4}-\d{2}(?:-\d{2})?)$/, function (m) { return 'صالح حتى ' + m[1]; }],
    [/^\((sales|business development)\) at (.+)$/, function (m) { return '(' + (m[1] === 'sales' ? 'المبيعات' : 'تطوير الأعمال') + ') في ' + m[2]; }],
    [new RegExp('^valid until ' + GB + '$'), function (m) { var d = gbDate(m); return d ? 'صالح حتى ' + d : null; }], [new RegExp('^renews ' + GB + '$'), function (m) { var d = gbDate(m); return d ? 'يتجدد في ' + d : null; }], [new RegExp('^expired ' + GB + '$'), function (m) { var d = gbDate(m); return d ? 'انتهى في ' + d : null; }],
    [new RegExp('^This offer expired on ' + GB + ' — ask for a new quote \\(counter-offer\\)$'), function (m) { var d = gbDate(m); return d ? 'انتهى هذا العرض في ' + d + ' — اطلب عرض سعر جديدًا (عرض مضاد)' : null; }],
    [/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})$/, function (m) { return MON[m[1]] + ' ' + m[2]; }],
    [/^(Sat|Sun|Mon|Tue|Wed|Thu|Fri): (\d+)$/, function (m) { return WDAY[m[1]] + ': ' + m[2]; }],
    [/^(≈ )?EGP ([\d,.]+)$/, function (m) { return (m[1] || '') + m[2] + ' ج.م'; }], [/^EGP ([\d,.]+)\/(\w+)$/, function (m) { return m[1] + ' ج.م/' + (UNIT[m[2]] || m[2]); }],
    [/^EGP ([\d,.]+) per (\w+)$/, function (m) { return m[1] + ' ج.م لكل ' + (UNIT[m[2]] || m[2]); }], [/^Approximate, at ([\d.,]+) EGP per USD$/, function (m) { return 'تقريبي، بسعر ' + m[1] + ' ج.م للدولار'; }],
    [/^([\d.]+) g\/mol$/, function (m) { return m[1] + ' جم/مول'; }], [/^Chemical structure of (.+)$/, function (m) { return 'التركيب الكيميائي لـ ' + m[1]; }],
    [/^Go to (.+)$/, function (m) { return 'انتقل إلى ' + (D[m[1]] || m[1]); }], [/^(\d) of 4 selected$/, function (m) { return m[1] + ' من 4 محددة'; }], [/^Compare (\d)$/, function (m) { return 'قارن ' + m[1]; }],
    [/^No results for “(.+)”\. Try a product, a company or a person\.$/, function (m) { return 'لا نتائج لـ “' + m[1] + '”. جرّب اسم منتج أو شركة أو شخص.'; }],
    [/^Search saved — alerts (instant|daily|weekly)$/, function (m) { return 'تم حفظ البحث — التنبيهات ' + ({ instant: 'فورية', daily: 'يومية', weekly: 'أسبوعية' })[m[1]]; }],
    [/^Showing “(.+)”$/, function (m) { return 'عرض “' + m[1] + '”'; }], [/^(\d+) new$/, function (m) { return m[1] + ' ' + plural(m[1], ['جديد', 'جديدة']); }],
    [/^Remove “(.+)” to see (\d+) listings?$/, function (m) { return 'أزل “' + (D[m[1]] || m[1]) + '” لترى ' + m[2] + ' ' + plural(m[2], WORDS.listings); }],
    [/^Call ([A-Z].+)$/, function (m) { return 'اتصال بـ ' + m[1]; }], [/^Company phone of (.+):$/, function (m) { return 'هاتف شركة ' + m[1] + ':'; }],
    [/^(.+) has not shared a phone number\. Send a message and ask for a call — the quick reply “Schedule a call” does it in one tap\.$/, function (m) { return m[1] + ' لم يشارك رقم هاتف. أرسل رسالة واطلب مكالمة — الرد السريع “حدّد موعد مكالمة” يفعلها بلمسة واحدة.'; }],
    [/^(.+) has no public profile yet$/, function (m) { return 'لا يوجد ملف عام لـ ' + m[1] + ' بعد'; }], [/^and (\d+) more in your network$/, function (m) { return 'و' + m[1] + ' آخرون في شبكتك'; }],
    [/^You endorsed (.+)$/, function (m) { return 'أيّدت ' + m[1]; }], [/^You are acting as (.+)$/, function (m) { return 'أنت تتصرف باسم ' + m[1]; }],
    [/^(.+)’s workspace$/, function (m) { return 'مساحة عمل ' + m[1]; }], [/^Open (.+)’s page$/, function (m) { return 'افتح صفحة ' + m[1]; }],
    [/^Verification level (\d) of 3: (Registered|Licensed|Inspected|Not verified)$/, function (m) { return 'مستوى التوثيق ' + m[1] + ' من 3: ' + (D[m[2]] || m[2]); }],
    [/^Supplier status for (.+)$/, function (m) { return 'حالة المورّد: ' + m[1]; }],
    [/^(\S+) (Supply|Demand|CMO|Equipment|License|Service|Job|Training) (\d+)$/, function (m) { var w = D[m[2]] || ({ CMO: 'تصنيع لدى الغير', License: 'ترخيص', Service: 'خدمة' })[m[2]]; return m[1] + ' ' + w + ' ' + m[3]; }],
    [/^Request a quote from (.+)$/, function (m) { return 'اطلب عرض سعر من ' + m[1]; }], [/^QR code — (.+)$/, function (m) { return 'رمز QR — ' + m[1]; }],
    [/^Report wrong information — (.+)$/, function (m) { return 'الإبلاغ عن معلومة خاطئة — ' + m[1]; }], [/^Verify ([A-Z].+)$/, function (m) { return 'توثيق ' + m[1]; }],
    [/^Sent by (.+)$/, function (m) { return 'مُرسل من ' + m[1]; }], [/^Approved suppliers of (.+)$/, function (m) { return 'المورّدون المعتمدون لدى ' + m[1]; }], [/^(.+) \(you\)$/, function (m) { return m[1] + ' (أنت)'; }],
    [/^Set a status from any supplier page \(while acting as (.+)\) or send a qualification questionnaire\.$/, function (m) { return 'حدّد الحالة من صفحة أي مورّد (أثناء التصرف باسم ' + m[1] + ') أو أرسل استبيان تأهيل.'; }],
    [/^⏱ (\d+) hours?$/, function (m) { return '⏱ ' + m[1] + ' ' + plural(m[1], ['ساعة', 'ساعات']); }], [/^valid (\d+) days$/, function (m) { return 'صالح ' + m[1] + ' ' + plural(m[1], ['يوم', 'أيام']); }],
    [/^You're in the top (\d+)% of active members across your (\d+) groups this month\.$/, function (m) { return 'أنت ضمن أنشط ' + m[1] + '% من الأعضاء في مجموعاتك (' + m[2] + ') هذا الشهر.'; }]
  );
  PATTERNS.push(   /* groups (groups.js) */
    [/^(Members|Admins) \(([\d,]+)\)$/, function (m) { return D[m[1]] + ' (' + m[2] + ')'; }],
    [/^\+ ([\d,]+) more members?$/, function (m) { return '+ ' + m[1] + ' ' + plural(m[1], ['عضو آخر', 'أعضاء آخرين']); }],
    [/^Joined (\d+) (year|month|week|day)s? ago$/, function (m) { return 'انضم منذ ' + m[1] + ' ' + plural(m[1], ({ year: ['سنة', 'سنوات'], month: ['شهر', 'أشهر'], week: ['أسبوع', 'أسابيع'], day: ['يوم', 'أيام'] })[m[2]]); }],
    [/^(\d+)\s*(mo|y) ago$/, function (m) { return 'منذ ' + m[1] + ' ' + plural(m[1], m[2] === 'mo' ? ['شهر', 'أشهر'] : ['سنة', 'سنوات']); }],
    [/^reported by 1 member$/, function () { return 'أبلغ عنه عضو واحد'; }], [/^reported by ([\d,]+) members$/, function (m) { return 'أبلغ عنه ' + m[1] + ' ' + plural(m[1], ['عضو', 'أعضاء']); }],
    [/^([\d,]+) real members and their history live in this group\. Choose carefully\.$/, function (m) { return 'في هذه المجموعة ' + m[1] + ' ' + plural(m[1], ['عضو حقيقي', 'أعضاء حقيقيين']) + ' وتاريخهم. اختر بعناية.'; }],
    [/^Removes all ([\d,]+) members & history forever\. No recovery\.$/, function (m) { return 'يحذف كل الأعضاء (' + m[1] + ') وتاريخهم نهائيًا. لا يمكن الاسترجاع.'; }],
    [/^This will permanently remove all ([\d,]+) members, every post, and the full history\. There is no undo\.$/, function (m) { return 'سيُحذف نهائيًا كل الأعضاء (' + m[1] + ') وكل المنشورات والتاريخ كاملًا. لا يمكن التراجع.'; }],
    [/^You’ll stop seeing posts from (.+) and lose access to its members and listings\.$/, function (m) { return 'لن ترى منشورات ' + m[1] + ' بعد الآن، وستفقد الوصول إلى أعضائها وإعلاناتها.'; }],
    [/^Delete "(.+)"\?$/, function (m) { return 'حذف "' + m[1] + '"؟'; }], [/^Remove (.+)\?$/, function (m) { return 'إزالة ' + m[1] + '؟'; }],
    [/^Request sent to the admins of (.+)$/, function (m) { return 'تم إرسال طلبك إلى مديري ' + m[1]; }], [/^Quote sent to (.+)$/, function (m) { return 'تم إرسال العرض إلى ' + m[1]; }],
    [/^(.+) removed from the group$/, function (m) { return 'أُزيل ' + m[1] + ' من المجموعة'; }], [/^(.+) was deleted permanently$/, function (m) { return 'حُذفت ' + m[1] + ' نهائيًا'; }],
    [/^1 new post this week$/, function () { return 'منشور جديد واحد هذا الأسبوع'; }],
    [/^asked to join the private group "(.+)"$/, function (m) { return 'طلب الانضمام إلى المجموعة الخاصة "' + m[1] + '"'; }],   /* live notifications (0027) */
    [/^approved your request to join "(.+)"$/, function (m) { return 'وافق على طلب انضمامك إلى "' + m[1] + '"'; }],
    [/^The group's admins declined your last request — you can ask again from (\d{4}-\d{2}-\d{2})$/, function (m) { return 'رفض مديرو المجموعة طلبك السابق — يمكنك الطلب مرة أخرى بدءًا من ' + m[1]; }],
    [/^(.+) is now an admin$/, function (m) { return m[1] + ' — مدير الآن'; }], [/^(.+) is now a sub-admin$/, function (m) { return m[1] + ' — مشرف الآن'; }], [/^(.+) is now a member$/, function (m) { return m[1] + ' — عضو الآن'; }]
  );
  /* phase 1: what the live app shows instead of sample numbers and cards (groups, marketplace, my listings) */
  Object.assign(D, {
    'Loading…': 'جارٍ التحميل…', 'Loading groups…': 'جارٍ تحميل المجموعات…', 'You have not joined a group yet.': 'لم تنضم إلى أي مجموعة بعد.',
    'You have not joined a group yet — join one below or create your own.': 'لم تنضم إلى أي مجموعة بعد — انضم إلى واحدة بالأسفل أو أنشئ مجموعتك.',
    'No other discussion groups yet — create the first one.': 'لا توجد مجموعات نقاش أخرى بعد — أنشئ الأولى.', 'No other deal rooms yet — create the first one.': 'لا توجد غرف صفقات أخرى بعد — أنشئ الأولى.',
    'new posts today in your groups': 'منشورات جديدة اليوم في مجموعاتك', 'Groups you have not joined yet — most active first': 'مجموعات لم تنضم إليها بعد — الأكثر نشاطًا أولًا',
    'You have not joined a group yet — find one on the Groups page.': 'لم تنضم إلى أي مجموعة بعد — ابحث عن واحدة في صفحة المجموعات.',
    'Boost your listing — show it at the top of the marketplace': 'روّج لإعلانك — اعرضه في أعلى السوق', 'Boosted and featured listings appear before free ones': 'الإعلانات المروّجة والمميّزة تظهر قبل الإعلانات المجانية',
    'Show your listing at the top of the marketplace, before free listings.': 'اعرض إعلانك في أعلى السوق، قبل الإعلانات المجانية.',
    'Nothing posted yet — new listings show here as they are posted.': 'لا شيء منشور بعد — تظهر الإعلانات الجديدة هنا فور نشرها.',
    'No services listed yet — offer yours with “+ Offer Service”.': 'لا توجد خدمات بعد — اعرض خدمتك من «+ قدّم خدمة».',
    'No open jobs yet — post the first one with “+ Post a Job”.': 'لا توجد وظائف متاحة بعد — انشر الأولى من «+ انشر وظيفة».',
    'No open requests yet.': 'لا توجد طلبات مفتوحة بعد.', 'No open jobs yet.': 'لا توجد وظائف متاحة بعد.',
    'You have no listings yet — publish one with “New Listing”.': 'ليس لديك إعلانات بعد — انشر إعلانًا من «إعلان جديد».',
    'Boosted': 'مروّج', 'Open request': 'طلب مفتوح', 'professional — graduates, specialists and industry veterans': 'متخصص — خريجون ومتخصصون وخبراء صناعة'
  });
  /* phase 1b: Messages, sign-up and connection texts that stayed English in the Arabic interface */
  Object.assign(D, {
    'No conversations yet.': 'لا توجد محادثات بعد.', 'No conversations yet': 'لا توجد محادثات بعد', "Open someone's profile and press Message.": 'افتح ملف أحد الأعضاء واضغط «رسالة».',
    'To *': 'إلى *', 'Connected! 🤝': 'تم الاتصال! 🤝', 'Choose your specialty…': 'اختر تخصصك…'
  });
  /* phase 1b: the Arabic leftovers on the pages phase 1 touched — company pages, the create wizard, the marketplace (create, intents,
     my listings), messages, Admin → Review (P1b polish). Interface words only; what members wrote stays as written. */
  Object.assign(D, {
    /* company page, workspace and the create wizard */
    'Owner': 'المالك', 'No description yet.': 'لا يوجد وصف بعد.', 'No credentials listed.': 'لا توجد اعتمادات مدرجة.', 'No live listings.': 'لا توجد إعلانات حالية.',
    'No open positions.': 'لا توجد وظائف متاحة.', 'Do it': 'نفّذ', 'Reply to a request or update your page to show as Active.': 'رد على طلب أو حدّث صفحتك لتظهر كنشطة.',
    'Tell buyers what you make or offer.': 'أخبر المشترين بما تصنعه أو تقدّمه.', 'View in Marketplace': 'اعرض في السوق', 'Still correct': 'لا تزال صحيحة',
    'May be outdated': 'قد تكون قديمة', 'Thanks — marked as up to date': 'شكرًا — عُلّمت كمحدّثة', 'Licensing': 'ترخيص',
    'A company exists once on Drugbox. Search first — if it is already here, claim it instead of creating a copy.': 'كل شركة موجودة مرة واحدة على Drugbox. ابحث أولًا — إن كانت موجودة فطالب بها بدلًا من إنشاء نسخة.',
    'Company name': 'اسم الشركة', 'Arabic or English': 'بالعربية أو الإنجليزية', 'My company is not listed — create it': 'شركتي غير مدرجة — أنشئها',
    'Company legal name *': 'الاسم القانوني للشركة *', 'Main activity *': 'النشاط الرئيسي *', 'Governorate *': 'المحافظة *', 'City / area *': 'المدينة / المنطقة *',
    'Company phone *': 'الهاتف للشركة *', 'Company email *': 'البريد الإلكتروني للشركة *', 'Next: review': 'التالي: المراجعة', 'Create my page': 'أنشئ صفحتي',
    'Claim': 'طالب بها', 'Open workspace': 'افتح مساحة العمل', 'Ask to join the team': 'اطلب الانضمام للفريق',
    'Subtotal': 'المجموع الفرعي', 'VAT 14%': 'ضريبة القيمة المضافة 14%', 'Total': 'الإجمالي', 'Bank transfer': 'تحويل بنكي', 'Demo — no payment is taken.': 'نسخة تجريبية — لا يُخصم أي مبلغ.',
    /* the company workspace (found by the Arabic sweep of its tabs) */
    'Nothing yet': 'لا شيء بعد', 'No requests yet.': 'لا توجد طلبات بعد.', 'No listings yet.': 'لا توجد إعلانات بعد.', 'Not verified yet.': 'غير موثّقة بعد.',
    'Documents received — being checked.': 'استلمنا المستندات — قيد الفحص.', 'Get verified': 'وثّق شركتك', 'Get VIP': 'احصل على VIP',
    'Appear in the Sponsored row of the directory, with your own link and Marketplace boosts. It never changes search order or trust.': 'اظهر في صف الشركات المُموَّلة في الدليل، برابطك الخاص وترويج إعلاناتك في السوق. لا يغيّر ذلك ترتيب البحث ولا الثقة أبدًا.',
    'Verification': 'التوثيق', 'Plan': 'الخطة','Optional, later — from your page (gives the Verified badge)': 'اختياري، لاحقًا — من صفحتك (يمنح شارة «موثّق»)',
    /* Admin → Review */
    'Review': 'المراجعة', '🛡️ Review': '🛡️ المراجعة', 'Decisions here change what everyone sees — verification, published warnings, level 3.': 'القرارات هنا تغيّر ما يراه الجميع — التوثيق والتحذيرات المنشورة والمستوى 3.',
    'Verification requests': 'طلبات التوثيق', 'Warning references': 'مراجع التحذير', 'Site certificates': 'شهادات المواقع', 'Company reports': 'بلاغات الشركات',
    'Mark checked': 'علّم كمراجَعة', 'Could not save the decision': 'تعذّر حفظ القرار', 'Documents open in the live app': 'تُفتح المستندات في التطبيق الفعلي',
    'It will not be published.': 'لن يُنشر.', 'Mark this transfer as not received?': 'هل تعلّم هذا التحويل كغير مستلَم؟', 'Reject this reference?': 'هل ترفض هذه المرجعية؟',
    'The company page stays as it is.': 'تبقى صفحة الشركة كما هي.', 'The order stays unpaid.': 'يبقى الطلب غير مدفوع.', 'The registry document is not readable': 'مستند السجل غير مقروء',
    'admin': 'مدير', 'user': 'مستخدم',   /* the role pills on Admin → Users */
    'Admin access required': 'يلزم صلاحية الإدارة', 'Your account is not allowed here — Admin is for Drugbox staff.': 'غير مسموح لحسابك هنا — الإدارة لفريق Drugbox فقط.',
    /* messages */
    'To *': 'إلى *', 'No conversations yet.': 'لا توجد محادثات بعد.', 'No conversations yet': 'لا توجد محادثات بعد', "Open someone's profile and press Message.": 'افتح ملف أحد الأعضاء واضغط «مراسلة».',
    'Choose a conversation': 'اختر محادثة', 'Connected! 🤝': 'تم الاتصال! 🤝',
    /* marketplace: browse */
    'No supply listings yet — be the first to post one.': 'لا توجد إعلانات عرض بعد — كن أول من ينشر واحدًا.', '⚙ Filters': '⚙ الفلاتر', '✕ Close filters': '✕ أغلق الفلاتر',
    'Filters': 'الفلاتر', 'Filters reset': 'أُعيد ضبط الفلاتر', 'Contact Supplier': 'تواصل مع المورّد', 'Request Quote': 'اطلب عرض سعر',
    /* marketplace: create a listing */
    'Create a Listing': 'أنشئ إعلانًا', 'Step 1 of 2 — Are you seeking or offering?': 'الخطوة 1 من 2 — هل تبحث أم تعرض؟', 'Step 2 of 2 — Choose a category': 'الخطوة 2 من 2 — اختر فئة',
    'Are you seeking something, or offering something?': 'هل تبحث عن شيء أم تعرض شيئًا؟', "I'm Offering": 'أعرض', 'I have something to give': 'لدي ما أقدّمه',
    "I'm Seeking": 'أبحث', 'I need something': 'أحتاج شيئًا', 'Draft auto-saved — you can leave and continue anytime from "My Listings"': 'حُفظت المسودة تلقائيًا — يمكنك المغادرة والمتابعة في أي وقت من «إعلاناتي»',
    '← Change': '→ تغيير', 'New Supply Listing': 'إعلان عرض جديد', 'For raw materials, APIs, excipients & finished products': 'للمواد الخام والمواد الفعالة والسواغات والمنتجات النهائية',
    'Material / Product name': 'اسم المادة / المنتج', 'Pharmacopoeia Grade': 'درجة دستور الأدوية', 'Price per unit': 'السعر للوحدة', 'per kg': 'للكيلوجرام', 'per ton': 'للطن', 'per unit': 'للوحدة',
    'MOQ': 'الحد الأدنى للطلب', 'Certifications available': 'الشهادات المتاحة', 'Selected certs show as "claimed" until you upload proof for verification': 'تظهر الشهادات المختارة «مُدّعاة» حتى ترفع ما يثبتها للتوثيق',
    'Origin country / Manufacturing site': 'بلد المنشأ / موقع التصنيع', 'Lead time & shipping terms': 'مدة التوريد وشروط الشحن', 'COA / Spec sheet': 'شهادة التحليل / المواصفات', 'Upload': 'ارفع',
    'Certificate of Analysis or spec sheet (PDF)': 'شهادة التحليل أو ورقة المواصفات (PDF)', 'Save as Draft': 'احفظ كمسودة', 'Preview Listing': 'معاينة الإعلان',
    'New Demand Request': 'طلب شراء جديد', "Tell suppliers exactly what you're looking for": 'أخبر المورّدين بما تبحث عنه بالضبط', 'What are you looking for?': 'عمّ تبحث؟',
    'Quantity needed': 'الكمية المطلوبة', 'Contract type': 'نوع التعاقد', 'One-time order': 'طلب لمرة واحدة', 'Annual contract': 'عقد سنوي', 'Trial order first': 'طلب تجريبي أولًا',
    'Required certifications': 'الشهادات المطلوبة', 'Target price (optional)': 'السعر المستهدف (اختياري)', 'Urgency': 'الاستعجال', 'Flexible': 'مرن', 'This month': 'هذا الشهر', 'Urgent': 'عاجل',
    'Additional details': 'تفاصيل إضافية', 'New CMO Listing': 'إعلان تصنيع لدى الغير جديد', 'For contract & toll manufacturing facilities': 'لمنشآت التصنيع التعاقدي والتصنيع لدى الغير',
    'Facility / Service name': 'اسم المنشأة / الخدمة', 'Dosage forms produced': 'الأشكال الصيدلانية المنتجة', 'Liquids': 'سوائل', 'Creams/Ointments': 'كريمات/مراهم', 'Injectables': 'حقن',
    'Annual capacity': 'الطاقة السنوية', 'Min. batch size': 'أقل حجم تشغيلة', 'Facility certifications': 'شهادات المنشأة', 'Services included': 'الخدمات المشمولة', 'Tech transfer': 'نقل التقنية',
    'NDA filing support': 'دعم تقديم ملفات التسجيل', 'Custom packaging': 'تعبئة حسب الطلب', 'Export markets covered': 'أسواق التصدير المغطاة', 'Facility photos / GMP certificate': 'صور المنشأة / شهادة GMP',
    'facility photos and certification documents': 'صور المنشأة ومستندات الشهادات', 'List Equipment': 'أدرج معدات', 'For machinery, lab instruments & production equipment': 'للآلات وأجهزة المعامل ومعدات الإنتاج',
    'Equipment name': 'اسم المعدة', 'Tablet Press': 'مكبس أقراص', 'Filling Line': 'خط تعبئة', 'Lab Instrument': 'جهاز معمل', 'Packaging Machine': 'ماكينة تغليف', 'Condition': 'الحالة',
    'Used': 'مستعمل', 'Refurb.': 'مُجدَّد', 'Manufacture year': 'سنة الصنع', 'Capacity / Output': 'الطاقة / الإنتاج', 'Asking price': 'السعر المطلوب', 'Validation documents available': 'مستندات التأهيل المتاحة',
    'Service history': 'سجل الصيانة', 'CE Marking': 'علامة CE', 'Location / Pickup': 'الموقع / الاستلام', 'Photos of equipment': 'صور المعدة', 'multiple angles + service records': 'زوايا متعددة + سجلات الصيانة',
    'Sell a License / Registration': 'بيع ترخيص / تسجيل', 'For product registrations, trademarks & regulatory dossiers': 'لتسجيلات المنتجات والعلامات التجارية وملفات التسجيل',
    'Product / Registration name': 'اسم المنتج / التسجيل', 'Registering authority': 'جهة التسجيل', 'EDA (Egypt)': 'هيئة الدواء (مصر)', 'SFDA (Saudi)': 'SFDA (السعودية)', 'DHA (Dubai)': 'DHA (دبي)',
    'MOHAP (UAE)': 'MOHAP (الإمارات)', 'Registration status': 'حالة التسجيل', 'Active & valid': 'سارٍ وصالح', 'Pending renewal': 'بانتظار التجديد', 'Dossier only': 'الملف فقط',
    "What's included in the sale": 'ما يشمله البيع', 'Brand name rights': 'حقوق الاسم التجاري', 'Formula/dossier': 'التركيبة/الملف', 'Manufacturing rights': 'حقوق التصنيع', 'Trademark': 'العلامة التجارية',
    'Transfer terms': 'شروط النقل', 'Registration certificate': 'شهادة التسجيل', 'official registration document for verification': 'مستند التسجيل الرسمي للتوثيق',
    'Offer a Service': 'قدّم خدمة', 'For consulting, regulatory, lab testing & advisory services': 'للاستشارات والتسجيل والتحاليل المعملية والخدمات الاستشارية', 'Service name': 'اسم الخدمة',
    'Service category': 'فئة الخدمة', 'Regulatory & Registration': 'الشؤون التنظيمية والتسجيل', 'Lab Testing': 'التحاليل المعملية', 'QA/QC Consulting': 'استشارات ضمان/مراقبة الجودة',
    'Dossier Preparation': 'إعداد الملفات', 'Pricing model': 'نموذج التسعير', 'Per project': 'للمشروع', 'Per hour/day': 'للساعة/لليوم', 'Free consult': 'استشارة مجانية',
    'Your experience / track record': 'خبرتك / سجل أعمالك', 'Coverage area': 'نطاق التغطية', 'RAC Certified': 'حاصل على RAC', 'Description of service': 'وصف الخدمة',
    'For full-time, part-time, or contract positions': 'لوظائف الدوام الكامل أو الجزئي أو التعاقد', 'Job title': 'المسمى الوظيفي', 'Employment type': 'نوع التوظيف', 'Salary': 'الراتب',
    'Show range': 'اعرض النطاق', '"Competitive" (hidden)': '«تنافسي» (مخفي)', 'EDA Knowledge': 'معرفة بهيئة الدواء', 'GMP Auditing': 'تدقيق GMP', 'Job description & responsibilities': 'الوصف الوظيفي والمسؤوليات',
    'Create a Course': 'أنشئ دورة', 'For workshops, certifications & training programs': 'لورش العمل والشهادات والبرامج التدريبية', 'Course title': 'عنوان الدورة', 'Format': 'الشكل',
    'In-person': 'حضوري', 'Hybrid': 'مدمج', 'Duration': 'المدة', 'Course date(s)': 'تاريخ (تواريخ) الدورة', 'Max participants': 'أقصى عدد مشاركين', 'Price per seat': 'السعر للمقعد',
    'Topics covered': 'الموضوعات المغطاة', 'CTD Structure': 'هيكل CTD', 'Stability Studies': 'دراسات الثبات', 'Ministerial Decree 122': 'القرار الوزاري 122',
    'Certificate provided on completion?': 'هل تُمنح شهادة عند الإتمام؟', 'Yes': 'نعم', 'No': 'لا', 'Instructor credentials': 'مؤهلات المحاضر',
    'Helps suppliers quote accurately': 'يساعد المورّدين على التسعير بدقة', 'Any other specs, preferred origin, etc.': 'أي مواصفات أخرى أو منشأ مفضّل وغير ذلك',
    'Negotiable, or specify amount': 'قابل للتفاوض، أو حدّد المبلغ', '📅 Select date(s)': '📅 اختر التاريخ (التواريخ)',
    /* marketplace: my intents */
    'My Marketplace Intents': 'أهدافي في السوق', 'Tell Drugbox what you have and what you need, per category — this powers your matches, your feed, and what shows on your profile.': 'أخبر Drugbox بما لديك وما تحتاجه في كل فئة — هذا يحدد ما يطابقك وما يظهر في خلاصتك وفي ملفك.',
    'How to read every toggle below': 'كيف تقرأ كل اختيار بالأسفل', 'One side always means': 'أحد الجانبين يعني دائمًا', '"I already HAVE this / I provide this"': '«لدي هذا بالفعل / أقدّم هذا»',
    '— shown in green. The other side always means': '— ويظهر بالأخضر. والجانب الآخر يعني دائمًا', '"I NEED this / I\'m looking for this"': '«أحتاج هذا / أبحث عن هذا»',
    '— shown in orange. Every label is written in plain words from your point of view — never abstract "Offer" or "Seek" alone.': '— ويظهر بالبرتقالي. كل عنوان مكتوب بكلمات بسيطة من وجهة نظرك — لا «عرض» أو «طلب» مجردين.',
    'Set all to "I have / provide"': 'اجعل الكل «لدي / أقدّم»', 'Set all to "I need"': 'اجعل الكل «أحتاج»', 'Set all to "Both"': 'اجعل الكل «الاثنان»',
    'Materials & Products': 'المواد والمنتجات', 'APIs & Raw Materials': 'المواد الفعالة والخامات', 'e.g. Metformin HCl, Neomycin Sulphate': 'مثلًا Metformin HCl وNeomycin Sulphate',
    'I have this to sell': 'لدي هذا للبيع', 'I need to buy this': 'أحتاج شراء هذا', 'Both': 'الاثنان', 'Cosmetic Ingredients': 'مكونات التجميل', 'e.g. Hyaluronic Acid, Niacinamide': 'مثلًا Hyaluronic Acid وNiacinamide',
    'Supplement Ingredients': 'مكونات المكملات', 'e.g. vitamins, nutraceutical raw materials': 'مثلًا الفيتامينات وخامات المكملات الغذائية', '— Not active here': '— غير نشط هنا',
    'Packaging Materials': 'مواد التعبئة والتغليف', 'e.g. blister packs, cartons, labels': 'مثلًا البلستر والكرتون والملصقات', 'Facilities & Equipment': 'المنشآت والمعدات',
    'CMO / Contract Manufacturing': 'التصنيع لدى الغير / التعاقدي', "e.g. your facility's production capacity": 'مثلًا الطاقة الإنتاجية لمنشأتك', 'I have a facility to offer': 'لدي منشأة أعرضها',
    'I need a manufacturer': 'أحتاج مصنّعًا', 'e.g. tablet presses, lab instruments': 'مثلًا مكابس الأقراص وأجهزة المعامل', 'I have one to sell': 'لدي واحدة للبيع', 'I want to buy one': 'أريد شراء واحدة',
    'IP & Regulatory': 'الملكية الفكرية والتسجيل', 'Licenses & Registrations': 'التراخيص والتسجيلات', 'e.g. product registration for sale': 'مثلًا تسجيل منتج للبيع', "I'm selling a registration": 'أبيع تسجيلًا',
    'Professional Services': 'الخدمات المهنية', 'e.g. EDA registration, QA consulting': 'مثلًا التسجيل في هيئة الدواء واستشارات الجودة', 'I provide this service': 'أقدّم هذه الخدمة',
    'I need this service': 'أحتاج هذه الخدمة', 'Career & Knowledge': 'المهنة والمعرفة', 'Are you hiring, or are you the candidate?': 'هل توظّف أم أنت المرشّح؟', 'I need to hire someone': 'أحتاج توظيف أحد',
    "I'm looking for a job": 'أبحث عن وظيفة', 'Training & Courses': 'التدريب والدورات', 'Are you the instructor, or the student?': 'هل أنت المحاضر أم المتدرّب؟', 'I teach this course': 'أقدّم هذه الدورة',
    'I want to take a course': 'أريد حضور دورة', 'How this appears on your profile': 'كيف يظهر هذا في ملفك', 'Save My Intents': 'احفظ أهدافي', 'Nothing selected yet': 'لم تختر شيئًا بعد',
    'APIs': 'المواد الفعالة', 'CMO': 'التصنيع لدى الغير',
    /* marketplace: my listings */
    'Manage Listings': 'إدارة الإعلانات', 'Manage, edit, boost or remove your active listings': 'أدِر إعلاناتك النشطة: عدّلها أو روّج لها أو احذفها', 'New Listing': 'إعلان جديد',
    'Active Listings': 'الإعلانات النشطة', 'Total Views': 'إجمالي المشاهدات', 'Inquiries': 'الاستفسارات', 'Renew Now': 'جدّد الآن', 'Expiring soon': 'ينتهي قريبًا', 'Paused': 'متوقف مؤقتًا', 'Resume': 'استأنف',
    'views': 'مشاهدات', 'inquiries': 'استفسارات', 'not verified': 'غير موثّقة', 'License': 'ترخيص', 'Service': 'خدمة'
  });
  /* ===== AREA business: company page, certificates, team (B-02, B-03, B-04) ===== */
  Object.assign(D, {
    'E-mail me about requests, deals, payments and my company': 'راسلني بالبريد بخصوص الطلبات والصفقات والمدفوعات وشركتي', 'E-mails on — we will write when something needs you': 'تم تشغيل البريد — سنراسلك عندما يحتاجك أمر ما', 'E-mails off — notifications stay here': 'تم إيقاف البريد — تبقى الإشعارات هنا',
    'no free slot soon': 'لا مواعيد متاحة قريبًا', 'Claim this page': 'طالب بهذه الصفحة', 'selected': 'مختارة', 'Goes to': 'يذهب إلى', 'Free from': 'متاح من', 'business development': 'تطوير الأعمال', 'sales': 'المبيعات',
    'Not paid by then, it simply expires — nothing is charged': 'إن لم يُدفع حتى ذلك الحين ينتهي ببساطة — دون أي خصم',
    'No active listing to promote — publish or renew one first': 'لا يوجد إعلان نشط للترويج — انشر إعلانًا أو جدّده أولًا',
    'Back': 'رجوع', 'tablets': 'أقراص', 'sachets': 'أكياس', 'tubes': 'أنابيب', 'vials': 'فيالات', 'bottles': 'زجاجات',
    'Add a membership': 'إضافة عضوية', 'Organisation *': 'الجهة *', 'Chamber of Pharmaceutical Industries': 'غرفة صناعة الدواء', 'Chamber of Cosmetics Industries': 'غرفة صناعة مستحضرات التجميل',
    'Export Council for Medical Industries': 'المجلس التصديري للصناعات الطبية', 'Egyptian Pharmaceutical Trading Association': 'الجمعية المصرية لتجارة الأدوية',
    'Drugbox checks the membership with the organisation before the badge shows as confirmed.': 'يتحقق Drugbox من العضوية مع الجهة قبل أن تظهر الشارة مؤكدة.', 'Being checked by Drugbox': 'قيد المراجعة من Drugbox', 'Membership number *': 'رقم العضوية *',
    'File (PDF or image, optional)': 'الملف (PDF أو صورة، اختياري)', 'Site master file': 'ملف الموقع الرئيسي (SMF)', 'Manufacturing licence': 'ترخيص التصنيع', 'Membership': 'عضوية', 'Memberships': 'العضويات',
    'Shown as self-declared until Drugbox checks the document. The file is seen only by your team and Drugbox’s reviewers.': 'يظهر كمُصرَّح به حتى يراجع Drugbox المستند. لا يرى الملف إلا فريقك ومراجعو Drugbox.',
    'Document added — Drugbox will check it': 'تمت إضافة المستند — سيراجعه Drugbox', 'Delete this document?': 'هل تحذف هذا المستند؟', 'Document deleted': 'تم حذف المستند', 'Not accepted': 'غير مقبول',
    'The file is larger than 10 MB': 'الملف أكبر من 10 ميجابايت', 'In this demo the file stays on the computer it was added from': 'في هذا العرض يبقى الملف على الجهاز الذي أُضيف منه',
    'Compliance documents': 'مستندات الامتثال', 'Mark verified': 'وثّقه', 'Reject this document?': 'هل ترفض هذا المستند؟', 'The document file is not readable': 'ملف المستند غير مقروء',
    'It shows as not accepted on the company’s passport and the person who added it is told why.': 'سيظهر كغير مقبول في جواز امتثال الشركة ويُبلَّغ من أضافه بالسبب.',
    'This document was already decided': 'تم البت في هذا المستند بالفعل', 'Only the company’s owners and admins, or the person who added it, can delete this document': 'لا يحذف هذا المستند إلا مالكو الشركة ومديروها أو من أضافه',
    'not yet checked': 'لم تُراجع بعد', 'not yet checked by Drugbox': 'لم يراجعها Drugbox بعد', 'Public industry list': 'قائمة صناعية عامة', 'Company-wide': 'على مستوى الشركة',
    'Asked to join the team': 'طلب الانضمام للفريق', 'Invited — waiting for them to accept': 'تمت دعوته — بانتظار قبوله', 'Your role *': 'دورك *', 'Note for the admin': 'ملاحظة للمدير',
    'e.g. I work in the Cairo sales office': 'مثلًا: أعمل في مكتب مبيعات القاهرة', 'Request declined': 'تم رفض الطلب', 'Invitation declined': 'تم رفض الدعوة',
    'You joined the team — the company is in My companies': 'انضممت إلى الفريق — الشركة الآن في شركاتي', 'The page’s owner stays its owner': 'مالك الصفحة يبقى مالكها',
    'Write the reason for the company': 'اكتب السبب للشركة', 'The certificate document is not readable': 'مستند الشهادة غير مقروء', 'Site added': 'تمت إضافة الموقع',
    'Certificate added': 'تمت إضافة الشهادة', 'Capabilities saved': 'تم حفظ القدرات', 'Invitation sent': 'تم إرسال الدعوة', 'Company page published': 'تم نشر صفحة الشركة',
    'Page saved': 'تم حفظ الصفحة', 'Arabic name saved': 'تم حفظ الاسم العربي', 'Thanks — marked as up to date': 'شكرًا — تم تعليمها كمحدّثة', 'Could not send the request': 'تعذّر إرسال الطلب',
    'Could not answer the request': 'تعذّر الرد على الطلب', 'This company is not on Drugbox yet': 'هذه الشركة ليست على Drugbox بعد',
    'Reject this certificate?': 'هل ترفض هذه الشهادة؟', 'Reject this verification request?': 'هل ترفض طلب التوثيق هذا؟', 'It is removed from the page and the company is told why.': 'ستُحذف من الصفحة وتُبلَّغ الشركة بالسبب.',
    'The company is told why and can send new documents.': 'ستُبلَّغ الشركة بالسبب ويمكنها إرسال مستندات جديدة.', 'Reason for the company (they will see it) *': 'السبب للشركة (ستراه) *', 'The registry document is not readable': 'مستند السجل التجاري غير مقروء',
    'Open reports': 'البلاغات المفتوحة', 'Change': 'غيّر', 'Leave': 'غادر', 'Enter your new quantity': 'أدخل الكمية الجديدة', 'Closed — target not reached': 'أُغلقت — لم يكتمل الهدف',
    'Quantity changed': 'تغيّرت الكمية', 'Left the group': 'غادر المجموعة', 'The organiser stays in its group — withdraw the group instead': 'يبقى المنظِّم في مجموعته — اسحب المجموعة بدلًا من ذلك', 'Enter a quantity (0 to leave)': 'أدخل كمية (0 للمغادرة)', 'Request a proposal': 'اطلب عرضًا', 'Documents': 'المستندات', 'No documents yet.': 'لا توجد مستندات بعد.', 'Attach a document': 'أرفق مستندًا', 'Download': 'تنزيل', 'Document type': 'نوع المستند',
    'Invoice': 'فاتورة', 'Specification': 'المواصفات', 'Data room': 'غرفة البيانات', 'Deliverable': 'المُخرَج', 'Questionnaire evidence': 'مستند الاستبيان', 'Document attached': 'تم إرفاق مستند',
    'Data room file (optional)': 'ملف غرفة البيانات (اختياري)', 'Deliverable (file)': 'المُخرَج (ملف)', 'Delivery note': 'ملاحظة التسليم', 'e.g. Final report and EDA submission receipt': 'مثلًا: التقرير النهائي وإيصال التقديم لهيئة الدواء',
    'Supporting document (SOP, certificate…)': 'مستند داعم (إجراء تشغيل قياسي، شهادة…)', 'Files up to 20 MB': 'الملفات حتى 20 ميجابايت', 'Could not attach the file': 'تعذّر إرفاق الملف',
    'This file was attached in another visit — documents open from the live app': 'أُرفق هذا الملف في زيارة سابقة — تُفتح المستندات من التطبيق الفعلي', 'Reviews': 'التقييمات', 'Keep review': 'أبقِ التقييم', 'Remove review': 'احذف التقييم',
    'Remove this review?': 'هل تحذف هذا التقييم؟', 'It disappears from the company page and from its rating. Both sides are told.': 'سيختفي من صفحة الشركة ومن تقييمها، ويُبلَّغ الطرفان.',
    'This request is still being saved — try again in a moment': 'ما زال الطلب قيد الحفظ — حاول بعد لحظة', 'Role *': 'الدور *', 'an admin': 'مدير', 'Claims': 'المطالبات', 'Claim pending': 'المطالبة قيد المراجعة', 'Claim pending.': 'المطالبة قيد المراجعة.',
    'Drugbox is checking your proof and tells you when the page is yours.': 'يراجع Drugbox إثباتك ويُبلغك عندما تصبح الصفحة لك.', 'Commercial registry document *': 'مستند السجل التجاري *',
    'Seen only by Drugbox’s reviewers.': 'لا يراه إلا مراجعو Drugbox.', 'Send claim': 'أرسل المطالبة', 'Attach the commercial registry document': 'أرفق مستند السجل التجاري',
    'Claim sent — Drugbox checks it and tells you when the page is yours': 'تم إرسال المطالبة — يراجعها Drugbox ويُبلغك عندما تصبح الصفحة لك', 'Could not send the claim': 'تعذّر إرسال المطالبة',
    'Reject this claim?': 'هل ترفض هذه المطالبة؟', 'The page stays unclaimed and the claimant is told why.': 'تبقى الصفحة بلا مالك ويُبلَّغ صاحب المطالبة بالسبب.', 'management': 'الإدارة', 'sales': 'المبيعات', 'quality': 'الجودة', 'regulatory': 'التسجيل', 'a team member': 'عضو في الفريق'
  });
  PATTERNS.unshift(
    [/^checked (\d{4}-\d{2}-\d{2})$/, function (m) { return 'تمت المراجعة ' + m[1]; }],
    [/^checked by Drugbox (\d{4}-\d{2}-\d{2})$/, function (m) { return 'راجعها Drugbox في ' + m[1]; }],
    [/^Drugbox checked your report on (.+) — the page stays as it is\.$/, function (m) { return 'راجع Drugbox بلاغك عن ' + m[1] + ' — تبقى الصفحة كما هي.'; }],
    [/^Drugbox checked your report on (.+) \((.+)\) — it has been corrected\.$/, function (m) { return 'راجع Drugbox بلاغك عن ' + m[1] + ' (' + (D[m[2]] || m[2]) + ') — تم التصحيح.'; }],
    [/^(\d+) open reports?( · (.+))?$/, function (m) { return m[1] + ' ' + (m[1] === '1' ? 'بلاغ مفتوح' : 'بلاغات مفتوحة') + (m[3] ? ' · ' + m[3] : ''); }],
    [/^Closed on (\S+) below its target — no orders were made$/, function (m) { return 'أُغلقت في ' + m[1] + ' دون الهدف — لم تُنشأ طلبات'; }],
    [/^You joined · ([\d,]+) (.+)$/, function (m) { return 'انضممت · ' + m[1] + ' ' + m[2]; }],
    [/^(.+) left the group$/, function (m) { return 'غادرت ' + m[1] + ' المجموعة'; }],
    [/^(.+) now takes ([\d,]+)$/, function (m) { return 'حصة ' + m[1] + ' الآن ' + m[2]; }],
    [/^([\d,]+) followers?$/, function (m) { return m[1] + ' ' + (m[1] === '1' ? 'متابع' : plural(m[1], ['متابع', 'متابعين'])); }],
    [/^(.+) posted (surplus stock|a licensing dossier|a request|a new listing): (.*)\.$/, function (m) { return 'نشرت ' + m[1] + ' ' + { 'surplus stock': 'مخزونًا فائضًا', 'a licensing dossier': 'ملف تسجيل للترخيص', 'a request': 'طلبًا', 'a new listing': 'إعلانًا جديدًا' }[m[2]] + ': ' + m[3] + '.'; }],
    [/^(.+) attached$/, function (m) { return 'تم إرفاق ' + m[1]; }],
    [/^(PO|CoA|Invoice|Specification|NDA|Data room|Deliverable|Questionnaire evidence|Other): (.+)$/, function (m) { return (D[m[1]] || m[1]) + ': ' + m[2]; }],
    [/^(.+) replied to your review of (.+)\.$/, function (m) { return 'ردّت ' + m[1] + ' على تقييمك لـ ' + m[2] + '.'; }],
    [/^Drugbox removed a review of (.+) after checking it\.$/, function (m) { return 'حذف Drugbox تقييمًا لـ ' + m[1] + ' بعد مراجعته.'; }],
    [/^Drugbox checked a review of (.+) — it stays up\.$/, function (m) { return 'راجع Drugbox تقييمًا لـ ' + m[1] + ' — سيبقى منشورًا.'; }],
    [/^Claimed by (.+)$/, function (m) { return 'طالب بها ' + m[1]; }],
    [/^Your claim for (.+) is with Drugbox — you will be told when the page is yours$/, function (m) { return 'مطالبتك بـ ' + m[1] + ' لدى Drugbox — ستُبلَّغ عندما تصبح الصفحة لك'; }],
    [/^Ask to join (.+)$/, function (m) { return 'اطلب الانضمام إلى ' + m[1]; }],
    [/^Request sent to the admin of (.+)$/, function (m) { return 'تم إرسال طلبك إلى مدير ' + m[1]; }],
    [/^(.+) is on the team$/, function (m) { return 'انضم ' + m[1] + ' إلى الفريق'; }],
    [/^(.+) invited you to join (.+) on Drugbox as (.+)\.$/, function (m) { return m[1] + ' دعاك للانضمام إلى ' + m[2] + ' على Drugbox (' + (D[m[3]] || m[3]) + ').'; }],
    [/^(.+) (accepted|declined) your invitation to (.+)\.$/, function (m) { return m[1] + (m[2] === 'accepted' ? ' قبل دعوتك للانضمام إلى ' : ' رفض دعوتك للانضمام إلى ') + m[3] + '.'; }],
    [/^(.+) asked to join (.+) as (.+) — answer in Workspace → Team\.$/, function (m) { return m[1] + ' طلب الانضمام إلى ' + m[2] + ' (' + (D[m[3]] || m[3]) + ') — رُد من مساحة العمل ← الفريق.'; }],
    [/^You are now on the team of (.+) \((.+)\)\.$/, function (m) { return 'أنت الآن في فريق ' + m[1] + ' (' + (D[m[2]] || m[2]) + ').'; }],
    [/^(.+) did not accept your request to join the team\.$/, function (m) { return 'لم تقبل ' + m[1] + ' طلبك للانضمام إلى الفريق.'; }],
    [/^Drugbox checked your (.+?)( \((.+)\))? — it now shows as checked on your page\.$/, function (m) { return 'راجع Drugbox شهادة ' + m[1] + (m[3] ? ' (' + m[3] + ')' : '') + ' — تظهر الآن كمراجَعة على صفحتك.'; }],
    [/^Drugbox could not accept your (.+?)( \((.+)\))? — reason: (.+)\. Add it again with a readable document\.$/, function (m) { return 'لم يقبل Drugbox شهادة ' + m[1] + (m[3] ? ' (' + m[3] + ')' : '') + ' — السبب: ' + m[4] + '. أضفها مرة أخرى بمستند مقروء.'; }],
    [/^free from (.+)$/, function (m) { return 'متاح من ' + tr(m[1]); }],
    [/^Request quotes from (\d+)$/, function (m) { return 'اطلب عروض أسعار من ' + m[1]; }],
    [/^Request a service from (.+)$/, function (m) { return 'اطلب خدمة من ' + m[1]; }],
    [/^\((.+)\) at (.+)$/, function (m) { return '(' + (D[m[1]] || m[1]) + ') في ' + m[2]; }],
    [/^([A-Z0-9]\S*(?: [A-Z0-9]\S*){0,5}) team$/, function (m) { return 'فريق ' + m[1].trim(); }],   /* "<Company> team" (a name of capitalised words), never a sentence */
    [/^to (\d{4}-\d{2}(?:-\d{2})?)$/, function (m) { return 'حتى ' + m[1]; }],
    [/^expired (\d{4}-\d{2}(?:-\d{2})?)$/, function (m) { return 'انتهت ' + m[1]; }],
    [/^(from|to) ([^·]+)$/, function (m) { return (m[1] === 'from' ? 'من ' : 'إلى ') + m[2]; }],
    [/^(tablets|units|kg|MT|cartons|batches|sachets|tubes|vials|bottles) \/ (year|month)$/, function (m) { return (D[m[1]] || m[1]) + ' / ' + (m[2] === 'year' ? 'سنويًا' : 'شهريًا'); }],
    [/^MOQ ([\d,.]+) (.+)$/, function (m) { return 'الحد الأدنى للطلب ' + m[1] + ' ' + (D[m[2]] || m[2]); }],
    [/^Your company appears in the Sponsored row of the directory(?: · VIP (monthly|yearly) · renews (.+?))?\. 3 Marketplace boosts a month are included\.$/, function (m) {
      return 'تظهر شركتك في صف الإعلانات المموّلة في الدليل' + (m[1] ? ' · VIP ' + (m[1] === 'yearly' ? 'سنوي' : 'شهري') + ' · يتجدد ' + m[2] : '') + '. تشمل الخطة 3 تمييزات شهريًا في السوق.'; }],
    [/^(.+) · being checked by Drugbox$/, function (m) { return m[1] + ' · قيد المراجعة من Drugbox'; }],
    [/^Sent — Drugbox checks it with the (.+)$/, function (m) { return 'تم الإرسال — يتحقق Drugbox منها مع ' + (D[m[1]] || m[1]); }],
    [/^(.+) is removed from your compliance passport( and its file is deleted)?\.$/, function (m) { return 'سيُحذف ' + m[1] + ' من جواز امتثال شركتك' + (m[2] ? ' ويُحذف ملفه' : '') + '.'; }],
    [/^(?:(.+) · )?added(?: by (.+?))?(?: · (\d{4}-\d{2}-\d{2}))?(?: · (.+))?$/, function (m) { return (m[1] ? m[1] + ' · ' : '') + 'أُضيف' + (m[2] ? ' بواسطة ' + m[2] : '') + (m[3] ? ' · ' + m[3] : '') + (m[4] ? ' · ' + m[4] : ''); }],
    [/^Drugbox checked your (.+) for (.+) — it now shows as verified on your compliance passport\.$/, function (m) { return 'راجع Drugbox مستند ' + m[1] + ' لـ ' + m[2] + ' — يظهر الآن موثّقًا في جواز الامتثال.'; }],
    [/^Drugbox could not accept your (.+) for (.+) — reason: (.+)\. Add it again with a readable file\.$/, function (m) { return 'لم يقبل Drugbox مستند ' + m[1] + ' لـ ' + m[2] + ' — السبب: ' + m[3] + '. أضفه مرة أخرى بملف مقروء.'; }],
  );
  /* ===== /AREA business ===== */
  PATTERNS.unshift(
    [/^Some information on this page was last updated more than 6 months ago \((.+)\)\.$/, function (m) { return 'آخر تحديث لبعض المعلومات في هذه الصفحة كان منذ أكثر من 6 أشهر (' + secs(m[1]) + ').'; }],
    [/^Please review: (.+) \(older than 6 months\)\.$/, function (m) { return 'يُرجى المراجعة: ' + secs(m[1]) + ' (أقدم من 6 أشهر).'; }],
    [/^May be outdated · (Source: .+)$/, function (m) { return 'قد تكون قديمة · ' + tr(m[1]); }],
    [/^What's on your mind, (.+)\?$/, function (m) { return 'بماذا تفكر يا ' + m[1] + '؟'; }],
    [/^(.+) is live( on VIP)? — add your products and details$/, function (m) { return m[1] + ' أصبحت متاحة' + (m[2] ? ' بخطة VIP' : '') + ' — أضف منتجاتك وتفاصيلك'; }],
    [/^Create a company page · (\d) of 3 — (choose a plan|company details|review|review and pay)$/, function (m) { return 'أنشئ صفحة شركة · ' + m[1] + ' من 3 — ' + ({ 'choose a plan': 'اختر خطة', 'company details': 'بيانات الشركة', review: 'المراجعة', 'review and pay': 'المراجعة والدفع' })[m[2]]; }],
    [/^(\d) of 3 — (choose a plan|company details|review|review and pay)$/, function (m) { return m[1] + ' من 3 — ' + ({ 'choose a plan': 'اختر خطة', 'company details': 'بيانات الشركة', review: 'المراجعة', 'review and pay': 'المراجعة والدفع' })[m[2]]; }],
    [/^(\S+) ([A-Z][A-Za-z ]*): (.+)$/, function (m) { var a = D[m[2]], b = D[m[3]] || D[m[3].replace(/^\S+\s+/, '')]; return a && b ? m[1] + ' ' + a + ': ' + b : null; }],   /* "📦 APIs: I have this to sell" on the intents preview */
    [/^Posted (\d+) days? ago · (Expires in (\d+) days?|No expiry)(.*)$/, function (m) { return 'نُشر منذ ' + m[1] + ' ' + unit(m[1], 'd') + ' · ' + (m[3] ? 'ينتهي خلال ' + m[3] + ' ' + unit(m[3], 'd') : 'بلا انتهاء') + (m[4] ? ' ' + m[4].trim().replace('(90-day CMO cycle)', '(دورة تصنيع لدى الغير 90 يومًا)').replace('(license sale)', '(بيع ترخيص)') : ''); }],
    [/^Expiry notice: "(.+)" expires in (\d+) days? — listings auto-expire to keep the marketplace fresh$/, function (m) { return 'تنبيه انتهاء: «' + m[1] + '» ينتهي خلال ' + m[2] + ' ' + unit(m[2], 'd') + ' — تنتهي الإعلانات تلقائيًا ليبقى السوق محدّثًا'; }],
    [/^No\. (\d+)$/, function (m) { return 'رقم ' + m[1]; }],
    [/^(.+) · (not claimed yet|managed by its team)$/, function (m) { return m[1] + ' · ' + (m[2] === 'not claimed yet' ? 'لم يطالب بها أحد بعد' : 'يديرها فريقها'); }],   /* 'Add or claim your company' results */
    [/^Pay EGP ([\d,]+) and create$/, function (m) { return 'ادفع ' + m[1] + ' ج.م وأنشئ الصفحة'; }],   /* the create wizard, VIP */
    [/^(VIP|Basic|Free) · (monthly|yearly|month|year)$/, function (m) { return (D[m[1]] || m[1]) + ' · ' + ({ monthly: 'شهري', month: 'شهري', yearly: 'سنوي', year: 'سنوي' })[m[2]]; }],
    [/^(\S+) ([A-Z][A-Za-z]+) …$/, function (m) { return D[m[2]] ? m[1] + ' ' + D[m[2]] + ' …' : null; }],   /* a filter's name while its count loads */
    [/^Service by (.+)$/, function (m) { return 'خدمة من ' + m[1]; }],
    [/^messaged (.+?): (.+)$/, function (m) { return 'راسل ' + (m[1] === 'your company' ? 'شركتك' : m[1]) + ': ' + m[2]; }]   /* the company_message notification (0032) */,
    [/^Show more \((\d+) of (\d+)\)$/, function (m) { return 'اعرض المزيد (' + m[1] + ' من ' + m[2] + ')'; }],   /* the company directory */
    [/^Commercial registry (\S+)(?: · sent (.+))?$/, function (m) { return 'السجل التجاري ' + m[1] + (m[2] ? ' · أُرسل ' + m[2] : ''); }]   /* Admin → Review, verification rows */
  );
  var SECS = { about: 'النبذة', products: 'المنتجات', sites: 'المواقع', contact: 'التواصل' };
  function secs(l) { return l.split(', ').map(function (x) { return SECS[x] || x; }).join('، '); }
  PATTERNS.unshift(
    [/^trending — (\d+) posts? today$/, function (m) { return 'رائج — ' + m[1] + ' ' + plural(m[1], ['منشور', 'منشورات']) + ' اليوم'; }],
    [/^([\d,]+) new post (today|this week)$/, function (m) { return word(m[1], 'new posts ' + m[2]); }],
    [/^([\d,.]+K?)\s+(provider|open position)$/i, function (m) { return word(m[1], m[2] + 's'); }],
    [/^Posted (just now|\d+\s*(?:m|min|h|d|w) ago)$/, function (m) { return 'نُشر ' + tr(m[1]); }]
  );
  /* phase 1b: the live app's real numbers (ticker labels, Jobs headers, the reach line) and My Intents on the profile */
  Object.assign(D, {
    'Service:': 'خدمة:', 'News:': 'أخبار:', 'Marketplace intents': 'نوايا السوق', 'Nothing selected yet': 'لم تختر شيئًا بعد', 'Both': 'الاثنان',
    'APIs': 'المواد الخام الدوائية', 'Cosmetic Ingredients': 'مكونات التجميل', 'CMO': 'التصنيع لدى الغير',
    'I have this to sell': 'لدي هذا للبيع', 'I need to buy this': 'أحتاج إلى شرائه', 'I have a facility to offer': 'لدي مصنع أعرضه', 'I need a manufacturer': 'أحتاج إلى مصنّع',
    'I have one to sell': 'لدي واحدة للبيع', 'I want to buy one': 'أريد شراء واحدة', "I'm selling a registration": 'أبيع تسجيلًا', 'I provide this service': 'أقدّم هذه الخدمة',
    'I need this service': 'أحتاج إلى هذه الخدمة', 'I need to hire someone': 'أحتاج إلى توظيف شخص', "I'm looking for a job": 'أبحث عن وظيفة', 'I teach this course': 'أدرّس هذه الدورة',
    'I want to take a course': 'أريد أن أتعلّم دورة', 'Open Positions': 'الوظائف المتاحة',
    'Post your profile and let verified companies reach out to you directly': 'انشر ملفك ودع الشركات الموثّقة تتواصل معك مباشرة',
    'Post My Profile': 'انشر ملفي', 'Favourites only': 'المفضّلة فقط',
    'Join pharma professionals — from new graduates to industry veterans': 'انضم إلى متخصصي الدواء — من حديثي التخرج حتى خبراء الصناعة'
  });
  PATTERNS.unshift(
    [/^Reach ([\d,]+|…) pharma professionals? on Drugbox$/, function (m) { return 'صِل إلى ' + m[1] + ' ' + (m[1] === '…' ? 'متخصص' : plural(m[1], ['متخصص', 'متخصصين'])) + ' في الدواء على Drugbox'; }],
    [/^([\d,]+) jobs?$/, function (m) { return m[1] + ' ' + plural(m[1], ['وظيفة', 'وظائف']); }],
    [/^([\d,]+) profile$/, function (m) { return m[1] + ' ' + plural(m[1], ['ملف', 'ملفات']); }]
  );
  /* ===== AREA business: marketplace (B-06…B-10) ===== */
  Object.assign(D, {
    'Draft': 'مسودة', 'Edit listing': 'تعديل الإعلان', 'Title *': 'العنوان *', 'MOQ / quantity': 'الحد الأدنى / الكمية', 'Save changes': 'احفظ التغييرات', 'Listing updated': 'تم تحديث الإعلان',
    '✅ Publish listing': '✅ انشر الإعلان', '⭐ Boost this listing': '⭐ روّج لهذا الإعلان', '⏸ Pause listing': '⏸ إيقاف الإعلان مؤقتًا', '▶ Resume listing': '▶ استئناف الإعلان',
    '🔁 Renew listing': '🔁 جدّد الإعلان', '🗑 Delete listing': '🗑 احذف الإعلان', 'Delete this listing?': 'هل تحذف هذا الإعلان؟', 'Delete listing': 'احذف الإعلان', 'Listing resumed': 'تم استئناف الإعلان',
    'Listing paused — hidden from buyers': 'تم إيقاف الإعلان — مخفي عن المشترين', 'Draft saved — find it in My Listings': 'حُفظت المسودة — تجدها في إعلاناتي', 'Could not save the draft': 'تعذّر حفظ المسودة',
    'Your listing is live': 'إعلانك منشور الآن', 'Expired — renew to show it again': 'انتهى — جدّده ليظهر من جديد', 'No expiry (license sale)': 'بلا انتهاء (بيع ترخيص)', 'not published': 'غير منشور',
    'You have no listings yet — publish one with “New Listing”.': 'لا توجد لديك إعلانات بعد — انشر إعلانًا من «إعلان جديد».', 'Could not load your listings': 'تعذّر تحميل إعلاناتك', 'Could not save': 'تعذّر الحفظ',
    'Your price *': 'سعرك *', 'Lead time': 'مدة التوريد', 'Note': 'ملاحظة', 'e.g. US$ 21 per kg': 'مثلًا: 21 دولار للكيلو', 'e.g. 2 MT': 'مثلًا: 2 طن', 'e.g. 3 weeks': 'مثلًا: 3 أسابيع',
    'e.g. CEP and CoA available': 'مثلًا: CEP وشهادة التحليل متوفرتان', 'Could not send the quote': 'تعذّر إرسال عرض السعر', '🛒 Saved listings': '🛒 الإعلانات المحفوظة',
    'Message *': 'الرسالة *', 'Send message': 'أرسل الرسالة', 'This is your own listing': 'هذا إعلانك', 'Saved to your list': 'تم الحفظ في قائمتك', 'Removed from saved': 'تمت الإزالة من المحفوظات',
    'View': 'عرض', 'Claimed by the seller — not checked by Drugbox': 'يدّعيها البائع — لم يراجعها Drugbox', 'Create or claim your company page first — quotes are sent by a company': 'أنشئ صفحة شركتك أو طالب بها أولًا — عروض الأسعار تُرسل باسم شركة',
    'Message this buyer instead — their request was posted before quotes': 'راسل هذا المشتري بدلًا من ذلك — نُشر طلبه قبل إتاحة عروض الأسعار', 'Create or claim your company page first': 'أنشئ صفحة شركتك أو طالب بها أولًا',
    'Enter your price': 'أدخل سعرك', 'The file is larger than 10 MB': 'الملف أكبر من 10 ميجابايت', '📄 COA': '📄 شهادة التحليل', 'No certificate of analysis on this listing': 'لا توجد شهادة تحليل لهذا الإعلان',
    'The certificate could not be opened': 'تعذّر فتح الشهادة', 'Only the listing’s owner can change it': 'صاحب الإعلان فقط يمكنه تعديله', 'view': 'مشاهدة', 'inquiry': 'استفسار', 'License': 'ترخيص', 'Listing': 'إعلان'
  });
  PATTERNS.unshift(
    [/^Posted just now · (Expires in (\d+) days?|No expiry \(license sale\))$/, function (m) { return 'نُشر الآن · ' + (m[2] ? 'ينتهي خلال ' + m[2] + ' ' + unit(m[2], 'd') : 'بلا انتهاء (بيع ترخيص)'); }],
    [/^(Posted|Renewed) (\d+) days? ago · (Expires in (\d+) days?|Expired — renew to show it again|No expiry \(license sale\))$/, function (m) { return (m[1] === 'Posted' ? 'نُشر منذ ' : 'جُدّد منذ ') + m[2] + ' ' + unit(m[2], 'd') + ' · ' + (m[4] ? 'ينتهي خلال ' + m[4] + ' ' + unit(m[4], 'd') : /Expired/.test(m[3]) ? 'انتهى — جدّده ليظهر من جديد' : 'بلا انتهاء (بيع ترخيص)'); }],
    [/^Renewed just now · Expires in (\d+) days?$/, function (m) { return 'جُدّد الآن · ينتهي خلال ' + m[1] + ' ' + unit(m[1], 'd'); }],
    [/^Saved (just now|(\d+) days? ago) · not published$/, function (m) { return 'حُفظ ' + (m[2] ? 'منذ ' + m[2] + ' ' + unit(m[2], 'd') : 'الآن') + ' · غير منشور'; }],
    [/^Renewed — it shows for another (\d+) days$/, function (m) { return 'تم التجديد — يظهر ' + m[1] + ' يومًا أخرى'; }],
    [/^Send a quote — (.+)$/, function (m) { return 'أرسل عرض سعر — ' + m[1]; }],
    [/^Your quote goes to (.+) in Requests & deals, where they can accept it, counter or decline\.$/, function (m) { return 'يصل عرضك إلى ' + m[1] + ' في الطلبات والصفقات، حيث يمكنه قبوله أو تقديم عرض مضاد أو رفضه.'; }],
    [/^Quote sent to (.+) — follow it in Requests & deals$/, function (m) { return 'تم إرسال عرض السعر إلى ' + m[1] + ' — تابعه في الطلبات والصفقات'; }],
    [/^Show more \(([\d,]+) of ([\d,]+)\)$/, function (m) { return 'عرض المزيد (' + m[1] + ' من ' + m[2] + ')'; }],
    [/^Message sent to (.+) — see Messages for the reply$/, function (m) { return 'تم إرسال الرسالة إلى ' + m[1] + ' — تابع الرد في الرسائل'; }],
    [/^Write to (.+)$/, function (m) { return 'راسل ' + m[1]; }],
    [/^“(.+)” is removed from the Marketplace and from your company page\.$/, function (m) { return 'سيُحذف «' + m[1] + '» من السوق ومن صفحة شركتك.'; }],
    [/^📦 Products \((\d+)\)$/, function (m) { return '📦 المنتجات (' + m[1] + ')'; }],
    [/^✓ (.+) \(checked\)$/, function (m) { return '✓ ' + m[1] + ' (تمت المراجعة)'; }],
    [/^A buyer is looking for what you sell: (.+) — open the Marketplace$/, function (m) { return 'مشترٍ يبحث عمّا تبيعه: ' + m[1] + ' — افتح السوق'; }],
    [/^New offer matching what you need: (.+) — open the Marketplace$/, function (m) { return 'عرض جديد يطابق ما تحتاجه: ' + m[1] + ' — افتح السوق'; }],
    [/^📄 (.+) · attached$/, function (m) { return '📄 ' + m[1] + ' · مرفق'; }],
    [/^target (.+)$/, function (m) { return 'السعر المستهدف ' + m[1]; }]
  );
  /* ===== /AREA business: marketplace ===== */
  PATTERNS.push([/^(.+?): ([A-Z][A-Za-z -]+) — (.+)$/, function (m) { return D[m[2]] ? m[1] + ': ' + D[m[2]] + ' — ' + m[3] : null; }]);   /* last: '<company>: Send quote — <deal>' in notifications */
  var ARROWS = { '→': '←', '←': '→' };
  function put(raw, t, r) {   /* keep the original's surrounding spaces even when its inner spacing differs */
    if (raw.indexOf(t) >= 0) return raw.replace(t, r);
    var m = /^(\s*)[\s\S]*?(\s*)$/.exec(raw); return (m ? m[1] : '') + r + (m ? m[2] : '');
  }
  var SEEN = new Map();   /* the same labels come back on every render: each distinct text is worked out once */
  function tr(s) {
    if (!s) return s; var raw = s, t = s.replace(/\s+/g, ' ').trim(); if (!t) return s;
    var r = SEEN.get(t); if (r === undefined) { r = look(t); if (SEEN.size > 4000) SEEN.clear(); SEEN.set(t, r); }
    return r == null ? s : put(raw, t, r);
  }
  function look(t) {
    if (D[t]) return D[t];
    for (var i = 0; i < PATTERNS.length; i++) { var m = PATTERNS[i][0].exec(t); if (m) { var r = PATTERNS[i][1](m); if (r) return r; } }
    if (t.indexOf(' · ') > 0) { var tail = / ·$/.test(t) ? ' ·' : '', parts = (tail ? t.slice(0, -2) : t).split(' · '), hit = 0; parts = parts.map(function (p) { var q = tr(p); if (q !== p) hit++; return q; }); if (hit) return parts.join(' · ') + tail; }   /* 'site · source ·' before a bold expiry */
    var pre = /^([A-Za-z][A-Za-z &/]+:)\s+(.+)$/.exec(t); if (pre && D[pre[1]]) return D[pre[1]] + ' ' + pre[2];
    /* leading icons / trailing arrows around a known phrase */
    var mm = /^([^A-Za-z]*?)([A-Za-z][^→←]*?)(\s*[→←])?$/.exec(t);
    if (mm && D[mm[2].trim()]) return mm[1] + D[mm[2].trim()] + (mm[3] ? ' ' + ARROWS[mm[3].trim()] : '');
    return null;
  }
  /* ===== AREA business: payments (B-14…B-16) ===== */
  Object.assign(D, {
    'My payments': 'مدفوعاتي', 'Boosts and Featured listings you paid for — references, receipts and invoices': 'الترقيات والإعلانات المميزة التي دفعت ثمنها — المراجع والإيصالات والفواتير',
    'No payments yet.': 'لا توجد مدفوعات بعد.', 'Payment history': 'سجل المدفوعات', 'Invoice': 'فاتورة', 'Send the transfer': 'أرسل التحويل', 'Pay again': 'ادفع مرة أخرى',
    'Waiting for payment': 'بانتظار الدفع', 'Under review': 'قيد المراجعة', 'Paid': 'مدفوع', 'Did not go through': 'لم يكتمل', 'Expired': 'منتهي', 'Refunded': 'مُسترد',
    'Mobile wallet': 'محفظة الموبايل', 'Card': 'بطاقة', 'Fawry': 'فوري', 'InstaPay': 'إنستاباي', 'Marketplace boost': 'ترقية إعلان في السوق', 'Featured listing': 'إعلان مميز',
    'VIP — monthly': 'VIP — شهري', 'VIP — yearly': 'VIP — سنوي', '👑 Use an included boost': '👑 استخدم ترقية مجانية من VIP', 'Use an included boost': 'استخدم ترقية مجانية من VIP',
    'Choose the listing to promote': 'اختر الإعلان المراد ترقيته', 'Could not use an included boost': 'تعذّر استخدام الترقية المجانية', 'Act as your VIP company first': 'تصرّف باسم شركتك الـ VIP أولًا',
    'Your page is created first; VIP starts as soon as the payment is confirmed.': 'تُنشأ صفحتك أولًا، ويبدأ VIP بمجرد تأكيد الدفع.', 'Demo — no money is charged; the steps are the real ones.': 'نسخة تجريبية — لا يُخصم أي مبلغ؛ والخطوات هي الخطوات الفعلية.',
    'Allow pop-ups to open the invoice': 'اسمح بالنوافذ المنبثقة لفتح الفاتورة', 'The invoice could not be opened': 'تعذّر فتح الفاتورة', 'An invoice is issued once the payment is confirmed': 'تُصدر الفاتورة بعد تأكيد الدفع',
    'The payment failed or was declined — nothing was charged and nothing was activated. Try again from My payments': 'لم يكتمل الدفع — لم يُخصم أي مبلغ ولم يُفعَّل شيء. حاول مرة أخرى من مدفوعاتي',
    'Payment received — VIP is active (demo: no card was charged)': 'تم استلام الدفع — VIP مفعّل (نسخة تجريبية: لم تُخصم البطاقة)', 'Loading…': 'جارٍ التحميل…',
    'Make your listing Featured': 'اجعل إعلانك مميزًا', '⭐ Make your listing Featured': '⭐ اجعل إعلانك مميزًا', 'Featured fee': 'رسوم الإعلان المميز', '⚡ BOOSTED': '⚡ معزز', '⭐ FEATURED': '⭐ مميز',
    'Opening the secure Paymob page…': 'جارٍ فتح صفحة Paymob الآمنة…', 'Pay at Fawry': 'ادفع في فوري', 'Fawry reference number': 'رقم مرجع فوري', 'Pay with InstaPay': 'ادفع بإنستاباي', 'Send to': 'أرسل إلى',
    'Transfer number *': 'رقم التحويل *', 'Receipt (screenshot or PDF)': 'الإيصال (صورة أو PDF)', 'Send for confirmation': 'أرسل للتأكيد', 'From the InstaPay confirmation': 'من رسالة تأكيد إنستاباي',
    'Thank you — we confirm InstaPay transfers within one working day': 'شكرًا — نؤكد تحويلات إنستاباي خلال يوم عمل واحد', 'Pay with': 'ادفع بـ', 'Listing to promote': 'الإعلان المراد ترقيته',
    /* verification follow-ups (October 2026) */
    'Write': 'اكتب', 'in the transfer note.': 'في ملاحظة التحويل.', '· monthly': '· شهري', '· yearly': '· سنوي',
    'It activates automatically once Fawry confirms — we notify you. You find this reference again in My payments.': 'يتفعّل تلقائيًا بمجرد تأكيد فوري — وسنخطرك. وتجد هذا الرقم المرجعي مرة أخرى في مدفوعاتي.',
    'Demo — a sample reference number; Fawry is not contacted and nothing is charged.': 'نسخة تجريبية — رقم مرجعي توضيحي؛ لا يتم التواصل مع فوري ولا يُخصم أي مبلغ.',
    'Demo — a sample InstaPay address; send no money, nothing is charged.': 'نسخة تجريبية — عنوان إنستاباي توضيحي؛ لا ترسل أي أموال، ولا يُخصم أي مبلغ.',
    'Cancelled': 'أُلغي', 'Continue payment': 'أكمل الدفع', 'Cancel this payment?': 'إلغاء هذه الدفعة؟', 'Keep it': 'أبقِها', 'Cancel payment': 'ألغِ الدفع',
    'Its Fawry reference can no longer be used. Nothing was charged.': 'لن يمكن استخدام رقم فوري المرجعي بعد ذلك. لم يُخصم أي مبلغ.',
    'Nothing was charged. If you already paid on the payment page, do not cancel — the payment confirms itself.': 'لم يُخصم أي مبلغ. إذا كنت قد دفعت بالفعل في صفحة الدفع فلا تُلغِ — يتأكد الدفع تلقائيًا.',
    'Payment cancelled — nothing was charged': 'أُلغيت الدفعة — لم يُخصم أي مبلغ', 'Could not cancel': 'تعذّر الإلغاء', 'You cancelled this payment — nothing was charged': 'ألغيت هذه الدفعة — لم يُخصم أي مبلغ',
    'Only a payment that is still waiting can be cancelled': 'لا يمكن إلغاء إلا دفعة لا تزال بانتظار الدفع',
    'Add your mobile number (01…) to your profile to pay at Fawry — Fawry sends the reference to it': 'أضف رقم موبايلك (01…) إلى ملفك الشخصي للدفع في فوري — يرسل فوري الرقم المرجعي إليه',
    'Fawry did not issue a reference number — nothing was charged; please try again': 'لم يُصدر فوري رقمًا مرجعيًا — لم يُخصم أي مبلغ؛ حاول مرة أخرى',
    'Paymob did not start the payment — nothing was charged; please try again': 'لم تبدأ Paymob عملية الدفع — لم يُخصم أي مبلغ؛ حاول مرة أخرى',
    'The payment provider could not be reached — nothing was charged; please try again': 'تعذّر الوصول إلى مزوّد الدفع — لم يُخصم أي مبلغ؛ حاول مرة أخرى',
    'The payment started but could not be recorded yet — look in My payments in a minute': 'بدأ الدفع لكن لم يُسجَّل بعد — راجع مدفوعاتي بعد دقيقة',
    'This company page is suspended — VIP cannot be bought for it': 'صفحة هذه الشركة موقوفة — لا يمكن شراء VIP لها',
    'This listing is not active — publish it again before promoting it': 'هذا الإعلان غير نشط — انشره مرة أخرى قبل ترقيته',
    'The receipt must be a file you uploaded': 'يجب أن يكون الإيصال ملفًا رفعته أنت', 'Enter the transfer number from the InstaPay confirmation': 'أدخل رقم التحويل من رسالة تأكيد إنستاباي',
    'We have not received the payment confirmation yet — if you paid, it activates automatically; if you left the payment page, continue or cancel it in My payments': 'لم يصلنا تأكيد الدفع بعد — إذا كنت دفعت فسيتفعّل تلقائيًا؛ وإذا غادرت صفحة الدفع فأكمله أو ألغه من مدفوعاتي',
    '👑 VIP · answer within 48 h': '👑 VIP · الرد خلال 48 ساعة', 'VIP · answer within 48 h': 'VIP · الرد خلال 48 ساعة'
  });
  PATTERNS.unshift(
    [/^(\d+) of 3 included boosts left this month with VIP — no payment$/, function (m) { return 'متبقٍ ' + m[1] + ' من 3 ترقيات مجانية هذا الشهر مع VIP — بدون دفع'; }],
    [/^Boost activated — included with VIP \((\d+) left this month\)$/, function (m) { return 'تم تفعيل الترقية — مجانًا مع VIP (متبقٍ ' + m[1] + ' هذا الشهر)'; }],
    [/^(.+) is live — VIP starts when the payment is confirmed$/, function (m) { return 'صفحة ' + m[1] + ' منشورة — يبدأ VIP عند تأكيد الدفع'; }],
    [/^Fawry reference (\d+)( · pay by (.+))?$/, function (m) { return 'مرجع فوري ' + m[1] + (m[3] ? ' · ادفع قبل ' + gbIn(m[3]) : ''); }],
    [/^valid until (.+)$/, function (m) { return 'صالح حتى ' + gbIn(m[1]); }],
    [/^Your InstaPay transfer for this \((.+)\) is being checked by Drugbox — wait for the confirmation in My payments$/, function (m) { return 'تحويل إنستاباي لهذا (' + m[1] + ') قيد المراجعة من Drugbox — انتظر التأكيد في مدفوعاتي'; }],
    [/^Only a payment that is still waiting can be cancelled \(this one is (.+)\)$/, function () { return 'لا يمكن إلغاء إلا دفعة لا تزال بانتظار الدفع'; }],
    [/^Order (DBX\d+) was paid after the buyer cancelled it — nothing was activated; refund due$/, function (m) { return 'دُفع الطلب ' + m[1] + ' بعد أن ألغاه المشتري — لم يُفعَّل شيء؛ يلزم رد المبلغ'; }],
    [/^Transfer (.+) — Drugbox confirms within one working day$/, function (m) { return 'التحويل ' + m[1] + ' — يؤكده Drugbox خلال يوم عمل'; }],
    [/^incl\. VAT (.+)$/, function (m) { return 'شامل ضريبة القيمة المضافة ' + m[1]; }],
    [/^(Boosted|Featured) until (.+)$/, function (m) { return (m[1] === 'Boosted' ? 'معزز حتى ' : 'مميز حتى ') + m[2]; }],
    [/^Every payment for (.+)’s plan, with its status\. Paid ones have a tax invoice \(VAT 14% included\)\.$/, function (m) { return 'كل مدفوعات خطة ' + m[1] + ' وحالتها. للمدفوع منها فاتورة ضريبية (شاملة ضريبة القيمة المضافة 14%).'; }],
    [/^You already have a Fawry reference for this \((.+)\) — pay it or find it in My payments$/, function (m) { return 'لديك بالفعل مرجع فوري لهذا (' + m[1] + ') — ادفعه أو تجده في مدفوعاتي'; }],
    [/^You already have an InstaPay payment waiting for this \((.+)\) — send the transfer from My payments$/, function (m) { return 'لديك بالفعل دفعة إنستاباي معلّقة لهذا (' + m[1] + ') — أرسل التحويل من مدفوعاتي'; }],
    [/^Your Fawry reference for (.+) \((.+)\) expired — nothing was charged; start a new payment from My payments$/, function (m) { return 'انتهت صلاحية مرجع فوري لـ ' + (D[m[1]] || m[1]) + ' (' + m[2] + ') — لم يُخصم أي مبلغ؛ ابدأ دفعة جديدة من مدفوعاتي'; }],
    [/^Your payment for (.+) \((.+)\) did not go through — nothing was activated; try again from My payments$/, function (m) { return 'لم يكتمل دفعك لـ ' + (D[m[1]] || m[1]) + ' (' + m[2] + ') — لم يُفعَّل شيء؛ حاول مرة أخرى من مدفوعاتي'; }],
    [/^VIP for (.+) ends on (.+) — renew it from Plan & verification to keep it$/, function (m) { return 'ينتهي VIP لـ ' + m[1] + ' في ' + m[2] + ' — جدّده من الخطة والتوثيق للاحتفاظ به'; }],
    [/^Payment received — (.+) is active$/, function (m) { return 'تم استلام الدفع — ' + (D[m[1]] || m[1]) + ' مفعّل'; }]
  );
  /* ===== /AREA business: payments ===== */
  PATTERNS.unshift.apply(PATTERNS, PATTERNS_EXTRA);
  window.dxT = tr;
  /* the original (English) text of an element, whatever the interface language — so logic never depends on the language shown */

  /* never translate what people wrote */
  var SKIP = 'script,style,svg,input,textarea,[contenteditable],.post-body,.post-text,.msg-text,.bubble,.mx-msg,.cmt-text,.dx-entity,.lc-title,.sp-title,.sc-title,.gcard-title,.gcard-desc,.dl-title,[data-noi18n]';   /* whole blocks people wrote */
  var SKIP_SELF = '.post-name,.sugg-name,.dr-card h3,.hb-card h3,.cp-name,.dr-name,.mg-name,.profile-name,.dx-mine-name,.jc-title';   /* .jc-title: the job title stays, its Hiring / level badges are translated */   /* a name's own words stay; badges inside it are translated */
  var ORIG = new WeakMap(), LAST = new WeakMap(), LASTA = new WeakMap(), ATTR = ['placeholder', 'title', 'aria-label'];   /* LAST = what we wrote, so our own output is never translated again */
  window.dxOrigText = function (el) { if (!el) return ''; var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), o = ''; while (w.nextNode()) { var n = w.currentNode; o += ORIG.has(n) ? ORIG.get(n) : n.nodeValue; } return o; };
  function isAr() { return document.documentElement.lang === 'ar'; }
  /* layers that split a text node (emoji → icon, ✓ → seal) rebuild it from the English original and hand each piece back here, so switching to English restores it */
  window.dxI18nOrig = function (n) { return ORIG.has(n) ? ORIG.get(n) : null; };
  /* the same English word in another place: a saved post or job says "محفوظ" on its own button, "المحفوظات" is the Saved page */
  var CTX = [['.dbk-saved', { 'Saved': 'محفوظ', '🔖 Saved': '🔖 محفوظ' }],
             ['.cap-slots', { 'Free': 'متاح' }]];   /* a production month that is free is available ("متاح"), not free of charge ("مجاني") */
  function trAt(n, v) { var p = n.parentElement, k = v.replace(/\s+/g, ' ').trim();
    /* "<b>9</b> members": the word after a number in its own element takes the number's Arabic plural (9 أعضاء, not 9 عضو) */
    var ps = n.previousSibling, wf = WORDS[k.toLowerCase()] || WORDS[k.toLowerCase() + 's'];
    if (wf && ps && ps.nodeType === 1) { var num = (ps.textContent || '').trim(); if (/^[\d,.]+K?\+?$/i.test(num)) return put(v, k, plural(num.replace(/\+$/, ''), wf)); }
    for (var i = 0; p && i < CTX.length; i++) if (CTX[i][1][k] && p.closest(CTX[i][0])) return put(v, k, CTX[i][1][k]);
    return tr(v); }
  window.dxI18nAdopt = function (n) { if (!n || !isAr()) return; var v = n.nodeValue, t = trAt(n, v); if (t !== v) { keepValue(n, v); ORIG.set(n, v); LAST.set(n, t); n.nodeValue = t; } else { ORIG.delete(n); LAST.delete(n); } };
  window.dxI18nAttrs = function (el) { if (el && isAr()) walk(el); };   /* attributes a layer set after the page was translated (tooltips) */
  /* an <option> without a value submits its text: pin the English text as its value before translating it, so a choice made in
     Arabic is the same choice (a role, a governorate, a document type) the app and the database expect */
  function keepValue(n, v) { var o = n.parentElement; if (o && o.tagName === 'OPTION' && !o.hasAttribute('value')) o.setAttribute('value', v.trim()); }
  function walk(root) {
    if (!root || !isAr()) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { var p = n.parentElement; return !p || p.closest(SKIP) || p.matches(SKIP_SELF) || !/[A-Za-z]/.test(n.nodeValue) ? 2 : 1; } });
    var list = []; while (w.nextNode()) list.push(w.currentNode);
    list.forEach(function (n) { var v = n.nodeValue; if (LAST.get(n) === v) return;   /* already our translation */
      var t = trAt(n, v); if (t !== v) { keepValue(n, v); ORIG.set(n, v); LAST.set(n, t); n.nodeValue = t; } else if (ORIG.has(n)) { ORIG.delete(n); LAST.delete(n); } });   /* a new value from the app becomes the new original */
    var withAttr = root.querySelectorAll ? Array.prototype.slice.call(root.querySelectorAll('[placeholder],[title],[aria-label]')) : []; if (root.matches && root.matches('[placeholder],[title],[aria-label]')) withAttr.push(root);
    withAttr.forEach(function (el) {
      if (el.closest('[data-noi18n]')) return;
      ATTR.forEach(function (a) { var v = el.getAttribute(a); if (!v || !/[A-Za-z]/.test(v)) return; var m = LASTA.get(el) || {}; if (m[a] === v) return; var t = tr(v); if (t !== v) { el.setAttribute('data-i18n-' + a, v); m[a] = t; LASTA.set(el, m); el.setAttribute(a, t); } });
    });
  }
  /* a translated label that a layer later re-created (split around an icon, or a button copied with its price) has lost its recorded original:
     the dictionary gives it back — only for buttons and icon labels, never for what people wrote */
  var REV = null;
  function rev(v) {
    if (!REV) { REV = {}; Object.keys(D).forEach(function (k) { var a = D[k]; REV[a] = a in REV && REV[a] !== k ? '' : k; }); }   /* ambiguous values are never reversed */
    var t = v.replace(/\s+/g, ' ').trim(), k = REV[t]; return k ? put(v, t, k) : null;
  }
  function restoreIn(root) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); while (w.nextNode()) { var n = w.currentNode, p = n.parentElement;
      if (ORIG.has(n)) { n.nodeValue = ORIG.get(n); ORIG.delete(n); }
      else if (p && /[\u0600-\u06FF]/.test(n.nodeValue) && (p.tagName === 'BUTTON' || p.querySelector(':scope > .dx-ic')) && !p.closest(SKIP)) { var e = rev(n.nodeValue); if (e != null) n.nodeValue = e; } }
    ATTR.forEach(function (a) { var sel = '[data-i18n-' + a + ']', els = Array.prototype.slice.call(root.querySelectorAll(sel)); if (root.matches && root.matches(sel)) els.push(root);
      els.forEach(function (el) { el.setAttribute(a, el.getAttribute('data-i18n-' + a)); el.removeAttribute('data-i18n-' + a); }); });
  }
  function restore() {   /* the page itself, plus the pages the app keeps detached between visits (Marketplace, Jobs, Groups) */
    [document.body, window.__mkxNode, window.__jxNode, window.__gxNode].forEach(function (r) { if (r && r.nodeType === 1 && (r === document.body || !r.isConnected)) restoreIn(r); });
    LAST = new WeakMap(); LASTA = new WeakMap();
  }
  /* a number that changes after its word was translated ("<b>2</b> وظيفة" counting up to 6, a live count arriving): the word after it
     takes the new number's form (X-03) */
  function recount(el) { var ns = el && el.nextSibling; if (!ns || ns.nodeType !== 3 || !ORIG.has(ns)) return;
    var t = trAt(ns, ORIG.get(ns)); if (t !== ns.nodeValue) { LAST.set(ns, t); ns.nodeValue = t; } }
  /* new content (dialogs, notices, lists) is translated as it appears */
  var pending = null;
  new MutationObserver(function (muts) {
    if (!isAr()) return;
    muts.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType === 1) (pending = pending || []).push(n); else if (n.nodeType === 3 && n.parentElement) (pending = pending || []).push(n.parentElement); }); if (m.type === 'characterData' && m.target.parentElement) (pending = pending || []).push(m.target.parentElement); });
    if (pending && !walk.__t) walk.__t = requestAnimationFrame(function () { var p = pending; pending = null; walk.__t = 0; p.forEach(function (n) { if (n.isConnected) { walk(n); recount(n); } }); });
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
  /* ===== AREA social: other layers add their own words (and patterns) to the dictionary ===== */
  window.dxI18nAdd = function (words, pats) { Object.assign(D, words || {}); (pats || []).forEach(function (p) { PATTERNS.unshift(p); }); SEEN.clear(); REV = null; if (isAr()) walk(document.body); };
  /* a notice is shown in the interface language at once (not in English first, then translated a frame later) */
  [['DBK', 'toast'], [null, 'toast']].forEach(function (k) {
    var host = k[0] ? window[k[0]] : window, f = host && host[k[1]]; if (typeof f !== 'function' || f.__i18n) return;
    var w = function (m) { var a = [].slice.call(arguments); if (isAr() && typeof m === 'string') a[0] = tr(m); return f.apply(this, a); }; w.__i18n = 1; host[k[1]] = w;
  });
  C.onRender('i18n', function () { if (isAr()) walk(document.body); });
  var saved = null; try { saved = localStorage.getItem('dx_lang'); } catch (e) {}
  if (saved === 'ar') setLang('ar');
})();
