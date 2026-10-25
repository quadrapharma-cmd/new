-- ═════════════════════════════════════════════════════════════════════
-- 0072 — structured trade offers on the one listing table (W-01, W-02, W-04, W-05, W-06, W-07, W-13, W-14, W-15; design:
--        docs/areas/w-trade-design.md)
--   1. products gains: kind (the trade post kind; null = a classic listing of the approved forms), attrs (the kind's fields,
--      cleaned by trade_attrs_clean: allow-listed keys, typed, bounded), price_mode (amount / discount / ask) + discount_pct,
--      and server-only columns: item_key, roots, root_words, search_text, fingerprint, bumped_at, published_at,
--      closed_reason, docs_checked_at / docs_checked_by. status gains 'reserved' (shown with its badge; active = active or reserved).
--   2. listing_lines: the items of one post (name, Arabic name, strength, form, quantity + unit, expiry month, source + country,
--      pack state, cold chain, price / discount); written only by the listing's owner, keys derived by the database.
--   3. The database keeps kind → side (supply / demand), category and expiry; the item keys and the search text are computed
--      from the name, description, attrs and lines (trade_refresh); a structured listing is published only with its kind's
--      required fields (trade_missing); a company page posts as the company only when Drugbox verified it (owner's rule).
--   4. market_search(q, type, category, limit, offset, kind): canonical words (Arabic ⇄ English, Arabic-Indic digits, forms)
--      over search_text; the free renewal (bumped_at) orders listings after paid placement; reserved listings show.
--   5. my_listings(): kind, lines, reserved / sold.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. columns ────
alter table public.products add column if not exists kind            text;
alter table public.products add column if not exists attrs           jsonb not null default '{}'::jsonb;
alter table public.products add column if not exists price_mode      text;
alter table public.products add column if not exists discount_pct    numeric(5,2);
alter table public.products add column if not exists item_key        text;
alter table public.products add column if not exists roots           text[] not null default '{}';
alter table public.products add column if not exists root_words      text[] not null default '{}';
alter table public.products add column if not exists search_text     text;
alter table public.products add column if not exists fingerprint     text;
alter table public.products add column if not exists bumped_at       timestamptz;
alter table public.products add column if not exists published_at    timestamptz;
alter table public.products add column if not exists closed_reason   text;
alter table public.products add column if not exists docs_checked_at timestamptz;
alter table public.products add column if not exists docs_checked_by uuid references public.profiles(id) on delete set null;
alter table public.products drop constraint if exists products_status_chk;
alter table public.products add constraint products_status_chk check (status in ('active', 'paused', 'draft', 'closed', 'reserved'));
do $$ begin
  alter table public.products add constraint products_kind_chk check (kind is null or kind in
    ('stock', 'wanted', 'file_sale', 'file_wanted', 'company_sale', 'agency', 'distributor', 'toll', 'toll_wanted', 'materials'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.products add constraint products_price_mode_chk check (price_mode is null or price_mode in ('amount', 'discount', 'ask'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.products add constraint products_discount_chk check ((price_mode = 'discount') = (discount_pct is not null) and (discount_pct is null or (discount_pct > 0 and discount_pct <= 95)));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.products add constraint products_trade_len check (pg_column_size(attrs) <= 8192 and jsonb_typeof(attrs) = 'object' and cardinality(roots) <= 400
    and cardinality(root_words) <= 1200 and length(search_text) <= 60000 and (closed_reason is null or closed_reason in ('sold', 'withdrawn')));
exception when duplicate_object then null; end $$;
create index if not exists idx_products_search_trgm on public.products using gin (search_text gin_trgm_ops);
create index if not exists idx_products_root_words on public.products using gin (root_words);
create index if not exists idx_products_kind_open on public.products (kind, type) where active and kind is not null;
create index if not exists idx_products_fingerprint on public.products (user_id, fingerprint) where status in ('active', 'paused', 'reserved');
create index if not exists idx_products_bumped on public.products (type, (coalesce(bumped_at, created_at)) desc, id desc) where active;

-- ── 2. the kind's fields ────
-- spec per kind: key → 'text:N' · 'num:max' · 'int:max' · 'bool' · 'month' (YYYY-MM) · 'enum:a,b' · 'list:enum:a,b' · 'list:month' · 'gov' (governorates)
create or replace function public.trade_attr_spec() returns jsonb language sql immutable set search_path = public as $$ select '{
  "_common":     {"gov":"enum:cairo,giza,alex,qalyubia,sharqia,dakahlia,gharbia,monufia,beheira,kafr_el_sheikh,damietta,port_said,ismailia,suez,faiyum,beni_suef,minya,asyut,sohag,qena,luxor,aswan,red_sea,new_valley,matrouh,north_sinai,south_sinai",
                  "delivery":"enum:seller,buyer,shipping,agreement","urgent":"bool","credit_days":"int:365","currency":"enum:EGP,USD,EUR,SAR,AED,GBP,CNY,INR","moq":"text:80","coa":"bool"},
  "stock":       {},
  "materials":   {"sector":"enum:api,excipient,packaging,cosmetic,supplement","grade":"enum:bp_usp,ep,jp,na","origin":"text:80","lead":"text:80"},
  "wanted":      {"qty":"text:80","contract":"enum:one_time,annual,trial","needed_by":"month","target_price":"text:60","certs":"list:enum:usfda,eu_gmp,who_gmp,cep,iso,halal"},
  "file_sale":   {"authority":"enum:eda,sfda,dha,mohap,jfda,other","reg_type":"enum:human,supplement,cosmetic,device,vet","form":"text:60","strength":"text:60",
                  "decision":"enum:yes,no","stage":"enum:submitted,pricing,committee,analysis,notification,final","stages_done":"list:enum:submitted,pricing,committee,analysis,notification,final",
                  "notif_valid_until":"month","public_price":"num:10000000","pack":"text:60","price_increase":"enum:none,submitted,approved","asking_price":"text:60","commission":"text:40",
                  "included":"list:enum:brand,dossier,studies,artwork,stock,trademark,manufacturing","buyer_conditions":"list:enum:own_factory,toll_ok,licensed_warehouse,company_only",
                  "sales_units":"int:1000000000","factory":"text:120","reg_expiry":"month"},
  "file_wanted": {"authority":"enum:eda,sfda,dha,mohap,jfda,other","reg_type":"enum:human,supplement,cosmetic,device,vet","form":"text:60","stage":"enum:any,submitted,pricing,committee,analysis,notification,final",
                  "budget":"text:60","conditions":"text:200"},
  "company_sale":{"company_type":"enum:manufacturer,distributor,importer,scientific_office,warehouse,cosmetics,other","licensed":"bool","files_count":"int:100000","asking_price":"text:60","reason":"text:200"},
  "agency":      {"cats":"list:enum:medicines,supplements,cosmetics,devices,veterinary,herbal,baby,hospital","govs":"list:gov","exclusive":"bool","contract_years":"int:50","bonus_pct":"num:100","target":"text:80"},
  "distributor": {"cats":"list:enum:medicines,supplements,cosmetics,devices,veterinary,herbal,baby,hospital","govs":"list:gov","warehouses":"int:10000","cold_chain":"bool","fleet":"int:100000","agencies":"int:10000","reach":"text:120"},
  "toll":        {"forms":"list:enum:tab,cap,syrup,susp,amp,vial,supp,cream,oint,gel,drops,spray,sachet,eff,powder,lotion,solution","packs":"list:enum:blister,strip,bottle,tube,sachet,vial,amp,jar",
                  "min_batch":"text:80","lead_time":"text:80","free_months":"list:month","licensed":"bool","reg_contract":"bool","gmp":"enum:yes,no","gmp_by":"text:80","gmp_date":"month","capacity":"text:80"},
  "toll_wanted": {"forms":"list:enum:tab,cap,syrup,susp,amp,vial,supp,cream,oint,gel,drops,spray,sachet,eff,powder,lotion,solution","packs":"list:enum:blister,strip,bottle,tube,sachet,vial,amp,jar",
                  "batch":"text:80","by_when":"month","reg_contract":"bool"}
}'::jsonb $$;

create or replace function public.trade_govs() returns text[] language sql immutable set search_path = public as $$
  select string_to_array('cairo,giza,alex,qalyubia,sharqia,dakahlia,gharbia,monufia,beheira,kafr_el_sheikh,damietta,port_said,ismailia,suez,faiyum,beni_suef,minya,asyut,sohag,qena,luxor,aswan,red_sea,new_valley,matrouh,north_sinai,south_sinai', ',')
$$;

-- keeps only the keys the kind knows, each in its type; anything else is dropped (never stored)
create or replace function public.trade_attrs_clean(p_kind text, p_attrs jsonb) returns jsonb language plpgsql immutable set search_path = public as $$
declare spec jsonb := coalesce(public.trade_attr_spec() -> '_common', '{}') || coalesce(public.trade_attr_spec() -> p_kind, '{}');
        out jsonb := '{}'; k text; t text; v jsonb; s text; n numeric; arr jsonb; e jsonb; parts text[]; lim numeric;
begin
  if p_kind is null or jsonb_typeof(p_attrs) is distinct from 'object' then return '{}'; end if;
  for k, v in select * from jsonb_each(p_attrs) loop
    t := spec ->> k; if t is null or v is null or jsonb_typeof(v) = 'null' then continue; end if;
    parts := string_to_array(t, ':');
    if parts[1] = 'text' then
      s := btrim(regexp_replace(case jsonb_typeof(v) when 'string' then v #>> '{}' when 'number' then v::text else '' end, '[\x00-\x1f\x7f]', ' ', 'g'));
      if s <> '' then out := out || jsonb_build_object(k, left(s, parts[2]::int)); end if;
    elsif parts[1] in ('num', 'int') then
      begin n := (v #>> '{}')::numeric; exception when others then n := null; end;
      lim := parts[2]::numeric;
      if n is not null and n = n and n >= 0 and n <= lim then out := out || jsonb_build_object(k, case when parts[1] = 'int' then trunc(n) else round(n, 2) end); end if;
    elsif parts[1] = 'bool' then
      if jsonb_typeof(v) = 'boolean' then out := out || jsonb_build_object(k, v); end if;
    elsif parts[1] = 'month' then
      s := v #>> '{}'; if s ~ '^20[0-9]{2}-(0[1-9]|1[0-2])$' then out := out || jsonb_build_object(k, s); end if;
    elsif parts[1] = 'enum' then
      s := v #>> '{}'; if s = any(string_to_array(parts[2], ',')) then out := out || jsonb_build_object(k, s); end if;
    elsif parts[1] = 'list' then
      if jsonb_typeof(v) <> 'array' then continue; end if;
      arr := '[]';
      for e in select * from jsonb_array_elements(v) limit 40 loop
        s := e #>> '{}';
        if (parts[2] = 'enum' and s = any(string_to_array(parts[3], ','))) or (parts[2] = 'gov' and (s = 'all' or s = any(public.trade_govs())))
           or (parts[2] = 'month' and s ~ '^20[0-9]{2}-(0[1-9]|1[0-2])$') then
          if not arr @> jsonb_build_array(s) then arr := arr || jsonb_build_array(s); end if;
        end if;
      end loop;
      if jsonb_array_length(arr) > 0 then out := out || jsonb_build_object(k, arr); end if;
    end if;
  end loop;
  return out;
end $$;

-- what a kind still needs before it is published (null = nothing); EN — the page shows its own words for each
create or replace function public.trade_missing(p_kind text, p_attrs jsonb, p_id bigint, p_name text) returns text language plpgsql stable security definer set search_path = public as $$
declare a jsonb := coalesce(p_attrs, '{}');
begin
  if p_kind is null then return null; end if;
  if coalesce(btrim(p_name), '') = '' then return 'a name'; end if;
  if p_kind = 'stock' then
    if not exists (select 1 from public.listing_lines l where l.listing_id = p_id) then return 'at least one item (name and quantity)'; end if;
    if exists (select 1 from public.listing_lines l where l.listing_id = p_id and (coalesce(l.qty, 0) <= 0 or l.unit is null)) then return 'the quantity and unit of every item'; end if;
  elsif p_kind in ('file_sale') then
    if a ->> 'authority' is null then return 'the registering authority'; end if;
    if a ->> 'reg_type' is null then return 'the registration type'; end if;
    if a ->> 'stage' is null then return 'the file''s stage'; end if;
  elsif p_kind = 'file_wanted' then
    if a ->> 'reg_type' is null then return 'the registration type'; end if;
  elsif p_kind = 'toll' then
    if jsonb_array_length(coalesce(a -> 'forms', '[]')) = 0 then return 'the dosage forms'; end if;
    if a ->> 'min_batch' is null then return 'the minimum batch'; end if;
    if a ->> 'lead_time' is null then return 'the lead time'; end if;
    if a ->> 'gmp' is null then return 'GMP (yes with its date, or no)'; end if;
    if a ->> 'gmp' = 'yes' and (a ->> 'gmp_date' is null or a ->> 'gmp_by' is null) then return 'who issued the GMP and its date'; end if;
  elsif p_kind = 'toll_wanted' then
    if jsonb_array_length(coalesce(a -> 'forms', '[]')) = 0 then return 'the dosage forms'; end if;
  elsif p_kind in ('agency', 'distributor') then
    if jsonb_array_length(coalesce(a -> 'cats', '[]')) = 0 then return 'the product categories'; end if;
    if jsonb_array_length(coalesce(a -> 'govs', '[]')) = 0 then return 'the governorates'; end if;
  elsif p_kind = 'company_sale' then
    if a ->> 'company_type' is null then return 'the company type'; end if;
  end if;
  return null;
end $$;
revoke all on function public.trade_missing(text, jsonb, bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.trade_missing(text, jsonb, bigint, text) to authenticated, service_role;

-- ── 3. the items of one post ────
create table if not exists public.listing_lines (
  id             bigint generated always as identity primary key,
  listing_id     bigint not null references public.products(id) on delete cascade,
  pos            smallint not null default 0,
  name           text not null,
  name_ar        text,
  strength       text,
  form           text,
  qty            numeric(14,2),
  unit           text,
  expiry         date,
  source         text,
  origin_country text,
  pack_state     text,
  cold           boolean not null default false,
  price          numeric(14,2),
  discount_pct   numeric(5,2),
  item_key       text,
  root           text,
  search_text    text,
  created_at     timestamptz not null default now(),
  constraint listing_lines_len check (length(name) between 1 and 160 and length(name_ar) <= 160 and length(strength) <= 40 and length(form) <= 40
    and (qty is null or (qty > 0 and qty <= 100000000)) and (price is null or (price >= 0 and price <= 100000000)) and (discount_pct is null or (discount_pct > 0 and discount_pct <= 95))
    and (expiry is null or (expiry >= date '2020-01-01' and expiry <= date '2045-12-01' and extract(day from expiry) = 1))),
  constraint listing_lines_unit_chk check (unit is null or unit in ('box', 'strip', 'carton', 'pack', 'piece', 'bottle', 'tube', 'vial', 'amp', 'kg', 'g', 'l', 'ton', 'drum', 'bag')),
  constraint listing_lines_source_chk check (source is null or source in ('company', 'factory', 'authority', 'importer')),
  constraint listing_lines_pack_chk check (pack_state is null or pack_state in ('intact', 'opened', 'damaged', 'repacked')),
  constraint listing_lines_country_chk check (origin_country is null or origin_country ~ '^[A-Z]{2}$'));
create index if not exists idx_listing_lines_listing on public.listing_lines (listing_id, pos, id);
create index if not exists idx_listing_lines_root on public.listing_lines (root) where root <> '';
alter table public.listing_lines enable row level security;
do $$ begin
  create policy "listing lines: whoever reads the listing" on public.listing_lines for select to authenticated
    using (exists (select 1 from public.products p where p.id = listing_id));                     -- products' own policies decide
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "listing lines: the owner adds" on public.listing_lines for insert to authenticated
    with check (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid()) and p.status in ('draft', 'active', 'paused')));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "listing lines: the owner edits" on public.listing_lines for update to authenticated
    using (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid()) and p.status in ('draft', 'active', 'paused')))
    with check (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid()) and p.status in ('draft', 'active', 'paused')));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "listing lines: the owner removes" on public.listing_lines for delete to authenticated
    using (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid()) and p.status in ('draft', 'active', 'paused')));
