#!/usr/bin/env python3
"""Drugbox — database timings of the hot queries the live app sends, as a signed-in member, WITH row-level security.

    STAGING_DB_URL=… python3 tools/scale/timings.py                        # member1 (heavy) + member50000 (typical)
    (the URL may also be the first argument — but then its password shows in `ps`; from the environment it does not)
    python3 tools/scale/timings.py "$STAGING_DB_URL" --member 1 --member 777 --runs 9
    python3 tools/scale/timings.py "$STAGING_DB_URL" --max 50 --max-for directory_page=120 --json out.json

Each query is the SQL equivalent of what web/src/live/adapter.js asks PostgREST for (same filters, embeds, order and
limits; RPCs are called exactly as the adapter calls them), wrapped like PostgREST wraps a response (json_agg).
It runs inside a transaction that is rolled back, as `authenticated` with request.jwt.claims for the member — so
RLS policies, SECURITY DEFINER bodies and auth.uid() behave as for a real request. EXPLAIN (ANALYZE) is repeated
--runs times (the first run is a warm-up and not counted); the table shows the median and the worst database time
(planning + execution) and the rows returned. Exit code 1 if any median is over its limit or any query fails.

Members are the seeded ones (tools/scale/seed_100k.sql): member<N>@scale.test with id md5('drugbox-scale-' || N).
Use --uuid to time a real account instead. Needs psql on PATH and a DB URL for a role that can SET ROLE
authenticated (postgres on Supabase). Read-only: every statement is rolled back.
"""
import argparse, hashlib, json, os, re, statistics, subprocess, sys, uuid

PCOLS = 'id,name,headline,company,country,bio,avatar_url,role,verified,location,open_to_work,hiring,profile_views,followers_count'
P = ', '.join('x.' + c for c in PCOLS.split(','))


def member_uuid(n):
    return str(uuid.UUID(hashlib.md5(('drugbox-scale-%d' % n).encode()).hexdigest()))


def wrap(sql):  # PostgREST returns the rows as one json array
    return "select coalesce(json_agg(t), '[]') from (%s) t" % sql


def queries(ctx):
    me, partner, company, ids20, cursor, review_ids = ctx['me'], ctx['partner'], ctx['company'], ctx['ids20'], ctx['cursor'], ctx['review_ids']
    author = "(select row_to_json(a) from (select %s from public.profiles x where x.id = %s) a)"
    feed = ("select p.*, %s as author, coalesce((select json_agg(m) from public.post_media m where m.post_id = p.id), '[]') as post_media "
            "from public.posts p {where} order by p.created_at desc, p.id desc limit 20") % (author % (P, 'p.user_id'))
    q = [
        # feed (adapter fetchPage): first page, a deep page by the keyset cursor, then my likes / saves among its ids
        ('feed_page', wrap(feed.format(where=''))),
        ('feed_page_cursor', wrap(feed.format(where="where p.created_at <= '{t}' and (p.created_at < '{t}' or (p.created_at = '{t}' and p.id < {i}))".format(**cursor)))),
        ('feed_my_likes', wrap("select post_id from public.reactions where user_id = '%s' and post_id in (%s)" % (me, ids20))),
        ('feed_my_saved', wrap("select post_id from public.saved_posts where user_id = '%s' and post_id in (%s)" % (me, ids20))),
        ('post_comments', wrap("select c.*, %s as author from public.comments c where c.post_id = %s order by c.created_at, c.id limit 50"
                               % (author % (P, 'c.user_id'), ctx['hot_post']))),
        # network
        ('connections_page', wrap(("select c.id, c.requester, c.addressee, c.status, %s as rp, %s as ap from public.connections c "
                                   "where (c.requester = '{me}' or c.addressee = '{me}') and c.id > 0 order by c.id limit 1000")
                                  .format(me=me) % (author % (P, 'c.requester'), author % (P, 'c.addressee')))),
        ('suggest_people', "select json_agg(s) from public.suggest_people(12) s"),
        ('my_network_stats', "select public.my_network_stats()"),
        # notifications: the list, the poll for new ones, the start-up "last id"
        ('notifications_list', wrap("select n.*, %s as actor from public.notifications n where n.user_id = '%s' order by n.created_at desc limit 50"
                                    % (author % (P, 'n.from_user'), me))),
        ('notifications_poll', wrap("select id, type from public.notifications where user_id = '%s' and id > %s order by id desc limit 50" % (me, ctx['notif_after']))),
        ('notifications_unread', wrap("select id from public.notifications where user_id = '%s' and read = false limit 50" % me)),
        # messages
        ('my_conversations', "select json_agg(c) from public.my_conversations(50) c"),
        ('conversation_messages', "select json_agg(m) from public.conversation_messages('%s'::uuid, null, 50) m" % partner),
        ('new_messages_poll', "select json_agg(m) from public.new_messages(%s) m" % ctx['msg_after']),
        ('my_last_message_id', "select public.my_last_message_id()"),
        # companies directory and hub
        ('directory_page', "select public.directory_companies_page(100, 0, null)"),
        ('directory_page_deep', "select public.directory_companies_page(100, %d, null)" % ctx['dir_offset']),
        ('directory_search', "select public.directory_companies_page(100, 0, 'metformin')"),
        ('company_track_record', "select public.company_track_record(%s)" % company),
        ('deals_list', wrap("select d.*, coalesce((select json_agg(e) from public.deal_events e where e.deal_id = d.id), '[]') as deal_events, "
                            "(select row_to_json(f) from (select slug, name from public.companies where id = d.from_company_id) f) as fc, "
                            "(select row_to_json(g) from (select slug, name from public.companies where id = d.to_company_id) g) as tc, "
                            "(select row_to_json(u) from (select name from public.profiles where id = d.from_user) u) as fu "
                            "from public.deals d order by d.updated_at desc limit 300")),
        # jobs + trust layer
        ('jobs_list', wrap("select j.*, %s as poster from public.jobs j where j.active order by j.created_at desc limit 60" % (author % (P, 'j.user_id')))),
        ('open_candidates', "select json_agg(c) from public.open_candidates(40) c"),
        ('get_reviews_many', "select json_agg(r) from public.get_reviews_many(array[%s]::uuid[], 'employer') r" % review_ids),
        ('my_interactions', "select json_agg(i) from public.my_interactions() i"),
        # marketplace, groups
        ('market_products', wrap("select p.*, %s as seller from public.products p where p.active and p.type = 'supply' order by p.created_at desc limit 40" % (author % (P, 'p.user_id')))),
        ('listings_active', wrap("select l.*, (select row_to_json(c) from (select slug from public.companies where id = l.company_id) c) as co "
                                 "from public.company_listings l where l.active order by l.created_at desc limit 500")),
        ('groups_list', wrap("select * from public.groups order by member_count desc, created_at desc limit 60")),
    ]
    return q


