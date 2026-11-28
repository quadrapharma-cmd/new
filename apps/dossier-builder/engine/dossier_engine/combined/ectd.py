"""Stage 8 — the eCTD v3.2.2 sequence (Egypt's provisional regional profile v0) and its validation.

From the plan's documents: Modules 2–5 as leaves of index.xml (ICH App. 4 folders and names; the element chain read from the
ICH DTD; the attributes a heading needs — substance, manufacturer, product, dosage form, excipient, indication), Module 1 as
eg-regional.xml (the envelope; the cover letter and tracking table written here; the product information from the corrections
stage; mock-ups, specimens, experts, GMO and clinical-trial pages taken from a Module 1 received in the EU layout, without its
heading-only pages). Left out, as Egypt's draft asks (EG-BP-E24): the tables of contents (the XML is the table of contents) and
the documents that only say «not applicable», «none» or «----». A document shared by several drug substances is stored once and
referenced from each. A Quality Overall Summary that reproduces Module 3 pages (five or more in a row) gets one cross-reference
page in their place. Every PDF is written linearised at PDF 1.4 or later; util/ is the profile's own; MD5 checksums.
What the dossier decides (the envelope, the names, the attributes, a title or a file name, a document left out or kept) is in
dossier.json → ectd. Then validate.py checks the sequence; ectd.json and validation.json are written."""
import csv
import datetime
import json
import re
import shutil
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import pikepdf

from . import validate
from .common import APP4, FONTS, PROFILE_EG, Work, md5_file, parse_ranges, say

EG_PDF = '1.4'
S_FILES = {
    '3.2.S.1.1': ('32s1-gen-info', 'nomenclature'), '3.2.S.1.2': ('32s1-gen-info', 'structure'), '3.2.S.1.3': ('32s1-gen-info', 'general-properties'),
    '3.2.S.2.1': ('32s2-manuf', 'manufacturer'), '3.2.S.2.2': ('32s2-manuf', 'manuf-process-and-controls'),
    '3.2.S.2.3': ('32s2-manuf', 'control-of-materials'), '3.2.S.2.4': ('32s2-manuf', 'control-critical-steps'),
    '3.2.S.2.5': ('32s2-manuf', 'process-validation'), '3.2.S.2.6': ('32s2-manuf', 'manuf-process-development'),
    '3.2.S.3.1': ('32s3-charac', 'elucidation-of-structure'), '3.2.S.3.2': ('32s3-charac', 'impurities'),
    '3.2.S.4.1': ('32s4-contr-drug-sub/32s41-spec', 'specification'), '3.2.S.4.2': ('32s4-contr-drug-sub/32s42-analyt-proc', 'analytical-procedures'),
    '3.2.S.4.3': ('32s4-contr-drug-sub/32s43-val-analyt-proc', 'validation-analyt-procedures'),
    '3.2.S.4.4': ('32s4-contr-drug-sub/32s44-batch-analys', 'batch-analyses'), '3.2.S.4.5': ('32s4-contr-drug-sub/32s45-justif-spec', 'justification-of-specification'),
    '3.2.S.5': ('32s5-ref-stand', 'reference-standards'), '3.2.S.6': ('32s6-cont-closure-sys', 'container-closure-system'),
    '3.2.S.7.1': ('32s7-stab', 'stability-summary'), '3.2.S.7.2': ('32s7-stab', 'postapproval-stability'), '3.2.S.7.3': ('32s7-stab', 'stability-data'),
}
P_FILES = {
    '3.2.P.1': ('32p1-desc-comp', 'description-and-composition'),
    '3.2.P.2.1': ('32p2-pharm-dev', 'pharm-dev-components'), '3.2.P.2.2': ('32p2-pharm-dev', 'pharm-dev-drug-product'),
    '3.2.P.2.3': ('32p2-pharm-dev', 'pharm-dev-manuf-process'), '3.2.P.2.4': ('32p2-pharm-dev', 'pharm-dev-container-closure'),
    '3.2.P.2.5': ('32p2-pharm-dev', 'pharm-dev-microbiological'), '3.2.P.2.6': ('32p2-pharm-dev', 'pharm-dev-compatibility'),
    '3.2.P.3.1': ('32p3-manuf', 'manufacturers'), '3.2.P.3.2': ('32p3-manuf', 'batch-formula'), '3.2.P.3.3': ('32p3-manuf', 'manuf-process-and-controls'),
    '3.2.P.3.4': ('32p3-manuf', 'control-critical-steps'), '3.2.P.3.5': ('32p3-manuf', 'process-validation'),
    '3.2.P.4.1': ('32p4-contr-excip/excipients', 'specifications'), '3.2.P.4.2': ('32p4-contr-excip/excipients', 'analytical-procedures'),
    '3.2.P.4.3': ('32p4-contr-excip/excipients', 'validation-analyt-procedures'), '3.2.P.4.4': ('32p4-contr-excip/excipients', 'justification-of-specifications'),
    '3.2.P.4.5': ('32p4-contr-excip', 'excipients-human-animal'), '3.2.P.4.6': ('32p4-contr-excip', 'novel-excipients'),
    '3.2.P.5.1': ('32p5-contr-drug-prod/32p51-spec', 'specifications'), '3.2.P.5.2': ('32p5-contr-drug-prod/32p52-analyt-proc', 'analytical-procedures'),
    '3.2.P.5.3': ('32p5-contr-drug-prod/32p53-val-analyt-proc', 'validation-analytical-procedures'),
    '3.2.P.5.4': ('32p5-contr-drug-prod/32p54-batch-analys', 'batch-analyses'), '3.2.P.5.5': ('32p5-contr-drug-prod/32p55-charac-imp', 'characterisation-impurities'),
    '3.2.P.5.6': ('32p5-contr-drug-prod/32p56-justif-spec', 'justification-of-specifications'),
    '3.2.P.6': ('32p6-ref-stand', 'reference-standards'), '3.2.P.7': ('32p7-cont-closure-sys', 'container-closure-system'),
    '3.2.P.8.1': ('32p8-stab', 'stability-summary'), '3.2.P.8.2': ('32p8-stab', 'postapproval-stability'), '3.2.P.8.3': ('32p8-stab', 'stability-data'),
}
M2_FILES = {'2.2': ('m2/22-intro', 'introduction', '2.2 Introduction'), '2.3': ('m2/23-qos', 'introduction', '2.3 Introduction'),
            '2.3.P': ('m2/23-qos', 'drug-product', '2.3.P Drug product'), '2.4': ('m2/24-nonclin-over', 'nonclinical-overview', '2.4 Nonclinical overview'),
            '2.5': ('m2/25-clin-over', 'clinical-overview', '2.5 Clinical overview'),
            '2.6': ('m2/26-nonclin-sum', 'nonclinical-summaries', '2.6 Nonclinical written and tabulated summaries'),
            '2.7': ('m2/27-clin-sum', 'clinical-summary', '2.7 Clinical summary')}