exception when duplicate_object then null; end $$;
revoke all on public.listing_lines from public, anon, authenticated;
grant select on public.listing_lines to anon, authenticated;              -- anon: no rows (policies are for members), never an error
grant insert (listing_id, pos, name, name_ar, strength, form, qty, unit, expiry, source, origin_country, pack_state, cold, price, discount_pct) on public.listing_lines to authenticated;
grant update (pos, name, name_ar, strength, form, qty, unit, expiry, source, origin_country, pack_state, cold, price, discount_pct) on public.listing_lines to authenticated;
grant delete on public.listing_lines to authenticated;
grant all on public.listing_lines to service_role;
revoke all on sequence public.listing_lines_id_seq from public, anon, authenticated;
grant usage, select on sequence public.listing_lines_id_seq to authenticated, service_role;

-- a line's keys come from its words; at most 300 lines a listing
create or replace function public.listing_lines_derive() returns trigger language plpgsql set search_path = public as $$
declare w text := btrim(coalesce(new.name, '') || ' ' || coalesce(new.name_ar, '') || ' ' || coalesce(new.strength, '') || ' ' || coalesce(new.form, ''));
begin
  new.name := btrim(regexp_replace(new.name, '[\x00-\x1f\x7f]', ' ', 'g'));
  if tg_op = 'UPDATE' and new.listing_id is distinct from old.listing_id then raise exception 'An item stays on its listing' using errcode = '42501'; end if;
  if tg_op = 'INSERT' and (select count(*) from public.listing_lines l where l.listing_id = new.listing_id) >= 300 then
    raise exception 'A listing carries at most 300 items — post the rest as another listing' using errcode = '22023';
  end if;
  new.item_key := public.trade_key(w); new.root := public.trade_root(coalesce(new.name, '') || ' ' || coalesce(new.name_ar, ''));
  new.search_text := public.trade_search_text(w);
  return new;
