"""Social journeys — notifications: told promptly, notification → the thing it is about, mark read / clear, email
preferences (J-SOCIAL-41 … 44). Run: python3 tests/journeys/social_notifications.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE
from _social import *

def alerts_badge(pg):
    return pg.evaluate("(()=>{const e=[...document.querySelectorAll('#tnb-notifs [class*=badge],#mb-notifs [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length?e.innerText.trim():''})()")
def items(pg):
    return pg.eval_on_selector_all('#content .notif-item', 'e=>e.filter(x=>x.getClientRects().length).map(x=>({id:x.id,text:x.innerText,unread:x.classList.contains("unread")}))')
def notifs(j, pg): j.nav(pg, 'notifs'); j.settle(pg, 900); return items(pg)
def filt(j, pg, pat, what):
    el = j.find(pg, pat, scope='#content', exact=True); j.check(el, 'no "%s" filter' % what); el.click(); pg.wait_for_timeout(500); return items(pg)

@journey('J-SOCIAL-41')
def told_promptly(j):
    """A member is told promptly when something concerns him, without reloading."""
    if j.live:
        a = j.person('Dr. Adel Watcher'); b = j.person('Dr. Bassem Actor'); new = j.person('Dr. Nadia Fresh')
        p = post_db(j, a['id'], 'Adel post for notifications ' + j.tag)
        pa = a['page']; j.reload(pa); j.nav(pa, 'feed'); pb = b['page']; j.reload(pb)
    else:
        pa = j.demo_signin(j.new_page())
    def expect_one(kind_re, what, before):
        end = time.time() + 15
        while time.time() < end:
            rows = [r for r in j.sql("select type from public.notifications where user_id='%s' and from_user='%s'" % (a['id'], b['id'])).split('\n') if re.search(kind_re, r)]
            if rows: break
            time.sleep(0.5)
        j.check(rows, "B's %s created no notification for A in the database" % what)
        ok = j.wait(pa, "n=>{const e=[...document.querySelectorAll('#tnb-notifs [class*=badge],#mb-notifs [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length&&+e.innerText.trim()>n}", 30, arg=before)
        j.check(ok, "A's Alerts badge did not increase within 30 s after B's %s (no reload)" % what)
        rows = j.sql("select type from public.notifications where user_id='%s' and from_user='%s'" % (a['id'], b['id'])).split('\n')
        n = sum(1 for r in rows if re.search(kind_re, r)); j.check(n == 1, '%d notifications for the %s (want exactly 1)' % (n, what))
        return int(alerts_badge(pa) or 0)
    if j.live:
        cur = int(alerts_badge(pa) or 0)
        with j.step("B sends A a connection request (A's badge updates without reload)"):
            goto_profile(j, pb, a); j.click(pb, r'^\W*(Connect|تواصل|اتصال)$', scope='#content', what='Connect', exact=True)
            cur = expect_one(r'connection', 'connection request', cur)
        with j.step("B reacts to A's post"):
            j.nav(pb, 'feed'); post = pb.locator('#post-%s' % p)
            post.locator('.post-acts > .pact:nth-child(1) [onclick*="doReact"]:visible').first.click()
            cur = expect_one(r'like|reaction', 'reaction', cur)
        with j.step("B comments on A's post"):
            post.locator('.post-acts > .pact:nth-child(2)').click(); pb.wait_for_timeout(800)
            pb.fill('#ci-%s' % p, 'Congrats ' + j.tag); pb.press('#ci-%s' % p, 'Enter')
            cur = expect_one(r'comment', 'comment', cur)
        with j.step("A's Notifications page says each of them in the interface language (no English sentence in Arabic)"):
            rows = notifs(j, pa); j.check(len(rows) >= 3, 'A sees %d notifications, want the request, the reaction and the comment' % len(rows))
            if j.ar: j.check(not [r for r in rows if re.search(r'reacted to|commented|sent you|accepted your|removed your|reviewed your|messaged', r['text'])],
                             'notifications are written in English in the Arabic interface: %s' % [r['text'][:50] for r in rows if re.search(r'reacted to|commented|sent you|accepted your', r['text'])][:3])
            j.nav(pa, 'feed')
        with j.step("B replies to A's comment, mentions A, follows A and messages A — one notification each"):
            j.notbuilt('replies, mentions and person follows do not exist (see J-SOCIAL-15, -21, -33)')
    with j.step('Open Notifications; filter by Connections / Reactions / Comments: only matching kinds'):
        it = notifs(j, pa); j.check(it, 'no notifications listed')
        for pat, kind in ((r'^(Connections|اتصالات|الاتصالات)$', r'connect|تواصل|اتصال'), (r'^(Reactions|تفاعلات|التفاعلات)$', r'react|liked|أعجب|تفاعل'), (r'^(Comments|تعليقات|التعليقات)$', r'comment|علّق|تعليق')):
            rows = filt(j, pa, pat, pat)
            j.check(rows and all(re.search(kind, r['text'], re.I) for r in rows), 'the %s filter shows other kinds: %s' % (pat, [r['text'][:40] for r in rows][:3]))
            if j.ar: j.check(not [r for r in rows if re.search(r'reacted to|commented|sent you|accepted your|removed your|reviewed your|messaged', r['text'])],
                             'notifications are written in English in the Arabic interface: %s' % [r['text'][:50] for r in rows if re.search(r'[A-Za-z]{5,} (to|your|you)', r['text'])][:3])
    with j.step('A brand-new user starts with 0 notifications and badges hidden'):
        if j.demo: j.skip('a brand-new account exists only in live')
        pn = new['page']; j.check(alerts_badge(pn) in ('', '0'), 'a new user sees an Alerts badge "%s"' % alerts_badge(pn))
        j.check(not notifs(j, pn), 'a new user has notifications')

@journey('J-SOCIAL-42')
def notification_to_item(j):
    """From a notification the member goes straight to the thing it is about and acts on it."""
    if j.live:
        a = j.person('Dr. Amany Target'); b = j.person('Dr. Bahy Liker'); c = j.person('Dr. Cyrus Requester'); d = j.person('Dr. Dalia Accepter')
        p = int(post_db(j, a['id'], 'Amany post with activity ' + j.tag))
        j.sql("insert into public.reactions (post_id, user_id, kind) values (%d,'%s','like')" % (p, b['id']))
        comment_db(j, b['id'], p, 'Bahy comment on Amany post ' + j.tag)
        j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','pending')" % (c['id'], a['id']))
        j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','pending')" % (a['id'], d['id']))
        j.sql("update public.connections set status='accepted' where requester='%s' and addressee='%s'" % (a['id'], d['id']))
        j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Bahy message %s')" % (b['id'], a['id'], j.tag))
        pg = a['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); p = None
    def click_row(pat, what):
        it = notifs(j, pg); row = pg.locator('#content .notif-item').filter(has_text=re.compile(pat, re.I))
        j.check(row.count(), 'no %s notification' % what); n0 = int(alerts_badge(pg) or 0)
        row.first.locator('xpath=.').click(); j.settle(pg, 1000); return n0
    with j.step('Click the reaction notification: post P opens, scrolled into view'):
        click_row(r'react|liked|أعجب|تفاعل', 'reaction')
        page = pg.evaluate("document.body.getAttribute('data-page')")
        vis = pg.evaluate("(()=>{const e=[...document.querySelectorAll('#content .post')].find(x=>{const r=x.getBoundingClientRect();return r.top>=-5&&r.top<innerHeight});return !!e})()")
        j.check(page != 'notifs' and vis, 'dead end: clicking a reaction notification does not open the post (stays on %s)' % page)
        if j.live: j.check(pg.locator('#post-%d' % p).count(), 'the opened post is not P')
    with j.step('Back to Notifications; click the comment notification: P opens with comments expanded'):
        click_row(r'comment|علّق|تعليق', 'comment')
        j.check(pg.evaluate("[...document.querySelectorAll('#content [id^=cmt-]')].some(e=>e.getClientRects().length&&e.querySelector('.cmt'))"), 'the comment notification does not open P with the comments expanded')
    with j.step('Accept on the request row performs the real accept; View profile opens that profile'):
        notifs(j, pg); row = pg.locator('#content .notif-item').filter(has=pg.locator('button')).first
        j.check(row.count(), 'no request row with buttons'); who = row.inner_text().split('\n')[1] if j.demo else 'Cyrus'
        row.locator('button').filter(has_text=re.compile(r'Accept|قبول')).first.click(); pg.wait_for_timeout(800)
        if j.live: j.check(j.wait_db("select status from public.connections where requester='%s' and addressee='%s'" % (c['id'], a['id']), 5, want='accepted') == 'accepted', 'Accept on the notification did not accept in the database')
        vp = pg.locator('#content .notif-item button').filter(has_text=re.compile(r'View profile|عرض الملف'))
        j.check(vp.count(), 'no View profile on a request notification'); vp.first.click(); j.settle(pg, 900)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'profile', 'View profile does not open a profile')
    with j.step('Click the accepted notification (opens D) and the message notification (opens the thread with B)'):
        if j.demo: j.skip('these notification kinds exist in the sample only in live')
        click_row(r'accepted|قبل', 'accepted'); j.check('Dalia' in j.text(pg)[:400], 'the accepted notification does not open D')
        click_row(r'message|رسالة', 'message'); j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'messages' and 'Bahy' in j.text(pg, '#content .chat-head'), 'the message notification does not open the thread with B')
    with j.step('Each clicked notification is read (stored) and the badge decreased'):
        if j.demo: j.skip('the database exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and read=false" % a['id']) == '0', 'clicked notifications are not stored as read')
    with j.step('A notification about a deleted post says "no longer available"'):
        if j.demo: j.skip('the database exists only in live')
        j.sql("delete from public.posts where id=%d" % p); j.reload(pg)
        rows = pg.locator('#content .notif-item').filter(has_text=re.compile(r'react|comment', re.I))
        if rows.count():
            rows.first.click(); j.settle(pg)
            j.check(re.search(r'no longer available|not available|غير متاح|لم يعد', j.text(pg, 'body')[:3000]), 'a notification about a deleted post opens nothing and says nothing')

@journey('J-SOCIAL-43')
def mark_read_and_clear(j):
    """A member marks all notifications read or clears them, and the state is remembered."""
    if j.live:
        a = j.person('Dr. Aya Tidy'); b = j.person('Dr. Bassem Noisy')
        for i in range(6): j.sql("insert into public.notifications (user_id, type, from_user, message) values ('%s','system','%s','Note %d %s')" % (a['id'], b['id'], i, j.tag))
        pg = a['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Notifications → Mark all read: no bold rows, badges gone'):
        it = notifs(j, pg); j.check(any(x['unread'] for x in it), 'no unread notifications to start with')
        j.click(pg, r'Mark all read|تعليم الكل|تحديد الكل كمقروء|قراءة الكل', scope='#content', what='Mark all read'); pg.wait_for_timeout(600)
        j.check(not any(x['unread'] for x in items(pg)), 'rows are still unread after Mark all read')
        j.check(alerts_badge(pg) in ('', '0'), 'the Alerts badge still shows "%s"' % alerts_badge(pg))
    with j.step('Reload: they stay read'):
        if j.demo: j.skip('demo keeps no data across a reload (no backend) — checked in live')
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and read=false" % a['id'], 5, want='0') == '0', 'rows are not read=true in the database')
        j.reload(pg); j.check(not any(x['unread'] for x in notifs(j, pg)) and alerts_badge(pg) in ('', '0'), 'after reload notifications are unread again')
    with j.step('Clear all; Undo restores the list'):
        n = len(items(pg)); j.click(pg, r'Clear all|مسح الكل', scope='#content', what='Clear all'); pg.wait_for_timeout(500)
        ok = j.find(pg, r'^(Clear|Yes|Confirm|مسح|نعم|تأكيد)$', scope='body', exact=True)
        if ok: ok.click(); pg.wait_for_timeout(400)
        j.check(not items(pg), 'Clear all left rows')
        j.click(pg, r'^(Undo|تراجع)$', scope='body', what='Undo', exact=True); pg.wait_for_timeout(500)
        j.check(len(items(pg)) == n, 'Undo did not restore the %d notifications' % n)
    with j.step('Clear all again and wait 15 s; reload: empty (rows deleted)'):
        j.click(pg, r'Clear all|مسح الكل', scope='#content', what='Clear all'); pg.wait_for_timeout(400)
        ok = j.find(pg, r'^(Clear|Yes|Confirm|مسح|نعم|تأكيد)$', scope='body', exact=True)
        if ok: ok.click()
        if j.demo: j.check(re.search(r'No notifications|all caught up|لا توجد|لا إشعارات', j.text(pg), re.I), 'no empty state after Clear all'); return
        pg.wait_for_timeout(16000)
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s'" % a['id']) == '0', 'notification rows still exist after Clear all')
        j.reload(pg); j.check(not notifs(j, pg), 'after reload cleared notifications are back')
    with j.step('A new notification after clearing appears with badge 1'):
        j.sql("insert into public.notifications (user_id, type, from_user, message) values ('%s','system','%s','Fresh one %s')" % (a['id'], b['id'], j.tag))
        j.check(j.wait(pg, "(()=>{const e=[...document.querySelectorAll('#tnb-notifs [class*=badge],#mb-notifs [class*=badge]')].find(e=>e.getClientRects().length);return e&&e.getClientRects().length&&e.innerText.trim()==='1'})()", 30), 'the badge does not show 1 for the new notification')

@journey('J-SOCIAL-44', applies='live')
def notification_preferences(j):
    """A busy member chooses which notifications reach him by email."""
    a = j.person('Dr. Akram Busy'); pg = a['page']
    with j.step('Open Settings → Notifications'):
        el = j.find(pg, r'^(Settings|الإعدادات)$', exact=True)
        if not el: pg.click('#topAv'); j.settle(pg); el = j.find(pg, r'^(Settings|Notification settings|الإعدادات)$', exact=True)
        j.check(el, 'not built: no Settings page with notification preferences')
        el.click(); j.settle(pg)
        j.check(j.find(pg, r'Email|البريد', scope='#content'), 'not built: no email notification preferences')
    with j.step('Turn email on for messages and requests, off for reactions; daily digest; saved per user'):
        j.check(j.has_table('notification_prefs') or j.has_column('profiles', 'notify_email'), 'not built: preferences are not stored')
    with j.step("Sign out; B sends A a message, a request and a like; A's inbox gets one email each for the message and the request"):
        j.notbuilt('no notification emails: nothing sends them and the local stack has no mail catcher')

if __name__ == '__main__': main(__file__)
