// Drugbox — load test of the live app's hot paths, as signed-in members (k6, https://k6.io).
//
//   k6 run -e BASE=https://<staging-ref>.supabase.co -e ANON=<anon key> -e VUS=2000 -e USERS=100000 tests/load/k6_drugbox.js
//
// Each virtual user signs in as a random seeded member (member<N>@scale.test / Scale-pass-2026 — tools/scale/seed_100k.sql)
// with POST /auth/v1/token?grant_type=password, then loops over a weighted mix of exactly the requests
// web/src/live/adapter.js sends (same paths, select/embed strings, order, limits and RPC bodies; apikey + Bearer
// headers like supabase-js): feed page (+ my likes/saves among its ids, sometimes the next page by the keyset cursor),
// conversations (my_conversations, then one conversation), the companies directory (directory_companies_page),
// notifications, the background poll (new_messages + new notifications), suggestions, and a small share of writes
// (create a post, send a message, like a post). Every request carries an `endpoint` tag.
// A token lives an hour (no refresh needed below DURATION = 55m).
//
// Settings (-e NAME=value): BASE (required), ANON (required), VUS (default 50), USERS (seeded members, 100000),
//   DURATION (steady phase, 3m), RAMP (ramp-up, 1m — on Supabase keep ≥ VUS/30 s: see "sign-in" below),
//   THINK (seconds between a member's actions, mean, 1), PASSWORD (Scale-pass-2026), SUMMARY (write the JSON summary here).
// Pass = every threshold green: http_req_failed < 1 %, p95 feed / conversations / directory < 500 ms, post < 800 ms.
//
// Sign-in: Supabase Auth limits password sign-ins per IP (Dashboard → Authentication → Rate Limits). For a 2,000-member
// run from one machine raise that limit on STAGING for the test (or ramp slowly); a 429 is retried with back-off and
// counted in `signin_throttled` (not as a failed request), so throttling shows up without failing the run by itself.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE = (__ENV.BASE || '').replace(/\/+$/, '');
const ANON = __ENV.ANON || '';
const VUS = +(__ENV.VUS || 50);
const USERS = +(__ENV.USERS || 100000);
const THINK = +(__ENV.THINK || 1);
const PASSWORD = __ENV.PASSWORD || 'Scale-pass-2026';
if (!BASE || !ANON) throw new Error('set -e BASE=https://<ref>.supabase.co -e ANON=<anon key>');

const PCOLS = 'id,name,headline,company,country,bio,avatar_url,role,verified,location,open_to_work,hiring,profile_views,followers_count';
const ENDPOINTS = ['signin', 'feed', 'feed_mine', 'conversations', 'conversation', 'directory', 'notifications', 'poll', 'suggest', 'post', 'message', 'like'];
const lat = {}, err = {};
ENDPOINTS.forEach((e) => { lat[e] = new Trend('lat_' + e, true); err[e] = new Rate('err_' + e); });
const throttled = new Counter('signin_throttled');

