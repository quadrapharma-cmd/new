"""EU eCTD 3.2.2 sequence validator: EU Module 1 v3.1.1 and the EU eCTD Validation Criteria v8.2, word for word from the profile's
validation-criteria.csv (docs/ctd/ectd/EU-M1-3.1.1-PROFILE).

Each criterion that the files on disk decide is run: most through the same reader and checks as the EG validator (they read any
eCTD 3.2.2 sequence), the EU's own here. A criterion that needs earlier sequences runs only when `previous` is given; one the files
cannot decide is reported «not run» with the reason — nothing is passed silently. This is not an EMA-accepted validation tool: the
label says so, and the sequence should go through one (VC 8.2) before it is submitted."""
import csv, re
from pathlib import Path
from . import ectd32 as v32
from .ectd32 import Ctx, MOD_RE, XLINK, md5, _exists

REGIONAL = 'm1/eu/eu-regional.xml'
APP4 = Path(__file__).resolve().parents[3] / 'rulepacks' / 'ich.ectd.v322' / 'app4.csv'
RULES = {}
# EU criterion → the EG check that reads the same thing (called with the id it was written for)
SAME = {'EU-1.1': 'EG-PF-1.1', 'EU-1.2': 'EG-PF-1.2', 'EU-2.1': 'EG-PF-2.1', 'EU-2.2': 'EG-PF-2.2',
        'EU-7.1': 'EG-PF-7.1', 'EU-7.2': 'EG-PF-7.2', 'EU-7.3': 'EG-PF-7.3', 'EU-7.4': 'EG-PF-7.4', 'EU-7.5': 'EG-PF-7.5',
        'EU-7.6': 'EG-PF-7.6', 'EU-8.1': 'EG-PF-8.1', 'EU-8.2': 'EG-PF-8.2', 'EU-8.3': 'EG-PF-8.3',
        'EU-9.1': 'EG-PF-9.1', 'EU-9.2': 'EG-PF-9.2', 'EU-9.3': 'EG-PF-9.3', 'EU-9.4': 'EG-PF-9.4', 'EU-9.5': 'EG-PF-9.5',
        'EU-9.6': 'EG-PF-9.6', 'EU-9.7': 'EG-PF-9.7', 'EU-9.8': 'EG-PF-9.8', 'EU-9.9': 'EG-PF-9.9',
        'EU-11.1': 'EG-PF-11.1', 'EU-11.2': 'EG-PF-11.2', 'EU-11.3': 'EG-PF-11.3', 'EU-11.5': 'EG-PF-11.5', 'EU-11.6': 'EG-PF-11.6',
        'EU-11.7': 'EG-PF-11.7', 'EU-11.8': 'EG-PF-11.8', 'EU-11.9': 'EG-PF-11.9', 'EU-11.11': 'EG-PF-11.11',
        'EU-11.BP1': 'EG-PF-11.9', 'EU-12.1': 'EG-PF-12.1', 'EU-13.1': 'EG-PF-13.1', 'EU-13.2': 'EG-PF-13.2', 'EU-13.3': 'EG-PF-13.3',
        'EU-14.8': 'EG-BP-14.8', 'EU-15.3': 'EG-PF-15.3', 'EU-15.4': 'EG-PF-15.4', 'EU-15.5': 'EG-PF-15.5', 'EU-15.8': 'EG-PF-15.8',
        'EU-15.9': 'EG-PF-15.9', 'EU-15.10': 'EG-PF-15.10', 'EU-15.BP1': 'EG-BP-15.BP1',
        'EU-16.1': 'EG-PF-16.1', 'EU-16.2': 'EG-PF-16.2', 'EU-16.5': 'EG-PF-16.5', 'EU-16.BP1': 'EG-BP-16.BP1'}
NOT_RUN = {
    'EU-16.6': 'which eAF a file is (PLM Portal with its FHIR XML, or the interactive PDF form) is not known from the file alone — check 1.2',
    'EU-16.7': 'which eAF a file is (PLM Portal with its FHIR XML, or the interactive PDF form) is not known from the file alone — check 1.2',
    'EU-16.BP10': 'how a link between two PDFs is configured (ISO 32000-1 file specification and destination) is checked by eye in Acrobat',
}
VIDEO = ('.mp4', '.avi', '.mov', '.wmv', '.mpg', '.mpeg', '.webm', '.mkv')
SECURE_OK = ('m1/eu/10-cover/', 'm1/eu/12-form/', 'm3/33-lit-ref/', 'm4/43-lit-ref/', 'm5/54-lit-ref/')   # VC 16.3: 1.0, 1.2, 3.3, 4.3, 5.4
NO_FWV = ('m1/eu/10-cover/', 'm1/eu/12-form/')                                                        # VC 16.BP5: not 1.0 and 1.2


