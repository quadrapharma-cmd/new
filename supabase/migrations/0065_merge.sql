-- ═════════════════════════════════════════════════════════════════════
-- 0065 — the three areas together (integration of social 0040–0049, business 0050–0059, community 0060–0064)
--   1. open_candidates() returns a named table (RETURNS TABLE): a new profiles column can never change or break it; phone
--      stays a column that is always NULL (0036)
--   2. search_all() finds what business and community added, as their own pages show it: companies (not suspended, also by
--      a catalogue product or active ingredient), listings still on the market (not expired), open jobs (before their deadline),
--      groups not archived (unless I am a member); people and find_people() leave out suspended accounts (J-COMMUNITY-47)
--   3. one suspension for the whole app (social's account_suspensions, 0044/0047): every write path the business and community
--      areas added refuses a suspended or deleted account — company products, sites, certificates, documents, invitations,
--      follows, deal files, quote answers, listing enquiries, reviews' answers, group requests/invitations/listing answers/
--      reports, job applications, alerts, published CVs, claims and verification requests, post files — new rows and edits
--      of content; suspending from Admin → Users closes the member's open reports (reporters told) and is in the social log;
--      suspending from Reported members is in the Decided history; an admin account is suspended by neither
--   4. names (the name rule, 0038/0039): a name typed for someone else (company invitation) and the name printed on a
--      training certificate go through the same rule as profiles.name
--   5. a certificate is decided once (DX409), by whom, and listed in Decided (review_certificate, the Review queue's path);
--      verification requests keep one decide-once trigger (0063's, before the approval trigger)
--   6. jobs_search() (0060) at scale: the matching jobs are carried as (id, created_at) — counted and paged without copying
--      every whole row to disk — and the words are one LIKE ALL per row instead of a sub-query per row (20k jobs: the Jobs
--      page from ~70 ms to ~35 ms); same answers, same signature, same rights (security invoker: RLS as before)
--   7. market_search() (0054) the same way: the matching listings as (id, rank, created_at), the page's 40 rows read once
--      (20k listings: browsing the Market from ~40 ms to ~12 ms); same answers, signature and rights
-- Every object keeps or gets its own GRANT/REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. open_candidates() with named columns ──────────────────────────
-- a member reads only their own suspension (0044's policy): a list that leaves suspended accounts out asks this (true / false only)
create or replace function private.is_suspended(p_user uuid) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.account_suspensions s where s.user_id = p_user)
$$;
revoke all on function private.is_suspended(uuid) from public, anon, authenticated, service_role;
grant execute on function private.is_suspended(uuid) to authenticated, service_role;
drop function if exists public.open_candidates(int);
create function public.open_candidates(p_limit int default 40)
returns table (id uuid, name text, headline text, company text, country character(2), bio text, avatar_url text, cover_url text, website text,
               phone text, certs text, role text, verified boolean, account_type text, created_at timestamptz, updated_at timestamptz,
               location text, experience jsonb, education jsonb, certifications jsonb, skills text[], languages text[], open_to_work boolean,
               hiring boolean, profile_views integer, followers_count integer, years_experience integer, desired_role text, desired_type text,
               remote_ok boolean, available_since timestamptz, intro_video jsonb, intents jsonb, name_key text, name_needs_fix boolean)
language sql stable set search_path = public as $$
  select p.id, p.name, p.headline, p.company, p.country, p.bio, p.avatar_url, p.cover_url, p.website, null::text, p.certs, p.role,
         p.verified, p.account_type, p.created_at, p.updated_at, p.location, p.experience, p.education, p.certifications, p.skills,
         p.languages, p.open_to_work, p.hiring, p.profile_views, p.followers_count, p.years_experience, p.desired_role,
         p.desired_type, p.remote_ok, p.available_since, p.intro_video, p.intents, p.name_key, p.name_needs_fix
    from public.profiles p where p.open_to_work and p.id <> coalesce(auth.uid(), '00000000-0000-0000-0000-000000000000'::uuid)
     and p.id <> all (coalesce((select private.blocked_parties()), '{}'::uuid[]))
     and not private.is_suspended(p.id)
   order by p.created_at desc limit least(greatest(coalesce(p_limit, 40), 1), 100)
$$;
revoke all on function public.open_candidates(int) from public, anon, authenticated, service_role;
grant execute on function public.open_candidates(int) to authenticated, service_role;

-- ── 2. one search over what every area added ─────────────────────────
create or replace function public.search_all(p_q text, p_limit int default 6) returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); q text := regexp_replace(trim(coalesce(p_q, '')), '\s+', ' ', 'g'); pat text; pre text;
        n int := least(greatest(coalesce(p_limit, 6), 1), 20); bl uuid[];
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if length(q) < 2 or length(q) > 80 then return jsonb_build_object('q', q); end if;
  pre := replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_'); pat := '%' || pre || '%'; pre := pre || '%';
  bl := private.blocks_with_me();
  return jsonb_build_object('q', q,
    'people', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select p.id, p.name, p.headline, p.company, p.avatar_url, p.verified, p.location, p.country from public.profiles p
         where (p.name ilike pat or p.company ilike pat or p.headline ilike pat) and p.account_type is distinct from 'deleted' and p.id <> me and p.id <> all (bl)
           and not exists (select 1 from public.account_suspensions s where s.user_id = p.id)
         order by (p.name ilike pre) desc, (p.name ilike pat) desc, length(p.name), p.created_at desc limit n) x),
    'companies', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select c.id, c.slug, c.name, c.city, c.country, c.verified, c.logo_emoji, c.type from public.companies c
         where c.status <> 'suspended'
           and (c.name ilike pat or c.name_ar ilike pat
                or c.id in (select k.company_id from public.company_products k where k.name ilike pat or k.active_ingredient ilike pat or k.active_ingredient_ar ilike pat limit 200))
         order by (c.name ilike pre) desc, c.verified desc nulls last, length(c.name) limit n) x),
    'products', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select r.id, r.name, r.category, r.price, r.unit, r.emoji, r.user_id, (select s.name from public.profiles s where s.id = r.user_id) as seller from public.products r
         where r.active and (r.expires_at is null or r.expires_at > now()) and r.name ilike pat and r.user_id <> all (bl) order by (r.name ilike pre) desc, r.created_at desc limit n) x),
    'jobs', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select j.id, j.title, j.company, j.location, j.type, j.user_id from public.jobs j
         where j.active and (j.deadline is null or j.deadline >= current_date) and (j.title ilike pat or j.company ilike pat) and j.user_id <> all (bl) order by (j.title ilike pre) desc, j.created_at desc limit n) x),
    'groups', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select g.id, g.name, g.emoji, g.type, g.member_count from public.groups g
         where g.name ilike pat and (g.archived_at is null or public.is_group_member(g.id))
           and (g.type = 'public' or g.listed or g.created_by = me or public.is_group_member(g.id)
                or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = me))
         order by (g.name ilike pre) desc, g.member_count desc limit n) x),
    'posts', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select o.id, left(o.body, 240) as body, o.user_id, o.created_at, (select a.name from public.profiles a where a.id = o.user_id) as author from public.posts o
         where o.group_id is null and o.body ilike pat and o.user_id <> all (bl) order by o.created_at desc limit n) x));
