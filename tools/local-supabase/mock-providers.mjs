// Test stand-in for Paymob and FawryPay: records requests, checks Fawry's charge signature, answers like the real APIs.
import http from 'node:http'; import crypto from 'node:crypto';
// order and reference numbers keep growing across restarts of the stand-in (the database keeps the earlier ones, and they are unique there)
const SEQ0 = Math.floor(Date.now() / 1000) * 1000;
const LOG = [], PORT = +(process.env.MOCK_PORT || 54500), FKEY = process.env.FAWRY_SECURE_KEY, PSECRET = process.env.PAYMOB_SECRET_KEY;
http.createServer((req, res) => { let d = ''; req.on('data', c => d += c); req.on('end', () => {
  const send = (s, b) => { res.writeHead(s, { 'content-type': 'application/json' }); res.end(JSON.stringify(b)); }; let b = {}; try { b = d ? JSON.parse(d) : {}; } catch {}
  if (req.url === '/log') return send(200, LOG);
  LOG.push({ path: req.url, auth_ok: req.url !== '/v1/intention/' || req.headers.authorization === 'Token ' + PSECRET, body: b });   // never the secret itself
  if (req.url === '/v1/intention/') { if (req.headers.authorization !== 'Token ' + PSECRET) return send(401, { detail: 'bad key' });
    return send(201, { id: 'pi_' + Date.now(), client_secret: 'egy_csk_' + crypto.randomBytes(8).toString('hex'), intention_order_id: SEQ0 + LOG.length }); }
  if (req.url === '/ECommerceWeb/Fawry/payments/charge') {
    const want = crypto.createHash('sha256').update(b.merchantCode + b.merchantRefNum + (b.customerProfileId || '') + b.paymentMethod + b.amount + FKEY).digest('hex');
    if (want !== b.signature) return send(200, { statusCode: 9946, statusDescription: 'Invalid signature' });
    return send(200, { type: 'ChargeResponse', referenceNumber: '9' + (SEQ0 + LOG.length), merchantRefNumber: b.merchantRefNum, orderAmount: +b.amount, paymentAmount: +b.amount, orderStatus: 'UNPAID', paymentMethod: 'PAYATFAWRY', statusCode: 200 }); }
  send(404, { error: 'not found' }); }); }).listen(PORT, '127.0.0.1');   // loopback only
