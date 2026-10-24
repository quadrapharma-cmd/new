"""Community actions: groups (and their admins), jobs, the trust layer, training, and Drugbox moderation by the sim admin
(J-COMMUNITY-01…50, J-BUSINESS-49, J-SOCIAL-20/51)."""
import datetime, urllib.parse as up

from .catalog import action, Fail, Skip, NotBuilt, post_text, comment_text
from .act_social import PCOLS, KINDS, fixture
from .act_business import my_companies, my_company, sim_company, create_deal
from .personas import APIS

GCOLS = up.quote('*,creator:profiles!groups_created_by_fkey(%s)' % PCOLS, safe=',*()!:')
GROUPS = [('Egypt QA & GMP Forum', 'Audits, CAPA, deviations and inspection readiness', 'public', 'DISCUSS'),
          ('Regulatory Affairs Egypt', 'EDA submissions, variations, pricing and renewals', 'public', 'DISCUSS'),
          ('Pharmacy Owners Network', 'Community pharmacy business, stock and regulation', 'public', 'DISCUSS'),
          ('API Sourcing Deal Room', 'Members trade APIs and excipients — offers and RFQs', 'private', 'DEAL ROOM'),
          ('Medical Reps Cairo', 'Field force tips, jobs and territories', 'public', 'DISCUSS'),
          ('Stability & Validation Club', 'Protocols, Zone IVb, method validation', 'public', 'DISCUSS'),
          ('Women in Pharma Egypt', 'Mentoring and careers', 'private', 'DISCUSS'),
          ('Cold Chain Logistics', 'Vaccines, biologics and temperature control', 'public', 'DISCUSS')]


def my_groups(x, admin=False):
    return x.db.q("select g.id, g.type, g.topic from public.groups g join public.group_members m on m.group_id=g.id and m.user_id=%s" + (" and m.role='admin'" if admin else ''), (x.me,))


# ── groups ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
@action('group.browse', 'community', ['J-COMMUNITY-01', 'J-COMMUNITY-02', 'J-COMMUNITY-03', 'J-COMMUNITY-07', 'J-COMMUNITY-08'], dict(group=3, social=1))
def group_browse(x):
    a = x.acc
    r = x.ok(a.get('groups', 'select=%s&order=member_count.desc,created_at.desc&limit=60' % GCOLS), 'the groups list')
    x.ok(a.get('group_members', 'select=group_id,role&user_id=eq.%s' % x.me), 'my groups')
    x.ok(a.get('group_invites', 'select=group_id,g:groups(%s)&user_id=eq.%s&limit=50' % (GCOLS, x.me)), 'my invitations')
    ids = [g['id'] for g in (r.data or [])]
    if ids: x.ok(a.rpc('group_activity', {'p_ids': ids}), 'group activity')
    mine = my_groups(x)
    if mine:
        gid = x.r.choice(mine)[0]; x.target = 'group %s' % gid
        sel = up.quote('*,author:profiles!posts_user_id_fkey(%s),post_media(*),my:reactions(kind,user_id),sv:saved_posts(user_id),cm:comments(post_id,user_id,body,created_at,author:profiles!comments_user_id_fkey(%s))' % (PCOLS, PCOLS), safe=',*()!:')
        x.ok(a.get('posts', 'select=%s&group_id=eq.%s&my.user_id=eq.%s&sv.user_id=eq.%s&cm.order=created_at.desc,id.desc&cm.limit=20&order=created_at.desc&limit=20' % (sel, gid, x.me, x.me)), 'the group discussion')
        x.ok(a.get('group_members', 'select=user_id,role,joined_at,p:profiles(%s)&group_id=eq.%s&limit=200' % (PCOLS, gid)), 'the members tab')
    # privacy probe: the posts of a private group I am not in stay hidden
    g = x.pick("select id from public.groups where type='private' and not exists (select 1 from public.group_members m where m.group_id=groups.id and m.user_id=%s) and created_by<>%s", (x.me, x.me))
    if g:
        p = x.ok(a.get('posts', 'select=id&group_id=eq.%s&limit=5' % g[0]), "a private group's posts")
        if p.data: raise Fail('posts of a private group are readable by a non-member (group %s)' % g[0])


@action('group.create', 'community', ['J-COMMUNITY-12', 'J-COMMUNITY-13'], dict(group=0.6, trade=0.2), rare=True)
def group_create(x):
    name, desc, typ, topic = x.r.choice(GROUPS)
    name = '%s %s' % (name, x.p.get('city', ''))[:110]
    if x.db.val("select 1 from public.groups where name=%s", (name,)): raise Skip('exists')
    d = x.rows(x.acc.insert('groups', {'name': name, 'description': desc + ' (simulated)', 'emoji': '🤝' if topic == 'DEAL ROOM' else '👥', 'type': typ, 'topic': topic, 'created_by': x.me,
                                        'listed': not (typ == 'private' and topic == 'DEAL ROOM')}), 'create a group')[0]
    x.target = 'group %s' % d['id']
    x.dbwait("select role from public.group_members where group_id=%s and user_id=%s", (d['id'], x.me), 'admin', 'the creator is the group admin')
    x.dbwait("select member_count from public.groups where id=%s", (d['id'],), 1, 'member_count is 1')


