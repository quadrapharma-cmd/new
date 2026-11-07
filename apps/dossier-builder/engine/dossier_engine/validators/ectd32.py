"""eCTD 3.2.2 sequence validator against the EG provisional profile's rule list.

Rules are the profile's validation-criteria.csv (EU VC 8.2 mapped + EG drafts);
this module implements the automatable ones by rule id. Rules that need earlier
sequences are run only when `previous` is given; the rest are reported «not run»
with the reason, so coverage is explicit — never silently passed."""
import csv, hashlib, re, uuid
from pathlib import Path
from lxml import etree
from ..checks.pdf import check as pdf_check

XLINK = '{http://www.w3c.org/1999/xlink}href'
NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
RULES = {}


def rule(*ids):
    def deco(fn):
        for i in ids:
            RULES[i] = fn
        return fn
    return deco


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


class Ctx:
    def __init__(self, seq_dir, profile_root, previous=None):
        self.previous = {Path(p).name: Path(p) for p in (previous or [])}
        self._prev_xml = {}
        self.base = Path(seq_dir)
        self.seq = self.base.name
        self.profile = Path(profile_root)
        self.files = sorted(p.relative_to(self.base).as_posix() for p in self.base.rglob('*') if p.is_file())
        self.dirs = sorted(p.relative_to(self.base).as_posix() for p in self.base.rglob('*') if p.is_dir())
        self.index, self.index_err = self._parse('index.xml')
        self.reg, self.reg_err = self._parse('m1/eg/eg-regional.xml')
        self.leaves = []                     # (xml, element, resolved path from sequence root)
        if self.index is not None:
            for lf in self.index.iter('leaf'):
                self.leaves.append(('index.xml', lf, lf.get(XLINK) or ''))
        if self.reg is not None:
            for lf in self.reg.iter('leaf'):
                h = lf.get(XLINK) or ''
                self.leaves.append(('eg-regional.xml', lf, ('m1/eg/' + h) if h else ''))
        self._pdf = {}

    def _parse(self, rel):
        """Well-formedness, then validity against the DTD named in the file's own DOCTYPE
        (lxml's parse-time validation mishandles the ICH DTD's parameter entities; a
        separate etree.DTD object validates like xmllint)."""
        p = self.base / rel
        if not p.exists():
            return None, 'missing'
        try:
            t = etree.parse(str(p), etree.XMLParser(load_dtd=False, resolve_entities=False, no_network=True))
        except etree.XMLSyntaxError as e:
            return None, f'not well formed: {e}'
        sysid = t.docinfo.system_url
        if not sysid:
            return t.getroot(), ['no DOCTYPE']
        dtd_path = (p.parent / sysid).resolve()
        if not dtd_path.is_file():
            return t.getroot(), [f'DTD {sysid} not found']
        try:
            dtd = etree.DTD(str(dtd_path))
        except etree.DTDParseError as e:
            return t.getroot(), [f'DTD unreadable: {e}']
        if dtd.validate(t):
            return t.getroot(), []
        return t.getroot(), [f'{e.line}: {e.message}' for e in dtd.error_log.filter_from_errors()][:50]

    def prev_xml(self, seq, which):
        k = (seq, which)
        if k not in self._prev_xml:
            p = self.previous.get(seq)
            f = p / ('index.xml' if which == 'index' else 'm1/eg/eg-regional.xml') if p else None
            self._prev_xml[k] = etree.parse(str(f)).getroot() if f and f.exists() else None
        return self._prev_xml[k]

    def env(self, tag):
        if self.reg is None:
            return []
        return self.reg.findall(f'.//envelope/{tag}')

    def pdf(self, rel):
        if rel not in self._pdf:
            self._pdf[rel] = pdf_check(str(self.base / rel), 'company_technical')
        return self._pdf[rel]

    def content_files(self):
        return [f for f in self.files if f.split('/')[0] in ('m1', 'm2', 'm3', 'm4', 'm5')]


def _exists(ctx, rel, folder_rule=False):
    return [] if (ctx.base / rel).is_file() else [f'{rel} missing']


@rule('EG-PF-1.1', 'EG-PF-1.2')
def r_ich_dtd(ctx, rid):
    return _exists(ctx, 'util/dtd/ich-ectd-3-2.dtd')


