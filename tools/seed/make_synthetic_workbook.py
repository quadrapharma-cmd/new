#!/usr/bin/env python3
"""Builds a small INVENTED workbook with the same 21-sheet layout and Arabic headers as the real accounting workbook.

    python3 tools/seed/make_synthetic_workbook.py OUT.xlsx

Every name, number and text here is made up (a fictional company, fictional people). The workbook is deterministic and
exercises the tricky shapes of the real file: a multi-line entry, placeholders and trade words as parties, spelling variants
of one party, '+' document strings, "افتراض N" / "بند N" / "قيد الاستفسار" text (and a contract-clause look-alike that is
NOT a cross reference), two fiscal years, an unused account, a closed account, an entry dated before incorporation, an
identical duplicate entry, an entry with two dates, gaps in entry numbers, and depreciation lines in the accountant's own
words so that the asset register can be inferred. Sheets 3-6 hold the VALUES a spreadsheet would have computed.
"""
import os
import sys
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import openpyxl

TITLES = ['٠. دليل التشغيل', '١. دليل الحسابات', '٢. دفتر اليومية', '٣. الأستاذ العام', '٤. ميزان المراجعة',
          '٥. قائمة الدخل', '٦. المركز المالي', '٧. الأصول والإهلاك', '٨. مستحقو عقد التسوية', '٩. أرصدة الشركاء',
          '١٠. البنود المفتوحة', '١١. حالة الإقفال والتحفظات', '١٢. الالتزامات المحتملة', '١٣. الافتراضات المعلقة',
          '١٤. تمويل أحد الممولين', '١٥. المصروفات القانونية', '١٦. ضريبة المرتبات والضمان', '١٧. مطابقة مع المحاسب',
          '١٨. تنسيب الأموال المضخوخة', '١٩. إثبات مبالغ الضخ', '٢٠. الضخ مقابل الصرف']

INCORPORATED = date(2019, 3, 1)
CHART = [
    ('الأصول', None, None),
    ('1110', 'أرض اختبار', 'أصول'), ('1120', 'مبانٍ ومنشآت', 'أصول'), ('1130', 'آلات ومعدات', 'أصول'),
    ('1150', 'أجهزة حاسب', 'أصول'), ('1170', 'تراخيص', 'أصول'), ('1180', 'مشروعات تحت التنفيذ', 'أصول'),
    ('1191', 'مجمع إهلاك المباني', 'مجمع إهلاك'), ('1192', 'مجمع إهلاك الآلات', 'مجمع إهلاك'),
    ('1194', 'مجمع إطفاء التراخيص', 'مجمع إهلاك'), ('1196', 'مجمع إهلاك أجهزة الحاسب', 'مجمع إهلاك'),
    ('1290', 'أرصدة مدينة أخرى', 'أصول'), ('1310', 'الخزينة', 'أصول'), ('1340', 'البنك — حساب جاري 7788', 'أصول'),
    ('الالتزامات', None, None),
    ('2110', 'الموردون', 'التزامات'), ('2160', 'ذمم دائنة متنوعة', 'التزامات'), ('2250', 'أقساط الضمان المستحقة', 'التزامات'),
    ('2310', 'ذمم الممول د/ زهرة المقدسي — تحت حساب رأس المال (تعهد غير موثق)', 'التزامات'),
    ('2311', 'ذمم الممول د/ زهرة المقدسي — استحقاقات', 'التزامات'),
    ('2322', 'جاري د/ زهرة المقدسي — مرتبات مستحقة', 'التزامات'),
    ('حقوق الملكية', None, None),
    ('3110', 'رأس المال المصدر', 'حقوق ملكية'), ('3120', 'رأس المال تحت الطلب', 'حقوق ملكية مدين'),
    ('3150', 'الأرباح (الخسائر) المرحلة', 'حقوق ملكية'),
    ('3211', 'حصة منير الحلبي — مقابل عقد التسوية', 'حقوق ملكية'),
    ('الإيرادات', None, None),
    ('4110', 'مبيعات محلية', 'إيرادات'), ('4130', 'مردودات المبيعات', 'إيرادات مدين'),
    ('التكاليف والمصروفات', None, None),
    ('5210', 'مرتبات وأجور', 'مصروفات'),
    ('5211', 'مكافآت — مغلق: لا توجد مكافآت بالشركة', 'مصروفات'),
    ('5230', 'أتعاب محاماة', 'مصروفات'), ('5250', 'صيانة وإصلاحات', 'مصروفات'),
    ('5290', 'إهلاك الأصول الثابتة', 'مصروفات'), ('5420', 'مصروفات ورسوم بنكية', 'مصروفات'),
    ('الحسابات الوسيطة', None, None),
    ('6110', 'حساب وسيط للمشروعات', 'وسيط'),
]
PL = {'إيرادات', 'إيرادات مدين', 'تكلفة مبيعات', 'مصروفات', 'مصروفات غير واجبة الخصم'}