@action('group.join', 'community', ['J-COMMUNITY-09', 'J-COMMUNITY-10'], dict(group=2, social=0.5, learn=0.5))
def group_join(x):
    g = x.need(x.pick("select id, type from public.groups where (type='public' or listed) and not exists (select 1 from public.group_members m where m.group_id=groups.id and m.user_id=%s) "
                      "and not exists (select 1 from public.group_join_requests r where r.group_id=groups.id and r.user_id=%s and r.status='pending')", (x.me, x.me)), 'no group to join')
    gid, typ = g; x.target = 'group %s (%s)' % (gid, typ)
    before = x.db.val("select member_count from public.groups where id=%s", (gid,))
    if typ == 'public':
        x.ok(x.acc.insert('group_members', {'group_id': gid, 'user_id': x.me, 'role': 'member'}, select=None), 'join the group')
        x.expect("select role from public.group_members where group_id=%s and user_id=%s", (gid, x.me), 'member', 'a member')
        x.dbwait("select member_count = (select count(*) from public.group_members where group_id=%s) from public.groups where id=%s", (gid, gid), True, 'member_count equals members')
    else:
        x.ok(x.acc.rpc('group_request_join', {'p_group': gid, 'p_message': 'I work in %s (simulated)' % x.p.get('headline', 'pharma')}), 'ask to join a private group')
        x.expect("select status from public.group_join_requests where group_id=%s and user_id=%s", (gid, x.me), 'pending', 'the request waits for an admin')
        r = x.ok(x.acc.insert('group_members', {'group_id': gid, 'user_id': x.me, 'role': 'member'}, select=None), 'join a private group directly', allow=(401, 403, 409))
        x.expect("select count(*) from public.group_members where group_id=%s and user_id=%s", (gid, x.me), 0, 'not a member without approval')


@action('group.leave', 'community', ['J-COMMUNITY-09'], dict(group=0.3), rare=True)
def group_leave(x):
    g = x.need(x.pick("select m.group_id from public.group_members m join public.groups g on g.id=m.group_id where m.user_id=%s and m.role='member'", (x.me,)), 'in no group')
    x.target = 'group %s' % g[0]
    x.rows(x.acc.delete('group_members', 'group_id=eq.%s&user_id=eq.%s' % (g[0], x.me), select='user_id'), 'leave the group')
    x.dbwait("select member_count = (select count(*) from public.group_members where group_id=%s) from public.groups where id=%s", (g[0], g[0]), True, 'member_count equals members')


@action('group.post', 'community', ['J-COMMUNITY-04', 'J-COMMUNITY-13'], dict(group=2, trade=0.5))
def group_post(x):
    g = x.need(x.r.choice(my_groups(x)) if my_groups(x) else None, 'in no group')
    cat = 'market' if g[2] == 'DEAL ROOM' else x.r.choice(['general', 'regulatory', 'innovation'])
    body = post_text(x)
    d = x.rows(x.acc.insert('posts', {'user_id': x.me, 'body': body, 'category': cat, 'group_id': g[0]}), 'post in the group')[0]
    x.target = 'group %s post %s' % (g[0], d['id'])
    x.expect("select group_id from public.posts where id=%s", (d['id'],), g[0], 'the post is in the group')
    o = x.pick("select id from public.profiles p where not exists (select 1 from public.group_members m where m.group_id=%s and m.user_id=p.id) and id <> %s and exists (select 1 from auth.users u where u.id=p.id and u.email like '%%@sim.drugbox.test') limit 20", (g[0], x.me))
    if o and g[1] == 'private':
        acc = x.sim.acc_of(o[0])
        if acc and acc.ensure():
            r = acc.get('posts', 'select=id&id=eq.%s' % d['id'])
            if r.ok and r.data: raise Fail('a non-member reads a private group post (%s)' % d['id'])


@action('group.comment', 'community', ['J-COMMUNITY-05', 'J-COMMUNITY-06'], dict(group=2))
def group_comment(x):
    from .act_social import recent_post
    pid = x.need(recent_post(x, group=True), 'no group posts'); x.target = 'post %s' % pid
    if x.r.random() < 0.5:
        x.ok(x.acc.insert('reactions', {'post_id': pid, 'user_id': x.me, 'kind': x.r.choice(KINDS)}, select=None, upsert='post_id,user_id'), 'like a group post')
        x.dbwait("select (select like_count from public.posts where id=%s) = (select count(*) from public.reactions where post_id=%s)", (pid, pid), True, 'like_count equals reactions')
    else:
        x.ok(x.acc.insert('comments', {'post_id': pid, 'user_id': x.me, 'body': comment_text(x)}, select=None), 'comment in the group')
        x.dbwait("select (select comment_count from public.posts where id=%s) = (select count(*) from public.comments where post_id=%s)", (pid, pid), True, 'comment_count equals comments')


@action('group.invite', 'community', ['J-COMMUNITY-11'], dict(group=0.5))
def group_invite(x):
    g = x.need(x.r.choice(my_groups(x, admin=True)) if my_groups(x, admin=True) else None, 'admin of no group')
    u = x.need(x.other()); x.target = 'group %s → %s' % (g[0], u)
    if x.db.val("select 1 from public.group_members where group_id=%s and user_id=%s", (g[0], u)): raise Skip('already a member')
    x.ok(x.acc.insert('group_invites', [{'group_id': g[0], 'user_id': u, 'invited_by': x.me}], select=None, upsert='group_id,user_id', ignore=True), 'invite to the group')
    x.expect("select count(*) from public.group_invites where group_id=%s and user_id=%s", (g[0], u), 1, 'invited')


