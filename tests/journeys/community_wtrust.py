"""Community journeys of the trust slice (area w-trust): a group's admin tools (W-08), moving a WhatsApp group honestly with an
invite link every member opens by themselves (W-44), posts that look out of scope wait for Drugbox review (W-17), and a trade
problem reported with evidence, answered, and decided by two Drugbox moderators (W-19).
Run: python3 tests/journeys/community_wtrust.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
from _social import compose as feed_compose, goto_profile
import _dx

def gpost_try(j, pg, body, category=None):
    """Write a post in the open group; returns the toasts it caused (a refusal says why)."""
    c = pg.locator('#gpBox [data-pane=disc] .comp-btn')
    if not (c.count() and c.first.is_visible()): j.notbuilt('no composer in the group')
    c.first.click(); pg.wait_for_selector('#postBody', state='visible', timeout=5000); pg.fill('#postBody', body)
    if category: pg.select_option('#postCat', category)
    mark = j.toast_mark(pg); pg.locator('.modal-bg.show .btn-p').last.click(); j.settle(pg, 1500)
    said = j.toasts_since(pg, mark)
    if pg.locator('.modal-bg.show #postBody').count(): pg.locator('.modal-bg.show').evaluate('e=>e.remove()')   # a refused post: the window is closed by hand
    return ' | '.join(said)

def manage_tab(j, pg, wt):
    """Manage → one of the new tabs (pending | invite)."""
    b = pg.locator('#groupDetail .btn-manage')
    if not (b.count() and b.first.is_visible()): j.notbuilt('no Manage Group for the group admin')
    if not pg.locator('#managePanel').is_visible(): b.first.click(); pg.wait_for_timeout(700)
    t = pg.locator('#managePanel .panel-tabs [data-wt-tab="%s"]' % wt)
    j.wait(pg, "k=>!!document.querySelector('#managePanel .panel-tabs [data-wt-tab=\"'+k+'\"]')", 6, wt)
    j.check(t.count(), 'not built: Manage has no "%s" tab' % wt); t.first.click(); pg.wait_for_timeout(900)
    if j.live: j.wait(pg, "k=>{const p=document.getElementById('tab-wt'+k);return p&&!/Loading|جارٍ التحميل/.test(p.innerText.slice(0,200))}", 8, wt)
    return pg.evaluate("k=>(document.getElementById('tab-wt'+k)||{}).innerText||''", wt)

def tick(pg, sel, on=True):
    el = pg.locator(sel)
    if el.is_checked() != on: el.click()

def join_with_rules(j, pg, accept=True):
    b = pg.locator('#gpBox [data-gpa="join"]:visible, #groupDetail [data-gpa="join"]:visible')
    j.check(b.count(), 'no Join in the group (buttons: %s)' % gd_buttons(pg)); b.first.click(); pg.wait_for_timeout(800)
    t = mtext(pg)
    j.check(re.search(r'The group’s rules|قواعد الجروب', t), 'joining a group that asks for its rules shows no rules window (dialog: "%s")' % t[:160])
    return t

@journey('J-COMMUNITY-W08')
def group_admin_tools(j):
    """A group's admin sets the rules on join, a daily limit, slow mode, no duplicates or outside links, posts reviewed first — and members are told why."""
    t = j.tag[:5]
    if j.live:
        g = j.person('Gamal Admin'); pg = g['page']; m = j.person('Jihan Member'); pm = m['page']; k = j.person('Kamal Reader'); pk = k['page']
        gname = 'Traders Hub %s' % t; gid = seed_group(j, gname, g['id'], rules='Trade offers only — no retail\nOne offer a day — keep it short')
        add_member(j, gid, g['id'], 'admin'); add_member(j, gid, k['id'])
        for p in (pg, pm, pk): j.reload(p)
    else:
        pg = j.demo_signin(j.new_page()); pm = pg; gname = 'Regulatory Affairs Egypt'
    with j.step('Manage → Settings: the admin tools (rules on join, posts a day, slow mode, duplicates, outside links, review first, category)'):
        groups_page(j, pg); open_card(j, pg, gname); manage(j, pg, 'settings')
        j.check(pg.locator('#tab-settings .wt-tools').count(), 'not built: Manage → Settings has no admin tools')
        tick(pg, '#wtRulesReq'); pg.fill('#wtDaily', '1'); pg.fill('#wtSlow', ''); tick(pg, '#wtDup'); tick(pg, '#wtLinks'); tick(pg, '#wtReview'); tick(pg, '#wtCat')
        mark = j.toast_mark(pg); pg.locator('#tab-settings .btn-create').first.click(); j.settle(pg, 1500)
        if j.live:
            row = j.wait_db("select rules_required||'|'||daily_post_limit||'|'||coalesce(slow_mode_minutes::text,'-')||'|'||block_links||'|'||review_posts||'|'||require_category from public.groups where id=%s" % gid, 8, want='true|1|-|true|true|true')
            j.check(row, 'the admin tools are not saved: %s' % j.sql1("select rules_required||'|'||daily_post_limit||'|'||block_links||'|'||review_posts from public.groups where id=%s" % gid))
    with j.step('Close and open the group again: the settings are kept'):
        gd_close(pg); groups_page(j, pg); open_card(j, pg, gname); manage(j, pg, 'settings')
        kept = pg.evaluate("[document.getElementById('wtRulesReq').checked,document.getElementById('wtDaily').value,document.getElementById('wtLinks').checked,document.getElementById('wtReview').checked,document.getElementById('wtCat').checked]")
        j.check(kept == [True, '1', True, True, True], 'the admin tools were not kept: %s' % kept)
        gd_close(pg)
    if j.demo:
        # the demo account administers one group: the member side is shown on another public group, set up as its admin would
        pg.evaluate("dxTrust.saveTools({key:'cmo'},{rules_required:true,daily_post_limit:1,block_links:true,require_category:true,review_posts:false})"); gname = 'CMO & Contract Manufacturing'
    with j.step('A member joins: the rules window first — "I accept" is needed'):
        groups_page(j, pm); open_card(j, pm, gname)
        t0 = join_with_rules(j, pm)
        j.check(re.search(r'Trade offers only|CMO|Respect|قواعد', t0), 'the rules window does not list the rules: "%s"' % t0[:200])
        mark = j.toast_mark(pm); mclick(j, pm, r'Accept and join|موافق وانضم', 'Accept and join'); said = ' '.join(j.toasts_since(pm, mark))
        j.check(mopen(pm) and re.search(r'I accept|موافق', said), 'joining without ticking "I accept" went through (toasts: %s)' % said)
        pm.locator('.dbk-ov #wtRulesOk').check(); mclick(j, pm, r'Accept and join|موافق وانضم', 'Accept and join'); j.settle(pm, 1600)
        j.check(re.search(r'Joined|انضممت|عضو', gd_header(pm)) or has_composer(pm), 'after accepting the rules the member is not in the group (header: %s)' % gd_header(pm)[:160])
        if j.live:
            j.check(j.wait_db("select count(*) from public.group_rule_acceptances where group_id=%s and user_id='%s'" % (gid, m['id']), 8, want='1'), 'the acceptance is not recorded')
            j.check(j.sql1("select count(*) from public.group_members where group_id=%s and user_id='%s'" % (gid, m['id'])) == '1', 'the member row is missing')
    with j.step('An invite link to an outside chat group is refused, saying why'):
        said = gpost_try(j, pm, 'Join our other group https://chat.whatsapp.com/AbCdEf %s' % t, 'market')
        j.check(re.search(r'outside chat groups|الجروبات الخارجية', said), 'a WhatsApp invite link was not refused with a reason (toasts: %s)' % said)
        if j.live: j.check(j.sql1("select count(*) from public.posts where group_id=%s and body like '%%chat.whatsapp%%'" % gid) == '0', 'the link post reached the database')
    with j.step('A post must say what it is: "general" is refused, a category goes'):
        said = gpost_try(j, pm, 'Hello everyone %s' % t, 'general')
        j.check(re.search(r'say what it is|يحدد نوعه', said), 'an uncategorised post was not refused (toasts: %s)' % said)
        said = gpost_try(j, pm, 'Available: lactose monohydrate 200 kg, CoA attached %s' % t, 'market')
        if j.live:
            j.check(re.search(r'group’s admins|مديري الجروب', said), 'the member is not told the post waits for the admins (toasts: %s)' % said)
            j.check(j.wait_db("select group_pending from public.posts where group_id=%s and body like '%%lactose monohydrate%%'" % gid, 8) == 't', 'the post is not waiting for the admins')
        else: j.check(not re.search(r'not allowed|refused|ممنوع', said), 'the categorised post was refused: %s' % said)
    if j.live:
        with j.step('Another member does not see the waiting post; the admin publishes it from Manage → Pending posts; then everyone sees it'):
            groups_page(j, pk); open_card(j, pk, gname); j.check(not any('lactose monohydrate' in p['text'] for p in gposts(pk)), 'another member sees a post that waits for the admins')
            j.reload(pg); groups_page(j, pg); open_card(j, pg, gname)
            txt = manage_tab(j, pg, 'pending'); j.check('lactose monohydrate' in txt, 'the pending post is not in Manage → Pending posts: "%s"' % txt[:200])
            mark = j.toast_mark(pg); pg.locator('#tab-wtpending [data-wtpub="yes"]').first.click(); j.settle(pg, 1500)
            j.check(j.wait_db("select group_pending from public.posts where group_id=%s and body like '%%lactose monohydrate%%'" % gid, 8, want='f'), 'the post is still waiting after Publish')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='group_post_published'" % m['id'], 8, want='1'), 'the author is not told the post was published')
            gd_close(pk); groups_page(j, pk); open_card(j, pk, gname)
            j.check(any('lactose monohydrate' in p['text'] for p in gposts(pk)), 'after Publish another member still does not see the post')
    with j.step('The daily limit: a second post the same day is refused, saying when to post again'):
        if j.demo: pass
        else: gd_close(pm); groups_page(j, pm); open_card(j, pm, gname)
        said = gpost_try(j, pm, 'Needed: HPMC E5 100 kg %s' % t, 'market')
        j.check(re.search(r'post\(s\) a day|منشور في اليوم', said), 'a post over the daily limit was not refused with the reason (toasts: %s)' % said)
    if j.live:
        with j.step('A join request to a private group shows the person\'s trade card to the admin (Manage → Requests)'):
            pid = seed_group(j, 'Private Traders %s' % t, g['id'], private=True); add_member(j, pid, g['id'], 'admin')
            j.sql("insert into public.trade_profiles (user_id, role, governorate, sells) values ('%s','distributor','Alexandria','Excipients') on conflict (user_id) do nothing" % k['id'])
            j.sql("insert into public.group_join_requests (group_id, user_id) values (%s,'%s')" % (pid, k['id']))
            j.reload(pg); groups_page(j, pg); open_card(j, pg, 'Private Traders %s' % t)
            manage(j, pg); pg.locator('#managePanel [data-gpq-tab]').first.click(); pg.wait_for_timeout(1500)
            j.wait(pg, "!!document.querySelector('#tab-requests .wt-req-card')", 8)
            rq = pg.evaluate("(document.getElementById('tab-requests')||{}).innerText||''")
            j.check(re.search(r'Distributor|موزع', rq) and re.search(r'Alexandria|الإسكندرية', rq), 'the request does not show the trade card: "%s"' % rq[:200])

