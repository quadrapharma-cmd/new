"""Stage 9 — the reports, in formal Arabic, as Word and as PDF: one for the CTD folder (what was received, what was built, what
was left out and why, the product card, the findings, what Egypt's Module 1 still needs, how the work was done and what the
program decided by itself, the list of documents) and one for the eCTD sequence (its content, the corrections, the changes to
the product information, what only the company or the authority can complete, the values to confirm, the translation, the
validation). Everything is read from the stages' files; what a person decided comes from the dossier's decisions file.
Writes report/ctd-report.{html,pdf,docx}, report/ectd-report.{…} and report.json."""
import html as H
import re
from collections import Counter, defaultdict
from pathlib import Path

from .common import Work, ranges, say
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
                t._tbl.tblPr.append(OxmlElement('w:bidiVisual'))
                for i, r in enumerate([head] + rows):
                    for j, c in enumerate(r):
                        cell = t.cell(i, j)
                        if widths:
                            cell.width = Twips(widths[j])
                        for k, x in enumerate(c if isinstance(c, list) else [c]):
                            p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
                            spacing(p, None, 0, align='both' if AR.search(str(x)) else 'right', bidi=True)
                            runs(p, str(x), 17, i == 0)
                d.add_paragraph()
        d.save(path)


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
    doc.ul([f'وصل {len(files)} ملفًّا؛ فيها {n_pages:,} صفحة PDF.',
            f'تُرك {sum(x["pages"] for x in rep["dropped"]):,} صفحة لأنها نسخ ثانية من كتل كاملة سبقتها في الملف نفسه.',
            f'بُني الملف من {len(docs)} مستندًا تضم {placed:,} صفحة، كل صفحة منها طوبقت بأصلها '
            f'({asm.get("pages_checked", 0) - len(asm.get("wrong", [])):,} من {asm.get("pages_checked", 0):,} مطابقة).',
            f'الصفحات القابلة للبحث بعد التعرف الضوئي: {asm.get("searchable", 0):,} من {asm.get("pages_in_docs", placed):,}.',
            f'قطع البرنامج ووضع {by_program} مستندًا بنفسه، و{len(docs) - by_program} بقرارات من ملف القرارات (القسم 8).',
            f'الملاحظات: {len(found)} — ' + '، '.join(f'{sum(1 for f in found if f["severity"] == s)} {SEV[s]}' for s in ('critical', 'major', 'minor')) + '.'])
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
        doc.h2(f'4.1 الكتل المكررة ({sum(x["pages"] for x in rep["dropped"]):,} صفحة)')
        doc.table(['الكتلة المتروكة', 'الصفحات', 'نسخة من', 'متطابقة بالبايت', 'متطابقة في الرسم بدقة 24 نقطة'],
                  [[x['title'], f"{x['from']}–{x['to']}", f"{x['same_as_title']} ({x['same_as'][0]}–{x['same_as'][1]})", x['same_bytes'], x['same_24dpi']]
                   for x in rep['dropped']])
    why = Counter(r['why'] for r in plan['removed'] if not any(x['from'] <= r['page'] <= x['to'] for x in rep['dropped']))
    doc.h2('4.2 صفحات تُركت من داخل الكتل')
    doc.table(['السبب', 'عدد الصفحات'], [[k, v] for k, v in why.most_common()])
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
              [[f['label'], f['text'], f['where'], f['action'], 'البرنامج' if f['by'] == 'program' else 'المراجع'] for f in found])
    needs = R.get('eg_m1_needs')
    if needs:
        doc.h1('7. Module 1 المصرية: ما يلزم')
        if R.get('eg_m1_intro'):
            doc.p(R['eg_m1_intro'])
        if needs and isinstance(needs[0], list):
            doc.table(['البند', 'الحال في الملف الوارد', 'الجهة المصدِرة'], needs)
        else:
            doc.ul(needs)
    doc.h1('8. طريقة العمل')
    edits = plan.get('edits', [])
    doc.ul(['قُرئ نص كل صفحة كما في الملف، وقُرئت الإشارات المرجعية، ورُسمت كل صفحة بدقة 24 نقطة في البوصة.',
            'عُرفت الكتل المكررة بمقارنة الصفحات بالبايت وبالرسم، ثم قورنت كل صفحتين متقابلتين.',
            f'قُرئت الصفحات التي بلا نص بالتعرف الضوئي (OCRmyPDF وTesseract) على مرحلتين؛ بقيت {sum(len(p["still_without_text"]) for p in parts)} صفحة بلا نص.',
            'قُطع الملف بعناوين CTD في أعلى الصفحات، مع قواعد الفهارس والفواصل والأغلفة، ووُضع كل مستند في مكانه.',
            f'قطع البرنامج ووضع {by_program} مستندًا من {len(docs)} بنفسه؛ والباقي بـ{len(edits)} قرارًا من ملف القرارات (تسمية أو قطع أو وضع).',
            'نُسخت الصفحات دون تغيير، ثم طوبقت صور كل صفحة بصفحتها الأصلية بايتًا ببايت، وقيس أثر طبقة النص على شكل الصفحة '
            f'(أسوأ نسبة بكسلات تغيرت: {asm.get("worst_look_change", 0)}).'])
    doc.h1('الملحق: فهرس الوثائق')
    doc.table(['CTD', 'المستند', 'صفحات الملف الأصلي', 'العدد', 'قابلة للبحث'],
              [[d['ctd'], d['title'], ranges(d['pages']), len(d['pages']), d.get('searchable', '')] for d in docs])
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
            f"{len(e['leaves'])} ورقة في Modules 2–5 و{len(e['m1'])} في Module 1؛ {e['files']} ملفًّا بحجم {mb(e['bytes'])}.",
            f"قواعد النجاح والرسوب: {v['pf_pass']} ناجحة و{v['pf_fail']} راسبة؛ أفضل الممارسات: {v['bp_met']} متحققة و{v['bp_not']} غير متحققة.",
            'ما رسب أو لم يتحقق مذكور في القسم 5 مع سببه.'])
    doc.h1(f"2. محتوى التسلسل {e['envelope']['sequence']}")
    by_mod = Counter(l['code'][0] for l in e['leaves'])
    doc.table(['الوحدة', 'الأوراق'], [['1', len(e['m1'])]] + [[m, by_mod[m]] for m in sorted(by_mod)])
    if e['left_out']:
        doc.h2('مستندات لم تدخل التسلسل')
        doc.table(['المستند', 'السبب'], [[Path(p).stem, why] for p, why in e['left_out'].items()])
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
    doc.h1('8. طريقة العمل')
    doc.ul(['أُخذت المستندات من الملف المبني (CTD)، ووُضع كل مستند في عنصره من ICH DTD 3.2 بأسماء المجلدات والملفات في الملحق 4 من ICH.',
            'تُركت الفهارس (ملف XML هو الفهرس) والمستندات التي لا تقول إلا «غير قابل للتطبيق» أو «لا شيء» (EG-BP-E24).',
            'المستند المشترك بين عدة مواد فعالة حُفظ مرة واحدة وأُشير إليه من كل مادة.',
            'صفحات الملخص الشامل المنسوخة من Module 3 (خمس متتالية أو أكثر) حلت محلها صفحة إحالة.',
            'كُتب كل ملف PDF بصيغة 1.4 أو أحدث، مُحسَّنًا للعرض على الويب، ومجموع MD5 لكل ملف.',
            'فُحص التسلسل بمعايير الملف المصري المؤقت (validation-criteria.csv) قاعدة قاعدة.'])
    return doc


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    out = {}
    say('تقرير الملف')
    out['ctd'] = write(ctd_report(w), 'ctd-report', w)
    if w.load('ectd.json'):
        say('تقرير eCTD')
        out['ectd'] = write(ectd_report(w), 'ectd-report', w)
    w.save('report.json', out)
    return out
