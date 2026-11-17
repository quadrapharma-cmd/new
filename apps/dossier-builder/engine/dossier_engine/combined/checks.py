"""Stage 6 — the findings: what the documents say against each other, and what the dossier lacks.

The rules the program runs by itself (each finding says its pages):
  · units: the same quantity of the same component written with different mass units (1.25 mg in 3.2.P.1, 1.25 mcg in the SmPC)
    — a thousandfold difference: critical;
  · shelf life: the product information states it in more than one way («24 months from date of manufacture» / «… from the date
    of last satisfactory potency»);
  · animal origin: materials of animal origin named in control of materials (3.2.S.2.3) while 3.2.A.2 says «not applicable»;
  · the Quality Overall Summary reproducing Module 3 pages (the pages identical to Module 3 pages, by their bytes);
  · old references: pharmacopoeia editions and WHO Technical Report Series ten years old or more;
  · regional information (3.2.R) of one page;
  · clinical data ten years old or more, post-marketing experience stated as none, pharmacovigilance empty;
  · no GMP certificate, no certificate of a pharmaceutical product (CPP) among the documents;
  · a Module 1 received in another region's layout, its empty sections, its heading-only documents, the same pages in two
    experts' sections, mock-ups without Arabic;
  · a printed CTD number whose title is another section's (from the cut);
  · pages that still have no text after the OCR;
  · a document over the authority's size limit (from the cut).
What the rules cannot see (a wrong description of a container, an excipient list that leaves out what Module 3 names) is added
in the dossier's decisions file (findings), marked as a reviewer's finding. Writes findings.json."""
import datetime
import re
from collections import defaultdict

from .common import NO_TEXT, Work, ranges, say

MASS = {'mg': 1e-3, 'mcg': 1e-6, 'µg': 1e-6, 'μg': 1e-6, 'ug': 1e-6, 'g': 1.0}
QTY = re.compile(r'([A-Za-z][A-Za-z\-]{0,30}(?:\s?\+{1,3})?)\s?[:=]?\s?([≤≥<>]\s?)?(\d{1,6}(?:\.\d{1,4})?)\s?(mcg|µg|μg|ug|mg|g|%)(?![A-Za-z])')
SYMBOL = str.maketrans({'\uf0a3': '≤', '\uf0b3': '≥', '\uf03c': '<', '\uf03e': '>', '\uf0b1': '±', '\uf0b4': '×', '\uf06d': 'µ'})
ANIMAL = re.compile(r'\b(beef|bovine|casein|peptone|porcine|pancrea\w*|calf|horse\s+serum|sheep|gelatin|trypsin|meat)\b', re.I)
SHELF = re.compile(r'(\d+)\s*months?\s+from\s+(?:the\s+)?(date\s+of\s+(?:the\s+)?(?:last\s+)?[a-z]+(?:\s+[a-z]+)?)', re.I)
PHARMA = re.compile(r'\b(I\.?P\.?|B\.?P\.?|Ph\.?\s?Eur\.?|U\.?S\.?P\.?)\b[^0-9]{0,40}?\(?\s*((?:19|20)\d\d)', re.I)
TRS = re.compile(r'\bTRS\s*(\d+)\s*\(\s*((?:19|20)\d\d)\s*\)', re.I)
SEV = {'critical': 'حرجة', 'major': 'مهمة', 'minor': 'شكلية'}
STOP = {'of', 'about', 'and', 'to', 'than', 'per', 'add', 'dissolve', 'dilute', 'containing', 'contains', 'with', 'in', 'is', 'x',
        'weigh', 'accurately', 'approximately', 'each', 'the', 'or', 'from', 'take', 'pack', 'mix', 'into', 'at', 'for', 'equivalent'}


