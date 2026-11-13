"""Import an eCTD 3.2.2 application's sequences into a dossier (updates list, item 24): each sequence's leaves become the dossier's
documents in their items (a «replace» a new version of the document it replaces, a «delete» withdrawn), the sequences become the
dossier's submitted history — frozen, with their envelope — and their folders are kept, so the next sequence the program makes
continues the lifecycle (the right number, «replace» and «delete» against the imported leaves, references to their files).
Egypt's (m1/eg) and the EU's (m1/eu) Module 1 are read; Modules 2–5 are ICH's everywhere."""
import csv, posixpath, re
from pathlib import Path
from lxml import etree

XLINK = '{http://www.w3c.org/1999/xlink}href'
XMLLANG = '{http://www.w3.org/XML/1998/namespace}lang'


def _local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


class Maps:
    """Element → CTD section, from the profiles the writers use (ICH Appendix 4, the EG folders table, the EU M1 table)."""

    def __init__(self):
        from .writers import ectd32 as w32, ectd32_eu as w32eu
        p = w32.Profile32()
        self.ich = {}
        for r in p.app4:
            if r.get('kind') == 'D' and r.get('ctd') and r.get('element'):
                self.ich.setdefault(r['element'], r['ctd'])
        self.files = {}                          # a section with no element of its own (3.2.S.1.1 under 3.2.S.1): App. 4 names its file
        for r in p.app4:
            if r.get('kind') == 'F' and r.get('ctd') and r.get('path', '').endswith('.pdf'):
                d, b = posixpath.split(r['path'])
                self.files[(posixpath.basename(d), b[:-4])] = r['ctd']
        self.eg = {r['element']: k for k, r in p.m1.items()}
        self.eu = {}
        m1 = Path(w32eu.DEFAULT_PROFILE) / 'm1.csv'
        if m1.exists():
            for r in csv.DictReader(open(m1, encoding='utf-8')):
                self.eu.setdefault(r['element'], r['node'])

    def file_node(self, href):
        """The App. 4 section of a file by its folder and name («32s1-gen-info/nomenclature.pdf» → 3.2.S.1.1; a second file there,
        «nomenclature-2.pdf», too), else None."""
        d, b = posixpath.split(href or '')
        stem, tail = posixpath.splitext(b)[0], posixpath.basename(d)
        best = None
        for (t, s), ctd in self.files.items():
            if t == tail and (stem == s or (stem.startswith(s + '-') and stem[len(s) + 1:].isdigit())) and (best is None or len(s) > best[0]):
                best = (len(s), ctd)
        return best[1] if best else None


def read_sequence(seq, maps):
    """{'envelope': {...}, 'region': 'eg'|'eu'|None, 'leaves': [{node, op, href, title, checksum, leaf_id, modified, substance,
    manufacturer, pi_type, lang, country, study, xml}]} — every leaf of index.xml and of the regional XML, its href from the sequence."""
    seq = Path(seq)
    out, env, region = [], {}, None
    files = [('index', seq / 'index.xml', maps.ich)]
    for reg in ('eg', 'eu'):
        f = seq / 'm1' / reg / f'{reg}-regional.xml'
        if f.exists():
            region = reg
            files.append(('regional', f, maps.eg if reg == 'eg' else maps.eu))
    for xml, path, table in files:
        tree = etree.parse(str(path), etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False))
        base = path.parent.relative_to(seq).as_posix()
        if xml == 'regional':
            env = envelope(tree)
        for lf in tree.iter():
            if _local(lf.tag) != 'leaf':
                continue
            node, attrs, el = None, {}, lf.getparent()
            while el is not None:
                name = _local(el.tag)
                node = node or table.get(name)
                if name == 'node-extension' and 'study' not in attrs:     # a study's own node: its title is the study identifier
                    t = next((c for c in el if _local(c.tag) == 'title'), None)
                    attrs['study'] = (t.text or '').strip() if t is not None else None
                if name in ('m3-2-s-drug-substance', 'm2-3-s-drug-substance'):
                    attrs.setdefault('substance', el.get('substance'))
                    attrs.setdefault('manufacturer', el.get('manufacturer'))
                if name in ('pi-doc', 'specific', 'm1-3-1-spc-label-pl') or el.get('type') or el.get(XMLLANG) or el.get('country'):
                    attrs.setdefault('pi_type', el.get('type') if name == 'pi-doc' else None)
                    attrs.setdefault('lang', el.get(XMLLANG))
                    attrs.setdefault('country', el.get('country') if el.get('country') not in (None, 'common', 'ema') else None)
                el = el.getparent()
            href = lf.get(XLINK) or ''
            rel = posixpath.normpath(posixpath.join(base, href)) if href and base != '.' else href
            if xml == 'index':
                node = maps.file_node(rel) or node
            t = next((c for c in lf if _local(c.tag) == 'title'), None)
            out.append({'node': node, 'op': lf.get('operation') or 'new', 'href': rel, 'title': (t.text or '').strip() if t is not None else '',
                        'checksum': (lf.get('checksum') or '').lower(), 'leaf_id': lf.get('ID'), 'modified': lf.get('modified-file'),
                        'xml': xml, **{k: v for k, v in attrs.items() if v}})
    return {'envelope': env, 'region': region, 'leaves': out}


def envelope(tree):
    """The regional envelope's type, unit, description, tracking number and related sequence, read leniently."""
    out = {}
    for el in tree.iter():
        n = _local(el.tag)
        txt = (el.text or '').strip()
        if n in ('submission', 'submission-type') and (el.get('type') or txt):
            out.setdefault('type', el.get('type') or txt)
        elif n == 'submission-unit' and (el.get('type') or txt):
            out.setdefault('unit', el.get('type') or txt)
        elif n == 'submission-description' and txt:
            out.setdefault('description', txt)
        elif n in ('tracking', 'procedure-tracking', 'number') and txt:
            out.setdefault('tracking', txt)
        elif n == 'related-sequence' and txt:
            out.setdefault('related', txt)
        elif n == 'identifier' and txt:                 # the application's UUID: the same in every sequence of its lifecycle
            out.setdefault('identifier', txt)
    return out


def replaced_leaf(modified):
    """'../0000/index.xml#ID' → ('0000', 'ID')."""
    m = re.search(r'(\d{4})/[^#]*#(.+)$', modified or '')
    return (m.group(1), m.group(2)) if m else (None, None)