# a Module 1 received in the EU layout → Egypt's elements (the EG draft follows the EU Module 1)
EU_TO_EG = {'1.3.2': ('m1-3-2-mockup', '13-pi/132-mockup/mockup.pdf'), '1.3.3': ('m1-3-3-specimen', '13-pi/133-specimen/specimen.pdf'),
            '1.4.1': ('m1-4-1-quality', '14-expert/141-quality/quality.pdf'),
            '1.4.2': ('m1-4-2-non-clinical', '14-expert/142-nonclinical/nonclinical.pdf'),
            '1.4.3': ('m1-4-3-clinical', '14-expert/143-clinical/clinical.pdf'),
            '1.6': ('m1-6-2-gmo', '16-environrisk/162-gmo/gmo.pdf'), '1.9': ('m1-9-clinical-trials', '19-clinical-trials/clinicaltrials.pdf')}
NA = re.compile(r'not\s+applicable|\bno\s+(?:\w+\s+){0,3}(?:studies|study)\s+(?:(?:have|has)\s+been|are|is|were|was)\s+'
                r'(?:performed|conducted|done|carried\s+out|available)(?:\s+so\s+far)?|\bno\s+novel\s+excipients?\b|\bnone\s+(?:performed|available)\b', re.I)


def slug(s, n=60):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:n].strip('-') or 'document'



COMPANY_WORDS = {'of', 'the', 'and', 'ltd', 'limited', 'inc', 'co', 'company', 'corp', 'corporation', 'gmbh', 'ag', 'sa', 'llc',
                 'plc', 'pvt', 'private', 'kg', 'bv', 'nv', 'spa', 'srl', 'sas'}


def without_maker(stem, maker, name=''):
    """A drug substance's folder is «substance-manufacturer» (ICH M2, Appendix 4); its 2.3.S file names the substance only. The
    manufacturer's part is dropped when the folder ends with it: the short name the dossier writes after the substance
    («Zentorine (EP)»), or the manufacturer's name before its address, its first word or its initials («example pharma ltd.,
    some city» gives «example-pharma», «example» and «ep»)."""
    marks = []
    short = re.search(r'\(([A-Z][A-Za-z]{1,7})\)\s*$', name or '')
    if short:
        marks.append(short.group(1).lower())
    words = [w for w in re.findall(r'[a-z0-9]+', (maker or '').split(',')[0].lower()) if w not in COMPANY_WORDS]
    if words:
        marks += ['-'.join(words), words[0], ''.join(w[0] for w in words)]
    for mark in marks:
        if len(mark) >= 2 and stem.endswith('-' + mark) and len(stem) > len(mark) + 1:
            return stem[:-len(mark) - 1]
    return stem

class Dtd:
    def __init__(self, profile):
        text = (profile / 'util' / 'dtd' / 'ich-ectd-3-2.dtd').read_text(encoding='utf-8')
        elems = re.findall(r'<!ELEMENT\s+([\w:-]+)\s+(.*?)>', text, re.S)
        self.names = [n for n, _ in elems]
        self.model = {n: re.findall(r'[\w:-]+', m) for n, m in elems}
        self.attlist = {}
        for name, body in re.findall(r'<!ATTLIST\s+([\w:-]+)\s+(.*?)>', text, re.S):
            self.attlist[name] = set(re.findall(r'^\s*([\w:-]+)\s+CDATA', body, re.M))
        eg = (profile / 'util' / 'dtd' / 'eg-regional.dtd').read_text(encoding='utf-8')
        self.eg_model = {n: re.findall(r'[\w:-]+', m) for n, m in re.findall(r'<!ELEMENT\s+([\w:-]+)\s+(.*?)>', eg, re.S)}

    def elem(self, code):
        """CTD number → ICH element name (3.2.S.4.4 → m3-2-s-4-4-batch-analyses)."""
        special = {'2': 'm2-common-technical-document-summaries', '3': 'm3-quality', '4': 'm4-nonclinical-study-reports',
                   '5': 'm5-clinical-study-reports', '2.3.intro': 'm2-3-introduction', '2.3': 'm2-3-quality-overall-summary',
                   '3.2': 'm3-2-body-of-data', '4.2': 'm4-2-study-reports', '5.3': 'm5-3-clinical-study-reports'}
        if code in special:
            return special[code]
        pre = 'm' + code.lower().replace('.', '-') + '-'
        c = [n for n in self.names if n.startswith(pre) and not n[len(pre)].isdigit() and not re.match(r'[a-z]-', n[len(pre):])]
        if len(c) != 1:
            raise ValueError(f'CTD {code}: {c}')
        return c[0]

    @staticmethod
    def chain(code):
        if code == '2.3.intro':
            return ['2', '2.3', '2.3.intro']
        parts = code.split('.')
        return ['.'.join(parts[:i]) for i in range(1, len(parts) + 1)]


def app4():
    folders, files = {}, {}
    if APP4.exists():
        for r in csv.DictReader(open(APP4, encoding='utf-8')):
            if r['kind'] == 'D' and r['ctd']:
                folders.setdefault(r['ctd'], r['path'])
            elif r['kind'] == 'F' and r['ctd']:
                files.setdefault(r['ctd'], r['path'])
    return folders, files


