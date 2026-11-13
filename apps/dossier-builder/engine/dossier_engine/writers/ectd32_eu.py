"""Writer — an EU eCTD 3.2.2 sequence: EU Module 1 v3.1.1 on the EMA's own DTD (docs/ctd/ectd/EU-M1-3.1.1-PROFILE).

Input: an EnvelopeEU, the product's attributes and a list of Doc (node + file; Doc.country, pi_type and lang where the section asks).
Output: <out>/<sequence>/ with m1/eu/eu-regional.xml, m2–m5, util, index.xml, index-md5.txt.
What is applied here (the validator reads all of it back from disk):
  * eu-regional.xml in the DTD's element order, with the specific / pi-doc wrappers (country; language and PI type) — SPEC 3.1.1 App. 1
  * the envelopes: one 'ema' for the centralised procedure, one per country otherwise, one UUID in all (VC 9.9, 14.1–14.3, 14.5)
  * the folders and names of SPEC 3.1.1 App. 2 (the profile's m1.csv) and ICH App. 4 for Modules 2–5; lower case a-z 0-9 '-'
  * file name <= 64, folder name <= 64, path from XXXX <= 180 (VC 15.3–15.5); MD5 for each leaf and for index.xml"""
import csv, re
from dataclasses import dataclass, field, replace
from pathlib import Path
from xml.sax.saxutils import escape
from . import dtd
from .ectd32 import (APP4, REPO, Product, Profile32, WriterError, _Node, _hist, _leaf_id, _render, copy_files, finish,
                     ich_rel_path, md5, place, slug, write_index)

DEFAULT_PROFILE = REPO / 'docs' / 'ctd' / 'ectd' / 'EU-M1-3.1.1-PROFILE'
REGIONAL = 'm1/eu/eu-regional.xml'
PROCEDURE = {'cp': 'centralised', 'dcp': 'decentralised', 'mrp': 'mutual-recognition', 'np': 'national'}
# SPEC 3.1.1 App. 2.4 — the receiving agency of each destination; DE-PEI (vaccines, blood products, sera, ATMPs…) is named by the user
AGENCY = {'at': 'AT-BASG', 'be': 'BE-FAMHP', 'bg': 'BG-BDA', 'cy': 'CY-PHS', 'cz': 'CZ-SUKL', 'de': 'DE-BFARM', 'dk': 'DK-DKMA',
          'ee': 'EE-SAM', 'el': 'EL-EOF', 'es': 'ES-AEMPS', 'fi': 'FI-FIMEA', 'fr': 'FR-ANSM', 'hr': 'HR-HALMED', 'hu': 'HU-OGYI',
          'ie': 'IE-HPRA', 'is': 'IS-IMCA', 'it': 'IT-AIFA', 'li': 'LI-LLV', 'lt': 'LT-SMCA', 'lu': 'LU-MINSANT', 'lv': 'LV-ZVA',
          'mt': 'MT-MEDAUTH', 'nl': 'NL-MEB', 'no': 'NO-NOMA', 'pl': 'PL-URPL', 'pt': 'PT-INFARMED', 'ro': 'RO-ANMMD', 'se': 'SE-MPA',
          'si': 'SI-JAZMP', 'sk': 'SK-SIDC', 'uk': 'UK-MHRA', 'xi': 'UK-MHRA', 'ema': 'EU-EMA', 'edqm': 'EU-EDQM'}
ISO = {'gr': 'el', 'gb': 'uk'}       # SPEC 3.1.1 App. 2.1: the destination code is the ISO 3166 one except Greece (el) and the UK (uk)
BASIS = ('generic', 'hybrid', 'biosimilar')


def code(country):
    """A country as the dossier keeps it (ISO 3166, any case) or an EU M1 code → the EU M1 code: GR → el, DE → de."""
    c = (country or '').strip().lower()
    return ISO.get(c, c)


def _entity(text, name):
    m = re.search(r'<!ENTITY\s+%\s+' + re.escape(name) + r'\s+"\(([^)]*)\)"', text)
    return [v.strip() for v in m.group(1).split('|')]


def _attr(text, element, attr):
    m = re.search(r'<!ATTLIST\s+' + re.escape(element) + r'\s(.*?)>', text, re.S)
    a = re.search(r'(?<![\w:-])' + re.escape(attr) + r'\s*\(([^)]*)\)', m.group(1), re.S)
    return [v.strip() for v in a.group(1).split('|')]