@action('group.admin', 'community', ['J-COMMUNITY-10', 'J-COMMUNITY-14', 'J-COMMUNITY-16', 'J-COMMUNITY-17'], dict(group=1))
def group_admin(x):
    mine = my_groups(x, admin=True); g = x.need(x.r.choice(mine) if mine else None, 'admin of no group'); gid = g[0]; x.target = 'group %s' % gid
    req = x.pick("select user_id from public.group_join_requests where group_id=%s and status='pending'", (gid,))
    roll = x.r.random()
    if req:
        yes = x.r.random() < 0.85
        x.ok(x.acc.rpc('group_decide_request', {'p_group': gid, 'p_user': req[0], 'p_approve': yes}), 'decide a join request')
        x.expect("select count(*) from public.group_members where group_id=%s and user_id=%s", (gid, req[0]), 1 if yes else 0, 'approved → member, rejected → not')
    elif roll < 0.4:
        p = x.need(x.pick("select id from public.posts where group_id=%s order by id desc limit 10", (gid,)), 'no posts to pin')
        x.ok(x.acc.rpc('group_pin_post', {'p_group': gid, 'p_post': p[0]}), 'pin a post')
        x.expect("select pinned_post_id from public.groups where id=%s", (gid,), p[0], 'pinned')
    elif roll < 0.7:
        m = x.need(x.pick("select user_id from public.group_members where group_id=%s and role='member'", (gid,)), 'no members')
        x.rows(x.acc.update('group_members', 'group_id=eq.%s&user_id=eq.%s' % (gid, m[0]), {'role': 'admin'}, select='user_id'), 'make a member admin')
        x.expect("select role from public.group_members where group_id=%s and user_id=%s", (gid, m[0]), 'admin', 'now an admin')
    else:
        rules = 'Be respectful. No spam. Offers only in the Deal Room. (simulated)'
        x.rows(x.acc.update('groups', 'id=eq.%s' % gid, {'rules': rules}), 'edit the group settings')
        x.expect("select rules from public.groups where id=%s", (gid,), rules, 'saved')


@action('group.report', 'community', ['J-COMMUNITY-15'], dict(group=0.3), rare=True)
def group_report(x):
    p = x.need(x.pick("select p.id, p.group_id from public.posts p join public.group_members m on m.group_id=p.group_id and m.user_id=%s where p.user_id<>%s and not exists (select 1 from public.group_post_reports r where r.post_id=p.id and r.reporter=%s) limit 20", (x.me, x.me, x.me)), 'nothing to report')
    x.target = 'post %s' % p[0]
    x.ok(x.acc.insert('group_post_reports', {'post_id': p[0], 'reporter': x.me, 'reason': 'Off-topic advertising (simulated)'}, select=None), 'report a group post')
    x.expect("select status from public.group_post_reports where post_id=%s and reporter=%s", (p[0], x.me), 'open', 'the report waits for the group admins')


@action('group.reports_review', 'community', ['J-COMMUNITY-15'], dict(group=0.5))
def group_reports_review(x):
    gids = [g[0] for g in my_groups(x, admin=True)]
    rep = x.need(x.pick("select post_id, group_id from public.group_post_reports where status='open' and group_id = any(%s)", (gids,)), 'no reports in my groups')
    x.target = 'post %s' % rep[0]
    if x.r.random() < 0.5:
        x.rows(x.acc.delete('posts', 'id=eq.%s' % rep[0], select='id'), 'remove the reported post')
        x.expect("select count(*) from public.posts where id=%s", (rep[0],), 0, 'removed')
    else:
        x.rows(x.acc.update('group_post_reports', 'group_id=eq.%s&post_id=eq.%s&status=eq.open' % (rep[1], rep[0]), {'status': 'dismissed'}, select='post_id'), 'dismiss the report')
        x.expect("select count(*) from public.group_post_reports where post_id=%s and status='open'", (rep[0],), 0, 'dismissed')


# ── jobs ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
JOB_TITLES = [('QC Analyst', 'qaqc'), ('QA Specialist', 'qaqc'), ('Regulatory Affairs Specialist', 'regulatory'), ('Production Supervisor', 'production'),
              ('Medical Representative', 'sales'), ('Key Account Manager', 'sales'), ('Formulation Scientist', 'rd'), ('Warehouse Pharmacist', 'other'), ('Pharmacovigilance Officer', 'regulatory')]


@action('job.search', 'community', ['J-COMMUNITY-19'], dict(seek=4, hire=0.5, social=0.3))
def job_search(x):
    a = x.acc
    r = x.ok(a.get('jobs', 'select=*,poster:profiles!jobs_user_id_fkey(%s)&active=eq.true&order=created_at.desc&limit=60' % PCOLS), 'the jobs list')
    cat = x.r.choice(['qaqc', 'regulatory', 'sales', 'production'])
    x.ok(a.get('jobs', 'select=id,title&active=eq.true&category=eq.%s&location=ilike.%s&limit=60' % (cat, up.quote('*%s*' % x.p.get('city', 'Cairo')))), 'filter jobs')
    x.ok(a.rpc('jobs_stats'), 'jobs numbers')
    x.ok(a.get('saved_jobs', 'select=job_id&user_id=eq.%s' % x.me), 'my saved jobs')
    x.ok(a.get('job_applications', 'select=job_id,status,created_at&user_id=eq.%s' % x.me), 'my applications')


