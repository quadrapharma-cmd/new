-- ═════════════════════════════════════════════════════════════════════
-- 0055 — paying Drugbox, completed (B-14, B-15, B-16; J-BUSINESS-13, 42–48)
--   1. Every order keeps its VAT split as the server computed it (net_cents + vat_cents = amount_cents, from payment_products at
--      the time of the order) and, once paid, a sequential tax-invoice number (DBX-INV-<year>-<000001>) assigned by the database
--      in the same transaction that marks it paid (confirm_payment, review_instapay) — never by the browser.
--      order_invoice(order) gives the buyer (and Drugbox) the invoice's data: seller from billing_settings (Drugbox admins set
--      the legal name / tax registration number / address), buyer, company, product, net, VAT 14 %, total, method, dates.
--   2. A Fawry reference keeps its expiry (fawry_expires_at, stored by payments-create through set_order_provider_ref) so the
--      buyer finds it again in My payments until it is paid or expires.
--   3. A payment that did not go through is recorded: fail_payment(provider, order key, …) (server-only, called by the signed
--      webhooks) marks a pending card / wallet order 'failed', a Fawry reference 'expired' (Fawry's EXPIRED / FAILED
--      notification), and tells the buyer. Nothing is activated.
--   4. create_order refuses a second pending Fawry (or InstaPay) order for the same thing by the same method (the first reference or
--      transfer is still payable — the buyer is sent to it; another method stays possible), and a new card / wallet order supersedes the older pending card / wallet ones for the
--      same thing (they become 'expired', provider_payload.superseded). A late callback for a superseded order is still honoured
--      by confirm_payment (the money arrived: it activates), so no payment is ever lost.
--   5. VIP perks: a VIP company has 3 included Marketplace boosts per calendar month. use_included_boost(listing, company)
--      (SECURITY DEFINER) checks that the caller owns the listing and manages a company whose VIP is current, counts this
--      month's uses under a row lock (two clicks at once cannot both take the last one) and boosts the listing for 7 days
--      (payment_products 'boost' duration). included_boosts_left(company) tells the window. Uses are kept in vip_boost_uses.
--   6. vip_reminders(): a notice 3 days before a VIP plan ends (daily with expire_vip_plans when pg_cron is enabled).
--   7. (verification follow-ups) a payment that could not start (the provider refused or was unreachable) is closed at once by
--      payment_start_failed (server-only, called by payments-create) — it never blocks a new payment; only a Fawry order WITH a
--      reference that has not expired counts as "already have a reference" (and the message names that Fawry reference).
--      The buyer may cancel their own pending, unpaid order (cancel_order → 'cancelled'); a cancelled order is never activated
--      (a late payment for it is recorded and Drugbox is told a refund is due). VIP cannot be bought for a suspended company,
--      a paid boost / Featured only for an active listing, and a second InstaPay order waits while one is under review.
--      submit_instapay accepts only a receipt path payments/<buyer>/<safe file name>.
--      Each invoice keeps what it said when it was issued (invoice_snapshot: product, days, VAT rate, seller, buyer, company):
--      later price, VAT or seller changes never rewrite an issued invoice; a refunded order's invoice still opens (marked refunded).
-- Money rules: amounts only from payment_products; confirm_payment / activate_order / set_order_provider_ref / fail_payment stay
-- server-only; the browser never writes an order (no insert/update grants), a plan, a boost date, a status or an invoice number.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. VAT split and invoice numbers ────
alter table public.payment_orders add column if not exists net_cents        integer;
alter table public.payment_orders add column if not exists vat_cents        integer;
alter table public.payment_orders add column if not exists invoice_no       text;
alter table public.payment_orders add column if not exists fawry_expires_at timestamptz;
alter table public.payment_orders add column if not exists invoice_snapshot jsonb;
-- the buyer can cancel a pending, unpaid order ('cancelled')
alter table public.payment_orders drop constraint if exists payment_orders_status_check;
alter table public.payment_orders add constraint payment_orders_status_check check (status in ('pending','review','paid','failed','expired','refunded','cancelled'));
create unique index if not exists idx_payment_orders_invoice_no on public.payment_orders (invoice_no) where invoice_no is not null;
create index if not exists idx_payment_orders_pending_target on public.payment_orders (user_id, product_code, coalesce(listing_id, 0), coalesce(company_id, 0)) where status = 'pending';
-- orders made before this migration: the split as create_order computed the total (VAT 14 %)
update public.payment_orders o set net_cents = round(o.amount_cents / (1 + p.vat_rate)), vat_cents = o.amount_cents - round(o.amount_cents / (1 + p.vat_rate))
  from public.payment_products p where p.code = o.product_code and o.net_cents is null;
