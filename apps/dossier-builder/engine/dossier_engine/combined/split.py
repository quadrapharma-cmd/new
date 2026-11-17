"""Stage 4 — the documents: what the program proposes, the dossier's decisions laid over it, the plan.

How the program cuts (the same reading that cut the DTP-HB dossier by hand):
  · the top blocks are the top-level bookmarks (or the files), less the repeated blocks; each block is a drug substance, the
    drug product, annexures, appendices or a module, by its title or by the CTD numbers on its pages;
  · a page's CTD heading is read from its own text (never from the OCR: a scanned page belongs to the document before it), in its
    first seven lines; «3.2» broken from «P.3.5» on the next line is joined. Drug substance and product pages: the first heading
    there. Other modules: the deepest heading of a chain (5.3 → 5.3.1 → 5.3.1.1), filed at its document's level (5.3.1); a
    heading that goes back in the CTD order inside a block is a line of the text, not a new document;
  · a page without a heading (or without text) joins the document before it;
  · table-of-contents pages: at the start of a module they are the module's table of contents (1.0, 2.1, 3.1, 4.1, 5.1); at the
    start of a drug substance, the product or the appendices they are left out (their lines are in 3.1) — unless they name
    several drug substances, which makes them Module 3's own (3.1); a page in the middle of a document listing three or more
    sections of one level is its table of contents going on;
  · covers («MODULE – 3 …», «ANNEXURES FOR MODULE …») and the pages without text after them are left out; a group's separator
    (4.2, 5.3, 3.2.S.4 …) is left out; a section's own separator in front of its pages (its title in capitals and the product
    in brackets, nothing else) is left out; a section with only its heading page is kept as it is (it says the section is
    empty);
  · a printed number whose title is another section's title is filed by its title (and said);
  · annexures («ANNEXURE – 1 …») are documents of their own, placed by their title (raw materials → 3.2.S.2.3, common to the
    drug substances when there are several); literature (3.3, 4.3, 5.4) is cut at each publication's title page;
  · a document over the authority's size limit is cut into parts of about equal size.
Then the dossier's decisions file (dossier.json → plan: page-range edits, each with its reason) is laid over the proposal.
Writes plan.json: {docs: [{path, ctd, title, pages, note, by}], removed: [{page, why, by}], edits, proposal_counts}."""
import re
from collections import Counter

from . import ctdnames as N
from .common import Work, parse_ranges, ranges, say

NUMS = {'3': r'3\.(?:1|3|2(?:\.[SPAR](?:\.\d{1,2}){0,3})?)', '2': r'2\.[1-7](?:\.[SP]|\.\d{1,2}){0,3}',
        '4': r'4\.[1-3](?:\.\d{1,2}){0,3}', '5': r'5\.[1-4](?:\.\d{1,2}){0,3}', '1': r'1\.(?:\d{1,2})(?:\.\d{1,2}){0,2}'}
ROMAN = {'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5'}
SIZE_LIMIT = 100 * 1000 * 1000          # EDA, the GCC and most others: 100 MB a file
LIT = re.compile(r'^\s*(?:WHO\s+)?(?:TRS|Technical\s+Report\s+Series)\s*(?:No\.?\s*)?\d+', re.I)


# ------------------------------------------------------------------ reading a page
def clean_lines(text):
    return [re.sub(r'\s+', ' ', l).strip() for l in text.splitlines() if l.strip()]


def head_re(mod):
    return re.compile(r'^\(?\s*(?:Module\s*)?(' + NUMS[mod] + r')\b(?!\.\d)\s*[-–:.]?\s*(.*)$', re.I if mod in '12345' else 0)


def joined(lines):
    """«3.2» on one line and «P.3.5 – …» on the next are one heading; «3.2. P.3.5» is «3.2.P.3.5»; «2.3. S» is «2.3.S»."""
    lines = list(lines)
    for i in range(len(lines) - 1):
        if re.fullmatch(r'3\.2\.?', lines[i]) and re.match(r'[SPAR](?:\.|\b)', lines[i + 1]):
            lines[i] = '3.2.' + lines[i + 1]
            lines[i + 1] = ''
    lines = [re.sub(r'^(3\.2)\.?\s+([SPAR])(?=[\s.]|$)', r'\1.\2', l) for l in lines if l]
    lines = [re.sub(r'^(2\.3)\.?\s+([SPAR])(?=[\s.]|$)', r'\1.\2', l) for l in lines]
    lines = [re.sub(r'^(\d(?:\.\d{1,2})+)\.\s(\d{1,2})\b', r'\1.\2', l) for l in lines]                 # «1.4. 2» is «1.4.2»
    return lines


