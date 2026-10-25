"""Helpers of the growth-plan journeys (AREA w-growth): community_growth.py, business_growth.py, social_growth.py.
Kept apart so that importing them registers no journey of another file."""
import re, time
from _biz import close_dialogs, dlg_click, fill_by_label, make_admin
from _community import gd_open, gd_close

def T(j, en, ar_): return ar_ if j.ar else en

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


# ---- the marketplace (as business_market.py does it; copied, not imported: importing it would register its journeys) ----
def market(j, pg, tab='browse'):
    close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200)
    t = pg.locator('.master-tab[data-tab=%s]:visible' % tab)
    j.check(t.count(), 'not built: the marketplace has no "%s" tab' % tab); t.first.click(); j.settle(pg, 800)
    return pg.evaluate("t=>(document.querySelector('#tab-'+t)||{}).innerText||''", tab)

def cards(pg, sel='#tab-browse :is(.lcard,.dcard,.scard,.jcard,.sponsored-card)'):
    return pg.evaluate("s=>[...document.querySelectorAll(s)].filter(e=>e.getClientRects().length).map(e=>({cat:e.dataset.dxcat||'',t:(e.querySelector('.lc-title')||e).innerText.split('\\n')[0].trim(),txt:e.innerText}))", sel)

def fill_ph(j, pg, ph_re, val, root='#tab-create'):
    el = pg.evaluate_handle("([r,p])=>[...document.querySelectorAll(r+' input,'+r+' textarea')].find(e=>e.getClientRects().length&&new RegExp(p,'i').test(e.placeholder||''))||null", [root, ph_re]).as_element()
    if not el: j.notbuilt('no field "%s" in the listing form' % ph_re)
    el.fill(val); return el

def create_listing(j, pg, side, fields, certs=(), draft=False, coa=None):
    """Market → Create Listing → I'm Offering / I'm Seeking → fill by placeholder → Preview → Publish (or Save as Draft)."""
    market(j, pg, 'create')
    if not pg.locator('#bigOfferBtn:visible').count():
        ch = pg.locator('#tab-create :is(span,button,a):visible', has_text=re.compile(r'Change|تغيير')).first
        if ch.count(): ch.click(); pg.wait_for_timeout(500)
    pg.click('#bigOfferBtn' if side == 'offer' else '#bigSeekBtn'); pg.wait_for_timeout(600)
    for ph, v in fields: fill_ph(j, pg, ph, v)
    for c in certs:
        el = pg.locator('#tab-create :is(div,span,label,button):visible', has_text=re.compile(r'^\W*%s\W*$' % re.escape(c))).first
        if el.count(): el.click()
    if coa:   # the form's "COA / Spec sheet" takes a real file
        z = pg.locator('#tab-create .form-section.active .upload-zone-sm:visible').first
        j.check(z.count(), 'no COA upload in the listing form')
        with pg.expect_file_chooser() as fc: z.click()
        fc.value.set_files(coa); pg.wait_for_timeout(400)
        j.check(re.search(r'attached|مرفق', z.inner_text()), 'the COA file is not shown as attached')
    mark = j.toast_mark(pg)
    if draft:
        b = pg.locator('#tab-create button:visible', has_text=re.compile(r'Save as Draft|حفظ كمسودة')); j.check(b.count(), "no 'Save as Draft'"); b.first.click(); j.settle(pg, 900)
    else:
        b = pg.locator('#tab-create button:visible', has_text=re.compile(r'Preview Listing|معاينة')); j.check(b.count(), "no 'Preview Listing'"); b.first.click(); pg.wait_for_timeout(700)
        dlg_click(j, pg, r'Publish listing|انشر', 'Publish listing'); j.settle(pg, 1500)
    return j.toasts_since(pg, mark)

