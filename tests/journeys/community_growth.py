"""Community journeys of the growth plan (AREA w-growth): the official Drugbox channels and their scheduler (W-41), the therapeutic
filter on Home (W-21), Ask an expert (W-43) and the six courses in Arabic (decision 7). J-COMMUNITY-W01 … W05 (docs/JOURNEYS.md)."""
import re, time
from _j import journey, main
from _community import (groups_page, open_card, gd_open, gd_close, gd_pane, gposts, has_composer, notifs, close_dialogs, mopen, mtext, mclick,
                        make_admin, add_member, reopen, tour_off)
from _biz import ui_ok, dlg_open, dlg_click, fill_by_label

def T(j, en, ar_): return ar_ if j.ar else en
CH_AR = {}   # a channel's name is a name (Drugbox News …) — it reads the same in Arabic

def staff(j, name='Drugbox Staff'):
    """Live: a Drugbox admin (an account made through the UI, given the admin role — that role is Drugbox's to give)."""
    p = j.person(name); make_admin(j, p['id']); j.reload(p['page']); return p

def admin_tab(j, pg, key, label):
    close_dialogs(pg)
    if gd_open(pg): gd_close(pg)
    if pg.evaluate("document.body.getAttribute('data-page')") != 'admin':   # the Admin entry sits at the foot of the side menu (as admin_review opens it)
        a = pg.locator("#app [onclick=\"goto('admin')\"]")
        j.check(a.count(), 'not built: no Admin entry for a Drugbox admin')
        if not a.first.is_visible() and pg.locator('#sbToggle:visible').count(): pg.click('#sbToggle'); pg.wait_for_timeout(400)
        a.first.scroll_into_view_if_needed()
        try: a.first.click(timeout=5000)
        except Exception: a.first.evaluate('e=>e.click()')
        j.settle(pg, 900)
    el = pg.locator('.admin-nav [data-gwadm="%s"]' % key)
    j.check(el.count(), 'not built: Admin has no "%s" tab' % label)
    el.first.scroll_into_view_if_needed(); el.first.click(); j.settle(pg, 900)
    return pg

def cairo_slot(j, pg, minutes):
    """The Cairo wall time minutes from now, as the page computes it ('YYYY-MM-DD HH:MM')."""
    return pg.evaluate("m=>dxGrowthUI.cairoNow(m*60000)", minutes)

def seed_channel_post(j, admin_id, channel, body, thera='{}'):
    """Live precondition: Drugbox published a post in a channel (the publisher the scheduler uses, as the server)."""
    sid = j.sql1("insert into public.channel_schedule (group_id, body, thera, status, created_by, updated_by) select id, $q$%s$q$, '%s', 'draft', '%s', '%s' from public.groups where channel_key='%s' returning id" % (body, thera, admin_id, admin_id, channel))
    return j.sql1("select private.channel_publish(%s)" % sid)

def channel_card(j, pg, en):
    title = CH_AR.get(en, en)
    c = pg.locator('#content .gcard').filter(has=pg.locator('.gcard-title', has_text=title))
    j.check(c.count(), 'no card for the channel "%s" (cards: %s)' % (title, ', '.join(pg.evaluate("[...document.querySelectorAll('#content .gcard-title')].map(e=>e.innerText)"))[:300]))
    return c.first, title