def rule(*ids):
    def deco(fn):
        for i in ids:
            RULES[i] = fn
        return fn
    return deco


def _profile(ctx):
    if not hasattr(ctx, '_eu'):
        from ..writers.ectd32_eu import ProfileEU
        ctx._eu = ProfileEU(ctx.profile)
    return ctx._eu


def _envs(ctx):
    return list(ctx.reg.iter('envelope')) if ctx.reg is not None else []


def _first(ctx, path, attr='type'):
    e = ctx.reg.find(f'.//envelope/{path}') if ctx.reg is not None else None
    return e.get(attr) if e is not None else None


def _wrapped(ctx):
    """(wrapper, country, leaf) for every leaf of eu-regional.xml inside a specific or pi-doc."""
    if ctx.reg is None:
        return []
    return [(w, w.get('country'), lf) for w in ctx.reg.iter('specific', 'pi-doc') for lf in w.iter('leaf')]


# ---------------------------------------------------------------- util files (VC 1–6)
@rule('EU-3.1', 'EU-3.2')
def r_eu_dtd(ctx, rid):
    return _exists(ctx, 'util/dtd/eu-regional.dtd')


@rule('EU-4.1', 'EU-4.2')
def r_eu_leafmod(ctx, rid):
    return _exists(ctx, 'util/dtd/eu-leaf.mod')


@rule('EU-5.1', 'EU-5.2')
def r_eu_envmod(ctx, rid):
    return _exists(ctx, 'util/dtd/eu-envelope.mod')


@rule('EU-6.1', 'EU-6.2')
def r_eu_xsl(ctx, rid):
    return _exists(ctx, 'util/style/eu-regional.xsl')


@rule('EU-1.3', 'EU-2.3', 'EU-3.3', 'EU-4.3', 'EU-5.3', 'EU-6.3')
def r_published_md5(ctx, rid):
    """The published checksums (VC 1.3, 3.3, 6.3 quote them) — the profile's util-md5.txt, made from the EMA's util package."""
    f = {'EU-1.3': 'util/dtd/ich-ectd-3-2.dtd', 'EU-2.3': 'util/style/ectd-2-0.xsl', 'EU-3.3': 'util/dtd/eu-regional.dtd',
         'EU-4.3': 'util/dtd/eu-leaf.mod', 'EU-5.3': 'util/dtd/eu-envelope.mod', 'EU-6.3': 'util/style/eu-regional.xsl'}[rid]
    published = dict(reversed(line.split()) for line in (ctx.profile / 'util-md5.txt').read_text().split('\n') if line.strip())
    if not (ctx.base / f).is_file():
        return [f'{f} missing']
    got = md5(ctx.base / f)
    return [] if got == published[f] else [f'{f}: MD5 {got}, published {published[f]}']


def _versions(root_dir):
    """(ICH DTD version, EU M1 DTD version) a sequence uses."""
    ich = eu = None
    p = Path(root_dir)
    if (p / 'index.xml').is_file():
        m = re.search(r'ich-ectd-(\d+)-(\d+)\.dtd', (p / 'index.xml').read_text(encoding='utf-8', errors='replace')[:600])
        ich = (int(m.group(1)), int(m.group(2))) if m else None
    if (p / REGIONAL).is_file():
        m = re.search(r'dtd-version="(\d+)\.(\d+)"', (p / REGIONAL).read_text(encoding='utf-8', errors='replace')[:2000])
        eu = (int(m.group(1)), int(m.group(2))) if m else None
    return ich, eu


@rule('EU-1.4', 'EU-1.5', 'EU-3.4', 'EU-3.5')
def r_dtd_order(ctx, rid):
    """1.4/3.4: not lower than the sequence numerically before; 1.5/3.5: not higher than the one after (when it is at hand)."""
    k = 0 if rid in ('EU-1.4', 'EU-1.5') else 1
    mine = _versions(ctx.base)[k]
    seqs = sorted(s for s in ctx.previous if s != ctx.seq)
    if rid in ('EU-1.4', 'EU-3.4'):
        lower = [s for s in seqs if s < ctx.seq]
        other = _versions(ctx.previous[lower[-1]])[k] if lower else None
        return [] if other is None or mine is None or mine >= other else [f'DTD {mine} is lower than {other} in {lower[-1]}']
    higher = [s for s in seqs if s > ctx.seq]
    other = _versions(ctx.previous[higher[0]])[k] if higher else None
    return [] if other is None or mine is None or mine <= other else [f'DTD {mine} is higher than {other} in {higher[0]}']


