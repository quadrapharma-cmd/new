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
from ..checks.pdf import check as pdf_check, Finding, Report, status_of
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
create table if not exists doc_text(sha256 text primary key, pages text not null, read real not null);
create table if not exists doc_comment(id text primary key, dossier_id text not null, doc_id text not null, page integer,
  text text not null, author text, created real not null, resolved real, resolved_by text);
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


from ..conditions import VALIDITY_KINDS, LEGALIZE      # the ones EDA asks to be valid at submission; the legalised items
ATTEST_LEGALIZE = set(LEGALIZE)   # legalised: the CPP (Egyptian embassy; an eCPP is exempt), the licence holder's
                                                          # declarations (under licence), storage contract + agency (imported) — NP.CAPP.065 v5
RENEWAL_RX = re.compile(r'(?:تجديد|تحديث|renew|updat)', re.I)
REQUEST_RX = re.compile(r'(?:request|application|receipt|طلب|إيصال|ايصال)', re.I)
PRICE_CERT_RX = re.compile(r'(?:pricing certificate|price certificate|شهادة\s*(?:ال)?تسعير|سعر\s*البيع\s*للجمهور)', re.I)
RETEST_RX = re.compile(r'(?:re-?test|إعادة\s*(?:ال)?(?:تحليل|اختبار))[^\n]{0,30}\d', re.I)


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
    (5, 'a sequence keeps its receipt once submitted', ["alter table submission add column receipt text not null default '{}'"]),
]


def _line_with(pages, page, text):
    """The line of `page` that holds `text` (a changed word in its sentence), or None."""
    try:
        lines = (pages[int(page) - 1] or '').splitlines()
    except (TypeError, ValueError, IndexError):
        return None
    want = ' '.join(str(text).split())
    for ln in lines:
        ln = ' '.join(ln.split())
        if want and want in ln:
            return ln[:300]
    return None


class StoreError(ValueError):
    def __init__(self, code, en, ar, **extra):
        self.code, self.en, self.ar, self.extra = code, en, ar, extra
        super().__init__(f'{code}: {en}')


