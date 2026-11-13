"""Workspace store (02-LOGIC §2.6, D1 local-first).

<workspace>/workspace.sqlite  — dossiers, document versions, audit, exports
<workspace>/blobs/<sha256>    — content-addressed files: never overwritten, never deleted
Principle 7 «no silent data loss»: a document is withdrawn or superseded, not deleted;
a profile change moves documents of removed slots to «unassigned»."""
import contextvars, hashlib, json, re, shutil, sqlite3, sys, threading, time, uuid
from datetime import date, timedelta
from pathlib import Path
from .. import packs
from ..profile import Profile
from ..resolver import resolve, diff
from ..checks.pdf import check as pdf_check, Finding, Report
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
create table if not exists intake_draft(id text primary key, state text not null default '{}', created real not null, updated real not null);
create table if not exists intake_file(draft_id text not null, filename text not null, sha256 text not null, kind text, size integer not null default 0,
  added real not null, primary key(draft_id, filename));
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


# who is acting in the current request (set by the auth middleware; 'local' when login is off)
ACTOR = contextvars.ContextVar('actor', default='local')

# Numbered, additive schema migrations with a ledger (never edit an applied one — add a new one).
MIGRATIONS = [
    (1, 'dossier.data column', ["alter table dossier add column data text not null default '{}'"]),
    (2, 'audit actor and hash chain', ["alter table audit add column actor text",
                                       "alter table audit add column prev_hash text",
                                       "alter table audit add column hash text"]),
    (3, 'audit is append-only', [
        "create trigger if not exists audit_no_update before update on audit begin select raise(abort, 'audit is append-only'); end",
        "create trigger if not exists audit_no_delete before delete on audit begin select raise(abort, 'audit is append-only'); end"]),
    (4, 'a project can be put in the trash', ["alter table dossier add column deleted real"]),
]


class StoreError(ValueError):
    def __init__(self, code, en, ar, **extra):
        self.code, self.en, self.ar, self.extra = code, en, ar, extra
        super().__init__(f'{code}: {en}')


SOURCE_DRAFT = {
    'word': ('Word draft. Print it on letterhead, sign, stamp, scan and upload the PDF (or export it to PDF): the PDF replaces this draft.',
             'مسودة Word. اطبعها على ورق الشركة ووقّعها واختمها وامسحها ضوئياً وارفع الـ PDF (أو صدّرها PDF): نسخة الـ PDF بتحل محل المسودة.'),
    'excel': ('An Excel file. The dossier takes PDF: export the sheet to PDF (signed and stamped where the document needs it) and upload it; the PDF replaces this file.',
              'ملف Excel. الملف التسجيلي بياخد PDF: صدّر الشيت PDF (موقّع ومختوم لو المستند محتاج) وارفعه؛ الـ PDF بيحل محل الملف ده.'),
    'powerpoint': ('A PowerPoint file. The dossier takes PDF: export it to PDF and upload it; the PDF replaces this file.',
                   'ملف PowerPoint. الملف التسجيلي بياخد PDF: صدّره PDF وارفعه؛ الـ PDF بيحل محل الملف ده.'),
    'image': ('An image this machine could not turn into a PDF. The dossier takes PDF: save or scan it as PDF and upload it; the PDF replaces this file.',
              'صورة الجهاز ده ما قدرش يحوّلها PDF. الملف التسجيلي بياخد PDF: احفظها أو امسحها PDF وارفعها؛ الـ PDF بيحل محل الملف ده.'),
    'text': ('A text or web file, not a PDF. The dossier takes PDF: save it as PDF (signed and stamped where the document needs it) and upload it; the PDF replaces this file.',
             'ملف نصي أو صفحة ويب، مش PDF. الملف التسجيلي بياخد PDF: احفظه PDF (موقّع ومختوم لو المستند محتاج) وارفعه؛ الـ PDF بيحل محل الملف ده.')}


