"""Review tables on the dossier store (SQLite): runs, findings, responses. Functions take the Store."""
import json
import time
import uuid

SCHEMA = '''
create table if not exists review_run(id text primary key, dossier_id text not null, created real not null, actor text,
  options text not null default '{}', pack_version text not null, status text not null, verdict text,
  dept_verdicts text not null default '{}', counts text not null default '{}', previous_run_id text,
  clock text not null default '{}', diff text not null default '{}', signed text not null default '{}', letters text not null default '{}');
create table if not exists review_finding(id text primary key, run_id text not null references review_run(id), dossier_id text not null,
  question_id text not null, key text not null, dept text not null, layer text not null, ctd text not null, slot_id text,
  severity text not null, verdict text not null, payload text not null default '{}', origin text not null, confidence real,
  confirmed_by text, confirmed_at real, override text, status text not null default 'open', created real not null);
create index if not exists review_finding_run on review_finding(run_id);
create table if not exists review_response(id text primary key, finding_id text not null references review_finding(id), run_id text not null,
  round integer not null default 1, text text not null, doc_ids text not null default '[]', actor text, created real not null,
  result text not null default 'pending', note text);
'''
RUN_JSON = ('options', 'dept_verdicts', 'counts', 'clock', 'diff', 'signed', 'letters')


def ensure(st):
    st.db.executescript(SCHEMA)


def _row(r, json_cols):
    d = dict(r)
    for k in json_cols:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except ValueError:
                pass
    return d


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def save_run(st, run, findings):
    db = st.db
    db.execute('insert into review_run(id, dossier_id, created, actor, options, pack_version, status, verdict, dept_verdicts, counts, previous_run_id, clock, diff, signed, letters) '
               'values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (run['id'], run['dossier_id'], run['created'], run.get('actor'), json.dumps(run.get('options') or {}), run['pack_version'], run['status'],
                run.get('verdict'), json.dumps(run.get('dept_verdicts') or {}), json.dumps(run.get('counts') or {}), run.get('previous_run_id'),
                json.dumps(run.get('clock') or {}), json.dumps(run.get('diff') or {}), json.dumps(run.get('signed') or {}), json.dumps(run.get('letters') or {})))
    for f in findings:
        db.execute('insert into review_finding(id, run_id, dossier_id, question_id, key, dept, layer, ctd, slot_id, severity, verdict, payload, origin, confidence, '
                   'confirmed_by, confirmed_at, override, status, created) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (f['id'], run['id'], run['dossier_id'], f['question_id'], f['key'], f['dept'], f['layer'], f['ctd'], f.get('slot_id'), f['severity'], f['verdict'],
                    json.dumps(f.get('payload') or {}), f['origin'], f.get('confidence'), f.get('confirmed_by'), f.get('confirmed_at'),
                    json.dumps(f['override']) if f.get('override') else None, f.get('status', 'open'), f.get('created', run['created'])))
    db.commit()


def update_run(st, rid, **cols):
    sets, vals = [], []
    for k, v in cols.items():
        sets.append(f'{k}=?')
        vals.append(json.dumps(v) if k in RUN_JSON else v)
    st.db.execute(f"update review_run set {', '.join(sets)} where id=?", (*vals, rid))
    st.db.commit()


def runs(st, did):
    return [_row(r, RUN_JSON) for r in st.db.execute('select * from review_run where dossier_id=? order by created desc', (did,)).fetchall()]


def run(st, rid):
    r = st.db.execute('select * from review_run where id=?', (rid,)).fetchone()
    return _row(r, RUN_JSON) if r else None


def latest(st, did):
    r = st.db.execute('select * from review_run where dossier_id=? order by created desc limit 1', (did,)).fetchone()
    return _row(r, RUN_JSON) if r else None


def finding(st, fid):
    r = st.db.execute('select * from review_finding where id=?', (fid,)).fetchone()
    return _finding(st, r) if r else None


def _finding(st, r):
    d = _row(r, ('payload', 'override'))
    d['responses'] = [dict(x, doc_ids=json.loads(x['doc_ids'])) for x in st.db.execute('select * from review_response where finding_id=? order by created', (d['id'],)).fetchall()]
    return d


def findings(st, rid, dept=None, verdict=None, severity=None, status=None):
    q, args = 'select * from review_finding where run_id=?', [rid]
    for col, val in (('dept', dept), ('verdict', verdict), ('severity', severity), ('status', status)):
        if val:
            q += f' and {col}=?'
            args.append(val)
    return [_finding(st, r) for r in st.db.execute(q + ' order by created, id', args).fetchall()]


def update_finding(st, fid, **cols):
    sets, vals = [], []
    for k, v in cols.items():
        sets.append(f'{k}=?')
        vals.append(json.dumps(v) if k in ('payload', 'override') else v)
    st.db.execute(f"update review_finding set {', '.join(sets)} where id=?", (*vals, fid))
    st.db.commit()


def add_response(st, fid, rid, text, doc_ids, actor=None, round_no=1):
    resp = {'id': new_id('RS'), 'finding_id': fid, 'run_id': rid, 'round': round_no, 'text': text, 'doc_ids': doc_ids or [],
            'actor': actor, 'created': time.time(), 'result': 'pending', 'note': None}
    st.db.execute('insert into review_response(id, finding_id, run_id, round, text, doc_ids, actor, created, result, note) values (?,?,?,?,?,?,?,?,?,?)',
                  (resp['id'], fid, rid, round_no, text, json.dumps(doc_ids or []), actor, resp['created'], 'pending', None))
    st.db.commit()
    return resp


def set_response_result(st, resp_id, result, note=None):
    st.db.execute('update review_response set result=?, note=? where id=?', (result, note, resp_id))
    st.db.commit()