# ---------------------------------------------------------------- the backbone (VC 10–13)
@rule('EU-10.1')
def r_empty(ctx, rid):
    out = v32.RULES['EG-PF-10.1'](ctx, 'EG-PF-10.1')
    if ctx.reg is not None:
        out += [f"empty {w.tag} country={w.get('country')}" for w in ctx.reg.iter('specific', 'pi-doc') if len(w) == 0]
    return out


HREF_RE = re.compile(r'^(?:[a-z0-9][a-z0-9-]*/)*[a-z0-9][a-z0-9-]*\.[a-z0-9]+$')


@rule('EU-11.4')
def r_href_eu(ctx, rid):
    out = []
    for _, lf, rel in ctx.leaves:
        if lf.get('operation') not in ('new', 'replace', 'append'):
            continue
        h = lf.get(XLINK)
        if not h:
            out.append(f"leaf {lf.get('ID')} ({lf.get('operation')}) has no href")
        elif not HREF_RE.match(h):
            out.append(f'{h}: only a-z, 0-9 and hyphens in names (ICH eCTD specification)')
    return out


def _section(el):
    """The CTD section a leaf sits in: every heading above it with its attributes (substance, manufacturer, country, language…)."""
    out, p = [], el.getparent()
    while p is not None and p.getparent() is not None:
        out.append((p.tag, tuple(sorted((k, v) for k, v in p.attrib.items()))))
        p = p.getparent()
    return tuple(reversed(out))


def _exempt(lf):
    tags = [a.tag for a in lf.iterancestors()]
    return any(t == 'node-extension' or str(t).startswith('m3-2-a-') for t in tags)


@rule('EU-11.10', 'EU-11.BP2')
def r_same_section(ctx, rid):
    out = []
    for x, lf, _ in ctx.leaves:
        if lf.get('operation') not in ('replace', 'delete', 'append'):
            continue
        if (rid == 'EU-11.10') == _exempt(lf):
            continue                     # 11.10: all but node extensions and 3.2.A; 11.BP2: exactly those
        if rid == 'EU-11.10' and lf.get('operation') == 'delete' and any(a.tag == 'm1-additional-data' for a in lf.iterancestors()):
            continue
        tgt, _why = v32._target(ctx, lf)
        if tgt is not None and _section(tgt) != _section(lf):
            out.append(f"leaf {lf.get('ID')} ({lf.get('operation')}) is in {'/'.join(t for t, _ in _section(lf))}, "
                       f"its target in {'/'.join(t for t, _ in _section(tgt))}")
    return out


@rule('EU-11.12')
def r_not_twice(ctx, rid):
    """The modified file was not replaced or deleted already — by an earlier sequence or by another leaf of this one."""
    done = {}
    for s in sorted(ctx.previous):
        if s >= ctx.seq:
            continue
        for which in ('index', 'regional'):
            root = ctx.prev_xml(s, which)
            for lf in (root.iter('leaf') if root is not None else []):
                m = MOD_RE.match(lf.get('modified-file') or '')
                if m and lf.get('operation') in ('replace', 'delete'):
                    done[(m.group(1), m.group(3))] = s
    out = []
    for _, lf, _ in ctx.leaves:
        m = MOD_RE.match(lf.get('modified-file') or '')
        if not m or lf.get('operation') not in ('replace', 'delete', 'append'):
            continue
        k = (m.group(1), m.group(3))
        if k in done:
            out.append(f"leaf {lf.get('ID')}: {k[0]}#{k[1]} was already {'replaced or deleted'} in {done[k]}")
        done[k] = ctx.seq
    return out


@rule('EU-11.BP3')
def r_ich_attrs(ctx, rid):
    out = []
    for el in (ctx.index.iter() if ctx.index is not None else []):
        if not isinstance(el.tag, str) or el.tag in ('leaf', 'title'):
            continue
        for k, v in el.attrib.items():
            if k.startswith('{') or k in ('ID',):
                continue
            if v != v.strip() or v.strip().startswith('-') or v.strip().endswith('-'):
                out.append(f'<{el.tag} {k}={v!r}>')
    return out


# ---------------------------------------------------------------- the envelopes (VC 14)
@rule('EU-14.1')
def r_cp_one(ctx, rid):
    if _first(ctx, 'procedure') != 'centralised' or _first(ctx, 'submission') == 'cep':
        return []
    c = [e.get('country') for e in _envs(ctx)]
    return [] if c == ['ema'] else [f'centralised: envelopes {c}, expected one ema']


@rule('EU-14.2')
def r_mrp_dcp(ctx, rid):
    if _first(ctx, 'procedure') not in ('mutual-recognition', 'decentralised'):
        return []
    c = [e.get('country') for e in _envs(ctx)]
    return [] if c and not {'ema', 'edqm'} & set(c) else [f'{_first(ctx, "procedure")}: envelopes {c}']


