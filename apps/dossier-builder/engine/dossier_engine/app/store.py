"""Workspace store (02-LOGIC §2.6, D1 local-first).

<workspace>/workspace.sqlite  — dossiers, document versions, audit, exports
<workspace>/blobs/<sha256>    — content-addressed files: never overwritten, never deleted
Principle 7 «no silent data loss»: a document is withdrawn or superseded, not deleted;
a profile change moves documents of removed slots to «unassigned»."""
import hashlib, json, shutil, sqlite3, threading, time, uuid
from datetime import date, timedelta
from pathlib import Path
from .. import packs
from ..profile import Profile
from ..resolver import resolve, diff
from ..checks.pdf import check as pdf_check
from .. import crosschecks

SCHEMA = '''
create table if not exists dossier(id text primary key, name text not null, profile text not null,
  product text not null, envelope text not null, pack text not null, created real not null);
create table if not exists document(id text primary key, dossier_id text not null references dossier(id),
  slot_id text, version integer not null, sha256 text not null, filename text not null, title text,
  doc_class text not null, meta text not null default '{}', findings text not null default '[]',
  check_status text not null, state text not null default 'current', created real not null);
create index if not exists document_slot on document(dossier_id, slot_id, state);
create table if not exists audit(id integer primary key autoincrement, ts real not null, dossier_id text,
  event text not null, detail text not null default '{}');
create table if not exists request(id text primary key, dossier_id text not null, slot_id text not null,
  issuer text not null, lang text not null, sent real not null, due real not null, state text not null default 'open',
  letter_sha text, reason text not null default '[]', closed real);
create table if not exists submission(id text primary key, dossier_id text not null, output text not null,
  seq text not null, activity text, submission_uuid text, envelope text not null, history text not null,
  path text not null, created real not null, unique(dossier_id, output, seq));
create table if not exists export(id text primary key, dossier_id text not null, outputs text not null,
  path text not null, acknowledged integer not null, created real not null);
'''
EXPIRY_WARN_DAYS = 90


def _validity(d, today):
    """Expired evidence blocks its item; evidence expiring within 90 days is flagged. Computed on every read,
    so a document turns red on the day it expires without anyone re-uploading it."""
    vu = d['meta'].get('valid_until')
    if not vu:
        return
    try:
        end = date.fromisoformat(vu)
    except ValueError:
        return
    shown = end.strftime('%d/%m/%Y')
    if end < today:
        d['findings'] = d['findings'] + [{'rule': 'DOC-EXPIRED', 'severity': 'block', 'action': 're_obtain',
            'en': f'Expired on {shown} ({(today - end).days} days ago). Obtain a current certificate from the issuer.',
            'ar': f'منتهي من {shown} (من {(today - end).days} يوم). لازم نسخة سارية من الجهة اللي أصدرته.'}]
        d['check_status'] = 'non_conforming'
    elif end <= today + timedelta(days=EXPIRY_WARN_DAYS):
        d['findings'] = d['findings'] + [{'rule': 'DOC-EXPIRING', 'severity': 'warn', 'action': 're_obtain',
            'en': f'Expires on {shown} (in {(end - today).days} days). Start renewal now.',
            'ar': f'هينتهي {shown} (بعد {(end - today).days} يوم). ابدأ التجديد من دلوقتي.'}]
        if d['check_status'] in ('conforming', 'received'):
            d['check_status'] = 'needs_attention'


STATUS_ORDER = ['not_started', 'received', 'conforming', 'needs_attention', 'non_conforming', 'not_applicable']
SIGN_KINDS = {'annex1', 'cover', 'composition', 'salt', 'cep_commitment', 'translation', 'stability_commitment', 'justification',
              'reobtain'}


class StoreError(ValueError):
    def __init__(self, code, en, ar, **extra):
        self.code, self.en, self.ar, self.extra = code, en, ar, extra
        super().__init__(f'{code}: {en}')