@journey('J-COMMUNITY-W44')
def move_whatsapp_group(j):
    """A WhatsApp group moves honestly: its admin shares an invite link; each member opens it and joins by themselves after the rules; Drugbox marks a partner group."""
    t = j.tag[:5]
    if j.live:
        g = j.person('Gamal Admin'); pg = g['page']; m = j.person('Jihan Member'); pm = m['page']; k = j.person('Kamal Late'); pk = k['page']
        adm = j.person('Mona Moderator'); make_admin(j, adm['id']); pa = adm['page']; j.reload(pa)
        gname = 'Delta Traders %s' % t; gid = seed_group(j, gname, g['id'], rules='Trade offers only — no retail'); add_member(j, gid, g['id'], 'admin')
        j.sql("update public.groups set rules_required=true where id=%s" % gid); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); pm = pg; gname = 'Regulatory Affairs Egypt'
    with j.step('Manage → Invite link: how to move a WhatsApp group honestly, and "Make an invite link"'):
        groups_page(j, pg); open_card(j, pg, gname); txt = manage_tab(j, pg, 'invite')
        j.check(re.search(r'never imports phone numbers|عمره ما بيستورد أرقام', txt), 'the invite tab does not say Drugbox never imports numbers or members: "%s"' % txt[:200])
        pg.select_option('#wtLinkDays', '30'); pg.fill('#wtLinkMax', '2')
        pg.locator('#tab-wtinvite [data-wtlink="new"]').click(); j.settle(pg, 1500)
        j.wait(pg, "!!document.querySelector('#tab-wtinvite .wt-link-row code')", 8)
        link = pg.evaluate("(document.querySelector('#tab-wtinvite .wt-link-row code')||{}).innerText||''").strip()
        j.check(re.search(r'#/join/[A-Za-z0-9_-]{20,}$', link), 'no invite link is shown: "%s"' % link)
        if j.live: j.check(j.wait_db("select count(*) from public.group_invite_links where group_id=%s and max_uses=2 and revoked_at is null" % gid, 8, want='1'), 'the link is not in the database')
        j.data['link'] = link
    if j.live:
        with j.step('A member opens the link (signed in): the group, its rules, "I accept" → joins by themselves'):
            pm.goto(link); j.settle(pm, 2500)
            j.wait(pm, "!!document.querySelector('.dbk-ov')", 10); t0 = mtext(pm)
            j.check(re.search(re.escape(gname), t0) and re.search(r'Trade offers only', t0), 'the link does not show the group and its rules: "%s"' % t0[:200])
            j.check(re.search(r'You join by yourself|أنت بتنضم بنفسك', t0), 'the window does not say the person joins by themselves')
            pm.locator('.dbk-ov #wtRulesOk').check(); mclick(j, pm, r'Join group|انضم للجروب', 'Join group'); j.settle(pm, 2500)
            j.check(j.wait_db("select count(*) from public.group_members where group_id=%s and user_id='%s'" % (gid, m['id']), 10, want='1'), 'the member did not join through the link')
            j.check(j.sql1("select uses from public.group_invite_links where group_id=%s" % gid) == '1', 'the link did not count the use')
            j.check(j.sql1("select count(*) from public.group_rule_acceptances where group_id=%s and user_id='%s'" % (gid, m['id'])) == '1', 'the rules acceptance is not recorded')
        with j.step('The admin stops the link: someone who opens it later is told it no longer works'):
            j.reload(pg); groups_page(j, pg); open_card(j, pg, gname); manage_tab(j, pg, 'invite')
            pg.locator('#tab-wtinvite [data-wtlink="stop"]').first.click(); pg.wait_for_timeout(500); mclick(j, pg, r'Stop link|أوقف اللينك', 'Stop link'); j.settle(pg, 1200)
            j.check(j.wait_db("select revoked_at is not null from public.group_invite_links where group_id=%s" % gid, 8, want='t'), 'the link is not stopped')
            pk.goto(link); j.settle(pk, 2500); j.wait(pk, "!!document.querySelector('.dbk-ov')", 10)
            j.check(re.search(r'no longer works|مبقاش شغال', mtext(pk)), 'a stopped link does not say it no longer works: "%s"' % mtext(pk)[:160])
            j.check(j.sql1("select count(*) from public.group_members where group_id=%s and user_id='%s'" % (gid, k['id'])) == '0', 'someone joined through a stopped link')
        with j.step('Nobody can be added for them: an outsider cannot insert a member or list the group\'s links through the API'):
            r = pk.evaluate("([g,u])=>dxLive.sb.from('group_members').insert({group_id:+g,user_id:u}).then(r=>r.error?r.error.message:'added')", [gid, m['id']])
            j.check(r != 'added', 'an outsider added someone else to the group: %s' % r)
            r = pk.evaluate("g=>dxLive.sb.from('group_invite_links').select('token').eq('group_id',+g).then(r=>(r.data||[]).length)", gid)
            j.check(r == 0, 'an outsider reads the group\'s invite tokens')
        with j.step('The admin asks Drugbox to mark it a partner group; Drugbox approves in Admin → Review; the badge shows'):
            closed = manage_tab(j, pg, 'invite'); pg.locator('#tab-wtinvite [data-wtlink="partner"]').click(); pg.wait_for_timeout(600)
            pg.fill('.dbk-ov #wtPn', 'Our WhatsApp group of 640 traders moves here; I am its admin since 2021'); mclick(j, pg, r'^\W*(Send|إرسال)\W*$', 'Send'); j.settle(pg, 1200)
            j.check(j.wait_db("select status from public.group_partner_requests where group_id=%s" % gid, 8) == 'pending', 'the request did not reach Drugbox')
            from _biz import admin_review, admin_decide
            q = admin_review(j, pa, r'Partner groups|الجروبات الشريكة'); j.check(gname in q, 'the request is not in Admin → Review → Partner groups')
            admin_decide(j, pa, gname, ok=True)
            j.check(j.wait_db("select partner_at is not null from public.groups where id=%s" % gid, 8, want='t'), 'the group is not marked partner')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='group_partner_decided'" % g['id'], 8, want='1'), 'the admin is not told')
            j.reload(pm); groups_page(j, pm); j.wait(pm, "!!document.querySelector('#gx .wt-partner-b')", 8)
            card = pm.locator('#content .gcard').filter(has=pm.locator('.gcard-title', has_text=gname))
            j.check(re.search(r'Drugbox partner group|جروب شريك', card.first.inner_text()), 'the group card shows no partner badge')
    else:
        with j.step('Copy the link, open it: the group window says the person joins by themselves; stop the link → it no longer works'):
            pg.locator('#tab-wtinvite [data-wtlink="copy"]').first.click(); pg.wait_for_timeout(500)
            gd_close(pg); pg.evaluate("l=>{location.hash=l.slice(l.indexOf('#'))}", j.data['link']); j.settle(pg, 1500)
            j.check(not mopen(pg) or re.search(re.escape(gname) + r'|Join', mtext(pg)), 'opening the invite link shows something else: %s' % mtext(pg)[:120])
            close_dialogs(pg); groups_page(j, pg); open_card(j, pg, gname); manage_tab(j, pg, 'invite')
            pg.locator('#tab-wtinvite [data-wtlink="stop"]').first.click(); pg.wait_for_timeout(500); mclick(j, pg, r'Stop link|أوقف اللينك', 'Stop link'); j.settle(pg, 900)
            j.check(re.search(r'Stopped|متوقف', manage_tab(j, pg, 'invite')), 'the stopped link is not marked stopped')
            gd_close(pg); pg.evaluate("l=>{location.hash=l.slice(l.indexOf('#'))}", j.data['link']); j.settle(pg, 1500)
            j.check(re.search(r'no longer works|مبقاش شغال', mtext(pg)), 'a stopped link does not say it no longer works')

