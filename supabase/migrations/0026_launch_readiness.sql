-- ═════════════════════════════════════════════════════════════════════
-- 0026 — launch readiness
--   1. N-12   company slugs are chosen one at a time: two DIFFERENT names can no longer race to the same suffix
--   2. L-scale the directory page (80 % of database time under load) costs a fraction, with byte-identical JSON
--   3. L-deploy every privilege the API roles hold is written out explicitly: Supabase is deprecating the automatic grants on
--             new public tables (api.auto_expose_new_tables, 2026-10-30), and migrations 0001–0025 relied on them
-- Safe to run twice. Checked by supabase/tests/launch_readiness.rls.sql.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. N-12 slug assignment is race-free ────────────────────────────────────────────────────────
-- 0025 locked the BASE slug, so 'X' (which needed x-4 because x, x-2, x-3 were taken) and 'X 4' (slug x-4) could both find
-- x-4 free at the same moment and one of them failed with a unique violation (23505). Now every slug assignment takes ONE fixed
-- transaction lock: the free-slug search of a second company waits until the first company's insert is committed, then sees
-- its slug. A company insert or slug change is rare and short, so serialising them costs nothing noticeable; one fixed key
-- also means no deadlock between two candidate locks, and a bulk insert holds one lock instead of one per row.
create or replace function public.companies_before_write() returns trigger
language plpgsql security definer set search_path = public as $$
declare base text; cand text; n int := 1;
begin
  if new.slug is null or new.slug = '' then
    new.slug := coalesce(nullif(public.slugify(new.name), ''), 'company') || '-' || coalesce(new.id::text, substr(md5(random()::text), 1, 6));
  end if;
  if tg_op = 'INSERT' or new.slug is distinct from old.slug then
    base := new.slug; cand := base;
    perform pg_advisory_xact_lock(hashtext('drugbox.company_slug'));   -- one slug assignment at a time, whatever the slug (N-12)
    while exists (select 1 from public.companies c where c.slug = cand and c.id is distinct from new.id) loop
      n := n + 1;
      cand := base || '-' || case when n <= 9 then n::text else substr(md5(random()::text || clock_timestamp()::text), 1, 6) end;
    end loop;
    new.slug := cand;
  end if;
  new.updated_at := now();
  return new;
end $$;
revoke all on function public.companies_before_write() from public, anon, authenticated;

-- ── 2. the directory page costs a fraction of what it did, with exactly the same JSON ─────────────────────
-- Load test (100k members, 5k companies): directory_companies_page was 80 % of all database time — ~27 ms a page. Where it went:
-- every call sorted ALL companies as whole rows to find its 100, called company_tier() once per row, ran a sub-query per row
-- for the certificates and for the products (json_build_object per product), and was re-planned on every call (a SQL function),
-- as was company_ratings(), which also read every event of the page's deals to find the few 'rate' ones.
-- Now:
--   * the page's ids come from idx_companies_dir_order, an index in the directory order that also holds the columns the order
--     needs: the scan stops after offset + limit entries, without touching the table. The order's "effective VIP" depends on
--     now() (an expired plan sorts as free), which no index can hold — so while a VIP plan has run out and the daily
--     expire_vip_plans() job (pg_cron, set up by deploy/supabase_deploy.sh) has not yet turned it free, the same index is read
--     whole and sorted (still narrow, still exact);
--   * a search finds its companies through the trigram indexes (name, Arabic name, product, ingredient), not by testing every company;
--   * the level (company_tier's rule, unchanged) and the certificate list come from one read of each company's certificates;
--   * each company's product list is kept ready in private.directory_products (statement triggers on company_products keep it
--     exact; it is the same json_agg the page built before), so the page reads 100 rows instead of building ~500 objects;
--   * both functions are PL/pgSQL, so a connection plans them once instead of on every call, and the ratings read a small
--     partial index of the 'rate' events.
-- The output is byte-for-byte the old one (supabase/tests/launch_readiness.rls.sql compares them on every page / search case).