# ------------------------------------------------------------------ PDFs written here (reportlab, fonts embedded)
def styles():
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    # the program's own copies (vendor/fonts: the same files as Debian's fonts-liberation), so that a Mac writes the same PDFs
    pdfmetrics.registerFont(TTFont('LS', str(FONTS / 'LiberationSans-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('LSB', str(FONTS / 'LiberationSans-Bold.ttf')))
    return {
        'n': ParagraphStyle('n', fontName='LS', fontSize=10.5, leading=14.5, spaceAfter=6),
        's': ParagraphStyle('s', fontName='LS', fontSize=8.5, leading=11, textColor=colors.HexColor('#555555'), spaceAfter=4),
        'h': ParagraphStyle('h', fontName='LSB', fontSize=13, leading=17, spaceAfter=10),
        'b': ParagraphStyle('b', fontName='LSB', fontSize=10.5, leading=14.5, spaceAfter=6),
        't': ParagraphStyle('t', fontName='LS', fontSize=9, leading=11.5),
        'tb': ParagraphStyle('tb', fontName='LSB', fontSize=9, leading=11.5)}


def make_pdf(path, story, title, author, creator):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
                            title=title, author=author, creator=creator)
    doc.build(story)


def table(rows, widths, S, head=True):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle
    t = Table([[Paragraph(escape(str(c)), S['tb'] if (head and i == 0) else S['t']) for c in r] for i, r in enumerate(rows)], colWidths=widths)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#9aa5b1')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3e8ef') if head else colors.white),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
    return t


class Builder:
    def __init__(self, w):
        self.w = w
        self.dec = w.decisions()
        self.E = self.dec.get('ectd') or {}
        self.plan = w.load('plan.json')
        self.docs = self.plan['docs']
        self.by_path = {d['path']: d for d in self.docs}
        self.folder = w.ctd / (self.dec.get('ctd_folder') or 'CTD')
        self.fixed = (w.load('fixed.json', {}) or {}).get('docs', {})
        self.pi = (w.load('fixed.json', {}) or {}).get('pi', [])
        self.built = w.load('built.json', []) or []          # what the build stage wrote for a missing item (build.py)
        self.built_out = []
        self.gen = w.ectd / 'generated'
        self.out_root = w.ectd / 'out'
        self.seq_dir = self.out_root / self._env()['sequence']
        self.dtd = Dtd(PROFILE_EG)
        self.folders, self.files = app4()
        self.text = w.pages_text('read/text.txt')
        ocr = w.pages_text('read/ocr.txt')
        self.ocr = ocr if len(ocr) == len(self.text) else self.text
        self.header = set(self.E.get('running_header') or self._header())
        self.leaves, self.left_out, self.m1 = [], {}, []
        today = self.E.get('today')
        self.today = datetime.date.fromisoformat(today) if today else datetime.date.today()
        self.S = styles()
        self.gaps = []

    def _env(self):
        e = dict(self.E.get('envelope') or {})
        e.setdefault('sequence', '0000')
        e.setdefault('related', e['sequence'])
        return e

    def _header(self):
        from collections import Counter
        c = Counter()
        for t in self.text:
            for l in set(x.strip() for x in t.splitlines()[:6] if x.strip()):
                c[' '.join(l.split())] += 1
        n = max(1, len(self.text))
        return [l for l, k in c.items() if k >= 0.05 * n and len(l) > 3 and not re.match(r'^\(?\s*\d\.\d', l)]

    # -- what a document says
    def body(self, pages):
        out = []
        for p in pages:
            t = self.text[p - 1] if len(self.text[p - 1].strip()) >= 30 else self.ocr[p - 1]
            lines = [' '.join(l.split()) for l in t.splitlines() if l.strip()]
            out += [l for l in lines if l not in self.header]
        return ' '.join(out)

    HEADING = re.compile(r'^\(?\s*(?:Module\s*)?\d(?:\.\s?\d+|\.\s?[SPAR])+\.?(?:\s*[-–:]?\s*[A-Z(][A-Za-z ,&/()\-–]{0,90}:?)?$')

    def content_lines(self, pages, title=''):
        """A document's lines without the running header, its CTD headings (a number, with or without its title), its title
        repeated, page numbers and rules («____»)."""
        tw = {w.lower() for w in re.findall(r'[A-Za-z]{2,}', title)}
        out = []
        for p in pages:
            t = self.text[p - 1] if len(self.text[p - 1].strip()) >= 30 else self.ocr[p - 1]
            for l in t.splitlines():
                l = ' '.join(l.split())
                if not l or l in self.header or re.fullmatch(r'[_\\]{1,}|_{3,}', l) or re.fullmatch(r'\d{1,3}', l):
                    continue
                if self.HEADING.match(l):
                    continue                                                # «4.2.3.7.1 Antigenicity», «3.2.A.3 – Excipients:», «4.3»
                words = {w.lower() for w in re.findall(r'[A-Za-z]{2,}', l)}
                if words and words <= tw and len(words) <= 8:
                    continue                                                # the title again («Literature References»)
                out.append(l)
        return out

    def statement_only(self, d):
        """A document that only says «not applicable», «no studies are available» or «----», with no justification after it
        (EG-BP-E24). A document that points to another section is a cross-reference, and is kept."""
        if len(d['pages']) > 2:
            return None
        rest = ' '.join(self.content_lines(d['pages'], d.get('title', '')))
        if len(rest) > 700:
            return None
        if re.fullmatch(r'[\s\-–—_]*', rest) and re.search(r'-{3,}', rest):
            return 'empty («----»)'
        if not rest.strip():
            return 'a heading only'
        m = NA.search(rest)
        if m and len(re.findall(r'[A-Za-z]{2,}', rest[m.end():])) < 15:
            said = m.group(0)
            return f'«{said[0].upper() + said[1:]}» only'
        return None                                                         # a pointer to another section is a cross-reference: kept

    def heading_only(self, p, key='', title=''):
        """A typed page of a Module 1 document that holds only its heading, a «not applicable», or one sentence saying that
        something «is enclosed in the following pages»: left out when the document goes into Egypt's Module 1."""
        if len(self.text[p - 1].strip()) < 1:
            return False                                                    # a picture (a mock-up, a scanned page): content
        lines = self.content_lines([p], title)
        if not lines:
            return True
        rest = ' '.join(lines)
        if NA.fullmatch(rest.strip(' .')):
            return True
        return len(lines) <= 2 and bool(re.fullmatch(r'[^.]{0,120}\benclosed in the following pages?\.?', rest, re.I))

    def title_of(self, d):
        t = d['title']
        for name in (self.dec.get('names') or {}).get('substances', {}).values():
            t = t.replace(f' ({name})', '')
        return t.replace('–', '-')

    # -- the leaves of Modules 2–5
    def add(self, code, folder, file, title, source, attrs=None, pages=None, note='', doc=None):
        self.leaves.append({'code': code, 'folder': folder, 'file': file, 'title': title, 'source': str(source), 'attrs': attrs or {},
                            'pages': pages, 'note': note, 'doc': doc})

    def source_of(self, d):
        f = self.fixed.get(d['path'])
        if f:
            return Path(f['pdf']), f.get('note', '')
        return self.folder / d['path'], ''

    def decide_left_out(self):
        keep = set(self.E.get('keep_in') or [])
        for d in self.docs:
            if d['path'].startswith('Module 1') or d['path'] in keep:
                continue
            if d['ctd'] in ('2.1', '3.1', '4.1', '5.1'):
                self.left_out[d['path']] = 'table of contents: the eCTD XML replaces it'
                continue
            why = self.statement_only(d)
            if why:
                self.left_out[d['path']] = why
        for path, why in (self.E.get('left_out') or {}).items():
            self.left_out[path] = why

    def build_leaves(self):
        E = self.E
        manuf = E.get('manufacturer', '')
        product = E.get('product') or {}
        subst = E.get('substances') or {}
        names = (self.dec.get('names') or {})
        order = list(subst) or list((names.get('substances') or {}).values())
        over = E.get('leaves') or {}
        common = [d for d in self.docs if '/3.2.S Common to the ' in d['path']]

        def leaf(d, code, folder, file, title, attrs, note=''):
            o = over.get(d['path'], {})
            src, fnote = self.source_of(d)
            if o.get('source'):
                src = self.w.root / o['source']
            self.add(o.get('code', code), o.get('folder', folder), o.get('file', file), o.get('title', title), src, attrs,
                     d['pages'], (o.get('note') or fnote or note), d['path'])
        # Module 2
        qos = self.make_qos() if E.get('qos_xref', True) else {}
        for d in sorted((d for d in self.docs if d['path'].startswith('Module 2/')), key=lambda d: d['pages'][0]):
            if d['path'] in self.left_out:
                continue
            c = d['ctd']
            if c == '2.3.S':
                name = next((n for n in order if d['path'].endswith(f'2.3.S {n}.pdf')), None)
                s = subst.get(name, {})
                stem = s.get('folder', slug(name or 'substance'))
                attrs = {'2.3.S': {'substance': s.get('substance', (name or '').lower()), 'manufacturer': manuf}}
                src = qos.get(d['path'])
                leaf(d, '2.3.S', 'm2/23-qos', f"drug-substance-{without_maker(stem, s.get('manufacturer') or manuf, name or '')}.pdf",
                     f"2.3.S Drug substance - {attrs['2.3.S']['substance']}", attrs)
                if src:
                    self.leaves[-1]['source'] = str(src)
                continue
            code = '2.3.intro' if c == '2.3' else c
            folder, file, title = M2_FILES.get(c, (f'm2/{slug(c)}', slug(d['title']), d['title']))
            attrs = {'2.3.P': product} if c == '2.3.P' else {}
            leaf(d, code, folder, file + '.pdf', title, attrs)
            if d['path'] in qos:
                self.leaves[-1]['source'] = str(qos[d['path']])
        # Module 3: the drug substances in their order, each with the shared documents after its own of the same number
        first_folder = {}
        for name in order:
            s = subst.get(name, {})
            base = f"m3/32-body-data/32s-drug-sub/{s.get('folder', slug(name))}"
            attrs = {'3.2.S': {'substance': s.get('substance', name.lower()), 'manufacturer': manuf}}
            mine = sorted([d for d in self.docs if d['path'].startswith(f'Module 3/3.2.S {name}/')], key=lambda d: d['pages'][0])
            for d in mine:
                if d['path'] in self.left_out:
                    continue
                sub, fname = S_FILES[d['ctd']]
                leaf(d, d['ctd'], f'{base}/{sub}', f'{fname}.pdf', self.title_of(d), attrs)
                for c in [c for c in common if c['ctd'] == d['ctd']]:
                    o = over.get(c['path'], {})
                    where = first_folder.setdefault(c['path'], o.get('folder', f'{base}/{sub}'))
                    src, fnote = self.source_of(c)
                    self.add(c['ctd'], where, o.get('file', self.shared_file(c, fname)), o.get('title', self.title_of(c)), src, attrs,
                             c['pages'], o.get('note', 'shared file'), c['path'])
        pslug = E.get('product_folder', slug(names.get('product') or 'product'))
        for d in sorted((d for d in self.docs if d['path'].startswith('Module 3/3.2.P ')), key=lambda d: d['pages'][0]):
            if d['path'] in self.left_out or d['path'] in [c['path'] for c in common]:
                continue
            code = '3.2.P.2' if d['ctd'].startswith('3.2.P.2.') else d['ctd']
            sub, fname = P_FILES[d['ctd']]
            attrs = {'3.2.P': product}
            if code.startswith('3.2.P.4'):
                attrs['3.2.P.4'] = {'excipient': E.get('excipient', 'all excipients')}
            leaf(d, code, f'm3/32-body-data/32p-drug-prod/{pslug}/{sub}', f'{fname}.pdf', self.title_of(d), attrs)
        for d in sorted((d for d in self.docs if d['path'].startswith('Module 3/') and d['ctd'] in ('3.2.A.1', '3.2.A.2', '3.2.A.3', '3.2.R', '3.3')),
                        key=lambda d: d['pages'][0]):
            if d['path'] in self.left_out:
                continue
            c = d['ctd']
            if c == '3.2.A.1':
                leaf(d, c, 'm3/32-body-data/32a-app/32a1-fac-equip', 'facilities-and-equipment.pdf', self.title_of(d), {'3.2.A.1': {'manufacturer': manuf}})
            elif c == '3.2.A.2':
                leaf(d, c, 'm3/32-body-data/32a-app/32a2-advent-agent', 'adventitious-agents.pdf', self.title_of(d),
                     {'3.2.A.2': {'product-name': product.get('product-name', ''), 'dosageform': product.get('dosageform', ''), 'manufacturer': manuf}})
            elif c == '3.2.A.3':
                leaf(d, c, 'm3/32-body-data/32a-app/32a3-excip', 'novel-excipients.pdf', self.title_of(d), {'3.2.A.3': {'excipient': E.get('excipient', 'all excipients')}})
            elif c == '3.2.R':
                leaf(d, c, 'm3/32-body-data/32r-reg-info', 'regional-information.pdf', self.title_of(d), {})
            else:
                leaf(d, c, 'm3/33-lit-ref', slug(re.sub(r'^\d(?:\.\d+)*\s+', '', d['title'])) + '.pdf', self.title_of(d), {})
        # Modules 4 and 5
        ind = E.get('indication', '')
        islug = E.get('indication_folder', slug(ind, 30) if ind else 'indication-1')
        from .ctdnames import order as ctd_order                            # Module 4 before Module 5, each in its CTD order
        for d in sorted((d for d in self.docs if d['path'].startswith(('Module 4/', 'Module 5/'))),
                        key=lambda d: (ctd_order(d['ctd']), d['pages'][0])):
            if d['path'] in self.left_out:
                continue
            c = d['ctd']
            folder = self.folders.get(c, f'm{c[0]}/{slug(c)}').replace('indication-1', islug)
            fname = Path(self.files[c]).name if c in self.files else slug(re.sub(r'^\d(?:\.\d+)*\s+', '', d['title'])) + '.pdf'
            attrs = {'5.3.5': {'indication': ind}} if c.startswith('5.3.5') else {}
            if c.startswith('5.3.5.') and c not in ('5.3.5.3',):
                folder += '/' + slug(re.sub(r'^\d(?:\.\d+)*\s+', '', d['title']), 30)        # one folder a study
                fname = slug(re.sub(r'^\d(?:\.\d+)*\s+', '', d['title']), 40) + '.pdf'
            leaf(d, c, folder, fname, self.title_of(d), attrs)
        # what the build stage wrote for a missing item of Modules 2–5 (build.py), at its heading
        for b in (x for x in self.built if not x['node'].startswith('1.')):
            c = b['node']
            folder = self.folders.get(c)
            if not folder:
                self.built_out.append({'item': b['item'], 'node': c, 'why': 'no eCTD folder for this heading'})
                continue
            attrs = {}
            if c.startswith('3.2.S'):                    # a substance's own: in its folder, with its substance and manufacturer
                name = b.get('substance') or (order[0] if order else None)
                s = subst.get(name, {}) if name else {}
                own = f"m3/32-body-data/32s-drug-sub/{s.get('folder', slug(name or 'substance'))}"
                folder = own if c == '3.2.S' else folder.replace('m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1', own)
                attrs = {'3.2.S': {'substance': s.get('substance', (name or '').lower()), 'manufacturer': manuf}}
            elif '/32p-drug-prod/' in folder:
                folder = folder.replace('product-1', pslug)
                attrs = {'3.2.P': product}
            elif c == '2.3.P':
                attrs = {'2.3.P': product}
            self.add(c, folder.replace('indication-1', islug), slug(b['title']) + '.pdf', b['title'], Path(b['pdf']), attrs, [],
                     'written by the program for a missing item (build stage)', None)

    def shared_file(self, c, fname):
        m = re.search(r'Annexure\s+(\d+)(?:\s*\(part\s+(\d+)\s+of\s+\d+\))?', c['title'], re.I)
        if m:
            return f"{fname}-annex{m.group(1)}" + (f"-part{m.group(2)}" if m.group(2) else '') + '.pdf'
        return f'{fname}-{slug(c["title"], 30)}.pdf'

    # -- the Quality Overall Summary: pages copied from Module 3 replaced by a cross-reference
    def make_qos(self):
        from reportlab.platypus import Paragraph, Spacer
        groups = (self.w.load('repeats.json') or {}).get('identical_groups', [])
        where = {}
        for d in self.docs:
            for i, p in enumerate(d['pages']):
                where[p] = (d, i + 1)
        twin = {}
        for g in groups:
            m3 = sorted(p for p in g if p in where and where[p][0]['ctd'].startswith('3.'))
            for p in g:
                if m3 and p in where and where[p][0]['ctd'].startswith('2.3'):
                    twin[p] = m3[0]
        out = {}
        self.qos_runs = {}
        for d in self.docs:
            if not d['ctd'].startswith('2.3') or d['path'] in self.left_out:
                continue
            runs, cur = [], None
            for p in d['pages']:
                t = twin.get(p)
                if t is not None and cur and p == cur['q2'] + 1 and t == cur['m2'] + 1 and where[t][0]['path'] == where[cur['m1']][0]['path']:
                    cur['q2'], cur['m2'] = p, t
                    continue
                cur = {'q1': p, 'q2': p, 'm1': t, 'm2': t} if t is not None else None
                if cur:
                    runs.append(cur)
            runs = [r for r in runs if r['q2'] - r['q1'] + 1 >= 5]
            if not runs:
                continue
            self.qos_runs[d['path']] = runs
            src_path, _ = self.source_of(d)
            src = pikepdf.open(src_path)
            new = pikepdf.new()
            xref = {}
            a = d['pages'][0]
            name = re.sub(r'\s*\([^()]*\)$', '', Path(d['path']).stem)                # «2.3.S Zentorine bulk»
            for r in runs:
                md, i1 = where[r['m1']]
                i2 = where[r['m2']][1]
                tmp = self.gen / f"xref-{r['q1']}.pdf"
                at = self.planned_place(md)
                make_pdf(tmp, [Paragraph(f'{escape(name)} - cross-reference to Module 3', self.S['h']),
                               Paragraph(f"Pages {d['pages'].index(r['q1']) + 1} to {d['pages'].index(r['q2']) + 1} of the summary as first written reproduced "
                                         f"{r['q2'] - r['q1'] + 1} pages of Module 3, {escape(md['ctd'])} «{escape(self.title_of(md))}». They are not repeated here: "
                                         'the Quality Overall Summary summarises Module 3 and does not duplicate it (ICH M4Q).', self.S['n']),
                               Paragraph(f"See Module 3, {escape(md['ctd'])}: file {escape(at)}, pages {i1} to {i2}.", self.S['n']),
                               Spacer(1, 12), Paragraph('Page placed by the applicant in place of the reproduced pages.', self.S['s'])],
                         'Cross-reference', self._env().get('applicant', ''), 'eCTD publishing')
                xref[r['q1']] = (r, pikepdf.open(tmp))
            i = 0
            pages = d['pages']
            while i < len(pages):
                p = pages[i]
                if p in xref:
                    r, x = xref[p]
                    new.pages.extend(x.pages)
                    i = pages.index(r['q2']) + 1
                    continue
                new.pages.append(src.pages[i])
                i += 1
            with new.open_outline() as ol:
                ol.root.append(pikepdf.OutlineItem(name, 0))
            new.Root.PageMode = pikepdf.Name.UseOutlines
            dst = self.gen / ('qos-' + slug(Path(d['path']).stem) + '.pdf')
            new.save(dst)
            out[d['path']] = dst
        return out

    def planned_place(self, md):
        """Where a Module 3 document will sit in the sequence (its folder and file), for a cross-reference page."""
        subst = self.E.get('substances') or {}
        for name, s in subst.items():
            if md['path'].startswith(f'Module 3/3.2.S {name}/') and md['ctd'] in S_FILES:
                sub, fname = S_FILES[md['ctd']]
                return f"m3/32-body-data/32s-drug-sub/{s.get('folder', slug(name))}/{sub}/{fname}.pdf"
        if md['ctd'] in P_FILES:
            sub, fname = P_FILES[md['ctd']]
            pslug = self.E.get('product_folder', slug((self.dec.get('names') or {}).get('product') or 'product'))
            return f'm3/32-body-data/32p-drug-prod/{pslug}/{sub}/{fname}.pdf'
        return md['path']

    # -- Module 1 (EG)
    def build_m1(self):
        E = self.E
        env = self._env()
        self.make_tracking(env)
        self.m1.append(('m1-0-cover', None, '10-cover/cover.pdf', 'Cover letter for sequence ' + env['sequence'], self.gen / 'cover.pdf', None, None))
        self.m1.append(('m1-0-cover', None, '10-cover/tracking.pdf', 'Tracking table', self.gen / 'tracking.pdf', None, None))
        for p in self.pi:
            self.m1.append(('m1-3-1-spc-label-pl', {'xml:lang': p['lang'], 'type': p['type'], 'country': 'eg'},
                            f"13-pi/131-spclabelpl/{p['lang']}/{p['type']}.pdf", p['title'], Path(p['pdf']), None, None))
        over = {x['from']: x for x in (E.get('m1') or []) if x.get('from')}
        for d in sorted((d for d in self.docs if d['path'].startswith('Module 1')), key=lambda d: d['pages'][0]):
            if d['ctd'] not in EU_TO_EG:
                continue
            o = over.get(d['path'], {})
            if o.get('skip'):
                continue
            keep = parse_ranges(o['keep']) if o.get('keep') else [p for p in d['pages'] if not self.heading_only(p, d['ctd'], d['title'])]
            if not keep or self.statement_only({'pages': keep, 'ctd': d['ctd']}):
                continue
            el, href = EU_TO_EG[d['ctd']]
            self.m1.append((o.get('element', el), None, o.get('href', href), o.get('title', self.title_of(d).split(' ', 1)[1]),
                            self.folder / d['path'], keep, d['path']))
        from ..writers.ectd32 import Profile32
        rows = Profile32(PROFILE_EG).m1
        for b in (x for x in self.built if x['node'].startswith('1.')):
            row = rows.get(b['node'])
            if not row or not row.get('directory', '').startswith('m1/eg/'):
                self.built_out.append({'item': b['item'], 'node': b['node'], 'why': 'no EG Module 1 element for this node'})
                continue
            href = f"{row['directory'][len('m1/eg/'):]}/{slug(b['title'])}.pdf"
            self.m1.append((row['element'], None, href, b['title'], Path(b['pdf']), None, None))
        content = E.get('cover', {}).get('content') or self.default_content()
        self.make_cover(env, content)

    def default_content(self):
        mods = {}
        for l in self.leaves:
            mods.setdefault(l['code'][0], []).append(l['title'])
        out = ['Module 1 (EG): cover letter, tracking table' + (', proposed product information' if self.pi else '')]
        names = {'2': 'Module 2: summaries', '3': 'Module 3: quality data', '4': 'Module 4: nonclinical study reports', '5': 'Module 5: clinical study reports'}
        out += [names[m] for m in sorted(mods) if m in names]
        return out

    def make_tracking(self, env):
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer
        S = self.S
        rows = [['Sequence', 'Related sequence', 'Submission type', 'Submission unit', 'Description', 'Date', 'EDA tracking number'],
                [env['sequence'], env['related'], {'maa': 'maa - Marketing Authorisation Application'}.get(env.get('submission_type'), env.get('submission_type', '')),
                 env.get('unit', ''), env.get('description', ''), self.today.strftime('%d/%m/%Y') + ' (prepared)', env.get('tracking') or 'to be given by EDA']]
        make_pdf(self.gen / 'tracking.pdf', [Paragraph('Tracking table', S['h']),
                                             Paragraph(escape(env.get('invented_name', '')) + ' - ' + escape(env.get('applicant', '')), S['n']), Spacer(1, 6),
                                             table(rows, [16 * mm, 16 * mm, 28 * mm, 16 * mm, 52 * mm, 20 * mm, 18 * mm], S)],
                 'Tracking table', env.get('applicant', ''), 'eCTD publishing')

    def make_cover(self, env, content):
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer
        S = self.S
        c = self.E.get('cover') or {}
        story = [Paragraph(self.today.strftime('%d %B %Y'), S['n']), Spacer(1, 4),
                 Paragraph('To: ' + escape(c.get('to', 'Egyptian Drug Authority (EDA)')), S['n']), Spacer(1, 4),
                 Paragraph('Subject: ' + c.get('subject_html', escape(c.get('subject', f"eCTD sequence {env['sequence']} - {env.get('description', '')}"))), S['n']),
                 Spacer(1, 6), Paragraph('Dear Sir / Madam,', S['n']),
                 Paragraph(escape(c.get('opening', f"Please find enclosed eCTD sequence {env['sequence']}. The sequence follows the ICH eCTD specification v3.2.2 and "
                                    'the EG Module 1 eCTD specification (draft v1.0).')) + ' Its universally unique identifier is ' + env.get('identifier', '') + '.', S['n'])]
        if c.get('product'):
            story += [Paragraph('Product', S['b']), table(c['product'], [55 * mm, 111 * mm], S, head=False)]
        story += [Spacer(1, 6), Paragraph('Content of this sequence', S['b'])]
        story += [Paragraph('• ' + escape(x), S['n']) for x in content]
        story += [Spacer(1, 10), Paragraph('Yours faithfully,', S['n']), Spacer(1, 26),
                  Paragraph('Name, title and signature of the authorised person of the applicant', S['s']),
                  Paragraph(escape(env.get('applicant', '')), S['n'])]
        make_pdf(self.gen / 'cover.pdf', story, 'Cover letter for sequence ' + env['sequence'], env.get('applicant', ''), 'eCTD publishing')

    # -- writing
    def put_pdf(self, src, dst, keep_pages=None, title=None):
        dst.parent.mkdir(parents=True, exist_ok=True)
        pdf_in = pikepdf.open(src)
        if keep_pages is not None:
            out = pikepdf.new()
            out.pages.extend(pdf_in.pages[i] for i in keep_pages)
            with out.open_outline() as ol:
                ol.root.append(pikepdf.OutlineItem(title or 'Document', 0))
            out.Root.PageMode = pikepdf.Name.UseOutlines
            pdf_in = out
        if title:
            pdf_in.docinfo['/Title'] = title
        with pdf_in.open_outline() as ol:
            has = len(ol.root) > 0
        if has:
            pdf_in.Root.PageMode = pikepdf.Name.UseOutlines
        elif '/PageMode' in pdf_in.Root:
            del pdf_in.Root['/PageMode']
        pdf_in.save(dst, linearize=True, min_version=EG_PDF)

    def write(self):
        if self.out_root.exists():
            shutil.rmtree(self.out_root)
        m1_leaves = []
        for n, (el, pidoc, href, title, src, keep, path) in enumerate(self.m1, 1):
            dst = self.seq_dir / 'm1' / 'eg' / href
            idx = None
            if keep is not None:
                d = self.by_path[path]
                idx = [d['pages'].index(p) for p in keep]
            self.put_pdf(src, dst, idx, title)
            m1_leaves.append((el, pidoc, href, title, md5_file(dst), f'eg-m1-{n:02d}', str(src), keep))
        written = {}
        for n, l in enumerate(self.leaves, 1):
            rel = f"{l['folder']}/{l['file']}"
            if rel not in written:
                self.put_pdf(Path(l['source']), self.seq_dir / rel, title=l['title'])
                written[rel] = md5_file(self.seq_dir / rel)
            l['href'], l['md5'], l['id'] = rel, written[rel], f'ectd-{n:03d}'
        for sub in ('dtd', 'style'):
            (self.seq_dir / 'util' / sub).mkdir(parents=True, exist_ok=True)
            for f in (PROFILE_EG / 'util' / sub).iterdir():
                shutil.copyfile(f, self.seq_dir / 'util' / sub / f.name)
        self.write_regional(m1_leaves)
        self.write_index()
        return m1_leaves, written

    def write_regional(self, m1_leaves):
        e = self._env()
        x = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<!DOCTYPE eg-backbone SYSTEM "../../util/dtd/eg-regional.dtd">',
             '<?xml-stylesheet type="text/xsl" href="../../util/style/eg-regional.xsl"?>',
             '<eg-backbone xmlns:xlink="http://www.w3c.org/1999/xlink">',
             '  <eg-envelope>', '    <envelope country="eg">',
             f'      <identifier>{e.get("identifier", "")}</identifier>',
             f'      <submission type="{e.get("submission_type", "")}">', '        <procedure-tracking>',
             f'          <number>{escape(e.get("tracking", ""))}</number>', '        </procedure-tracking>', '      </submission>',
             f'      <submission-unit type="{e.get("unit", "")}"/>', f'      <applicant>{escape(e.get("applicant", ""))}</applicant>', '      <agency code="EG-EDA"/>',
             f'      <invented-name>{escape(e.get("invented_name", ""))}</invented-name>', f'      <registration type="{e.get("registration", "")}"/>',
             f'      <marketing type="{e.get("marketing", "")}"/>']
        x += [f'      <inn>{escape(i)}</inn>' for i in e.get('inn', [])]
        x += [f'      <sequence>{e["sequence"]}</sequence>', f'      <related-sequence>{e["related"]}</related-sequence>',
              f'      <submission-description>{escape(e.get("description", ""))}</submission-description>', '    </envelope>', '  </eg-envelope>', '  <m1-eg>']
        parents = {}
        for name, model in self.dtd.eg_model.items():
            for child in model:
                parents.setdefault(child, name)
        tree = {}
        for (el, pidoc, href, title, digest, lid, src, keep) in m1_leaves:
            path = [el]
            while parents.get(path[0]) and parents[path[0]] != 'm1-eg':
                path.insert(0, parents[path[0]])
            node = tree
            for p in path:
                node = node.setdefault(p, {})
            node.setdefault('__leaves__', []).append((pidoc, href, title, digest, lid))
        eg_model = self.dtd.eg_model

        def emit(name, node, ind):
            out = [f'{ind}<{name}>']
            pis = {}
            for (pidoc, href, title, digest, lid) in node.get('__leaves__', []):
                leaf = (f'{ind}  <leaf ID="{lid}" operation="new" checksum="{digest}" checksum-type="md5" xlink:href="{href}">\n'
                        f'{ind}    <title>{escape(title)}</title>\n{ind}  </leaf>')
                if pidoc:
                    pis.setdefault((pidoc['xml:lang'], pidoc['type']), []).append(
                        leaf.replace('\n' + ind, '\n' + ind + '  ').replace(ind + '  <leaf', ind + '    <leaf', 1))
                else:
                    out.append(leaf)
            for (lang, typ), ls in pis.items():
                out.append(f'{ind}  <pi-doc xml:lang="{lang}" type="{typ}" country="eg">')
                out += ls
                out.append(f'{ind}  </pi-doc>')
            order = eg_model.get(name, [])
            for child in sorted([k for k in node if k != '__leaves__'], key=lambda c: order.index(c) if c in order else 999):
                out += emit(child, node[child], ind + '  ')
            out.append(f'{ind}</{name}>')
            return out
        order = eg_model['m1-eg']
        for child in sorted(tree, key=lambda c: order.index(c)):
            x += emit(child, tree[child], '    ')
        x += ['  </m1-eg>', '</eg-backbone>']
        p = self.seq_dir / 'm1' / 'eg' / 'eg-regional.xml'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('\n'.join(x) + '\n', encoding='utf-8')

    def write_index(self):
        dtd = self.dtd
        root = {}
        for l in self.leaves:
            node = root
            for c in dtd.chain(l['code']):
                el = dtd.elem(c)
                attrs = {k: v for k, v in l['attrs'].get(c, {}).items() if k in dtd.attlist.get(el, set())}
                key = (el, tuple(sorted(attrs.items())))
                node = node.setdefault(key, {})
            node.setdefault('__leaves__', []).append(l)

        def emit(key, node, ind):
            el, attrs = key
            a = ''.join(f' {k}={quoteattr(v)}' for k, v in attrs)
            out = [f'{ind}<{el}{a}>']
            for l in node.get('__leaves__', []):
                out.append(f'{ind}  <leaf ID="{l["id"]}" operation="new" checksum="{l["md5"]}" checksum-type="md5" xlink:href="{l["href"]}">')
                out.append(f'{ind}    <title>{escape(l["title"])}</title>')
                out.append(f'{ind}  </leaf>')
            order = dtd.model.get(el, [])
            kids = [k for k in node if k != '__leaves__']
            kids.sort(key=lambda k: order.index(k[0]) if k[0] in order else 999)
            for k in kids:
                out += emit(k, node[k], ind + '  ')
            out.append(f'{ind}</{el}>')
            return out
        reg = self.seq_dir / 'm1' / 'eg' / 'eg-regional.xml'
        x = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<?xml-stylesheet type="text/xsl" href="util/style/ectd-2-0.xsl"?>',
             '<!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd">',
             '<ectd:ectd xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">',
             '  <m1-administrative-information-and-prescribing-information>',
             f'    <leaf ID="eg-regional" operation="new" checksum="{md5_file(reg)}" checksum-type="md5" xlink:href="m1/eg/eg-regional.xml">',
             '      <title>EG Module 1</title>', '    </leaf>', '  </m1-administrative-information-and-prescribing-information>']
        order = dtd.model['ectd:ectd']
        for k in sorted(root, key=lambda k: order.index(k[0])):
            x += emit(k, root[k], '  ')
        x.append('</ectd:ectd>')
        p = self.seq_dir / 'index.xml'
        p.write_text('\n'.join(x) + '\n', encoding='utf-8')
        (self.seq_dir / 'index-md5.txt').write_text(md5_file(p), encoding='ascii')


