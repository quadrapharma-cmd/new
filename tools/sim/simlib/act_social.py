"""Social actions: profile, feed, posts, reactions, comments, network, messages, notifications, search (J-SOCIAL-01…51)."""
import datetime, os, urllib.parse as up

from .catalog import action, Fail, Skip, NotBuilt, post_text, comment_text, message_text

PCOLS = 'id,name,headline,company,country,bio,avatar_url,role,verified,location,open_to_work,hiring,profile_views,followers_count,name_needs_fix,name_key'
POST_SEL = up.quote('*,author:profiles!posts_user_id_fkey(%s),post_media(*)' % PCOLS, safe=',*()!:')
KINDS = ['like', 'like', 'like', 'support', 'celebrate', 'insightful', 'appreciation', 'curious']
FIX = os.environ.get('DRUGBOX_FIXTURES', '/tmp/vids')
S = dict(social=1)


# a person's followers: everyone who follows them or is connected to them (connections follow each other), each once
FOLLOWERS_OK = ("select (select followers_count from public.profiles where id=%s) = (select count(*) from (select user_id from public.person_followers where person_id=%s "
                "union select case when requester=%s then addressee else requester end from public.connections where status='accepted' and (requester=%s or addressee=%s)) f)")


def fixture(name, fallback=b''):
    try:
        with open(os.path.join(FIX, name), 'rb') as f: return f.read()
    except OSError: return fallback


def recent_post(x, own=False, group=False):
    if own: row = x.pick("select id from public.posts where user_id=%s and group_id is null order by id desc limit 30", (x.me,))
    elif group: row = x.pick("select p.id from public.posts p join public.group_members m on m.group_id=p.group_id and m.user_id=%s order by p.id desc limit 40", (x.me,))
    else: row = x.pick("select id from public.posts where group_id is null order by id desc limit 60")
    return row[0] if row else None


# ── feed and posts ─────────────────────────────────────────────────────────────────────────────────────────────────────
@action('feed.read', 'social', ['J-SOCIAL-10', 'J-SOCIAL-49'], dict(social=3, trade=1, seek=1, learn=1, group=1))
def feed_read(x):
    a = x.acc
    r = x.ok(a.get('posts', 'select=%s&group_id=is.null&order=created_at.desc,id.desc&limit=20' % POST_SEL), 'the feed page')
    ids = [p['id'] for p in (r.data or [])]
    if not ids: return
    inl = ','.join(map(str, ids))
    x.ok(a.get('reactions', 'select=post_id,kind&user_id=eq.%s&post_id=in.(%s)' % (x.me, inl)), 'my reactions on the page')
    x.ok(a.get('saved_posts', 'select=post_id&user_id=eq.%s&post_id=in.(%s)' % (x.me, inl)), 'my saved posts on the page')
    s = x.ok(a.rpc('post_reaction_summary', {'p_ids': ids[:100]}), 'reaction summary')
    x.ok(a.rpc('increment_post_views', {'post_ids': ids[:20]}), 'post views')
    if x.r.random() < 0.5:   # a second page by the keyset cursor
        last = r.data[-1]; t = up.quote(last['created_at'])
        x.ok(a.get('posts', 'select=%s&group_id=is.null&created_at=lte.%s&or=(created_at.lt.%s,id.lt.%s)&order=created_at.desc,id.desc&limit=20' % (POST_SEL, t, t, last['id'])), 'the next feed page')
    # every like count shown equals the reactions in the database (the counter trigger)
    pid = x.r.choice(ids)
    x.expect("select (select like_count from public.posts where id=%s) = (select count(*) from public.reactions where post_id=%s)", (pid, pid), True, 'post %s like_count equals its reactions' % pid)


@action('post.text', 'social', ['J-SOCIAL-11', 'J-SOCIAL-21'], dict(social=2, trade=1, hire=1, group=0.5))
def post_text_(x):
    body = post_text(x)
    if x.r.random() < 0.25:   # a mention of a connection (the app writes @Name in the text)
        o = x.pick("select p.name from public.connections c join public.profiles p on p.id = case when c.requester=%s then c.addressee else c.requester end where (c.requester=%s or c.addressee=%s) and c.status='accepted' limit 20", (x.me, x.me, x.me))
        if o: body += ' @' + o[0]
    cat = x.r.choice(['general', 'general', 'regulatory', 'market', 'innovation', 'job'])
    d = x.rows(x.acc.insert('posts', {'user_id': x.me, 'body': body, 'category': cat}), 'publish a post')[0]
    x.target = 'post %s' % d['id']
    x.expect("select body from public.posts where id=%s and user_id=%s and category=%s", (d['id'], x.me, cat), lambda v: v is not None and v.strip() == body.strip(), 'the post is stored with its text and category')


