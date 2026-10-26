// Web push without dependencies (Deno and Node 20+: WebCrypto only) — slice w-pwa.
// encrypt(): RFC 8291 message encryption (aes128gcm, one record) to a browser subscription (its p256dh key and auth secret);
// vapid(): RFC 8292 VAPID authorization (ES256 JWT signed with the server's key pair: VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY, base64url
// raw keys — 65-byte public point, 32-byte private scalar; tools/pwa/vapid_keys.mjs makes a pair). send() posts one message.
// Only addresses of the known push services are ever called (pushHostOk); PUSH_TEST_HOSTS adds a loopback stand-in for tests.
const te = new TextEncoder();
export const b64u = {
  enc: (b) => { let s = ''; for (const x of new Uint8Array(b)) s += String.fromCharCode(x); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); },
  dec: (s) => { const t = String(s).replace(/-/g, '+').replace(/_/g, '/'); const r = atob(t + '='.repeat((4 - (t.length % 4)) % 4)); return Uint8Array.from(r, (c) => c.charCodeAt(0)); },
};
const cat = (...a) => { const o = new Uint8Array(a.reduce((n, x) => n + x.length, 0)); let i = 0; for (const x of a) { o.set(x, i); i += x.length; } return o; };
async function hmac(key, data) { const k = await crypto.subtle.importKey('raw', key, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']); return new Uint8Array(await crypto.subtle.sign('HMAC', k, data)); }

const HOSTS = ['fcm.googleapis.com', 'push.services.mozilla.com', 'push.apple.com', 'notify.windows.com'];   // = private.push_hosts (0110)
export function pushHostOk(endpoint, testHosts) {
  let u; try { u = new URL(endpoint); } catch { return false; }
  const h = u.hostname.toLowerCase(), extra = String(testHosts || '').split(',').map((x) => x.trim().toLowerCase()).filter(Boolean);
  if (u.protocol === 'https:' && HOSTS.some((x) => h === x || h.endsWith('.' + x))) return true;
  return extra.includes(h) && (h === '127.0.0.1' || h === 'localhost');                              // tests only: a loopback stand-in
}

export async function encrypt(sub, payload) {
  const ua = b64u.dec(sub.p256dh), secret = b64u.dec(sub.auth);
  if (ua.length !== 65 || ua[0] !== 4 || secret.length !== 16) throw new Error('invalid subscription keys');
  const as = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const asPub = new Uint8Array(await crypto.subtle.exportKey('raw', as.publicKey));
  const uaKey = await crypto.subtle.importKey('raw', ua, { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const ecdh = new Uint8Array(await crypto.subtle.deriveBits({ name: 'ECDH', public: uaKey }, as.privateKey, 256));
  const ikm = await hmac(await hmac(secret, ecdh), cat(te.encode('WebPush: info\0'), ua, asPub, new Uint8Array([1])));
  const salt = crypto.getRandomValues(new Uint8Array(16)), prk = await hmac(salt, ikm);
  const cek = (await hmac(prk, cat(te.encode('Content-Encoding: aes128gcm\0'), new Uint8Array([1])))).slice(0, 16);
  const nonce = (await hmac(prk, cat(te.encode('Content-Encoding: nonce\0'), new Uint8Array([1])))).slice(0, 12);
  const body = typeof payload === 'string' ? te.encode(payload) : new Uint8Array(payload);
  if (body.length > 3800) throw new Error('push payload too large');
  const key = await crypto.subtle.importKey('raw', cek, 'AES-GCM', false, ['encrypt']);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, key, cat(body, new Uint8Array([2]))));   // 0x02: the last record
  const rs = new Uint8Array([0, 0, 16, 0]);                                                            // record size 4096
  return cat(salt, rs, new Uint8Array([65]), asPub, ct);
}

const signers = new Map();
async function signer(pub, priv) {
  const id = pub + '.' + priv; if (signers.has(id)) return signers.get(id);
  const p = b64u.dec(pub), d = b64u.dec(priv);
  if (p.length !== 65 || p[0] !== 4 || d.length !== 32) throw new Error('VAPID keys are not a P-256 key pair (base64url: 65-byte public, 32-byte private)');
  const k = await crypto.subtle.importKey('jwk', { kty: 'EC', crv: 'P-256', d: priv, x: b64u.enc(p.slice(1, 33)), y: b64u.enc(p.slice(33)), ext: false }, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  signers.set(id, k); return k;
}
export async function vapid(endpoint, keys, now = Date.now()) {
  const aud = new URL(endpoint).origin, sub = String(keys.subject || '');
  if (!/^(mailto:[^\s@]+@[^\s@]+|https:\/\/\S+)$/.test(sub)) throw new Error('VAPID_SUBJECT must be mailto:<address> or an https URL');
  const h = b64u.enc(te.encode(JSON.stringify({ typ: 'JWT', alg: 'ES256' })));
  const c = b64u.enc(te.encode(JSON.stringify({ aud, exp: Math.floor(now / 1000) + 12 * 3600, sub })));
  const sig = new Uint8Array(await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, await signer(keys.publicKey, keys.privateKey), te.encode(h + '.' + c)));
  return `vapid t=${h}.${c}.${b64u.enc(sig)}, k=${keys.publicKey}`;
}

// one message to one device → { ok, gone, status }. gone: the service no longer knows the device (404/410) — remove it.
export async function send(sub, payload, keys, opts = {}) {
  if (!pushHostOk(sub.endpoint, opts.testHosts)) return { ok: false, gone: false, status: 0, error: 'not a known push service' };
  const body = await encrypt(sub, payload);
  const headers = { Authorization: await vapid(sub.endpoint, keys), 'Content-Encoding': 'aes128gcm', 'Content-Type': 'application/octet-stream',
                    TTL: String(opts.ttl ?? 86400), Urgency: opts.urgency || 'normal' };
  if (opts.topic && /^[A-Za-z0-9_-]{1,32}$/.test(opts.topic)) headers.Topic = opts.topic;               // a newer message of the same topic replaces it
  const r = await fetch(sub.endpoint, { method: 'POST', headers, body, redirect: 'manual', signal: AbortSignal.timeout(opts.timeoutMs || 10000) });
  const text = r.ok ? '' : (await r.text().catch(() => '')).slice(0, 200);
  return { ok: r.status >= 200 && r.status < 300, gone: r.status === 404 || r.status === 410, status: r.status, error: r.ok ? '' : `push service answered ${r.status}: ${text}` };
}
