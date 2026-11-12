# برامج مشابهة — eCTD publishing / validation / authoring (06/11/2026)

**تحديث 12/11/2026:** صف Freyr اتحدّث من موقع المنتج نفسه (ectdtool.com)، واتضاف RATools-for-eCTD من GitHub، وMono eCTD Viewer من موقعه، وeCTD Indexer من SourceForge. اللي هناخده منهم في `UPDATES.md`.

**مصدر المعلومات:** بحث ويب، وأغلبه **مواد تسويقية من الشركات نفسها، أو مواقع مقارنة**، مش اختبار فعلي. أي رقم أو ميزة مكتوب «حسب الشركة» محتاج يتأكد بديمو قبل ما نعتمد عليه. الروابط في §7.

## 1. أهم معلومة: شريك الهيئة نفسها

| البند | التفاصيل |
|---|---|
| **EXTEDO (ألمانيا) + DAF للحلول الرقمية (مصر)** | الشريكين الرسميين للهيئة في مشروع الـ eCTD. **المرحلة الأولى (2025):** تطبيق الـ eCTD، وحل للمراجعة، وبوابة تقديم. **المرحلة التانية (أُطلقت 14/06/2026):** بوابة اتصال في الاتجاهين مع الهيئة، وMaster Data Management، وRegulatory Procedure Management (RPM)، وDocument Management |
| المواعيد الرسمية (صفحة أخبار الهيئة بالإنجليزي، 14/06/2026) | «Regulatory Process Management System to Go Live by **February 2027**, with Full eCTD Implementation Targeted for **Q1 2028**». الخبر العربي في جريدة المال بيحدد إن المقصود **eCTD الإصدار 4.0** |
| منتج EXTEDO للشركات | **eCTDmanager**، وبيتباع داخلي أو مستضاف. بيبني ويعرض ويتحقق وينشر، وفيه التسلسلات والـ lifecycle واستيراد ملفات eCTD قديمة، وإجراءات أوروبية (MRP/DCP)، وبحث نصي وتقارير وتعليقات. بيقول إنه جاهز لـ v4.0 (حسب الشركة) |
| تدريب السوق المصري | EXTEDO وDAF عاملين ديمو وتدريب 7 أسابيع على تسجيل CTD/eCTD في مصر، وسلسلة ندوات من 3 أجزاء **أغلبها بالعربي** |
| **⚠️ مستند مهم يتلاحق** | إعلان الندوة بيقول إن **مواصفة الـ Module 1 المصرية ومعايير التحقق اتنشروا** («milestone»). ما لقيناش المستند نفسه على موقع الهيئة، فممكن يكون بيتوزّع عن طريق EXTEDO وDAF أو جوه البوابة. **ده أهم مستند ناقص عندنا** |
| معلومة تانية (EXTEDO FAQ، مش رسمية) | «eCTD accepted from Q3/2025; mandatory January 2026 for new pharmaceutical registrations». بتتعارض مع خطاب الهيئة اللي بيقول «التطبيق الكامل الربع الأول 2028»، فممكن يكونوا قصدهم مراحل. **محتاج تأكيد رسمي** |

**المعنى العملي:** الهيئة على الأرجح بتتحقق من الملفات بأداة EXTEDO. يبقى **أي أداة بنعملها لازم ملفها يعدّي على مدقّق EXTEDO**، وEXTEDO في نفس الوقت **منافس مباشر** في السوق المصري.

## 1b. أداة رسمية من الهيئة: EDA Variation Self-Guided Tool

**الرابط:** `eservices.edaegypt.gov.eg/EDAVariationTool/`. أُعلن عنها 14/09/2023، والإصدار 1.0 (© 2026).

**بتعمل إيه:**
- بتغطي البشري والعشبي والبيطري والمستلزمات الطبية.
- بتبحث بالمجموعة (Drug Substance أو Drug Product) ونوع التغيير وفئة PAC.
- لكل تغيير بتعرض الشروط والمطلوب، ورابط التقديم، والإطار الزمني، ودليل التقديم.
- فيها «سلة» بتجمع التغييرات المختارة.