class ProfileEU(Profile32):
    """EU M1 3.1.1: the EMA's DTD and the folder map (m1.csv), over the ICH DTD and App. 4 (Modules 2–5 are the same everywhere).
    The allowed values (countries, languages, PI types, submission and unit types, agencies, procedures) are read from the DTD."""

    def __init__(self, root=DEFAULT_PROFILE):
        self.root = Path(root)
        d = self.root / 'util' / 'dtd'
        self.ich_children, self.ich_parents = dtd.read((d / 'ich-ectd-3-2.dtd').read_text(encoding='utf-8'))
        eu = ''.join((d / f).read_text(encoding='utf-8') for f in ('eu-regional.dtd', 'eu-envelope.mod', 'eu-leaf.mod'))
        self.eu_children, self.eu_parents = dtd.read(eu)
        self.m1 = {r['node']: r for r in csv.DictReader(open(self.root / 'm1.csv', encoding='utf-8'))}
        self.app4 = list(csv.DictReader(open(APP4, encoding='utf-8')))
        self.values = {'countries': _entity(eu, 'countries'), 'env_countries': _entity(eu, 'env-countries'),
                       'languages': _entity(eu, 'languages'), 'pi_types': _attr(eu, 'pi-doc', 'type'),
                       'submission_types': _attr(eu, 'submission', 'type'), 'modes': _attr(eu, 'submission', 'mode'),
                       'units': _attr(eu, 'submission-unit', 'type'), 'agencies': _attr(eu, 'agency', 'code'),
                       'procedures': _attr(eu, 'procedure', 'type')}


_PROFILE = None


def default_profile():
    global _PROFILE
    if _PROFILE is None:
        _PROFILE = ProfileEU()
    return _PROFILE


@dataclass
class EnvelopeEU:
    identifier: str                    # the application's UUID: the same in every envelope and every sequence (VC 9.7–9.9)
    procedure: str                     # centralised | decentralised | mutual-recognition | national
    countries: list                    # the envelopes: ['ema'] (CP), every country of the procedure (DCP/MRP), [cc] (NP)
    submission_type: str               # eu-envelope.mod: maa, var-type2, renewal, …
    unit: str                          # initial | validation-response | response | additional-info | closing | …
    applicant: str
    invented_names: list
    inn: list = field(default_factory=list)
    tracking: list = field(default_factory=lambda: ['to be advised'])   # SPEC 3.1.1: «to be advised» until the number is allocated
    sequence: str = '0000'
    related_sequence: list = None      # [sequence] for initial / reformat, else the sequence that started the activity (VC 14.6/14.7)
    description: str = ''
    mode: str = None                   # single | grouping | worksharing — variations and extensions only
    number: str = None                 # the high-level number of a grouping / worksharing
    agencies: dict = None              # a country whose receiving agency is not the default (de → DE-PEI)
    legal_basis: str = None            # 1.5.2: generic | hybrid | biosimilar (the file's fixed name)


def home(envelope):
    """Where a document that names no country goes (SPEC 3.1.1 «Country-specific folders»): ema in the centralised procedure, the
    country in a national one, common in DCP / MRP («documents potentially applicable to all EU countries»)."""
    if envelope.procedure == 'centralised':
        return 'ema'
    if envelope.procedure == 'national':
        return envelope.countries[0]
    return 'common'


def resolve(docs, envelope, profile=None):
    """Each document with the country it is filed under — the one it names, else the procedure's shared folder — and none outside
    the country sections. Run before the lifecycle plan, so a document keeps one location from sequence to sequence."""
    profile = profile or default_profile()
    out = []
    for d in docs:
        row = profile.m1.get(d.node)
        out.append(replace(d, country=(code(d.country) or home(envelope)) if row and row['country'] == 'Y' else None))
    return out


def m1_rel_path(d, envelope, profile):
    """The folder and name of an EU Module 1 document (SPEC 3.1.1 App. 2): cc-fixed[-var].pdf in the country sections."""
    row = profile.m1.get(d.node)
    if not row:
        raise WriterError(f'{d.node}: not a document heading of EU Module 1')
    cc = d.country or ''
    if row['country'] == 'Y' and not cc:
        raise WriterError(f'{d.node}: needs its country (the folder and specific/@country)')
    directory, stem = row['directory'].replace('{cc}', cc), row['stem'].split('|')[0]     # the first fixed name is the default
    if d.node == '1.3.1':
        if not (d.pi_type and d.lang):
            raise WriterError('1.3.1 needs pi_type and lang (pi-doc type and xml:lang)')
        if d.pi_type not in profile.values['pi_types']:
            raise WriterError(f"1.3.1: PI type {d.pi_type!r} is not one of the EU M1 types {profile.values['pi_types']}")
        if d.lang not in profile.values['languages']:
            raise WriterError(f'1.3.1: language {d.lang!r} is not an EU M1 language code')
        directory, stem = directory.replace('{ll}', d.lang), stem.replace('{pidoc}', d.pi_type)
    stem = stem.replace('{basis}', envelope.legal_basis if envelope.legal_basis in BASIS else 'generic')
    if d.name:
        name = slug(d.name, 50)
        stem = f'{cc}-{name}' if row['country'] == 'Y' and not name.startswith(f'{cc}-') else name
    return f"{directory}/{stem.replace('{cc}', cc)}.pdf"