@journey('J-COMMUNITY-W01')
def official_channels(j):
    """A member finds the official Drugbox channels, joins one and reads Drugbox's posts — clearly Drugbox, never a member."""
    if j.live:
        adm = staff(j); me = j.person('Rana Channel Reader'); pg = me['page']
        body = 'Wanted today %s: Insulin glargine pens for distributors' % j.tag
        pid = seed_channel_post(j, adm['id'], 'market', body)
    else:
        pg = j.demo_signin(j.new_page()); body = 'Wanted today'
    with j.step('Groups shows the four Drugbox channels, each with the "Drugbox official" badge'):
        groups_page(j, pg)
        for en in ('Drugbox News', 'Drugbox Jobs', 'Drugbox Regulatory', 'Drugbox Market'):
            c, title = channel_card(j, pg, en)
            j.check(re.search(T(j, r'Drugbox official', r'رسمي من Drugbox'), c.inner_text()), 'the card of %s has no "Drugbox official" badge' % title)
        if j.live: j.check(j.sql1("select count(*) from public.groups where official and channel_key is not null") == '4', 'the database does not hold the four official channels')
        ui_ok(j, pg, 'Groups with the channels')
    with j.step('Open Drugbox Market: the official-channel note, no composer, the post reads as Drugbox with the ✓ Official mark'):
        c, title = channel_card(j, pg, 'Drugbox Market'); c.scroll_into_view_if_needed(); c.locator('.gcard-title').click(); j.settle(pg, 1200)
        j.check(gd_open(pg), 'the Drugbox Market card opens nothing')
        btn = j.find(pg, T(j, r'^\W*\+?\s*Join( Group)?\W*$', r'انضم'), scope='#groupDetail')
        if btn: btn.click(); j.settle(pg, 1200)
        if j.live: j.check(j.wait_db("select count(*) from public.group_members m join public.groups g on g.id=m.group_id where g.channel_key='market' and m.user_id='%s' and m.role='member'" % me['id'], 6) == '1', 'joining the channel left no membership row')
        t = j.text(pg, '#groupDetail')
        j.check(re.search(T(j, r'Official Drugbox channel', r'قناة Drugbox الرسمية'), t), 'the channel does not say it is the official Drugbox channel')
        j.check(not has_composer(pg), 'a member gets a composer in an official channel')
        post = pg.locator('#gpBox .post', has_text=body).first
        j.check(post.count(), 'the Drugbox post "%s" is not in the channel' % body[:40])
        nm = post.locator('.post-name').inner_text()
        j.check(nm.startswith('Drugbox') and re.search(T(j, r'Official', r'رسمي'), nm), 'the post does not read as Drugbox ✓ Official (author: %s)' % nm)
        if j.live: j.check(adm['name'] not in post.inner_text(), "the Drugbox post shows the admin's own name — it must read as Drugbox")
        j.check(not post.locator('.post-name[onclick], .post-av[onclick]').count(), 'the Drugbox author still opens a member profile')
        ui_ok(j, pg, 'inside a channel')
    with j.step('React to the Drugbox post (members comment and react)'):
        like = post.locator('.post-acts .pact').first; like.click(); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select count(*) from public.reactions where post_id=%s and user_id='%s'" % (pid, me['id']), 6) == '1', 'the reaction was not stored')
    with j.step('Nobody posts into a channel but Drugbox — the server refuses a member who tries through the API'):
        if j.demo: j.skip('the server rule is checked in live')
        err = pg.evaluate("async()=>{const r=await dxLive.sb.from('posts').insert({user_id:dxLive.uuidOf(ME.id),body:'fake drugbox',group_id:%s});return r.error?(r.error.code||r.error.message):'allowed'}" % j.sql1("select id from public.groups where channel_key='market'"))
        j.check(err != 'allowed', 'a member could post into the Drugbox Market channel through the API')
        j.check(j.sql1("select count(*) from public.posts p join public.groups g on g.id=p.group_id where g.official and not p.as_drugbox") == '0', 'a non-Drugbox post sits in an official channel')

