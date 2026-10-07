// Local stand-in for Supabase (tests only): Auth endpoints used by supabase-js + a /rest/v1 proxy to PostgREST + the built app at /.
// Passwords: bcrypt via pgcrypto. Tokens: HS256 JWT with the same secret PostgREST verifies, so RLS applies exactly as on Supabase.
// Loopback only (HOST defaults to 127.0.0.1): it offers open sign-up and a storage emulation, never expose it to a network.
import http from 'node:http'; import crypto from 'node:crypto'; import fs from 'node:fs'; import path from 'node:path'; import pg from 'pg';
const PORT = +process.env.PORT || 54321, HOST = process.env.HOST || '127.0.0.1', REST = process.env.REST_URL || 'http://127.0.0.1:3001';
const SECRET = process.env.JWT_SECRET, APP_DIR = process.env.APP_DIR, STORE = path.resolve(process.env.STORE_DIR || '/tmp/drugbox-storage');
if (!SECRET || SECRET.length < 32) throw new Error('JWT_SECRET (32+ chars) required');
const db = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
const b64u = b => Buffer.from(b).toString('base64url');
function sign(payload) { const h = b64u(JSON.stringify({ alg: 'HS256', typ: 'JWT' })), p = b64u(JSON.stringify(payload)); return `${h}.${p}.${crypto.createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url')}`; }
function verify(t) { const [h, p, s] = String(t || '').split('.'); if (!s) return null; const ok = crypto.createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url'); if (!crypto.timingSafeEqual(Buffer.from(ok), Buffer.from(s.padEnd(ok.length).slice(0, ok.length)))) return null; try { const c = JSON.parse(Buffer.from(p, 'base64url')); return c.exp * 1000 > Date.now() ? c : null; } catch { return null; } }
const bearer = req => (req.headers.authorization || '').replace(/^Bearer /i, '');
/* refresh_token → { uid, used }. Like Supabase: a used token stays valid for 10 s (two tabs refreshing at once), logout revokes the user's tokens */
const refresh = new Map(), REUSE_MS = 10000;
function userJson(u) { return { id: u.id, aud: 'authenticated', role: 'authenticated', email: u.email, user_metadata: u.raw_user_meta_data || {}, app_metadata: { provider: 'email', providers: ['email'] }, identities: [{ provider: 'email' }], created_at: u.created_at }; }
function session(u) { const now = Math.floor(Date.now() / 1000), rt = crypto.randomBytes(24).toString('hex'); refresh.set(rt, { uid: u.id, used: 0 });
  for (const [k, v] of refresh) if (v.used && Date.now() - v.used > REUSE_MS) refresh.delete(k);   // the map does not grow for ever
  return { access_token: sign({ sub: u.id, role: 'authenticated', aud: 'authenticated', email: u.email, iat: now, exp: now + 3600 }), token_type: 'bearer', expires_in: 3600, expires_at: now + 3600, refresh_token: rt, user: userJson(u) }; }
/* the same response headers a production host sends (see vercel.json); the app is one page with inline scripts, so 'unsafe-inline' is needed for scripts (no eval) */
const CSP = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; " +
  "img-src 'self' data: blob: http://localhost:* http://127.0.0.1:*; media-src 'self' data: blob: http://localhost:* http://127.0.0.1:*; " +
  "connect-src 'self' data: blob: http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* https://api.exchangerate.host; worker-src 'self' blob:; " +   // data:/blob: — the app turns picked files into uploads with fetch()
  "frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";
const SEC = { 'x-content-type-options': 'nosniff', 'referrer-policy': 'strict-origin-when-cross-origin' };
const PAGE = { ...SEC, 'content-security-policy': CSP, 'x-frame-options': 'DENY', 'permissions-policy': 'camera=(), microphone=(), geolocation=()' };   // (HSTS only on https: see vercel.json)
const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS', 'access-control-expose-headers': 'content-range,content-profile' };
const send = (res, code, body, extra = {}) => { if (res.headersSent) return res.destroy(); res.writeHead(code, { 'content-type': 'application/json', ...cors, ...SEC, ...extra }); res.end(body === undefined ? '' : JSON.stringify(body)); };
/* a file stream that cannot crash the process (a file removed between the check and the read, a client that hangs up) */
function stream(res, file, code, headers, opts) { const s = fs.createReadStream(file, opts); s.on('error', e => { console.error(e.message); res.destroy(); }); res.writeHead(code, headers); s.pipe(res); }
const readRaw = req => new Promise((r, j) => { const c = []; req.on('data', d => c.push(d)); req.on('end', () => r(Buffer.concat(c))); req.on('error', j); });
const readBody = async req => { const d = (await readRaw(req)).toString(); try { return d ? JSON.parse(d) : {}; } catch { return {}; } };
const authErr = (res, code, msg, extra) => send(res, code, { error: 'invalid_grant', error_description: msg, msg, code, ...extra });
/* storage object names: plain relative keys only; the file must stay inside STORE/<bucket> (no "..", no empty or absolute segments) */
function objFile(bucket, name) {
  if (!/^[a-z0-9_-]{1,63}$/.test(bucket || '')) return null;
  if (!name || name.length > 1024 || /[\\\0]/.test(name) || name.split('/').some(s => s === '' || s === '.' || s === '..')) return null;
  const root = path.join(STORE, bucket), f = path.resolve(root, name);
  return f.startsWith(root + path.sep) ? f : null;
}
const badName = res => send(res, 400, { error: 'Invalid key', statusCode: '400' });
/* Kong in front of Supabase refuses /rest and /auth requests without a valid project key (anon or service_role) */
function apikeyOk(req, res) {
  const k = req.headers.apikey || new URL(req.url, 'http://x').searchParams.get('apikey');
  if (!k) { send(res, 401, { message: 'No API key found in request' }); return false; }
  const c = verify(k); if (!c || !['anon', 'service_role'].includes(c.role)) { send(res, 401, { message: 'Invalid API key' }); return false; }
  return true;
}
process.on('uncaughtException', e => console.error('uncaught:', e));   // last resort: one bad request never takes the stack down
http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://x');
    if (req.method === 'OPTIONS') return send(res, 204);
    if (url.pathname === '/' || url.pathname === '/index.html') return stream(res, APP_DIR + '/index.html', 200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-cache', ...PAGE });
    if (/^\/js\/[\w.-]+\.js$/.test(url.pathname) && fs.existsSync(APP_DIR + url.pathname)) return stream(res, APP_DIR + url.pathname, 200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'public, max-age=31536000, immutable', ...SEC });
    if (/^\/media\/[\w.-]+\.mp4$/.test(url.pathname) && fs.existsSync(APP_DIR + url.pathname)) {   // the splash video of the live build (content-hashed)
      const f = APP_DIR + url.pathname, size = fs.statSync(f).size, rg = range(req, size);
      if (rg === 416) return send(res, 416, { error: 'Range Not Satisfiable' }, { 'content-range': `bytes */${size}` });
      const h = { 'content-type': 'video/mp4', 'accept-ranges': 'bytes', 'cache-control': 'public, max-age=31536000, immutable', ...SEC };
      return rg ? stream(res, f, 206, { ...h, 'content-range': `bytes ${rg.start}-${rg.end}/${size}`, 'content-length': rg.end - rg.start + 1 }, rg) : stream(res, f, 200, { ...h, 'content-length': size });
    }
    if (url.pathname.startsWith('/auth/v1/') && !apikeyOk(req, res)) return;
    if (url.pathname === '/auth/v1/signup' && req.method === 'POST') {
      const b = await readBody(req); const email = String(b.email || '').trim().toLowerCase(), pw = String(b.password || '');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return authErr(res, 400, 'Invalid email');
      if (pw.length < 8) return authErr(res, 422, 'Password should be at least 8 characters');
      const ex = await db.query('select 1 from auth.users where email=$1', [email]);
      /* an address that already has an account gets the same answer as a new one that must confirm its e-mail (Supabase with
         "Confirm email" on): a user object without a session, nothing created — sign-up cannot be used to find out who is registered */
      if (ex.rowCount) return send(res, 200, { id: crypto.randomUUID(), aud: 'authenticated', role: '', email, user_metadata: {}, app_metadata: { provider: 'email', providers: ['email'] }, identities: [], created_at: new Date().toISOString() });
      const r = await db.query("insert into auth.users (email, encrypted_password, raw_user_meta_data) values ($1, crypt($2, gen_salt('bf', 10)), $3) returning *", [email, pw, b.data || {}]);
      return send(res, 200, session(r.rows[0]));
    }
    if (url.pathname === '/auth/v1/token' && req.method === 'POST') {
      const b = await readBody(req), gt = url.searchParams.get('grant_type');
      if (gt === 'password') { const r = await db.query('select * from auth.users where email=$1 and encrypted_password = crypt($2, encrypted_password)', [String(b.email || '').trim().toLowerCase(), String(b.password || '')]);
        return r.rowCount ? send(res, 200, session(r.rows[0])) : authErr(res, 400, 'Invalid login credentials'); }
      if (gt === 'refresh_token') { const t = refresh.get(b.refresh_token); if (!t || (t.used && Date.now() - t.used > REUSE_MS)) return authErr(res, 400, 'Invalid Refresh Token: Refresh Token Not Found');
        t.used = t.used || Date.now();
        const r = await db.query('select * from auth.users where id=$1', [t.uid]); if (!r.rowCount) return authErr(res, 400, 'Invalid Refresh Token: Refresh Token Not Found'); return send(res, 200, session(r.rows[0])); }
      return authErr(res, 400, 'Unsupported grant type');
    }
    if (url.pathname === '/auth/v1/user') {
      if (req.method !== 'GET') return send(res, 405, { code: 405, msg: 'Updating the user is not emulated locally' });   // never a silent no-op
      const c = verify(bearer(req)); if (!c) return authErr(res, 401, 'invalid JWT: unable to parse or verify signature, token has invalid claims: token is expired', { error: 'bad_jwt' });
      const r = await db.query('select * from auth.users where id=$1', [c.sub]); if (!r.rowCount) return authErr(res, 404, 'User not found'); return send(res, 200, userJson(r.rows[0])); }
    if (url.pathname === '/auth/v1/logout') { const c = verify(bearer(req)); if (c) for (const [k, v] of refresh) if (v.uid === c.sub) refresh.delete(k); return send(res, 204); }

    /* Edge Functions (tests): forwarded to the local function server */
    if (url.pathname.startsWith('/functions/v1/')) {
      const target = 'http://127.0.0.1:' + (process.env.FN_PORT || 54400) + url.pathname.replace('/functions/v1', '') + url.search;
      const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await readRaw(req);
      try { const fr = await fetch(target, { method: req.method, headers: { 'content-type': req.headers['content-type'] || 'application/json', authorization: req.headers.authorization || '' }, body });
        const buf = Buffer.from(await fr.arrayBuffer()); res.writeHead(fr.status, { ...cors, ...SEC, 'content-type': fr.headers.get('content-type') || 'text/plain' }); return res.end(buf); }
      catch (e) { return send(res, 502, { error: 'functions not running' }); }
    }

    /* ── Storage (tests only): the object row is inserted AS the user, so the bucket's row-level policies decide; then the file is written ── */
    if (url.pathname.startsWith('/storage/v1/object/')) {
      let rest; try { rest = decodeURIComponent(url.pathname.slice('/storage/v1/object/'.length)); } catch { return badName(res); }
      if (req.method === 'GET' && rest.startsWith('public/')) {
        const [bucket, ...pp] = rest.slice(7).split('/'), name = pp.join('/'), f = objFile(bucket, name); if (!f) return badName(res);
        const b = await db.query('select public from storage.buckets where id=$1', [bucket]); if (!b.rowCount || !b.rows[0].public) return send(res, 404, { error: 'not found' });
        const o = await db.query("select metadata from storage.objects where bucket_id=$1 and name=$2", [bucket, name]);
        if (!o.rowCount || !fs.existsSync(f)) return send(res, 404, { error: 'not found' });
        const size = fs.statSync(f).size, type = (o.rows[0].metadata || {}).mimetype || 'application/octet-stream', rg = range(req, size);
        if (rg === 416) return send(res, 416, { error: 'Range Not Satisfiable' }, { 'content-range': `bytes */${size}` });
        const h = { ...cors, ...SEC, 'content-type': type, 'accept-ranges': 'bytes' };
        return rg ? stream(res, f, 206, { ...h, 'content-range': `bytes ${rg.start}-${rg.end}/${size}`, 'content-length': rg.end - rg.start + 1 }, rg) : stream(res, f, 200, { ...h, 'content-length': size });
      }

      /* signed links for private files: issued only if the user may read the object (policies decide), valid for expiresIn seconds */
      if (rest.startsWith('sign/')) {
        const tail = rest.slice(5), parts = tail.split('/'), bucket = parts[0], name = parts.slice(1).join('/');
        const mk = (n, exp) => { const payload = Buffer.from(JSON.stringify({ b: bucket, n, exp })).toString('base64url'); return payload + '.' + crypto.createHmac('sha256', SECRET).update(payload).digest('base64url'); };
        if (req.method === 'GET') {
          const f = objFile(bucket, name); if (!f) return badName(res);
          const tok = url.searchParams.get('token') || '', [pl, sg] = tok.split('.');
          if (!pl || !sg || crypto.createHmac('sha256', SECRET).update(pl).digest('base64url') !== sg) return send(res, 400, { error: 'Invalid signature' });
          const t = JSON.parse(Buffer.from(pl, 'base64url')); if (t.b !== bucket || t.n !== name || t.exp < Date.now() / 1000) return send(res, 400, { error: 'Link expired' });
          const o = await db.query('select metadata from storage.objects where bucket_id=$1 and name=$2', [bucket, name]);
          if (!o.rowCount || !fs.existsSync(f)) return send(res, 404, { error: 'not found' });
          return stream(res, f, 200, { ...cors, ...SEC, 'content-type': (o.rows[0].metadata || {}).mimetype || 'application/octet-stream', 'content-length': fs.statSync(f).size });
        }
        if (req.method === 'POST') {
          const cl = verify(bearer(req)); if (!cl) return send(res, 401, { error: 'Sign in first', statusCode: '401' });
          const body = await readBody(req), exp = Math.floor(Date.now() / 1000) + Math.min(+body.expiresIn || 3600, 7 * 86400);
          const names = (name ? [name] : (body.paths || [])).map(String);
          const c = await db.connect(); let seen = [];
          try { await c.query('begin'); await claimsAs(c, cl);
            seen = (await c.query('select name from storage.objects where bucket_id=$1 and name = any($2)', [bucket, names])).rows.map(r => r.name); await c.query('commit'); }
          catch (e) { await c.query('rollback').catch(() => {}); } finally { c.release(); }
          const out = names.map(n => seen.includes(n) && objFile(bucket, n) ? { path: n, signedURL: `/object/sign/${bucket}/${n}?token=${mk(n, exp)}`, error: null } : { path: n, signedURL: null, error: 'Either the object does not exist or you do not have access to it' });
          if (name) return out[0].error ? send(res, 400, { error: out[0].error, statusCode: '400' }) : send(res, 200, { signedURL: out[0].signedURL });
          return send(res, 200, out);
        }
      }
      const claims = verify(bearer(req)); if (!claims || claims.role !== 'authenticated') return send(res, 401, { error: 'Sign in first', statusCode: '401' });
      const asUser = async (fn) => { const c = await db.connect(); try { await c.query('begin'); await claimsAs(c, claims); const out = await fn(c); await c.query('commit'); return out; } catch (e) { await c.query('rollback').catch(() => {}); throw e; } finally { c.release(); } };
      if (req.method === 'DELETE') { const bucket = rest.split('/')[0], body = await readBody(req), names = (body.prefixes || []).map(String);
        if (names.some(n => !objFile(bucket, n))) return badName(res);
        try { const gone = await asUser(c => c.query('delete from storage.objects where bucket_id=$1 and name = any($2) returning name', [bucket, names]));
          gone.rows.forEach(r => { const f = objFile(bucket, r.name); if (f) try { fs.unlinkSync(f); } catch {} }); return send(res, 200, gone.rows.map(r => ({ name: r.name }))); }
        catch (e) { return send(res, 403, { error: e.message, statusCode: '403' }); } }
      if (req.method === 'POST' || req.method === 'PUT') {
        const [bucket, ...pp] = rest.split('/'), name = pp.join('/'), upsert = req.method === 'PUT' || /true/i.test(req.headers['x-upsert'] || ''), f = objFile(bucket, name);
        if (!f) return badName(res);
        const raw = await readRaw(req);
        let data = raw, type = req.headers['content-type'] || 'application/octet-stream';
        const mb = /multipart\/form-data;\s*boundary=(.+)$/i.exec(type);
        if (mb) { const bnd = Buffer.from('--' + mb[1]); let i = raw.indexOf(bnd); while (i >= 0) { const j = raw.indexOf(bnd, i + bnd.length); if (j < 0) break;
            const part = raw.slice(i + bnd.length + 2, j - 2), h = part.indexOf('\r\n\r\n'), head = part.slice(0, h).toString();
            if (/filename=/i.test(head)) { data = part.slice(h + 4); type = (/content-type:\s*([^\r\n]+)/i.exec(head) || [])[1] || 'application/octet-stream'; break; } i = j; } }
        const b = await db.query('select file_size_limit, allowed_mime_types from storage.buckets where id=$1', [bucket]); if (!b.rowCount) return send(res, 404, { error: 'Bucket not found', statusCode: '404' });
        if (b.rows[0].file_size_limit && data.length > +b.rows[0].file_size_limit) return send(res, 413, { error: 'The object exceeded the maximum allowed size', statusCode: '413' });
        if (b.rows[0].allowed_mime_types && !b.rows[0].allowed_mime_types.includes(type)) return send(res, 415, { error: 'mime type ' + type + ' is not supported', statusCode: '415' });
        /* as Supabase Storage: an upsert is INSERT … ON CONFLICT DO UPDATE, so the bucket's UPDATE policy decides a replace */
        try { await asUser(c => c.query('insert into storage.objects (bucket_id, name, owner, metadata) values ($1,$2,$3,$4)' + (upsert ? ' on conflict (bucket_id, name) do update set owner = excluded.owner, metadata = excluded.metadata, created_at = now()' : ''), [bucket, name, claims.sub, { mimetype: type, size: data.length }])); }
        catch (e) { return send(res, /duplicate/.test(e.message) ? 409 : 403, { error: /row-level security/.test(e.message) ? 'new row violates row-level security policy' : e.message, statusCode: /duplicate/.test(e.message) ? '409' : '403' }); }
        fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, data);
        return send(res, 200, { Key: bucket + '/' + name });
      }
    }
    if (url.pathname.startsWith('/rest/v1/')) {                       // → PostgREST, same headers; the JWT decides the role
      if (!apikeyOk(req, res)) return;
      const target = REST + url.pathname.slice(8) + url.search, h = { ...req.headers }; delete h.host; delete h.apikey;
      if (!/^Bearer /i.test(h.authorization || '')) h.authorization = 'Bearer ' + req.headers.apikey;   // supabase-js sends the anon key as the bearer
      /* an expired or forged token is NOT downgraded to anon: PostgREST answers 401 (PGRST301), exactly as on Supabase */
      const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await readRaw(req);
      const up = await fetch(target, { method: req.method, headers: h, body }); const out = Buffer.from(await up.arrayBuffer());
      const hh = { ...cors, ...SEC }; up.headers.forEach((v, k) => { if (!['content-encoding', 'transfer-encoding', 'connection'].includes(k)) hh[k] = v; });
      res.writeHead(up.status, hh); return res.end(out);
    }
    send(res, 404, { error: 'not found' });
  } catch (e) { console.error(e); if (res.headersSent) return res.destroy(); send(res, 500, { error: String(e.message || e) }); }
}).listen(PORT, HOST, () => console.log(`local supabase on ${HOST}:${PORT}`));
/* the policies see the same request settings as on Supabase Storage: the user id and the whole claims object */
async function claimsAs(c, cl) {
  await c.query("select set_config('request.jwt.claim.sub',$1,true), set_config('request.jwt.claim.role','authenticated',true), set_config('request.jwt.claims',$2,true)", [cl.sub, JSON.stringify({ sub: cl.sub, role: 'authenticated', email: cl.email || null, aud: 'authenticated' })]);
  await c.query('set local role authenticated');
}
/* Range: bytes=a-b | a- | -n ; null = whole file, 416 = cannot be satisfied (start past the end, or start > end) */
function range(req, size) {
  const m = /^bytes=(\d*)-(\d*)$/.exec((req.headers.range || '').trim()); if (!m || (m[1] === '' && m[2] === '')) return null;
  let start, end;
  if (m[1] === '') { const n = +m[2]; if (!n) return 416; start = Math.max(0, size - n); end = size - 1; }
  else { start = +m[1]; end = m[2] === '' ? size - 1 : Math.min(+m[2], size - 1); }
  return start >= size || start > end ? 416 : { start, end };
}
