"""Check any eCTD 3.2.2 package, whoever made it (updates list, item 18): a ZIP of one sequence or of several. Each sequence (a
four-digit folder with its index.xml) goes through the check for any country (global_ectd.py): first the ICH rules every eCTD must
pass in every region (ICH's validator checklist, eCTD Q&A 36, and the format rules), then its region's own criteria where the program
has them — Egypt's provisional profile (m1/eg), the EU's criteria 8.2 (m1/eu), the GCC's specification (m1/gc) — earlier sequences
given for the lifecycle rules. Two packages can be compared: what was added, removed or changed, sequence by sequence."""
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


OWN = {'eu': 'EU M1 3.1.1 · criteria 8.2', 'eg': 'EG (provisional profile)', 'gc': 'GCC M1 1.5'}


def validate_files(files, name='package'):
    """files: [(path, bytes)] of the package → {'sequences': [{sequence, region, m1, ok, counts, coverage, ich}], 'html'}: `region` is
    the region whose own criteria were run (eu, eg, gc) or «ich» when only the ICH rules were; counts and coverage are those of the
    region's criteria (of the ICH rules for «ich»); `ich` is the ICH layer's own result; `ok` needs both."""
    from . import global_ectd, report
    tmp = Path(tempfile.mkdtemp())
    try:
        write_files(files, tmp)
        seqs = sequences(tmp)
        if not seqs:
            raise PackageError('E-NO-SEQUENCE', 'No eCTD sequence in the package: a four-digit folder (0000, 0001…) holding its index.xml.',
                               'لا يوجد تسلسل eCTD في الملف: مجلد من 4 أرقام (0000، 0001…) بداخله index.xml.')
        reports, rows, prev, notes = {}, [], [], []
        for s in seqs:
            res = global_ectd.validate(s, previous=list(prev))
            layers = list(res['layers'].values())
            ich, own = layers[0], (layers[1] if len(layers) > 1 else None)
            reg = res['region'] if own is not None else 'ich'
            reports[f'{s.name} · ICH (every country)'] = ich
            if own is not None:
                reports[f'{s.name} · {OWN[reg]}'] = own
            main = own or ich
            rows.append({'sequence': s.name, 'region': reg, 'm1': res['region'], 'ok': res['ok'], 'counts': main['counts'],
                         'coverage': main['coverage'], 'ich': {k: ich[k] for k in ('ok', 'counts', 'coverage')}})
            notes.append(global_ectd.note(res))
            prev.append(s)
        note = notes[0] if len(set(notes)) == 1 else (
            'Layer 1 is ICH\'s, the same in every country; each region\'s own criteria follow where the program has them. '
            'Not an authority\'s own validator.',
            'الطبقة الأولى قواعد ICH، وهي نفسها في كل الدول، ثم معايير كل منطقة حيث توجد في البرنامج. وهذه ليست أداة التحقق الخاصة بالجهة.')
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
                               'كل حزمة تحتاج إلى تسلسل eCTD واحد على الأقل (مجلد من 4 أرقام بداخله index.xml).')
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
