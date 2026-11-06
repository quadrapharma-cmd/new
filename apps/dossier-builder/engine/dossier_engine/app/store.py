"""Workspace store (02-LOGIC §2.6, D1 local-first).

<workspace>/workspace.sqlite  — dossiers, document versions, audit, exports
<workspace>/blobs/<sha256>    — content-addressed files: never overwritten, never deleted
Principle 7 «no silent data loss»: a document is withdrawn or superseded, not deleted;
a profile change moves documents of removed slots to «unassigned»."""
import hashlib, json, shutil, sqlite3, time, uuid
from pathlib import Path
from .. import packs
from ..profile import Profile
from ..resolver import resolve, diff
from ..checks.pdf import check as pdf_check

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
create table if not exists export(id text primary key, dossier_id text not null, outputs text not null,
  path text not null, acknowledged integer not null, created real not null);
'''
STATUS_ORDER = ['not_started', 'received', 'conforming', 'needs_attention', 'non_conforming', 'not_applicable']


class StoreError(ValueError):
    def __init__(self, code, en, ar, **extra):
        self.code, self.en, self.ar, self.extra = code, en, ar, extra
        super().__init__(f'{code}: {en}')


class Store:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / 'blobs').mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'workspace.sqlite', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._packs = {}

    # ---------------- helpers
    def pack(self, pid):
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
        self.db.execute('insert into dossier values (?,?,?,?,?,?,?)',
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
        for k in ('profile', 'product', 'envelope'):
            d[k] = json.loads(d[k])
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
            for r in self.db.execute("select id from document where dossier_id=? and slot_id=? and state='current'", (did, sid)):
                self.db.execute("update document set slot_id=null, meta=json_set(meta, '$.previous_slot', ?) where id=?",
                                (sid, r['id']))
                moved.append(r['id'])
        self.db.commit()
        self.audit(did, 'profile.changed', diff=change, moved_to_unassigned=moved)
        return {**change, 'moved_to_unassigned': moved}

    # ---------------- documents
    def add_document(self, did, slot_id, filename, data, title=None, meta=None):
        slots = {s.slot_id: s for s in self.slots(did)}
        if slot_id not in slots:
            raise StoreError('E-SLOT', f'Unknown requirement slot {slot_id}.', 'بند غير معروف.')
        s = slots[slot_id]
        if not s.active:
            raise StoreError('E-SLOT-INACTIVE', f'{slot_id} is not required for this product ({s.level}).',
                             'البند ده مش مطلوب للمنتج ده.', reason=s.reasons[-1])
        sha = self.put_blob(data)
        tmp = self.root / 'blobs' / f'.check-{uuid.uuid4().hex}.pdf'
        shutil.copyfile(self.blob_path(sha), tmp)
        try:
            rep = pdf_check(str(tmp), s.doc_class)
        finally:
            tmp.unlink(missing_ok=True)
        version = 1 + (self.db.execute('select coalesce(max(version),0) from document where dossier_id=? and slot_id=?',
                                       (did, slot_id)).fetchone()[0])
        doc_id = str(uuid.uuid4())
        self.db.execute('insert into document values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (doc_id, did, slot_id, version, sha, filename, title or s.title['en'], s.doc_class,
                         json.dumps(meta or {}, ensure_ascii=False), json.dumps([f.to_dict() for f in rep.findings],
                                                                                ensure_ascii=False),
                         rep.status, 'current', time.time()))
        self.db.commit()
        self.audit(did, 'document.added', slot=slot_id, doc=doc_id, version=version, sha256=sha, status=rep.status)
        return self.document(doc_id)

    def document(self, doc_id):
        r = self.db.execute('select * from document where id=?', (doc_id,)).fetchone()
        if not r:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        d = dict(r)
        d['meta'], d['findings'] = json.loads(d['meta']), json.loads(d['findings'])
        return d

    def documents(self, did, slot_id=None, include_withdrawn=False):
        q = 'select id from document where dossier_id=?'
        args = [did]
        if slot_id is not None:
            q += ' and slot_id=?'
            args.append(slot_id)
        if not include_withdrawn:
            q += " and state='current'"
        return [self.document(r['id']) for r in self.db.execute(q + ' order by created', args)]

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
        unassigned = [d for d in self.documents(did) if d['slot_id'] is None]
        counts = {}
        for x in out:
            counts[x['status']] = counts.get(x['status'], 0) + 1
        return {'slots': out, 'unassigned': unassigned, 'counts': counts}

    def gate(self, did):
        """Blocking reasons before export (01-PLAN P1 «export gate»)."""
        b = self.board(did)
        missing = [s['slot_id'] for s in b['slots'] if s['level'] == 'R' and s['status'] == 'not_started']
        blocking = [s['slot_id'] for s in b['slots'] if s['status'] == 'non_conforming']
        return {'ok': not missing and not blocking, 'missing_required': missing, 'non_conforming': blocking,
                'provisional_profiles': ['EG eCTD 3.2.2 provisional v0', 'EG eCTD 4.0 provisional v0']}
