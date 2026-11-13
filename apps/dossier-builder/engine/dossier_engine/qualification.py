"""Qualification of the program where it is installed — IQ, OQ and the PQ protocol (updates list, item 33).

A company's quality unit may ask for the program to be qualified before it is used for regulatory files (a computerised system:
GAMP 5 thinking, the PIC/S and EU GMP Annex 11 expectations). The program qualifies itself on the machine it runs on:

  IQ  what is installed: the program's own files (a SHA-256 fingerprint of each part), Python and every library it needs with its
      version, the official schemas it checks against, the office converter, a workspace it can write to.
  OQ  that it works there: scripted checks run in a fresh workspace of their own (never the company's), each with what is
      expected and what happened — a positive and a negative control for the checks that decide (the upload gate, the PDF checks,
      the activity log's chain, the eCTD validator, the backup and its restore drill, the export gate).
  PQ  that it does the company's work: a protocol to run on one of the company's own products, with its acceptance criteria and
      signatures, and the evidence the workspace already holds (the exports and their validation results).

The package is a Word document with a traceability table (requirement → check → result) and the sign-off blocks; the JSON beside
it holds the same results. Nothing here replaces the company's own validation decisions: it gives them the evidence."""
import hashlib, importlib, io, json, os, platform, shutil, sys, tempfile, time
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
PARTS = {'engine': APP / 'engine' / 'dossier_engine', 'interface': APP / 'ui', 'rules': APP / 'rulepacks'}
LIBS = ('fastapi', 'starlette', 'pydantic', 'lxml', 'pypdf', 'yaml', 'docx')
OPTIONAL = ('openpyxl',)                                 # Excel sheets read faster with it; the program's own reader does without


def _digest(root):
    """SHA-256 over every file of `root` (its path and its bytes, in a fixed order), and how many files."""
    h, n = hashlib.sha256(), 0
    for p in sorted(x for x in Path(root).rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix != '.pyc'):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(hashlib.sha256(p.read_bytes()).digest())
        n += 1
    return h.hexdigest(), n


def _row(rows, rid, req, expected, actual, ok, kind='pass'):
    rows.append({'id': rid, 'requirement': req, 'expected': expected, 'actual': actual, 'result': ('pass' if ok else 'fail') if kind == 'pass' else kind})


def iq(workspace):
    rows = []
    for i, (name, root) in enumerate(PARTS.items(), 1):
        if root.exists():
            dg, n = _digest(root)
            _row(rows, f'IQ-0{i}', f'The program\'s {name} files are installed', 'present; fingerprint recorded', f'{n} files · SHA-256 {dg}', n > 0)
        else:
            _row(rows, f'IQ-0{i}', f'The program\'s {name} files are installed', 'present', 'missing', False)
    _row(rows, 'IQ-04', 'Python 3.10 or later', '≥ 3.10', platform.python_version(), sys.version_info >= (3, 10))
    for lib in LIBS + OPTIONAL:
        try:
            m = importlib.import_module(lib)
            v = getattr(m, '__version__', None) or getattr(m, 'VERSION', None) or getattr(m, 'Version', None) or 'present'
            _row(rows, 'IQ-05', f'Library {lib} is installed', 'importable', f'{lib} {v}', True)
        except Exception as e:                            # noqa: BLE001 — what is missing is what the row says
            _row(rows, 'IQ-05', f'Library {lib} is installed' + (' (optional)' if lib in OPTIONAL else ''), 'importable', f'{lib}: {e}',
                 False, kind='pass' if lib not in OPTIONAL else 'info')
    from .writers.ectd32 import DEFAULT_PROFILE, APP4
    schemas = {'ICH eCTD 3.2 DTD': DEFAULT_PROFILE / 'util' / 'dtd' / 'ich-ectd-3-2.dtd', 'ICH eCTD App. 4 table': APP4,
               'ICH STF DTD 2.2': APP / 'rulepacks' / 'ich.ectd.v322' / 'stf' / 'ich-stf-v2-2.dtd',
               'EG provisional criteria': DEFAULT_PROFILE / 'validation-criteria.csv'}
    try:
        from .writers.ectd32_eu import DEFAULT_PROFILE as EU
        schemas['EU M1 3.1.1 criteria'] = Path(EU) / 'validation-criteria.csv'
    except Exception:                                    # noqa: BLE001
        pass
    for name, p in schemas.items():
        ok = Path(p).is_file()
        _row(rows, 'IQ-06', f'Official schema: {name}', 'present', (hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] + '…') if ok else 'missing', ok)
    from .generate.docx_kit import find_soffice
    so = find_soffice()
    _row(rows, 'IQ-07', 'Office converter (Word → PDF), optional', 'present, or the page says Word stays Word', so or 'not installed',
         True, kind='pass' if so else 'info')
    from . import pdfcraft
    pe = pdfcraft.status()
    vendored = APP / 'vendor' / 'pdfcraft' / 'PIN'
    same = not vendored.exists() or vendored.read_text().strip() == pe['pin']
    _row(rows, 'IQ-09', 'PDF engine: PdfCraft at its pinned release (tools/pdfcraft/PIN)', f"PdfCraft {(pe['pin'] or '')[:7]}",
         (f"{pe['version']} · {(pe['pin'] or '')[:7]}" if pe['available'] else f"pypdf — {pe['why']}") + ('' if same else ' · the built program is another commit'),
         same, kind='pass' if pe['available'] or not same else 'info')
    try:
        probe = Path(workspace) / f'.iq-{os.getpid()}'
        probe.write_text('x')
        probe.unlink()
        _row(rows, 'IQ-08', 'The workspace can be written', 'write and remove a file', str(workspace), True)
    except OSError as e:
        _row(rows, 'IQ-08', 'The workspace can be written', 'write and remove a file', str(e), False)
    return rows


