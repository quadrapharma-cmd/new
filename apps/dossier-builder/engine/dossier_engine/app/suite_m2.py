"""The authority's letters, its questions and the company's commitments, with their deadlines — module 2 of the suite (updates list,
item 11). A letter from the authority is read when it is added: its numbered questions become questions to answer, and a time it
gives («within 30 days», «خلال ٣٠ يوم») becomes the due date — both shown to the person, who corrects them. Each question gets its
answer; the reply letter is written from the answers. Every open question, letter and commitment with a due date is on one list of
deadlines, the overdue first."""
import json, re, time, uuid
from datetime import date, timedelta
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse

SCHEMA = '''
create table if not exists letter(id text primary key, product_id text, dossier_id text, direction text not null,
  authority text, subject text not null, ref_no text, dated text, received text, due text,
  status text not null default 'open', sha256 text, filename text, notes text, reply_to text, created real not null);
create table if not exists question(id text primary key, letter_id text not null, n integer not null, text text not null,
  owner text, due text, status text not null default 'open', answer text, answered real, created real not null);
create table if not exists commitment(id text primary key, product_id text, letter_id text, text text not null, due text,
  status text not null default 'open', done real, evidence text, created real not null);
'''
DIRECTIONS = ('in', 'out')
LETTER_STATUS = ('open', 'answered', 'closed')
Q_STATUS = ('open', 'drafted', 'answered')
SOON = 14                                            # days: a deadline this close is «soon»
_AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')
_Q_START = re.compile(r'^\s*(?:\(\s*(\d{1,2})\s*\)|(\d{1,2})\s*[-.)/:–]\s+)(.+)$')
_WITHIN = re.compile(r'(?:within|in)\s+(\d{1,3})\s*(working\s+days?|days?|weeks?|months?)|خلال\s+(\d{1,3})\s*(يوم(?:\s*عمل)?|أيام|ايام|اسبوع|أسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور)', re.I)


class M2Error(ValueError):
    def __init__(self, code, en, ar):
        super().__init__(en)
        self.code, self.en, self.ar = code, en, ar


def _date(s, field):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)).isoformat()
    except ValueError:
        raise M2Error('E-DATE', f'{field}: use a date like 2027-03-31.', f'{field}: اكتب التاريخ بالشكل 2027-03-31.')


def questions_in(text):
    """The numbered questions of an authority's letter: «1- …», «(2) …», «3. …» (Arabic digits too), each with the lines that follow it
    until the next number. Text that is not a numbered question is not a question."""
    out, cur = [], None
    for raw in (text or '').translate(_AR_DIGITS).splitlines():
        ln = re.sub(r'\s+', ' ', raw).strip()
        if not ln:
            continue
        m = _Q_START.match(ln)
        if m and len(m.group(3)) >= 8:
            n = int(m.group(1) or m.group(2))
            if cur is None or n == cur['n'] + 1 or (n == 1 and cur['n'] != 0):
                cur = {'n': n, 'text': m.group(3).strip()}
                out.append(cur)
                continue
        if cur is not None and len(ln) > 2 and not re.match(r'^(?:sincerely|regards|signature|توقيع|مع خالص|وتفضلوا)', ln, re.I):
            cur['text'] = (cur['text'] + ' ' + ln)[:2000]
    return [q for q in out if len(q['text']) >= 12]


def due_in(text, base):
    """A time the letter gives («within 30 days», «خلال ٣٠ يوم», «within 2 months») counted from `base` (the day it was received)."""
    m = _WITHIN.search((text or '').translate(_AR_DIGITS))
    if not m or not base:
        return None
    n = int(m.group(1) or m.group(3))
    unit = (m.group(2) or m.group(4) or '').lower()
    d = date.fromisoformat(base)
    if 'month' in unit or 'شهر' in unit or 'أشهر' in unit or 'اشهر' in unit or 'شهور' in unit:
        y, mo = divmod(d.month - 1 + n, 12)
        import calendar
        return date(d.year + y, mo + 1, min(d.day, calendar.monthrange(d.year + y, mo + 1)[1])).isoformat()
    if 'week' in unit or 'سبوع' in unit or 'سابيع' in unit:
        return (d + timedelta(weeks=n)).isoformat()
    return (d + timedelta(days=n)).isoformat()


