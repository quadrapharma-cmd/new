"""Check any eCTD 3.2.2 package, whoever made it (updates list, item 18): a ZIP of one sequence or of several. Each sequence (a
four-digit folder with its index.xml) is checked by its region's validator — Egypt's provisional profile (m1/eg/eg-regional.xml) or
the EU's criteria 8.2 (m1/eu/eu-regional.xml), earlier sequences given for the lifecycle rules — and a region the program has no
criteria for gets the ICH checks every eCTD must pass: the backbone parses, every leaf's file is there with its MD5, no file is left
unreferenced, index-md5.txt matches. Two packages can be compared: what was added, removed or changed, sequence by sequence."""
import hashlib, re, shutil, tempfile
from pathlib import Path, PurePosixPath
from lxml import etree

XLINK = '{http://www.w3c.org/1999/xlink}href'


class PackageError(ValueError):
    def __init__(self, code, en, ar):
        super().__init__(en)
        self.code, self.en, self.ar = code, en, ar


def write_files(files, root):
    """Files from an archive into `root`, never outside it."""
    root = Path(root)
    for name, data in files:
        parts = [p for p in PurePosixPath(str(name).replace('\\', '/')).parts if p not in ('', '.', '..', '/')]
        if not parts:
            continue
        dest = root.joinpath(*parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return root


def sequences(root):
    """Every sequence folder (four digits, holding its index.xml), in order."""
    return sorted((p.parent for p in Path(root).rglob('index.xml') if re.fullmatch(r'\d{4}', p.parent.name)), key=lambda p: p.name)


def region_of(seq):
    for reg in ('eu', 'eg'):
        if (seq / 'm1' / reg / f'{reg}-regional.xml').exists():
            return reg
    return None


def leaves(seq):
    """{href: {'md5', 'operation', 'title', 'modified', 'xml'}} of the backbone and the regional XML."""
    out = {}
    for xml in [seq / 'index.xml'] + sorted((seq / 'm1').glob('*/*-regional.xml')) if (seq / 'm1').exists() else [seq / 'index.xml']:
        try:
            tree = etree.parse(str(xml))
        except (etree.XMLSyntaxError, OSError):
            continue
        base = xml.parent.relative_to(seq)
        for lf in tree.iter('leaf'):
            href = lf.get(XLINK) or ''
            rel = (base / href).as_posix() if href else ''
            t = lf.find('title')
            out[_norm(rel)] = {'md5': (lf.get('checksum') or '').lower(), 'operation': lf.get('operation'), 'title': (t.text or '').strip() if t is not None else '',
                               'modified': lf.get('modified-file'), 'xml': xml.name}
    return out


def _norm(p):
    parts = []
    for x in PurePosixPath(p).parts:
        if x == '..':
            parts and parts.pop()
        elif x not in ('.', ''):
            parts.append(x)
    return '/'.join(parts)


def ich_checks(seq):
    """The checks every eCTD 3.2.2 sequence must pass, whatever its region."""
    results = []

    def res(rid, text, fails):
        results.append({'rule': rid, 'severity': 'pass_fail', 'text': text, 'provenance': 'ICH', 'source': 'ICH eCTD Specification v3.2.2',
                        'status': 'fail' if fails else 'pass', 'failures': fails[:50]})
    idx = seq / 'index.xml'
    try:
        etree.parse(str(idx))
        res('ICH-XML', 'index.xml is well-formed XML.', [])
    except etree.XMLSyntaxError as e:
        res('ICH-XML', 'index.xml is well-formed XML.', [str(e)])
        return results
    md5f = seq / 'index-md5.txt'
    real = hashlib.md5(idx.read_bytes()).hexdigest()
    got = md5f.read_text(errors='replace').strip().split()[0].lower() if md5f.exists() and md5f.read_text(errors='replace').strip() else ''
    res('ICH-MD5-INDEX', 'index-md5.txt holds the MD5 of index.xml.', [] if got == real else [f'index-md5.txt: «{got or "missing"}», index.xml: {real}'])
    lv = leaves(seq)
    missing, bad = [], []
    for href, x in lv.items():
        if x['operation'] == 'delete':
            continue
        f = seq / href
        if not f.exists():
            missing.append(href)
        elif x['md5'] and hashlib.md5(f.read_bytes()).hexdigest() != x['md5']:
            bad.append(href)
    res('ICH-FILE', 'Every leaf\'s file is in the sequence.', missing)
    res('ICH-MD5', 'Every leaf\'s file has the MD5 its leaf states.', bad)
    known = set(lv) | {'index.xml', 'index-md5.txt'}
    extra = [p.relative_to(seq).as_posix() for p in seq.rglob('*') if p.is_file()]
    extra = [p for p in extra if p not in known and not p.startswith('util/') and not re.fullmatch(r'm1/[a-z]{2}/[a-z]{2}-regional\.xml', p)]
    res('ICH-EXTRA', 'No file in the sequence that no leaf refers to.', extra)
    from .ectd32 import summarise
    return summarise(results)


def validate_files(files, name='package'):
    """files: [(path, bytes)] of the package → {'sequences': [{seq, region, ok, counts, coverage}], 'reports': {...}, 'html'}."""
    from . import ectd32 as v32, ectd32_eu as v32eu, report
    from ..writers import ectd32 as w32, ectd32_eu as w32eu
    tmp = Path(tempfile.mkdtemp())
    try:
        write_files(files, tmp)
        seqs = sequences(tmp)
        if not seqs:
            raise PackageError('E-NO-SEQUENCE', 'No eCTD sequence in the package: a four-digit folder (0000, 0001…) holding its index.xml.',
                               'مفيش تسلسل eCTD في الملف: فولدر من 4 أرقام (0000، 0001…) جواه index.xml.')
        reports, rows, prev, regions = {}, [], [], set()
        for s in seqs:
            reg = region_of(s)
            regions.add(reg)
            if reg == 'eu':
                rep = v32eu.validate(s, w32eu.DEFAULT_PROFILE, previous=list(prev))
            elif reg == 'eg':
                rep = v32.validate(s, w32.DEFAULT_PROFILE, previous=list(prev))
            else:
                rep = ich_checks(s)
            label = f"{s.name} · {'EU M1 3.1.1' if reg == 'eu' else 'EG (provisional profile)' if reg == 'eg' else 'ICH only'}"
            reports[label] = rep
            rows.append({'sequence': s.name, 'region': reg or 'ich', 'ok': rep['ok'], 'counts': rep['counts'], 'coverage': rep['coverage']})
            prev.append(s)
        note = report.EU_NOTE if regions == {'eu'} else report.EG_NOTE if regions == {'eg'} else (
            'A region this program has no criteria for: only the ICH checks every eCTD must pass were run. Not an authority\'s validator.')
        return {'name': name, 'sequences': rows, 'ok': all(r['ok'] for r in rows), 'html': report.render(name, reports, note)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def compare_files(files_a, files_b):
    """What changed from package A to package B, sequence by sequence: leaves added, removed, changed (another MD5), retitled."""
    ta, tb = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
    try:
        write_files(files_a, ta)
        write_files(files_b, tb)
        sa, sb = {s.name: s for s in sequences(ta)}, {s.name: s for s in sequences(tb)}
        if not sa or not sb:
            raise PackageError('E-NO-SEQUENCE', 'Each package needs at least one eCTD sequence (a four-digit folder with its index.xml).',
                               'كل ملف محتاج تسلسل eCTD واحد على الأقل (فولدر من 4 أرقام جواه index.xml).')
        out = []
        for name in sorted(set(sa) | set(sb)):
            if name not in sb or name not in sa:
                out.append({'sequence': name, 'only_in': 'a' if name in sa else 'b', 'changes': []})
                continue
            la, lb = leaves(sa[name]), leaves(sb[name])
            ch = []
            real = lambda seq, href: hashlib.md5((seq / href).read_bytes()).hexdigest() if (seq / href).is_file() else None
            for href in sorted(set(la) | set(lb)):
                a, b = la.get(href), lb.get(href)
                if a and not b:
                    ch.append({'href': href, 'change': 'removed', 'title': a['title']})
                elif b and not a:
                    ch.append({'href': href, 'change': 'added', 'title': b['title'], 'operation': b['operation']})
                elif a['md5'] != b['md5'] or real(sa[name], href) != real(sb[name], href):       # the stated checksum, or the file itself
                    ch.append({'href': href, 'change': 'changed', 'title': b['title']})
                elif a['title'] != b['title'] or a['operation'] != b['operation']:
                    ch.append({'href': href, 'change': 'retitled' if a['title'] != b['title'] else 'operation', 'title': b['title'], 'was': a['title'],
                               'operation': b['operation']})
            out.append({'sequence': name, 'only_in': None, 'changes': ch})
        return {'sequences': out, 'same': all(not s['changes'] and not s['only_in'] for s in out)}
    finally:
        shutil.rmtree(ta, ignore_errors=True)
        shutil.rmtree(tb, ignore_errors=True)