@action('job.save', 'community', ['J-COMMUNITY-20'], dict(seek=2))
def job_save(x):
    j = x.need(x.pick("select id from public.jobs where active and user_id<>%s order by id desc limit 40", (x.me,)), 'no jobs'); x.target = 'job %s' % j[0]
    if x.db.val("select 1 from public.saved_jobs where user_id=%s and job_id=%s", (x.me, j[0])):
        x.ok(x.acc.delete('saved_jobs', 'user_id=eq.%s&job_id=eq.%s' % (x.me, j[0]), select=None), 'unsave the job')
        x.expect("select count(*) from public.saved_jobs where user_id=%s and job_id=%s", (x.me, j[0]), 0, 'unsaved')
    else:
        x.ok(x.acc.insert('saved_jobs', {'user_id': x.me, 'job_id': j[0]}, select=None, upsert='user_id,job_id'), 'save the job')
        x.expect("select count(*) from public.saved_jobs where user_id=%s and job_id=%s", (x.me, j[0]), 1, 'saved')


@action('job.apply', 'community', ['J-COMMUNITY-21'], dict(seek=3))
def job_apply(x):
    j = x.need(x.pick("select id from public.jobs j where active and user_id<>%s and not exists (select 1 from public.job_applications a where a.job_id=j.id and a.user_id=%s) order by id desc limit 40", (x.me, x.me)), 'no new jobs')
    jid = j[0]; x.target = 'job %s' % jid
    cv = None
    if x.r.random() < 0.7:
        cv = 'cv/%s/%s.pdf' % (x.me, x.r.getrandbits(48))
        x.ok(x.acc.upload('documents', cv, fixture('spec.pdf') or b'%PDF-1.4\n%%EOF\n', 'application/pdf'), 'upload my CV')
    before = x.db.val("select applicant_count from public.jobs where id=%s", (jid,)) or 0
    x.ok(x.acc.insert('job_applications', {'job_id': jid, 'user_id': x.me, 'note': 'I have %d years in %s. (simulated)' % (x.p.get('years', 1), x.p.get('headline')), 'status': 'submitted', 'cv_path': cv}, select=None), 'apply')
    x.expect("select status from public.job_applications where job_id=%s and user_id=%s", (jid, x.me), 'submitted', 'the application is stored')
    x.dbwait("select applicant_count from public.jobs where id=%s", (jid,), lambda v: (v or 0) == before + 1, 'applicant_count +1')
    dup = x.acc.insert('job_applications', {'job_id': jid, 'user_id': x.me, 'note': 'again', 'status': 'submitted'}, select=None)
    if dup.ok: raise Fail('the same person could apply twice to one job')
    if cv:   # the poster can read the CV through a signed link; another member cannot
        poster = x.sim.acc_of(x.db.val("select user_id from public.jobs where id=%s", (jid,)))
        if poster and poster.ensure():
            s = poster.sign('documents', cv)
            if not s.ok: raise Fail('the job poster cannot open the CV: ' + s.repro())
        o = x.sim.acc_of(x.other())
        if o and o.ensure() and o.uid != (poster.uid if poster else None):
            s2 = o.sign('documents', cv)
            if s2.ok: raise Fail('a stranger can open my CV: ' + s2.repro())


@action('job.apply_company', 'community', ['J-BUSINESS-11'], dict(seek=1))
def job_apply_company(x):
    to = x.need(sim_company(x, exclude=[r[0] for r in my_companies(x)]), 'no company')
    create_deal(x, 'job', to, None, 'Application: %s' % x.p.get('headline', 'Pharmacist'), {'role': x.p.get('headline'), 'years': x.p.get('years', 1)}, 'I would like to join your team (simulated).')


@action('job.withdraw', 'community', ['J-COMMUNITY-22'], dict(seek=0.3), rare=True)
def job_withdraw(x):
    a = x.need(x.pick("select job_id from public.job_applications where user_id=%s and status='submitted'", (x.me,)), 'no applications'); x.target = 'job %s' % a[0]
    x.ok(x.acc.delete('job_applications', 'job_id=eq.%s&user_id=eq.%s' % (a[0], x.me), select=None), 'withdraw my application')
    x.expect("select count(*) from public.job_applications where job_id=%s and user_id=%s", (a[0], x.me), 0, 'withdrawn')
    x.dbwait("select applicant_count = (select count(*) from public.job_applications where job_id=%s) from public.jobs where id=%s", (a[0], a[0]), True, 'applicant_count equals applications')


