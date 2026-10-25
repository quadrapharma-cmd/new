-- ═════════════════════════════════════════════════════════════════════
-- 0090 — who stands behind a trade offer (area w-trust: W-10, W-16, W-25)
--   Drugbox trade is business-to-business before the pharmacy. Members post trade offers as themselves; a company page posts
--   AS THE COMPANY only once Drugbox verified it (companies.status = 'verified'); a member who posts someone else's product or
--   registration file says so (a broker / وسيط) and names the owner, attaches the owner's authorisation and the commission.
--   1. trade_profiles: the short trade card a member fills before their first trade offer — role, company, governorate,
--      what they sell / buy. Read by every signed-in member (it is the card shown on the profile and to group admins);
--      written by its owner only. Pharmacies are not trading parties: no pharmacy role.
--   2. products (marketplace offers) and group_listings (deal-room listings) carry posted_as:
--        'company'    — company_id set, the company is verified (and the poster belongs to it, as before)
--        'individual' — the member as themselves
--        'broker'     — the member for someone else: broker_for (the owner of the product / file), broker_auth_path (the owner's
--                       authorisation in private storage, documents/listings/<member>/…, uploaded first), broker_commission (%)
--        'drugbox'    — only a Drugbox admin (anything Drugbox posts is badged as Drugbox)
--      The browser never decides alone: a trigger checks every rule on insert and on any change of these columns, and fills
--      posted_as from company_id when the browser sends none ('company' with a company, else 'individual').
--   3. private.trade_gate(user, company, posted_as): the same rules as one function, for any other trade table (the trade area's
--      offer posts can call it).
--   4. trade_card(user): the card + 'member since' + how many offers they published (kept on the server) + upheld trader reports
--      (0092) — one call for a profile.
-- Every new table / function has its own GRANT / REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. trade profiles ────
create table if not exists public.trade_profiles (
  user_id     uuid primary key references public.profiles(id) on delete cascade,
  role        text not null,
  company     text,
  governorate text not null,
  sells       text,
  buys        text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint trade_profiles_role check (role in ('manufacturer', 'toll_manufacturer', 'file_owner', 'importer_exporter', 'distributor',
                                                 'supplier', 'service_provider', 'consultant')),
  constraint trade_profiles_gov check (governorate in ('Cairo', 'Giza', 'Alexandria', 'Qalyubia', 'Sharqia', 'Dakahlia', 'Gharbia', 'Monufia',
                                                       'Beheira', 'Kafr El Sheikh', 'Damietta', 'Port Said', 'Ismailia', 'Suez', 'North Sinai',
                                                       'South Sinai', 'Red Sea', 'Matrouh', 'New Valley', 'Faiyum', 'Beni Suef', 'Minya', 'Asyut',
                                                       'Sohag', 'Qena', 'Luxor', 'Aswan', 'Outside Egypt')),
  constraint trade_profiles_len check (char_length(coalesce(company, '')) <= 120 and char_length(coalesce(sells, '')) <= 300
                                       and char_length(coalesce(buys, '')) <= 300),
  constraint trade_profiles_what check (char_length(trim(coalesce(sells, ''))) >= 2 or char_length(trim(coalesce(buys, ''))) >= 2)
);
alter table public.trade_profiles enable row level security;
drop policy if exists "trade profiles: members read" on public.trade_profiles;
create policy "trade profiles: members read" on public.trade_profiles for select to authenticated
  using (user_id <> all (coalesce((select private.blocked_parties()), '{}'::uuid[])));
drop policy if exists "trade profiles: own insert" on public.trade_profiles;
create policy "trade profiles: own insert" on public.trade_profiles for insert to authenticated with check (user_id = (select auth.uid()));
drop policy if exists "trade profiles: own update" on public.trade_profiles;
create policy "trade profiles: own update" on public.trade_profiles for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
drop policy if exists "trade profiles: own delete" on public.trade_profiles;
create policy "trade profiles: own delete" on public.trade_profiles for delete to authenticated using (user_id = (select auth.uid()));
revoke all on table public.trade_profiles from public, anon, authenticated, service_role;
grant select on table public.trade_profiles to anon;                              -- no policy for anon → an empty answer (F-26)
grant select, insert, update, delete on table public.trade_profiles to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.trade_profiles to service_role;