def d(y, m, dd):
    return datetime(y, m, dd)


def half_up(x):
    return int(Decimal(x).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def money(c):
    return c / 100 if c % 100 else c // 100


def journal_rows():
    """(date, no, code, dr, cr, memo, doc, cc, party, sector); amounts in whole currency units or Decimal."""
    R = []
    cc, sec = 'عام', 'مشترك'

    def e(no, when, lines, doc, cc_=cc, sec_=sec):
        for ln in lines:
            code, dr, cr, memo, party = ln[:5]
            ccx = ln[5] if len(ln) > 5 else cc_
            when_ = ln[6] if len(ln) > 6 else when
            R.append((when_, no, code, dr, cr, memo, doc, ccx, party, sec_))

    day = d
    # entry 9 is typed first (before incorporation, physical order differs from number order)
    e(9, day(2019, 1, 15), [('1310', 50000, None, 'تمويل نقدي مبكر — افتراض 3', 'د/ زهرة المقدسي'),
                            ('2310', None, 50000, 'تمويل نقدي مبكر', 'د/ زهرة المقدسي')], 'إفادة الإدارة — تمويل مبكر')
    e(1, day(2019, 3, 1), [('1340', 100000, None, 'سداد 10% من رأس المال', 'المساهمون'),
                           ('3120', 900000, None, 'رأس المال تحت الطلب', 'المساهمون'),
                           ('3110', None, 1000000, 'رأس المال المصدر', 'المساهمون')], 'شهادة تأسيس + استمارة سجل')
    e(2, day(2019, 7, 2), [('1110', 5000, None, 'أرض — حق تخصيص', 'منير الحلبي'),
                           ('1120', 20000, None, 'مبانٍ', 'منير الحلبي'),
                           ('1130', 10000, None, 'آلات ومعدات', 'منير الحلبي'),
                           ('3211', None, 35000, 'حصة المساهم مقابل التسوية', 'منير الحلبي')],
      'عقد التسوية + قرار المناطق 2/7/2019')
    e(3, day(2019, 8, 10), [('1340', 30000, None, 'تحويل وارد — بند مفتوح 2', '—'),
                            ('2310', None, 30000, 'تحويل وارد — بند مفتوح 2', '—')],
      'كشف بنك الاختبار 7788 — شيك 501 + كشف حسابات الشركاء')
    e(4, day(2019, 9, 1), [('5250', 800, None, 'صيانة سباكة', 'سباك'), ('1310', None, 800, 'صرف نقدي', 'عام')],
      'دفتر الخزينة (بخط اليد)')
    e(5, day(2019, 9, 15), [('1290', 2000, None, 'دفعة لم يتحدد مستفيدها — قيد الاستفسار', 'غير محدد'),
                            ('1340', None, 2000, 'سحب بشيك', 'بنك الاختبار الوطني')], 'كشف بنك الاختبار 7788')
    e(6, day(2019, 10, 1), [('5210', 3000, None, 'استحقاق مرتب — افتراض 1', 'د/ زهرة المقدسي'),
                            ('2322', None, 3000, 'استحقاق مرتب', 'زهرة المقدسي (قيد الاستفسار)')], 'جدول المرتبات')
    e(7, day(2019, 12, 31), [('1150', 2000, None, 'كاميرات المراقبة', 'مورد'), ('2110', None, 2000, 'مستحق للمورد', 'مورد')],
      'فاتورة كاميرات')
    e(8, day(2019, 12, 31), [('5290', 450, None, 'إهلاك الفترة من 2/7/2019 حتى 31/12/2019 — ستة أشهر', ''),
                             ('1192', None, 250, 'مجمع إهلاك آلات', ''), ('1191', None, 200, 'مجمع إهلاك مبانٍ', '')],
      'جدول الأصول والإهلاك')
    e(10, day(2020, 1, 20), [('1340', 8000, None, 'تحصيل مبيعات', 'عملاء'), ('4110', None, 8000, 'مبيعات', 'عملاء')],
      'كشف بنك الاختبار 7788 — 2020')
    e(11, day(2020, 2, 2), [('1340', 20000, None, 'تمويل وارد', 'د/ زهرة المقدسي'),
                            ('2310', None, 20000, 'تمويل وارد', 'د/ زهرة المقدسي')], 'كشف بنك الاختبار 7788 — شيك 503')
    for no in (12, 13):                                            # identical duplicate pair
        e(no, day(2020, 3, 4), [('5420', 150, None, 'رسوم بنكية', 'الاختبار الوطني'),
                                ('1340', None, 150, 'رسوم بنكية', 'الاختبار الوطني')], 'كشف بنك الاختبار 7788')
    e(14, day(2020, 3, 7), [('1150', 1200, None, 'جهاز بصمة', 'سامية الراوي'), ('1340', None, 1200, 'شراء', 'سامية الراوي')],
      'فاتورة جهاز البصمة')
    e(15, day(2020, 6, 30), [('1150', 5000, None, 'طابعة', 'سامية علي الراوي'), ('1340', None, 5000, 'شراء', 'سامية علي الراوي')],
      'فاتورة الطابعة')
    e(16, day(2020, 12, 31), [('5210', 3000, None, 'مرتبات 2020 (البند 2-7 من العقد)', 'د/ زهرة المقدسي'),
                              ('2322', None, 2000, 'مرتب مستحق', 'د/ زهرة المقدسي'),
                              ('2160', None, 1000, 'تحويل بتاريخ آخر — افتراض 2 — بند 4', 'أ/ منير', cc, day(2020, 3, 4))],
      'جدول المرتبات')
    dep = [('5290', 900, None, 'إهلاك سنة 2020 كاملة — مكونات المصنع', ''), ('1192', None, 500, 'مجمع إهلاك آلات', ''),
           ('1191', None, 400, 'مجمع إهلاك مبانٍ', '')]
    dep += [('5290', 400, None, 'إهلاك كاميرات المراقبة المرسملة 31/12/2019 — 2,000 × 20%', ''),
            ('1196', None, 400, 'مجمع إهلاك أجهزة الحاسب — الكاميرات', '')]
    d_dc = half_up(Decimal(120000) * Decimal('0.2') * 300 / 365)          # 1,200 x 20% x 300/365 in cents
    dep += [('5290', Decimal(d_dc) / 100, None, 'إهلاك جهاز البصمة من 7/3/2020 — 1,200 × 20% × 300/365', ''),
            ('1196', None, Decimal(d_dc) / 100, 'مجمع إهلاك أجهزة الحاسب — البصمة', '')]
    dep += [('5290', 500, None, 'إهلاك طابعة — 5,000 × 20% × نصف سنة', ''),
            ('1196', None, 500, 'مجمع إهلاك أجهزة الحاسب — الطابعة', '')]
    e(17, day(2020, 12, 31), dep, 'جدول الأصول والإهلاك')
    e(18, day(2020, 12, 31), [('1180', 10000, None, 'دفعة مشروع قيد التنفيذ', 'مصنع الفجر'),
                              ('1340', None, 10000, 'سداد', 'مصنع الفجر')], 'فاتورة مصنع الفجر', 'المصنع')
    e(19, day(2020, 11, 1), [('2110', 500, None, 'مرتجع آلة', 'مورد الأسمنت'), ('1130', None, 500, 'مرتجع آلة', 'مورد الأسمنت')],
      'إشعار مرتجع')
    e(20, day(2020, 12, 15), [('5420', 60, None, 'عمولة بنكية', 'بنك الاختبار الوطني'),
                              ('1340', None, 60, 'عمولة بنكية', 'بنك الاختبار الوطني')], 'كشف بنك الاختبار 7788', 'عام',
      'داخل ق.72')
    return R


def to_cents(x):
    return int((Decimal(str(x)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def replay(rows):
    """Plain-python ledger replay used only to write the cached statement sheets: {(year, acct): (dr_c, cr_c)}."""
    out = {}
    for when, no, code, dr, cr, *_ in rows:
        k = (when.year, code)
        a, b = out.get(k, (0, 0))
        out[k] = (a + (to_cents(dr) if dr else 0), b + (to_cents(cr) if cr else 0))
    return out


def build(path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = [wb.create_sheet(t) for t in TITLES]
    wb.properties.creator = 'synthetic'
    wb.properties.created = datetime(2026, 1, 1, 8, 0, 0)
    wb.properties.modified = datetime(2026, 1, 2, 9, 30, 0)
    cls_of = {c: k for c, n, k in CHART if n}
    name_of = {c: n for c, n, k in CHART if n}

    # 0 company
    s = ws[0]
    s['A1'] = 'شركة نور للتجارة (شركة الأمل للتجارة سابقاً)'
    s['A2'] = 'النظام المحاسبي — دفاتر الشركة'
    s['A4'], s['B4'] = 'الرقم الضريبي', '111-222-333'
    s['A5'], s['B5'] = 'سجل تجاري', '900100'
    s['A6'], s['B6'] = 'تاريخ التأسيس', '01/03/2019'
    s['A8'] = 'كيف تُستخدم هذه الدفاتر'
    for i, t in enumerate(['كل قيد يُدخل في ورقة اليومية في صف واحد لكل طرف.', 'أي قيد ينقصه مستند — لا يُرحَّل.'], start=1):
        s.cell(8 + i, 1, str(i))
        s.cell(8 + i, 2, t)

    # 1 chart
    s = ws[1]
    for c, h in enumerate(['الكود', 'اسم الحساب', 'التصنيف'], start=1):
        s.cell(1, c, h)
    for r, (a, b, c) in enumerate(CHART, start=2):
        s.cell(r, 1, a)
        if b:
            s.cell(r, 2, b)
            s.cell(r, 3, c)

    # 2 journal
    s = ws[2]
    heads = ['التاريخ', 'السنة', 'رقم القيد', 'كود الحساب', 'اسم الحساب', 'مدين', 'دائن', 'البيان', 'رقم المستند',
             'مركز التكلفة', 'الطرف', 'القطاع القانوني', 'حالة القيد']
    for c, h in enumerate(heads, start=1):
        s.cell(1, c, h)
    rows = journal_rows()
    for r, (when, no, code, dr, cr, memo, doc, ccx, party, sec) in enumerate(rows, start=2):
        s.cell(r, 1, when)
        s.cell(r, 2, when.year)
        s.cell(r, 3, no)
        s.cell(r, 4, code)
        s.cell(r, 5, name_of[code])
        if dr:
            s.cell(r, 6, float(dr) if isinstance(dr, Decimal) else dr)
        if cr:
            s.cell(r, 7, float(cr) if isinstance(cr, Decimal) else cr)
        s.cell(r, 8, memo)
        s.cell(r, 9, doc)
        s.cell(r, 10, ccx)
        if party:
            s.cell(r, 11, party)
        s.cell(r, 12, sec)
        s.cell(r, 13, 'سليم')
    last = len(rows) + 1
    s.cell(last + 3, 5, 'إجمالي اليومية')          # a total row without an account code (must be ignored)

    # 3-6 computed sheets (values)
    mov = replay(rows)
    years = sorted({y for y, _ in mov})
    codes = [c for c, n, k in CHART if n]
    ry = years[-1]
    cum_before = {c: [0, 0] for c in codes}
    for (y, c), (a, b) in mov.items():
        if y < ry:
            cum_before[c][0] += a
            cum_before[c][1] += b
    s = ws[3]
    s['A1'], s['B1'] = 'سنة التقرير', ry
    for c, h in enumerate(['الكود', 'اسم الحساب', 'التصنيف', 'رصيد أول المدة مدين', 'رصيد أول المدة دائن', 'حركة السنة مدين',
                           'حركة السنة دائن', 'الرصيد مدين', 'الرصيد دائن'], start=1):
        s.cell(3, c, h)
    tot = [0] * 6
    closing = {}
    for r, c in enumerate(codes, start=4):
        od, oc = cum_before[c]
        md, mc = mov.get((ry, c), (0, 0))
        net = od + md - oc - mc
        cd, cc_ = max(net, 0), max(-net, 0)
        closing[c] = net
        vals = [od, oc, md, mc, cd, cc_]
        for i, v in enumerate(vals):
            tot[i] += v
        s.cell(r, 1, c)
        s.cell(r, 2, name_of[c])
        s.cell(r, 3, cls_of[c])
        for i, v in enumerate(vals):
            s.cell(r, 4 + i, money(v))
    r = 4 + len(codes)
    s.cell(r, 2, 'الإجمالي')
    for i, v in enumerate(tot):
        s.cell(r, 4 + i, money(v))
    s.cell(r + 1, 2, 'اختبار التوازن')
    s.cell(r + 1, 8, 'متوازن' if tot[4] == tot[5] else 'غير متوازن')
    s = ws[4]
    s['A1'] = 'شركة نور للتجارة — ميزان المراجعة'
    s['A2'], s['C2'] = 'عن السنة المنتهية في 31 ديسمبر', ry
    for c, h in enumerate(['الكود', 'اسم الحساب', 'مدين', 'دائن'], start=1):
        s.cell(4, c, h)
    r = 5
    td = tcr = 0
    for c in codes:
        net = closing[c]
        if net == 0:
            continue
        s.cell(r, 1, c)
        s.cell(r, 2, name_of[c])
        s.cell(r, 3, money(max(net, 0)))
        s.cell(r, 4, money(max(-net, 0)))
        td += max(net, 0)
        tcr += max(-net, 0)
        r += 1
    s.cell(r, 2, 'الإجمالي')
    s.cell(r, 3, money(td))
    s.cell(r, 4, money(tcr))
    s.cell(r + 1, 2, 'اختبار التوازن')
    s.cell(r + 1, 3, 'متوازن')

    def ymov(cls_names):
        return sum(mov.get((ry, c), (0, 0))[1] - mov.get((ry, c), (0, 0))[0] for c in codes if cls_of[c] in cls_names)
    revenue = ymov({'إيرادات', 'إيرادات مدين'})
    cogs = -ymov({'تكلفة مبيعات'})
    opex = -ymov({'مصروفات'})
    nond = -ymov({'مصروفات غير واجبة الخصم'})
    s = ws[5]
    s['A1'] = 'شركة نور للتجارة'
    s['A2'], s['C2'] = 'قائمة الدخل عن السنة المنتهية في 31 ديسمبر', ry
    for r, (lab, v) in enumerate([('إيرادات النشاط', revenue), ('تكلفة المبيعات', cogs), ('مجمل الربح (الخسارة)', revenue - cogs),
                                  ('مرتبات ومكافآت وأتعاب ومصروفات عمومية', opex), ('مصروفات غير واجبة الخصم ضريبياً', nond),
                                  ('إجمالي المصروفات', opex + nond), ('صافي الربح (الخسارة) عن السنة', revenue - cogs - opex - nond)],
                                 start=4):
        s.cell(r, 1, lab)
        s.cell(r, 2, money(v))
    gross = sum(closing[c] for c in codes if cls_of[c] == 'أصول')
    accum = -sum(closing[c] for c in codes if cls_of[c] == 'مجمع إهلاك')
    liab = -sum(closing[c] for c in codes if cls_of[c] == 'التزامات')
    share = -sum(closing[c] for c in codes if c.startswith('32'))
    capital = -closing['3110']
    called = sum(closing[c] for c in codes if cls_of[c] == 'حقوق ملكية مدين')
    prior = -sum(sum(a - b for (yy, c), (a, b) in mov.items() if yy < ry and c == code) for code in codes if cls_of[code] in PL)
    cur = revenue - cogs - opex - nond
    equity = capital - called + share + prior + cur
    s = ws[6]
    s['A1'] = 'شركة نور للتجارة'
    s['A2'], s['C2'] = 'قائمة المركز المالي في 31 ديسمبر', ry
    items6 = [('الأصول بالتكلفة', gross), ('يخصم: مجمع الإهلاك والإطفاء', accum), ('إجمالي الأصول', gross - accum),
              ('رأس المال المصدر', capital), ('يخصم: رأس المال تحت الطلب', called), ('حصص المساهمين مقابل عقد التسوية', share),
              ('أرباح (خسائر) مرحلة', prior), ('صافي ربح (خسارة) السنة', cur), ('إجمالي حقوق الملكية', equity),
              ('إجمالي الالتزامات', liab), ('إجمالي الالتزامات وحقوق الملكية', liab + equity)]
    for r, (lab, v) in enumerate(items6, start=4):
        s.cell(r, 1, lab)
        s.cell(r, 2, money(v))
    s.cell(4 + len(items6), 1, 'اختبار التوازن')
    s.cell(4 + len(items6), 2, 'متوازن' if gross - accum == liab + equity else 'غير متوازن')

    # 7 assets (originals)
    s = ws[7]
    s['A1'] = 'جدول الأصول الثابتة والإهلاك'
    s['A2'] = 'تاريخ بدء الإهلاك: 02/07/2019 — تاريخ قرار الجهة بقبول التنازل'
    for c, h in enumerate(['كود الحساب', 'المكوّن', 'التكلفة', 'نسبة الإهلاك السنوي', 'الإهلاك السنوي', 'إهلاك 2019 (6 أشهر)',
                           'إهلاك 2020'], start=1):
        s.cell(4, c, h)
    orig = [('1130', 'آلات ومعدات', 10000, 0.05), ('1120', 'مبانٍ ومنشآت', 20000, 0.02), ('1110', 'أرض', 5000, 0)]
    for r, (a, b, c, rate) in enumerate(orig, start=5):
        s.cell(r, 1, a)
        s.cell(r, 2, b)
        s.cell(r, 3, c)
        s.cell(r, 4, rate)
        s.cell(r, 5, c * rate)
        s.cell(r, 6, c * rate / 2)
        s.cell(r, 7, c * rate)
    s.cell(8, 2, 'الإجمالي')
    s.cell(8, 3, sum(x[2] for x in orig))

    # 8 settlement
    s = ws[8]
    s['A1'] = 'سجل مساعد — مقابل عقد التسوية موزعاً على المساهمين'
    for c, h in enumerate(['المساهم', 'الكود', 'نسبة المساهمة', 'الرصيد الدائن', 'مسدد', 'الرصيد'], start=1):
        s.cell(4, c, h)
    for c, v in enumerate(['منير الحلبي', '2351', 1, 35000, 0, 35000], start=1):
        s.cell(5, c, v)
    s.cell(6, 1, 'الإجمالي')
    for c, v in zip((3, 4, 5, 6), (1, 35000, 0, 35000)):
        s.cell(6, c, v)
    s.cell(8, 1, 'ملحوظة')
    s.cell(8, 2, 'ملاحظة اختبار على التوزيع.')

    # 9 partner balances (by account binding)
    s = ws[9]
    s['A1'] = 'سجل مساعد — أرصدة الأطراف الممولة'
    for c, h in enumerate(['الطرف', 'الصفة', 'كود حساب الممول', 'رصيد حساب الممول', 'كود الاستحقاقات', 'رصيد الاستحقاقات',
                           'الإجمالي'], start=1):
        s.cell(4, c, h)
    f10 = -closing['2310']
    f11 = -closing['2311']
    for c, v in enumerate(['د/ زهرة المقدسي', 'ممول', '2310', money(f10), '2311', money(f11), money(f10 + f11)], start=1):
        s.cell(5, c, v)
    s.cell(6, 1, 'الإجمالي')
    for c, v in zip((4, 6, 7), (money(f10), money(f11), money(f10 + f11))):
        s.cell(6, c, v)

    # 10 open items
    s = ws[10]
    s['A1'] = 'سجل البنود المفتوحة — يُغلق البند عند ورود مستنده'
    for c, h in enumerate(['#', 'السنة', 'البند', 'الأثر على الحسابات', 'المستند المطلوب', 'الحالة'], start=1):
        s.cell(3, c, h)
    oi = [(1, 2019, 'تفصيل مصروفات التأسيس', 'يغيّر مصروف الفترة', 'إيصالات', 'مفتوح'),
          (2, 2019, 'تحويل وارد غير موضح', 'يحدد مصدر المبلغ', 'كشف البنك', 'قيد الاستفسار'),
          (3, '2019-2020', 'توزيع المصروفات على السنوات', 'يغيّر مصروف كل سنة', 'تواريخ البنود', 'جزئي'),
          (4, '2020', 'مرتبات 2020', 'يعدل المستحق', 'كشوف الأجور', 'مغلق'),
          (5, '2019+', 'ضريبة المرتبات', 'التزام غير مسجل', 'تسوية', 'مفتوح'),
          (6, 2019, 'تاريخ قيد تمويل 15/1/2019', 'سابق على تأسيس الشركة', 'تاريخ الاستلام الفعلي', 'مفتوح')]
    for r, row in enumerate(oi, start=4):
        for c, v in enumerate(row, start=1):
            s.cell(r, c, v)

    # 11 close status
    s = ws[11]
    s['A1'] = 'شركة نور للتجارة — حالة إقفال السنوات والتحفظات'
    for c, h in enumerate(['السنة', 'حالة الإقفال', 'مصادر البناء', 'ما لم يُقيَّد', 'التحفظ', 'تاريخ آخر تحديث'], start=1):
        s.cell(4, c, h)
    s.cell(5, 1, '2019'); s.cell(5, 2, 'مقفلة بتحفظ'); s.cell(5, 3, 'شهادة التأسيس · جدول الأصول')
    s.cell(5, 4, 'مصروفات التشغيل'); s.cell(5, 5, 'لم تُقدَّم دفاتر عن هذه السنة.'); s.cell(5, 6, '05/02/2026')
    s.cell(6, 1, '2020'); s.cell(6, 2, 'مقفلة مبدئياً بتحفظ — لحين الردود'); s.cell(6, 3, 'كشف البنك 2020')
    s.cell(6, 4, 'فرق منصرف'); s.cell(6, 5, 'تُعدَّل السنة بما يرد.'); s.cell(6, 6, '11/02/2026')
    s.cell(7, 1, 'تحفظ عام على السنوات 2019 – 2020')
    s.cell(8, 1, '•'); s.cell(8, 2, 'لم تُمسك دفاتر منتظمة قبل 2020.')
    s.cell(10, 1, 'ما يلزم لإعادة فتح السنوات وتعديل قيودها')
    s.cell(11, 1, '2019'); s.cell(11, 2, 'كشف حساب البنك من التأسيس')
    s.cell(12, 1, '2019'); s.cell(12, 2, 'إيصالات مصروفات التأسيس')
    s.cell(13, 1, '2020'); s.cell(13, 2, 'دفتر خزينة 2020')
    s.cell(14, 1, 'عام'); s.cell(14, 2, 'محاضر الجمعيات العامة')
    s.cell(15, 1, '•'); s.cell(15, 2, 'نطاق الإقفال — أُقفلت السنوات 2019 و2020 بتحفظ.')
    s.cell(16, 1, '2021'); s.cell(16, 2, 'جاهزة للاعتماد — لم تُفتح بعد')

    # 12 contingent
    s = ws[12]
    s['A1'] = 'الالتزامات المحتملة'
    for c, h in enumerate(['الاسم', 'الصفة', 'المستحق بعقد التسوية', 'المقيَّد بالدفاتر', 'الفرق'], start=1):
        s.cell(6, c, h)
    for c, v in enumerate(['منير الحلبي', 'دائن ومساهم', 40000, 35000, -5000], start=1):
        s.cell(7, c, v)
    s.cell(8, 2, 'الإجمالي')
    for c, v in zip((3, 4, 5), (40000, 35000, -5000)):
        s.cell(8, c, v)
    s.cell(10, 1, 'خلاصة')
    s.cell(11, 1, '•'); s.cell(11, 2, 'نص اختباري للموقف.')

    # 13 assumptions
    s = ws[13]
    s['A1'] = 'الافتراضات المعتمدة لحين ورود مستنداتها'
    for c, h in enumerate(['#', 'الافتراض', 'الأثر على القوائم', 'المستند المطلوب', 'لو لم يرد'], start=1):
        s.cell(4, c, h)
    for r, n in enumerate(range(1, 6), start=5):
        for c, v in enumerate([n, f'افتراض اختباري رقم {n}', 'أثر اختباري', 'مستند اختباري', 'يُعدَّل المبلغ'], start=1):
            s.cell(r, c, v)

    # 14 financier funding trace
    s = ws[14]
    s['A1'] = 'سجل مساعد — تمويل أحد الممولين ومصارفه'
    for c, h in enumerate(['البيان', 'السنة', 'المبلغ', 'الحساب المقابل'], start=1):
        s.cell(4, c, h)
    s.cell(5, 1, 'المبلغ المستلم'); s.cell(5, 2, '2019'); s.cell(5, 3, 1000); s.cell(5, 4, '2310')
    s.cell(7, 1, 'يخصم — المصروفات المسددة منه:')
    s.cell(8, 1, 'أتعاب'); s.cell(8, 2, '2019'); s.cell(8, 3, -600); s.cell(8, 4, '5230')
    s.cell(9, 1, 'الرصيد المتبقي'); s.cell(9, 3, 400)
    s.cell(11, 1, 'ملاحظات')
    s.cell(12, 1, '•'); s.cell(12, 2, 'ملاحظة اختبارية.')

    # 15 legal expenses
    s = ws[15]
    s['A1'] = 'تفصيل المصروفات القانونية — 3 بنود'
    for c, h in enumerate(['#', 'البند', 'المبلغ', 'التصنيف', 'السنة الفعلية'], start=1):
        s.cell(4, c, h)
    legal = [(1, 'رسوم اختبار', 300, 'رسوم ونثريات', 2019), (2, 'أتعاب اختبار', 700, 'أتعاب وقضايا', 2019),
             (3, 'نثريات', 100, 'رسوم ونثريات', 2020)]
    for r, row in enumerate(legal, start=5):
        for c, v in enumerate(row, start=1):
            s.cell(r, c, v)
    s.cell(9, 1, 'ملخص التصنيف')
    s.cell(10, 1, 'رسوم ونثريات — حساب 5260'); s.cell(10, 3, 400)
    s.cell(11, 1, 'أتعاب محاماة وقضايا — حساب 5230'); s.cell(11, 3, 700)
    s.cell(12, 1, 'الإجمالي'); s.cell(12, 3, 1100)

    # 16 payroll exposure
    s = ws[16]
    s['A1'] = 'التزام ضريبة المرتبات والضمان الاجتماعي'
    for c, h in enumerate(['السنة', 'المدير التنفيذي', 'موظف أول', 'بقية الموظفين', 'إجمالي المرتبات', 'الحالة الضريبية',
                           'حالة الضمان'], start=1):
        s.cell(4, c, h)
    for r, row in enumerate([(2019, 3000, 0, 1000, 4000, 'لم تُحسب', 'لم تُسدَّد'), (2020, 3000, 500, 1500, 5000, 'لم تُحسب', 'لم تُسدَّد')], start=5):
        for c, v in enumerate(row, start=1):
            s.cell(r, c, v)
    for c, v in zip(range(1, 6), ('الإجمالي', 6000, 500, 2500, 9000)):
        s.cell(7, c, v)
    s.cell(9, 1, 'الأساس القانوني')
    s.cell(10, 1, '•'); s.cell(10, 2, 'نص اختباري للأساس القانوني.')

    # 17 accountant reconciliation
    s = ws[17]
    s['A1'] = 'مطابقة أرصدة الأطراف ونتائج السنوات مع دفاتر المحاسب'
    s['A3'] = '(1) أرصدة الأطراف'
    for c, h in enumerate(['الطرف', 'عند المحاسب', 'عندنا', 'الفرق', 'التفسير'], start=1):
        s.cell(4, c, h)
    for c, v in enumerate(['د/ زهرة المقدسي', 90000, 100000, -10000, 'فرق اختباري'], start=1):
        s.cell(5, c, v)
    s['A7'] = '(2) نتائج السنوات'
    for c, h in enumerate(['البند', 'عند المحاسب', 'عندنا', 'ملاحظة', 'الفرق'], start=1):
        s.cell(8, c, h)
    for c, v in enumerate(['خسارة 2019', -1000, -1100, 'اختبار', 100], start=1):
        s.cell(9, c, v)

    # 18 allocation
    s = ws[18]
    s['A1'] = 'تنسيب الأموال المضخوخة إلى أسهم'
    s['A4'] = 'مدخلات الحساب'
    s['A5'], s['B5'] = 'أسهم الأساس', 1000
    s['A6'], s['B6'] = 'تقييم الشركة المتفق عليه', 1000000
    s['A7'], s['B7'] = 'تقييم الضخ اللاحق', 2000000
    s['A9'], s['B9'] = 'تاريخ الإقفال', datetime(2020, 12, 31)
    s['A12'] = 'السيناريو (أ): اختباري'
    heads = ['الاسم', 'نسبة الأساس', 'أسهم الأساس', 'ضخ 2022', 'أسهم 2022', 'ضخ 2023', 'أسهم 2023', 'ضخ 2024', 'أسهم 2024',
             'أسهم حتى 2024', 'النسبة حتى 2024', 'ضخ 2025 حتى الإقفال', 'أسهم 2025 حتى الإقفال', 'الأسهم يوم الإقفال',
             'النسبة يوم الإقفال']
    for c, h in enumerate(heads, start=1):
        s.cell(14, c, h)
    p1 = [0.6, 600, '=2000+3000', 5, 0, 0, 0, 0, 605, 0.605, 0, 0, 605, 0.605]
    p2 = [0.4, 400, 0, 0, 0, 0, 0, 0, 395, 0.395, 0, 0, 395, 0.395]
    for c, v in enumerate(['شخص أول'] + p1, start=1):
        s.cell(15, c, v)
    for c, v in enumerate(['شخص ثانٍ'] + p2, start=1):
        s.cell(16, c, v)
    for c, v in enumerate(['الإجمالي', 1, 1000, 5000, 5, 0, 0, 0, 0, 1000, 1, 0, 0, 1000, 1], start=1):
        s.cell(17, c, v)
    s.cell(18, 1, 'سعر الحصة المستخدم'); s.cell(18, 7, 1000); s.cell(18, 13, 1000)
    s.cell(19, 1, 'قيمة الشركة الضمنية بعد الضخ'); s.cell(19, 2, 1000000)
    s.cell(21, 1, 'توريدات الممول الأول بتاريخها')
    for c, h in enumerate(['التاريخ', 'المبلغ', 'البيان', 'محتسب؟'], start=1):
        s.cell(22, c, h)
    for r, (dt, amt, txt, flag) in enumerate([(datetime(2020, 1, 3), 1000, 'توريد اختباري', 'نعم'),
                                              (datetime(2020, 5, 3), 2000, 'توريد اختباري آخر', 'بعد الإقفال')], start=23):
        for c, v in enumerate([dt, amt, txt, flag], start=1):
            s.cell(r, c, v)

    # 19 funding evidence
    s = ws[19]
    s['A1'] = 'إثبات كل مبلغ من مبالغ الضخ'
    for c, h in enumerate(['الشريك', 'التاريخ', 'المبلغ', 'النوع', 'المستند المُثبِت', 'موضعه والمستفيد', 'التأكيد المستقل',
                           'قوة الإثبات', 'داخل في النسب؟'], start=1):
        s.cell(4, c, h)
    s.cell(5, 1, 'ممول أول — 2020')
    ev = [('ممول أول', datetime(2020, 2, 2), 20000, 'تحويل بنكي', 'كشف البنك', 'سطر 4', 'تحليل', '(أ)', 'نعم'),
          ('ممول أول', datetime(2020, 3, 2), 500, 'نقدي', 'دفتر الخزينة', 'ص1', 'تحليل', '(ب) + تطابق', 'نعم'),
          ('ممول أول', datetime(2021, 1, 2), 700, 'إفادة', 'إفادة الإدارة', 'بند', '—', '(ج) — لا عقد', 'بعد الإقفال'),
          ('ممول أول', datetime(2020, 4, 2), 300, 'مصروف مستبعد', 'دفتر', 'ص2', '—', '(ب)', 'مستبعد')]
    for r, row in enumerate(ev, start=6):
        for c, v in enumerate(row, start=1):
            s.cell(r, c, v)
    s.cell(11, 1, 'ملخص الأرقام')
    for c, h in enumerate(['الشريك', 'داخل في النسب', 'بعد الإقفال', 'الإجمالي (بدون المستبعد)'], start=1):
        s.cell(12, c, h)
    for c, v in enumerate(['ممول أول', 20500, 700, 21200], start=1):
        s.cell(13, c, v)

    # 20 sources and uses
    s = ws[20]
    s['A1'] = 'هل الضخ يساوي الصرف؟'
    for c, h in enumerate(['البند', '2019', '2020'], start=1):
        s.cell(4, c, h)
    cash = [c for c in codes if c.startswith('13')]
    ch = {y: sum(mov.get((y, c), (0, 0))[0] - mov.get((y, c), (0, 0))[1] for c in cash) for y in (2019, 2020)}
    s.cell(5, 1, 'أ) ضخ الشركاء النقدي')
    s.cell(6, 1, '   ممول أول'); s.cell(6, 2, 0); s.cell(6, 3, 20000)
    s.cell(7, 1, 'هـ) التغير في النقدية (خزينة + بنوك)'); s.cell(7, 2, money(ch[2019])); s.cell(7, 3, money(ch[2020]))
    s.cell(9, 1, 'تحقق: (ج) + (د) − (هـ) = صفر'); s.cell(9, 2, 0); s.cell(9, 3, 0)
    s.cell(11, 1, 'قراءة الجدول')
    s.cell(12, 1, 'نص اختباري للقراءة.')

    wb.save(path)
    return path


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'synthetic.xlsx'
    build(out)
    print('wrote', out)
