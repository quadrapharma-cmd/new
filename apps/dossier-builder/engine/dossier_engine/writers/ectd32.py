"""Writer 2 — eCTD 3.2.2 sequence with the EG provisional regional profile.

Input: an Envelope, product attributes and a list of Doc (node + file).
Output: <out>/<sequence>/ with m1/eg, m2–m5, util, index.xml, index-md5.txt.
Rules applied here (others live in the validator):
  * element names and order from the DTDs; folders/files from ICH App. 4 and
    the EG folder map; names lower-case a-z 0-9 '-' (ICH SPEC p.2-3)
  * file name <= 64, folder name <= 64, path from DDDD <= 180 (EG-PF-15.3/4/5)
  * MD5 for each leaf and for index.xml (ICH SPEC p.5-2)
"""
import csv, hashlib, os, re, shutil, uuid
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from . import dtd

APP = Path(__file__).resolve().parents[3]
REPO = APP.parents[1]
DEFAULT_PROFILE = REPO / 'docs' / 'ctd' / 'ectd' / 'EG-PROVISIONAL-PROFILE-v0'
APP4 = APP / 'rulepacks' / 'ich.ectd.v322' / 'app4.csv'
MAX_NAME, MAX_PATH = 64, 180
REG_TYPE = {'own': 'local', 'toll': 'toll', 'f_toll': 'f-toll', 'under_licence': 'under-license',
            'imported': 'imported-finished', 'imported_bulk': 'imported-bulk'}


class WriterError(ValueError):
    pass


@dataclass
class Envelope:
    identifier: str              # application UUID, identical in every sequence
    submission_type: str         # vocab/submission-type.yaml, e.g. maa
    tracking: list               # EDA procedure tracking number(s)
    unit: str                    # initial / response / …
    applicant: str
    invented_name: str
    registration: str            # local / toll / … (REG_TYPE maps from profile.licence)
    marketing: str               # local / tender / export / hospital
    inn: list
    sequence: str = '0000'
    related_sequence: list = None
    description: str = ''
    mode: str = None


@dataclass
class Doc:
    node: str                    # '1.2.1', '3.2.S.4.1', …
    file: str                    # source PDF
    title: str
    substance: str = None        # 3.2.S / 2.3.S
    manufacturer: str = None
    pi_type: str = None          # 1.3.1: spc / pl / …
    lang: str = None             # 1.3.1: en / ar
    indication: str = None       # 2.7.3 / 5.3.5 (defaults to Product.indication)
    study: str = None            # v4: 'study id_study title' keyword (M5 study reports)
    doc_type: str = None         # v4: ICH document type code for study documents
    control: str = None          # v4: ICH type-of-control code (5.3.5.1)
    excipient: str = None        # v4: excipient keyword (3.2.P.4 / 3.2.A.3)
    uuid: str = None             # v4: document UUID (reuse keeps it identical)
    name: str = None             # optional file stem override
    operation: str = 'new'       # new | replace | delete (lifecycle)
    modified_file: str = None    # 3.2.2 replace/delete: '<seq>/<index.xml|m1/eg/eg-regional.xml>#<leaf ID>'
    leaf_id: str = None          # keep a stable leaf ID (lifecycle history)
    doc_id: str = None           # dossier document id (lifecycle history)
    cou_replaces: str = None     # 4.0 replace: id of the context of use being replaced


@dataclass
class Product:
    name: str
    dosageform: str
    manufacturer: str
    indication: str = None       # m2-7-3 / m5-3-5 (#REQUIRED in the ICH DTD)