end $$;
revoke all on function public.listing_lines_derive() from public, anon, authenticated, service_role;
drop trigger if exists trg_listing_lines_derive on public.listing_lines;
create trigger trg_listing_lines_derive before insert or update on public.listing_lines for each row execute function public.listing_lines_derive();

-- ── 4. the listing's derived columns ────
-- the words of the listing: name, description, the text of its attrs; the lines' keys are added by trade_refresh
create or replace function public.trade_text_of(p public.products) returns text language sql stable set search_path = public as $$
  select coalesce(p.name, '') || ' ' || coalesce(p.description, '') || ' ' ||
         coalesce((select string_agg(v, ' ') from jsonb_each_text(coalesce(p.attrs, '{}')) e(k, v) where k in ('form', 'strength', 'origin', 'factory', 'reach', 'target', 'gmp_by')), '')
$$;
revoke all on function public.trade_text_of(public.products) from public, anon;
grant execute on function public.trade_text_of(public.products) to authenticated, service_role;

-- computes item_key, roots, root_words, search_text, fingerprint of a listing row (lines read as the database)
create or replace function public.trade_compute(p public.products) returns public.products language plpgsql stable security definer set search_path = public as $$
declare t text := public.trade_text_of(p); lines_txt text; lines_roots text[]; lines_fp text; extra text[] := '{}';
begin
  select coalesce(string_agg(l.search_text, ' ' order by l.pos, l.id), ''), coalesce(array_agg(distinct l.root) filter (where l.root <> ''), '{}'),
         coalesce(string_agg(coalesce(l.item_key, '') || '/' || coalesce(l.qty::text, '') || '/' || coalesce(l.expiry::text, '') || '/' || coalesce(l.price::text, ''), ';' order by l.item_key, l.qty, l.id), '')
    into lines_txt, lines_roots, lines_fp from public.listing_lines l
   where l.listing_id = p.id and (auth.uid() is null or auth.uid() = p.user_id)          -- the caller's own listing only (a row passed in names its owner)
     and exists (select 1 from public.products x where x.id = p.id and x.user_id = p.user_id);
  -- toll: the dosage forms are what matches; agency / distributor: the categories
  if p.kind in ('toll', 'toll_wanted') then extra := array(select 'form:' || x from jsonb_array_elements_text(coalesce(p.attrs -> 'forms', '[]')) x); end if;
  if p.kind in ('agency', 'distributor') then extra := array(select 'cat:' || x from jsonb_array_elements_text(coalesce(p.attrs -> 'cats', '[]')) x); end if;
  p.item_key := nullif(public.trade_key(t), '');
  p.roots := (select coalesce(array_agg(distinct r), '{}') from unnest(lines_roots || case when public.trade_root(t) <> '' then array[public.trade_root(t)] else '{}'::text[] end || extra) r)[1:400];
  p.root_words := (select coalesce(array_agg(distinct w), '{}') from unnest(p.roots) r, unnest(string_to_array(r, ' ')) w where w <> '')[1:1200];
  p.search_text := left(public.trade_search_text(t) || lines_txt, 60000);
  p.fingerprint := md5(coalesce(p.kind, p.category, '') || '|' || coalesce(p.type, '') || '|' || public.trade_norm(p.name) || '|' || public.trade_norm(coalesce(p.description, '')) || '|' || lines_fp);
  return p;