**حدودها:** بتعرض المعلومة بس. ما بتبنيش ملف، ولا بتحدد أقسام الـ CTD اللي تتحدّث، ولا بتفحص المستندات.

**القيمة لينا:** بياناتها اتسحبت في `data/EDA_VariationTool_2026-11-06.csv`، 90 تغيير بشري بفئاتها وشروطها. لو اتربطت بـ NP.CAPP.112 تبقى أساس «ملف التغيير الآلي».

## 2. المنافسين العالميين

| البرنامج | النوع | بيعمل إيه | ملاحظات |
|---|---|---|---|
| **LORENZ docuBridge + eValidator** (ألمانيا) | نشر وتحقق، ديسكتوب أو سيرفر | تجميع eCTD، وإخراج متعدد من نفس التسلسل (eCTD وNeeS وHTML وPDF وورق)، ومدقق بقواعد إقليمية كتير. **eValidator Basic مجاني** ويشتغل لوحده. بيقول إنه بيدعم v4.0 أوروبا في إصدار 25.2 | **FDA وHealth Canada بيستخدموه.** باقات: ONE (مستخدم واحد)، وTWO (فريق ومنطقتين)، وFIVE. ريفيوهات بتقول إن الواجهة قديمة |
| **Veeva Vault Submissions Publishing** (أمريكا) | سحابي جوه منصة RIM | نشر مستمر (بيتجمّع ويتحقق أول بأول)، وتحقق في الخلفية واختبار الروابط، وبناء الملف بقواعد من خطة المحتوى، وتحويل الروابط. بيدعم v4.0 (اليابان 1.6، وأمريكا 1.8، وأوروبا 1.3)، والإرسال المباشر لبوابات FDA وEMA | الأغلى، ومخصص للشركات الكبيرة |
| **Certara GlobalSubmit** (أمريكا) | ويب سحابي، PUBLISH وVALIDATE وREVIEW | نشر من المتصفح من غير تثبيت (3.2.2)، وتحقق من أخطاء eCTD وNeeS، وعارض بأكتر من 40 فحص PDF (حسب الشركة) | **FDA بتستخدمه من 2005، وANVISA في البرازيل لـ v4.0**. وعندهم **CoAuthor**، كاتب بالذكاء الاصطناعي جوه Word، فيه أكتر من 275 قالب eCTD (حسب الشركة) |
| **Ennov** (فرنسا) | eCTD247 سحابي للشركات الصغيرة والمتوسطة، وDossier للمتوسطة والكبيرة، وInSight Publishing (اتشترى من Calyx/Liquent) للكبيرة | نشر وتحقق | بيقولوا إنهم من 4 شركات بس قدّموا تسلسلات v4.0 تجريبية لـ EMA (11 تجربة مع EMA وFDA وPMDA) |
| **Freyr SUBMIT PRO** (الهند) | سحابي، أو على سيرفر الشركة | إنشاء وتحقق ونشر، ومدقق مدمج («أكتر من 800 سيناريو خطأ» حسب الشركة)، ومدير PDF (bookmarks وروابط)، و**نسخ Modules 2–5 من ملف سابق**، والإحالة لمستندات تقديم سابق، واستيراد تسلسلات من برامج تانية، وعارض بأكتر من شكل (تراكمي، بالتسلسل، بالنشاط، بالدراسات)، ومتابعة التقديمات وأسئلة الهيئات. 21 CFR Part 11 | **الدول (من موقعه، 12/11/2026):** أمريكا، وأوروبا، وكندا، وسويسرا، وأستراليا، والخليج، والأردن، وتايلاند، وجنوب أفريقيا، والاتحاد الأوراسي، والصين، وآسيان. **مفيش مصر.** بيطلّع eCTD 3.2.2 وNeeS، وeCTD 4.0 لسه «هيدعمه» لـ FDA. **الأسعار المنشورة:** GEO بـ 4,125$ للمستخدم في السنة لهيئة واحدة، و1,450$ لكل هيئة زيادة. إيجار بـ 1,925$ لـ 3 شهور، أو 3,025$ لـ 6 شهور. ASSIST بـ 26,400$ في السنة (3 مستخدمين وخدمة نشر). والتجهيز بياخد 4 لـ 6 أسابيع |
| **Mono eCTD Viewer** (Mono Software)، ومعاه Mono eCTD Office للنشر وMono eCTD Validator | ويندوز ديسكتوب | عرض الـ lifecycle (تراكمي، وحالي، وبالتسلسل)، ومقارنة المستند ببديله، ومقارنة تسلسلين، ومستكشف الروابط جوه الـ PDF (ومعاه Fast Web View وخصائص الملف)، وبحث في نص كل المستندات، وملاحظات وعلامات للمراجعة، ودمج العرض في PDF واحد، وأداة تصليح الـ MD5. التحقق والـ 4.0 بزيادة | **الدول:** أمريكا، وكندا، وأوروبا، والمملكة المتحدة، والبوسنة، وسويسرا، والخليج، والأردن، وأستراليا، وتايلاند، وتونس، وجنوب أفريقيا، والصين، وسنغافورة، وأوكرانيا، والـ WHO. **مفيش مصر**، لا في العارض ولا في Office. الـ 4.0 لأوروبا وأمريكا بس. الواجهة بـ 6 لغات أوروبية، ومفيش عربي. **الأسعار (للكمبيوتر الواحد في السنة):** Beginner مجاني، وProfessional بـ 350€، وExpert بـ 450€، وMaster بـ 550€. لو ضفت التحقق والـ 4.0 السعر بيوصل لـ 990€ |
| **Image Solutions eCTDXPress Aspire** / **Assyro** / **DnXT** | ويب للشركات الصغيرة والمتوسطة | نشر من غير فريق نشر متخصص | — |