do $$ begin
  alter table public.payment_orders add constraint payment_orders_vat_split check (net_cents is null or (net_cents > 0 and vat_cents >= 0 and net_cents + vat_cents = amount_cents));
exception when duplicate_object then null; end $$;

create sequence if not exists public.payment_invoice_seq;
revoke all on sequence public.payment_invoice_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.payment_invoice_seq to service_role;

-- the seller's details printed on every invoice (one row; Drugbox admins fill them in — waiting on the owner)
create table if not exists public.billing_settings (
  id          boolean primary key default true check (id),
  legal_name  text not null default 'Drugbox' check (length(legal_name) between 2 and 200),
  tax_reg_no  text check (length(tax_reg_no) <= 40),
  address     text check (length(address) <= 300),
  email       text check (length(email) <= 320),
  updated_at  timestamptz not null default now()
);
insert into public.billing_settings (id) values (true) on conflict do nothing;
alter table public.billing_settings enable row level security;
do $$ begin
  create policy "billing settings: signed-in members read" on public.billing_settings for select to authenticated using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "billing settings: Drugbox admins edit" on public.billing_settings for update to authenticated using (public.is_platform_admin()) with check (public.is_platform_admin());
exception when duplicate_object then null; end $$;
revoke all on public.billing_settings from public, anon, authenticated, service_role;
grant select, update on public.billing_settings to authenticated;
grant all on public.billing_settings to service_role;

create or replace function public.assign_invoice_no(p_id bigint) returns text language plpgsql security definer set search_path = public as $$
declare v text;
begin
  update public.payment_orders set invoice_no = 'DBX-INV-' || to_char(coalesce(paid_at, now()), 'YYYY') || '-' || lpad(nextval('public.payment_invoice_seq')::text, 6, '0')
   where id = p_id and status = 'paid' and invoice_no is null returning invoice_no into v;
  return coalesce(v, (select invoice_no from public.payment_orders where id = p_id));
end $$;
revoke all on function public.assign_invoice_no(bigint) from public, anon, authenticated, service_role;
grant execute on function public.assign_invoice_no(bigint) to service_role;