class M2:
    def __init__(self, st, today=None):
        self.st, self._today = st, today
        st.db.executescript(SCHEMA)
        st.db.commit()

    @property
    def db(self):
        return self.st.db

    def today(self):
        return self._today() if callable(self._today) else (self._today or date.today())

    def _audit(self, event, **kw):
        self.st.audit(kw.get('dossier'), 'suite.' + event, **{k: v for k, v in kw.items() if k != 'dossier'})

    # ---------------- letters
    def add_letter(self, meta, data=None, filename=None):
        subject = (meta.get('subject') or '').strip()
        direction = meta.get('direction') or 'in'
        if direction not in DIRECTIONS:
            raise M2Error('E-DIRECTION', 'A letter comes in from the authority or goes out to it.', 'الخطاب يا وارد من الهيئة يا صادر ليها.')
        text = ''
        if data:
            from .. import extract
            text = extract.read_text(filename or 'letter.pdf', data, max_pages=12).get('text') or ''
        if not subject:                                  # the letter's own «Subject:» line, else its first line, else the file's name
            m = re.search(r'(?:^|\n)\s*(?:subject|re)\s*[:：]\s*([^\n]{4,})|الموضوع\s*[:：]\s*([^\n]{4,})', text, re.I)
            subject = (re.sub(r'\s+', ' ', (m.group(1) or m.group(2))).strip()[:160] if m else
                       next((re.sub(r'\s+', ' ', ln).strip()[:120] for ln in text.splitlines() if len(ln.strip()) > 8), '') or (filename or ''))
        if not subject:
            raise M2Error('E-SUBJECT', 'Give the letter a subject.', 'اكتب موضوع الخطاب.')
        dated, received = _date(meta.get('dated'), 'dated'), _date(meta.get('received'), 'received')
        base = received or dated or self.today().isoformat()
        due = _date(meta.get('due'), 'due') or (due_in(text, base) if direction == 'in' else None)
        if meta.get('product_id'):
            self._product(meta['product_id'])
        lid = str(uuid.uuid4())
        sha = self.st.put_blob(data) if data else None
        self.db.execute('insert into letter values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (lid, meta.get('product_id'), meta.get('dossier_id'), direction, meta.get('authority') or 'EDA', subject,
                         meta.get('ref_no'), dated, received, due, 'open', sha, filename, meta.get('notes'), meta.get('reply_to'), time.time()))
        found = questions_in(text) if direction == 'in' and meta.get('read_questions', True) else []
        for q in found:
            self.db.execute('insert into question values (?,?,?,?,?,?,?,?,?,?)',
                            (str(uuid.uuid4()), lid, q['n'], q['text'], None, due, 'open', None, None, time.time()))
        if meta.get('reply_to'):
            self.db.execute("update letter set status='answered' where id=?", (meta['reply_to'],))
        self.db.commit()
        self._audit('letter.added', letter=lid, direction=direction, questions=len(found), dossier=meta.get('dossier_id'))
        return dict(self.letter(lid), read={'questions': len(found), 'due': due if due and not meta.get('due') else None})

    def letter(self, lid):
        r = self.db.execute('select * from letter where id=?', (lid,)).fetchone()
        if not r:
            raise M2Error('E-NOT-FOUND', 'Letter not found.', 'الخطاب مش موجود.')
        out = dict(r)
        out['questions'] = [dict(q) for q in self.db.execute('select * from question where letter_id=? order by n', (lid,)).fetchall()]
        out['product'] = self._product_name(out['product_id'])
        return out

    def letters(self, product=None):
        q, args = 'select id from letter', []
        if product:
            q, args = q + ' where product_id=?', [product]
        out = []
        for r in self.db.execute(q + ' order by coalesce(received, dated, created) desc', args).fetchall():
            x = self.letter(r['id'])
            x['open_questions'] = sum(1 for k in x['questions'] if k['status'] != 'answered')
            out.append(x)
        return out

    def update_letter(self, lid, **f):
        self.letter(lid)
        for k in ('subject', 'ref_no', 'authority', 'notes', 'product_id', 'dossier_id'):
            if k in f:
                self.db.execute(f'update letter set {k}=? where id=?', (f[k], lid))
        for k in ('dated', 'received', 'due'):
            if k in f:
                self.db.execute(f'update letter set {k}=? where id=?', (_date(f[k], k), lid))
        if 'status' in f:
            if f['status'] not in LETTER_STATUS:
                raise M2Error('E-STATUS', 'Unknown status.', 'حالة مش معروفة.')
            self.db.execute('update letter set status=? where id=?', (f['status'], lid))
        self.db.commit()
        return self.letter(lid)

    def delete_letter(self, lid):
        self.letter(lid)
        self.db.execute('delete from question where letter_id=?', (lid,))
        self.db.execute('delete from letter where id=?', (lid,))
        self.db.commit()
        self._audit('letter.deleted', letter=lid)

    # ---------------- questions
    def add_question(self, lid, text, due=None):
        let = self.letter(lid)
        if not text or len(text.strip()) < 3:
            raise M2Error('E-TEXT', 'Write the question.', 'اكتب السؤال.')
        n = max([q['n'] for q in let['questions']] or [0]) + 1
        qid = str(uuid.uuid4())
        self.db.execute('insert into question values (?,?,?,?,?,?,?,?,?,?)',
                        (qid, lid, n, text.strip(), None, _date(due, 'due') or let['due'], 'open', None, None, time.time()))
        self.db.commit()
        return self.question(qid)

    def question(self, qid):
        r = self.db.execute('select * from question where id=?', (qid,)).fetchone()
        if not r:
            raise M2Error('E-NOT-FOUND', 'Question not found.', 'السؤال مش موجود.')
        return dict(r)

    def update_question(self, qid, **f):
        q = self.question(qid)
        for k in ('text', 'owner', 'answer'):
            if k in f:
                self.db.execute(f'update question set {k}=? where id=?', (f[k], qid))
        if 'due' in f:
            self.db.execute('update question set due=? where id=?', (_date(f['due'], 'due'), qid))
        status = f.get('status') or ('drafted' if f.get('answer') and q['status'] == 'open' else None)
        if status:
            if status not in Q_STATUS:
                raise M2Error('E-STATUS', 'Unknown status.', 'حالة مش معروفة.')
            self.db.execute('update question set status=?, answered=? where id=?', (status, time.time() if status == 'answered' else None, qid))
        self.db.commit()
        let = self.letter(q['letter_id'])
        if let['questions'] and all(x['status'] == 'answered' for x in let['questions']) and let['status'] == 'open':
            self.db.execute("update letter set status='answered' where id=?", (let['id'],))
            self.db.commit()
        return self.question(qid)

    def delete_question(self, qid):
        self.question(qid)
        self.db.execute('delete from question where id=?', (qid,))
        self.db.commit()

    # ---------------- commitments
    def add_commitment(self, text, due=None, product_id=None, letter_id=None):
        if not text or len(text.strip()) < 3:
            raise M2Error('E-TEXT', 'Write the commitment.', 'اكتب الالتزام.')
        if product_id:
            self._product(product_id)
        if letter_id:
            self.letter(letter_id)
        cid = str(uuid.uuid4())
        self.db.execute('insert into commitment values (?,?,?,?,?,?,?,?,?)',
                        (cid, product_id, letter_id, text.strip(), _date(due, 'due'), 'open', None, None, time.time()))
        self.db.commit()
        self._audit('commitment.added', commitment=cid)
        return self.commitment(cid)

    def commitment(self, cid):
        r = self.db.execute('select * from commitment where id=?', (cid,)).fetchone()
        if not r:
            raise M2Error('E-NOT-FOUND', 'Commitment not found.', 'الالتزام مش موجود.')
        return dict(r, product=self._product_name(r['product_id']))

    def commitments(self, product=None):
        q, args = 'select id from commitment', []
        if product:
            q, args = q + ' where product_id=?', [product]
        return [self.commitment(r['id']) for r in self.db.execute(q + " order by status='done', coalesce(due, '9999')", args).fetchall()]

    def update_commitment(self, cid, **f):
        self.commitment(cid)
        for k in ('text', 'evidence', 'product_id'):
            if k in f:
                self.db.execute(f'update commitment set {k}=? where id=?', (f[k], cid))
        if 'due' in f:
            self.db.execute('update commitment set due=? where id=?', (_date(f['due'], 'due'), cid))
        if 'status' in f:
            if f['status'] not in ('open', 'done'):
                raise M2Error('E-STATUS', 'A commitment is open or done.', 'الالتزام يا مفتوح يا اتنفّذ.')
            self.db.execute('update commitment set status=?, done=? where id=?', (f['status'], time.time() if f['status'] == 'done' else None, cid))
        self.db.commit()
        return self.commitment(cid)

    # ---------------- deadlines
    def deadlines(self):
        """Every open question, letter and commitment with a due date: [{kind, id, title, due, days, state, product}], the overdue first."""
        today = self.today()
        out = []

        def add(kind, rid, title, due, product, extra=None):
            days = (date.fromisoformat(due) - today).days
            out.append({'kind': kind, 'id': rid, 'title': title, 'due': due, 'days': days, 'product': product,
                        'state': 'overdue' if days < 0 else 'soon' if days <= SOON else 'later', **(extra or {})})
        for r in self.db.execute("select q.*, l.subject, l.product_id from question q join letter l on l.id=q.letter_id "
                                 "where q.status!='answered' and q.due is not null").fetchall():
            add('question', r['id'], f"{r['subject']} — {r['n']}. {r['text'][:120]}", r['due'], self._product_name(r['product_id']), {'letter_id': r['letter_id']})
        for r in self.db.execute("select * from letter where status='open' and due is not null").fetchall():
            if not self.db.execute("select 1 from question where letter_id=? and status!='answered' and due is not null", (r['id'],)).fetchone():
                add('letter', r['id'], r['subject'], r['due'], self._product_name(r['product_id']))
        for r in self.db.execute("select * from commitment where status='open' and due is not null").fetchall():
            add('commitment', r['id'], r['text'][:160], r['due'], self._product_name(r['product_id']))
        return sorted(out, key=lambda x: (x['due'], x['kind']))

    # ---------------- the reply
    def reply_docx(self, lid, out, lang='en', company=None, signatory=None):
        """The reply letter: each question of the authority with the company's answer, in the letter's order."""
        from ..generate.docx_kit import new_doc, para, table
        let = self.letter(lid)
        ar = lang == 'ar'
        if not let['questions'] or any(not (q['answer'] or '').strip() for q in let['questions']):
            raise M2Error('E-ANSWERS', 'Answer every question first.', 'جاوب كل الأسئلة الأول.')
        d = new_doc(draft=True)
        para(d, f"{'إلى' if ar else 'To'}: {let['authority'] or 'EDA'}", ar=ar)
        para(d, f"{'الموضوع: الرد على' if ar else 'Subject: Response to'} {let['subject']}" + (f" ({let['ref_no']})" if let['ref_no'] else ''), ar=ar, bold=True)
        if let['product']:
            para(d, ('المستحضر: ' if ar else 'Product: ') + let['product'], ar=ar)
        para(d, 'بالإشارة إلى خطابكم، نتشرف بالرد على الملاحظات كالتالي:' if ar else 'With reference to your letter, please find our response to each comment below.', ar=ar)
        table(d, ['م' if ar else 'No.', 'الملاحظة' if ar else 'Comment', 'الرد' if ar else 'Response'],
              [[str(q['n']), q['text'], q['answer']] for q in let['questions']], ar=ar)
        para(d, (company or '') + ('\n' + signatory if signatory else ''), ar=ar)
        d.save(out)
        return out

    # ---------------- helpers
    def _product(self, pid):
        r = self.db.execute('select id, name from product where id=?', (pid,)).fetchone()
        if not r:
            raise M2Error('E-NOT-FOUND', 'Product not found.', 'المنتج مش موجود.')
        return dict(r)

    def _product_name(self, pid):
        if not pid:
            return None
        r = self.db.execute('select name from product where id=?', (pid,)).fetchone()
        return r['name'] if r else None


