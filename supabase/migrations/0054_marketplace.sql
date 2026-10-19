-- ═════════════════════════════════════════════════════════════════════
-- 0054 — a marketplace that keeps what its members do (B-06 rest, B-07 rest, B-08, B-09, B-10; J-BUSINESS-34…41)
--   1. Listings (products) carry what a buyer needs to trust them and what their owner manages:
--      company_id (the company that lists it — one the owner belongs to), currency (from the price), status (active / paused /
--      draft / closed; `active` follows it, so every existing reader keeps working), renewed_at → expires_at (30 days, 90 for
--      CMO capacity, none for licences; "Renew" moves it), view_count / inquiry_count (counted by the database, never written
--      by the browser), coa_path (the Certificate of Analysis in private storage, documents/listings/<owner>/…), certs_verified
--      (the certificates Drugbox checked — only Drugbox writes them; the owner's own claims stay in docs).
--   2. Demand listings are products of type 'demand' (as the create form says); market_stats counts them.
--   3. listing_view(id): one view per member and day (the owner's own views are not counted).
--      listing_contact(id, body): the buyer's message reaches the owner as a direct message naming the listing, and counts
--      one inquiry per buyer and listing.
--   4. listing_quote(id, company, price, …): a supplier's priced quote on a demand goes through the deals engine — a 'quote'
--      deal from the buyer's company to the supplier's company, already at "Quote received" with the offer — never a chat.
--   5. listing_renew(id): the owner renews an active or expired listing for another period.
--   6. Matching (intents, 0035): a new active listing tells the members whose My Intents match it (a demand → those who have
--      the category to sell; an offer → those who need it), at most 200 per listing, once (a notification each).
--   7. market_search(q, type, category, limit, offset): the marketplace page by the database — newest first after paid
--      placement, name / description search (trigram), filters, the total for "Show more"; expired, paused and draft
--      listings never show. One call per page.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. listing columns ────
alter table public.products add column if not exists company_id     bigint references public.companies(id) on delete set null;
alter table public.products add column if not exists currency       text;
alter table public.products add column if not exists status         text not null default 'active';
alter table public.products add column if not exists renewed_at     timestamptz;
alter table public.products add column if not exists expires_at     timestamptz;
alter table public.products add column if not exists view_count     int not null default 0;
alter table public.products add column if not exists inquiry_count  int not null default 0;
alter table public.products add column if not exists coa_path       text;
alter table public.products add column if not exists certs_verified text[] not null default '{}';
do $$ begin
  alter table public.products add constraint products_status_chk check (status in ('active', 'paused', 'draft', 'closed'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.products add constraint products_currency_chk check (currency is null or currency in ('EGP','USD','EUR','SAR','AED','GBP','CNY','INR'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.products add constraint products_market_len check (length(coa_path) <= 200 and cardinality(certs_verified) <= 12 and length(price) <= 60 and length(moq) <= 80 and length(unit) <= 30);
exception when duplicate_object then null; end $$;
create index if not exists idx_products_company on public.products (company_id) where company_id is not null;
create index if not exists idx_products_market on public.products (type, status, expires_at, created_at desc);
create index if not exists idx_products_name_trgm on public.products using gin (name gin_trgm_ops);
update public.products set status = case when active then 'active' else 'closed' end where status = 'active' and not active;
update public.products set expires_at = case when category = 'registration' then null else coalesce(renewed_at, created_at) + case when category = 'cmo' then interval '90 days' else interval '30 days' end end
 where expires_at is null and category is distinct from 'registration';

-- what the browser may and may not write
create or replace function public.products_market_guard() returns trigger language plpgsql set search_path = public as $$   -- not a definer: is_server_call() sees the caller
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then
    new.view_count := 0; new.inquiry_count := 0; new.renewed_at := null;
    if not public.is_platform_admin() then new.certs_verified := '{}'; end if;
    if new.status not in ('active', 'draft') then new.status := 'active'; end if;
  else
    new.view_count := old.view_count; new.inquiry_count := old.inquiry_count;
    if not public.is_platform_admin() then new.certs_verified := old.certs_verified; end if;
    new.renewed_at := case when new.renewed_at is distinct from old.renewed_at then now() else old.renewed_at end;   -- "Renew" means now, never a date the browser chose
    if new.type is distinct from old.type then raise exception 'A listing cannot change between offer and request' using errcode = '42501'; end if;
  end if;
  if new.company_id is not null and (tg_op = 'INSERT' or new.company_id is distinct from old.company_id) and not public.is_company_member(new.company_id) then
    raise exception 'You can list only for a company you belong to' using errcode = '42501';
  end if;
  if new.coa_path is not null and (tg_op = 'INSERT' or new.coa_path is distinct from old.coa_path) and (new.coa_path !~ ('^listings/' || new.user_id::text || '/[A-Za-z0-9._-]{1,120}$')
       or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = new.coa_path)) then
    raise exception 'Upload the certificate of analysis first' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.products_market_guard() from public, anon, authenticated, service_role;
drop trigger if exists trg_products_a_market_guard on public.products;
create trigger trg_products_a_market_guard before insert or update on public.products for each row execute function public.products_market_guard();

-- status ⇄ active, the currency of the price, and the expiry: kept by the database (runs last: after server_columns)
create or replace function public.products_market_derive() returns trigger language plpgsql set search_path = public as $$
declare p text := coalesce(new.price, '');
begin
  if tg_op = 'UPDATE' and new.status is not distinct from old.status and new.active is distinct from old.active then
    new.status := case when new.active then 'active' else 'paused' end;
  end if;
  new.active := new.status = 'active';
  -- a bare number is in US dollars: the listing form's price field is "$5.80"
  new.currency := case when p !~ '\d' then null when p ~* 'US\$|USD|\$' or p ~ '^\s*[0-9][0-9.,]*\s*(/.*)?$' then 'USD' when p ~* '€|EUR' then 'EUR' when p ~* 'SAR|ريال' then 'SAR' when p ~* 'AED|درهم' then 'AED'
                       when p ~* '£|GBP' then 'GBP' when p ~* 'EGP|E£|جنيه|ج\.?\s?م' then 'EGP' when p ~* 'CNY|RMB|¥' then 'CNY' when p ~* 'INR|₹' then 'INR' else null end;
  new.expires_at := case when new.category = 'registration' then null
                         else coalesce(new.renewed_at, new.created_at, now()) + case when new.category = 'cmo' then interval '90 days' else interval '30 days' end end;
  return new;
end $$;
revoke all on function public.products_market_derive() from public, anon, authenticated, service_role;
drop trigger if exists trg_products_zz_market_derive on public.products;
create trigger trg_products_zz_market_derive before insert or update on public.products for each row execute function public.products_market_derive();

-- the owner reads their own drafts and paused listings; everyone signed in reads the active ones (the existing policy)
do $$ begin
  create policy "products: owners read their own" on public.products for select to authenticated using ((select auth.uid()) = user_id);
exception when duplicate_object then null; end $$;

-- the COA: documents/listings/<owner>/… — the owner uploads; signed-in members read the COA of an active listing
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator()
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
    when 'listings' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
                   or (auth.uid() is not null and exists (select 1 from public.products p where p.coa_path = p_name and p.active))
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'listings' then (storage.foldername(p_name))[2] = auth.uid()::text
    else false end
$$;
create index if not exists idx_products_coa on public.products (coa_path) where coa_path is not null;

-- ── 2. counts: demand listings are products ────
create or replace function public.market_stats() returns jsonb language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else jsonb_build_object(
    'supply',            (select count(*) from public.products  where active and type = 'supply' and (expires_at is null or expires_at > now())),
    'demand',            (select count(*) from public.products  where active and type = 'demand' and (expires_at is null or expires_at > now()))
                       + (select count(*) from public.enquiries where status = 'active' and type = 'demand'),
    'by_cat',            (select coalesce(jsonb_object_agg(c, n), '{}'::jsonb) from (select coalesce(category, 'other') c, count(*) n from public.products where active and type = 'supply' and (expires_at is null or expires_at > now()) group by 1) x),
    'demand_by_cat',     (select coalesce(jsonb_object_agg(c, n), '{}'::jsonb) from (select coalesce(category, 'other') c, count(*) n from public.products where active and type = 'demand' and (expires_at is null or expires_at > now()) group by 1) x),
    'suppliers',         (select count(distinct user_id) from public.products where active and type = 'supply'),
    'service_providers', (select count(distinct user_id) from public.products where active and type = 'supply' and category = 'service'),
    'jobs',              (select count(*) from public.jobs where active)
  ) end
$$;

-- ── 3. views and inquiries, counted by the database ────
create table if not exists public.listing_views (
  listing_id bigint not null references public.products(id) on delete cascade,
  viewer     uuid not null references public.profiles(id) on delete cascade,
  day        date not null default current_date,
  primary key (listing_id, viewer, day));
create index if not exists idx_listing_views_viewer on public.listing_views (viewer);
alter table public.listing_views enable row level security;
do $$ begin
  create policy "listing views: nobody reads them directly" on public.listing_views for select to authenticated using (false);
exception when duplicate_object then null; end $$;
revoke all on public.listing_views from public, anon, authenticated;
grant select on public.listing_views to anon, authenticated;   -- F-26: answers with nothing (policy false), never an error
grant all on public.listing_views to service_role;

create table if not exists public.listing_inquiries (
  listing_id bigint not null references public.products(id) on delete cascade,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (listing_id, user_id));
create index if not exists idx_listing_inquiries_user on public.listing_inquiries (user_id);
alter table public.listing_inquiries enable row level security;
do $$ begin
  create policy "listing inquiries: the asker and the lister read" on public.listing_inquiries for select to authenticated
    using (user_id = (select auth.uid()) or exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
revoke all on public.listing_inquiries from public, anon, authenticated;
grant select on public.listing_inquiries to anon, authenticated;
grant all on public.listing_inquiries to service_role;

create or replace function public.listing_views_count() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then update public.products set view_count = view_count + 1 where id = new.listing_id; end if;
  return null;
end $$;
revoke all on function public.listing_views_count() from public, anon, authenticated, service_role;
drop trigger if exists trg_listing_views_count on public.listing_views;
create trigger trg_listing_views_count after insert on public.listing_views for each row execute function public.listing_views_count();

create or replace function public.listing_inquiries_count() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then update public.products set inquiry_count = inquiry_count + 1 where id = new.listing_id;
  elsif tg_op = 'DELETE' then update public.products set inquiry_count = greatest(inquiry_count - 1, 0) where id = old.listing_id; end if;
  return null;
end $$;
revoke all on function public.listing_inquiries_count() from public, anon, authenticated, service_role;
drop trigger if exists trg_listing_inquiries_count on public.listing_inquiries;
create trigger trg_listing_inquiries_count after insert or delete on public.listing_inquiries for each row execute function public.listing_inquiries_count();

create or replace function public.listing_view(p_id bigint) returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v_owner uuid;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select user_id into v_owner from public.products where id = p_id and active;
  if v_owner is null or v_owner = me then return false; end if;
  insert into public.listing_views (listing_id, viewer) values (p_id, me) on conflict do nothing;
  return found;
end $$;
revoke all on function public.listing_view(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_view(bigint) to authenticated, service_role;

create or replace function public.listing_contact(p_id bigint, p_body text) returns bigint language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p record; v_body text := left(trim(coalesce(p_body, '')), 3800); mid bigint;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select id, user_id, name, type into p from public.products where id = p_id and active;
  if p.id is null then raise exception 'This listing is not available any more' using errcode = 'P0002'; end if;
  if p.user_id = me then raise exception 'This is your own listing' using errcode = '22023'; end if;
  if v_body = '' then raise exception 'Write a message' using errcode = '22023'; end if;
  if exists (select 1 from public.user_blocks b where (b.blocker = p.user_id and b.blocked = me) or (b.blocker = me and b.blocked = p.user_id)) then
    raise exception 'You cannot message this member' using errcode = '42501';
  end if;
  insert into public.messages (sender_id, receiver_id, body)
  values (me, p.user_id, 'Re: ' || p.name || ' (listing #' || p.id || ')' || chr(10) || v_body) returning id into mid;
  insert into public.listing_inquiries (listing_id, user_id) values (p.id, me) on conflict do nothing;
  return mid;
end $$;
revoke all on function public.listing_contact(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_contact(bigint, text) to authenticated, service_role;

-- ── 4. a priced quote on a demand goes through the deals engine ────
create or replace function public.listing_quote(p_id bigint, p_from_slug text, p_price text, p_qty text default null, p_lead text default null, p_note text default null)
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p record; v_sup public.companies; v_buyer bigint; d public.deals; v_price text := nullif(left(trim(coalesce(p_price, '')), 60), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and active and type = 'demand';
  if p.id is null then raise exception 'This request is not open any more' using errcode = 'P0002'; end if;
  if v_price is null or v_price !~ '\d' then raise exception 'Enter your price' using errcode = '22023'; end if;
  select * into v_sup from public.companies where slug = p_from_slug;
  if v_sup.id is null or not public.is_company_member(v_sup.id) then raise exception 'Quote on behalf of a company you belong to — create or claim your company page first' using errcode = '42501'; end if;
  if v_sup.status = 'suspended' then raise exception 'Your company is suspended and cannot send quotes' using errcode = '42501'; end if;
  if p.user_id = me then raise exception 'This is your own request' using errcode = '22023'; end if;
  -- the buyer's company: the one the request was posted for, else the buyer's own page
  v_buyer := coalesce(p.company_id, (select c.id from public.companies c where c.owner_id = p.user_id and c.status <> 'suspended' order by c.created_at limit 1),
                      (select m.company_id from public.company_members m where m.user_id = p.user_id and m.accepted order by m.created_at limit 1));
  if v_buyer is null then raise exception 'This buyer has no company page yet — message them instead' using errcode = '22023'; end if;
  if v_buyer = v_sup.id then raise exception 'You cannot quote to your own company' using errcode = '22023'; end if;
  if exists (select 1 from public.deals x where x.to_company_id = v_sup.id and x.lines ->> 'listing_id' = p.id::text and x.status in ('quoted', 'countered', 'sent')) then
    raise exception 'Your company has already quoted on this request — revise it in Requests & deals' using errcode = '23505';
  end if;
  if (select count(*) from public.deal_events e where e.actor = me and e.created_at > now() - interval '1 hour') >= 60 then
    raise exception 'Too many actions in one hour — please try again later' using errcode = '42501';
  end if;
  insert into public.deals (type, title, from_company_id, from_user, to_company_id, lines, status, offer, offer_at, assignee)
  values ('quote', left(p.name, 200), v_buyer, p.user_id, v_sup.id,
          jsonb_build_object('product', p.name, 'qty', coalesce(nullif(trim(p_qty), ''), p.moq, ''), 'listing_id', p.id),
          'quoted', jsonb_build_object('price', v_price, 'validity', '14 days', 'lead', coalesce(left(trim(p_lead), 60), ''), 'note', coalesce(left(trim(p_note), 500), '')), now(), me)
  returning * into d;
  insert into public.deal_events (deal_id, side, action, note, actor) values (d.id, 'from', 'sent', 'Request posted in the Marketplace: ' || p.name, p.user_id);
  insert into public.deal_events (deal_id, side, action, note, actor, data)
  values (d.id, 'to', 'quote', 'Send quote: ' || v_price || coalesce(' · lead time ' || nullif(trim(p_lead), ''), '') || coalesce(' — ' || nullif(trim(p_note), ''), ''), me,
          jsonb_build_object('price', v_price, 'lead', coalesce(p_lead, ''), 'note', coalesce(p_note, '')));
  insert into public.notifications (user_id, type, from_user, message) values (p.user_id, 'deal', me, left(v_sup.name || ': Send quote — ' || p.name, 300));
  return d.ref;
end $$;
revoke all on function public.listing_quote(bigint, text, text, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_quote(bigint, text, text, text, text, text) to authenticated, service_role;

-- ── 5. renew ────
create or replace function public.listing_renew(p_id bigint) returns timestamptz language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v timestamptz;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  update public.products set renewed_at = now(), status = case when status = 'closed' then 'active' else status end
   where id = p_id and user_id = me and status <> 'draft' returning expires_at into v;
  if not found then raise exception 'Only the listing''s owner can renew it' using errcode = '42501'; end if;
  return v;
end $$;
revoke all on function public.listing_renew(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_renew(bigint) to authenticated, service_role;

-- ── 6. matching: a new listing reaches the members whose intents match it ────
create index if not exists idx_profiles_intents on public.profiles using gin (intents jsonb_path_ops);
create or replace function public.products_match_notify() returns trigger language plpgsql security definer set search_path = public as $$
declare k text := case new.category when 'api' then 'api' when 'cmo' then 'cmo' when 'registration' then 'license' when 'equipment' then 'equipment' when 'service' then 'service' else null end;
        want text := case new.type when 'demand' then 'i-have' else 'i-need' end;
begin
  if k is null or new.status <> 'active' or (tg_op = 'UPDATE' and old.status = 'active') then return null; end if;
  if tg_op = 'UPDATE' and old.status <> 'draft' then return null; end if;                -- a draft published now: once; a resumed listing: not again
  insert into public.notifications (user_id, type, from_user, data)
  select pr.id, 'listing_match', new.user_id, jsonb_build_object('listing', new.id, 'name', left(new.name, 200), 'kind', new.type, 'category', k)
    from public.profiles pr
   where (pr.intents @> jsonb_build_object(k, want) or pr.intents @> jsonb_build_object(k, 'both')) and pr.id <> new.user_id
   limit 200;
  return null;
end $$;
revoke all on function public.products_match_notify() from public, anon, authenticated, service_role;
drop trigger if exists trg_products_match_notify on public.products;
create trigger trg_products_match_notify after insert or update of status on public.products for each row execute function public.products_match_notify();

-- ── 7. the marketplace page ────
create or replace function public.market_search(p_q text default null, p_type text default null, p_category text default null, p_limit int default 40, p_offset int default 0)
returns jsonb language plpgsql stable security invoker set search_path = public set jit = off as $$
declare v_q text := nullif(left(trim(coalesce(p_q, '')), 100), ''); v_lim int := least(greatest(coalesce(p_limit, 40), 1), 100); v_off int := greatest(coalesce(p_offset, 0), 0);
        v_total int; v_rows jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  with hits as (
    select p.* from public.products p
     where p.active and (p.expires_at is null or p.expires_at > now())
       and (p_type is null or p.type = p_type) and (p_category is null or p.category = p_category)
       and (v_q is null or p.name ilike '%' || v_q || '%' or p.description ilike '%' || v_q || '%'))
  select count(*)::int, coalesce((select jsonb_agg(to_jsonb(x) order by x.rank desc, x.created_at desc, x.id desc) from (
      select h.id, h.user_id, h.name, h.category, h.type, h.price, h.unit, h.moq, h.description, h.emoji, h.docs, h.certs_verified, h.lead_time, h.currency,
             h.company_id, h.created_at, h.expires_at, h.boosted_until, h.featured_until, h.view_count, h.inquiry_count, (h.coa_path is not null) as has_coa,
             case when h.featured_until > now() then 2 when h.boosted_until > now() then 1 else 0 end as rank,
             (select json_build_object('slug', c.slug, 'name', c.name, 'verified', c.status = 'verified') from public.companies c where c.id = h.company_id) as co
        from hits h order by case when h.featured_until > now() then 2 when h.boosted_until > now() then 1 else 0 end desc, h.created_at desc, h.id desc
        limit v_lim offset v_off) x), '[]'::jsonb)
    into v_total, v_rows from hits;
  return jsonb_build_object('total', v_total, 'rows', v_rows);
end $$;
revoke all on function public.market_search(text, text, text, int, int) from public, anon, authenticated, service_role;
grant execute on function public.market_search(text, text, text, int, int) to authenticated, service_role;

-- my listings with what the page needs (status, expiry, views, inquiries)
create or replace function public.my_listings() returns jsonb language sql stable security invoker set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'emoji', p.emoji, 'category', p.category, 'type', p.type, 'status', p.status, 'price', p.price, 'moq', p.moq,
           'description', p.description, 'created_at', p.created_at, 'renewed_at', p.renewed_at, 'expires_at', p.expires_at, 'views', p.view_count, 'inquiries', p.inquiry_count,
           'boosted', (p.boosted_until > now() or p.featured_until > now()), 'company_id', p.company_id) order by p.created_at desc, p.id desc), '[]'::jsonb)
  from (select * from public.products where user_id = auth.uid() and status <> 'closed' order by created_at desc limit 200) p
$$;
revoke all on function public.my_listings() from public, anon, authenticated, service_role;
grant execute on function public.my_listings() to authenticated, service_role;

-- ── 8. surplus sold: the quantity a buyer received comes off the surplus listing (J-BUSINESS-38) ────
create or replace function public.deals_surplus_sold() returns trigger language plpgsql security definer set search_path = public as $$
declare l record; have numeric; unit text; got numeric; left_ numeric;
begin
  if new.type <> 'surplus' or new.status <> 'delivered' or old.status = 'delivered' or coalesce(new.lines ->> 'listing', '') = '' then return null; end if;
  select * into l from public.company_listings where ref = new.lines ->> 'listing' and company_id = new.to_company_id and kind = 'surplus' for update;
  if l.id is null then return null; end if;
  have := nullif(substring(replace(coalesce(l.qty, ''), ',', '') from '([0-9]+(\.[0-9]+)?)'), '')::numeric;
  unit := trim(regexp_replace(coalesce(l.qty, ''), '^[^A-Za-z]*', ''));
  got := nullif(substring(replace(coalesce(new.lines ->> 'qty', ''), ',', '') from '([0-9]+(\.[0-9]+)?)'), '')::numeric;
  if have is null or got is null or got <= 0 then return null; end if;
  -- the same unit, or the buyer gave a bare number
  if trim(regexp_replace(coalesce(new.lines ->> 'qty', ''), '^[^A-Za-z]*', '')) not in ('', unit) then return null; end if;
  left_ := greatest(have - got, 0);
  update public.company_listings set qty = trim(case when left_ = trunc(left_) then trunc(left_)::text else rtrim(rtrim(left_::text, '0'), '.') end || ' ' || unit), active = left_ > 0 where id = l.id;
  return null;
end $$;
revoke all on function public.deals_surplus_sold() from public, anon, authenticated, service_role;
drop trigger if exists trg_deals_surplus_sold on public.deals;
create trigger trg_deals_surplus_sold after update of status on public.deals for each row execute function public.deals_surplus_sold();

-- ── 9. saved listings (the card's 🔖): kept with the member, not in one browser ────
create table if not exists public.saved_listings (
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  listing_id bigint not null references public.products(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, listing_id));
create index if not exists idx_saved_listings_listing on public.saved_listings (listing_id);
alter table public.saved_listings enable row level security;
do $$ begin
  create policy "saved listings: your own" on public.saved_listings for select to authenticated using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "saved listings: save as yourself" on public.saved_listings for insert to authenticated with check (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "saved listings: remove your own" on public.saved_listings for delete to authenticated using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on public.saved_listings from public, anon, authenticated;
grant select on public.saved_listings to anon;
grant select, insert, delete on public.saved_listings to authenticated;
grant all on public.saved_listings to service_role;

-- ── 10. Drugbox marks a listing's certificates checked (only those the seller claims) ────
create or replace function public.listing_verify_certs(p_id bigint, p_certs text[]) returns text[] language plpgsql security definer set search_path = public as $$
declare v text[];
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  update public.products set certs_verified = array(select c from unnest(coalesce(p_certs, '{}')) c where c = any(coalesce(docs, '{}')))
   where id = p_id returning certs_verified into v;
  if not found then raise exception 'This listing does not exist' using errcode = 'P0002'; end if;
  return v;
end $$;
revoke all on function public.listing_verify_certs(bigint, text[]) from public, anon, authenticated, service_role;
grant execute on function public.listing_verify_certs(bigint, text[]) to authenticated, service_role;

notify pgrst, 'reload schema';
