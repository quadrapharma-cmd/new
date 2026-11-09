"""Product file (RIM) — module 1 of the suite.

Products, parties (holder, manufacturers, API suppliers, labs, authority), a shared document library where each
certificate / licence / approval has a type, an issuer, dates and links to the products and parties it serves,
and a dashboard computed from those facts:
  - expired / expiring documents with the products they affect;
  - documents a product must have on file and does not (per role: holder, manufacturer, API supplier…);
  - renewal of the registration.
Validity rules live in rulepacks/eda.doc-validity.v1/doc_types.yaml with source and provenance."""
import json, time, uuid
from datetime import date
from pathlib import Path
import yaml
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse

TYPES_FILE = Path(__file__).resolve().parents[3] / 'rulepacks' / 'eda.doc-validity.v1' / 'doc_types.yaml'
ROLES = ('holder', 'manufacturer', 'api_supplier', 'storage', 'lab', 'other')
PARTY_KINDS = ('company', 'manufacturer', 'supplier', 'lab', 'authority', 'other')

SCHEMA = '''
create table if not exists party(id text primary key, name text not null, kind text not null, country text,
  address text, notes text, created real not null);
create table if not exists product(id text primary key, name text not null, name_ar text, dosage_form text,
  admin_route text, strength text, reg_no text, reg_date text, licence_type text, shelf_life text, storage text,
  packs text not null default '[]', price text, status text not null default 'registered', notes text,
  dossier_id text, created real not null);
create table if not exists product_party(id text primary key, product_id text not null, party_id text not null,
  role text not null, api_name text, unique(product_id, party_id, role, api_name));
create table if not exists libdoc(id text primary key, doc_type text not null, title text not null, number text,
  issuer text, issued text, valid_until text, sha256 text, filename text, url text, notes text,
  state text not null default 'current', replaced_by text, created real not null);
create table if not exists libdoc_link(doc_id text not null, product_id text, party_id text);
create index if not exists libdoc_link_p on libdoc_link(product_id);
create index if not exists libdoc_link_q on libdoc_link(party_id);
'''


class SuiteError(ValueError):
    def __init__(self, code, en, ar):
        super().__init__(en)
        self.code, self.en, self.ar = code, en, ar


def _date(s, field):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise SuiteError('E-DATE', f'{field}: use a date like 2027-03-31.', f'{field}: اكتب التاريخ بالشكل 2027-03-31.')