end $$;
revoke all on function public.trade_compute(public.products) from public, anon, authenticated, service_role;
grant execute on function public.trade_compute(public.products) to authenticated, service_role;   -- the derive trigger runs as the caller

-- after the lines change, the listing's search text, keys and fingerprint follow (the owner wrote the line; the database writes the listing)
create or replace function public.trade_refresh(p_id bigint) returns void language plpgsql security definer set search_path = public as $$
declare p public.products;
begin
  select * into p from public.products where id = p_id; if p.id is null then return; end if;
  p := public.trade_compute(p);
  update public.products set item_key = p.item_key, roots = p.roots, root_words = p.root_words, search_text = p.search_text, fingerprint = p.fingerprint
   where id = p_id and (item_key, roots, root_words, search_text, fingerprint) is distinct from (p.item_key, p.roots, p.root_words, p.search_text, p.fingerprint);
end $$;
revoke all on function public.trade_refresh(bigint) from public, anon, authenticated, service_role;

create or replace function public.listing_lines_after() returns trigger language plpgsql security definer set search_path = public as $$
begin
  perform public.trade_refresh(coalesce(new.listing_id, old.listing_id));
  return null;
end $$;
revoke all on function public.listing_lines_after() from public, anon, authenticated, service_role;
drop trigger if exists trg_listing_lines_after on public.listing_lines;
create trigger trg_listing_lines_after after insert or update or delete on public.listing_lines for each row execute function public.listing_lines_after();

