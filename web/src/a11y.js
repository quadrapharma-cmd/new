/* Accessibility layer (WCAG 2.1 AA): names for unnamed controls, keyboard access to scroll areas. Visual fixes live in a11y.css. */
(function () {
  var C = window.dxCore; if (!C) return;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function named(el) {
    if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.getAttribute('title')) return true;
    if (el.id && document.querySelector('label[for="' + el.id.replace(/"/g, '') + '"]')) return true;
    if (el.closest('label') && txt(el.closest('label'))) return true;
    return false;
  }
  function fix() {
    /* form controls without a name get one from their placeholder or the text around them */
    document.querySelectorAll('input:not([type=hidden]),select,textarea').forEach(function (el) {
      if (named(el)) return;
      var box = el.closest('.f-opt,.cat-item,.dbk-f,.dr-ver,.fd-row,li,label,div'), fld = el.closest('.f-field,.dbk-f'), lab = fld && fld.querySelector('label,.f-label');
      var name = (lab && txt(lab)) || el.getAttribute('placeholder') || (box && txt(box).replace(el.tagName === 'SELECT' || el.tagName === 'TEXTAREA' ? txt(el) : '', '').trim().slice(0, 60)) || el.getAttribute('name') ||
        (el.tagName === 'SELECT' && el.options.length ? txt(el.options[Math.max(0, el.selectedIndex)]) : '');   /* the field's own label first; a list's options and a text box's contents are not its name */
      if (name) el.setAttribute('aria-label', name);
    });
    /* elements that act as buttons but have no name */
    document.querySelectorAll('[role=button],button').forEach(function (el) {
      if (txt(el) || el.getAttribute('aria-label') || el.getAttribute('title')) return;
      el.setAttribute('aria-label', el.classList.contains('btn-save') ? 'Save' : el.classList.contains('dk-h') ? 'Chat' : 'Button');
    });
    /* scroll areas reachable with the keyboard */
    document.querySelectorAll('#sidebar,.profile-tabs,.tp-filter-row,.cp-tabs,.dr-vs-row,.dx-ptabs,.hb-mk-tabs,.cm-res,.dk-b').forEach(function (el) {
      if (!el.hasAttribute('tabindex')) { el.setAttribute('tabindex', '0'); if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', el.id === 'sidebar' ? 'Navigation' : 'Scrollable list'); }
    });
  }
  C.onRender('a11y-names', fix);
})();