def m25_rel_path(d, product, profile):
    """Modules 2–5 as ICH App. 4 places them; a 5.3 study report (except 5.3.6) in a folder of its own, as App. 4 shows
    (study-report-1) and the EU Q&A on additional folders asks: «in module 5 additional folders are required … apart from m5.2 …
    m5.3.6 and m5.4» — the study's identifier names it when the document has one."""
    if d.node == '2.3' and not d.name:            # one QOS file: qos[-var].pdf in m2/23-qos (VC 8.2 «File-Folder Structure & Names»)
        d = replace(d, name='qos')
    rel = ich_rel_path(d, product, profile)
    if d.node.startswith('5.3.') and not d.node.startswith('5.3.6'):
        directory, name = rel.rsplit('/', 1)
        rel = f"{directory}/{slug(d.study, 40) if d.study else 'study-report-1'}/{name}"
    return rel


def _check_envelope(e, seq, profile):
    v = profile.values
    if e.procedure not in v['procedures']:
        raise WriterError(f'procedure {e.procedure!r} is not one of {v["procedures"]}')
    if e.submission_type not in v['submission_types']:
        raise WriterError(f'submission type {e.submission_type!r} is not an EU M1 type (eu-envelope.mod)')
    if e.unit not in v['units']:
        raise WriterError(f'submission unit {e.unit!r} is not one of {v["units"]}')
    if e.mode and e.mode not in v['modes']:
        raise WriterError(f'mode {e.mode!r} is not one of {v["modes"]}')
    if not e.countries or len(set(e.countries)) != len(e.countries) or any(c not in v['env_countries'] for c in e.countries):
        raise WriterError(f'envelope countries {e.countries} (each once, from {v["env_countries"]})')
    if e.procedure == 'centralised' and e.submission_type != 'cep' and e.countries != ['ema']:
        raise WriterError('the centralised procedure has one envelope, ema (VC 14.1)')
    if e.procedure == 'national' and len(e.countries) != 1:
        raise WriterError('a national procedure has one envelope, for its country (VC 14.3)')
    if e.procedure != 'centralised' and 'ema' in e.countries:
        raise WriterError('ema is the envelope of the centralised procedure only')
    rel = e.related_sequence or [seq]
    if e.unit in ('initial', 'reformat') and rel != [seq]:
        raise WriterError(f'an {e.unit} sequence relates to itself: related-sequence {rel}, expected [{seq}] (VC 14.6)')
    if e.unit not in ('initial', 'reformat') and seq in rel:
        raise WriterError(f'a {e.unit} sequence relates to the sequence that started the activity, not to itself (VC 14.7)')
    if e.unit == 'reformat' and e.submission_type != 'none':
        raise WriterError('a reformat sequence has the submission type none (SPEC 3.1.1)')
    if not e.applicant or not e.invented_names or not e.description or not e.tracking:
        raise WriterError('the envelope needs the applicant, the invented name, the description and a tracking number')
    for c in e.countries:
        a = (e.agencies or {}).get(c) or AGENCY.get(c)
        if a not in v['agencies']:
            raise WriterError(f'no receiving agency for {c}')


def _envelopes(e, seq):
    rel = e.related_sequence or [seq]
    out = []
    for c in e.countries:
        out += [f'    <envelope country="{c}">',
                f'      <identifier>{escape(e.identifier)}</identifier>',
                f'      <submission type="{e.submission_type}"' + (f' mode="{e.mode}"' if e.mode else '') + '>']
        if e.number:
            out.append(f'        <number>{escape(e.number)}</number>')
        out += ['        <procedure-tracking>'] + [f'          <number>{escape(t)}</number>' for t in e.tracking] + \
               ['        </procedure-tracking>', '      </submission>',
                f'      <submission-unit type="{e.unit}"/>',
                f'      <applicant>{escape(e.applicant)}</applicant>',
                f'      <agency code="{(e.agencies or {}).get(c) or AGENCY[c]}"/>',
                f'      <procedure type="{e.procedure}"/>'] + \
               [f'      <invented-name>{escape(n)}</invented-name>' for n in e.invented_names] + \
               [f'      <inn>{escape(i)}</inn>' for i in e.inn] + \
               [f'      <sequence>{seq}</sequence>'] + \
               [f'      <related-sequence>{r}</related-sequence>' for r in rel] + \
               [f'      <submission-description>{escape(e.description)}</submission-description>', '    </envelope>']
    return out