end $$;
create or replace function public.find_people(p_q text default null, p_spec text default null, p_country text default null, p_limit int default 30)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean)
language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); words text[]; sp text[]; bl uuid[]; n int := least(greatest(coalesce(p_limit, 30), 1), 60);
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  words := array(select '%' || replace(replace(replace(w, '\', '\\'), '%', '\%'), '_', '\_') || '%'
                   from unnest(regexp_split_to_array(left(trim(coalesce(p_q, '')), 80), '\s+')) w where w <> '' limit 5);
  sp := case p_spec
    when 'regulatory' then array['%regulat%', '%registration%', '%dossier%']
    when 'quality' then array['%QA %', '%QC %', '%quality%', '%GMP%']
    when 'procurement' then array['%procure%', '%purchas%', '%sourcing%', '%buyer%']
    when 'production' then array['%production%', '%manufactur%', '%plant%', '%operations%']
    when 'sales' then array['%sales%', '%marketing%', '%business development%', '%commercial%']
    when 'rnd' then array['%R&D%', '%research%', '%formulat%']
    when 'supply' then array['%supply%', '%distribut%', '%logistic%', '%import%', '%export%']
    when 'medical' then array['%medical%', '%pharmacist%', '%clinical%', '%doctor%', '%physician%']
    when 'management' then array['%CEO%', '%founder%', '%director%', '%chairman%', '%general manager%', '%managing%']
    else null end;
  if coalesce(array_length(words, 1), 0) = 0 and sp is null and nullif(p_country, '') is null then return; end if;
  bl := private.blocks_with_me();
  -- built per call so each word is a plain "ilike" the trigram indexes serve (a generic plan would scan)
  return query execute 'select * from (select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring
      from public.profiles p where p.id <> $1 and p.account_type is distinct from ''deleted'' and p.id <> all ($2)'
    || ' and not exists (select 1 from public.account_suspensions s where s.user_id = p.id)'
    || (select coalesce(string_agg(format(' and (p.name ilike %1$L or p.company ilike %1$L or p.headline ilike %1$L)', w), ''), '') from unnest(words) w)
    || case when sp is null then '' else ' and p.headline ilike any ($3)' end
    || case when nullif(p_country, '') is null then '' else ' and p.country = $4' end
    || ' limit 400) x order by (x.id = any ($6)) desc,'
    || ' x.verified desc nulls last, x.name limit $5'   -- my connections first (a picker names the colleague I mean)   -- the first 400 matches, then ordered: a common word stays fast
    using me, bl, sp, upper(left(coalesce(p_country, ''), 2)), n,
          array(select case when c.requester = me then c.addressee else c.requester end from public.connections c
                 where c.status = 'accepted' and (c.requester = me or c.addressee = me) limit 5000);
end $$;

revoke all on function public.search_all(text, int) from public, anon, authenticated, service_role;
grant execute on function public.search_all(text, int) to authenticated, service_role;
revoke all on function public.find_people(text, text, text, int) from public, anon, authenticated, service_role;
grant execute on function public.find_people(text, text, text, int) to authenticated;

-- ── 3. one suspension for the whole app ──────────────────────────────
-- new rows: the tables the business and community areas added that a member writes (the triggers of 0047 / 0063 stay where they are)
do $$ declare t text; begin
  foreach t in array array['company_products', 'company_sites', 'site_certificates', 'company_documents', 'company_invites', 'company_followers',
                           'company_members', 'deal_files', 'review_responses', 'listing_inquiries', 'group_members', 'group_join_requests', 'group_invites',
                           'group_listing_responses', 'group_post_reports', 'job_applications', 'job_alerts', 'job_seeker_cvs', 'verification_requests',
                           'post_media', 'company_activity'] loop
    if to_regclass('public.' || t) is not null and not exists (select 1 from pg_trigger where tgrelid = ('public.' || t)::regclass and tgname = 'trg_' || t || '_not_suspended') then
      execute format('create trigger trg_%s_not_suspended before insert on public.%I for each row execute function public.writer_not_suspended()', t, t);
    end if;
  end loop;
  -- changes to content a member wrote (not counters: leaving a group or unfollowing a company stays possible)
  foreach t in array array['company_products', 'company_sites', 'site_certificates', 'company_documents', 'company_listings', 'group_listings',
                           'work_references', 'job_reviews', 'review_responses', 'job_applications'] loop
    if to_regclass('public.' || t) is not null then
      execute format('drop trigger if exists trg_%s_not_suspended_upd on public.%I', t, t);
      execute format('create trigger trg_%s_not_suspended_upd before update on public.%I for each row execute function public.writer_not_suspended()', t, t);
    end if;
  end loop;
end $$;

create or replace function public.member_decide(p_user uuid, p_action text, p_reason text default null, p_remove_posts boolean default false) returns integer
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); why text := nullif(left(trim(coalesce(p_reason, '')), 500), ''); n int := 0; removed int := 0;
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  if p_action not in ('suspend', 'dismiss') then raise exception 'Choose suspend or dismiss' using errcode = '22023'; end if;
  if p_user = me then raise exception 'You cannot suspend yourself' using errcode = '22023'; end if;
  if p_action = 'suspend' and exists (select 1 from public.profiles where id = p_user and role = 'admin') then
    raise exception 'An admin account cannot be suspended — change its role first' using errcode = '22023';
  end if;
  if p_action = 'suspend' then
    if why is null then raise exception 'Write the reason for the suspension' using errcode = '22023'; end if;
    insert into public.account_suspensions (user_id, reason, suspended_by) values (p_user, why, me)
      on conflict (user_id) do update set reason = excluded.reason, suspended_by = excluded.suspended_by, suspended_at = now();
    if p_remove_posts then delete from public.posts where user_id = p_user; get diagnostics removed = row_count; end if;
  end if;
  with a as (update public.member_reports set status = case when p_action = 'suspend' then 'actioned' else 'dismissed' end, decided_by = me, decided_at = now()
              where reported = p_user and status = 'open' returning reporter),
       b as (update public.message_reports set status = case when p_action = 'suspend' then 'actioned' else 'dismissed' end
              where reported = p_user and status = 'open' returning reporter),
       c as (update public.post_reports set status = case when p_action = 'suspend' then 'removed' else 'dismissed' end, decided_by = me, decided_at = now()
              where post_author = p_user and status = 'open' returning reporter),
       closed as (select reporter from a union all select reporter from b union all select reporter from c)
  insert into public.notifications (user_id, type, from_user, message, data)
    select distinct reporter, 'report_closed', null::uuid, null::text, jsonb_build_object('outcome', case when p_action = 'suspend' then 'member_actioned' else 'member_dismissed' end)
      from closed where reporter <> p_user;
  get diagnostics n = row_count;
  insert into public.moderation_log (admin, action, target_user, reason, detail)
    values (me, case when p_action = 'suspend' then 'suspend' else 'dismiss_reports' end, p_user, why, jsonb_build_object('posts_removed', removed, 'reporters_told', n));
  if p_action = 'suspend' then   -- merge: the Decided history (0063) lists it too
    perform private.log_decision('suspension', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), 'suspended', why);
  end if;
  return n;
end $$;

create or replace function public.lift_suspension(p_user uuid, p_reason text default null) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  delete from public.account_suspensions where user_id = p_user;
  if found then perform private.log_decision('suspension', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), 'restored', p_reason); end if;   -- merge
  insert into public.moderation_log (admin, action, target_user, reason) values (auth.uid(), 'lift_suspension', p_user, nullif(left(trim(coalesce(p_reason, '')), 500), ''));
