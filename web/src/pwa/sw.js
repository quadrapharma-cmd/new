/* Drugbox service worker (w-pwa). web/build/live.py writes it to <live>/sw.js from web/src/pwa/sw.js; VERSION is the build's stamp.
   What it does — and what it never does:
   · pages (navigations) always come from the network (with navigation preload): a new deploy is what the next open shows;
     only when the network fails it answers with the bilingual offline page, which is written into this file (nothing to keep)
   · every other request (scripts, Supabase API / auth / storage, signed links, photos, videos) is not touched: no answer from
     here and nothing kept — the browser's own HTTP cache rules apply as without a service worker
   · Cache Storage holds nothing of the member's; caches of earlier versions ('drugbox-*') are removed when this one takes over,
     and the page removes them all on sign-out
   · push: shows the notice Drugbox sent (its own words for the kind of notice and a name — never what a member wrote) and
     opens the page it is about when tapped */
'use strict';
const VERSION = '__VERSION__', CACHE = 'drugbox-static-' + VERSION;
const ICON = '__ICON__', BADGE = '__BADGE__', OFFLINE = __OFFLINE__;
const scoped = (p) => new URL(p, self.registration.scope).href;
const clip = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u001f\u007f‪-‮⁦-⁩]/g, ' ').trim().slice(0, n);

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    // requests that are not page loads go straight to the network, without starting this worker (Chrome's static routing)
    if (e.addRoutes) {
      try { await e.addRoutes([{ condition: { not: { requestMode: 'navigate' } }, source: 'network' }]); }
      catch (_) { try { await e.addRoutes(['script', 'style', 'image', 'font', 'video', 'audio', 'empty', 'manifest'].map((d) => ({ condition: { requestDestination: d }, source: 'network' }))); } catch (__) { /* older browser: the fetch handler lets them through */ } }
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('drugbox-') && k !== CACHE) await caches.delete(k);
    if (self.registration.navigationPreload) { try { await self.registration.navigationPreload.enable(); } catch (_) { /* not supported */ } }
    await self.clients.claim();
  })());
});

const offline = () => new Response(OFFLINE, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'" } });

self.addEventListener('fetch', (e) => {
  const r = e.request;
  if (r.mode !== 'navigate' || r.method !== 'GET') return;          // never answered or kept here: see the note at the top
  e.respondWith((async () => {
    try { const pre = await e.preloadResponse; return pre || await fetch(r); }
    catch (_) { return offline(); }
  })());
});

self.addEventListener('message', (e) => {
  if (e.data && e.data.dx === 'version' && e.ports && e.ports[0]) e.ports[0].postMessage({ version: VERSION });
});

/* ── push ── */
const route = (u) => { const s = String(u || ''); return /^#\/[\w\/-]{0,120}$/.test(s) ? s : '#/notifs'; };
self.addEventListener('push', (e) => {
  let d = {}; try { d = e.data ? e.data.json() : {}; } catch (_) { d = {}; }
  const ar = d.lang === 'ar', tag = clip(d.tag, 64);
  e.waitUntil(self.registration.showNotification(clip(d.title, 120) || 'Drugbox', {
    body: clip(d.body, 240), icon: scoped(ICON), badge: scoped(BADGE), lang: ar ? 'ar' : 'en', dir: ar ? 'rtl' : 'ltr',
    tag: tag || undefined, renotify: !!tag, timestamp: Number(d.at) || Date.now(), data: { url: route(d.url) } }));
});
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const hash = route(e.notification.data && e.notification.data.url);
  e.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const w = wins.find((c) => c.url.startsWith(self.registration.scope));
    if (w) { try { await w.focus(); } catch (_) { /* not allowed: the message still opens the page */ } w.postMessage({ dx: 'open', hash }); return; }
    await self.clients.openWindow(scoped('./') + hash);
  })());
});
/* the browser replaced the subscription: subscribe again with the same server key; the page saves it on its next open
   (the old address answers 410 and the server removes it) */
self.addEventListener('pushsubscriptionchange', (e) => {
  const opts = e.oldSubscription && e.oldSubscription.options;
  if (opts && opts.applicationServerKey) e.waitUntil(self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: opts.applicationServerKey }).catch(() => {}));
});