@journey('J-COMMUNITY-W02')
def channel_scheduler(j):
    """Drugbox plans its channel posts from the content plan: a template, a Cairo time, edit, cancel, publish now — the server publishes on time."""
    if j.live:
        adm = staff(j); pg = adm['page']; mem = j.person('Omar Market Follower')
        add_member(j, j.sql1("select id from public.groups where channel_key='market'"), mem['id'])
    else:
        pg = j.demo_signin(j.new_page()); mem = None
    tag = j.tag
    with j.step('Admin → Channels lists the content plan: «Wanted today» daily at 21:00 and the weekly templates'):
        admin_tab(j, pg, 'channels', 'Channels'); t = j.text(pg, '#adminContent')
        j.check(re.search(T(j, r'Wanted today', r'مطلوب النهارده'), t) and '21:00' in t, 'the content plan has no «Wanted today» at 21:00')
        j.check(len(re.findall(T(j, r'Weekly', r'أسبوعيًا'), t)) >= 5, 'the weekly templates (bulletin, file ads, agency market, guide, shortages) are missing')
        ui_ok(j, pg, 'Admin → Channels')
    with j.step('Use «Wanted today»: the form is filled (Market, the text, the next 21:00); schedule it for in 3 minutes (Cairo)'):
        row = pg.locator('#adminContent .dx-tpl', has_text=T(j, 'Wanted today', 'مطلوب النهارده')).first
        row.locator('.dx-tpl-use').click(); j.settle(pg, 900)
        j.check(dlg_open(pg), '"Use" opened no form')
        j.check(pg.locator('#chC').input_value() == 'market', 'the template did not choose the Market channel')
        j.check(pg.locator('#chH').input_value() == '21:00', 'the template did not propose 21:00 Cairo')
        when = cairo_slot(j, pg, 3)
        pg.fill('#chB', 'Wanted today %s — Semaglutide API 2 kg, Alexandria (manufacturer). Companies only.' % tag)
        pg.locator('.dx-th-ck input[value="glp1"]').check()
        pg.fill('#chD', when[:10]); pg.fill('#chH', when[11:]); pg.locator('input[name=chM][value=scheduled]').check()
        dlg_click(j, pg, T(j, r'^\W*Save\W*$', r'^\W*حفظ\W*$'), 'Save'); j.settle(pg, 1200)
        t = j.text(pg, '#adminContent')
        j.check(tag in t and when in t and re.search(T(j, r'Scheduled', r'مجدول'), t), 'the scheduled post is not listed with its Cairo time %s' % when)
        if j.live:
            row = j.sql("select status, to_char(publish_at at time zone 'Africa/Cairo','YYYY-MM-DD HH24:MI'), thera::text from public.channel_schedule where body like '%%%s%%'" % tag)
            j.check(row.startswith('scheduled|' + when) and 'glp1' in row, 'the database does not hold the post as scheduled at %s Cairo (%s)' % (when, row))
    with j.step('Edit it before it goes out: the text changes, the time stays'):
        r = pg.locator('#adminContent tr', has_text=tag).first; r.locator('.dx-ch-edit').click(); j.settle(pg, 800)
        pg.fill('#chB', 'Wanted today %s — Semaglutide API 3 kg, Alexandria (manufacturer). Companies only.' % tag)
        dlg_click(j, pg, T(j, r'^\W*Save\W*$', r'^\W*حفظ\W*$'), 'Save'); j.settle(pg, 1000)
        j.check('3 kg' in j.text(pg, '#adminContent'), 'the edit is not in the plan')
        if j.live: j.check(j.sql1("select count(*) from public.channel_schedule where body like '%%%s%%3 kg%%' and status='scheduled'" % tag) == '1', 'the edit was not stored')
    with j.step('The time comes: the server publishes it as Drugbox in Market (the clock is moved forward, nothing else)'):
        if j.live:
            j.sql("update public.channel_schedule set publish_at = now() - interval '1 minute' where body like '%%%s%%'" % tag)
            j.check(j.wait_db("select status from public.channel_schedule where body like '%%%s%%'" % tag, 20, want='published') == 'published', 'the runner (growth_tick) did not publish the post when its time came')
            j.check(j.sql1("select p.as_drugbox::text||'|'||g.channel_key from public.channel_schedule s join public.posts p on p.id=s.post_id join public.groups g on g.id=p.group_id where s.body like '%%%s%%'" % tag) == 'true|market', 'the published post is not a Drugbox post in Market')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='group_post' and from_user is null and (data->>'drugbox')::boolean" % mem['id'], 6) == '1', 'the channel member was not told (as Drugbox)')
        else:
            pg.evaluate("t=>{const p=DBK.store.get('gwPlan',[]);p.forEach(x=>{if(String(x.body).indexOf(t)>=0)x.local='2000-01-01 00:00'});DBK.store.set('gwPlan',p)}", tag)
            end = time.time() + 12
            while time.time() < end and not re.search(T(j, 'Published', 'نُشر'), pg.locator('#adminContent tr', has_text=tag).first.inner_text()): pg.wait_for_timeout(700)
        admin_tab(j, pg, 'channels', 'Channels')
        j.check(re.search(T(j, r'Published', r'نُشر'), pg.locator('#adminContent tr', has_text=tag).first.inner_text()), 'the plan does not show the post as published')
    with j.step('Members see it in Drugbox Market, from Drugbox'):
        v = mem['page'] if j.live else pg
        if j.live: j.reload(v)
        groups_page(j, v); c, title = channel_card(j, v, 'Drugbox Market'); c.locator('.gcard-title').click(); j.settle(v, 1500)
        post = v.locator('#gpBox .post', has_text=tag).first
        j.check(post.count(), 'the published post is not in the channel')
        j.check(post.locator('.post-name').inner_text().startswith('Drugbox'), 'the published post does not read as Drugbox')
        gd_close(v)
    with j.step('A draft can be cancelled; another draft is published at once with "Publish now"'):
        admin_tab(j, pg, 'channels', 'Channels')
        for k, txt in (('c', 'Draft to cancel %s' % tag), ('n', 'Agency market %s: principals looking for distributors' % tag)):
            pg.locator('.dx-ch-new').click(); j.settle(pg, 600)
            pg.select_option('#chC', 'news' if k == 'c' else 'market'); pg.fill('#chB', txt); pg.locator('input[name=chM][value=draft]').check()
            dlg_click(j, pg, T(j, r'^\W*Save\W*$', r'^\W*حفظ\W*$'), 'Save'); j.settle(pg, 900)
        r = pg.locator('#adminContent tr', has_text='Draft to cancel %s' % tag).first; r.locator('.dx-ch-cancel').click(); j.settle(pg, 500)
        dlg_click(j, pg, T(j, r'Cancel post', r'إلغاء المنشور'), 'Cancel post'); j.settle(pg, 900)
        j.check(re.search(T(j, r'Cancelled', r'أُلغي'), pg.locator('#adminContent tr', has_text='Draft to cancel %s' % tag).first.inner_text()), 'the cancelled draft is not marked cancelled')
        r = pg.locator('#adminContent tr', has_text='Agency market %s' % tag).first; r.locator('.dx-ch-pub').click(); j.settle(pg, 1200)
        j.check(re.search(T(j, r'Published', r'نُشر'), pg.locator('#adminContent tr', has_text='Agency market %s' % tag).first.inner_text()), '"Publish now" did not publish the draft')
        if j.live:
            j.check(j.sql1("select status from public.channel_schedule where body like 'Draft to cancel %s%%'" % tag) == 'cancelled', 'the cancel was not stored')
            j.check(j.sql1("select count(*) from public.channel_schedule s join public.posts p on p.id=s.post_id where s.body like 'Agency market %s%%' and p.as_drugbox" % tag) == '1', '"Publish now" wrote no Drugbox post')
    with j.step('A member cannot plan or publish channel posts (the server refuses)'):
        if j.demo: j.skip('the server rule is checked in live')
        err = mem['page'].evaluate("async()=>{const r=await dxLive.sb.rpc('channel_schedule_save',{p_id:null,p_channel:'news',p_body:'fake',p_local:null,p_status:'draft',p_thera:[],p_template:null});return r.error?(r.error.code||'err'):'allowed'}")
        j.check(err == '42501', 'a member could plan a channel post (%s)' % err)
        j.check(not mem['page'].locator('.admin-nav [data-gwadm]').count(), 'a member sees the Channels admin tab')

