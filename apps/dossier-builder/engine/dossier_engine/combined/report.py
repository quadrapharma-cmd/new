"""Stage 9 — the reports, in formal Arabic, as Word and as PDF: one for the CTD folder (what was received, what was built, what
was left out and why, the product card, the findings, what Egypt's Module 1 still needs, how the work was done and what the
program decided by itself, the list of documents) and one for the eCTD sequence (its content, the corrections, the changes to
the product information, what only the company or the authority can complete, the values to confirm, the translation, the
validation). Everything is read from the stages' files; what a person decided comes from the dossier's decisions file.
Writes report/ctd-report.{html,pdf,docx}, report/ectd-report.{…} and report.json; then the delivery, as the hand-built one
was given: the dossier's report inside its CTD folder («00 READ FIRST - report (Arabic)»), and deliver/<name>/ with the sequence
(submission/<sequence>), the Word files of the product information (submission/<sequence>-workingdocuments), «report and
checks» (the eCTD report, validation-results.csv, source-map.csv) and a zip of the submission folder."""
import csv
import html as H
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .assess import DESK_VERDICT_AR, KIND_AR, VERDICT_AR
from .common import Work, count, ranges, say
from .fix import AR, LRM, ZWSP, keep, pieces, print_html

SEV = {'critical': 'حرجة', 'major': 'مهمة', 'minor': 'شكلية'}
CSS = '''@page { size: A4; margin: 18mm 18mm 16mm 18mm; }
body { font-family: "Noto Naskh Arabic", "Liberation Sans", sans-serif; font-size: 10.5pt; line-height: 1.6; color: #111; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 4pt; } .sub { color: #555; margin: 0 0 12pt; }
h2 { font-size: 13pt; margin: 16pt 0 5pt; border-bottom: 1px solid #ccd; padding-bottom: 2pt; break-after: avoid; }
h3 { font-size: 11pt; margin: 10pt 0 3pt; break-after: avoid; }
p { margin: 0 0 5pt; text-align: justify; } ul { margin: 0 0 5pt; padding: 0 16pt 0 0; } li { margin: 0 0 2pt; }
table { border-collapse: collapse; width: 100%; margin: 3pt 0 9pt; font-size: 9pt; } td, th { border: 1px solid #b8c0cc; padding: 2pt 4pt; vertical-align: top; }
th { background: #e8ecf2; } .nw { white-space: nowrap; } .num { text-align: center; }'''


