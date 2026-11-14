"""Every piece of information the program reads from a document is kept in its place in the dossier's data (the owner, 13/11/2026:
«any information it reads, it stores and puts in its place»). A document's reading — its own words through the rules (meta
«extracted».fields) and what Claude read on its pages (meta «model».fields) — goes into the same shape the wizard writes:
apis, composition, batches, specs.product, results, registration, product. A value goes where the place is empty; a different value
where one is already written is not written over — it is kept as a difference for the person to choose (data «conflicts»), with the
document it came from. Where each value came from is kept too (data «sources»), so the person can always see «read from …»."""
import re

SCALARS = {'registration': ('reg_no', 'reg_date', 'valid_until', 'shelf_life', 'storage', 'price', 'licence_type', 'marketing'),
           'product': ('name', 'name_ar', 'dosage_form', 'strength', 'manufacturer', 'manufacturer_address', 'indication',
                       'shelf_life', 'storage')}
NAMES = {'registration.reg_no': ('registration no.', 'رقم التسجيل'), 'registration.reg_date': ('registration date', 'تاريخ التسجيل'),
         'registration.valid_until': ('licence valid until', 'الترخيص ساري لحد'), 'registration.shelf_life': ('shelf life', 'الصلاحية'),
         'registration.storage': ('storage', 'التخزين'), 'registration.price': ('price', 'السعر'), 'registration.licence_type': ('licence type', 'نوع الترخيص'),
         'registration.marketing': ('marketing', 'التسويق'), 'product.name': ('trade name', 'الاسم التجاري'), 'product.name_ar': ('Arabic name', 'الاسم بالعربي'),
         'product.dosage_form': ('dosage form', 'الشكل الصيدلي'), 'product.strength': ('strength', 'التركيز'), 'product.manufacturer': ('manufacturer', 'المصنّع'),
         'product.manufacturer_address': ('manufacturer address', 'عنوان المصنّع'), 'product.indication': ('indication', 'دواعي الاستعمال'),
         'product.shelf_life': ('shelf life', 'الصلاحية'), 'product.storage': ('storage', 'التخزين'),
         'apis': ('active substance', 'مادة فعالة'), 'batches': ('batch', 'تشغيلة'), 'specs': ('specification test', 'اختبار مواصفة'),
         'results': ('result', 'نتيجة'), 'composition': ('composition row', 'مكوّن في التركيب'), 'packs': ('pack', 'عبوة')}


CURRENCY = re.compile(r'(?<![a-z])(?:l\.?\s?e\.?|egp|e\.g\.p\.?|pounds?|جنيه(?:ا|اً)?|ج\.?\s?م\.?)(?![a-z])', re.I)
IDENTITY = ('licence', 'annex1', 'variation', 'cpp', 'smpc', 'composition', 'pricing', 'cadc', 'contract')   # extract.IDENTITY: the documents that say what the product is


def _norm(v):
    return re.sub(r'[\s\-_.,:;()/]+', '', CURRENCY.sub('egp', str(v or ''))).lower()   # 18 L.E. = 18 EGP = ١٨ جنيه


def _clean(v):
    """A value as a scan's reading gives it, without the stray quotes and marks at its ends («‘Powder for oral solution»); a final dot
    stays («Example Pharm Co.»)."""
    if not isinstance(v, str):
        return v
    v = v.strip(' \t\u2018\u2019\u201c\u201d"\'`\u00b4')
    return v.lstrip(':;,-\u2013').rstrip(':;,').strip()


def _words(v):
    return [w for w in re.sub(r'[^a-z0-9\u0600-\u06ff]+', ' ', CURRENCY.sub('egp', str(v or '')).lower().replace('&', ' and ')).split()
            if len(w) >= 3 and not w.isdigit()]


def _same(a, b):
    """One value in two spellings: equal once marks and currencies are set aside, or every word of the shorter in the longer
    («Nerhadou … Pharmaceuticals and Nutraceuticals» / «5294 (Nerhadou … Pharmaceuticals & Nutraceuticals …»)."""
    na, nb = _norm(a), _norm(b)
    if not (na and nb):
        return False
    if na == nb or na in nb or nb in na:
        return True
    wa, wb = _words(a), _words(b)
    small, big = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    return len(small) >= 2 and all(w in big for w in small)


def _fields(meta):
    """The document's reading in the fill shape: Claude's over the rules', key by key (what it saw on the pages is the fuller reading)."""
    rules = ((meta or {}).get('extracted') or {}).get('fields') or {}
    model = ((meta or {}).get('model') or {}).get('fields') or {}
    out = {}
    for k in set(rules) | set(model):
        a, b = rules.get(k), model.get(k)
        if isinstance(a, dict) or isinstance(b, dict):
            out[k] = {**(a if isinstance(a, dict) else {}), **{x: y for x, y in (b if isinstance(b, dict) else {}).items() if y not in (None, '', [])}}
        else:
            out[k] = b if b not in (None, '', []) else a
    return out


