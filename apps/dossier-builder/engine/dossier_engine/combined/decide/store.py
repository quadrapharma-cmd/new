"""Claude's decisions written into the dossier's decisions file (dossier.json), the same file a person's decisions go to: each
one checked before it is written, the file saved after each, so a stop keeps what was decided. What cannot be applied as given
is a ToolError: its message goes back to Claude, which corrects it."""
import copy
import re
import uuid

import pikepdf

from ..common import ranges
from ..fix import check_translation
from ..pdfedit import drawn_text, edit_page
from .brain import ToolError

CTD = re.compile(r'^[1-5](\.[0-9A-Z]+)*$')
SEVERITY = ('critical', 'major', 'minor')
KINDS = ('t', 'h', 's', 'p', 'b', 'rows')
PI_KEYS = {'SPC': ('spc', 'en'), 'PIL': ('pl', 'en'), 'OUTER': ('outer', 'en'), 'IMPACK': ('impack', 'en'), 'PIL_AR': ('pl', 'ar')}
REGISTRATION = ('local', 'toll', 'f-toll', 'under-license', 'imported-finished', 'imported-bulk')      # the EG envelope's DTD
MARKETING = ('local', 'tender', 'export', 'hospital')
PI_FILE = 'decisions/pi-content.json'
LEAF_FILE = re.compile(r'^[a-z0-9][a-z0-9-]{0,60}\.pdf$')


def glossary(x):
    """The program's glossary in its Arabic texts: a CTD module is «Module N» in Latin letters, never «الوحدة N»."""
    if isinstance(x, str):
        return re.sub(r'الوحدة ([1-5])(?![0-9])', r'Module \1', x).strip()
    if isinstance(x, list):
        return [glossary(v) for v in x]
    if isinstance(x, dict):
        return {k: glossary(v) for k, v in x.items()}
    return x


def text(a, key, most=4000, need=True):
    v = a.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        if need:
            raise ToolError(f'«{key}» is missing.')
        return ''
    if not isinstance(v, str):
        raise ToolError(f'«{key}» must be text.')
    if len(v) > most:
        raise ToolError(f'«{key}» is longer than {most} characters.')
    return v.strip()


def rows_of(a, key, width, most=60):
    rows = a.get(key)
    if not isinstance(rows, list) or not rows:
        raise ToolError(f'«{key}» must be a list of rows.')
    if len(rows) > most:
        raise ToolError(f'At most {most} rows.')
    for r in rows:
        if not isinstance(r, list) or len(r) != width or not all(isinstance(c, str) for c in r):
            raise ToolError(f'Each row of «{key}» is a list of {width} texts; this one is not: {r!r}'[:400])
    return [[c.strip() for c in r] for r in rows]


def path_of(p):
    p = (p or '').strip().strip('/')
    if not p or '..' in p.split('/') or '\\' in p or re.search(r'[:*?"<>|\x00-\x1f]', p):
        raise ToolError(f'«{p}» is not a usable path in the CTD folder.')
    if not re.match(r'^Module [1-5]\b', p):
        raise ToolError('A path starts with its module folder, e.g. «Module 3/3.2.P …/…pdf» (see the paths of the documents).')
    if not p.lower().endswith('.pdf'):
        p += '.pdf'
    if len(p) > 230:
        raise ToolError('The path is longer than 230 characters: shorten the title in it.')
    return p


