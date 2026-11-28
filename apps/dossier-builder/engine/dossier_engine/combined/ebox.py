"""Stage 11 — the dossier handed to eBOX's full program, for any country it serves.

The desk's program makes a combined file ready for Egypt. eBOX's full program (`app/`: the store, the export, the review desk,
the missing items by party) knows every authority it has a pack for: Egypt, the EU, the Gulf, the US, and other countries. This
stage makes one of its dossiers from this work folder — the authority's pack chosen by the country (`dossier.json → ectd.country`,
Egypt when none is said), the product's case as `ctdzip.profile_of` reads it, every document of the CTD folder (the corrected
copy where a correction was made, and the product information this program wrote) placed in the item of that authority whose
headings hold it — and then asks the full program for that authority's outputs as a working copy: the CTD folders and, where the
authority takes one, its eCTD sequence with its validation, all marked «not for submission», never recorded (exporter
`_working_copy`). A document that no item of that authority takes, or one its matrix does not ask for in this case, is named in
ebox.json, never dropped silently. ebox.json is written; the full program's own folder is `ebox/`."""
import dataclasses
import re
import shutil
from pathlib import Path

from .. import packs
from ..app.store import Store, StoreError
from ..app import exporter
from ..writers.ectd40 import Profile40
from .common import Work, say
from .ctdzip import profile_of
from .ectd40 import IG_ZIP


def documents(w, built=True):
    """(node, file, title, substance, meta) for every document of the CTD folder, the corrected copy where there is one, the
    product information the corrections stage wrote, and (built) what the build stage wrote for a missing item (built.json),
    each with the item it was written for."""
    plan = w.load('plan.json')
    folder = Path(w.load('assembled.json')['folder'])
    fixed = w.load('fixed.json', {}) or {}
    out = []
    for d in plan['docs']:
        f = (fixed.get('docs') or {}).get(d['path'])
        src = Path(f['pdf']) if f else folder / d['path']
        m = re.search(r'/3\.2\.S ([^/]+)/', d['path'])
        out.append({'node': d['ctd'], 'file': src, 'title': re.sub(rf"^{re.escape(d['ctd'])}\s+", '', d['title']),
                    'substance': m.group(1) if m else None, 'meta': {}, 'path': d['path']})
    for p in fixed.get('pi') or []:
        out.append({'node': '1.3.1', 'file': Path(p['pdf']), 'title': p.get('title') or 'Product information', 'substance': None,
                    'meta': {'pi_type': p.get('type'), 'lang': p.get('lang')}, 'path': p['pdf']})
    for b in (w.load('built.json', []) or []) if built else []:
        out.append({'node': b['node'], 'file': Path(b['pdf']), 'title': b['title'], 'substance': b.get('substance'),
                    'meta': {'built': b.get('how'), 'draft_unsigned': bool(b.get('sign'))}, 'path': b['pdf'], 'req': b['req']})
    return out


def slot_of_req(slots, doc):
    """The item a built document was written for: its requirement, and its substance where the item is one a substance."""
    mine = [s for s in slots if s.req_id == doc['req']]
    per = [s for s in mine if s.item and s.item.get('name') == doc.get('substance')]
    return (per or [s for s in mine if not s.item] or mine or [None])[0]


def slot_for(slots, doc):
    node = doc['node']
    while True:
        cands = [s for s in slots if node in s.ectd or s.ctd.split(' (')[0] == node]
        if cands or node.count('.') <= 1:
            break
        node = node.rsplit('.', 1)[0]
    if any(s.item for s in cands):
        per = [s for s in cands if s.item and s.item['name'] == doc['substance']]
        cands = per or [s for s in cands if not s.item]
    return cands[0] if cands else None