def _add_months(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    import calendar
    day = min(d.day, calendar.monthrange(d.year + y, mo + 1)[1])
    return date(d.year + y, mo + 1, day)


class Suite:
    def __init__(self, st, today=None):
        self.st = st
        self._today = today
        st.db.executescript(SCHEMA)
        st.db.commit()
        rules = yaml.safe_load(TYPES_FILE.read_text(encoding='utf-8'))
        self.types = {t['id']: t for t in rules['types']}
        self.required = rules['required']
        self.warn_default = rules.get('warn_days_default', 90)

    @property
    def db(self):
        return self.st.db

    def today(self):
        return self._today() if callable(self._today) else (self._today or date.today())

    def _audit(self, event, **kw):
        self.st.audit(None, 'suite.' + event, **kw)

    # ---------------- parties
    def add_party(self, name, kind='company', country=None, address=None, notes=None):
        if not name or not name.strip():
            raise SuiteError('E-NAME', 'Name is required.', 'الاسم مطلوب.')
        if kind not in PARTY_KINDS:
            raise SuiteError('E-KIND', f'Kind must be one of {PARTY_KINDS}.', 'نوع الطرف غير معروف.')
        pid = str(uuid.uuid4())
        self.db.execute('insert into party values (?,?,?,?,?,?,?)', (pid, name.strip(), kind, country, address, notes, time.time()))
        self.db.commit()
        self._audit('party.added', party=pid, name=name)
        return self.party(pid)

    def update_party(self, pid, **f):
        self.party(pid)
        for k in ('name', 'kind', 'country', 'address', 'notes'):
            if k in f:
                self.db.execute(f'update party set {k}=? where id=?', (f[k], pid))
        self.db.commit()
        return self.party(pid)

    def party(self, pid):
        r = self.db.execute('select * from party where id=?', (pid,)).fetchone()
        if not r:
            raise SuiteError('E-NOT-FOUND', 'Party not found.', 'الطرف غير موجود.')
        return dict(r)

    def parties(self):
        out = []
        for r in self.db.execute('select * from party order by name').fetchall():
            p = dict(r)
            p['products'] = [dict(x) for x in self.db.execute(
                'select pp.role, pp.api_name, p.id product_id, p.name product from product_party pp join product p on p.id=pp.product_id '
                'where pp.party_id=?', (p['id'],)).fetchall()]
            p['documents'] = [self.doc_view(d) for d in self._docs_where('l.party_id=?', (p['id'],))]
            out.append(p)
        return out

    # ---------------- products
    PRODUCT_FIELDS = ('name', 'name_ar', 'dosage_form', 'admin_route', 'strength', 'reg_no', 'reg_date', 'licence_type',
                      'shelf_life', 'storage', 'price', 'status', 'notes', 'dossier_id')

    def add_product(self, **f):
        if not f.get('name'):
            raise SuiteError('E-NAME', 'Product name is required.', 'اسم المنتج مطلوب.')
        _date(f.get('reg_date'), 'reg_date')
        pid = str(uuid.uuid4())
        self.db.execute('insert into product(id, name, created, packs) values (?,?,?,?)',
                        (pid, f['name'], time.time(), json.dumps(f.get('packs') or [], ensure_ascii=False)))
        self.db.commit()
        self.update_product(pid, **{k: v for k, v in f.items() if k != 'packs'})
        self._audit('product.added', product=pid, name=f['name'])
        return self.product(pid)

    def update_product(self, pid, **f):
        self._product_row(pid)
        if 'reg_date' in f:
            _date(f['reg_date'], 'reg_date')
        for k in self.PRODUCT_FIELDS:
            if k in f:
                self.db.execute(f'update product set {k}=? where id=?', (f[k], pid))
        if 'packs' in f:
            self.db.execute('update product set packs=? where id=?', (json.dumps(f['packs'] or [], ensure_ascii=False), pid))
        self.db.commit()
        return self.product(pid)

    def _product_row(self, pid):
        r = self.db.execute('select * from product where id=?', (pid,)).fetchone()
        if not r:
            raise SuiteError('E-NOT-FOUND', 'Product not found.', 'المنتج غير موجود.')
        d = dict(r)
        d['packs'] = json.loads(d['packs'])
        return d

    def link_party(self, product_id, party_id, role, api_name=None):
        self._product_row(product_id)
        self.party(party_id)
        if role not in ROLES:
            raise SuiteError('E-ROLE', f'Role must be one of {ROLES}.', 'الدور غير معروف.')
        if role == 'api_supplier' and not api_name:
            raise SuiteError('E-API', 'Name the active substance this supplier provides.', 'اكتب اسم المادة الفعالة اللي المورد ده بيوردها.')
        lid = str(uuid.uuid4())
        try:
            self.db.execute('insert into product_party values (?,?,?,?,?)', (lid, product_id, party_id, role, api_name))
        except Exception:
            raise SuiteError('E-DUP', 'This party already has that role on the product.', 'الطرف ده متسجّل بنفس الدور على المنتج.')
        self.db.commit()
        self._audit('product.party_linked', product=product_id, party=party_id, role=role, api=api_name)
        return lid

    def unlink_party(self, product_id, link_id):
        self.db.execute('delete from product_party where id=? and product_id=?', (link_id, product_id))
        self.db.commit()

    def product_parties(self, pid):
        return [dict(r) for r in self.db.execute(
            'select pp.id link_id, pp.role, pp.api_name, p.* from product_party pp join party p on p.id=pp.party_id '
            'where pp.product_id=? order by pp.role, pp.api_name', (pid,)).fetchall()]

    # ---------------- document library
    def add_doc(self, doc_type, title=None, number=None, issuer=None, issued=None, valid_until=None, notes=None,
                url=None, data=None, filename=None, products=(), parties=(), replaces=None):
        if doc_type not in self.types:
            raise SuiteError('E-TYPE', 'Unknown document type.', 'نوع المستند غير معروف.')
        _date(issued, 'issued'), _date(valid_until, 'valid_until')
        if not data and not url:
            raise SuiteError('E-FILE', 'Attach the file or give its link.', 'ارفع الملف أو اكتب الرابط بتاعه.')
        if url and not str(url).startswith('https://'):
            raise SuiteError('E-URL', 'The link must start with https://', 'الرابط لازم يبدأ بـ https://')
        if not products and not parties:
            raise SuiteError('E-LINK', 'Link the document to at least one product or party.', 'اربط المستند بمنتج أو طرف واحد على الأقل.')
        for p in products:
            self._product_row(p)
        for p in parties:
            self.party(p)
        sha = self.st.put_blob(data) if data else None
        did = str(uuid.uuid4())
        self.db.execute('insert into libdoc values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (did, doc_type, title or self.types[doc_type]['en'], number, issuer, issued, valid_until, sha,
                         filename, url, notes, 'current', None, time.time()))
        links = [(p, None) for p in products] + [(None, q) for q in parties]
        if products and parties:          # product-specific evidence about a party (e.g. import approval of API X for product Y)
            links = [(p, q) for p in products for q in parties]
        for p, q in links:
            self.db.execute('insert into libdoc_link values (?,?,?)', (did, p, q))
        if replaces:
            self.db.execute("update libdoc set state='superseded', replaced_by=? where id=?", (did, replaces))
        self.db.commit()
        self._audit('document.added', doc=did, type=doc_type, sha256=sha, url=url, replaces=replaces)
        return self.doc(did)

    def update_doc(self, did, **f):
        self._doc_row(did)
        for k in ('issued', 'valid_until'):
            if k in f:
                _date(f[k], k)
        for k in ('title', 'number', 'issuer', 'issued', 'valid_until', 'notes', 'doc_type'):
            if k in f:
                if k == 'doc_type' and f[k] not in self.types:
                    raise SuiteError('E-TYPE', 'Unknown document type.', 'نوع المستند غير معروف.')
                self.db.execute(f'update libdoc set {k}=? where id=?', (f[k] or None, did))
        self.db.commit()
        self._audit('document.updated', doc=did, fields=sorted(f))
        return self.doc(did)

    def withdraw_doc(self, did, reason='user'):
        self._doc_row(did)
        self.db.execute("update libdoc set state='withdrawn' where id=?", (did,))
        self.db.commit()
        self._audit('document.withdrawn', doc=did, reason=reason)

    def _doc_row(self, did):
        r = self.db.execute('select * from libdoc where id=?', (did,)).fetchone()
        if not r:
            raise SuiteError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        return dict(r)

    def doc(self, did):
        return self.doc_view(self._doc_row(did))

    def _docs_where(self, cond, args, state='current'):
        rows = self.db.execute(f'select distinct d.* from libdoc d join libdoc_link l on l.doc_id=d.id where {cond} and d.state=? '
                               'order by d.created', (*args, state)).fetchall()
        return [dict(r) for r in rows]

    def validity(self, d):
        """→ (end date or None, status, rule text). status: expired | expiring | valid | no_expiry | needs_date."""
        t = self.types[d['doc_type']]
        end = _date(d['valid_until'], 'valid_until')
        basis = 'printed' if end else None          # codes, translated by the interface
        if not end and t.get('validity_months') and d.get('issued'):
            end = _add_months(_date(d['issued'], 'issued'), t['validity_months'])
            basis = f"issued+{t['validity_months']}"
        today = self.today()
        warn = t.get('warn_days') or self.warn_default
        if end is None:
            return None, ('needs_date' if t.get('validity_months') else 'no_expiry'), basis
        if end < today:
            return end, 'expired', basis
        if (end - today).days <= warn:
            return end, 'expiring', basis
        return end, 'valid', basis

    def doc_view(self, d):
        d = dict(d)
        end, status, basis = self.validity(d)
        t = self.types[d['doc_type']]
        d.update(end=end.isoformat() if end else None, validity=status, validity_basis=basis,
                 days_left=(end - self.today()).days if end else None,
                 type_en=t['en'], type_ar=t['ar'], rule_source=t['source'], rule_provenance=t['provenance'])
        links = self.db.execute('select l.product_id, l.party_id, p.name product, q.name party from libdoc_link l '
                                'left join product p on p.id=l.product_id left join party q on q.id=l.party_id where l.doc_id=?',
                                (d['id'],)).fetchall()
        d['products'] = sorted({(r['product_id'], r['product']) for r in links if r['product_id']})
        d['parties'] = sorted({(r['party_id'], r['party']) for r in links if r['party_id']})
        d['affected'] = self.affected_products(d['id'])
        return d

    def affected_products(self, did):
        """Products that rely on this document: linked directly, or using a party the document is about."""
        rows = self.db.execute(
            'select distinct p.id, p.name from libdoc_link l join product p on p.id=l.product_id where l.doc_id=? '
            'union select distinct p.id, p.name from libdoc_link l join product_party pp on pp.party_id=l.party_id '
            'join product p on p.id=pp.product_id where l.doc_id=? and l.product_id is null', (did, did)).fetchall()
        return sorted({(r['id'], r['name']) for r in rows}, key=lambda x: x[1])

    def documents(self, product=None, party=None, state='current'):
        if product:
            rows = self._docs_where('(l.product_id=? or l.party_id in (select party_id from product_party where product_id=?))',
                                    (product, product), state)
        elif party:
            rows = self._docs_where('l.party_id=?', (party,), state)
        else:
            rows = [dict(r) for r in self.db.execute('select * from libdoc where state=? order by created', (state,)).fetchall()]
        return [self.doc_view(r) for r in rows]

    # ---------------- what each product must have on file
    def checklist(self, pid):
        prod = self._product_row(pid)
        parties = self.product_parties(pid)
        items = []

        def best(doc_types, product_id=None, party_id=None):
            docs = []
            for doc_type in doc_types:
                cond, args = ['d.doc_type=?'], [doc_type]
                if product_id and party_id:
                    cond.append('l.product_id=? and l.party_id=?'); args += [product_id, party_id]
                elif product_id:
                    cond.append('l.product_id=?'); args.append(product_id)
                else:
                    cond.append('l.party_id=?'); args.append(party_id)
                docs += [self.doc_view(d) for d in self._docs_where(' and '.join(cond), args)]
            # a valid document wins; otherwise a known fact (expiring / expired) beats an undated one
            rank = {'valid': 0, 'no_expiry': 0, 'expiring': 1, 'expired': 2, 'needs_date': 3}
            # same status: the one lasting longest, then the most recently issued
            return min(docs, key=lambda x: (rank[x['validity']], -(x['days_left'] or 0),
                                            -date.fromisoformat(x['issued']).toordinal() if x['issued'] else 0), default=None)

        def add(doc_type, who, product_id=None, party=None, api=None):
            alts = doc_type if isinstance(doc_type, list) else [doc_type]
            d = best(alts, product_id, party and party['id'])
            items.append({'doc_type': d['doc_type'] if d else alts[0], 'alternatives': alts,
                          'type_ar': ' أو '.join(self.types[x]['ar'] for x in alts),
                          'type_en': ' or '.join(self.types[x]['en'] for x in alts),
                          'for': who, 'party_id': party and party['id'], 'party': party and party['name'], 'api': api,
                          'status': d['validity'] if d else 'missing', 'document': d})

        for t in self.required['product']:
            add(t, 'product', product_id=pid)
        for p in parties:
            if p['role'] == 'api_supplier':
                for t in self.required['api_supplier']:
                    t_scope = self.types[t[0] if isinstance(t, list) else t]['scope']
                    add(t, 'api_supplier', product_id=pid if t_scope == 'product_party' else None, party=p, api=p['api_name'])
            elif p['role'] == 'manufacturer':
                for t in self.required['manufacturer']:
                    add(t, 'manufacturer', party=p)
            elif p['role'] == 'holder':
                for t in self.required['holder']:
                    add(t, 'holder', party=p)
                if (prod.get('licence_type') or '') in ('toll', 'f_toll'):
                    for t in self.required['toll']:
                        add(t, 'holder', party=p)
        return items

    def renewal(self, pid):
        prod = self._product_row(pid)
        lic = [d for d in self.documents(product=pid) if d['doc_type'] == 'registration_licence' and d['end']]
        if lic:
            d = max(lic, key=lambda x: x['end'])
            return {'due': d['end'], 'basis': d['validity_basis'], 'doc': d['title'], 'source': d['rule_source']}
        if prod.get('reg_date'):
            due = _add_months(_date(prod['reg_date'], 'reg_date'), self.types['registration_licence']['validity_months'])
            return {'due': due.isoformat(), 'basis': 'reg_date+120', 'source': self.types['registration_licence']['source']}
        return None

    def product(self, pid):
        p = self._product_row(pid)
        p['parties'] = self.product_parties(pid)
        p['checklist'] = self.checklist(pid)
        p['documents'] = self.documents(product=pid)
        p['renewal'] = self.renewal(pid)
        c = {}
        for it in p['checklist']:
            c[it['status']] = c.get(it['status'], 0) + 1
        p['counts'] = c
        total = len(p['checklist'])
        ok = c.get('valid', 0) + c.get('no_expiry', 0)
        p['readiness'] = round(100 * ok / total) if total else 0
        return p

    def products(self):
        out = []
        for r in self.db.execute('select id from product order by name').fetchall():
            p = self.product(r['id'])
            out.append({k: p[k] for k in ('id', 'name', 'name_ar', 'dosage_form', 'reg_no', 'licence_type', 'status',
                                          'counts', 'readiness', 'renewal')})
        return out

    # ---------------- dashboard
    def dashboard(self):
        today = self.today()
        issues = []
        sev = {'expired': 0, 'missing': 1, 'needs_date': 2, 'expiring': 3, 'renewal': 4}
        seen = set()
        prods = [self.product(r['id']) for r in self.db.execute('select id from product order by name').fetchall()]
        for p in prods:
            for it in p['checklist']:
                if it['status'] in ('valid', 'no_expiry'):
                    continue
                d = it['document']
                key = (it['status'], d and d['id'], it['doc_type'], it['party_id'], None if d else p['id'])
                if key in seen and d:
                    continue
                seen.add(key)
                dmy = lambda iso: date.fromisoformat(iso).strftime('%d/%m/%Y') if iso else ''
                who = f" — {it['party']}" + (f" ({it['api']})" if it['api'] else '') if it['party'] else ''
                if it['status'] == 'missing':
                    en = f"Missing: {it['type_en']}{who}."
                    ar = f"ناقص: {it['type_ar']}{who}."
                elif it['status'] == 'expired':
                    en = f"Expired {dmy(d['end'])}: {it['type_en']}{who}."
                    ar = f"منتهي من {dmy(d['end'])}: {it['type_ar']}{who}."
                elif it['status'] == 'expiring':
                    en = f"Expires in {d['days_left']} days ({dmy(d['end'])}): {it['type_en']}{who}."
                    ar = f"هينتهي بعد {d['days_left']} يوم ({dmy(d['end'])}): {it['type_ar']}{who}."
                else:
                    en = f"No expiry date recorded: {it['type_en']}{who}."
                    ar = f"مفيش تاريخ انتهاء متسجّل: {it['type_ar']}{who}."
                affected = d['affected'] if d else [(p['id'], p['name'])]
                issues.append({'severity': it['status'], 'en': en, 'ar': ar, 'doc_id': d and d['id'],
                               'doc_type': it['doc_type'], 'party_id': it['party_id'],
                               'products': [{'id': a, 'name': b} for a, b in affected],
                               'source': self.types[it['doc_type']]['source'], 'due': d and d['end']})
            r = p['renewal']
            if r and (date.fromisoformat(r['due']) - today).days <= 365:
                days = (date.fromisoformat(r['due']) - today).days
                issues.append({'severity': 'renewal' if days >= 0 else 'expired', 'doc_type': 'registration_licence',
                               'en': f"{p['name']}: registration renewal due {date.fromisoformat(r['due']).strftime('%d/%m/%Y')} ({days} days).",
                               'ar': f"{p['name']}: ميعاد إعادة التسجيل {date.fromisoformat(r['due']).strftime('%d/%m/%Y')} (بعد {days} يوم).",
                               'products': [{'id': p['id'], 'name': p['name']}], 'source': r['source'], 'due': r['due']})
        # one row per (problem, document/party): merge the products it affects
        merged = {}
        for i in issues:
            k = (i['severity'], i['en'] if not i.get('doc_id') else i['doc_id'])
            if k in merged:
                have = {x['id'] for x in merged[k]['products']}
                merged[k]['products'] += [x for x in i['products'] if x['id'] not in have]
            else:
                merged[k] = i
        issues = sorted(merged.values(), key=lambda i: (sev[i['severity']], i.get('due') or '9999'))
        docs = self.documents()
        return {
            'today': today.isoformat(),
            'counts': {'products': len(prods), 'documents': len(docs),
                       'expired': sum(1 for i in issues if i['severity'] == 'expired'),
                       'missing': sum(1 for i in issues if i['severity'] == 'missing'),
                       'expiring': sum(1 for i in issues if i['severity'] == 'expiring'),
                       'needs_date': sum(1 for i in issues if i['severity'] == 'needs_date'),
                       'renewal': sum(1 for i in issues if i['severity'] == 'renewal')},
            'issues': issues,
            'products': [{k: p[k] for k in ('id', 'name', 'name_ar', 'reg_no', 'readiness', 'counts', 'renewal')} for p in prods],
        }


