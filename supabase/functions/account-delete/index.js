// POST { password, confirm: "DELETE" }  (Authorization: Bearer <member JWT>) — Settings → Delete my account (X-01).
// 1. as the member: account_delete_begin checks the password and the word, and lists the member's files;
// 2. as the server: the files go through the Storage API (a row deleted in SQL would leave the file in the bucket);
// 3. as the server: account_anonymise deletes the member's rows and turns the profile into the "Deleted member" tombstone;
// 4. as the server: the sign-in is removed with GoTrue's soft delete (the e-mail is freed, sessions end; the auth row stays,
//    so the tombstone profile and the other person's messages stay).
import { rpc, env } from '../_shared/db.js';
const origins = () => (env('ALLOWED_ORIGINS') || env('APP_URL') || '').split(',').map((u) => { try { return new URL(u.trim()).origin; } catch { return ''; } }).filter(Boolean);
export async function handler(req) {
  const origin = req.headers.get('origin'), cors = { 'Access-Control-Allow-Headers': 'authorization, apikey, content-type', 'Access-Control-Allow-Methods': 'POST, OPTIONS', Vary: 'Origin' };
  if (origin && origins().includes(origin)) cors['Access-Control-Allow-Origin'] = origin;
  const json = (b, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...cors, 'Content-Type': 'application/json' } });
  if (origin && !cors['Access-Control-Allow-Origin']) return json({ error: 'Origin not allowed' }, 403);
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
  if (req.method !== 'POST') return json({ error: 'POST only' }, 405);
  const jwt = (req.headers.get('authorization') || '').replace(/^Bearer /i, ''); if (!jwt) return json({ error: 'Sign in first' }, 401);
  let b; try { b = await req.json(); } catch { return json({ error: 'Bad request' }, 400); }
  const url = env('SUPABASE_URL'), service = env('SUPABASE_SERVICE_ROLE_KEY'), anon = env('SUPABASE_ANON_KEY');
  let begun;
  try { begun = await rpc('account_delete_begin', { p_password: String(b.password || ''), p_confirm: String(b.confirm || '') }, jwt); }
  catch (e) { return json({ error: e.message }, e.status === 401 ? 401 : 400); }
  const uid = begun && begun.user; if (!uid) return json({ error: 'Sign in first' }, 401);
  const byBucket = {};
  for (const f of begun.files || []) (byBucket[f.bucket] = byBucket[f.bucket] || []).push(f.name);
  for (const [bucket, names] of Object.entries(byBucket)) {
    for (let i = 0; i < names.length; i += 100) {
      const r = await fetch(`${url}/storage/v1/object/${bucket}`, { method: 'DELETE', headers: { apikey: anon, Authorization: `Bearer ${service}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ prefixes: names.slice(i, i + 100) }) });
      if (!r.ok) return json({ error: 'Your files could not be removed — nothing was deleted, please try again' }, 502);
    }
  }
  try { await rpc('account_anonymise', { p_user: uid }); } catch (e) { return json({ error: 'The account could not be deleted — please try again' }, 500); }
  const d = await fetch(`${url}/auth/v1/admin/users/${uid}`, { method: 'DELETE', headers: { apikey: service, Authorization: `Bearer ${service}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ should_soft_delete: true }) });
  if (!d.ok) return json({ error: 'Your data was deleted but the sign-in could not be removed — Drugbox will finish it' }, 502);
  return json({ deleted: true, files: (begun.files || []).length });
}
if (import.meta.main) Deno.serve(handler);