-- whatever marks an order paid (a webhook, Drugbox's review, a correction by the service role), the paid order gets its split
-- and its invoice number in the same statement
create or replace function public.payment_orders_paid() returns trigger language plpgsql security definer set search_path = public as $$
declare r numeric;
begin
  if new.net_cents is null then
    select vat_rate into r from public.payment_products where code = new.product_code;
    new.net_cents := round(new.amount_cents / (1 + coalesce(r, 0.14))); new.vat_cents := new.amount_cents - new.net_cents;
  end if;
  if tg_op = 'UPDATE' and old.invoice_no is not null then           -- an issued invoice never changes (number and contents)
    new.invoice_no := old.invoice_no; new.invoice_snapshot := coalesce(old.invoice_snapshot, new.invoice_snapshot);
  end if;
  if new.status = 'paid' and new.invoice_no is null then
    new.paid_at := coalesce(new.paid_at, now());
    new.invoice_no := 'DBX-INV-' || to_char(new.paid_at, 'YYYY') || '-' || lpad(nextval('public.payment_invoice_seq')::text, 6, '0');
  end if;
  if new.invoice_no is not null and new.invoice_snapshot is null then   -- what the invoice says, fixed when its number is assigned
    select jsonb_build_object('product', pr.label, 'kind', pr.kind, 'days', pr.duration_days, 'vat_rate', pr.vat_rate,
             'seller', (select jsonb_build_object('name', b.legal_name, 'tax_reg_no', b.tax_reg_no, 'address', b.address, 'email', b.email) from public.billing_settings b limit 1),
             'buyer', (select jsonb_build_object('name', p.name) from public.profiles p where p.id = new.user_id),
             'company', (select jsonb_build_object('name', c.name, 'registry', c.registry, 'address', coalesce(c.location, c.city)) from public.companies c where c.id = new.company_id),
             'listing', (select l.name from public.products l where l.id = new.listing_id))
      into new.invoice_snapshot from public.payment_products pr where pr.code = new.product_code;
  end if;
  return new;
end $$;
revoke all on function public.payment_orders_paid() from public, anon, authenticated, service_role;
drop trigger if exists trg_payment_orders_paid on public.payment_orders;
create trigger trg_payment_orders_paid before insert or update on public.payment_orders for each row execute function public.payment_orders_paid();
update public.payment_orders set status = status where (status = 'paid' and invoice_no is null) or (invoice_no is not null and invoice_snapshot is null);

-- ── 4. create_order: the split, no duplicate payable Fawry / InstaPay, card / wallet supersede ────
create or replace function public.create_order(p_product text, p_method text, p_company bigint default null, p_listing bigint default null)
returns public.payment_orders language plpgsql security definer set search_path = public as $$
declare pr public.payment_products; o public.payment_orders; v_total int; v_net int; v_company bigint; v_listing bigint; dup public.payment_orders;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if p_method is null or p_method not in ('card','wallet','fawry','instapay') then raise exception 'Choose a payment method' using errcode = '22023'; end if;
  select * into pr from public.payment_products where code = p_product and active; if not found then raise exception 'Unknown product'; end if;
  if pr.kind = 'vip' and (p_company is null or not public.is_company_member(p_company, array['owner','admin'])) then raise exception 'Only the company''s owner or admins can upgrade it' using errcode = '42501'; end if;
  if pr.kind = 'vip' and exists (select 1 from public.companies where id = p_company and status = 'suspended') then
    raise exception 'This company page is suspended — VIP cannot be bought for it' using errcode = '42501';
  end if;
  if pr.kind in ('boost','featured') and not exists (select 1 from public.products where id = p_listing and user_id = auth.uid()) then raise exception 'You can boost only your own listings' using errcode = '42501'; end if;
  if pr.kind in ('boost','featured') and not exists (select 1 from public.products where id = p_listing and active) then
    raise exception 'This listing is not active — publish it again before promoting it' using errcode = '42501';
  end if;
  v_company := case when pr.kind = 'vip' then p_company end; v_listing := case when pr.kind <> 'vip' then p_listing end;
  perform pg_advisory_xact_lock(hashtext('drugbox.order.' || auth.uid()::text));   -- one order at a time per buyer (two clicks make one order)
  -- a Fawry order that never got its reference (the provider call failed or never returned) can never be paid: closed, never blocking
  update public.payment_orders x set status = 'failed', provider_payload = coalesce(x.provider_payload, '{}'::jsonb) || jsonb_build_object('start_failed', true)
   where x.user_id = auth.uid() and x.product_code = pr.code and coalesce(x.listing_id, 0) = coalesce(v_listing, 0) and coalesce(x.company_id, 0) = coalesce(v_company, 0)
     and x.status = 'pending' and x.method = 'fawry' and x.provider_ref is null;
  -- still payable: a Fawry reference that has not expired, an InstaPay order waiting for its transfer or being checked by Drugbox
  select * into dup from public.payment_orders x
   where x.user_id = auth.uid() and x.product_code = pr.code and coalesce(x.listing_id, 0) = coalesce(v_listing, 0) and coalesce(x.company_id, 0) = coalesce(v_company, 0)
     and x.method = p_method
     and ((x.method = 'fawry' and x.status = 'pending' and x.provider_ref is not null and x.fawry_expires_at is not null and x.fawry_expires_at > now())
          or (x.method = 'instapay' and x.status in ('pending','review')))
   order by x.id desc limit 1;
  if dup.id is not null then
    raise exception '%', case when dup.method = 'fawry' then 'You already have a Fawry reference for this (' || dup.provider_ref || ') — pay it or find it in My payments'
                              when dup.status = 'review' then 'Your InstaPay transfer for this (' || dup.merchant_ref || ') is being checked by Drugbox — wait for the confirmation in My payments'
                              else 'You already have an InstaPay payment waiting for this (' || dup.merchant_ref || ') — send the transfer from My payments' end using errcode = '23505';
  end if;
  update public.payment_orders x set status = 'expired', provider_payload = coalesce(x.provider_payload, '{}'::jsonb) || jsonb_build_object('superseded', true)
   where x.user_id = auth.uid() and x.product_code = pr.code and coalesce(x.listing_id, 0) = coalesce(v_listing, 0) and coalesce(x.company_id, 0) = coalesce(v_company, 0)
     and x.status = 'pending' and x.method in ('card','wallet');
  v_total := round(pr.amount_egp * (1 + pr.vat_rate) * 100); v_net := round(pr.amount_egp * 100);
  insert into public.payment_orders (user_id, product_code, company_id, listing_id, method, amount_cents, net_cents, vat_cents)
  values (auth.uid(), pr.code, v_company, v_listing, p_method, v_total, v_net, v_total - v_net)
  returning * into o;
  return o;
end $$;
revoke all on function public.create_order(text, text, bigint, bigint) from public, anon, authenticated, service_role;
grant execute on function public.create_order(text, text, bigint, bigint) to authenticated, service_role;

-- ── 7. a payment that could not start: payments-create closes the order at once (server-only) ────
create or replace function public.payment_start_failed(p_id bigint, p_detail jsonb default null) returns text language plpgsql security definer set search_path = public as $$
declare o public.payment_orders;
begin
  select * into o from public.payment_orders where id = p_id for update;
  if not found then return 'unknown order'; end if;
  if o.status <> 'pending' then return 'order is ' || o.status; end if;      -- a paid or reviewed order is never turned back
  update public.payment_orders set status = 'failed', provider_payload = coalesce(provider_payload, '{}'::jsonb) || jsonb_build_object('start_failed', true, 'detail', p_detail) where id = p_id;
  return 'failed';
end $$;
revoke all on function public.payment_start_failed(bigint, jsonb) from public, anon, authenticated, service_role;
grant execute on function public.payment_start_failed(bigint, jsonb) to service_role;

-- ── 7. the buyer cancels their own pending, unpaid order (never a paid one, nor an InstaPay transfer Drugbox is checking) ────
create or replace function public.cancel_order(p_id bigint) returns text language plpgsql security definer set search_path = public as $$
declare o public.payment_orders;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into o from public.payment_orders where id = p_id for update;      -- the same row lock as confirm_payment: one of them wins
  if o.id is null or o.user_id <> auth.uid() then raise exception 'This order is not yours' using errcode = '42501'; end if;
  if o.status <> 'pending' then raise exception 'Only a payment that is still waiting can be cancelled (this one is %)', o.status using errcode = '22023'; end if;
  update public.payment_orders set status = 'cancelled', provider_payload = coalesce(provider_payload, '{}'::jsonb) || jsonb_build_object('cancelled_by_buyer', now()) where id = p_id;
  return 'cancelled';
end $$;
revoke all on function public.cancel_order(bigint) from public, anon, authenticated, service_role;
grant execute on function public.cancel_order(bigint) to authenticated, service_role;

-- InstaPay: the transfer number and a receipt the buyer uploaded to their own folder (payments/<buyer>/<file name>)
create or replace function public.submit_instapay(p_id bigint, p_transfer_ref text, p_receipt text) returns void language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if length(trim(coalesce(p_transfer_ref, ''))) not between 3 and 64 then raise exception 'Enter the transfer number from the InstaPay confirmation' using errcode = '22023'; end if;
  if p_receipt is not null and (position('..' in p_receipt) > 0 or p_receipt !~ ('^payments/' || auth.uid()::text || '/[A-Za-z0-9][A-Za-z0-9._-]{0,120}$')) then
    raise exception 'The receipt must be a file you uploaded' using errcode = '42501';
  end if;
  update public.payment_orders set status = 'review', transfer_ref = left(trim(p_transfer_ref), 64), receipt_path = p_receipt
   where id = p_id and user_id = auth.uid() and method = 'instapay' and status = 'pending';
  if not found then raise exception 'This order cannot take a transfer' using errcode = '42501'; end if;
end $$;
revoke all on function public.submit_instapay(bigint, text, text) from public, anon, authenticated, service_role;
grant execute on function public.submit_instapay(bigint, text, text) to authenticated, service_role;

-- ── 2. the Fawry reference keeps its expiry ────
drop function if exists public.set_order_provider_ref(bigint, text, text);
create or replace function public.set_order_provider_ref(p_id bigint, p_ref text, p_order text default null, p_expires timestamptz default null)
returns void language sql security definer set search_path = public as $$
  update public.payment_orders set provider_ref = p_ref, provider_order = coalesce(p_order, provider_order),
         fawry_expires_at = case when method = 'fawry' then coalesce(p_expires, fawry_expires_at) else fawry_expires_at end
   where id = p_id and status = 'pending'
$$;
revoke all on function public.set_order_provider_ref(bigint, text, text, timestamptz) from public, anon, authenticated, service_role;
grant execute on function public.set_order_provider_ref(bigint, text, text, timestamptz) to service_role;

-- ── confirm_payment: invoice number; a superseded card / wallet order is still honoured ────
create or replace function public.confirm_payment(p_provider text, p_order_key text, p_provider_ref text, p_amount_cents integer, p_currency text, p_payload jsonb)
returns text language plpgsql security definer set search_path = public as $$
declare o public.payment_orders;
begin
  if p_provider = 'paymob' then
    select * into o from public.payment_orders where provider_order = p_order_key and method in ('card','wallet') for update;
  elsif p_provider = 'fawry' then
    select * into o from public.payment_orders where merchant_ref = p_order_key and method = 'fawry' for update;
  else
    return 'unknown provider';
  end if;
  if not found or p_order_key is null or p_order_key = '' then return 'unknown order'; end if;
  if p_provider = 'fawry' and (o.provider_ref is null or p_provider_ref is distinct from o.provider_ref) then return 'reference mismatch'; end if;
  if o.status = 'paid' then return 'already paid'; end if;                      -- providers retry; never activate twice
  if o.status = 'cancelled' then                                                -- the buyer cancelled it: never activated; if money arrived, Drugbox refunds
    if not coalesce((o.provider_payload ->> 'paid_after_cancel')::boolean, false) then
      update public.payment_orders set provider_payload = coalesce(provider_payload, '{}'::jsonb) || coalesce(p_payload, '{}'::jsonb) || jsonb_build_object('paid_after_cancel', true) where id = o.id;
      insert into public.notifications (user_id, type, message)
      select p.id, 'payment', 'Order ' || o.merchant_ref || ' was paid after the buyer cancelled it — nothing was activated; refund due' from public.profiles p where p.role = 'admin';
    end if;
    return 'order is cancelled (refund due)';
  end if;
  if not (o.status = 'pending' or (o.status in ('expired','failed') and o.method in ('card','wallet'))) then return 'order is ' || o.status; end if;   -- a superseded or retried card order paid late: the money arrived
  if p_amount_cents is distinct from o.amount_cents then
    update public.payment_orders set provider_payload = coalesce(provider_payload, '{}'::jsonb) || coalesce(p_payload, '{}'::jsonb) where id = o.id; return 'amount mismatch';
  end if;
  if upper(coalesce(p_currency, '')) <> upper(o.currency) then
    update public.payment_orders set provider_payload = coalesce(provider_payload, '{}'::jsonb) || coalesce(p_payload, '{}'::jsonb) where id = o.id; return 'currency mismatch';
  end if;
  if p_provider_ref is not null and exists (select 1 from public.payment_orders x where x.id <> o.id and x.status = 'paid'
                                              and x.provider_ref = p_provider_ref and (x.method = 'fawry') = (o.method = 'fawry')) then
    update public.payment_orders set provider_payload = coalesce(provider_payload, '{}'::jsonb) || coalesce(p_payload, '{}'::jsonb) where id = o.id; return 'transaction already used';
  end if;
  update public.payment_orders set status = 'paid', paid_at = now(), provider_ref = coalesce(p_provider_ref, provider_ref),
         provider_payload = coalesce(provider_payload, '{}'::jsonb) || coalesce(p_payload, '{}'::jsonb) where id = o.id;
  perform public.assign_invoice_no(o.id);
  if public.activate_order(o.id) then return 'paid'; end if;
  return 'paid, not activated (refund due)';
end $$;
revoke all on function public.confirm_payment(text, text, text, integer, text, jsonb) from public, anon, authenticated, service_role;
grant execute on function public.confirm_payment(text, text, text, integer, text, jsonb) to service_role;

-- ── 3. a payment that did not go through ────
create or replace function public.fail_payment(p_provider text, p_order_key text, p_provider_ref text, p_status text, p_payload jsonb)
returns text language plpgsql security definer set search_path = public as $$
declare o public.payment_orders; pr public.payment_products; v_new text;
begin
  if p_provider = 'paymob' then
    select * into o from public.payment_orders where provider_order = p_order_key and method in ('card','wallet') for update;
  elsif p_provider = 'fawry' then
    select * into o from public.payment_orders where merchant_ref = p_order_key and method = 'fawry' for update;
    if found and (o.provider_ref is null or p_provider_ref is distinct from o.provider_ref) then return 'reference mismatch'; end if;
  else return 'unknown provider'; end if;
  if not found then return 'unknown order'; end if;
  if o.status <> 'pending' then return 'order is ' || o.status; end if;            -- a paid order is never turned back
  v_new := case when p_provider = 'fawry' and upper(coalesce(p_status, '')) in ('EXPIRED', 'CANCELED', 'CANCELLED') then 'expired' else 'failed' end;
  update public.payment_orders set status = v_new, provider_payload = coalesce(provider_payload, '{}'::jsonb) || coalesce(p_payload, '{}'::jsonb) where id = o.id;
  select * into pr from public.payment_products where code = o.product_code;
  insert into public.notifications (user_id, type, message)
  values (o.user_id, 'payment', case when v_new = 'expired' then 'Your Fawry reference for ' || pr.label || ' (' || o.merchant_ref || ') expired — nothing was charged; start a new payment from My payments'
                                     else 'Your payment for ' || pr.label || ' (' || o.merchant_ref || ') did not go through — nothing was activated; try again from My payments' end);
  return v_new;
end $$;
revoke all on function public.fail_payment(text, text, text, text, jsonb) from public, anon, authenticated, service_role;
grant execute on function public.fail_payment(text, text, text, text, jsonb) to service_role;

-- ── InstaPay: confirmed by Drugbox — invoice number too ────
create or replace function public.review_instapay(p_id bigint, p_ok boolean)
returns void language plpgsql security definer set search_path = public as $$
declare who uuid;
begin
  if not public.is_platform_admin() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  if p_ok then
    update public.payment_orders set status = 'paid', paid_at = now() where id = p_id and status = 'review'; if not found then raise exception 'Not waiting for review'; end if;
    perform public.assign_invoice_no(p_id);
    perform public.activate_order(p_id);
  else
    update public.payment_orders set status = 'failed' where id = p_id and status = 'review' returning user_id into who;
    if not found then raise exception 'Not waiting for review'; end if;
    insert into public.notifications (user_id, type, message) values (who, 'payment', 'We could not match your InstaPay transfer — please check the number and receipt');
  end if;
end $$;
revoke all on function public.review_instapay(bigint, boolean) from public, anon, authenticated, service_role;
grant execute on function public.review_instapay(bigint, boolean) to authenticated, service_role;

-- the invoice / receipt of one paid (or later refunded) order — its buyer, the managers of its company, or Drugbox. It prints what
-- the invoice said when its number was assigned (invoice_snapshot), never today's prices, VAT rate or seller details.
create or replace function public.order_invoice(p_id bigint) returns jsonb language plpgsql stable security definer set search_path = public as $$
declare o public.payment_orders; pr public.payment_products; b public.billing_settings; sn jsonb; v jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into o from public.payment_orders where id = p_id;
  if o.id is null or not (o.user_id = auth.uid() or public.is_platform_admin() or (o.company_id is not null and public.is_company_member(o.company_id, array['owner','admin']))) then
    raise exception 'This invoice is not yours' using errcode = '42501';
  end if;
  if o.status not in ('paid','refunded') or o.invoice_no is null then raise exception 'An invoice is issued once the payment is confirmed' using errcode = '22023'; end if;
  sn := o.invoice_snapshot;
  if sn is null then                                                            -- (only an order paid before snapshots existed and not yet backfilled)
    select * into pr from public.payment_products where code = o.product_code; select * into b from public.billing_settings limit 1;
    sn := jsonb_build_object('product', pr.label, 'days', pr.duration_days, 'vat_rate', pr.vat_rate,
            'seller', jsonb_build_object('name', b.legal_name, 'tax_reg_no', b.tax_reg_no, 'address', b.address, 'email', b.email),
            'buyer', (select jsonb_build_object('name', p.name) from public.profiles p where p.id = o.user_id),
            'company', (select jsonb_build_object('name', c.name, 'registry', c.registry, 'address', coalesce(c.location, c.city)) from public.companies c where c.id = o.company_id),
            'listing', (select l.name from public.products l where l.id = o.listing_id));
  end if;
  v := jsonb_build_object('invoice_no', o.invoice_no, 'issued_at', o.paid_at, 'order', o.merchant_ref, 'method', o.method, 'status', o.status, 'refunded', o.status = 'refunded',
         'product', sn->>'product', 'days', (sn->>'days')::int, 'net', o.net_cents / 100.0, 'vat', o.vat_cents / 100.0, 'vat_rate', (sn->>'vat_rate')::numeric,
         'total', o.amount_cents / 100.0, 'currency', o.currency, 'seller', sn->'seller', 'buyer', sn->'buyer', 'company', sn->'company', 'listing', sn->>'listing');
  return v;
end $$;
revoke all on function public.order_invoice(bigint) from public, anon, authenticated, service_role;
grant execute on function public.order_invoice(bigint) to authenticated, service_role;

-- My payments: my orders, and those of the companies I manage (a company's billing is shared by its owners and admins)
create or replace function public.my_payments(p_company bigint default null) returns jsonb language sql stable security definer set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'order', o.merchant_ref, 'product', pr.label, 'kind', pr.kind, 'code', o.product_code, 'method', o.method,
           'status', case when o.status = 'pending' and o.method = 'fawry' and o.fawry_expires_at <= now() then 'expired' else o.status end,
           'total', o.amount_cents / 100.0, 'net', o.net_cents / 100.0, 'vat', o.vat_cents / 100.0, 'created_at', o.created_at, 'paid_at', o.paid_at, 'invoice_no', o.invoice_no,
           'fawry_reference', case when o.method = 'fawry' then o.provider_ref end, 'fawry_expires_at', o.fawry_expires_at, 'transfer', o.transfer_ref,
           'listing_id', o.listing_id, 'listing', l.name, 'company_id', o.company_id, 'company', c.name, 'mine', o.user_id = auth.uid()) order by o.id desc), '[]'::jsonb)
  from (select * from public.payment_orders x
         where auth.uid() is not null
           and ((p_company is null and x.user_id = auth.uid())
                or (p_company is not null and x.company_id = p_company and public.is_company_member(p_company, array['owner','admin'])))
           and not (x.status = 'expired' and x.provider_payload ? 'superseded')
           and not (x.status = 'failed' and x.provider_payload ? 'start_failed')   -- a payment that never started (nothing to pay, nothing to show)
         order by x.id desc limit 100) o
  join public.payment_products pr on pr.code = o.product_code
  left join public.products l on l.id = o.listing_id
  left join public.companies c on c.id = o.company_id
