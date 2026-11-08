"""Writes rulepacks/eda.ctd.nta065.v5/templates/library.yaml: for every requirement of the EDA pack, what the document looks
like (sections, fields, tables), whether the program can draft it from the base documents (full / partial / none), which base
documents feed it, and an example of an acceptable one. Shared section sets keep the 101 entries consistent."""
import yaml, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
REQS = yaml.safe_load(open(ROOT / 'rulepacks/eda.ctd.nta065.v5/requirements.yaml', encoding='utf-8'))

T = lambda en, ar: {'en': en, 'ar': ar}


def sec(id_, en, ar, kind='para', hint_en='', hint_ar='', columns=None, fields=None, source=None, lang=None):
    s = {'id': id_, 'title': T(en, ar), 'kind': kind}
    if hint_en or hint_ar:
        s['hint'] = T(hint_en, hint_ar)
    if columns:
        s['columns'] = columns
    if fields:
        s['fields'] = fields
    if source:
        s['source'] = source                     # data the program fills itself: product | apis | composition | batches | specs | manufacturers | packs
    if lang:
        s['lang'] = lang
    return s


# ---- shared section sets
PRODUCT_ID = sec('product', 'Product identification', 'بيانات المستحضر', 'fields', source='product',
                 fields=[{'key': 'trade_name', 'label': T('Trade name', 'الاسم التجاري')}, {'key': 'dosage_form', 'label': T('Pharmaceutical form', 'الشكل الصيدلي')},
                         {'key': 'strength', 'label': T('Strength', 'التركيز')}, {'key': 'pack', 'label': T('Pack', 'العبوة')},
                         {'key': 'manufacturer', 'label': T('Manufacturer', 'المصنّع')}, {'key': 'applicant', 'label': T('Applicant / licence holder', 'مقدم الطلب / مالك الترخيص')},
                         {'key': 'registration_number', 'label': T('Registration / request number', 'رقم التسجيل / الطلب')}])
LETTER_HEAD = [sec('date', 'Date', 'التاريخ', 'fields', fields=[{'key': 'date', 'label': T('Date', 'التاريخ')}], source='product'),
               sec('to', 'Addressee', 'الجهة الموجّه لها', 'para', 'Egyptian Drug Authority — General Administration for Human Pharmaceuticals Registration (or the department named in the requirement).',
                   'هيئة الدواء المصرية — الإدارة العامة لتسجيل المستحضرات البشرية (أو الإدارة المذكورة في المتطلب).'),
               sec('subject', 'Subject', 'الموضوع', 'para', 'One line: document type, trade name, form, strength.', 'سطر واحد: نوع المستند، الاسم التجاري، الشكل، التركيز.')]
SIGN = sec('signature', 'Signature block', 'التوقيع والختم', 'fields', 'Authorised signatory name and title, company name, stamp; printed on company letterhead, signed, stamped, dated, then scanned.',
           'اسم المفوَّض بالتوقيع ووظيفته، اسم الشركة، الختم؛ يُطبع على ورق الشركة ويُوقَّع ويُختم ويُؤرَّخ ثم يُمسح.',
           fields=[{'key': 'signatory', 'label': T('Signatory', 'المفوَّض بالتوقيع')}, {'key': 'signatory_title', 'label': T('Title', 'الوظيفة')}, {'key': 'company', 'label': T('Company', 'الشركة')}])
MANUF_TABLE = sec('manufacturers', 'Manufacturers and sites', 'المصنّعون والمواقع', 'table', 'Every site with its responsibility (manufacture, packaging, QC testing, release); addresses exactly as on the GMP certificate / licence.',
                  'كل موقع ومسؤوليته (تصنيع، تعبئة، اختبار، إفراج)؛ العناوين كما في شهادة GMP / الرخصة.', columns=['Name', 'Address', 'Country', 'Responsibility', 'GMP / licence ref.'], source='manufacturers')
SPEC_TABLE = sec('specification', 'Specification table', 'جدول المواصفات', 'table', 'Universal tests first (description, identification, assay, impurities), then specific tests; a reference column with the general-chapter number; identification never by a single retention time.',
                 'الاختبارات العامة أولًا (الوصف، التعرّف، التقدير، الشوائب) ثم الاختبارات الخاصة؛ عمود المرجع برقم الفصل العام؛ التعرّف لا يكون بزمن احتباس واحد.', columns=['Test', 'Acceptance criterion', 'Method', 'Reference (chapter)'], source='specs')
BATCH_TABLE = sec('batches', 'Batch analyses', 'نتائج التشغيلات', 'table', 'At least two recent batches: number, size, date, type (pilot/production), site; numeric results for every test, never «conforms».',
                  'تشغيلتان حديثتان على الأقل: الرقم، الحجم، التاريخ، النوع، الموقع؛ نتائج رقمية لكل اختبار، وليس «مطابق».', columns=['Batch no.', 'Size', 'Date', 'Type', 'Site', 'Test', 'Limit', 'Result'], source='batches')
METHODS = [sec('procedures', 'Analytical procedures', 'الطرق التحليلية', 'list', 'For every test of the specification: principle, reagents, standard and sample preparation, system suitability, calculation; compendial methods cited by chapter.',
               'لكل اختبار في المواصفة: المبدأ، الكواشف، تحضير القياسي والعينة، ملاءمة النظام، الحساب؛ الطرق الدستورية بالإشارة إلى الفصل.'),
           sec('validation', 'Validation / verification summary', 'ملخص التحقق', 'table', 'In-house methods validated per ICH Q2(R2); compendial methods verified; chromatograms for specificity, forced degradation and SST referenced.',
               'الطرق الداخلية متحقَّق منها حسب ICH Q2(R2)؛ الدستورية مُتحقَّق من ملاءمتها؛ الإشارة إلى الكروماتوجرامات (النوعية، التحلل القسري، ملاءمة النظام).',
               columns=['Test / method', 'Specificity', 'Linearity & range', 'Accuracy', 'Precision', 'LOD / LOQ', 'Robustness', 'Report ref.'])]