@action('job.post', 'community', ['J-COMMUNITY-23'], dict(hire=3, trade=0.3), who='company')
def job_post(x):
    cid, slug, role = my_company(x, ('owner', 'admin', 'hr'), 'cannot hire for a company')
    if x.db.val("select count(*) from public.jobs where user_id=%s and active", (x.me,)) >= 6: raise Skip('enough open jobs')
    t, cat = x.r.choice(JOB_TITLES); co = x.db.val("select name from public.companies where id=%s", (cid,))
    row = {'user_id': x.me, 'title': t, 'company': co, 'location': x.p.get('city', 'Cairo'), 'country': 'EG', 'type': x.r.choice(['Full-time', 'Full-time', 'Contract']),
           'seniority': x.r.choice(['Junior', 'Mid', 'Senior']), 'description': 'Join %s as %s. Simulated job post.' % (co, t), 'tags': ['GMP', 'Pharma'], 'salary': None,
           'active': True, 'category': cat, 'remote': False, 'deadline': str(datetime.date.today() + datetime.timedelta(days=30)), 'requirements': ['B.Sc. Pharmacy']}
    d = x.rows(x.acc.insert('jobs', row), 'post a job')[0]; x.target = 'job %s' % d['id']
    x.expect("select active and applicant_count = 0 from public.jobs where id=%s", (d['id'],), True, 'the job is open with no applicants')


@action('job.manage', 'community', ['J-COMMUNITY-24', 'J-COMMUNITY-25', 'J-COMMUNITY-26'], dict(hire=3), path='api')
def job_manage(x):
    a = x.need(x.pick("select ja.job_id, ja.user_id, ja.status from public.job_applications ja join public.jobs j on j.id=ja.job_id where j.user_id=%s and ja.status not in ('hired','rejected','no_show')", (x.me,)), 'no applicants to review')
    nxt = {'submitted': ['viewed', 'shortlisted', 'rejected'], 'viewed': ['shortlisted', 'rejected'], 'shortlisted': ['interviewed', 'rejected'], 'interviewed': ['hired', 'rejected']}.get(a[2], ['viewed'])
    st = x.r.choice(nxt); x.target = 'job %s applicant %s: %s → %s' % (a[0], a[1], a[2], st)
    x.ok(x.acc.get('job_applications', 'select=*&job_id=eq.%s' % a[0]), 'the applicants list')
    x.rows(x.acc.update('job_applications', 'job_id=eq.%s&user_id=eq.%s' % (a[0], a[1]), {'status': st}, select='status'), 'move the applicant')
    x.expect("select status from public.job_applications where job_id=%s and user_id=%s", (a[0], a[1]), st, 'the stage is stored')
    if st == 'hired' and x.r.random() < 0.5:
        x.rows(x.acc.update('jobs', 'id=eq.%s' % a[0], {'active': False}, select='id'), 'close the job')


@action('job.alerts', 'community', ['J-COMMUNITY-20'], dict(seek=0.2))
def job_alerts(x): raise NotBuilt('job alerts: no table or request in the live app')


# ── trust layer ────────────────────────────────────────────────────────────────────────────────────────────────────────
@action('trust.read', 'community', ['J-COMMUNITY-34', 'J-COMMUNITY-29'], dict(hire=2, seek=1))
def trust_read(x):
    c = x.ok(x.acc.rpc('open_candidates', {'p_limit': 40}), 'open candidates')
    ids = [r['id'] for r in (c.data or []) if isinstance(r, dict) and r.get('id')][:20] or [x.other()]
    x.ok(x.acc.rpc('get_reviews_many', {'p_ids': ids, 'p_role': 'candidate'}), 'their reviews')
    x.ok(x.acc.rpc('my_interactions'), 'my interactions')
    x.ok(x.acc.get('job_lists', 'select=*,t:profiles!job_lists_target_fkey(name)&owner=eq.%s' % x.me), 'my lists')
    x.ok(x.acc.get('work_references', 'select=id,kind,status,candidate,role_title&limit=50'), 'references I may read')


@action('trust.review', 'community', ['J-COMMUNITY-30'], dict(hire=1, seek=1))
def trust_review(x):
    row = x.pick("select j.user_id, 'employer' from public.job_applications a join public.jobs j on j.id=a.job_id where a.user_id=%s union all "
                 "select a.user_id, 'candidate' from public.job_applications a join public.jobs j on j.id=a.job_id where j.user_id=%s", (x.me, x.me))
    who, role = x.need(row, 'no hiring interaction'); x.target = '%s %s' % (role, who)
    c = x.r.choice
    body = c(['Clear process and on-time feedback after the interview. Recommended.', 'Professional and well prepared; documents were complete and accurate.',
              'The interview was postponed twice without notice, communication could be better.'])
    x.ok(x.acc.insert('job_reviews', {'reviewer': x.me, 'reviewee': who, 'reviewee_role': role, 'c1': c([3, 4, 5]), 'c2': c([2, 3, 4, 5]), 'c3': c([3, 4, 5]), 'c4': c([3, 4, 5]),
                                      'body': body, 'anonymous': role == 'employer' and x.r.random() < 0.5}, select=None, upsert='reviewer,reviewee,reviewee_role'), 'review')
    x.expect("select count(*) from public.job_reviews where reviewer=%s and reviewee=%s and reviewee_role=%s", (x.me, who, role), 1, 'the review is stored')
    stranger = x.other(lambda q: q.get('uid') != who)
    r = x.acc.insert('job_reviews', {'reviewer': x.me, 'reviewee': stranger, 'reviewee_role': 'candidate', 'c1': 1, 'c2': 1, 'c3': 1, 'c4': 1, 'body': 'A review without any interaction should be refused.'}, select=None)
    if r.ok and x.db.val("select count(*) from public.job_reviews where reviewer=%s and reviewee=%s and reviewee_role='candidate'", (x.me, stranger)) and \
       not x.db.val("select exists(select 1 from public.job_applications a join public.jobs j on j.id=a.job_id where (a.user_id=%s and j.user_id=%s))", (stranger, x.me)):
        raise Fail('a review of someone I never interacted with was accepted')


