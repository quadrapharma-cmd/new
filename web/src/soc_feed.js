/* Feed (area social): safe links, #hashtags (a tag page) and @mentions in posts; Edit my post (with an "edited" marker); Repost
   (with an optional comment, shown in Home as "… reposted") and Send in a message; replies under a comment and likes on
   comments; the composer's photo / file previews can be removed and added to; an end marker after the last post.
   The approved post card stays the template — only its own toasts become the real actions, and the comment rows keep the
   approved markup. Data goes through window.dxFeedSvc: the sample implementation here (in this browser), the database in the
   live app (web/src/live/social.js). */
(function () {
  var D = window.DBK; if (!D || typeof window.renderPost !== 'function') return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(id) { return document.getElementById(id); }
  function toast(m) { (window.toast || D.toast)(m); }
  function same(a, b) { return String(a) === String(b); }
  function U(id) { return window.U ? window.U(id) : {}; }
  function me() { return window.ME || {}; }
  function find(id) { return (window.POSTS || []).find(function (p) { return same(p.id, id); }) || (window.SAVED_POSTS || []).find(function (p) { return same(p.id, id); }) ||
    (window.dxTagPosts || []).find(function (p) { return same(p.id, id); }) || null; }
  function cards(id) { return [].filter.call(document.querySelectorAll('[id="post-' + id + '"]'), function (el) { return el.classList.contains('post') && !el.closest('#gpBox'); }); }
  function inFeed() { return document.body.getAttribute('data-page') === 'feed'; }

  /* ── the sample data source; the live app replaces it ── */
  var REPOSTS = [], SEQ = 1;
  window.dxFeedSvc = window.dxFeedSvc || {
    live: false,
    edit: function (p, body, cat) { p.body = body; p.cat = cat; p.edited = true; return Promise.resolve(p); },
    repost: function (p, note) { REPOSTS = REPOSTS.filter(function (r) { return !(same(r.pid, p.id) && r.uid === me().id); }); REPOSTS.unshift({ pid: p.id, uid: me().id, note: note, ts: 'just now', at: Date.now() });
      p.reposted = true; p.shareCount = (p.shareCount || 0) + 1; return Promise.resolve(); },
    unrepost: function (p) { REPOSTS = REPOSTS.filter(function (r) { return !(same(r.pid, p.id) && r.uid === me().id); }); p.reposted = false; p.shareCount = Math.max(0, (p.shareCount || 1) - 1); return Promise.resolve(); },
    reposts: function () { return REPOSTS; },
    people: function (q) { q = String(q || '').toLowerCase(); return Promise.resolve((window.USERS || []).filter(function (u) { return u.id !== me().id && u.name && u.name.toLowerCase().indexOf(q) >= 0; }).slice(0, 8)); },
    send: function (u, text) { if (D.sendToOutbox) D.sendToOutbox({ to: u.name, text: text }); return Promise.resolve(); },
    comment: function (pid, text, parent) { return Promise.resolve({ id: 'c' + (SEQ++) }); },
    likeComment: function (c, on) { return Promise.resolve(); },
    byTag: function (tag) { var re = new RegExp('(^|[^\\w&])#' + tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![\\w])', 'i'); return Promise.resolve((window.POSTS || []).filter(function (p) { return re.test(p.body || ''); })); },
    done: function () { return true; },
    mentions: function (p, list) { return Promise.resolve(); }
  };
  function S() { return window.dxFeedSvc; }

  /* ── text of a post: http(s) links (rel=noopener), #tags (their page) and @mentions (the person) ── */
  function linkify(h, post) {   /* h is already escaped text (no < >): only the matches become links */
    var ms = (post && post.mentions) || [];
    h = h.replace(/(^|[\s(])((?:https?:\/\/)[^\s<>"']+[^\s<>"'.,;:!?)\]])/g, function (m, a, u) {
      return a + '<a href="' + u + '" target="_blank" rel="noopener noreferrer nofollow" class="dx-link" data-noi18n>' + u + '</a>'; });
    h = h.replace(/(^|[^\w&;\/#])#([\w؀-ۿ]{1,60})/g, function (m, a, t) { return a + '<a href="#/tag/' + encodeURIComponent(t.toLowerCase()) + '" class="dx-tag" data-tag="' + esc(t.toLowerCase()) + '" data-noi18n>#' + t + '</a>'; });
    ms.slice().sort(function (x, y) { return (y.name || '').length - (x.name || '').length; }).forEach(function (m) {
      var n = esc(m.name || ''); if (!n) return; var i = h.indexOf('@' + n); if (i < 0) return;
      h = h.slice(0, i) + '<a href="#/profile/' + m.uid + '" class="dx-mention" data-gp="' + m.uid + '" data-noi18n>@' + n + '</a>' + h.slice(i + n.length + 1);
    });
    return h;
  }
  window.dxLinkify = linkify;

  /* ── the card: links in the text, "edited", Edit / Repost / Send for real, comment threads ── */
  var oRender = window.renderPost;
  window.renderPost = function (post) {
    var h = oRender.apply(this, arguments); if (!post || typeof h !== 'string') return h;
    var id = post.id, k = h.indexOf('id="pb-' + id + '"');
    if (k >= 0) { var a = h.indexOf('>', k) + 1, e1 = h.indexOf('<span id="pb-ell-' + id + '"', a), e2 = h.indexOf('</div>', a), z = e1 >= 0 && e1 < e2 ? e1 : e2;
      if (a > 0 && z > a) h = h.slice(0, a) + linkify(h.slice(a, z), post) + h.slice(z); }
    if (post.edited) h = h.replace(' · 🌐', ' · <span class="dx-edited" title="Edited">edited</span> · 🌐');
    h = h.replace('onclick="toast(\'Edit coming soon\')">✏️ Edit</div>', 'data-ep-edit="' + id + '" onclick="dxEditPost(this.dataset.epEdit)">✏️ Edit</div>');
    h = h.replace('<button class="pact" onclick="toast(\'Reposted!\')">🔄 Repost</button>', post.reposted
      ? '<button class="pact dx-reposted" aria-pressed="true" data-rpp="' + id + '" onclick="dxRepost(this.dataset.rpp)">🔄 Reposted</button>'
      : '<button class="pact" aria-pressed="false" data-rpp="' + id + '" onclick="dxRepost(this.dataset.rpp)">🔄 Repost</button>');
    h = h.replace(/(<button class="pact[^"]*"[^>]*>🔖 Save[d]?<\/button>)<\/div>/, '$1<button class="pact dx-send" type="button" data-snd="' + id + '" onclick="dxSendPost(this.dataset.snd)">Send</button></div>');
    /* the comment rows: the same markup, with Like and Reply that work, replies under their comment */
    var f = h.indexOf('onclick="submitComment(parseInt(this.dataset.scc))">➤</button></div>');
    if (f >= 0) { var s = f + 'onclick="submitComment(parseInt(this.dataset.scc))">➤</button></div>'.length, end = h.lastIndexOf('</div></div></div>');
      if (end >= s) h = h.slice(0, s) + commentsHtml(post) + h.slice(end); }
    return h;
  };
  function cmtRow(post, cm, reply) {
    var cu = U(cm.uid), parentU = reply && cm.to != null ? U(cm.to) : null;
    var o = '<div class="cmt' + (reply ? ' dx-cmt-reply' : '') + '"' + (cm.id != null ? ' data-cid="' + esc(cm.id) + '"' : '') + '><div class="cmt-av" style="background:' + esc(cu.color) + '">' +
      (cu.avatar ? '<img src="' + (window.escSrc ? window.escSrc(cu.avatar) : esc(cu.avatar)) + '" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%">' : esc(cu.initials)) + '</div>';
    o += '<div class="cmt-bubble"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px"><div>';
    o += '<span class="cmt-name" data-gcp="' + cu.id + '" onclick="gotoProfile(this.dataset.gcp)" style="cursor:pointer">' + esc(cu.name) + (cu.verified ? ' &#10003;' : '') + '</span>';
    o += '<span style="font-size:11px;color:#9ca3af"> · ' + esc((cu.headline || '').split('|')[0].trim().split(' ').slice(0, 3).join(' ')) + '</span>';
    o += '</div><span style="font-size:11px;color:#9ca3af;white-space:nowrap">' + esc(cm.ts || 'just now') + '</span></div>';
    if (parentU && parentU.name) o += '<div class="dx-replying-to">↳ <span>Replying to</span> <b data-noi18n>' + esc(parentU.name) + '</b></div>';
    o += '<div class="cmt-text">' + esc(cm.text) + '</div>';
    o += '<div style="display:flex;gap:12px;margin-top:5px">';
    o += '<span role="button" tabindex="0" class="dx-cmt-like' + (cm.liked ? ' on' : '') + '" aria-pressed="' + (cm.liked ? 'true' : 'false') + '" style="font-size:11.5px;font-weight:700;color:' + (cm.liked ? 'var(--cp)' : '#65676b') + ';cursor:pointer" data-cl="' + esc(cm.id) + '" data-clp="' + esc(post.id) + '" onclick="dxCmtLike(this.dataset.clp,this.dataset.cl)">' + (cm.likes ? '👍 ' + cm.likes : 'Like') + '</span>';
    o += '<span role="button" tabindex="0" style="font-size:11.5px;font-weight:700;color:#65676b;cursor:pointer" data-cr="' + esc(cm.id) + '" data-crp="' + esc(post.id) + '" onclick="dxCmtReply(this.dataset.crp,this.dataset.cr)">Reply</span>';
    o += '</div></div></div>';
    return o;
  }
  function commentsHtml(post) {
    var list = (window.COMMENTS || {})[post.id] || [], top = list.filter(function (c) { return c.parent == null; }), o = '';
    list.forEach(function (c, i) { if (c.id == null) c.id = 'c' + post.id + '-' + i; });
    top.forEach(function (c) {
      o += cmtRow(post, c, false);
      var rs = list.filter(function (r) { return r.parent != null && same(r.parent, c.id); });
      if (rs.length) o += '<div class="cmt-replies">' + rs.map(function (r) { return cmtRow(post, Object.assign({ to: c.uid }, r), true); }).join('') + '</div>';
    });
    list.filter(function (r) { return r.parent != null && !top.some(function (c) { return same(c.id, r.parent); }); }).forEach(function (r) { o += cmtRow(post, r, false); });   /* a reply whose comment is gone */
    return o;
  }
  function redrawComments(pid) {
    var p = find(pid); if (!p) return;
    cards(pid).forEach(function (el) { var bx = el.querySelector('.cmt-box'), form = bx && bx.querySelector('.cmt-form'); if (!form) return;
      while (form.nextSibling) form.nextSibling.remove(); form.insertAdjacentHTML('afterend', commentsHtml(p)); });
    if (window.dxFeedPaint) window.dxFeedPaint(p.id);                                   /* the "N comments" count */
  }
  window.dxRedrawComments = redrawComments;

  /* ── replies and comment likes ── */
  var REPLY = {}, TOGGLE0 = window.toggleComments;
  window.dxCmtReply = function (pid, cid) {
    var p = find(pid); if (!p) return; var list = (window.COMMENTS || {})[p.id] || [], c = list.find(function (x) { return same(x.id, cid); }); if (!c) return;
    var top = c.parent != null ? c.parent : c.id, who = U(c.uid);
    REPLY[p.id] = { parent: top, name: who.name };
    cards(p.id).forEach(function (el) {
      var form = el.querySelector('.cmt-form'); if (!form) return; var chip = form.parentElement.querySelector('.dx-reply-chip');
      if (!chip) { form.insertAdjacentHTML('beforebegin', '<div class="dx-reply-chip" role="status"><span>Replying to</span> <b data-noi18n></b> <button type="button" class="dx-reply-x" aria-label="Cancel reply">×</button></div>'); chip = form.parentElement.querySelector('.dx-reply-chip'); }
      chip.querySelector('b').textContent = who.name || '';
    });
    var inp = $('ci-' + p.id); if (inp) { inp.focus(); }
  };
  document.addEventListener('click', function (e) {
    var x = e.target.closest && e.target.closest('.dx-reply-x'); if (!x) return;
    var post = x.closest('.post'); if (!post) return; var pid = post.id.slice(5); delete REPLY[/^\d+$/.test(pid) ? +pid : pid]; delete REPLY[pid];
    document.querySelectorAll('[id="' + post.id + '"] .dx-reply-chip').forEach(function (c) { c.remove(); });
  });
  function replyOf(pid) { return REPLY[pid] || REPLY[String(pid)] || null; }
  /* Enter / ➤: a reply goes under its comment; a comment updates the count at once (the approved code added the row only) */
  var oSubmit = window.submitComment;
  window.submitComment = function (pid) {
    var r = replyOf(pid), inp = $('ci-' + pid), text = inp ? inp.value.trim() : '';
    if (!r) { var out = oSubmit.apply(this, arguments); var p0 = find(pid), l0 = (window.COMMENTS || {})[pid];
      if (p0 && l0 && l0.length) { var last = l0[l0.length - 1]; if (last && last.id == null) last.id = 'n' + (SEQ++); } redrawComments(pid); return out; }
    return submitReply(pid);
  };
  function submitReply(pid) {
    var r = replyOf(pid), inp = $('ci-' + pid), text = inp ? inp.value.trim() : '';
    if (!r || !text) return;
    var p = find(pid); if (!p) return; var list = window.COMMENTS[p.id] || (window.COMMENTS[p.id] = []);
    var c = { id: 't' + (SEQ++), uid: me().id, text: text, ts: 'just now', parent: r.parent, likes: 0 };
    list.push(c); inp.value = ''; delete REPLY[pid]; delete REPLY[String(pid)];
    document.querySelectorAll('[id="post-' + p.id + '"] .dx-reply-chip').forEach(function (x) { x.remove(); });
    redrawComments(p.id);
    S().comment(p.id, text, r.parent).then(function (res) { if (res && res.id != null) { c.id = res.id; redrawComments(p.id); } },
      function (err) { var i = list.indexOf(c); if (i >= 0) list.splice(i, 1); redrawComments(p.id); toast((err && err.message) || 'Could not send the reply'); });
    toast('Reply posted');
  }
  window.dxSocFeed = { toggle0: TOGGLE0, submit: window.submitComment, replyOf: replyOf, submitReply: submitReply, redraw: redrawComments, linkify: linkify, find: find, cards: cards, endMarker: function () { endMarker(); } };
  window.dxCmtLike = function (pid, cid) {
    var p = find(pid); if (!p) return; var c = ((window.COMMENTS || {})[p.id] || []).find(function (x) { return same(x.id, cid); }); if (!c) return;
    var on = !c.liked; c.liked = on; c.likes = Math.max(0, (c.likes || 0) + (on ? 1 : -1)); redrawComments(p.id);
    S().likeComment(c, on, p).then(null, function (err) { c.liked = !on; c.likes = Math.max(0, (c.likes || 0) + (on ? -1 : 1)); redrawComments(p.id); toast((err && err.message) || 'Could not save the like'); });
  };
  document.addEventListener('keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('.dx-cmt-like,[data-cr]')) { e.preventDefault(); e.target.click(); } });

  /* ── Edit my post: the approved Create Post window, filled in ── */
  window.dxEditPost = function (id) {
    var p = find(id); if (!p || p.uid !== me().id) return;
    window.showPostModal();
    var m = [].slice.call(document.querySelectorAll('.modal-bg')).pop(); if (!m) return; m.classList.add('dx-edit-post');
    var hd = m.querySelector('.modal-hdr'); if (hd && hd.firstChild && hd.firstChild.nodeType === 3) hd.firstChild.nodeValue = 'Edit Post ';
    var ta = m.querySelector('#postBody'), cat = m.querySelector('#postCat'); if (ta) { ta.value = p.body || ''; var cc = $('charCount'); if (cc) cc.textContent = ta.value.length + '/5000'; }
    if (cat && p.cat) cat.value = p.cat;
    var add = m.querySelector('input[type=file]'); add = add && add.closest('div[style*="border-top"]'); if (add) [].forEach.call(add.querySelectorAll('label'), function (l) { l.style.display = 'none'; });
    var btn = m.querySelector('[onclick^="submitPost"]'); if (!btn) return;
    var row = document.createElement('div'); row.className = 'dx-edit-acts';
    row.innerHTML = '<button type="button" class="btn-ghost" data-ed="cancel">Cancel</button><button type="button" class="btn-p" data-ed="save">Save</button>';
    btn.replaceWith(row);
    row.addEventListener('click', function (e) {
      var b = e.target.closest('[data-ed]'); if (!b) return;
      if (b.dataset.ed === 'cancel') { m.remove(); return; }
      var body = ta.value.trim(), c = cat ? cat.value : p.cat; if (!body && !(p.imgs || []).length && !(p.files || []).length) { toast('Post cannot be empty'); return; }
      if (body === (p.body || '') && c === p.cat) { m.remove(); return; }
      b.disabled = true; var was = { body: p.body, cat: p.cat, edited: p.edited };
      S().edit(p, body, c).then(function () { m.remove(); repaintCard(p); toast('Post updated'); },
        function (err) { Object.assign(p, was); b.disabled = false; toast((err && err.message) || 'Could not save the change'); });
    });
    setTimeout(function () { if (ta) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); } }, 80);
  };
  function repaintCard(p) {
    cards(p.id).forEach(function (el) { var box = document.createElement('div'); box.innerHTML = window.renderPost(p); var n = box.firstElementChild; if (!n) return;
      var open = el.querySelector('[id="cmt-' + p.id + '"]'), head = el.querySelector(':scope > .dx-repost-head'); if (open && open.style.display !== 'none') { var nb = n.querySelector('[id="cmt-' + p.id + '"]'); if (nb) nb.style.display = 'block'; }
      if (head) n.insertBefore(head, n.firstChild); el.replaceWith(n); });
  }
  window.dxRepaintPost = repaintCard;

  /* ── Repost: a window like Create Post with the post and an optional comment ── */
  function modalBg(title, inner, cls) {
    var m = document.createElement('div'); m.className = 'modal-bg show ' + (cls || '');
    m.innerHTML = '<div class="modal" style="max-width:520px" role="dialog" aria-modal="true" aria-label="' + esc(title) + '"><div class="modal-hdr">' + esc(title) + ' <button class="modal-close" aria-label="Close" onclick="this.closest(\'.modal-bg\').remove()">×</button></div>' + inner + '</div>';
    document.body.appendChild(m); m.addEventListener('click', function (e) { if (e.target === m) m.remove(); });
    return m;
  }
  function preview(p) { var a = U(p.uid); return '<div class="dx-post-quote"><b data-noi18n>' + esc(a.name) + '</b><div data-noi18n>' + esc(String(p.body || '').slice(0, 220)) + (String(p.body || '').length > 220 ? '…' : '') + '</div></div>'; }
  window.dxRepost = function (id) {
    var p = find(id); if (!p) return;
    if (p.reposted) {
      var u = modalBg('Repost', '<p class="gp-muted">You reposted this post. Undo the repost?</p>' + preview(p) + '<div class="dx-edit-acts"><button type="button" class="btn-ghost" data-rp="cancel">Cancel</button><button type="button" class="btn-p" data-rp="undo">Undo repost</button></div>', 'dx-repost-modal');
      u.addEventListener('click', function (e) { var b = e.target.closest('[data-rp]'); if (!b) return; if (b.dataset.rp === 'cancel') return u.remove();
        b.disabled = true; S().unrepost(p).then(function () { u.remove(); afterRepost(p); toast('Repost removed'); }, function (err) { b.disabled = false; toast((err && err.message) || 'Could not undo the repost'); }); });
      return;
    }
    var m = modalBg('Repost', '<p class="gp-muted">Share this post with your network. Add your thoughts if you like.</p>' + preview(p) +
      '<textarea class="m-ta" id="rpNote" rows="3" maxlength="1000" placeholder="Add your thoughts (optional)"></textarea><div class="dx-edit-acts"><button type="button" class="btn-ghost" data-rp="cancel">Cancel</button><button type="button" class="btn-p" data-rp="ok">Repost</button></div>', 'dx-repost-modal');
    setTimeout(function () { var t = m.querySelector('#rpNote'); if (t) t.focus(); }, 60);
    m.addEventListener('click', function (e) { var b = e.target.closest('[data-rp]'); if (!b) return; if (b.dataset.rp === 'cancel') return m.remove();
      b.disabled = true; var note = m.querySelector('#rpNote').value.trim();
      S().repost(p, note).then(function () { m.remove(); afterRepost(p); toast('Reposted to your network'); }, function (err) { b.disabled = false; toast((err && err.message) || 'Could not repost'); }); });
  };
  function afterRepost(p) { if (inFeed()) window.goto('feed'); else repaintCard(p); }
  /* Home: reposts are cards of their own ("… reposted"), newest first among the posts */
  var oFeed = window.renderFeed;
  window.renderFeed = function (c) {
    var r = oFeed.apply(this, arguments);
    var col = c && c.querySelector('.post') ? c.querySelector('.post').parentElement : null;
    var list = (S().reposts() || []).slice(0, 30);
    if (col) list.slice().reverse().forEach(function (rp) {
      var p = rp.post || find(rp.pid); if (!p) return; var who = rp.uid === me().id ? null : U(rp.uid);
      var box = document.createElement('div'); box.innerHTML = window.renderPost(p); var card = box.firstElementChild; if (!card) return;
      card.classList.add('dx-repost-card');
      card.insertAdjacentHTML('afterbegin', '<div class="dx-repost-head">🔄 ' + (who ? '<b data-noi18n data-gp="' + who.id + '" onclick="gotoProfile(this.dataset.gp)">' + esc(who.name) + '</b> <span>reposted</span>' : '<span>You reposted</span>') +
        (rp.note ? '<div class="dx-repost-note" data-noi18n>' + esc(rp.note) + '</div>' : '') + '</div>');
      var at = rp.created_at ? new Date(rp.created_at).getTime() : 0, before = null;
      if (at) before = [].find.call(col.querySelectorAll(':scope > .post:not(.dx-repost-card)'), function (x) { var q = find(x.id.slice(5)); return q && q.created_at && new Date(q.created_at).getTime() < at && !q.pinned; });
      var first = col.querySelector(':scope > .post'); col.insertBefore(card, before || (first && !at ? first : before) || first);
    });
    endMarker(c);
    return r;
  };
  /* ── the end of Home: once every post is on the page ── */
  function endMarker(c) {
    c = c || $('content'); if (!c || !inFeed() && !(c.querySelector && c.querySelector('.feed-wrap'))) return;
    var first = c.querySelector('.feed-wrap .post'), col = first ? first.parentElement : null, old = c.querySelector('.dx-feed-end');
    if (!col || !S().done()) { if (old) old.remove(); return; }
    if (!old) { old = document.createElement('div'); old.className = 'dx-feed-end'; old.setAttribute('role', 'status'); old.innerHTML = '<span>✓</span> <span>You\'re all caught up — that\'s every post so far.</span>'; }
    if (col.lastElementChild !== old) col.appendChild(old);
  }
  if (window.dxCore) window.dxCore.onRender('soc-feed-end', function () { if (inFeed()) endMarker(); });

  /* ── Send in a message: pick a member, add a note, the message carries the post's link ── */
  window.dxSendPost = function (id) {
    var p = find(id); if (!p) return; var pick = null, t = null, link = window.dxPostLink ? window.dxPostLink(p.id) : location.href.split('#')[0] + '#/post/' + p.id;
    var m = modalBg('Send in a message', '<div class="m-field"><label class="m-label" for="sndTo">To</label><input class="m-input" id="sndTo" autocomplete="off" placeholder="Type a name…" role="combobox" aria-expanded="false" aria-controls="sndList"></div>' +
      '<div id="sndList" class="dx-snd-list" role="listbox" aria-label="Members"></div><div class="dx-snd-pick" id="sndPick" aria-live="polite"></div>' + preview(p) +
      '<textarea class="m-ta" id="sndNote" rows="2" maxlength="1000" placeholder="Add a note (optional)"></textarea><div class="dx-edit-acts"><button type="button" class="btn-ghost" data-sn="cancel">Cancel</button><button type="button" class="btn-p" data-sn="ok">Send</button></div>', 'dx-send-modal');
    var inp = m.querySelector('#sndTo'), list = m.querySelector('#sndList');
    function conn(u) { return (window.CONN_STATE || {})[u.id] === 'connected'; }
    function draw(people) { people = people.slice().sort(function (a, b) { return conn(b) - conn(a); }); list.innerHTML = people.map(function (u) { return '<button type="button" role="option" class="dx-snd-opt" data-u="' + u.id + '">' + (window.av ? window.av(u, 30) : '') + '<span><b data-noi18n>' + esc(u.name) + '</b><small data-noi18n>' + esc([(u.headline || '').split('|')[0].trim(), u.company].filter(Boolean).join(' · ')) + '</small>' +
      (conn(u) ? '<small class="dx-snd-conn">✓ Your connection</small>' : '') + '</span></button>'; }).join('') ||
      (inp.value.trim().length >= 2 ? '<div class="dx-snd-none">No member found</div>' : ''); inp.setAttribute('aria-expanded', people.length ? 'true' : 'false'); }
    inp.addEventListener('input', function () { pick = null; m.querySelector('#sndPick').textContent = ''; clearTimeout(t); var q = inp.value.trim(); if (q.length < 2) { draw([]); return; }
      t = setTimeout(function () { S().people(q).then(function (l) { if (inp.value.trim() === q) draw(l || []); }, function () { draw([]); }); }, 200); });
    m.addEventListener('click', function (e) {
      var o = e.target.closest('.dx-snd-opt'); if (o) { pick = U(+o.dataset.u); inp.value = pick.name; list.innerHTML = ''; var pk = m.querySelector('#sndPick'); pk.innerHTML = '<span>To:</span> <b data-noi18n></b>'; pk.querySelector('b').textContent = pick.name; return; }
      var b = e.target.closest('[data-sn]'); if (!b) return; if (b.dataset.sn === 'cancel') return m.remove();
      if (!pick) { inp.classList.add('dbk-err'); toast('Choose a member from the list'); return; }
      var note = m.querySelector('#sndNote').value.trim(), a = U(p.uid), text = (note ? note + '\n' : '') + '📝 ' + (a.name ? a.name + ': ' : '') + String(p.body || '').slice(0, 90) + (String(p.body || '').length > 90 ? '…' : '') + '\n' + link;
      b.disabled = true; S().send(pick, text, p).then(function () { m.remove(); toast('Sent to ' + pick.name); }, function (err) { b.disabled = false; toast((err && err.message) || 'Could not send'); });
    });
    setTimeout(function () { inp.focus(); }, 60);
  };

  /* ── the composer: previews that can be removed and added to; a size check; @mentions ── */
  var MAX_IMG = 10 * 1024 * 1024, MAX_FILE = 20 * 1024 * 1024, FILE_OK = /\.(pdf|docx|xlsx|zip)$/i;
  function drawImgs() {
    var prev = $('postImgPrev'); if (!prev) return; var l = window._postImgs || [];
    prev.style.display = l.length ? 'block' : 'none';
    prev.innerHTML = l.length ? '<div class="post-imgs ' + (l.length === 1 ? 'n1' : l.length === 2 ? 'n2' : 'n3') + ' dx-prev" style="border-radius:10px;overflow:hidden">' + l.slice(0, 10).map(function (u, i) {
      return '<div class="post-img-wrap" style="cursor:default;position:relative"><img src="' + esc(u) + '" alt=""><button type="button" class="dx-prev-x" data-rmi="' + i + '" aria-label="Remove photo">×</button></div>'; }).join('') + '</div>' : '';
  }
  function drawFiles() {
    var prev = $('postFilePrev'); if (!prev) return; var l = window._postFiles || [], icons = { pdf: '📄', docx: '📝', xlsx: '📊', zip: '🗜️' };
    prev.style.display = l.length ? 'block' : 'none';
    prev.innerHTML = l.map(function (f, i) { var ext = String(f.name || '').split('.').pop().toLowerCase();
      return '<div class="file-chip"><span class="file-chip-ic">' + (icons[ext] || '📎') + '</span><span class="file-chip-name">' + esc(f.name) + '</span><span class="file-chip-sz">' + (window.fmtSize ? window.fmtSize(f.size) : f.size) + '</span><button type="button" class="dx-prev-x" data-rmf="' + i + '" aria-label="Remove file">×</button></div>'; }).join('');
  }
  window.previewPostImgs = function (input) {
    var files = Array.from(input.files || []), bad = [];
    if (!Array.isArray(window._postImgs)) window._postImgs = [];
    files.forEach(function (f) {
      if (!/^image\/(jpeg|png|webp|gif)$/.test(f.type)) { bad.push(f.name + ' — not a photo (JPG, PNG, WebP or GIF)'); return; }
      if (f.size > MAX_IMG) { bad.push(f.name + ' — too big (max 10 MB)'); return; }
      if (window._postImgs.length >= 10) { bad.push(f.name + ' — at most 10 photos'); return; }
      window._postImgs.push(URL.createObjectURL(f));
    });
    input.value = ''; drawImgs(); if (bad.length) toast(bad[0]);
  };
  window.previewPostFile = function (input) {
    var f = input.files && input.files[0]; input.value = ''; if (!f) return;
    if (!FILE_OK.test(f.name)) { toast(f.name + ' — not accepted (PDF, Word, Excel or ZIP)'); return; }
    if (f.size > MAX_FILE) { toast(f.name + ' — too big (max 20 MB)'); return; }
    if (!Array.isArray(window._postFiles)) window._postFiles = [];
    if (window._postFiles.length >= 5) { toast('At most 5 files in a post'); return; }
    window._postFiles.push({ name: f.name, size: f.size, url: URL.createObjectURL(f) }); drawFiles();
  };
  document.addEventListener('click', function (e) {
    var x = e.target.closest && e.target.closest('#postImgPrev [data-rmi], #postFilePrev [data-rmf]'); if (!x) return; e.preventDefault(); e.stopPropagation();
    if (x.dataset.rmi != null) { (window._postImgs || []).splice(+x.dataset.rmi, 1); drawImgs(); } else { (window._postFiles || []).splice(+x.dataset.rmf, 1); drawFiles(); }
  }, true);
  /* a new composer starts empty (the approved code kept the previous window's photos) */
  var oModal = window.showPostModal;
  window.showPostModal = function () { window._postImgs = []; window._postFiles = []; MENTIONS = []; return oModal.apply(this, arguments); };

  /* @mentions: typing "@" and two letters lists members; choosing one writes "@Full Name" and remembers who it is */
  var MENTIONS = [], MT = null;
  function caretWord(ta) { var v = ta.value, i = ta.selectionStart, s = v.slice(0, i), m = /(^|\s)@([^\s@]{2,40})$/.exec(s); return m ? { q: m[2], at: i - m[2].length - 1, end: i } : null; }
  document.addEventListener('input', function (e) {
    var ta = e.target; if (!ta || ta.id !== 'postBody') return;
    var box = ta.parentElement.querySelector('.dx-mention-list'), w = caretWord(ta);
    if (!w) { if (box) box.remove(); return; }
    clearTimeout(MT); MT = setTimeout(function () { S().people(w.q).then(function (l) {
      var cur = caretWord(ta); if (!cur || cur.q !== w.q) return; box = ta.parentElement.querySelector('.dx-mention-list');
      if (!l.length) { if (box) box.remove(); return; }
      if (!box) { box = document.createElement('div'); box.className = 'dx-mention-list'; box.setAttribute('role', 'listbox'); box.setAttribute('aria-label', 'Members'); ta.insertAdjacentElement('afterend', box); }
      var cs = window.CONN_STATE || {}; l = l.slice().sort(function (a, b) { return (cs[b.id] === 'connected') - (cs[a.id] === 'connected'); });
      box.innerHTML = l.slice(0, 6).map(function (u) { return '<button type="button" role="option" class="dx-mention-opt" data-mu="' + u.id + '">' + (window.av ? window.av(u, 26) : '') + '<span><b data-noi18n>' + esc(u.name) + '</b><small data-noi18n>' + esc((u.headline || '').split('|')[0].trim()) + '</small></span></button>'; }).join('');
    }, function () {}); }, 150);
  });
  document.addEventListener('mousedown', function (e) { if (e.target.closest && e.target.closest('.dx-mention-opt')) e.preventDefault(); }, true);   /* keep the caret in the text */
  document.addEventListener('click', function (e) {
    var o = e.target.closest && e.target.closest('.dx-mention-opt'); if (!o) return;
    var ta = $('postBody'), u = U(+o.dataset.mu), w = ta && caretWord(ta); o.closest('.dx-mention-list').remove(); if (!ta || !u || !w) return;
    var ins = '@' + u.name + ' '; ta.value = ta.value.slice(0, w.at) + ins + ta.value.slice(w.end); var pos = w.at + ins.length; ta.focus(); ta.setSelectionRange(pos, pos);
    if (!MENTIONS.some(function (m) { return m.uid === u.id; })) MENTIONS.push({ uid: u.id, name: u.name });
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  });
  /* Post: the mentions still in the text go with it (and are told) */
  var oPost = window.submitPost;
  window.submitPost = function () {
    var ta = $('postBody'), body = ta ? ta.value : '', ms = MENTIONS.filter(function (m) { return body.indexOf('@' + m.name) >= 0; }), first = (window.POSTS || [])[0];
    var r = oPost.apply(this, arguments), p = (window.POSTS || [])[0];
    if (p && p !== first && ms.length) { p.mentions = ms; S().mentions(p, ms); if (inFeed()) repaintCard(p); }
    MENTIONS = [];
    return r;
  };

  /* a file in a post is a download link (the approved chip, now an <a>): the name and size as before */
  var oFiles = window.renderPostFiles;
  if (oFiles) window.renderPostFiles = function (post) {
    var h = oFiles.apply(this, arguments); if (!h || !post || !post.files) return h; var i = 0;
    return h.replace(/<div class="file-chip">([\s\S]*?)<\/span><\/div>/g, function (m, inner) { var f = post.files[i++] || {}, u = String(f.url || '');
      if (!/^(https?:|blob:|data:)/i.test(u)) return m;
      return '<a class="file-chip" href="' + esc(u) + '" download="' + esc(f.name || 'file') + '" target="_blank" rel="noopener" style="text-decoration:none;color:inherit">' + inner + '</span></a>'; });
  };

  /* ── links in a post: #tag opens its page, @name the person; "see more" keeps the links ── */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a.dx-tag, a.dx-mention'); if (!a) return;
    e.preventDefault(); e.stopPropagation();
    if (a.classList.contains('dx-tag')) window.goto('tag', a.dataset.tag); else window.gotoProfile(a.dataset.gp);
  }, true);
  var oExpand = window.expandPost;
  window.expandPost = function (id) { var r = oExpand.apply(this, arguments); var p = find(id), el = $('pb-' + id); if (p && el) el.innerHTML = linkify(esc(p.body || ''), p); return r; };
  /* the tag page: the posts with that tag, as Home cards */
  var PAGES = window.dxSocialPages || (window.dxSocialPages = {});
  if (window.DG_TITLES) window.DG_TITLES.tag = 'Posts with a hashtag';
  PAGES.tag = function (c, args) {
    var tag = String((args && args[0]) || '').replace(/^#/, '').toLowerCase().slice(0, 60);
    c.innerHTML = '<div class="dx-tag-page"><h1 class="dx-set-title">#<span data-noi18n></span></h1><div class="dx-set-sub"><span>Posts with this hashtag</span></div><div class="dx-tag-list">Loading…</div></div>';
    c.querySelector('h1 span').textContent = tag;
    S().byTag(tag).then(function (list) {
      window.dxTagPosts = list || []; var box = c.querySelector('.dx-tag-list'); if (!box || document.body.getAttribute('data-page') !== 'tag') return;
      box.innerHTML = list.length ? list.map(function (p) { return window.renderPost(p); }).join('') : '<div class="dx-feed-end"><span>No posts with #</span><span data-noi18n>' + esc(tag) + '</span><span> yet.</span></div>';
    }, function (e) { var box = c.querySelector('.dx-tag-list'); if (box) box.textContent = (e && e.message) || 'Could not load the posts'; });
  };

  /* links in messages (a shared post, a website): the text stays text, only the addresses become links — a Drugbox link opens in the app */
  var URLRE = /https?:\/\/[^\s<>"']+[^\s<>"'.,;:!?)\]]|file:\/\/\/[^\s<>"']+#\/post\/\d+/g;
  function linkBubble(el) {
    if (el.dataset.dxL === el.textContent.length + '') return; el.dataset.dxL = el.textContent.length + '';
    var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), list = []; while (w.nextNode()) { var n = w.currentNode; if (!n.parentElement.closest('a') && URLRE.test(n.nodeValue)) list.push(n); URLRE.lastIndex = 0; }
    var base = location.href.split('#')[0];
    list.forEach(function (n) { var f = document.createDocumentFragment(), v = n.nodeValue, last = 0; v.replace(URLRE, function (u, i) {
      f.appendChild(document.createTextNode(v.slice(last, i))); var a = document.createElement('a'); a.href = u; a.textContent = u; a.className = 'dx-link';
      if (u.split('#')[0] !== base) { a.target = '_blank'; a.rel = 'noopener noreferrer nofollow'; } f.appendChild(a); last = i + u.length; return u; });
      f.appendChild(document.createTextNode(v.slice(last))); n.parentNode.replaceChild(f, n); });
  }
  if (window.dxCore) window.dxCore.onRender('soc-msg-links', function () { document.querySelectorAll('#messagesArea .mx-bubble, #messagesArea .bubble-body').forEach(linkBubble); });

  if (window.dxI18nAdd) window.dxI18nAdd({
    'edited': 'معدّل', 'Edited': 'معدّل', 'Edit Post': 'تعديل المنشور', 'Cancel': 'إلغاء', 'Save': 'حفظ', 'Post updated': 'تم تحديث المنشور', 'Could not save the change': 'تعذّر حفظ التعديل',
    'Repost': 'إعادة نشر', '🔄 Repost': '🔄 إعادة نشر', '🔄 Reposted': '🔄 تمت إعادة النشر', 'Share this post with your network. Add your thoughts if you like.': 'شارك هذا المنشور مع شبكتك، وأضف رأيك إن أردت.',
    'Add your thoughts (optional)': 'أضف رأيك (اختياري)', 'Reposted to your network': 'تمت إعادة النشر لشبكتك', 'Could not repost': 'تعذّرت إعادة النشر', 'You reposted this post. Undo the repost?': 'لقد أعدت نشر هذا المنشور. هل تريد التراجع؟',
    'Undo repost': 'تراجع عن إعادة النشر', 'Repost removed': 'تم التراجع عن إعادة النشر', 'Could not undo the repost': 'تعذّر التراجع', 'You reposted': 'أعدت نشر هذا', 'reposted': 'أعاد النشر',
    'Send': 'إرسال', 'Send in a message': 'أرسل في رسالة', 'To': 'إلى', 'Type a name…': 'اكتب اسمًا…', 'Add a note (optional)': 'أضف ملاحظة (اختياري)', 'No member found': 'لا يوجد عضو بهذا الاسم',
    'Choose a member from the list': 'اختر عضوًا من القائمة', '✓ Your connection': '✓ من اتصالاتك', 'Could not send': 'تعذّر الإرسال', 'To:': 'إلى:', 'Members': 'الأعضاء',
    'Reply': 'رد', 'Like': 'إعجاب', 'Replying to': 'ردًا على', 'Cancel reply': 'إلغاء الرد', 'Reply posted': 'تم نشر الرد', 'Could not send the reply': 'تعذّر إرسال الرد', 'Could not save the like': 'تعذّر حفظ الإعجاب',
    'Remove photo': 'إزالة الصورة', 'Remove file': 'إزالة الملف', 'At most 5 files in a post': 'خمسة ملفات على الأكثر في المنشور', 'Post cannot be empty': 'لا يمكن نشر منشور فارغ',
    "You're all caught up — that's every post so far.": 'لقد شاهدت كل شيء — هذه كل المنشورات حتى الآن.', 'Posts with a hashtag': 'منشورات بوسم', 'Posts with this hashtag': 'منشورات بهذا الوسم',
    'No posts with #': 'لا توجد منشورات بالوسم #', ' yet.': ' بعد.', 'yet.': 'بعد.', 'Could not load the posts': 'تعذّر تحميل المنشورات', 'Link copied!': 'تم نسخ الرابط!', 'Reposted!': 'تمت إعادة النشر!'
  }, [[/^Sent to (.+)$/, function (m) { return 'أُرسل إلى ' + m[1]; }],
      [/^(.+) — (not a photo \(JPG, PNG, WebP or GIF\)|too big \(max 10 MB\)|too big \(max 20 MB\)|at most 10 photos|not accepted \(PDF, Word, Excel or ZIP\))$/, function (m) {
        return m[1] + ' — ' + { 'not a photo (JPG, PNG, WebP or GIF)': 'ليست صورة (JPG أو PNG أو WebP أو GIF)', 'too big (max 10 MB)': 'كبيرة جدًا (الحد 10 ميجابايت)', 'too big (max 20 MB)': 'كبير جدًا (الحد 20 ميجابايت)',
          'at most 10 photos': '10 صور على الأكثر', 'not accepted (PDF, Word, Excel or ZIP)': 'غير مقبول (PDF أو Word أو Excel أو ZIP)' }[m[2]]; }]]);
})();