class Store:
    def claim_readings(self):
        """The reader's kept readings (extract.read_text) go to this workspace's cache folder."""
        from .. import extract as _ex
        _ex.READ_DIR = self.root / 'cache' / 'text'

    def __init__(self, root):
        self.root = Path(root)
        self.claim_readings()                                # a file is read once: its reading is kept by its SHA-256
        (self.root / 'blobs').mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.db.execute('pragma journal_mode=' + ('delete' if sys.platform == 'emscripten' else 'wal'))   # no shared memory in the browser
        self.db.executescript(SCHEMA)
        self._migrate()
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

    def _migrate(self):
        db = self.db
        db.execute('create table if not exists schema_migrations(id integer primary key, name text not null, applied real not null)')
        done = {r[0] for r in db.execute('select id from schema_migrations')}
        for mid, name, stmts in MIGRATIONS:
            if mid in done:
                continue
            for sql in stmts:
                try:
                    db.execute(sql)
                except sqlite3.OperationalError as e:      # column already there from an older ad-hoc migration
                    if 'duplicate column' not in str(e):
                        raise
            db.execute('insert into schema_migrations values (?,?,?)', (mid, name, time.time()))
            db.commit()

    _audit_lock = threading.Lock()

    def audit(self, dossier_id, event, **detail):
        """Append-only, hash-chained activity record: who (actor), when, what. Each row's hash covers the previous
        row's hash, so editing or removing a row breaks the chain (see verify_audit)."""
        actor = ACTOR.get()
        ts = time.time()
        body = json.dumps(detail, ensure_ascii=False, sort_keys=True)
        with self._audit_lock:
            prev = self.db.execute('select hash from audit order by id desc limit 1').fetchone()
            prev = prev[0] if prev and prev[0] else ''
            h = hashlib.sha256(f'{prev}|{ts!r}|{actor}|{dossier_id}|{event}|{body}'.encode()).hexdigest()
            self.db.execute('insert into audit(ts, dossier_id, event, detail, actor, prev_hash, hash) values (?,?,?,?,?,?,?)',
                            (ts, dossier_id, event, body, actor, prev, h))
            self.db.commit()

    def verify_audit(self):
        """Recompute the chain; returns (ok, first_bad_id)."""
        prev = ''
        for r in self.db.execute('select id, ts, dossier_id, event, detail, actor, prev_hash, hash from audit order by id'):
            if r['hash'] is None:                  # rows written before migration 2 are outside the chain
                continue
            h = hashlib.sha256(f"{prev}|{r['ts']!r}|{r['actor']}|{r['dossier_id']}|{r['event']}|{r['detail']}".encode()).hexdigest()
            if r['prev_hash'] != prev or r['hash'] != h:
                return False, r['id']
            prev = r['hash']
        return True, None

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
        """pack: the authority the dossier is for (its Module 1 on the common CTD); Egypt's when none is named."""
        pack = pack or 'eda.ctd.nta065.v5'
        try:
            pk = self.pack(pack)
        except (FileNotFoundError, NotADirectoryError):
            raise StoreError('E-PACK', f'Unknown authority pack {pack}.', 'الهيئة دي مش موجودة في البرنامج.')
        if pk.meta.get('kind') == 'base':
            raise StoreError('E-PACK', 'A dossier is built for an authority, not on the common CTD alone.', 'الملف بيتعمل لهيئة، مش على الـ CTD المشترك لوحده.')
        prof = Profile.from_dict(profile)
        prof.validate(pack=pk)
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

    def list_dossiers(self, deleted=False):
        """The projects in use; `deleted=True` gives the ones in the trash instead (with how many documents each holds)."""
        rows = self.db.execute('select id, name, created, profile, product, deleted, pack, envelope from dossier where deleted is %s order by %s desc'
                               % (('not null', 'deleted') if deleted else ('null', 'created'))).fetchall()
        out = []
        for r in rows:
            d = dict(r) | {'profile': json.loads(r['profile'] or '{}'), 'product': json.loads(r['product'] or '{}')}
            env = json.loads(d.pop('envelope') or '{}')
            try:
                au = self.pack(d['pack']).authority
            except Exception:                              # a pack this version no longer has: the project still lists
                au = {'id': '?', 'name': {'en': d['pack'], 'ar': d['pack']}, 'countries': []}
            d['authority'] = {'id': au['id'], 'name': au['name'], 'country': env.get('country') or (au['countries'][0] if len(au['countries']) == 1 and au['countries'][0] != '*' else None)}
            out.append(d)
        if deleted:
            for d in out:
                d['documents'] = self.db.execute("select count(*) from document where dossier_id=? and state='current'", (d['id'],)).fetchone()[0]
        return out

    # ---------------- deleting a project: to the trash first (it comes back), then for good
    def trash_dossier(self, did):
        d = self.dossier(did)
        if not d.get('deleted'):
            self.db.execute('update dossier set deleted=? where id=?', (time.time(), did))
            self.db.commit()
            self.audit(did, 'dossier.trashed', name=d['name'])
        return {'id': did, 'name': d['name'], 'deleted': True}

    def restore_dossier(self, did):
        d = self.dossier(did)
        if d.get('deleted'):
            self.db.execute('update dossier set deleted=null where id=?', (did,))
            self.db.commit()
            self.audit(did, 'dossier.restored', name=d['name'])
        return {'id': did, 'name': d['name'], 'deleted': False}

    def purge_dossier(self, did):
        """Delete a project for good: its documents, data, requests, reviews, conversations and exports. The activity record is
        append-only and keeps its lines, plus one that says who deleted the project and when. Stored files nothing else refers to
        are removed from the disk."""
        d = self.dossier(did)
        counts = {'documents': self.db.execute('select count(*) from document where dossier_id=?', (did,)).fetchone()[0]}
        tables = [r[0] for r in self.db.execute("select name from sqlite_master where type='table'")]
        cols = {t: [c[1] for c in self.db.execute(f'pragma table_info("{t}")')] for t in tables}
        own = [t for t in tables if t not in ('audit', 'dossier', 'product') and 'dossier_id' in cols[t]]
        own.sort(key=lambda t: {'review_finding': 0, 'review_run': 2, 'document': 3}.get(t, 1))     # what refers to a row goes before the row
        try:                                                                       # all of it or none of it
            if 'review_response' in cols and 'review_run' in cols and 'dossier_id' not in cols['review_response']:
                self.db.execute('delete from review_response where run_id in (select id from review_run where dossier_id=?)', (did,))
            if 'product' in cols and 'dossier_id' in cols['product']:              # the product file keeps the product, without its link
                self.db.execute('update product set dossier_id=null where dossier_id=?', (did,))
            for t in own:
                self.db.execute(f'delete from "{t}" where dossier_id=?', (did,))
            self.db.execute('delete from dossier where id=?', (did,))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        for sub in ('exports', 'lifecycle'):
            shutil.rmtree(self.root / sub / did, ignore_errors=True)
        freed = self.gc_blobs(min_age=60)
        self.audit(None, 'dossier.deleted', id=did, name=d['name'], documents=counts['documents'], files_removed=freed['files'])
        return {'id': did, 'name': d['name'], 'documents': counts['documents'], 'files_removed': freed['files'], 'bytes_freed': freed['bytes']}

    def gc_blobs(self, min_age=600, only=None):
        """Remove stored files that no row refers to any more (the activity record does not count: it only remembers). A file
        written in the last `min_age` seconds is left alone: an upload may be on its way to its row. `only`: look at these files alone."""
        used = set()
        for (t,) in self.db.execute("select name from sqlite_master where type='table'").fetchall():
            if t == 'audit':
                continue
            for row in self.db.execute(f'select * from "{t}"'):
                for v in row:
                    if isinstance(v, str) and len(v) >= 64:
                        used.update(re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', v))
        files = size = 0
        now = time.time()
        for p in ((self.root / 'blobs').iterdir() if only is None else [self.root / 'blobs' / n for n in only]):
            if re.fullmatch(r'[0-9a-f]{64}', p.name) and p.name not in used and p.exists() and now - p.stat().st_mtime >= min_age:
                size += p.stat().st_size
                p.unlink(missing_ok=True)
                files += 1
        return {'files': files, 'bytes': size}

    def slots(self, did):
        d = self.dossier(did)
        return resolve(Profile.from_dict(d['profile']), self.pack(d['pack']))

    def update_profile(self, did, profile):
        d = self.dossier(did)
        old = self.slots(did)
        prof = Profile.from_dict(profile)
        prof.validate(pack=self.pack(d['pack']))
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
        out = [f.to_dict() for f in crosschecks.run(data, Profile.from_dict(d['profile']))] if (d['data'] or len(set(
            v for v in names.values() if v)) > 1) else []
        if not self.pack(d['pack']).egypt:               # Egypt's own deficiency list (NP.CAPP.040) is Egypt's; consistency across the dossier is everyone's
            out = [dict(f, source='Consistency across the dossier (general practice)') for f in out if not f['id'].startswith('NP040')]
        return out

    # ---------------- documents
    def refuse_without_text(self, filename, data):
        """The upload gate — NP.CAPP.065 v5 general note 4: every document a scanned and searchable PDF. A file without text of its own
        (a PDF whose pages are images only, an image) is not stored: the program does no OCR, the text layer is made when scanning."""
        from .. import extract as _extract
        from ..checks.pdf import NO_TEXT_EN, NO_TEXT_AR, NO_TEXT_IMAGE_EN, NO_TEXT_IMAGE_AR
        why = _extract.has_text(filename, data)
        if why:
            en, ar = (NO_TEXT_IMAGE_EN, NO_TEXT_IMAGE_AR) if why == 'image' else (NO_TEXT_EN, NO_TEXT_AR)
            raise StoreError('E-NOTEXT', f'{filename}: {en}', f'{filename}: {ar}', why=why, filename=filename)

    def add_document(self, did, slot_id, filename, data, title=None, meta=None, supersede=None, doc_class=None, kind=None):
        """kind: the kind an earlier reading gave this file (the wizard's) — the kind rule uses it when the file's own words say nothing.
        A file without text is refused (refuse_without_text); a PDF 1.0–1.3 is stored with its version line set to 1.7 (fixes.set_version_17:
        every other byte the same; not for a digitally signed file) and says so in meta['converted']."""
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
        from .. import extract as _extract, fixes as _fixes
        self.claim_readings()
        if not meta.get('fixed_from') and not meta.get('external'):      # the upload gate (a fixed copy of a stored document passed it already)
            self.refuse_without_text(filename, data)
        v17 = _fixes.set_version_17(data) if data[:1024].find(b'%PDF-1.') >= 0 else None
        if v17:                                       # PDF 1.0–1.3: only the version line changes (eCTD takes 1.4–1.7)
            meta['converted'] = list(meta.get('converted') or []) + ['pdf_version_1.7']
            data = v17
        sha = self.put_blob(data)
        family = _extract.source_family(filename, data) or ('word' if filename.lower().endswith('.docx') else None)
        if family:                                      # a source file (Word, Excel, PowerPoint, text — old format or new): the PDF the user uploads replaces it
            en, ar = SOURCE_DRAFT[family]
            rep = Report(str(self.blob_path(sha)), [Finding('DOCX-DRAFT', 'warn', en, ar, 'user_fix', 'NP.CAPP.065 v5 general note 4 (PDF)')])
        else:
            tmp = self.root / 'blobs' / f'.check-{uuid.uuid4().hex}.pdf'
            shutil.copyfile(self.blob_path(sha), tmp)
            try:
                rep = pdf_check(str(tmp), doc_class or s.doc_class)
            finally:
                tmp.unlink(missing_ok=True)
        if meta.get('fixed_from'):                    # a repaired / readable copy of a stored document: the verdict on the document it was made from stands
            try:
                src = self.document(meta['fixed_from'])
                for f0 in src.get('findings') or []:
                    if f0.get('rule') == 'DOC-KIND' and src.get('slot_id') == slot_id:
                        rep.findings.insert(0, Finding('DOC-KIND', f0.get('severity', 'block'), f0.get('en', ''), f0.get('ar', ''), f0.get('action', 'move'), f0.get('source', ''), f0.get('extra') or {}))
            except Exception:
                pass
        elif not meta.get('generated') and not meta.get('signed_for') and not meta.get('amended_from'):      # the kind rule: is this file the document the item expects? (PDF, image or Word)
            try:
                kc = _extract.kind_check(s.req_id, filename, data, known_kind=kind or meta.get('kind'), pack=self.pack(self.dossier(did)['pack']))
            except Exception:
                kc = {'ok': True}
            if not kc.get('ok'):
                home = next((x.slot_id for x in slots.values() if x.req_id in kc['homes'] and x.active), None)
                home_title = next((x.title for x in slots.values() if x.slot_id == home), None)
                kn = kc.get('kind_name') or {'en': kc['kind'], 'ar': kc['kind']}
                rep.findings.insert(0, Finding(
                    'DOC-KIND', 'block',
                    f"This file reads as a {kn['en']}, not the document this item needs" + (f"; it belongs in {home_title['en']}." if home_title else '.'),
                    f"الملف ده شكله {kn['ar']}، مش المستند المطلوب في البند ده" + (f"؛ مكانه «{home_title['ar']}»." if home_title else '.'),
                    'move' if home else 'user_fix', 'intake kind rule (classify keywords)',
                    {'kind': kc['kind'], 'suggested_slot': home, 'suggested_title': home_title}))
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

    ITEM_META = ('pi_type', 'lang', 'study', 'doc_type', 'eu_country')
    PI_ITEMS = ('M1-09', 'EU-1.3.1')

    def check_item_meta(self, did, slot_id, meta):
        """A document placed or moved into the leaflet item (1.3.1) or a Module 5 item carries what the eCTD writers need — the PI type and
        language, the study — as an upload there does; without them the gate says «ready» and the export fails."""
        s = next((x for x in self.slots(did) if x.slot_id == slot_id), None)
        need = ('pi_type', 'lang') if s and s.req_id in self.PI_ITEMS else ('study', 'doc_type') if s and s.module == 5 else ()
        missing = [k for k in need if not (meta or {}).get(k)]
        if missing:
            raise StoreError('E-META', f"This item needs the document's details first: {', '.join(missing)}.",
                             'البند ده محتاج تفاصيل المستند الأول: ' + ('نوع النشرة ولغتها' if s.req_id in self.PI_ITEMS else 'اسم الدراسة ونوع المستند') + '.',
                             missing=missing)
        if s and s.req_id == 'EU-1.3.1':
            from ..writers.ectd32_eu import default_profile
            v = default_profile().values
            if meta['pi_type'] not in v['pi_types'] or meta['lang'] not in v['languages']:
                raise StoreError('E-META', f"EU 1.3.1: the PI type is one of {', '.join(v['pi_types'])} and the language an EU code (en, de, fr…).",
                                 'بند 1.3.1 الأوروبي: نوع النشرة من ' + '، '.join(v['pi_types']) + ' واللغة كود أوروبي (en، de، fr…).',
                                 missing=['pi_type', 'lang'])

    def move_document(self, did, doc_id, slot_id, extra_meta=None):
        """A misfiled document goes to its own item: a new version there (checked again), the old one withdrawn; blob kept once."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if d['slot_id'] == slot_id:
            return d
        data = self.blob_path(d['sha256']).read_bytes()
        meta = {k: v for k, v in d['meta'].items() if k not in ('signed_for',)} | {'moved_from': d['slot_id']}
        meta |= {k: v for k, v in (extra_meta or {}).items() if k in self.ITEM_META and v}
        self.check_item_meta(did, slot_id, meta)
        new = self.add_document(did, slot_id, d['filename'], data, None, meta)
        self.db.execute("update document set state='withdrawn' where id=?", (doc_id,))
        self.db.commit()
        self.audit(did, 'document.moved', doc=doc_id, to=slot_id, new_doc=new['id'])
        return new

    # ---------------- intake drafts: the wizard's work in progress (fields, files, readings), so a refresh loses nothing
    def draft_save(self, draft_id, state):
        now = time.time()
        self.db.execute('insert into intake_draft(id, state, created, updated) values (?,?,?,?) on conflict(id) do update set state=excluded.state, updated=excluded.updated',
                        (draft_id, json.dumps(state or {}, ensure_ascii=False), now, now))
        self.db.commit()
        return self.draft_get(draft_id)

    def draft_get(self, draft_id):
        r = self.db.execute('select * from intake_draft where id=?', (draft_id,)).fetchone()
        if not r:
            return None
        files = [dict(x) for x in self.db.execute('select filename, sha256, kind, size, added from intake_file where draft_id=? order by added', (draft_id,))]
        return {'id': r['id'], 'state': json.loads(r['state'] or '{}'), 'created': r['created'], 'updated': r['updated'], 'files': files}

    def drafts(self):
        return [{'id': r['id'], 'created': r['created'], 'updated': r['updated'], 'state': json.loads(r['state'] or '{}'),
                 'files': self.db.execute('select count(*) from intake_file where draft_id=?', (r['id'],)).fetchone()[0]}
                for r in self.db.execute('select * from intake_draft order by updated desc')]

    def draft_add_file(self, draft_id, filename, data, kind=None):
        if not self.draft_get(draft_id):
            self.draft_save(draft_id, {})
        sha = self.put_blob(data)
        self.db.execute('insert into intake_file(draft_id, filename, sha256, kind, size, added) values (?,?,?,?,?,?) on conflict(draft_id, filename) do update set sha256=excluded.sha256, kind=excluded.kind, size=excluded.size',
                        (draft_id, filename, sha, kind, len(data), time.time()))
        self.db.execute('update intake_draft set updated=? where id=?', (time.time(), draft_id))
        self.db.commit()
        return {'filename': filename, 'sha256': sha, 'kind': kind, 'size': len(data)}

    def draft_file(self, draft_id, filename):
        r = self.db.execute('select sha256 from intake_file where draft_id=? and filename=?', (draft_id, filename)).fetchone()
        return self.blob_path(r['sha256']).read_bytes() if r else None

    def draft_remove_file(self, draft_id, filename):
        """The file leaves the draft, and the disk too when nothing else uses it (a large scan taken out frees its space at once)."""
        r = self.db.execute('select sha256 from intake_file where draft_id=? and filename=?', (draft_id, filename)).fetchone()
        self.db.execute('delete from intake_file where draft_id=? and filename=?', (draft_id, filename))
        self.db.commit()
        return self.gc_blobs(min_age=0, only={r['sha256']}) if r else {'files': 0, 'bytes': 0}

    def draft_delete(self, draft_id, free=False):
        """The draft goes. `free` (the user discarded it) also removes its files from the disk when nothing else uses them; a draft
        that ended in a project needs no clean-up: its files are the project's now."""
        had = self.db.execute('select count(*) from intake_file where draft_id=?', (draft_id,)).fetchone()[0]
        self.db.execute('delete from intake_file where draft_id=?', (draft_id,))
        self.db.execute('delete from intake_draft where id=?', (draft_id,))
        self.db.commit()
        return self.gc_blobs(min_age=5) if free and had else {'files': 0, 'bytes': 0}

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
            x['note'] = rq.get('level_note')            # where the level comes from when the source does not state it
            x['group'] = rq.get('group')
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