@action('trust.list', 'community', ['J-COMMUNITY-29'], dict(hire=1))
def trust_list(x):
    u = x.need(x.other()); x.target = 'person %s' % u
    side = x.r.choice(['candidate', 'employer']); lst = 'white' if x.r.random() < 0.85 else 'black'
    row = {'owner': x.me, 'target': u, 'side': side, 'list': lst, 'reason': None if lst == 'white' else 'No-show at interview', 'note': 'simulated', 'until': None}
    x.ok(x.acc.insert('job_lists', row, select=None, upsert='owner,target,side'), 'put a person on my %s list' % lst)
    x.expect("select list from public.job_lists where owner=%s and target=%s and side=%s", (x.me, u, side), lst, 'stored')


def ref_author(x):
    """References are written by an owner, admin or HR member of a verified company (the app's rule)."""
    if not x.db.val("select exists(select 1 from public.companies c left join public.company_members m on m.company_id=c.id and m.user_id=%s and m.accepted and m.role in ('admin','hr') "
                    "where c.status='verified' and (c.owner_id=%s or m.user_id is not null))", (x.me, x.me)):
        raise Skip('not an owner, admin or HR of a verified company')


@action('trust.honor', 'community', ['J-COMMUNITY-31'], dict(hire=0.6), who='company')
def trust_honor(x):
    ref_author(x)
    u = x.need(x.other(lambda q: q.get('kind') != 'owner')); x.target = 'person %s' % u
    d = x.ok(x.acc.insert('work_references', {'author': x.me, 'candidate': u, 'kind': 'honor', 'role_title': x.w.people[u].get('headline', 'Pharmacist'), 'from_month': '2022-01-01', 'to_month': '2024-06-01',
                                              'body': 'Reliable and careful colleague; led our stability programme and passed two inspections without findings. (simulated)', 'status': 'published'}), 'write an honour reference')
    x.expect("select count(*) from public.work_references where author=%s and candidate=%s and kind='honor'", (x.me, u), lambda v: v >= 1, 'the reference is stored')


@action('trust.warn', 'community', ['J-COMMUNITY-32'], dict(hire=0.2), who='company', rare=True)
def trust_warn(x):
    ref_author(x)
    u = x.need(x.other(lambda q: q.get('kind') != 'owner')); x.target = 'person %s' % u
    ev = '%s/%s.pdf' % (x.me, x.r.getrandbits(40))
    x.ok(x.acc.upload('reference-evidence', ev, fixture('spec.pdf') or b'%PDF-1.4\n%%EOF\n', 'application/pdf'), 'upload the evidence')
    x.ok(x.acc.insert('work_references', {'author': x.me, 'candidate': u, 'kind': 'warn', 'role_title': 'QC Analyst', 'from_month': '2023-01-01', 'to_month': '2024-01-01', 'category': 'Left without notice',
                                          'body': 'Left during a validation campaign without notice; documented in the HR file attached. (simulated)', 'evidence_path': ev}, select=None), 'file a warning with evidence')
    x.expect("select status from public.work_references where author=%s and candidate=%s and kind='warn' order by id desc limit 1", (x.me, u), 'pending', 'the warning waits for moderation, not published')


@action('trust.reply', 'community', ['J-COMMUNITY-33'], dict(seek=1))
def trust_reply(x):
    r = x.need(x.pick("select id, kind from public.work_references where candidate=%s and reply is null and status in ('published','pending')", (x.me,)), 'no reference about me')
    x.target = 'reference %s' % r[0]
    dispute = r[1] == 'warn' and x.r.random() < 0.6
    x.ok(x.acc.rpc('reply_to_reference', {'ref_id': r[0], 'reply_text': 'Thank you. (simulated reply)' if not dispute else 'This is not accurate; I resigned with one month notice. (simulated)', 'dispute': dispute}), 'reply to a reference')
    x.expect("select reply is not null from public.work_references where id=%s", (r[0],), True, 'the reply is stored')


# ── training ───────────────────────────────────────────────────────────────────────────────────────────────────────────
@action('training.enroll', 'community', ['J-COMMUNITY-35', 'J-COMMUNITY-36'], dict(learn=3, seek=1))
def training_enroll(x):
    x.ok(x.acc.get('training_courses', 'select=*&active=eq.true&order=sort_order,created_at&limit=100'), 'the courses')
    c = x.need(x.pick("select id from public.training_courses c where active and not exists (select 1 from public.course_enrollments e where e.course_id=c.id and e.user_id=%s)", (x.me,)), 'enrolled in every course')
    x.target = 'course %s' % c[0]
    before = x.db.val("select enrolled_count from public.training_courses where id=%s", (c[0],)) or 0
    x.ok(x.acc.insert('course_enrollments', {'course_id': c[0], 'user_id': x.me}, select=None), 'enroll')
    x.expect("select status from public.course_enrollments where course_id=%s and user_id=%s", (c[0], x.me), 'enrolled', 'enrolled')
    x.dbwait("select enrolled_count from public.training_courses where id=%s", (c[0],), lambda v: (v or 0) == before + 1, 'enrolled_count +1')