RS = sec('standards', 'Reference standards', 'المواد المرجعية', 'table', 'Primary standard source and lot; working standard with its CoA and the primary lot it was standardised against; impurity standards; concomitant IR primary vs secondary.',
         'مصدر القياسي الأولي ورقم دفعته؛ القياسي العامل وشهادته والقياسي الأولي الذي عُيِّر عليه؛ قياسيات الشوائب؛ IR متزامن للأولي والثانوي.', columns=['Standard', 'Type (primary/working/impurity)', 'Source', 'Lot', 'Purity / assigned value', 'CoA / IR ref.'])
CONTAINER = [sec('description', 'Description of the container closure system', 'وصف نظام العبوة', 'para', 'Every component with material, supplier, and the specification it is tested against.', 'كل مكوّن ومادته ومورّده والمواصفة التي يُختبر عليها.'),
             sec('specs', 'Specifications of the components', 'مواصفات المكوّنات', 'table', columns=['Component', 'Material', 'Test', 'Limit', 'Method']),
             sec('suitability', 'Suitability', 'الملاءمة', 'para', 'Protection, compatibility, safety; IR of the reference material versus the test material; supplier CoA referenced.', 'الحماية، التوافق، السلامة؛ IR للمادة المرجعية مقابل العينة؛ الإشارة إلى شهادة المورّد.')]
STABILITY = [sec('summary', 'Stability summary and conclusion', 'ملخص الثبات والخلاصة', 'para', 'Batches studied, conditions (long-term, accelerated, intermediate), container, data available, proposed shelf life / retest period and storage statement.',
                 'التشغيلات المدروسة، الظروف (طويل الأمد، معجّل، متوسط)، العبوة، البيانات المتاحة، مدة الصلاحية / إعادة الاختبار المقترحة وعبارة التخزين.'),
             sec('protocol', 'Protocol and batches', 'البروتوكول والتشغيلات', 'table', columns=['Batch no.', 'Type / size', 'Container', 'Condition', 'Start date', 'Time points', 'Tests']),
             sec('results', 'Results summary', 'ملخص النتائج', 'table', 'Numeric results per time point; trends discussed; out-of-trend results explained.', 'نتائج رقمية لكل نقطة زمنية؛ مناقشة الاتجاهات؛ تفسير أي نتيجة خارج الاتجاه.',
                 columns=['Batch', 'Condition', 'Time point', 'Test', 'Limit', 'Result']),
             sec('forced', 'Forced degradation / photostability', 'التحلل القسري / الثبات الضوئي', 'para'),
             sec('commitment', 'Post-approval commitment and ongoing studies', 'التعهد والدراسات الجارية', 'para', 'Signed commitment letters referenced; ongoing batches and their schedule.', 'الإشارة إلى خطابات التعهد الموقَّعة؛ التشغيلات الجارية وجدولها.')]
JUSTIFICATION = [sec('tests', 'Rationale per test', 'مبررات كل اختبار', 'table', 'Why each test and limit: pharmacopoeia, ICH Q3A/Q3B/Q3C/Q3D/M7, batch data, stability; non-routine tests justified (skip testing).',
                     'سبب كل اختبار وحدّه: دستور الأدوية، ICH Q3A/Q3B/Q3C/Q3D/M7، بيانات التشغيلات، الثبات؛ تبرير الاختبارات غير الروتينية.', columns=['Test', 'Limit', 'Justification', 'Reference'])]
STUDY_LIST = sec('studies', 'Tabular listing of studies', 'قائمة الدراسات', 'table', 'Every clinical study including pilot and failed BE studies (WHO screening 12e/f).', 'كل الدراسات السريرية بما فيها التجريبية والفاشلة (WHO screening 12e/f).',
                 columns=['Study ID', 'Type / design', 'Test product (batch)', 'Reference product', 'Subjects', 'Site / CRO', 'Dates', 'Report location (5.3.x)'])
EXAMPLE_LETTER = T('On company letterhead: date, addressed to EDA, subject with trade name / form / strength, the statement itself, product identification, signature of the authorised person with title, company stamp.',
                   'على ورق الشركة: التاريخ، موجَّه لهيئة الدواء، الموضوع بالاسم التجاري / الشكل / التركيز، نص الإقرار، بيانات المستحضر، توقيع المفوَّض ووظيفته، ختم الشركة.')


def entry(id_, kind, draft, sections=None, inputs=None, example=None, lang='en', letterhead=False, generator=None, note=None):
    e = {'id': id_, 'kind': kind, 'draft': draft, 'lang': lang}
    if letterhead:
        e['letterhead'] = True
    if generator:
        e['generator'] = generator
    if inputs:
        e['inputs'] = inputs
    if sections:
        e['sections'] = sections
    if example:
        e['example'] = example
    if note:
        e['note'] = note
    return e


L = {}
# ---------------- Module 1
L['M1-01'] = entry('M1-01', 'form', 'generator', generator='annex1', inputs=['registration_licence', 'pricing_certificate', 'leaflet'], letterhead=True, lang='both',
                   example=T('The EDA Annex I form with every field filled (one box per API), the Arabic undertaking per the decree case, signed by the chairman / authorised signatory, stamped and dated.',
                             'نموذج Annex I بكل حقوله (خانة لكل مادة فعالة) + التعهد العربي حسب حالة القرار، موقَّع من رئيس مجلس الإدارة / المفوَّض، مختوم ومؤرَّخ.'))
