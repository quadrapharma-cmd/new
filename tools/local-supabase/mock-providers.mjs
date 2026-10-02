// Test stand-in for Paymob and FawryPay: records requests, checks Fawry's charge signature, answers like the real APIs.
import http from 'node:http'; import crypto from 'node:crypto';
const LOG = [], PORT = +(process.env.MOCK_PORT || 54500), FKEY = process.env.FAWRY_SECURE_KEY, PSECRET = process.env.PAYMOB_SECRET_KEY;
http.createServer((req, res) => { let d = ''; req.on('data', c => d += c); req.on('end', () => {
  const send = (s, b) => { res.writeHead(s, { 'content-type': 'application/json' }); res.end(JSON.stringify(b)); }; let b = {}; try { b = d ? JSON.parse(d) : {}; } catch {}
  if (req.url === '/log') return send(200, LOG);
  LOG.push({ path: req.url, auth: req.headers.authorization || '', body: b });
  if (req.url === '/v1/intention/') { if (req.headers.authorization !== 'Token ' + PSECRET) return send(401, { detail: 'bad key' });
    return send(201, { id: 'pi_' + Date.now(), client_secret: 'egy_csk_' + crypto.randomBytes(8).toString('hex'), intention_order_id: 900000 + LOG.length }); }
  if (req.url === '/ECommerceWeb/Fawry/payments/charge') {
    const want = crypto.createHash('sha256').update(b.merchantCode + b.merchantRefNum + (b.customerProfileId || '') + b.paymentMethod + b.amount + FKEY).digest('hex');
    if (want !== b.signature) return send(200, { statusCode: 9946, statusDescription: 'Invalid signature' });
    return send(200, { type: 'ChargeResponse', referenceNumber: String(900000000 + LOG.length), merchantRefNumber: b.merchantRefNum, orderAmount: +b.amount, paymentAmount: +b.amount, orderStatus: 'UNPAID', paymentMethod: 'PAYATFAWRY', statusCode: 200 }); }
  send(404, { error: 'not found' }); }); }).listen(PORT);