@action('post.image', 'social', ['J-SOCIAL-12'], dict(social=1, trade=1))
def post_image(x):
    img = fixture('photo.png'); pdf = fixture('spec.pdf')
    if not img: raise Skip('no photo fixture (tests/fixtures/make_fixtures.py)')
    d = x.rows(x.acc.insert('posts', {'user_id': x.me, 'body': post_text(x), 'category': 'general'}), 'publish a post with a photo')[0]
    rows = []
    for data, ctype, kind, name in [(img, 'image/png', 'image', 'photo')] + ([(pdf, 'application/pdf', 'file', 'spec.pdf')] if pdf and x.r.random() < 0.5 else []):
        path = 'posts/%s/%s-%s.%s' % (x.me, d['id'], x.r.getrandbits(40), 'png' if kind == 'image' else 'pdf')
        x.ok(x.acc.upload('post-media', path, data, ctype), 'upload the %s' % kind)
        rows.append({'post_id': d['id'], 'url': x.sim.base + '/storage/v1/object/public/post-media/' + path, 'type': kind, 'name': name, 'size': len(data)})
    x.ok(x.acc.insert('post_media', rows, select=None), 'attach the files to the post')
    x.target = 'post %s' % d['id']
    x.expect("select count(*) from public.post_media where post_id=%s", (d['id'],), len(rows), 'the post has its files')
    u = rows[0]['url'][len(x.sim.base):]
    g = x.acc.fetch(u)
    if g.status != 200 or len(g.text.encode('latin-1', 'ignore')) == 0: raise Fail('the uploaded photo cannot be read back from Storage: ' + g.repro())


@action('post.react', 'social', ['J-SOCIAL-13', 'J-COMMUNITY-06'], dict(social=4, trade=1, seek=1, learn=1, group=1))
def post_react(x):
    pid = x.need(recent_post(x), 'no posts yet'); kind = x.r.choice(KINDS); x.target = 'post %s' % pid
    x.ok(x.acc.insert('reactions', {'post_id': pid, 'user_id': x.me, 'kind': kind}, select=None, upsert='post_id,user_id'), 'react')
    x.expect("select kind from public.reactions where post_id=%s and user_id=%s", (pid, x.me), kind, 'my reaction is stored')
    x.dbwait("select (select like_count from public.posts where id=%s) = (select count(*) from public.reactions where post_id=%s)", (pid, pid), True, 'like_count equals reactions')


@action('post.unreact', 'social', ['J-SOCIAL-13'], dict(social=1))
def post_unreact(x):
    row = x.need(x.pick("select post_id from public.reactions where user_id=%s order by created_at desc limit 20", (x.me,)), 'no reactions to undo')
    x.target = 'post %s' % row[0]
    x.ok(x.acc.delete('reactions', 'post_id=eq.%s&user_id=eq.%s' % (row[0], x.me), select=None), 'remove my reaction')
    x.expect("select count(*) from public.reactions where post_id=%s and user_id=%s", (row[0], x.me), 0, 'the reaction is gone')
    x.dbwait("select (select like_count from public.posts where id=%s) = (select count(*) from public.reactions where post_id=%s)", (row[0], row[0]), True, 'like_count equals reactions')


@action('post.comment', 'social', ['J-SOCIAL-14'], dict(social=3, trade=1, group=1))
def post_comment(x):
    pid = x.need(recent_post(x), 'no posts yet'); body = comment_text(x); x.target = 'post %s' % pid
    x.ok(x.acc.get('comments', 'select=*,author:profiles!comments_user_id_fkey(%s)&post_id=eq.%s&order=created_at.asc,id.asc&limit=50' % (PCOLS, pid)), 'read the comments')
    d = x.rows(x.acc.insert('comments', {'post_id': pid, 'user_id': x.me, 'body': body}), 'comment')[0]
    x.expect("select body from public.comments where id=%s and user_id=%s", (d['id'], x.me), body, 'the comment is stored')
    x.dbwait("select (select comment_count from public.posts where id=%s) = (select count(*) from public.comments where post_id=%s)", (pid, pid), True, 'comment_count equals comments')


@action('post.reply', 'social', ['J-SOCIAL-15', 'J-COMMUNITY-05'], dict(social=1, group=1), path='api')
def post_reply(x):
    c = x.need(x.pick("select id, post_id from public.comments where parent_id is null order by id desc limit 50"), 'no comments to reply to')
    body = comment_text(x); x.target = 'comment %s' % c[0]
    d = x.rows(x.acc.insert('comments', {'post_id': c[1], 'user_id': x.me, 'body': body, 'parent_id': c[0]}), 'reply to a comment')[0]
    x.expect("select parent_id from public.comments where id=%s", (d['id'],), c[0], 'the reply hangs under its comment')


