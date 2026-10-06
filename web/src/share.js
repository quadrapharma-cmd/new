/* Share cards (1200×630 image + caption for WhatsApp/LinkedIn) and trade-show mode (full-screen QR).
   Nothing is drawn until a Share or Trade-show button is pressed; trade-show timers stop when it closes. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function idle(fn) { var p = false; return function () { if (p) return; p = true; (window.requestIdleCallback || function (cb) { return setTimeout(cb, 1); })(function () { p = false; try { fn(); } catch (e) {} }, { timeout: 400 }); }; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function orig(el) { return el ? (window.dxOrigText ? window.dxOrigText(el) : el.textContent).replace(/\s+/g, ' ').trim() : ''; }
  function pageUrl(co) { return 'https://' + (window.dxDir && window.dxDir.isVip && window.dxDir.isVip(co) ? co.slug + '.drugbox.app' : 'drugbox.app/c/' + co.slug); }
  var SHARE_IC = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="6" cy="12" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="18" cy="19" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8.2 10.8l7.6-4.4M8.2 13.2l7.6 4.4" stroke="currentColor" stroke-width="2"/></svg>';
  /* ── the card image ── */
  var logoImg = null; function logo() { if (logoImg) return logoImg; try { if (typeof LOGO_ICON !== 'undefined') { logoImg = new Image(); logoImg.src = LOGO_ICON; } } catch (e) {} return logoImg; }
  function wrap(x, text, maxW, maxLines) { var w = String(text || '').split(' '), lines = [], cur = ''; w.forEach(function (t) { var n = cur ? cur + ' ' + t : t; if (x.measureText(n).width > maxW && cur) { lines.push(cur); cur = t; } else cur = n; }); if (cur) lines.push(cur);
    if (lines.length > maxLines) { lines = lines.slice(0, maxLines); lines[maxLines - 1] = lines[maxLines - 1].replace(/\s*\S*$/, '') + '…'; } return lines; }
  function pill(x, text, px, py, bg, fg) { x.font = '600 22px Poppins, sans-serif'; var w = x.measureText(text).width + 36; x.fillStyle = bg; x.beginPath(); x.roundRect ? x.roundRect(px, py, w, 44, 22) : x.rect(px, py, w, 44); x.fill(); x.fillStyle = fg; x.fillText(text, px + 18, py + 30); return w; }
  function draw(d) {
    var cv = document.createElement('canvas'); cv.width = 1200; cv.height = 630; var x = cv.getContext('2d');
    var g = x.createLinearGradient(0, 0, 1200, 630); g.addColorStop(0, '#0A1F4D'); g.addColorStop(.6, '#0B2A6B'); g.addColorStop(1, '#123C9C'); x.fillStyle = g; x.fillRect(0, 0, 1200, 630);
    x.strokeStyle = 'rgba(255,255,255,.06)'; x.lineWidth = 1; for (var i = 0; i < 1200; i += 40) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 630); x.stroke(); } for (var j = 0; j < 630; j += 40) { x.beginPath(); x.moveTo(0, j); x.lineTo(1200, j); x.stroke(); }
    var rg = x.createRadialGradient(1000, 520, 20, 1000, 520, 420); rg.addColorStop(0, 'rgba(6,182,212,.35)'); rg.addColorStop(1, 'rgba(6,182,212,0)'); x.fillStyle = rg; x.fillRect(0, 0, 1200, 630);
    x.fillStyle = d.accent || '#F59E0B'; x.fillRect(0, 0, 12, 630);
    var L = logo(); if (L && L.complete && L.naturalWidth) x.drawImage(L, 64, 48, 56, 60);
    x.font = '700 30px Poppins, sans-serif'; x.fillStyle = '#fff'; x.fillText('DRUG', 132, 90); var dw = x.measureText('DRUG').width; x.fillStyle = '#5B9BF5'; x.fillText('BOX', 132 + dw, 90);
    x.font = '600 20px Poppins, sans-serif'; x.fillStyle = '#7DD3FC'; x.fillText(d.kicker.toUpperCase(), 64, 176);
    x.font = '700 60px Poppins, sans-serif'; x.fillStyle = '#fff'; var ty = 246; wrap(x, d.title, 1060, 2).forEach(function (l) { x.fillText(l, 64, ty); ty += 70; });
    x.font = '400 28px Poppins, sans-serif'; x.fillStyle = '#C7D6F5'; wrap(x, d.sub, 1060, 2).forEach(function (l) { x.fillText(l, 64, ty + 6); ty += 40; });
    var px = 64, py = Math.max(ty + 34, 430); (d.pills || []).slice(0, 5).forEach(function (p) { if (px > 1000) return; px += pill(x, p[0], px, py, p[1] || 'rgba(255,255,255,.12)', p[2] || '#fff') + 12; });
    x.fillStyle = 'rgba(255,255,255,.1)'; x.fillRect(64, 548, 1072, 1);
    x.font = '500 22px Poppins, sans-serif'; x.fillStyle = '#DCE6FF'; x.fillText(d.url.replace('https://', ''), 64, 590);
    x.textAlign = 'right'; x.fillStyle = '#FDE68A'; x.fillText('The professional network for pharma', 1136, 590); x.textAlign = 'left';
    return cv;
  }
  function dataFor(kind, el) {
    if (kind === 'co') { var co = el; var t = window.dxTiers ? window.dxTiers.tierOf(co) : 0, TN = ['', 'Registered', 'Licensed', 'Inspected'];
      var pills = []; if (t) pills.push(['Level ' + t + ' · ' + TN[t], '#10B981', '#fff']); (co.certs || []).slice(0, 4).forEach(function (c) { pills.push([c]); });
      return { kicker: (co.sectors || []).join(' · ') || 'Company', title: co.name, sub: (co.tagline || '') + (co.city ? ' — ' + co.city + (co.gov ? ', ' + co.gov : '') : ''), pills: pills, url: pageUrl(co), accent: '#10B981',
        caption: co.name + ' on Drugbox' + (t ? ' — verification level ' + t + ' (' + TN[t] + ')' : '') + ((co.certs || []).length ? ' · ' + co.certs.slice(0, 4).join(', ') : '') + (co.city ? ' · ' + co.city : '') + '. ' + pageUrl(co) };
    }
    if (kind === 'listing') { var card = el, ti = orig(card.querySelector('.sp-title,.lc-title')), pr = orig(card.querySelector('.sp-price,.lc-price')).replace(/Landed cost/g, '').trim(), sup = orig(card.querySelector('.sp-supplier,.lc-supplier,[class*=supplier]'));
      return { kicker: 'Marketplace listing', title: ti, sub: sup, pills: pr ? [[pr, '#F59E0B', '#1F1300']] : [], url: 'https://drugbox.app/market', accent: '#F59E0B', caption: ti + (pr ? ' — ' + pr : '') + (sup ? ' · ' + sup : '') + '. On the Drugbox marketplace: https://drugbox.app/market' };
    }
    var j = el, jt = orig(j.querySelector('.jc-title')), meta = orig(j.querySelector('.jc-co,.jc-meta,[class*=company]'));
    return { kicker: 'Job opening', title: jt, sub: meta, pills: [['Apply on Drugbox', '#EC4899', '#fff']], url: 'https://drugbox.app/jobs', accent: '#EC4899', caption: jt + (meta ? ' — ' + meta : '') + '. Apply on Drugbox: https://drugbox.app/jobs' };
  }
  function copy(text, btn) { function done() { btn.textContent = 'Copied ✓'; setTimeout(function () { btn.textContent = 'Copy caption'; }, 1600); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
    function fallback() { var t = document.createElement('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select(); var ok = false; try { ok = document.execCommand('copy'); } catch (e) {} t.remove();
      if (ok) return done();   /* the clipboard was refused: leave the caption selected for a manual copy */
      var cap = btn.closest('.dx-sh') && btn.closest('.dx-sh').querySelector('.dx-sh-cap'); if (cap) { cap.focus(); cap.select(); } D.toast('Press Ctrl+C to copy the caption'); } }
  function openShare(kind, src) {
    var d = dataFor(kind, src); if (!d.title) return; var cv = draw(d), url = cv.toDataURL('image/png'), fname = (d.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'drugbox') + '-card.png';
    var canNative = !!(navigator.canShare && window.File);
    var m = D.modal({ title: 'Share card', secondary: 'Close', body: '<div class="dx-sh"><img class="dx-sh-img" alt="Share card preview" src="' + url + '"><textarea class="dx-sh-cap" rows="3" aria-label="Caption">' + esc(d.caption) + '</textarea>' +
      '<div class="dx-sh-a"><a class="dx-sh-b p" href="' + url + '" download="' + fname + '">Download image</a><button type="button" class="dx-sh-b" data-sh="copy">Copy caption</button>' +
      '<a class="dx-sh-b wa" href="https://wa.me/?text=' + encodeURIComponent(d.caption) + '" target="_blank" rel="noopener">WhatsApp</a>' + (canNative ? '<button type="button" class="dx-sh-b" data-sh="native">Share…</button>' : '') + '</div>' +
      '<p class="dx-sh-n">1200 × 630 — the size WhatsApp and LinkedIn show in full. For LinkedIn, download the image and paste the caption.</p></div>' });
    var box = m.el || document.querySelector('.dbk-ov'); if (!box) return;
    box.addEventListener('click', function (e) { var b = e.target.closest('[data-sh]'); if (!b) return; var cap = box.querySelector('.dx-sh-cap').value;
      if (b.dataset.sh === 'copy') copy(cap, b);
      if (b.dataset.sh === 'native') cv.toBlob(function (bl) { try { var f = new File([bl], fname, { type: 'image/png' }); if (navigator.canShare({ files: [f] })) navigator.share({ files: [f], text: cap }).catch(function () {}); else navigator.share({ text: cap }).catch(function () {}); } catch (x) {} }); });
  }
  /* ── trade-show mode ── */
  var TS = null;
  function tradeShow(co) {
    if (TS) return; var t = window.dxTiers ? window.dxTiers.tierOf(co) : 0, TN = ['Not verified', 'Registered', 'Licensed', 'Inspected'], url = pageUrl(co);
    var qr = ''; if (window.qrcode) { var q = window.qrcode(0, 'M'); q.addData(url); q.make(); qr = q.createSvgTag({ cellSize: 10, margin: 2, scalable: true }); }
    var hi = []; (co.products || []).slice(0, 6).forEach(function (p) { hi.push(['Product', typeof p === 'string' ? p : (p.name || p.title || '')]); });
    if (window.dxHubData) window.dxHubData.credentials(co).filter(function (c) { return !/^Member:/.test(c.name); }).slice(0, 6).forEach(function (c) { hi.push(['Certificate', c.name + (c.expiry ? ' · valid to ' + c.expiry : '') + ' — ' + c.site]); });
    (co.sectors || []).forEach(function (s) { hi.push(['We work in', s]); }); if (!hi.length) hi.push(['Based in', co.city || 'Egypt']);
    var el = document.createElement('div'); el.className = 'dx-ts'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Trade-show mode');
    var L = (typeof LOGO_ICON !== 'undefined') ? '<img class="dx-ts-logo" src="' + LOGO_ICON + '" alt="">' : '';
    el.innerHTML = '<button type="button" class="dx-ts-x" aria-label="Exit trade-show mode">Exit ✕</button><div class="dx-ts-in"><div class="dx-ts-l">' + L + '<div class="dx-ts-k">' + esc((co.sectors || []).join(' · ')) + '</div><h1>' + esc(co.name) + '</h1><p>' + esc(co.tagline || '') + '</p>' +
      '<div class="dx-ts-t">' + (t ? 'Verification level ' + t + ' · ' + TN[t] : 'On Drugbox') + '</div><div class="dx-ts-hi"><span></span><b></b></div></div><div class="dx-ts-r"><div class="dx-ts-qr">' + qr + '</div><div class="dx-ts-u">Scan to see our page, certificates and products</div><div class="dx-ts-url">' + esc(url.replace('https://', '')) + '</div></div></div>';
    document.body.appendChild(el); var n = 0, sp = el.querySelector('.dx-ts-hi span'), bb = el.querySelector('.dx-ts-hi b');
    function tick() { var h = hi[n % hi.length]; sp.textContent = h[0]; bb.textContent = h[1]; el.querySelector('.dx-ts-hi').classList.remove('in'); void el.offsetWidth; el.querySelector('.dx-ts-hi').classList.add('in'); n++; }
    tick(); var iv = setInterval(tick, 4000);
    function close() { clearInterval(iv); document.removeEventListener('keydown', key); el.remove(); TS = null; try { if (document.fullscreenElement) document.exitFullscreen(); } catch (e) {} }
    function key(e) { if (e.key === 'Escape') close(); }
    el.querySelector('.dx-ts-x').addEventListener('click', close); document.addEventListener('keydown', key);
    try { if (el.requestFullscreen) el.requestFullscreen().catch(function () {}); } catch (e) {}
    TS = { close: close };
  }
  /* ── entry points ── */
  function coFromHeader() { if (!document.querySelector('#dxDir.cp h1.cp-name')) return null; var s = window.dxDir.S && window.dxDir.S.open; return s ? (window.dxDir.bySlug(s) || null) : null; }   /* the open slug, never the heading text: names are not unique */
  function decorate() {
    var q = document.querySelector('#dxDir.cp [data-hqr]'); if (q && !q.parentElement.querySelector('.dx-sh-open')) q.insertAdjacentHTML('afterend', '<button type="button" class="dr-btn dx-sh-open" data-share="co">' + SHARE_IC + 'Share card</button>');
    var pg = document.body.getAttribute('data-page');
    if (pg === 'jobs') document.querySelectorAll('#jx .jcard .jx-acts').forEach(function (r) { if (r.querySelector('.dx-sh-ic')) return; r.insertAdjacentHTML('beforeend', '<button type="button" class="jx-ic dx-sh-ic" data-share="job" title="Share card" aria-label="Share card">' + SHARE_IC + '</button>'); });
    if (pg === 'market') document.querySelectorAll('#mkx .sponsored-card, #mkx .lcard').forEach(function (c) { if (c.dataset.dxsh || c.closest('[onclick],[role=link]')) return; c.dataset.dxsh = '1';
      var main = [].slice.call(c.querySelectorAll('button')).filter(function (b) { return /Contact Supplier|Request details|Make an offer|Contact/i.test(orig(b)); })[0]; if (!main) return;
      main.insertAdjacentHTML('afterend', '<button type="button" class="dx-sh-mini" data-share="listing" title="Share card" aria-label="Share card">' + SHARE_IC + '</button>'); });
  }
  function qrDialogHook() { var ov = [].slice.call(document.querySelectorAll('.dbk-ov')).pop(); if (!ov || ov.dataset.ts) return; var dl = [].slice.call(ov.querySelectorAll('a')).filter(function (a) { return /Download QR/.test(orig(a)); })[0]; if (!dl) return;
    ov.dataset.ts = '1'; dl.insertAdjacentHTML('afterend', '<button type="button" class="dr-btn dx-ts-open">Trade-show mode</button>'); }
  new MutationObserver(function () { if (document.querySelector('.dbk-ov:not([data-ts])')) qrDialogHook(); }).observe(document.body, { childList: true });
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-share],.dx-ts-open'); if (!t) return; e.preventDefault(); e.stopPropagation();
    if (t.classList.contains('dx-ts-open')) { var co0 = coFromHeader(); document.querySelectorAll('.dbk-ov').forEach(function (o) { o.remove(); }); if (co0) tradeShow(co0); return; }
    var k = t.dataset.share; if (k === 'co') { var co = coFromHeader(); if (co) openShare('co', co); }
    else if (k === 'job') openShare('job', t.closest('.jcard')); else openShare('listing', t.closest('.sponsored-card,.lcard'));
  }, true);
  C.onRender('share', idle(decorate));
  window.dxShare = { open: openShare, tradeShow: tradeShow, draw: draw, data: dataFor };
})();
