// Serves the Edge Functions locally (tests): /payments-create, /paymob-webhook, /fawry-webhook on one port.
import { handler as create } from '../../supabase/functions/payments-create/index.js';
import { handler as paymob } from '../../supabase/functions/paymob-webhook/index.js';
import { handler as fawry } from '../../supabase/functions/fawry-webhook/index.js';
const routes = { 'payments-create': create, 'paymob-webhook': paymob, 'fawry-webhook': fawry };
Deno.serve({ port: Number(Deno.env.get('FN_PORT') || 54400), hostname: '127.0.0.1' }, (req) => { const name = new URL(req.url).pathname.split('/').filter(Boolean).pop(); const h = routes[name]; return h ? h(req) : new Response('not found', { status: 404 }); });
