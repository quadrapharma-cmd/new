-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 0022 — integrity and speed at launch scale (code review 2026-10, items F-04 F-05 F-17 F-18 F-43 F-44 F-45
--                F-46 F-47 F-48 F-49 F-99 F-110 F-112 F-166)
-- Database only: the approved interface is untouched. Every change is re-runnable.
--   speed      F-04 deals read through one set of "my companies" (my_company_ids), not a function call per row, newest first by index
--              F-05 directory_companies_page(): one page of the directory without the per-company track record
--              F-44 / F-99 indexes on the foreign keys and hot lookups that had none; duplicate indexes dropped
--              F-47 suggest_people does bounded work   F-110 message reads use the pair / receiver indexes
--              F-112 get_reviews_many uses the reviews index   F-46 no JIT compilation for API requests
--   integrity  F-17 deleting a post, a comment or an account is no longer blocked by notifications, replies,
--              groups, verification decisions or sponsorships   F-18 one like notification per person and post,
--              removed on unlike   F-48 / F-49 counters move by +1/−1 (also when a reaction or membership row moves)
--              F-43 size limits on free text   F-166 the conversation list follows a deleted message
--   F-45 (likes on one viral post queue on the post row) is measured in supabase/tests/integrity_perf.sql and left
--   as is — see the note in section 13.
-- supabase/tests/integrity_perf.sql checks each item and prints before/after timings.
-- ═════════════════════════════════════════════════════════════════════════════