L['M1-09'] = entry('M1-09', 'leaflet', 'full', lang='both', inputs=['leaflet', 'registration_licence', 'analysis_conformity'],
                   example=T('Proposed SmPC and PIL in English and Arabic as Word files, in the standard section order, aligned with the latest reference SmPC/PIL; a PDF copy goes in the eCTD and the Word files in the working documents.',
                             'الـ SmPC والنشرة المقترحتان عربي وإنجليزي Word، بترتيب الأقسام القياسي، مطابقتان لآخر نشرة مرجعية؛ نسخة PDF في الـ eCTD وملفات Word في مستندات العمل.'),
                   sections=[sec('smpc', 'SmPC sections 1–10', 'أقسام الـ SmPC 1–10', 'list', 'Name; qualitative and quantitative composition; pharmaceutical form; clinical particulars 4.1–4.9; pharmacological properties 5.1–5.3; pharmaceutical particulars 6.1–6.6; MAH; MA number; dates. Text from the reference SmPC adapted to this product (strengths, excipients, pack, MAH); warnings per EDA pharmacology guidelines.',
                                 'الاسم؛ التركيب النوعي والكمي؛ الشكل الصيدلي؛ البيانات السريرية 4.1–4.9؛ الخواص الدوائية 5.1–5.3؛ البيانات الصيدلية 6.1–6.6؛ مالك الترخيص؛ رقم الترخيص؛ التواريخ. النص من الـ SmPC المرجعي مع تعديله لهذا المستحضر (التراكيز، السواغات، العبوة، المالك)؛ التحذيرات حسب إرشادات الفارماكولوجي بالهيئة.'),
                             sec('pil', 'PIL sections 1–6 (EN + AR)', 'النشرة الداخلية 1–6 (عربي + إنجليزي)', 'list', 'What X is and what it is used for; before you take; how to take; possible side effects; how to store; contents of the pack and other information. Arabic by an authorised medical translation (company review required).',
                                 'ما هو X وفيم يُستخدم؛ قبل الاستخدام؛ طريقة الاستخدام؛ الآثار الجانبية؛ التخزين؛ محتويات العبوة ومعلومات أخرى. العربية بترجمة طبية معتمدة (مراجعة الشركة مطلوبة).'),
                             sec('alignment', 'Alignment with the reference', 'المطابقة مع المرجع', 'table', columns=['Section', 'Reference text (version/date)', 'Proposed text', 'Difference and reason'])])
L['M1-10'] = entry('M1-10', 'declaration', 'generator', generator='translation', letterhead=True, lang='both', inputs=['leaflet'], example=EXAMPLE_LETTER)
L['M1-11'] = entry('M1-11', 'artwork', 'partial', lang='both', inputs=['leaflet', 'registration_licence', 'pricing_certificate'],
                   example=T('Coloured, stamped outer and inner artwork (editable PDF preferred) carrying the mandatory texts; the compendial monograph when applicable; an image of the original pack for imported / under-licence products.',
                             'تصميم ملون مختوم للعبوة الخارجية والداخلية (PDF قابل للتعديل) يحمل النصوص الإلزامية؛ المونوجراف الدستوري عند الانطباق؛ صورة العبوة الأصلية للمستورد / تحت الترخيص.'),
                   sections=[sec('outer', 'Outer pack mandatory texts', 'نصوص العبوة الخارجية الإلزامية', 'list', 'Trade name, strength, form, actives with quantities, pack size, route, storage, batch/expiry fields, registration number, manufacturer and licence holder, price field, warnings (Rx, keep out of reach of children), Arabic texts.',
                                 'الاسم التجاري، التركيز، الشكل، المواد الفعالة بكمياتها، حجم العبوة، طريقة الاستخدام، التخزين، خانات التشغيلة والصلاحية، رقم التسجيل، المصنّع ومالك الترخيص، خانة السعر، التحذيرات، النصوص العربية.'),
                             sec('inner', 'Inner / blister texts', 'نصوص العبوة الداخلية / الشريط', 'list'),
                             sec('check', 'Check against Annex I data', 'مطابقة بيانات Annex I', 'table', columns=['Text on artwork', 'Annex I / licence value', 'Match'], source='product')])
L['M1-15'] = entry('M1-15', 'letter', 'full', letterhead=True, inputs=['registration_licence'], example=EXAMPLE_LETTER,
                   sections=LETTER_HEAD + [sec('countries', 'Countries where registered and marketed', 'الدول المسجَّل والمسوَّق فيها', 'table', 'Country, status (registered / marketed / under registration), authority, registration number and date.',
                                               'الدولة، الحالة (مسجَّل / مسوَّق / تحت التسجيل)، الجهة، رقم التسجيل وتاريخه.', columns=['Country', 'Status', 'Authority', 'Registration no.', 'Date']), SIGN])
L['M1-24'] = entry('M1-24', 'contract', 'partial', inputs=['manufacturing_contract', 'toll_card', 'commercial_register'],
                   example=T('Original agreement (manufacturing / storage / packaging / agency) authenticated or legalised as the requirement states (bank, EDA legal affairs, chamber + embassy for imported).',
                             'العقد الأصلي (تصنيع / تخزين / تعبئة / توكيل) موثَّق أو مصدَّق كما ينص المتطلب (بنك، الشؤون القانونية بالهيئة، الغرفة + السفارة للمستورد).'),
                   sections=[sec('parties', 'Parties', 'الأطراف', 'table', columns=['Party', 'Role', 'Address', 'Licence / register no.'], source='manufacturers'),
                             sec('scope', 'Scope and products', 'النطاق والمستحضرات', 'para'),
                             sec('duties', 'Responsibilities (GMP, QC release, complaints, recalls, documentation, audits, changes)', 'المسؤوليات (GMP، الإفراج، الشكاوى، الاسترجاع، التوثيق، التفتيش، التغييرات)', 'list'),
                             sec('term', 'Term, termination, confidentiality, governing law', 'المدة والإنهاء والسرية والقانون', 'para'), SIGN],
                   note=T('An unsigned draft for negotiation only; the signed agreement must be authenticated again.', 'مسودة غير موقَّعة للتفاوض فقط؛ العقد الموقَّع لازم يتوثَّق من جديد.'))
