"""Writer — a GCC eCTD 3.2.2 sequence: GCC Module 1 v1.5 (SFDA, November 2015) on its own DTD (docs/ctd/ectd/GCC-M1-1.5-PROFILE),
for the Gulf authorities (updates list, item 39).

The DTD is the one the specification prints in its Appendix 6 (gc-regional.dtd 1.1, gc-envelope.mod, gc-leaf.mod); the folders and
file names are its Appendix 2 (the profile's m1.csv); the envelope and its codes its Appendices 1 and 5. Output: <out>/<sequence>/
with m1/gc/gc-regional.xml, m2–m5, util, index.xml, index-md5.txt:
  * gc-regional.xml in the DTD's element order: 1.0, 1.2, 1.3.4, 1.3.5, 1.9 and additional data under specific/@country; 1.3.1–1.3.3
    under pi-doc (language, type spc|label|pil, country); the other sections hold their leaves
  * one envelope per destination (sa, ae, kw, bh, om, qa, ye — or common), each with its receiving agency (App. 5)
  * «CC» in a name is the destination's code, or «common» when the document is for every GCC country (App. 2)
  * lower-case names, file and folder ≤ 64, path ≤ 180, MD5 for each leaf and for index.xml (ICH)"""
import csv, posixpath
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape
from . import dtd
from .ectd32 import (APP4, REPO, Product, Profile32, WriterError, _Node, _hist, _leaf_id, _render, copy_files, finish,
                     ich_rel_path, md5, place, slug, write_index)

DEFAULT_PROFILE = REPO / 'docs' / 'ctd' / 'ectd' / 'GCC-M1-1.5-PROFILE'
REGIONAL = 'm1/gc/gc-regional.xml'
AGENCY = {'ae': 'AE-MOH', 'bh': 'BH-MOH', 'kw': 'KW-MOH', 'om': 'OM-MOH', 'qa': 'QA-NHA', 'sa': 'SA-SFDA', 'ye': 'YE-MOPHP'}
PI_TYPE = {'1.3.1': 'spc', '1.3.2': 'label', '1.3.3': 'pil'}


class ProfileGCC(Profile32):
    """GCC M1 v1.5: the DTD of its Appendix 6 and the folder map of its Appendix 2, over the ICH DTD and App. 4."""

    def __init__(self, root=DEFAULT_PROFILE):
        from .ectd32_eu import _attr, _entity
        self.root = Path(root)
        d = self.root / 'util' / 'dtd'
        self.ich_children, self.ich_parents = dtd.read((d / 'ich-ectd-3-2.dtd').read_text(encoding='utf-8'))
        gc = ''.join((d / f).read_text(encoding='utf-8') for f in ('gc-regional.dtd', 'gc-envelope.mod', 'gc-leaf.mod'))
        self.gc_children, self.gc_parents = dtd.read(gc)
        self.m1 = {r['node']: r for r in csv.DictReader(open(self.root / 'm1.csv', encoding='utf-8'))}
        self.app4 = list(csv.DictReader(open(APP4, encoding='utf-8')))
        self.values = {'countries': _entity(gc, 'countries'), 'env_countries': _entity(gc, 'env-countries'),
                       'languages': _entity(gc, 'languages'), 'submission_types': _attr(gc, 'submission', 'type'),
                       'units': _attr(gc, 'submission-unit', 'type'), 'agencies': _attr(gc, 'agency', 'code'),
                       'procedures': _attr(gc, 'procedure', 'type')}


_PROFILE = None


def default_profile():
    global _PROFILE
    if _PROFILE is None:
        _PROFILE = ProfileGCC()
    return _PROFILE


@dataclass
class EnvelopeGCC:
    countries: list                    # the destinations: one envelope each (sa, ae, …), or ['common']
    application: list                  # the application number(s) the GCC issued for the sponsor and the product (App. 1)
    applicant: str
    submission_type: str               # gc-envelope.mod: new-gen, new-nce, var-type1, renewal, …
    unit: str                          # initial | response | additional-info | closing | correction | reformat
    procedure: str                     # gcc | national
    invented_names: list
    inn: list = field(default_factory=list)
    atc: list = field(default_factory=list)
    sequence: str = '0000'
    related_sequence: list = None
    description: str = ''


def code(country):
    return (country or '').strip().lower()


def home(envelope):
    """Where a document that names no country goes: the one destination of a national procedure, «common» otherwise (App. 2)."""
    return envelope.countries[0] if envelope.procedure == 'national' and len(envelope.countries) == 1 else 'common'


def rel_path(d, envelope, product, profile):
    row = profile.m1.get(d.node)
    if not row:
        return ich_rel_path(d, product, profile)
    cc = code(d.country) or home(envelope)
    ll = (d.lang or 'en').lower()
    if row['kind'] == 'pi' and ll not in profile.values['languages']:
        raise WriterError(f'{d.node}: the language is one of {", ".join(profile.values["languages"])}')
    directory = row['directory'].replace('{cc}', cc).replace('{ll}', ll)
    stem = d.name or row['stem'].replace('{cc}', cc)
    return f'{directory}/{stem}.pdf'