def psql(db, script, timeout=600):
    # the password goes to psql in PGPASSWORD, not on its command line (visible to every user in `ps`)
    from urllib.parse import urlsplit, urlunsplit, unquote
    env, u = dict(os.environ), urlsplit(db)
    if u.password is not None:
        env['PGPASSWORD'] = unquote(u.password)
        db = urlunsplit((u.scheme, u.netloc.rsplit('@', 1)[0].split(':', 1)[0] + '@' + u.netloc.rsplit('@', 1)[1], u.path, u.query, u.fragment))
    r = subprocess.run(['psql', db, '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1'], input=script, capture_output=True, text=True, timeout=timeout, env=env)
    return r.returncode, r.stdout, r.stderr


def context(db, n, explicit_uuid):
    """Values the app would have in hand when it sends each query (cursor of page 10, my top conversation, my company …)."""
    me = explicit_uuid or member_uuid(n)
    sql = f"""
      select json_build_object(
        'exists', exists (select 1 from public.profiles where id = '{me}'),
        'ids20', (select string_agg(id::text, ',') from (select id from public.posts order by created_at desc, id desc limit 20) x),
        'cursor', (select json_build_object('t', created_at, 'i', id) from public.posts order by created_at desc, id desc offset 199 limit 1),
        'hot_post', coalesce((select id from public.posts where user_id = '{me}' order by comment_count desc limit 1), (select id from public.posts order by comment_count desc limit 1), 0),
        'partner', coalesce((select partner from public.conversation_heads where owner = '{me}' order by last_at desc limit 1), '{me}'),
        'company', coalesce((select company_id from public.company_members where user_id = '{me}' and accepted order by company_id limit 1), 0),
        'notif_after', coalesce((select max(id) - 30 from public.notifications where user_id = '{me}'), 0),
        'msg_after', coalesce((select max(id) - 20 from public.messages where receiver_id = '{me}'), 0),
        'dir_offset', greatest(((select count(*) from public.companies) / 2 / 100) * 100, 0),
        'review_ids', (select string_agg(quote_literal(reviewee::text), ',') from (select distinct reviewee from public.job_reviews where reviewee_role = 'employer' limit 60) r))
    """
    code, out, err = psql(db, sql)
    if code: sys.exit('context query failed: ' + err.strip())
    c = json.loads(out.strip().splitlines()[-1])
    if not c['exists']: sys.exit(f'no profile {me} — seed first (tools/scale/seed_100k.sql) or pass --uuid')
    c['me'] = me
    c['ids20'] = c['ids20'] or '0'
    c['cursor'] = c['cursor'] or {'t': '2100-01-01', 'i': 0}
    c['review_ids'] = c['review_ids'] or "'%s'" % me
    return c


