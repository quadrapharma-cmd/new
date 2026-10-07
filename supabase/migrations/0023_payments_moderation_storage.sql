-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0023 — payments, moderation and storage (code review 2026-10, items F-30 F-31 F-32 F-41 F-97 F-98
--                F-114 F-115 F-116; the Edge Functions part of F-115/F-170 is in supabase/functions)
-- Database only: the approved interface is untouched. Safe to run more than once.
--   payments  F-30 a VIP plan ends at vip_until (is_vip(), expire_vip_plans() daily)   F-31 nothing is "active" when the
--             listing/company is gone   F-115 a Paymob callback is bound by the SIGNED order id, amount AND currency
--             F-116 a provider never confirms an InstaPay order   F-114 rejecting a transfer only notifies an order in review
--   reports   F-32 the reported company may only mark a report fixed — dismissing or rewriting it is Drugbox's
--   storage   F-41 deleting a post removes its files   F-98 evidence bucket: size/type limits, the author removes unused files
--   paths     F-97 file paths written by the browser must point into the writer's own folder (and review fields are Drugbox's)
-- Guards check API callers only (current_user anon / authenticated): SECURITY DEFINER functions and server work pass.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. F-30 VIP ends at vip_until ────────────────────────────────────────────
-- vip_until is the source of truth: a VIP without an end date was granted by Drugbox and does not lapse.
-- is_vip(companies) is also a computed column for the API: companies?select=*,is_vip
create or replace function public.is_vip(c public.companies) returns boolean language sql stable set search_path = public as $$
  select c.plan = 'vip' and (c.vip_until is null or c.vip_until > now())
$$;
revoke all on function public.is_vip(public.companies) from public, anon;
grant execute on function public.is_vip(public.companies) to authenticated, service_role;

-- plan goes back to 'free' once vip_until has passed (vip_until is kept as the record of the last paid period)
create or replace function public.expire_vip_plans() returns int language plpgsql security definer set search_path = public as $$
declare n int;
begin
  update public.companies set plan = 'free' where plan = 'vip' and vip_until is not null and vip_until <= now();
  get diagnostics n = row_count; return n;
end $$;
revoke all on function public.expire_vip_plans() from public, anon, authenticated;
grant execute on function public.expire_vip_plans() to service_role;     -- an outside scheduler may call it if pg_cron is off

-- daily at 01:17 UTC (night in Cairo) when pg_cron is enabled (Supabase → Database → Extensions → pg_cron); re-running replaces the job
do $$ begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    execute $q$select cron.schedule('drugbox-expire-vip', '17 1 * * *', 'select public.expire_vip_plans()')$q$;
  end if;
exception when others then raise warning 'pg_cron job not scheduled: %', sqlerrm;
end $$;
do $$ begin perform public.expire_vip_plans(); end $$;

-- ── 2. payment orders: the provider's own order id, one transaction pays one order ──
alter table public.payment_orders add column if not exists provider_order text;      -- Paymob order id (signed in its callback)
create unique index if not exists idx_payment_orders_provider_order on public.payment_orders (provider_order) where provider_order is not null;
-- (if one transaction already paid two orders before this rule, the index cannot be built: confirm_payment still refuses a
--  reused transaction, and the notice tells Drugbox to look at those orders)
do $$ begin
  create unique index if not exists idx_payment_orders_provider_tx on public.payment_orders ((method = 'fawry'), provider_ref)
    where status = 'paid' and provider_ref is not null;
exception when unique_violation then
  raise notice 'DRUGBOX 0023: one provider transaction paid several orders — check payment_orders with a repeated provider_ref';
end $$;

