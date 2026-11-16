"""Walking «ملف جديد» in the browser tests (eBOX stage 2, 16/11/2026). The wizard is the stations الدولة → الرفع → القراءة والفرز and the
product card; confirming the card makes the dossier and opens the proposed tree, and approving the tree puts the files in their items."""


def to_upload(page, timeout=60000):
    """«ملف جديد» just opened (on the country): on to the upload station."""
    page.wait_for_selector('#auCard', timeout=timeout)
    page.click('#wizNext')
    page.wait_for_selector('#intakeBtn', timeout=timeout)


def to_card(page, timeout=60000):
    """From whichever station to the product card (nothing to do when already on it)."""
    for _ in range(4):
        if page.locator('#pcard').count():
            return
        page.wait_for_selector('#wizNext', timeout=timeout)
        page.click('#wizNext')
    page.wait_for_selector('#pcard', timeout=timeout)


def confirm_card(page, files=0, approve=False, then='board', timeout=120000):
    """«اعتماد البطاقة»: the dossier is made, its files arrive in the waiting box and the proposed tree shows them.
    files: how many waiting files to see there before going on; approve: «اعتماد الشجرة» too (each file into its item);
    then: the page of the dossier the test goes on with ('tree' stays; after an approval the page is 'prepare')."""
    page.click('#wizCreate')
    page.wait_for_function("() => location.hash.endsWith('/tree')", timeout=timeout)
    page.wait_for_function("() => typeof S === 'object' && !S.staging && !!S.tree && !!document.getElementById('treeSum')", timeout=timeout)
    if files:
        page.wait_for_function("n => document.querySelectorAll('#treeOut [data-pw]').length >= n", arg=files, timeout=timeout)
    if approve:
        page.wait_for_function("() => !S.prepWaitP && !!document.getElementById('treeGo')", timeout=timeout)
        page.click('#treeGo')
        page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=timeout)
    here = 'prepare' if approve else 'tree'
    if then != here:
        page.evaluate("p => { location.hash = location.hash.replace(/\\/[a-z]+$/, '/' + p); }", then)
    return page.evaluate("() => location.hash.split('/').pop()")