def headings(text, mod, top=7):
    """The CTD headings in a page's first lines: [(key, title)]. A number alone on its line counts when another number of the same
    module is on the page or a title follows (the hand rule: a title on the line, or two dots in it)."""
    rx = head_re(mod)
    lines = joined(clean_lines(text))
    out = []
    for i, l in enumerate(lines[:top]):
        m = rx.match(l)
        if not m:
            continue
        if not m.group(2) and l.count('.') < 2 and i + 1 < len(lines) and is_title_line(lines[i + 1]):
            l = l + ' ' + lines[i + 1]                                          # «3.3» / «LITERATURE REFERENCES»
            m = rx.match(l)
        key = re.sub(r'\.([spar])(?=\.|$)', lambda x: '.' + x.group(1).upper(), m.group(1)).strip('.')
        title = m.group(2)
        if title or l.count('.') >= 2:
            out.append((key, (title or l)[:80]))
    return out


def is_title_line(l):
    """A heading's title written on its own line: capitals («LITERATURE REFERENCES») or a short title in Title Case."""
    if not l or l[0].isdigit() or not l[0].isalpha() or len(l) > 80:
        return False
    words = re.findall(r'[A-Za-z]+', l)
    if not words:
        return False
    if l.upper() == l:
        return True
    caps = sum(1 for w in words if w[0].isupper() or w.lower() in ('of', 'and', 'the', 'to', 'in', 'for', 'or', 'a', 'on'))
    return len(words) <= 9 and caps == len(words)


def first_key(text, mod):
    h = headings(text, mod)
    return h[0] if h else (None, '')


def deepest_key(text, mod):
    """The heading chain at the top of a page (5.3 → 5.3.1 → 5.3.1.1): its deepest member."""
    h = headings(text, mod)
    if not h:
        return None, ''
    key, title = h[0]
    for k, t in h[1:]:
        if N.is_under(k, key) and k != key:
            key, title = k, t
        else:
            break
    return key, title


def ctd_numbers(text, mod):
    rx = re.compile(r'^\(?\s*(?:Module\s*)?(' + NUMS[mod] + r')\b(?!\.\d)', re.I)
    out = set()
    for l in joined(clean_lines(text)):
        m = rx.match(l)
        if m:
            out.add(m.group(1).upper().strip('.'))
    return out


