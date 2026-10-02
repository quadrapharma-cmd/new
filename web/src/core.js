/* Drugbox core — the single place every add-on hooks into.
   · one navigation hook:   document events "dx:beforepage" / "dx:page"
   · one render bus:        dxOnRender(name, fn) — runs after the app renders, once per frame
   · isolation:             every feature runs inside its own try/catch
   · circuit breaker:       a feature that fails 3 times is switched off for the session
   · flags:                 localStorage "dx_flags" = {"featureName": false} turns a feature off
   · undo:                  dxUndo(message, onUndo, onCommit) — replaces "Are you sure?" dialogs */
(function () {
  if (window.dxCore) return;
  var flags = {}; try { flags = JSON.parse(localStorage.getItem('dx_flags') || '{}'); } catch (e) {}
  var fails = {}, broken = {};
  function on(name) { return flags[name] !== false && !broken[name]; }
  function run(name, fn, args) {
    if (!on(name)) return;
    try { return fn.apply(null, args || []); }
    catch (e) {
      fails[name] = (fails[name] || 0) + 1;
      if (window.console) console.warn('[drugbox] ' + name + ' failed (' + fails[name] + '/3)', e);
      if (fails[name] >= 3) { broken[name] = true; if (window.console) console.warn('[drugbox] ' + name + ' switched off for this session'); }
    }
  }
  /* one navigation hook */
  if (typeof window.goto === 'function') {
    var g = window.goto;
    window.goto = function (p) {
      document.dispatchEvent(new CustomEvent('dx:beforepage', { detail: { page: p } }));
      var r = g.apply(this, arguments);
      /* every page opens at its top — the content area is the scroller, not the window */
      var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0;
      if (window.scrollY) window.scrollTo(0, 0);
      document.dispatchEvent(new CustomEvent('dx:page', { detail: { page: p } }));
      return r;
    };
  }
  /* opening a profile is a navigation too: same events, same scroll reset */
  if (typeof window.gotoProfile === 'function') {
    var gp = window.gotoProfile;
    window.gotoProfile = function () {
      document.dispatchEvent(new CustomEvent('dx:beforepage', { detail: { page: 'profile' } }));
      var r = gp.apply(this, arguments);
      document.body.setAttribute('data-page', 'profile');
      var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0;
      if (window.scrollY) window.scrollTo(0, 0);
      document.dispatchEvent(new CustomEvent('dx:page', { detail: { page: 'profile' } }));
      return r;
    };
  }

  /* pages kept in memory (marketplace, jobs, groups) must not come back with a window still open */
  var OPEN_SEL = '#content .show[class*="overlay"], #content .show[class*="modal"], #content [class*="overlay"].open, #content [class*="modal"].open, #content .gx-modal.show, #content .jx-modal.show';
  function closeCachedWindows() { document.querySelectorAll(OPEN_SEL).forEach(function (el) { el.classList.remove('show'); el.classList.remove('open'); }); document.body.style.overflow = ''; }
  document.addEventListener('dx:beforepage', closeCachedWindows);
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var open = document.querySelectorAll(OPEN_SEL); if (open.length) { closeCachedWindows(); e.stopPropagation(); }
  });
  function onPage(name, fn, before) { document.addEventListener(before ? 'dx:beforepage' : 'dx:page', function (e) { run(name, fn, [e.detail.page]); }); }
  /* one render bus */
  var subs = [], queued = false, perf = {};
  function timed(s) { var t = performance.now(); run(s.name, s.fn); var d = performance.now() - t; var p = perf[s.name] || (perf[s.name] = { runs: 0, ms: 0, max: 0 }); p.runs++; p.ms += d; if (d > p.max) p.max = d; }
  /* run features in slices of at most ~8 ms, then yield to the browser so taps and scrolling stay smooth */
  var cursor = 0;
  function flush() {
    queued = false; var start = performance.now();
    while (cursor < subs.length) { timed(subs[cursor++]); if (performance.now() - start > 8 && cursor < subs.length) { queued = true; requestAnimationFrame(flush); return; } }
    cursor = 0;
  }
  function onRender(name, fn) { subs.push({ name: name, fn: fn }); if (!queued) { queued = true; requestAnimationFrame(flush); } }
  new MutationObserver(function (list) {
    if (queued) return;
    for (var i = 0; i < list.length; i++) {
      var n = list[i].addedNodes; if (!n.length) continue;
      /* ignore changes made by our own layers (floating widgets and in-page decorations) */
      var t = list[i].target; if (t && t.closest && t.closest('#dxHover,#dxTray,#dxSkel,#dxOk,#dxLoader,#dxUndo,.dx-pop,#dxTour,#dxDock,#dxTerm,#dxCmd,#dxForYou,#dxEditor,#dxCoSwitch,#dxCoMenu,#dxRfqTray,.dx-saved,.dx-insights,.dx-ic,.dx-tile,.dx-tools,.dx-chips,.dx-comb,.dx-certwall')) continue;
      var ours = true;
      for (var j = 0; j < n.length && ours; j++) { var x = n[j]; ours = x.nodeType === 3 ? !!(x.parentNode && x.parentNode.closest && x.parentNode.closest('abbr.dx-term,.dx-num,.dx-egp')) : !!(x.className && typeof x.className === 'string' && /(^|\s)dx-/.test(x.className)) || x.tagName === 'ABBR'; }
      if (ours) continue;
      queued = true; requestAnimationFrame(flush); return;
    }
  }).observe(document.body, { childList: true, subtree: true });

  /* undo bar (one at a time; a new one commits the previous) */
  var bar = document.createElement('div'); bar.id = 'dxUndo'; bar.setAttribute('role', 'status'); document.body.appendChild(bar);
  var pending = null, timer = null;
  function commitPending() { if (!pending) return; var p = pending; pending = null; clearTimeout(timer); bar.className = ''; run('undo-commit', function () { if (p.commit) p.commit(); }); }
  function undo(msg, onUndo, onCommit, ms) {
    commitPending(); ms = ms || 5000;
    pending = { undo: onUndo, commit: onCommit };
    bar.innerHTML = '<span class="u-msg"></span><button type="button" class="u-btn">Undo</button><i class="u-bar" style="animation-duration:' + ms + 'ms"></i>';
    bar.querySelector('.u-msg').textContent = msg;
    bar.querySelector('.u-btn').onclick = function () { var p = pending; pending = null; clearTimeout(timer); bar.className = ''; if (p && p.undo) run('undo', p.undo); };
    void bar.offsetWidth; bar.className = 'on';
    timer = setTimeout(commitPending, ms);
  }
  window.addEventListener('beforeunload', commitPending);
  document.addEventListener('dx:beforepage', commitPending);

  window.dxCore = { perf: perf, on: on, run: run, onPage: onPage, onRender: onRender, undo: undo, flags: flags };
  window.dxUndo = undo;
})();
