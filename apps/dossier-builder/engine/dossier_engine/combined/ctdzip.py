"""Stage 9c — the CTD One Submission package (ctd.zip): what EDA receives today (NP.CAPP.065 v5), as the full program's export
writes it (`writers/ctd.py`: «Module N/NN section title/…», 00-navigator.html, 00-checklist.csv).

The documents are the eCTD sequence's own (the same files, byte for byte, as the 3.2.2 and 4.0 sequences). Each is given the
item of EDA's matrix whose eCTD headings hold it (`resolver.resolve` on the EDA pack, with the product's case read from the
dossier: the registration type gives local or imported, each drug substance and its manufacturer gives the per-substance
items of 3.2.S). A document whose heading the matrix marks «not required» or «not applicable» for this case is still put in
(the company gave it): the item is opened as optional, and the checklist says why. A document no item takes is named in
ctdzip.json and the report, never dropped silently. ctdzip.json is written."""
import re
import shutil
import zipfile
from pathlib import Path

from .. import packs
from ..profile import Api, Profile
from ..resolver import resolve
from ..writers import ctd as wctd
from ..writers import ectd32
from ..writers.ectd40 import Profile40
from .common import Work, say
from .ectd40 import docs_of

PACK = 'eda.ctd.nta065.v5'
LICENCE = {v: k for k, v in ectd32.REG_TYPE.items()}


def profile_of(env, E):
    over = dict(E.get('ctd_profile') or {})                     # the dossier may say the case itself (dossier.json → ectd.ctd_profile)
    licence = over.pop('licence', None) or LICENCE.get(env.get('registration'), 'own')
    manuf = E.get('manufacturer', '')
    apis = [Api(name=name, manufacturer=(s or {}).get('manufacturer') or manuf) for name, s in (E.get('substances') or {}).items()]
    return Profile(licence=licence, origin='imported' if licence.startswith('imported') else 'local', apis=apis,
                   **{k: v for k, v in over.items() if k in Profile.__dataclass_fields__ and k != 'apis'})


def place(slots, docs, E):
    """{slot_id: [files]} and the documents no item takes."""
    subst = {(s or {}).get('substance', name).lower(): name for name, s in (E.get('substances') or {}).items()}
    files, unplaced = {}, []
    for d in docs:
        node = d.node
        cands = [s for s in slots if node in s.ectd]
        while not cands and node.count('.') > 1:                # 3.2.S.7.1 → 3.2.S.7: EDA's item holds the whole section
            node = node.rsplit('.', 1)[0]
            cands = [s for s in slots if node in s.ectd]
        if any(s.item for s in cands):
            name = subst.get((d.substance or '').lower())
            per = [s for s in cands if s.item and s.item['name'] == name]
            cands = per or [s for s in cands if not s.item]
        if not cands:
            unplaced.append({'node': d.node, 'title': d.title, 'file': Path(d.file).name})
            continue
        s = cands[0]
        if not s.active:
            s.reasons.append({'en': f'Provided by the company, though the matrix marks it {s.level} for this case.',
                              'ar': 'قدّمته الشركة مع أن الجدول لا يطلبه لهذه الحالة.', 'source': PACK})
            s.level = 'O'
        title = re.sub(rf'^{re.escape(d.node)}\s+', '', d.title)          # the writer puts the item's number in front itself
        f = {'file': d.file, 'title': title}
        if d.node == '1.3.1' and d.pi_type:
            f['title'] = f'{title} ({d.pi_type}, {d.lang})'
        files.setdefault(s.slot_id, []).append(f)
    return files, unplaced


def run(work, rec=None):
    w = work if isinstance(work, Work) else Work(work)
    rec = rec or w.load('ectd.json')
    env = rec['envelope']
    E = (w.load('dossier.json', {}) or {}).get('ectd') or {}
    pk = packs.load(PACK)
    slots = resolve(profile_of(env, E), pk, validate=False)
    docs = docs_of(rec, rec['sequence'], Profile40().v32)
    files, unplaced = place(slots, docs, E)
    out_dir = w.root / 'ctdzip'
    if out_dir.exists():
        shutil.rmtree(out_dir)
    say('كتابة ملف CTD One Submission (ctd.zip) كما تستلمه الهيئة اليوم')
    r = wctd.write(out_dir, env.get('invented_name') or 'Dossier', slots, files)
    root = Path(r['path'])
    zpath = w.root / 'ctdzip' / 'ctd.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(root.parent).as_posix())
    req = [s for s in slots if s.level == 'R']
    out = {'folder': str(root), 'zip': str(zpath), 'documents': len(docs) - len(unplaced), 'unplaced': unplaced,
           'required': len(req), 'required_missing': [{'id': s.slot_id, 'ctd': s.ctd, 'en': s.title['en'], 'ar': s.title['ar']}
                                                      for s in req if s.slot_id in r['missing']],
           'files': len(r['files'])}
    w.save('ctdzip.json', out)
    say(f"ctd.zip: {out['documents']} مستندًا في بنودها · بنود مطلوبة ناقصة: {len(out['required_missing'])} · "
        f"مستندات بلا بند: {len(unplaced)}")
    return out