@journey('J-COMMUNITY-W03')
def home_therapeutic_filter(j):
    """A member narrows Home to one therapeutic area (insulin, oncology …) — the server finds every post about it."""
    if j.live:
        me = j.person('Hany Insulin Distributor'); pg = me['page']; other = j.person('Sara Poster')
        from _social import post_db
        pid = post_db(j, other['id'], 'Insulin glargine pens %s — available for distributors, business to business' % j.tag)
        post_db(j, other['id'], 'Our new stability chamber %s is running' % j.tag)
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    needle = 'Insulin glargine pens %s' % j.tag
    with j.step('Home has a therapeutic-area filter'):
        j.nav(pg, 'feed'); j.settle(pg, 900)
        j.check(pg.locator('#dxThFeed').count(), 'not built: Home has no therapeutic-area filter')
        ui_ok(j, pg, 'Home with the filter')
    with j.step('A post about insulin is tagged by its words (no member chooses tags)'):
        if j.demo:
            from _social import compose
            compose(j, pg, needle + ' — available for distributors, business to business'); j.settle(pg, 800)
        else:
            j.check(j.sql1("select thera::text from public.posts where id=%s" % pid) == '{insulin}', 'the insulin post is not tagged insulin in the database')
    with j.step('Choose Insulin: the insulin post shows, the others are hidden'):
        pg.select_option('#dxThFeed', 'insulin'); j.settle(pg, 1500)
        vis = pg.evaluate("[...document.querySelectorAll('#content .post')].filter(e=>e.offsetParent!==null).map(e=>e.innerText)")
        j.check(any(needle in v for v in vis), 'the insulin post is not shown under Insulin')
        j.check(all(re.search(r'insulin|انسولين|إنسولين', v, re.I) for v in vis), 'a post not about insulin shows under Insulin')
    with j.step('Choose Oncology: nothing about it — the page says so'):
        pg.select_option('#dxThFeed', 'oncology'); j.settle(pg, 1500)
        vis = pg.evaluate("[...document.querySelectorAll('#content .post')].filter(e=>e.offsetParent!==null).map(e=>e.innerText)")
        j.check(not any(needle in v for v in vis), 'the insulin post shows under Oncology')
        if not vis: j.check(re.search(T(j, r'No posts about', r'لا توجد منشورات'), j.text(pg)), 'an empty result says nothing')
    with j.step('All areas again: the feed is back'):
        pg.select_option('#dxThFeed', ''); j.settle(pg, 900)
        j.check(pg.locator('#content .post:visible').count() > 0, 'the feed did not come back')

