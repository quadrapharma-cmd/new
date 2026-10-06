/* Intro videos: a company video on the company page (owners/admins upload) and a personal "about me" video on the profile
   and on candidate cards. Nothing loads until Play is pressed (a poster frame is shown). Storage goes through window.dxMedia:
   IndexedDB in the demo, Supabase Storage in the live app (the adapter replaces it). */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var LIM = { c: { sec: 180, mb: 100, label: '3 minutes' }, p: { sec: 90, mb: 50, label: '90 seconds' } };
  var TYPES = /^video\/(mp4|webm|quicktime)$/;
  function idle(fn) { var p = false; return function () { if (p) return; p = true; (window.requestIdleCallback || function (cb) { return setTimeout(cb, 1); })(function () { p = false; try { fn(); } catch (e) {} }, { timeout: 400 }); }; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  /* a poster is only ever a JPEG data URL made here or an http(s) storage link from the adapter; anything else (a stored string
     that tries to close the attribute) is dropped — the card then shows the plain play button */
  function safePoster(u) { u = String(u || ''); if (/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(u)) return u; if (!/^https?:\/\/[^\s"'<>()\\]+$/.test(u)) return ''; try { new URL(u); return u; } catch (e) { return ''; } }
  function mmss(s) { s = Math.round(s || 0); return Math.floor(s / 60) + ':' + ('0' + s % 60).slice(-2); }
  /* ── demo storage: IndexedDB (blobs survive reloads) ── */
  var dbp = null;
  function db() { return dbp || (dbp = new Promise(function (res, rej) { var r = indexedDB.open('drugbox-media', 1); r.onupgradeneeded = function () { r.result.createObjectStore('v'); }; r.onsuccess = function () { res(r.result); }; r.onerror = function () { rej(r.error); }; })); }
  function tx(mode, fn) { return db().then(function (d) { return new Promise(function (res, rej) { var t = d.transaction('v', mode), s = t.objectStore('v'), out = fn(s); t.oncomplete = function () { res(out && out.result); }; t.onerror = function () { rej(t.error); }; }); }); }
  var URLS = {};
  if (!window.dxMedia) window.dxMedia = {
    put: function (key, file, meta) { return tx('readwrite', function (s) { return s.put({ blob: file, poster: meta.poster, duration: meta.duration, at: Date.now() }, key); }).then(function () { if (URLS[key]) { URL.revokeObjectURL(URLS[key]); delete URLS[key]; } return { poster: meta.poster, duration: meta.duration }; }); },
    meta: function (key) { return tx('readonly', function (s) { return s.get(key); }).then(function (v) { return v ? { poster: v.poster, duration: v.duration } : null; }); },
    url: function (key) { if (URLS[key]) return Promise.resolve(URLS[key]); return tx('readonly', function (s) { return s.get(key); }).then(function (v) { return v ? (URLS[key] = URL.createObjectURL(v.blob)) : null; }); },
    remove: function (key) { if (URLS[key]) { URL.revokeObjectURL(URLS[key]); delete URLS[key]; } return tx('readwrite', function (s) { return s.delete(key); }); }
  };
  var META = {};                                   /* key → {poster, duration} | null, cached per session */
  function meta(key) { if (key in META) return Promise.resolve(META[key]); return window.dxMedia.meta(key).then(function (m) { META[key] = m || null; return META[key]; }).catch(function () { return null; }); }
  /* ── checks before upload: type, size, length; a poster frame from the video itself ── */
  function inspect(file, kind) {
    var L = LIM[kind];
    if (!file) return Promise.reject(new Error('Choose a video file'));
    if (!TYPES.test(file.type || '') && !(!file.type && /\.(mp4|m4v|webm|mov)$/i.test(file.name || ''))) return Promise.reject(new Error('Use an MP4, WebM or MOV video'));   /* some pickers report no type: the extension decides, then the metadata probe below */
    if (file.size > L.mb * 1048576) return Promise.reject(new Error('The video is larger than ' + L.mb + ' MB'));
    return new Promise(function (res, rej) {
      var v = document.createElement('video'), u = URL.createObjectURL(file), done = false; v.muted = true; v.preload = 'metadata'; v.src = u;
      function fail(m) { if (done) return; done = true; URL.revokeObjectURL(u); rej(new Error(m)); }
      v.onerror = function () { fail('This video could not be read — try MP4 (H.264)'); };
      v.onloadedmetadata = function () { var d = v.duration; if (!isFinite(d) || d <= 0) return fail('This video could not be read — try MP4 (H.264)');
        if (d > L.sec + 0.5) return fail('Keep it under ' + L.label + ' (this one is ' + mmss(d) + ')'); v.currentTime = Math.min(1, d / 2); };
      v.onseeked = function () { if (done) return; var w = Math.min(480, v.videoWidth || 480), h = Math.round(w * (v.videoHeight || 270) / (v.videoWidth || 480)), cv = document.createElement('canvas');
        cv.width = w; cv.height = h; var poster = ''; try { cv.getContext('2d').drawImage(v, 0, 0, w, h); poster = cv.toDataURL('image/jpeg', 0.72); } catch (e) {}
        done = true; URL.revokeObjectURL(u); res({ duration: v.duration, poster: poster }); };
      setTimeout(function () { fail('This video could not be read — try MP4 (H.264)'); }, 15000);
    });
  }
  function upload(key, kind) {
    var inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'video/mp4,video/webm,video/quicktime'; inp.style.display = 'none'; document.body.appendChild(inp);
    inp.onchange = function () { var f = inp.files[0]; inp.remove(); if (!f) return;
      D.toast && D.toast('Checking the video…');
      inspect(f, kind).then(function (m) { return window.dxMedia.put(key, f, m).then(function (saved) { META[key] = { poster: saved.poster || m.poster, duration: saved.duration || m.duration }; D.toast && D.toast('Video saved'); refresh(); }); })
        .catch(function (e) { D.toast && D.toast(e.message || 'The video could not be saved'); });
    };
    inp.click(); return inp;
  }
  function play(key, title) {
    window.dxMedia.url(key).then(function (u) { if (!u) { D.toast && D.toast('This video is no longer available'); return; }
      var m = META[key] || {};
      var ps = safePoster(m.poster);
      D.modal({ title: title || 'Video', secondary: 'Close', body: '<video class="dx-vid-player" src="' + esc(u) + '"' + (ps ? ' poster="' + esc(ps) + '"' : '') + ' controls autoplay playsinline preload="auto"></video>' });
    }).catch(function () { D.toast && D.toast('This video could not be played'); });
  }
  function card(key, kind, title, canEdit) {
    var m = META[key], L = LIM[kind], ps = m && safePoster(m.poster);
    if (!m && !canEdit) return '';
    var head = '<div class="dx-vid-h"><b>' + esc(title) + '</b>' + (m ? '<span>' + mmss(m.duration) + '</span>' : '') + '</div>';
    if (!m) return '<section class="dx-vid dx-vid-empty" data-vk="' + key + '">' + head + '<p>' + (kind === 'c' ? 'Show buyers your site, team and quality in a short video (up to ' + L.label + ').' : 'Introduce yourself to employers and partners in a short video (up to ' + L.label + ').') + '</p>' +
      '<button type="button" class="dx-vid-up" data-vk="' + key + '" data-kind="' + kind + '">' + (kind === 'c' ? 'Add a company video' : 'Add a video introduction') + '</button></section>';
    return '<section class="dx-vid" data-vk="' + key + '">' + head + '<button type="button" class="dx-vid-play" data-vk="' + key + '" data-title="' + esc(title) + '" aria-label="Play ' + esc(title) + '"' +
      (ps ? ' style="background-image:url(\'' + esc(ps) + '\')"' : '') + '><i>▶</i></button>' +
      (canEdit ? '<div class="dx-vid-a"><button type="button" class="dx-vid-up" data-vk="' + key + '" data-kind="' + kind + '">Replace video</button><button type="button" class="dx-vid-rm" data-vk="' + key + '">Remove</button></div>' : '') + '</section>';
  }
  function coOnPage() { var h = document.querySelector('#dxDir.cp h1.cp-name'); if (!h || !window.dxDir) return null; var t = (window.dxOrigText ? window.dxOrigText(h) : h.textContent).trim();
    return window.dxDir.companies().find(function (c) { return t.indexOf(c.name) === 0; }); }
  function profileUser() { return window._profUser || window.ME; }
  function personKey(u) { return 'p:' + (u && u.id); }
  function decorate() {
    var pg = document.body.getAttribute('data-page');
    if (pg === 'companies') { var dir = document.getElementById('dxDir'), co = coOnPage(); if (!dir || !co || !dir.classList.contains('cp')) return;
      var body = dir.querySelector('.cp-body'), tab = dir.querySelector('.cp-tabs .on, .cp-tabs [aria-selected="true"], .cp-tabs .active'); if (!body || (tab && !/Overview/.test(window.dxOrigText ? window.dxOrigText(tab) : tab.textContent))) return;
      var key = 'c:' + co.slug; if (body.querySelector('.dx-vid[data-vk="' + key + '"]')) return;
      meta(key).then(function () { if (!body.isConnected || body.querySelector('.dx-vid[data-vk="' + key + '"]')) return; var h = card(key, 'c', 'Company video', co.owner === (window.ME || {}).id); if (h) body.insertAdjacentHTML('afterbegin', h); }); }
    if (pg === 'profile') { var tabs = document.querySelector('.profile-tabs'), u = profileUser(); if (!tabs || !u) return; var k = personKey(u);
      if (document.querySelector('.dx-vid[data-vk="' + k + '"]')) return;
      /* the page may have been left or re-rendered while the media store answered: a detached .profile-tabs has no parent to insert next to */
      meta(k).then(function () { if (!tabs.isConnected || profileUser() !== u || document.querySelector('.dx-vid[data-vk="' + k + '"]')) return; var h = card(k, 'p', u.id === (window.ME || {}).id ? 'My video introduction' : 'Video introduction', u.id === (window.ME || {}).id); if (h) tabs.insertAdjacentHTML('beforebegin', h); }); }
    if (pg === 'jobs') { document.querySelectorAll('#jx .jcard').forEach(function (c) { if (c.dataset.vid || !c.querySelector('.role-badge.need')) return; c.dataset.vid = '1';
      var nm = (c.querySelector('.jc-company span') || {}).textContent || '', u = c.dataset.uid ? window.U(+c.dataset.uid) : (window.USERS || []).find(function (x) { return x.name === nm.trim(); }); if (!u) return;   /* a linked person first, then by name */
      var k = personKey(u); meta(k).then(function (m) { if (!m) return; var side = c.querySelector('.jc-right'); if (side && side.isConnected) side.insertAdjacentHTML('afterbegin', '<button type="button" class="dx-vid-chip" data-vk="' + k + '" data-title="' + esc(u.name) + '">▶ Video intro · ' + mmss(m.duration) + '</button>'); }); }); }
  }
  function refresh() { document.querySelectorAll('.dx-vid').forEach(function (x) { x.remove(); }); document.querySelectorAll('#jx .jcard[data-vid]').forEach(function (c) { delete c.dataset.vid; var ch = c.querySelector('.dx-vid-chip'); if (ch) ch.remove(); }); decorate(); }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-vid-up, .dx-vid-play, .dx-vid-rm, .dx-vid-chip'); if (!t) return; e.preventDefault(); e.stopPropagation();
    var key = t.dataset.vk;
    if (t.classList.contains('dx-vid-up')) upload(key, t.dataset.kind);
    else if (t.classList.contains('dx-vid-rm')) { if (!window.confirm(document.documentElement.lang === 'ar' && window.dxT ? window.dxT('Remove this video?') : 'Remove this video?')) return;   /* the native confirm follows the interface language */ window.dxMedia.remove(key).then(function () { META[key] = null; D.toast && D.toast('Video removed'); refresh(); }); }
    else play(key, t.dataset.title);
  }, true);
  C.onRender('videos', idle(decorate));
  window.dxVideos = { inspect: inspect, refresh: function () { META = {}; refresh(); }, keyOf: { company: function (slug) { return 'c:' + slug; }, person: function (id) { return 'p:' + id; } }, limits: LIM };
})();