class Checker:
    def __init__(self, w):
        self.w = w
        self.plan = w.load('plan.json')
        self.docs = self.plan['docs']
        self.text = w.pages_text('read/text.txt')
        ocr = w.pages_text('read/ocr.txt')
        self.ocr = ocr if len(ocr) == len(self.text) else self.text
        self.where = {p: d for d in self.docs for p in d['pages']}
        self.found = []
        self._pages = {}
        dec = w.decisions()
        today = (dec.get('ectd') or {}).get('today')
        self.today = datetime.date.fromisoformat(today) if today else datetime.date.today()

    def page(self, p):
        if p not in self._pages:
            t = self.text[p - 1] if len(self.text[p - 1].strip()) >= NO_TEXT else self.ocr[p - 1]
            self._pages[p] = ' '.join(t.translate(SYMBOL).split())          # the Symbol font's ≤ ≥ are private-use letters
        return self._pages[p]

    def add(self, rule, order, severity, text, where, action):
        self.found.append({'rule': rule, 'order': order, 'severity': severity, 'text': text, 'where': where, 'action': action, 'by': 'program'})

    def docs_at(self, prefix):
        return [d for d in self.docs if d['ctd'].startswith(prefix)]

    # -- the rules
    def units(self):
        """The composition of 3.2.P.1 is the reference: a component's quantity found elsewhere with the same number and another
        mass unit is a finding (critical: a thousandfold difference); the same number with the limit sign («≤») missing is a
        finding too (minor). The labels are the words just before the quantity in 3.2.P.1."""
        ref = {}
        for d in self.docs_at('3.2.P.1'):
            for p in d['pages']:
                for m in QTY.finditer(self.page(p)):
                    label = re.sub(r'\s+', '', m.group(1)).lower()
                    if label in STOP or len(label) < 3 and '+' not in label:
                        continue
                    ref.setdefault((label, m.group(3)), ((m.group(2) or '').strip(), m.group(4).lower().replace('μ', 'µ'), p))
        seen = defaultdict(lambda: defaultdict(set))
        for d in self.docs:
            for p in d['pages']:
                for m in QTY.finditer(self.page(p)):
                    key = (re.sub(r'\s+', '', m.group(1)).lower(), m.group(3))
                    if key in ref:
                        seen[key][((m.group(2) or '').strip(), m.group(4).lower().replace('μ', 'µ'))].add(p)
        for (label, num), by in seen.items():
            q0, u0, p0 = ref[(label, num)]
            name = label.replace('+++', ' +++').strip().capitalize() if '+' in label else label.capitalize()
            units = {u for (_, u) in by if u in MASS}
            factors = {MASS[u] for u in units}
            if len(factors) > 1:
                pages = defaultdict(set)
                for (q, u), ps in by.items():
                    pages[u] |= ps
                parts = [f'بوحدة {u}: ص {ranges(sorted(pages[u]))}' for u in sorted(units, key=lambda u: MASS[u])]
                wrong = sorted(u for u in units if u != u0)
                self.add('units', 10, 'critical',
                         f'كمية «{name}» مكتوبة «{q0 + " " if q0 else ""}{num} {" / ".join(wrong)}» في مواضع، و«{q0 + " " if q0 else ""}{num} {u0}» في 3.2.P.1: '
                         f'فرق {int(round(max(factors) / min(factors)))} ضعف في معلومات المنتج.',
                         '؛ '.join(parts), 'تصحيح الوحدة في كل موضع خطأ (الصحيح ما في 3.2.P.1 وبيانات التصنيع).')
            if q0 and u0 not in MASS:
                bare = sorted(p for (q, u), ps in by.items() if u == u0 and not q for p in ps)
                if bare:
                    self.add('limit_sign', 130, 'minor', f'«{name}» مكتوب «{num} {u0}» في مواضع، و«{q0} {num} {u0}» في 3.2.P.1.',
                             f'ص {ranges(bare)}؛ 3.2.P.1 ص {p0}', 'صيغة واحدة.')

    def shelf_life(self):
        said = defaultdict(set)
        for d in self.docs:
            if not d['path'].startswith('Module 1'):
                continue
            for p in d['pages']:
                for m in SHELF.finditer(self.page(p)):
                    said[(m.group(1), ' '.join(m.group(2).lower().split()))].add(p)
        if len({k[1] for k in said}) > 1:
            self.add('shelf_life', 50, 'major', 'مدة الصلاحية مكتوبة بأكثر من صيغة في معلومات المنتج: '
                     + '، '.join(f'«{n} months from {w}»' for n, w in sorted(said)) + '.',
                     'ص ' + ranges(sorted(set().union(*said.values()))), 'صيغة واحدة تستند إلى بيانات الثبات (3.2.P.8).')

    def animal_origin(self):
        hits = defaultdict(set)
        for d in self.docs_at('3.2.S.2.3'):
            for p in d['pages']:
                for m in ANIMAL.finditer(self.page(p)):
                    hits[m.group(1).lower()].add(p)
        a2 = self.docs_at('3.2.A.2')
        na = any(re.search(r'not\s+applicable', self.page(p), re.I) for d in a2 for p in d['pages'])
        if hits and (na or not a2):
            pages = sorted(set().union(*hits.values()))
            self.add('animal_origin', 60, 'major',
                     'مواد من أصل حيواني مذكورة في ضبط المواد (3.2.S.2.3): ' + '، '.join(sorted(hits)) + '؛ بينما البند 3.2.A.2 '
                     + ('مكتوب فيه «Not Applicable».' if na else 'غير موجود.'),
                     f'ص {ranges(pages[:40])}' + (f'؛ 3.2.A.2 ص {ranges([p for d in a2 for p in d["pages"]])}' if a2 else ''),
                     'تقييم السلامة من العوامل العرضية (3.2.A.2) وشهادات TSE/BSE للمواد الحيوانية.')

    def qos_copy(self):
        groups = (self.w.load('repeats.json') or {}).get('identical_groups', [])
        m3 = {p for d in self.docs if d['ctd'].startswith('3.') for p in d['pages']}
        copied = defaultdict(set)
        for g in groups:
            if any(p in m3 for p in g):
                for p in g:
                    d = self.where.get(p)
                    if d and d['ctd'].startswith('2.3'):
                        copied[d['path']].add(p)
        if copied:
            total = sum(len(v) for v in copied.values())
            parts = [f"{len(v)} من {len(self.where_doc(k)['pages'])} في {self.where_doc(k)['title']}" for k, v in copied.items() if len(v) >= 5]
            if parts:
                self.add('qos_copy', 70, 'major',
                         f'الملخص الشامل للجودة (2.3) يعيد صفحات من Module 3 كما هي: {total} صفحة ({"، ".join(parts)}). '
                         'ودليل ICH M4Q يجعل الملخص في حدود 40 صفحة نصية عادةً، و80 صفحة للمنتجات الحيوية.',
                         'ص ' + ranges(sorted(set().union(*copied.values()))), 'إعادة كتابة الملخص ملخصًا يحيل إلى Module 3.')

    def where_doc(self, path):
        return next(d for d in self.docs if d['path'] == path)

    def references(self):
        old = set()
        pages = set()
        for d in self.docs:
            if not (d['ctd'].startswith('3.2.P.1') or d['ctd'] == '3.3'):
                continue
            for p in d['pages'][:3]:
                t = self.page(p)
                for m in PHARMA.finditer(t):
                    if int(m.group(2)) <= self.today.year - 10:
                        old.add(f'{m.group(1).replace(" ", "")} {m.group(2)}')
                        pages.add(p)
                for m in TRS.finditer(t):
                    if int(m.group(2)) <= self.today.year - 10:
                        old.add(f'WHO TRS {m.group(1)} ({m.group(2)})')
                        pages.add(p)
        if old:
            self.add('references', 80, 'major', 'المراجع قديمة: ' + '، '.join(sorted(old)) + '.', 'ص ' + ranges(sorted(pages)),
                     'التحديث إلى الإصدارات السارية من الدساتير ومتطلبات منظمة الصحة العالمية.')

    def regional(self):
        r = self.docs_at('3.2.R')
        if r and sum(len(d['pages']) for d in r) <= 1:
            self.add('regional', 90, 'major', 'البند 3.2.R (المعلومات الإقليمية) صفحة واحدة.', 'ص ' + ranges([p for d in r for p in d['pages']]),
                     'المعلومات الإقليمية التي تطلبها الهيئة.')

    def clinical(self):
        years = []
        for d in self.docs_at('5.3.5'):
            for p in d['pages'][:5]:
                years += [int(y) for y in re.findall(r'\b(19[89]\d|20[0-4]\d)\b', self.page(p))]
        notes, where = [], []
        if years and max(years) <= self.today.year - 10:
            notes.append(f'البيانات السريرية حتى عام {max(years)}')
            where.append('ص ' + ranges([p for d in self.docs_at('5.3.5') for p in (d['pages'][0], d['pages'][-1])]))
        pm = self.docs_at('5.3.6')
        if pm and len(pm[0]['pages']) <= 2 and re.search(r'no\s+(?:\w+\s+){0,3}stud(?:y|ies)\s+(?:have|has)\s+been', ' '.join(self.page(p) for p in pm[0]['pages']), re.I):
            notes.append('البند 5.3.6 (خبرة ما بعد التسويق) ينص على عدم إجراء أي دراسات')
            where.append('ص ' + ranges(pm[0]['pages']))
        pv = [d for d in self.docs if d['path'].startswith('Module 1') and d['ctd'] == '1.8']
        if pv and re.search(r'-{4,}', ' '.join(self.page(p) for p in pv[0]['pages'])):
            notes.append('البند 1.8 (اليقظة الدوائية) فارغ')
            where.append('ص ' + ranges(pv[0]['pages']))
        if notes:
            self.add('clinical', 100, 'major', '، و'.join(notes) + '.', '، '.join(where),
                     'تقارير السلامة الدورية (PSUR/PBRER) وخطة إدارة المخاطر وبيانات ما بعد التسويق.')

    def certificates(self):
        gmp = cpp = False
        said = []
        for d in self.docs:
            for p in d['pages'][:2]:
                t = self.page(p)
                if re.search(r'certificate\s+of\s+(?:a\s+)?pharmaceutical\s+product|\bCPP\b', t, re.I):
                    cpp = True
                if re.search(r'GMP\s+certificate|certificate\s+of\s+(?:GMP|good\s+manufacturing)', t, re.I):
                    gmp = True
        for d in self.docs:
            for p in d['pages']:
                if re.search(r'complying\s+with\s+prevailing\s+WHO\s+GMP', self.page(p), re.I):
                    said.append(p)
        if not gmp or not cpp:
            lack = [x for x, ok in (('شهادة GMP', gmp), ('شهادة المستحضر الصيدلاني (CPP)', cpp)) if not ok]
            self.add('certificates', 110, 'major', 'لا توجد في الملف ' + ' ولا '.join(lack)
                     + ('؛ يوجد فقط نص يقول إن التصنيع «complying with prevailing WHO GMP conditions».' if said else '.'),
                     ('ص ' + ranges(said[:5])) if said else '—', 'طلبها من الشركة المصنعة.')

    def module1(self):
        m1 = [d for d in self.docs if d['path'].startswith('Module 1')]
        if not m1:
            return
        notes = []
        if any('EU layout' in d['path'] for d in m1):
            notes.append('Module 1 الواردة على نموذج الاتحاد الأوروبي')
        heading = [d['ctd'] for d in m1 if 'heading page' in d['title'] or 'heading page' in d.get('note', '')]
        empty = [d['ctd'] for d in m1 if re.search(r'-{4,}', ' '.join(self.page(p) for p in d['pages'][-1:]))
                 and len(' '.join(self.page(p) for p in d['pages'])) < 900]
        if heading:
            notes.append('صفحات عنوان فقط في البنود ' + ' و'.join(heading))
        if empty:
            notes.append('البنود ' + ' و'.join(sorted(set(empty), key=lambda k: [int(x) for x in k.split('.')])) + ' فارغة')
        groups = (self.w.load('repeats.json') or {}).get('identical_groups', [])
        twins = set()
        for g in groups:
            ds = {self.where[p]['ctd'] for p in g if p in self.where and self.where[p]['path'].startswith('Module 1')}
            if {'1.4.2', '1.4.3'} <= ds:
                twins.add(True)
        if twins:
            notes.append('السيرة الذاتية نفسها في 1.4.2 و1.4.3')
        mock = [d for d in m1 if d['ctd'] == '1.3.2']
        if mock and not any(re.search('[؀-ۿ]', self.page(p)) for d in mock for p in d['pages']):
            notes.append('نماذج العبوة بلا نص عربي')
        if notes:
            self.add('module1', 120, 'major', '، و'.join(notes) + '.', 'ص ' + ranges([p for d in m1 for p in (d['pages'][0],)]),
                     'Module 1 المصرية بمستنداتها (القائمة في التقرير).')

    def from_cut(self):
        for f in self.plan.get('findings', []):
            if f['kind'] == 'heading_number':
                self.add('heading_number', 140, 'minor', f"عنوان الصفحة مطبوع «{f['printed']}»، ومحتواها {f['is']}؛ وُضعت في {f['is']} حسب محتواها.",
                         f"ص {f['page']}", 'تصحيح العنوان.')
            elif f['kind'] == 'too_large':
                self.add('too_large', 160, 'minor', f"مستند بحجم {f['bytes'] // 10**6} ميجابايت، أكبر من حد الملف الواحد (100 ميجابايت).",
                         f['doc'], f"قُسِّم إلى {f['parts']} أجزاء.")

    def no_text(self):
        parts = self.w.load('parts.json', []) or []
        still = sorted(p for x in parts for p in x.get('still_without_text', []) if p in self.where)
        if still:
            self.add('no_text', 150, 'minor', f'{len(still)} صفحة بلا نص حتى بعد التعرف الضوئي (صور أو خط يد).', 'ص ' + ranges(still),
                     'طلب نسخ أصلية بنص للوثائق الأساسية إن أمكن.')

    def run(self):
        for rule in (self.units, self.shelf_life, self.animal_origin, self.qos_copy, self.references, self.regional, self.clinical,
                     self.certificates, self.module1, self.from_cut, self.no_text):
            rule()
        return self.found


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    c = Checker(w)
    found = c.run()
    for f in (w.decisions().get('findings') or []):
        g = dict(f)
        g.setdefault('by', 'decision')
        found.append(g)
    rank = {'critical': 0, 'major': 1, 'minor': 2}
    found.sort(key=lambda f: (rank.get(f['severity'], 3), f.get('order', 999)))
    for i, f in enumerate(found, 1):
        f['n'] = i
        f['label'] = f'{i} — {SEV.get(f["severity"], f["severity"])}'
    w.save('findings.json', found)
    say(f'{len(found)} ملاحظة: ' + '، '.join(f'{sum(1 for f in found if f["severity"] == s)} {SEV[s]}' for s in ('critical', 'major', 'minor'))
        + f' · منها {sum(1 for f in found if f["by"] == "program")} وجدها البرنامج بنفسه')
    return found
