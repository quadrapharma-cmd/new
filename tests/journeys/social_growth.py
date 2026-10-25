"""Social journey of the growth plan (AREA w-growth): the one-time question to members whose specialty is still the old sign-up
default "Regulatory Affairs" (the owner's decision 9). J-SOCIAL-W01 (docs/JOURNEYS.md)."""
import re
from _j import journey, main
from _biz import ui_ok, dlg_open, dlg_click, dlg_text
from _growth import T

def asked(j, pg, timeout=6):
    return j.wait(pg, "(()=>{const d=[...document.querySelectorAll('.dbk-ov')].pop();return !!d&&!!d.querySelector('#spSel')})()", timeout)

def demo_signup(j, pg, name):
    pg.click('#loginPage [onclick="showSignup()"]'); pg.wait_for_selector('#suName', state='visible', timeout=5000)
    pg.fill('#suName', name); pg.fill('#suEmail', 'w01.%s@journey.test' % j.tag); pg.fill('#suPw', 'Str0ng-pass!2026'); pg.select_option('#suRole', 'Regulatory Affairs')
    pg.click('#signupPage button.f-btn.dx-js-only'); j.wait_js(pg, "document.getElementById('app').getClientRects().length>0", 15); j.settle(pg, 900); j.skip_tour(pg)

@journey('J-SOCIAL-W01')
def specialty_question(j):
    """A member whose headline is still the old default 'Regulatory Affairs' is asked once to confirm or change it."""
    if j.live:
        me = j.person('Hala Old Member', role='Regulatory Affairs'); pg = me['page']
        j.check(j.sql1("select headline from public.profiles where id='%s'" % me['id']) == 'Regulatory Affairs', 'the sign-up did not store the specialty')
        with j.step('A brand-new account that chose Regulatory Affairs itself is not asked'):
            j.settle(pg, 2000); j.check(not asked(j, pg, 3), 'a new account that chose its specialty is asked')
        j.sql("update public.profiles set created_at = (select at from private.growth_marks where key='specialty_prompt_from') - interval '30 days' where id='%s'" % me['id'])   # an account from before the new sign-up form
        j.reload(pg)
    else:
        pg = j.new_page(); demo_signup(j, pg, 'Hala Old Member')
    with j.step('On coming in, the member is asked whether Regulatory Affairs is really their specialty'):
        j.check(asked(j, pg, 10), 'the member with the old default is not asked about the specialty')
        j.check(re.search(r'Regulatory Affairs', dlg_text(pg)), 'the question does not name the current specialty')
        ui_ok(j, pg, 'the specialty question')
    with j.step('"Ask me later" closes it without recording an answer'):
        dlg_click(j, pg, T(j, r'Ask me later', r'اسألني لاحقًا'), 'Ask me later'); j.settle(pg, 600)
        if j.live:
            j.check(j.sql1("select count(*) from public.member_prompts where user_id='%s'" % me['id']) == '0', '"Ask me later" recorded an answer')
            j.reload(pg); j.check(asked(j, pg, 10), 'after "Ask me later" the member is not asked again on the next visit')
        else:
            pg.evaluate("dxGrowthUI.specialty()"); j.check(asked(j, pg, 6), 'the question does not come back')
    with j.step('Choose "Quality Control / QA" and save: the profile headline changes'):
        pg.select_option('#spSel', 'Quality Control / QA'); dlg_click(j, pg, T(j, r'^\W*Save\W*$', r'^\W*حفظ\W*$'), 'Save'); j.settle(pg, 1200)
        j.check(not asked(j, pg, 1), 'the question stays open after saving')
        if j.live:
            j.check(j.wait_db("select headline from public.profiles where id='%s'" % me['id'], 6) == 'Quality Control / QA', 'the headline was not changed')
            j.check(j.sql1("select answer from public.member_prompts where user_id='%s' and key='specialty'" % me['id']) == 'Quality Control / QA', 'the answer was not recorded')
        j.nav(pg, 'profile'); j.check('Quality Control / QA' in j.text(pg, '#content .profile-headline'), 'the profile does not show the new specialty')
    with j.step('It is asked only once: after a reload nothing is asked'):
        if j.demo: j.skip('the demo signs in again as its sample account after a reload')
        j.reload(pg); j.settle(pg, 2500); j.check(not asked(j, pg, 3), 'the member is asked again after answering')
    with j.step('Another member keeps Regulatory Affairs: recorded, the headline stays, not asked again'):
        if j.demo: j.skip('checked in live (one demo account)')
        o = j.person('Karim Real Regulatory', role='Regulatory Affairs')
        j.sql("update public.profiles set created_at = (select at from private.growth_marks where key='specialty_prompt_from') - interval '30 days' where id='%s'" % o['id'])
        op = o['page']; j.reload(op); j.check(asked(j, op, 10), 'the second member is not asked')
        dlg_click(j, op, T(j, r'^\W*Save\W*$', r'^\W*حفظ\W*$'), 'Save'); j.settle(op, 1000)
        j.check(j.wait_db("select answer from public.member_prompts where user_id='%s'" % o['id'], 6) == 'Regulatory Affairs', 'keeping the specialty was not recorded')
        j.check(j.sql1("select headline from public.profiles where id='%s'" % o['id']) == 'Regulatory Affairs', 'the headline changed')
        j.reload(op); j.settle(op, 2500); j.check(not asked(j, op, 3), 'the member who kept it is asked again')

if __name__ == '__main__': main(__file__)
