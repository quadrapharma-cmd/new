-- 0076 — W-trade: no restriction that holds a new member back (the owner, 25 Oct 2026: «مش عايز أي قيود تضايق اليوزر في الأول» → «delete all»)
--   · a company posts as the company without the verification badge (cards still show ✓ only for verified companies)
--   · a listing needs only its name; every other field (items' quantities, toll GMP, file stage…) is optional
--   · the same offer may be posted again (no duplicate refusal)
--   · a listing is renewed whenever its owner wants (no once-a-week limit); a sold one is still posted anew
--   · no checklist is required before agreeing a file deal
-- Kept (they protect members, a newcomer never meets them): price-request / quote / answer rate limits, the cap on recorded sales
-- between the same two members, the private box opened only by an agreed deal, statuses and prices set by the server.

create or replace function public.trade_missing(p_kind text, p_attrs jsonb, p_id bigint, p_name text) returns text language plpgsql stable security definer set search_path = public as $$
begin
  -- the owner (25 Oct): nothing stops a new member at the start — a listing needs only its name; the other fields are optional
  if p_kind is not null and coalesce(btrim(p_name), '') = '' then return 'a name'; end if;
  return null;
end $$;
revoke all on function public.trade_missing(text, jsonb, bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.trade_missing(text, jsonb, bigint, text) to authenticated, service_role;

create or replace function public.products_trade_guard() returns trigger language plpgsql set search_path = public as $$   -- not a definer: is_server_call() sees the caller
begin
  if public.is_server_call() then return new; end if;
  -- server-only columns
  if tg_op = 'INSERT' then
    new.item_key := null; new.roots := '{}'; new.root_words := '{}'; new.search_text := null; new.fingerprint := null; new.bumped_at := null;
    new.published_at := null; new.closed_reason := null; new.docs_checked_at := null; new.docs_checked_by := null;
    if new.status = 'reserved' then new.status := 'active'; end if;
  else
    new.item_key := old.item_key; new.roots := old.roots; new.root_words := old.root_words; new.search_text := old.search_text; new.fingerprint := old.fingerprint;
    new.bumped_at := old.bumped_at; new.published_at := old.published_at; new.docs_checked_at := old.docs_checked_at; new.docs_checked_by := old.docs_checked_by;
    new.closed_reason := case when new.status = 'closed' and old.status <> 'closed' then 'withdrawn' when new.status = 'closed' then old.closed_reason else null end;
    if new.kind is distinct from old.kind and old.status <> 'draft' then raise exception 'A published listing keeps its kind — post a new one' using errcode = '42501'; end if;
    if new.status = 'reserved' and old.status <> 'reserved' then raise exception 'Mark it reserved with “Reserved / sold” in My Listings' using errcode = '42501'; end if;
    if old.status = 'reserved' and new.status = 'active' then raise exception 'Reopen it with “Reserved / sold” in My Listings' using errcode = '42501'; end if;
    if old.status = 'closed' and new.status <> 'closed' then raise exception 'Renew a closed listing to show it again' using errcode = '42501'; end if;
  end if;
  return new;
end $$;
revoke all on function public.products_trade_guard() from public, anon, authenticated, service_role;

create or replace function public.products_market_derive() returns trigger language plpgsql set search_path = public as $$
declare p text := coalesce(new.price, ''); miss text; going_live boolean;
begin
  if tg_op = 'UPDATE' and new.status is not distinct from old.status and new.active is distinct from old.active then
    new.status := case when new.active then 'active' else 'paused' end;
  end if;
  new.active := new.status in ('active', 'reserved');
  -- the kind decides the side and the category (every reader of type / category keeps working)
  if new.kind is not null then
    new.type := case when new.kind in ('wanted', 'file_wanted', 'distributor', 'toll_wanted') then 'demand' else 'supply' end;
    new.category := case new.kind when 'stock' then 'finished' when 'materials' then 'api' when 'toll' then 'cmo' when 'toll_wanted' then 'cmo'
                                  when 'file_sale' then 'registration' when 'file_wanted' then 'registration' else 'other' end;
    new.attrs := public.trade_attrs_clean(new.kind, new.attrs);
  else
    new.attrs := '{}';
  end if;
  if new.price_mode is null then new.price_mode := case when p ~ '\d' then 'amount' else null end; end if;
  if new.price_mode is distinct from 'discount' then new.discount_pct := null; end if;
  if new.price_mode = 'discount' and new.discount_pct is null then raise exception 'Enter the discount (1–95 %%)' using errcode = '22023'; end if;
  -- a bare number is in US dollars: the listing form's price field is "$5.80" (0054); a structured listing names its currency
  new.currency := case when p !~ '\d' then null when new.attrs ? 'currency' and p ~ '^\s*[0-9][0-9.,]*\s*(/.*)?$' then new.attrs ->> 'currency'
                       when p ~* 'US\$|USD|\$' or p ~ '^\s*[0-9][0-9.,]*\s*(/.*)?$' then 'USD' when p ~* '€|EUR' then 'EUR' when p ~* 'SAR|ريال' then 'SAR' when p ~* 'AED|درهم' then 'AED'
                       when p ~* '£|GBP' then 'GBP' when p ~* 'EGP|E£|جنيه|ج\.?\s?م' then 'EGP' when p ~* 'CNY|RMB|¥' then 'CNY' when p ~* 'INR|₹' then 'INR' else null end;
  new.expires_at := case when new.category = 'registration' or new.kind in ('file_sale', 'file_wanted') then null
                         else coalesce(new.bumped_at, new.renewed_at, new.created_at, now())
                              + case when new.kind in ('toll', 'toll_wanted', 'agency', 'distributor', 'company_sale') or (new.kind is null and new.category = 'cmo') then interval '90 days' else interval '30 days' end end;
  -- keys, roots, search text, fingerprint: computed again when the words change (a view or an inquiry does not recompute them)
  if tg_op = 'INSERT' or new.name is distinct from old.name or new.description is distinct from old.description or new.attrs is distinct from old.attrs
     or new.kind is distinct from old.kind or new.search_text is null then
    new := public.trade_compute(new);
  end if;
  going_live := new.status = 'active' and (tg_op = 'INSERT' or old.status in ('draft', 'closed') or old.published_at is null);   -- never published (a draft paused, then resumed): the checks still apply
  if going_live then
    miss := public.trade_missing(new.kind, new.attrs, new.id, new.name);
    if miss is not null then raise exception 'Add % before publishing', miss using errcode = '22023'; end if;
  end if;
  return new;
end $$;
revoke all on function public.products_market_derive() from public, anon, authenticated, service_role;

create or replace function public.listing_lines_replace(p_id bigint, p_lines jsonb) returns int language plpgsql security invoker set search_path = public as $$
declare n int;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if jsonb_typeof(p_lines) is distinct from 'array' then raise exception 'Send the items as a list' using errcode = '22023'; end if;
  if not exists (select 1 from public.products where id = p_id and user_id = auth.uid() and status in ('draft', 'active', 'paused')) then
    raise exception 'Only the listing''s owner can change it' using errcode = '42501'; end if;
  delete from public.listing_lines where listing_id = p_id;
  insert into public.listing_lines (listing_id, pos, name, name_ar, strength, form, qty, unit, expiry, source, origin_country, pack_state, cold, price, discount_pct)
  select p_id, (e.o - 1)::int, e.v ->> 'name', e.v ->> 'name_ar', e.v ->> 'strength', e.v ->> 'form', (e.v ->> 'qty')::numeric, e.v ->> 'unit', (e.v ->> 'expiry')::date,
         e.v ->> 'source', e.v ->> 'origin_country', e.v ->> 'pack_state', coalesce((e.v ->> 'cold')::boolean, false), (e.v ->> 'price')::numeric, (e.v ->> 'discount_pct')::numeric
    from jsonb_array_elements(p_lines) with ordinality as e(v, o)
   limit 300;
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function public.listing_lines_replace(bigint, jsonb) from public, anon, authenticated, service_role;
grant execute on function public.listing_lines_replace(bigint, jsonb) to authenticated, service_role;

create or replace function public.listing_renew(p_id bigint) returns timestamptz language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; v timestamptz;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and user_id = me for update;
  if p.id is null then raise exception 'Only the listing''s owner can renew it' using errcode = '42501'; end if;
  if p.status = 'draft' then raise exception 'Publish the draft first' using errcode = '22023'; end if;
  if p.closed_reason = 'sold' then raise exception 'A sold listing is not renewed — post a new one' using errcode = '22023'; end if;
  update public.products set renewed_at = now(), bumped_at = now(), status = case when status = 'closed' then 'active' else status end,
         closed_reason = case when status = 'closed' then null else closed_reason end
   where id = p_id returning expires_at into v;
  return v;
end $$;
revoke all on function public.listing_renew(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_renew(bigint) to authenticated, service_role;

drop trigger if exists trg_deal_events_agree_guard on public.deal_events;
drop function if exists public.deal_events_agree_guard();

notify pgrst, 'reload schema';
