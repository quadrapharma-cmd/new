-- ═════════════════════════════════════════════════════════════════════
-- 0101 — Founding members (AREA w-growth: W-42, the owner's growth plan instead of fake members)
--   Invite-only early access. A Drugbox admin makes an invitation for one segment of the trade; the code is long and random
--   (120 bits), shown ONCE to the admin and stored only as its SHA-256; it works once, until it expires or is revoked.
--   Joining is the invitee's own choice: they open the link, sign in or sign up, and press Join (founder_redeem) — nobody is
--   made a founder by anyone else. A founder gets the founder badge (founder_members, public) and 3 months of VIP for a
--   company page they run (founder_apply_vip — once, within a year of joining; VIP is a company plan, 0018/0023).
--   Quotas by segment (founder_segments), with NO pharmacy / "Rx traders" segment (owner: Drugbox trade is business to
--   business before the pharmacy): manufacturers, toll manufacturers / brand owners, agencies, distributors,
--   registration-file owners, API suppliers, packaging suppliers, regulatory consultants — changed by Drugbox admins only.
--   An invitation counts against its segment while it can still be used; redeeming re-checks the quota under a lock.
--   Ten wrong codes in an hour block further tries for that account (guessing).
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

create table if not exists public.founder_segments (
  key       text primary key,
  label_en  text not null,
  label_ar  text not null,
  quota     int not null check (quota between 0 and 1000),
  sort      int not null default 0
);
alter table public.founder_segments enable row level security;
drop policy if exists "founder segments: members read" on public.founder_segments;
create policy "founder segments: members read" on public.founder_segments for select to authenticated using (true);
revoke all on table public.founder_segments from public, anon, authenticated, service_role;
grant select on table public.founder_segments to anon, authenticated;              -- anon: no policy → empty (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.founder_segments to service_role;
insert into public.founder_segments (key, label_en, label_ar, quota, sort) values
  ('manufacturer',   'Manufacturers',                      'مصانع',                          8, 1),
  ('toll_brand',     'Toll manufacturers / brand owners',  'تصنيع لدى الغير / أصحاب براند',   10, 2),
  ('agency',         'Agencies',                           'وكالات',                         15, 3),
  ('distributor',    'Distributors / warehouses',          'موزّعين / مخازن',                 15, 4),
  ('file_owner',     'Registration-file owners',           'أصحاب ملفات تسجيل',              5, 5),
  ('api',            'API / excipient suppliers',          'موردي خامات',                    5, 6),
  ('packaging',      'Packaging suppliers',                'موردي عبوات وتغليف',             10, 7),
  ('regulatory',     'Regulatory consultants',             'استشاريين تسجيل',                5, 8)
on conflict (key) do nothing;

create table if not exists public.founder_invites (
  id          bigint generated always as identity primary key,
  code_hash   bytea not null unique,                         -- sha256 of the code; the code itself is never stored
  code_hint   text not null,                                 -- its last 4 characters, so the admin can tell invitations apart
  segment     text not null references public.founder_segments(key),
  note        text check (length(note) <= 200),               -- who it is for (the admin's own note)
  created_by  uuid references public.profiles(id) on delete set null,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null,
  revoked_at  timestamptz,
  used_by     uuid unique references public.profiles(id) on delete set null,
  used_at     timestamptz
);
create index if not exists idx_founder_invites_segment on public.founder_invites (segment);
create index if not exists idx_founder_invites_created_by on public.founder_invites (created_by) where created_by is not null;
create index if not exists idx_founder_invites_list on public.founder_invites (created_at desc);
alter table public.founder_invites enable row level security;
drop policy if exists "founder invites: Drugbox admins read" on public.founder_invites;
create policy "founder invites: Drugbox admins read" on public.founder_invites for select to authenticated using (public.is_platform_admin());
revoke all on table public.founder_invites from public, anon, authenticated, service_role;
grant select (id, code_hint, segment, note, created_by, created_at, expires_at, revoked_at, used_by, used_at) on table public.founder_invites to authenticated;  -- never the hash
grant select, insert, update, delete, truncate, references, trigger on table public.founder_invites to service_role;
revoke all on sequence public.founder_invites_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.founder_invites_id_seq to service_role;

create table if not exists public.founder_members (
  user_id         uuid primary key references public.profiles(id) on delete cascade,
  segment         text not null references public.founder_segments(key),
  invite_id       bigint unique references public.founder_invites(id) on delete set null,
  joined_at       timestamptz not null default now(),
  vip_company_id  bigint references public.companies(id) on delete set null,
  vip_applied_at  timestamptz
);
create index if not exists idx_founder_members_segment on public.founder_members (segment);
create index if not exists idx_founder_members_company on public.founder_members (vip_company_id) where vip_company_id is not null;
alter table public.founder_members enable row level security;
drop policy if exists "founder members: the badge is public to members" on public.founder_members;
create policy "founder members: the badge is public to members" on public.founder_members for select to authenticated using (true);
revoke all on table public.founder_members from public, anon, authenticated, service_role;
grant select (user_id, segment, joined_at) on table public.founder_members to authenticated;     -- the badge; which invitation / company is the founder's own business
grant select (user_id) on table public.founder_members to anon;                                  -- no policy for anon → empty (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.founder_members to service_role;

create table if not exists private.founder_attempts (
  user_id  uuid not null,
  at       timestamptz not null default now()
);
create index if not exists idx_founder_attempts on private.founder_attempts (user_id, at desc);
revoke all on table private.founder_attempts from public, anon, authenticated, service_role;
grant select, insert, delete on table private.founder_attempts to service_role;

-- the code as typed: letters and digits only, upper case (people copy it with spaces or dashes)
create or replace function private.founder_code_norm(p text) returns text language sql immutable as $$
  select upper(regexp_replace(coalesce(p, ''), '[^A-Za-z0-9]', '', 'g'))
$$;
revoke all on function private.founder_code_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.founder_code_norm(text) to service_role;

-- invitations still counting against a segment: used, or still usable (not revoked, not expired)
create or replace function private.founder_taken(p_segment text) returns int language sql stable security definer set search_path = public as $$
  select count(*)::int from public.founder_invites i
   where i.segment = p_segment and (i.used_by is not null or (i.revoked_at is null and i.expires_at > now()))
$$;
revoke all on function private.founder_taken(text) from public, anon, authenticated, service_role;
grant execute on function private.founder_taken(text) to service_role;

-- Admin → Founders: a new invitation. Returns the code once (format DBX-XXXX-XXXX-XXXX-XXXX-XXXX; Crockford-style letters).
create or replace function public.founder_invite_create(p_segment text, p_note text default null, p_days int default 60)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare q int; code text := ''; b bytea := gen_random_bytes(24); alpha text := '0123456789ABCDEFGHJKMNPQRSTVWXYZ'; v_id bigint; d int := coalesce(p_days, 60);
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin invites founding members' using errcode = '42501'; end if;
  if d < 1 or d > 365 then raise exception 'An invitation lasts 1 to 365 days' using errcode = '22023'; end if;
  if length(coalesce(p_note, '')) > 200 then raise exception 'The note is at most 200 characters' using errcode = '22023'; end if;
  select quota into q from public.founder_segments where key = p_segment for update;
  if q is null then raise exception 'Pick a segment' using errcode = '22023'; end if;
  if private.founder_taken(p_segment) >= q then raise exception 'This segment is full (% of %)', q, q using errcode = '23514'; end if;
  for i in 0..19 loop code := code || substr(alpha, (get_byte(b, i) % 32) + 1, 1); end loop;          -- 20 × 5 bits = 100 bits
  insert into public.founder_invites (code_hash, code_hint, segment, note, created_by, expires_at)
  values (digest(code, 'sha256'), right(code, 4), p_segment, nullif(trim(coalesce(p_note, '')), ''), auth.uid(), now() + make_interval(days => d))
  returning founder_invites.id into v_id;
  return jsonb_build_object('id', v_id, 'code', 'DBX-' || substr(code, 1, 4) || '-' || substr(code, 5, 4) || '-' || substr(code, 9, 4) || '-' || substr(code, 13, 4) || '-' || substr(code, 17, 4),
                            'expires_at', now() + make_interval(days => d));
end $$;
revoke all on function public.founder_invite_create(text, text, int) from public, anon, authenticated, service_role;
grant execute on function public.founder_invite_create(text, text, int) to authenticated, service_role;

create or replace function public.founder_invite_revoke(p_id bigint) returns void
language plpgsql security definer set search_path = public as $$
declare u uuid; r timestamptz;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin revokes invitations' using errcode = '42501'; end if;
  select used_by, revoked_at into u, r from public.founder_invites where id = p_id for update;
  if not found then raise exception 'This invitation is gone' using errcode = 'P0002'; end if;
  if u is not null then raise exception 'This invitation was already used' using errcode = '55000'; end if;
  if r is null then update public.founder_invites set revoked_at = now() where id = p_id; end if;
end $$;
revoke all on function public.founder_invite_revoke(bigint) from public, anon, authenticated, service_role;
grant execute on function public.founder_invite_revoke(bigint) to authenticated, service_role;

create or replace function public.founder_segment_quota(p_segment text, p_quota int) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin changes the quotas' using errcode = '42501'; end if;
  if p_quota is null or p_quota < 0 or p_quota > 1000 then raise exception 'A quota is 0 to 1,000' using errcode = '22023'; end if;
  update public.founder_segments set quota = p_quota where key = p_segment;
  if not found then raise exception 'Pick a segment' using errcode = '22023'; end if;
end $$;
revoke all on function public.founder_segment_quota(text, int) from public, anon, authenticated, service_role;
grant execute on function public.founder_segment_quota(text, int) to authenticated, service_role;

-- Admin → Founders: each segment with its quota, founders joined and invitations still open
create or replace function public.founder_overview() returns table (key text, label_en text, label_ar text, quota int, joined int, open_invites int, sort int)
language sql stable security definer set search_path = public as $$
  select s.key, s.label_en, s.label_ar, s.quota,
         (select count(*)::int from public.founder_members m where m.segment = s.key),
         (select count(*)::int from public.founder_invites i where i.segment = s.key and i.used_by is null and i.revoked_at is null and i.expires_at > now()),
         s.sort
    from public.founder_segments s
   where public.is_platform_admin()
   order by s.sort
$$;
revoke all on function public.founder_overview() from public, anon, authenticated, service_role;
grant execute on function public.founder_overview() to authenticated, service_role;

create or replace function public.founder_invites_list(p_limit int default 200)
returns table (id bigint, code_hint text, segment text, note text, created_at timestamptz, expires_at timestamptz, revoked_at timestamptz,
               used_at timestamptz, used_by_name text, state text)
language sql stable security definer set search_path = public as $$
  select i.id, i.code_hint, i.segment, i.note, i.created_at, i.expires_at, i.revoked_at, i.used_at,
         (select p.name from public.profiles p where p.id = i.used_by),
         case when i.used_by is not null then 'used' when i.revoked_at is not null then 'revoked' when i.expires_at <= now() then 'expired' else 'open' end
    from public.founder_invites i
   where public.is_platform_admin()
   order by i.created_at desc, i.id desc
   limit least(greatest(coalesce(p_limit, 200), 1), 500)
$$;
revoke all on function public.founder_invites_list(int) from public, anon, authenticated, service_role;
grant execute on function public.founder_invites_list(int) to authenticated, service_role;

-- the invitee: what an invitation is for (before choosing to join). Counts as a try (guessing is blocked the same way).
create or replace function public.founder_invite_peek(p_code text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare me uuid := auth.uid(); i public.founder_invites; s public.founder_segments;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if (select count(*) from private.founder_attempts a where a.user_id = me and a.at > now() - interval '1 hour') >= 10 then
    raise exception 'Too many tries — wait an hour and open your invitation link again' using errcode = '54000'; end if;
  select * into i from public.founder_invites where code_hash = digest(private.founder_code_norm(regexp_replace(coalesce(p_code, ''), '^\s*DBX[-\s]*', '', 'i')), 'sha256');
  if not found then insert into private.founder_attempts (user_id) values (me); return jsonb_build_object('state', 'unknown'); end if;
  select * into s from public.founder_segments where key = i.segment;
  return jsonb_build_object('state', case when i.used_by = me then 'mine' when i.used_by is not null then 'used' when i.revoked_at is not null then 'revoked'
                                          when i.expires_at <= now() then 'expired' when exists (select 1 from public.founder_members m where m.user_id = me) then 'already' else 'open' end,
                            'segment', s.key, 'label_en', s.label_en, 'label_ar', s.label_ar, 'expires_at', i.expires_at);
end $$;
revoke all on function public.founder_invite_peek(text) from public, anon, authenticated, service_role;
grant execute on function public.founder_invite_peek(text) to authenticated, service_role;

-- the invitee joins (their own choice). Optionally gives the 3 VIP months to a company page they run.
-- A code that matches no invitation returns {"error": "invalid"} (counted as a try); every other refusal is an error.
create or replace function public.founder_redeem(p_code text, p_company bigint default null) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare me uuid := auth.uid(); i public.founder_invites; q int; vip jsonb := null;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if exists (select 1 from public.account_suspensions s where s.user_id = me) then raise exception 'This account is suspended' using errcode = '42501'; end if;
  if (select count(*) from private.founder_attempts a where a.user_id = me and a.at > now() - interval '1 hour') >= 10 then
    raise exception 'Too many tries — wait an hour and open your invitation link again' using errcode = '54000'; end if;
  select * into i from public.founder_invites where code_hash = digest(private.founder_code_norm(regexp_replace(coalesce(p_code, ''), '^\s*DBX[-\s]*', '', 'i')), 'sha256') for update;
  if not found then                       -- recorded, so not raised (an error would roll the record of the try back)
    insert into private.founder_attempts (user_id) values (me); return jsonb_build_object('error', 'invalid'); end if;
  if i.used_by = me then raise exception 'You are already a founding member' using errcode = '55000'; end if;
  if i.used_by is not null then raise exception 'This invitation was already used' using errcode = '55000'; end if;
  if i.revoked_at is not null then raise exception 'This invitation was withdrawn by Drugbox' using errcode = '55000'; end if;
  if i.expires_at <= now() then raise exception 'This invitation has expired — ask Drugbox for a new one' using errcode = '55000'; end if;
  if exists (select 1 from public.founder_members m where m.user_id = me) then raise exception 'You are already a founding member' using errcode = '55000'; end if;
  select quota into q from public.founder_segments where key = i.segment for update;
  if (select count(*) from public.founder_members m where m.segment = i.segment) >= q then raise exception 'This segment is full — ask Drugbox' using errcode = '23514'; end if;
  update public.founder_invites set used_by = me, used_at = now() where id = i.id;
  insert into public.founder_members (user_id, segment, invite_id) values (me, i.segment, i.id);
  if p_company is not null then vip := public.founder_apply_vip(p_company); end if;
  return jsonb_build_object('segment', i.segment, 'vip', vip);
end $$;

-- 3 months of VIP for a company page the founder runs (owner or admin) — once, within a year of joining
create or replace function public.founder_apply_vip(p_company bigint) returns jsonb
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); f public.founder_members; c public.companies; until timestamptz; sub text; claims text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into f from public.founder_members where user_id = me for update;
  if not found then raise exception 'Only founding members have the 3 VIP months' using errcode = '42501'; end if;
  if f.vip_applied_at is not null then raise exception 'Your 3 VIP months were already given to a company page' using errcode = '55000'; end if;
  if f.joined_at < now() - interval '1 year' then raise exception 'The 3 VIP months had to be used within a year of joining' using errcode = '55000'; end if;
  select * into c from public.companies where id = p_company for update;
  if not found then raise exception 'Company not found' using errcode = 'P0002'; end if;
  if not exists (select 1 from public.company_members m where m.company_id = c.id and m.user_id = me and m.role in ('owner', 'admin') and m.accepted)
     and c.owner_id is distinct from me then
    raise exception 'Give the VIP months to a company page you run (owner or admin)' using errcode = '42501'; end if;
  until := greatest(case when c.plan = 'vip' then coalesce(c.vip_until, now()) else now() end, now()) + interval '3 months';
  if c.plan = 'vip' and c.vip_until is null then until := null; end if;          -- a VIP granted by Drugbox without an end stays without an end
  -- companies_guard (0006) refuses a plan change made in a member's session (it runs only while auth.uid() is set): this one
  -- update is made as the server, the member's identity put back right after (all checks above were made as the member)
  sub := current_setting('request.jwt.claim.sub', true); claims := current_setting('request.jwt.claims', true);
  perform set_config('request.jwt.claim.sub', '', true); perform set_config('request.jwt.claims', '', true);
  update public.companies set plan = 'vip', vip_until = until where id = c.id;
  perform set_config('request.jwt.claim.sub', coalesce(sub, ''), true); perform set_config('request.jwt.claims', coalesce(claims, ''), true);
  update public.founder_members set vip_company_id = c.id, vip_applied_at = now() where user_id = me;
  return jsonb_build_object('company', c.id, 'vip_until', until);
end $$;
revoke all on function public.founder_apply_vip(bigint) from public, anon, authenticated, service_role;
grant execute on function public.founder_apply_vip(bigint) to authenticated, service_role;
revoke all on function public.founder_redeem(text, bigint) from public, anon, authenticated, service_role;
grant execute on function public.founder_redeem(text, bigint) to authenticated, service_role;

-- the founder's own record (what to show on their profile / whether the VIP months are still to give)
create or replace function public.my_founder() returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object('segment', f.segment, 'joined_at', f.joined_at, 'vip_company_id', f.vip_company_id, 'vip_applied_at', f.vip_applied_at,
                            'vip_open', f.vip_applied_at is null and f.joined_at > now() - interval '1 year',
                            'vip_until', (select c.vip_until from public.companies c where c.id = f.vip_company_id))
    from public.founder_members f where f.user_id = auth.uid()
$$;
revoke all on function public.my_founder() from public, anon, authenticated, service_role;
grant execute on function public.my_founder() to authenticated, service_role;

notify pgrst, 'reload schema';