@rule('EG-PF-2.1', 'EG-PF-2.2')
def r_ich_xsl(ctx, rid):
    return _exists(ctx, 'util/style/ectd-2-0.xsl')


@rule('EG-PF-3.1', 'EG-PF-3.2')
def r_eg_dtd(ctx, rid):
    return _exists(ctx, 'util/dtd/eg-regional.dtd')


@rule('EG-PF-4.1', 'EG-PF-4.2')
def r_leafmod(ctx, rid):
    return _exists(ctx, 'util/dtd/eg-leaf.mod')


@rule('EG-PF-5.1', 'EG-PF-5.2')
def r_envmod(ctx, rid):
    return _exists(ctx, 'util/dtd/eg-envelope.mod')


@rule('EG-PF-6.1', 'EG-PF-6.2')
def r_egxsl(ctx, rid):
    return _exists(ctx, 'util/style/eg-regional.xsl')


@rule('EG-PF-1.3', 'EG-PF-2.3', 'EG-PF-3.3', 'EG-PF-4.3', 'EG-PF-5.3', 'EG-PF-6.3')
def r_util_checksums(ctx, rid):
    """'Published' checksum = the provisional profile's file (EDA has published none)."""
    f = {'EG-PF-1.3': 'dtd/ich-ectd-3-2.dtd', 'EG-PF-2.3': 'style/ectd-2-0.xsl', 'EG-PF-3.3': 'dtd/eg-regional.dtd',
         'EG-PF-4.3': 'dtd/eg-leaf.mod', 'EG-PF-5.3': 'dtd/eg-envelope.mod', 'EG-PF-6.3': 'style/eg-regional.xsl'}[rid]
    a, b = ctx.base / 'util' / f, ctx.profile / 'util' / f
    if not a.exists():
        return [f'util/{f} missing']
    return [] if md5(a) == md5(b) else [f'util/{f} differs from the profile copy']


@rule('EG-PF-7.1', 'EG-PF-7.2')
def r_index_present(ctx, rid):
    return _exists(ctx, 'index.xml')


@rule('EG-PF-7.3')
def r_index_wf(ctx, rid):
    return [] if ctx.index is not None else [f'index.xml {ctx.index_err}']


@rule('EG-PF-7.4')
def r_index_valid(ctx, rid):
    return ['index.xml missing'] if ctx.index is None else list(ctx.index_err or [])


@rule('EG-PF-7.5')
def r_index_doctype(ctx, rid):
    if ctx.index is None:
        return ['index.xml missing']
    sysid = ctx.index.getroottree().docinfo.system_url
    return [] if sysid == 'util/dtd/ich-ectd-3-2.dtd' else [f'DOCTYPE points to {sysid!r}']


@rule('EG-PF-7.6')
def r_index_xsl(ctx, rid):
    txt = (ctx.base / 'index.xml').read_text(encoding='utf-8', errors='replace') if (ctx.base / 'index.xml').exists() else ''
    return [] if 'href="util/style/ectd-2-0.xsl"' in txt else ['xml-stylesheet does not point to util/style/ectd-2-0.xsl']


@rule('EG-PF-8.1', 'EG-PF-8.2')
def r_md5_present(ctx, rid):
    return _exists(ctx, 'index-md5.txt')


@rule('EG-PF-8.3')
def r_md5(ctx, rid):
    p = ctx.base / 'index-md5.txt'
    if not p.exists() or not (ctx.base / 'index.xml').exists():
        return ['index-md5.txt or index.xml missing']
    return [] if p.read_text().strip().lower() == md5(ctx.base / 'index.xml') else ['checksum does not match index.xml']


@rule('EG-PF-9.1', 'EG-PF-9.2')
def r_reg_present(ctx, rid):
    return _exists(ctx, 'm1/eg/eg-regional.xml')


@rule('EG-PF-9.3')
def r_reg_wf(ctx, rid):
    return [] if ctx.reg is not None else [f'eg-regional.xml {ctx.reg_err}']


@rule('EG-PF-9.4')
def r_reg_valid(ctx, rid):
    return ['eg-regional.xml missing'] if ctx.reg is None else list(ctx.reg_err or [])


