"""Stage 9b — the same sequence as eCTD 4.0 (Egypt's provisional v4 profile), and its validation.

Made from the eCTD 3.2.2 sequence the stage before wrote, so the two carry the same documents, byte for byte: every leaf of
index.xml (Modules 2–5) and of eg-regional.xml (Module 1) becomes a document of the full program's own 4.0 writer
(`writers/ectd40.py`), its heading read back to its CTD number, its attributes (substance, manufacturer, excipient, indication,
the product information's type and language) carried over. The envelope is the 3.2.2 one: the same application (its UUID), the
first 4.0 sequence (1), a new submission. Then the full program's 4.0 validator (`validators/ectd40.py`: the ICH IG v1.7 rules and
the XSD, and the EG provisional rules). ectd40.json is written."""
import uuid
from pathlib import Path

from ..writers import ectd32
from ..writers import ectd40 as w40
from ..validators import ectd40 as v40
from .common import Work, say

IG_ZIP = Path(__file__).resolve().parents[5] / 'docs' / 'ctd' / 'sources' / 'ectd' / 'ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'
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
        d = ectd32.Doc(node=l['code'], file=str(Path(seq_dir) / l['href']), title=l['title'], leaf_id=l.get('id'))
        for attrs in (l.get('attrs') or {}).values():
            for k, field in ATTRS.items():
                if attrs.get(k) and not getattr(d, field):
                    setattr(d, field, attrs[k])
        docs.append(d)
    return docs


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
    docs = docs_of(rec, seq_dir, p40.v32)
    r = w40.write(out_root, e4, product, docs, profile=p40)
    say('التحقق من تسلسل eCTD 4.0')
    report = v40.validate(r['path'], p40, IG_ZIP, w.root / 'cache')
    rows = report['results']
    fails = [x for x in rows if x.get('status') == 'fail']
    warns = [x for x in rows if x.get('status') == 'warning']
    out = {'sequence': str(r['path']), 'number': seq, 'documents': len(docs),
           'files': sum(1 for p in Path(r['path']).rglob('*') if p.is_file()),
           'validation': {'pass': report['counts']['pass'], 'fail': len(fails), 'warning': len(warns),
                          'not_run': report['counts']['not_run']},
           'label': report['label'], 'results': rows}
    w.save('ectd40.json', out)
    v = out['validation']
    say(f"eCTD 4.0: {len(docs)} مستندًا · {out['files']} ملفًا · القواعد: {v['pass']} ناجحة و{v['fail']} راسبة و{v['warning']} تنبيهًا")
    return out