$$;
revoke all on function public.my_payments(bigint) from public, anon, authenticated, service_role;
grant execute on function public.my_payments(bigint) to authenticated, service_role;

-- ── 5. VIP: 3 included Marketplace boosts per calendar month ────
create table if not exists public.vip_boost_uses (
  id         bigint generated always as identity primary key,
  company_id bigint not null references public.companies(id) on delete cascade,
  listing_id bigint references public.products(id) on delete set null,
  user_id    uuid references public.profiles(id) on delete set null,
  month      date not null,
  used_at    timestamptz not null default now()
);
create index if not exists idx_vip_boost_uses_company_month on public.vip_boost_uses (company_id, month);
create index if not exists idx_vip_boost_uses_listing on public.vip_boost_uses (listing_id) where listing_id is not null;
create index if not exists idx_vip_boost_uses_user on public.vip_boost_uses (user_id) where user_id is not null;
alter table public.vip_boost_uses enable row level security;
do $$ begin
  create policy "vip boosts: the company's managers read" on public.vip_boost_uses for select to authenticated
    using (public.is_company_member(company_id, array['owner','admin']) or public.is_platform_admin());
exception when duplicate_object then null; end $$;
revoke all on public.vip_boost_uses from public, anon, authenticated, service_role;
grant select on public.vip_boost_uses to authenticated;
grant all on public.vip_boost_uses to service_role;

