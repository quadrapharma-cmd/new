-- ═════════════════════════════════════════════════════════════════════
-- 0093 — an identity that does not get lost with a phone (area w-trust: W-20)
--   The phone number stays private (0036: members read every profile column except phone). What others see is that the number
--   was VERIFIED — a code sent to it and typed back — never the number itself.
--   1. member_verifications(user_id, phone_verified_at): read by every signed-in member; written by the functions below only.
--      phone_hash (sha-256 of the normalised number) stays private: one number verifies one account, so a second account
--      cannot borrow the number of a known trader.
--   2. phone_verify_start(phone): normalises the number (+20 1x xxxx xxxx for Egypt, else +<7–15 digits>), keeps a 6-digit
--      code for 10 minutes (only its hash), puts the SMS in private.sms_outbox for the SMS provider (the provider and its
--      account are the owner's decision — LAUNCH), at most 3 codes an hour and 6 a day.
--      phone_verify_confirm(code): 5 tries; the number becomes the profile's (private) phone and verified.
--      Changing the phone in Edit Profile to another number removes the verification (the trigger below).
--   3. trade_card (0092) says phone_verified; 'member since' and 'new account' (under 30 days) were already on it.
--   Offers and conversations live on the server (products, messages) — a lost phone loses nothing.
-- Every new table / function has its own GRANT / REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

create table if not exists public.member_verifications (
  user_id           uuid primary key references public.profiles(id) on delete cascade,
  phone_verified_at timestamptz,
  phone_hash        text,
  updated_at        timestamptz not null default now()
);
create unique index if not exists idx_member_verifications_phone on public.member_verifications (phone_hash) where phone_hash is not null;
alter table public.member_verifications enable row level security;
drop policy if exists "verifications: members read" on public.member_verifications;
create policy "verifications: members read" on public.member_verifications for select to authenticated using (true);
revoke all on table public.member_verifications from public, anon, authenticated, service_role;
grant select (user_id, phone_verified_at) on table public.member_verifications to authenticated;   -- never the hash
grant select, insert, update, delete, truncate, references, trigger on table public.member_verifications to service_role;

create table if not exists private.phone_codes (
  user_id    uuid primary key references public.profiles(id) on delete cascade,
  phone      text not null,
  code_hash  text not null,
  tries      int not null default 0,
  expires_at timestamptz not null
);
create table if not exists private.phone_code_log (
  id      bigint generated always as identity primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  sent_at timestamptz not null default now()
);
create index if not exists idx_phone_code_log_user on private.phone_code_log (user_id, sent_at desc);
create table if not exists private.sms_outbox (
  id         bigint generated always as identity primary key,
  phone      text not null,
  body       text not null,
  created_at timestamptz not null default now(),
  sent_at    timestamptz
);
create index if not exists idx_sms_outbox_unsent on private.sms_outbox (created_at) where sent_at is null;
revoke all on table private.phone_codes, private.phone_code_log, private.sms_outbox from public, anon, authenticated;
grant select, insert, update, delete on table private.phone_codes, private.phone_code_log, private.sms_outbox to service_role;

-- '+201001234567' for an Egyptian mobile (01…, 201…, +201…, 00201…), '+<digits>' for another country; null when it is not a number
create or replace function private.phone_norm(p text) returns text language sql immutable set search_path = public as $$
  select case
    when d ~ '^(0020|\+20|20)?0?1[0125][0-9]{8}$' then '+20' || substring(d from '(1[0125][0-9]{8})$')
    when d ~ '^(\+|00)[1-9][0-9]{6,14}$' then '+' || regexp_replace(d, '^(\+|00)', '')
    else null end
  from (select regexp_replace(translate(coalesce(p, ''), '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'), '[\s().-]', '', 'g') d) x
$$;
revoke all on function private.phone_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.phone_norm(text) to authenticated, service_role;

create or replace function public.phone_verify_start(p_phone text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare me uuid := auth.uid(); ph text := private.phone_norm(p_phone); code text; h text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if private.is_suspended(me) then raise exception 'Your account is suspended' using errcode = '42501'; end if;
  if ph is null then raise exception 'Enter a mobile number (e.g. 010 1234 5678 or +971 50 123 4567)' using errcode = '22023', hint = 'DX440'; end if;
  h := encode(sha256(convert_to('drugbox-phone:' || ph, 'UTF8')), 'hex');
  if exists (select 1 from public.member_verifications v where v.phone_hash = h and v.user_id <> me) then
    raise exception 'This number is already verified on another Drugbox account' using errcode = '23505', hint = 'DX441'; end if;
  if (select count(*) from private.phone_code_log l where l.user_id = me and l.sent_at > now() - interval '1 hour') >= 3
     or (select count(*) from private.phone_code_log l where l.user_id = me and l.sent_at > now() - interval '1 day') >= 6 then
    raise exception 'Too many codes — try again later' using errcode = '54000', hint = 'DX442'; end if;
  code := lpad((floor(random() * 1000000))::int::text, 6, '0');
  insert into private.phone_codes (user_id, phone, code_hash, tries, expires_at)
  values (me, ph, encode(sha256(convert_to(me::text || ':' || code, 'UTF8')), 'hex'), 0, now() + interval '10 minutes')
  on conflict (user_id) do update set phone = excluded.phone, code_hash = excluded.code_hash, tries = 0, expires_at = excluded.expires_at;
  insert into private.phone_code_log (user_id) values (me);
  insert into private.sms_outbox (phone, body) values (ph, 'Drugbox code: ' || code || ' — رمز Drugbox: ' || code || '. It expires in 10 minutes.');
  return jsonb_build_object('sent', true, 'to', left(ph, 4) || repeat('•', greatest(char_length(ph) - 6, 0)) || right(ph, 2), 'minutes', 10);
end $$;
revoke all on function public.phone_verify_start(text) from public, anon, authenticated, service_role;
grant execute on function public.phone_verify_start(text) to authenticated, service_role;

create or replace function public.phone_verify_confirm(p_code text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare me uuid := auth.uid(); c private.phone_codes; h text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into c from private.phone_codes where user_id = me for update;
  if c.user_id is null or c.expires_at < now() then raise exception 'The code expired — ask for a new one' using errcode = '22023', hint = 'DX443'; end if;
  if c.tries >= 5 then raise exception 'Too many wrong codes — ask for a new one' using errcode = '54000', hint = 'DX444'; end if;
  if c.code_hash <> encode(sha256(convert_to(me::text || ':' || regexp_replace(translate(coalesce(p_code, ''), '٠١٢٣٤٥٦٧٨٩', '0123456789'), '\D', '', 'g'), 'UTF8')), 'hex') then
    update private.phone_codes set tries = tries + 1 where user_id = me;
    raise exception 'That code is not right' using errcode = '22023', hint = 'DX445';
  end if;
  h := encode(sha256(convert_to('drugbox-phone:' || c.phone, 'UTF8')), 'hex');
  if exists (select 1 from public.member_verifications v where v.phone_hash = h and v.user_id <> me) then
    raise exception 'This number is already verified on another Drugbox account' using errcode = '23505', hint = 'DX441'; end if;
  delete from private.phone_codes where user_id = me;
  perform set_config('drugbox.phone_verifying', '1', true);
  update public.profiles set phone = c.phone where id = me;
  perform set_config('drugbox.phone_verifying', '', true);
  insert into public.member_verifications (user_id, phone_verified_at, phone_hash, updated_at) values (me, now(), h, now())
  on conflict (user_id) do update set phone_verified_at = now(), phone_hash = excluded.phone_hash, updated_at = now();
  return jsonb_build_object('verified', true, 'phone', c.phone);
end $$;
revoke all on function public.phone_verify_confirm(text) from public, anon, authenticated, service_role;
grant execute on function public.phone_verify_confirm(text) to authenticated, service_role;

-- another number typed in Edit Profile is not the verified one any more
create or replace function public.profiles_phone_unverify() returns trigger language plpgsql security definer set search_path = public, extensions as $$
begin
  if current_setting('drugbox.phone_verifying', true) = '1' then return null; end if;
  update public.member_verifications v set phone_verified_at = null, phone_hash = null, updated_at = now()
   where v.user_id = new.id and v.phone_hash is not null
     and v.phone_hash is distinct from encode(sha256(convert_to('drugbox-phone:' || coalesce(private.phone_norm(new.phone), ''), 'UTF8')), 'hex');
  return null;
end $$;
revoke all on function public.profiles_phone_unverify() from public, anon, authenticated, service_role;
grant execute on function public.profiles_phone_unverify() to service_role;
drop trigger if exists trg_profiles_phone_unverify on public.profiles;
create trigger trg_profiles_phone_unverify after update of phone on public.profiles for each row
  when (new.phone is distinct from old.phone) execute function public.profiles_phone_unverify();

-- ── the trade card (0092) says whether the phone is verified ────
create or replace function public.trade_card(p_user uuid) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null or p_user = any (coalesce(private.blocked_parties(), '{}'::uuid[])) then null else (
    select jsonb_build_object(
      'user_id', p.id,
      'member_since', p.created_at,
      'new_account', p.created_at > now() - interval '30 days',
      'profile', (select to_jsonb(t) - 'user_id' from public.trade_profiles t where t.user_id = p.id),
      'offers', (select count(*) from public.products x where x.user_id = p.id and x.status <> 'draft'),
      'offers_active', (select count(*) from public.products x where x.user_id = p.id and x.active and not x.review_hold and (x.expires_at is null or x.expires_at > now())),
      'reports_upheld', (select count(*) from public.trader_reports r where r.reported = p.id and r.status = 'upheld'),
      'buyer_rating', public.buyer_rating(null, p.id),
      'phone_verified', exists (select 1 from public.member_verifications v where v.user_id = p.id and v.phone_verified_at is not null))
    from public.profiles p where p.id = p_user) end
$$;
revoke all on function public.trade_card(uuid) from public, anon, authenticated, service_role;
grant execute on function public.trade_card(uuid) to authenticated, service_role;

notify pgrst, 'reload schema';
