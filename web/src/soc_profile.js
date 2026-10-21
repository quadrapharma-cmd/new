/* Profile (area social): the profile photo and the cover image (checked, made smaller in the browser), Experience and Education
   (add / edit / delete, newest first, "Present"), Skills with real endorsements (never invented numbers), Languages, and who
   viewed my profile. The approved profile page stays the template: its Experience / Skills rows keep their markup, with the
   owner's controls added. Data goes through window.dxProfileSvc: the sample implementation here (this page), the database in
   the live app (web/src/live/social.js). */
(function () {
  var D = window.DBK; if (!D || typeof window.renderProfileTab !== 'function') return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(id) { return document.getElementById(id); }
  function toast(m) { (window.toast || D.toast)(m); }
  function me() { return window.ME || {}; }
  function U(id) { return window.U ? window.U(id) : {}; }
  function ar() { return document.documentElement.lang === 'ar'; }

  /* ── the sample data source; the live app replaces it ── */
  var ENDORSE = {};                                           /* "<uid>|<skill>" → [endorser ids] (sample: nobody has endorsed yet) */
  window.dxProfileSvc = window.dxProfileSvc || {
    live: false,
    picture: function (kind, blob, dataUrl) { return Promise.resolve(dataUrl); },
    save: function (fields) { Object.assign(window.ME, fields); var m = (window.USERS || []).find(function (u) { return u.id === me().id; }); if (m && m !== window.ME) Object.assign(m, fields); return Promise.resolve(); },
    endorsements: function (u) { var out = {}; (u.skills || []).forEach(function (s) { var l = ENDORSE[u.id + '|' + s] || []; out[s] = { n: l.length, mine: l.indexOf(me().id) >= 0, who: l.map(function (x) { return U(x).name; }) }; }); return Promise.resolve(out); },
    endorse: function (u, skill, on) { var k = u.id + '|' + skill, l = ENDORSE[k] || (ENDORSE[k] = []), i = l.indexOf(me().id); if (on && i < 0) l.push(me().id); if (!on && i >= 0) l.splice(i, 1); return Promise.resolve(); },
    viewers: function () { return Promise.resolve({ total: 3, private: 0, viewers: (window.USERS || []).filter(function (u) { return u.id !== me().id; }).slice(0, 3).map(function (u, i) { return { uid: u.id, day: i ? i + ' days ago' : 'today' }; }), sample: true }); }
  };
  function S() { return window.dxProfileSvc; }

  /* ── photo and cover: a picture is made smaller here (a 12 MB photo becomes ~100 KB), anything else is refused ── */
  var MAX_IN = 25 * 1024 * 1024;
  function shrink(file, maxW, maxH) {
    return new Promise(function (ok, no) {
      if (!/^image\/(jpeg|png|webp|gif)$/.test(file.type)) return no(new Error('Choose a photo (JPG, PNG or WebP)'));
      if (file.size > MAX_IN) return no(new Error('This picture is too big (max 25 MB)'));
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () { var w = img.naturalWidth, h = img.naturalHeight, k = Math.min(1, maxW / w, maxH / h), c = document.createElement('canvas');
        c.width = Math.max(1, Math.round(w * k)); c.height = Math.max(1, Math.round(h * k)); var x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); x.drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url); var d = c.toDataURL('image/jpeg', 0.86); c.toBlob(function (b) { ok({ blob: b, dataUrl: d }); }, 'image/jpeg', 0.86); };
      img.onerror = function () { URL.revokeObjectURL(url); no(new Error('This picture cannot be read — choose a JPG or PNG')); };
      img.src = url;
    });
  }
  function refreshMe() {
    if (typeof window.updateTopUser === 'function') window.updateTopUser();
    if (document.body.getAttribute('data-page') === 'profile' && window._profUser && window._profUser.id === me().id) window.renderProfile($('content'), me().id);
  }
  window.handleAvatarChange = function (input) {
    var f = input.files && input.files[0]; input.value = ''; if (!f) return;
    shrink(f, 512, 512).then(function (r) { return S().picture('avatar', r.blob, r.dataUrl).then(function (u) { S().save({ avatar: u }); return u; }); })
      .then(function () { refreshMe(); toast('Profile photo updated! 📷'); }, function (e) { toast((e && e.message) || 'Could not save the photo'); });
  };
  window.dxEditCover = function () { var i = $('dxCoverInput'); if (i) i.click(); };
  function coverChange(input) {
    var f = input.files && input.files[0]; input.value = ''; if (!f) return;
    shrink(f, 1600, 600).then(function (r) { return S().picture('cover', r.blob, r.dataUrl).then(function (u) { S().save({ cover: u }); return u; }); })
      .then(function () { refreshMe(); toast('Cover updated'); }, function (e) { toast((e && e.message) || 'Could not save the cover'); });
  }
  document.addEventListener('change', function (e) { if (e.target && e.target.id === 'dxCoverInput') coverChange(e.target); });

  /* the profile page: the cover shows; "Edit cover" opens a file picker (the approved button, its toast replaced) */
  var oProfile = window.renderProfile;
  window.renderProfile = function (c, uid) {
    var r = oProfile.apply(this, arguments), u = window._profUser || {}, cov = c && c.querySelector('.profile-cover');
    if (cov && u.cover && /^(https?:|blob:|data:image\/)/.test(u.cover)) { cov.style.setProperty('background-image', 'url("' + String(u.cover).replace(/["\\]/g, '') + '")', 'important'); cov.style.setProperty('background-size', 'cover', 'important'); cov.style.setProperty('background-position', 'center', 'important'); cov.classList.add('dx-has-cover'); }
    var eb = cov && [].find.call(cov.querySelectorAll('button'), function (b) { return /Cover upload coming soon/.test(b.getAttribute('onclick') || ''); });
    if (eb) { eb.setAttribute('onclick', 'dxEditCover()'); if (!c.querySelector('#dxCoverInput')) cov.insertAdjacentHTML('beforeend', '<input type="file" id="dxCoverInput" accept="image/jpeg,image/png,image/webp" style="display:none" aria-label="Choose a cover image">'); }
    var ai = c && c.querySelector('#avatarInput'); if (ai) ai.setAttribute('accept', 'image/jpeg,image/png,image/webp');
    /* Profile views (mine) opens the list of who viewed */
    if (u.id === me().id) [].forEach.call(c.querySelectorAll('.profile-stats > div'), function (d) { var l = d.querySelector('.pstat-l'); if (l && /^Profile views$/.test((window.dxOrigText ? window.dxOrigText(l) : l.textContent).trim())) { d.setAttribute('role', 'button'); d.setAttribute('tabindex', '0'); d.setAttribute('data-dx-viewers', ''); d.setAttribute('title', 'Who viewed your profile'); d.style.cursor = 'pointer'; } });
    return r;
  };
  /* Home's side card: my photo instead of my initials */
  var oSide = window.renderFeedSidebar;
  if (oSide) window.renderFeedSidebar = function () {
    var h = oSide.apply(this, arguments); if (typeof h !== 'string') return h; var m = me();
    if (m.avatar) h = h.replace('onclick="gotoProfile(this.dataset.gp)">' + m.initials + '</div>', 'onclick="gotoProfile(this.dataset.gp)" style="overflow:hidden;padding:0"><img src="' + (window.escSrc ? window.escSrc(m.avatar) : esc(m.avatar)) + '" alt="" style="width:100%;height:100%;object-fit:cover"></div>');
    return h.replace('<span style="color:#65676b">Profile viewers</span>', '<span style="color:#65676b" role="button" tabindex="0" data-dx-viewers>Profile viewers</span>');
  };
  /* everywhere a person is drawn from their initials in a list (messages, network cards): their photo when they have one */
  function paintFaces() {
    document.querySelectorAll('#content .mx-thread[data-uid] .av, #content [data-uid] > .sugg-av, #content .chat-head .av').forEach(function (el) {
      var holder = el.closest('[data-uid]'), id = holder ? +holder.dataset.uid : (window.dxMxOpenUid ? window.dxMxOpenUid() : 0), u = id ? U(id) : null;
      if (!u || !u.avatar || u === me() && id !== me().id || el.querySelector('img.dx-face')) return;
      var dot = el.querySelector('.online-dot'); el.textContent = ''; var im = document.createElement('img'); im.className = 'dx-face'; im.alt = ''; im.src = u.avatar; el.appendChild(im); if (dot) el.appendChild(dot);
    });
  }
  if (window.dxCore) window.dxCore.onRender('soc-faces', paintFaces);

  /* ── Experience / Education / Skills / Languages ── */
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function month(s) { var m = /^(\d{4})-(\d{2})$/.exec(s || ''); return m ? MON[+m[2] - 1] + ' ' + m[1] : String(s || ''); }
  function span(a, b) { var x = /^(\d{4})-(\d{2})$/.exec(a || ''), y = /^(\d{4})-(\d{2})$/.exec(b || '') || (function () { var d = new Date(); return [0, d.getFullYear(), d.getMonth() + 1]; })();
    if (!x) return ''; var n = (+y[1] - +x[1]) * 12 + (+y[2] - +x[2]) + 1; if (n < 1) return ''; var yr = Math.floor(n / 12), mo = n % 12;
    return [yr ? yr + (yr === 1 ? ' yr' : ' yrs') : '', mo ? mo + (mo === 1 ? ' mo' : ' mos') : ''].filter(Boolean).join(' '); }
  function expView(x) { return x.start ? Object.assign({}, x, { period: month(x.start) + ' – ' + (x.end ? month(x.end) : 'Present'), years: span(x.start, x.end) }) : x; }
  function expSorted(l) { return (l || []).map(function (x, i) { return { x: x, i: i }; }).sort(function (a, b) {
    var ae = a.x.start ? (a.x.end || '9999-99') : '', be = b.x.start ? (b.x.end || '9999-99') : '';
    return be.localeCompare(ae) || String(b.x.start || '').localeCompare(String(a.x.start || '')) || a.i - b.i; }); }
  function eduSorted(l) { return (l || []).map(function (x, i) { return { x: x, i: i }; }).sort(function (a, b) { return String(b.x.end || b.x.year || '').localeCompare(String(a.x.end || a.x.year || '')) || a.i - b.i; }); }
  var CARD = '<div style="background:#fff;border:1px solid #e4e6eb;border-radius:12px;padding:18px;margin:0 0 12px">';
  function own() { var u = window._profUser; return !!u && u.id === me().id; }
  function head(title, addLabel, act) { return '<div class="dx-pf-head"><h3 style="font-size:16px;font-weight:700;margin-bottom:12px">' + title + '</h3>' + (own() ? '<button type="button" class="btn-ghost dx-pf-add" data-pf="' + act + '">' + addLabel + '</button>' : '') + '</div>'; }
  function ctl(kind, i) { return own() ? '<span class="dx-pf-ctl"><button type="button" class="dx-pf-btn" data-pf="edit-' + kind + '" data-i="' + i + '">Edit</button><button type="button" class="dx-pf-btn" data-pf="del-' + kind + '" data-i="' + i + '" aria-label="Delete">🗑</button></span>' : ''; }
  function tabExperience(u) {
    var h = CARD + head('Experience', '+ Add position', 'add-exp');
    expSorted(u.experience).forEach(function (o) { var x = expView(o.x);
      h += '<div class="dx-pf-row" style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f0f2f5"><div style="width:44px;height:44px;border-radius:10px;background:#eff6ff;color:var(--cp);font-weight:800;display:flex;align-items:center;justify-content:center;flex:none">' + esc(String(x.company || '').slice(0, 2).toUpperCase()) + '</div>';
      h += '<div style="flex:1;min-width:0"><div style="font-size:14px;font-weight:700;color:var(--cx)" data-noi18n>' + esc(x.title) + '</div><div style="font-size:13px;color:#374151" data-noi18n>' + esc(x.company) + '</div><div style="font-size:12px;color:#65676b">' + esc(x.period) + (x.years ? ' &middot; ' + esc(x.years) : '') + '</div><div style="font-size:13px;color:#374151;margin-top:4px;line-height:1.6;white-space:pre-line" data-noi18n>' + esc(x.desc || '') + '</div></div>' + ctl('exp', o.i) + '</div>'; });
    if (!(u.experience || []).length) h += '<div style="color:#65676b;font-size:13px">No experience added.</div>';
    h += '</div>' + CARD + head('Education', '+ Add education', 'add-edu');
    eduSorted(u.education).forEach(function (o) { var e = o.x;
      h += '<div class="dx-pf-row" style="display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #f0f2f5"><div style="flex:1;min-width:0"><div style="font-size:14px;font-weight:700;color:var(--cx)">&#127891; <span data-noi18n>' + esc(e.school) + '</span></div><div style="font-size:13px;color:#374151" data-noi18n>' + esc(e.degree) + '</div><div style="font-size:12px;color:#65676b">' + esc(e.start ? e.start + ' – ' + (e.end || 'Present') : e.year || '') + '</div></div>' + ctl('edu', o.i) + '</div>'; });
    if (!(u.education || []).length) h += '<div style="color:#65676b;font-size:13px">No education added.</div>';
    return h + '</div>';
  }
  function tabSkills(u) {
    /* someone else's skills: the approved honeycomb (batch2.js) is built from these rows and its cells press their Endorse; my own
       skills stay a list (no honeycomb: the marker below) with Remove — nobody endorses themselves */
    var h = own() ? CARD + head('Skills', '+ Add skill', 'add-skill').replace('</h3>', '</h3><div class="dx-comb" hidden></div>') + '<div class="dx-pf-skills" data-u="' + u.id + '">'
      : CARD + '<div class="dx-pf-skills" data-u="' + u.id + '"><h3 style="font-size:16px;font-weight:700;margin-bottom:12px">Skills</h3>';
    (u.skills || []).forEach(function (s, i) {
      h += '<div class="dx-pf-skill" data-skill="' + esc(s) + '" style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #f0f2f5"><span style="font-size:13.5px;font-weight:600;color:var(--cx)" data-noi18n>' + esc(s) + '</span>' +
        '<span class="dx-pf-end" style="font-size:11.5px;color:#65676b;display:flex;align-items:center;gap:6px"><span class="dx-pf-n">…</span>' +
        (own() ? '<button type="button" class="dx-pf-btn" data-pf="del-skill" data-i="' + i + '" aria-label="Remove skill">×</button>' : '<button type="button" class="btn-ghost dx-pf-endorse" style="padding:3px 10px;font-size:11px" data-pf="endorse" data-i="' + i + '">Endorse</button>') + '</span></div>';
    });
    if (!(u.skills || []).length) h += '<div style="color:#65676b;font-size:13px">No skills added.</div>';
    h += '</div></div>';
    /* the approved Licenses & Certifications card stays as it was */
    var orig = oTab('skills'), k = orig.indexOf('Licenses &amp; Certifications'); if (k >= 0) h += orig.slice(orig.lastIndexOf('<div style="background:#fff', k));
    setTimeout(function () { paintEndorse(u); }, 0);
    return h;
  }
  function paintEndorse(u) {
    S().endorsements(u).then(function (m) {
      document.querySelectorAll('.dx-pf-skills[data-u="' + u.id + '"] .dx-pf-skill').forEach(function (row) {
        var e = m[row.dataset.skill] || { n: 0, mine: false, who: [] }, n = row.querySelector('.dx-pf-n'), b = row.querySelector('.dx-pf-endorse');
        if (n) { n.textContent = e.n + (e.n === 1 ? ' endorsement' : ' endorsements'); n.title = e.who.length ? 'Endorsed by ' + e.who.slice(0, 5).join(', ') : ''; }
        if (b) { b.textContent = e.mine ? '✓ Endorsed' : 'Endorse'; b.setAttribute('aria-pressed', e.mine ? 'true' : 'false'); b.dataset.on = e.mine ? '1' : ''; }
        var w = row.querySelector('.dx-pf-who'); if (e.who.length) { if (!w) { w = document.createElement('span'); w.className = 'dx-pf-who'; w.setAttribute('data-noi18n', ''); row.querySelector('.dx-pf-end').appendChild(w); } w.textContent = e.who.slice(0, 2).join(', ') + (e.who.length > 2 ? ' +' + (e.who.length - 2) : '') + ' ·'; } else if (w) w.remove();
      });
      setTimeout(function () {   /* the honeycomb shows what I already endorsed */
        var rows = [].slice.call(document.querySelectorAll('.dx-pf-skills[data-u="' + u.id + '"] .dx-pf-skill'));
        document.querySelectorAll('.dx-pf-skills[data-u="' + u.id + '"] .dx-comb .dx-cell').forEach(function (c) { var r = rows[+c.dataset.i], e = r && m[r.dataset.skill]; if (e && e.mine) c.classList.add('done'); });
      }, 120);
    }, function () {});
  }
  function langCard(u) {
    if (!own() && !(u.languages || []).length) return '';
    var h = CARD + head('Languages', '+ Add language', 'add-lang');
    (u.languages || []).forEach(function (l, i) { h += '<div style="display:flex;justify-content:space-between;align-items:center;font-size:13.5px;margin-bottom:5px">&#127758; <span style="flex:1;margin-inline-start:6px" data-noi18n>' + esc(l) + '</span>' + (own() ? '<button type="button" class="dx-pf-btn" data-pf="del-lang" data-i="' + i + '" aria-label="Remove language">×</button>' : '') + '</div>'; });
    if (!(u.languages || []).length) h += '<div style="color:#65676b;font-size:13px">No languages added.</div>';
    return h + '</div>';
  }
  var oTab = window.renderProfileTab;
  window.renderProfileTab = function (tab) {
    var u = window._profUser || me();
    if (tab === 'experience') return tabExperience(u);
    if (tab === 'skills') return tabSkills(u);
    var h = oTab.apply(this, arguments);
    if (tab === 'about') { var k = h.indexOf('>Languages</h3>'); if (k >= 0) h = h.slice(0, h.lastIndexOf('<div style="background:#fff', k)); h += langCard(u); }
    return h;
  };
  function redrawTab(tab) { var box = $('profileTabContent'); if (box) box.innerHTML = window.renderProfileTab(tab); }
  function curTab() { var t = document.querySelector('.ptab.active'); return t ? t.dataset.tab : 'activity'; }

  /* the forms (the approved window style) */
  function form(title, fields, onSave) {
    var m = document.createElement('div'); m.className = 'modal-bg show';
    m.innerHTML = '<div class="modal" role="dialog" aria-modal="true" aria-label="' + esc(title) + '"><div class="modal-hdr">' + esc(title) + ' <button class="modal-close" aria-label="Close">×</button></div>' +
      fields.map(function (f) {
        if (f.type === 'check') return '<div class="m-field"><label style="display:flex;align-items:center;gap:9px;min-height:40px;font-size:13.5px;font-weight:700;cursor:pointer"><input type="checkbox" id="' + f.id + '" style="width:18px;height:18px"' + (f.value ? ' checked' : '') + '> ' + esc(f.label) + '</label></div>';
        if (f.type === 'area') return '<div class="m-field"><label class="m-label" for="' + f.id + '">' + esc(f.label) + '</label><textarea class="m-ta" id="' + f.id + '" rows="3" maxlength="1500">' + esc(f.value || '') + '</textarea></div>';
        return '<div class="m-field"><label class="m-label" for="' + f.id + '">' + esc(f.label) + '</label><input class="m-input" id="' + f.id + '" type="' + (f.type || 'text') + '"' + (f.ph ? ' placeholder="' + esc(f.ph) + '"' : '') + (f.max ? ' maxlength="' + f.max + '"' : '') + ' value="' + esc(f.value || '') + '"></div>';
      }).join('') + '<div class="dx-set-msg err" id="pfErr" role="alert"></div><div class="m-foot"><button type="button" class="btn-ghost" data-f="cancel">Cancel</button><button type="button" class="btn-p" data-f="save">Save</button></div></div>';
    document.body.appendChild(m);
    function close() { m.remove(); }
    m.addEventListener('click', function (e) {
      if (e.target === m || e.target.closest('.modal-close') || e.target.closest('[data-f=cancel]')) return close();
      var b = e.target.closest('[data-f=save]'); if (!b) return;
      var v = {}; fields.forEach(function (f) { var x = m.querySelector('#' + f.id); v[f.key] = f.type === 'check' ? x.checked : x.value.trim(); });
      var err = onSave(v); if (err) { m.querySelector('#pfErr').textContent = err; return; }
      close();
    });
    m.addEventListener('keydown', function (e) { if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') { e.preventDefault(); m.querySelector('[data-f=save]').click(); } });
    var f0 = m.querySelector('input,textarea'); if (f0) setTimeout(function () { f0.focus(); }, 50);
    return m;
  }
  function save(fields, tab, msg) {
    var before = {}; Object.keys(fields).forEach(function (k) { before[k] = me()[k]; });
    S().save(fields).then(function () { window._profUser = Object.assign({}, window._profUser, fields); redrawTab(tab); if (msg) toast(msg); },
      function (e) { Object.assign(window.ME, before); window._profUser = Object.assign({}, window._profUser, before); redrawTab(tab); toast((e && e.message) || 'Could not save — please try again'); });
    window._profUser = Object.assign({}, window._profUser, fields); redrawTab(tab);
  }
  var YM = /^\d{4}-(0[1-9]|1[0-2])$/;
  function expForm(i) {
    var l = (me().experience || []).slice(), x = i == null ? {} : l[i] || {};
    form(i == null ? 'Add position' : 'Edit position', [
      { id: 'pfTitle', key: 'title', label: 'Job title *', value: x.title, max: 120 }, { id: 'pfCo', key: 'company', label: 'Company *', value: x.company, max: 120 },
      { id: 'pfStart', key: 'start', label: 'Start (month) *', type: 'month', value: x.start, ph: 'YYYY-MM' }, { id: 'pfEnd', key: 'end', label: 'End (month) — empty if you work here now', type: 'month', value: x.end, ph: 'YYYY-MM' },
      { id: 'pfDesc', key: 'desc', label: 'Description', type: 'area', value: x.desc }], function (v) {
        if (!v.title || !v.company) return 'Title and company are required';
        if (!YM.test(v.start)) return 'Choose the start month';
        if (v.end && !YM.test(v.end)) return 'Choose the end month, or leave it empty';
        if (v.end && v.end < v.start) return 'The end cannot be before the start';
        var now = new Date(), cur = now.getFullYear() + '-' + ('0' + (now.getMonth() + 1)).slice(-2); if (v.start > cur || (v.end && v.end > cur)) return 'Dates cannot be in the future';
        var e = { title: v.title, company: v.company, start: v.start, end: v.end || '', desc: v.desc };
        if (i == null) l.push(e); else l[i] = e; save({ experience: l }, 'experience', i == null ? 'Position added' : 'Position updated');
      });
  }
  function eduForm(i) {
    var l = (me().education || []).slice(), x = i == null ? {} : l[i] || {};
    form(i == null ? 'Add education' : 'Edit education', [
      { id: 'pfSchool', key: 'school', label: 'School *', value: x.school, max: 160 }, { id: 'pfDeg', key: 'degree', label: 'Degree', value: x.degree, max: 120 },
      { id: 'pfFrom', key: 'start', label: 'From (year)', value: x.start || '', ph: 'YYYY', max: 4 }, { id: 'pfTo', key: 'end', label: 'To (year)', value: x.end || x.year || '', ph: 'YYYY', max: 4 }], function (v) {
        if (!v.school) return 'The school is required';
        if ((v.start && !/^\d{4}$/.test(v.start)) || (v.end && !/^\d{4}$/.test(v.end))) return 'Years are 4 digits, e.g. 2019';
        if (v.start && v.end && v.end < v.start) return 'The end cannot be before the start';
        var e = { school: v.school, degree: v.degree, start: v.start, end: v.end };
        if (i == null) l.push(e); else l[i] = e; save({ education: l }, 'experience', i == null ? 'Education added' : 'Education updated');
      });
  }
  function skillForm() {
    var adds = [], m = form('Add skills', [{ id: 'pfSkill', key: 'skill', label: 'Skill (press Enter after each)', max: 60, ph: 'e.g. CTD dossiers' }], function (v) {
      if (v.skill) adds.push(v.skill);
      var l = (me().skills || []).slice(); adds.forEach(function (s) { if (!l.some(function (x) { return x.toLowerCase() === s.toLowerCase(); })) l.push(s); });
      if (l.length > 50) return 'At most 50 skills';
      save({ skills: l }, 'skills', adds.length ? 'Skills saved' : null);
    });
    var inp = m.querySelector('#pfSkill'), chips = document.createElement('div'); chips.className = 'dx-pf-chips'; inp.parentElement.appendChild(chips);
    inp.addEventListener('keydown', function (e) { if (e.key !== 'Enter') return; e.preventDefault(); e.stopPropagation(); var s = inp.value.trim(); if (!s) return;
      if (!adds.some(function (x) { return x.toLowerCase() === s.toLowerCase(); })) { adds.push(s); var c = document.createElement('span'); c.className = 'dx-pf-chip'; c.setAttribute('data-noi18n', ''); c.textContent = s; chips.appendChild(c); }
      inp.value = ''; }, true);
  }
  function langForm() {
    form('Add language', [{ id: 'pfLang', key: 'lang', label: 'Language (and level)', max: 60, ph: 'e.g. Arabic — native' }], function (v) {
      if (!v.lang) return 'Write a language'; var l = (me().languages || []).slice(); if (l.length >= 20) return 'At most 20 languages'; l.push(v.lang); save({ languages: l }, 'about', 'Language added');
    });
  }
  function confirmDel(what, onYes) { D.modal({ title: 'Delete ' + what, body: '<p style="margin:0">Delete this ' + esc(what) + ' from your profile?</p>', primary: { label: 'Delete', danger: true, onClick: function () { onYes(); } } }); }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#content [data-pf], #content [data-dx-viewers]'); if (!b) return;
    if (b.hasAttribute('data-dx-viewers')) { viewersDialog(); return; }
    var a = b.dataset.pf, i = b.dataset.i != null ? +b.dataset.i : null;
    if (a === 'endorse') { var u = window._profUser, sk = (u.skills || [])[i], on = !b.dataset.on; b.disabled = true;
      S().endorse(u, sk, on).then(function () { b.disabled = false; paintEndorse(u); if (on) toast('Endorsed ' + sk); }, function (er) { b.disabled = false; toast((er && er.message) || 'Could not save the endorsement'); }); return; }
    if (!own()) return;
    if (a === 'add-exp') expForm(null); else if (a === 'edit-exp') expForm(i);
    else if (a === 'del-exp') confirmDel('position', function () { var l = (me().experience || []).slice(); l.splice(i, 1); save({ experience: l }, 'experience', 'Position deleted'); });
    else if (a === 'add-edu') eduForm(null); else if (a === 'edit-edu') eduForm(i);
    else if (a === 'del-edu') confirmDel('education', function () { var l = (me().education || []).slice(); l.splice(i, 1); save({ education: l }, 'experience', 'Education deleted'); });
    else if (a === 'add-skill') skillForm();
    else if (a === 'del-skill') { var l = (me().skills || []).slice(); l.splice(i, 1); save({ skills: l }, 'skills', 'Skill removed'); }
    else if (a === 'add-lang') langForm();
    else if (a === 'del-lang') { var l2 = (me().languages || []).slice(); l2.splice(i, 1); save({ languages: l2 }, 'about', 'Language removed'); }
  });
  document.addEventListener('keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('#content [data-dx-viewers]')) { e.preventDefault(); e.target.click(); } });

  /* ── who viewed my profile ── */
  function viewersDialog() {
    var m = D.modal({ title: 'Who viewed your profile', secondary: 'Close', body: '<div class="dx-rx-list"><div class="dx-rx-more">Loading…</div></div>' });
    S().viewers().then(function (r) {
      var box = m.el.querySelector('.dx-rx-list'); if (!box) return;
      var h = (r.viewers || []).map(function (v) { var u = U(v.uid); return '<button type="button" class="dx-rx-row" data-rxu="' + u.id + '">' + (window.av ? window.av(u, 36) : '') + '<span class="dx-rx-who"><b>' + esc(u.name) + '</b><small>' + esc([(u.headline || '').split('|')[0].trim(), u.company].filter(Boolean).join(' · ')) + '</small></span><span class="dx-rx-k" style="font-size:11px">' + esc(v.day || '') + '</span></button>'; }).join('');
      if (r.private) h += '<div class="dx-rx-more">' + r.private + (r.private === 1 ? ' member viewed privately' : ' members viewed privately') + '</div>';
      box.innerHTML = h || '<div class="dx-rx-more">Nobody has viewed your profile in the last 90 days.</div>';
      if (r.sample) box.insertAdjacentHTML('beforeend', '<div class="dx-rx-more">Demo: sample visitors. The live app lists the members who really viewed your profile.</div>');
    }, function (e) { var box = m.el.querySelector('.dx-rx-list'); if (box) box.textContent = (e && e.message) || 'Could not load the list'; });
    m.el.addEventListener('click', function (e) { var r = e.target.closest && e.target.closest('[data-rxu]'); if (!r) return; m.close(); window.gotoProfile(r.dataset.rxu); });
  }
  window.dxViewers = viewersDialog;

  if (window.dxI18nAdd) window.dxI18nAdd({
    'Profile photo updated! 📷': 'تم تحديث صورة الملف! 📷', 'Cover updated': 'تم تحديث الغلاف', 'Could not save the photo': 'تعذّر حفظ الصورة', 'Could not save the cover': 'تعذّر حفظ الغلاف',
    'Choose a photo (JPG, PNG or WebP)': 'اختر صورة (JPG أو PNG أو WebP)', 'This picture is too big (max 25 MB)': 'الصورة كبيرة جدًا (الحد 25 ميجابايت)', 'This picture cannot be read — choose a JPG or PNG': 'تعذّرت قراءة الصورة — اختر JPG أو PNG',
    'Choose a cover image': 'اختر صورة الغلاف', 'Experience': 'الخبرة', 'Education': 'التعليم', 'Skills': 'المهارات', 'Languages': 'اللغات', '+ Add position': '+ أضف خبرة', '+ Add education': '+ أضف تعليمًا', '+ Add skill': '+ أضف مهارة', '+ Add language': '+ أضف لغة',
    'Edit': 'تعديل', 'Delete': 'حذف', 'Present': 'حتى الآن', 'No experience added.': 'لم تُضف خبرات.', 'No education added.': 'لم يُضف تعليم.', 'No skills added.': 'لم تُضف مهارات.', 'No languages added.': 'لم تُضف لغات.',
    'Endorse': 'أؤيد', '✓ Endorsed': '✓ أيّدت', 'endorsement': 'تأييد', 'endorsements': 'تأييدات', 'Add position': 'أضف خبرة', 'Edit position': 'تعديل الخبرة', 'Add education': 'أضف تعليمًا', 'Edit education': 'تعديل التعليم',
    'Job title *': 'المسمى الوظيفي *', 'Company *': 'الشركة *', 'Start (month) *': 'البداية (الشهر) *', 'End (month) — empty if you work here now': 'النهاية (الشهر) — اتركها فارغة إن كنت تعمل هنا الآن', 'Description': 'الوصف',
    'School *': 'الجهة التعليمية *', 'Degree': 'الدرجة', 'From (year)': 'من (سنة)', 'To (year)': 'إلى (سنة)', 'Add skills': 'أضف مهارات', 'Skill (press Enter after each)': 'المهارة (اضغط Enter بعد كل واحدة)',
    'Add language': 'أضف لغة', 'Language (and level)': 'اللغة (والمستوى)', 'Title and company are required': 'المسمى والشركة مطلوبان', 'Choose the start month': 'اختر شهر البداية', 'Choose the end month, or leave it empty': 'اختر شهر النهاية أو اتركه فارغًا',
    'The end cannot be before the start': 'لا يمكن أن تسبق النهاية البداية', 'Dates cannot be in the future': 'لا يمكن أن تكون التواريخ في المستقبل', 'The school is required': 'الجهة التعليمية مطلوبة', 'Years are 4 digits, e.g. 2019': 'السنة 4 أرقام، مثل 2019',
    'At most 50 skills': '50 مهارة على الأكثر', 'Write a language': 'اكتب لغة', 'At most 20 languages': '20 لغة على الأكثر', 'Position added': 'تمت إضافة الخبرة', 'Position updated': 'تم تحديث الخبرة', 'Position deleted': 'تم حذف الخبرة',
    'Education added': 'تمت إضافة التعليم', 'Education updated': 'تم تحديث التعليم', 'Education deleted': 'تم حذف التعليم', 'Skills saved': 'تم حفظ المهارات', 'Skill removed': 'تمت إزالة المهارة', 'Language added': 'تمت إضافة اللغة', 'Language removed': 'تمت إزالة اللغة',
    'Could not save — please try again': 'تعذّر الحفظ — حاول مرة أخرى', 'Could not save the endorsement': 'تعذّر حفظ التأييد', 'Remove skill': 'إزالة المهارة', 'Remove language': 'إزالة اللغة', 'Delete position': 'حذف الخبرة', 'Delete education': 'حذف التعليم',
    'Delete this position from your profile?': 'حذف هذه الخبرة من ملفك؟', 'Delete this education from your profile?': 'حذف هذا التعليم من ملفك؟',
    'Who viewed your profile': 'من شاهد ملفك', 'Nobody has viewed your profile in the last 90 days.': 'لم يشاهد أحد ملفك خلال آخر 90 يومًا.', 'member viewed privately': 'عضو شاهد ملفك بشكل خاص', 'members viewed privately': 'أعضاء شاهدوا ملفك بشكل خاص',
    'Demo: sample visitors. The live app lists the members who really viewed your profile.': 'العرض التجريبي: زوار تجريبيون. يعرض التطبيق الحقيقي الأعضاء الذين شاهدوا ملفك فعلًا.', 'Could not load the list': 'تعذّر تحميل القائمة', 'today': 'اليوم'
  }, [[/^Endorsed by (.+)$/, function (m) { return 'أيّده ' + m[1]; }], [/^Endorsed (.+)$/, function (m) { return 'أيّدت ' + m[1]; }], [/^(\d+) endorsements?$/, function (m) { return m[1] + ' ' + (+m[1] >= 3 && +m[1] <= 10 ? 'تأييدات' : 'تأييد'); }],
      [/^(\d+) (members|member) viewed privately$/, function (m) { return m[1] + ' شاهدوا ملفك بشكل خاص'; }],
      [/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4}) – (Present|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4}))( · .+)?$/, function (m) {
        var A = { Jan: 'يناير', Feb: 'فبراير', Mar: 'مارس', Apr: 'أبريل', May: 'مايو', Jun: 'يونيو', Jul: 'يوليو', Aug: 'أغسطس', Sep: 'سبتمبر', Oct: 'أكتوبر', Nov: 'نوفمبر', Dec: 'ديسمبر' };
        return A[m[1]] + ' ' + m[2] + ' – ' + (m[3] === 'Present' ? 'حتى الآن' : A[m[4]] + ' ' + m[5]) + (m[6] ? m[6].replace(/yrs?/g, 'سنة').replace(/mos?/g, 'شهر') : ''); }],
      [/^(\d{4}) – Present$/, function (m) { return m[1] + ' – حتى الآن'; }]]);
})();
