"""Assistant tables on the dossier store: the conversation (API messages as stored), runs, approvals, saved readings."""
import json
import time
import uuid

SCHEMA = '''
create table if not exists assistant_message(id text primary key, dossier_id text not null, run_id text, role text not null,
  content text not null, created real not null);
create index if not exists assistant_message_d on assistant_message(dossier_id, created);
create table if not exists assistant_run(id text primary key, dossier_id text not null, status text not null, started real not null,
  ended real, user text, error text, usage text not null default '{}', steps integer not null default 0, partial text,
  pending text not null default '{}', stop integer not null default 0);
create index if not exists assistant_run_d on assistant_run(dossier_id, started);
create table if not exists assistant_approval(id text primary key, dossier_id text not null, run_id text not null, tool_use_id text not null,
  tool text not null, args text not null, status text not null default 'pending', created real not null, decided real, by text, note text, result text);
create index if not exists assistant_approval_d on assistant_approval(dossier_id, status);
create table if not exists assistant_reading(id text primary key, dossier_id text not null, doc_id text not null, pages text,
  note text not null, created real not null);
create index if not exists assistant_reading_d on assistant_reading(dossier_id, doc_id);
'''


def ensure(st):
    st.db.executescript(SCHEMA)


def new_id(prefix):
    return f'{prefix}-{uuid.uuid4().hex[:10]}'


def _j(s, default):
    try:
        return json.loads(s) if isinstance(s, str) else (s if s is not None else default)
    except ValueError:
        return default


# ---------------- messages
def add_message(st, did, run_id, role, content):
    mid = new_id('am')
    st.db.execute('insert into assistant_message(id, dossier_id, run_id, role, content, created) values (?,?,?,?,?,?)',
                  (mid, did, run_id, role, json.dumps(content, ensure_ascii=False), time.time()))
    st.db.commit()
    return mid


def messages(st, did):
    return [{'id': r['id'], 'run_id': r['run_id'], 'role': r['role'], 'content': _j(r['content'], []), 'created': r['created']}
            for r in st.db.execute('select * from assistant_message where dossier_id=? order by created, rowid', (did,)).fetchall()]


def clear(st, did):
    for t in ('assistant_message', 'assistant_approval', 'assistant_run'):
        st.db.execute(f'delete from {t} where dossier_id=?', (did,))
    st.db.commit()


# ---------------- runs
def start_run(st, did, user):
    rid = new_id('ar')
    st.db.execute('insert into assistant_run(id, dossier_id, status, started, user) values (?,?,?,?,?)', (rid, did, 'running', time.time(), user))
    st.db.commit()
    return rid


def run(st, rid):
    r = st.db.execute('select * from assistant_run where id=?', (rid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d['usage'], d['pending'] = _j(d['usage'], {}), _j(d['pending'], {})
    return d


def latest_run(st, did):
    r = st.db.execute('select id from assistant_run where dossier_id=? order by started desc, rowid desc limit 1', (did,)).fetchone()
    return run(st, r['id']) if r else None


def active_run(st, did):
    r = st.db.execute("select id from assistant_run where dossier_id=? and status in ('running','waiting_approval') order by started desc limit 1",
                      (did,)).fetchone()
    return run(st, r['id']) if r else None


def update_run(st, rid, **cols):
    sets, vals = [], []
    for k, v in cols.items():
        if k in ('usage', 'pending'):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f'{k}=?')
        vals.append(v)
    vals.append(rid)
    st.db.execute(f"update assistant_run set {', '.join(sets)} where id=?", vals)
    st.db.commit()


def add_usage(st, rid, usage):
    r = run(st, rid)
    u = r['usage'] if r else {}
    for k, v in usage.items():
        u[k] = (u.get(k) or 0) + (v or 0)
    update_run(st, rid, usage=u, steps=(r['steps'] if r else 0) + 1)
    return u


def usage_total(st, did):
    tot = {}
    for r in st.db.execute('select usage from assistant_run where dossier_id=?', (did,)).fetchall():
        for k, v in _j(r['usage'], {}).items():
            tot[k] = (tot.get(k) or 0) + (v or 0)
    return tot


# ---------------- approvals
def add_approval(st, did, rid, tool_use_id, tool, args):
    aid = new_id('ap')
    st.db.execute('insert into assistant_approval(id, dossier_id, run_id, tool_use_id, tool, args, status, created) values (?,?,?,?,?,?,?,?)',
                  (aid, did, rid, tool_use_id, tool, json.dumps(args, ensure_ascii=False), 'pending', time.time()))
    st.db.commit()
    return aid


def approval(st, aid):
    r = st.db.execute('select * from assistant_approval where id=?', (aid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d['args'] = _j(d['args'], {})
    return d


def approvals(st, did, status=None, run_id=None):
    q, args = 'select * from assistant_approval where dossier_id=?', [did]
    if status:
        q += ' and status=?'
        args.append(status)
    if run_id:
        q += ' and run_id=?'
        args.append(run_id)
    out = []
    for r in st.db.execute(q + ' order by created', args).fetchall():
        d = dict(r)
        d['args'] = _j(d['args'], {})
        out.append(d)
    return out


def decide_approval(st, aid, status, by, note=None, result=None):
    st.db.execute('update assistant_approval set status=?, decided=?, by=?, note=?, result=? where id=?',
                  (status, time.time(), by, note, result, aid))
    st.db.commit()


# ---------------- readings (Claude's notes on a document, kept so the next session does not re-read it)
def add_reading(st, did, doc_id, pages, note):
    rid = new_id('rd')
    st.db.execute('insert into assistant_reading(id, dossier_id, doc_id, pages, note, created) values (?,?,?,?,?,?)',
                  (rid, did, doc_id, pages, note, time.time()))
    st.db.commit()
    return rid


def readings(st, did, doc_id=None):
    q, args = 'select * from assistant_reading where dossier_id=?', [did]
    if doc_id:
        q += ' and doc_id=?'
        args.append(doc_id)
    return [dict(r) for r in st.db.execute(q + ' order by created', args).fetchall()]


# ---------------- staged files (uploaded in the chat, not yet placed in a CTD item)
def stage_document(st, did, filename, data, title=None):
    """A document row without a slot («unassigned»): the Assistant reads it and places it with place_document."""
    sha = st.put_blob(data)
    doc_id = str(uuid.uuid4())
    st.db.execute('insert into document values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (doc_id, did, None, 1, sha, filename, title or filename, 'unassigned', json.dumps({'staged_by': 'assistant'}), '[]',
                   'received', 'current', time.time()))
    st.db.commit()
    st.audit(did, 'document.staged', doc=doc_id, filename=filename, sha256=sha)
    return st.document(doc_id)
