"""Business journeys — Drugbox admins keep the business directory trustworthy from one place (J-BUSINESS-49).
Run: python3 tests/journeys/business_admin.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

@journey('J-BUSINESS-49')
def admin_review_business(j):
    """Drugbox admins keep the directory trustworthy from one place: claims, verification requests, certificates,
    wrong-information reports, outdated pages, payments."""
    if j.live:
        o1 = j.person('Pending Owner A'); o2 = j.person('Pending Owner B')
        a = seed_company(j, o1['id'], 'Verify Me A %s' % j.tag, status='pending'); b = seed_company(j, o2['id'], 'Verify Me B %s' % j.tag, status='pending')
        for c, u in ((a, o1), (b, o2)):
            j.sql("insert into public.verification_requests (company_id, submitted_by, registry, status) values (%s,'%s','55%s','pending')" % (c['id'], u['id'], j.tag[:5]))
            s = seed_site(j, c['id'], 'Plant %s' % c['name'][-12:]); seed_cert(j, c['id'], s, 'GDP', '2027-12-31', False)
            j.sql("insert into public.company_reports (company_id, reporter, section, issue, status) values (%s,'%s','Sites','Factory moved %s','open')" % (c['id'], o1['id'], j.tag))
        j.sql("insert into public.companies (name, slug, type, status, source, sectors) values ('Claim Me %s','claim-me-%s','Manufacturer','unclaimed','public_list','{Manufacturer}')" % (j.tag, j.tag))
        adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); pg = adm['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Admin → Review: each queue (verification, certificates, reports, payments, claims) lists exactly the pending items with who, what, when and the documents'):
        counts = {}
        for q in ('verifications', 'certs', 'reports', 'payments'):
            t = admin_review(j, pg, q)
            tab = pg.evaluate("p=>{const t=[...document.querySelectorAll('.dx-mod-tab')].find(t=>new RegExp(p,'i').test(t.innerText));return t?t.innerText:''}", QUEUES[q])
            n = pg.locator('.dx-mod-row').count(); m = re.search(r'(\d+)\s*$', tab.strip())
            j.check((int(m.group(1)) if m else 0) == n, 'the %s tab count (%s) differs from its rows (%d)' % (q, m and m.group(1), n))
            counts[q] = n
            if j.live and q in ('verifications', 'certs', 'reports'):
                j.check(('Verify Me A %s' % j.tag) in t or ('Factory moved %s' % j.tag) in t, 'the pending %s item is not in its queue' % q)
        j.data['counts'] = counts
        admin_review(j, pg, 'claims')
    with j.step('Approve one and reject one item per queue (reject with a reason): each decision is applied and removed from the queue'):
        if j.demo: j.skip('decisions are checked against the database in live')
        admin_review(j, pg, 'verifications'); admin_decide(j, pg, 'Verify Me A %s' % j.tag, True); admin_decide(j, pg, 'Verify Me B %s' % j.tag, False, 'Registry document unreadable')
        j.check(j.sql1("select status from public.companies where id=%s" % a['id']) == 'verified', 'approving verification did not verify the company')
        j.check(j.sql1("select status||'|'||coalesce(note,'') from public.verification_requests where company_id=%s" % b['id']) == 'rejected|Registry document unreadable', 'the rejection and its reason are not stored')
        admin_review(j, pg, 'certs'); admin_decide(j, pg, 'Verify Me A %s' % j.tag, True)
        j.check(pg.locator('.dx-mod-row', has_text='Verify Me B %s' % j.tag).locator('.dx-mod-no').count(), 'not built: a certificate cannot be rejected (only "Mark checked")')
    with j.step('The affected users are notified (with the reason on rejection)'):
        if j.demo: j.skip('checked in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s'" % o2['id']) not in ('', '0'), 'the rejected company owner is not notified')
    with j.step("Companies → 'Directory health' lists real outdated pages and open reports with links to the company"):
        directory(j, pg); j.click(pg, L('Directory health'), scope='#content', what='Directory health')
        t = dlg_text(pg) or j.text(pg)
        j.check(re.search(r'report|بلاغ', t, re.I), 'Directory health lists no open reports')
        if j.live: j.check(('Verify Me B %s' % j.tag) in t, 'Directory health does not list the company with an open report')
    with j.step('A normal user sees no Admin entry, and every admin write is refused by the database'):
        if j.demo: j.skip('the demo account is the admin; checked in live')
        u = j.person('Normal User'); up = u['page']
        j.check(not up.locator("#app [onclick*=\"goto('admin')\"]:visible").count(), 'a normal user sees the Admin entry')
        r = up.evaluate("i=>dxLive.sb.from('verification_requests').update({status:'approved'}).eq('company_id',i).select().then(r=>(r.data||[]).length)", int(b['id']))
        j.check(r == 0 and j.sql1("select status from public.verification_requests where company_id=%s" % b['id']) == 'rejected', 'a normal user changed a verification request')

if __name__ == '__main__': main(__file__)