create or replace function public.included_boosts_left(p_company bigint) returns int language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null or not public.is_company_member(p_company, array['owner','admin'])
              or not exists (select 1 from public.companies c where c.id = p_company and c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) and c.status <> 'suspended') then 0
         else greatest(0, 3 - (select count(*)::int from public.vip_boost_uses u where u.company_id = p_company and u.month = date_trunc('month', now())::date)) end
$$;
revoke all on function public.included_boosts_left(bigint) from public, anon, authenticated, service_role;
grant execute on function public.included_boosts_left(bigint) to authenticated, service_role;

create or replace function public.use_included_boost(p_listing bigint, p_company bigint) returns jsonb language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); c public.companies; n int; v_days int; v_until timestamptz;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not exists (select 1 from public.products where id = p_listing and user_id = me and active) then raise exception 'You can boost only your own active listings' using errcode = '42501'; end if;
  if not public.is_company_member(p_company, array['owner','admin']) then raise exception 'Only the company''s owner or admins can use its boosts' using errcode = '42501'; end if;
  select * into c from public.companies where id = p_company for update;              -- one use at a time per company: the count below cannot race
  if c.id is null or c.status = 'suspended' or c.plan <> 'vip' or (c.vip_until is not null and c.vip_until <= now()) then
    raise exception 'Included boosts come with VIP' using errcode = '42501';
  end if;
  select count(*) into n from public.vip_boost_uses where company_id = p_company and month = date_trunc('month', now())::date;
  if n >= 3 then raise exception 'All 3 included boosts of this month are used — they renew on the 1st' using errcode = '54000'; end if;
  select duration_days into v_days from public.payment_products where code = 'boost';
  insert into public.vip_boost_uses (company_id, listing_id, user_id, month) values (p_company, p_listing, me, date_trunc('month', now())::date);
  update public.products set boosted_until = greatest(coalesce(boosted_until, now()), now()) + make_interval(days => coalesce(v_days, 7)) where id = p_listing returning boosted_until into v_until;
  return jsonb_build_object('boosted_until', v_until, 'left', 2 - n);