@rule('EG-PF-9.5')
def r_reg_doctype(ctx, rid):
    if ctx.reg is None:
        return ['eg-regional.xml missing']
    s = ctx.reg.getroottree().docinfo.system_url
    return [] if s == '../../util/dtd/eg-regional.dtd' else [f'DOCTYPE points to {s!r}']


@rule('EG-PF-9.6')
def r_reg_xsl(ctx, rid):
    p = ctx.base / 'm1/eg/eg-regional.xml'
    txt = p.read_text(encoding='utf-8', errors='replace') if p.exists() else ''
    return [] if 'href="../../util/style/eg-regional.xsl"' in txt else ['xml-stylesheet does not point to util/style/eg-regional.xsl']


@rule('EG-PF-9.7', 'EG-BP-E15')
def r_uuid(ctx, rid):
    out = []
    for e in ctx.env('identifier'):
        try:
            u = uuid.UUID((e.text or '').strip())
            if rid == 'EG-BP-E15' and u.version != 4:
                out.append(f'UUID version {u.version}, not 4')
        except ValueError:
            out.append(f'not a UUID: {e.text!r}')
    return out or ([] if ctx.env('identifier') else ['no identifier'])


@rule('EG-PF-9.9')
def r_uuid_same(ctx, rid):
    ids = {(e.text or '').strip() for e in ctx.env('identifier')}
    return [] if len(ids) <= 1 else ['different UUIDs in one sequence']


@rule('EG-PF-10.1')
def r_empty_headings(ctx, rid):
    out = []
    for name, root in (('index.xml', ctx.index), ('eg-regional.xml', ctx.reg)):
        if root is None:
            continue
        for el in root.iter():
            if not isinstance(el.tag, str) or el.tag in ('leaf', 'title', 'link-text', 'eg-envelope', 'envelope') or \
                    el.getparent() is not None and el.getparent().tag in ('envelope', 'submission', 'procedure-tracking'):
                continue
            if el.tag.startswith('m') and len(el) == 0:
                out.append(f'{name}: empty heading <{el.tag}>')
    return out


@rule('EG-PF-11.1')
def r_cktype(ctx, rid):
    return [f"{x}: leaf {lf.get('ID')} checksum-type {lf.get('checksum-type')}" for x, lf, _ in ctx.leaves
            if lf.get('operation') != 'delete' and (lf.get('checksum-type') or '').lower() != 'md5']


MOD_RE = re.compile(r'^(?:\.\./)+(\d{4})/(index\.xml|m1/eg/eg-regional\.xml)#(.+)$')


def _target(ctx, lf):
    m = MOD_RE.match(lf.get('modified-file') or '')
    if not m:
        return None, 'modified-file is not ../SSSS/index.xml#ID or ../../../SSSS/m1/eg/eg-regional.xml#ID'
    seq, f, lid = m.groups()
    if seq not in ctx.previous:
        return None, f'sequence {seq} not available'
    root = ctx.prev_xml(seq, 'index' if f == 'index.xml' else 'regional')
    tgt = None if root is None else next((x for x in root.iter('leaf') if x.get('ID') == lid), None)
    return tgt, None if tgt is not None else f'leaf {lid} not found in {seq}/{f}'


@rule('EG-PF-11.9')
def r_modfile_target(ctx, rid):
    out = []
    for x, lf, _ in ctx.leaves:
        if lf.get('operation') in ('replace', 'delete', 'append'):
            tgt, why = _target(ctx, lf)
            if tgt is None:
                out.append(f"leaf {lf.get('ID')}: {why}")
    return out


@rule('EG-PF-11.10')
def r_same_location(ctx, rid):
    def loc(el):
        p = el.getparent()
        a = dict(p.attrib) if p is not None else {}
        return (p.tag if p is not None else None, tuple(sorted(a.items())))
    out = []
    for x, lf, _ in ctx.leaves:
        if lf.get('operation') in ('replace', 'delete', 'append'):
            tgt, _ = _target(ctx, lf)
            if tgt is not None and loc(tgt) != loc(lf):
                out.append(f"leaf {lf.get('ID')} is in {loc(lf)[0]}, target in {loc(tgt)[0]}")
    return out