end $$;

create or replace function public.admin_suspend(p_user uuid, p_reason text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin suspends accounts' using errcode = '42501'; end if;
  if p_user = auth.uid() then raise exception 'You cannot suspend your own account' using errcode = '22023'; end if;
  if exists (select 1 from public.profiles where id = p_user and role = 'admin') then raise exception 'An admin account cannot be suspended — change its role first' using errcode = '22023'; end if;
  if length(trim(coalesce(p_reason, ''))) < 3 then raise exception 'Give the reason — the member sees it' using errcode = '22023'; end if;
  if exists (select 1 from public.account_suspensions where user_id = p_user) then raise exception 'This account is already suspended' using errcode = 'DX409'; end if;
  insert into public.account_suspensions (user_id, reason, suspended_by) values (p_user, left(trim(p_reason), 500), auth.uid());
  perform private.log_decision('suspension', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), 'suspended', p_reason);
  -- merge: one suspension for the whole app — the reports about this member (social S-09) are closed and their reporters told
  with a as (update public.member_reports set status = 'actioned', decided_by = auth.uid(), decided_at = now() where reported = p_user and status = 'open' returning reporter),
       b as (update public.message_reports set status = 'actioned' where reported = p_user and status = 'open' returning reporter),
       closed as (select reporter from a union all select reporter from b)
  insert into public.notifications (user_id, type, from_user, message, data)
    select distinct reporter, 'report_closed', null::uuid, null::text, jsonb_build_object('outcome', 'member_actioned') from closed where reporter <> p_user;
  insert into public.moderation_log (admin, action, target_user, reason) values (auth.uid(), 'suspend', p_user, left(trim(p_reason), 500));