-- ── 5. what the browser may write on a listing ────
create or replace function public.products_trade_guard() returns trigger language plpgsql set search_path = public as $$   -- not a definer: is_server_call() sees the caller
declare v_co public.companies;
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
  -- the owner's rule: a company page posts trade offers as the company only with Drugbox's verification badge
  if new.company_id is not null and new.status in ('active', 'reserved') and (tg_op = 'INSERT' or new.company_id is distinct from old.company_id or old.status not in ('active', 'reserved', 'paused')) then
    select * into v_co from public.companies where id = new.company_id;
    if v_co.status is distinct from 'verified' then
      raise exception 'Your company page needs the Drugbox verification badge before it posts offers as the company — post as yourself, or ask for verification' using errcode = '42501';
    end if;
  end if;
  return new;
end $$;
revoke all on function public.products_trade_guard() from public, anon, authenticated, service_role;
drop trigger if exists trg_products_b_trade_guard on public.products;
create trigger trg_products_b_trade_guard before insert or update on public.products for each row execute function public.products_trade_guard();

-- status ⇄ active, currency, expiry (0054, now by kind), the kind's side / category / fields, derived keys, required fields, duplicates
create or replace function public.products_market_derive() returns trigger language plpgsql set search_path = public as $$
declare p text := coalesce(new.price, ''); dup bigint; miss text; going_live boolean;
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
  going_live := new.status = 'active' and (tg_op = 'INSERT' or old.status in ('draft', 'closed'));
  if going_live then
    miss := public.trade_missing(new.kind, new.attrs, new.id, new.name);
    if miss is not null then raise exception 'Add % before publishing', miss using errcode = '22023'; end if;
    -- W-07: the same member's same offer, already open → renew that one (merge) instead of posting it again
    select x.id into dup from public.products x where x.user_id = new.user_id and x.fingerprint = new.fingerprint and x.id <> new.id
       and x.status in ('active', 'paused', 'reserved') limit 1;
    if dup is not null then raise exception 'DUPLICATE:% — you already posted this offer; renew that one instead of posting it again', dup using errcode = '23505'; end if;
  end if;
  return new;