class Store:
    def __init__(self, w, case):
        self.w = w
        self.case = case
        self.d = copy.deepcopy(w.decisions())
        for k, v in (('names', {}), ('plan', []), ('notes', {}), ('fixes', []), ('findings', []), ('report', {}), ('ectd', {})):
            self.d.setdefault(k, v)
        self.d.setdefault('claude', {'tasks': {}})

    def save(self):
        self.w.save('dossier.json', self.d)

    def docs(self):
        return {d['path']: d for d in (self.w.load('plan.json', {}) or {}).get('docs', [])}

    def doc(self, path):
        d = self.docs().get((path or '').strip())
        if not d:
            raise ToolError(f'«{path}» is not a document of the plan; give its path exactly as the document list shows it.')
        return d

    def kept_pages(self, spec):
        pages = self.case.check_pages(spec, most=None)
        out = [p for p in pages if p not in self.case.kept]
        if out:
            raise ToolError(f'Pages {ranges(out)} are in a block received twice and were left out; they cannot be placed.')
        return pages

    # -- 1. the documents
    def place(self, a):
        pages = self.kept_pages(a.get('pages'))
        path = path_of(a.get('path'))
        ctd = text(a, 'ctd', 20)
        if not CTD.match(ctd):
            raise ToolError(f'«{ctd}» is not a CTD number (e.g. 3.2.S.2.3, 5.3.5.1, 1.3.2).')
        e = {'pages': ranges(pages).replace('–', '-'), 'path': path, 'ctd': ctd, 'title': text(a, 'title', 200)}
        self.d['plan'].append(e)
        if a.get('note'):
            self.d['notes'][path] = text(a, 'note', 500)
        self.save()
        return f"Recorded: pages {e['pages']} → «{path}» ({ctd})."

    def leave_out(self, a):
        pages = self.kept_pages(a.get('pages'))
        e = {'pages': ranges(pages).replace('–', '-'), 'drop': text(a, 'why', 300)}
        self.d['plan'].append(e)
        self.save()
        return f"Recorded: pages {e['pages']} left out ({e['drop']})."

    def note(self, a):
        path = path_of(a.get('path'))
        if path not in self.docs() and not any(e.get('path') == path for e in self.d['plan']):
            raise ToolError(f'«{path}» is not a document of the plan.')
        self.d['notes'][path] = text(a, 'note', 500)
        self.save()
        return 'Recorded.'

    def names(self, a):
        subst = a.get('substances') or {}
        if not isinstance(subst, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in subst.items()):
            raise ToolError('«substances» maps each drug substance block\'s bookmark title to its short name.')
        tops = {o['title'] for o in (self.w.load('read/outline.json', []) or []) if o['level'] == 0}
        bad = [k for k in subst if k not in tops]
        if bad:
            raise ToolError(f"Not top-level bookmarks: {bad}. They are: {sorted(tops)}")
        n = self.d['names']
        if subst:
            n['substances'] = {k: v.strip() for k, v in subst.items()}
        if a.get('product'):
            n['product'] = text(a, 'product', 120)
        self.save()
        return 'Recorded.'

    # -- 2. the product and Module 1
    def envelope(self, a):
        reg, mkt = text(a, 'registration', 40), text(a, 'marketing', 40)
        if reg not in REGISTRATION:
            raise ToolError(f'registration is one of {REGISTRATION}.')
        if mkt not in MARKETING:
            raise ToolError(f'marketing is one of {MARKETING}.')
        inn = a.get('inn')
        if not isinstance(inn, list) or not inn or not all(isinstance(x, str) and x.strip() for x in inn):
            raise ToolError('«inn» is the list of the active substances.')
        e = self.d['ectd'].setdefault('envelope', {})
        e.setdefault('identifier', str(uuid.uuid4()))
        e.update({'submission_type': 'maa', 'tracking': e.get('tracking', ''), 'unit': 'initial', 'sequence': '0000', 'related': '0000',
                  'applicant': text(a, 'applicant', 200), 'invented_name': text(a, 'invented_name', 200), 'registration': reg,
                  'marketing': mkt, 'inn': [x.strip() for x in inn], 'description': text(a, 'description', 400)})
        self.save()
        return 'Recorded.'

    def product(self, a):
        E = self.d['ectd']
        subst = a.get('substances')
        if not isinstance(subst, list) or not subst:
            raise ToolError('«substances»: one item for each drug substance: {name, folder, substance}.')
        sd = {}
        for s in subst:
            if not isinstance(s, dict):
                raise ToolError('Each substance is {name, folder, substance}.')
            name, folder = text(s, 'name', 120), text(s, 'folder', 60)
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', folder):
                raise ToolError(f'A folder name is lower case letters, digits and hyphens: «{folder}».')
            sd[name] = {'folder': folder, 'substance': text(s, 'substance', 120).lower()}
        names = set((self.d['names'].get('substances') or {}).values())
        if names and set(sd) != names:
            raise ToolError(f'The substances are named as in set_names: {sorted(names)}.')
        for k in ('product_folder', 'indication_folder'):
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', text(a, k, 40)):
                raise ToolError(f'«{k}» is lower case letters, digits and hyphens.')
        manuf = text(a, 'manufacturer', 200).lower()
        E.update({'manufacturer': manuf, 'indication': text(a, 'indication', 200).lower(), 'substances': sd,
                  'product': {'product-name': text(a, 'product_name', 200).lower(), 'dosageform': text(a, 'dosage_form', 80).lower(),
                              'manufacturer': manuf},
                  'product_folder': a['product_folder'].strip(), 'indication_folder': a['indication_folder'].strip(),
                  'excipient': (a.get('excipient') or 'all excipients').strip()})
        self.save()
        return 'Recorded.'

    def cover(self, a):
        content = a.get('content')
        if not isinstance(content, list) or not all(isinstance(x, str) for x in content):
            raise ToolError('«content» is a list of lines, one for each module.')
        self.d['ectd']['cover'] = {'subject_html': text(a, 'subject_html', 600), 'opening': text(a, 'opening', 600),
                                   'product': rows_of(a, 'product', 2, 12), 'content': [x.strip() for x in content]}
        self.save()
        return 'Recorded.'

    def card(self, a):
        self.d['report']['product_card'] = glossary(rows_of(a, 'rows', 3, 30))
        self.save()
        return 'Recorded.'

    def eg_m1(self, a):
        self.d['report']['eg_m1_intro'] = glossary(text(a, 'intro', 600))
        self.d['report']['eg_m1_needs'] = glossary(rows_of(a, 'rows', 3, 40))
        self.save()
        return 'Recorded.'

    def titles(self, a):
        for k in ('title', 'subtitle', 'ectd_title', 'ectd_subtitle'):
            self.d['report'][k] = glossary(text(a, k, 200))
        self.save()
        return 'Recorded.'

    def to_confirm(self, a):
        self.d['report'].setdefault('to_confirm', []).append(glossary([text(a, 'item', 200), text(a, 'value', 400), text(a, 'why', 400)]))
        self.save()
        return 'Recorded.'

    def gap(self, a):
        self.d['report'].setdefault('company_gaps', []).append(glossary([text(a, 'item', 300), text(a, 'where', 300), text(a, 'who', 100)]))
        self.save()
        return 'Recorded.'

    # -- 3. the product information
    def pi_content(self):
        return self.w.load(PI_FILE, {}) or {}

    def write_pi(self, a):
        key = text(a, 'key', 10)
        if key not in PI_KEYS:
            raise ToolError(f'«key» is one of {list(PI_KEYS)}.')
        blocks = a.get('blocks')
        if not isinstance(blocks, list) or not blocks:
            raise ToolError('«blocks» is the list of the document\'s blocks.')
        for i, b in enumerate(blocks):
            if not isinstance(b, dict) or len(b) != 1 or next(iter(b)) not in KINDS:
                raise ToolError(f'Block {i}: one key of {KINDS}: {b!r}'[:300])
            k, v = next(iter(b.items()))
            if k == 'rows':
                if not isinstance(v, list) or not all(isinstance(r, list) and len(r) == 2 and all(isinstance(c, str) for c in r) for r in v):
                    raise ToolError(f'Block {i}: «rows» is a list of [name, value] pairs.')
            elif not isinstance(v, str) or not v.strip():
                raise ToolError(f'Block {i}: its text is empty.')
        content = self.pi_content()
        typ, lang = PI_KEYS[key]
        note = ''
        if key == 'PIL_AR':
            if 'PIL' not in content:
                raise ToolError('Write the English leaflet (PIL) first: the Arabic one is checked against it.')
            bad = check_translation(content['PIL'], blocks)
            if bad:
                raise ToolError('The Arabic leaflet does not match the English one block by block:\n' + '\n'.join(bad[:15]))
        elif key == 'PIL' and 'PIL_AR' in content and check_translation(blocks, content['PIL_AR']):
            note = ' The Arabic leaflet no longer matches it: write PIL_AR again.'
        content[key] = blocks
        self.w.save(PI_FILE, content)
        pi = self.d.setdefault('pi', {'content': PI_FILE, 'documents': []})
        pi['content'] = PI_FILE
        pi['documents'] = [x for x in pi.get('documents', []) if x.get('blocks') != key]
        doc = {'type': typ, 'lang': lang, 'blocks': key, 'file': f'{typ}-{lang}', 'title': text(a, 'title', 200),
               'ectd_title': text(a, 'ectd_title', 200)}
        if key == 'PIL_AR':
            doc['check_against'] = 'PIL'
        pi['documents'].append(doc)
        order = list(PI_KEYS)
        pi['documents'].sort(key=lambda x: order.index(x['blocks']))
        for k in ('header', 'creator', 'creator_ar'):
            if a.get(k):
                pi[k] = text(a, k, 300)
        self.save()
        return f'Recorded: {key}, {len(blocks)} blocks.' + note

    def pi_change(self, a):
        row = [text(a, 'where', 200), text(a, 'old', 600), text(a, 'new', 600), text(a, 'source', 300)]
        self.d['report'].setdefault('pi_changes', []).append(row)
        self.save()
        return 'Recorded.'

    def fix_in_pdf(self, a):
        d = self.doc(a.get('doc'))
        page = a.get('page')
        if not isinstance(page, int) or not 1 <= page <= len(d['pages']):
            raise ToolError(f"«page» is the page within the document: 1–{len(d['pages'])}.")
        old, new = text(a, 'old', 200), (a.get('new') or '')
        folder = self.w.ctd / (self.d.get('ctd_folder') or 'CTD')
        src = folder / d['path']
        if not src.exists():
            raise ToolError('The CTD folder is not built yet.')
        with pikepdf.open(src) as pdf:
            try:
                edit_page(pdf, page - 1, [(old, new)])
            except ValueError as e:
                drawn = drawn_text(pdf, page - 1)
                raise ToolError(f'{e}\nThe page\'s text as the PDF draws it (the phrase must be found in it exactly once):\n{drawn[:2500]}')
        for f in self.d['fixes']:
            if f['doc'] == d['path'] and f['page'] == page:
                f['edits'].append([old, new])
                break
        else:
            self.d['fixes'].append({'doc': d['path'], 'page': page, 'edits': [[old, new]], 'note': text(a, 'note', 300)})
        self.save()
        return 'Recorded: the correction applies (characters deleted only).'

    def translation_note(self, a):
        self.d['report'].setdefault('translation_notes', []).append(glossary(text(a, 'text', 600)))
        self.save()
        return 'Recorded.'

    # -- 4. the reviewer's findings
    def finding(self, a):
        sev = text(a, 'severity', 10)
        if sev not in SEVERITY:
            raise ToolError(f'severity is one of {SEVERITY}.')
        n = sum(1 for f in self.d['findings'] if f.get('rule') == 'reviewer')
        self.d['findings'].append(glossary({'rule': 'reviewer', 'order': 20 + 10 * n, 'severity': sev, 'text': text(a, 'text', 1500),
                                            'where': text(a, 'where', 600), 'action': text(a, 'action', 800)}))
        self.save()
        return 'Recorded.'

    # -- 5. the eCTD
    def leaf(self, a):
        d = self.doc(a.get('doc'))
        o = {}
        if a.get('file'):
            f = text(a, 'file', 70)
            if not LEAF_FILE.match(f):
                raise ToolError('A file name is lower case letters, digits and hyphens, ending in .pdf, at most 64 characters.')
            o['file'] = f
        if a.get('folder'):
            f = text(a, 'folder', 180).strip('/')
            if not re.fullmatch(r'm[1-5](/[a-z0-9][a-z0-9-]*)+', f):
                raise ToolError('A folder is the sequence\'s path, e.g. «m3/32-body-data/32s-drug-sub/name-maker/32s2-manuf».')
            o['folder'] = f
        if a.get('title'):
            o['title'] = text(a, 'title', 250)
        if not o:
            raise ToolError('Give a new file name, folder or title.')
        self.d['ectd'].setdefault('leaves', {}).setdefault(d['path'], {}).update(o)
        self.save()
        return 'Recorded.'

    def ectd_out(self, a):
        d = self.doc(a.get('doc'))
        self.d['ectd'].setdefault('left_out', {})[d['path']] = glossary(text(a, 'why', 400))
        keep = self.d['ectd'].setdefault('keep_in', [])
        if d['path'] in keep:
            keep.remove(d['path'])
        self.save()
        return 'Recorded.'

    def ectd_in(self, a):
        d = self.doc(a.get('doc'))
        keep = self.d['ectd'].setdefault('keep_in', [])
        if d['path'] not in keep:
            keep.append(d['path'])
        (self.d['ectd'].get('left_out') or {}).pop(d['path'], None)
        self.save()
        return 'Recorded.'

    def m1(self, a):
        d = self.doc(a.get('doc'))
        o = {'from': d['path']}
        if a.get('title'):
            o['title'] = text(a, 'title', 250)
        if a.get('pages'):
            pages = self.case.check_pages(a['pages'], most=None)
            out = [p for p in pages if p not in d['pages']]
            if out:
                raise ToolError(f"Pages {ranges(out)} are not in that document (its pages: {ranges(d['pages'])}).")
            o['keep'] = ','.join(map(str, pages))
        if a.get('skip'):
            o['skip'] = True
        if len(o) == 1:
            raise ToolError('Give a title, the pages to keep, or skip.')
        m1 = self.d['ectd'].setdefault('m1', [])
        for x in m1:
            if x.get('from') == d['path']:
                x.update(o)
                break
        else:
            m1.append(o)
        self.save()
        return 'Recorded.'
