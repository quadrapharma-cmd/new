# مراجعة مسودة NP.CAPP.065 الإصدار 6 (2026) مقابل الإصدار 5 اللي شغالين بيه

بند المعرفة 30 في `UPDATES.md`. المصدر: `docs/ctd/sources/EDA_NP.CAPP.065_v6_DRAFT_2026_CTD-submission-guidance.pdf` قصاد `EDA_NP.CAPP.065_v5_2025_CTD-submission-guidance.pdf` وباقة القواعد `rulepacks/eda.ctd.nta065.v5`. المقارنة اتعملت بالبرنامج (جدول «CTD Format» في المسودة سطر سطر، ومطابقته ببنودنا برقم الـ eCTD لموديول 1 وبرقم الـ CTD لموديول 2–5)، وكل سطر هنا اتراجع على نص المسودة.

## الخلاصة

1. **موديول 1 اتعاد ترقيمه بترقيم الـ eCTD المصري** (1.0، 1.2.1، 1.2.2.x، 1.2.3.x…) بدل ترقيم 1.1.x بتاع الإصدار 5. بنودنا شايلة أرقام الـ eCTD دي أصلًا، فالمطابقة مباشرة.
2. **17 بند جديد في موديول 1** مش موجود في الإصدار 5 (الجدول تحت): اتفاقيات تانية، وإنهاء/تنازل، وإقرارات (تعديل طريقة تصنيع المادة الفعالة، ومورّد المادة الفعالة، وإضافة موقع، وكل التغييرات)، وقايمة الشركات التابعة، وطلب تغيير RRA، ودليل المرادفات، وقسم 1.2.10 للتغييرات بعد التسجيل، و1.3.5 النشرة المعتمدة في الدول الأعضاء.
3. **16 بند مستواه اتغيّر** (مطلوب / مش مطلوب / اختياري) — أهمها للأدوية المستوردة: رخصة تسجيل المذيب، وأحدث دستور أدوية، وتقرير التقييم الكامل، وإقرارات صاحب الترخيص.
4. **موديول 2 اتفصّل بند بند** (2.3.S.1…7، 2.3.P.1…8، 2.5.x، 2.6.x…) مطلوب للمبتكر (I) ومش مطلوب للمثيل (G) — نفس اللي عندنا للمثيل.
5. **الأهم للأولوية ١: المسودة 6 مفيهاش شروط خالص** — مفيش «legalized» ولا «signed and stamped» ولا الترجمة ولا الـ PDF القابل للبحث (الإصدار 5 فيه 12 مرة legalized و12 stamp و9 translation). الشروط دي اتنقلت لمسودة **إرشادات تقديم موديول 1 المصرية 2026** (`EDA_EG-Human-Pharma-Module1-Submission-Guidance_DRAFT_2026.pdf`، 68 صفحة: legalized 22 مرة، valid 66، stamp 18)، وفيها شروط بالتفصيل لكل مستند (مثلًا: «التصديق من الغرفة التجارية والسفارة المصرية»، أو «توثيق البنك والإدارة القانونية في الهيئة»).

**المطلوب لما الإصدار 6 يبقى نهائي:** باقة قواعد جديدة `eda.ctd.nta065.v6` بالترقيم الجديد والمستويات الجديدة، وشروط الأولوية ١ (`conditions.py`) تتنقل مصادرها من ملاحظات الـ 065 v5 لإرشادات موديول 1 — ومش قبل كده: المسودتين لسه مسودات، والبرنامج شغال بالإصدار 5 اللي ساري.

## بنود جديدة في موديول 1 (مش في الإصدار 5)

| رقم v6 | البند | I / G مستورد / G محلي |
|---|---|---|
| 1.2.2.13 | Other Agreements | R / R / R |
| 1.2.2.14 | Termination / Waiver | R / R / R |
| 1.2.3.1 | Registration Request Approval | R / R / R |
| 1.2.3.6 | Non-Reference Approval | R / R / R |
| 1.2.4.3 | Declaration letter from the license holder specifying approved pack in Egypt | R / R / R |
| 1.2.4.5 | Declaration Letter from the Manufacturer of the active substance to inform the applicant in case of modification of the manufacturing Process or Specifications | R / R / R |
| 1.2.4.6 | Declaration Letter from API Supplier | R / R / R |
| 1.2.4.7 | Declaration Letter for Site Addition | R / R / R |
| 1.2.4.8 | Declaration Letter Form LH stating all Variations & Justification for the Change | R / R / R |
| 1.2.6.2 | List of Affiliates / Subsidiaries | R / R / R |
| 1.2.7.3 | RRA Variation Application with Annexes | R / R / R |
| 1.2.8.7 | Synonyms Evidence | R / R / R |
| 1.2.10.1 | PAC Approval from the COO (Imported Products) | R / R / R |
| 1.2.10.2 | Summary of Change for Variation | R / R / R |
| 1.2.10.3 | Justification of the proposed Post Approval Change | R / R / R |
| 1.2.10.4 | Any additional Documents relevant to Variations | R / R / R |
| 1.3.5 | Product Information already approved in the member states | R / R / R |