def _envelopes(e, seq, profile):
    out = []
    for cc in e.countries:
        cc = code(cc)
        if cc not in profile.values['env_countries']:
            raise WriterError(f'envelope country {cc!r} is not a GCC destination ({", ".join(profile.values["env_countries"])})')
        agency = AGENCY.get(cc)
        if not agency:
            raise WriterError('«common» has no receiving agency: name the destinations (sa, ae, kw, bh, om, qa, ye)')
        rel = e.related_sequence or []
        out.append('\n'.join([f'    <envelope country="{cc}">',
                              '      <application>' + ''.join(f'<number>{escape(n)}</number>' for n in e.application) + '</application>',
                              f'      <applicant>{escape(e.applicant)}</applicant>',
                              f'      <agency code="{agency}"/>'] +
                             [f'      <atc>{escape(a)}</atc>' for a in e.atc] +
                             [f'      <submission type="{e.submission_type}"/>',
                              f'      <submission-unit type="{e.unit}"/>',
                              f'      <procedure type="{e.procedure}"/>'] +
                             [f'      <invented-name>{escape(n)}</invented-name>' for n in e.invented_names] +
                             [f'      <inn>{escape(i)}</inn>' for i in e.inn] +
                             [f'      <sequence>{seq}</sequence>'] +
                             [f'      <related-sequence>{r}</related-sequence>' for r in rel] +
                             [f'      <submission-description>{escape(e.description or "")}</submission-description>', '    </envelope>']))
    return out


def write(out_dir, envelope: EnvelopeGCC, product: Product, docs, profile: ProfileGCC = None, links=None):
    profile = profile or default_profile()
    e, seq = envelope, envelope.sequence
    for k, allowed in (('submission_type', 'submission_types'), ('unit', 'units'), ('procedure', 'procedures')):
        if getattr(e, k) not in profile.values[allowed]:
            raise WriterError(f'{k} {getattr(e, k)!r} is not one of {", ".join(profile.values[allowed])} (GCC M1 v1.5 App. 5)')
    base = Path(out_dir) / seq
    if base.exists():
        raise WriterError(f'{base} exists — a sequence is never overwritten')
    placed = place(docs, lambda d: rel_path(d, e, product, profile), seq, 'GCC', 'the program writes new, replace and delete')
    copy_files(base, placed)
    linked = None
    if links is not None:
        from ..links import relink
        linked = relink(base, placed, links)
    history, root = [], _Node('m1-gc')
    for d, rel in placed:
        row = profile.m1.get(d.node)
        if not row:
            continue
        chain = [row['element']]
        while profile.gc_parents.get(chain[-1]) not in (None, 'm1-gc'):
            chain.append(profile.gc_parents[chain[-1]])
        cur = root
        for name in reversed(chain):
            cur = cur.child(name, {}, profile.gc_children.get(cur.name, []))
        cc = code(d.country) or home(e)
        if row['kind'] == 'pi':
            cur = cur.child('pi-doc', {'xml:lang': (d.lang or 'en').lower(), 'type': PI_TYPE[d.node], 'country': cc}, ['pi-doc'])
        elif row['kind'] == 'specific':
            cur = cur.child('specific', {'country': cc}, ['specific'])
        modified = None
        if d.modified_file:
            s, lid = d.modified_file.split('#', 1)
            modified = f'../../../{s}/{REGIONAL}#{lid}'
        leaf = dict(id=d.leaf_id or _leaf_id(seq, rel or d.modified_file), op=d.operation, md5=md5(base / rel) if rel else '',
                    href=(posixpath.relpath(rel, 'm1/gc') if d.ref else rel[len('m1/gc/'):]) if rel else None, title=d.title, modified=modified)
        cur.leaves.append(leaf)
        history.append(_hist(d, leaf, rel, 'regional'))
    if not any(k.name == 'm1-0-cover' for k in root.kids):
        raise WriterError('1.0 cover letter is mandatory in every sequence (m1-0-cover)')
    env = next((k for k in root.kids if k.name == 'm1-5-environrisk'), None)
    if env is not None and len(env.kids) > 1:
        raise WriterError('1.5.1 (non-GMO) and 1.5.2 (GMO) cannot both hold documents: the GCC DTD takes one of them')
    regional = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE gc:gc-backbone SYSTEM "../../util/dtd/gc-regional.dtd">\n'
                '<gc:gc-backbone xmlns:gc="http://sfda.gov.sa" xmlns:xlink="http://www.w3c.org/1999/xlink" dtd-version="1.1">\n'
                '  <gc-envelope>\n' + '\n'.join(_envelopes(e, seq, profile)) + '\n  </gc-envelope>\n'
                + _render(root, profile.gc_children) + '</gc:gc-backbone>\n')
    reg_path = base / REGIONAL
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(regional, encoding='utf-8')
    write_index(base, seq, [(d, rel) for d, rel in placed if d.node not in profile.m1], product, profile, REGIONAL, 'GCC Module 1', history)
    return dict(finish(base, profile, placed, history), links=linked)