def install(app, st, err):
    from fastapi.responses import JSONResponse
    m2 = M2(st)
    app.state.m2 = m2

    @app.exception_handler(M2Error)
    def _m2_err(request, e):
        return JSONResponse(status_code=404 if e.code == 'E-NOT-FOUND' else 422, content={'detail': {'code': e.code, 'en': e.en, 'ar': e.ar}})

    @app.get('/api/suite/letters')
    def letters(product: str = None):
        return m2.letters(product)

    @app.post('/api/suite/letters', status_code=201)
    async def add_letter(meta: str = Form(...), file: UploadFile = File(None)):
        data = await file.read() if file else None
        return m2.add_letter(json.loads(meta), data, file.filename if file else None)

    @app.get('/api/suite/letters/{lid}')
    def letter(lid: str):
        return m2.letter(lid)

    @app.put('/api/suite/letters/{lid}')
    def put_letter(lid: str, body: dict):
        return m2.update_letter(lid, **body)

    @app.delete('/api/suite/letters/{lid}')
    def del_letter(lid: str):
        m2.delete_letter(lid)
        return {'ok': True}

    @app.get('/api/suite/letters/{lid}/file')
    def letter_file(lid: str):
        x = m2.letter(lid)
        if not x['sha256']:
            err(404, 'E-NO-FILE', 'This letter has no file.', 'الخطاب ده مفيهوش ملف.')
        return FileResponse(st.blob_path(x['sha256']), filename=x['filename'] or 'letter.pdf')

    @app.post('/api/suite/letters/{lid}/questions', status_code=201)
    def add_q(lid: str, body: dict):
        return m2.add_question(lid, body.get('text'), body.get('due'))

    @app.put('/api/suite/questions/{qid}')
    def put_q(qid: str, body: dict):
        return m2.update_question(qid, **body)

    @app.delete('/api/suite/questions/{qid}')
    def del_q(qid: str):
        m2.delete_question(qid)
        return {'ok': True}

    def _reply(lid, lang, company=None, signatory=None):
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp()) / 'reply.docx'
        m2.reply_docx(lid, tmp, lang or 'en', company, signatory)
        return FileResponse(tmp, filename='reply.docx',
                            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    @app.post('/api/suite/letters/{lid}/reply')
    def reply(lid: str, body: dict = None):
        """The reply letter (Word) from the answers: each comment with its response."""
        body = body or {}
        return _reply(lid, body.get('lang'), body.get('company'), body.get('signatory'))

    @app.get('/api/suite/letters/{lid}/reply.docx')
    def reply_file(lid: str, lang: str = 'en'):
        """The same reply letter as a link the page downloads."""
        return _reply(lid, lang)

    @app.get('/api/suite/commitments')
    def commitments(product: str = None):
        return m2.commitments(product)

    @app.post('/api/suite/commitments', status_code=201)
    def add_c(body: dict):
        return m2.add_commitment(body.get('text'), body.get('due'), body.get('product_id'), body.get('letter_id'))

    @app.put('/api/suite/commitments/{cid}')
    def put_c(cid: str, body: dict):
        return m2.update_commitment(cid, **body)

    @app.get('/api/suite/deadlines')
    def deadlines():
        return m2.deadlines()

    return m2