@rule('EU-14.3')
def r_np_one(ctx, rid):
    if _first(ctx, 'procedure') != 'national':
        return []
    c = [e.get('country') for e in _envs(ctx)]
    return [] if len(c) == 1 and c[0] not in ('ema', 'edqm') else [f'national: envelopes {c}, expected one country']


@rule('EU-14.4')
def r_cep(ctx, rid):
    if _first(ctx, 'submission') != 'cep':
        return []
    c = [e.get('country') for e in _envs(ctx)]
    return [] if c == ['edqm'] else [f'cep: envelopes {c}, expected one edqm']


@rule('EU-14.5', 'EU-14.BP3')
def r_country_envelope(ctx, rid):
    ops = ('new', 'replace', 'append') if rid == 'EU-14.5' else ('delete',)
    env = {e.get('country') for e in _envs(ctx)}
    used = {c for _, c, lf in _wrapped(ctx) if lf.get('operation') in ops and c != 'common'}
    return [f'{c} is used in a leaf but has no envelope' for c in sorted(used - env)]


@rule('EU-14.6', 'EU-14.7')
def r_related(ctx, rid):
    out = []
    for e in _envs(ctx):
        u = e.find('submission-unit').get('type') if e.find('submission-unit') is not None else None
        rel = [(r.text or '').strip() for r in e.findall('related-sequence')]
        if rid == 'EU-14.6' and u in ('initial', 'reformat') and rel != [ctx.seq]:
            out.append(f"{e.get('country')}: {u} with related-sequence {rel}, expected [{ctx.seq}]")
        if rid == 'EU-14.7' and u not in ('initial', 'reformat') and ctx.seq in rel:
            out.append(f"{e.get('country')}: {u} relates to itself ({ctx.seq})")
    return out


@rule('EU-14.9')
def r_edqm_cp(ctx, rid):
    return [f"edqm envelope with procedure {e.find('procedure').get('type')}" for e in _envs(ctx)
            if e.get('country') == 'edqm' and e.find('procedure') is not None and e.find('procedure').get('type') != 'centralised']


@rule('EU-14.BP4', 'EU-14.BP5', 'EU-14.BP7', 'EU-14.BP8')
def r_mode(ctx, rid):
    out = []
    for e in _envs(ctx):
        s = e.find('submission')
        if s is None:
            continue
        mode, t, has = s.get('mode'), s.get('type'), s.find('number') is not None
        if rid == 'EU-14.BP4' and mode in ('grouping', 'worksharing') and t != 'psusa' and not has:
            out.append(f"{e.get('country')}: {mode} without the high-level number")
        if rid == 'EU-14.BP5' and mode not in ('grouping', 'worksharing') and has:
            out.append(f"{e.get('country')}: a high-level number without grouping / worksharing")
        if rid == 'EU-14.BP7' and mode == 'grouping' and t not in ('var-type1a', 'var-type1ain', 'var-type1b', 'var-type2', 'extension'):
            out.append(f"{e.get('country')}: grouping of {t}")
        if rid == 'EU-14.BP8' and mode == 'worksharing' and t not in ('var-type1b', 'var-type2', 'psusa'):
            out.append(f"{e.get('country')}: worksharing of {t}")
    return out


@rule('EU-14.BP6')
def r_tracking_number(ctx, rid):
    out = []
    for e in _envs(ctx):
        nums = [(n.text or '').strip() for n in e.findall('submission/procedure-tracking/number')]
        if not any(n and n.lower() != 'to be advised' for n in nums):
            out.append(f"{e.get('country')}: procedure-tracking is «to be advised» — put the procedure number once the agency has given it")
    return out


# ---------------------------------------------------------------- files and folders (VC 15)
FILE_RE = re.compile(r'^[a-z0-9][a-z0-9-]*\.[a-z0-9]+$')
DIR_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


@rule('EU-15.6')
def r_file_chars(ctx, rid):
    return [f for f in ctx.files if not FILE_RE.match(f.split('/')[-1])]


@rule('EU-15.7')
def r_dir_chars(ctx, rid):
    return [d for d in ctx.dirs if not DIR_RE.match(d.split('/')[-1])]


def _home(ctx):
    proc, env = _first(ctx, 'procedure'), [e.get('country') for e in _envs(ctx)]
    return {'centralised': 'ema', 'national': env[0] if env else None}.get(proc, 'common')