-- 2a. the directory order, ready to read (replaces 0022's idx_companies_directory: same keys, plus the columns the scan needs)
create index if not exists idx_companies_dir_order on public.companies ((status = 'verified') desc, (plan = 'vip') desc, name, id)
  include (status, plan, vip_until) where status <> 'suspended';
drop index if exists public.idx_companies_directory;
-- the expired-VIP test is one probe
create index if not exists idx_companies_vip_until on public.companies (vip_until) where plan = 'vip' and status <> 'suspended';
-- the ratings read only the 'rate' events
create index if not exists idx_deal_events_rate on public.deal_events (deal_id) where action = 'rate';

-- 2b. each company's product list for the directory, kept exact by the triggers below
create table if not exists private.directory_products (
  company_id bigint primary key,
  products   json   not null
);
alter table private.directory_products enable row level security;
do $$ begin
  create policy "directory products: signed-in members read" on private.directory_products for select to authenticated using (true);
exception when duplicate_object then null; end $$;
revoke all on table private.directory_products from public, anon, authenticated, service_role;
grant select on table private.directory_products to authenticated, service_role;

-- rebuild the lists of these companies. One transaction at a time (product edits are rare and short): a second transaction
-- adding a product to the same company waits here until the first commits, so its rebuild includes the first one's product.
create or replace function private.directory_products_refresh(p_ids bigint[]) returns void
language plpgsql volatile security definer set search_path = public as $$
begin
  if p_ids is null or cardinality(p_ids) = 0 then return; end if;
  perform pg_advisory_xact_lock(hashtext('drugbox.directory_products'));
  delete from private.directory_products d where d.company_id = any(p_ids)
     and not exists (select 1 from public.company_products p where p.company_id = d.company_id);
  insert into private.directory_products (company_id, products)
  select p.company_id, json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                 'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name)
    from public.company_products p where p.company_id = any(p_ids) group by p.company_id
  on conflict (company_id) do update set products = excluded.products;
end $$;
revoke all on function private.directory_products_refresh(bigint[]) from public, anon, authenticated, service_role;

create or replace function private.directory_products_changed() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    perform private.directory_products_refresh(array(select distinct n.company_id from new_rows n));
  elsif tg_op = 'UPDATE' then
    perform private.directory_products_refresh(array(select o.company_id from old_rows o union select n.company_id from new_rows n));
  elsif tg_op = 'DELETE' then
    perform private.directory_products_refresh(array(select distinct o.company_id from old_rows o));
  else   -- TRUNCATE
    delete from private.directory_products;
  end if;
  return null;
end $$;
revoke all on function private.directory_products_changed() from public, anon, authenticated, service_role;
drop trigger if exists trg_directory_products_ins on public.company_products;
create trigger trg_directory_products_ins after insert on public.company_products referencing new table as new_rows
  for each statement execute function private.directory_products_changed();
drop trigger if exists trg_directory_products_upd on public.company_products;
create trigger trg_directory_products_upd after update on public.company_products referencing old table as old_rows new table as new_rows
  for each statement execute function private.directory_products_changed();
drop trigger if exists trg_directory_products_del on public.company_products;
create trigger trg_directory_products_del after delete on public.company_products referencing old table as old_rows
  for each statement execute function private.directory_products_changed();
drop trigger if exists trg_directory_products_trunc on public.company_products;
create trigger trg_directory_products_trunc after truncate on public.company_products
  for each statement execute function private.directory_products_changed();
-- fill it (and put it right again when this migration runs a second time)
do $$ begin perform private.directory_products_refresh(array(select c.id from public.companies c)); end $$;

-- 2c. the ratings: the same query, planned once per connection
create or replace function public.company_ratings(p_ids bigint[])
returns table (company_id bigint, rating numeric, reviews int)
language plpgsql stable security definer set search_path = public set plan_cache_mode = force_generic_plan as $$
#variable_conflict use_column
begin
  return query
  select d.to_company_id, round(avg((e.data ->> 'stars')::numeric), 1), count(*)::int
  from public.deals d join public.deal_events e on e.deal_id = d.id and e.action = 'rate'
  where d.to_company_id = any(p_ids) and d.type <> 'job'
    and not exists (select 1 from public.company_members a join public.company_members b on b.user_id = a.user_id
                    where a.company_id = d.to_company_id and a.accepted and b.company_id = d.from_company_id and b.accepted)
  group by d.to_company_id;
end $$;

-- 2d. the page (same arguments, same JSON)
create or replace function public.directory_companies_page(p_limit int default 100, p_offset int default 0, p_q text default null)
returns json language plpgsql stable security invoker set search_path = public set jit = off set plan_cache_mode = force_generic_plan as $$
declare
  v_q   text := nullif(left(trim(coalesce(p_q, '')), 100), '');
  v_lim int  := least(greatest(coalesce(p_limit, 100), 1), 200);
  v_off int  := greatest(coalesce(p_offset, 0), 0);
  v_ids bigint[];
begin
  -- the page's ids in the directory order: verified first, then (effective) VIP, then name, id. (A STABLE function: both
  -- statements see the snapshot of the call, as the single statement before did.)
  with hits as (   -- a search: the companies whose name / Arabic name or one of whose products matches (the same test as before)
    select c2.id from public.companies c2 where c2.name ilike '%' || v_q || '%' or c2.name_ar ilike '%' || v_q || '%'
    union
    select p.company_id from public.company_products p
     where p.name ilike '%' || v_q || '%' or p.active_ingredient ilike '%' || v_q || '%' or p.active_ingredient_ar ilike '%' || v_q || '%')
  select case when exists (select 1 from public.companies e where e.plan = 'vip' and e.status <> 'suspended' and e.vip_until <= now())
    then array(select c.id from public.companies c   -- a VIP plan has run out: it sorts as free
               where c.status <> 'suspended' and (v_q is null or c.id in (select h.id from hits h))
               order by (c.status = 'verified') desc, (c.plan = 'vip' and (c.vip_until is null or c.vip_until > now())) desc, c.name, c.id
               limit v_lim offset v_off)
    else array(select c.id from public.companies c   -- none has: read in index order, stop after offset + limit
               where c.status <> 'suspended' and (v_q is null or c.id in (select h.id from hits h))
               order by (c.status = 'verified') desc, (c.plan = 'vip') desc, c.name, c.id
               limit v_lim offset v_off) end
  into v_ids;

  return (
    with mine as (select public.my_company_ids() as id),
    rated as (select * from public.company_ratings(v_ids))
    select coalesce(json_agg(x order by (x.status = 'verified') desc, (x.plan = 'vip') desc, x.name, x.id), '[]'::json) from (
      select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
             c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours,
             case when c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) then 'vip' else 'free' end as plan,
             c.logo_url, c.follower_count, c.profile, c.created_at, c.intro_video,
             -- company_tier(c.id), the same rule: 0 not verified / no registry, 1 not licensed, 3 a checked valid GMP-type certificate, else 2
             case when c.status <> 'verified' or c.registry is null then 0 when not c.licensed then 1 when s.gmp then 3 else 2 end as tier,
             c.id in (select id from mine) as mine,
             coalesce(s.certs, '[]'::json) as certs,
             coalesce(dp.products, '[]'::json) as products,
             json_build_object('rating', r.rating, 'reviews', coalesce(r.reviews, 0)) as track
      from public.companies c
      left join rated r on r.company_id = c.id
      left join lateral (   -- the listed certificates (not expired) and company_tier's GMP-type test, in one pass
        select json_agg(distinct s.name) filter (where s.expiry is null or s.expiry >= current_date) as certs,
               bool_or(s.checked_at is not null and (s.expiry is null or s.expiry >= current_date)
                       and s.name ~* '(GMP|ISO 17025|GDP|ISO 15378|ISO 22716)') as gmp
        from public.site_certificates s where s.company_id = c.id) s on true
      left join private.directory_products dp on dp.company_id = c.id
      where c.id = any(v_ids)) x);
end $$;

