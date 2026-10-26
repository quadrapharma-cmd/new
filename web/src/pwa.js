/* The installable app (slice w-pwa): an "Install Drugbox" offer, the iPhone/iPad guide (Share → Add to Home Screen), and
   notifications on this device — in Settings ("Drugbox app and this device") and as a small ask on the Notifications page.
   Never on the first load: the offer waits until the member has used the app a little, the notification ask only shows on the
   Notifications page and the browser's own permission prompt only after "Turn on" is pressed. Once dismissed or installed,
   neither comes back on this device (kept in this browser under drugbox.* keys, which signing out does not clear).
   Device notifications go through window.dxPwa: the sample implementation below only previews them (the demo has no server);
   the live app replaces it with the service worker, the browser's push subscription and the database (web/src/live/adapter.js,
   AREA w-pwa). Installing is the browser's own: the same code runs in both. */
(function () {
  var D = window.DBK; if (!D || typeof window.goto !== 'function') return;
  function $(id) { return document.getElementById(id); }
  function toast(m) { (window.toast || D.toast)(m); }
  function get(k) { try { return localStorage.getItem('drugbox.' + k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem('drugbox.' + k, v); } catch (e) {} }
  function inApp() { var a = $('app'); if (!a) return false; var d = a.style.display; return d === 'flex' || d === 'block' ? true : d === 'none' ? false : a.getClientRects().length > 0; }
  var UA = navigator.userAgent || '';
  var IOS = /iPhone|iPad|iPod/.test(UA) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var WEB = /^https?:$/.test(location.protocol);                   /* the offline demo file cannot be installed */
  function standalone() { try { return (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true; } catch (e) { return false; } }

  /* ── install ── */
  var PROMPT = null, PREVIEW = false;
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); PROMPT = e; later(maybeOffer, 0); paintApp(); });   /* our own offer, at a good moment */
  window.addEventListener('appinstalled', function () { PROMPT = null; put('install', 'installed'); hideOffer(); paintApp(); });
  function installState() {
    if (standalone() || get('install') === 'installed') return 'installed';
    if (PROMPT) return 'prompt';
    if (IOS && WEB) return 'ios';
    return 'manual';
  }
  function install() {
    var st = installState();
    if (st === 'prompt') {
      var p = PROMPT; PROMPT = null; hideOffer();
      return Promise.resolve(p.prompt()).then(function () { return p.userChoice; }).then(function (c) {
        if (c && c.outcome === 'accepted') { put('install', 'installed'); toast('Drugbox is being installed'); } else put('install', 'dismissed');
        paintApp();
      }, function () { paintApp(); });
    }
    guide(); return Promise.resolve();
  }
  var SHARE = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" class="dx-pwa-ic"><path d="M12 3v12M7.5 7.5 12 3l4.5 4.5M5 11v9h14v-9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var PLUS = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" class="dx-pwa-ic"><rect x="4" y="4" width="16" height="16" rx="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 8v8M8 12h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  function guide() {
    var ios = '<h3 class="dx-pwa-h">On iPhone or iPad</h3><ol class="dx-pwa-steps">' +
      '<li><span>Open Drugbox in <b>Safari</b>.</span></li>' +
      '<li><span>Tap <b>Share</b> ' + SHARE + ' — at the bottom of the screen on iPhone, at the top on iPad.</span></li>' +
      '<li><span>Choose <b>Add to Home Screen</b> ' + PLUS + ', then tap <b>Add</b>.</span></li>' +
      '<li><span>Open Drugbox from its icon on your Home Screen.</span></li></ol>' +
      '<p class="dx-pwa-note">Notifications on iPhone and iPad work only in the installed app (iOS 16.4 or later).</p>';
    var other = '<h3 class="dx-pwa-h">On Android, Windows or Mac</h3><ol class="dx-pwa-steps">' +
      '<li><span>Open Drugbox in <b>Chrome</b> or <b>Edge</b>.</span></li>' +
      '<li><span>Open the browser menu <b>⋮</b> and choose <b>Install app</b> or <b>Add to Home screen</b>.</span></li>' +
      '<li><span>Drugbox opens in its own window, like an app.</span></li></ol>';
    D.modal({ title: 'Install Drugbox', body: '<div class="dx-pwa-guide">' + (IOS ? ios + other : other + ios) + '</div>', secondary: 'Close' });
  }

  /* the offer: a small card once the member has used the app a little (a few pages or a minute), never on the first screen */
  var seen = 0, t0 = 0;
  function later(fn, ms) { setTimeout(fn, ms || 0); }
  function wanted() { var st = installState(); return PREVIEW || ((st === 'prompt' || st === 'ios') && !get('install')); }
  function maybeOffer() {
    if (!wanted() || !inApp() || $('dxInstall') || document.querySelector('.modal-bg')) return;
    if (!PREVIEW && seen < 3 && (!t0 || Date.now() - t0 < 60000)) return;
    var ios = installState() === 'ios', b = document.createElement('div');
    b.id = 'dxInstall'; b.className = 'dx-pwa-offer'; b.setAttribute('role', 'region'); b.setAttribute('aria-label', 'Install Drugbox');
    b.innerHTML = '<img class="dx-pwa-logo" alt="" src="' + (typeof LOGO_ICON !== 'undefined' ? LOGO_ICON : '') + '">' +
      '<div class="dx-pwa-txt"><b>Install Drugbox</b><span>' + (ios ? 'Add it to your Home Screen: it opens full screen, like an app, and can send you notifications.'
        : 'Open it from your Home screen or desktop like an app — full screen, quicker to reach.') + '</span>' +
      '<div class="dx-pwa-btns"><button type="button" class="btn-p" data-pwa="install">' + (ios ? 'Show me how' : 'Install') + '</button>' +
      '<button type="button" class="btn-ghost" data-pwa="later">Not now</button></div></div>' +
      '<button type="button" class="dx-pwa-x" data-pwa="later" aria-label="Close">×</button>';
    document.body.appendChild(b);
    if (window.dxI18nAttrs) window.dxI18nAttrs(b);
  }
  function hideOffer() { var b = $('dxInstall'); if (b) b.remove(); }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-pwa]'); if (!t) return;
    var a = t.dataset.pwa;
    if (a === 'install') { if (!PREVIEW) put('install', 'dismissed'); PREVIEW = false; hideOffer(); install(); }
    else if (a === 'later') { put('install', 'dismissed'); PREVIEW = false; hideOffer(); }
    else if (a === 'guide') guide();
    else if (a === 'app-install') install();
    else if (a === 'push-on' || a === 'ask-on') pushOn(t, a === 'ask-on');
    else if (a === 'push-off') pushOff(t);
    else if (a === 'ask-later') { put('pushask', 'later'); var s = $('dxPushAsk'); if (s) s.remove(); }
    else if (a === 'push-save') savePrefs(t);
  });
  if (window.dxCore) window.dxCore.onRender('pwa', function () {
    if (inApp()) { if (!t0) t0 = Date.now(); seen++; }
    hideOfferOnModal(); later(maybeOffer, 400); later(paintPage, 0);
  });
  setInterval(function () { if (!document.hidden) maybeOffer(); }, 15000);
  function hideOfferOnModal() { if (document.querySelector('.modal-bg') && $('dxInstall')) hideOffer(); }

  /* ── notifications on this device ── */
  var DEMO_ON = false;
  var PUSH_DEF = { push_messages: true, push_connections: true, push_comments: true, push_mentions: true, push_reactions: false, push_follows: false, push_jobs: true, push_business: true };
  window.dxPwa = window.dxPwa || {
    live: false,
    /* on | off | denied (blocked in the browser) | install (iPhone/iPad: install first) | unsupported */
    pushState: function () { return Promise.resolve(DEMO_ON ? 'on' : 'off'); },
    pushOn: function () { DEMO_ON = true; return Promise.resolve('on'); },
    pushOff: function () { DEMO_ON = false; return Promise.resolve('off'); },
    prefs: function () { return Promise.resolve(Object.assign({}, PUSH_DEF, D.store.get('pushPrefs', {}))); },
    savePrefs: function (o) { D.store.set('pushPrefs', Object.assign({}, D.store.get('pushPrefs', {}), o)); return Promise.resolve(); }
  };
  function P() { return window.dxPwa; }
  var SAY = { on: 'Notifications are on for this device.', off: 'Get a notification on this device when someone messages you or answers a request.',
    denied: 'Notifications are blocked for Drugbox in this browser. Allow them in the browser settings (the lock next to the address), then try again.',
    install: 'On iPhone and iPad, install Drugbox first (Share → Add to Home Screen, iOS 16.4 or later), then turn notifications on in the installed app.',
    unsupported: 'This browser cannot show notifications from Drugbox. You still see every notification inside Drugbox.' };
  function pushOn(btn, fromAsk) {
    busy(btn, true);
    P().pushOn().then(function (st) {
      if (st === 'on') { toast(P().live ? 'Notifications are on for this device' : 'Demo: in the live app this device now gets notifications'); put('pushask', 'done'); }
      else toast(SAY[st] || 'Could not turn notifications on');
      paintPage();
    }, function (e) { toast((e && e.message) || 'Could not turn notifications on'); }).then(function () { busy(btn, false); });
  }
  function pushOff(btn) {
    busy(btn, true);
    P().pushOff().then(function () { toast('Notifications are off for this device'); paintPage(); }, function (e) { toast((e && e.message) || 'Could not turn notifications off'); }).then(function () { busy(btn, false); });
  }
  function busy(b, on) { if (!b) return; b.disabled = on; if (on) b.setAttribute('aria-busy', 'true'); else b.removeAttribute('aria-busy'); }
  var KINDS = { push_messages: 'Messages', push_connections: 'Connection requests and answers', push_comments: 'Comments and replies on my posts', push_mentions: 'Mentions',
    push_reactions: 'Reactions to my posts', push_follows: 'New followers', push_jobs: 'Jobs and saved-search alerts', push_business: 'Requests, deals, payments, companies and groups' };
  function savePrefs(btn) {
    var o = {}; document.querySelectorAll('#setApp [data-push]').forEach(function (x) { o[x.dataset.push] = x.checked; });
    busy(btn, true);
    P().savePrefs(o).then(function () { say('setAppMsg', 'Device notification settings saved'); }, function (e) { say('setAppMsg', (e && e.message) || 'Could not save', true); }).then(function () { busy(btn, false); });
  }
  function say(id, text, bad) { var e = $(id); if (!e) return; e.textContent = text; e.className = 'dx-set-msg' + (bad ? ' err' : ' ok'); if (window.dxI18nAdopt && e.firstChild) window.dxI18nAdopt(e.firstChild); }

  /* Settings → "Drugbox app and this device", right after Notifications */
  function paintPage() {
    var pg = document.body.getAttribute('data-page');
    if (pg === 'notifs') paintAsk(); else if ($('setNotif')) paintSettings();
  }
  function paintSettings() {
    var n = $('setNotif'); if (!n) return;
    var c = $('setApp');
    if (!c) {
      c = document.createElement('section'); c.className = 'card dx-set-card'; c.id = 'setApp'; c.setAttribute('aria-labelledby', 'setApp-h');
      c.innerHTML = '<h2 id="setApp-h">Drugbox app and this device</h2>' +
        '<div class="dx-set-row dx-pwa-row"><span><b>Install the app</b><span class="dx-set-sub" id="setAppInst"></span></span><span id="setAppInstBtn"></span></div>' +
        '<div class="dx-set-row dx-pwa-row"><span><b>Notifications on this device</b><span class="dx-set-sub" id="setAppPush"></span></span><span id="setAppPushBtn"></span></div>' +
        '<div id="setAppKinds" class="dx-set-list" hidden></div><div class="dx-set-msg" id="setAppMsg" role="status"></div>';
      n.parentNode.insertBefore(c, n.nextSibling);
      P().prefs().then(function (s) {
        var l = $('setAppKinds'); if (!l) return;
        l.innerHTML = '<p class="dx-set-sub">What this device is told about:</p>' + Object.keys(KINDS).map(function (k) { return '<label class="dx-set-tg"><input type="checkbox" data-push="' + k + '"' + (s[k] ? ' checked' : '') + '> <span>' + KINDS[k] + '</span></label>'; }).join('') +
          '<button class="btn-p" type="button" data-pwa="push-save">Save device notification settings</button>';
        if (window.dxI18nAttrs) window.dxI18nAttrs(l);
      }, function () {});
    }
    paintApp();
  }
  function paintApp() {
    var c = $('setApp'); if (!c) return;
    var st = installState(), it = $('setAppInst'), ib = $('setAppInstBtn');
    it.textContent = st === 'installed' ? 'Drugbox is installed on this device.' : st === 'prompt' ? 'Open Drugbox from your Home screen or desktop, full screen.'
      : st === 'ios' ? 'Add Drugbox to your Home Screen from Safari.' : "Use your browser's menu: Install app or Add to Home screen.";
    ib.innerHTML = st === 'installed' ? '<span class="dx-pwa-ok">✓ Installed</span>' : st === 'prompt' ? '<button class="btn-p" type="button" data-pwa="app-install">Install</button>'
      : '<button class="btn-ghost" type="button" data-pwa="guide">How to install</button>';
    P().pushState().then(function (ps) {
      var pt = $('setAppPush'), pb = $('setAppPushBtn'), k = $('setAppKinds'); if (!pt) return;
      pt.textContent = ps === 'off' ? 'Messages, requests and answers, even when Drugbox is closed.' : SAY[ps];
      pb.innerHTML = ps === 'on' ? '<button class="btn-ghost" type="button" data-pwa="push-off">Turn off</button>'
        : ps === 'off' ? '<button class="btn-p" type="button" data-pwa="push-on">Turn on</button>' : ps === 'install' ? '<button class="btn-ghost" type="button" data-pwa="guide">How to install</button>' : '';
      if (k) k.hidden = ps !== 'on';
      if (window.dxI18nAttrs) window.dxI18nAttrs(c);
    });
    if (window.dxI18nAttrs) window.dxI18nAttrs(c);
  }
  /* Notifications page: one short ask, until it is answered on this device */
  function paintAsk() {
    var c = $('content'); if (!c || $('dxPushAsk') || get('pushask')) return;
    P().pushState().then(function (ps) {
      if (ps !== 'off' || $('dxPushAsk') || document.body.getAttribute('data-page') !== 'notifs') return;
      var first = c.firstElementChild; if (!first) return;
      var a = document.createElement('div'); a.id = 'dxPushAsk'; a.className = 'dx-pwa-ask'; a.setAttribute('role', 'region'); a.setAttribute('aria-label', 'Notifications on this device');
      a.innerHTML = '<span class="dx-pwa-bell" aria-hidden="true">🔔</span><span class="dx-pwa-txt"><b>Notifications on this device</b><span>' + SAY.off + '</span></span>' +
        '<span class="dx-pwa-btns"><button type="button" class="btn-p" data-pwa="ask-on">Turn on</button><button type="button" class="btn-ghost" data-pwa="ask-later">Not now</button></span>';
      first.parentNode.insertBefore(a, first);
      if (window.dxI18nAttrs) window.dxI18nAttrs(a);
    });
  }
  /* screenshots for approval: window.dxPwa.preview() shows the offer at once */
  window.dxPwaPreview = function () { PREVIEW = true; hideOffer(); maybeOffer(); };
  window.dxPwaGuide = guide;

  var AR = {
    'Install Drugbox': 'ثبّت Drugbox', 'Install': 'تثبيت', 'Not now': 'ليس الآن', 'Show me how': 'أرني الطريقة', 'Close': 'إغلاق', 'How to install': 'طريقة التثبيت',
    'Add it to your Home Screen: it opens full screen, like an app, and can send you notifications.': 'أضِفه إلى الشاشة الرئيسية: يفتح بملء الشاشة مثل التطبيق ويمكنه إرسال الإشعارات إليك.',
    'Open it from your Home screen or desktop like an app — full screen, quicker to reach.': 'افتحه من الشاشة الرئيسية أو سطح المكتب مثل التطبيق — بملء الشاشة وأسرع في الوصول.',
    'On iPhone or iPad': 'على iPhone أو iPad', 'On Android, Windows or Mac': 'على Android أو Windows أو Mac',
    'Open Drugbox in': 'افتح Drugbox في', 'Tap': 'اضغط', 'Share': 'مشاركة', '— at the bottom of the screen on iPhone, at the top on iPad.': '— أسفل الشاشة في iPhone، وأعلاها في iPad.',
    'Choose': 'اختر', 'Add to Home Screen': 'إضافة إلى الشاشة الرئيسية', ', then tap': '، ثم اضغط', 'Add': 'إضافة',
    'Open Drugbox from its icon on your Home Screen.': 'افتح Drugbox من أيقونته على الشاشة الرئيسية.',
    'Notifications on iPhone and iPad work only in the installed app (iOS 16.4 or later).': 'الإشعارات على iPhone وiPad تعمل فقط في التطبيق المثبّت (iOS 16.4 أو أحدث).',
    'Open the browser menu': 'افتح قائمة المتصفح', 'and choose': 'واختر', 'Install app': 'تثبيت التطبيق', 'or': 'أو', 'Add to Home screen': 'إضافة إلى الشاشة الرئيسية',
    'Drugbox opens in its own window, like an app.': 'يفتح Drugbox في نافذته الخاصة مثل التطبيق.', 'Drugbox is being installed': 'جارٍ تثبيت Drugbox',
    'Drugbox app and this device': 'تطبيق Drugbox وهذا الجهاز', 'Install the app': 'تثبيت التطبيق', 'Notifications on this device': 'الإشعارات على هذا الجهاز',
    'Drugbox is installed on this device.': 'Drugbox مثبّت على هذا الجهاز.', 'Open Drugbox from your Home screen or desktop, full screen.': 'افتح Drugbox من الشاشة الرئيسية أو سطح المكتب بملء الشاشة.',
    'Add Drugbox to your Home Screen from Safari.': 'أضِف Drugbox إلى الشاشة الرئيسية من Safari.', "Use your browser's menu: Install app or Add to Home screen.": 'استخدم قائمة المتصفح: تثبيت التطبيق أو إضافة إلى الشاشة الرئيسية.',
    '✓ Installed': '✓ مثبّت', 'Turn on': 'تشغيل', 'Turn off': 'إيقاف',
    'Messages, requests and answers, even when Drugbox is closed.': 'الرسائل والطلبات والردود، حتى وDrugbox مغلق.',
    'Notifications are on for this device.': 'الإشعارات مفعّلة على هذا الجهاز.',
    'Get a notification on this device when someone messages you or answers a request.': 'يصلك إشعار على هذا الجهاز عندما يراسلك أحد أو يرد على طلب.',
    'Notifications are blocked for Drugbox in this browser. Allow them in the browser settings (the lock next to the address), then try again.': 'الإشعارات محظورة لـ Drugbox في هذا المتصفح. اسمح بها من إعدادات المتصفح (القفل بجوار العنوان) ثم حاول مرة أخرى.',
    'On iPhone and iPad, install Drugbox first (Share → Add to Home Screen, iOS 16.4 or later), then turn notifications on in the installed app.': 'على iPhone وiPad ثبّت Drugbox أولًا (مشاركة ← إضافة إلى الشاشة الرئيسية، iOS 16.4 أو أحدث)، ثم فعّل الإشعارات من التطبيق المثبّت.',
    'This browser cannot show notifications from Drugbox. You still see every notification inside Drugbox.': 'هذا المتصفح لا يعرض إشعارات Drugbox. ستظل ترى كل الإشعارات داخل Drugbox.',
    'What this device is told about:': 'ما يُبلَّغ به هذا الجهاز:', 'Requests, deals, payments, companies and groups': 'الطلبات والصفقات والمدفوعات والشركات والمجموعات',
    'Save device notification settings': 'احفظ إعدادات إشعارات الجهاز', 'Device notification settings saved': 'تم حفظ إعدادات إشعارات الجهاز',
    'Notifications are on for this device': 'تم تفعيل الإشعارات على هذا الجهاز', 'Notifications are off for this device': 'تم إيقاف الإشعارات على هذا الجهاز',
    'Demo: in the live app this device now gets notifications': 'العرض التجريبي: في التطبيق الحقيقي يصل الإشعار الآن إلى هذا الجهاز',
    'Could not turn notifications on': 'تعذّر تفعيل الإشعارات', 'Could not turn notifications off': 'تعذّر إيقاف الإشعارات',
    'Sign in first': 'سجّل الدخول أولًا', "This browser's push service is not supported": 'خدمة الإشعارات في هذا المتصفح غير مدعومة'
  };
  if (window.dxI18nExtend) window.dxI18nExtend(AR); else if (window.dxI18nAdd) window.dxI18nAdd(AR);
})();