@rule('EG-PF-9.8')
def r_uuid_lifecycle(ctx, rid):
    lower = sorted(s for s in ctx.previous if s < ctx.seq)
    if not lower:
        return []
    root = ctx.prev_xml(lower[-1], 'regional')
    prev = root.findtext('.//envelope/identifier') if root is not None else None
    cur = [(e.text or '').strip() for e in ctx.env('identifier')]
    return [] if prev and cur and cur[0] == prev.strip() else [f'UUID {cur} differs from {lower[-1]} ({prev})']


@rule('EG-PF-13.2')
def r_seq_unused(ctx, rid):
    return [f'sequence {ctx.seq} already used'] if ctx.seq in ctx.previous and ctx.previous[ctx.seq] != ctx.base else []


@rule('EG-PF-11.6')
def r_href_exists(ctx, rid):
    return [f'{rel} missing' for x, lf, rel in ctx.leaves
            if lf.get('operation') in ('new', 'replace', 'append') and rel and not (ctx.base / rel).is_file()]


@rule('EG-PF-11.2')
def r_leaf_md5(ctx, rid):
    out = []
    for x, lf, rel in ctx.leaves:
        if lf.get('operation') == 'delete':
            continue
        p = ctx.base / rel
        if not p.is_file():
            out.append(f'{rel} not in this sequence (lifecycle reference not checked)')
        elif md5(p) != (lf.get('checksum') or '').lower():
            out.append(f'{rel}: checksum mismatch')
    return out


@rule('EG-PF-11.3')
def r_titles(ctx, rid):
    return [f"leaf {lf.get('ID')} has no title" for _, lf, _ in ctx.leaves
            if lf.find('title') is None or not (lf.find('title').text or '').strip()]


@rule('EG-PF-11.4')
def r_href(ctx, rid):
    return [f"leaf {lf.get('ID')} ({lf.get('operation')}) has no href" for _, lf, rel in ctx.leaves
            if lf.get('operation') in ('new', 'replace', 'append') and not lf.get(XLINK)]


@rule('EG-PF-11.5')
def r_delete_nohref(ctx, rid):
    return [f"leaf {lf.get('ID')} delete with href" for _, lf, _ in ctx.leaves if lf.get('operation') == 'delete' and lf.get(XLINK)]


@rule('EG-PF-11.7')
def r_modfile(ctx, rid):
    return [f"leaf {lf.get('ID')} {lf.get('operation')} without modified-file" for _, lf, _ in ctx.leaves
            if lf.get('operation') in ('replace', 'delete', 'append') and not lf.get('modified-file')]


@rule('EG-PF-11.8')
def r_new_nomod(ctx, rid):
    return [f"leaf {lf.get('ID')} new with modified-file" for _, lf, _ in ctx.leaves
            if lf.get('operation') == 'new' and lf.get('modified-file')]


@rule('EG-PF-11.11')
def r_unique_ids(ctx, rid):
    seen, out = set(), []
    for _, lf, _ in ctx.leaves:
        if lf.get('ID') in seen:
            out.append(f"duplicate leaf ID {lf.get('ID')}")
        seen.add(lf.get('ID'))
    return out


@rule('EG-PF-12.1')
def r_nodeext(ctx, rid):
    out = []
    for root in (ctx.index, ctx.reg):
        if root is not None:
            for ne in root.iter('node-extension'):
                t = ne.find('title')
                if t is None or not (t.text or '').strip():
                    out.append('node-extension without title')
    return out


@rule('EG-PF-13.1')
def r_seqname(ctx, rid):
    return [] if re.fullmatch(r'\d{4}', ctx.seq) else [f'sequence folder {ctx.seq!r}']


@rule('EG-PF-13.3', 'EG-PF-E07')
def r_seq_env(ctx, rid):
    seqs = [(e.text or '').strip() for e in ctx.env('sequence')]
    rel = [(e.text or '').strip() for e in ctx.env('related-sequence')]
    if rid == 'EG-PF-13.3':
        return [] if seqs and all(s == ctx.seq for s in seqs) else [f'envelope sequence {seqs} vs folder {ctx.seq}']
    return [f'not 4 digits: {x}' for x in seqs + rel if not re.fullmatch(r'\d{4}', x)]