end $$;

create or replace function public.admin_unsuspend(p_user uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin restores accounts' using errcode = '42501'; end if;
  delete from public.account_suspensions where user_id = p_user;
  if not found then raise exception 'This account is not suspended' using errcode = 'P0002'; end if;
  insert into public.notifications (user_id, type, message) values (p_user, 'account', 'Your Drugbox account is active again');
  perform private.log_decision('suspension', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), 'restored');
  insert into public.moderation_log (admin, action, target_user) values (auth.uid(), 'lift_suspension', p_user);   -- merge
end $$;

revoke all on function public.member_decide(uuid, text, text, boolean) from public, anon, authenticated, service_role;
grant execute on function public.member_decide(uuid, text, text, boolean) to authenticated;
revoke all on function public.lift_suspension(uuid, text) from public, anon, authenticated, service_role;
grant execute on function public.lift_suspension(uuid, text) to authenticated;
revoke all on function public.admin_suspend(uuid, text) from public, anon, authenticated, service_role;
grant execute on function public.admin_suspend(uuid, text) to authenticated, service_role;
revoke all on function public.admin_unsuspend(uuid) from public, anon, authenticated, service_role;
grant execute on function public.admin_unsuspend(uuid) to authenticated, service_role;

-- ── 4. names typed for someone else, or printed for them ─────────────
-- a company invitation's name: the rule's normal form; a name the rule refuses is refused with its message (a server write is kept)
create or replace function public.company_invites_name_rule() returns trigger language plpgsql set search_path = public as $$
declare n text; p text;
begin
  if new.name is null or (tg_op = 'UPDATE' and new.name is not distinct from old.name) then return new; end if;
  n := nullif(public.person_name_norm(new.name), '');
  if n is null then new.name := null; return new; end if;
  p := public.person_name_problem(n);
  if p <> '' and auth.uid() is not null then          -- a member typed it (company_invite() runs as its owner, so is_server_call() would not tell)
    raise exception '%', public.person_name_message(new.name, p) using errcode = '23514', hint = 'name:' || p;
  end if;
  new.name := left(n, 120); return new;