end $$;
revoke all on function public.products_market_derive() from public, anon, authenticated, service_role;

-- older rows get their keys, roots and search text
update public.products p set search_text = (c.r).search_text, item_key = (c.r).item_key, roots = (c.r).roots, root_words = (c.r).root_words, fingerprint = (c.r).fingerprint
  from (select x.id as pid, public.trade_compute(x) as r from public.products x where x.search_text is null) c where c.pid = p.id;

-- ── 6. the marketplace page: canonical words, renewals, reserved listings, the kind ────
drop function if exists public.market_search(text, text, text, int, int);
create or replace function public.market_search(p_q text default null, p_type text default null, p_category text default null, p_limit int default 40, p_offset int default 0, p_kind text default null)
returns jsonb language plpgsql stable security invoker set search_path = public set jit = off as $$
declare v_pats text[] := public.trade_query_patterns(p_q); v_lim int := least(greatest(coalesce(p_limit, 40), 1), 100); v_off int := greatest(coalesce(p_offset, 0), 0);
        v_total int; v_rows jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  with hits as (   -- the matching listings as (id, rank, time) only: counted and paged without carrying whole rows
    select p.id, coalesce(p.bumped_at, p.created_at) as at, case when p.featured_until > now() then 2 when p.boosted_until > now() then 1 else 0 end as rank
      from public.products p
     where p.active and (p.expires_at is null or p.expires_at > now())
       and (p_type is null or p.type = p_type) and (p_category is null or p.category = p_category) and (p_kind is null or p.kind = p_kind)
       and (cardinality(v_pats) = 0 or p.search_text like all (v_pats))),
  pg as (select h.id, h.rank, h.at from hits h order by h.rank desc, h.at desc, h.id desc limit v_lim offset v_off)
  select (select count(*)::int from hits), coalesce((select jsonb_agg(to_jsonb(x) order by x.rank desc, x.at desc, x.id desc) from (
      select h.id, h.user_id, h.name, h.category, h.type, h.price, h.unit, h.moq, h.description, h.emoji, h.docs, h.certs_verified, h.lead_time, h.currency,
             h.company_id, h.created_at, h.expires_at, h.boosted_until, h.featured_until, h.view_count, h.inquiry_count, (h.coa_path is not null) as has_coa,
             h.kind, h.attrs, h.price_mode, h.discount_pct, h.status, h.bumped_at, h.docs_checked_at, h.urgent, pg.rank, pg.at,
             (select count(*) from public.listing_lines l where l.listing_id = h.id)::int as lines_count,
             (select coalesce(jsonb_agg(jsonb_build_object('name', l.name, 'name_ar', l.name_ar, 'strength', l.strength, 'form', l.form, 'qty', l.qty, 'unit', l.unit,
                     'expiry', to_char(l.expiry, 'YYYY-MM'), 'source', l.source, 'origin_country', l.origin_country, 'pack_state', l.pack_state, 'cold', l.cold,
                     'price', l.price, 'discount_pct', l.discount_pct) order by l.pos, l.id), '[]')
                from (select * from public.listing_lines l2 where l2.listing_id = h.id order by l2.pos, l2.id limit 3) l) as lines,
             (select json_build_object('slug', c.slug, 'name', c.name, 'verified', c.status = 'verified') from public.companies c where c.id = h.company_id) as co
        from pg join public.products h on h.id = pg.id) x), '[]'::jsonb)
    into v_total, v_rows;
  return jsonb_build_object('total', v_total, 'rows', v_rows);