L['M1-25'] = entry('M1-25', 'declaration', 'full', letterhead=True, lang='both', inputs=['registration_licence', 'toll_card'], example=EXAMPLE_LETTER,
                   sections=LETTER_HEAD + [sec('products', 'Registered and under-registration products owned by the toll company', 'منتجات شركة الـ toll المسجلة وتحت التسجيل', 'table', columns=['Trade name', 'Form / strength', 'Status', 'Registration no.', 'Manufacturing site']), SIGN])
for i in ('M1-26', 'M1-27'):
    L[i] = entry(i, 'declaration', 'partial', letterhead=True, inputs=['registration_licence', 'gmp_certificate', 'dmf_cep', 'api_coa'],
                 example=T('Licence-holder declaration naming every API manufacturer with the address exactly as in 3.2.S.2.1 and on its GMP certificate; signed by the licence holder; legalised when the holder is a different entity.',
                           'إقرار من مالك الترخيص يسمّي كل مصنّع مادة فعالة بعنوانه كما في 3.2.S.2.1 وشهادة GMP؛ موقَّع من المالك؛ مصدَّق إذا كان المالك جهة مختلفة.'),
                 sections=LETTER_HEAD + [sec('statement', 'Declaration', 'نص الإقرار', 'para', 'We, the licence holder of X, declare that the active substance(s) are manufactured by the following manufacturer(s) …',
                                              'نقر نحن مالك ترخيص المستحضر X بأن المادة (المواد) الفعالة تُصنَّع لدى المصنّع (المصنّعين) الآتي بيانهم …'),
                                          sec('apis', 'Active substances and their manufacturers', 'المواد الفعالة ومصنّعوها', 'table', columns=['Active substance', 'Manufacturer', 'Address', 'Country', 'Route (CEP / DMF / full)'], source='apis'), SIGN],
                 note=T('Signature by the licence holder and legalisation are outside the program.', 'توقيع مالك الترخيص والتصديق خارج البرنامج.'))
L['M1-27b'] = entry('M1-27b', 'declaration', 'partial', letterhead=True, inputs=['registration_licence', 'manufacturing_contract'], example=EXAMPLE_LETTER,
                    sections=LETTER_HEAD + [sec('statement', 'Declaration of the form of bulk', 'إقرار شكل الـ bulk', 'para', 'Form in which the bulk is imported (e.g. uncoated tablets in bulk, powder for filling), its packaging and the local operations performed.',
                                                 'الشكل الذي يُستورد به الـ bulk (مثلًا أقراص غير مغلفة، مسحوق للتعبئة)، عبوته، والعمليات المحلية التي تُجرى عليه.'), PRODUCT_ID, SIGN])
L['M1-31'] = entry('M1-31', 'certificate', 'generator', generator='composition', letterhead=True, inputs=['api_coa', 'analysis_conformity'],
                   example=T('Composition certificate on letterhead: unit formula with every component, quantity per unit, function and standard; actives as salt / hydrate as on the supplier CoA; overage, core and coat, capsule shell; signed and stamped.',
                             'شهادة تركيب على ورق الشركة: التركيبة لكل مكوّن بكميته ووظيفته ومواصفته؛ المواد الفعالة كملح/هيدرات كما في شهادة المورّد؛ الزيادة، اللب والغلاف، غلاف الكبسولة؛ موقَّعة ومختومة.'))
L['M1-32'] = entry('M1-32', 'calculation', 'generator', generator='salt', letterhead=True, inputs=['api_coa'], example=EXAMPLE_LETTER)
L['M1-36'] = entry('M1-36', 'table', 'full', letterhead=True, inputs=['specification', 'api_coa'],
                   example=T('Specification tables for every active (pharmacopoeial edition stated) and in-house specifications of every inactive, on company letterhead, signed and stamped.',
                             'جداول مواصفات كل مادة فعالة (مع ذكر طبعة الدستور) ومواصفات داخلية لكل سواغ، على ورق الشركة، موقَّعة ومختومة.'),
                   sections=[PRODUCT_ID, sec('actives', 'Specifications of the active substances', 'مواصفات المواد الفعالة', 'table', columns=['Substance', 'Test', 'Limit', 'Method', 'Reference (edition / chapter)'], source='specs'),
                             sec('inactives', 'In-house specifications of the inactive ingredients', 'المواصفات الداخلية للسواغات', 'table', columns=['Ingredient', 'Grade / standard', 'Test', 'Limit', 'Method'], source='composition'), SIGN])
L['M1-40'] = entry('M1-40', 'commitment', 'generator', generator='cep_commitment', letterhead=True, inputs=['dmf_cep'], example=EXAMPLE_LETTER)
L['M1-43'] = entry('M1-43', 'letter', 'generator', generator='cover', letterhead=True, example=EXAMPLE_LETTER)
L['M1-44'] = entry('M1-44', 'table', 'generator', generator='tracking', example=T('Table with columns sequence, description, type, date for every sequence submitted.', 'جدول بأعمدة: التسلسل، الوصف، النوع، التاريخ لكل تسلسل مُقدَّم.'))
# third-party and EDA documents of Module 1: example from the acceptance text, nothing to draft
# ---------------- Module 2
L['M2-01'] = entry('M2-01', 'toc', 'full', inputs=[], example=T('Table of contents of Modules 2–5 generated from the dossier structure, plus a one-page introduction (product, form, strength, applicant, type of application).',
                                                                   'فهرس Modules 2–5 مُولَّد من هيكل الملف + مقدمة من صفحة (المستحضر، الشكل، التركيز، مقدم الطلب، نوع الطلب).'),
                   sections=[sec('intro', 'Introduction', 'المقدمة', 'para', 'Product, pharmaceutical form and strength, proposed indication in one line, applicant and manufacturer, type of application and legal basis, reference product.',
                                 'المستحضر، الشكل والتركيز، الاستخدام في سطر، مقدم الطلب والمصنّع، نوع الطلب وأساسه، المستحضر المرجعي.', source='product'),
                             sec('toc', 'Table of contents', 'الفهرس', 'table', columns=['Module / section', 'Title', 'Included (yes / N/A)'], source='board')])