def write(out_dir, envelope: EnvelopeEU, product: Product, docs, profile: ProfileEU = None):
    """Writes the sequence; returns {path, files, leaves, problems, history} like the EG writer. Documents should come through
    resolve() first (the exporter does); a country section's document without a country is refused."""
    profile = profile or default_profile()
    e, seq = envelope, envelope.sequence
    if not re.fullmatch(r'\d{4}', seq):
        raise WriterError('sequence must be 4 digits')
    _check_envelope(e, seq, profile)
    base = Path(out_dir) / seq
    if base.exists():
        raise WriterError(f'{base} exists — a sequence is never overwritten')
    allowed = set(e.countries) | {'common'}
    for d in docs:
        row = profile.m1.get(d.node)
        if not row or row['country'] != 'Y' or d.operation == 'delete':
            continue                    # a delete may reach a country that left the procedure (VC 14.BP3 is a best practice)
        if d.country not in profile.values['countries']:
            raise WriterError(f'{d.node}: country {d.country!r} is not an EU M1 destination code')
        if d.country not in allowed:
            raise WriterError(f'{d.node}: {d.title!r} is filed for {d.country}, which has no envelope in this sequence '
                              f'(VC 14.5: envelopes {e.countries})')
    placed = place(docs, lambda d: m1_rel_path(d, e, profile) if d.node in profile.m1 else m25_rel_path(d, product, profile),
                   seq, 'EU', 'the program writes new, replace and delete')
    copy_files(base, placed)

    # ---- eu-regional.xml ----
    history, root = [], _Node('m1-eu')
    for d, rel in placed:
        row = profile.m1.get(d.node)
        if not row:
            continue
        chain = [row['element']]
        while profile.eu_parents.get(chain[-1]) not in (None, 'm1-eu'):
            chain.append(profile.eu_parents[chain[-1]])
        cur = root
        for name in reversed(chain):
            cur = cur.child(name, {}, profile.eu_children.get(cur.name, []))
        if row['country'] == 'Y' and not d.country:
            raise WriterError(f'{d.node}: needs its country (specific/@country)')
        if d.node == '1.3.1':
            cur = cur.child('pi-doc', {'xml:lang': d.lang, 'type': d.pi_type, 'country': d.country}, ['pi-doc'])
        elif row['country'] == 'Y':
            cur = cur.child('specific', {'country': d.country}, ['specific'])
        modified = None
        if d.modified_file:
            s, lid = d.modified_file.split('#', 1)
            modified = f'../../../{s}/{REGIONAL}#{lid}'
        leaf = dict(id=d.leaf_id or _leaf_id(seq, rel or d.modified_file), op=d.operation, md5=md5(base / rel) if rel else '',
                    href=rel[len('m1/eu/'):] if rel else None, title=d.title, modified=modified)
        cur.leaves.append(leaf)
        history.append(_hist(d, leaf, rel, 'regional'))
    if not any(k.name == 'm1-0-cover' for k in root.kids):
        raise WriterError('1.0 cover letter is mandatory in every sequence (m1-0-cover)')
    env = next((k for k in root.kids if k.name == 'm1-6-environrisk'), None)
    if env is not None and len(env.kids) > 1:
        raise WriterError('1.6.1 (non-GMO) and 1.6.2 (GMO) cannot both hold documents: the EU DTD takes one of them')
    regional = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE eu:eu-backbone SYSTEM "../../util/dtd/eu-regional.dtd">\n'
                '<?xml-stylesheet type="text/xsl" href="../../util/style/eu-regional.xsl"?>\n'
                '<eu:eu-backbone xmlns:eu="http://europa.eu.int" xmlns:xlink="http://www.w3c.org/1999/xlink" dtd-version="3.1">\n'
                '  <eu-envelope>\n' + '\n'.join(_envelopes(e, seq)) + '\n  </eu-envelope>\n'
                + _render(root, profile.eu_children) + '</eu:eu-backbone>\n')
    reg_path = base / REGIONAL
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(regional, encoding='utf-8')

    write_index(base, seq, [(d, rel) for d, rel in placed if d.node not in profile.m1], product, profile, REGIONAL, 'EU Module 1',
                history)
    return finish(base, profile, placed, history)