end $$;
revoke all on function public.market_search(text, text, text, int, int, text) from public, anon, authenticated, service_role;
grant execute on function public.market_search(text, text, text, int, int, text) to authenticated, service_role;

-- every item of one listing (the card's "N items" opens them)
create or replace function public.listing_items(p_id bigint) returns jsonb language sql stable security invoker set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', l.id, 'pos', l.pos, 'name', l.name, 'name_ar', l.name_ar, 'strength', l.strength, 'form', l.form, 'qty', l.qty, 'unit', l.unit,
           'expiry', to_char(l.expiry, 'YYYY-MM'), 'source', l.source, 'origin_country', l.origin_country, 'pack_state', l.pack_state, 'cold', l.cold,
           'price', l.price, 'discount_pct', l.discount_pct) order by l.pos, l.id), '[]')
    from public.listing_lines l where l.listing_id = p_id and auth.uid() is not null
$$;
revoke all on function public.listing_items(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_items(bigint) to authenticated, service_role;

-- my listings with the kind, the items and the state (reserved shows; sold / withdrawn leave the list)
create or replace function public.my_listings() returns jsonb language sql stable security invoker set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'emoji', p.emoji, 'category', p.category, 'type', p.type, 'status', p.status, 'price', p.price, 'moq', p.moq,
           'description', p.description, 'created_at', p.created_at, 'renewed_at', p.renewed_at, 'bumped_at', p.bumped_at, 'expires_at', p.expires_at, 'views', p.view_count,
           'inquiries', p.inquiry_count, 'boosted', (p.boosted_until > now() or p.featured_until > now()), 'company_id', p.company_id, 'kind', p.kind, 'attrs', p.attrs,
           'price_mode', p.price_mode, 'discount_pct', p.discount_pct, 'docs_checked_at', p.docs_checked_at,
           'lines', (select count(*) from public.listing_lines l where l.listing_id = p.id)) order by p.created_at desc, p.id desc), '[]'::jsonb)
  from (select * from public.products where user_id = auth.uid() and status <> 'closed' order by created_at desc limit 200) p
$$;
revoke all on function public.my_listings() from public, anon, authenticated, service_role;
grant execute on function public.my_listings() to authenticated, service_role;

notify pgrst, 'reload schema';