@rule('EG-PF-14.5')
def r_pi_country(ctx, rid):
    if ctx.reg is None:
        return []
    env_c = {e.get('country') for e in ctx.reg.iter('envelope')}
    return [f"pi-doc country {p.get('country')} has no envelope" for p in ctx.reg.iter('pi-doc') if p.get('country') not in env_c]


@rule('EG-PF-14.6')
def r_related_initial(ctx, rid):
    units = [e.get('type') for e in ctx.env('submission-unit')]
    rel = [(e.text or '').strip() for e in ctx.env('related-sequence')]
    if units and units[0] in ('initial', 'reformat'):
        return [] if rel == [ctx.seq] else [f'initial/reformat: related-sequence {rel}, expected [{ctx.seq}]']
    return []


@rule('EG-PF-14.7')
def r_related_lower(ctx, rid):
    units = [e.get('type') for e in ctx.env('submission-unit')]
    rel = [(e.text or '').strip() for e in ctx.env('related-sequence')]
    if units and units[0] not in ('initial', 'reformat'):
        return [f'related-sequence {r} is not lower than {ctx.seq}' for r in rel if not r < ctx.seq]
    return []


@rule('EG-BP-14.8')
def r_inn(ctx, rid):
    st = [e.get('type') for e in ctx.env('submission')]
    un = [e.get('type') for e in ctx.env('submission-unit')]
    if st and st[0].startswith('maa') and un and un[0] == 'initial' and not ctx.env('inn'):
        return ['no inn for an initial MAA']
    return []


@rule('EG-PF-15.3')
def r_pathlen(ctx, rid):
    return [f'{ctx.seq}/{f} ({len(ctx.seq + "/" + f)})' for f in ctx.files if len(f'{ctx.seq}/{f}') > 180]


@rule('EG-PF-15.4')
def r_namelen(ctx, rid):
    return [f for f in ctx.files if len(f.split('/')[-1]) > 64]


@rule('EG-PF-15.5')
def r_dirlen(ctx, rid):
    return [d for d in ctx.dirs if len(d.split('/')[-1]) > 64]


@rule('EG-PF-15.6')
def r_namechars(ctx, rid):
    return [f for f in ctx.files if not NAME_RE.match(f.split('/')[-1])]


@rule('EG-PF-15.7')
def r_dirchars(ctx, rid):
    return [d for d in ctx.dirs if not NAME_RE.match(d.split('/')[-1])]


@rule('EG-PF-15.8')
def r_unreferenced(ctx, rid):
    refs = {rel for _, _, rel in ctx.leaves} | {'m1/eg/eg-regional.xml'}
    return [f for f in ctx.content_files() if f not in refs]


@rule('EG-PF-15.9')
def r_top_files(ctx, rid):
    return [f for f in ctx.files if '/' not in f and f not in ('index.xml', 'index-md5.txt')]


@rule('EG-PF-15.10')
def r_empty_dirs(ctx, rid):
    return [d for d in ctx.dirs if not any((ctx.base / d).iterdir())]


@rule('EG-PF-15.11', 'EG-PF-15.12')
def r_tracking(ctx, rid):
    tr = [f for f in ctx.files if f.startswith('m1/eg/10-cover/tracking')]
    if rid == 'EG-PF-15.11':
        return [] if tr else ['no tracking table in m1/eg/10-cover/']
    bad = [f for f in ctx.files if f.startswith('m1/eg/10-cover/') and not re.match(r'm1/eg/10-cover/(cover|tracking)(-[a-z0-9-]+)?\.pdf$', f)]
    return bad


@rule('EG-BP-15.BP1')
def r_size(ctx, rid):
    return [f for f in ctx.content_files() if (ctx.base / f).stat().st_size > 500 * 2 ** 20]


@rule('EG-PF-16.1', 'EG-PF-16.2', 'EG-PF-16.3', 'EG-PF-16.5', 'EG-BP-16.BP1', 'EG-BP-E23')
def r_pdf(ctx, rid):
    out = []
    for f in ctx.content_files():
        if not f.lower().endswith('.pdf'):
            continue
        for fd in ctx.pdf(f).findings:
            if fd.rule == rid or (rid == 'EG-BP-E23' and fd.rule in ('EG-BP-E23', 'NTA065-N4')):
                out.append(f'{f}: {fd.en}')
    return out


