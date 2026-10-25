// Serves the Edge Functions locally (tests): /payments-create, /paymob-webhook, /fawry-webhook, /account-delete, /notify-email,
// /notify-dispatch, /sms-dispatch on one port. LOCAL_CRON_SECONDS stands in for the production schedule: notify-email is run that often with the service key.
import { handler as create } from '../../supabase/functions/payments-create/index.js';
import { handler as paymob } from '../../supabase/functions/paymob-webhook/index.js';
import { handler as fawry } from '../../supabase/functions/fawry-webhook/index.js';
import { handler as accountDelete } from '../../supabase/functions/account-delete/index.js';
import { handler as notifyEmail } from '../../supabase/functions/notify-email/index.js';
import { handler as notify } from '../../supabase/functions/notify-dispatch/index.js';
import { handler as sms } from '../../supabase/functions/sms-dispatch/index.js';
const routes = { 'payments-create': create, 'paymob-webhook': paymob, 'fawry-webhook': fawry, 'account-delete': accountDelete, 'notify-email': notifyEmail, 'notify-dispatch': notify, 'sms-dispatch': sms };
Deno.serve({ port: Number(Deno.env.get('FN_PORT') || 54400), hostname: '127.0.0.1' }, (req) => { const name = new URL(req.url).pathname.split('/').filter(Boolean).pop(); const h = routes[name]; return h ? h(req) : new Response('not found', { status: 404 }); });
const every = Number(Deno.env.get('LOCAL_CRON_SECONDS') || 0);
if (every > 0) setInterval(() => { notifyEmail(new Request('http://local/notify-email', { method: 'POST', headers: { Authorization: 'Bearer ' + Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') } })).catch((e) => console.error('notify-email', e)); }, every * 1000);