@rule('EU-15.11', 'EU-15.12')
def r_tracking(ctx, rid):
    if _first(ctx, 'submission') == 'cep' or 'edqm' in [e.get('country') for e in _envs(ctx)]:
        return []                        # no tracking table for EDQM submissions
    cc = _home(ctx)
    trk = [f for f in ctx.files if f.startswith('m1/eu/10-cover/') and re.search(r'(^|-)tracking(-|\.)', f.split('/')[-1])]
    if rid == 'EU-15.11':
        return [] if any(f.startswith(f'm1/eu/10-cover/{cc}/') for f in trk) else [f'no tracking table in m1/eu/10-cover/{cc}/']
    return [f'{f}: named {cc}-tracking[-var].pdf in m1/eu/10-cover/{cc}/' for f in trk
            if not re.fullmatch(rf'm1/eu/10-cover/{cc}/{cc}-tracking(-[a-z0-9-]+)?\.pdf', f)]


def _m1_patterns(ctx):
    """For each m1.csv row: (directory regex, file-name regex) with the DTD's countries, languages and PI types."""
    if not hasattr(ctx, '_m1p'):
        p = _profile(ctx)
        cc, ll, pi = '(?:' + '|'.join(p.values['countries']) + ')', '(?:' + '|'.join(p.values['languages']) + ')', \
            '(?:' + '|'.join(p.values['pi_types']) + ')'
        out = []
        for r in p.m1.values():
            d = re.escape(r['directory']).replace(r'\{cc\}', cc).replace(r'\{ll\}', ll)
            stem = '(?:' + '|'.join(re.escape(s).replace(r'\{cc\}', '[a-z]+').replace(r'\{pidoc\}', pi)
                                    .replace(r'\{basis\}', '(?:generic|hybrid|biosimilar)') for s in r['stem'].split('|')) + ')'
            ext = r'(?:pdf|jpg|jpeg|gif|png|svg)' if r['node'] == '1.3.2' else 'pdf'
            out.append((r, re.compile(d + '$'), re.compile(stem + r'(?:-[a-z0-9-]+)?\.' + ext + '$')))
        ctx._m1p = out
    return ctx._m1p


VAR_SEG = re.compile(r'^(?:product-1|substance-1-manufacturer-1|excipient-1|indication-1|study-report-\d+|study-\d+)$')


def _app4(ctx):
    """ICH App. 4: the specified directories (as regexes, variable folders open) and the fixed file names in each."""
    if not hasattr(ctx, '_a4'):
        rows = list(csv.DictReader(open(APP4, encoding='utf-8')))
        dirs, names = {}, {}
        def rx(path):
            return '/'.join('[a-z0-9-]+' if VAR_SEG.match(s) else re.escape(s) for s in path.split('/'))
        for r in rows:
            if '/' not in r['path'] and r['kind'] == 'F':
                continue
            d = r['path'] if r['kind'] == 'D' else r['path'].rsplit('/', 1)[0]
            parts = d.split('/')
            for i in range(1, len(parts) + 1):
                dirs.setdefault(rx('/'.join(parts[:i])), set())
            if r['kind'] == 'F' and r['placeholder'] != 'yes':
                names.setdefault(rx(d), set()).add(r['path'].rsplit('/', 1)[1].rsplit('.', 1)[0])
        names.setdefault(rx('m2/23-qos'), set()).add('qos')        # the EU's one-file QOS (VC 8.2 «File-Folder Structure & Names»)
        ctx._a4 = ([re.compile(k + '$') for k in dirs], {re.compile(k + '$'): v for k, v in names.items()})
    return ctx._a4


def _extra_ok(d):
    """Folders the Q&A on additional folders allows below the specified structure."""
    if d.startswith(('m3/32-body-data/32a-app/', 'm3/32-body-data/32r-reg-info/', 'm3/33-lit-ref/')):
        return True
    if d.startswith('m4/'):
        return True                      # one optional level (checked by the caller)
    return d.startswith('m5/') and not d.startswith('m5/52-tab-list/')


@rule('EU-15.BP2')
def r_folders(ctx, rid):
    out = []
    m1 = _m1_patterns(ctx)
    m1_dirs = set()
    for r, d, _ in m1:
        parts = d.pattern[:-1].split('/')
        for i in range(1, len(parts) + 1):
            m1_dirs.add('/'.join(parts[:i]))
    m1_rx = [re.compile(x + '$') for x in m1_dirs]
    a4, _names = _app4(ctx)
    for d in ctx.dirs:
        top = d.split('/')[0]
        if top in ('util',) or d.startswith('util/'):
            continue
        if top == 'm1':
            if not any(x.match(d) for x in m1_rx):
                out.append(f'{d}: not a folder of EU Module 1 (additional folders are not allowed in m1)')
        elif top in ('m2', 'm3', 'm4', 'm5'):
            if any(x.match(d) for x in a4):
                continue
            parent = d.rsplit('/', 1)[0]
            if _extra_ok(d) and (not d.startswith('m4/') or any(x.match(parent) for x in a4)):
                continue
            out.append(f'{d}: not in the ICH folder structure')
    for f in ctx.files:                  # Module 5: a study's files sit in their own folder (Q&A), except 5.2, 5.3.6 and 5.4
        if f.startswith('m5/53-clin-stud-rep/') and '/536-postmark-exp/' not in f:
            d = f.rsplit('/', 1)[0]
            if re.search(r'/53\d{2}-[a-z0-9-]+$', d) or re.search(r'/535\d-[a-z0-9-]+$', d):
                out.append(f'{f}: directly in the section folder — module 5 puts each study in a folder of its own')
    return out


