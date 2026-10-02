// Minimal PostgREST calls (no dependencies). As the user: their JWT, so row-level security and auth.uid() apply.
// As the server: the service-role key, used only for confirm_payment / set_order_provider_ref.
const env = (k, d) => (globalThis.Deno ? Deno.env.get(k) : process.env[k]) ?? d;
export const cfg = () => ({ url: env('SUPABASE_URL'), anon: env('SUPABASE_ANON_KEY'), service: env('SUPABASE_SERVICE_ROLE_KEY') });
export async function rpc(name, args, jwt) {
  const c = cfg(); const r = await fetch(`${c.url}/rest/v1/rpc/${name}`, { method: 'POST', headers: { apikey: c.anon, Authorization: `Bearer ${jwt || c.service}`, 'Content-Type': 'application/json' }, body: JSON.stringify(args) });
  const t = await r.text(); let j = null; try { j = t ? JSON.parse(t) : null; } catch { j = t; }
  if (!r.ok) throw Object.assign(new Error((j && (j.message || j.error)) || `rpc ${name} failed`), { status: r.status });
  return j;
}
export async function select(path, jwt) {
  const c = cfg(); const r = await fetch(`${c.url}/rest/v1/${path}`, { headers: { apikey: c.anon, Authorization: `Bearer ${jwt || c.service}` } });
  if (!r.ok) throw new Error(`select ${path} failed`); return r.json();
}
export { env };