-- ── 1. F-04 deals: "my companies" once per request ─────────────────────────────
-- The companies the caller belongs to, by the same rule as is_company_member() (whatever that rule is today:
-- the candidates are the caller's membership rows and owned pages, each confirmed by is_company_member).
-- Used as `x in (select public.my_company_ids())`: the planner runs it once per query and hashes the result.
create or replace function public.my_company_ids() returns setof bigint
language sql stable security definer set search_path = public rows 10 as $$
  select x.id from (select m.company_id as id from public.company_members m where m.user_id = auth.uid()
                    union select c.id from public.companies c where c.owner_id = auth.uid()) x
  where auth.uid() is not null and public.is_company_member(x.id)
$$;
revoke all on function public.my_company_ids() from public;
grant execute on function public.my_company_ids() to anon, authenticated;   -- evaluated inside the deals policy (empty for anon)

create index if not exists idx_companies_owner on public.companies (owner_id);
create index if not exists idx_deals_updated on public.deals (updated_at desc);   -- the deals list: newest first, limit 300

-- same rule as 0021 (F-15: the "from" side is the originating company's team; from_user alone counts only for
-- person-originated deals), written as set membership so an index can drive the read
drop policy if exists "deals: the two sides read" on public.deals;
create policy "deals: the two sides read" on public.deals for select
  using ((from_company_id is null and from_user = (select auth.uid()))
         or to_company_id in (select public.my_company_ids())
         or (from_company_id is not null and from_company_id in (select public.my_company_ids())));
-- deal events and members keep their policy (`exists` the deal, 0007 / 0008): with the policy above, each check is one
-- primary-key probe of deals against the already-built "my companies" set, so the cost follows the rows returned
-- (300 deals ≈ 900 events + 550 members), not the size of the deals table, and the plan stays under the JIT threshold.

-- ── 2. F-05 the company directory, one page at a time ───────────────────────────
-- Same row shape as directory_companies() (which keeps working), except `track`: the list carries only the
-- rating and the number of reviews (what a card shows), computed for the page in one grouped query; the full
-- track record stays company_track_record(id), loaded when a company page opens.
-- Order: verified pages first, then VIP, then by name (id breaks ties) — stable, so pages never overlap.
-- F-30: a VIP plan counts (and is reported) only until vip_until, as is_vip() in 0023 (written out: 0023 runs later).
-- Ratings follow company_track_record (0021, F-39): rated deals to the company, jobs excluded, deals between related companies
-- (a shared accepted member) ignored. Definer: the caller cannot read other companies' deals, the rating is public.
create or replace function public.company_ratings(p_ids bigint[])
returns table (company_id bigint, rating numeric, reviews int)
language sql stable security definer set search_path = public as $$
  select d.to_company_id, round(avg((e.data ->> 'stars')::numeric), 1), count(*)::int
  from public.deals d join public.deal_events e on e.deal_id = d.id and e.action = 'rate'
  where d.to_company_id = any(p_ids) and d.type <> 'job'
    and not exists (select 1 from public.company_members a join public.company_members b on b.user_id = a.user_id
                    where a.company_id = d.to_company_id and a.accepted and b.company_id = d.from_company_id and b.accepted)
  group by d.to_company_id
$$;
revoke all on function public.company_ratings(bigint[]) from public;
grant execute on function public.company_ratings(bigint[]) to authenticated;

create index if not exists idx_companies_directory on public.companies ((status = 'verified') desc, (plan = 'vip') desc, name, id)
  where status <> 'suspended';

create or replace function public.directory_companies_page(p_limit int default 100, p_offset int default 0, p_q text default null)
returns json language sql stable security invoker set search_path = public set jit = off as $$
  with q as (select nullif(left(trim(coalesce(p_q, '')), 100), '') as q),
  page as (
    select c.* from public.companies c, q
    where c.status <> 'suspended'
      and (q.q is null or c.name ilike '%' || q.q || '%' or c.name_ar ilike '%' || q.q || '%'
           or exists (select 1 from public.company_products p where p.company_id = c.id
                      and (p.name ilike '%' || q.q || '%' or p.active_ingredient ilike '%' || q.q || '%' or p.active_ingredient_ar ilike '%' || q.q || '%')))
    order by (c.status = 'verified') desc, (c.plan = 'vip' and (c.vip_until is null or c.vip_until > now())) desc, c.name, c.id
    limit least(greatest(coalesce(p_limit, 100), 1), 200) offset greatest(coalesce(p_offset, 0), 0)),
  mine as (select public.my_company_ids() as id),
  rated as (select * from public.company_ratings(array(select id from page)))
  select coalesce(json_agg(x order by (x.status = 'verified') desc, (x.plan = 'vip') desc, x.name, x.id), '[]'::json) from (
    select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
           c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours,
           case when c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) then 'vip' else 'free' end as plan,
           c.logo_url, c.follower_count, c.profile, c.created_at, c.intro_video,
           public.company_tier(c.id) as tier, c.id in (select id from mine) as mine,
           (select coalesce(json_agg(distinct s.name), '[]'::json) from public.site_certificates s where s.company_id = c.id and (s.expiry is null or s.expiry >= current_date)) as certs,
           (select coalesce(json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                   'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name), '[]'::json) from public.company_products p where p.company_id = c.id) as products,
           json_build_object('rating', r.rating, 'reviews', coalesce(r.reviews, 0)) as track
    from page c left join rated r on r.company_id = c.id) x
$$;
-- (jit = off on both: their per-company subqueries look expensive to the planner, which then compiles them on every
--  call — 60 ms instead of 9 ms for a page — even where the database-wide setting of section 12 cannot be made)
do $$ begin alter function public.directory_companies(int) set jit = off; exception when undefined_function then null; end $$;
revoke all on function public.directory_companies_page(int, int, text) from public, anon;
grant execute on function public.directory_companies_page(int, int, text) to authenticated;

-- ── 3. F-17 deletes that foreign keys used to block ────────────────────────────
-- a post's notifications go with the post; a deleted person's notifications stay without a sender; a reply goes with
-- the comment it answers; a group outlives its creator; a verification decision keeps its status without the reviewer;
-- a sponsorship goes with its company. payment_orders.product_code stays NO ACTION on purpose (a product with orders
-- must not vanish); 0021 makes deals / members / approved suppliers RESTRICT on purpose (F-36).
do $$ declare k record; begin
  for k in select * from (values
      ('notifications',         'notifications_post_id_fkey',             'post_id',     'posts',     'c'),
      ('notifications',         'notifications_from_user_fkey',           'from_user',   'profiles',  'n'),
      ('comments',              'comments_parent_id_fkey',                'parent_id',   'comments',  'c'),
      ('groups',                'groups_created_by_fkey',                 'created_by',  'profiles',  'n'),
      ('verification_requests', 'verification_requests_reviewed_by_fkey', 'reviewed_by', 'profiles',  'n'),
      ('sponsored_suppliers',   'sponsored_suppliers_company_id_fkey',    'company_id',  'companies', 'c')) v(tbl, con, col, ref, act) loop
    if not exists (select 1 from pg_constraint where conname = k.con and conrelid = ('public.' || k.tbl)::regclass and confdeltype = k.act) then
      execute format('alter table public.%I drop constraint if exists %I', k.tbl, k.con);
      execute format('alter table public.%I add constraint %I foreign key (%I) references public.%I(id) on delete %s',
                     k.tbl, k.con, k.col, k.ref, case k.act when 'c' then 'cascade' else 'set null' end);
    end if;
  end loop;
end $$;
-- the cascades / set-nulls above look these up on every post, comment and account delete
create index if not exists idx_notifs_post on public.notifications (post_id) where post_id is not null;
create index if not exists idx_notifs_from on public.notifications (from_user) where from_user is not null;
create index if not exists idx_comments_parent on public.comments (parent_id) where parent_id is not null;
create index if not exists idx_groups_created_by on public.groups (created_by) where created_by is not null;

-- ── 4. F-18 / F-49 likes: one notification per person and post, counters follow a moved reaction ──
-- existing duplicates and notifications for likes that were taken back are removed first (keeps the newest)
delete from public.notifications n using public.notifications k
 where n.type = 'like' and k.type = 'like' and n.user_id = k.user_id and n.from_user = k.from_user and n.post_id = k.post_id and n.id < k.id;
delete from public.notifications n
 where n.type = 'like' and n.post_id is not null and n.from_user is not null
   and not exists (select 1 from public.reactions r where r.post_id = n.post_id and r.user_id = n.from_user);
create unique index if not exists idx_notifs_like_once on public.notifications (user_id, from_user, post_id) where type = 'like';

create or replace function public.notify_reaction()
returns trigger language plpgsql security definer set search_path = public as $$
declare owner uuid;
begin
  if tg_op = 'UPDATE' and new.post_id = old.post_id and new.user_id = old.user_id then return null; end if;   -- only the kind changed
  if tg_op in ('DELETE', 'UPDATE') then   -- unlike (or moved away): the "liked your post" notification goes too
    delete from public.notifications where type = 'like' and post_id = old.post_id and from_user = old.user_id;
  end if;
  if tg_op in ('INSERT', 'UPDATE') then
    select user_id into owner from public.posts where id = new.post_id;
    if owner is not null and owner <> new.user_id then
      insert into public.notifications(user_id, type, from_user, post_id)
      values (owner, 'like', new.user_id, new.post_id)
      on conflict (user_id, from_user, post_id) where type = 'like' do nothing;
    end if;
  end if;
  return null;
end; $$;
drop trigger if exists trg_notify_reaction on public.reactions;
create trigger trg_notify_reaction after insert or delete or update of post_id, user_id on public.reactions
  for each row execute procedure public.notify_reaction();

-- the one like counter on reactions also handles a reaction moved to another post (REST allows the UPDATE)
create or replace function public.update_like_count()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'UPDATE' and new.post_id = old.post_id then return null; end if;
  if tg_op in ('DELETE', 'UPDATE') then
    update public.posts set like_count = greatest(0, like_count - 1) where id = old.post_id;
  end if;
  if tg_op in ('INSERT', 'UPDATE') then
    update public.posts set like_count = like_count + 1 where id = new.post_id;
  end if;
  return null;
end; $$;
drop trigger if exists trg_like_count on public.reactions;
create trigger trg_like_count after insert or delete or update of post_id on public.reactions
  for each row execute procedure public.update_like_count();
-- once: counts that drifted before this fix
update public.posts p set like_count = coalesce(x.n, 0)
  from public.posts q left join (select post_id, count(*)::int as n from public.reactions group by post_id) x on x.post_id = q.id
 where q.id = p.id and p.like_count is distinct from coalesce(x.n, 0);

-- ── 5. F-48 group members: +1/−1 (a recount reads a stale count under concurrent joins) ──
create or replace function public.group_member_count() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'UPDATE' and new.group_id = old.group_id then return null; end if;
  if tg_op in ('DELETE', 'UPDATE') then
    update public.groups set member_count = greatest(member_count - 1, 0) where id = old.group_id;
  end if;
  if tg_op in ('INSERT', 'UPDATE') then
    update public.groups set member_count = member_count + 1 where id = new.group_id;
  end if;
  return null;
end $$;
drop trigger if exists trg_group_member_count on public.group_members;
create trigger trg_group_member_count after insert or delete or update of group_id on public.group_members
  for each row execute function public.group_member_count();
update public.groups g set member_count = coalesce(x.n, 0)
  from public.groups q left join (select group_id, count(*)::int as n from public.group_members group by group_id) x on x.group_id = q.id
 where q.id = g.id and g.member_count is distinct from coalesce(x.n, 0);

-- ── 6. F-43 size limits on free text ──────────────────────────────────────────
-- Generous limits (the approved interface's longest sample text is under 300 characters); they stop one row from
-- weighing megabytes in every list that carries it. Added NOT VALID, then validated when existing rows allow it.
do $$ declare k record; begin
  for k in select * from (values
      ('messages',         'messages_body_len',          'length(body) <= 10000'),
      ('messages',         'messages_attachment_size',   'pg_column_size(attachment) <= 8192'),
      ('profiles',         'profiles_text_len',          'length(name) <= 200 and length(headline) <= 300 and length(company) <= 200 and length(bio) <= 5000
                                                          and length(location) <= 200 and length(desired_role) <= 200'),
      ('profiles',         'profiles_lists_size',        'pg_column_size(experience) <= 65536 and pg_column_size(education) <= 65536
                                                          and pg_column_size(certifications) <= 65536 and cardinality(skills) <= 100 and cardinality(languages) <= 50'),
      ('companies',        'companies_text_len',         'length(name) <= 200 and length(name_ar) <= 200 and length(tagline) <= 300 and length(bio) <= 5000
                                                          and length(hours) <= 300 and length(location) <= 500 and length(employees) <= 50
                                                          and length(phone) <= 50 and length(whatsapp) <= 50 and length(email) <= 320 and length(website) <= 500'),
      ('companies',        'companies_profile_size',     'pg_column_size(profile) <= 32768'),
      ('company_sites',    'company_sites_text_len',     'length(capacity) <= 200 and length(min_batch) <= 200 and pg_column_size(free_slots) <= 4096'),
      ('company_listings', 'company_listings_text_len',  'length(qty) <= 200 and length(batch) <= 200 and length(expiry) <= 200 and length(price) <= 200
                                                          and length(reg_status) <= 200 and length(deal_kind) <= 200 and length(markets) <= 500'),
      ('deals',            'deals_json_size',            'pg_column_size(lines) <= 16384 and pg_column_size(offer) <= 16384 and pg_column_size(counter) <= 16384
                                                          and pg_column_size(answers) <= 65536'),
      ('deal_events',      'deal_events_size',           'length(note) <= 4000 and pg_column_size(data) <= 32768'),
      ('groups',           'groups_text_len',            'length(name) <= 120 and length(description) <= 2000'),
      ('jobs',             'jobs_text_len',              'length(title) <= 200 and length(company) <= 200 and length(location) <= 200
                                                          and length(description) <= 10000 and length(salary) <= 100'),
      ('products',         'products_text_len',          'length(name) <= 200 and length(description) <= 5000
                                                          and pg_column_size(specs) <= 16384 and pg_column_size(price_tiers) <= 16384'),
      ('enquiries',        'enquiries_text_len',         'length(title) <= 300 and length(body) <= 5000'),
      ('job_applications', 'job_applications_note_len',  'length(note) <= 2000'),
      ('job_lists',        'job_lists_text_len',         'length(note) <= 1000 and length(reason) <= 500')) v(tbl, con, chk) loop
    if not exists (select 1 from pg_constraint where conname = k.con and conrelid = ('public.' || k.tbl)::regclass) then
      execute format('alter table public.%I add constraint %I check (%s) not valid', k.tbl, k.con, k.chk);
    end if;
    begin
      execute format('alter table public.%I validate constraint %I', k.tbl, k.con);
    exception when check_violation then
      raise notice 'DRUGBOX 0022: % has older rows over the limit — the limit applies to new and edited rows', k.con;
    end;
  end loop;
end $$;

-- ── 7. F-44 / F-99 indexes: foreign keys and hot lookups, duplicates out ────────
-- (each one is named after what it serves; partial where most rows are NULL)
create index if not exists idx_comments_user          on public.comments (user_id);
create index if not exists idx_products_user          on public.products (user_id, created_at desc);           -- my listings (checkout picker)
create index if not exists idx_enquiries_user         on public.enquiries (user_id);
create index if not exists idx_company_followers_user on public.company_followers (user_id);                    -- pages I follow (every sign-in)
create index if not exists idx_jobs_user              on public.jobs (user_id, created_at desc);               -- my jobs, my_interactions()
create index if not exists idx_saved_posts_post       on public.saved_posts (post_id);
create index if not exists idx_saved_jobs_job         on public.saved_jobs (job_id);
create index if not exists idx_job_apps_user_created  on public.job_applications (user_id, created_at desc);   -- 0010 meant this one (name taken)
create index if not exists idx_job_apps_cv_path       on public.job_applications (cv_path) where cv_path is not null;   -- can_read_document()
create index if not exists idx_listings_active_created on public.company_listings (created_at desc) where active;  -- the listings page
create index if not exists idx_site_certs_unchecked   on public.site_certificates (created_at) where checked_at is null;  -- Admin → Review queue
create index if not exists idx_site_certs_site        on public.site_certificates (site_id);
create index if not exists idx_heads_partner          on public.conversation_heads (partner);
create index if not exists idx_refs_author            on public.work_references (author);
create index if not exists idx_approved_suppliers_supplier on public.approved_suppliers (supplier_company_id);
create index if not exists idx_deal_members_company   on public.deal_members (company_id);
create index if not exists idx_deals_assignee         on public.deals (assignee) where assignee is not null;
create index if not exists idx_deals_group_of         on public.deals (group_of) where group_of is not null;
create index if not exists idx_deal_events_actor      on public.deal_events (actor) where actor is not null;
create index if not exists idx_listings_created_by    on public.company_listings (created_by) where created_by is not null;
create index if not exists idx_company_products_made_by on public.company_products (made_by_company_id) where made_by_company_id is not null;
create index if not exists idx_payment_orders_company on public.payment_orders (company_id) where company_id is not null;
create index if not exists idx_payment_orders_listing on public.payment_orders (listing_id) where listing_id is not null;
-- duplicates: an exact copy (0010's idx_jobs_live = idx_jobs_active) and single-column indexes whose column already
-- leads a wider index on the same table (every write paid for both)
drop index if exists public.idx_jobs_live;                -- = idx_jobs_active (active, created_at desc)
drop index if exists public.idx_job_apps_user;            -- (user_id)   ⊂ idx_job_apps_user_created
drop index if exists public.idx_posts_created;            -- (created_at desc) ⊂ idx_posts_created_id
drop index if exists public.idx_conn_requester;           -- (requester) ⊂ idx_conn_requester_status, connections_requester_addressee_key
drop index if exists public.idx_conn_addressee;           -- (addressee) ⊂ idx_conn_addressee_status
drop index if exists public.idx_msgs_receiver;            -- (receiver_id) ⊂ idx_msgs_receiver_id
drop index if exists public.idx_reactions_post;           -- (post_id)   ⊂ reactions_pkey (post_id, user_id)
drop index if exists public.idx_comments_post;            -- (post_id)   ⊂ idx_comments_post_created
drop index if exists public.idx_enquiries_type;           -- (type)      ⊂ idx_enquiries_live (type, status, created_at desc)
drop index if exists public.idx_saved_jobs_user;          -- (user_id)   ⊂ saved_jobs_pkey (user_id, job_id)

-- ── 8. F-47 suggest_people: bounded work for people with many connections ─────
-- Same result shape and ranking. Mutual counts come from my 300 most recent friends and up to 200 connections of each
-- friend per direction (hubs with thousands of connections no longer multiply the work); the final rows are read by key.
create or replace function public.suggest_people(p_limit int default 12)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean, mutual int)
language sql stable security definer set search_path = public as $$
  with me as (select auth.uid() as uid),
  lim as (select least(greatest(coalesce(p_limit, 12), 1), 50) as n),
  friends as materialized (select case when c.requester = me.uid then c.addressee else c.requester end as fid
              from public.connections c, me where c.status = 'accepted' and (c.requester = me.uid or c.addressee = me.uid)
              order by c.created_at desc nulls last limit 300),
  known as materialized (select case when c.requester = me.uid then c.addressee else c.requester end as pid
            from public.connections c, me where c.requester = me.uid or c.addressee = me.uid),
  second as (select x.pid, count(*)::int as mutual
             from friends f cross join lateral (
               (select c.addressee as pid from public.connections c where c.requester = f.fid and c.status = 'accepted' limit 200)
               union all
               (select c.requester from public.connections c where c.addressee = f.fid and c.status = 'accepted' limit 200)) x
             group by x.pid),
  ranked as (select s.pid, s.mutual from second s, me where s.pid <> me.uid and s.pid not in (select pid from known)
             order by s.mutual desc limit (select n from lim)),
  fill as (select p.id as pid, 0 as mutual from public.profiles p, me where p.id <> me.uid
             and p.id not in (select pid from known) and p.id not in (select pid from ranked)
           order by p.created_at desc limit (select n from lim)),
  picked as materialized (select * from ranked union all select * from fill)
  select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring, x.mutual
  from picked x join public.profiles p on p.id = x.pid
  where auth.uid() is not null and p.id = any(array(select pid from picked))
  order by x.mutual desc, p.created_at desc
  limit (select n from lim)
$$;

-- ── 9. F-110 messages: reads that use the pair and receiver indexes ─────────────
-- Both functions only ever return the caller's own messages (the pair includes the caller; new messages are to the
-- caller), so they run as definer: the "messages: own read" OR-policy no longer turns the pair / receiver index read
-- into a scan of all of a busy person's messages.
create or replace function public.conversation_messages(p_partner uuid, p_before_id bigint default null, p_limit int default 50)
returns setof public.messages language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); lo uuid; hi uuid;
begin
  if me is null or p_partner is null then return; end if;
  lo := least(me, p_partner); hi := greatest(me, p_partner);
  return query select m.* from public.messages m
    where least(m.sender_id, m.receiver_id) = lo and greatest(m.sender_id, m.receiver_id) = hi
      and (p_before_id is null or m.id < p_before_id)
    order by least(m.sender_id, m.receiver_id), greatest(m.sender_id, m.receiver_id), m.created_at desc, m.id desc
    limit least(greatest(coalesce(p_limit, 50), 1), 100);
end $$;
create or replace function public.new_messages(p_after bigint default 0)
returns setof public.messages language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then return; end if;
  return query select m.* from public.messages m where m.receiver_id = me and m.id > coalesce(p_after, 0) order by m.receiver_id, m.id limit 50;
end $$;
-- the newest message id addressed to me (live polling starts after it) — one index probe
create or replace function public.my_last_message_id() returns bigint
language sql stable security definer set search_path = public as $$
  select coalesce(max(m.id), 0) from public.messages m where m.receiver_id = auth.uid()
$$;
revoke all on function public.conversation_messages(uuid, bigint, int) from public, anon;
revoke all on function public.new_messages(bigint) from public, anon;
revoke all on function public.my_last_message_id() from public, anon;
grant execute on function public.conversation_messages(uuid, bigint, int) to authenticated;
grant execute on function public.new_messages(bigint) to authenticated;
grant execute on function public.my_last_message_id() to authenticated;

-- ── 10. F-112 get_reviews_many: `not r.hidden` matches the partial index (hidden is NOT NULL) ──
create or replace function public.get_reviews_many(p_ids uuid[], p_role text)
returns table (reviewee uuid, id bigint, author text, anonymous boolean, c1 smallint, c2 smallint, c3 smallint, c4 smallint, body text, created_at timestamptz, mine boolean)
language sql stable security definer set search_path = public as $$
  select r.reviewee, r.id, case when r.anonymous then null else p.name end, r.anonymous, r.c1, r.c2, r.c3, r.c4, r.body, r.created_at, r.reviewer = auth.uid()
  from public.job_reviews r join public.profiles p on p.id = r.reviewer
  where r.reviewee = any(p_ids) and r.reviewee_role = p_role and not r.hidden
  order by r.created_at desc limit 2000
$$;

-- ── 11. F-166 the conversation list follows a deleted message ──────────────────
-- (people cannot delete messages; Drugbox, an account deletion or SQL can) — both heads of each touched
-- conversation are recomputed once per statement: newest remaining message and the unread count, or the head goes.
create or replace function public.messages_heads_on_delete() returns trigger language plpgsql security definer set search_path = public as $$
begin
  with pairs as (select distinct sender_id as a, receiver_id as b from gone union select distinct receiver_id, sender_id from gone)
  update public.conversation_heads h
     set last_message = l.id, last_body = coalesce(nullif(l.body, ''), case when l.image_url is not null then '📷 Photo' end),
         last_at = l.created_at, last_from_me = (l.sender_id = h.owner),
         unread = (select count(*) from public.messages u where u.receiver_id = h.owner and u.sender_id = h.partner and u.read_at is null)
    from pairs p cross join lateral (
           select m.id, m.body, m.image_url, m.created_at, m.sender_id from public.messages m
            where least(m.sender_id, m.receiver_id) = least(p.a, p.b) and greatest(m.sender_id, m.receiver_id) = greatest(p.a, p.b)
            order by least(m.sender_id, m.receiver_id), greatest(m.sender_id, m.receiver_id), m.created_at desc, m.id desc limit 1) l
   where h.owner = p.a and h.partner = p.b;
  with pairs as (select distinct sender_id as a, receiver_id as b from gone union select distinct receiver_id, sender_id from gone)
  delete from public.conversation_heads h using pairs p
   where h.owner = p.a and h.partner = p.b
     and not exists (select 1 from public.messages m where least(m.sender_id, m.receiver_id) = least(p.a, p.b)
                                                      and greatest(m.sender_id, m.receiver_id) = greatest(p.a, p.b));
  return null;
end $$;
drop trigger if exists trg_messages_heads_delete on public.messages;
create trigger trg_messages_heads_delete after delete on public.messages referencing old table as gone
  for each statement execute function public.messages_heads_on_delete();
revoke all on function public.messages_heads_on_delete() from public, anon;   -- a trigger function, not an RPC

-- ── 12. F-46 no JIT compilation for API requests ───────────────────────────────
-- PostgREST plans are used once, so LLVM compile time (0.8 s measured on the deals list) is never paid back.
-- Set for this database's API login role; when the migration role may not alter it (hosted Supabase), run in the
-- SQL editor:  alter role authenticator in database postgres set jit = off;   (then `show jit` through the API = off)
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'authenticator') then
    execute format('alter role authenticator in database %I set jit = off', current_database());
  end if;
exception when insufficient_privilege then
  raise notice 'DRUGBOX 0022: could not turn JIT off for authenticator — run: alter role authenticator in database % set jit = off', current_database();
end $$;

-- ── 13. F-45 note: likes on one viral post ─────────────────────────────────────
-- Every like updates posts.like_count in the liker's transaction, so concurrent likes of ONE post queue on that row
-- (pgbench, 50 clients liking/unliking: ~120–170 likes/s on one post on 4 idle cores, 70–80/s on a loaded shared box with
-- or without 0022, vs ~1,000–2,500/s spread over posts; 0022 adds no measurable cost there). That ceiling is far above
-- what a B2B network sees on one post; moving the counter off the write path (delta table + periodic fold) is a
-- redesign of the feed's counters and is left for after launch measurements.

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