@action('training.progress', 'community', ['J-COMMUNITY-37', 'J-COMMUNITY-38', 'J-COMMUNITY-39'], dict(learn=1))
def training_progress(x): raise NotBuilt('paid courses, lesson progress, exams and certificates: no request in the live app')


@action('training.admin', 'community', ['J-COMMUNITY-40'], who='admin', path='api')
def training_admin(x):
    if x.db.val("select count(*) from public.training_courses where title like '%%(simulated)'") >= 4: raise Skip('enough simulated courses')
    left = [t + ' (simulated)' for t in ['Data Integrity Basics', 'CAPA That Works', 'Cold Chain Essentials', 'Pharmacovigilance 101'] if not x.db.val("select 1 from public.training_courses where title=%s", (t + ' (simulated)',))]
    t = x.need(x.r.choice(left) if left else None, 'all simulated courses exist')
    d = x.rows(x.acc.insert('training_courses', {'title': t, 'description': 'A short course made by the activity simulator.', 'emoji': '🎓', 'duration': '2h', 'level': 'Beginner', 'active': True, 'sort_order': 90}), 'add a course')[0]
    x.target = 'course %s' % d['id']


# ── Drugbox moderation (the sim admin) ─────────────────────────────────────────────────────────────────────────────────
@action('admin.post_reports', 'admin', ['J-SOCIAL-20', 'J-COMMUNITY-47', 'J-COMMUNITY-48', 'J-COMMUNITY-49'], who='admin')
def admin_post_reports(x):
    r = x.ok(x.acc.get('post_reports', 'select=*&status=eq.open&order=created_at&limit=50'), 'the reports queue')
    rep = x.need(r.data, 'no open reports')[0]; x.target = 'report %s' % rep['id']
    remove = x.r.random() < 0.4
    x.ok(x.acc.rpc('post_report_decide', {'p_report': rep['id'], 'p_remove': remove, 'p_note': 'simulated decision'}), 'decide the report')
    x.expect("select status from public.post_reports where id=%s", (rep['id'],), 'removed' if remove else 'dismissed', 'decided')
    if remove: x.expect("select count(*) from public.posts where id=%s", (rep['post_id'],), 0, 'the post is removed')
    again = x.acc.rpc('post_report_decide', {'p_report': rep['id'], 'p_remove': not remove, 'p_note': 'second moderator'})
    if again.ok and x.db.val("select status from public.post_reports where id=%s", (rep['id'],)) != ('removed' if remove else 'dismissed'): raise Fail('a second decision overwrote the first')


@action('admin.verifications', 'admin', ['J-BUSINESS-49', 'J-COMMUNITY-41', 'J-COMMUNITY-42', 'J-BUSINESS-14', 'J-BUSINESS-21'], who='admin')
def admin_verifications(x):
    r = x.ok(x.acc.get('verification_requests', 'select=*,company:companies(name,slug,status)&status=eq.pending&order=created_at&limit=50'), 'the verification queue')
    v = x.need(r.data, 'no pending requests')[0]; x.target = 'request %s (%s)' % (v['id'], 'claim' if v.get('claim') else 'verify')
    for k in ('registry_path', 'tax_card_path', 'licence_path'):
        if v.get(k):
            s = x.ok(x.acc.sign('documents', v[k]), 'open the %s' % k)
    ok = x.r.random() < 0.85
    x.rows(x.acc.update('verification_requests', 'id=eq.%s' % v['id'], {'status': 'approved' if ok else 'rejected', 'note': 'simulated review'}), 'decide')
    if ok and v.get('claim'):
        x.expect("select owner_id from public.companies where id=%s", (v['company_id'],), v['submitted_by'], 'the claimant owns the page')
    elif ok:
        x.expect("select status from public.companies where id=%s", (v['company_id'],), 'verified', 'the company is verified')
    x.dbwait("select count(*) from public.notifications where user_id=%s and created_at > now() - interval '5 minutes'", (v['submitted_by'],), lambda n: n >= 1, 'the requester is told')


@action('admin.company_reports', 'admin', ['J-BUSINESS-49', 'J-COMMUNITY-43'], who='admin')
def admin_company_reports(x):
    r = x.ok(x.acc.get('company_reports', 'select=*&status=eq.open&order=created_at&limit=50'), 'wrong-data reports')
    rep = x.need(r.data, 'no open reports')[0]; x.target = 'report %s' % rep['id']
    st = x.r.choice(['resolved', 'dismissed'])
    x.rows(x.acc.update('company_reports', 'id=eq.%s' % rep['id'], {'status': st}), 'decide')
    x.expect("select status from public.company_reports where id=%s", (rep['id'],), st, 'decided')