export const options = {
  scenarios: {
    members: {
      executor: 'ramping-vus', startVUs: 0, gracefulRampDown: '15s',
      stages: [{ duration: __ENV.RAMP || '1m', target: VUS }, { duration: __ENV.DURATION || '3m', target: VUS }, { duration: '20s', target: 0 }],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{endpoint:feed}': ['p(95)<500'],
    'http_req_duration{endpoint:conversations}': ['p(95)<500'],
    'http_req_duration{endpoint:directory}': ['p(95)<500'],
    'http_req_duration{endpoint:post}': ['p(95)<800'],
  },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max', 'count'],
};

// ── per virtual user (module scope is per VU in k6) ──
const S = { token: null, me: null, n: 0, partners: [], lastMsg: 0, lastNotif: 0, feedIds: [], cursor: null, nextSignin: 0 };

function headers(json) {
  const h = { apikey: ANON, Authorization: 'Bearer ' + (S.token || ANON), 'X-Client-Info': 'supabase-js-web/2.45.0', 'Accept-Profile': 'public' };
  if (json) { h['Content-Type'] = 'application/json'; h['Content-Profile'] = 'public'; delete h['Accept-Profile']; }
  return h;
}
function record(ep, res, ok) {
  lat[ep].add(res.timings.duration);
  err[ep].add(!ok);
  return res;
}
function get(ep, path, extra) {
  const res = http.get(BASE + '/rest/v1/' + path, { headers: Object.assign(headers(false), extra || {}), tags: { endpoint: ep } });
  return record(ep, res, res.status === 200);
}
function rpc(ep, fn, body) {
  const res = http.post(BASE + '/rest/v1/rpc/' + fn, JSON.stringify(body || {}), { headers: headers(true), tags: { endpoint: ep } });
  return record(ep, res, res.status === 200);
}
function insert(ep, table, row, single) {
  const h = headers(true);
  if (single) { h.Prefer = 'return=representation'; h.Accept = 'application/vnd.pgrst.object+json'; }
  const res = http.post(BASE + '/rest/v1/' + table + (single ? '?select=*' : ''), JSON.stringify(row), { headers: h, tags: { endpoint: ep } });
  return record(ep, res, res.status === 201 || res.status === 200 || res.status === 204);
}
function json(res) { try { return res.json(); } catch (e) { return null; } }
const enc = encodeURIComponent;

function signIn() {
  if (Date.now() < S.nextSignin) { sleep(1); return false; }
  S.n = 1 + Math.floor(Math.random() * USERS);
  const res = http.post(BASE + '/auth/v1/token?grant_type=password',
    JSON.stringify({ email: 'member' + S.n + '@scale.test', password: PASSWORD, gotrue_meta_security: {} }),
    { headers: { apikey: ANON, Authorization: 'Bearer ' + ANON, 'Content-Type': 'application/json', 'X-Client-Info': 'supabase-js-web/2.45.0' },
      tags: { endpoint: 'signin' }, responseCallback: http.expectedStatuses(200, 429) });
  if (res.status === 429) { throttled.add(1); S.nextSignin = Date.now() + 2000 + Math.random() * 8000; lat.signin.add(res.timings.duration); return false; }
  const b = json(res), ok = res.status === 200 && b && b.access_token && b.user;
  record('signin', res, !!ok);
  check(res, { 'signed in': () => !!ok });
  if (!ok) { S.nextSignin = Date.now() + 5000; return false; }
  S.token = b.access_token; S.me = b.user.id;
  return true;
}

// ── the mix (weights sum to 100) ──
function feed() {
  let path = 'posts?select=' + enc('*,author:profiles!posts_user_id_fkey(' + PCOLS + '),post_media(*)') + '&order=created_at.desc,id.desc&limit=20';
  if (S.cursor && Math.random() < 0.3) {   // scrolling: the next page by the (created_at, id) keyset, as fetchPage builds it
    const t = enc(S.cursor.t);
    path += '&created_at=lte.' + t + '&or=' + enc('(created_at.lt.' + S.cursor.t + ',and(created_at.eq.' + S.cursor.t + ',id.lt.' + S.cursor.id + '))');
  } else S.cursor = null;
  const res = get('feed', path), rows = res.status === 200 ? json(res) : null;
  if (!rows || !rows.length) return;
  const ids = rows.map((r) => r.id).join(','), last = rows[rows.length - 1];
  S.cursor = { t: last.created_at, id: last.id };
  S.feedIds = rows.map((r) => r.id);
  get('feed_mine', 'reactions?select=post_id&user_id=eq.' + S.me + '&post_id=in.(' + ids + ')');
  get('feed_mine', 'saved_posts?select=post_id&user_id=eq.' + S.me + '&post_id=in.(' + ids + ')');
}
function conversations() {
  const res = rpc('conversations', 'my_conversations', { p_limit: 50 }), rows = res.status === 200 ? json(res) : null;
  if (rows && rows.length) {
    S.partners = rows.slice(0, 10).map((r) => r.partner);
    rpc('conversation', 'conversation_messages', { p_partner: S.partners[Math.floor(Math.random() * S.partners.length)], p_limit: 50 });
  }
}
function directory() {
  const q = Math.random() < 0.1 ? (['metformin', 'nile', 'paracetamol', 'delta'])[Math.floor(Math.random() * 4)] : null;
  const off = q ? 0 : 100 * Math.floor(Math.random() * Math.max(1, Math.floor(USERS / 20 / 100)));
  rpc('directory', 'directory_companies_page', { p_limit: 100, p_offset: off, p_q: q });
}
function notifications() {
  const res = get('notifications', 'notifications?select=' + enc('*,actor:profiles!notifications_from_user_fkey(' + PCOLS + ')') + '&user_id=eq.' + S.me + '&order=created_at.desc&limit=50');
  const rows = res.status === 200 ? json(res) : null;
  if (rows && rows.length) S.lastNotif = Math.max(S.lastNotif, ...rows.map((r) => r.id));
}
function poll() {   // the background poll (no Realtime): new messages after the last id, new notifications after the last id
  const m = rpc('poll', 'new_messages', { p_after: S.lastMsg }), rows = m.status === 200 ? json(m) : null;
  if (rows && rows.length) S.lastMsg = Math.max(S.lastMsg, ...rows.map((r) => r.id));
  get('poll', 'notifications?select=id,type&user_id=eq.' + S.me + '&id=gt.' + S.lastNotif + '&order=id.desc&limit=50');
}
function suggest() { rpc('suggest', 'suggest_people', { p_limit: 12 }); }
function post() {
  insert('post', 'posts', { user_id: S.me, body: 'Load test post from member' + S.n + ' at ' + new Date().toISOString(), category: 'general' }, true);
}
function message() {
  const to = S.partners.length ? S.partners[Math.floor(Math.random() * S.partners.length)] : null;
  if (!to) return conversations();
  insert('message', 'messages', { sender_id: S.me, receiver_id: to, body: 'Load test message ' + Date.now() }, true);
}
function like() {
  if (!S.feedIds.length) return feed();
  const id = S.feedIds[Math.floor(Math.random() * S.feedIds.length)];
  const h = headers(true); h.Prefer = 'resolution=merge-duplicates';
  const res = http.post(BASE + '/rest/v1/reactions', JSON.stringify({ post_id: id, user_id: S.me, kind: 'like' }), { headers: h, tags: { endpoint: 'like' } });
  record('like', res, res.status === 201 || res.status === 200 || res.status === 204);
}
const MIX = [[feed, 35], [conversations, 15], [directory, 10], [notifications, 12], [poll, 10], [suggest, 5], [post, 3], [message, 6], [like, 4]];
const TOTAL = MIX.reduce((s, x) => s + x[1], 0);

export default function () {
  if (!S.token && !signIn()) return;
  let r = Math.random() * TOTAL;
  for (const [fn, w] of MIX) { if ((r -= w) < 0) { fn(); break; } }
  sleep(THINK * (0.5 + Math.random()));
}

export function handleSummary(data) {
  const m = data.metrics, row = (e) => {
    const t = m['lat_' + e], er = m['err_' + e];
    if (!t || !t.values || !t.values.count) return null;
    const v = t.values, f = (x) => (x === undefined ? '-' : x.toFixed(1));
    return [e.padEnd(14), String(v.count).padStart(8), f(v.med).padStart(9), f(v['p(95)']).padStart(9), f(v['p(99)']).padStart(9), f(v.max).padStart(9),
            ((er && er.values ? er.values.rate * 100 : 0).toFixed(2) + '%').padStart(8)].join(' ');
  };
  const lines = ['', 'endpoint        requests   p50 ms    p95 ms    p99 ms    max ms   errors'];
  ENDPOINTS.forEach((e) => { const l = row(e); if (l) lines.push(l); });
  const fail = m.http_req_failed ? (m.http_req_failed.values.rate * 100).toFixed(2) : '?';
  const reqs = m.http_reqs ? m.http_reqs.values : {};
  lines.push('', 'requests: ' + (reqs.count || 0) + ' (' + (reqs.rate || 0).toFixed(1) + '/s)   http_req_failed: ' + fail + '%   sign-ins throttled: ' + (m.signin_throttled ? m.signin_throttled.values.count : 0));
  const th = [];
  Object.keys(m).forEach((k) => { if (m[k].thresholds) Object.keys(m[k].thresholds).forEach((t) => th.push((m[k].thresholds[t].ok ? 'PASS ' : 'FAIL ') + k + ' ' + t)); });
  lines.push('thresholds:', ...th.map((t) => '  ' + t), '');
  const out = { stdout: lines.join('\n') };
  if (__ENV.SUMMARY) out[__ENV.SUMMARY] = JSON.stringify(data, null, 1);
  return out;
}