-- ── 3. explicit privileges for anon, authenticated and service_role ────────────────────────────────────────────────
-- Until now every public table, sequence and function got its API grants from the project's default privileges ("alter default
-- privileges … grant all … to anon, authenticated, service_role"), narrowed by 0020 / 0024 / 0025. A project created after
-- 2026-10-30 may grant nothing automatically, and every API call would then fail with "permission denied". This section states
-- the privileges outright: for each object of 0001–0025 it revokes what the API roles hold and grants exactly what they held on
-- a project WITH the automatic grants — the result is identical on both kinds of project (the catalog privileges compare equal,
-- ACL entry for ACL entry). PUBLIC keeps EXECUTE where it had it (PostgreSQL gives it to every new function), and loses it where
-- 0020 took it away. Objects created by later sections and migrations grant their own privileges, as section 2 does.
-- Generated from a full build of 0001–0025 on supabase/tests/_local_supabase_stub.sql (the privileges of that build, listed per
-- object). A future migration that creates a table, view, sequence or function must grant it explicitly in the same way.
-- tables, views and sequences: revoke everything from the API roles, then grant exactly what they had (a table-level revoke also
-- revokes the column-level grants, which are given back below)
revoke all on table public.approved_suppliers from anon, authenticated, service_role;
grant select, references, trigger on table public.approved_suppliers to anon;
grant select, insert, update, delete, references, trigger on table public.approved_suppliers to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.approved_suppliers to service_role;
revoke all on table public.comments from anon, authenticated, service_role;
grant select, references, trigger on table public.comments to anon;
grant select, insert, delete, references, trigger on table public.comments to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.comments to service_role;
revoke all on sequence public.comments_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.comments_id_seq to authenticated, service_role;
revoke all on table public.companies from anon, authenticated, service_role;
grant select, references, trigger on table public.companies to anon;
grant select, insert, update, delete, references, trigger on table public.companies to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.companies to service_role;
revoke all on sequence public.companies_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.companies_id_seq to authenticated, service_role;
revoke all on table public.company_documents from anon, authenticated, service_role;
grant references, trigger on table public.company_documents to anon;
grant insert, update, delete, references, trigger on table public.company_documents to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_documents to service_role;
revoke all on sequence public.company_documents_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.company_documents_id_seq to authenticated, service_role;
revoke all on table public.company_documents_public from anon, authenticated, service_role;
grant select, references, trigger on table public.company_documents_public to anon;
grant select, insert, update, delete, references, trigger on table public.company_documents_public to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_documents_public to service_role;
revoke all on table public.company_followers from anon, authenticated, service_role;
grant select, references, trigger on table public.company_followers to anon;
grant select, insert, delete, references, trigger on table public.company_followers to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_followers to service_role;
revoke all on table public.company_listings from anon, authenticated, service_role;
grant select, references, trigger on table public.company_listings to anon;
grant select, insert, update, delete, references, trigger on table public.company_listings to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_listings to service_role;
revoke all on sequence public.company_listings_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.company_listings_id_seq to authenticated, service_role;
revoke all on table public.company_members from anon, authenticated, service_role;
grant select, references, trigger on table public.company_members to anon;
grant select, insert, update, delete, references, trigger on table public.company_members to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_members to service_role;
revoke all on table public.company_products from anon, authenticated, service_role;
grant select, references, trigger on table public.company_products to anon;
grant select, insert, update, delete, references, trigger on table public.company_products to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_products to service_role;
revoke all on sequence public.company_products_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.company_products_id_seq to authenticated, service_role;
revoke all on table public.company_reports from anon, authenticated, service_role;
grant select, references, trigger on table public.company_reports to anon;
grant select, insert, update, references, trigger on table public.company_reports to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_reports to service_role;
revoke all on sequence public.company_reports_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.company_reports_id_seq to authenticated, service_role;
revoke all on table public.company_routing from anon, authenticated, service_role;
grant select, references, trigger on table public.company_routing to anon;
grant select, insert, update, delete, references, trigger on table public.company_routing to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_routing to service_role;
revoke all on table public.company_sites from anon, authenticated, service_role;
grant select, references, trigger on table public.company_sites to anon;
grant select, insert, update, delete, references, trigger on table public.company_sites to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.company_sites to service_role;
revoke all on sequence public.company_sites_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.company_sites_id_seq to authenticated, service_role;
revoke all on table public.connections from anon, authenticated, service_role;
grant select, references, trigger on table public.connections to anon;
grant select, insert, update, delete, references, trigger on table public.connections to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.connections to service_role;
revoke all on sequence public.connections_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.connections_id_seq to authenticated, service_role;
revoke all on table public.conversation_heads from anon, authenticated, service_role;
grant select, references, trigger on table public.conversation_heads to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.conversation_heads to service_role;
revoke all on table public.course_enrollments from anon, authenticated, service_role;
grant select, references, trigger on table public.course_enrollments to anon;
grant select, insert, delete, references, trigger on table public.course_enrollments to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.course_enrollments to service_role;
revoke all on table public.deal_events from anon, authenticated, service_role;
grant select, references, trigger on table public.deal_events to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.deal_events to service_role;
revoke all on sequence public.deal_events_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.deal_events_id_seq to authenticated, service_role;
revoke all on table public.deal_members from anon, authenticated, service_role;
grant select, references, trigger on table public.deal_members to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.deal_members to service_role;
revoke all on table public.deals from anon, authenticated, service_role;
grant select, references, trigger on table public.deals to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.deals to service_role;
revoke all on sequence public.deals_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.deals_id_seq to authenticated, service_role;
revoke all on table public.enquiries from anon, authenticated, service_role;
grant select, references, trigger on table public.enquiries to anon;
grant select, insert, update, delete, references, trigger on table public.enquiries to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.enquiries to service_role;
revoke all on table public.group_invites from anon, authenticated, service_role;
grant select, references, trigger on table public.group_invites to anon;
grant select, insert, update, delete, references, trigger on table public.group_invites to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.group_invites to service_role;
revoke all on table public.group_members from anon, authenticated, service_role;
grant select, references, trigger on table public.group_members to anon;
grant select, insert, update, delete, references, trigger on table public.group_members to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.group_members to service_role;
revoke all on table public.groups from anon, authenticated, service_role;
grant select, references, trigger on table public.groups to anon;
grant select, insert, update, delete, references, trigger on table public.groups to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.groups to service_role;
revoke all on sequence public.groups_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.groups_id_seq to authenticated, service_role;
revoke all on table public.job_applications from anon, authenticated, service_role;
grant select, references, trigger on table public.job_applications to anon;
grant select, insert, update, delete, references, trigger on table public.job_applications to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.job_applications to service_role;
revoke all on table public.job_lists from anon, authenticated, service_role;
grant select, references, trigger on table public.job_lists to anon;
grant select, insert, update, delete, references, trigger on table public.job_lists to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.job_lists to service_role;
revoke all on table public.job_reviews from anon, authenticated, service_role;
grant select, references, trigger on table public.job_reviews to anon;
grant select, insert, update, delete, references, trigger on table public.job_reviews to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.job_reviews to service_role;
revoke all on sequence public.job_reviews_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.job_reviews_id_seq to authenticated, service_role;
revoke all on table public.jobs from anon, authenticated, service_role;
grant select, references, trigger on table public.jobs to anon;
grant select, insert, update, delete, references, trigger on table public.jobs to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.jobs to service_role;
revoke all on sequence public.jobs_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.jobs_id_seq to authenticated, service_role;
revoke all on table public.messages from anon, authenticated, service_role;
grant select, references, trigger on table public.messages to anon;
grant select, insert, update, references, trigger on table public.messages to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.messages to service_role;
revoke all on sequence public.messages_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.messages_id_seq to authenticated, service_role;
revoke all on table public.notifications from anon, authenticated, service_role;
grant select, references, trigger on table public.notifications to anon;
grant select, update, delete, references, trigger on table public.notifications to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.notifications to service_role;
revoke all on sequence public.notifications_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.notifications_id_seq to authenticated, service_role;
revoke all on table public.payment_orders from anon, authenticated, service_role;
grant select, references, trigger on table public.payment_orders to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.payment_orders to service_role;
revoke all on sequence public.payment_orders_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.payment_orders_id_seq to authenticated, service_role;
revoke all on table public.payment_products from anon, authenticated, service_role;
grant select, references, trigger on table public.payment_products to anon;
grant select, update, references, trigger on table public.payment_products to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.payment_products to service_role;
revoke all on table public.post_media from anon, authenticated, service_role;
grant select, references, trigger on table public.post_media to anon;
grant select, insert, delete, references, trigger on table public.post_media to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.post_media to service_role;
revoke all on sequence public.post_media_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.post_media_id_seq to authenticated, service_role;
revoke all on table public.post_view_log from anon, authenticated, service_role;
grant select, references, trigger on table public.post_view_log to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.post_view_log to service_role;
revoke all on table public.posts from anon, authenticated, service_role;
grant select, references, trigger on table public.posts to anon;
grant select, insert, update, delete, references, trigger on table public.posts to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.posts to service_role;
revoke all on sequence public.posts_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.posts_id_seq to authenticated, service_role;
revoke all on table public.products from anon, authenticated, service_role;
grant select, references, trigger on table public.products to anon;
grant select, insert, update, delete, references, trigger on table public.products to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.products to service_role;
revoke all on sequence public.products_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.products_id_seq to authenticated, service_role;
revoke all on table public.profile_view_log from anon, authenticated, service_role;
grant select, references, trigger on table public.profile_view_log to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.profile_view_log to service_role;
revoke all on table public.profiles from anon, authenticated, service_role;
grant select, references, trigger on table public.profiles to anon;
grant select, update, references, trigger on table public.profiles to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.profiles to service_role;
revoke all on table public.reactions from anon, authenticated, service_role;
grant select, references, trigger on table public.reactions to anon;
grant select, insert, update, delete, references, trigger on table public.reactions to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.reactions to service_role;
revoke all on table public.saved_jobs from anon, authenticated, service_role;
grant select, references, trigger on table public.saved_jobs to anon;
grant select, insert, update, delete, references, trigger on table public.saved_jobs to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.saved_jobs to service_role;
revoke all on table public.saved_posts from anon, authenticated, service_role;
grant select, references, trigger on table public.saved_posts to anon;
grant select, insert, update, delete, references, trigger on table public.saved_posts to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.saved_posts to service_role;
revoke all on table public.settings from anon, authenticated, service_role;
grant select, references, trigger on table public.settings to anon;
grant select, insert, update, delete, references, trigger on table public.settings to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.settings to service_role;
revoke all on table public.site_certificates from anon, authenticated, service_role;
grant select, references, trigger on table public.site_certificates to anon;
grant select, insert, update, delete, references, trigger on table public.site_certificates to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.site_certificates to service_role;
revoke all on sequence public.site_certificates_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.site_certificates_id_seq to authenticated, service_role;
revoke all on table public.sponsored_suppliers from anon, authenticated, service_role;
grant select, references, trigger on table public.sponsored_suppliers to anon;
grant select, insert, update, delete, references, trigger on table public.sponsored_suppliers to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.sponsored_suppliers to service_role;
revoke all on sequence public.sponsored_suppliers_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.sponsored_suppliers_id_seq to authenticated, service_role;
revoke all on table public.ticker_items from anon, authenticated, service_role;
grant select, references, trigger on table public.ticker_items to anon;
grant select, insert, update, delete, references, trigger on table public.ticker_items to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.ticker_items to service_role;
revoke all on sequence public.ticker_items_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.ticker_items_id_seq to authenticated, service_role;
revoke all on table public.training_courses from anon, authenticated, service_role;
grant select, references, trigger on table public.training_courses to anon;
grant select, insert, update, delete, references, trigger on table public.training_courses to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.training_courses to service_role;
revoke all on sequence public.training_courses_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.training_courses_id_seq to authenticated, service_role;
revoke all on table public.verification_requests from anon, authenticated, service_role;
grant select, references, trigger on table public.verification_requests to anon;
grant select, insert, update, references, trigger on table public.verification_requests to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.verification_requests to service_role;
revoke all on sequence public.verification_requests_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.verification_requests_id_seq to authenticated, service_role;
revoke all on table public.work_references from anon, authenticated, service_role;
grant select, references, trigger on table public.work_references to anon;
grant select, insert, delete, references, trigger on table public.work_references to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.work_references to service_role;
revoke all on sequence public.work_references_id_seq from anon, authenticated, service_role;
grant usage, select, update on sequence public.work_references_id_seq to authenticated, service_role;
-- column-level grants
grant select (id, company_id, type, product, number, expiry, status, created_by, created_at) on table public.company_documents to anon;
grant select (id, company_id, type, product, number, expiry, status, created_by, created_at) on table public.company_documents to authenticated;
-- functions: EXECUTE for exactly these roles (PUBLIC included: PostgreSQL grants it to every new function)
revoke all on function private.blocked_parties() from public, anon, authenticated, service_role;
grant execute on function private.blocked_parties() to anon, authenticated;
revoke all on function public.activate_order(p_id bigint) from public, anon, authenticated, service_role;
grant execute on function public.activate_order(p_id bigint) to service_role;
revoke all on function public.can_read_document(p_name text) from anon, authenticated, service_role;
grant execute on function public.can_read_document(p_name text) to public, anon, authenticated, service_role;
revoke all on function public.can_review(p_reviewer uuid, p_reviewee uuid, p_role text) from public, anon, authenticated, service_role;
grant execute on function public.can_review(p_reviewer uuid, p_reviewee uuid, p_role text) to authenticated, service_role;
revoke all on function public.can_write_document(p_name text) from anon, authenticated, service_role;
grant execute on function public.can_write_document(p_name text) to public, anon, authenticated, service_role;
revoke all on function public.can_write_video(p_name text) from anon, authenticated, service_role;
grant execute on function public.can_write_video(p_name text) to public, anon, authenticated, service_role;
revoke all on function public.claim_company(p_company_id bigint, p_note text) from public, anon, authenticated, service_role;
grant execute on function public.claim_company(p_company_id bigint, p_note text) to authenticated, service_role;
revoke all on function public.companies_after_insert() from public, anon, authenticated, service_role;
grant execute on function public.companies_after_insert() to authenticated, service_role;
revoke all on function public.companies_before_delete() from public, anon, authenticated, service_role;
grant execute on function public.companies_before_delete() to authenticated, service_role;
revoke all on function public.companies_before_write() from public, anon, authenticated, service_role;
grant execute on function public.companies_before_write() to service_role;
revoke all on function public.companies_guard() from public, anon, authenticated, service_role;
grant execute on function public.companies_guard() to authenticated, service_role;
revoke all on function public.companies_owner_gone() from public, anon, authenticated, service_role;
grant execute on function public.companies_owner_gone() to service_role;
revoke all on function public.company_documents_guard() from public, anon, authenticated, service_role;
grant execute on function public.company_documents_guard() to authenticated, service_role;
revoke all on function public.company_has_member(p_company bigint, p_user uuid) from public, anon, authenticated, service_role;
grant execute on function public.company_has_member(p_company bigint, p_user uuid) to service_role;
revoke all on function public.company_members_cleanup() from public, anon, authenticated, service_role;
grant execute on function public.company_members_cleanup() to authenticated, service_role;
revoke all on function public.company_members_guard() from public, anon, authenticated, service_role;
grant execute on function public.company_members_guard() to authenticated, service_role;
revoke all on function public.company_ratings(p_ids bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.company_ratings(p_ids bigint[]) to authenticated, service_role;
revoke all on function public.company_reports_guard() from public, anon, authenticated, service_role;
grant execute on function public.company_reports_guard() to service_role;
revoke all on function public.company_reports_received(p_company bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_reports_received(p_company bigint) to authenticated, service_role;
revoke all on function public.company_routing_guard() from public, anon, authenticated, service_role;
grant execute on function public.company_routing_guard() to authenticated, service_role;
revoke all on function public.company_sites_public(p_slug text) from public, anon, authenticated, service_role;
grant execute on function public.company_sites_public(p_slug text) to authenticated, service_role;
revoke all on function public.company_tier(cid bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_tier(cid bigint) to authenticated, service_role;
revoke all on function public.company_track_record(p_company bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_track_record(p_company bigint) to authenticated, service_role;
revoke all on function public.confirm_payment(p_provider text, p_order_key text, p_provider_ref text, p_amount_cents integer, p_currency text, p_payload jsonb) from public, anon, authenticated, service_role;
grant execute on function public.confirm_payment(p_provider text, p_order_key text, p_provider_ref text, p_amount_cents integer, p_currency text, p_payload jsonb) to service_role;
revoke all on function public.connections_guard() from public, anon, authenticated, service_role;
grant execute on function public.connections_guard() to authenticated, service_role;
revoke all on function public.conversation_messages(p_partner uuid, p_before_id bigint, p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.conversation_messages(p_partner uuid, p_before_id bigint, p_limit integer) to authenticated, service_role;
revoke all on function public.course_enrolled_count() from public, anon, authenticated, service_role;
grant execute on function public.course_enrolled_count() to authenticated, service_role;
revoke all on function public.create_order(p_product text, p_method text, p_company bigint, p_listing bigint) from public, anon, authenticated, service_role;
grant execute on function public.create_order(p_product text, p_method text, p_company bigint, p_listing bigint) to authenticated, service_role;
revoke all on function public.deal_act(p_ref text, p_action text, p_data jsonb, p_side text) from public, anon, authenticated, service_role;
grant execute on function public.deal_act(p_ref text, p_action text, p_data jsonb, p_side text) to authenticated, service_role;
revoke all on function public.deal_create(p_type text, p_to_slug text, p_from_slug text, p_title text, p_lines jsonb, p_message text, p_group text, p_ref text) from public, anon, authenticated, service_role;
grant execute on function public.deal_create(p_type text, p_to_slug text, p_from_slug text, p_title text, p_lines jsonb, p_message text, p_group text, p_ref text) to authenticated, service_role;
revoke all on function public.deal_flow() from public, anon, authenticated, service_role;
grant execute on function public.deal_flow() to authenticated, service_role;
revoke all on function public.deal_join(p_ref text, p_from_slug text, p_qty numeric) from public, anon, authenticated, service_role;
grant execute on function public.deal_join(p_ref text, p_from_slug text, p_qty numeric) to authenticated, service_role;
revoke all on function public.deal_next_status(p_type text, p_action text) from public, anon, authenticated, service_role;
grant execute on function public.deal_next_status(p_type text, p_action text) to authenticated, service_role;
revoke all on function public.deal_receiver(p_company bigint, p_type text) from public, anon, authenticated, service_role;
grant execute on function public.deal_receiver(p_company bigint, p_type text) to service_role;
revoke all on function public.directory_companies(p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.directory_companies(p_limit integer) to service_role;
revoke all on function public.directory_companies_page(p_limit integer, p_offset integer, p_q text) from public, anon, authenticated, service_role;
grant execute on function public.directory_companies_page(p_limit integer, p_offset integer, p_q text) to authenticated, service_role;
revoke all on function public.evidence_in_use(p_name text) from public, anon, authenticated, service_role;
grant execute on function public.evidence_in_use(p_name text) to authenticated, service_role;
revoke all on function public.expire_vip_plans() from public, anon, authenticated, service_role;
grant execute on function public.expire_vip_plans() to service_role;
revoke all on function public.fast_track_preferred() from public, anon, authenticated, service_role;
grant execute on function public.fast_track_preferred() to authenticated, service_role;
revoke all on function public.get_ratings(p_role text, ids uuid[]) from public, anon, authenticated, service_role;
grant execute on function public.get_ratings(p_role text, ids uuid[]) to authenticated, service_role;
revoke all on function public.get_reviews(p uuid, p_role text) from public, anon, authenticated, service_role;
grant execute on function public.get_reviews(p uuid, p_role text) to authenticated, service_role;
revoke all on function public.get_reviews_many(p_ids uuid[], p_role text) from public, anon, authenticated, service_role;
grant execute on function public.get_reviews_many(p_ids uuid[], p_role text) to authenticated, service_role;
revoke all on function public.group_invite_withdrawn() from public, anon, authenticated, service_role;
grant execute on function public.group_invite_withdrawn() to service_role;
revoke all on function public.group_member_count() from public, anon, authenticated, service_role;
grant execute on function public.group_member_count() to authenticated, service_role;
revoke all on function public.group_members_after_join() from public, anon, authenticated, service_role;
grant execute on function public.group_members_after_join() to authenticated, service_role;
revoke all on function public.group_members_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_members_guard() to authenticated, service_role;
revoke all on function public.groups_after_insert() from public, anon, authenticated, service_role;
grant execute on function public.groups_after_insert() to authenticated, service_role;
revoke all on function public.groups_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_guard() to authenticated, service_role;
revoke all on function public.handle_new_user() from public, anon, authenticated, service_role;
grant execute on function public.handle_new_user() to authenticated, service_role;
revoke all on function public.has_real_interaction(a uuid, b uuid) from public, anon, authenticated, service_role;
grant execute on function public.has_real_interaction(a uuid, b uuid) to service_role;
revoke all on function public.increment_post_share(p_id bigint) from public, anon, authenticated, service_role;
grant execute on function public.increment_post_share(p_id bigint) to authenticated, service_role;
revoke all on function public.increment_post_views(post_ids bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.increment_post_views(post_ids bigint[]) to authenticated, service_role;
revoke all on function public.increment_profile_view(target uuid) from public, anon, authenticated, service_role;
grant execute on function public.increment_profile_view(target uuid) to authenticated, service_role;
revoke all on function public.intro_video_guard() from public, anon, authenticated, service_role;
grant execute on function public.intro_video_guard() to service_role;
revoke all on function public.is_company_member(cid bigint, roles text[]) from anon, authenticated, service_role;
grant execute on function public.is_company_member(cid bigint, roles text[]) to public, anon, authenticated, service_role;
revoke all on function public.is_group_member(gid bigint, roles text[]) from anon, authenticated, service_role;
grant execute on function public.is_group_member(gid bigint, roles text[]) to public, anon, authenticated, service_role;
revoke all on function public.is_moderator() from public, anon, authenticated, service_role;
grant execute on function public.is_moderator() to authenticated, service_role, anon;
revoke all on function public.is_platform_admin() from anon, authenticated, service_role;
grant execute on function public.is_platform_admin() to public, anon, authenticated, service_role;
revoke all on function public.is_server_call() from public, anon, authenticated, service_role;
grant execute on function public.is_server_call() to authenticated, service_role;
revoke all on function public.is_vip(c companies) from public, anon, authenticated, service_role;
grant execute on function public.is_vip(c companies) to authenticated, service_role;
revoke all on function public.job_applications_guard() from public, anon, authenticated, service_role;
grant execute on function public.job_applications_guard() to authenticated, service_role;
revoke all on function public.job_list_rules() from public, anon, authenticated, service_role;
grant execute on function public.job_list_rules() to authenticated, service_role;
revoke all on function public.job_reviews_guard() from public, anon, authenticated, service_role;
grant execute on function public.job_reviews_guard() to authenticated, service_role;
revoke all on function public.jobs_hidden_for_me() from public, anon, authenticated, service_role;
grant execute on function public.jobs_hidden_for_me() to authenticated, service_role;
revoke all on function public.jobs_interacted(a uuid, b uuid) from public, anon, authenticated, service_role;
grant execute on function public.jobs_interacted(a uuid, b uuid) to authenticated, service_role;
revoke all on function public.messages_guard() from public, anon, authenticated, service_role;
grant execute on function public.messages_guard() to authenticated, service_role;
revoke all on function public.messages_heads_on_delete() from public, anon, authenticated, service_role;
grant execute on function public.messages_heads_on_delete() to authenticated, service_role;
revoke all on function public.messages_heads_on_insert() from public, anon, authenticated, service_role;
grant execute on function public.messages_heads_on_insert() to authenticated, service_role;
revoke all on function public.messages_heads_on_read() from public, anon, authenticated, service_role;
grant execute on function public.messages_heads_on_read() to authenticated, service_role;
revoke all on function public.messages_image_guard() from public, anon, authenticated, service_role;
grant execute on function public.messages_image_guard() to service_role;
revoke all on function public.moderate_reference(ref_id bigint, new_status text) from public, anon, authenticated, service_role;
grant execute on function public.moderate_reference(ref_id bigint, new_status text) to authenticated, service_role;
revoke all on function public.moderate_review(p_id bigint, p_hidden boolean) from public, anon, authenticated, service_role;
grant execute on function public.moderate_review(p_id bigint, p_hidden boolean) to authenticated, service_role;
revoke all on function public.my_company_ids() from public, anon, authenticated, service_role;
grant execute on function public.my_company_ids() to authenticated, service_role, anon;
revoke all on function public.my_conversations(p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.my_conversations(p_limit integer) to authenticated, service_role;
revoke all on function public.my_interactions() from public, anon, authenticated, service_role;
grant execute on function public.my_interactions() to authenticated, service_role;
revoke all on function public.my_last_message_id() from public, anon, authenticated, service_role;
grant execute on function public.my_last_message_id() to authenticated, service_role;
revoke all on function public.my_network_stats() from public, anon, authenticated, service_role;
grant execute on function public.my_network_stats() to authenticated, service_role;
revoke all on function public.new_messages(p_after bigint) from public, anon, authenticated, service_role;
grant execute on function public.new_messages(p_after bigint) to authenticated, service_role;
revoke all on function public.notify_comment() from public, anon, authenticated, service_role;
grant execute on function public.notify_comment() to authenticated, service_role;
revoke all on function public.notify_connection() from public, anon, authenticated, service_role;
grant execute on function public.notify_connection() to authenticated, service_role;
revoke all on function public.notify_group_invite() from public, anon, authenticated, service_role;
grant execute on function public.notify_group_invite() to service_role;
revoke all on function public.notify_job_application() from public, anon, authenticated, service_role;
grant execute on function public.notify_job_application() to authenticated, service_role;
revoke all on function public.notify_reaction() from public, anon, authenticated, service_role;
grant execute on function public.notify_reaction() to authenticated, service_role;
revoke all on function public.open_candidates(p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.open_candidates(p_limit integer) to authenticated, service_role;
revoke all on function public.path_in_folder(p_path text, p_folder text) from public, anon, authenticated, service_role;
grant execute on function public.path_in_folder(p_path text, p_folder text) to authenticated, service_role;
revoke all on function public.posts_remove_media() from public, anon, authenticated, service_role;
grant execute on function public.posts_remove_media() to service_role;
revoke all on function public.profiles_admin_scope() from public, anon, authenticated, service_role;
grant execute on function public.profiles_admin_scope() to service_role;
revoke all on function public.profiles_erase_person_deals() from public, anon, authenticated, service_role;
grant execute on function public.profiles_erase_person_deals() to service_role;
revoke all on function public.profiles_followers_count() from public, anon, authenticated, service_role;
grant execute on function public.profiles_followers_count() to service_role;
revoke all on function public.profiles_guard() from public, anon, authenticated, service_role;
grant execute on function public.profiles_guard() to authenticated, service_role;
revoke all on function public.purge_old_notifications(p_days integer) from public, anon, authenticated, service_role;
grant execute on function public.purge_old_notifications(p_days integer) to service_role;
revoke all on function public.reference_published_notify() from public, anon, authenticated, service_role;
grant execute on function public.reference_published_notify() to authenticated, service_role;
revoke all on function public.reply_to_reference(ref_id bigint, reply_text text, dispute boolean) from public, anon, authenticated, service_role;
grant execute on function public.reply_to_reference(ref_id bigint, reply_text text, dispute boolean) to authenticated, service_role;
revoke all on function public.review_instapay(p_id bigint, p_ok boolean) from public, anon, authenticated, service_role;
grant execute on function public.review_instapay(p_id bigint, p_ok boolean) to authenticated, service_role;
revoke all on function public.search_companies(q text, p_sector text, p_gov text, p_limit integer, p_after bigint) from public, anon, authenticated, service_role;
grant execute on function public.search_companies(q text, p_sector text, p_gov text, p_limit integer, p_after bigint) to authenticated, service_role;
revoke all on function public.server_columns() from public, anon, authenticated, service_role;
grant execute on function public.server_columns() to authenticated, service_role;
revoke all on function public.set_order_provider_ref(p_id bigint, p_ref text, p_order text) from public, anon, authenticated, service_role;
grant execute on function public.set_order_provider_ref(p_id bigint, p_ref text, p_order text) to service_role;
revoke all on function public.site_certificates_guard() from public, anon, authenticated, service_role;
grant execute on function public.site_certificates_guard() to authenticated, service_role;
revoke all on function public.slugify(t text) from public, anon, authenticated, service_role;
grant execute on function public.slugify(t text) to authenticated, service_role;
revoke all on function public.submit_instapay(p_id bigint, p_transfer_ref text, p_receipt text) from public, anon, authenticated, service_role;
grant execute on function public.submit_instapay(p_id bigint, p_transfer_ref text, p_receipt text) to authenticated, service_role;
revoke all on function public.suggest_people(p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.suggest_people(p_limit integer) to authenticated, service_role;
revoke all on function public.update_applicant_count() from public, anon, authenticated, service_role;
grant execute on function public.update_applicant_count() to authenticated, service_role;
revoke all on function public.update_comment_count() from public, anon, authenticated, service_role;
grant execute on function public.update_comment_count() to authenticated, service_role;
revoke all on function public.update_follower_count() from public, anon, authenticated, service_role;
grant execute on function public.update_follower_count() to authenticated, service_role;
revoke all on function public.update_like_count() from public, anon, authenticated, service_role;
grant execute on function public.update_like_count() to authenticated, service_role;
revoke all on function public.verification_decided_notify() from public, anon, authenticated, service_role;
grant execute on function public.verification_decided_notify() to authenticated, service_role;
revoke all on function public.verification_requests_apply() from public, anon, authenticated, service_role;
grant execute on function public.verification_requests_apply() to authenticated, service_role;
revoke all on function public.verification_requests_insert_guard() from public, anon, authenticated, service_role;
grant execute on function public.verification_requests_insert_guard() to service_role;
revoke all on function public.work_reference_rules() from public, anon, authenticated, service_role;
grant execute on function public.work_reference_rules() to authenticated, service_role;
revoke all on function public.work_references_remove_evidence() from public, anon, authenticated, service_role;
grant execute on function public.work_references_remove_evidence() to service_role;
-- extension functions (pg_trgm, created in public by 0001): only where the extension lives in public on this project
do $$ begin
  if to_regprocedure('public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal)') is not null then
    execute 'revoke all on function public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) to service_role';
  end if;
  if to_regprocedure('public.gin_extract_value_trgm(text, internal)') is not null then
    execute 'revoke all on function public.gin_extract_value_trgm(text, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gin_extract_value_trgm(text, internal) to service_role';
  end if;
  if to_regprocedure('public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal)') is not null then
    execute 'revoke all on function public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) to service_role';
  end if;
  if to_regprocedure('public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal)') is not null then
    execute 'revoke all on function public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_compress(internal)') is not null then
    execute 'revoke all on function public.gtrgm_compress(internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_compress(internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_consistent(internal, text, smallint, oid, internal)') is not null then
    execute 'revoke all on function public.gtrgm_consistent(internal, text, smallint, oid, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_consistent(internal, text, smallint, oid, internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_decompress(internal)') is not null then
    execute 'revoke all on function public.gtrgm_decompress(internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_decompress(internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_distance(internal, text, smallint, oid, internal)') is not null then
    execute 'revoke all on function public.gtrgm_distance(internal, text, smallint, oid, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_distance(internal, text, smallint, oid, internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_in(cstring)') is not null then
    execute 'revoke all on function public.gtrgm_in(cstring) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_in(cstring) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_options(internal)') is not null then
    execute 'revoke all on function public.gtrgm_options(internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_options(internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_out(gtrgm)') is not null then
    execute 'revoke all on function public.gtrgm_out(gtrgm) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_out(gtrgm) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_penalty(internal, internal, internal)') is not null then
    execute 'revoke all on function public.gtrgm_penalty(internal, internal, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_penalty(internal, internal, internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_picksplit(internal, internal)') is not null then
    execute 'revoke all on function public.gtrgm_picksplit(internal, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_picksplit(internal, internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_same(gtrgm, gtrgm, internal)') is not null then
    execute 'revoke all on function public.gtrgm_same(gtrgm, gtrgm, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_same(gtrgm, gtrgm, internal) to service_role';
  end if;
  if to_regprocedure('public.gtrgm_union(internal, internal)') is not null then
    execute 'revoke all on function public.gtrgm_union(internal, internal) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.gtrgm_union(internal, internal) to service_role';
  end if;
  if to_regprocedure('public.set_limit(real)') is not null then
    execute 'revoke all on function public.set_limit(real) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.set_limit(real) to service_role';
  end if;
  if to_regprocedure('public.show_limit()') is not null then
    execute 'revoke all on function public.show_limit() from public, anon, authenticated, service_role';
    execute 'grant execute on function public.show_limit() to service_role';
  end if;
  if to_regprocedure('public.show_trgm(text)') is not null then
    execute 'revoke all on function public.show_trgm(text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.show_trgm(text) to service_role';
  end if;
  if to_regprocedure('public.similarity(text, text)') is not null then
    execute 'revoke all on function public.similarity(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.similarity(text, text) to service_role';
  end if;
  if to_regprocedure('public.similarity_dist(text, text)') is not null then
    execute 'revoke all on function public.similarity_dist(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.similarity_dist(text, text) to service_role';
  end if;
  if to_regprocedure('public.similarity_op(text, text)') is not null then
    execute 'revoke all on function public.similarity_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.similarity_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.strict_word_similarity(text, text)') is not null then
    execute 'revoke all on function public.strict_word_similarity(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.strict_word_similarity(text, text) to service_role';
  end if;
  if to_regprocedure('public.strict_word_similarity_commutator_op(text, text)') is not null then
    execute 'revoke all on function public.strict_word_similarity_commutator_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.strict_word_similarity_commutator_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.strict_word_similarity_dist_commutator_op(text, text)') is not null then
    execute 'revoke all on function public.strict_word_similarity_dist_commutator_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.strict_word_similarity_dist_commutator_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.strict_word_similarity_dist_op(text, text)') is not null then
    execute 'revoke all on function public.strict_word_similarity_dist_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.strict_word_similarity_dist_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.strict_word_similarity_op(text, text)') is not null then
    execute 'revoke all on function public.strict_word_similarity_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.strict_word_similarity_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.word_similarity(text, text)') is not null then
    execute 'revoke all on function public.word_similarity(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.word_similarity(text, text) to service_role';
  end if;
  if to_regprocedure('public.word_similarity_commutator_op(text, text)') is not null then
    execute 'revoke all on function public.word_similarity_commutator_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.word_similarity_commutator_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.word_similarity_dist_commutator_op(text, text)') is not null then
    execute 'revoke all on function public.word_similarity_dist_commutator_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.word_similarity_dist_commutator_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.word_similarity_dist_op(text, text)') is not null then
    execute 'revoke all on function public.word_similarity_dist_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.word_similarity_dist_op(text, text) to service_role';
  end if;
  if to_regprocedure('public.word_similarity_op(text, text)') is not null then
    execute 'revoke all on function public.word_similarity_op(text, text) from public, anon, authenticated, service_role';
    execute 'grant execute on function public.word_similarity_op(text, text) to service_role';
  end if;
end $$;

notify pgrst, 'reload schema';