@rule('EU-15.BP3')
def r_names(ctx, rid):
    out = []
    m1 = _m1_patterns(ctx)
    _a4, names = _app4(ctx)
    for f in ctx.files:
        if f == REGIONAL or '/' not in f or f.startswith('util/'):
            continue
        d, n = f.rsplit('/', 1)
        if f.startswith('m1/'):
            rows = [(r, nx) for r, dx, nx in m1 if dx.match(d)]
            if rows and not any(nx.match(n) for _, nx in rows):
                out.append(f"{f}: the name is {rows[0][0]['stem']}[-var] (SPEC 3.1.1 App. 2)")
        else:
            fixed = next((v for k, v in names.items() if k.match(d)), None)
            stem = n.rsplit('.', 1)[0]
            if fixed and not any(stem == s or stem.startswith(s + '-') for s in fixed):
                out.append(f'{f}: ICH App. 4 names it {" / ".join(sorted(fixed))}[-var]')
    return out


def _cc_segment(ctx, lf):
    """The country folder and the file's own country prefix of a wrapped leaf's href (relative to m1/eu)."""
    h = lf.get(XLINK) or ''
    for r, dx, _ in _m1_patterns(ctx):
        if r['country'] == 'Y' and dx.match('m1/eu/' + h.rsplit('/', 1)[0]):
            i = r['directory'].split('/').index('{cc}') - 2
            parts = h.split('/')
            return parts[i] if len(parts) > i else None, parts[-1].split('-', 1)[0]
    return None, None


@rule('EU-15.BP4', 'EU-15.BP5')
def r_cc_consistent(ctx, rid):
    out = []
    for w, c, lf in _wrapped(ctx):
        if lf.get('operation') == 'delete':
            continue
        folder, prefix = _cc_segment(ctx, lf)
        got = folder if rid == 'EU-15.BP4' else prefix
        if got is not None and got != c:
            out.append(f"{lf.get(XLINK)}: {'folder' if rid == 'EU-15.BP4' else 'file name'} {got}, leaf country {c}")
    return out