@journey('J-COMMUNITY-W04')
def ask_an_expert(j):
    """Members ask for a topic, Drugbox schedules an expert session, members register, get reminded, ask — and the Q&A is kept."""
    tag = j.tag
    if j.live:
        adm = staff(j); me = j.person('Mahmoud File Buyer'); pg, ap = me['page'], adm['page']
    else:
        pg = j.demo_signin(j.new_page()); ap = pg
    def experts(p):
        close_dialogs(p); j.nav(p, 'training'); j.settle(p, 1000)
        b = j.find(p, T(j, r'Ask an expert', r'اسأل خبيرًا'), scope='#content')
        j.check(b, 'not built: Training has no "Ask an expert"'); b.click(); j.settle(p, 1200)
        j.check(p.locator('#content .dx-xp').count(), '"Ask an expert" opened nothing')
    with j.step('Training → Ask an expert → request "Buying a registration file safely" with a note'):
        experts(pg)
        tp = pg.locator('#content [data-xtopic="file_purchase"]')
        b = tp.locator('.dx-xp-ask')
        if not b.count() and j.demo: tp.locator('.dx-xp-unask').click(); j.settle(pg, 800); b = pg.locator('#content [data-xtopic="file_purchase"] .dx-xp-ask')
        j.check(b.count(), 'the topic has no Request button')
        b.click(); j.settle(pg, 500); pg.fill('#xpN', 'How do I check the transfer papers %s?' % tag)
        dlg_click(j, pg, T(j, r'Send request', r'أرسل الطلب'), 'Send request'); j.settle(pg, 1000)
        j.check(pg.locator('#content [data-xtopic="file_purchase"] .dx-xp-unask').count(), 'the topic does not show my request')
        if j.live: j.check(j.wait_db("select count(*) from public.expert_requests where user_id='%s' and topic='file_purchase'" % me['id'], 6) == '1', 'no expert_requests row')
        ui_ok(j, pg, 'Ask an expert')
    with j.step('Drugbox sees the request with its note and schedules a session (Cairo time, seats, meeting link)'):
        admin_tab(j, ap, 'experts', 'Expert sessions')
        if j.live: j.check(tag in j.text(ap, '#adminContent'), "the member's note is not in Admin → Expert sessions")
        ap.locator('.dx-xa-new').click(); j.settle(ap, 600)
        when = cairo_slot(j, ap, 2 * 24 * 60)
        ap.select_option('#xaT', 'file_purchase'); ap.fill('#xaTi', 'Buying a file safely %s' % tag); ap.fill('#xaTa', 'شراء ملف بأمان %s' % tag)
        ap.fill('#xaEn', 'Dr. Mona Saleh'); ap.fill('#xaEl', 'Regulatory consultant'); ap.fill('#xaD', when[:10]); ap.fill('#xaH', '20:00'); ap.fill('#xaS', '40')
        ap.fill('#xaL', 'https://meet.example.test/%s' % tag)
        dlg_click(j, ap, T(j, r'^\W*Schedule\W*$', r'^\W*جدولة\W*$'), 'Schedule'); j.settle(ap, 1200)
        j.check(('Buying a file safely %s' % tag) in j.text(ap, '#adminContent') or ('شراء ملف بأمان %s' % tag) in j.text(ap, '#adminContent'), 'the session is not listed in Admin')
        if j.live:
            sid = j.wait_db("select id from public.expert_sessions where title like '%%%s'" % tag, 6); j.check(sid, 'no expert_sessions row')
            j.check(j.sql1("select to_char(starts_at at time zone 'Africa/Cairo','YYYY-MM-DD HH24:MI') from public.expert_sessions where id=%s" % sid) == when[:10] + ' 20:00', 'the session is not at 20:00 Cairo')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='expert_session'" % me['id'], 6) == '1', 'the member who asked was not told')
    with j.step('The member registers and asks the expert a question'):
        if j.live: j.reload(pg)
        experts(pg)
        card = pg.locator('#content .dx-xp-up [data-xsid]', has_text=tag).first if j.live else pg.locator('#content .dx-xp-up [data-xsid]').filter(has_text=re.compile('Buying a file safely %s|شراء ملف بأمان %s' % (tag, tag))).first
        j.check(card.count(), 'the session is not under Upcoming sessions')
        card.locator('.dx-xp-reg').click(); j.settle(pg, 1200)
        card = pg.locator('#content .dx-xp-up [data-xsid]').filter(has_text=re.compile('Buying a file safely %s|شراء ملف بأمان %s' % (tag, tag))).first
        j.check(card.locator('.dx-xp-unreg').count(), 'the session does not show me as registered')
        card.locator('.dx-xp-qa').click(); j.settle(pg, 800)
        card.locator('textarea').fill('Who pays the transfer fees %s?' % tag); card.locator('.dx-xp-send').click(); j.settle(pg, 1200)
        if j.live:
            j.check(j.wait_db("select count(*) from public.expert_registrations g join public.expert_sessions s on s.id=g.session_id where g.user_id='%s' and s.title like '%%%s'" % (me['id'], tag), 6) == '1', 'no registration row')
            j.check(j.wait_db("select count(*) from public.expert_questions where user_id='%s' and body like '%%%s%%'" % (me['id'], tag), 6) == '1', 'no question row')
    with j.step('A reminder reaches the registered member before the session (the clock moves to 30 minutes before)'):
        if j.demo: j.skip('reminders are sent by the server (growth_tick) — checked in live')
        j.sql("update public.expert_sessions set starts_at = now() + interval '30 minutes' where title like '%%%s'" % tag)
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='expert_reminder'" % me['id'], 20) == '1', 'no reminder reached the registered member')
        j.reload(pg); experts(pg)
        card = pg.locator('#content .dx-xp-up [data-xsid]', has_text=tag).first
        pg.context.route('https://meet.example.test/**', lambda r: r.fulfill(status=200, content_type='text/html', body='<title>meeting</title>'))   # the meeting service (outside Drugbox)
        with pg.context.expect_page(timeout=8000) as pi: card.locator('.dx-xp-join').click()
        try: pi.value.wait_for_url('**/%s' % tag, timeout=6000)
        except Exception: pass
        j.check(tag in pi.value.url, '"Join the session" did not open the meeting link (%s)' % pi.value.url)
        pi.value.close()
    with j.step('Drugbox (the expert) answers; the member is told; after the session the Q&A stays for every member'):
        admin_tab(j, ap, 'experts', 'Expert sessions')
        sc = ap.locator('#adminContent [data-xsid]').filter(has_text=re.compile('Buying a file safely %s|شراء ملف بأمان %s' % (tag, tag))).first
        sc.locator('.dx-xa-qs').click(); j.settle(ap, 900)
        sc.locator('textarea').first.fill('The buyer pays, unless the contract says otherwise.'); sc.locator('.dx-xa-ans').first.click(); j.settle(ap, 1200)
        if j.live: j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='expert_answer'" % me['id'], 6) == '1', 'the member was not told about the answer')
        sc = ap.locator('#adminContent [data-xsid]').filter(has_text=re.compile('Buying a file safely %s|شراء ملف بأمان %s' % (tag, tag))).first
        sc.locator('.dx-xa-done').click(); j.settle(ap, 500); dlg_click(j, ap, T(j, r'Mark done', r'تمت الجلسة'), 'Mark done'); j.settle(ap, 1200)
        if j.live:
            j.check(j.sql1("select status from public.expert_sessions where title like '%%%s'" % tag) == 'done', 'the session is not done in the database')
            other = j.person('Late Reader'); vp = other['page']
        else: vp = pg
        experts(vp)
        past = vp.locator('#content .dx-xp-past [data-xsid]').filter(has_text=re.compile('Buying a file safely %s|شراء ملف بأمان %s' % (tag, tag))).first
        j.check(past.count(), 'the session is not under Past sessions')
        past.locator('.dx-xp-qa').click(); j.settle(vp, 1000)
        j.check('The buyer pays' in past.inner_text(), 'the answer is not kept for other members')