-- ── 3. F-31 activation only for a listing/company that still exists and is still the buyer's ──
-- returns false (nothing activated, the buyer and the Drugbox admins are told a refund is due) when the target is gone
drop function if exists public.activate_order(bigint);
create function public.activate_order(p_id bigint) returns boolean language plpgsql security definer set search_path = public as $$
declare o public.payment_orders; pr public.payment_products; n int := 0; what text;
begin
  select * into o from public.payment_orders where id = p_id; select * into pr from public.payment_products where code = o.product_code;
  if pr.kind = 'vip' then
    what := 'company page';
    update public.companies c set plan = 'vip',
           vip_until = case when c.plan = 'vip' and c.vip_until is null then null       -- granted by Drugbox without an end date
                            else greatest(coalesce(c.vip_until, now()), now()) + make_interval(days => pr.duration_days) end
     where c.id = o.company_id
       and (c.owner_id = o.user_id or exists (select 1 from public.company_members m where m.company_id = c.id and m.user_id = o.user_id and m.role in ('owner','admin')));
  elsif pr.kind = 'boost' then
    what := 'listing';
    update public.products set boosted_until = greatest(coalesce(boosted_until, now()), now()) + make_interval(days => pr.duration_days)
     where id = o.listing_id and user_id = o.user_id;
  else
    what := 'listing';
    update public.products set featured_until = greatest(coalesce(featured_until, now()), now()) + make_interval(days => pr.duration_days)
     where id = o.listing_id and user_id = o.user_id;
  end if;
  get diagnostics n = row_count;
  if n = 0 then
    update public.payment_orders set provider_payload = coalesce(provider_payload, '{}'::jsonb) || jsonb_build_object('not_activated', what) where id = o.id;
    insert into public.notifications (user_id, type, message)
    values (o.user_id, 'payment', 'Payment received for ' || pr.label || ' (' || o.merchant_ref || '), but the ' || what
                                  || ' is no longer available — the Drugbox team will refund you');
    insert into public.notifications (user_id, type, message)
    select p.id, 'payment', 'Order ' || o.merchant_ref || ' was paid but not activated (the ' || what || ' is gone) — refund due'
      from public.profiles p where p.role = 'admin';
    return false;
  end if;
  insert into public.notifications (user_id, type, message) values (o.user_id, 'payment', 'Payment received — ' || pr.label || ' is active');
  return true;
end $$;
revoke all on function public.activate_order(bigint) from public, anon, authenticated;

-- ── 4. F-115 F-116 confirm_payment: called by the webhooks only, after their signature is checked ──
-- p_provider 'paymob': p_order_key is the Paymob order id (obj.order.id — covered by the HMAC; merchant_order_id is not)
-- p_provider 'fawry' : p_order_key is merchantRefNumber (covered by Fawry's signature)
-- The order must be pending and paid by that provider's methods (an InstaPay order is confirmed only in Admin → Review),
-- and the amount AND currency must match. One provider transaction pays one order.
drop function if exists public.confirm_payment(text, text, int, jsonb);
create or replace function public.confirm_payment(p_provider text, p_order_key text, p_provider_ref text, p_amount_cents int, p_currency text, p_payload jsonb)
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
  if o.status = 'paid' then return 'already paid'; end if;                      -- providers retry; never activate twice
  if o.status <> 'pending' then return 'order is ' || o.status; end if;
  if p_amount_cents is distinct from o.amount_cents then
    update public.payment_orders set provider_payload = p_payload where id = o.id; return 'amount mismatch';
  end if;
  if upper(coalesce(p_currency, '')) <> upper(o.currency) then
    update public.payment_orders set provider_payload = p_payload where id = o.id; return 'currency mismatch';
  end if;
  if p_provider_ref is not null and exists (select 1 from public.payment_orders x where x.id <> o.id and x.status = 'paid'
                                              and x.provider_ref = p_provider_ref and (x.method = 'fawry') = (o.method = 'fawry')) then
    update public.payment_orders set provider_payload = p_payload where id = o.id; return 'transaction already used';
  end if;
  update public.payment_orders set status = 'paid', paid_at = now(), provider_ref = coalesce(p_provider_ref, provider_ref), provider_payload = p_payload where id = o.id;
  if public.activate_order(o.id) then return 'paid'; end if;
  return 'paid, not activated (refund due)';
end $$;
revoke all on function public.confirm_payment(text, text, text, int, text, jsonb) from public, anon, authenticated;
grant execute on function public.confirm_payment(text, text, text, int, text, jsonb) to service_role;

-- payments-create records the provider's references once the payment is started (p_order: Paymob's intention_order_id)
drop function if exists public.set_order_provider_ref(bigint, text);
create or replace function public.set_order_provider_ref(p_id bigint, p_ref text, p_order text default null) returns void language sql security definer set search_path = public as $$
  update public.payment_orders set provider_ref = p_ref, provider_order = coalesce(p_order, provider_order) where id = p_id and status = 'pending'
$$;
revoke all on function public.set_order_provider_ref(bigint, text, text) from public, anon, authenticated;
grant execute on function public.set_order_provider_ref(bigint, text, text) to service_role;