def make(w, country=None, root=None, built=True):
    """eBOX's dossier made from this work folder in its own store (root: <work>/ebox), every document placed in its item:
    {st, did, pk, meta, country, root, placed, unplaced, not_asked}. built=False: without what the build stage wrote (the build
    stage asks this dossier what is missing)."""
    dec = w.load('dossier.json', {}) or {}
    E = dec.get('ectd') or {}
    env = E.get('envelope') or {}
    country = (country or E.get('country') or (w.load('country.json', {}) or {}).get('code') or 'EG').upper()      # the desk's choice: country.json
    meta = packs.for_country(country)
    if not meta:
        raise SystemExit(f'لا توجد جهة رقابية للدولة {country} في البرنامج.')
    root = Path(root or w.root / 'ebox')
    if root.exists():
        shutil.rmtree(root)
    st = Store(root)
    prof = profile_of(env, E)
    pdict = dataclasses.asdict(prof)
    pk = st.pack(meta['id'])
    if not pk.egypt:                                      # Egypt's licence kinds are Egypt's own: elsewhere the product is the company's
        pdict.update(licence='own')
    prod = E.get('product') or {}
    product = {'name': prod.get('product-name') or env.get('invented_name', ''), 'dosageform': prod.get('dosageform', ''),
               'manufacturer': prod.get('manufacturer') or E.get('manufacturer', ''), 'indication': E.get('indication')}
    envelope = {'application_uuid': env.get('identifier'), 'applicant': env.get('applicant'), 'invented_name': env.get('invented_name'),
                'inn': env.get('inn') or [], 'marketing': env.get('marketing', 'local'), 'tracking': env.get('tracking', ''),
                'country': country, 'submission_type': env.get('submission_type', 'maa'), 'description': env.get('description', '')}
    name = (dec.get('names') or {}).get('product') or env.get('invented_name') or 'Dossier'
    say(f'إنشاء الملف في برنامج eBOX الكامل: {name} — {pk.authority["name"]["ar"] if isinstance(pk.authority.get("name"), dict) else meta["id"]}')
    try:
        did = st.create_dossier(name, pdict, product, envelope, pack=meta['id'])
    except (StoreError, ValueError) as ex:                # the case as read does not fit this authority's own rules: say it, take its defaults
        say(f'بيانات الحالة لا تناسب قواعد هذه الجهة ({ex}); أُخذت القيم الافتراضية.')
        pdict = dataclasses.asdict(type(prof)(apis=prof.apis))
        did = st.create_dossier(name, pdict, product, envelope, pack=meta['id'])
    slots = st.slots(did)
    placed, unplaced, not_asked = [], [], []
    for doc in documents(w, built=built):
        s = slot_of_req(slots, doc) if doc.get('req') else slot_for(slots, doc)
        if not s:
            unplaced.append({'node': doc['node'], 'title': doc['title'], 'from': doc['path']})
            continue
        if not s.active:
            not_asked.append({'node': doc['node'], 'title': doc['title'], 'item': s.ctd, 'level': s.level})
            continue
        try:
            st.add_document(did, s.slot_id, Path(doc['file']).name, Path(doc['file']).read_bytes(), title=doc['title'],
                            meta=doc['meta'])
            placed.append({'node': doc['node'], 'item': s.slot_id})
        except StoreError as ex:
            unplaced.append({'node': doc['node'], 'title': doc['title'], 'from': doc['path'], 'refused': ex.args[0] if ex.args else str(ex)})
    say(f'المستندات في بنود الجهة: {len(placed)} · بلا بند: {len(unplaced)} · لا يطلبها جدول الجهة لهذه الحالة: {len(not_asked)}')
    return {'st': st, 'did': did, 'pk': pk, 'meta': meta, 'country': country, 'root': root, 'placed': placed, 'unplaced': unplaced,
            'not_asked': not_asked}


def run(work, country=None):
    w = work if isinstance(work, Work) else Work(work)
    m = make(w, country)
    st, did, pk, meta, country, root = m['st'], m['did'], m['pk'], m['meta'], m['country'], m['root']
    placed, unplaced, not_asked = m['placed'], m['unplaced'], m['not_asked']
    say('نسخة العمل بمخرجات الجهة كلها، مع التحقق')
    res = exporter.export(st, did, list(pk.outputs_for(country)), True, {}, Profile40(), IG_ZIP, working=True)
    base = Path(st.root) / 'exports' / did / res['id']
    files = {k: str(base / Path(v).name) for k, v in res['downloads'].items()}
    out = {'country': country, 'pack': meta['id'], 'dossier': did, 'store': str(root), 'placed': len(placed), 'unplaced': unplaced,
           'not_asked': not_asked, 'missing_required': res['missing_required'], 'files': files,
           'validation': res.get('validation') or {}, 'report': str(base / 'validation-report.html') if res.get('report') else None,
           'skipped': (res.get('ectd') or {}).get('skipped') or {}}
    w.save('ebox.json', out)
    vs = ' · '.join(f"{k}: {'مطابق' if v['ok'] else 'غير مطابق'} ({v['counts'].get('fail', 0)} راسبة)" for k, v in out['validation'].items())
    say(f"مخرجات {country}: {', '.join(files)}" + (f' · {vs}' if vs else '') + f" · بنود مطلوبة ناقصة: {out['missing_required']}")
    return out