@action('admin.warnings', 'admin', ['J-COMMUNITY-44', 'J-COMMUNITY-33'], who='admin')
def admin_warnings(x):
    w = x.need(x.pick("select id, evidence_path from public.work_references where kind='warn' and status in ('pending','disputed')"), 'no warnings to review')
    x.target = 'reference %s' % w[0]
    if w[1]: x.ok(x.acc.sign('reference-evidence', w[1]), 'open the evidence')
    st = x.r.choice(['published', 'rejected'])
    x.ok(x.acc.rpc('moderate_reference', {'ref_id': w[0], 'new_status': st}), 'decide the warning')
    x.expect("select status from public.work_references where id=%s", (w[0],), st, 'decided')


@action('admin.certs', 'admin', ['J-COMMUNITY-45', 'J-BUSINESS-19'], who='admin')
def admin_certs(x):
    c = x.need(x.pick("select id from public.site_certificates where checked_at is null"), 'no certificates to check'); x.target = 'certificate %s' % c[0]
    x.rows(x.acc.update('site_certificates', 'id=eq.%s' % c[0], {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}), 'mark checked')
    x.expect("select checked_at is not null from public.site_certificates where id=%s", (c[0],), True, 'checked')


@action('admin.instapay', 'admin', ['J-BUSINESS-45', 'J-COMMUNITY-46'], who='admin')
def admin_instapay(x):
    o = x.need(x.pick("select id, receipt_path, listing_id, product_code from public.payment_orders where status='review' order by id"), 'no transfers to confirm'); x.target = 'order %s' % o[0]
    if o[1]: x.ok(x.acc.sign('documents', o[1]), 'open the receipt')
    good = x.r.random() < 0.85
    x.ok(x.acc.rpc('review_instapay', {'p_id': o[0], 'p_ok': good}), 'confirm the transfer')
    x.expect("select status from public.payment_orders where id=%s", (o[0],), 'paid' if good else 'failed', 'decided')
    if good and o[2] and o[3] == 'featured': x.expect("select featured_until > now() + interval '29 days' from public.products where id=%s", (o[2],), True, 'the listing is featured')


@action('admin.messages', 'admin', ['J-COMMUNITY-47', 'J-SOCIAL-40'], who='admin')
def admin_messages(x):
    r = x.ok(x.acc.get('message_reports', 'select=*&status=eq.open&order=created_at&limit=50'), 'message reports')
    rep = x.need(r.data, 'no message reports')[0]; x.target = 'message report %s' % rep['id']
    st = x.r.choice(['actioned', 'dismissed'])
    x.rows(x.acc.update('message_reports', 'id=eq.%s' % rep['id'], {'status': st}, select='id'), 'decide')
    x.expect("select status from public.message_reports where id=%s", (rep['id'],), st, 'decided')


@action('admin.directory', 'admin', ['J-BUSINESS-14'], who='admin', path='server')
def admin_directory(x):
    """Drugbox imports public-list pages (unclaimed) that members later claim. Server-side work (only Drugbox may set
    source 'public_list'; the live app has no import screen): written in the database as the owner, like an import job."""
    if x.db.val("select count(*) from public.companies where slug like 'sim-dir-%%' and status='unclaimed'") >= max(3, len(x.w.people) // 40): raise Skip('enough unclaimed pages')
    n = x.db.val("select count(*) from public.companies where slug like 'sim-dir-%%'")
    pre = x.r.choice(['Arab', 'United', 'Modern', 'Global', 'Kemet', 'Saqqara', 'Giza', 'Nubia']); name = '%s %s Pharma' % (pre, x.r.choice(['Medical', 'Chemicals', 'Labs', 'Trading']))
    slug = 'sim-dir-%d-%d' % (n, x.r.randint(100, 999))
    x.db.q("insert into public.companies (name, slug, type, status, source, city, sectors, owner_id) values (%s, %s, %s, 'unclaimed', 'public_list', 'Cairo', '{Manufacturer}', null)", (name, slug, x.r.choice(['Manufacturer', 'Distributor', 'Supplier'])))
    x.target = slug
    d = x.rows(x.acc.get('companies', 'select=id,slug,status&slug=eq.%s' % slug), 'the imported page is public')[0]
    if d['status'] != 'unclaimed': raise Fail('an imported page is not unclaimed')


@action('admin.only_staff', 'admin', ['J-COMMUNITY-50'], dict(social=0.2))
def admin_only_staff(x):
    """A member is not a moderator: the queues stay empty and decisions are refused."""
    ids = [c[0] for c in my_companies(x)]
    r = x.ok(x.acc.get('verification_requests', 'select=id,company_id&submitted_by=neq.%s&limit=50' % x.me), "others' verification requests")
    leak = [v['id'] for v in (r.data or []) if v.get('company_id') not in ids]
    if leak: raise Fail("a member reads other companies' verification requests: %s" % leak[:3])
    rep = x.pick("select id from public.post_reports where status='open'")
    if rep:
        d = x.acc.rpc('post_report_decide', {'p_report': rep[0], 'p_remove': True, 'p_note': 'not a moderator'})
        if d.ok: raise Fail('a member decided a post report')
    o = x.pick("select id from public.payment_orders where status='review'")
    if o:
        d2 = x.acc.rpc('review_instapay', {'p_id': o[0], 'p_ok': True})
        if d2.ok: raise Fail('a member confirmed an InstaPay transfer')