def _raw_pdf(stream):
    """One A4 page in Helvetica with the given content (no library needed)."""
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
            b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    o, offs = bytearray(b'%PDF-1.4\n'), []
    for i, x in enumerate(objs, 1):
        offs.append(len(o))
        o += b'%d 0 obj\n' % i + x + b'\nendobj\n'
    xr = len(o)
    o += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % f for f in offs)
    return bytes(o + b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xr))


def _pdf(path, lines):
    from .generate.docx_kit import text_pdf
    text_pdf(lines, path)
    return Path(path)


def oq():
    """The scripted checks, in a workspace of their own (removed afterwards)."""
    from .app.store import Store, StoreError
    from .checks.pdf import check as pdf_check
    from .writers import ectd32
    from .validators import ectd32 as v32
    from . import backup
    rows, tmp = [], Path(tempfile.mkdtemp(prefix='oq-'))
    try:
        st = Store(tmp / 'ws')
        prof = dict(dossier_kind='generic', origin='local', licence='toll', activity='new', apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='DMF')])
        did = st.create_dossier('OQ product', prof, dict(name='OQ product', dosageform='tablet', manufacturer='Example Pharm Co.'), {'tracking': 'OQ-0001'})
        n = len([s for s in st.slots(did) if s.active])
        _row(rows, 'OQ-01', 'A dossier for Egypt resolves its required items from the rules (NP.CAPP.065 v5)', 'more than 50 items', f'{n} items', n > 50)
        good = _pdf(tmp / 'stab.pdf', ['Stability summary and conclusion', 'Three primary batches, 25 C / 60 % RH, 12 months'])
        doc = st.add_document(did, 'P-16', 'stability.pdf', good.read_bytes(), None, {})
        same = st.blob_path(doc['sha256']).read_bytes() == good.read_bytes() or hashlib.sha256(st.blob_path(doc['sha256']).read_bytes()).hexdigest() == doc['sha256']
        _row(rows, 'OQ-02', 'A document is stored whole, under the SHA-256 of what is kept', 'file kept, fingerprint matches', f'{doc["filename"]} · {doc["sha256"][:16]}…', same)
        blank = tmp / 'blank.pdf'
        from pypdf import PdfWriter
        w = PdfWriter(); w.add_blank_page(595, 842); w.write(str(blank))
        try:
            st.add_document(did, 'P-15', 'scan.pdf', blank.read_bytes(), None, {})
            _row(rows, 'OQ-03', 'A PDF without text is refused at upload (negative control)', 'refused (E-NOTEXT)', 'accepted', False)
        except StoreError as e:
            _row(rows, 'OQ-03', 'A PDF without text is refused at upload (negative control)', 'refused (E-NOTEXT)', e.code, e.code == 'E-NOTEXT')
        js = tmp / 'js.pdf'
        from pypdf import PdfReader
        w = PdfWriter(clone_from=PdfReader(str(good))); w.add_js('app.alert(1);'); w.write(str(js))
        rules = {f.rule for f in pdf_check(str(js)).findings}
        _row(rows, 'OQ-04', 'The PDF checks find JavaScript in a document (negative control)', 'PDF-JS found', ', '.join(sorted(rules)) or 'none', 'PDF-JS' in rules)
        ok, _ = st.verify_audit()
        import sqlite3
        try:
            st.db.execute("update audit set detail='{}' where id=(select min(id) from audit)")
            refused = False
        except sqlite3.DatabaseError:
            refused = True
        st.db.rollback()
        _row(rows, 'OQ-05', 'The activity log refuses a change to an entry (append-only)', 'refused', 'refused' if refused else 'changed', refused)
        con = sqlite3.connect(str(st.root / 'workspace.sqlite'))          # someone working on the file itself, around the program
        con.execute('drop trigger audit_no_update')
        con.execute("update audit set detail='{}' where id=(select min(id) from audit)")
        con.commit()
        con.close()
        bad, first = st.verify_audit()
        _row(rows, 'OQ-06', 'The activity log is a chain: an entry changed outside the program is found (positive and negative control)',
             'intact, then the change found', f'intact: {ok} · after the change: {"found at entry " + str(first) if not bad else "not found"}', ok and not bad)
        f = str(good)
        env = ectd32.Envelope(identifier='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_type='maa', tracking=['OQ-0001'], unit='initial',
                              applicant='Example Pharm Co.', invented_name='OQ product', registration='local', marketing='local',
                              inn=['paracetamol'], description='OQ')
        docs = [ectd32.Doc('1.0', f, 'Cover letter'), ectd32.Doc('1.0', f, 'Tracking table', name='tracking'), ectd32.Doc('1.2.1', f, 'Application form'),
                ectd32.Doc('1.3.1', f, 'SmPC', pi_type='spc', lang='en'),
                ectd32.Doc('3.2.S.4.1', f, 'Specification', substance='paracetamol', manufacturer='Example API Co.'), ectd32.Doc('3.2.P.1', f, 'Description')]
        ectd32.write(tmp / 'seq', env, ectd32.Product('OQ product', 'tablet', 'Example Pharm Co.'), docs)
        seq = tmp / 'seq' / '0000'
        r = v32.validate(seq, ectd32.DEFAULT_PROFILE)
        _row(rows, 'OQ-07', 'An eCTD 3.2.2 sequence is written and passes its validation criteria (positive control)', 'no pass/fail rule fails',
             f'{r["counts"]["pass"]} passed, {r["counts"]["fail"]} failed', r['ok'])
        (seq / 'util' / 'dtd' / 'ich-ectd-3-2.dtd').unlink()
        r2 = v32.validate(seq, ectd32.DEFAULT_PROFILE)
        failed = sorted(x['rule'] for x in r2['results'] if x['status'] == 'fail')
        _row(rows, 'OQ-08', 'The validator fails a sequence whose ICH DTD is missing (negative control)', 'EG-PF-1.1 fails', ', '.join(failed[:4]) or 'nothing failed',
             'EG-PF-1.1' in failed)
        z = backup.make(tmp / 'ws', tmp / 'bk')
        d = backup.drill(z)
        _row(rows, 'OQ-09', 'A backup restores whole (the restore drill)', 'database sound, every file present with its fingerprint',
             f'{d["documents"]} documents · integrity {d["integrity"]} · missing {len(d["missing"])} · altered {len(d["altered"])}',
             d['integrity'] == 'ok' and not d['missing'] and not d['altered'])
        g = st.gate(did)
        _row(rows, 'OQ-10', 'The export gate holds a dossier with required documents missing (negative control)', 'blocked',
             f'{"open" if g["ok"] else "blocked"} · {len(g["missing_required"])} required missing', not g['ok'] and bool(g['missing_required']))
        from . import pdfcraft
        if pdfcraft.available():                         # the PDF engine: a faux redaction found, and the text read in its order
            box = tmp / 'faux.pdf'
            box.write_bytes(_raw_pdf(b'BT /F1 12 Tf 60 780 Td (OQ document of the Dossier Builder) Tj ET\n'
                                     b'BT /F1 12 Tf 60 700 Td (Confidential price: EGP 45.00 per pack) Tj ET\n0 g 55 695 260 18 re f\n'))
            rep = pdf_check(str(box), 'company_technical')
            faux = [f for f in rep.findings if f.rule == 'PDF-REDACT']
            _row(rows, 'OQ-11', 'PdfCraft finds a faux redaction (a black box over text that can still be read)', 'PDF-REDACT',
                 f"{len(faux)} found · engine {rep.info.get('engine')}", bool(faux) and rep.info.get('engine') == 'pdfcraft')
    except Exception as e:                                # noqa: BLE001 — a check that cannot run is a failed check, said
        _row(rows, 'OQ-ERR', 'The scripted checks ran to the end', 'no error', f'{type(e).__name__}: {e}', False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rows


PQ = [
    ('PQ-01', 'Create the dossier of one of the company\'s registered products (country, profile, product, actives).',
     'The items the program asks for match the company\'s own checklist for that product (differences explained).'),
    ('PQ-02', 'Upload the product\'s real documents (the base documents first, then the rest).',
     'Each document lands in its item; the ones it cannot place are in the unplaced box with the reason.'),
    ('PQ-03', 'Read the checks page and the conditions of each item.', 'Every finding is true of the document; no document is called wrong when it is right.'),
    ('PQ-04', 'Export the CTD folders and the eCTD (where the authority takes it).', 'The export passes its validation report; the folders open as the authority expects.'),
    ('PQ-05', 'Validate the eCTD with another validator (or the authority\'s portal) and compare the reports in the program.',
     'Every difference is explained; none is left open.'),
    ('PQ-06', 'Make a backup, run its restore drill, and restore it on a second machine.', 'The restored workspace shows the same dossiers and documents.'),
]


def evidence(st):
    """What the workspace already holds for the PQ: each export with its outputs and validation results."""
    out = []
    for r in st.db.execute("select dossier_id, ts, detail, actor from audit where event='export' order by id desc limit 50"):
        d = json.loads(r['detail'] or '{}')
        name = st.db.execute('select name from dossier where id=?', (r['dossier_id'],)).fetchone()
        out.append({'dossier': name['name'] if name else r['dossier_id'], 'when': time.strftime('%Y-%m-%d %H:%M', time.localtime(r['ts'])),
                    'by': r['actor'], 'outputs': d.get('outputs'), 'validation': d.get('validation')})
    return out


def package(st, out_dir):
    """Runs IQ and OQ, adds the PQ protocol and the evidence: → {'json', 'docx', 'summary'}."""
    from docx import Document
    from docx.shared import Pt
    t0 = time.strftime('%Y-%m-%d %H:%M:%S')
    res = {'made': t0, 'machine': platform.node(), 'system': f'{platform.system()} {platform.release()}', 'iq': iq(st.root), 'oq': oq(),
           'pq': [{'id': a, 'step': b, 'acceptance': c} for a, b, c in PQ], 'evidence': evidence(st)}
    res['summary'] = {k: {'pass': sum(1 for r in res[k] if r['result'] == 'pass'), 'fail': sum(1 for r in res[k] if r['result'] == 'fail')}
                      for k in ('iq', 'oq')}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = time.strftime('qualification-%Y%m%d-%H%M%S')
    (out / f'{stem}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    doc = Document()
    doc.styles['Normal'].font.size = Pt(9.5)
    doc.add_heading('Dossier Builder — qualification package (IQ / OQ / PQ)', 0)
    doc.add_paragraph(f'Made {t0} on {res["machine"]} ({res["system"]}). IQ: {res["summary"]["iq"]["pass"]} passed, {res["summary"]["iq"]["fail"]} failed. '
                      f'OQ: {res["summary"]["oq"]["pass"]} passed, {res["summary"]["oq"]["fail"]} failed. The OQ ran in a workspace of its own, '
                      'never the company\'s. This package is evidence for the company\'s own validation decision; it does not replace it.')
    for key, title in (('iq', 'Installation qualification (IQ)'), ('oq', 'Operational qualification (OQ)')):
        doc.add_heading(title, 1)
        tb = doc.add_table(rows=1, cols=5)
        tb.style = 'Table Grid'
        for c, h in zip(tb.rows[0].cells, ('ID', 'Requirement', 'Expected', 'Actual', 'Result')):
            c.text = h
        for r in res[key]:
            cells = tb.add_row().cells
            for c, v in zip(cells, (r['id'], r['requirement'], r['expected'], r['actual'], r['result'].upper())):
                c.text = str(v)
    doc.add_heading('Performance qualification (PQ) — protocol', 1)
    tb = doc.add_table(rows=1, cols=4)
    tb.style = 'Table Grid'
    for c, h in zip(tb.rows[0].cells, ('ID', 'Step on the company\'s own product', 'Acceptance criterion', 'Result / initials / date')):
        c.text = h
    for r in res['pq']:
        cells = tb.add_row().cells
        cells[0].text, cells[1].text, cells[2].text, cells[3].text = r['id'], r['step'], r['acceptance'], ''
    doc.add_heading('Evidence already in this workspace (exports and their validation)', 2)
    if res['evidence']:
        for e in res['evidence'][:30]:
            doc.add_paragraph(f'{e["when"]} · {e["dossier"]} · {", ".join(e["outputs"] or [])} · {json.dumps(e["validation"] or {}, ensure_ascii=False)} · {e["by"]}',
                              style='List Bullet')
    else:
        doc.add_paragraph('No export yet in this workspace.')
    doc.add_heading('Sign-off', 1)
    for role in ('Prepared by (system owner)', 'Reviewed by (quality assurance)', 'Approved by (head of quality)'):
        doc.add_paragraph(f'{role}: ______________________   Signature: ______________   Date: ____________')
    doc.save(str(out / f'{stem}.docx'))
    return {'json': f'{stem}.json', 'docx': f'{stem}.docx', 'summary': res['summary'], 'iq': res['iq'], 'oq': res['oq']}