# ------------------------------------------------------------------ the plan
class Planner:
    def __init__(self, w):
        self.w = w
        self.text = w.pages_text('read/text.txt')
        ocr = w.pages_text('read/ocr.txt')
        self.ocr = ocr if len(ocr) == len(self.text) else [''] * len(self.text)
        self.pages = {p['n']: p for p in w.load('read/pages.json')}
        rep = w.load('repeats.json')
        self.dropped = set()
        for d in rep['dropped']:
            self.dropped |= set(range(d['from'], d['to'] + 1))
        self.blocks = [b for b in rep['blocks'] if not all(p in self.dropped for p in range(b['from'], b['to'] + 1))]
        self.header = self.running_header()
        self.assign = {}                     # page -> doc id
        self.docs = {}                       # doc id -> {ctd, title, path, note, by}
        self.removed = {}                    # page -> why
        self.names = (w.decisions().get('names') or {})
        self.counter = 0

    # -- the running header (lines among the first four of one page in twenty or more)
    def running_header(self):
        c = Counter()
        for t in self.text:
            for l in set(clean_lines(t)[:4]):
                c[l] += 1
        n = max(1, len(self.text))
        return {l for l, k in c.items() if k >= 0.05 * n and len(l) > 3 and not re.match(r'^\(?\s*\d\.\d', l)}

    def top(self, p, n=4):
        return [l for l in clean_lines(self.own(p)) if l not in self.header][:n]

    def body(self, p):
        lines = [l for l in clean_lines(self.text[p - 1]) if l not in self.header]
        return ' '.join(' '.join(lines).split())

    def body_any(self, p):
        """The page's words from its own text, or from the OCR when it has none (a scanned title page)."""
        lines = [l for l in clean_lines(self.any_text(p)) if l not in self.header]
        return ' '.join(' '.join(lines).split())

    def chars(self, p):
        return len(self.text[p - 1].strip())

    def own(self, p):
        return self.text[p - 1]

    def any_text(self, p):
        return self.text[p - 1] if self.chars(p) >= 30 else self.ocr[p - 1]

    # -- page kinds
    def is_cover(self, p):
        b = self.body(p)
        if len(b) > 220 or not b or re.search(r'table\s+of\s+contents?', b, re.I):
            return False
        if re.search(r'(?:^|\s)(?:MODULE\s*[-–:]?\s*(?:[1-5]|I{1,3}|IV|V)\b|ANNEXURES?\s+(?:FOR|TO)\s+MODULE)', b, re.I):
            return not re.search(r'\b[1-5]\.\d', b)
        return False

    def is_separator(self, p):
        """A section's own separator: «3.2.S.5 REFERENCE STANDARDS OR MATERIALS ( … ) 3.2.S.5 Reference Standards or Materials [n]» —
        its title in capitals after the number, the product in brackets, the title again: nothing else (the hand rule)."""
        b = self.body(p)
        if len(b) > 400 or re.search(r'not applicable|enclosed|no impurit', b, re.I):
            return False
        m = re.match(r'^\s*(?:\d\.\d(?:\.?\s?[SPAR])?(?:\.\d+)*)\s+([A-Z][A-Z ,&/\-–]+?)\s*\(', b)
        if not m:
            return False
        title = m.group(1)
        letters = [c for c in title if c.isalpha()]
        if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.9:
            return False
        rest = b[m.end() - 1:]
        depth, cut = 0, None
        for i, c in enumerate(rest):
            depth += (c == '(') - (c == ')')
            if depth == 0:
                cut = i + 1
                break
        rest = rest[cut:] if cut else ''
        words = {w.lower() for w in re.findall(r'[A-Za-z]{2,}', rest)}
        return words <= {w.lower() for w in re.findall(r'[A-Za-z]{2,}', title)}

    def is_title_page(self, p, key):
        """A short page that holds a group's number and title, perhaps twice, and nothing else (4.2 Study Reports ____ 4.2 Study Reports)."""
        b = self.body(p)
        if len(b) > 260 or not b:
            return False
        words = re.findall(r'[A-Za-z]{2,}', b)
        first = self.top(p, 99)
        if not first:
            return False
        tw = {w.lower() for w in re.findall(r'[A-Za-z]{2,}', ' '.join(first[:2]))}
        rest = [w.lower() for w in words if w.lower() not in tw]
        return len(rest) <= max(1, len(words) // 5)


    def is_toc_more(self, p, mod, key=None):
        """A page listing three or more sections that are not its own heading's sub-sections (1.7, 1.8, 1.9 on a page of 1.1):
        a table of contents going on."""
        nums = ctd_numbers(self.own(p), mod)
        if key:
            nums = {k for k in nums if not N.is_under(k, key)}
        return len(nums) >= 3

    # -- documents
    def new_doc(self, ctd, title, path, note='', by='program'):
        self.counter += 1
        did = f'd{self.counter:04d}'
        self.docs[did] = {'ctd': ctd, 'title': title, 'path': path, 'note': note, 'by': by}
        return did

    def put(self, did, pages):
        for p in pages:
            self.assign[p] = did
            self.removed.pop(p, None)

    def drop(self, pages, why):
        for p in pages:
            self.removed[p] = why
            self.assign.pop(p, None)

    # -- the blocks
    def kind(self, b):
        t = b['title']
        m = re.search(r'\bMODULE\s*[-–:]?\s*(V|IV|III|II|I|[1-5])\b', t, re.I)
        if re.search(r'drug\s+substance', t, re.I):
            return '3S'
        if re.search(r'drug\s+product', t, re.I):
            return '3P'
        if re.search(r'annex', t, re.I):
            return '3X'
        if re.search(r'append', t, re.I) or re.match(r'\s*3\.2\.A\b', t):
            return '3A'
        if m:
            v = m.group(1).upper()
            return ROMAN.get(v, v)
        c = Counter()
        for p in range(b['from'], b['to'] + 1):
            for mod in '12345':
                if headings(self.own(p), mod):
                    c[mod] += 1
        return c.most_common(1)[0][0] if c else '?'

    def substance_name(self, b):
        """The name a drug substance block gives itself: «( Bulk Pertussis Vaccine, Serum Institute of India Ltd. )»."""
        c = Counter()
        for p in range(b['from'], min(b['to'], b['from'] + 30) + 1):
            for m in re.finditer(r'\(\s*([A-Z][^()]{3,80}?),\s*([^()]{3,60}?)\s*\)', ' '.join(clean_lines(self.own(p)))):
                c[(m.group(1).strip(), m.group(2).strip())] += 1
        if c:
            return c.most_common(1)[0][0]
        return (re.sub(r'\s*[-–]?\s*drug\s+substance.*$', '', b['title'], flags=re.I).strip() or b['title'], '')

    def toc_lead(self, b, mod):
        """The table-of-contents pages at the start of a block (its covers already set aside), as sequences: a page saying «table
        of contents» starts one, a page with four or more CTD numbers goes on with it (six or more start one)."""
        seqs, cur = [], None

        def says(p):
            return bool(re.search(r'table\s+of\s+contents?\b', ' '.join(self.top(p)).lower()))

        def strong(p):
            return self.chars(p) >= 30 and (says(p) or len(ctd_numbers(self.own(p), mod)) >= 4)
        for p in range(b['from'], b['to'] + 1):
            if self.chars(p) < 5:
                break
            n = len(ctd_numbers(self.own(p), mod))
            if says(p) or (cur is None and n >= 6):
                cur = [p]
                seqs.append(cur)
            elif cur is not None and (n >= 4 or (n >= 2 and p + 1 <= b['to'] and strong(p + 1))):
                cur.append(p)
            else:
                break
        return seqs

    def plan_block(self, b):
        k = self.kind(b)
        if k in ('3S', '3P', '3A', '3X', '3'):
            return self.plan_m3(b, k)
        if k in ('1', '2', '4', '5'):
            return self.plan_module(b, k)
        did = self.new_doc('', b['title'] or 'Unplaced pages', f"Unplaced/{b['title'] or 'pages'} {b['from']}-{b['to']}.pdf",
                           'the program could not tell what this block is', by='program?')
        self.put(did, range(b['from'], b['to'] + 1))

    # ---- Module 3
    def plan_m3(self, b, k):
        pages = [p for p in range(b['from'], b['to'] + 1)]
        p0 = b['from']
        covers = []
        while pages and (self.is_cover(pages[0]) or (covers and self.chars(pages[0]) < 5)):
            covers.append(pages.pop(0))
        if covers:
            what = 'cover page of the annexures to Module 3' if re.search(r'annex', self.body(covers[0]), re.I) else 'cover page of Module 3'
            self.drop(covers[:1], what)
            self.drop(covers[1:], 'page after the cover (' + what + ')')
        if k == '3X':
            return self.plan_annexures(pages)
        # tables of contents at the start
        tocs = []
        sub = {'from': pages[0], 'to': b['to']} if pages else None
        if sub:
            tocs = self.toc_lead(sub, '3')
        lead = [p for s in tocs for p in s]
        subject = '3.2.P' if k == '3P' else ('3.2.A' if k == '3A' else 'this substance')
        for s in tocs:
            names = set()
            for p in s:
                for m in re.finditer(r'3\.2\.S\s+DRUG SUBSTANCE\s*\(\s*([^,()]+)', ' '.join(clean_lines(self.own(p))), re.I):
                    names.add(m.group(1).strip().lower())
                if re.search(r'3\.2\.\s?P\b', self.own(p)) and re.search(r'3\.2\.\s?A\b', self.own(p)):
                    names.add('product and appendices')
            if len(names) >= 2:
                did = self.new_doc('3.1', N.TOC['3'][0] + ' ' + N.TOC['3'][1], 'Module 3/3.1 Table of contents of Module 3.pdf')
                self.put(did, s)
            else:
                why = {'3.2.P': "table of contents of 3.2.P (the same lines are in Module 3's table of contents, 3.1)",
                       '3.2.A': 'table of contents of 3.2.A (the same lines are in 3.1)'}.get(
                    subject, "table of contents of this substance (the same lines are in Module 3's table of contents, 3.1)")
                self.drop(s, why)
        pages = [p for p in pages if p not in lead]
        if k == '3S':
            name, maker = self.substance_name(b)
            folder = (self.names.get('substances') or {}).get(b['title']) or f'{name}'
            self.substance_folders.append((b, folder, name, maker))
            base = f'Module 3/3.2.S {folder}'
        elif k == '3P':
            folder = self.names.get('product') or 'Drug product'
            self.product_folder = folder
            base = f'Module 3/3.2.P {folder}'
        else:
            base = 'Module 3'
        self.leaf_runs(pages, '3', base, k, folder if k == '3S' else None)

    def runs(self, pages, mod, first=True):
        """The hand rule: pages grouped by the heading at their top; a page without one joins the run before it."""
        out, cur = [], None
        for p in pages:
            key, title = (first_key if first else deepest_key)(self.own(p), mod) if self.chars(p) >= 1 else (None, '')
            if cur and (key is None or key == cur['key']):
                cur['pages'].append(p)
                continue
            cur = {'key': key, 'title': title, 'pages': [p]}
            out.append(cur)
        return out

    def leaf_runs(self, pages, mod, base, k, folder):
        for r in self.runs(pages, mod):
            key, pg = r['key'], list(r['pages'])
            if not pg:
                continue
            fixed = self.by_title(key, r['title'])
            note = ''
            if fixed and fixed != key:
                note = f"printed heading «{key}»; its text is {fixed}"
                self.findings.append({'kind': 'heading_number', 'page': pg[0], 'printed': key, 'is': fixed})
                key = fixed
            leaf = N.doc_key(key) if key else None
            if leaf is None or (key and key != leaf and key in (N.S_GROUP.keys() | N.P_GROUP.keys())):
                if key is None and self.assign and pg:
                    prev = self.assign.get(pg[0] - 1)
                    if prev:
                        self.put(prev, pg)
                        continue
                self.drop(pg, f'separator page ({key})' if key else 'page without a heading at the start of its block')
                continue
            while pg and self.is_separator(pg[0]):
                self.drop([pg[0]], 'separator page (the section title only)')
                pg = pg[1:]
            if not pg:
                continue
            self.add_leaf(leaf, pg, base, k, folder, note)

    def add_leaf(self, leaf, pg, base, k, folder, note=''):
        if leaf.startswith('3.2.S.'):
            group = N.S_GROUP['.'.join(leaf.split('.')[:4])]
            path = f'{base}/{group}/{leaf} {N.S_TITLES[leaf]}.pdf'
            title = f'{leaf} {N.S_TITLES[leaf]} ({folder})'
        elif leaf.startswith('3.2.P.'):
            group = N.P_GROUP['.'.join(leaf.split('.')[:4])]
            path = f'{base}/{group}/{leaf} {N.P_TITLES[leaf]}.pdf'
            title = f'{leaf} {N.P_TITLES[leaf]}'
        elif leaf.startswith('3.2.A.'):
            path = f'Module 3/3.2.A Appendices/{leaf} {N.A_TITLES[leaf]}.pdf'
            title = f'{leaf} {N.A_TITLES[leaf]}'
        elif leaf == '3.2.R':
            path, title = 'Module 3/3.2.R Regional information.pdf', '3.2.R Regional information'
        elif leaf == '3.3':
            return self.plan_literature(pg, '3.3', 'Module 3/3.3 Literature references')
        elif leaf == '3.1':
            path, title = 'Module 3/3.1 Table of contents of Module 3.pdf', '3.1 Table of contents of Module 3'
        else:
            path, title = f'Module 3/{leaf}.pdf', leaf
        did = self.doc_at(path, leaf, title, note)
        self.put(did, pg)

    def doc_at(self, path, ctd, title, note=''):
        for did, d in self.docs.items():
            if d['path'] == path:
                if note:
                    d['note'] = (d['note'] + ' ' + note).strip()
                return did
        return self.new_doc(ctd, title, path, note)

    def by_title(self, key, title):
        """A heading whose title is another leaf's title of the same part (3.2.P.2.1 «Description and Composition of the Drug
        Product»): that leaf — when the printed number's own title does not fit and exactly one other leaf's does."""
        if not key or not title or len(key.split('.')) < 3:
            return None
        tw = N.norm_words(title)
        if len(tw) < 3:
            return None

        def fits(t2):
            w2 = N.norm_words(t2)
            return w2 == tw[:len(w2)] and len(tw) - len(w2) <= 1
        table = N.S_TITLES if key.split('.')[2] == 'S' else N.P_TITLES if key.split('.')[2] == 'P' else {}
        if key in table and fits(table[key]):
            return key
        hits = [k2 for k2, t2 in table.items() if fits(t2)]
        return hits[0] if len(hits) == 1 else None

    def plan_annexures(self, pages):
        """«ANNEXURE – 1 …» title pages start the annexures; each is placed by its title."""
        cur = None
        n_subst = max(1, len(self.substance_folders) or self.count_substance_blocks())
        for p in pages:
            m = re.match(r'^\s*ANNEXURE\s*[-–:]?\s*(\d+)\s*(.*)$', self.body_any(p), re.I)
            if m and cur and self.docs[cur].get('annex') == m.group(1):
                m = None                                                    # the same annexure's title again at the top of its pages
            if m:
                num, rest = m.group(1), m.group(2)
                title = ' '.join(rest.split()).rstrip('.').capitalize()
                place = self.place_annex(title, n_subst)
                cur = self.new_doc(place['ctd'], f'Annexure {num} – {title}', place['folder'] + f'/Annexure {num} - {title[:60]}.pdf',
                                   place['note'])
                self.docs[cur]['annex'] = num
                self.put(cur, [p])
            elif cur:
                self.put(cur, [p])
            else:
                self.drop([p], 'page before the first annexure (a list of the annexures)')

    def count_substance_blocks(self):
        return sum(1 for b in self.blocks if self.kind(b) == '3S')

    def place_annex(self, title, n_subst):
        t = title.lower()
        common = f'3.2.S Common to the {N.NUMBER_WORDS.get(n_subst, str(n_subst))} drug substances' if n_subst > 1 else None
        if re.search(r'raw\s+material', t):
            folder = f'Module 3/{common}/3.2.S.2.3 Control of materials' if common else 'Module 3/3.2.S/3.2.S.2.3 Control of materials'
            return {'ctd': '3.2.S.2.3', 'folder': folder, 'note': ''}
        if re.search(r'excipient', t):
            return {'ctd': '3.2.P.4.1', 'folder': f'Module 3/3.2.P {self.product_folder or "Drug product"}/3.2.P.4 Control of excipients', 'note': ''}
        return {'ctd': '', 'folder': 'Module 3/Annexures to be placed', 'note': 'the program could not place this annexure by its title'}

    def plan_literature(self, pg, ctd, folder):
        cur, first = None, True
        for p in pg:
            t = self.any_text(p)
            lines = [l for l in clean_lines(t) if l not in self.header]
            m = LIT.match(' '.join(lines[:2])) if lines else None
            if m and not first:
                head = ' '.join(lines[:6])
                title = re.sub(r'\s+', ' ', head)[:150]
                cur = self.new_doc(ctd, title, f'{folder}/{title[:70]}.pdf')
            elif cur is None:
                cur = self.new_doc(ctd, f'{ctd} Literature references – statement', f'{folder}/{ctd} Literature references - statement.pdf')
            self.put(cur, [p])
            first = False

    # ---- Modules 1, 2, 4, 5
    def plan_module(self, b, mod):
        pages = list(range(b['from'], b['to'] + 1))
        covers = []
        while pages and (self.is_cover(pages[0]) or (covers and self.chars(pages[0]) < 5)):
            covers.append(pages.pop(0))
        if covers:
            self.drop(covers[:1], f'cover page of Module {mod}')
            self.drop(covers[1:], f'page after the cover of Module {mod}')
        tocs = self.toc_lead({'from': pages[0], 'to': b['to']}, mod) if pages else []
        lead = [p for s in tocs for p in s]
        if lead:
            key, title = N.TOC[mod]
            path = {'1': 'Module 1 - EU layout as received (for reference)/1.0 Module 1 table of contents.pdf',
                    '2': 'Module 2/2.1 CTD table of contents (Modules 2-5).pdf', '4': 'Module 4/4.1 Table of contents of Module 4.pdf',
                    '5': 'Module 5/5.1 Table of contents of Module 5.pdf'}[mod]
            did = self.new_doc(key, f'{key} {title}', path)
            self.put(did, lead)
        pages = [p for p in pages if p not in lead]
        cur_key, cur_doc = None, None
        for p in pages:
            if self.chars(p) < 1:
                key, title = None, ''
            else:
                key, title = deepest_key(self.own(p), mod)
                if mod == '1' and key is None:
                    key, title = self.m1_by_title(p)
            if key and cur_key and N.order(key) < N.order(cur_key) and not (N.doc_key(key) is None and N.is_under(cur_key, key)):
                key = None                                                  # backwards: a line of the text
            top_heads = headings(self.own(p), mod) if key else []
            if key and cur_doc and self.is_toc_more(p, mod, top_heads[0][0] if top_heads else key):
                key = None                                                  # its table of contents going on
            if key is None and mod == '1' and cur_key == '1.3.1' and self.m1_pi_start(p):
                key = '1.3.1'
            leaf = N.doc_key(key) if key else None
            if key and leaf is None:                                        # a group's own page
                if N.is_under(cur_key or '', key):
                    key = None                                              # «1.4 2 Non Clinical» after 1.4.2: the same document
                elif self.is_title_page(p, key) or self.chars(p) < 300:
                    self.drop([p], f'separator page ({key})')
                    cur_key = key
                    cur_doc = None
                    continue
            if key is None:
                if cur_doc:
                    self.put(cur_doc, [p])
                else:
                    self.drop([p], 'page without a heading at the start of its module')
                continue
            if leaf == cur_key and cur_doc and not (mod == '1' and leaf == '1.3.1' and self.m1_pi_start(p)) \
                    and not (mod == '2' and leaf == '2.3.S' and self.qos_new_substance(p, cur_doc)):
                self.put(cur_doc, [p])
                continue
            cur_key = leaf
            cur_doc = self.module_doc(mod, leaf, p, title)
            self.put(cur_doc, [p])

    def m1_by_title(self, p):
        first = [l for l in clean_lines(self.own(p)) if l not in self.header]
        if not first:
            return None, ''
        fw = N.norm_words(first[0])
        for k, t in N.M1EU_TITLES.items():
            if fw and fw == N.norm_words(t):
                return k, t
        return None, ''

    def m1_pi_start(self, p):
        first = [l for l in clean_lines(self.own(p)) if l not in self.header]
        return bool(first) and bool(re.match(r'^(labell?ing|package\s+leaflet)\b', first[0], re.I))

    def module_doc(self, mod, leaf, p, title):
        if mod == '1':
            t = N.M1EU_TITLES.get(leaf, title)
            if leaf == '1.3.1':
                first = [l for l in clean_lines(self.own(p)) if l not in self.header]
                t = 'Labelling' if first and re.match(r'^labell?ing', first[0], re.I) else (
                    'Package leaflet' if first and re.match(r'^package\s+leaflet', first[0], re.I) else 'SPC')
            path = f'Module 1 - EU layout as received (for reference)/{leaf} {t}.pdf'
            return self.doc_at(path, leaf, f'{leaf} {t}')
        if mod == '2':
            if leaf == '2.3':
                return self.doc_at('Module 2/2.3 Quality overall summary/2.3 Introduction.pdf', '2.3', '2.3 Quality overall summary – introduction')
            if leaf == '2.3.S':
                name = self.qos_substance(p)
                plain = re.sub(r'\s*\([^()]*\)\s*$', '', name)
                did = self.new_doc('2.3.S', f'2.3.S Drug substance – {plain[0].lower() + plain[1:] if plain else ""}',
                                   f'Module 2/2.3 Quality overall summary/2.3.S {name}.pdf')
                self.docs[did]['substance'] = name
                return did
            if leaf == '2.3.P':
                return self.doc_at('Module 2/2.3 Quality overall summary/2.3.P Drug product.pdf', '2.3.P', '2.3.P Drug product')
            t = N.M2_TITLES.get(leaf, title)
            return self.doc_at(f'Module 2/{leaf} {t}.pdf', leaf, f'{leaf} {t}')
        if mod == '4':
            t = N.M4_TITLES.get(leaf, title)
            if leaf.startswith('4.2.3.'):
                path = f'Module 4/4.2 Study reports/4.2.3 Toxicology/{leaf} {t}.pdf'
            elif leaf.startswith('4.2.'):
                path = f'Module 4/4.2 Study reports/{leaf} {t}.pdf'
            else:
                path = f'Module 4/{leaf} {t}.pdf'
            return self.doc_at(path, leaf, f'{leaf} {t}')
        if mod == '5':
            t = N.M5_TITLES.get(leaf, title)
            if leaf.startswith('5.3.5.'):
                path = f'Module 5/5.3 Clinical study reports/5.3.5 Reports of efficacy and safety studies/{leaf} {t}.pdf'
            elif leaf.startswith('5.3.'):
                path = f'Module 5/5.3 Clinical study reports/{leaf} {t}.pdf'
            else:
                path = f'Module 5/{leaf} {t}.pdf'
            return self.doc_at(path, leaf, f'{leaf} {t}')
        return self.new_doc(leaf, leaf, f'Module {mod}/{leaf}.pdf')

    def qos_said(self, p):
        t = ' '.join(clean_lines(self.own(p))[:12])
        m = re.search(r'DRUG\s+SUBSTANCE\s*\(\s*([^()]+?)(?:\)|$)', t, re.I)
        return m.group(1) if m else None

    def qos_new_substance(self, p, cur_doc):
        said = self.qos_said(p)
        return bool(said) and self.qos_substance(p) != self.docs[cur_doc].get('substance')

    def qos_substance(self, p):
        """2.3.S «DRUG SUBSTANCE (POOL OF PURIFIED DIPHTHERIA TOXOID, SIIL)»: the drug substance block whose name shares most words."""
        said_text = self.qos_said(p)
        said = N.norm_words(said_text) if said_text else []
        best, score = None, 0
        for b, folder, name, maker in self.substance_folders:
            s = len(set(said) & set(N.norm_words(name + ' ' + folder)))
            if s > score:
                best, score = folder, s
        return best or (said_text.strip().title() if said_text else 'Drug substance')

    # ---- sizes
    def page_bytes(self):
        """About how many bytes each kept page takes: its content and its pictures, from the parts after the OCR."""
        import pikepdf
        out = {}
        for part in self.w.load('parts.json', []):
            pdf = pikepdf.open(part['pdf'])
            for i, pg in enumerate(pdf.pages):
                n = 0
                try:
                    c = pg.obj.get('/Contents')
                    for x in (c if isinstance(c, pikepdf.Array) else [c]):
                        n += int(x.get('/Length', 0) or 0)
                    res = pg.obj.get('/Resources')

                    def walk(r, depth=0):
                        nonlocal n
                        if r is None or depth > 3 or '/XObject' not in r:
                            return
                        for k in r.XObject.keys():
                            x = r.XObject[k]
                            n += int(x.get('/Length', 0) or 0)
                            if x.get('/Subtype') == '/Form':
                                walk(x.get('/Resources'), depth + 1)
                    walk(res)
                except Exception:
                    pass
                out[part['from'] + i] = n
            pdf.close()
        return out

    def cut_large(self, limit):
        sizes = self.page_bytes()
        if not sizes:
            return
        for did in list(self.docs):
            pg = sorted(p for p, d in self.assign.items() if d == did)
            total = sum(sizes.get(p, 0) for p in pg)
            if total <= limit * 0.95 or len(pg) < 2:
                continue
            k = -(-total // int(limit * 0.9))
            d = self.docs[did]
            bounds, acc, target, cuts = [], 0, total / k, []
            for p in pg:
                acc += sizes.get(p, 0)
                if acc >= target * (len(cuts) + 1) and len(cuts) < k - 1:
                    cuts.append(p)
            pieces, start = [], 0
            for c in cuts:
                i = pg.index(c) + 1
                pieces.append(pg[start:i])
                start = i
            pieces.append(pg[start:])
            stem = d['path'][:-4]
            for i, piece in enumerate(pieces, 1):
                nd = self.new_doc(d['ctd'], d['title'].replace(' – ', f' (part {i} of {len(pieces)}) – ', 1) if ' – ' in d['title'] else f"{d['title']} (part {i} of {len(pieces)})",
                                  f'{stem} (part {i} of {len(pieces)}).pdf', (d['note'] + f' over {limit // 10**6} MB in one file: cut into parts').strip())
                self.put(nd, piece)
            del self.docs[did]
            self.findings.append({'kind': 'too_large', 'doc': d['path'], 'bytes': total, 'parts': len(pieces)})

    def propose(self, limit=SIZE_LIMIT):
        self.findings, self.substance_folders, self.product_folder = [], [], None
        order = sorted(self.blocks, key=lambda b: 0 if self.kind(b) in ('3S', '3P') else 1)   # substances and product first: the
        for b in order:                                                                         # annexures and 2.3.S need their names
            self.plan_block(b)
        self.cut_large(limit)
        for p in self.dropped:
            self.assign.pop(p, None)
            self.removed.pop(p, None)


def apply(planner, edits):
    """The decisions laid over the proposal, in order: {pages, drop: why} or {pages, path, ctd, title, note}."""
    used = []
    for e in edits:
        pages = parse_ranges(e['pages'])
        if 'drop' in e:
            planner.drop(pages, e['drop'])
            for p in pages:
                planner.removed[p] = e['drop']
            used.append(e)
            continue
        did = None
        for k, d in planner.docs.items():
            if d['path'] == e['path']:
                did = k
                d.update({x: e[x] for x in ('ctd', 'title', 'note') if x in e})
                d['by'] = 'decision'
        if did is None:
            did = planner.new_doc(e.get('ctd', ''), e.get('title', e['path']), e['path'], e.get('note', ''), by='decision')
        planner.put(did, pages)
        used.append(e)
    return used


def result(planner):
    docs = []
    for did, d in planner.docs.items():
        pg = sorted(p for p, x in planner.assign.items() if x == did)
        if pg:
            docs.append({'path': d['path'], 'ctd': d['ctd'], 'title': d['title'], 'pages': pg, 'note': d['note'], 'by': d['by']})
    docs.sort(key=lambda d: d['pages'][0])
    removed = [{'page': p, 'why': w} for p, w in sorted(planner.removed.items())]
    return docs, removed


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    dec = w.decisions()
    pl = Planner(w)
    limit = int(dec.get('size_limit_mb', SIZE_LIMIT // 10**6)) * 10**6
    pl.propose(limit)
    proposal, proposal_removed = result(pl)
    used = apply(pl, dec.get('plan', []))
    docs, removed = result(pl)
    for d in docs:
        if d['path'] in (dec.get('notes') or {}):
            d['note'] = dec['notes'][d['path']]
    placed = {p for d in docs for p in d['pages']} | {r['page'] for r in removed}
    kept = set()
    for a, b in w.load('repeats.json')['kept']:
        kept |= set(range(a, b + 1))
    missing = sorted(kept - placed)
    w.save('plan.json', {'docs': docs, 'removed': removed, 'edits': used, 'findings': pl.findings,
                         'proposal': {'docs': proposal, 'removed': proposal_removed}, 'missing': missing})
    say(f'{len(docs)} مستندًا · {sum(len(d["pages"]) for d in docs)} صفحة فيها · {len(removed)} صفحة تُركت · '
        f'{len(used)} قرارًا من ملف القرارات · صفحات بلا مكان: {len(missing)}')
    return docs, removed


def compare(mine, ref):
    """Two plans side by side: the documents with the same pages and the same path, the same pages under another path, and the
    rest; the pages left out by one and not the other."""
    by_pages = {tuple(d['pages']): d for d in mine}
    same, renamed, other = [], [], []
    for d in ref:
        m = by_pages.get(tuple(d['pages']))
        if m and m['path'] == d['path']:
            same.append(d)
        elif m:
            renamed.append((d, m))
        else:
            other.append(d)
    return same, renamed, other


def record(proposal, proposal_removed, wanted, wanted_removed):
    """The decisions that turn the program's proposal into a wanted plan (a person's corrections, or a plan made by hand):
    an edit for every wanted document the proposal does not give as it is (pages, CTD number, path, title), a «drop» for every
    page left out that the proposal keeps; the notes apart. Returns (edits, notes)."""
    have = {(tuple(d['pages']), d['path'], d['ctd'], d['title']) for d in proposal}
    note_of = {d['path']: d.get('note', '') for d in proposal}
    edits, notes = [], {}
    for d in sorted(wanted, key=lambda d: d['pages'][0]):
        if (tuple(d['pages']), d['path'], d['ctd'], d['title']) not in have:
            edits.append({'pages': ranges(d['pages']).replace('–', '-'), 'path': d['path'], 'ctd': d['ctd'], 'title': d['title']})
        if d.get('note') and d['note'] != note_of.get(d['path'], ''):
            notes[d['path']] = d['note']
    kept_out = {r['page'] for r in proposal_removed}
    run, why = [], None
    for r in sorted(wanted_removed, key=lambda r: r['page']):
        if r['page'] in kept_out:
            continue
        if run and r['page'] == run[-1] + 1 and r['why'] == why:
            run.append(r['page'])
            continue
        if run:
            edits.append({'pages': ranges(run).replace('–', '-'), 'drop': why})
        run, why = [r['page']], r['why']
    if run:
        edits.append({'pages': ranges(run).replace('–', '-'), 'drop': why})
    return edits, notes