class Doc:
    """A report written once and given as HTML (for the PDF) and as Word."""

    def __init__(self, title, sub=''):
        self.title, self.sub, self.blocks = title, sub, []

    def h1(self, t):
        self.blocks.append(('h1', t))

    def h2(self, t):
        self.blocks.append(('h2', t))

    def p(self, t):
        self.blocks.append(('p', t))

    def ul(self, items):
        self.blocks.append(('ul', [x for x in items if x]))

    def table(self, head, rows, widths=None):
        self.blocks.append(('table', (head, rows, widths)))

    # -- HTML
    @staticmethod
    def h(t):
        t = str(t)
        if not AR.search(t):
            return f'<span dir="ltr">{H.escape(t)}</span>'
        out = ''
        for x, ltr in pieces(t):
            nw = ' class="nw"' if len(x) <= 30 and ' ' not in x else ''
            out += f'<span dir="ltr"{nw}>{H.escape(keep(x))}</span>' if ltr else H.escape(x)
        return out

    def html(self):
        b = [f'<h1>{self.h(self.title)}</h1>', f'<p class="sub">{self.h(self.sub)}</p>' if self.sub else '']
        for kind, x in self.blocks:
            if kind == 'h1':
                b.append(f'<h2>{self.h(x)}</h2>')
            elif kind == 'h2':
                b.append(f'<h3>{self.h(x)}</h3>')
            elif kind == 'p':
                b.append(f'<p>{self.h(x)}</p>')
            elif kind == 'ul':
                b.append('<ul>' + ''.join(f'<li>{self.h(i)}</li>' for i in x) + '</ul>')
            elif kind == 'table':
                head, rows, _ = x
                cell = lambda c: '<br>'.join(self.h(x) for x in c) if isinstance(c, list) else self.h(c)
                b.append('<table><tr>' + ''.join(f'<th>{cell(c)}</th>' for c in head) + '</tr>'
                         + ''.join('<tr>' + ''.join(f'<td>{cell(c)}</td>' for c in r) + '</tr>' for r in rows) + '</table>')
        return (f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{H.escape(self.title)}</title>'
                f'<style>{CSS}</style></head><body>{"".join(b)}</body></html>')

    # -- Word
    def docx(self, path):
        from docx.oxml import OxmlElement
        from docx.shared import Twips
        from .fix import docx_doc, no_borders, page_field, run_props, spacing
        d = docx_doc('Arial', 21, rtl=True)
        d.core_properties.title = self.title
        fp = d.sections[0].footer.paragraphs[0]
        spacing(fp, align='center', bidi=True)
        page_field(fp, 16, '666666', 'Arial', ('صفحة ', ' من '), rtl=True)
        first = [(d.paragraphs[0] if d.paragraphs else d.add_paragraph())]

        def par(t, size=21, bold=False, before=None, after=80, keep_next=False):
            p = first.pop() if first else d.add_paragraph()
            ar = bool(AR.search(str(t)))
            spacing(p, before, after, keep_next, 'both' if ar else 'right', bidi=True)
            runs(p, str(t), size, bold)
            return p

        def runs(p, t, size, bold):
            ps = pieces(t) if AR.search(t) else [(t, True)]
            for i, (x, ltr) in enumerate(ps):
                if ltr:
                    if i == 0 and AR.search(t):
                        run_props(p.add_run(LRM + ZWSP), size=size, bold=bold, font='Arial', rtl=True)
                    run_props(p.add_run(keep(x) + ('' if re.search(r'[A-Za-z0-9µ½]$', x) else LRM)), size=size, bold=bold, font='Arial')
                else:
                    nxt = ps[i + 1] if i + 1 < len(ps) else None
                    run_props(p.add_run(x + (LRM + ZWSP if nxt and nxt[1] else '')), size=size, bold=bold, font='Arial', rtl=True)
        par(self.title, 32, True, after=60)
        if self.sub:
            par(self.sub, 19, after=200)
        for kind, x in self.blocks:
            if kind == 'h1':
                par(x, 26, True, before=280, after=100, keep_next=True)
            elif kind == 'h2':
                par(x, 22, True, before=180, after=60, keep_next=True)
            elif kind == 'p':
                par(x)
            elif kind == 'ul':
                for i in x:
                    par('• ' + str(i), after=40)
            elif kind == 'table':
                head, rows, widths = x
                t = d.add_table(rows=len(rows) + 1, cols=len(head))
                t.style = d.styles['Table Grid']
                fixed_table(t, widths or WIDTHS.get(len(head)) or [1] * len(head))
                for i, r in enumerate([head] + rows):
                    for j, c in enumerate(r):
                        cell = t.cell(i, j)
                        for k, x in enumerate(c if isinstance(c, list) else [c]):
                            p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
                            spacing(p, None, 0, align='right', bidi=True)    # not justified: LibreOffice loops on a narrow justified
                                                                              # cell mixing Arabic and Latin
                            runs(p, str(x), 17, i == 0)
                d.add_paragraph()
        d.save(path)


REASONS = [   # why a page or a document was left out, as the stages write it (English), in the report's Arabic
    (r'^separator page \(the section title only\)$', 'صفحة فاصلة (عنوان القسم وحده)'),
    (r'^separator page \((.+)\)$', r'صفحة فاصلة (\1)'),
    (r'^table of contents of this substance.*$', 'فهرس المادة الفعالة (سطوره في فهرس Module 3، البند 3.1)'),
    (r'^table of contents of (3\.2\.[PA]).*$', r'فهرس \1 (سطوره في فهرس Module 3، البند 3.1)'),
    (r'^table of contents: the eCTD XML replaces it$', 'فهرس: ملف XML يقوم مقامه'),
    (r'^cover page of the annexures to Module 3$', 'غلاف ملاحق Module 3'),
    (r'^cover page of Module (\d).*$', r'غلاف Module \1'),
    (r'^page after the cover.*$', 'صفحة بعد الغلاف'),
    (r'^list of the annexures.*$', 'قائمة ملاحق Module 3'),
    (r'^page without a heading at the start of its (?:block|module)$', 'صفحة بلا عنوان في بداية جزئها'),
    (r'^page before the first annexure.*$', 'صفحة قبل أول ملحق'),
    (r'^empty \(«----»\)$', 'فارغ («----»)'),
    (r'^a heading only$', 'عنوان فقط'),
    (r'^«(.+)» only$', r'لا يقول إلا «\1»'),
]


def reason_ar(t):
    for rx, ar in REASONS:
        if re.match(rx, t):
            return re.sub(rx, ar, t)
    return t


TEXT_WIDTH = 9026                                   # A4 less two margins of 2.54 cm, in twips
WIDTHS = {2: [7, 3], 3: [4, 4, 2], 4: [2, 5, 3, 3], 5: [2, 6, 3, 3, 2]}