end $$;
revoke all on function public.company_invites_name_rule() from public, anon, authenticated, service_role;
grant execute on function public.company_invites_name_rule() to authenticated, service_role;   -- it runs as the writer (company_invite runs as its owner)
drop trigger if exists trg_company_invites_name_rule on public.company_invites;
create trigger trg_company_invites_name_rule before insert or update of name on public.company_invites for each row execute function public.company_invites_name_rule();
-- a training certificate prints the holder's name as the rule writes it; a name that breaks the rule is not printed on one
create or replace function public.certificates_name_rule() returns trigger language plpgsql set search_path = public as $$
declare n text := coalesce(nullif(public.person_name_norm(new.name), ''), 'Drugbox member');
begin
  if tg_op = 'UPDATE' and new.name is not distinct from old.name then return new; end if;
  if public.person_name_problem(n) <> '' then
    raise exception 'Update your name in your profile first — it is printed on the certificate' using errcode = '23514', hint = 'name:certificate';
  end if;
  new.name := left(n, 200); return new;
end $$;
revoke all on function public.certificates_name_rule() from public, anon, authenticated, service_role;
grant execute on function public.certificates_name_rule() to authenticated, service_role;
drop trigger if exists trg_certificates_name_rule on public.certificates;
create trigger trg_certificates_name_rule before insert or update of name on public.certificates for each row execute function public.certificates_name_rule();

