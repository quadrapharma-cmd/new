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
    'Timeline': 'التسلسل الزمني', 'Unit': 'الوحدة', 'You are the sender': 'أنت المرسل', 'You are the receiver': 'أنت المستقبل', 'Send quote': 'أرسل عرضًا', 'Request sent': 'تم إرسال الطلب',
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
    'Message on WhatsApp': 'راسل على واتساب', 'Address · directions': 'العنوان · الاتجاهات', 'Who answers': 'من يرد', 'Quote requests go to': 'طلبات عروض الأسعار تذهب إلى', 'Send a message': 'أرسل رسالة',
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
    'Edit Profile': 'تعديل الملف', 'Headline': 'العنوان المهني', 'Bio': 'نبذة', 'Save Changes': 'حفظ التغييرات', 'No notifications': 'لا توجد إشعارات', 'New message': 'رسالة جديدة', 'Attach file': 'إرفاق ملف',
    'Attach photo': 'إرفاق صورة', 'This conversation is about this listing': 'هذه المحادثة بخصوص هذا الإعلان',
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
    'Welcome back, Haytham!': 'أهلًا بعودتك يا هيثم!', 'Post shared': 'تم نشر المنشور', 'Copied': 'تم النسخ', 'Deleted': 'تم الحذف', 'Undo': 'تراجع'
  };
  var UNITS = { m: ['دقيقة', 'دقائق'], h: ['ساعة', 'ساعات'], d: ['يوم', 'أيام'], w: ['أسبوع', 'أسابيع'], min: ['دقيقة', 'دقائق'] };
  function unit(n, u) { var p = UNITS[u] || [u, u]; return +n >= 3 && +n <= 10 ? p[1] : p[0]; }
  /* [one, few]: Arabic uses the plural for 3–10 (and, in everyday use, 2); 1 and 11+ take the singular */
  function plural(n, forms) { var x = /K$/i.test(String(n)) ? 1000 : parseFloat(String(n).replace(/,/g, '')); return x >= 2 && x <= 10 ? forms[1] : forms[0]; }
  var WORDS = { comments: ['تعليق', 'تعليقات'], reposts: ['إعادة نشر', 'إعادات نشر'], members: ['عضو', 'أعضاء'], posts: ['منشور', 'منشورات'], views: ['مشاهدة', 'مشاهدات'],
    connections: ['اتصال', 'اتصالات'], listings: ['إعلان', 'إعلانات'], companies: ['شركة', 'شركات'], providers: ['مقدّم خدمة', 'مقدّمي خدمة'], clients: ['عميل', 'عملاء'], inquiries: ['استفسار', 'استفسارات'],
    results: ['نتيجة', 'نتائج'], sites: ['موقع', 'مواقع'], profiles: ['ملف', 'ملفات'], warnings: ['تحذير', 'تحذيرات'],
    'open positions': ['وظيفة متاحة', 'وظائف متاحة'], 'requests received': ['طلب وارد', 'طلبات واردة'], 'new posts today': ['منشور جديد اليوم', 'منشورات جديدة اليوم'],
    'new posts this week': ['منشور جديد هذا الأسبوع', 'منشورات جديدة هذا الأسبوع'], 'deals closed': ['صفقة مكتملة', 'صفقات مكتملة'], 'new posts': ['منشور جديد', 'منشورات جديدة'],
    'new requests today': ['طلب جديد اليوم', 'طلبات جديدة اليوم'], 'quote requests today': ['طلب تسعير اليوم', 'طلبات تسعير اليوم'], listing: ['إعلان', 'إعلانات'] };
  function word(n, w) { w = w.toLowerCase().replace(/^request received$/, 'requests received').replace(/^company$/, 'companies'); var f = WORDS[w] || WORDS[w + 's']; return f ? n + ' ' + plural(n, f) : null; }
  var PATTERNS = [
    [/^(\d+)\s*(m|min|h|d|w) ago$/i, function (m) { return 'منذ ' + m[1] + ' ' + unit(m[1], m[2].toLowerCase()); }],
    [/^(\d+)(min|h|d) ago(.*)$/i, function (m) { return 'منذ ' + m[1] + ' ' + unit(m[1], m[2].toLowerCase()) + tr(m[3]); }],
    [/^([\d,.]+K?)\s+(comments?|reposts?|members?|posts?|views?|connections?|listings?|companies|company|providers|clients|inquiries|results|sites?|open positions|requests received|request received|new posts today|new posts this week|deals closed)$/i, function (m) { return word(m[1], m[2]); }],
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
    [/^(\d+) profiles$/, function (m) { return word(m[1], 'profiles'); }], [/^#(\d+) top-rated candidate$/, function (m) { return 'المرشح #' + m[1] + ' الأعلى تقييمًا'; }],
    [/^(\d+) warnings?$/, function (m) { return word(m[1], 'warnings'); }], [/^(\d+) new posts?$/, function (m) { return word(m[1], 'new posts'); }],
    [/^(\d+) new requests today$/, function (m) { return word(m[1], 'new requests today'); }], [/^(\d+) quote requests today$/, function (m) { return word(m[1], 'quote requests today'); }],
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
  var CAPS = { COURSES: 'دورات', REGULATORY: 'التسجيل', FORMULATION: 'التركيبات', 'MARKET POSTS': 'منشورات سوق', 'REGULATORY UPDATES': 'تحديثات تسجيل', LISTINGS: 'إعلان', SUPPLY: 'عرض', DEMAND: 'طلب', SUPPLIERS: 'مورّد', CONNECTIONS: 'اتصالات', PENDING: 'معلّقة', UNREAD: 'غير مقروء', TOTAL: 'إجمالي' };
  PATTERNS.push(
    [/^[A-Za-z0-9 .,K]+( \/ [A-Za-z0-9 .,K]+)+$/, function (m) { var ok = 0, out = m[0].split(' / ').map(function (seg) { seg = seg.trim(); var U = seg.toUpperCase(); if (DAYS[U]) { ok++; return DAYS[U]; } var x = /^([\d.,]+K?) ([A-Za-z ]+)$/.exec(seg); if (x && CAPS[x[2].toUpperCase()]) { ok++; return x[1] + ' ' + CAPS[x[2].toUpperCase()]; } if (CAPS[U] && !/\d/.test(U)) { ok++; return CAPS[U]; } return seg; }).join(' / '); return ok ? out : null; }],
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
  /* dates the app prints with the browser's default toLocaleString() (e.g. 10/3/2026, 1:36:27 AM) are re-written in Arabic */
  var DLOC = (function () { try { return Intl.DateTimeFormat().formatToParts(new Date(2001, 10, 22)).filter(function (p) { return /day|month|year/.test(p.type); }).map(function (p) { return p.type; }); } catch (e) { return ['month', 'day', 'year']; } })();
  function arDate(m) {
    var v = {}; DLOC.forEach(function (k, i) { v[k] = +m[i + 1]; }); if (!(v.month >= 1 && v.month <= 12 && v.day >= 1 && v.day <= 31)) return null;
    var h = m[4] == null ? null : m[7] ? +m[4] % 12 + (/PM/i.test(m[7]) ? 12 : 0) : +m[4], d = new Date(v.year, v.month - 1, v.day, h || 0, +(m[5] || 0), +(m[6] || 0));
    try { return window.dxFmtDate(d, h != null); } catch (e) { return null; }
  }
  window.dxFmtDate = function (d, withTime) {   /* one formatter for dates in the interface language (Latin digits, like the rest of the Arabic UI) */
    d = d instanceof Date ? d : new Date(d); var ar = document.documentElement.lang === 'ar';
    var o = { year: 'numeric', month: 'short', day: 'numeric' }; if (withTime) { o.hour = 'numeric'; o.minute = '2-digit'; }
    return new Intl.DateTimeFormat(ar ? 'ar-EG-u-nu-latn' : 'en-GB', o).format(d);
  };
  var DATE = '(\\d{1,2})/(\\d{1,2})/(\\d{4})(?:,? (\\d{1,2}):(\\d{2})(?::(\\d{2}))?\\s?(AM|PM)?)?';
  var MON = { Jan: 'يناير', Feb: 'فبراير', Mar: 'مارس', Apr: 'أبريل', May: 'مايو', Jun: 'يونيو', Jul: 'يوليو', Aug: 'أغسطس', Sep: 'سبتمبر', Oct: 'أكتوبر', Nov: 'نوفمبر', Dec: 'ديسمبر' };
  var WDAY = { Sat: 'السبت', Sun: 'الأحد', Mon: 'الاثنين', Tue: 'الثلاثاء', Wed: 'الأربعاء', Thu: 'الخميس', Fri: 'الجمعة' };
  var UNIT = { kg: 'كجم', g: 'جم', pc: 'قطعة', pcs: 'قطعة', unit: 'وحدة', tablet: 'قرص', box: 'علبة', L: 'لتر', mL: 'مل', MT: 'طن' };
  PATTERNS.push(
    [new RegExp('^' + DATE + '$'), arDate], [new RegExp('^sent ' + DATE + '$'), function (m) { var d = arDate(m); return d ? 'أُرسل ' + d : null; }],
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
    if (t.indexOf(' · ') > 0) { var parts = t.split(' · '), hit = 0; parts = parts.map(function (p) { var q = tr(p); if (q !== p) hit++; return q; }); if (hit) return parts.join(' · '); }
    var pre = /^([A-Za-z][A-Za-z &/]+:)\s+(.+)$/.exec(t); if (pre && D[pre[1]]) return D[pre[1]] + ' ' + pre[2];
    /* leading icons / trailing arrows around a known phrase */
    var mm = /^([^A-Za-z]*?)([A-Za-z][^→←]*?)(\s*[→←])?$/.exec(t);
    if (mm && D[mm[2].trim()]) return mm[1] + D[mm[2].trim()] + (mm[3] ? ' ' + ARROWS[mm[3].trim()] : '');
    return null;
  }
  window.dxT = tr;
  /* the original (English) text of an element, whatever the interface language — so logic never depends on the language shown */

  /* never translate what people wrote */
  var SKIP = 'script,style,svg,input,textarea,[contenteditable],.post-body,.post-text,.msg-text,.bubble,.mx-msg,.cmt-text,.dx-entity,.lc-title,.sp-title,.sc-title,.jc-title,.gcard-title,.gcard-desc,.dl-title,[data-noi18n]';   /* whole blocks people wrote */
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
