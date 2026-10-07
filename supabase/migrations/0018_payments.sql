-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0018 — payments (step E4)
-- Card and mobile wallets (Vodafone Cash, Orange, e&, WE Pay) through Paymob; Fawry reference numbers through FawryPay;
-- InstaPay by transfer + receipt, confirmed by the Drugbox team (InstaPay has no public merchant API).
-- Amounts come from payment_products only. Orders are created and paid only through these functions;
-- confirm_payment can be called only by the server (webhooks, after their signature is checked).
-- ═════════════════════════════════════════════════════════════════════
create table if not exists public.payment_products (
  code text primary key, label text not null, kind text not null check (kind in ('vip','boost','featured')),
  amount_egp numeric(12,2) not null check (amount_egp > 0), vat_rate numeric(4,3) not null default 0.14,
  duration_days int not null check (duration_days > 0), active boolean not null default true
);
insert into public.payment_products (code, label, kind, amount_egp, duration_days) values
  ('vip_month', 'VIP — monthly', 'vip', 2500, 30), ('vip_year', 'VIP — yearly', 'vip', 25000, 365),
  ('boost', 'Marketplace boost', 'boost', 1450, 7), ('featured', 'Featured listing', 'featured', 3950, 30)   -- boost/featured: USD 29/79 at EGP 50 — set the real prices
on conflict (code) do nothing;
alter table public.payment_products enable row level security;
do $$ begin create policy "prices: everyone reads" on public.payment_products for select using (true);
exception when duplicate_object then null; end $$;
do $$ begin create policy "prices: Drugbox edits" on public.payment_products for update using (public.is_platform_admin()) with check (public.is_platform_admin());
exception when duplicate_object then null; end $$;

alter table public.products add column if not exists boosted_until timestamptz, add column if not exists featured_until timestamptz;

create table if not exists public.payment_orders (
  id           bigint generated always as identity primary key,
  user_id      uuid   not null references public.profiles(id) on delete cascade,
  product_code text   not null references public.payment_products(code),
  company_id   bigint references public.companies(id) on delete set null,
  listing_id   bigint references public.products(id) on delete set null,
  method       text   not null check (method in ('card','wallet','fawry','instapay')),
  amount_cents int    not null check (amount_cents > 0),
  currency     text   not null default 'EGP',
  status       text   not null default 'pending' check (status in ('pending','review','paid','failed','expired','refunded')),
  provider_ref text, transfer_ref text, receipt_path text, provider_payload jsonb,
  created_at   timestamptz not null default now(), paid_at timestamptz,
  merchant_ref text generated always as ('DBX' || id::text) stored
);
create index if not exists idx_payment_orders_user on public.payment_orders (user_id, created_at desc);
create index if not exists idx_payment_orders_review on public.payment_orders (status) where status = 'review';
alter table public.payment_orders enable row level security;
do $$ begin create policy "orders: you and Drugbox read" on public.payment_orders for select using (user_id = (select auth.uid()) or public.is_platform_admin());
exception when duplicate_object then null; end $$;

create or replace function public.create_order(p_product text, p_method text, p_company bigint default null, p_listing bigint default null)
returns public.payment_orders language plpgsql security definer set search_path = public as $$
declare pr public.payment_products; o public.payment_orders;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into pr from public.payment_products where code = p_product and active; if not found then raise exception 'Unknown product'; end if;
  if pr.kind = 'vip' and (p_company is null or not public.is_company_member(p_company, array['owner','admin'])) then raise exception 'Only the company''s owner or admins can upgrade it' using errcode = '42501'; end if;
  if pr.kind in ('boost','featured') and not exists (select 1 from public.products where id = p_listing and user_id = auth.uid()) then raise exception 'You can boost only your own listings' using errcode = '42501'; end if;
  insert into public.payment_orders (user_id, product_code, company_id, listing_id, method, amount_cents)
  values (auth.uid(), pr.code, case when pr.kind = 'vip' then p_company end, case when pr.kind <> 'vip' then p_listing end, p_method, round(pr.amount_egp * (1 + pr.vat_rate) * 100))
  returning * into o;
  return o;
