/* No dead clicks: anything that looks clickable either does its own thing or, if it did nothing, goes to its logical destination. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function idle(fn) { var p = false; return function () { if (p) return; p = true; (window.requestIdleCallback || function (cb) { return setTimeout(cb, 1); })(function () { p = false; try { fn(); } catch (e) {} }, { timeout: 400 }); }; }   /* decoration waits until the page is on screen */
  function txt(el) { if (!el) return ''; var s = window.dxOrigText ? window.dxOrigText(el) : el.textContent; return s.replace(/\s+/g, ' ').replace(/[✓✔]/g, '').trim(); }   /* original text, so Arabic mode decides the same way */
  var LINKY = /(^|\s)(tag|chip|pill|hashtag|trend|ad|ads|sponsor|promo|banner|name|title|link|more|see-?all|view-?all|author|company|seller|brand|topic|badge|cta|headline|stat|count|sug|who|person|user|member|mygroup|mg-|sh-row|net-overview|sugg|gcard|me-row|post-av|profile-av-cam|badge-cat|jc-title|lc-title|sp-title|sc-title|dc-title|post-name|seller-name)/i;
  function looksClickable(el) {
    if (!el || el.nodeType !== 1 || el.closest('input,textarea,select,[contenteditable],#dxDock,.dbk-ov,#dxCmd,#dxHover')) return false;
    return getComputedStyle(el).cursor === 'pointer' || LINKY.test(el.className || '');
  }
  function explicit(el, target) {   /* only the pressed element and what lies between it and the clickable target count */
    for (var e = el; e && e !== document.body; e = e.parentElement) {
      if (e.hasAttribute('onclick') || e.hasAttribute('href') || e.tagName === 'LABEL' || e.tagName === 'SUMMARY' || /^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName) ||
        Array.prototype.some.call(e.attributes, function (a) { return /^data-(h|w|dl|go|mk|t|cs|deal|act|open|rfq|cmp|mco|slug|sq|tab|verify|upgrade|create|mine|a)$|^data-(h|w|mk|cs|dl)[a-z0-9]/.test(a.name); })) return true;
      if (e === target) break;
    }
    return false;
  }
  function user(name) { name = String(name || '').replace(/[✓✔]/g, '').trim(); return (window.USERS || []).find(function (u) { return u.name === name || (name.length > 3 && name.indexOf(u.name) === 0); }); }
  function company(name) {   /* exact name, or a name followed only by a separator ('Pharco · Cairo'); the longest such name wins, so a shorter company never takes a longer one's click */
    if (!window.dxDir) return null; name = String(name || '').trim(); if (!name) return null; var best = null;
    window.dxDir.companies().some(function (c) { var n = c.name; if (!n) return false; if (n === name) { best = c; return true; }
      if (name.length > n.length && name.indexOf(n) === 0 && !/^\s*[A-Za-z0-9\u0600-\u06FF&]/.test(name.slice(n.length)) && (!best || n.length > best.name.length)) best = c; return false; });
    return best;
  }
  function groupTitles() { return Array.prototype.map.call(document.querySelectorAll('#gx .gcard-title, #gx .mg-name'), txt).concat((window.GX_HTML || '').match(/class="gcard-title">([^<]+)</g) ? window.GX_HTML.match(/class="gcard-title">([^<]+)</g).map(function (s) { return s.replace(/.*>/, ''); }) : []); }
  function openGroup(name) {
    window.goto('groups');
    setTimeout(function () {
      var card = Array.prototype.find.call(document.querySelectorAll('#gx .gcard, #gx .mygroup'), function (c) { return txt(c).indexOf(name) >= 0 && c.getAttribute('onclick'); }) ||
                 Array.prototype.find.call(document.querySelectorAll('#gx .gcard'), function (c) { return txt(c).indexOf(name) >= 0; });
      if (!card) { D.toast(name); return; }
      if (card.getAttribute('onclick')) card.click(); else { card.scrollIntoView({ block: 'center' }); card.classList.remove('dx-flash'); void card.offsetWidth; card.classList.add('dx-flash'); }
    }, 80);
  }
  function search(q) { if (window.dxOpenSearch) { window.dxOpenSearch(); var i = document.querySelector('#dxCmd input'); if (i) { i.value = q; i.dispatchEvent(new Event('input', { bubbles: true })); } } }
  function changePhoto() {
    var inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/*';
    inp.onchange = function () { var f = inp.files[0]; if (!f) return; var r = new FileReader(); r.onload = function () {
      document.querySelectorAll('.profile-av, .profile-avatar, #meAvatar').forEach(function (a) { a.style.backgroundImage = 'url(' + r.result + ')'; a.style.backgroundSize = 'cover'; a.style.color = 'transparent'; });
      try { localStorage.setItem('dx_my_photo', r.result.length < 2e6 ? r.result : ''); } catch (e) {}
      D.toast('Profile photo updated'); }; r.readAsDataURL(f); };
    inp.click();
  }
  /* the logical destination of a clickable-looking element */
  function destination(el) {
    var t = txt(el), row = el.closest('.sugg-card,.sugg,.person,.net-card,.me-row,.post-head,.post,.jcard,.gcard,.mygroup,.sh-row,.notif-item,.dr-card') || el.parentElement;
    var cls = String(el.className || '') + ' ' + String((row && row.className) || '');
    if (/profile-av-cam/.test(cls)) return changePhoto;
    var u = user(t) || (row && user(txt(row.querySelector('.sugg-name,.post-name,.me-name,.p-name,.n-name,.name')))); if (u && /av|name|me-row|author|person|sugg|post-head|user/i.test(cls + ' ' + t)) return function () { window.gotoProfile ? window.gotoProfile(u.id) : search(u.name); };
    var co = company(t); if (co) return function () { window.dxHub ? window.dxHub.page(co.slug) : search(co.name); };
    if (el.closest('.dx-ic,.dx-seal') || /verified/i.test(t)) return null;   /* a verification seal is a label, not a link anywhere */
    var t2 = t.replace(/^[^A-Za-z\u0600-\u06FF]+/, ''); var g = t2.length >= 3 ? groupTitles().find(function (x) { return x && (t2 === x || t2.indexOf(x) === 0 || x.indexOf(t2) === 0 || (row && txt(row).replace(/^[^A-Za-z\u0600-\u06FF]+/, '').indexOf(x) === 0)); }) : null; if (g && /group|gcard|mygroup|mg-|sh-row|sug/i.test(cls) || (g && t.length < 60)) return function () { openGroup(g); };
    if (/^connections/i.test(t)) return function () { window.goto('network'); };
    if (/profile views|impressions|views/i.test(t)) return function () { window.goto('profile'); };
    if (/saved/i.test(t)) return function () { window.goto('saved'); };
    if (/^admin/i.test(t.replace(/^\W+/, ''))) return function () { window.goto('admin'); };
    if (/repost|reaction|likes?\b|comments?\b/i.test(t) && /\d/.test(t)) return function () { D.toast(t + ' — people in your network engaged with this post'); };
    if (/^#\w/.test(t) || /badge-cat|tag|chip|pill|topic|trend/i.test(cls)) return function () { search(t.replace(/\s*\d[\d,]*\s*posts?$/i, '').replace(/^#/, '')); };
    if (/hashtag|trend|topic|tag\b|kw|keyword/i.test(cls) && t && t.length < 50) return function () { search(t.replace(/\s*\d[\d,]*\s*(posts?|members?)?$/i, '').replace(/^#/, '')); };
    return null;
  }
  /* watch whether a click did anything; if not, act */
  var muts = 0;
  var QUIET = /^(data-i18n-|data-dx|placeholder|title|aria-label|tabindex|role|lang|dir)/;
  new MutationObserver(function (list) { for (var i = 0; i < list.length; i++) { var m = list[i]; if (m.type === 'characterData') continue; if (m.type === 'attributes' && QUIET.test(m.attributeName)) continue; muts++; } }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, characterData: true });
  var opened = 0, _open = window.open; window.open = function () { opened++; return _open.apply(window, arguments); };
  var inputs = 0; ['change', 'input'].forEach(function (t) { document.addEventListener(t, function () { inputs++; }, true); });   /* ticking a box or typing is an effect */
  document.addEventListener('click', function (e) {
    var el = e.target && e.target.closest ? e.target : null; if (!el) return;
    var target = el; while (target && target !== document.body && !looksClickable(target)) target = target.parentElement;
    if (!target || target === document.body || !target.closest('#content,#sidebar')) return;
    if (explicit(el, target)) return;
    if (el.closest('.f-opt,.dx-chip,.dx-chip-clear,.dx-chips,.dx-sugg,.dx-nores,.dx-term,abbr,.dbk-ov,#dxDock,.dx-tour,.tour-pop,#dxUndo,.dx-save-search,.ss-chip,.dx-ss,.mode-opt,.cf-tag.on,.sen-opt.on,.ptab.active,.tab.active,.active,[aria-selected=true]')) return;   /* other features own these */
    var before = { m: muts, p: document.body.getAttribute('data-page'), h: location.hash, o: opened, i: inputs };
    setTimeout(function () {
      var changed = muts - before.m > 2 || document.body.getAttribute('data-page') !== before.p || location.hash !== before.h || opened !== before.o || inputs !== before.i;
      if (changed) return;
      var go = destination(target); if (go) go();
    }, 380);
  });
  /* restore a photo chosen earlier */
  C.onRender('my-photo', function () { var ph = null; try { ph = localStorage.getItem('dx_my_photo'); } catch (e) {} if (!ph) return; document.querySelectorAll('.profile-av, #meAvatar').forEach(function (a) { if (a.dataset.ph) return; a.dataset.ph = '1'; a.style.backgroundImage = 'url(' + ph + ')'; a.style.backgroundSize = 'cover'; a.style.color = 'transparent'; }); });

  /* ── Names are links: any person or company name shown as text opens that profile or company page ── */
  var ENT_SKIP = 'a,button,input,textarea,select,.dx-entity,.dbk-ov,#dxCmd,#dxDock,.topbar,.lh,.post-input,[contenteditable]';
  function linkEntities() {
    var people = {}; (window.USERS || []).forEach(function (u) { people[u.name] = u; });
    var cos = {}; if (window.dxDir) window.dxDir.companies().forEach(function (c) { cos[c.name] = c; });
    document.querySelectorAll('#content b, #content strong, #content span, #content .name, #content h3, #content h4, #content small, #sidebar b, #sidebar span').forEach(function (el) {
      if (el.dataset.dxent || el.children.length || el.closest(ENT_SKIP)) return;
      var t = el.textContent.replace(/[✓✔]/g, '').trim(); if (t.length < 4 || t.length > 60) return;
      var u = people[t], co = !u && cos[t];
      if (!u && !co) return;
      if (getComputedStyle(el).cursor === 'pointer' && el.closest('[onclick],[data-hopen],[data-slug]')) return;   /* already handled by its card */
      el.dataset.dxent = u ? 'u' + u.id : 'c' + co.slug; el.classList.add('dx-entity'); el.setAttribute('role', 'link'); el.setAttribute('tabindex', '0');
      el.setAttribute('title', u ? 'Open ' + u.name + '\u2019s profile' : 'Open ' + co.name);
      if (window.dxI18nAttrs) window.dxI18nAttrs(el);   /* set after the page was translated: translate the tooltip now (Arabic only) */
    });
  }
  function openEntity(el) { var v = el.dataset.dxent || ''; if (v[0] === 'u' && window.gotoProfile) window.gotoProfile(+v.slice(1)); else if (v[0] === 'c' && window.dxHub) window.dxHub.page(v.slice(1)); }
  document.addEventListener('click', function (e) { var el = e.target.closest && e.target.closest('.dx-entity'); if (!el) return; e.preventDefault(); e.stopPropagation(); openEntity(el); }, true);
  document.addEventListener('keydown', function (e) { if (e.key !== 'Enter') return; var el = document.activeElement; if (el && el.classList && el.classList.contains('dx-entity')) { e.preventDefault(); openEntity(el); } });
  C.onRender('entity-links', idle(linkEntities));

  window.dxAfford = { destination: destination, looksClickable: looksClickable };
})();