class Store:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / 'blobs').mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.db.execute('pragma journal_mode=wal')
        self.db.executescript(SCHEMA)
        cols = {r[1] for r in self.db.execute('pragma table_info(dossier)')}
        if 'data' not in cols:                       # P2: structured dossier data (additive migration)
            self.db.execute("alter table dossier add column data text not null default '{}'")
            self.db.commit()
        self._packs = {}
        self._pack_lock = threading.Lock()

    @property
    def db(self):
        """One SQLite connection per thread (the API serves requests in a thread pool)."""
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.root / 'workspace.sqlite', timeout=30)
            c.row_factory = sqlite3.Row
            c.execute('pragma busy_timeout=30000')
            self._local.conn = c
        return c

    # ---------------- helpers
    def pack(self, pid):
        with self._pack_lock:
            if pid not in self._packs:
                self._packs[pid] = packs.load(pid)
            return self._packs[pid]

    def audit(self, dossier_id, event, **detail):
        self.db.execute('insert into audit(ts, dossier_id, event, detail) values (?,?,?,?)',
                        (time.time(), dossier_id, event, json.dumps(detail, ensure_ascii=False)))
        self.db.commit()

    def blob_path(self, sha):
        return self.root / 'blobs' / sha

    def put_blob(self, src_bytes):
        sha = hashlib.sha256(src_bytes).hexdigest()
        p = self.blob_path(sha)
        if not p.exists():
            tmp = p.with_suffix('.tmp')
            tmp.write_bytes(src_bytes)
            tmp.rename(p)
        return sha

    # ---------------- dossiers
    def create_dossier(self, name, profile, product, envelope, pack='eda.ctd.nta065.v5'):
        prof = Profile.from_dict(profile)
        prof.validate()
        did = str(uuid.uuid4())
        envelope = dict(envelope)
        envelope.setdefault('application_uuid', str(uuid.uuid4()))
        self.db.execute('insert into dossier(id, name, profile, product, envelope, pack, created) values (?,?,?,?,?,?,?)',
                        (did, name, json.dumps(profile, ensure_ascii=False), json.dumps(product, ensure_ascii=False),
                         json.dumps(envelope, ensure_ascii=False), pack, time.time()))
        self.db.commit()
        self.audit(did, 'dossier.created', name=name)
        return did

    def dossier(self, did):
        r = self.db.execute('select * from dossier where id=?', (did,)).fetchone()
        if not r:
            raise StoreError('E-NOT-FOUND', 'Dossier not found.', 'الملف غير موجود.')
        d = dict(r)
        for k in ('profile', 'product', 'envelope', 'data'):
            d[k] = json.loads(d.get(k) or '{}')
        return d

    def list_dossiers(self):
        return [dict(r) for r in self.db.execute('select id, name, created from dossier order by created desc')]

    def slots(self, did):
        d = self.dossier(did)
        return resolve(Profile.from_dict(d['profile']), self.pack(d['pack']))

    def update_profile(self, did, profile):
        d = self.dossier(did)
        old = self.slots(did)
        prof = Profile.from_dict(profile)
        prof.validate()
        new = resolve(prof, self.pack(d['pack']))
        change = diff(old, new)
        self.db.execute('update dossier set profile=? where id=?', (json.dumps(profile, ensure_ascii=False), did))
        moved = []
        for sid in change['removed']:
            for r in self.db.execute("select id from document where dossier_id=? and slot_id=? and state='current'", (did, sid)).fetchall():
                self.db.execute("update document set slot_id=null, meta=json_set(meta, '$.previous_slot', ?) where id=?",
                                (sid, r['id']))
                moved.append(r['id'])
        self.db.commit()
        self.audit(did, 'profile.changed', diff=change, moved_to_unassigned=moved)
        return {**change, 'moved_to_unassigned': moved}

    def set_data(self, did, data):
        self.dossier(did)
        self.db.execute('update dossier set data=? where id=?', (json.dumps(data, ensure_ascii=False), did))
        self.db.commit()
        self.audit(did, 'data.updated', keys=sorted(data))
        return self.cross(did)

    def cross(self, did):
        d = self.dossier(did)
        data = dict(d['data'])
        names = dict(data.get('applicant_names') or {})
        names.setdefault('envelope', d['envelope'].get('applicant'))
        for doc in self.documents(did):
            g = (doc['meta'].get('data') or {}).get('company')
            if g:
                names.setdefault(doc['meta'].get('generated') or 'letter', g)
        data['applicant_names'] = names
        return [f.to_dict() for f in crosschecks.run(data, Profile.from_dict(d['profile']))] if (d['data'] or len(set(
            v for v in names.values() if v)) > 1) else []

    # ---------------- documents
    def add_document(self, did, slot_id, filename, data, title=None, meta=None, supersede=None, doc_class=None):
        slots = {s.slot_id: s for s in self.slots(did)}
        if slot_id not in slots:
            raise StoreError('E-SLOT', f'Unknown requirement slot {slot_id}.', 'بند غير معروف.')
        s = slots[slot_id]
        if not s.active:
            raise StoreError('E-SLOT-INACTIVE', f'{slot_id} is not required for this product ({s.level}).',
                             'البند ده مش مطلوب للمنتج ده.', reason=s.reasons[-1])
        meta = dict(meta or {})
        if meta.get('signed_for'):                    # signed scan of a generated draft (02-LOGIC §6 «signed_scan»)
            draft = self.document(meta['signed_for'])
            if draft['dossier_id'] != did or draft['slot_id'] != slot_id or not draft['meta'].get('draft_unsigned'):
                raise StoreError('E-SIGNED-FOR', 'The signed copy must belong to an unsigned draft of the same section.',
                                 'النسخة الموقّعة لازم تخص مسودة غير موقّعة في نفس القسم.')
            doc_class, supersede = 'signed_scan', draft['id']
        sha = self.put_blob(data)
        tmp = self.root / 'blobs' / f'.check-{uuid.uuid4().hex}.pdf'
        shutil.copyfile(self.blob_path(sha), tmp)
        try:
            rep = pdf_check(str(tmp), doc_class or s.doc_class)
        finally:
            tmp.unlink(missing_ok=True)
        version = 1 + (self.db.execute('select coalesce(max(version),0) from document where dossier_id=? and slot_id=?',
                                       (did, slot_id)).fetchone()[0])
        doc_id = str(uuid.uuid4())
        self.db.execute('insert into document values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (doc_id, did, slot_id, version, sha, filename, title or s.title['en'], doc_class or s.doc_class,
                         json.dumps(meta, ensure_ascii=False), json.dumps([f.to_dict() for f in rep.findings],
                                                                                ensure_ascii=False),
                         rep.status, 'current', time.time()))
        if supersede:
            self.db.execute("update document set state='superseded' where id=? and dossier_id=?", (supersede, did))
        if rep.status == 'conforming':
            for r in self.db.execute("select id from request where dossier_id=? and slot_id=? and state='open'", (did, slot_id)).fetchall():
                self.db.execute("update request set state='closed', closed=? where id=?", (time.time(), r['id']))
                self.audit(did, 'request.closed', request=r['id'], by_doc=doc_id)
        self.db.commit()
        self.audit(did, 'document.added', slot=slot_id, doc=doc_id, version=version, sha256=sha, status=rep.status,
                   supersedes=supersede, signed_for=meta.get('signed_for'))
        return self.document(doc_id)

    def add_reference(self, did, slot_id, title, url, source='drive', note=None, ref_id=None, valid_until=None):
        """An «external reference»: the document exists (e.g. on the company Drive) but its file is not in the
        workspace yet. Shown as «received — not checked»; it never counts as conforming and it blocks export
        until the real file is uploaded (upload with replaces=<reference id>)."""
        slots = {s.slot_id: s for s in self.slots(did)}
        if slot_id not in slots:
            raise StoreError('E-SLOT', f'Unknown requirement slot {slot_id}.', 'بند غير معروف.')
        s = slots[slot_id]
        if not s.active:
            raise StoreError('E-SLOT-INACTIVE', f'{slot_id} is not required for this product ({s.level}).',
                             'البند ده مش مطلوب للمنتج ده.', reason=s.reasons[-1])
        if not title or not url:
            raise StoreError('E-REFERENCE', 'A reference needs a title and a link.', 'المرجع محتاج عنوان ورابط.')
        version = 1 + (self.db.execute('select coalesce(max(version),0) from document where dossier_id=? and slot_id=?',
                                       (did, slot_id)).fetchone()[0])
        doc_id = str(uuid.uuid4())
        meta = {'external': True, 'url': url, 'source': source, 'note': note, 'ref_id': ref_id}
        if valid_until:
            date.fromisoformat(valid_until)
            meta['valid_until'] = valid_until
        self.db.execute('insert into document values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (doc_id, did, slot_id, version, '', title, title, s.doc_class,
                         json.dumps(meta, ensure_ascii=False), '[]', 'received', 'current', time.time()))
        self.db.commit()
        self.audit(did, 'reference.added', slot=slot_id, doc=doc_id, source=source, url=url)
        return self.document(doc_id)

    def fix_document(self, did, doc_id):
        from .. import fixes
        d = self.document(doc_id)
        if d['dossier_id'] != did or d['state'] != 'current':
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if d['meta'].get('external'):
            raise StoreError('E-EXTERNAL', 'Upload the file first: an external reference has nothing to fix.',
                             'ارفع الملف الأول: المرجع الخارجي مفيهوش ملف يتصلّح.')
        r = fixes.apply(self.blob_path(d['sha256']), d['findings'], d['doc_class'])
        new = None
        if r['data']:
            new = self.add_document(did, d['slot_id'], d['filename'], r['data'], d['title'],
                                    {**d['meta'], 'fixed_from': doc_id, 'fixes': [x['op'] for x in r['done']]},
                                    supersede=doc_id, doc_class=d['doc_class'])
        self.audit(did, 'document.fixed' if new else 'document.fix_refused', doc=doc_id, new=new and new['id'],
                   done=[x['op'] for x in r['done']], refused=[x['op'] for x in r['refused']])
        return {'document': new, 'done': r['done'], 'refused': r['refused']}

    # ---------------- submission history (lifecycle, P3)
    def record_submission(self, did, output, seq, activity, suuid, envelope, history, path):
        self.db.execute('insert into submission values (?,?,?,?,?,?,?,?,?,?)',
                        (str(uuid.uuid4()), did, output, str(seq), str(activity), suuid, json.dumps(envelope, ensure_ascii=False),
                         json.dumps(history, ensure_ascii=False), str(path), time.time()))
        self.db.commit()

    def history(self, did, output):
        rows = self.db.execute('select * from submission where dossier_id=? and output=? order by created', (did, output)).fetchall()
        out = []
        for r in rows:
            seq = r['seq'] if output == 'ectd32' else int(r['seq'])
            act = r['activity'] if output == 'ectd32' else int(r['activity'])
            out.append({'seq': seq, 'activity': act, 'submission_uuid': r['submission_uuid'], 'created': r['created'],
                        'envelope': json.loads(r['envelope']), 'leaves': json.loads(r['history']), 'path': r['path']})
        return out

    # ---------------- requests to issuers (re-obtain)
    def open_request(self, did, slot_id, issuer, lang, due_days, letter_sha, reason):
        rid = str(uuid.uuid4())
        now = time.time()
        self.db.execute('insert into request(id, dossier_id, slot_id, issuer, lang, sent, due, letter_sha, reason) values (?,?,?,?,?,?,?,?,?)',
                        (rid, did, slot_id, issuer, lang, now, now + 86400 * int(due_days), letter_sha,
                         json.dumps(reason, ensure_ascii=False)))
        self.db.commit()
        self.audit(did, 'request.opened', request=rid, slot=slot_id, issuer=issuer, due_days=due_days)
        return rid

    def requests(self, did, state='open'):
        return [dict(r) | {'reason': json.loads(r['reason']), 'overdue': r['state'] == 'open' and r['due'] < time.time()}
                for r in self.db.execute('select * from request where dossier_id=? and state=? order by sent', (did, state))]

    def document(self, doc_id):
        r = self.db.execute('select * from document where id=?', (doc_id,)).fetchone()
        if not r:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        d = dict(r)
        d['meta'], d['findings'] = json.loads(d['meta']), json.loads(d['findings'])
        _validity(d, self.today())
        return d

    def today(self):
        return date.today()

    def set_validity(self, did, doc_id, valid_until, issued=None, note=None):
        """Record the date a certificate / licence / approval stops being valid (ISO yyyy-mm-dd)."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        try:
            date.fromisoformat(valid_until)
        except (TypeError, ValueError):
            raise StoreError('E-DATE', 'Use a date like 2027-03-31.', 'اكتب التاريخ بالشكل 2027-03-31.')
        meta = {**d['meta'], 'valid_until': valid_until}
        if issued:
            meta['issued'] = issued
        if note:
            meta['validity_note'] = note
        self.db.execute('update document set meta=? where id=?', (json.dumps(meta, ensure_ascii=False), doc_id))
        self.db.commit()
        self.audit(did, 'document.validity', doc=doc_id, valid_until=valid_until)
        return self.document(doc_id)

    def documents(self, did, slot_id=None, include_withdrawn=False):
        q = 'select id from document where dossier_id=?'
        args = [did]
        if slot_id is not None:
            q += ' and slot_id=?'
            args.append(slot_id)
        if not include_withdrawn:
            q += " and state='current'"
        ids = [r['id'] for r in self.db.execute(q + ' order by created', args).fetchall()]
        return [self.document(i) for i in ids]

    def withdraw(self, did, doc_id, reason):
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        self.db.execute("update document set state='withdrawn' where id=?", (doc_id,))
        self.db.commit()
        self.audit(did, 'document.withdrawn', doc=doc_id, reason=reason)   # blob kept: undo is possible
        return self.document(doc_id)

    def restore(self, did, doc_id):
        self.db.execute("update document set state='current' where id=? and dossier_id=?", (doc_id, did))
        self.db.commit()
        self.audit(did, 'document.restored', doc=doc_id)
        return self.document(doc_id)

    # ---------------- board
    def board(self, did):
        out = []
        for s in self.slots(did):
            docs = self.documents(did, s.slot_id) if s.active else []
            if not s.active:
                status = 'not_applicable'
            elif not docs:
                status = 'not_started'
            else:
                status = max((d['check_status'] for d in docs), key=lambda x: STATUS_ORDER.index(x))
            out.append({**s.to_dict(), 'status': status,
                        'documents': [{k: d[k] for k in ('id', 'version', 'filename', 'title', 'check_status',
                                                         'findings', 'sha256', 'meta')} for d in docs]})
        reqs_by_id = self.pack(self.dossier(did)['pack']).by_id
        for x in out:
            rq = reqs_by_id.get(x['req_id'], {})
            x['acceptance'] = rq.get('acceptance_text')
            x['sources'] = rq.get('sources', [])
            x['provenance'] = rq.get('provenance')
            x['produced_by'] = rq.get('produced_by')
            x['how'] = (rq.get('rebuild') or {}).get('needs')
        cross = self.cross(did)
        by_slot = {}
        for f in cross:
            for sid in f['slots']:
                by_slot.setdefault(sid, []).append(f)
        reqs = {r['slot_id']: r for r in self.requests(did)}
        for x in out:
            x['cross'] = by_slot.get(x['slot_id'], [])
            x['request'] = reqs.get(x['slot_id'])
            x['unsigned'] = [d['id'] for d in x['documents'] if d['meta'].get('draft_unsigned')]
            x['external'] = [d['id'] for d in x['documents'] if d['meta'].get('external')]
            if x['status'] in ('received', 'conforming', 'needs_attention') and x['cross']:
                x['status'] = 'non_conforming' if any(f['severity'] == 'block' for f in x['cross']) else \
                    max(x['status'], 'needs_attention', key=STATUS_ORDER.index)
        for x in out:
            if x['unsigned'] and x['status'] == 'conforming':
                x['status'] = 'needs_attention'
            if x['request'] and x['status'] in ('not_started', 'non_conforming', 'needs_attention', 'received'):
                x['status'] = 'waiting'
            if x['req_id'] == 'M1-44' and x['status'] == 'not_started':
                x['status'] = 'auto'              # tracking table: rebuilt from the history at every eCTD export
        unassigned = [d for d in self.documents(did) if d['slot_id'] is None]
        counts = {}
        for x in out:
            counts[x['status']] = counts.get(x['status'], 0) + 1
        return {'slots': out, 'unassigned': unassigned, 'counts': counts, 'cross': cross}

    def gate(self, did):
        """Blocking reasons before export (01-PLAN P1 «export gate»)."""
        b = self.board(did)
        missing = [s['slot_id'] for s in b['slots'] if s['level'] == 'R' and (s['status'] == 'not_started' or
                   s['status'] == 'waiting' and not s['documents'])]
        blocking = [s['slot_id'] for s in b['slots'] if s['status'] == 'non_conforming' or
                    s['status'] == 'waiting' and s['documents']]
        unsigned = [s['slot_id'] for s in b['slots'] if s['unsigned']]
        external = [s['slot_id'] for s in b['slots'] if s['external']]
        xb = [f for f in b['cross'] if f['severity'] == 'block']
        return {'ok': not missing and not blocking and not xb and not unsigned and not external, 'unsigned': unsigned,
                'external_only': external, 'missing_required': missing, 'non_conforming': blocking,
                'cross_blocking': [{'id': f['id'], 'en': f['en'], 'ar': f['ar']} for f in xb],
                'provisional_profiles': ['EG eCTD 3.2.2 provisional v0', 'EG eCTD 4.0 provisional v0']}