end $$;

create or replace function public.activate_order(p_id bigint) returns void language plpgsql security definer set search_path = public as $$
declare o public.payment_orders; pr public.payment_products;
begin
  select * into o from public.payment_orders where id = p_id; select * into pr from public.payment_products where code = o.product_code;
  if pr.kind = 'vip' then
    update public.companies set plan = 'vip', vip_until = greatest(coalesce(vip_until, now()), now()) + make_interval(days => pr.duration_days) where id = o.company_id;
  elsif pr.kind = 'boost' then
    update public.products set boosted_until = greatest(coalesce(boosted_until, now()), now()) + make_interval(days => pr.duration_days) where id = o.listing_id;
  else
    update public.products set featured_until = greatest(coalesce(featured_until, now()), now()) + make_interval(days => pr.duration_days) where id = o.listing_id;
  end if;
  insert into public.notifications (user_id, type, message) values (o.user_id, 'payment', 'Payment received — ' || pr.label || ' is active');
end $$;
revoke all on function public.activate_order(bigint) from public, anon, authenticated;

-- called by the server only (Paymob / Fawry webhooks, after checking their signature)
create or replace function public.confirm_payment(p_merchant_ref text, p_provider_ref text, p_amount_cents int, p_payload jsonb)
returns text language plpgsql security definer set search_path = public as $$
declare o public.payment_orders;
begin
  select * into o from public.payment_orders where merchant_ref = p_merchant_ref for update;
  if not found then return 'unknown order'; end if;
  if o.status = 'paid' then return 'already paid'; end if;                      -- providers retry; never activate twice
  if o.status not in ('pending','review') then return 'order is ' || o.status; end if;
  if p_amount_cents <> o.amount_cents then
    update public.payment_orders set provider_payload = p_payload where id = o.id; return 'amount mismatch';
  end if;
  update public.payment_orders set status = 'paid', paid_at = now(), provider_ref = coalesce(p_provider_ref, provider_ref), provider_payload = p_payload where id = o.id;
  perform public.activate_order(o.id);
  return 'paid';
end $$;
revoke all on function public.confirm_payment(text, text, int, jsonb) from public, anon, authenticated;
grant execute on function public.confirm_payment(text, text, int, jsonb) to service_role;

create or replace function public.set_order_provider_ref(p_id bigint, p_ref text) returns void language sql security definer set search_path = public as $$
  update public.payment_orders set provider_ref = p_ref where id = p_id and status = 'pending'
$$;
revoke all on function public.set_order_provider_ref(bigint, text) from public, anon, authenticated;
grant execute on function public.set_order_provider_ref(bigint, text) to service_role;

-- InstaPay: the customer sends the transfer number and receipt; Drugbox confirms
create or replace function public.submit_instapay(p_id bigint, p_transfer_ref text, p_receipt text) returns void language plpgsql security definer set search_path = public as $$
begin
  update public.payment_orders set status = 'review', transfer_ref = left(trim(p_transfer_ref), 64), receipt_path = p_receipt
   where id = p_id and user_id = auth.uid() and method = 'instapay' and status = 'pending'
     and (p_receipt is null or p_receipt like 'payments/' || auth.uid()::text || '/%');
  if not found then raise exception 'This order cannot take a transfer' using errcode = '42501'; end if;
end $$;
create or replace function public.review_instapay(p_id bigint, p_ok boolean) returns void language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  if p_ok then
    update public.payment_orders set status = 'paid', paid_at = now() where id = p_id and status = 'review'; if not found then raise exception 'Not waiting for review'; end if;
    perform public.activate_order(p_id);
  else
    update public.payment_orders set status = 'failed' where id = p_id and status = 'review';
    insert into public.notifications (user_id, type, message) select user_id, 'payment', 'We could not match your InstaPay transfer — please check the number and receipt' from public.payment_orders where id = p_id;
  end if;
end $$;

-- receipts live in the private documents bucket under payments/<user>/ (the user and Drugbox read them)
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_platform_admin())
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text
    else false end
$$;

notify pgrst, 'reload schema';