L['M2-02'] = entry('M2-02', 'summary', 'partial', inputs=['specification', 'stability_data', 'api_coa', 'analysis_conformity'],
                   example=T('Quality Overall Summary following Module 3 section by section (2.3.S, 2.3.P, 2.3.A, 2.3.R) with cross-references; the WHO QOS-PD tables are the model; one QOS per ASMF with a dated front page.',
                             'ملخص الجودة الشامل متتبعًا Module 3 قسمًا قسمًا (2.3.S، 2.3.P، 2.3.A، 2.3.R) مع الإحالات؛ جداول WHO QOS-PD هي النموذج؛ QOS واحد لكل ASMF بصفحة غلاف مؤرَّخة.'),
                   sections=[sec('front', 'Front page', 'صفحة الغلاف', 'fields', fields=[{'key': 'version', 'label': T('Version', 'الإصدار')}, {'key': 'date', 'label': T('Date', 'التاريخ')}], source='product'),
                             sec('s', '2.3.S Drug substance (per API: general information, manufacture, characterisation, control, reference standards, container, stability)', '2.3.S المادة الفعالة', 'list', source='apis'),
                             sec('p', '2.3.P Drug product (description and composition, development, manufacture, excipients, control, reference standards, container, stability)', '2.3.P المستحضر', 'list', source='composition'),
                             sec('tables', 'QOS-PD summary tables', 'جداول QOS-PD', 'table', columns=['Table', 'Content', 'Cross-reference to Module 3'], source='specs'),
                             sec('a_r', '2.3.A appendices and 2.3.R regional information', '2.3.A و2.3.R', 'para')],
                   note=T('The program builds the structure and the tables from the product data; the narrative is reviewed by the company.', 'البرنامج يبني الهيكل والجداول من بيانات المنتج؛ السرد تراجعه الشركة.'))
L['M2-03'] = entry('M2-03', 'summary', 'partial', inputs=['leaflet'],
                   example=T('Non-clinical overview (2.4) and clinical overview (2.5) with ICH M4S / M4E headings; one 2.7.3 summary per indication; for generics mostly literature-based with the BE study summarised in 2.7.1.',
                             'النظرة قبل السريرية (2.4) والسريرية (2.5) بعناوين ICH M4S / M4E؛ ملخص 2.7.3 لكل استخدام؛ للجنيسة تعتمد على الأدبيات مع تلخيص دراسة التكافؤ في 2.7.1.'),
                   sections=[sec('nc', '2.4 Non-clinical overview', '2.4 النظرة قبل السريرية', 'list', 'Overview of the non-clinical testing strategy, pharmacology, pharmacokinetics, toxicology, integrated overview and conclusions; literature references.', 'استراتيجية الاختبار قبل السريري، الفارماكولوجي، الحرائك، السمّية، النظرة المتكاملة والخلاصة؛ المراجع.'),
                             sec('c', '2.5 Clinical overview', '2.5 النظرة السريرية', 'list', 'Product development rationale, biopharmaceutics, clinical pharmacology, efficacy, safety, benefit–risk conclusions, literature references.', 'منطق التطوير، البيوصيدلانيات، الفارماكولوجي السريري، الفعالية، السلامة، خلاصة الفائدة–الخطر، المراجع.'),
                             sec('s7', '2.7 Clinical summary (2.7.1 biopharmaceutics incl. BE; 2.7.2; 2.7.3 per indication; 2.7.4 safety)', '2.7 الملخص السريري', 'list')])
# ---------------- Module 3 — S
S_NOTE = T('One document per API manufacturer; with a CEP or DMF the acceptance criteria change as the requirement says.', 'مستند لكل مصنّع مادة فعالة؛ مع CEP أو DMF تتغير معايير القبول كما في المتطلب.')
L['S-01'] = entry('S-01', 'section', 'full', inputs=['api_coa', 'dmf_cep'], note=S_NOTE,
                  sections=[sec('names', 'Nomenclature', 'التسمية', 'fields', source='apis', fields=[{'key': 'inn', 'label': T('INN', 'الاسم الدولي')}, {'key': 'compendial', 'label': T('Compendial name', 'الاسم الدستوري')}, {'key': 'chemical', 'label': T('Chemical name', 'الاسم الكيميائي')},
                                                                                                        {'key': 'iupac', 'label': T('IUPAC name', 'اسم IUPAC')}, {'key': 'code', 'label': T('Company or laboratory code', 'الكود')}, {'key': 'other', 'label': T('USAN / BAN / other names', 'أسماء أخرى')}, {'key': 'cas', 'label': T('CAS registry number', 'رقم CAS')}])])
L['S-02'] = entry('S-02', 'section', 'full', inputs=['api_coa', 'dmf_cep'], note=S_NOTE,
                  sections=[sec('structure', 'Structure', 'التركيب الكيميائي', 'fields', 'Structural formula with chiral centres shown; molecular formula; relative molecular mass including the hydrate / salt; stereochemistry.', 'الصيغة البنائية بمراكز الكيرالية؛ الصيغة الجزيئية؛ الكتلة الجزيئية النسبية شاملة الهيدرات / الملح؛ الكيمياء الفراغية.',
                                source='apis', fields=[{'key': 'formula', 'label': T('Molecular formula', 'الصيغة الجزيئية')}, {'key': 'mw', 'label': T('Relative molecular mass', 'الكتلة الجزيئية')}, {'key': 'stereo', 'label': T('Stereochemistry', 'الكيمياء الفراغية')}, {'key': 'image', 'label': T('Structure drawing (insert)', 'رسم التركيب (يُدرج)')}])])