def time_query(db, me, sql, runs):
    claims = json.dumps({'sub': me, 'role': 'authenticated', 'aud': 'authenticated'})
    body = ["begin;", "set local role authenticated;", "set local statement_timeout = '60s';",
            "select set_config('request.jwt.claims', %s, true) \\g /dev/null" % ("'" + claims.replace("'", "''") + "'")]
    for _ in range(runs + 1):
        body += ["\\echo @@RUN", "explain (analyze, buffers, format json) %s;" % sql]
    body.append("rollback;")
    code, out, err = psql(db, '\n'.join(body) + '\n')
    if code: return None, err.strip().splitlines()[-1] if err.strip() else 'psql failed'
    res = []
    for chunk in out.split('@@RUN')[2:]:      # the first is before any run, the second is the warm-up
        plan = json.loads(chunk.strip())[0]; root = plan['Plan']
        node = root['Plans'][0] if root.get('Node Type') == 'Aggregate' and root.get('Plans') else root   # rows inside the json_agg
        res.append((plan['Planning Time'] + plan['Execution Time'], node.get('Actual Rows', 0),
                    root.get('Shared Hit Blocks', 0) + root.get('Shared Read Blocks', 0)))
    return res, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('db', nargs='?', default=os.environ.get('STAGING_DB_URL') or os.environ.get('DATABASE_URL'), help='postgres:// URL (or STAGING_DB_URL)')
    ap.add_argument('--member', type=int, action='append', help='seeded member number (repeatable; default 1 and 50000 — or users/2 on a smaller seed)')
    ap.add_argument('--uuid', action='append', default=[], help='time a real profile id instead (repeatable)')
    ap.add_argument('--runs', type=int, default=7, help='measured runs per query (after one warm-up), default 7')
    ap.add_argument('--max', type=float, default=50.0, help='limit in ms for the median of every query (default 50)')
    ap.add_argument('--max-for', action='append', default=[], metavar='NAME=MS', help='a different limit for one query (repeatable)')
    ap.add_argument('--only', action='append', default=[], help='run only these query names (repeatable)')
    ap.add_argument('--json', help='also write the results here')
    a = ap.parse_args()
    if not a.db: ap.error('give the database URL (or set STAGING_DB_URL)')
    limits = {}
    for x in a.max_for:
        k, _, v = x.partition('='); limits[k.strip()] = float(v)
    who = [(None, u) for u in a.uuid]
    if not who:
        members = a.member
        if not members:
            code, out, _ = psql(a.db, "select v from scale.kv where k = 'users'")       # the seed's size (no scale schema: 100k)
            users = int(out.strip()) if code == 0 and out.strip().isdigit() else 100000
            members = [1, max(users // 2, 2)]
        who = [(n, None) for n in members]
    results, bad = [], []
    for n, u in who:
        ctx = context(a.db, n, u)
        label = ('member%d' % n) if n else u
        print(f'\n── {label} ({ctx["me"]}) — median / worst of {a.runs} runs, database time incl. planning, RLS on')
        print(f'{"query":<24}{"median ms":>11}{"worst ms":>10}{"rows":>7}{"buffers":>9}{"limit":>8}  ')
        for name, sql in queries(ctx):
            if a.only and name not in a.only: continue
            res, err = time_query(a.db, ctx['me'], sql, a.runs)
            lim = limits.get(name, a.max)
            if err:
                print(f'{name:<24}{"ERROR":>11}  {err}'); bad.append((label, name, err)); results.append({'who': label, 'query': name, 'error': err}); continue
            ms = [r[0] for r in res]; med = statistics.median(ms)
            flag = '' if med <= lim else '  OVER'
            if flag: bad.append((label, name, '%.1f ms > %.0f ms' % (med, lim)))
            print(f'{name:<24}{med:>11.2f}{max(ms):>10.2f}{res[-1][1]:>7}{res[-1][2]:>9}{lim:>8.0f}{flag}')
            results.append({'who': label, 'query': name, 'median_ms': round(med, 3), 'worst_ms': round(max(ms), 3), 'rows': res[-1][1], 'buffers': res[-1][2], 'limit_ms': lim})
    if a.json:
        with open(a.json, 'w') as f: json.dump(results, f, indent=1)
    print()
    if bad:
        print('FAIL: %d over the limit or failed' % len(bad))
        for b in bad: print('  %s %s: %s' % b)
        sys.exit(1)
    print('OK: every hot query is within its limit')


if __name__ == '__main__':
    main()