WORD_ITEMS = {'M1-09'}        # NP.CAPP.065 v5 1.1.9: the proposed SmPC and PIL, Arabic and English, in Word
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

    def attest(self, did, slot_id, answer):
        """The answer to the item's one question (signed and stamped / legalised): 'yes', or 'no' — «not yet», which blocks the export."""
        if answer not in ('yes', 'no'):
            raise StoreError('E-ATTEST', 'The answer is yes or no.', 'الإجابة نعم أو لأ.')
        if slot_id not in {s.slot_id for s in self.slots(did)}:
            raise StoreError('E-SLOT', f'Unknown requirement slot {slot_id}.', 'بند غير معروف.')
        d = self.dossier(did)
        data = d.get('data') or {}
        data.setdefault('attest', {})[slot_id] = {'answer': answer, 'at': time.time(), 'by': ACTOR.get()}
        self.db.execute('update dossier set data=? where id=?', (json.dumps(data, ensure_ascii=False), did))
        self.db.commit()
        self.audit(did, 'item.attested', slot=slot_id, answer=answer)
        return data['attest'][slot_id]

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
        return out + self.duplicates(did, d)

    def duplicates(self, did, d=None):
        """The same file (same SHA-256) in more than one item: for an imported product in Egypt, in two modules, it stops the
        submission (NP.CAPP.065 v5 general note 3); otherwise a note."""
        d = d or self.dossier(did)
        egypt = self.pack(d['pack']).egypt
        imported = egypt and (d['profile'] or {}).get('origin') == 'imported'
        slots = {s.slot_id: s for s in self.slots(did) if s.active}
        by_sha = {}
        for doc in self.documents(did):
            if doc['slot_id'] in slots and not doc['meta'].get('external'):
                by_sha.setdefault(doc['sha256'], []).append(doc)
        out = []
        for docs in by_sha.values():
            sids = sorted({x['slot_id'] for x in docs}, key=lambda s: (slots[s].module, s))
            if len({slots[s].req_id for s in sids}) < 2:
                continue                                 # one requirement per active substance: the same certificate for two substances
            where = ', '.join(slots[s].ctd for s in sids)
            block = imported and len({slots[s].module for s in sids}) > 1
            name = docs[0]['filename']
            out.append({'id': 'XC-DUP', 'severity': 'block' if block else 'warn', 'slots': sids, 'action': 'move' if block else 'none', 'needs': [],
                        'en': f'The same file («{name}») is in {len(sids)} items: {where}.' + (
                            ' An imported product does not submit a document already given in another module: keep it in one item and withdraw it from the others.'
                            if block else ' Fine if it serves each of them; otherwise keep it in one.'),
                        'ar': f'نفس الملف («{name}») موجود في {len(sids)} بنود: {where}.' + (
                            ' المنتج المستورد ما يقدّمش مستند متقدّم في موديول تاني: سيبه في بند واحد واسحبه من الباقي.'
                            if block else ' مفيش مشكلة لو بيخدم كل بند فيهم؛ وإلا سيبه في بند واحد.'),
                        'source': 'NP.CAPP.065 v5 general note 3' if egypt else 'Consistency across the dossier (general practice)'})
        return out

    # ---------------- documents
    def refuse_without_text(self, filename, data):
        """NP.CAPP.065 v5 general note 4 asks every document as a scanned and searchable PDF. A file without text of its own (a PDF whose
        pages are images only, an image) is no longer refused (the owner, 13/11/2026): it is kept, PdfCraft reads it (OCR, Arabic and
        English) and makes it searchable as a fix; its finding (NTA065-N4) says so, or — where PdfCraft is not — what to do. Kept as a
        no-op so the callers stay as they were."""
        return None

    def as_pdf(self, filename, data):
        """An image uploaded as a document becomes a PDF page here (PdfCraft), so the checks, the reading and the fixes take it like
        any scan: (filename, data, converted?)."""
        from .. import extract as _extract, pdfcraft as _pc
        if data[:5] == b'%PDF-' or _extract.has_text(filename, data) != 'image' or not _pc.available():
            return filename, data, False
        pdf = _pc.image_to_pdf(data, filename)
        if not pdf:
            return filename, data, False
        stem = filename.rsplit('.', 1)[0] if '.' in filename else filename
        return f'{stem}.pdf', pdf, True

    def add_document(self, did, slot_id, filename, data, title=None, meta=None, supersede=None, doc_class=None, kind=None):
        """kind: the kind an earlier reading gave this file (the wizard's) — the kind rule uses it when the file's own words say nothing.
        A file without text is kept (its finding says how it becomes searchable); an image becomes a PDF page; a PDF 1.0–1.3 is stored with its version line set to 1.7 (fixes.set_version_17:
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
        given_sha = _extract._sha(data)
        if not meta.get('fixed_from') and not meta.get('external') and not meta.get('imported'):
            given = filename
            filename, data, made = self.as_pdf(filename, data)              # a photo or an image file: a PDF page (PdfCraft)
            if made:
                meta['converted'] = list(meta.get('converted') or []) + ['image_to_pdf']
                meta.setdefault('original_name', given)
        v17 = _fixes.set_version_17(data) if data[:1024].find(b'%PDF-1.') >= 0 else None
        if v17:                                       # PDF 1.0–1.3: only the version line changes (eCTD takes 1.4–1.7)
            meta['converted'] = list(meta.get('converted') or []) + ['pdf_version_1.7']
            data = v17
        sha = self.put_blob(data)
        if sha != given_sha:                          # the same pages under a new version line: the page's reading of a scan goes with them
            _extract.carry_browser_reading(given_sha, data)
        family = _extract.source_family(filename, data) or ('word' if filename.lower().endswith('.docx') else None)
        if family == 'word' and s.req_id in WORD_ITEMS:  # the format the item asks: the document itself
            rep = Report(str(self.blob_path(sha)), [Finding(
                'ECTD-WORD', 'warn', 'The One Submission takes the proposed leaflet in Word (NP.CAPP.065 v5 1.1.9); an eCTD takes it as PDF — '
                'the export converts it, or add its PDF to this item.',
                'الـ One Submission بياخد النشرة المقترحة Word (NP.CAPP.065 v5 بند 1.1.9)؛ الـ eCTD بياخدها PDF — التصدير بيحوّلها، أو ضيف الـ PDF '
                'بتاعها في البند ده.', 'none', 'NP.CAPP.065 v5 1.1.9; EG eCTD TG draft')])
        elif family:                                      # a source file (Word, Excel, PowerPoint, text — old format or new): the PDF the user uploads replaces it
            en, ar = SOURCE_DRAFT[family]
            rep = Report(str(self.blob_path(sha)), [Finding('DOCX-DRAFT', 'warn', en, ar, 'user_fix', 'NP.CAPP.065 v5 general note 4 (PDF)')])
        elif data[:5] != b'%PDF-' and _extract.has_text(filename, data) == 'image':   # an image PdfCraft could not make a PDF page here
            from ..checks.pdf import NO_TEXT_IMAGE_EN, NO_TEXT_IMAGE_AR
            rep = Report(str(self.blob_path(sha)), [Finding('NTA065-N4', 'block', NO_TEXT_IMAGE_EN, NO_TEXT_IMAGE_AR, 'user_fix',
                                                            'NP.CAPP.065 v5 general note 4')])
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
        txt = ''
        if not meta.get('generated') and not meta.get('external'):
            try:
                txt = _extract.read_text(filename, data, max_pages=3)['text']      # read once: the reading is kept by the file's SHA-256
            except Exception:
                txt = ''
        txt_kind = _extract.content_kind(txt) if txt else 'other'
        renewal = (s.req_id == 'M1-05' and bool(RENEWAL_RX.search(txt)) and bool(REQUEST_RX.search(txt[:1500]))
                   and not PRICE_CERT_RX.search(txt))          # a request (or its receipt) for renewing the price — not the certificate itself
        if renewal:                                    # the request for updating an expired pricing certificate (NP.CAPP.065 v5 1.1.5)
            meta['renewal_request'] = True
        if meta.get('fixed_from'):
            pass
        elif renewal:
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
        if txt and txt_kind in VALIDITY_KINDS and not meta.get('valid_until'):
            vu = ((_extract.fields_for(txt_kind, filename, txt).get('document') or {}).get('valid_until'))
            try:
                date.fromisoformat(vu or '')
                meta['valid_until'], meta['valid_until_read'] = vu, True        # read from the document; the expiry rule does the rest
            except ValueError:
                pass
        if txt and txt_kind == 'coa' and s.req_id == 'M1-35':                     # an API's CoA: batch, manufacture, expiry (or retest)
            b = (_extract.fields_for('coa', filename, txt).get('batches') or [{}])[0]
            gaps = [(en, ar) for en, ar, ok in (('batch number', 'رقم التشغيلة', b.get('no')), ('manufacturing date', 'تاريخ التصنيع', b.get('date')),
                                                ('expiry or retest date', 'تاريخ الانتهاء أو إعادة التحليل', b.get('expiry') or RETEST_RX.search(txt)))
                    if not ok]
            if gaps:
                rep.findings.append(Finding('COA-DATA', 'warn',
                                            'This CoA does not show: ' + ', '.join(g[0] for g in gaps) + ' — EDA asks for the batch number, the '
                                            'manufacturing and the expiry dates (NP.CAPP.065 v5 1.2.3.1).',
                                            'شهادة التحليل مش ظاهر فيها: ' + '، '.join(g[1] for g in gaps) + ' — الهيئة طالبة رقم التشغيلة وتاريخ '
                                            'التصنيع والانتهاء (NP.CAPP.065 v5 بند 1.2.3.1).', 'user_fix', 'NP.CAPP.065 v5 1.2.3.1'))
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
        s = next((x for x in self.slots(did) if x.slot_id == d['slot_id']), None)
        dz = self.dossier(did)
        fixes.DOC_INFO = {'/Title': d['title'] or (s.title['en'] if s else d['filename']), '/Subject': f"{s.ctd} {s.title['en']}" if s else '',
                          '/Author': (dz['envelope'] or {}).get('applicant') or '', '/Keywords': (dz['product'] or {}).get('name') or ''}
        r = fixes.apply(self.blob_path(d['sha256']), d['findings'], d['doc_class'])
        new = None
        if r['data']:
            from .. import extract as _extract
            _extract.carry_browser_reading(d['sha256'], r['data'])      # a fix keeps the pages: the page's reading of a scan goes with them
            new = self.add_document(did, d['slot_id'], d['filename'], r['data'], d['title'],
                                    {**d['meta'], 'fixed_from': doc_id, 'fixes': [x['op'] for x in r['done']]},
                                    supersede=doc_id, doc_class=d['doc_class'])
        self.audit(did, 'document.fixed' if new else 'document.fix_refused', doc=doc_id, new=new and new['id'],
                   done=[x['op'] for x in r['done']], refused=[x['op'] for x in r['refused']])
        return {'document': new, 'done': r['done'], 'refused': r['refused']}

    def search(self, did, q, budget=6.0):
        """Where the dossier's documents say q: [{doc, item, matches: [{page, snippet, start, length}]}]. Each file's pages are read once
        and kept (doc_text); files not read yet are read within `budget` seconds — `pending` says how many are left for the next call."""
        from .. import search as _search
        rx = _search.pattern(q)
        if rx is None or len(q.strip()) < 2:
            raise StoreError('E-QUERY', 'Type at least two characters.', 'اكتب حرفين على الأقل.')
        slots = {s.slot_id: s for s in self.slots(did)}
        docs = [x for x in self.documents(did) if not x['meta'].get('external')]
        keys = {_search.text_key(x['sha256']): x['sha256'] for x in docs}
        known = {keys[r['sha256']]: json.loads(r['pages']) for r in self.db.execute(
            'select sha256, pages from doc_text where sha256 in (%s)' % ','.join('?' * len(keys)), list(keys)).fetchall()} if docs else {}
        t0, pending, hits, n = time.time(), 0, [], 0
        for x in docs:
            pages = known.get(x['sha256'])
            if pages is None:
                if time.time() - t0 > budget:
                    pending += 1
                    continue
                pages = _search.pages_of(x['filename'], self.blob_path(x['sha256']).read_bytes())
                known[x['sha256']] = pages
                self.db.execute('insert or replace into doc_text values (?,?,?)', (_search.text_key(x['sha256']), json.dumps(pages, ensure_ascii=False), time.time()))
                self.db.commit()
            found = _search.find(pages, rx)
            if found and n < _search.MAX_HITS:
                s = slots.get(x['slot_id'])
                hits.append({'doc_id': x['id'], 'filename': x['filename'], 'version': x['version'], 'slot_id': x['slot_id'],
                             'ctd': s.ctd if s else '', 'title': s.title if s else {'en': x['title'], 'ar': x['title']},
                             'pages': len(pages), 'matches': found})
                n += len(found)
        return {'q': q, 'hits': hits, 'matches': n, 'searched': len(docs) - pending, 'pending': pending, 'total': len(docs)}

    def copy_documents(self, did, src, scope='m2-5'):
        """The current documents of dossier `src` into this dossier's matching items: 'm2-5' (Modules 2–5 — the same in every country),
        'api' (only the active substances' own sections, 3.2.S, matched by substance and manufacturer). Module 1 is never copied: it
        belongs to its authority. An item that has a document already keeps it (nothing is overwritten); each copy is checked again."""
        if scope not in ('m2-5', 'api'):
            raise StoreError('E-SCOPE', 'Copy Modules 2–5, or the active substances\' sections.', 'انسخ موديول 2–5، أو أقسام المواد الفعالة.')
        if src == did:
            raise StoreError('E-SAME', 'Choose another dossier to copy from.', 'اختار ملف تاني تنسخ منه.')
        self.dossier(src)
        mine = {s.slot_id: s for s in self.slots(did) if s.active}
        theirs = [s for s in self.slots(src) if s.active and s.module != 1]
        key = lambda s: (s.req_id, (s.item or {}).get('name', '').lower(), (s.item or {}).get('manufacturer', '').lower())
        mine_by = {key(s): s for s in mine.values() if s.module != 1}
        copied, kept, skipped = [], [], []
        for s in theirs:
            if scope == 'api' and not s.slot_id.startswith('S-'):
                continue
            t = mine.get(s.slot_id) or mine_by.get(key(s))
            docs = self.documents(src, s.slot_id)
            if not docs:
                continue
            if not t:
                skipped.extend(d['filename'] for d in docs)
                continue
            if self.documents(did, t.slot_id):
                kept.append(t.slot_id)
                continue
            for d in docs:
                if d['meta'].get('external'):
                    continue
                meta = {k: v for k, v in d['meta'].items() if k in self.ITEM_META or k in ('generated', 'draft_unsigned')}
                new = self.add_document(did, t.slot_id, d['filename'], self.blob_path(d['sha256']).read_bytes(), d['title'],
                                        dict(meta, copied_from={'dossier': src, 'doc': d['id']}), doc_class=d['doc_class'])
                copied.append({'slot_id': t.slot_id, 'doc_id': new['id'], 'filename': new['filename']})
        self.audit(did, 'documents.copied', source=src, scope=scope, copied=len(copied), kept=kept)
        return {'copied': copied, 'kept': kept, 'not_here': skipped}

    def import_ectd(self, did, files):
        """An application's eCTD 3.2.2 sequences into this dossier (updates list, item 24): documents into their items, the sequences
        into the submitted history (frozen), their folders kept for the lifecycle. A leaf whose item this dossier does not have goes to
        the unplaced box."""
        import posixpath, tempfile
        from .. import importer
        from ..assistant import storage as _storage
        from ..validators.package import write_files, sequences
        tmp = Path(tempfile.mkdtemp())
        try:
            write_files(files, tmp)
            seqs = sequences(tmp)
            if not seqs:
                raise StoreError('E-NO-SEQUENCE', 'No eCTD sequence in the file: a four-digit folder holding its index.xml.',
                                 'مفيش تسلسل eCTD في الملف: فولدر من 4 أرقام جواه index.xml.')
            hist = self.history(did, 'ectd32')
            clash = sorted({s.name for s in seqs} & {str(h['seq']) for h in hist})
            if clash:
                raise StoreError('E-SEQ-EXISTS', f'This dossier has sequence(s) {", ".join(clash)} already.', f'الملف ده فيه التسلسل {"، ".join(clash)} أصلًا.')
            maps = importer.Maps()
            slots = [s for s in self.slots(did) if s.active]
            leafdoc = {(str(h['seq']), lf['leaf_id']): lf['doc_id'] for h in hist for lf in h['leaves']}
            lc = self.root / 'lifecycle' / did / 'ectd-3.2.2'
            reads = [(s, importer.read_sequence(s, maps)) for s in seqs]
            ids = {r['envelope'].get('identifier') for _, r in reads} - {None}
            mine = (self.dossier(did).get('envelope') or {}).get('application_uuid')
            if len(ids) > 1 or (hist and ids and mine not in ids):
                raise StoreError('E-UUID', f'These sequences belong to another application (UUID {", ".join(sorted(ids))}); this dossier\'s is {mine}.',
                                 f'التسلسلات دي لطلب تاني (UUID {"، ".join(sorted(ids))})، والملف ده رقمه {mine}.')
            if ids and mine not in ids:                  # the application's own UUID from now on: the next sequence carries it, character for character
                env0 = dict(self.dossier(did).get('envelope') or {}, application_uuid=ids.pop())
                self.db.execute('update dossier set envelope=? where id=?', (json.dumps(env0, ensure_ascii=False), did))
                self.db.commit()
            report = {'sequences': [], 'placed': 0, 'unplaced': [], 'check': []}
            used = set()
            for s, r in reads:
                rows = []
                for lf in r['leaves']:
                    node = lf['node'] or ''
                    seqr, lid = importer.replaced_leaf(lf.get('modified'))
                    if (lf.get('href') or '').lower().endswith('.xml'):
                        continue                         # the regional index itself (m1/eg/eg-regional.xml): not a document
                    if node == '1.0' and (posixpath.basename(lf['href'] or '').lower().startswith('tracking') or (lf['title'] or '').lower().startswith('tracking table')):
                        rows.append({'doc_id': None, 'key': [node, '', '', '', '', 'tracking'], 'leaf_id': lf['leaf_id'], 'href': lf['href'], 'xml': lf['xml'],
                                     'op': lf['op'], 'replaces': lid, 'node': node, 'title': lf['title']})
                        continue                         # the tracking table: the program makes it again for every sequence
                    cands = [x for x in slots if node and node in (x.ectd or [])]
                    for attr, field in (('substance', 'name'), ('manufacturer', 'manufacturer')):
                        if lf.get(attr) and len(cands) > 1:
                            v = lf[attr].lower()
                            cands = [x for x in cands if (x.item or {}).get(field, '').lower() in (v, *v.split())] or cands
                    if len(cands) > 1:                   # several items share this place: the leaf's title names the item, else the next free one
                        tl = (lf['title'] or '').strip().lower()
                        named = [x for x in cands if tl and tl in ((x.title or {}).get('en', '').strip().lower(), (x.title or {}).get('ar', '').strip())]
                        if named:
                            cands = named
                        else:
                            cands = [x for x in cands if x.slot_id not in used] or cands
                            report['check'].append({'sequence': s.name, 'href': lf['href'], 'slot_id': cands[0].slot_id,
                                                    'why': f'{node} holds several items: placed by order — check'})
                    slot = cands[0] if cands else None
                    key = [node, (slot.item or {}).get('name', '') if slot and slot.item else lf.get('substance', '') or '',
                           (slot.item or {}).get('manufacturer', '') if slot and slot.item else lf.get('manufacturer', '') or '',
                           lf.get('pi_type', ''), lf.get('lang', '')] + ([lf['country']] if lf.get('country') else [])
                    if lf['op'] == 'delete':
                        old = leafdoc.get((seqr, lid))
                        if old:
                            try:
                                self.withdraw(did, old, 'deleted in sequence ' + s.name)
                            except StoreError:
                                pass
                        rows.append({'doc_id': old, 'key': key, 'leaf_id': lf['leaf_id'], 'href': None, 'xml': lf['xml'], 'op': 'delete',
                                     'replaces': lid, 'node': node, 'title': lf['title']})
                        continue
                    f = s / lf['href']
                    if not f.is_file():
                        report['unplaced'].append({'sequence': s.name, 'href': lf['href'], 'why': 'missing file'})
                        continue
                    meta = {k: lf[k] for k in ('pi_type', 'lang', 'study') if lf.get(k)}
                    if lf.get('country'):
                        meta['eu_country'] = lf['country']
                    meta['imported'] = {'seq': s.name, 'leaf_id': lf['leaf_id']}
                    if slot:
                        prev = leafdoc.get((seqr, lid)) if lf['op'] == 'replace' else None
                        sup = prev if prev and self.document(prev)['state'] == 'current' else None
                        doc = self.add_document(did, slot.slot_id, f.name, f.read_bytes(), lf['title'] or None, meta, supersede=sup)
                        report['placed'] += 1
                        used.add(slot.slot_id)
                    else:
                        try:
                            doc = _storage.stage_document(self, did, f.name, f.read_bytes(), lf['title'] or None, meta={**meta, 'staged_by': 'import'})
                            why = f'no item for {node or "this place"}'
                        except StoreError as e:          # e.g. a scan without text: the leaf stays in the history, the file is not kept
                            doc, why = {'id': None}, e.en
                        report['unplaced'].append({'sequence': s.name, 'href': lf['href'], 'why': why})
                    leafdoc[(s.name, lf['leaf_id'])] = doc['id']
                    rows.append({'doc_id': doc['id'], 'key': key, 'leaf_id': lf['leaf_id'], 'href': lf['href'], 'xml': lf['xml'], 'op': lf['op'],
                                 'replaces': lid, 'node': node, 'title': lf['title']})
                dest = lc / s.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(s, dest)
                e = r['envelope']
                env = {'type': e.get('type') or 'imported', 'unit': e.get('unit') or '', 'description': e.get('description') or 'Imported sequence',
                       'tracking': e.get('tracking') or ''}
                self.record_submission(did, 'ectd32', s.name, e.get('related') or s.name, None, env, rows, str(dest))
                self.mark_submitted(did, 'ectd32', s.name, {'note': 'imported'})
                report['sequences'].append({'sequence': s.name, 'region': r['region'], 'leaves': len(rows)})
            self.audit(did, 'ectd.imported', sequences=[x['sequence'] for x in report['sequences']], placed=report['placed'],
                       unplaced=len(report['unplaced']))
            return report
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def reference_document(self, did, slot_id, output, seq, href):
        """An item's document taken from an earlier sequence of this application: the file it was sent as is kept for the checks and
        the search, and the next sequence refers to it there instead of sending it again."""
        h = next((x for x in self.history(did, output) if str(x['seq']) == str(seq)), None)
        if not h or not h['frozen']:
            raise StoreError('E-REF', 'Refer only to a sequence that was submitted.', 'الإحالة بتبقى لتسلسل اتقدّم بس.')
        if not any(lf.get('href') == href for lf in h['leaves']):
            raise StoreError('E-REF', 'That file is not a leaf of that sequence.', 'الملف ده مش من مستندات التسلسل ده.')
        f = Path(h['path']) / href
        if not f.is_file():
            raise StoreError('E-REF', 'The sequence\'s file is not in this workspace.', 'ملف التسلسل مش موجود في مساحة العمل دي.')
        slot = next((s for s in self.slots(did) if s.slot_id == slot_id), None)
        if not slot or not slot.active:
            raise StoreError('E-SLOT-INACTIVE', 'This item is not required for this product.', 'البند ده مش مطلوب للمنتج ده.')
        old = next((lf for lf in h['leaves'] if lf.get('href') == href), {})
        title = None
        try:
            title = self.document(old['doc_id'])['title'] if old.get('doc_id') else None
        except StoreError:
            pass
        doc = self.add_document(did, slot_id, f.name, f.read_bytes(), title,
                                {'reference': {'output': output, 'seq': str(seq), 'href': href}})
        self.audit(did, 'document.referenced', slot=slot_id, output=output, seq=str(seq), href=href, doc=doc['id'])
        return doc

    def views(self, did, output='ectd32'):
        """The submitted dossier four ways: cumulative, by sequence, by activity, by study."""
        from ..lifecycle import current_view
        hist = self.history(did, output)
        docs = {}

        def leaf(lf, seq):
            if lf['doc_id'] not in docs:
                try:
                    docs[lf['doc_id']] = self.document(lf['doc_id'])
                except StoreError:
                    docs[lf['doc_id']] = None
            d = docs[lf['doc_id']] or {}
            key = list(lf.get('key') or [])
            return {'seq': str(seq), 'op': lf.get('op'), 'node': key[0] if key else '', 'href': lf.get('href'), 'title': d.get('title') or lf.get('href'),
                    'filename': d.get('filename'), 'study': (d.get('meta') or {}).get('study'), 'doc_id': lf['doc_id']}
        cumulative = sorted((leaf(lf, lf['seq']) for lf in current_view(hist).values()), key=lambda x: (x['node'], x['seq']))
        by_seq = [{'seq': str(h['seq']), 'type': h['envelope'].get('type'), 'unit': h['envelope'].get('unit'), 'description': h['envelope'].get('description'),
                   'frozen': h['frozen'], 'leaves': [leaf(lf, h['seq']) for lf in h['leaves']]} for h in hist]
        acts = {}
        for h in hist:
            a = str(h.get('activity') or h['seq'])
            g = acts.setdefault(a, {'activity': a, 'type': h['envelope'].get('type'), 'description': h['envelope'].get('description'), 'sequences': []})
            g['sequences'].append({'seq': str(h['seq']), 'unit': h['envelope'].get('unit'), 'frozen': h['frozen'], 'documents': len(h['leaves'])})
        studies = {}
        for x in cumulative:
            if x['node'][:1] in ('4', '5'):
                studies.setdefault(x['study'] or '', []).append(x)
        return {'output': output, 'cumulative': cumulative, 'sequences': by_seq, 'activities': list(acts.values()),
                'studies': [{'study': k, 'leaves': v} for k, v in sorted(studies.items())]}

    def comments(self, did, doc_id=None, open_only=False):
        q, args = 'select * from doc_comment where dossier_id=?', [did]
        if doc_id:
            q, args = q + ' and doc_id=?', args + [doc_id]
        if open_only:
            q += ' and resolved is null'
        return [dict(r) for r in self.db.execute(q + ' order by created', args).fetchall()]

    def add_comment(self, did, doc_id, text, page=None):
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if not text or not text.strip():
            raise StoreError('E-TEXT', 'Write the note.', 'اكتب الملاحظة.')
        cid = str(uuid.uuid4())
        self.db.execute('insert into doc_comment(id, dossier_id, doc_id, page, text, author, created) values (?,?,?,?,?,?,?)',
                        (cid, did, doc_id, int(page) if page else None, text.strip()[:4000], ACTOR.get(), time.time()))
        self.db.commit()
        self.audit(did, 'comment.added', doc=doc_id, comment=cid)
        return dict(self.db.execute('select * from doc_comment where id=?', (cid,)).fetchone())

    def resolve_comment(self, did, cid, resolved=True):
        r = self.db.execute('select * from doc_comment where id=? and dossier_id=?', (cid, did)).fetchone()
        if not r:
            raise StoreError('E-NOT-FOUND', 'Note not found.', 'الملاحظة مش موجودة.')
        self.db.execute('update doc_comment set resolved=?, resolved_by=? where id=?',
                        (time.time() if resolved else None, ACTOR.get() if resolved else None, cid))
        self.db.commit()
        self.audit(did, 'comment.resolved' if resolved else 'comment.reopened', comment=cid)
        return dict(self.db.execute('select * from doc_comment where id=?', (cid,)).fetchone())

    def text_pages(self, doc):
        """A document's pages of text, read once and kept (the same store the search uses)."""
        from .. import search as _search
        key = _search.text_key(doc['sha256'])
        r = self.db.execute('select pages from doc_text where sha256=?', (key,)).fetchone()
        if r:
            return json.loads(r['pages'])
        pages = _search.pages_of(doc['filename'], self.blob_path(doc['sha256']).read_bytes())
        self.db.execute('insert or replace into doc_text values (?,?,?)', (key, json.dumps(pages, ensure_ascii=False), time.time()))
        self.db.commit()
        return pages

    def compare_versions(self, did, doc_id, against=None):
        """A document against the version it replaced (or `against`): {old, new, changes: [{op, text, page}]}."""
        from .. import search as _search
        new = self.document(doc_id)
        if new['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if against:
            old = self.document(against)
            if old['dossier_id'] != did:
                raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        else:
            r = self.db.execute("select id from document where dossier_id=? and slot_id=? and version<? and state='superseded' "
                                'order by version desc limit 1', (did, new['slot_id'], new['version'])).fetchone()
            if not r:
                raise StoreError('E-NO-VERSION', 'This document replaced no earlier version.', 'المستند ده ما حلّش محل نسخة قبله.')
            old = self.document(r['id'])
        brief = lambda d: {k: d[k] for k in ('id', 'filename', 'version', 'created')}
        a, b = self._blob_or_none(old), self._blob_or_none(new)
        from .. import pdfcraft
        if a and b and a[:5] == b[:5] == b'%PDF-' and pdfcraft.available():
            try:                                         # PdfCraft: word by word, each change with its page and its place on it
                r = pdfcraft.compare(a, b, limit=400)
                pa, pb = self.text_pages(old), self.text_pages(new)
                ch = []
                for c in r.get('changes') or []:
                    o, n = c.get('old') or {}, c.get('new') or {}
                    if o.get('text'):
                        ch.append({'op': 'removed', 'text': o['text'], 'page': o.get('page'), 'rects': o.get('rects') or [],
                                   'line': _line_with(pa, o.get('page'), o['text'])})
                    if n.get('text'):
                        ch.append({'op': 'added', 'text': n['text'], 'page': n.get('page'), 'rects': n.get('rects') or [],
                                   'line': _line_with(pb, n.get('page'), n['text'])})
                return {'old': brief(old), 'new': brief(new), 'changes': ch, 'same': not ch, 'engine': 'pdfcraft', 'marked': True}
            except pdfcraft.PdfCraftError:
                pass
        ch = _search.diff(self.text_pages(old), self.text_pages(new))
        return {'old': brief(old), 'new': brief(new), 'changes': ch, 'same': not ch, 'engine': 'text', 'marked': False}

    def _blob_or_none(self, d):
        try:
            return self.blob_path(d['sha256']).read_bytes() if d.get('sha256') else None
        except OSError:
            return None

    def compare_marked(self, did, doc_id, against=None):
        """The newer version with what changed from the older one marked on its pages (PdfCraft: blue replaced, green inserted, red
        deleted) — a copy to read, never stored as a version."""
        from .. import pdfcraft
        info = self.compare_versions(did, doc_id, against)
        if not info.get('marked'):
            raise StoreError('E-PDFCRAFT', 'A marked copy needs PdfCraft and two PDF versions.', 'النسخة المتعلّم عليها محتاجة PdfCraft ونسختين PDF.')
        old, new = self.document(info['old']['id']), self.document(info['new']['id'])
        return pdfcraft.compare(self._blob_or_none(old), self._blob_or_none(new), marked=True)['marked'], new['filename']

    def split_proposal(self, did, doc_id):
        """Where the program would cut a file that holds several documents (the person confirms or moves the cuts)."""
        from .. import pages as _pages
        d = self._current_pdf(did, doc_id)
        return _pages.propose(self.blob_path(d['sha256']).read_bytes(), self.pack(self.dossier(did)['pack']))

    def split_document(self, did, doc_id, starts):
        """Cut a file where documents start (pages, 1-based): each part goes to the unplaced box with its own reading, the file it came
        from is withdrawn (kept in the history)."""
        from .. import pages as _pages
        from ..assistant import storage as _storage
        d = self._current_pdf(did, doc_id)
        data = self.blob_path(d['sha256']).read_bytes()
        n = _pages.count(data)
        ranges = _pages.ranges_from_starts(starts or [], n)
        if len(ranges) < 2:
            raise StoreError('E-SPLIT', 'Choose where at least one more document starts.', 'اختار صفحة واحدة على الأقل بيبدأ عندها مستند تاني.')
        stem = d['filename'].rsplit('.', 1)[0] if '.' in d['filename'] else d['filename']
        parts = []
        for (a, b), blob in zip(ranges, _pages.split(data, ranges)):
            name = f'{stem} (p{a}-{b}).pdf' if a != b else f'{stem} (p{a}).pdf'
            parts.append(_storage.stage_document(self, did, name, blob, meta={'split_from': doc_id, 'pages': [a, b], 'staged_by': 'split'}))
        self.db.execute("update document set state='withdrawn' where id=?", (doc_id,))
        self.db.commit()
        self.audit(did, 'document.split', doc=doc_id, parts=[p['id'] for p in parts], ranges=ranges)
        return {'parts': parts}

    def merge_documents(self, did, slot_id, doc_ids):
        """One document of the item's PDFs, in the order given (a document scanned as separate files); the merged ones are withdrawn."""
        from .. import pages as _pages
        if len(doc_ids) < 2 or len(set(doc_ids)) != len(doc_ids):
            raise StoreError('E-MERGE', 'Choose two documents or more of this item.', 'اختار مستندين أو أكتر من البند ده.')
        docs = [self._current_pdf(did, x) for x in doc_ids]
        if any(x['slot_id'] != slot_id for x in docs):
            raise StoreError('E-MERGE', 'The documents to join must all be in this item.', 'المستندات اللي هتتدمج لازم تكون كلها في البند ده.')
        blob = _pages.merge([self.blob_path(x['sha256']).read_bytes() for x in docs])
        first = docs[0]
        new = self.add_document(did, slot_id, first['filename'], blob, first['title'],
                                {**first['meta'], 'merged_from': doc_ids}, doc_class=first['doc_class'])
        self.db.execute('update document set state=\'withdrawn\' where id in (%s)' % ','.join('?' * len(doc_ids)), doc_ids)
        self.db.commit()
        self.audit(did, 'document.merged', docs=doc_ids, new=new['id'])
        return {'document': new}

    def _current_pdf(self, did, doc_id):
        d = self.document(doc_id)
        if d['dossier_id'] != did or d['state'] != 'current':
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if self.blob_path(d['sha256']).read_bytes()[:5] != b'%PDF-':
            raise StoreError('E-NOT-PDF', 'Pages are split and joined in PDF files only.', 'التقسيم والدمج بيتعملوا في ملفات PDF بس.')
        return d

    def _pdfcraft(self):
        from .. import pdfcraft
        if not pdfcraft.available():
            raise StoreError('E-PDFCRAFT', 'This needs PdfCraft, the PDF engine of the desktop and company editions (not in the browser edition).',
                             'دي محتاجة PdfCraft، محرك الـ PDF في نسخة الكمبيوتر ونسخة الشركة (مش موجود في نسخة المتصفح).')
        return pdfcraft

    def page_image(self, did, doc_id, page, dpi=96):
        """One page drawn as a PNG (PdfCraft) — the viewer's page."""
        pc = self._pdfcraft()
        d = self._current_pdf(did, doc_id)
        try:
            png = pc.page_png(self.blob_path(d['sha256']).read_bytes(), int(page), max(24, min(int(dpi), 200)))
        except pc.PdfCraftError as e:
            raise StoreError('E-PAGE', f'The page cannot be drawn: {e}'[:300], 'الصفحة ما ينفعش تترسم.')
        if not png:
            raise StoreError('E-PAGE', 'The page cannot be drawn.', 'الصفحة ما ينفعش تترسم.')
        return png

    def find_in_document(self, did, doc_id, q):
        """Where a phrase is in one document, page by page, with its rectangles (points from the page's top-left) — PdfCraft."""
        pc = self._pdfcraft()
        d = self._current_pdf(did, doc_id)
        if len((q or '').strip()) < 2:
            raise StoreError('E-QUERY', 'Type at least two characters.', 'اكتب حرفين على الأقل.')
        return {'matches': pc.find(self.blob_path(d['sha256']).read_bytes(), q.strip(), limit=200)}

    def pdf_operation(self, did, doc_id, op, **kw):
        """A PdfCraft operation on a company document, stored as a new version (the original kept, superseded):
        redact (real redaction of words), reduce_size (a smaller file), sign (EU: a digital signature with the person's own ID).
        Third-party, EDA and executed documents are evidence: only their issuer changes them (E-LOCKED)."""
        from ..guard import assert_allowed, LockedError
        pc = self._pdfcraft()
        d = self._current_pdf(did, doc_id)
        try:
            assert_allowed(d['doc_class'], {'redact': 'redact', 'reduce_size': 'reduce_size', 'sign': 'edit_text'}[op])
        except LockedError:
            raise StoreError('E-LOCKED', 'Only its issuer may change this document (third-party, EDA or executed) — re-obtain it.',
                             'المستند ده من حق الجهة اللي أصدرته بس تعدّله (جهة خارجية أو الهيئة أو سجل تشغيل) — اطلبه منها.')
        data = self.blob_path(d['sha256']).read_bytes()
        try:
            if op == 'redact':
                words = [w.strip() for w in (kw.get('words') or []) if w and w.strip()]
                if not words:
                    raise StoreError('E-REDACT', 'Give the words or phrases to remove.', 'اكتب الكلمات أو العبارات اللي هتتشال.')
                out, rep = pc.redact(data, words=words)
                note = {'redacted': len(words)}
            elif op == 'reduce_size':
                out, rep = pc.reduce(data)
                if not pc.smaller_enough(data, out):
                    raise StoreError('E-REDUCE', 'The file cannot be made smaller (its images are already at 150 ppi or below).',
                                     'الملف ما ينفعش يصغر أكتر (صوره 150 نقطة/بوصة أو أقل).')
                note = {'reduced': [len(data), len(out)]}
            elif op == 'sign':
                if (self.pack(self.dossier(did)['pack']).ectd_region or '') != 'eu':
                    raise StoreError('E-SIGN-REGION', 'Electronic signatures are not used in the EDA eCTD (draft guidance 2.10.3); signing is offered for the EU, where eIDAS signatures are accepted.',
                                     'التوقيع الإلكتروني مش بيُستخدم في الـ eCTD بتاع الهيئة (المسودة 2.10.3)؛ التوقيع متاح لأوروبا بس، اللي بتقبل توقيعات eIDAS.')
                out = self._sign(pc, data, kw)
                note = {'signed': True}
            else:
                raise StoreError('E-OP', 'Unknown operation.', 'عملية مش معروفة.')
        except pc.PdfCraftError as e:
            raise StoreError('E-PDFCRAFT-OP', f'PdfCraft could not do it: {e}'[:400], 'PdfCraft ما قدرش يعملها.')
        new = self.add_document(did, d['slot_id'], d['filename'], out, d['title'], {**d['meta'], 'pdfcraft': op, 'from': doc_id, **note},
                                supersede=doc_id, doc_class=d['doc_class'])
        self.audit(did, f'document.{op}', doc=doc_id, new=new['id'], **note)
        return {'document': new, **note}

    def page_operation(self, did, doc_id, op, pages, degrees=90, to=None):
        """Turn, remove or move pages (PdfCraft), as a new version (the original kept, superseded). Turning a page changes how it
        shows, not what it says: allowed on every document. Removing or moving pages changes the document: the company's own only."""
        from ..guard import assert_allowed, LockedError
        pc = self._pdfcraft()
        d = self._current_pdf(did, doc_id)
        data = self.blob_path(d['sha256']).read_bytes()
        n = pc.page_count(data) or 0
        pages = sorted({int(x) for x in (pages or []) if 1 <= int(x) <= n})
        if not pages:
            raise StoreError('E-PAGES', f'Choose pages between 1 and {n}.', f'اختار صفحات من 1 لـ {n}.')
        try:
            assert_allowed(d['doc_class'], {'rotate': 'rotate_pages', 'delete': 'remove_pages', 'move': 'move_pages'}[op])
        except KeyError:
            raise StoreError('E-OP', 'Unknown operation.', 'عملية مش معروفة.')
        except LockedError:
            raise StoreError('E-LOCKED', 'Only its issuer may change this document (third-party, EDA or executed) — re-obtain it.',
                             'المستند ده من حق الجهة اللي أصدرته بس تعدّله (جهة خارجية أو الهيئة أو سجل تشغيل) — اطلبه منها.')
        if op == 'delete' and len(pages) >= n:
            raise StoreError('E-PAGES', 'A document keeps at least one page — withdraw it instead.', 'المستند لازم يفضل فيه صفحة على الأقل — اسحبه بدل كده.')
        if op == 'rotate' and int(degrees) % 90:
            raise StoreError('E-PAGES', 'Pages turn by 90, 180 or 270 degrees.', 'الصفحات بتلف 90 أو 180 أو 270 درجة.')
        step = {'rotate': ('page_rotate', {'doc': 1, 'pages': pages, 'degrees': int(degrees)}),
                'delete': ('page_delete', {'doc': 1, 'pages': pages}),
                'move': ('page_move', {'doc': 1, 'pages': pages, 'to': max(1, min(int(to or 1), n))})}[op]
        try:
            _res, out = pc.run([('doc_open', {'path': 'in.pdf'}), step, ('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True})],
                               {'in.pdf': data}, read=('out.pdf',))
        except pc.PdfCraftError as e:
            raise StoreError('E-PDFCRAFT-OP', f'PdfCraft could not do it: {e}'[:400], 'PdfCraft ما قدرش يعملها.')
        note = {'pages_op': op, 'pages': pages, **({'degrees': int(degrees)} if op == 'rotate' else {}), **({'to': int(to or 1)} if op == 'move' else {})}
        new = self.add_document(did, d['slot_id'], d['filename'], out['out.pdf'], d['title'], {**d['meta'], 'pdfcraft': f'pages.{op}', 'from': doc_id},
                                supersede=doc_id, doc_class=d['doc_class'])
        self.audit(did, f'document.pages.{op}', doc=doc_id, new=new['id'], **note)
        return {'document': new, **note}

    def notes_copy(self, did, doc_id):
        """The document with the team's notes on its pages as PDF comments (PdfCraft) — a copy to read or send for review, never a
        version (an eCTD document carries no comments)."""
        pc = self._pdfcraft()
        d = self._current_pdf(did, doc_id)
        data = self.blob_path(d['sha256']).read_bytes()
        n = pc.page_count(data) or 1
        steps, per = [('doc_open', {'path': 'in.pdf'})], {}
        for c in self.comments(did, doc_id):
            p = max(1, min(int(c.get('page') or 1), n))
            k = per[p] = per.get(p, 0) + 1
            steps.append(('comment_add', {'doc': 1, 'page': p, 'type': 'note', 'at': [18.0, 18.0 + 26 * (k - 1)],
                                          'contents': c['text'] + (' (resolved)' if c.get('resolved') else ''), 'author': c.get('author') or 'Dossier Builder',
                                          'color': 'green' if c.get('resolved') else 'yellow'}))
        if len(steps) == 1:
            raise StoreError('E-NO-NOTES', 'This document has no notes yet.', 'المستند ده لسه مالوش ملاحظات.')
        steps.append(('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True}))
        try:
            _res, out = pc.run(steps, {'in.pdf': data}, read=('out.pdf',))
        except pc.PdfCraftError as e:
            raise StoreError('E-PDFCRAFT-OP', f'PdfCraft could not do it: {e}'[:400], 'PdfCraft ما قدرش يعملها.')
        return out['out.pdf'], d['filename']

    def _sign(self, pc, data, kw):
        """Sign with the person's own digital ID (a .p12/.pfx and its password), used for this one call and never kept."""
        p12, password = kw.get('p12'), kw.get('password') or ''
        if not p12:
            raise StoreError('E-SIGN', 'Choose your digital ID (.p12 or .pfx).', 'اختار التوقيع الرقمي بتاعك (.p12 أو .pfx).')
        args = {'doc': 1, 'id': 'id.p12', 'password': password, 'out': 'signed.pdf', 'reason': kw.get('reason') or None,
                'location': kw.get('location') or None}
        _res, out = pc.run([('doc_open', {'path': 'in.pdf'}), ('sign_document', {k: v for k, v in args.items() if v is not None})],
                           {'in.pdf': data, 'id.p12': p12}, read=('signed.pdf',))
        if not out.get('signed.pdf'):
            raise StoreError('E-SIGN', 'The document could not be signed.', 'المستند ما اتوقّعش.')
        return out['signed.pdf']

    def pdf_of_document(self, did, doc_id):
        """A Word, Excel, PowerPoint or text file turned into its PDF on this machine (LibreOffice): a new version, the source kept
        (superseded) — or, for the proposed leaflet that 1.1.9 asks in Word, its PDF added beside it (the copy an eCTD takes)."""
        import tempfile
        from .. import extract as _extract
        from ..generate.docx_kit import to_pdf, find_soffice
        d = self.document(doc_id)
        if d['dossier_id'] != did or d['state'] != 'current':
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        ext = d['filename'].rsplit('.', 1)[-1].lower() if '.' in d['filename'] else ''
        family = _extract.source_family(d['filename'], self.blob_path(d['sha256']).read_bytes()[:8192]) or ('word' if ext == 'docx' else None)
        if d['meta'].get('external') or family not in ('word', 'excel', 'powerpoint', 'text'):
            raise StoreError('E-NOT-SOURCE', 'This document is not a Word, Excel, PowerPoint or text file.', 'المستند ده مش ملف Word أو Excel أو PowerPoint أو نص.')
        if not find_soffice():
            raise StoreError('E-NO-OFFICE', 'This computer has no LibreOffice to turn it into a PDF. In Word: File → Save As → PDF (tick «Create bookmarks '
                             'using headings»), then upload the PDF to this item: it replaces this file.',
                             'الجهاز ده مفيهوش LibreOffice يحوّله PDF. من Word: ملف ← حفظ باسم ← PDF (علّم «إنشاء إشارات مرجعية باستخدام العناوين»)، '
                             'وبعدين ارفع الـ PDF في البند ده: هيحل محل الملف ده.')
        tmp = Path(tempfile.mkdtemp())
        try:
            src = tmp / ('source.' + (ext or 'docx'))
            shutil.copyfile(self.blob_path(d['sha256']), src)
            try:
                pdf = to_pdf(src).read_bytes()
            except Exception:
                raise StoreError('E-PDF-FAILED', 'LibreOffice could not turn this file into a PDF. Save it as PDF from its own program and upload it.',
                                 'LibreOffice ما قدرش يحوّل الملف ده PDF. احفظه PDF من البرنامج بتاعه وارفعه.')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        beside = next((s.req_id for s in self.slots(did) if s.slot_id == d['slot_id']), '') in WORD_ITEMS                 # 1.1.9 keeps its Word: the PDF goes in next to it
        name = (d['filename'].rsplit('.', 1)[0] if '.' in d['filename'] else d['filename']) + '.pdf'
        new = self.add_document(did, d['slot_id'], name, pdf, d['title'], {**d['meta'], 'converted_from': d['filename']},
                                supersede=None if beside else doc_id, doc_class=d['doc_class'])
        self.audit(did, 'document.to_pdf', doc=doc_id, new=new['id'], beside=beside)
        return {'document': new, 'beside': beside}

    # ---------------- submission history (lifecycle, P3)
    def record_submission(self, did, output, seq, activity, suuid, envelope, history, path):
        self.db.execute('insert into submission(id, dossier_id, output, seq, activity, submission_uuid, envelope, history, path, created) '
                        'values (?,?,?,?,?,?,?,?,?,?)',
                        (str(uuid.uuid4()), did, output, str(seq), str(activity), suuid, json.dumps(envelope, ensure_ascii=False),
                         json.dumps(history, ensure_ascii=False), str(path), time.time()))
        self.db.commit()

    def history(self, did, output):
        rows = self.db.execute('select * from submission where dossier_id=? and output=? order by created', (did, output)).fetchall()
        out = []
        for r in rows:
            seq = r['seq'] if output == 'ectd32' else int(r['seq'])
            act = r['activity'] if output == 'ectd32' else int(r['activity'])
            rc = json.loads(r['receipt'] or '{}') if 'receipt' in r.keys() else {}
            out.append({'seq': seq, 'activity': act, 'submission_uuid': r['submission_uuid'], 'created': r['created'],
                        'envelope': json.loads(r['envelope']), 'leaves': json.loads(r['history']), 'path': r['path'],
                        'receipt': rc, 'frozen': bool(rc.get('submitted'))})
        return out

    def _seq_row(self, did, output, seq):
        r = self.db.execute('select * from submission where dossier_id=? and output=? and seq=?', (did, output, str(seq))).fetchone()
        if not r:
            raise StoreError('E-NOT-FOUND', 'Sequence not found.', 'التسلسل مش موجود.')
        return r

    def mark_submitted(self, did, output, seq, info, receipt=None, filename=None):
        """The sequence went to the authority: its receipt is kept with it and it is frozen (never replaced, never discarded)."""
        from datetime import date as _d
        r = self._seq_row(did, output, seq)
        rc = json.loads(r['receipt'] or '{}')
        day = info.get('submitted') or _d.today().isoformat()
        for k in ('submitted', 'ack', 'decided'):
            v = info.get(k) if k != 'submitted' else day
            if v:
                try:
                    _d.fromisoformat(v)
                except ValueError:
                    raise StoreError('E-DATE', f'{k}: use a date like 2026-11-13.', f'{k}: اكتب التاريخ بالشكل 2026-11-13.')
        rc.update({k: v for k, v in info.items() if k in ('tracking', 'ack', 'decision', 'decided', 'note') and v not in (None, '')}, submitted=day)
        if receipt:
            rc.update(receipt_sha=self.put_blob(receipt), receipt_name=filename or 'receipt.pdf')
        self.db.execute('update submission set receipt=? where id=?', (json.dumps(rc, ensure_ascii=False), r['id']))
        self.db.commit()
        self.audit(did, 'submission.submitted', output=output, seq=str(seq), **{k: rc.get(k) for k in ('submitted', 'tracking')})
        return rc

    def discard_sequence(self, did, output, seq):
        """An exported sequence that was not submitted, the last one: taken off the history (the next export takes its number)."""
        r = self._seq_row(did, output, seq)
        if json.loads(r['receipt'] or '{}').get('submitted'):
            raise StoreError('E-FROZEN', 'This sequence was submitted: it is frozen. A change goes in a new sequence.',
                             'التسلسل ده اتقدّم: متجمّد. أي تعديل بيبقى في تسلسل جديد.')
        last = self.db.execute('select seq from submission where dossier_id=? and output=? order by created desc limit 1', (did, output)).fetchone()
        if last['seq'] != r['seq']:
            raise StoreError('E-NOT-LAST', 'Only the last sequence can be discarded.', 'التسلسل الأخير بس هو اللي ينفع يتشال.')
        self.db.execute('delete from submission where id=?', (r['id'],))
        self.db.commit()
        folder = Path(r['path'] or '')                  # its folder in the dossier's lifecycle store goes too: the number is free again
        try:
            inside = folder.resolve().is_relative_to((self.root / 'lifecycle' / did).resolve())
        except (OSError, ValueError):
            inside = False
        if inside and folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
        self.audit(did, 'submission.discarded', output=output, seq=str(seq))

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
        docs = [self.document(i) for i in ids]
        if slot_id is not None and any(d['meta'].get('renewal_request') for d in docs):
            for d in docs:                                # an expired pricing certificate with its request for updating: accepted
                if any(f.get('rule') == 'DOC-EXPIRED' for f in d['findings']):
                    d['findings'] = [dict(f, rule='DOC-EXPIRED-RENEWAL', severity='warn', action='none',
                                          en=f['en'].split(' Obtain')[0] + ' Accepted with the request for updating in this item (NP.CAPP.065 v5 1.1.5).',
                                          ar=f['ar'].split(' لازم')[0] + ' مقبول ومعاه طلب التحديث في نفس البند (NP.CAPP.065 v5 بند 1.1.5).')
                                     if f.get('rule') == 'DOC-EXPIRED' else f for f in d['findings']]
                    d['check_status'] = status_of(d['findings']) if d['findings'] else 'conforming'
        return docs

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

    def split_large(self, did, doc_id):
        """A file over the eCTD's 100 MB a file (ICH eCTD specification App. 7) cut into parts that fit (pdfcraft.split_by_size: at its
        chapters' bookmarks when they fit, otherwise by size), each part a document of the same item, «part k of n», the file they came
        from withdrawn (kept in the history). The pages are not changed, so a third party's document is cut too.
        → {parts: [documents]} or {parts: [], why}."""
        from .. import pdfcraft
        from ..checks.pdf import SIZE_LIMIT
        d = self._current_pdf(did, doc_id)
        data = self.blob_path(d['sha256']).read_bytes()
        if len(data) <= SIZE_LIMIT or not pdfcraft.available() or not d.get('slot_id'):
            return {'parts': [], 'why': 'fits'}
        try:
            parts, rep = pdfcraft.split_by_size(data, limit_mb=SIZE_LIMIT * 0.95 / 1e6)
        except pdfcraft.PdfCraftError as e:
            return {'parts': [], 'why': str(e)[:200]}
        if len(parts) < 2:
            return {'parts': [], 'why': 'cannot be cut'}
        stem = d['filename'].rsplit('.', 1)[0] if '.' in d['filename'] else d['filename']
        out = []
        for k, blob in enumerate(parts, 1):
            title = f"{d['title'] or stem} (part {k} of {len(parts)})"
            out.append(self.add_document(did, d['slot_id'], f'{stem}-part{k}.pdf', blob, title,
                                         {**{x: v for x, v in d['meta'].items() if x not in ('fixed_from', 'optimized')},
                                          'split_from': doc_id, 'part': [k, len(parts)], 'staged_by': 'size'},
                                         doc_class=d['doc_class']))
        self.db.execute("update document set state='withdrawn' where id=?", (doc_id,))
        self.db.commit()
        self.audit(did, 'document.split_size', doc=doc_id, parts=[x['id'] for x in out], sizes=[len(b) for b in parts])
        return {'parts': out}

    def improve_document(self, did, doc_id):
        """«Improve the file» (the owner, 13/11/2026: «PdfCraft has file improvement… use it»): PdfCraft's optimizer on a stored PDF
        (pdfcraft.optimize). A third party's document only losslessly, and kept only when its pages are the same pixel for pixel; a
        company's own document also with its pictures above 450 ppi brought to 300 ppi and its links that go nowhere removed. A new
        version only when the file is clearly smaller (5 % and 4 KB, pdfcraft.smaller_enough). → {document, before, after} or
        {document: None, why}."""
        from .. import fixes, pdfcraft
        from ..checks.pdf import LOCKED
        d = self.document(doc_id)
        if d['dossier_id'] != did or d['state'] != 'current':
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if d['meta'].get('external') or not d['filename'].lower().endswith('.pdf') or not pdfcraft.available():
            return {'document': None, 'why': 'not here'}
        path = self.blob_path(d['sha256'])
        if fixes.is_signed(path):
            return {'document': None, 'why': 'signed'}
        data = path.read_bytes()
        locked = d['doc_class'] in LOCKED
        try:
            new, rep = pdfcraft.optimize(data, lossless=locked, links=not locked, pdf20=data[:16].startswith(b'%PDF-2'))
        except pdfcraft.PdfCraftError as e:
            return {'document': None, 'why': str(e)[:200]}
        if not pdfcraft.smaller_enough(data, new):
            return {'document': None, 'why': 'already small', 'before': len(data)}
        if locked and not pdfcraft.same_pixels(data, new):
            return {'document': None, 'why': 'pages would change', 'before': len(data)}
        doc = self.add_document(did, d['slot_id'], d['filename'], new, d['title'],
                                {**d['meta'], 'fixed_from': doc_id, 'fixes': list(d['meta'].get('fixes') or []) + ['optimize'],
                                 'optimized': {'before': len(data), 'after': len(new), 'resampled': rep.get('images_resampled') or 0,
                                               'links_removed': rep.get('invalid_links') or 0}},
                                supersede=doc_id, doc_class=d['doc_class'])
        self.audit(did, 'document.optimized', doc=doc_id, new=doc['id'], before=len(data), after=len(new))
        return {'document': doc, 'before': len(data), 'after': len(new)}

    def keep_reading(self, did, doc_id, extracted):
        """What the program read from a document — the information it found (a scan read by OCR) — kept with it (meta «extracted»); the
        file is not touched."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        meta = dict(d['meta'], extracted=extracted)
        self.db.execute('update document set meta=? where id=?', (json.dumps(meta, ensure_ascii=False), doc_id))
        self.db.commit()
        self.audit(did, 'document.read', doc=doc_id, reader=extracted.get('reader'), found=len(extracted.get('found') or []))
        return self.document(doc_id)

    def keep_model_reading(self, did, doc_id, ai, by):
        """What Claude read on a document's pages (claude.ai's model in the browser edition, or the API with the key) — its entry in the
        reading's «documents» (kind, dates, signed, stamped, letterhead, legalised, language…) and the fields it found — kept with it
        (meta «model»); the file is not touched. Its kind becomes the document's kind where its own words gave none (the item it is
        suggested for), and a validity date it read becomes the document's, unless one is set already."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        ai = ai if isinstance(ai, dict) else {}
        docs = [x for x in ai.get('documents') or [] if isinstance(x, dict)]
        base = lambda n: str(n or '').replace('\\', '/').split('/')[-1].lower()
        mine = next((x for x in docs if base(x.get('filename')) in (base(d['filename']), base(d['meta'].get('original_name')))), None)
        if mine is None and len(docs) == 1:
            mine = docs[0]
        keep = {k: v for k, v in (mine or {}).items() if k != 'filename' and v not in (None, '', [])}
        fields = {k: ai[k] for k in ('product', 'profile', 'apis', 'envelope', 'batches', 'specs', 'results', 'registration', 'composition')
                  if ai.get(k) not in (None, '', [], {})}
        meta = dict(d['meta'], model={'doc': keep, 'fields': fields, 'by': str(by or 'model')[:40], 'at': time.time(), 'sha256': d['sha256']})
        if keep.get('kind') and keep['kind'] != 'other' and not d['meta'].get('kind'):
            meta['kind'] = keep['kind']
        vu = str(keep.get('valid_until') or '')[:10]
        if vu and not d['meta'].get('valid_until'):
            try:
                date.fromisoformat(vu)
                meta['valid_until'] = vu
                meta['validity_note'] = 'read by Claude'
                if keep.get('issued'):
                    meta.setdefault('issued', str(keep['issued'])[:10])
            except ValueError:
                pass
        self.db.execute('update document set meta=? where id=?', (json.dumps(meta, ensure_ascii=False), doc_id))
        self.db.commit()
        self.audit(did, 'document.read_by_model', doc=doc_id, by=meta['model']['by'], kind=keep.get('kind'))
        return self.document(doc_id)

    def confirm_condition(self, did, doc_id, cond, answer):
        """The person's answer to one condition the program could not see on a document (dated, the production lines, a CoA's data…):
        'yes' it is met, 'no' not yet, None to take the answer back (meta «confirmed»)."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if answer not in ('yes', 'no', None) or not isinstance(cond, str) or not cond or len(cond) > 60:
            raise StoreError('E-ANSWER', "The answer is 'yes' or 'no'.", "الإجابة «yes» أو «no».")
        conf = dict(d['meta'].get('confirmed') or {})
        if answer is None:
            conf.pop(cond, None)
        else:
            conf[cond] = answer
        meta = dict(d['meta'], confirmed=conf)
        self.db.execute('update document set meta=? where id=?', (json.dumps(meta, ensure_ascii=False), doc_id))
        self.db.commit()
        self.audit(did, 'document.condition_confirmed', doc=doc_id, cond=cond, answer=answer)
        return self.document(doc_id)

    def keep_fix_refused(self, did, doc_id, refused):
        """The fixes the program tried on a document and could not make, with why (meta «fix_refused»): the preparation stage then shows
        them as needing the user instead of offering the same fix again. An empty list clears them; the file is not touched (the attempt
        itself is in the audit trail, «document.fix_refused»)."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        meta = dict(d['meta'], fix_refused=[{'op': x['op'], 'en': x.get('en'), 'ar': x.get('ar')} for x in refused or []])
        self.db.execute('update document set meta=? where id=?', (json.dumps(meta, ensure_ascii=False), doc_id))
        self.db.commit()
        return self.document(doc_id)

    def set_document_details(self, did, doc_id, meta=None, title=None):
        """A document's title and its eCTD attributes (leaflet type, language, study, document type, EU country) changed where it is —
        the file itself is not touched, so it stays the same version (the sheet of updates list item 47, a corrected title)."""
        d = self.document(doc_id)
        if d['dossier_id'] != did or d['state'] != 'current':
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        new = dict(d['meta'], **{k: v for k, v in (meta or {}).items() if k in self.ITEM_META and v})
        if d['slot_id']:
            self.check_item_meta(did, d['slot_id'], new)
        title = (title or '').strip() or d['title']
        self.db.execute('update document set meta=?, title=? where id=?', (json.dumps(new, ensure_ascii=False), title, doc_id))
        self.db.commit()
        changed = {k: new[k] for k in self.ITEM_META if new.get(k) != d['meta'].get(k)}
        self.audit(did, 'document.details', doc=doc_id, **changed, **({'title': title} if title != d['title'] else {}))
        return self.document(doc_id)

    def confirm_kind(self, did, doc_id):
        """«It is in the right place»: the person overrules the kind rule for this file. Its DOC-KIND objection goes; every other finding
        stays and the status follows them; the meta and the audit keep what the rule took the file for."""
        d = self.document(doc_id)
        if d['dossier_id'] != did:
            raise StoreError('E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        gone = [f for f in d['findings'] if f.get('rule') == 'DOC-KIND']
        if not gone:
            return d
        kept = [f for f in d['findings'] if f.get('rule') != 'DOC-KIND']
        status = status_of(kept)
        said = (gone[0].get('extra') or {}).get('kind')
        meta = d['meta'] | {'kind_confirmed': {'at': time.time(), 'rule_said': said}}
        self.db.execute('update document set findings=?, check_status=?, meta=? where id=?',
                        (json.dumps(kept, ensure_ascii=False), status, json.dumps(meta, ensure_ascii=False), doc_id))
        self.db.commit()
        self.audit(did, 'document.kind_confirmed', doc=doc_id, slot=d['slot_id'], rule_said=said)
        return self.document(doc_id)

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
            ectd_issue = any(f.get('scope') == 'ectd' and f.get('severity') == 'block' for d in x['documents'] for f in d['findings'])
            if x['request'] and (x['status'] in ('not_started', 'non_conforming', 'needs_attention', 'received') or ectd_issue):
                x['status'] = 'waiting'                    # a new copy asked from the issuer (for the One Submission or for eCTD readiness)
            if x['req_id'] == 'M1-44' and x['status'] == 'not_started':
                x['status'] = 'auto'              # tracking table: rebuilt from the history at every eCTD export
        open_notes = {}
        for cm in self.comments(did, open_only=True):
            open_notes[cm['doc_id']] = open_notes.get(cm['doc_id'], 0) + 1
        for x in out:                                   # the team's own open notes on the item's documents (a note, never a stop)
            x['notes_open'] = sum(open_notes.get(d['id'], 0) for d in x['documents'])
        attest = (self.dossier(did).get('data') or {}).get('attest') or {}
        for x in out:                                   # what no reading can see, asked once per item
            need = (['signed', 'stamped'] if x.get('doc_class') == 'company_letter' else []) + (['legalized'] if x['req_id'] in ATTEST_LEGALIZE else [])
            x['attest_need'] = need if x['documents'] and not all(d['meta'].get('generated') for d in x['documents']) else []
            x['attest'] = attest.get(x['slot_id']) if x['attest_need'] else None
            if x['attest'] and x['attest'].get('answer') == 'no' and x['status'] not in ('not_applicable', 'not_started'):
                x['status'] = 'non_conforming'                       # «not yet»: signed / stamped / legalised still to come
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
        to_confirm = [s['slot_id'] for s in b['slots'] if s.get('attest_need') and not s.get('attest')]
        notes_open = [s['slot_id'] for s in b['slots'] if s.get('notes_open')]
        ectd_blocking = [s['slot_id'] for s in b['slots'] if any(f.get('scope') == 'ectd' and f.get('severity') == 'block'
                                                                for d in s['documents'] for f in d['findings'])]
        return {'ok': not missing and not blocking and not xb and not unsigned and not external, 'unsigned': unsigned, 'to_confirm': to_confirm,
                'ectd_blocking': ectd_blocking, 'notes_open': notes_open,
                'external_only': external, 'missing_required': missing, 'non_conforming': blocking,
                'cross_blocking': [{'id': f['id'], 'en': f['en'], 'ar': f['ar']} for f in xb],
                'provisional_profiles': ['EG eCTD 3.2.2 provisional v0', 'EG eCTD 4.0 provisional v0']}