def absorb(data, doc, label=None):
    """Put what `doc` says into `data` (changed in place). → {added: [{field, value, en, ar}], conflicts: [{field, have, read}]}."""
    f = _fields(doc.get('meta'))
    meta = doc.get('meta') or {}
    kind = meta.get('kind') or ((meta.get('model') or {}).get('doc') or {}).get('kind') or (meta.get('extracted') or {}).get('kind')
    if not kind and (meta.get('extracted') or {}).get('text'):
        from . import extract as _extract
        kind = _extract.content_kind(meta['extracted']['text'])          # what its own words say it is
    says_what_it_is = kind in IDENTITY                 # a method, a validation or a CoA names the product at its top: it fills, it does not contradict
    src = {'doc_id': doc.get('id'), 'filename': label or doc.get('filename')}
    sources = data.setdefault('sources', {})
    conflicts = data.setdefault('conflicts', [])
    added, clashes = [], []

    def put(path, value):
        value = _clean(value)
        if value in (None, '', [], {}):
            return
        sec, key = path.split('.', 1)
        box = data.setdefault(sec, {})
        have = box.get(key)
        if have in (None, '', [], {}):
            box[key] = value
            sources[path] = src
            added.append({'field': path, 'value': value})
        elif not _same(have, value) and (sec != 'product' or says_what_it_is):
            c = {'field': path, 'have': have, 'read': value, **src}
            if not any(x.get('field') == path and _norm(x.get('read')) == _norm(value) for x in conflicts):
                conflicts.append(c)
                clashes.append(c)

    for sec, keys in SCALARS.items():
        for k in keys:
            put(f'{sec}.{k}', (f.get(sec) or {}).get(k))
    reg = f.get('registration') or {}
    for p in reg.get('prices') or []:                 # «Price» lines: one price per pack
        if isinstance(p, dict) and p.get('price'):
            prices = data.setdefault('registration', {}).setdefault('prices', [])
            if not any(_same(x.get('pack'), p.get('pack')) and _same(x.get('price'), p.get('price')) for x in prices if isinstance(x, dict)):
                prices.append({'price': p.get('price'), 'pack': p.get('pack') or ''})
                added.append({'field': 'registration.prices', 'value': p.get('price')})
    for pk in reg.get('packs') or []:
        packs = data.setdefault('registration', {}).setdefault('packs', [])
        if pk and not any(_same(x, pk) for x in packs):
            packs.append(pk)
            added.append({'field': 'packs', 'value': pk})

    from . import extract as _x

    def one(name, a, b):
        if name == 'apis':                             # one substance in other words: salt, hydrate, spelling
            return _x._same_substance(_x.api_key(a), _x.api_key(b))
        return _same(a, b)

    def rows(name, items, key, shape):
        cur = data.setdefault(name, [])
        had = any(isinstance(x, dict) and x.get(key) for x in cur)
        for it in items or []:
            if not isinstance(it, dict) or not it.get(key):
                continue
            if name == 'batches' and not re.search(r'\d', str(it.get(key))):
                continue                               # a batch number has digits: «SYYOFYNOA» is a misreading
            if name == 'apis' and not _x.plausible_api(str(it.get(key)), bool(it.get('strength'))):
                continue                               # a table's heading, a sentence, a company
            row = next((x for x in cur if isinstance(x, dict) and one(name, x.get(key), it.get(key))), None)
            if row is None and name == 'apis' and had and not says_what_it_is:
                continue                               # a method or a CoA names the substances; the licence and the composition say which they are
            if row is None:
                cur.append(shape(it))
                sources[f'{name}:{it[key]}'] = src
                added.append({'field': name, 'value': it[key]})
            else:                                      # a row already there: its empty cells filled from what the document says (never a default), nothing written over
                defaults = {k2 for k2, v in shape({key: it[key]}).items() if v not in (None, '')} - {key}
                for k2, v in shape(it).items():
                    if k2 in defaults and it.get(k2) in (None, ''):
                        continue
                    if v not in (None, '') and row.get(k2) in (None, ''):
                        row[k2] = v

    rows('apis', f.get('apis'), 'name', lambda a: {'name': a['name'], 'manufacturer': a.get('manufacturer') or '', 'country': a.get('country') or '',
                                                    'strength': a.get('strength') or '', 'option': a.get('option') or 'FULL',
                                                    **({'cep_no': a['cep_no']} if a.get('cep_no') else {}),
                                                    **({'address_gmp': a['address_gmp']} if a.get('address_gmp') else {})})
    rows('composition', f.get('composition'), 'name', lambda c: {'name': c['name'], 'amount': c.get('amount') or '', 'standard': c.get('standard') or '',
                                                                   'function': 'active' if c.get('role') == 'active' else (c.get('role') or ''),
                                                                   'equivalent': c.get('equivalent') or ''})
    rows('batches', f.get('batches'), 'no', lambda b: {'no': b['no'], 'kind': b.get('kind') or 'fpp', 'api': b.get('api') or '', 'size': b.get('size') or '',
                                                         'date': b.get('date') or '', 'site': b.get('site') or '', 'expiry': b.get('expiry') or '',
                                                         'conformity': b.get('conformity') or ''})
    specs = data.setdefault('specs', {})
    prod = specs.setdefault('product', []) if isinstance(specs, dict) else []
    for s in f.get('specs') or []:
        if isinstance(s, dict) and s.get('test') and not any(_same(x.get('test'), s['test']) for x in prod if isinstance(x, dict)):
            prod.append({'test': s['test'], 'limit': s.get('limit') or '', 'method': s.get('method') or ''})
            added.append({'field': 'specs', 'value': s['test']})
    results = data.setdefault('results', {})
    for r in f.get('results') or []:
        if isinstance(r, dict) and r.get('batch') and r.get('test') and r.get('value') not in (None, ''):
            box = results.setdefault(str(r['batch']), {})
            if str(r['test']) not in box:
                box[str(r['test'])] = str(r['value'])
                added.append({'field': 'results', 'value': f"{r['batch']} · {r['test']}"})
    for a in added:
        en, ar = NAMES.get(a['field'], (a['field'], a['field']))
        a.update(en=en, ar=ar)
    return {'added': added, 'conflicts': clashes}
