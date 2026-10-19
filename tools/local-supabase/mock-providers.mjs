// Test stand-in for Paymob, FawryPay and the e-mail provider (Resend's API): records requests, checks Fawry's charge signature, answers like the real APIs.
import http from 'node:http'; import crypto from 'node:crypto';
const LOG = [], CTL = { fawry_fail: 0, paymob_fail: 0 }, PORT = +(process.env.MOCK_PORT || 54500), FKEY = process.env.FAWRY_SECURE_KEY, PSECRET = process.env.PAYMOB_SECRET_KEY, EKEY = process.env.EMAIL_API_KEY;
http.createServer((req, res) => { let d = ''; req.on('data', c => d += c); req.on('end', () => {
  const send = (s, b) => { res.writeHead(s, { 'content-type': 'application/json' }); res.end(JSON.stringify(b)); }; let b = {}; try { b = d ? JSON.parse(d) : {}; } catch {}
  if (req.url === '/log') return send(200, LOG);
  if (req.url === '/control' && req.method === 'POST') { Object.assign(CTL, b); return send(200, CTL); }   // tests: make the next N charges fail like a provider outage
  LOG.push({ path: req.url, auth_ok: req.url === '/v1/intention/' ? req.headers.authorization === 'Token ' + PSECRET : req.url === '/emails' ? req.headers.authorization === 'Bearer ' + EKEY : true, body: b });   // never the secret itself
  if (req.url === '/v1/intention/') { if (req.headers.authorization !== 'Token ' + PSECRET) return send(401, { detail: 'bad key' });
    if (CTL.paymob_fail > 0) { CTL.paymob_fail--; return send(500, { detail: 'temporarily unavailable' }); }
    return send(201, { id: 'pi_' + Date.now(), client_secret: 'egy_csk_' + crypto.randomBytes(8).toString('hex'), intention_order_id: 900000 + LOG.length }); }
  if (req.url === '/emails') { if (!EKEY || req.headers.authorization !== 'Bearer ' + EKEY) return send(401, { message: 'bad key' });
    if (String(b.to && b.to[0]).includes('bounce')) return send(422, { message: 'invalid recipient' });   // a provider refusal, for the retry path
    return send(200, { id: 'em_' + LOG.length }); }
  if (req.url === '/ECommerceWeb/Fawry/payments/charge') {
    const want = crypto.createHash('sha256').update(b.merchantCode + b.merchantRefNum + (b.customerProfileId || '') + b.paymentMethod + b.amount + FKEY).digest('hex');
    if (want !== b.signature) return send(200, { statusCode: 9946, statusDescription: 'Invalid signature' });
    if (!/^01\d{9}$/.test(String(b.customerMobile || ''))) return send(200, { statusCode: 9901, statusDescription: 'customerMobile is required for PAYATFAWRY' });   // like FawryPay: a reference needs the payer's mobile
    if (CTL.fawry_fail > 0) { CTL.fawry_fail--; return send(200, { statusCode: 9999, statusDescription: 'Service temporarily unavailable' }); }
    return send(200, { type: 'ChargeResponse', referenceNumber: String(900000000 + LOG.length), merchantRefNumber: b.merchantRefNum, orderAmount: +b.amount, paymentAmount: +b.amount, orderStatus: 'UNPAID', paymentMethod: 'PAYATFAWRY', statusCode: 200 }); }
  send(404, { error: 'not found' }); }); }).listen(PORT, '127.0.0.1');   // loopback only