-- the dates are the server's; the text is trimmed (no invisible characters at the ends)
create or replace function public.trade_profiles_guard() returns trigger language plpgsql set search_path = public as $$
begin
  new.company := nullif(btrim(regexp_replace(coalesce(new.company, ''), '[[:cntrl:]​-‏‪-‮⁦-⁩﻿]', '', 'g')), '');
  new.sells := nullif(btrim(regexp_replace(coalesce(new.sells, ''), '[[:cntrl:]​-‏‪-‮⁦-⁩﻿]', ' ', 'g')), '');
  new.buys := nullif(btrim(regexp_replace(coalesce(new.buys, ''), '[[:cntrl:]​-‏‪-‮⁦-⁩﻿]', ' ', 'g')), '');
  if tg_op = 'INSERT' then new.created_at := now(); else new.created_at := old.created_at; new.user_id := old.user_id; end if;
  new.updated_at := now();
  return new;
end $$;
revoke all on function public.trade_profiles_guard() from public, anon, authenticated, service_role;
grant execute on function public.trade_profiles_guard() to service_role;
drop trigger if exists trg_trade_profiles_guard on public.trade_profiles;
create trigger trg_trade_profiles_guard before insert or update on public.trade_profiles for each row execute function public.trade_profiles_guard();
do $$ begin
  if not exists (select 1 from pg_trigger where tgrelid = 'public.trade_profiles'::regclass and tgname = 'trg_trade_profiles_not_suspended') then
    create trigger trg_trade_profiles_not_suspended before insert or update on public.trade_profiles for each row execute function public.writer_not_suspended();
  end if;
end $$;