@journey('J-COMMUNITY-W17')
def held_for_review(j):
    """A post that looks like a sale to patients / pharmacies, a controlled substance or an invite link waits for Drugbox review — never deleted silently, the member is told."""
    t = j.tag[:5]; body = 'متوفر علبة واحدة للمريض بالروشتة %s' % t; clean = 'Available: paracetamol API for factories, 2 tons %s' % t
    if j.live:
        a = j.person('Adel Poster'); pg = a['page']; b = j.person('Basma Reader'); pb = b['page']
        adm = j.person('Mona Moderator'); make_admin(j, adm['id']); pa = adm['page']; j.reload(pa)
    else: pg = j.demo_signin(j.new_page()); pa = pg
    with j.step('Post a retail sale for a patient → the member is told it waits for Drugbox review, and why; the post says "waiting"'):
        j.nav(pg, 'feed'); mark = j.toast_mark(pg); feed_compose(j, pg, body); j.settle(pg, 2500)
        said = ' '.join(j.toasts_since(pg, mark))
        j.check(re.search(r'waiting for Drugbox review|قيد مراجعة Drugbox', said), 'the member is not told the post waits for review (toasts: %s)' % said[:200])
        j.wait(pg, "n=>[...document.querySelectorAll('#content .post')].some(p=>p.innerText.includes(n)&&p.querySelector('.wt-held'))", 8, t)
        j.check(pg.locator('#content .post', has_text=t).first.locator('.wt-held').count(), 'the held post does not say it waits for review')
        if j.live:
            j.check(j.wait_db("select review_hold from public.posts where user_id='%s' and body like '%%%s%%'" % (a['id'], t), 8) == 't', 'the post is not held in the database')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='auto_review' and data->'topics' ? 'retail'" % a['id'], 8, want='1'), 'the member got no notice naming the reason')
    if j.live:
        with j.step('Another member does not see the held post; the clean post shows at once'):
            feed_compose(j, pg, clean); j.settle(pg, 2000)
            j.reload(pb); j.nav(pb, 'feed'); j.settle(pb, 2000); txt = j.text(pb)
            j.check(t not in txt.replace(clean, ''), 'another member sees the held post')
            j.check(clean in txt, 'a normal B2B trade post did not show to another member')
            r = pb.evaluate("x=>dxLive.sb.from('posts').select('id').like('body','%'+x+'%').eq('review_hold',true).then(r=>(r.data||[]).length)", t)
            j.check(r == 0, 'another member reads the held post through the API')
    with j.step('Admin → Review → "Held for review": the post with its reason; Publish'):
        from _biz import admin_review, admin_decide
        q = admin_review(j, pa, r'Held for review|محجوز للمراجعة')
        j.check(t in q and re.search(r'Retail|تجزئة', q), 'the held post is not in the queue with its reason: "%s"' % q[:200])
        admin_decide(j, pa, t, ok=True)
        if j.live:
            j.check(j.wait_db("select review_hold from public.posts where user_id='%s' and body like '%%%s%%'" % (a['id'], t), 8, want='f'), 'Publish did not release the post')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='auto_review_decided' and data->>'outcome'='published'" % a['id'], 8, want='1'), 'the member is not told it is published')
            j.reload(pb); j.nav(pb, 'feed'); j.settle(pb, 2000); j.check(t in j.text(pb).replace(clean, ''), 'after Publish another member still does not see the post')
        else:
            j.check(t not in admin_review(j, pa, r'Held for review|محجوز للمراجعة'), 'the decided post stays in the queue')
    if j.live:
        with j.step('An offer of a controlled substance is held too; Drugbox removes it with a note; the member is told the reason'):
            off = 'Tramadol 225 mg strips %s' % t
            pg.evaluate("([u,n])=>dxLive.sb.from('trade_profiles').upsert({user_id:u,role:'distributor',governorate:'Cairo',sells:'Finished products'})", [a['id'], off])
            r = pg.evaluate("([u,n])=>dxLive.sb.from('products').insert({user_id:u,name:n,type:'supply',category:'finished'}).select('id,review_hold,status').single().then(r=>r.error?r.error.message:r.data)", [a['id'], off])
            j.check(isinstance(r, dict) and r.get('review_hold') and r.get('status') == 'paused', 'a controlled substance offer was not held: %s' % r)
            q = admin_review(j, pa, r'Held for review|محجوز للمراجعة'); j.check(off in q, 'the held offer is not in the queue')
            admin_decide(j, pa, off, ok=False, reason='Controlled substances are not traded on Drugbox')
            j.check(j.wait_db("select count(*) from public.products where name=$q$%s$q$" % off, 8, want='0'), 'Remove did not remove the offer')
            n = j.wait_db("select data->>'note' from public.notifications where user_id='%s' and type='auto_review_decided' and data->>'outcome'='removed'" % a['id'], 8)
            j.check(n and 'Controlled substances' in n, 'the member is not told why the offer was removed: %s' % n)
            j.reload(pg); notifs(j, pg)
            j.check(re.search(r'Drugbox removed your offer|Drugbox حذف عرضك', j.text(pg)), 'the notification does not say the offer was removed: %s' % j.text(pg)[:200])