@action('comment.like', 'social', ['J-SOCIAL-14', 'J-COMMUNITY-05'], dict(social=1))
def comment_like(x): raise NotBuilt('comment likes: no table or request in the live app (FEATURE-STATUS)')


@action('post.repost', 'social', ['J-SOCIAL-16'], dict(social=1, trade=0.5))
def post_repost(x):
    row = x.need(x.pick("select id, body from public.posts where group_id is null and user_id<>%s order by id desc limit 40", (x.me,)), 'nothing to repost')
    pid, body = row; x.target = 'post %s' % pid
    before = x.db.val("select share_count from public.posts where id=%s", (pid,)) or 0
    quote = ('🔁 ' + (body or '')[:300]).strip()
    x.rows(x.acc.insert('posts', {'user_id': x.me, 'body': quote, 'category': 'general'}), 'repost')
    x.ok(x.acc.rpc('increment_post_share', {'p_id': pid}), 'count the share')
    x.dbwait("select share_count from public.posts where id=%s", (pid,), lambda v: (v or 0) >= before, 'share_count did not go down')


@action('post.save', 'social', ['J-SOCIAL-17', 'J-SOCIAL-48'], dict(social=1, learn=1))
def post_save(x):
    pid = x.need(recent_post(x)); x.target = 'post %s' % pid
    if x.db.val("select 1 from public.saved_posts where user_id=%s and post_id=%s", (x.me, pid)):
        x.ok(x.acc.delete('saved_posts', 'user_id=eq.%s&post_id=eq.%s' % (x.me, pid), select=None), 'unsave')
        x.expect("select count(*) from public.saved_posts where user_id=%s and post_id=%s", (x.me, pid), 0, 'unsaved')
    else:
        x.ok(x.acc.insert('saved_posts', {'user_id': x.me, 'post_id': pid}, select=None, upsert='user_id,post_id'), 'save')
        x.expect("select count(*) from public.saved_posts where user_id=%s and post_id=%s", (x.me, pid), 1, 'saved')
    x.ok(x.acc.get('saved_posts', 'select=post_id,created_at&user_id=eq.%s&order=created_at.desc&limit=50' % x.me), 'the Saved page')


@action('post.edit', 'social', ['J-SOCIAL-18'], dict(social=0.5))
def post_edit(x):
    pid = x.need(recent_post(x, own=True), 'no own posts'); x.target = 'post %s' % pid
    body = post_text(x) + ' (edited)'
    x.rows(x.acc.update('posts', 'id=eq.%s' % pid, {'body': body}, select='id'), 'edit my post')
    x.expect("select body from public.posts where id=%s", (pid,), body, 'the new text is stored')


@action('post.delete', 'social', ['J-SOCIAL-19'], dict(social=1), rare=True)
def post_delete(x):
    pid = x.need(recent_post(x, own=True), 'no own posts'); x.target = 'post %s' % pid
    x.rows(x.acc.delete('posts', 'id=eq.%s' % pid, select='id'), 'delete my post')
    x.expect("select count(*) from public.posts where id=%s", (pid,), 0, 'the post is gone')


@action('post.report', 'social', ['J-SOCIAL-20'], dict(social=1), rare=True)
def post_report(x):
    row = x.need(x.pick("select id, user_id from public.posts where group_id is null and user_id<>%s and not exists (select 1 from public.post_reports r where r.post_id=posts.id and r.reporter=%s) order by id desc limit 50", (x.me, x.me)))
    x.target = 'post %s' % row[0]
    x.ok(x.acc.insert('post_reports', {'post_id': row[0], 'reporter': x.me, 'reason': x.r.choice(['spam', 'misleading', 'counterfeit', 'abusive', 'other']), 'note': 'simulated report'}, select=None), 'report a post')
    x.expect("select status from public.post_reports where post_id=%s and reporter=%s", (row[0], x.me), 'open', 'the report waits for review')