def fixed_table(t, weights):
    """A right-to-left table of fixed column widths (LibreOffice lays out a table of free widths with long Arabic cells for
    ever): its width, its grid, each cell's width, «fixed» layout, and w:bidiVisual in its place after the style."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import qn
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    total = sum(weights)
    widths = [int(TEXT_WIDTH * x / total) for x in weights]
    tbl = t._tbl
    tblpr = tbl.tblPr
    for tag in ('w:tblW', 'w:tblLayout', 'w:bidiVisual'):
        for x in tblpr.findall(qn(tag)):
            tblpr.remove(x)
    style = tblpr.find(qn('w:tblStyle'))
    at = list(tblpr).index(style) + 1 if style is not None else 0
    tblpr.insert(at, parse_xml(f'<w:bidiVisual {ns}/>'))
    tblpr.insert(at + 1, parse_xml(f'<w:tblW {ns} w:type="dxa" w:w="{sum(widths)}"/>'))
    look = tblpr.find(qn('w:tblLook'))
    layout = parse_xml(f'<w:tblLayout {ns} w:type="fixed"/>')
    if look is not None:
        look.addprevious(layout)
    else:
        tblpr.append(layout)
    grid = tbl.find(qn('w:tblGrid'))
    for col, wdt in zip(grid.findall(qn('w:gridCol')), widths):
        col.set(qn('w:w'), str(wdt))
    from docx.shared import Twips
    for row in t.rows:
        for j, cell in enumerate(row.cells):
            cell.width = Twips(widths[j])


def write(doc, stem, w):
    w.report.mkdir(parents=True, exist_ok=True)
    html = w.report / f'{stem}.html'
    html.write_text(doc.html(), encoding='utf-8')
    print_html(html, w.report / f'{stem}.pdf')
    doc.docx(w.report / f'{stem}.docx')
    return {'html': str(html), 'pdf': str(w.report / f'{stem}.pdf'), 'docx': str(w.report / f'{stem}.docx')}


def mb(n):
    return f'{n / 1e6:,.1f} ميجابايت'


def ctd_report(w):
    dec = w.decisions()
    R = dec.get('report') or {}
    files = w.load('read/files.json')
    pages = w.load('read/pages.json')
    rep = w.load('repeats.json')
    parts = w.load('parts.json')
    plan = w.load('plan.json')
    asm = w.load('assembled.json')
    found = w.load('findings.json', [])
    docs = plan['docs']
    n_pages = len(pages)
    kept = sum(b - a + 1 for a, b in rep['kept'])
    placed = sum(len(d['pages']) for d in docs)
    by_program = sum(1 for d in docs if d.get('by') == 'program')
    doc = Doc(R.get('title', 'تقرير الملف'), R.get('subtitle', ''))
    doc.h1('1. الخلاصة')
    dropped = sum(x['pages'] for x in rep['dropped'])
    doc.ul([f'وصل {count(len(files), "ملف")}؛ فيها {count(n_pages, "صفحة")} بصيغة PDF.',
            f'تُرك منها {count(dropped, "صفحة")} لأنها نسخ ثانية من كتل كاملة سبقتها في الملف نفسه.' if dropped else '',
            f'بُني الملف من {count(len(docs), "مستند")} تضم {count(placed, "صفحة")}، وطوبقت كل صفحة منها بأصلها: '
            f'المطابقة {asm.get("pages_checked", 0) - len(asm.get("wrong", [])):,} من {asm.get("pages_checked", 0):,}.',
            f'الصفحات القابلة للبحث بعد التعرف الضوئي: {asm.get("searchable", 0):,} من {asm.get("pages_in_docs", placed):,}.',
            f'المستندات التي قطعها البرنامج ووضعها بنفسه: {by_program} من {len(docs)}؛ والباقي بقرارات من ملف القرارات (القسم 8).',
            f'الملاحظات: {len(found)} — ' + '، '.join(f'{SEV[s]}: {sum(1 for f in found if f["severity"] == s)}' for s in ('critical', 'major', 'minor')) + '.'])
    crit = [f for f in found if f['severity'] in ('critical', 'major')][:6]
    if crit:
        doc.h2('أهم ما يلزم قبل التقديم')
        doc.ul([f'{f["text"]} (الملاحظة {f["n"]})' for f in crit])
    doc.h1('2. ما وصل')
    doc.table(['الملف', 'النوع', 'الحجم', 'الصفحات', 'ملاحظة'],
              [[f['name'], {'pdf': 'PDF', 'rtf': 'RTF', 'doc': 'Word 97–2003', 'docx': 'Word'}.get(f['kind'], f['kind']), mb(f['size']),
                f'{f.get("pages", ""):,}' if f.get('pages') else '—',
                (f"حُفظ جانبًا باسم {f['keep_as']}" + (f"؛ {f['matches']['same_words']:,} من {f.get('words', 0):,} كلمة منه في «{f['matches']['block']}»" if f.get('matches') else ''))
                if f.get('aside') else ''] for f in files])
    doc.h1('3. الملف المبني')
    mods = defaultdict(lambda: [0, 0])
    for d in docs:
        m = d['path'].split('/')[0]
        mods[m][0] += 1
        mods[m][1] += len(d['pages'])
    doc.table(['الجزء', 'المستندات', 'الصفحات'], [[m, v[0], f'{v[1]:,}'] for m, v in sorted(mods.items())])
    doc.h1('4. ما استُبعد ولماذا')
    if rep['dropped']:
        doc.h2(f'4.1 الكتل المكررة ({count(dropped, "صفحة")})')
        doc.table(['الكتلة المتروكة', 'الصفحات', 'نسخة من', 'متطابقة بالبايت', 'متطابقة في الرسم بدقة 24 نقطة'],
                  [[x['title'], f"{x['from']}–{x['to']}", f"{x['same_as_title']} ({x['same_as'][0]}–{x['same_as'][1]})", x['same_bytes'], x['same_24dpi']]
                   for x in rep['dropped']])
    why = Counter(r['why'] for r in plan['removed'] if not any(x['from'] <= r['page'] <= x['to'] for x in rep['dropped']))
    doc.h2('4.2 صفحات تُركت من داخل الكتل')
    merged = Counter()
    for k, v in why.items():
        merged[reason_ar(k)] += v
    doc.table(['السبب', 'عدد الصفحات'], [[k, v] for k, v in merged.most_common()])
    where = {p: d for d in docs for p in d['pages']}
    pairs = Counter()
    for g in rep.get('identical_groups', []):
        ds = tuple(sorted({where[p]['title'] for p in g if p in where}))
        if len(ds) >= 1 and sum(1 for p in g if p in where) > 1:
            pairs[ds] += 1
    if pairs:
        doc.h2('4.3 صفحات متطابقة لم تُستبعد (للمراجعة)')
        doc.table(['المستندات', 'مجموعات الصفحات'], [[' | '.join(k), v] for k, v in pairs.most_common(12)])
    card = R.get('product_card')
    if card:
        doc.h1('5. بطاقة المنتج (من الملف نفسه)')
        doc.p('أرقام الصفحات في هذا التقرير هي أرقام صفحات الملف المجمَّع الأصلي، والفهرس في آخر التقرير يربطها بالمستندات المبنية.')
        doc.table(['البيان', 'القيمة', 'المصدر'], card)
    doc.h1('6. الملاحظات')
    doc.table(['م', 'الملاحظة', 'الموضع', 'المطلوب', 'المصدر'],
              [[f['label'], f['text'], f['where'], f['action'], 'البرنامج' if f['by'] == 'program' else 'المراجع'] for f in found],
              [11, 40, 21, 21, 9])
    needs = R.get('eg_m1_needs')
    if needs:
        doc.h1('7. Module 1 المصرية: ما يلزم')
        if R.get('eg_m1_intro'):
            doc.p(R['eg_m1_intro'])
        if needs and isinstance(needs[0], list):
            doc.table(['البند', 'الحال في الملف الوارد', 'الجهة المصدِرة'], needs, [33, 43, 22])
        else:
            doc.ul(needs)
    doc.h1('8. طريقة العمل')
    edits = plan.get('edits', [])
    doc.ul(['قُرئ نص كل صفحة كما في الملف، وقُرئت الإشارات المرجعية، ورُسمت كل صفحة بدقة 24 نقطة في البوصة.',
            'عُرفت الكتل المكررة بمقارنة الصفحات بالبايت وبالرسم، ثم قورنت كل صفحتين متقابلتين.',
            'قُرئت الصفحات التي بلا نص بالتعرف الضوئي (OCRmyPDF وTesseract) على مرحلتين؛ الصفحات التي بقيت بلا نص: '
            f'{sum(len(p["still_without_text"]) for p in parts)}.',
            'قُطع الملف بعناوين CTD في أعلى الصفحات، مع قواعد الفهارس والفواصل والأغلفة، ووُضع كل مستند في مكانه.',
            f'المستندات التي قطعها البرنامج ووضعها بنفسه: {by_program} من {len(docs)}؛ والباقي بقرارات من ملف القرارات (تسمية أو قطع أو وضع)، '
            f'عددها {len(edits)}.',
            'نُسخت الصفحات دون تغيير، ثم طوبقت صور كل صفحة بصفحتها الأصلية بايتًا ببايت، وقيس أثر طبقة النص على شكل الصفحة '
            f'(أسوأ نسبة بكسلات تغيرت: {asm.get("worst_look_change", 0)}).'])
    rv = w.load('review.json')
    if rv:
        au = (rv.get('authority') or {}).get('name') or {}
        doc.h1('مراجعة المقيّم (محاكاة البرنامج، لا قرار الجهة الرقابية)')
        cn = rv['counts']
        doc.ul([f"الجهة: {au.get('ar') or au.get('en') or ''}. النتيجة: {VERDICT_AR.get(rv['verdict'], rv['verdict'])} — {(rv.get('why') or {}).get('ar', '')}",
                f"الملاحظات المفتوحة: حرجة {cn.get('critical', 0)}، رئيسية {cn.get('major', 0)}، ثانوية {cn.get('minor', 0)}؛ "
                f"وأسئلة لم تُقيَّم آليًا {cn.get('not_assessable', 0)}.",
                'تقرير التقييم وخطاب الاستيفاء لكل إدارة في مجلد «review and requests» بالتسليم.'])
        doc.table(['الإدارة', 'التوصية', 'حرجة', 'رئيسية', 'ثانوية'],
                  [[d.get('name') or d['dept'], DESK_VERDICT_AR.get(d['verdict'], d['verdict']), d['counts'].get('critical', 0), d['counts'].get('major', 0), d['counts'].get('minor', 0)] for d in rv['desks']])
        if rv.get('parties'):
            doc.h2('النواقص حسب الجهة المُصدِرة')
            doc.table(['الجهة', 'عدد البنود', 'خطاب الطلب'],
                      [[p['name'] or KIND_AR.get(p['kind'], p['kind']), len(p['items']),
                        'مُعدّ' if p.get('letter') else ((f"كتب البرنامج {p['built']} للتوقيع؛ والباقي على الشركة" if p.get('built') else 'تكتبه الشركة')
                                                        if p['kind'] == 'company' else (p.get('letter_refused') or '—'))]
                       for p in rv['parties']])
    doc.h1('الملحق: فهرس الوثائق')
    doc.table(['CTD', 'المستند', 'صفحات الملف الأصلي', 'العدد', 'قابلة للبحث'],
              [[d['ctd'], d['title'], ranges(d['pages']), len(d['pages']), d.get('searchable', '')] for d in docs], [12, 50, 20, 8, 10])
    return doc


def ectd_report(w):
    dec = w.decisions()
    R = dec.get('report') or {}
    e = w.load('ectd.json')
    val = w.load('validation.json')
    fixed = w.load('fixed.json', {}) or {}
    v = e['validation']
    doc = Doc(R.get('ectd_title', 'تقرير eCTD'), R.get('ectd_subtitle', ''))
    doc.h1('1. الخلاصة')
    doc.ul([f"التسلسل {e['envelope']['sequence']} وفق ICH eCTD v3.2.2 والملف الإقليمي المصري المؤقت v0.",
            f"الأوراق (leaf): في Modules 2–5 {len(e['leaves'])}، وفي Module 1 {len(e['m1'])}؛ والملفات {e['files']} بحجم {mb(e['bytes'])}.",
            f"قواعد النجاح والرسوب: الناجحة {v['pf_pass']} والراسبة {v['pf_fail']}؛ قواعد أفضل الممارسات: المتحققة {v['bp_met']} وغير المتحققة {v['bp_not']}.",
            'ما رسب أو لم يتحقق مذكور في القسم 5 مع سببه.'])
    doc.h1(f"2. محتوى التسلسل {e['envelope']['sequence']}")
    by_mod = Counter(l['code'][0] for l in e['leaves'])
    doc.table(['الوحدة', 'الأوراق'], [['1', len(e['m1'])]] + [[m, by_mod[m]] for m in sorted(by_mod)])
    if e['left_out']:
        doc.h2('مستندات لم تدخل التسلسل')
        doc.table(['المستند', 'السبب'], [[Path(p).stem, reason_ar(why)] for p, why in e['left_out'].items()])
    doc.h1('3. التصحيحات المنفذة')
    rows = [[Path(k).stem, f"ص {x['page']}", '؛ '.join(f'«{a}» ← «{b}»' for a, b in x['edits']), x['changed_pixels']]
            for k, x in (fixed.get('docs') or {}).items()]
    if rows:
        doc.table(['المستند', 'الصفحة', 'التصحيح', 'نسبة البكسلات المتغيرة'], rows)
    if fixed.get('pi'):
        doc.ul([f"{p['title']}: Word وPDF" for p in fixed['pi']])
    changes = R.get('pi_changes')
    if changes:
        doc.h1('4. التغييرات في نص معلومات المنتج')
        doc.table(['الموضع', 'كان', 'صار', 'السبب'], changes)
    doc.h1('5. ما لا يُستكمل إلا من الشركة أو الهيئة')
    bad = [r for r in val if not r['ok']]
    doc.table(['القاعدة', 'النوع', 'التفصيل'], [[r['rule'], 'نجاح/رسوب' if r['kind'] == 'P/F' else 'أفضل الممارسات', r['detail']] for r in bad])
    if R.get('company_gaps'):
        doc.h2('مستندات تُطلب')
        doc.table(['المطلوب', 'موضعه في الـ eCTD', 'الجهة'], R['company_gaps'])
    if R.get('to_confirm'):
        doc.h1('6. قيم في الملف تحتاج تأكيدكم')
        doc.table(['البيان', 'القيمة الحالية', 'ملاحظة'], R['to_confirm'])
    if fixed.get('translation_checks') is not None and fixed.get('pi'):
        doc.h1('7. الترجمة العربية')
        doc.ul([f'{k}: ' + ('الكتل نفسها بالترتيب نفسه، والأرقام نفسها في كل كتلة، وقيم التركيب متطابقة.' if not v2 else '؛ '.join(v2))
                for k, v2 in fixed['translation_checks'].items()] + (R.get('translation_notes') or []))
    e4, cz = w.load('ectd40.json'), w.load('ctdzip.json')
    failed = w.load('outputs-failed.json', {}) or {}
    if e4 or cz or failed:
        doc.h1('8. الصيغتان الأخريان')
        if failed:
            doc.ul([f"تعذّرت صيغة {'eCTD 4.0' if k == 'ectd40' else 'ctd.zip'} لهذا الملف: {v}. تسلسل eCTD 3.2.2 سليم ومُسلَّم، "
                    'وتُبنى هذه الصيغة بعد تصحيح البرنامج.' for k, v in failed.items()])
        rows = []
        if e4:
            v4 = e4['validation']
            rows.append([f"eCTD 4.0 (التسلسل {e4['number']})", f"{e4['documents']} مستندًا، {e4['files']} ملفًا",
                         f"الناجحة {v4['pass']} والراسبة {v4['fail']} والتنبيهات {v4['warning']}"])
        if cz:
            rows.append(['CTD One Submission ‏(ctd.zip)', f"{cz['documents']} مستندًا في بنود NP.CAPP.065",
                         f"بنود مطلوبة ناقصة {len(cz['required_missing'])}؛ مستندات بلا بند {len(cz['unplaced'])}"])
        doc.table(['الصيغة', 'المحتوى', 'النتيجة'], rows)
        doc.ul(['المستندات في الصيغ الثلاث هي ملفات تسلسل eCTD 3.2.2 نفسها، بايتًا ببايت'
                + ('، إلا ما لا يقبله eCTD 4.0 في موضعه (الجدول أدناه).' if e4 and e4.get('left_out') else '.'),
                'eCTD 4.0 مكتوب على الملف المصري المؤقت للإصدار 4.0 (مسودات الهيئة)؛ وأرقام OID الإقليمية فيه مؤقتة حتى تسجلها الهيئة.',
                'ctd.zip هو ما تستلمه الهيئة اليوم (NP.CAPP.065 v5)، ومعه 00-navigator.html و00-checklist.csv لكل بند وحالته.'])
        if e4:
            bad4 = [r for r in e4['results'] if r['status'] != 'pass']
            if bad4:
                doc.table(['قاعدة eCTD 4.0', 'النتيجة', 'التفصيل'],
                          [[r['rule'], 'راسبة' if r['status'] == 'fail' else 'تنبيه', '؛ '.join(map(str, r['failures'][:3]))] for r in bad4])
        if e4 and e4.get('left_out'):
            doc.table(['مستند لم يدخل eCTD 4.0', 'موضعه في 3.2.2', 'السبب'],
                      [[x['title'], x['node'], x['why']['ar']] for x in e4['left_out']])
        if cz and cz['unplaced']:
            doc.table(['مستند بلا بند في ctd.zip', 'رقمه'], [[u['title'], u['node']] for u in cz['unplaced']])
    eb = w.load('ebox.json')
    if eb and eb.get('country') and eb['country'] != 'EG':
        doc.h1(f"مخرجات الدولة المطلوبة ({eb['country']})")
        doc.ul([f"أُنشئ الملف في برنامج eBOX الكامل لجهة {eb['pack']}، ووُضع {eb['placed']} مستندًا في بنودها؛ "
                f"وبقي {eb['missing_required']} بندًا مطلوبًا ناقصًا.",
                'المخرجات نسخة عمل ليست للتقديم حتى تكتمل البنود المطلوبة: ' + '، '.join(eb.get('files') or {}) + '.'] +
               [f"{k}: {'مطابق' if v['ok'] else 'غير مطابق'} — الناجحة {v['counts'].get('pass', 0)} والراسبة {v['counts'].get('fail', 0)}"
                for k, v in (eb.get('validation') or {}).items()])
        if eb.get('unplaced'):
            doc.table(['مستند بلا بند عند هذه الجهة', 'رقمه'], [[u['title'], u['node']] for u in eb['unplaced']])
    bd = w.load('build.json')
    if bd and bd.get('items'):
        items = bd['items']
        built = [x for x in items if x['state'] == 'built']
        doc.h1('المستندات الناقصة التي تُصدرها الشركة')
        doc.ul([f"البنود المطلوبة الناقصة التي تُصدرها الشركة نفسها: {len(items)}؛ كتب البرنامج منها {len(built)} من صفحات الملف وبياناته "
                f"({sum(1 for x in built if x.get('signed'))} منها وُقِّع وخُتم بصورتَي التوقيع والختم المرفوعتين، و{sum(1 for x in built if x.get('sign'))} "
                f"جاهزة لتوقيع الشركة وختمها)، وبقي على الشركة "
                f"{sum(1 for x in items if x['state'] == 'cannot')}، وأُجّل إلى تشغيل لاحق {sum(1 for x in items if x['state'] == 'later' and x.get('by') == 'claude')}؛ "
                f"وبنود الجهات الأخرى ({bd.get('others', 0)}) في خطابات الطلب.",
                'لم يُكتب في هذه المستندات إلا ما في صفحات الملف؛ وما لم تذكره الصفحات تُرك فارغًا وذُكر في «ما يلزم».'])
        doc.table(['البند', 'المستند', 'الحالة', 'ملاحظة'],
                  [[x['req'], (x.get('title') or {}).get('ar') or (x.get('title') or {}).get('en', ''),
                    ('يُكتب لاحقًا' if x['state'] == 'later' and x.get('by') == 'claude' else
                     {'built': 'كُتب' + (' ووُقِّع وخُتم بالصورتين المرفوعتين' if x.get('signed') else ' — للتوقيع' if x.get('sign') else ''),
                      'cannot': 'على الشركة', 'later': 'في مرحلة أخرى',
                      'to do': 'لم يُكتب بعد'}.get(x['state'], x['state'])),
                    x.get('note') or ('بيانات ناقصة فيه: ' + str(len(x.get('gaps') or [])) if x.get('gaps') else '')] for x in items], [10, 40, 16, 34])
    g = (w.load('ectd.json') or {}).get('global') or {}
    if g.get('layers'):
        doc.h1('الفحص العالمي (ICH ومعايير الجهة)')
        doc.ul([f"{k}: {'مطابق' if v.get('ok') else 'غير مطابق'} — الناجحة {v.get('pass', 0)} والراسبة {v.get('fail', 0)} والتنبيهات {v.get('warn', 0)}"
                for k, v in g['layers'].items()] + [(g.get('note') or {}).get('ar', '')])
    doc.h1('9. طريقة العمل')
    doc.ul(['أُخذت المستندات من الملف المبني (CTD)، ووُضع كل مستند في عنصره من ICH DTD 3.2 بأسماء المجلدات والملفات في الملحق 4 من ICH.',
            'تُركت الفهارس (ملف XML هو الفهرس) والمستندات التي لا تقول إلا «غير قابل للتطبيق» أو «لا شيء» (EG-BP-E24).',
            'المستند المشترك بين عدة مواد فعالة حُفظ مرة واحدة وأُشير إليه من كل مادة.',
            'صفحات الملخص الشامل المنسوخة من Module 3 (خمس متتالية أو أكثر) حلت محلها صفحة إحالة.',
            'كُتب كل ملف PDF بصيغة 1.4 أو أحدث، مُحسَّنًا للعرض على الويب، ومجموع MD5 لكل ملف.',
            'فُحص التسلسل بمعايير الملف المصري المؤقت (validation-criteria.csv) قاعدة قاعدة.'])
    return doc


def link_tree(src, dst):
    """A copy of a folder made of hard links where the disk allows it (no second copy of the bytes)."""
    for root, _, files in os.walk(src):
        r = Path(root)
        (dst / r.relative_to(src)).mkdir(parents=True, exist_ok=True)
        for f in files:
            t = dst / r.relative_to(src) / f
            try:
                os.link(r / f, t)
            except OSError:
                shutil.copy2(r / f, t)


def deliver(w, out):
    dec = w.decisions()
    D = dec.get('deliver') or {}
    folder = w.ctd / (dec.get('ctd_folder') or 'CTD')
    for kind in ('pdf', 'docx'):
        shutil.copyfile(out['ctd'][kind], folder / f'00 READ FIRST - report (Arabic).{kind}')
    e = w.load('ectd.json')
    if not e:
        return None
    seq = Path(e['sequence'])
    name = D.get('name') or f"{dec.get('ctd_folder') or 'CTD'} - eCTD {seq.name}"
    root = w.root / 'deliver' / name
    if root.exists():
        shutil.rmtree(root)
    sub = root / 'submission'
    link_tree(seq, sub / seq.name)
    fixed = w.load('fixed.json', {}) or {}
    if fixed.get('pi'):
        (sub / f'{seq.name}-workingdocuments').mkdir(parents=True, exist_ok=True)
        for p in fixed['pi']:
            shutil.copyfile(p['docx'], sub / f'{seq.name}-workingdocuments' / Path(p['docx']).name)
    rc = root / 'report and checks'
    rc.mkdir(parents=True, exist_ok=True)
    for kind in ('pdf', 'docx'):
        shutil.copyfile(out['ectd'][kind], rc / f'00 READ FIRST - eCTD report (Arabic).{kind}')
    with open(rc / 'validation-results.csv', 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.writer(f)
        wr.writerow(['rule', 'kind', 'result', 'detail'])
        for r in w.load('validation.json'):
            wr.writerow([r['rule'], r['kind'], 'PASS' if r['ok'] else 'NOT MET', r['detail']])

    def span(p):
        return '' if not p else (f'{p[0]}-{p[-1]}' if len(p) > 1 else str(p[0]))

    def rel(path):
        try:
            return str(Path(path).resolve().relative_to(w.root))
        except ValueError:
            return str(path)
    with open(rc / 'source-map.csv', 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.writer(f)
        wr.writerow(['eCTD file', 'leaf ID', 'title', 'source', 'pages of the combined file', 'note'])
        for m in e['m1']:
            wr.writerow(['m1/eg/' + m[2], m[5], m[3], rel(m[6]), span(m[7]) if m[7] else '', ''])
        for l in e['leaves']:
            wr.writerow([l['href'], l['id'], l['title'], rel(l['source']), span(l['pages']), l['note']])
        for k, v in e['left_out'].items():
            wr.writerow(['(not in the eCTD)', '', k, k, '', v])
    zname = D.get('zip') or f'{seq.name}.zip'
    parts = [seq.name] + ([f'{seq.name}-workingdocuments'] if fixed.get('pi') else [])
    subprocess.run(['zip', '-r', '-q', '-X', str(root / zname)] + parts, cwd=sub, check=True)
    got = {'folder': str(root), 'zip': str(root / zname)}
    e4, cz = w.load('ectd40.json'), w.load('ctdzip.json')
    if e4:                                                   # eCTD 4.0: <application UUID>/<sequence>, zipped from the application's folder
        s4 = Path(e4['sequence'])
        link_tree(s4, root / 'eCTD 4.0' / s4.parent.name / s4.name)
        subprocess.run(['zip', '-r', '-q', '-X', str(root / 'ectd40.zip'), s4.parent.name], cwd=root / 'eCTD 4.0', check=True)
        got['ectd40_zip'] = str(root / 'ectd40.zip')
        with open(rc / 'validation-results-ectd40.csv', 'w', newline='', encoding='utf-8-sig') as f:
            wr = csv.writer(f)
            wr.writerow(['rule', 'severity', 'result', 'failures'])
            for r in e4['results']:
                wr.writerow([r['rule'], r['severity'], r['status'].upper(), ' | '.join(map(str, r['failures']))])
    if cz:
        shutil.copyfile(cz['zip'], root / 'ctd.zip')
        got['ctd_zip'] = str(root / 'ctd.zip')
    rv = w.load('review.json')
    if rv and (w.root / 'review').exists():                 # the assessor's reports and letters, and one request letter per party
        link_tree(w.root / 'review', root / 'review and requests')
        got['review'] = str(root / 'review and requests')
    eb = w.load('ebox.json')
    if eb and eb.get('country') and eb['country'] != 'EG':  # another country's outputs, as eBOX's full program wrote them (working copies)
        dst = root / f"eBOX {eb['country']} (working copy)"
        dst.mkdir(parents=True, exist_ok=True)
        for k, f in (eb.get('files') or {}).items():
            if Path(f).exists():
                shutil.copyfile(f, dst / Path(f).name)
        if eb.get('report') and Path(eb['report']).exists():
            shutil.copyfile(eb['report'], dst / 'validation-report.html')
        got['country_outputs'] = str(dst)
    say(f'التسليم: {root}')
    return got


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    out = {}
    say('تقرير الملف')
    out['ctd'] = write(ctd_report(w), 'ctd-report', w)
    if w.load('ectd.json'):
        say('تقرير eCTD')
        out['ectd'] = write(ectd_report(w), 'ectd-report', w)
    out['deliver'] = deliver(w, out)
    w.save('report.json', out)
    return out