-- ── 5. decided once ──────────────────────────────────────────────────
-- 0059's trigger called the same function as 0063's "aa" trigger, but after the approval trigger: one is enough
drop trigger if exists trg_verification_requests_once on public.verification_requests;

create or replace function public.review_certificate(p_id bigint, p_ok boolean, p_reason text default null)
returns boolean language plpgsql security definer set search_path = public as $$
declare c record; v_reason text := nullif(left(trim(coalesce(p_reason, '')), 300), ''); v_owner uuid; v_site text;
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into c from public.site_certificates where id = p_id for update;
  if c.id is null then raise exception 'This certificate does not exist any more' using errcode = 'P0002'; end if;
  if public.is_company_member(c.company_id) then raise exception 'You belong to this company — another Drugbox reviewer decides' using errcode = '42501'; end if;
  if c.checked_at is not null then raise exception 'Already decided by % (checked)', private.who(c.checked_by) using errcode = 'DX409'; end if;   -- merge: decided once (0063)
  select owner_id into v_owner from public.companies where id = c.company_id;
  select name into v_site from public.company_sites where id = c.site_id;
  if p_ok then
    update public.site_certificates set checked_at = now(), checked_by = auth.uid() where id = p_id;
    if v_owner is not null then
      insert into public.notifications (user_id, type, from_user, company_id, data)
      values (v_owner, 'cert_checked', null, c.company_id, jsonb_build_object('name', c.name, 'site', v_site));
    end if;
  else
    if v_reason is null then raise exception 'Write the reason for the company' using errcode = '22023'; end if;
    delete from public.site_certificates where id = p_id;
    if c.file_path is not null then delete from storage.objects where bucket_id = 'documents' and name = c.file_path; end if;
    if v_owner is not null then
      insert into public.notifications (user_id, type, from_user, company_id, data)
      values (v_owner, 'cert_rejected', null, c.company_id, jsonb_build_object('name', c.name, 'site', v_site, 'reason', v_reason));
    end if;
  end if;
  perform private.log_decision('certificate', p_id::text, coalesce((select name from public.companies where id = c.company_id), 'Company') || ' · ' || c.name,
                               case when p_ok then 'checked' else 'rejected' end, v_reason, case when p_ok then null else jsonb_build_object('removed', true) end);   -- merge
  return true;
end $$;

