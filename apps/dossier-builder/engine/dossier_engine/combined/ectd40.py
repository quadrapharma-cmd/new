"""Stage 9b — the same sequence as eCTD 4.0 (Egypt's provisional v4 profile), and its validation.

Made from the eCTD 3.2.2 sequence the stage before wrote, so the two carry the same documents, byte for byte: every leaf of
index.xml (Modules 2–5) and of eg-regional.xml (Module 1) becomes a document of the full program's own 4.0 writer
(`writers/ectd40.py`), its heading read back to its CTD number, its attributes (substance, manufacturer, excipient, indication,
the product information's type and language) carried over. The envelope is the 3.2.2 one: the same application (its UUID), the
first 4.0 sequence (1), a new submission. Then the full program's 4.0 validator (`validators/ectd40.py`: the ICH IG v1.7 rules and
the XSD, and the EG provisional rules). ectd40.json is written."""
import re
import uuid
from pathlib import Path

from ..writers import ectd32
from ..writers import ectd40 as w40
from ..validators import ectd40 as v40
from .common import Work, say

IG_ZIP = Path(__file__).resolve().parents[5] / 'docs' / 'ctd' / 'sources' / 'ectd' / 'ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'
CODES = {'2.3.intro': '2.3.I'}                 # the 3.2.2 stage's own code → the heading's number (eCTD 4.0 ich_2.3.i)
ATTRS = {'substance': 'substance', 'manufacturer': 'manufacturer', 'excipient': 'excipient', 'indication': 'indication'}


def docs_of(rec, seq_dir, profile32):
    """The 3.2.2 sequence's leaves as the 4.0 writer's documents, Module 1 first (its order in the sequence)."""
    node_of = {row['element']: num for num, row in profile32.m1.items()}
    docs = []
    for (el, pidoc, href, title, _md5, lid, _src, _keep) in rec['m1']:
        node = node_of.get(el)
        if not node:
            raise ValueError(f'Module 1 element {el} has no EG number')
        d = ectd32.Doc(node=node, file=str(Path(seq_dir) / 'm1' / 'eg' / href), title=title, leaf_id=lid,
                       name=Path(href).stem)
        if pidoc:
            d.pi_type, d.lang = pidoc['type'], pidoc['xml:lang']
        docs.append(d)
    for l in rec['leaves']:
        d = ectd32.Doc(node=CODES.get(l['code'], l['code']), file=str(Path(seq_dir) / l['href']), title=l['title'], leaf_id=l.get('id'))
        for attrs in (l.get('attrs') or {}).values():
            for k, field in ATTRS.items():
                if attrs.get(k) and not getattr(d, field):
                    setattr(d, field, attrs[k])
        docs.append(d)
    return docs


KW_AR = {'species': 'نوع الحيوان', 'route of admin': 'طريق الإعطاء', 'study id_study title': 'معرّف الدراسة أو عنوانها',
         'document type': 'نوع المستند', 'substance': 'المادة الفعالة', 'manufacturer': 'الشركة المصنّعة'}
DOC_TYPE = {'4': 'ich_document_type_1', '5': 'ich_document_type_2'}    # preclinical study report; legacy clinical study report


def study_keywords(d, spec):
    """A study report of Modules 4–5 is one document of one study in the desk's sequence (ectd.py: one folder a study, named by the
    document's title): 4.0's study keyword is that title, and its document type the whole report's (ICH document types 1 and 2)."""
    names = {n for n, *_ in spec}
    if 'study id_study title' in names and not d.study:
        d.study = re.sub(r'^\d(?:\.\d+)*\s+', '', d.title or '').strip()[:200] or d.leaf_id
    if 'document type' in names and not d.doc_type and d.node[0] in DOC_TYPE:
        d.doc_type = DOC_TYPE[d.node[0]]