L['S-03'] = entry('S-03', 'section', 'partial', inputs=['api_coa', 'dmf_cep'], note=S_NOTE,
                  sections=[sec('props', 'General properties', 'الخصائص العامة', 'table', 'Appearance; solubility at pH 1.2, 4.5 and 6.8 (37 °C) and in organic solvents; pKa, logP; particle size distribution and polymorphism for low-solubility APIs; hygroscopicity; melting point. With a CEP only properties not controlled by the CEP / monograph.',
                                'المظهر؛ الذوبانية عند pH 1.2 و4.5 و6.8 (37°م) وفي المذيبات العضوية؛ pKa وlogP؛ توزيع حجم الجسيمات وتعدد الأشكال البلورية لقليلة الذوبان؛ الاسترطاب؛ نقطة الانصهار. مع CEP فقط الخصائص غير المضبوطة بالـ CEP / المونوجراف.', columns=['Property', 'Value / result', 'Method', 'Source'])])
L['S-04'] = entry('S-04', 'section', 'full', inputs=['gmp_certificate', 'dmf_cep'], note=S_NOTE, sections=[MANUF_TABLE])
L['S-06'] = entry('S-06', 'section', 'partial', inputs=['api_coa', 'dmf_cep'], note=S_NOTE,
                  sections=[sec('techniques', 'Elucidation of structure', 'إثبات التركيب', 'table', 'All essential techniques with legible spectra referenced and an interpretation table; NMR enumerated and zoomed; with a CEP: polymorph and PSD studies.',
                                'كل التقنيات الأساسية مع الإشارة إلى الأطياف وجدول التفسير؛ NMR مرقَّم ومكبَّر؛ مع CEP دراسات الأشكال البلورية وحجم الجسيمات.', columns=['Technique (IR, UV, 1H/13C NMR, MS, elemental analysis, XRPD, DSC…)', 'Key observations', 'Interpretation', 'Spectrum ref.'])])
L['S-07'] = entry('S-07', 'section', 'partial', inputs=['api_coa', 'dmf_cep'], note=S_NOTE,
                  sections=[sec('organic', 'Organic impurities', 'الشوائب العضوية', 'table', 'Potential impurities from the route and degradation; compendial specified impurities; ICH Q3A limits; carry-over.', 'الشوائب المحتملة من المسار والتحلل؛ الشوائب الدستورية المحددة؛ حدود ICH Q3A؛ الانتقال.',
                                columns=['Impurity', 'Origin', 'Structure / name', 'Limit', 'Justification']),
                            sec('solvents', 'Residual solvents (incl. benzene risk)', 'المذيبات المتبقية', 'table', columns=['Solvent', 'ICH Q3C class', 'Limit', 'Result']),
                            sec('elemental', 'Elemental impurities risk assessment (ICH Q3D)', 'تقييم الشوائب العنصرية (Q3D)', 'para'),
                            sec('mutagenic', 'Mutagenic impurities (ICH M7) and nitrosamines risk assessment', 'الشوائب المطفرة (M7) والنيتروزامينات', 'para')])
L['S-08'] = entry('S-08', 'table', 'generator', generator='s41', inputs=['specification', 'api_coa', 'dmf_cep'], note=S_NOTE, sections=[SPEC_TABLE])
L['S-09'] = entry('S-09', 'section', 'partial', inputs=['specification'], note=S_NOTE, sections=METHODS)
L['S-10'] = entry('S-10', 'table', 'generator', generator='s44', inputs=['api_coa'], note=S_NOTE, sections=[BATCH_TABLE])
L['S-11'] = entry('S-11', 'section', 'full', inputs=['specification', 'api_coa'], note=S_NOTE, sections=JUSTIFICATION)
L['S-12'] = entry('S-12', 'section', 'partial', inputs=['api_coa'], note=S_NOTE, sections=[RS])
L['S-13'] = entry('S-13', 'section', 'partial', inputs=['dmf_cep'], note=S_NOTE, sections=CONTAINER)
L['S-14'] = entry('S-14', 'section', 'partial', inputs=['stability_data', 'dmf_cep'], note=S_NOTE, sections=STABILITY)
L['S-15'] = entry('S-15', 'statement', 'full', inputs=['dmf_cep'],
                  example=T('A statement at the start of 3.2.S naming, per API manufacturer, the option used (1 CEP, 2 DMF/ASMF, 3 full details, 4 compendial) and, for a DMF, the applicant\'s part front page with version and date.',
                            'بيان في أول 3.2.S يذكر لكل مصنّع مادة فعالة الخيار المتبع (1 CEP، 2 DMF/ASMF، 3 بيانات كاملة، 4 دستوري)، وللـ DMF صفحة غلاف الجزء المفتوح بإصداره وتاريخه.'),
                  sections=[sec('options', 'S-part option per API manufacturer', 'خيار تقديم المادة الفعالة لكل مصنّع', 'table', columns=['Active substance', 'Manufacturer', 'Option (1–4)', 'CEP / DMF number', 'Version / date'], source='apis')])
# ---------------- Module 3 — P
L['P-01'] = entry('P-01', 'section', 'full', inputs=['api_coa', 'analysis_conformity', 'registration_licence'],
                  sections=[sec('description', 'Description of the dosage form', 'وصف الشكل الصيدلي', 'para', 'Appearance, markings, pack presentation; potency note where the salt / hydrate is used.', 'المظهر، العلامات، العبوة؛ ملاحظة الفاعلية عند استخدام الملح / الهيدرات.', source='product'),
                            sec('composition', 'Composition (unit formula)', 'التركيب (تركيبة الوحدة)', 'table', 'Every component with quantity per unit, function, standard / grade; actives with the salt-equivalence note; overage stated; shell / coating composition separately; identical to the CPP and approvals.',
                                'كل مكوّن بكميته للوحدة ووظيفته ومواصفته؛ المواد الفعالة مع معادلة الملح؛ الزيادة؛ تركيب الغلاف / الكبسولة منفصلًا؛ مطابق للـ CPP والموافقات.', columns=['Component', 'Function', 'Standard / grade', 'Quantity per unit', '%'], source='composition'),
                            sec('removed', 'Components removed during manufacture', 'المكوّنات المزالة أثناء التصنيع', 'para')])