@rule('EG-PF-E01')
def r_envelope_one(ctx, rid):
    envs = list(ctx.reg.iter('envelope')) if ctx.reg is not None else []
    return [] if len(envs) == 1 and envs[0].get('country') == 'eg' else [f'{len(envs)} envelopes']


@rule('EG-PF-E02')
def r_agency(ctx, rid):
    a = [e.get('code') for e in ctx.env('agency')]
    return [] if a == ['EG-EDA'] else [f'agency {a}']


@rule('EG-PF-E03')
def r_regmkt(ctx, rid):
    return [] if ctx.env('registration') and ctx.env('marketing') else ['registration/marketing type missing']


@rule('EG-PF-E04', 'EG-BP-E07')
def r_mode(ctx, rid):
    s = ctx.env('submission')
    if not s:
        return []
    is_var = (s[0].get('type') or '').startswith(('var-', 'ipv', 'imv', 'ibv', 'np-', 'rp-', 'rl-', 'not-'))
    has = s[0].get('mode') is not None
    if rid == 'EG-PF-E04':
        return ['variation without mode'] if is_var and not has else []
    return ['mode on a non-variation'] if has and not is_var else []


@rule('EG-PF-E05')
def r_reformat(ctx, rid):
    s, u = ctx.env('submission'), ctx.env('submission-unit')
    if not s or not u:
        return []
    return [] if (u[0].get('type') == 'reformat') == (s[0].get('type') == 'none') else ['reformat iff type none']


@rule('EG-PF-E06')
def r_mandatory_text(ctx, rid):
    out = []
    for tag in ('identifier', 'applicant', 'invented-name', 'procedure-tracking/number', 'submission-description'):
        if not any((e.text or '').strip() for e in ctx.env(tag) or ctx.reg.findall(f'.//{tag}') if ctx.reg is not None):
            out.append(f'{tag} empty')
    return out


@rule('EG-PF-E08')
def r_m1_leaf(ctx, rid):
    if ctx.index is None:
        return ['index.xml missing']
    m1 = ctx.index.find('m1-administrative-information-and-prescribing-information')
    leaves = m1.findall('leaf') if m1 is not None else []
    return [] if len(leaves) == 1 and leaves[0].get(XLINK) == 'm1/eg/eg-regional.xml' else ['m1 must hold exactly one leaf to eg-regional.xml']


@rule('EG-PF-E11')
def r_parent_docs(ctx, rid):
    parents = {'m1-2-form', 'm1-2-2-legal', 'm1-2-3-edaapp', 'm1-2-4-declar', 'm1-2-5-refprod', 'm1-2-6-importdoc',
               'm1-2-7-reliance', 'm1-2-8-composit', 'm1-2-10-postappch', 'm1-2-12-analysreq', 'm1-2-13-plasma',
               'm1-2-15-relpv', 'm1-2-16-relinsp'}
    if ctx.reg is None:
        return []
    return [f'leaf directly in {el.tag}' for el in ctx.reg.iter() if isinstance(el.tag, str) and el.tag in parents
            and el.find('leaf') is not None]


@rule('EG-PF-E12')
def r_gmo(ctx, rid):
    if ctx.reg is None:
        return []
    return ['both 1.6.1 and 1.6.2'] if ctx.reg.find('.//m1-6-1-non-gmo') is not None and ctx.reg.find('.//m1-6-2-gmo') is not None else []


@rule('EG-PF-E13')
def r_pidoc(ctx, rid):
    if ctx.reg is None:
        return []
    out = []
    for p in ctx.reg.iter('pi-doc'):
        lang = p.get('{http://www.w3.org/XML/1998/namespace}lang')
        if lang not in ('ar', 'en') or p.get('country') != 'eg':
            out.append(f"pi-doc lang={lang} country={p.get('country')}")
    return out


@rule('EG-BP-E01')
def r_cover(ctx, rid):
    return [] if any(re.match(r'm1/eg/10-cover/cover(-[a-z0-9-]+)?\.pdf$', f) for f in ctx.files) else ['no cover letter']


@rule('EG-BP-E02')
def r_cover_new(ctx, rid):
    return [f"{rel} uses {lf.get('operation')}" for _, lf, rel in ctx.leaves if rel.startswith('m1/eg/10-cover/') and lf.get('operation') != 'new']