def run(work, rec=None):
    w = work if isinstance(work, Work) else Work(work)
    rec = rec or w.load('ectd.json')
    seq_dir = Path(rec['sequence'])
    env = rec['envelope']
    E = (w.load('dossier.json', {}) or {}).get('ectd') or {}
    prod = E.get('product') or {}
    product = ectd32.Product(name=prod.get('product-name') or env.get('invented_name', ''), dosageform=prod.get('dosageform', ''),
                             manufacturer=prod.get('manufacturer') or E.get('manufacturer', ''), indication=E.get('indication'))
    p40 = w40.Profile40()
    seq = int(env.get('sequence') or 0) + 1                      # 3.2.2 counts from 0000, 4.0 from 1 (EG-V4-002)
    e4 = w40.Envelope4(application_uuid=env['identifier'], submission_uuid=str(uuid.uuid5(uuid.UUID(env['identifier']), f'submission-{seq}')),
                       tracking=env.get('tracking', ''), submission_type=env['submission_type'], unit=env['unit'], sequence=seq,
                       title=env.get('description', ''), applicant=env['applicant'],
                       applicant_portal_id=env.get('portal_id') or 'UNKNOWN', product_name=env['invented_name'],
                       inn=list(env.get('inn') or []), registration=env['registration'], marketing=env['marketing'])
    out_root = w.root / 'ectd40'
    if out_root.exists():
        import shutil
        shutil.rmtree(out_root)
    say(f'كتابة تسلسل eCTD 4.0 رقم {seq} من التسلسل {env.get("sequence")}')
    docs, left_out = [], []
    for d in docs_of(rec, seq_dir, p40.v32):
        try:
            spec = p40.cou(d.node)[2]
        except w40.WriterError:                    # a heading 3.2.2 takes a document at and 4.0 does not (2.6, 5.3.5): named, not dropped
            left_out.append({'node': d.node, 'title': d.title, 'file': Path(d.file).name,
                             'why': {'en': f'eCTD 4.0 has no context of use at {d.node}: its documents go in its sub-sections',
                                     'ar': f'لا يقبل eCTD 4.0 مستندًا في {d.node} نفسه، بل في أقسامه الفرعية'}})
            continue
        study_keywords(d, spec)
        missing = [name for name, card, _cs, _a in spec if card == 'R' and w40._kw_value(name, d, product) is None]
        if missing:                                # what 3.2.2 does not carry and the documents do not say (species, route): never guessed
            left_out.append({'node': d.node, 'title': d.title, 'file': Path(d.file).name,
                             'why': {'en': 'eCTD 4.0 requires keywords this dossier does not give: ' + ', '.join(missing),
                                     'ar': 'يطلب eCTD 4.0 كلمات مفتاحية لا يذكرها الملف: ' + '، '.join(KW_AR.get(m, m) for m in missing)}})
            continue
        docs.append(d)
    if left_out:
        say(f'مستندات لا يقبلها eCTD 4.0 في موضعها (تبقى في 3.2.2 وctd.zip): {len(left_out)} — '
            + '، '.join(sorted({x["node"] for x in left_out})))
    r = w40.write(out_root, e4, product, docs, profile=p40)
    say('التحقق من تسلسل eCTD 4.0')
    report = v40.validate(r['path'], p40, IG_ZIP, w.root / 'cache')
    rows = report['results']
    fails = [x for x in rows if x.get('status') == 'fail']
    warns = [x for x in rows if x.get('status') == 'warning']
    out = {'sequence': str(r['path']), 'number': seq, 'documents': len(docs), 'left_out': left_out,
           'files': sum(1 for p in Path(r['path']).rglob('*') if p.is_file()),
           'validation': {'pass': report['counts']['pass'], 'fail': len(fails), 'warning': len(warns),
                          'not_run': report['counts']['not_run']},
           'label': report['label'], 'results': rows}
    w.save('ectd40.json', out)
    v = out['validation']
    say(f"eCTD 4.0: {len(docs)} مستندًا · {out['files']} ملفًا · القواعد: {v['pass']} ناجحة و{v['fail']} راسبة و{v['warning']} تنبيهًا")
    return out