L['P-02'] = entry('P-02', 'section', 'partial', inputs=['leaflet', 'specification', 'stability_data'],
                  sections=[sec('ref', 'Reference product and QTPP', 'المستحضر المرجعي والـ QTPP', 'table', columns=['Attribute', 'Target', 'Justification'], source='product'),
                            sec('components', 'Components of the drug product (API–excipient compatibility, excipient choice)', 'مكوّنات المستحضر (التوافق، اختيار السواغات)', 'para'),
                            sec('formulation', 'Formulation development (comparison with the reference, overages justified step by step, CQAs)', 'تطوير التركيبة (المقارنة بالمرجع، تبرير الزيادات، الـ CQAs)', 'table', columns=['Trial / batch', 'Composition change', 'Result', 'Conclusion']),
                            sec('process', 'Manufacturing process development (CPPs, scale-up)', 'تطوير عملية التصنيع', 'para'),
                            sec('dissolution', 'Comparative dissolution in three BCS media (pH 1.2, 4.5, 6.8), multipoint, f2', 'الانحلال المقارن في ثلاثة أوساط', 'table', columns=['Medium', 'Time point', 'Test %', 'Reference %', 'f2']),
                            sec('container', 'Container closure, microbiological attributes, compatibility with diluent / device', 'العبوة، الخواص الميكروبيولوجية، التوافق مع المذيب / الجهاز', 'para')])
L['P-03'] = entry('P-03', 'section', 'full', inputs=['gmp_certificate', 'registration_licence'], sections=[MANUF_TABLE])
L['P-04'] = entry('P-04', 'section', 'full', inputs=['analysis_conformity'],
                  sections=[sec('batch_formula', 'Batch formula per commercial batch size', 'تركيبة التشغيلة لكل حجم تجاري', 'table', 'Every commercial batch size; overage / overfill; potency calculation of the API.', 'كل حجم تشغيلة تجاري؛ الزيادة؛ حساب فاعلية المادة الفعالة.', columns=['Component', 'Quantity per unit', 'Quantity per batch', 'Batch size', 'Overage'], source='composition')])
L['P-05'] = entry('P-05', 'section', 'partial', inputs=['analysis_conformity'],
                  sections=[sec('flow', 'Flow diagram', 'مخطط سير العملية', 'para', 'All steps with CPPs and IPCs marked (insert the diagram).', 'كل الخطوات مع علامات CPP وIPC (يُدرج المخطط).'),
                            sec('steps', 'Process narrative', 'سرد خطوات التصنيع', 'table', columns=['Step', 'Equipment (type, capacity, make)', 'Parameters (target and range)', 'IPC', 'Hold time'], source='batches'),
                            sec('packaging', 'Packaging operations and transfer precautions', 'التعبئة واحتياطات النقل', 'para'),
                            sec('hold', 'Hold times with supporting stability', 'أزمنة الانتظار ودعمها بالثبات', 'para')])
L['P-06'] = entry('P-06', 'section', 'partial', inputs=['analysis_conformity'],
                  sections=[sec('ipc', 'Critical steps and in-process controls', 'الخطوات الحرجة والضوابط أثناء التصنيع', 'table', 'CPPs discussed; every IPC with test, limit and justification.', 'مناقشة الـ CPPs؛ كل IPC باختباره وحدّه وتبريره.', columns=['Step', 'Parameter / IPC test', 'Limit', 'Justification'])])
L['P-07'] = entry('P-07', 'section', 'partial', inputs=['analysis_conformity'],
                  sections=[sec('validation', 'Process validation (protocol / report)', 'التحقق من العملية', 'table', 'Three batches (if applicable) for every batch size, or the protocol; each API source in at least one batch.', 'ثلاث تشغيلات (عند الانطباق) لكل حجم، أو البروتوكول؛ كل مصدر مادة فعالة في تشغيلة على الأقل.',
                                columns=['Batch no.', 'Size', 'API source', 'Critical parameters checked', 'Acceptance criteria', 'Result'], source='batches')])
L['P-08'] = entry('P-08', 'section', 'partial', inputs=['specification'],
                  sections=[sec('excipients', 'Specifications of excipients', 'مواصفات السواغات', 'table', columns=['Excipient', 'Standard (Ph. Eur. / USP / in-house)', 'Grade', 'Function', 'Supplier'], source='composition'),
                            sec('origin', 'Excipients of human or animal origin (TSE / BSE certificates)', 'السواغات ذات الأصل البشري أو الحيواني', 'para'),
                            sec('novel', 'Novel excipients', 'السواغات الجديدة', 'para', 'State «none» when none.', 'يُذكر «لا يوجد» عند عدم وجودها.')])
L['P-09'] = entry('P-09', 'table', 'generator', generator='p51', inputs=['specification', 'analysis_conformity'], sections=[SPEC_TABLE])
L['P-10'] = entry('P-10', 'section', 'partial', inputs=['specification'], sections=METHODS)
L['P-11'] = entry('P-11', 'table', 'generator', generator='p54', inputs=['analysis_conformity'], sections=[BATCH_TABLE])
L['P-12'] = entry('P-12', 'section', 'partial', inputs=['specification', 'stability_data'],
                  sections=[sec('degradation', 'Degradation products and synthetic impurities', 'نواتج التحلل والشوائب التصنيعية', 'table', columns=['Impurity', 'Source (degradation / synthesis)', 'Structure', 'Limit', 'Justification']),
                            sec('elemental', 'Elemental impurities risk assessment (ICH Q3D)', 'تقييم الشوائب العنصرية', 'para'), sec('nitrosamines', 'Nitrosamines risk assessment', 'تقييم النيتروزامينات', 'para')])
