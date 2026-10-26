// A VAPID key pair for web push (w-pwa): node tools/pwa/vapid_keys.mjs [--env]
// Prints the PUBLIC key (→ DRUGBOX_VAPID_PUBLIC_KEY for web/build/live.py, and the VAPID_PUBLIC_KEY function secret) and the PRIVATE
// key (→ the VAPID_PRIVATE_KEY function secret ONLY: never in git, never in the browser build). Make it once per project and keep it:
// a new pair makes every device's subscription useless (members would switch notifications on again).
const k = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
const pub = Buffer.from(await crypto.subtle.exportKey('raw', k.publicKey)).toString('base64url');
const priv = (await crypto.subtle.exportKey('jwk', k.privateKey)).d;
if (process.argv.includes('--env')) console.log(`VAPID_PUBLIC_KEY=${pub}\nVAPID_PRIVATE_KEY=${priv}`);
else console.log(`public  (DRUGBOX_VAPID_PUBLIC_KEY and the VAPID_PUBLIC_KEY secret): ${pub}\nprivate (the VAPID_PRIVATE_KEY secret only):                   ${priv}`);