-- ── 5. F-114 InstaPay review: both decisions need an order that is waiting for review ──
create or replace function public.review_instapay(p_id bigint, p_ok boolean) returns void language plpgsql security definer set search_path = public as $$
declare who uuid;
begin
  if not public.is_platform_admin() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  if p_ok then
    update public.payment_orders set status = 'paid', paid_at = now() where id = p_id and status = 'review'; if not found then raise exception 'Not waiting for review'; end if;
    perform public.activate_order(p_id);
  else
    update public.payment_orders set status = 'failed' where id = p_id and status = 'review' returning user_id into who;
    if not found then raise exception 'Not waiting for review'; end if;
    insert into public.notifications (user_id, type, message) values (who, 'payment', 'We could not match your InstaPay transfer — please check the number and receipt');
  end if;
end $$;

-- ── 6. F-32 company reports: the reported company may only mark an open report fixed ──
-- Dismissing a report, re-opening it or editing what the reporter wrote is for Drugbox (admins and moderators).
-- The company page's "Mark fixed" sends status 'fixed', which the table names 'resolved'.
create or replace function public.company_reports_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if new.status = 'fixed' then new.status := 'resolved'; end if;
  if current_user not in ('anon', 'authenticated') then return new; end if;
  if public.is_platform_admin() or exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'moderator') then return new; end if;
  if new.company_id is distinct from old.company_id or new.reporter is distinct from old.reporter or new.section is distinct from old.section
     or new.issue is distinct from old.issue or new.correction is distinct from old.correction or new.created_at is distinct from old.created_at
     or (new.status is distinct from old.status and not (old.status = 'open' and new.status = 'resolved')) then
    raise exception 'Only Drugbox can dismiss or change a report — mark it fixed once the page is corrected' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_company_reports_guard on public.company_reports;
create trigger trg_company_reports_guard before update on public.company_reports for each row execute function public.company_reports_guard();