def slug(s, maxlen=40):
    s = re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')
    return (s[:maxlen].rstrip('-')) or 'x'


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class Profile32:
    """The swappable regional profile (provisional now, official at P4)."""

    def __init__(self, root=DEFAULT_PROFILE):
        self.root = Path(root)
        d = self.root / 'util' / 'dtd'
        ich = (d / 'ich-ectd-3-2.dtd').read_text(encoding='utf-8')
        eg = ''.join((d / f).read_text(encoding='utf-8') for f in ('eg-regional.dtd', 'eg-envelope.mod', 'eg-leaf.mod'))
        self.ich_children, self.ich_parents = dtd.read(ich)
        self.eg_children, self.eg_parents = dtd.read(eg)
        self.m1 = {}
        for r in csv.DictReader(open(self.root / 'folders.csv', encoding='utf-8')):
            if r['ctd_number'] and r['element']:
                self.m1[r['ctd_number']] = r
        self.app4 = list(csv.DictReader(open(APP4, encoding='utf-8')))

    def ich_element(self, node):
        stem = 'm' + node.lower().replace('.', '-') + '-'
        hits = [e for e in self.ich_children if e.startswith(stem) and not e[len(stem)].isdigit()]
        if len(hits) != 1:
            raise WriterError(f'no unique ICH element for {node}: {hits}')
        return hits[0]

    def ich_location(self, element):
        """(directory, default file name) from App. 4."""
        rows = [r for r in self.app4 if r['element'] == element]
        ds = sorted((r['path'] for r in rows if r['kind'] == 'D'), key=len)
        fs = [r['path'] for r in rows if r['kind'] == 'F']
        if ds:
            return ds[0], (os.path.basename(fs[0]) if len(fs) == 1 else None)
        if fs:
            return os.path.dirname(fs[0]), (os.path.basename(fs[0]) if len(fs) == 1 else None)
        raise WriterError(f'{element}: not in ICH App. 4')


class _Node:
    def __init__(self, name, attrs=None):
        self.name, self.attrs, self.kids, self.leaves = name, attrs or {}, [], []

    def child(self, name, attrs, order):
        for k in self.kids:
            if k.name == name and k.attrs == (attrs or {}):
                return k
        n = _Node(name, attrs)
        self.kids.append(n)
        self.kids.sort(key=lambda k: order.index(k.name) if k.name in order else 999)
        return n


def _leaf_xml(leaf, ind):
    if leaf['op'] == 'delete':        # ICH SPEC Table 6-3: no file, empty checksum (and checksum-type outside Japan)
        head = f'{ind}<leaf ID="{leaf["id"]}" operation="delete" checksum="" checksum-type="" xlink:type="simple"'
    else:
        head = (f'{ind}<leaf ID="{leaf["id"]}" operation="{leaf["op"]}" checksum="{leaf["md5"]}" '
                f'checksum-type="md5" xlink:type="simple" xlink:href={quoteattr(leaf["href"])}')
    if leaf.get('modified'):
        head += f' modified-file={quoteattr(leaf["modified"])}'
    return f'{head}>\n{ind}  <title>{escape(leaf["title"])}</title>\n{ind}</leaf>\n'


def _modified(d, xml):
    """Doc.modified_file 'SSSS#LEAFID' -> path relative to the XML that holds the new leaf."""
    if not d.modified_file:
        return None
    seq, lid = d.modified_file.split('#', 1)
    return f'../{seq}/index.xml#{lid}' if xml == 'index' else f'../../../{seq}/m1/eg/eg-regional.xml#{lid}'


def _render(node, children, ind='  '):
    attrs = ''.join(f' {k}={quoteattr(v)}' for k, v in node.attrs.items())
    out = f'{ind}<{node.name}{attrs}>\n'
    for lf in node.leaves:
        out += _leaf_xml(lf, ind + '  ')
    for k in node.kids:
        out += _render(k, children, ind + '  ')
    return out + f'{ind}</{node.name}>\n'


def _leaf_id(seq, href):
    return 'id' + uuid.uuid5(uuid.NAMESPACE_URL, f'{seq}/{href}').hex[:20]


def rel_path(d, product, profile):
    """v3.2.2 path of a document relative to the sequence folder."""
    if d.node.startswith('1.'):
        row = profile.m1.get(d.node)
        if not row or row['kind'] not in ('leaf container', 'pi-doc container'):
            raise WriterError(f'{d.node}: not a document heading in the EG M1 map')
        directory = row['directory']
        pat = (row['file_pattern'] or '').split(' | ')[0]
        stem = d.name or (os.path.basename(pat).split('-VAR')[0].split('.')[0] if pat else slug(d.title))
        if d.node == '1.3.1':
            if not (d.pi_type and d.lang):
                raise WriterError('1.3.1 needs pi_type and lang')
            directory = f'{directory}/{d.lang}'
            stem = d.name or d.pi_type
        return f'{directory}/{stem}.pdf'
    el = profile.ich_element(d.node)
    directory, default = profile.ich_location(el)
    if d.node.startswith(('3.2.S', '2.3.S')) and 'substance-1-manufacturer-1' in directory:
        if not (d.substance and d.manufacturer):
            raise WriterError(f'{d.node} needs substance and manufacturer')
        directory = directory.replace('substance-1-manufacturer-1',
                                      f'{slug(d.substance, 20)}-{slug(d.manufacturer, 20)}')
    directory = directory.replace('product-1', slug(product.name, 30)).replace('/excipient-1', '')
    stem = d.name or (default.rsplit('.', 1)[0] if default else slug(d.title))
    return f'{directory}/{stem}.pdf'


