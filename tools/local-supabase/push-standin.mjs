// Test stand-in for a browser push service (w-pwa), loopback only: POST /push/<id> records what the server sent (headers + the encrypted
// body, base64) and checks the VAPID authorization against VAPID_PUBLIC_KEY (ES256 signature, audience = this origin, expiry);
// ids starting with "gone" answer 410 and "missing" 404 (a device the service no longer knows). GET /push/log[?id=<id>] lists them.
import http from 'node:http'; import crypto from 'node:crypto';
const PORT = +(process.env.PUSH_PORT || 54600), PUB = process.env.VAPID_PUBLIC_KEY || '', LOG = [];
function vapidOk(auth, origin) {
  const m = /^vapid t=([\w-]+)\.([\w-]+)\.([\w-]+), k=([\w-]+)$/.exec(auth || ''); if (!m || m[4] !== PUB) return false;
  try {
    const p = Buffer.from(PUB, 'base64url'), key = crypto.createPublicKey({ key: { kty: 'EC', crv: 'P-256', x: p.subarray(1, 33).toString('base64url'), y: p.subarray(33).toString('base64url') }, format: 'jwk' });
    const okSig = crypto.verify('sha256', Buffer.from(m[1] + '.' + m[2]), { key, dsaEncoding: 'ieee-p1363' }, Buffer.from(m[3], 'base64url'));
    const c = JSON.parse(Buffer.from(m[2], 'base64url')); return okSig && c.aud === origin && c.exp * 1000 > Date.now() && c.exp * 1000 < Date.now() + 25 * 3600e3 && /^(mailto:|https:)/.test(c.sub);
  } catch { return false; }
}
http.createServer((req, res) => { const c = []; req.on('data', (d) => c.push(d)); req.on('end', () => {
  const u = new URL(req.url, `http://127.0.0.1:${PORT}`), send = (s, b) => { res.writeHead(s, { 'content-type': 'application/json' }); res.end(JSON.stringify(b)); };
  if (req.method === 'GET' && u.pathname === '/push/log') return send(200, LOG.filter((x) => !u.searchParams.get('id') || x.id === u.searchParams.get('id')));
  const m = /^\/push\/([\w-]{1,80})$/.exec(u.pathname); if (!m || req.method !== 'POST') return send(404, { error: 'not found' });
  const id = m[1], entry = { id, at: new Date().toISOString(), vapid_ok: vapidOk(req.headers.authorization, u.origin), encoding: req.headers['content-encoding'] || '',
    ttl: req.headers.ttl || '', urgency: req.headers.urgency || '', body: Buffer.concat(c).toString('base64') };
  LOG.push(entry); if (LOG.length > 1000) LOG.shift();
  if (id.startsWith('gone')) return send(410, { error: 'expired' });
  if (id.startsWith('missing')) return send(404, { error: 'no such subscription' });
  if (!entry.vapid_ok) return send(403, { error: 'bad vapid' });
  res.writeHead(201, { location: u.pathname }); res.end();
}); }).listen(PORT, '127.0.0.1');