def global_check(w, seq_dir):
    """The check for any country (validators/global_ectd.py) on this sequence: ICH's layer, then the region's own criteria; the
    whole result in global.json, its counts in ectd.json. A failure of the check itself is said, never fatal to the sequence."""
    try:
        from ..validators import global_ectd
        res = global_ectd.validate(seq_dir)
    except Exception as ex:                                   # the sequence stands: the check's own fault is said, kept and shown
        say(f'تعذّر الفحص العالمي للتسلسل: {type(ex).__name__}: {ex}')
        return {'ok': None, 'error': f'{type(ex).__name__}: {ex}'}
    w.save('global.json', res)
    counts = {}
    for name, layer in (res.get('layers') or {}).items():
        c = layer.get('counts') or {}
        counts[name] = {'ok': layer.get('ok'), 'pass': c.get('pass', 0), 'fail': c.get('fail', 0), 'warn': c.get('warn', 0)}
    en, ar = global_ectd.note(res)
    say(f"الفحص العالمي ({res.get('authority')}): " + ' · '.join(f"{k}: {'مطابق' if v['ok'] else 'غير مطابق'} ({v['fail']} راسبة)"
                                                            for k, v in counts.items()))
    return {'ok': res.get('ok'), 'region': res.get('region'), 'authority': res.get('authority'), 'criteria': res.get('criteria'),
            'layers': counts, 'note': {'en': en, 'ar': ar}}


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    b = Builder(w)
    env = b._env()
    need = [k for k in ('identifier', 'submission_type', 'unit', 'applicant', 'invented_name', 'registration', 'marketing') if not env.get(k)]
    if need:
        raise SystemExit('بيانات الغلاف (envelope) ناقصة في dossier.json → ectd.envelope: ' + ', '.join(need))
    b.gen.mkdir(parents=True, exist_ok=True)
    say('المستندات المتروكة من التسلسل، ثم الأوراق في Modules 2–5')
    b.decide_left_out()
    b.build_leaves()
    say('Module 1 المصرية')
    b.build_m1()
    say(f'كتابة التسلسل {env["sequence"]}')
    m1_leaves, written = b.write()
    say('التحقق من التسلسل')
    results = validate.validate(b.seq_dir, PROFILE_EG, header=b.header)
    pf = [r for r in results if r['kind'] == 'P/F']
    bp = [r for r in results if r['kind'] == 'BP']
    rec = {'sequence': str(b.seq_dir), 'envelope': env, 'leaves': b.leaves, 'm1': m1_leaves, 'left_out': b.left_out,
           'qos_runs': getattr(b, 'qos_runs', {}), 'files': len(written) + len(m1_leaves),
           'bytes': sum(p.stat().st_size for p in b.seq_dir.rglob('*') if p.is_file()),
           'validation': {'pf_pass': sum(r['ok'] for r in pf), 'pf_fail': sum(not r['ok'] for r in pf),
                          'bp_met': sum(r['ok'] for r in bp), 'bp_not': sum(not r['ok'] for r in bp)}}
    out_items = {x['item'] for x in b.built_out}
    rec['built'] = [x['item'] for x in b.built if x['item'] not in out_items]
    rec['built_out'] = b.built_out
    rec['global'] = global_check(w, b.seq_dir)
    w.save('ectd.json', rec)
    w.save('validation.json', results)
    v = rec['validation']
    say(f"{len(b.leaves)} ورقة في Modules 2–5 · {len(m1_leaves)} في Module 1 · {rec['files']} ملفًا · "
        f"قواعد النجاح/الرسوب: {v['pf_pass']} ناجحة و{v['pf_fail']} راسبة · أفضل الممارسات: {v['bp_met']} متحققة و{v['bp_not']} غير متحققة")
    return rec