# ── profile ────────────────────────────────────────────────────────────────────────────────────────────────────────────
@action('profile.edit', 'social', ['J-SOCIAL-22', 'J-COMMUNITY-27'], dict(social=0.5, seek=1))
def profile_edit(x):
    p = x.p; head = p['headline'] + (' at ' + p['company_name'] if p.get('company_name') else '')
    otw = bool(p.get('open_to_work')) if x.r.random() < 0.8 else not p.get('open_to_work')
    row = {'headline': head[:300], 'company': p.get('company_name'), 'location': '%s, %s' % (p['city'], 'Egypt' if p['country'] == 'EG' else p['country']),
           'website': None, 'phone': '+20 10%08d' % x.r.randrange(10 ** 8), 'certs': None,
           'bio': 'Simulated account (Drugbox activity simulator). %s with %d years in pharma; interested in %s.' % (p['headline'], p.get('years', 0), ', '.join(p.get('interests', []))),
           'open_to_work': otw, 'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    d = x.rows(x.acc.update('profiles', 'id=eq.%s' % x.me, row, select='name,headline,company,location,website,certs,bio,open_to_work,name_needs_fix'), 'save the profile')[0]
    if 'phone' in d: raise Fail('the profile update answer includes the private phone column')
    x.expect("select headline||'|'||open_to_work from public.profiles where id=%s", (x.me,), '%s|%s' % (row['headline'], 'true' if otw else 'false'), 'the profile is stored')
    me = x.ok(x.acc.rpc('my_profile'), 'read my own profile')
    mine = me.data[0] if isinstance(me.data, list) and me.data else me.data
    if not isinstance(mine, dict) or mine.get('phone') != row['phone']: raise Fail('my_profile() does not return my phone (%s)' % str(mine)[:120])
    p['open_to_work'] = otw


@action('profile.rename', 'social', ['J-SOCIAL-22'], dict(social=0.2), rare=True)
def profile_rename(x):
    from .personas import make_name, _rng
    name = make_name(_rng('rename', x.me, x.r.random()))[0]
    prob = x.db.val("select coalesce(public.person_name_problem(public.person_name_norm(%s)),'')", (name,))
    r = x.acc.update('profiles', 'id=eq.%s' % x.me, {'name': name}, select='name,name_needs_fix')
    if prob:   # the browser path must refuse a name the rule refuses
        if r.ok and r.data: raise Fail('a name the rule refuses (%s: %r) was accepted' % (prob, name))
        return
    d = x.rows(r, 'change my name')[0]
    x.expect("select name_key is not null and not name_needs_fix from public.profiles where id=%s", (x.me,), True, 'the new name is keyed and not flagged')
    x.p['name'] = d['name']


@action('profile.experience', 'social', ['J-SOCIAL-25', 'J-SOCIAL-26'], dict(social=0.5, seek=1), path='api')
def profile_experience(x):
    p = x.p
    exp = [dict(e, company=e.get('company') or p.get('company_name')) for e in (p.get('experience') or [])]   # the employer by its page name
    row = {'experience': exp, 'education': p.get('education') or [], 'skills': p.get('skills') or [],
           'years_experience': p.get('years', 0), 'languages': ['Arabic', 'English']}
    x.rows(x.acc.update('profiles', 'id=eq.%s' % x.me, row, select='id'), 'save experience, education and skills')
    x.expect("select cardinality(skills) from public.profiles where id=%s", (x.me,), len(row['skills']), 'the skills are stored')


@action('profile.photo', 'social', ['J-SOCIAL-23'], dict(social=0.3))
def profile_photo(x): raise NotBuilt('profile photo / cover: the live app reads avatar_url but has no upload (FEATURE-STATUS)')


@action('profile.video', 'social', ['J-SOCIAL-24'], dict(social=0.3), rare=True)
def profile_video(x):
    data = fixture('me_intro.webm')
    if not data: raise Skip('no video fixture')
    path = 'people/%s/intro.webm' % x.me
    r = x.acc.c.call('POST', '/storage/v1/object/videos/' + path, token=x.acc.token, raw=data, ctype='video/webm', headers={'x-upsert': 'true'}); x.acc._rec(r)
    x.ok(r, 'upload my intro video')
    val = {'path': path, 'poster': None, 'duration': 3.0, 'v': int(datetime.datetime.now().timestamp() * 1000)}
    x.rows(x.acc.update('profiles', 'id=eq.%s' % x.me, {'intro_video': val}, select='id'), 'save the video on my profile')
    x.expect("select intro_video->>'path' from public.profiles where id=%s", (x.me,), path, 'the profile points at the video')
    g = x.acc.fetch('/storage/v1/object/public/videos/' + path)
    if g.status != 200: raise Fail('the intro video cannot be watched: ' + g.repro())


@action('profile.visit', 'social', ['J-SOCIAL-27'], dict(social=2, trade=1, hire=1))
def profile_visit(x):
    u = x.need(x.other()); x.target = 'person %s' % u
    before = x.db.val("select count(*) from public.profile_view_log where target=%s and viewer=%s", (u, x.me))
    d = x.rows(x.acc.get('profiles', 'select=%s&id=eq.%s' % (PCOLS, u)), 'open a profile')[0]
    if 'phone' in d: raise Fail('another member can read the phone column')
    x.ok(x.acc.rpc('increment_profile_view', {'target': u}), 'count the view')
    x.ok(x.acc.rpc('profile_counts', {'p_id': u}), 'profile counts')
    x.ok(x.acc.get('posts', 'select=%s&user_id=eq.%s&group_id=is.null&order=created_at.desc&limit=20' % (POST_SEL, u)), 'their activity')
    x.dbwait("select count(*) from public.profile_view_log where target=%s and viewer=%s", (u, x.me), lambda v: v >= 1 or before >= 1, 'the visit is logged once per day')
    # privacy probe: select=* on profiles must be refused (0036)
    s = x.acc.get('profiles', 'select=*&id=eq.%s' % u)
    if s.ok and s.data and 'phone' in (s.data[0] or {}): raise Fail('select=* on profiles returns the phone: ' + s.repro())


@action('people.search', 'social', ['J-SOCIAL-28', 'J-SOCIAL-45'], dict(social=1, trade=1, hire=2))
def people_search(x):
    u = x.need(x.other()); q = x.w.people[u]['name'].split()[-1][:6]; x.target = 'search %r' % q
    w = q.replace('%', '').replace('*', '')
    key = x.db.val("select public.person_name_key(%s)", (w,)) or w
    filt = 'or=(name.ilike.%s,name_key.like.%s)' % (up.quote('"*%s*"' % w), up.quote('"*%s*"' % key))
    r = x.ok(x.acc.get('profiles', 'select=%s&%s&id=neq.%s&order=name&limit=12' % (PCOLS, filt, x.me)), 'search people')
    if not isinstance(r.data, list): raise Fail('search did not return a list: ' + r.repro())
    x.ok(x.acc.rpc('directory_companies_page', {'p_limit': 20, 'p_offset': 0, 'p_q': q}), 'search companies from the top bar')


# ── network ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def pair_state(x, u):
    return x.db.one("select status, requester=%s from public.connections where (requester=%s and addressee=%s) or (requester=%s and addressee=%s) order by id desc limit 1", (x.me, x.me, u, u, x.me))


@action('net.connect', 'social', ['J-SOCIAL-29', 'J-SOCIAL-34'], dict(social=2, trade=1, hire=1, seek=1))
def net_connect(x):
    s = x.ok(x.acc.rpc('suggest_people', {'p_limit': 12}), 'people you may know')
    sugg = [r.get('id') for r in (s.data or []) if isinstance(r, dict) and r.get('id') in x.w.people]
    u = x.r.choice(sugg) if sugg and x.r.random() < 0.6 else x.other()
    x.need(u); x.target = 'person %s' % u
    st = pair_state(x, u)
    if st and st[0] in ('pending', 'accepted'): raise Skip('already %s' % st[0])
    r = x.ok(x.acc.insert('connections', {'requester': x.me, 'addressee': u, 'status': 'pending'}, select='id'), 'send a connection request')
    if not r.data:   # they asked me meanwhile: my request accepts theirs (no new row)
        x.expect("select count(*) from public.connections where requester=%s and addressee=%s and status='accepted'", (u, x.me), 1, 'a request to someone who asked me first connects us')
        return
    x.expect("select count(*) from public.connections where requester=%s and addressee=%s and status='pending'", (x.me, u), 1, 'the request is pending')
    x.dbwait("select count(*) from public.notifications where user_id=%s and from_user=%s and type='connection_request'", (u, x.me), lambda v: v >= 1, 'they are notified')


@action('net.accept', 'social', ['J-SOCIAL-30', 'J-SOCIAL-42'], dict(social=3, trade=1, hire=1, seek=1))
def net_accept(x):
    row = x.need(x.pick("select requester from public.connections where addressee=%s and status='pending' limit 30", (x.me,)), 'no pending requests')
    u = row[0]; x.target = 'person %s' % u
    x.ok(x.acc.get('connections', 'select=id,requester,addressee,status,rp:profiles!connections_requester_fkey(%s)&addressee=eq.%s&status=eq.pending&limit=100' % (PCOLS, x.me)), 'the invitations list')
    x.rows(x.acc.update('connections', 'requester=eq.%s&addressee=eq.%s&status=eq.pending' % (u, x.me), {'status': 'accepted'}), 'accept')
    x.expect("select status from public.connections where requester=%s and addressee=%s", (u, x.me), 'accepted', 'connected')
    x.ok(x.acc.rpc('my_network_stats'), 'network numbers')


@action('net.decline', 'social', ['J-SOCIAL-31'], dict(social=0.5))
def net_decline(x):
    row = x.need(x.pick("select requester from public.connections where addressee=%s and status='pending' limit 30", (x.me,)), 'no pending requests')
    u = row[0]; x.target = 'person %s' % u
    x.ok(x.acc.update('connections', 'requester=eq.%s&addressee=eq.%s&status=eq.pending' % (u, x.me), {'status': 'rejected'}, select=None), 'ignore the request')
    x.ok(x.acc.delete('notifications', 'user_id=eq.%s&from_user=eq.%s&type=eq.connection_request' % (x.me, u), select=None), 'clear its notification')
    x.expect("select status from public.connections where requester=%s and addressee=%s", (u, x.me), 'rejected', 'declined')


@action('net.withdraw', 'social', ['J-SOCIAL-29'], dict(social=0.3))
def net_withdraw(x):
    row = x.need(x.pick("select addressee from public.connections where requester=%s and status='pending' and created_at < now() - interval '2 minutes' limit 30", (x.me,)), 'no old pending requests')
    u = row[0]; x.target = 'person %s' % u
    x.ok(x.acc.delete('connections', 'requester=eq.%s&addressee=eq.%s&status=eq.pending' % (x.me, u), select=None), 'withdraw my request')
    x.expect("select count(*) from public.connections where requester=%s and addressee=%s and status='pending'", (x.me, u), 0, 'withdrawn')


@action('net.remove', 'social', ['J-SOCIAL-32'], dict(social=0.2), rare=True)
def net_remove(x):
    row = x.need(x.pick("select case when requester=%s then addressee else requester end from public.connections where (requester=%s or addressee=%s) and status='accepted' limit 50", (x.me, x.me, x.me)), 'no connections')
    u = row[0]; x.target = 'person %s' % u
    x.rows(x.acc.delete('connections', 'requester=in.(%s,%s)&addressee=in.(%s,%s)&status=eq.accepted' % (x.me, u, x.me, u), select='id'), 'remove a connection')
    x.expect("select count(*) from public.connections where ((requester=%s and addressee=%s) or (requester=%s and addressee=%s)) and status='accepted'", (x.me, u, u, x.me), 0, 'no longer connected')


@action('net.follow', 'social', ['J-SOCIAL-33'], dict(social=1, trade=0.5))
def net_follow(x):
    u = x.need(x.other()); x.target = 'person %s' % u
    if x.db.val("select 1 from public.person_followers where person_id=%s and user_id=%s", (u, x.me)):
        x.ok(x.acc.delete('person_followers', 'user_id=eq.%s&person_id=eq.%s' % (x.me, u), select=None), 'unfollow')
        x.expect("select count(*) from public.person_followers where person_id=%s and user_id=%s", (u, x.me), 0, 'unfollowed')
    else:
        x.ok(x.acc.insert('person_followers', {'person_id': u, 'user_id': x.me}, select=None), 'follow')
        x.expect("select count(*) from public.person_followers where person_id=%s and user_id=%s", (u, x.me), 1, 'following')
    x.dbwait(FOLLOWERS_OK, (u, u, u, u, u), True, 'followers_count = people who follow or are connected')


@action('net.dismiss', 'social', ['J-SOCIAL-34'], dict(social=0.5))
def net_dismiss(x):
    s = x.ok(x.acc.rpc('suggest_people', {'p_limit': 12}), 'people you may know')
    sugg = [r.get('id') for r in (s.data or []) if isinstance(r, dict) and r.get('id')]
    u = x.need(x.r.choice(sugg) if sugg else None, 'no suggestions'); x.target = 'person %s' % u
    x.ok(x.acc.insert('people_dismissed', {'person_id': u, 'user_id': x.me}, select=None), 'dismiss a suggestion', allow=(409,))
    s2 = x.ok(x.acc.rpc('suggest_people', {'p_limit': 12}), 'suggestions again')
    if any(isinstance(r, dict) and r.get('id') == u for r in (s2.data or [])): raise Fail('a dismissed person is suggested again')


# ── messages ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def partner(x):
    row = x.pick("select partner from public.conversation_heads where owner=%s order by last_at desc limit 15", (x.me,))
    if row and x.r.random() < 0.7: return row[0]
    row = x.pick("select case when requester=%s then addressee else requester end from public.connections where (requester=%s or addressee=%s) and status='accepted' limit 40", (x.me, x.me, x.me))
    return row[0] if row else x.other()


def blocked(x, u):
    return x.db.val("select exists(select 1 from public.user_blocks where (blocker=%s and blocked=%s) or (blocker=%s and blocked=%s))", (x.me, u, u, x.me))


@action('msg.send', 'social', ['J-SOCIAL-35', 'J-SOCIAL-36', 'J-COMMUNITY-28', 'J-BUSINESS-35'], dict(social=3, trade=3, hire=2, seek=1, group=0.5))
def msg_send(x):
    u = x.need(partner(x)); x.target = 'person %s' % u
    x.ok(x.acc.rpc('my_conversations', {'p_limit': 50}), 'the conversations list')
    x.ok(x.acc.rpc('conversation_messages', {'p_partner': u, 'p_limit': 50}), 'open the conversation')
    body = message_text(x)
    r = x.acc.insert('messages', {'sender_id': x.me, 'receiver_id': u, 'body': body})
    if blocked(x, u):
        if r.ok and r.data: raise Fail('a message reached someone across a block')
        return
    d = x.rows(r, 'send a message')[0]
    x.expect("select body from public.messages where id=%s and sender_id=%s and receiver_id=%s", (d['id'], x.me, u), body, 'the message is stored')
    x.dbwait("select unread from public.conversation_heads where owner=%s and partner=%s", (u, x.me), lambda v: (v or 0) >= 1, 'their conversation shows it unread')


@action('msg.attach', 'social', ['J-SOCIAL-37'], dict(social=0.5, trade=1))
def msg_attach(x):
    u = x.need(partner(x)); x.target = 'person %s' % u
    if blocked(x, u): raise Skip('blocked')
    photo = x.r.random() < 0.5; data = fixture('photo.png' if photo else 'spec.pdf')
    if not data: raise Skip('no fixtures')
    path = '%s/%s/%s.%s' % (x.me, u, x.r.getrandbits(48), 'png' if photo else 'pdf')
    x.ok(x.acc.upload('message-media', path, data, 'image/png' if photo else 'application/pdf'), 'upload the attachment')
    att = {'path': path, 'name': 'photo.png' if photo else 'CoA.pdf', 'size': len(data), 'kind': 'photo' if photo else 'file'}
    d = x.rows(x.acc.insert('messages', {'sender_id': x.me, 'receiver_id': u, 'body': '' if photo else '📎 CoA.pdf', 'image_url': path if photo else None, 'attachment': att}, select='id,read_at'), 'send the attachment')[0]
    x.expect("select attachment->>'path' from public.messages where id=%s", (d['id'],), path, 'the message carries the file')
    s = x.ok(x.acc.c.call('POST', '/storage/v1/object/sign/message-media', {'expiresIn': 600, 'paths': [path]}, token=x.acc.token), 'a signed link for the file')
    link = (s.data or [{}])[0].get('signedURL') if isinstance(s.data, list) else None
    if not link: raise Fail('no signed link for my own attachment: ' + s.repro())
    g = x.acc.fetch('/storage/v1' + link)
    if g.status != 200: raise Fail('the signed link does not open the file: ' + g.repro())


@action('msg.read', 'social', ['J-SOCIAL-38', 'J-SOCIAL-39'], dict(social=3, trade=2, hire=1, seek=1))
def msg_read(x):
    row = x.need(x.pick("select partner from public.conversation_heads where owner=%s and unread>0 limit 20", (x.me,)), 'no unread conversations')
    u = row[0]; x.target = 'person %s' % u
    x.ok(x.acc.rpc('conversation_messages', {'p_partner': u, 'p_limit': 50}), 'open the conversation')
    x.ok(x.acc.update('messages', 'sender_id=eq.%s&receiver_id=eq.%s&read_at=is.null' % (u, x.me), {'read_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, select=None), 'mark read')
    x.expect("select count(*) from public.messages where sender_id=%s and receiver_id=%s and read_at is null", (u, x.me), 0, 'all read')
    x.dbwait("select coalesce(unread,0) from public.conversation_heads where owner=%s and partner=%s", (x.me, u), 0, 'the unread count is 0')
    if x.r.random() < 0.3:   # search in messages
        x.ok(x.acc.get('messages', 'select=id,body,sender_id,receiver_id,created_at&or=(sender_id.eq.%s,receiver_id.eq.%s)&body=ilike.%s&order=id.desc&limit=100' % (x.me, x.me, up.quote('*price*'))), 'search my messages')
    x.ok(x.acc.rpc('new_messages', {'p_after': 0}), 'the new-messages poll')


@action('msg.mute', 'social', ['J-SOCIAL-40'], dict(social=0.3), rare=True)
def msg_mute(x):
    u = x.need(partner(x)); x.target = 'person %s' % u
    if x.db.val("select 1 from public.conversation_mutes where owner=%s and partner=%s", (x.me, u)):
        x.ok(x.acc.delete('conversation_mutes', 'owner=eq.%s&partner=eq.%s' % (x.me, u), select=None), 'unmute')
        x.expect("select count(*) from public.conversation_mutes where owner=%s and partner=%s", (x.me, u), 0, 'unmuted')
    else:
        x.ok(x.acc.insert('conversation_mutes', {'owner': x.me, 'partner': u}, select=None, upsert='owner,partner', ignore=True), 'mute')
        x.expect("select count(*) from public.conversation_mutes where owner=%s and partner=%s", (x.me, u), 1, 'muted')


@action('msg.block', 'social', ['J-SOCIAL-40'], dict(social=0.2), rare=True)
def msg_block(x):
    u = x.need(partner(x)); x.target = 'person %s' % u
    x.ok(x.acc.insert('user_blocks', {'blocker': x.me, 'blocked': u}, select=None, upsert='blocker,blocked', ignore=True), 'block')
    x.expect("select count(*) from public.user_blocks where blocker=%s and blocked=%s", (x.me, u), 1, 'blocked')
    # the blocked person's message must not arrive
    other = x.sim.acc_of(u)
    if other and other.ensure():
        r = other.insert('messages', {'sender_id': u, 'receiver_id': x.me, 'body': 'are you there?'})
        if r.ok and r.data: raise Fail('a blocked person could still send a message (%s)' % r.repro())
    if x.r.random() < 0.5:   # most people unblock later
        x.ok(x.acc.delete('user_blocks', 'blocker=eq.%s&blocked=eq.%s' % (x.me, u), select=None), 'unblock')


@action('msg.report', 'social', ['J-SOCIAL-40'], dict(social=0.2), rare=True)
def msg_report(x):
    row = x.need(x.pick("select sender_id from public.messages where receiver_id=%s order by id desc limit 20", (x.me,)), 'nobody wrote to me')
    x.target = 'person %s' % row[0]
    x.ok(x.acc.insert('message_reports', {'reporter': x.me, 'reported': row[0], 'reason': 'Spam', 'details': 'simulated report'}, select=None), 'report a conversation')
    x.expect("select count(*) from public.message_reports where reporter=%s and reported=%s and status='open'", (x.me, row[0]), lambda v: v >= 1, 'the report waits for review')


# ── notifications, saved, search ───────────────────────────────────────────────────────────────────────────────────────
@action('notif.read', 'social', ['J-SOCIAL-41', 'J-SOCIAL-42', 'J-SOCIAL-43', 'J-COMMUNITY-18', 'J-COMMUNITY-48'], dict(social=2, trade=1, hire=1, seek=1, learn=1, group=1))
def notif_read(x):
    a = x.acc
    r = x.ok(a.get('notifications', 'select=*,actor:profiles!notifications_from_user_fkey(%s),company:companies(name)&user_id=eq.%s&order=created_at.desc&limit=50' % (PCOLS, x.me)), 'the notifications list')
    rows = r.data or []
    if any(n.get('user_id') != x.me for n in rows): raise Fail("another person's notification is in my list")
    unread = [n for n in rows if not n.get('read')]
    if not unread: raise Skip('no unread notifications')
    if x.r.random() < 0.5:
        x.ok(a.update('notifications', 'user_id=eq.%s&read=eq.false' % x.me, {'read': True}, select=None), 'mark all read')
        x.expect("select count(*) from public.notifications where user_id=%s and not read", (x.me,), lambda v: v <= 3, 'all read (new ones may arrive meanwhile)')
    else:
        n = x.r.choice(unread)
        x.ok(a.update('notifications', 'id=eq.%s' % n['id'], {'read': True}, select=None), 'open one notification')
        x.expect("select read from public.notifications where id=%s", (n['id'],), True, 'it is read')
    if x.r.random() < 0.15:
        old = [n['id'] for n in rows if n.get('read')][:5]
        if old:
            x.ok(a.delete('notifications', 'user_id=eq.%s&id=in.(%s)' % (x.me, ','.join(map(str, old))), select=None), 'clear old notifications')
            x.expect("select count(*) from public.notifications where id = any(%s)", (old,), 0, 'cleared')


@action('notif.prefs', 'social', ['J-SOCIAL-44'], dict(social=0.1))
def notif_prefs(x): raise NotBuilt('notification and e-mail preferences: no table or request in the live app')


@action('search.saved', 'social', ['J-SOCIAL-47'], dict(social=0.1, seek=0.3))
def search_saved(x): raise NotBuilt('saved searches and alerts: no table or request in the live app')


@action('account.settings', 'social', ['J-SOCIAL-02', 'J-SOCIAL-05', 'J-SOCIAL-06', 'J-SOCIAL-07'], dict(social=0.05))
def account_settings(x):
    r = x.acc.c.call('PUT', '/auth/v1/user', {'password': x.acc.pw}, token=x.acc.token)
    if r.status == 405 and x.sim.target['kind'] == 'local': raise NotBuilt('password / e-mail change, reset and account deletion: Auth e-mails are not emulated by the local stack')
    x.ok(r, 'change the password')


@action('admin.suspend_person', 'social', ['J-SOCIAL-51'], who='admin')
def admin_suspend(x): raise NotBuilt('suspending a spam account: no request in the live app (companies only)')


@action('ticker.read', 'social', ['J-SOCIAL-49'], dict(social=0.5, trade=1, seek=1))
def ticker_read(x):
    x.ok(x.acc.rpc('ticker_feed'), 'the ticker'); x.ok(x.acc.rpc('market_stats'), 'market numbers'); x.ok(x.acc.rpc('jobs_stats'), 'jobs numbers')
    x.ok(x.acc.get('profiles', 'select=id,avatar_url&avatar_url=not.is.null&order=created_at.desc&limit=6'), 'faces on Home')