-- ── 7. F-41 a deleted post takes its files with it (post-media is public: the links must stop working) ──
-- The live app stores a post's files as posts/<author>/<post id>-<random>.<ext>. Removing the object rows makes the
-- public links answer 404 (Supabase's storage serves an object only while its row exists); a storage failure never
-- blocks the delete. Supabase refuses direct deletes from storage tables unless storage.allow_delete_query is on
-- for the transaction, so it is switched on just for this statement.
create or replace function public.posts_remove_media() returns trigger language plpgsql security definer set search_path = public as $$
declare prev text := current_setting('storage.allow_delete_query', true);
begin
  begin
    perform set_config('storage.allow_delete_query', 'true', true);
    delete from storage.objects where bucket_id = 'post-media' and name like 'posts/' || old.user_id::text || '/' || old.id::text || '-%';
    perform set_config('storage.allow_delete_query', coalesce(prev, ''), true);
  exception when others then raise warning 'post % files not removed: %', old.id, sqlerrm;
  end;
  return null;
end $$;
revoke all on function public.posts_remove_media() from public, anon, authenticated;
drop trigger if exists trg_posts_remove_media on public.posts;
create trigger trg_posts_remove_media after delete on public.posts for each row execute function public.posts_remove_media();

-- ── 8. F-98 reference-evidence: limits like the documents bucket; files are removed with their reference ──
update storage.buckets set file_size_limit = 10485760, allowed_mime_types = array['application/pdf','image/jpeg','image/png']
 where id = 'reference-evidence';
create or replace function public.evidence_in_use(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.work_references r where r.evidence_path = p_name)
$$;
revoke all on function public.evidence_in_use(text) from public, anon;
grant execute on function public.evidence_in_use(text) to authenticated;
-- the author may remove an upload that no reference uses (a warning's evidence stays while the warning exists)
drop policy if exists "evidence: author removes unused" on storage.objects;
create policy "evidence: author removes unused" on storage.objects for delete to authenticated
  using (bucket_id = 'reference-evidence' and (storage.foldername(name))[1] = (select auth.uid())::text and not public.evidence_in_use(name));
-- a withdrawn or removed reference takes its evidence file with it (unless another reference uses the same file)
create or replace function public.work_references_remove_evidence() returns trigger language plpgsql security definer set search_path = public as $$
declare prev text := current_setting('storage.allow_delete_query', true);
begin
  if old.evidence_path is null or old.evidence_path not like old.author::text || '/%' or public.evidence_in_use(old.evidence_path) then return null; end if;
  begin
    perform set_config('storage.allow_delete_query', 'true', true);
    delete from storage.objects where bucket_id = 'reference-evidence' and name = old.evidence_path;
    perform set_config('storage.allow_delete_query', coalesce(prev, ''), true);
  exception when others then raise warning 'evidence % not removed: %', old.evidence_path, sqlerrm;
  end;
  return null;
end $$;
revoke all on function public.work_references_remove_evidence() from public, anon, authenticated;
drop trigger if exists trg_work_references_remove_evidence on public.work_references;
create trigger trg_work_references_remove_evidence after delete on public.work_references for each row execute function public.work_references_remove_evidence();

-- ── 9. F-97 paths into storage point at the writer's own folder; review fields are Drugbox's ──
-- Hard errors: the approved interface and the adapter never send another folder or the review fields — only a forged call does.
create or replace function public.path_in_folder(p_path text, p_folder text) returns boolean language sql immutable as $$
  select p_path like p_folder || '%' and position('..' in p_path) = 0 and position('//' in p_path) = 0
$$;
revoke all on function public.path_in_folder(text, text) from public, anon;
grant execute on function public.path_in_folder(text, text) to authenticated;

-- verification requests: documents uploaded for THIS company (documents/verification/<company id>/…); no forged review
create or replace function public.verification_requests_insert_guard() returns trigger language plpgsql set search_path = public as $$
declare p text;
begin
  if current_user not in ('anon', 'authenticated') then return new; end if;              -- claim_company() and server work pass
  if new.reviewed_by is not null or new.reviewed_at is not null or new.note is not null then
    raise exception 'The review is filled in by Drugbox' using errcode = '42501';
  end if;
  foreach p in array array[new.tax_card_path, new.licence_path, new.registry_path] loop
    if p is not null and (not public.path_in_folder(p, 'verification/' || new.company_id::text || '/')
                          or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = p)) then
      raise exception 'Upload the documents for this company first' using errcode = '42501';
    end if;
  end loop;
  return new;
end $$;
drop trigger if exists trg_verification_requests_insert_guard on public.verification_requests;
create trigger trg_verification_requests_insert_guard before insert on public.verification_requests for each row execute function public.verification_requests_insert_guard();

-- intro videos: people/<person id>/… or companies/<company id>/… (bucket videos)
create or replace function public.intro_video_guard() returns trigger language plpgsql set search_path = public as $$
declare f text;
begin
  if current_user not in ('anon', 'authenticated') or new.intro_video is null then return new; end if;
  if tg_op = 'UPDATE' and new.intro_video is not distinct from old.intro_video then return new; end if;
  f := case when tg_table_name = 'profiles' then 'people/' else 'companies/' end || new.id::text || '/';
  if not public.path_in_folder(coalesce(new.intro_video->>'path', ''), f)
     or (new.intro_video->>'poster' is not null and not public.path_in_folder(new.intro_video->>'poster', f)) then
    raise exception 'The video must be uploaded to this page''s own folder' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_profiles_intro_video_guard on public.profiles;
create trigger trg_profiles_intro_video_guard before insert or update of intro_video on public.profiles for each row execute function public.intro_video_guard();
drop trigger if exists trg_companies_intro_video_guard on public.companies;
create trigger trg_companies_intro_video_guard before insert or update of intro_video on public.companies for each row execute function public.intro_video_guard();

-- message photos: <sender>/<receiver>/… in message-media, like attachments (messages cannot be edited afterwards)
create or replace function public.messages_image_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if current_user in ('anon', 'authenticated') and new.image_url is not null
     and not public.path_in_folder(new.image_url, new.sender_id::text || '/' || new.receiver_id::text || '/') then
    raise exception 'A photo must be uploaded to this conversation''s folder' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_messages_image_guard on public.messages;
create trigger trg_messages_image_guard before insert on public.messages for each row execute function public.messages_image_guard();

-- the guards above are trigger functions or internal helpers, not RPCs
revoke all on function public.company_reports_guard() from public, anon, authenticated;
revoke all on function public.verification_requests_insert_guard() from public, anon, authenticated;
revoke all on function public.intro_video_guard() from public, anon, authenticated;
revoke all on function public.messages_image_guard() from public, anon, authenticated;

notify pgrst, 'reload schema';
