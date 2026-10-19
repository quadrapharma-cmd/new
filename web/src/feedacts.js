/* Home feed actions that used to end in a toast: reactions (the count, the kind chosen, who reacted), Save (and the Saved page),
   Copy link (a real link that opens the post), Report (reasons, once per post, decided in Admin → Review).
   The approved post card stays the template: only its state is painted (the reaction chosen, the count, "🔖 Saved").
   Data goes through window.dxPostSvc — this file's sample implementation in the demo, the database in the live app
   (web/src/live/adapter.js replaces reactors / report / reported / open / queue / decide). */
(function () {
  var D = window.DBK; if (!D || typeof window.renderPost !== 'function') return;
  var ICON = { like: '👍', support: '❤️', celebrate: '🎉', insightful: '💡', appreciation: '👏', curious: '🤔' };
  var LABEL = { like: 'Like', support: 'Support', celebrate: 'Celebrate', insightful: 'Insightful', appreciation: 'Appreciation', curious: 'Curious' };
  var REASONS = [['spam', 'Spam or unrelated ad'], ['counterfeit', 'Unverified or counterfeit product'], ['misleading', 'Misleading information'], ['abusive', 'Harassment or hate'], ['other', 'Something else']];
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function toast(m) { (window.toast || D.toast)(m); }
  function same(a, b) { return String(a) === String(b); }
  function find(id) {
    return (window.POSTS || []).find(function (p) { return same(p.id, id); }) || (window.SAVED_POSTS || []).find(function (p) { return same(p.id, id); }) || null;
  }
  function kindOf(p) { return p && p.liked ? (ICON[p.myKind] ? p.myKind : 'like') : null; }
  function cards(id) {   /* the Home cards of a post on the page (feed, profile activity, Saved) — never a group's own cards */
    return Array.prototype.filter.call(document.querySelectorAll('[id="post-' + id + '"]'), function (el) { return el.classList.contains('post') && !el.closest('#gpBox'); });
  }

  /* ── demo data source (in memory); the live adapter replaces what it needs ── */
  var REPORTS = [];
  if (!window.dxPostSvc) window.dxPostSvc = {
    reactors: function (p) { return Promise.resolve(p.liked ? [{ uid: window.ME.id, kind: kindOf(p) }] : []); },
    reported: function (p) { return Promise.resolve(REPORTS.some(function (r) { return same(r.pid, p.id) && r.mine; })); },
    report: function (p, reason, note) {
      if (REPORTS.some(function (r) { return same(r.pid, p.id) && r.mine; })) return Promise.resolve('already');
      var a = window.U ? window.U(p.uid) : null;
      REPORTS.unshift({ id: 'p' + Date.now(), pid: p.id, mine: true, author: a ? a.name : 'Member', reporter: window.ME.name, reason: reason, note: note, excerpt: String(p.body || '').slice(0, 300), n: 1 });
      return Promise.resolve('ok');
    },
    open: function (id) { return Promise.resolve(find(id)); },
    queue: function () { return REPORTS.slice(); },
    decide: function (id, value) {
      var r = REPORTS.find(function (x) { return x.id === id; }); if (!r) return Promise.resolve(true);
      REPORTS = REPORTS.filter(function (x) { return !same(x.pid, r.pid); });
      if (value === 'removed') { window.POSTS = (window.POSTS || []).filter(function (p) { return !same(p.id, r.pid); }); window.SAVED_POSTS = (window.SAVED_POSTS || []).filter(function (p) { return !same(p.id, r.pid); }); }
      return Promise.resolve(true);
    }
  };
  function svc() { return window.dxPostSvc; }

  /* ── the card shows the post's state: the reaction chosen, "🔖 Saved" (the approved saved look: .dbk-saved) ── */
  var oRender = window.renderPost;
  window.renderPost = function (post) {
    var h = oRender.apply(this, arguments);
    if (!post || typeof h !== 'string') return h;
    var k = kindOf(post);
    h = h.replace('" id="like-' + post.id + '" role="button">', '" id="like-' + post.id + '" role="button" tabindex="0" aria-pressed="' + (k ? 'true' : 'false') + '">');
    h = h.split('" data-rk="').join('" role="button" tabindex="0" data-rk="');   /* the six reactions: reachable with Tab from Like (the panel opens on focus) */
    if (k && k !== 'like') h = h.replace('onclick="doReact(parseInt(this.dataset.lp),\'like\')" style="display:flex;align-items:center;gap:5px">👍 Like</span>',
                                         'onclick="doReact(parseInt(this.dataset.lp),\'like\')" style="display:flex;align-items:center;gap:5px">' + ICON[k] + ' ' + LABEL[k] + '</span>');
    h = h.replace('<button class="pact" onclick="toast(\'Saved!\')">🔖 Save</button>', post.saved
      ? '<button class="pact dbk-saved" aria-pressed="true" onclick="toast(\'Saved!\')">🔖 Saved</button>'
      : '<button class="pact" aria-pressed="false" onclick="toast(\'Saved!\')">🔖 Save</button>');
    if (post.saved) h = h.replace('<div class="ctx-item" onclick="toast(\'Saved!\')">🔖 Save</div>', '<div class="ctx-item" onclick="toast(\'Saved!\')">🔖 Saved</div>');
    return h;
  };
  /* repaint the parts of a card that show state — the comments box and an expanded text stay as they are */
  function paint(post) {
    var box = document.createElement('div'); box.innerHTML = window.renderPost(post); var fresh = box.firstElementChild; if (!fresh) return;
    cards(post.id).forEach(function (el) {
      var st = el.querySelector(':scope > .post-stats'), nst = fresh.querySelector(':scope > .post-stats'), acts = el.querySelector(':scope > .post-acts');
      if (st && nst) st.replaceWith(nst.cloneNode(true)); else if (st) st.remove(); else if (nst && acts) acts.before(nst.cloneNode(true));
      var na = fresh.querySelector(':scope > .post-acts'); if (acts && na) acts.replaceWith(na.cloneNode(true));
      var pm = el.querySelector('[id="pm-' + post.id + '"]'), npm = fresh.querySelector('[id="pm-' + post.id + '"]'); if (pm && npm) pm.innerHTML = npm.innerHTML;
    });
  }
  window.dxFeedPaint = function (id) { var p = find(id); if (p) paint(p); };

  /* ── reactions: the Like button adds or takes back my reaction; the panel picks (or changes) its kind ── */
  var mainAt = 0;
  document.addEventListener('click', function (e) { if (e.target && e.target.closest && e.target.closest('[data-lp]')) mainAt = Date.now(); }, true);
  function setReaction(post, next) {
    var cur = kindOf(post); if (cur === next) return;
    var rx = post.reactions || (post.reactions = {});
    if (cur) { rx[cur] = Math.max(0, (rx[cur] || 1) - 1); if (!rx[cur]) delete rx[cur]; }
    if (next) rx[next] = (rx[next] || 0) + 1;
    post.likeCount = Math.max(0, (post.likeCount || 0) + (next ? 1 : 0) - (cur ? 1 : 0));
    post.liked = !!next; post.myKind = next || null;
    paint(post);
  }
  window.dxSetReaction = function (id, kind) { var p = find(id); if (p) setReaction(p, kind || null); };
  window.doReact = function (pid, kind) {
    var post = find(pid); if (!post) return;
    kind = ICON[kind] ? kind : 'like';
    var main = Date.now() - mainAt < 1500; mainAt = 0;
    var cur = kindOf(post);
    setReaction(post, cur ? (main || cur === kind ? null : kind) : kind);
  };
  window.likePost = function (pid) { mainAt = Date.now(); window.doReact(pid, 'like'); };   /* older callers: the Like button */
  /* keyboard: the Like card is a button (Enter / Space) */
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var t = e.target; if (!t || !t.matches || !t.matches('.post .pact[id^="like-"]') || t.closest('#gpBox')) return;
    e.preventDefault(); var lp = t.querySelector('[data-lp]'); if (lp) lp.click();
  });

  /* ── the reaction panel on every screen (Home, Saved, a profile's Activity, a group's posts — all the same card):
     a mouse opens it by hovering Like (as approved); a touch screen by pressing and holding Like (a quick tap still likes);
     the keyboard by Tab onto Like and on into the six reactions (Enter / Space choose, Escape closes).
     It always opens inside the screen: in right-to-left it grows from Like's right edge, and it is nudged in from an edge. ── */
  function likeOf(t) { var l = t && t.closest ? t.closest('.pact[id^="like-"]') : null; return l && l.querySelector('.rxn-panel') ? l : null; }
  function fit(l) { fitEl(l && l.querySelector('.rxn-panel')); }
  function fitEl(p) {
    if (!p) return;
    p.style.transform = '';
    var r = p.getBoundingClientRect(); if (!r.width) return;
    var vw = document.documentElement.clientWidth || window.innerWidth, m = 8, dx = 0;
    if (r.right > vw - m) dx = vw - m - r.right;
    if (r.left + dx < m) dx = m - r.left;
    if (dx) p.style.transform = 'translateX(' + Math.round(dx) + 'px)';
  }
  function fitSoon(l) { if (l) (window.requestAnimationFrame || setTimeout)(function () { fit(l); }); }
  function closeAll(except) { document.querySelectorAll('.pact.dx-rxn-open').forEach(function (o) { if (o !== except) o.classList.remove('dx-rxn-open'); }); }
  var press = null, held = null, quiet = false;
  function menuOf(b) { return b && b.parentElement ? b.parentElement.querySelector('[id^="pm-"]') : null; }
  document.addEventListener('pointerover', function (e) {
    if (e.pointerType !== 'mouse') return; fitSoon(likeOf(e.target));
    var b = e.target.closest && e.target.closest('.post [data-mpid]'), m = menuOf(b); if (m) (window.requestAnimationFrame || setTimeout)(function () { fitEl(m); });
  }, true);
  /* the post ⋯ menu (Save / Copy link / Report …): hovering opens it (approved); a click or a tap on ⋯ opens it too — before, a tap
     on a phone found nothing new on the page and was taken for a click on the author (it opened their profile) — and a tap
     anywhere else closes it */
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('.post [data-mpid]') : null, m = menuOf(b); if (!m) return;
    e.stopPropagation(); m.style.display = 'block'; m.setAttribute('data-dx-open', ''); fitEl(m);   /* stays open until a choice or a tap elsewhere */
  }, true);
  function shut(m) { m.removeAttribute('data-dx-open'); m.style.display = 'none'; }
  document.addEventListener('pointerdown', function (e) {
    document.querySelectorAll('.post [id^="pm-"][data-dx-open]').forEach(function (m) { if (!m.parentElement.contains(e.target)) shut(m); });
  }, true);
  document.addEventListener('click', function (e) { var it = e.target && e.target.closest ? e.target.closest('.post [id^="pm-"][data-dx-open] .ctx-item') : null; if (it) shut(it.closest('[id^="pm-"]')); }, true);
  document.addEventListener('focusin', function (e) {   /* keyboard focus on Like or a reaction keeps the panel open */
    var l = likeOf(e.target); if (!l || quiet) return;
    var kb = false; try { kb = e.target.matches(':focus-visible'); } catch (x) {}
    if (kb || l.classList.contains('dx-rxn-open')) { closeAll(l); l.classList.add('dx-rxn-open'); fit(l); }
  }, true);
  document.addEventListener('focusout', function (e) { var l = likeOf(e.target); if (l && !(e.relatedTarget && l.contains(e.relatedTarget))) l.classList.remove('dx-rxn-open'); }, true);
  document.addEventListener('pointerdown', function (e) {
    var l = likeOf(e.target); held = null; closeAll(l);
    if (press) { clearTimeout(press.t); press = null; }
    if (!l || e.pointerType === 'mouse' || e.target.closest('.rxn-panel')) return;
    press = { l: l, x: e.clientX, y: e.clientY, t: setTimeout(function () { press = null; held = l; l.classList.add('dx-rxn-open'); fit(l); }, 450) };
  }, true);
  document.addEventListener('pointermove', function (e) { if (press && Math.abs(e.clientX - press.x) + Math.abs(e.clientY - press.y) > 12) { clearTimeout(press.t); press = null; } }, true);
  ['pointerup', 'pointercancel'].forEach(function (n) { document.addEventListener(n, function () { if (press) { clearTimeout(press.t); press = null; } }, true); });
  /* the long press opened the panel: the click that ends it is not a Like */
  window.addEventListener('click', function (e) {
    if (!held) return; var l = likeOf(e.target);
    if (l === held && !e.target.closest('.rxn-panel')) { e.preventDefault(); e.stopPropagation(); }
    held = null;
  }, true);
  document.addEventListener('contextmenu', function (e) { if (likeOf(e.target) && (held || press || e.pointerType === 'touch' || (window.matchMedia && matchMedia('(hover:none)').matches))) e.preventDefault(); }, true);
  /* a reaction chosen: the panel closes (Home repaints the card; a group card may not) */
  document.addEventListener('click', function (e) { if (e.target && e.target.closest && e.target.closest('.rxn-panel [data-rk]')) setTimeout(function () { closeAll(null); }, 0); });
  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if (e.key === 'Escape') {   /* closes the panel; the keyboard goes back to Like */
      var open = document.querySelector('.pact.dx-rxn-open'); if (!open) return;
      if (open.contains(t) && t !== open) { quiet = true; try { open.focus(); } finally { quiet = false; } }
      closeAll(null); return;
    }
    if ((e.key !== 'Enter' && e.key !== ' ') || !t || !t.matches || !t.matches('.rxn-panel [data-rk]') || t.closest('#gpBox')) return;
    e.preventDefault(); t.click();
  });

  /* who reacted: a window with the kinds and the people (not a toast) */
  window.showReactors = function (pid) {
    var post = find(pid); if (!post) return;
    var rx = post.reactions || {}, total = post.likeCount || 0;
    var m = D.modal({ title: 'Reactions', secondary: 'Close', body: '<div class="dx-rx-sum">' + esc(total.toLocaleString('en-US')) + ' · ' +
      Object.keys(ICON).filter(function (k) { return rx[k]; }).map(function (k) { return '<span title="' + LABEL[k] + '">' + ICON[k] + ' ' + rx[k] + '</span>'; }).join(' ') +
      '</div><div class="dx-rx-list"><div class="dx-rx-more">Loading…</div></div>' });
    svc().reactors(post).then(function (list) {
      var box = m.el.querySelector('.dx-rx-list'); if (!box) return;
      var h = (list || []).map(function (r) {
        var u = window.U ? window.U(r.uid) : null; if (!u) return '';
        return '<button type="button" class="dx-rx-row" data-rxu="' + esc(u.id) + '">' + (window.av ? window.av(u, 36) : '') +
          '<span class="dx-rx-who"><b>' + esc(u.name) + (u.id === window.ME.id ? ' (you)' : '') + '</b><small>' + esc((u.headline || '').split('|')[0].trim()) + '</small></span>' +
          '<span class="dx-rx-k" title="' + LABEL[r.kind] + '">' + (ICON[r.kind] || '👍') + '</span></button>';
      }).join('');
      var rest = total - (list || []).length;
      if (rest > 0) h += '<div class="dx-rx-more">' + (h ? 'and ' + rest.toLocaleString('en-US') + ' more' : rest.toLocaleString('en-US') + ' people reacted') + '</div>';
      box.innerHTML = h || '<div class="dx-rx-more">No reactions yet</div>';
    }, function (e) { var box = m.el.querySelector('.dx-rx-list'); if (box) box.innerHTML = '<div class="dx-rx-more">' + esc((e && e.message) || 'Could not load the reactions') + '</div>'; });
    m.el.addEventListener('click', function (e) { var r = e.target.closest && e.target.closest('[data-rxu]'); if (!r) return; m.close(); window.gotoProfile(r.dataset.rxu); });
  };

  /* ── Save: the card's 🔖 Save and ⋯ → Save keep the post in Saved (newest saved first) ── */
  window.savePost = function (id) {
    var post = find(id); if (!post) return;
    post.saved = !post.saved;
    window.SAVED_POSTS = (window.SAVED_POSTS || []).filter(function (p) { return !same(p.id, id); });
    if (post.saved) window.SAVED_POSTS.unshift(post);
    paint(post);
    if (!post.saved && document.body.getAttribute('data-page') === 'saved') window.renderSaved(document.getElementById('content'));
    toast(post.saved ? 'Post saved! 🔖' : 'Post removed from saved');
  };
  window.unsavePost = function (id) { var p = find(id); if (p && p.saved) window.savePost(id); };
  /* the Saved page: the saved posts as the approved post cards (Like, Comment, Save work there too); the approved empty state */
  var oSaved = window.renderSaved;
  window.renderSaved = function (c) {
    var list = window.SAVED_POSTS || [];
    if (!c || !list.length) return oSaved.apply(this, arguments);
    c.innerHTML = '<div class="saved-list"><h1 style="font-size:22px;font-weight:800;color:var(--cx);margin-bottom:14px">🔖 Saved Posts</h1>' +
      '<div class="dx-saved-posts">' + list.map(function (p) { return window.renderPost(p); }).join('') + '</div></div>';
  };

  /* ── Copy link: a link that opens this post (after signing in when needed) ── */
  function linkOf(id) { return location.href.split('#')[0] + '#/post/' + id; }
  function copyText(s) {
    var fallback = function () { try { var t = document.createElement('textarea'); t.value = s; t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); } catch (e) {} };
    try { if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(s).catch(fallback); } catch (e) {}
    fallback(); return Promise.resolve();
  }
  window.dxPostLink = linkOf;
  /* open one post: Home, scrolled to it (the live adapter first fetches a post that is not on the first page) */
  window.dxOpenPost = function (id, opt) {
    return Promise.resolve(svc().open(id)).then(function (p) {
      if (!p) { toast('This post is no longer available'); return; }
      if (document.body.getAttribute('data-page') !== 'feed' || !cards(p.id).length) window.goto('feed');
      var el = cards(p.id)[0]; if (!el) { toast('This post is no longer available'); return; }
      if (opt && opt.comments) { var cb = document.getElementById('cmt-' + p.id); if (cb && cb.style.display === 'none') window.toggleComments(p.id); }   /* a comment notification: the comments open */
      el.scrollIntoView({ block: 'center' }); el.classList.remove('dx-post-hit'); void el.offsetWidth; el.classList.add('dx-post-hit');
    }, function (e) { toast((e && e.message) || 'This post is no longer available'); });
  };
  var PENDING = null;
  function fromHash() { var m = /^#\/?post\/(\d+)$/.exec(location.hash || ''); return m ? +m[1] : null; }
  PENDING = fromHash();
  function inApp() { var a = document.getElementById('app'); return !!a && a.getClientRects().length > 0; }
  document.addEventListener('dx:page', function (e) {
    if (PENDING == null || !e.detail || e.detail.page !== 'feed') return;
    var id = PENDING; PENDING = null;
    setTimeout(function () { window.dxOpenPost(id); history.replaceState(null, '', location.pathname + location.search); }, 60);
  });
  window.addEventListener('hashchange', function () {
    var id = fromHash(); if (id == null) return;
    if (inApp()) { window.dxOpenPost(id); history.replaceState(null, '', location.pathname + location.search); } else PENDING = id;
  });

  /* ── Report: reasons, once per post; Drugbox reviews it in Admin → Review → Reported posts ── */
  function report(id) {
    var post = find(id); if (!post) return;
    svc().reported(post).then(function (yes) {
      if (yes) { toast('You already reported this post — Drugbox is reviewing it'); return; }
      D.modal({ title: 'Report this post', body: '<p class="gp-muted">Drugbox reviews every report. The author is not told who reported.</p>' +
        REASONS.map(function (r, i) { return '<label class="gp-radio"><input type="radio" name="dxRep" value="' + r[0] + '"' + (i ? '' : ' checked') + '> <span>' + r[1] + '</span></label>'; }).join('') +
        '<div class="dbk-f"><label for="dxRepN">Details (optional)</label><textarea id="dxRepN" maxlength="500" placeholder="What should Drugbox know?"></textarea></div>',
        primary: { label: 'Report', danger: true, onClick: function (bx) {
          var reason = (bx.querySelector('input[name=dxRep]:checked') || { value: 'other' }).value, note = bx.querySelector('#dxRepN').value.trim();
          svc().report(post, reason, note).then(function (r) { toast(r === 'already' ? 'You already reported this post — Drugbox is reviewing it' : 'Thanks — Drugbox will review this post'); },
            function (e) { toast((e && e.message) || 'Could not send the report — try again'); });
        } } });
    }, function (e) { toast((e && e.message) || 'Could not send the report — try again'); });
  }

  /* the card's own Save / Copy link / Report end in a toast (that markup is the approved template, also used by group posts):
     on a Home card they do the real thing instead */
  document.addEventListener('click', function (e) {
    var si = e.target && e.target.closest ? e.target.closest('[onclick*="Saved items"]') : null;   /* the feed sidebar's "🔖 Saved items" opens Saved */
    if (si) { e.preventDefault(); e.stopPropagation(); window.goto('saved'); return; }
    var t = e.target && e.target.closest ? e.target.closest('.pact, .ctx-item') : null; if (!t) return;
    var oc = t.getAttribute('onclick') || '', card = t.closest('.post[id^="post-"]'); if (!card || card.closest('#gpBox')) return;
    var act = /Saved!/.test(oc) ? 'save' : /Link copied!/.test(oc) ? 'link' : /Reported!/.test(oc) ? 'report' : null; if (!act) return;
    e.preventDefault(); e.stopPropagation();
    var id = card.id.slice(5), menu = t.closest('[id^="pm-"]'); if (menu) menu.style.display = 'none';
    var n = /^\d+$/.test(id) ? +id : id;
    if (act === 'save') window.savePost(n);
    else if (act === 'link') copyText(linkOf(n)).then(function () { toast('Link copied!'); });
    else report(n);
  }, true);
})();