## بنود مستواها اتغيّر

| رقم v6 | البند في v6 | المستوى في v6 | بندنا | رقمه في v5 | المستوى في v5 |
|---|---|---|---|---|---|
| 1.2.3.10 | Inspection Report | R / R / R | M1-12 | 1.1.11 | cond. / cond. / R |
| 1.2.3.20 | Registration License for the Solvent | R / R / R | M1-28 | 1.1.18 | NR / NR / R |
| 1.2.4.2 | Declaration Letter from the License Holder specifying the API Manufacturers | R / R / R | M1-26 | 1.1.17.9 | NR / NR / R |
| 1.2.4.2 | Declaration Letter from the License Holder specifying the API Manufacturers | R / R / R | M1-27 | 1.1.17.10 | O / O / O |
| 1.2.4.10 | List of the Countries where the Product is registered & marketed | R / R / R | M1-15 | 1.1.14 | R / R / NR |
| 1.2.5.4 | The latest recent Pharmacopeia | R / R / R | M1-29 | 1.1.19 | NR / NR / R |
| 1.2.7.2 | Unredacted Assessment Report | R / R / NR | M1-17 | 1.1.16 | O / O / NR |
| 5.2 | Tabular Listing of All Clinical Studies | R / R / R | M5-02 | 5.2 | R / cond. / cond. |
| 5.3.1.1 | Bioavailability (BA) Study Reports | R / O / O | M5-03 | 5.3.1.1 | R / cond. / cond. |
| 5.3.1.2 | Comparative BA & BE Study Reports | R / R / R | M5-04 | 5.3.1.2 | R / cond. / cond. |
| 5.3.1.3 | In vitro/In vivo Correlation (IV/IVC) study reports | R / O / O | M5-05 | 5.3.1.3 | R / cond. / cond. |
| 5.3.1.4 | Reports of Bioanalytical and Analytical Methods for Human Studies | R / R / R | M5-06 | 5.3.1.4 | R / cond. / cond. |
| 5.3.2.2 | Reports of Hepatic Metabolism and Drug Interaction Studies | R / NR / NR | M5-07 | 5.3.2.1–2 | R / cond. / cond. |
| 5.3.3.1 | Healthy Subject PK and Initial Tolerability study report | R / NR / NR | M5-08 | 5.3.3.1 | R / cond. / cond. |
| 5.3.5.4 | Other Study Reports | R / NR / NR | M5-09 | 5.3.5.4 | R / R / R |
| 5.3.7 | Case Report Forms and Individual Listings | R / O / O | M5-10 | 5.3.7 | R / cond. / cond. |

## أرقام الـ eCTD اللي معناها اتغيّر في v6 (تتراجع في خريطة البنود)

رقم الـ eCTD في بندنا (من ملف التعريف المصري المؤقت) بيشاور على حاجة تانية في جدول v6 — يعني ترتيب موديول 1 نفسه اتحرّك:

| رقم | في v6 | بندنا عليه | رقمه في v5 |
|---|---|---|---|
| 1.2.4.9 | Other declarations requested by Egyptian Drug Authority | M1-30 — Letter of Access (API master file) | 1.1.20 |
| 1.2.4.9 | Other declarations requested by Egyptian Drug Authority | M1-10 — Leaflet translation declaration (non-English leaflets) | 1.1.9 |

## بنود عندنا ملقيناش ليها سطر في جدول v6

| بندنا | رقمه في v5 | البند | رقم الـ eCTD عندنا |
|---|---|---|---|
| M1-39 | 1.2.4.3 | CEP incl. all annexes | 3.2.R |
| M1-40 | 1.2.4.3 | Written commitment: inform EDA if CEP revised/renewed/withdrawn | 3.2.R |

## موديول 2–5

155 سطر في v6 مالوش بند منفصل عندنا — كلهم تفصيل موديول 2 وموديول 4 للمبتكر (مستوى المثيل فيهم «NR» زي ما هو عندنا). القايمة الكاملة في `docs/ctd/np065-v6-diff.json`.

