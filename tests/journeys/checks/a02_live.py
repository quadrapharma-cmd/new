"""A-02 live check — run: python3 tests/journeys/checks/a02_live.py --target live
A-02 live check (not a numbered journey): a Drugbox admin manages the ticker, the sponsors and the site settings through
Admin: the ticker and the settings reach a normal member after a reload; sponsors are kept (no approved page shows
them to members — the Market Board became the Company Directory)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _j import journey, main
from _community import *

def admin_tab(j, pg, tab):
    close_dialogs(pg)
    a = pg.locator("#app [onclick=\"goto('admin')\"]"); a.first.scroll_into_view_if_needed(); a.first.click(); j.settle(pg, 900)
    pg.evaluate("t=>switchAdminTab(t)", tab); j.settle(pg, 1500)

@journey('A-02-CHECK', applies='live')
def a02(j):
    t = j.tag[:4]
    a = j.person('Drugbox Admin'); make_admin(j, a['id']); j.reload(a['page']); a['page'].wait_for_timeout(600); tour_off(j, a['page']); ap = a['page']
    m = j.person('Mona Member'); mp = m['page']
    with j.step('Ticker: add an item; a member sees it after a reload; Hide removes it; Delete deletes it'):
        admin_tab(j, ap, 'ticker'); ap.fill('#tkText', 'Check ticker item %s' % t); ap.click('.adm-tk-add'); j.settle(ap, 1500)
        j.check(j.wait_db("select count(*) from public.ticker_items where text='Check ticker item %s' and active" % t, 6) == '1', 'no active ticker row')
        j.check('Check ticker item %s' % t in j.text(ap), 'the admin list does not show it')
        j.reload(mp); mp.wait_for_timeout(2500)
        j.check(mp.evaluate("t=>document.body.innerText.includes(t)", 'Check ticker item %s' % t), 'the member does not see the ticker item')
        ap.locator('.admin-ticker-item', has_text='Check ticker item %s' % t).locator('.adm-tk-on').click(); j.settle(ap, 1200)
        j.check(j.wait_db("select active::text from public.ticker_items where text='Check ticker item %s'" % t, 6) == 'false', 'Hide did not store')
        j.reload(mp); mp.wait_for_timeout(2500)
        j.check(not mp.evaluate("t=>document.body.innerText.includes(t)", 'Check ticker item %s' % t), 'the hidden item still shows')
        ap.locator('.admin-ticker-item', has_text='Check ticker item %s' % t).locator('.adm-tk-del').click(); j.settle(ap, 1200); confirm(j, ap); j.settle(ap, 800)
        j.check(j.wait_db("select count(*) from public.ticker_items where text='Check ticker item %s'" % t, 6, want='0') == '0', 'Delete did not delete')
    with j.step('Sponsors: add one; a member sees it on the Market Board; Remove removes it'):
        admin_tab(j, ap, 'sponsors'); ap.click('.adm-sp-add'); ap.wait_for_timeout(500)
        ap.fill('.dbk-ov #spN', 'Check Sponsor %s' % t); ap.fill('.dbk-ov #spD', 'APIs and excipients'); mclick(j, ap, r'Add sponsor', 'Add sponsor'); j.settle(ap, 1200)
        j.check(j.wait_db("select count(*) from public.sponsored_suppliers where name='Check Sponsor %s'" % t, 6) == '1', 'no sponsor row')
        j.reload(ap); ap.wait_for_timeout(1500); admin_tab(j, ap, 'sponsors')   # the approved interface shows sponsors nowhere to members (the Market Board became the Directory)
        j.check('Check Sponsor %s' % t in j.text(ap), 'the sponsor is not kept after a reload'); ap.locator('[data-spid]', has_text='Check Sponsor %s' % t).locator('.adm-sp-del').click(); j.settle(ap, 1000); confirm(j, ap); j.settle(ap, 800)
        j.check(j.wait_db("select count(*) from public.sponsored_suppliers where name='Check Sponsor %s'" % t, 6, want='0') == '0', 'Remove did not remove')
    with j.step('Settings: the tagline saved by the admin shows for a member'):
        admin_tab(j, ap, 'settings')
        inp = ap.locator('#sSiteTag'); old = inp.input_value(); inp.fill('Check tagline %s' % t); ap.click('.adm-set-save'); j.settle(ap, 1200)
        j.check(j.wait_db("select value from public.settings where key='site_tagline'", 6) == 'Check tagline %s' % t, 'the tagline is not stored: %s' % j.sql1("select key||'='||value from public.settings order by key"))
        j.reload(mp); mp.wait_for_timeout(2500)
        j.check(mp.evaluate("t=>window.CMS.site_tagline===t", 'Check tagline %s' % t), 'the member does not get the tagline')
        inp = ap.locator('#sSiteTag'); inp.fill(old); ap.click('.adm-set-save'); j.settle(ap, 800)

if __name__ == '__main__': main(__file__)