@journey('J-COMMUNITY-W19')
def trader_report(j):
    """A trade problem goes to Drugbox with evidence instead of a public shaming; the trader replies; two moderators decide; both sides are told."""
    t = j.tag[:5]
    if j.live:
        trader = j.person('Tamer Trader'); pt = trader['page']; rep = j.person('Rania Reporter'); pr = rep['page']; other = j.person('Omar Other'); po = other['page']
        m1 = j.person('Mona Moderator'); m2 = j.person('Mahmoud Moderator'); make_admin(j, m1['id']); make_admin(j, m2['id'])
        for p in (m1['page'], m2['page']): j.reload(p)
    else: pr = j.demo_signin(j.new_page()); trader = {'local': 3}
    with j.step('Open the trader\'s profile → "Report a trade problem": reason, details, evidence (required)'):
        goto_profile(j, pr, trader if j.live else 3); j.wait(pr, "!!document.querySelector('.wt-tcard [data-wt=report]')", 8)
        pr.locator('.wt-tcard [data-wt=report]').click(); pr.wait_for_timeout(600)
        j.check(re.search(r'Two Drugbox moderators decide|مشرفين اتنين', mtext(pr)), 'the report window does not say two moderators decide')
        pr.select_option('#wtRr', 'non_delivery'); pr.fill('#wtRd', 'Paid 50%% in advance on 2 Sept for 200 kg MCC, nothing delivered by 15 Oct %s' % t)
        mark = j.toast_mark(pr); mclick(j, pr, r'Send to Drugbox|ابعت لـ Drugbox', 'Send to Drugbox'); said = ' '.join(j.toasts_since(pr, mark)) + ' ' + mtext(pr)
        j.check(mopen(pr) and re.search(r'evidence|دليل', said), 'a report without evidence was sent (toasts: %s)' % said[:200])
        from _biz import PDF
        pr.set_input_files('#wtRf', PDF); mark = j.toast_mark(pr); mclick(j, pr, r'Send to Drugbox|ابعت لـ Drugbox', 'Send to Drugbox'); j.settle(pr, 2500)
        j.check(re.search(r'Drugbox will check it|Drugbox هيراجعه', ' '.join(j.toasts_since(pr, mark))), 'the reporter is not told what happens next')
        if j.live:
            j.check(j.wait_db("select count(*) from public.trader_reports where reporter='%s' and reported='%s' and cardinality(evidence)=1 and status='open'" % (rep['id'], trader['id']), 10, want='1'), 'the report is not in the database with its evidence')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='trader_report'" % trader['id'], 8, want='1'), 'the trader is not told')
    if j.demo:
        with j.step('Admin → Review → Trader reports: the report with its evidence; one moderator\'s vote waits for a second'):
            from _biz import admin_review
            q = admin_review(j, pr, r'Trader reports|بلاغات التجار'); j.check(t in q and re.search(r'Two moderators decide|مشرفين اتنين', q), 'the report is not in the queue: %s' % q[:200])
            row = pr.locator('.dx-mod-row', has_text=t); row.locator('.dx-mod-ok').first.click(); pr.wait_for_timeout(600); mclick(j, pr, r'Vote: uphold|صوّت: تأكيد', 'Vote: uphold'); j.settle(pr, 1200)
            j.check(re.search(r'a second moderator decides|مشرف تاني', ' '.join(j.toasts(pr)) + admin_review(j, pr, r'Trader reports|بلاغات التجار')), 'one vote is not shown as waiting for a second moderator')
        return
    with j.step('The trader opens the notice → My trade reports → reads the claim and replies with their side'):
        j.reload(pt); j.nav(pt, 'notifs'); j.settle(pt, 1500)
        row = pt.locator('#content .notif-item').filter(has_text=re.compile(r'reported a problem|بلّغ عن مشكلة'))
        j.check(row.count(), 'the trader has no notice about the report: %s' % j.text(pt)[:200]); row.first.click(); pt.wait_for_timeout(1500)
        j.wait(pt, "!!document.querySelector('.dbk-ov .wt-reps')", 8); txt = mtext(pt)
        j.check(t in txt, 'the trader does not see what they are accused of: %s' % txt[:200])
        pt.locator('.dbk-ov textarea').first.fill('The goods were shipped on 10 Oct, courier receipt attached %s' % t)
        pt.locator('.dbk-ov [data-wtreply]').first.click(); j.settle(pt, 2000)
        j.check(j.wait_db("select replied_at is not null from public.trader_reports where reported='%s'" % trader['id'], 8, want='t'), 'the reply is not saved')
    with j.step('Moderator 1 votes Uphold → it waits for a second moderator; the trader\'s card shows nothing yet'):
        from _biz import admin_review, admin_decide
        p1 = m1['page']; q = admin_review(j, p1, r'Trader reports|بلاغات التجار')
        j.check(t in q and re.search(r'replied|ردّ', q), 'the queue does not show the report with the trader\'s reply: %s' % q[:300])
        row = p1.locator('.dx-mod-row', has_text=t); row.locator('.dx-mod-ok').first.click(); p1.wait_for_timeout(600)
        p1.locator('.dbk-ov textarea').fill('Invoice paid, no delivery note'); mclick(j, p1, r'Vote: uphold|صوّت: تأكيد', 'Vote: uphold'); j.settle(p1, 1500)
        j.check(j.sql1("select status from public.trader_reports where reported='%s'" % trader['id']) == 'open', 'one moderator decided the report alone')
        q = admin_review(j, p1, r'Trader reports|بلاغات التجار'); j.check(re.search(r'You voted|صوّتت', q), 'moderator 1 can vote again / is not told a second moderator decides')
    with j.step('Moderator 2 upholds too → upheld; both sides are told; the card shows the count (not the accusation)'):
        p2 = m2['page']; admin_review(j, p2, r'Trader reports|بلاغات التجار')
        row = p2.locator('.dx-mod-row', has_text=t); row.locator('.dx-mod-ok').first.click(); p2.wait_for_timeout(600); mclick(j, p2, r'Vote: uphold|صوّت: تأكيد', 'Vote: uphold'); j.settle(p2, 1500)
        j.check(j.wait_db("select status from public.trader_reports where reported='%s'" % trader['id'], 8, want='upheld'), 'two matching votes did not uphold the report')
        j.check(j.wait_db("select count(*) from public.notifications where user_id in ('%s','%s') and type='trader_report_decided'" % (trader['id'], rep['id']), 8, want='2'), 'both sides are not told')
        goto_profile(j, po, trader); j.wait(po, "!!document.querySelector('.wt-line .wt-warn')", 8)
        line = po.evaluate("(document.querySelector('.wt-line')||{}).innerText||''")
        j.check(re.search(r'1 report upheld by Drugbox|1 بلاغ أكّده Drugbox', line), 'the trader\'s card does not show the upheld report: "%s"' % line)
        j.check(t not in j.text(po), 'the accusation\'s words are shown on the trader\'s profile')
    with j.step('Privacy: another member reads no report, no evidence, no vote through the API'):
        r = po.evaluate("()=>Promise.all([dxLive.sb.from('trader_reports').select('id'),dxLive.sb.from('trader_report_votes').select('report_id')]).then(a=>a.map(x=>(x.data||[]).length))")
        j.check(r == [0, 0], 'another member reads reports or votes: %s' % r)

if __name__ == '__main__': main()