@journey('J-COMMUNITY-W05')
def courses_in_arabic(j):
    """The six courses read in Arabic in the Arabic interface (decision 7), and stay free until the owner sets prices."""
    pg = j.person('Nadia Learner')['page'] if j.live else j.demo_signin(j.new_page())
    with j.step('Training lists the six courses; in Arabic their titles and descriptions are Arabic'):
        j.nav(pg, 'training'); j.settle(pg, 1500)
        titles = pg.evaluate("[...document.querySelectorAll('#content .tr-card .tr-title')].map(e=>e.innerText.trim())")
        want = ['أساسيات التصنيع الجيد (GMP)', 'خطوات التسجيل في هيئة الدواء', 'إرشادات ICH', 'تنظيم مستحضرات التجميل', 'دراسات الثبات', 'دخول أسواق الخليج'] if j.ar else \
               ['GMP Fundamentals', 'EDA Registration Process', 'ICH Guidelines', 'Cosmetics Regulation', 'Stability Studies', 'GCC Market Access']
        for w in want: j.check(w in titles, 'the course "%s" is not on the Training page (titles: %s)' % (w, ', '.join(titles)))
        if j.ar:
            d = pg.evaluate("[...document.querySelectorAll('#content .tr-card .tr-desc')].map(e=>e.innerText)")
            j.check(any('ممارسات التصنيع الجيد' in x for x in d), 'the course descriptions are not in Arabic')
        if j.live: j.check(j.sql1("select count(*) from public.training_courses where title_ar is not null and price_egp = 0") == '6', 'the database does not hold the six Arabic titles (free)')
        ui_ok(j, pg, 'Training')

if __name__ == '__main__': main(__file__)