def write(out_dir, envelope: Envelope, product: Product, docs, profile: Profile32 = None):
    """Writes the sequence; returns a report dict {path, files, problems}."""
    profile = profile or Profile32()
    seq = envelope.sequence
    if not re.fullmatch(r'\d{4}', seq):
        raise WriterError('sequence must be 4 digits')
    base = Path(out_dir) / seq
    if base.exists():
        raise WriterError(f'{base} exists — a sequence is never overwritten')
    problems, placed, used = [], [], set()

    for d in docs:
        if d.operation not in ('new', 'replace', 'delete'):
            raise WriterError(f'operation {d.operation!r} not supported (append is not used in EG: EG-BP-E06)')
        if d.operation in ('replace', 'delete') and not d.modified_file:
            raise WriterError(f'{d.node}: {d.operation} needs modified_file (ICH SPEC Table 6-3)')
        if d.operation == 'delete':
            placed.append((d, None))
            continue
        if not Path(d.file).is_file():
            raise WriterError(f'missing file {d.file}')
        rel = rel_path(d, product, profile)
        n, k = rel, 2
        while n in used:                          # second document in the same heading
            n = rel[:-4] + f'-{k}.pdf'
            k += 1
        used.add(n)
        placed.append((d, n))

    # limits (EG-PF-15.3/15.4/15.5)
    for d, rel in placed:
        if rel is None:
            continue
        parts = rel.split('/')
        if len(parts[-1]) > MAX_NAME:
            problems.append(('EG-PF-15.4', rel, f'file name {len(parts[-1])} > {MAX_NAME}'))
        for p in parts[:-1]:
            if len(p) > MAX_NAME:
                problems.append(('EG-PF-15.5', rel, f'folder {p!r} > {MAX_NAME}'))
        if len(f'{seq}/{rel}') > MAX_PATH:
            problems.append(('EG-PF-15.3', rel, f'path {len(seq + "/" + rel)} > {MAX_PATH}'))
    if problems:
        raise WriterError('; '.join(f'{c} {r}: {m}' for c, r, m in problems))

    # copy files
    for d, rel in placed:
        if rel is None:
            continue
        dst = base / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(d.file, dst)

    # ---- eg-regional.xml ----
    history = []
    eg_root = _Node('m1-eg')
    for d, rel in placed:
        if not d.node.startswith('1.'):
            continue
        el = profile.m1[d.node]['element']
        chain = [el]
        while profile.eg_parents.get(chain[-1]) not in (None, 'm1-eg'):
            chain.append(profile.eg_parents[chain[-1]])
        cur = eg_root
        for name in reversed(chain):
            cur = cur.child(name, {}, profile.eg_children.get(cur.name, []))
        href = rel[len('m1/eg/'):] if rel else None
        leaf = dict(id=d.leaf_id or _leaf_id(seq, rel or d.modified_file), op=d.operation,
                    md5=md5(base / rel) if rel else '', href=href, title=d.title, modified=_modified(d, 'regional'))
        history.append(_hist(d, leaf, rel, 'regional'))
        if d.node == '1.3.1':
            pi = _Node('pi-doc', {'xml:lang': d.lang, 'type': d.pi_type, 'country': 'eg'})
            pi.leaves.append(leaf)
            cur.kids.append(pi)
        else:
            cur.leaves.append(leaf)
    if not any(k.name == 'm1-0-cover' for k in eg_root.kids):
        raise WriterError('1.0 cover letter is mandatory in every sequence')
    e = envelope
    rel_seqs = e.related_sequence or [seq]
    env = ['    <envelope country="eg">',
           f'      <identifier>{escape(e.identifier)}</identifier>',
           f'      <submission type="{e.submission_type}"' + (f' mode="{e.mode}"' if e.mode else '') + '>',
           '        <procedure-tracking>'] + \
          [f'          <number>{escape(t)}</number>' for t in e.tracking] + \
          ['        </procedure-tracking>', '      </submission>',
           f'      <submission-unit type="{e.unit}"/>',
           f'      <applicant>{escape(e.applicant)}</applicant>',
           '      <agency code="EG-EDA"/>',
           f'      <invented-name>{escape(e.invented_name)}</invented-name>',
           f'      <registration type="{e.registration}"/>',
           f'      <marketing type="{e.marketing}"/>'] + \
          [f'      <inn>{escape(i)}</inn>' for i in e.inn] + \
          [f'      <sequence>{seq}</sequence>'] + \
          [f'      <related-sequence>{r}</related-sequence>' for r in rel_seqs] + \
          [f'      <submission-description>{escape(e.description)}</submission-description>', '    </envelope>']
    regional = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE eg-backbone SYSTEM "../../util/dtd/eg-regional.dtd">\n'
                '<?xml-stylesheet type="text/xsl" href="../../util/style/eg-regional.xsl"?>\n'
                '<!-- PROVISIONAL EG profile v0: conforms to EDA drafts + ICH; not an EDA-issued DTD. -->\n'
                '<eg-backbone xmlns:xlink="http://www.w3c.org/1999/xlink">\n  <eg-envelope>\n'
                + '\n'.join(env) + '\n  </eg-envelope>\n' + _render(eg_root, profile.eg_children) + '</eg-backbone>\n')
    reg_path = base / 'm1' / 'eg' / 'eg-regional.xml'
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(regional, encoding='utf-8')

    # ---- index.xml ----
    root = _Node('ectd:ectd')
    m1 = root.child('m1-administrative-information-and-prescribing-information', {}, profile.ich_children['ectd:ectd'])
    m1.leaves.append(dict(id=_leaf_id(seq, 'm1/eg/eg-regional.xml'), op='new', md5=md5(reg_path),
                          href='m1/eg/eg-regional.xml', title='EG Module 1'))
    for d, rel in placed:
        if d.node.startswith('1.'):
            continue
        el = profile.ich_element(d.node)
        chain = [el]
        while profile.ich_parents.get(chain[-1]) not in (None, 'ectd:ectd'):
            chain.append(profile.ich_parents[chain[-1]])
        cur = root
        for name in reversed(chain):
            attrs = {}
            if name in ('m3-2-s-drug-substance', 'm2-3-s-drug-substance'):
                attrs = {'substance': d.substance, 'manufacturer': d.manufacturer}
            elif name in ('m3-2-p-drug-product', 'm2-3-p-drug-product'):
                attrs = {'product-name': product.name, 'dosageform': product.dosageform,
                         'manufacturer': product.manufacturer}
            elif name in ('m2-7-3-summary-of-clinical-efficacy', 'm5-3-5-reports-of-efficacy-and-safety-studies'):
                ind = d.indication or product.indication
                if not ind:
                    raise WriterError(f'{d.node} needs an indication (ICH DTD #REQUIRED)')
                attrs = {'indication': ind}
            cur = cur.child(name, attrs, profile.ich_children.get(cur.name, []))
        leaf = dict(id=d.leaf_id or _leaf_id(seq, rel or d.modified_file), op=d.operation,
                    md5=md5(base / rel) if rel else '', href=rel, title=d.title, modified=_modified(d, 'index'))
        cur.leaves.append(leaf)
        history.append(_hist(d, leaf, rel, 'index'))
    body = ''.join(_render(k, profile.ich_children) for k in root.kids)
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<?xml-stylesheet type="text/xsl" href="util/style/ectd-2-0.xsl"?>\n'
             '<!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd">\n'
             '<ectd:ectd xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">\n'
             + body + '</ectd:ectd>\n')
    (base / 'index.xml').write_text(index, encoding='utf-8')
    (base / 'index-md5.txt').write_text(md5(base / 'index.xml'), encoding='ascii')

    # ---- util ----
    for sub in ('dtd', 'style'):
        shutil.copytree(profile.root / 'util' / sub, base / 'util' / sub)
    files = sorted(str(p.relative_to(base)) for p in base.rglob('*') if p.is_file())
    return {'path': str(base), 'files': files, 'leaves': len(placed) + 1, 'problems': [], 'history': history}


def _hist(d, leaf, rel, xml):
    from ..lifecycle import location_key
    return {'doc_id': d.doc_id, 'key': list(location_key(d)), 'leaf_id': leaf['id'], 'href': rel, 'xml': xml,
            'op': d.operation, 'replaces': d.modified_file.split('#', 1)[1] if d.modified_file else None,
            'node': d.node, 'title': d.title}