## 3. أدوات مجانية أو مفتوحة المصدر

| الأداة | بتعمل إيه | حدودها |
|---|---|---|
| **RATools-for-eCTD** (GitHub، رخصة AGPL-3.0، آخر تحديث 11/11/2026) | نظام نشر eCTD (.NET 8 وReact وPostgreSQL). فيه التطبيقات والتسلسلات، واستيراد ملف eCTD موجود، وbackbone لـ FDA 3.2.2. الـ EU 3.2.2 عندهم «تحت التحكم» ومش مفعّل. وفيه فاحص مستقل لأي باكدج (37 فحص: XML وDTD، والـ lifecycle، والـ MD5، والـ ZIP، والروابط جوه الـ PDF)، وتجميد التسلسل بعد التقديم، وكل قاعدة مربوطة بمصدرها الرسمي وبصمته | مفيش مصر ولا الخليج. بيقول بنفسه إن مفيش ولا ملف تعريف مؤهل للتقديم الرسمي. الرخصة AGPL: نقرا بس، ومناخدش كود |
| **eCTD-indexer** (SourceForge بـ GPLv2، ونسخة على GitHub بـ GPL v3) | بيولّد `index.xml` و`eu-regional.xml` لملفات أوروبا (C#، وبيشتغل على ويندوز ولينكس) | **متوقف:** آخر تحديث على SourceForge في 19/11/2016، وحالته Beta، ومبني على EU M1 v2.0 (2013)، وأوروبا دلوقتي على 3.1.1. مفيش فيه حاجة ناخدها |
| **LORENZ eValidator Basic** | تحقق مجاني | تحقق بس |
| **Liquent eCTD Reviewer** (قديم) و**Altair viewer** (نسخة مجانية محدودة لـ v4.0) و**Mono eCTD Viewer** (Beginner مجاني) | عرض | عرض بس |

## 4. الميزات الأساسية اللي كل البرامج دي فيها

1. بناء التسلسل: فولدرات ICH، والـ backbone XML، والـ checksums، والـ envelope الإقليمي.
2. الـ lifecycle: new/replace/delete، والتسلسلات المرتبطة، والـ current view، واستيراد ملفات قديمة.
3. مدقق بقواعد كل هيئة (Pass/Fail وBest Practice) مع تقرير.
4. أدوات PDF: الإصدار، والـ bookmarks، والروابط، والخطوط، وFast Web View، و**تحويل الروابط بين المستندات**.
5. عارض للملف بطريقة المراجع.
6. نسخ وإعادة استخدام ملفات لدول تانية، وتعدد المستخدمين، والصلاحيات، وسجل المراجعة (Part 11).
7. الكبار عندهم كمان: النشر المستمر، والإرسال المباشر لبوابات الهيئات، وإدارة المحتوى (RIM)، و**الكتابة بالذكاء الاصطناعي** (Certara CoAuthor).

## 5. الفجوة اللي أداتنا تقدر تملاها

| الفجوة عند المنافسين | ميزتنا الممكنة | المصدر في معرفتنا |
|---|---|---|
| كلهم بيبدأوا **بعد** ما المستند يجهز، يعني بيجمعوا وينشروا بس | **نعرف المطلوب قبل ما يتكتب**: قائمة المتطلبات حسب نوع المنتج من NP.CAPP.065 v5، وقاعدة «المستند غير المطابق يتبني من الأول» | `CTD-KNOWLEDGE-BASE.md` §3–4، و`checklist/` |
| مفيش حد بيراجع **المحتوى** على نواقص الهيئة المصرية | فحص تلقائي لـ NP.CAPP.040: نتائج رقمية مش «Conform»، وQ للذوبان، وعمود المرجع الدستوري، وتشغيلتين على الأقل، وIR متزامن، وQ3D/M7/نيتروزامين/بنزين، والتطابق مع الـ CPP | `CTD-KNOWLEDGE-BASE.md` §6 |
| مفيش حد بيطلّع **ملف CTD الـ One Submission** (غير eCTD) اللي الهيئة بتستقبله النهارده | مخرج CTD بترقيم NP.CAPP.065 جنب eCTD 3.2.2 و4.0، والتلاتة من نفس البيانات | `APP-PLAN.md` §4 |
| خطابات Module 1 المصرية بالعربي ما بيعملهاش حد | نموذج الطلب Annex I بالتعهد العربي، وإقرار التركيب، وحساب الملح، وتعهدات الـ CEP والثبات، وإقرار الترجمة | NP.CAPP.065 Annex I |
| **التغييرات بفئات PAC** وأقسامها المصرية | خريطة NP.CAPP.112 (13 تغيير في المادة الفعالة و27 في المنتج النهائي) وفئات v6 | `CTD-KNOWLEDGE-BASE.md` §7 |
| واجهات إنجليزي بس، وتراخيص غالية بالدولار، وأغلبها سحابي برة مصر | واجهة عربي وإنجليزي، وتسعير للسوق المصري، وتشغيل محلي من غير ما الملفات السرية تطلع برة الشركة | — |
| الكتابة بالذكاء الاصطناعي عند الكبار بس، وبقوالب عامة | توليد جداول Module 3 والـ QOS من البيانات بقوالب WHO وNP.CAPP.040 | WHO QOS-PD 2025 |

**ولا برنامج من اللي اتراجعوا بيدعم مصر:** لا Freyr، ولا Mono، ولا RATools، ولا eCTD Indexer، ومقال IntuitionLabs ما ذكرش مصر. الوحيد EXTEDO، شريك الهيئة.

**نموذج السعر للشركات الصغيرة** (مقال IntuitionLabs، تحديث 15/10/2026، نقلًا عن PerfectDossier): الشركة اللي بتقدّم أقل من 10 ملفات في السنة غالبًا بتكسب لو استعانت بشركة خدمات أو دفعت بالتقديم، زي **docuBridge ONE** من LORENZ (مستخدم واحد على كمبيوتر واحد، والدفع بـ tokens لكل تقديم). اللي بتقدّم أكتر من 25 في السنة بتكسب لو اشترت برنامج. الصيانة السنوية للبرامج المشتراة حوالي 20% من سعر الترخيص. ده بيدعم إن برنامجنا يتسعّر للسوق المصري بالتقديم، أو بترخيص محلي رخيص.

**مش هننافس فيه دلوقتي:** RIM كامل، والإرسال المباشر لبوابات FDA وEMA، والإجراءات الأوروبية متعددة الدول. ده ملعب Veeva وLORENZ وEXTEDO.

## 6. اللي محتاج يتعمل بعد كده (معرفة مش كود)

1. **نجيب مواصفة الـ EG Module 1 ومعايير التحقق** اللي EXTEDO وDAF بيقولوا إنها اتنشرت. نسجّل في الندوة، أو نطلبها من DAF أو من الهيئة، أو ندوّر جوه بوابة `reg-submit`.
2. **ديمو لـ eCTDmanager** (من EXTEDO وDAF)، علشان نشوف الملف المصري بيطلع إزاي وإيه اللي المدقق بيرفضه.
3. **نجرّب LORENZ eValidator Basic** (مجاني) على أمثلة EMA اللي عندنا، علشان نشوف شكل تقرير التحقق.
4. **eCTD-indexer:** اتراجع في 12/11/2026. لقيناه متوقف من 2016 ومبني على EU M1 v2.0، والـ writers بتوعنا أحدث منه، فمش محتاجينه.

## 7. المصادر

- EDA news, Phase II (14/06/2026): https://edaegypt.gov.eg/en/media-center/news/the-eda-launches-phase-ii-of-the-electronic-common-technical-document-ectd-project-to-advance-digital-transformation-and-enhance-the-regulatory-system-in-cooperation-with-daf-and-extedo/
- EXTEDO, Egypt demo Q&A: https://www.extedo.com/blog/ectdmanager-demo-for-the-egyptian-life-science-industry-qa
- EXTEDO, EDA phase II: https://www.extedo.com/blog/egyptian-drug-authority-and-extedo-launch-phase-ii-of-egypts-pharmaceutical-digital-transformation
- EXTEDO, Egypt webinar: https://www.extedo.com/events/webinar-navigate-egypts-digital-shift-to-ectd-for-regulatory-submissions
- EXTEDO Egypt CTD/eCTD agenda: https://www.extedo.com/hubfs/Documents/Other%20Documents/Agenda%20CTD%20eCTD%20Egypt%20August.pdf
- LORENZ (overview): https://intuitionlabs.ai/articles/lorenz-docubridge-ectd-guide · FDA use: https://www.biospace.com/lorenz-docubridge-evalidator-and-automator-go-live-at-the-usfda
- Veeva help (eCTD 4.0 versions): https://regulatory.veevavault.help/en/lr/48611 · product: https://www.veeva.com/products/vault-submissions-publishing/
- Certara GlobalSubmit: https://www.certara.com/globalsubmit-ectd-submission-software/review/ · validate help: https://onlinehelp.certara.com/globalsubmit/22.9.1/GlobalSubmit/Validate/Validate.htm · CoAuthor: https://certara.com/coauthor
- Ennov eCTD247: https://vtr-website.pages.dev/en/products/ennov/ectd247.html
- Freyr SUBMIT PRO: https://freyrsolutions.com/ectd-software · https://www.capterra.com/p/179228/FreyrSUBMITPRO/
- eCTD-indexer: https://github.com/Quantentunnel/ectd_indexer
- Freyr SUBMIT PRO (موقع المنتج، 12/11/2026): https://www.ectdtool.com/ · الأسعار: https://www.ectdtool.com/ectd-pricing-plan · الأسئلة الشائعة: https://www.ectdtool.com/faq
- RATools-for-eCTD: https://github.com/PharmaRA/RATools-for-eCTD
- Mono eCTD Viewer: https://ectdviewer.pro/ · Mono eCTD Office: https://ectdoffice.com/
- eCTD Indexer (SourceForge): https://sourceforge.net/projects/ectdindexer/
- Comparisons: https://intuitionlabs.ai/articles/ectd-publishing-software-comparison · https://intuitionlabs.ai/articles/ectd-software-small-pharma