@rule('EG-BP-E04')
def r_formaf(ctx, rid):
    return [f for f in ctx.files if f.startswith('m1/eg/12-form/121-af/') and not re.match(r'.*/form-af(-[a-z0-9-]+)?\.pdf$', f)]


@rule('EG-BP-E05')
def r_reg_leaf_new(ctx, rid):
    return [f"eg-regional leaf uses {lf.get('operation')}" for x, lf, rel in ctx.leaves if rel == 'm1/eg/eg-regional.xml' and lf.get('operation') != 'new']


@rule('EG-BP-E06')
def r_append(ctx, rid):
    return [f"{rel} uses append" for _, lf, rel in ctx.leaves if lf.get('operation') == 'append']


@rule('EG-BP-E08')
def r_one_name(ctx, rid):
    return [] if len(ctx.env('invented-name')) <= 1 else ['more than one invented-name']


@rule('EG-BP-E16')
def r_pi_lang_folder(ctx, rid):
    if ctx.reg is None:
        return []
    out = []
    for p in ctx.reg.iter('pi-doc'):
        lang = p.get('{http://www.w3.org/XML/1998/namespace}lang')
        for lf in p.iter('leaf'):
            h = lf.get(XLINK) or ''
            if not h.startswith(f'13-pi/131-spclabelpl/{lang}/'):
                out.append(f'{h} not in language folder {lang}')
    return out


@rule('EG-BP-E18')
def r_resp_sub(ctx, rid):
    return [d for d in ctx.dirs if d.startswith('m1/eg/responses/')]


@rule('EG-BP-E20')
def r_word(ctx, rid):
    return [f for f in ctx.content_files() if f.lower().endswith(('.doc', '.docx', '.rtf', '.odt', '.xls', '.xlsx'))]


@rule('EG-BP-E28')
def r_m1_util(ctx, rid):
    return [f for f in ctx.files if f.startswith('m1/eg/util/')]


def load_rules(profile_root):
    rows = list(csv.DictReader(open(Path(profile_root) / 'validation-criteria.csv', encoding='utf-8')))
    return [r for r in rows if r['mapping'] != 'DROP' and not r['rule_id'].startswith('DROPPED')]


LIFECYCLE = {'EG-PF-11.9', 'EG-PF-11.10', 'EG-PF-9.8', 'EG-PF-13.2', 'EG-PF-11.6'}


def validate(seq_dir, profile_root, previous=None):
    """previous: earlier sequence folders of the same application (enables the lifecycle rules)."""
    ctx = Ctx(seq_dir, profile_root, previous)
    results = []
    for r in load_rules(profile_root):
        rid = r['rule_id']
        sev = 'pass_fail' if r['category'].startswith('Pass') else 'best_practice'
        base = {'rule': rid, 'severity': sev, 'text': r['rule_text'], 'provenance': r['provenance'], 'source': r['source']}
        fn = RULES.get(rid)
        if rid in LIFECYCLE and previous is None:
            fn = None
        if fn is None:
            reason = 'needs earlier sequences (lifecycle)' if r['lifecycle_needed'] == 'Y' else 'not automated yet (manual/visual check)'
            results.append({**base, 'status': 'not_run', 'reason': reason, 'failures': []})
            continue
        fails = fn(ctx, rid)
        status = 'pass' if not fails else ('fail' if sev == 'pass_fail' else 'warning')
        if rid in ('EG-PF-1.3', 'EG-PF-2.3', 'EG-PF-3.3', 'EG-PF-4.3', 'EG-PF-5.3', 'EG-PF-6.3') and fails:
            status = 'warning'         # no published EDA checksum yet: warn only (profile README risk 5)
        results.append({**base, 'status': status, 'failures': fails[:50]})
    return summarise(results)


def summarise(results):
    count = {k: sum(1 for r in results if r['status'] == k) for k in ('pass', 'fail', 'warning', 'not_run')}
    return {'ok': count['fail'] == 0, 'counts': count, 'coverage': f"{len(results) - count['not_run']}/{len(results)}",
            'label': 'Conforms to EDA drafts + ICH (provisional EG profile v0) — not «EDA-valid».' if count['fail'] == 0
            else 'Does not conform to the provisional EG profile.', 'results': results}