-- ── 2. who posts the offer ────
alter table public.products add column if not exists posted_as         text;
alter table public.products add column if not exists broker_for        text;
alter table public.products add column if not exists broker_auth_path  text;
alter table public.products add column if not exists broker_commission numeric(5,2);
alter table public.group_listings add column if not exists posted_as         text;
alter table public.group_listings add column if not exists broker_for        text;
alter table public.group_listings add column if not exists broker_auth_path  text;
alter table public.group_listings add column if not exists broker_commission numeric(5,2);
do $$ begin
  alter table public.products add constraint products_posted_as check (posted_as is null or posted_as in ('company', 'individual', 'broker', 'drugbox'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.products add constraint products_broker_len check (char_length(coalesce(broker_for, '')) <= 120 and char_length(coalesce(broker_auth_path, '')) <= 200
                                                                         and (broker_commission is null or broker_commission between 0 and 50));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.group_listings add constraint group_listings_posted_as check (posted_as is null or posted_as in ('company', 'individual', 'broker', 'drugbox'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.group_listings add constraint group_listings_broker_len check (char_length(coalesce(broker_for, '')) <= 120 and char_length(coalesce(broker_auth_path, '')) <= 200
                                                                                     and (broker_commission is null or broker_commission between 0 and 50));
exception when duplicate_object then null; end $$;
-- existing rows: what they are (an offer with a company is the company's)
update public.products set posted_as = case when company_id is not null then 'company' else 'individual' end where posted_as is null;
update public.group_listings set posted_as = case when company_id is not null then 'company' else 'individual' end where posted_as is null;
grant select (posted_as, broker_for, broker_commission) on table public.products to anon, authenticated;
grant select (posted_as, broker_for, broker_commission) on table public.group_listings to authenticated;

-- ── 3. the rules, once ────
-- raises with an EN message (the app translates it) and the code DX4xx the app can recognise
create or replace function private.trade_gate(p_user uuid, p_company bigint, p_posted_as text, p_broker_for text default null,
                                              p_auth_path text default null, p_commission numeric default null) returns void
language plpgsql stable security definer set search_path = public as $$
declare st text;
begin
  if p_posted_as = 'drugbox' then
    if not exists (select 1 from public.profiles p where p.id = p_user and p.role = 'admin') then
      raise exception 'Only the Drugbox team posts as Drugbox' using errcode = '42501', hint = 'DX416';
    end if;
    if p_company is not null then raise exception 'A Drugbox offer is not a company''s offer' using errcode = '22023', hint = 'DX416'; end if;
    return;
  end if;
  if not exists (select 1 from public.trade_profiles t where t.user_id = p_user) then
    raise exception 'Add your trade profile first (role, company, governorate, what you buy or sell) — it is shown with your offers'
      using errcode = '42501', hint = 'DX410';
  end if;
  if p_company is not null then
    if p_posted_as is distinct from 'company' then
      raise exception 'An offer with a company page is posted as the company' using errcode = '22023', hint = 'DX411';
    end if;
    select c.status into st from public.companies c where c.id = p_company;
    if st is distinct from 'verified' then
      raise exception 'Only a company page with the Drugbox verification badge posts trade offers as the company — get it verified (free), or post as yourself'
        using errcode = '42501', hint = 'DX412';
    end if;
    return;
  end if;
  if p_posted_as = 'company' then raise exception 'Choose the company page this offer is for' using errcode = '22023', hint = 'DX411'; end if;
  if p_posted_as = 'broker' then
    if char_length(trim(coalesce(p_broker_for, ''))) < 2 then
      raise exception 'A broker names whose product or file this is' using errcode = '22023', hint = 'DX413';
    end if;
    if p_commission is null then raise exception 'A broker states the commission (%%)' using errcode = '22023', hint = 'DX414'; end if;
    if p_auth_path is null or p_auth_path !~ ('^listings/' || p_user::text || '/[A-Za-z0-9._-]{1,120}$')
       or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = p_auth_path) then
      raise exception 'A broker attaches the owner''s authorisation (upload it first)' using errcode = '42501', hint = 'DX415';
    end if;
  elsif p_broker_for is not null or p_auth_path is not null or p_commission is not null then
    raise exception 'Broker details belong to a broker''s offer' using errcode = '22023', hint = 'DX413';
  end if;
end $$;
revoke all on function private.trade_gate(uuid, bigint, text, text, text, numeric) from public, anon, authenticated, service_role;
grant execute on function private.trade_gate(uuid, bigint, text, text, text, numeric) to authenticated, service_role;

-- the trigger: on insert, and when anything the rules look at changes (an old listing is not refused for being old)
create or replace function public.trade_offer_guard() returns trigger language plpgsql set search_path = public as $$   -- not a definer: is_server_call() sees the caller
begin
  new.broker_for := nullif(btrim(coalesce(new.broker_for, '')), '');
  if new.posted_as is null then new.posted_as := case when new.company_id is not null then 'company' else 'individual' end; end if;
  if public.is_server_call() then return new; end if;
  if tg_op = 'UPDATE' and (new.posted_as, new.company_id, new.broker_for, new.broker_auth_path, new.broker_commission)
                          is not distinct from (old.posted_as, old.company_id, old.broker_for, old.broker_auth_path, old.broker_commission) then
    return new;
  end if;
  if tg_op = 'UPDATE' and new.user_id is distinct from old.user_id then raise exception 'An offer keeps its author' using errcode = '42501'; end if;
  perform private.trade_gate(new.user_id, new.company_id, new.posted_as, new.broker_for, new.broker_auth_path, new.broker_commission);
  return new;
end $$;
revoke all on function public.trade_offer_guard() from public, anon, authenticated, service_role;
grant execute on function public.trade_offer_guard() to authenticated, service_role;
drop trigger if exists trg_products_trade_guard on public.products;
create trigger trg_products_trade_guard before insert or update on public.products for each row execute function public.trade_offer_guard();
drop trigger if exists trg_group_listings_trade_guard on public.group_listings;
create trigger trg_group_listings_trade_guard before insert or update on public.group_listings for each row execute function public.trade_offer_guard();

-- the broker's authorisation (documents/listings/<member>/…) is read by its owner, the Drugbox team and the members who can read the
-- offer: can_read_document() gets that branch in 0092 (with the trader reports' evidence), on top of 0060's version
create index if not exists idx_products_broker_auth on public.products (broker_auth_path) where broker_auth_path is not null;
create index if not exists idx_group_listings_broker_auth on public.group_listings (broker_auth_path) where broker_auth_path is not null;

-- ── 4. the trade card of a member (one call for a profile) ────
create or replace function public.trade_card(p_user uuid) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null or p_user = any (coalesce(private.blocked_parties(), '{}'::uuid[])) then null else (
    select jsonb_build_object(
      'user_id', p.id,
      'member_since', p.created_at,
      'new_account', p.created_at > now() - interval '30 days',
      'profile', (select to_jsonb(t) - 'user_id' from public.trade_profiles t where t.user_id = p.id),
      'offers', (select count(*) from public.products x where x.user_id = p.id and x.status <> 'draft'),
      'offers_active', (select count(*) from public.products x where x.user_id = p.id and x.active and (x.expires_at is null or x.expires_at > now())),
      'phone_verified', false)
    from public.profiles p where p.id = p_user) end
$$;
revoke all on function public.trade_card(uuid) from public, anon, authenticated, service_role;
grant execute on function public.trade_card(uuid) to authenticated, service_role;

notify pgrst, 'reload schema';