end $$;
revoke all on function public.use_included_boost(bigint, bigint) from public, anon, authenticated, service_role;
grant execute on function public.use_included_boost(bigint, bigint) to authenticated, service_role;

-- ── 6. a reminder before VIP ends ────
alter table public.companies add column if not exists vip_reminded_at timestamptz;
create or replace function public.vip_reminders() returns int language plpgsql security definer set search_path = public as $$
declare n int;
begin
  with due as (update public.companies set vip_reminded_at = now()
                where plan = 'vip' and vip_until is not null and vip_until > now() and vip_until <= now() + interval '3 days'
                  and (vip_reminded_at is null or vip_reminded_at < vip_until - interval '30 days')
               returning id, name, owner_id, vip_until)
  insert into public.notifications (user_id, type, company_id, message)
  select owner_id, 'payment', id, 'VIP for ' || name || ' ends on ' || to_char(vip_until, 'DD Mon YYYY') || ' — renew it from Plan & verification to keep it'
    from due where owner_id is not null;
  get diagnostics n = row_count; return n;
end $$;
revoke all on function public.vip_reminders() from public, anon, authenticated, service_role;
grant execute on function public.vip_reminders() to service_role;
do $$ begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    execute $q$select cron.schedule('drugbox-vip-reminders', '23 7 * * *', 'select public.vip_reminders()')$q$;
  end if;
exception when others then raise warning 'pg_cron job not scheduled: %', sqlerrm;
end $$;

notify pgrst, 'reload schema';