L['P-13'] = entry('P-13', 'section', 'full', inputs=['specification', 'analysis_conformity'], sections=JUSTIFICATION)
L['P-14'] = entry('P-14', 'section', 'partial', inputs=['api_coa'], sections=[RS])
L['P-15'] = entry('P-15', 'section', 'partial', inputs=['stability_data'], sections=CONTAINER)
L['P-16'] = entry('P-16', 'section', 'partial', generator='stability_commitment', inputs=['stability_data', 'stability_approval'], sections=STABILITY)
# ---------------- Module 3 — A / R
L['A-01'] = entry('A-01', 'statement', 'full', sections=[sec('statement', 'Facilities and equipment', 'المنشآت والمعدات', 'para', 'Per the Quality Module guideline v2: «Not applicable» for these files, stated with the reason.', 'حسب دليل الجودة v2: «لا ينطبق» لهذه الملفات مع ذكر السبب.', source='product')])
L['A-02'] = entry('A-02', 'section', 'partial', sections=[sec('ra', 'Adventitious agents risk assessment', 'تقييم مخاطر العوامل العارضة', 'para'), sec('certs', 'Certificates (TSE / BSE, viral safety)', 'الشهادات', 'table', columns=['Material', 'Origin', 'Supplier', 'Certificate', 'Validity'])])
L['A-03'] = entry('A-03', 'section', 'partial', sections=[sec('novel', 'Novel excipient data (manufacture, characterisation, control, safety)', 'بيانات السواغ الجديد', 'list')])
L['R-02'] = entry('R-02', 'record', 'partial', inputs=['analysis_conformity'],
                  example=T('The company\'s controlled master production document per strength, batch size and site: master formula, dispensing / processing / packaging instructions, calculations, equipment, parameters, IPCs, sampling plan, hold times, yields.',
                            'سجل التشغيل الرئيسي المعتمد للشركة لكل تركيز وحجم وموقع: التركيبة، تعليمات الصرف / التصنيع / التعبئة، الحسابات، المعدات، البارامترات، الـ IPCs، خطة أخذ العينات، أزمنة الانتظار، العوائد.'),
                  sections=[sec('formula', 'Master formula', 'التركيبة الرئيسية', 'table', columns=['Component', 'Quantity per batch', 'Standard'], source='composition'),
                            sec('instructions', 'Dispensing, processing and packaging instructions', 'تعليمات الصرف والتصنيع والتعبئة', 'list'),
                            sec('equipment', 'Equipment (type, capacity, make / model) and parameters (target and range)', 'المعدات والبارامترات', 'table', columns=['Step', 'Equipment', 'Capacity', 'Parameter', 'Target', 'Range']),
                            sec('ipc', 'IPCs, sampling plan, hold times, precautions', 'الـ IPCs وخطة العينات وأزمنة الانتظار', 'table', columns=['Step', 'Test', 'Limit', 'Sampling', 'Hold time']),
                            sec('yield', 'Theoretical and actual yield', 'العائد النظري والفعلي', 'para')],
                  note=T('A blank template from the process data; the approved master record stays the company\'s controlled document.', 'قالب فارغ من بيانات العملية؛ السجل المعتمد يظل مستند الشركة المضبوط.'))
L['R-03'] = entry('R-03', 'table', 'full', inputs=['specification'],
                  sections=[sec('methods', 'Analytical method summary (WHO template)', 'ملخص الطرق التحليلية', 'table', columns=['Method', 'Technique', 'Column / conditions', 'Standard & sample prep', 'SST', 'Calculation']),
                            sec('validation', 'Validation summary', 'ملخص التحقق', 'table', columns=['Method', 'Parameter', 'Acceptance criterion', 'Result', 'Report ref.'])])
# ---------------- Module 5
L['M5-01'] = entry('M5-01', 'toc', 'full', sections=[sec('toc', 'Table of contents of Module 5', 'فهرس Module 5', 'table', columns=['Section (5.2, 5.3.x, 5.4)', 'Title', 'Study / file', 'Node extension'], source='board')])
L['M5-02'] = entry('M5-02', 'table', 'full', sections=[STUDY_LIST])

# ---------------- everything else: from the requirement itself (what an acceptable document shows), nothing to draft
for r in REQS:
    if r['id'] in L:
        continue
    cls = r['doc_class']
    kind = {'third_party_certificate': 'third_party', 'eda_document': 'eda', 'executed_record': 'record'}.get(cls, 'report')
    acc = r.get('acceptance_text') or ''
    needs = (r.get('rebuild') or {}).get('needs') or ''
    ex_en = (acc + ('. ' if acc and not acc.endswith('.') else ' ') + ('Obtained from: ' + needs if needs else '')).strip()
    L[r['id']] = entry(r['id'], kind, 'none', example=T(ex_en, ''), note=T('Uploaded, never re-typed; the program checks it and can open a re-issue request to the issuer.',
                                                                              'يُرفع كما صدر ولا يُعاد كتابته؛ البرنامج يفحصه ويقدر يفتح طلب إعادة إصدار للجهة.'))

lib = [L[r['id']] for r in REQS]
out = ROOT / 'rulepacks/eda.ctd.nta065.v5/templates/library.yaml'
head = ('# Template library — what every requirement\'s document looks like and whether the program can draft it.\n'
        '# draft: full (the program drafts it from the base documents and the product data) · partial (the program builds the\n'
        '# structure and the tables, the company adds the science) · generator (an existing generator makes it) · none (issued by a\n'
        '# third party or EDA: uploaded as issued). Section kinds: para, list, table (columns), fields. `source` names the product data\n'
        '# the program fills itself. Generated by tools/build_template_library (owner decision 08/11/2026: «قدام كل نقطة فورمة المستند\n'
        '# أو مثال ليه، وأوبشن إن البرنامج يعمله من المستندات المرفقة الأساسية»).\n')
out.write_text(head + yaml.safe_dump(lib, allow_unicode=True, sort_keys=False, width=160), encoding='utf-8')
import collections
print(len(lib), 'entries', collections.Counter(e['draft'] for e in lib))