revoke all on function public.review_certificate(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.review_certificate(bigint, boolean, text) to authenticated, service_role;

-- ── 6. jobs_search() — the same answers, cheaper at scale ─────────────
create or replace function public.jobs_search(p_q text default '', p_category text default null, p_types text[] default null,
                                              p_countries text[] default null, p_level text default null,
                                              p_before timestamptz default null, p_before_id bigint default null, p_limit int default 50)
returns jsonb language sql stable security invoker set search_path = public as $$
  with w as (select coalesce(array_agg('%' || replace(replace(replace(x, '\', '\\'), '%', '\%'), '_', '\_') || '%'), '{}') pats   -- each word: LIKE '%word%'
              from unnest(array_remove(regexp_split_to_array(lower(trim(coalesce(p_q, ''))), '\s+'), '')) x),
  m as (   -- the matching jobs as (id, created_at) only: counted and paged without carrying whole rows
    select j.id, j.created_at from public.jobs j, w
     where j.active and (j.deadline is null or j.deadline >= current_date)
       and (p_category is null or j.category = p_category)
       and (p_countries is null or cardinality(p_countries) = 0 or j.country = any (p_countries))
       and (p_types is null or cardinality(p_types) = 0 or lower(coalesce(j.type, '')) = any (p_types) or ('remote' = any (p_types) and j.remote))
       and (p_level is null or (case when j.seniority in ('exec', 'executive') then 'exec' when j.seniority in ('entry', 'junior', 'senior') then j.seniority else 'mid' end) = p_level)
       and (cardinality(w.pats) = 0 or j.search_text like all (w.pats))   -- every word appears (a null text matches none)
  ),
  pg as (
    select m.id, m.created_at from m
     where p_before is null or (m.created_at, m.id) < (p_before, coalesce(p_before_id, 9223372036854775807))
     order by m.created_at desc, m.id desc limit least(greatest(coalesce(p_limit, 50), 1), 100)
  )
  select jsonb_build_object('total', (select count(*) from m),
    'rows', coalesce((select jsonb_agg(to_jsonb(j) - 'search_text' || jsonb_build_object('poster', (
        select jsonb_build_object('id', p.id, 'name', p.name, 'headline', p.headline, 'company', p.company, 'avatar_url', p.avatar_url,
                                  'verified', p.verified, 'country', p.country, 'location', p.location)
          from public.profiles p where p.id = j.user_id),
        'company_verified', (select c.status = 'verified' from public.companies c where c.id = j.company_id),
        'company_slug', (select c.slug from public.companies c where c.id = j.company_id))
      order by j.created_at desc, j.id desc) from pg join public.jobs j on j.id = pg.id), '[]'::jsonb))
$$;
revoke all on function public.jobs_search(text, text, text[], text[], text, timestamptz, bigint, int) from public, anon, authenticated, service_role;
grant execute on function public.jobs_search(text, text, text[], text[], text, timestamptz, bigint, int) to authenticated, service_role;

-- ── 7. market_search() — the same answers, cheaper at scale ───────────
create or replace function public.market_search(p_q text default null, p_type text default null, p_category text default null, p_limit int default 40, p_offset int default 0)
returns jsonb language plpgsql stable security invoker set search_path = public set jit = off as $$
declare v_q text := nullif(left(trim(coalesce(p_q, '')), 100), ''); v_lim int := least(greatest(coalesce(p_limit, 40), 1), 100); v_off int := greatest(coalesce(p_offset, 0), 0);
        v_total int; v_rows jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  with hits as (   -- the matching listings as (id, rank, created_at) only: counted and paged without carrying whole rows
    select p.id, p.created_at, case when p.featured_until > now() then 2 when p.boosted_until > now() then 1 else 0 end as rank
      from public.products p
     where p.active and (p.expires_at is null or p.expires_at > now())
       and (p_type is null or p.type = p_type) and (p_category is null or p.category = p_category)
       and (v_q is null or p.name ilike '%' || v_q || '%' or p.description ilike '%' || v_q || '%')),
  pg as (select h.id, h.rank from hits h order by h.rank desc, h.created_at desc, h.id desc limit v_lim offset v_off)
  select (select count(*)::int from hits), coalesce((select jsonb_agg(to_jsonb(x) order by x.rank desc, x.created_at desc, x.id desc) from (
      select h.id, h.user_id, h.name, h.category, h.type, h.price, h.unit, h.moq, h.description, h.emoji, h.docs, h.certs_verified, h.lead_time, h.currency,
             h.company_id, h.created_at, h.expires_at, h.boosted_until, h.featured_until, h.view_count, h.inquiry_count, (h.coa_path is not null) as has_coa,
             pg.rank,
             (select json_build_object('slug', c.slug, 'name', c.name, 'verified', c.status = 'verified') from public.companies c where c.id = h.company_id) as co
        from pg join public.products h on h.id = pg.id) x), '[]'::jsonb)
    into v_total, v_rows;
  return jsonb_build_object('total', v_total, 'rows', v_rows);
end $$;
revoke all on function public.market_search(text, text, text, int, int) from public, anon, authenticated, service_role;
grant execute on function public.market_search(text, text, text, int, int) to authenticated, service_role;

notify pgrst, 'reload schema';
