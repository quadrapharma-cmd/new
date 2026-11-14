// The made-up dossier of the preparation tests («الفحص الأول للملف»): its documents' pages as the program reads them. It holds the
// same five problems a real dossier showed — a manufacturer changed with only fee receipts, an approved limit missing from the
// specification, one substance in two forms, a review date passed, a licence's conditions. Every name and number is made up.
export const page = (n, text, by = 'text') => ({ n, text, by });

export const LICENCE = { id: 'd1', name: 'licence.pdf', pages: [
  page(1, `Arab Republic of Egypt
Egyptian Drug Authority
Final Registration Licence for Pharmaceutical Products
Registration No.: 98765/2024
Trade Name: Testamin powder for oral solution
Dosage Form: Powder for oral solution
License Holder: Nile Test Pharma
Manufacturer: Delta Test Manufacturing
Each sachet contains:
Citric Acid Monohydrate 11.000 g
Ascorbic Acid 2.500 g
Light Magnesium Oxide 3.500 g
Issue Date: 12/03/2024`, 'ocr'),
  page(2, `Conditions:
1. The company shall submit the stability study of three production batches.
2. The company shall submit the bioequivalence commitment before marketing.
3. The approved leaflet shall be printed in Arabic and English.`, 'ocr'),
] };
export const SPEC = { id: 'd2', name: 'specification.doc', pages: [page(1, `SINAI TEST INDUSTRIES
Finished Product Specification
Product Name: Testamin powder for oral solution
Document Code: QC-FPS-042
Issue Date: 01/02/2023
Review Date: 01/02/2025
Composition: each sachet contains
Citric Acid Anhydrous 10.06 g
Ascorbic Acid 2.500 g
Light Magnesium Oxide 3.500 g
Test | Acceptance criteria
Description | White to off-white powder
Assay of citric acid | 95.0 – 105.0 %
Assay of ascorbic acid | 90.0 – 110.0 %
Assay of magnesium oxide | 95.0 – 105.0 %`)] };
// a scanned letter, read by the program: «الموافقة على» comes out without its hamza and with ه for ة
export const STABILITY = { id: 'd3', name: 'stability approval.pdf', pages: [page(1, `Egyptian Drug Authority
Central Administration of Pharmaceutical Products
Stability Committee — Decision Letter
Outgoing No.: 3021
Date: 10/09/2025
Product: Testamin powder for oral solution
Applicant: Nile Test Pharma
Manufacturer: Sinai Test Industries
The committee reviewed the stability study of three batches.
القرار: الموافقه علي طلب الشركه
Limit of ascorbic acid to be 40 – 110 % until the end of shelf life.
Shelf life: 24 months, store below 30°C.`, 'ocr')] };
export const RECEIPTS = { id: 'd4', name: 'receipts.pdf', pages: [
  page(1, `هيئة الدواء المصرية
إيصال سداد رسوم
رقم الإيصال: ٥٥٦٦٧٧
اسم الشركة: شركة النيل التجريبية
البيان: رسوم نقل تصنيع إلى Sinai Test Industries
المبلغ: ١٥٠٠٠ جنيه
التاريخ: ٠٥/٠٦/٢٠٢٣`, 'ocr'),
  page(2, `هيئة الدواء المصرية
إيصال سداد رسوم
البيان: رسوم نقل تصنيع إلى Sinai Test Industries — دمغة`, 'ocr'),
] };
export const COA = { id: 'd5', name: 'coa.doc', pages: [page(1, `SINAI TEST INDUSTRIES
Certificate of Analysis
Product: Testamin powder for oral solution
Batch No.: TT-25001
Finished Product Specification No.: QC-FPS-042
Manufacturing Date: 03/2025
Expiry Date: 02/2027
Assay of citric acid: 99.8 %`)] };
export const BLANK = { id: 'd6', name: 'unreadable scan.pdf', pages: [page(1, '', 'ocr'), page(2, '', 'ocr')] };
export const DOSSIER = [LICENCE, SPEC, STABILITY, RECEIPTS, COA, BLANK];