@rule('EU-15.BP1.1', 'EU-15.BP2.1')
def r_formats(ctx, rid):
    if rid == 'EU-15.BP1.1':
        return [f for f in ctx.files if f.startswith('m1/') and f != REGIONAL and not f.lower().endswith('.pdf')
                and not (f.startswith('m1/eu/13-pi/132-mockup/') and f.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.svg')))]
    return [f for f in ctx.files if f.split('/')[0] in ('m2', 'm3', 'm4', 'm5') and not f.lower().endswith('.pdf')]


@rule('EU-15.BP6')
def r_video(ctx, rid):
    return [f for f in ctx.content_files() if f.lower().endswith(VIDEO) and (ctx.base / f).stat().st_size > 2 ** 30]


# ---------------------------------------------------------------- PDF (VC 16)
@rule('EU-16.3')
def r_security(ctx, rid):
    return [f'{f}: {fd.en}' for f in ctx.content_files() if f.lower().endswith('.pdf') and not f.startswith(SECURE_OK)
            for fd in ctx.pdf(f).findings if fd.rule == 'EG-PF-16.3']


def _facts(ctx, rel):
    """What the EU PDF criteria read from one file (pypdf); None when it cannot be read (16.5 says so)."""
    cache = ctx.__dict__.setdefault('_facts', {})
    if rel in cache:
        return cache[rel]
    p = ctx.base / rel
    try:
        from pypdf import PdfReader
        from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject
        rd = PdfReader(str(p), strict=False)
        perms = None
        if rd.is_encrypted:
            rd.decrypt('')
            enc = rd.trailer['/Encrypt'].get_object()
            perms = (int(enc.get('/P', -1)), int(enc.get('/R', 2)))
        root = rd.trailer['/Root']
        head = p.read_bytes()[:1024]
        dests, links = [], []

        def walk(items):
            for it in items:
                if isinstance(it, list):
                    walk(it)
                else:
                    dests.append(('bookmark', it.get('/Type'), it.get('/Zoom') if '/Zoom' in it else None, it.get('/Left')))
        try:
            walk(rd.outline)
        except Exception:
            pass
        for pg in rd.pages:
            for a in pg.get('/Annots') or []:
                a = a.get_object() if isinstance(a, IndirectObject) else a
                if not isinstance(a, DictionaryObject) or a.get('/Subtype') != '/Link':
                    continue
                act = a.get('/A')
                act = act.get_object() if isinstance(act, IndirectObject) else act
                links.append({'dest': a.get('/Dest'), 'action': dict(act) if isinstance(act, DictionaryObject) else None})
        info = rd.metadata or {}
        f = {'perms': perms, 'linearized': b'/Linearized' in head, 'layout': root.get('/PageLayout'),
             'open': root.get('/OpenAction'), 'mode': root.get('/PageMode'), 'outline': bool(dests), 'bookmarks': dests,
             'links': links, 'info': {k: str(info.get(k) or '').strip() for k in ('/Title', '/Author', '/Subject', '/Keywords')}}
    except Exception:
        f = None
    cache[rel] = f
    return f


def _pdfs(ctx):
    return [f for f in ctx.content_files() if f.lower().endswith('.pdf')]


def permissions(p, revision):
    """/P read the way the handler's revision reads it (ISO 32000-1:2008 Table 22) — after pdfcraft's crypt crate
    (github.com/storytold/pdfcraft, MIT OR Apache-2.0, © ArtCraft Team and the PdfCraft contributors). Page extraction is assembly
    and copying together, so a form may withhold it (VC 16.4) while copying itself stays allowed."""
    bit = lambda n: (p >> (n - 1)) & 1 == 1
    r3 = revision >= 3
    return {'printing': bit(3), 'content copying': bit(5),
            'filling of form fields / signing': (bit(9) or bit(6)) if r3 else bit(6),
            'content copying for accessibility': bit(10) if r3 else bit(5)}


@rule('EU-16.4')
def r_form_security(ctx, rid):
    out = []
    for f in _pdfs(ctx):
        if not f.startswith(('m1/eu/10-cover/', 'm1/eu/12-form/')):
            continue
        fa = _facts(ctx, f)
        if not fa or fa['perms'] is None:
            continue
        missing = [n for n, ok in permissions(*fa['perms']).items() if not ok]
        if missing:
            out.append(f'{f}: restricts {", ".join(missing)} (only changing, assembly, page extraction, commenting and template pages may be)')
    return out


@rule('EU-16.BP5')
def r_fast_web(ctx, rid):
    return [f'{f}: Fast Web View is off (not linearized)' for f in _pdfs(ctx) if not f.startswith(NO_FWV)
            and _facts(ctx, f) and not _facts(ctx, f)['linearized']]


@rule('EU-16.BP6')
def r_initial_view(ctx, rid):
    out = []
    for f in _pdfs(ctx):
        fa = _facts(ctx, f)
        if not fa:
            continue
        if fa['layout'] not in (None, '/SinglePage'):
            out.append(f"{f}: page layout {fa['layout']}")
        o = fa['open']
        try:
            o = o.get_object() if hasattr(o, 'get_object') else o
            if isinstance(o, list) and len(o) > 1 and str(o[1]) != '/XYZ' or isinstance(o, list) and len(o) > 4 and o[4] not in (None, 0):
                out.append(f'{f}: the initial view sets a magnification')
        except Exception:
            pass
    return out


@rule('EU-16.BP8', 'EU-16.BP9')
def r_bookmark_pane(ctx, rid):
    out = []
    for f in _pdfs(ctx):
        fa = _facts(ctx, f)
        if not fa:
            continue
        shows = fa['mode'] == '/UseOutlines'
        if rid == 'EU-16.BP8' and fa['outline'] and not shows:
            out.append(f'{f}: has bookmarks, opens without the bookmarks pane')
        if rid == 'EU-16.BP9' and not fa['outline'] and shows:
            out.append(f'{f}: no bookmarks, opens with the bookmarks pane')
    return out


@rule('EU-16.BP4')
def r_inherit_zoom(ctx, rid):
    out = []
    for f in _pdfs(ctx):
        fa = _facts(ctx, f)
        if not fa:
            continue
        for kind, typ, zoom, _left in fa['bookmarks']:
            if typ is not None and str(typ) != '/XYZ' or zoom not in (None, 0):
                out.append(f'{f}: a bookmark sets its own zoom ({typ} {zoom})')
                break
        for ln in fa['links']:
            d = ln['dest'] if ln['dest'] is not None else (ln['action'] or {}).get('/D')
            try:
                d = d.get_object() if hasattr(d, 'get_object') else d
                if isinstance(d, list) and len(d) > 1 and (str(d[1]) != '/XYZ' or (len(d) > 4 and d[4] not in (None, 0))):
                    out.append(f'{f}: a link sets its own zoom ({d[1]})')
                    break
            except Exception:
                pass
    return out


def _remote(ctx):
    """(file, target path from the sequence root) of every link to another file."""
    out = []
    for f in _pdfs(ctx):
        fa = _facts(ctx, f)
        for ln in (fa or {}).get('links', []):
            a = ln['action'] or {}
            if str(a.get('/S')) in ('/GoToR', '/Launch'):
                spec = a.get('/F')
                spec = spec.get_object() if hasattr(spec, 'get_object') else spec
                name = str(spec.get('/UF') or spec.get('/F')) if isinstance(spec, dict) else str(spec or '')
                out.append((f, name))
    return out


@rule('EU-16.BP7')
def r_relative_links(ctx, rid):
    return [f'{f}: link to {t}' for f, t in _remote(ctx) if re.match(r'^(?:/|[a-zA-Z]:|file:|\\\\)', t)]


@rule('EU-16.BP2', 'EU-16.BP3')
def r_link_targets(ctx, rid):
    import posixpath
    out = []
    for f, t in _remote(ctx):
        if re.match(r'^(?:/|[a-zA-Z]:|file:|https?:)', t):
            continue
        tgt = posixpath.normpath(posixpath.join(posixpath.dirname(f), t))
        if not tgt.startswith('../'):
            if rid == 'EU-16.BP2' and not (ctx.base / tgt).is_file():
                out.append(f'{f}: link to {t} — no such file in this sequence')
        elif rid == 'EU-16.BP3':
            m = re.match(r'^\.\./(\d{4})/(.+)$', tgt)
            ok = m and m.group(1) in ctx.previous and (ctx.previous[m.group(1)] / m.group(2)).is_file()
            if not ok:
                out.append(f'{f}: link to {t} — not found in the earlier sequences at hand')
    return out


@rule('EU-16.BP11')
def r_pi_description(ctx, rid):
    if _first(ctx, 'procedure') != 'centralised':
        return []
    out = []
    for f in _pdfs(ctx):
        if f.startswith('m1/eu/13-pi/131-spclabelpl/'):
            fa = _facts(ctx, f)
            empty = [k[1:] for k, v in (fa or {}).get('info', {}).items() if not v]
            if empty:
                out.append(f'{f}: Document Properties > Description: {", ".join(empty)} empty')
    return out


# ---------------------------------------------------------------- the run
def load_rules(profile_root):
    return list(csv.DictReader(open(Path(profile_root) / 'validation-criteria.csv', encoding='utf-8')))


def validate(seq_dir, profile_root, previous=None):
    """previous: the earlier sequence folders of the same application (the lifecycle criteria need them)."""
    ctx = Ctx(seq_dir, profile_root, previous, regional=REGIONAL)
    results = []
    for r in load_rules(profile_root):
        rid = r['rule_id']
        sev = 'pass_fail' if r['type'] == 'Pass/Fail' else 'best_practice'
        base = {'rule': rid, 'severity': sev, 'text': r['rule_text'], 'provenance': 'EU-IN-FORCE', 'source': r['source']}
        if rid in RULES:
            fn, arg = RULES[rid], rid
        elif rid in SAME:
            fn, arg = v32.RULES[SAME[rid]], SAME[rid]
        else:
            fn = arg = None
        if fn is not None and r['lifecycle_needed'] == 'Y' and previous is None:
            fn = None
        if fn is None:
            reason = NOT_RUN.get(rid) or ('needs the earlier sequences (lifecycle)' if r['lifecycle_needed'] == 'Y'
                                          else 'not automated yet (manual / visual check)')
            results.append({**base, 'status': 'not_run', 'reason': reason, 'failures': []})
            continue
        fails = fn(ctx, arg)
        results.append({**base, 'status': 'pass' if not fails else ('fail' if sev == 'pass_fail' else 'warning'),
                        'failures': [str(x) for x in fails[:50]]})
    out = v32.summarise(results)
    run = len(results) - out['counts']['not_run']
    out['label'] = (f'Conforms to EU Module 1 v3.1.1 (EMA DTD) — {run} of {len(results)} EU validation criteria v8.2 checked here, '
                    f'{out["counts"]["warning"]} best-practice warning(s). Not an EMA-accepted validator: run one before submission.'
                    if out['ok'] else f'Does not conform to the EU eCTD validation criteria v8.2 ({out["counts"]["fail"]} pass/fail '
                                      f'criteria failed of {run} checked).')
    return out