def install(app, st, err):
    """Register /api/suite/* routes on the FastAPI app."""
    from fastapi.responses import JSONResponse
    suite = Suite(st)
    app.state.suite = suite

    @app.exception_handler(SuiteError)
    def _suite_err(request, e):
        return JSONResponse(status_code=404 if e.code == 'E-NOT-FOUND' else 422,
                            content={'detail': {'code': e.code, 'en': e.en, 'ar': e.ar}})

    @app.get('/api/suite/types')
    def types():
        return {'types': list(suite.types.values()), 'required': suite.required, 'roles': ROLES, 'party_kinds': PARTY_KINDS}

    @app.get('/api/suite/dashboard')
    def dashboard():
        return suite.dashboard()

    @app.get('/api/suite/parties')
    def parties():
        return suite.parties()

    @app.post('/api/suite/parties', status_code=201)
    def add_party(body: dict):
        return suite.add_party(body.get('name'), body.get('kind') or 'company', body.get('country'), body.get('address'), body.get('notes'))

    @app.put('/api/suite/parties/{pid}')
    def put_party(pid: str, body: dict):
        return suite.update_party(pid, **{k: v for k, v in body.items() if k in ('name', 'kind', 'country', 'address', 'notes')})

    @app.get('/api/suite/products')
    def products():
        return suite.products()

    @app.post('/api/suite/products', status_code=201)
    def add_product(body: dict):
        return suite.add_product(**{k: v for k, v in body.items() if k in Suite.PRODUCT_FIELDS + ('packs',)})

    @app.get('/api/suite/products/{pid}')
    def product(pid: str):
        return suite.product(pid)

    @app.put('/api/suite/products/{pid}')
    def put_product(pid: str, body: dict):
        return suite.update_product(pid, **{k: v for k, v in body.items() if k in Suite.PRODUCT_FIELDS + ('packs',)})

    @app.post('/api/suite/products/{pid}/parties', status_code=201)
    def link(pid: str, body: dict):
        return {'link_id': suite.link_party(pid, body.get('party_id'), body.get('role'), body.get('api_name'))}

    @app.delete('/api/suite/products/{pid}/parties/{lid}')
    def unlink(pid: str, lid: str):
        suite.unlink_party(pid, lid)
        return {'ok': True}

    @app.get('/api/suite/documents')
    def documents(product: str = None, party: str = None, state: str = 'current'):
        return suite.documents(product, party, state)

    @app.post('/api/suite/documents', status_code=201)
    async def add_doc(meta: str = Form(...), file: UploadFile = File(None)):
        m = json.loads(meta)
        data = await file.read() if file else None
        return suite.add_doc(m.get('doc_type'), m.get('title'), m.get('number'), m.get('issuer'), m.get('issued') or None,
                             m.get('valid_until') or None, m.get('notes'), m.get('url') or None, data,
                             file.filename if file else None, m.get('products') or [], m.get('parties') or [], m.get('replaces'))

    @app.put('/api/suite/documents/{did}')
    def put_doc(did: str, body: dict):
        return suite.update_doc(did, **{k: v for k, v in body.items()
                                        if k in ('title', 'number', 'issuer', 'issued', 'valid_until', 'notes', 'doc_type')})

    @app.post('/api/suite/documents/{did}/withdraw')
    def withdraw(did: str, reason: str = 'user'):
        suite.withdraw_doc(did, reason)
        return {'ok': True}

    @app.get('/api/suite/documents/{did}/file')
    def doc_file(did: str):
        d = suite._doc_row(did)
        if not d['sha256']:
            err(404, 'E-EXTERNAL', 'This document is a link; open it from the link.', 'المستند ده رابط؛ افتحه من الرابط.')
        name = d['filename'] or 'document.pdf'
        return FileResponse(st.blob_path(d['sha256']), filename=name,
                            media_type='application/pdf' if name.lower().endswith('.pdf') else None)

    return suite
