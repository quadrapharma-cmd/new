-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 0021 — trust layer, company hub, deals engine, groups (code review 2026-10, items F-10…F-168)
-- Database only: the approved interface is untouched. Every change is re-runnable.
--   trust   F-10 a review needs a real interaction (has_real_interaction / can_review), one review per pair, hidden by moderators (F-34)
--           F-11 work references come from an accepted owner/admin/HR member of a verified company the person lists — no LIKE on free text
--           F-33 one dispute per warning, the moderator's decision is final     F-35 a block never reveals who blocked you
--   hub     F-13 certificates belong to the site's own company   F-14 editing a verified document clears the verification
--           F-36 a company page with deals on record cannot be deleted (RESTRICT)   F-37 an admin cannot remove the owner
--           F-38 requests are routed only to current members   F-42 claim_company(p_company_id, p_note) → reviewed in Admin → Review
--           F-100 is_company_member() counts accepted members only   F-108/F-109 search, public sites and the directory
--           F-168 is_moderator(): moderators work the review queues (approving a verification stays with admins)
--   deals   F-15 the "from" side is the company's current team, not the person who once sent it   F-16 finite, whole quantities; validity 1–365 days
--           F-39 track record ignores deals between related companies   F-40 only owner/admin/quality approve a questionnaire
--           F-105 flood limits   F-106 no requests to unclaimed pages or from suspended companies   F-107 open groups can be cancelled/declined,
--           the supplier may set the final price   F-167 the order's "sent" event is the member's
--   jobs    F-28 the applicant cannot set their status, the poster can; only note/CV editable by the applicant
--   groups  F-29 private groups: members and invited people see them, invitations let people join, membership rows cannot be moved
--   guards  check API callers only (anon / authenticated): SECURITY DEFINER functions, cascades and server work pass through
-- ═════════════════════════════════════════════════════════════════════════════

-- ── 0. helpers ──────────────────────────────────────────────────────────────
-- Drugbox staff: admins and moderators (moderators work the review queues; approving a verification stays with admins)
create or replace function public.is_moderator() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles p where p.id = auth.uid() and p.role in ('admin','moderator'))
$$;
revoke all on function public.is_moderator() from public; grant execute on function public.is_moderator() to anon, authenticated;

-- F-100: a membership counts only once the person accepted it (the creator's owner row is created accepted; companies.owner_id
-- always counts). An owner/admin adding someone — even as 'owner' — gives them nothing until they accept.
create or replace function public.is_company_member(cid bigint, roles text[] default null) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.company_members m
                 where m.company_id = cid and m.user_id = auth.uid() and m.accepted
                   and (roles is null or m.role = any(roles)))
      or exists (select 1 from public.companies c where c.id = cid and c.owner_id = auth.uid())
$$;
-- the same question about any person (internal: used by definer functions only)
create or replace function public.company_has_member(p_company bigint, p_user uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select p_company is not null and p_user is not null and (
         exists (select 1 from public.company_members m where m.company_id = p_company and m.user_id = p_user and m.accepted)
      or exists (select 1 from public.companies c where c.id = p_company and c.owner_id = p_user))
$$;
revoke all on function public.company_has_member(bigint, uuid) from public, anon, authenticated;
-- a person always sees their own memberships (needed to accept an invitation they cannot otherwise read)
drop policy if exists "members: read public or own team" on public.company_members;
create policy "members: read public or own team" on public.company_members for select
  using ((accepted and show_public) or user_id = (select auth.uid()) or public.is_company_member(company_id));

-- ── 1. F-10 / F-34: reviews after a real interaction, one per pair, moderators can hide ─────
-- a real interaction: an application to the other's job, a completed deal between the person and the other's company,
-- or an accepted connection with messages in BOTH directions (one unsolicited message is not an interaction)
create or replace function public.has_real_interaction(a uuid, b uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select a is not null and b is not null and a <> b and (
         exists (select 1 from public.job_applications ja join public.jobs j on j.id = ja.job_id
                 where (ja.user_id = a and j.user_id = b) or (ja.user_id = b and j.user_id = a))
      or exists (select 1 from public.deals d where d.status in ('delivered','closed','hired','confirmed','approved','agreed')
                 and ((d.from_user = a and public.company_has_member(d.to_company_id, b)) or (d.from_user = b and public.company_has_member(d.to_company_id, a))))
      or (exists (select 1 from public.connections c where c.status = 'accepted' and ((c.requester = a and c.addressee = b) or (c.requester = b and c.addressee = a)))
          and exists (select 1 from public.messages m where m.sender_id = a and m.receiver_id = b)
          and exists (select 1 from public.messages m where m.sender_id = b and m.receiver_id = a)))
$$;
revoke all on function public.has_real_interaction(uuid, uuid) from public, anon, authenticated;   -- never an oracle: internal only

-- who may review whom, and as what: answers only about the caller (no "did X deal with Y?" oracle)
create or replace function public.can_review(p_reviewer uuid, p_reviewee uuid, p_role text) returns boolean
language sql stable security definer set search_path = public as $$
  select p_reviewer = auth.uid() and p_reviewer <> p_reviewee and public.has_real_interaction(p_reviewer, p_reviewee)
     and case p_role
           when 'employer'  then exists (select 1 from public.jobs j where j.user_id = p_reviewee)            -- they hire through Drugbox
           when 'candidate' then exists (select 1 from public.profiles p where p.id = p_reviewee
                                         and (p.open_to_work or exists (select 1 from public.job_applications ja where ja.user_id = p_reviewee)))
           else false end
$$;
revoke all on function public.can_review(uuid, uuid, text) from public, anon; grant execute on function public.can_review(uuid, uuid, text) to authenticated;

drop policy if exists "reviews: write after a real interaction" on public.job_reviews;
create policy "reviews: write after a real interaction" on public.job_reviews
  for insert with check ((select auth.uid()) = reviewer and public.can_review(reviewer, reviewee, reviewee_role));
drop policy if exists "reviews: edit own" on public.job_reviews;
create policy "reviews: edit own" on public.job_reviews
  for update using ((select auth.uid()) = reviewer) with check ((select auth.uid()) = reviewer and public.can_review(reviewer, reviewee, reviewee_role));
drop policy if exists "reviews: moderators read" on public.job_reviews;
create policy "reviews: moderators read" on public.job_reviews for select using (public.is_moderator());

-- one review per pair of people (either role), and `hidden` belongs to moderators
create or replace function public.job_reviews_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or current_user not in ('anon', 'authenticated') then return new; end if;   -- server work, moderate_review()
  if exists (select 1 from public.job_reviews r where r.reviewer = new.reviewer and r.reviewee = new.reviewee and r.reviewee_role <> new.reviewee_role) then
    raise exception 'You have already reviewed this person' using errcode = '23505';
  end if;
  if tg_op = 'INSERT' then new.hidden := false; else new.hidden := old.hidden; new.updated_at := now(); end if;
  return new;
end $$;
drop trigger if exists trg_job_reviews_guard on public.job_reviews;
create trigger trg_job_reviews_guard before insert or update on public.job_reviews for each row execute function public.job_reviews_guard();

-- Admin → Review: hide / restore an abusive review (the only remedy besides the author deleting it)
create or replace function public.moderate_review(p_id bigint, p_hidden boolean) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_moderator() then raise exception 'Moderators only' using errcode = '42501'; end if;
  update public.job_reviews set hidden = coalesce(p_hidden, true), updated_at = now() where id = p_id;
  if not found then raise exception 'Review not found' using errcode = 'P0002'; end if;
end $$;
revoke all on function public.moderate_review(bigint, boolean) from public, anon; grant execute on function public.moderate_review(bigint, boolean) to authenticated;

-- the public label comes from the real relationship: "Verified applicant" only when an application exists
create or replace function public.get_reviews(p uuid, p_role text)
returns table (id bigint, author text, anonymous boolean, c1 smallint, c2 smallint, c3 smallint, c4 smallint, body text, created_at timestamptz, mine boolean)
language sql stable security definer set search_path = public as $$
  select r.id,
         case when not r.anonymous then coalesce(nullif(pr.company, ''), pr.name)
              when exists (select 1 from public.job_applications ja join public.jobs j on j.id = ja.job_id where ja.user_id = r.reviewer and j.user_id = r.reviewee)
                   then 'Verified applicant' else 'Anonymous' end,
         r.anonymous, r.c1, r.c2, r.c3, r.c4, r.body, r.created_at, r.reviewer = auth.uid()
  from public.job_reviews r join public.profiles pr on pr.id = r.reviewer
  where r.reviewee = p and r.reviewee_role = p_role and not r.hidden
  order by r.created_at desc;
$$;

-- the people I may review (same rules as can_review, so the Jobs page unlocks Review only where the insert will succeed),
-- never anyone I blocked or who blocked me
create or replace function public.my_interactions() returns table (party uuid) language sql stable security definer set search_path = public as $$
  select x.party from (
    select j.user_id as party from public.job_applications a join public.jobs j on j.id = a.job_id where a.user_id = auth.uid()
    union select a.user_id from public.job_applications a join public.jobs j on j.id = a.job_id where j.user_id = auth.uid()
    union select distinct m.receiver_id from public.messages m where m.sender_id = auth.uid()
          and exists (select 1 from public.messages m2 where m2.sender_id = m.receiver_id and m2.receiver_id = auth.uid())
          and exists (select 1 from public.connections c where c.status = 'accepted'
                      and ((c.requester = auth.uid() and c.addressee = m.receiver_id) or (c.requester = m.receiver_id and c.addressee = auth.uid())))
    union select distinct p.uid from public.deals d, lateral (
            select m.user_id as uid from public.company_members m where m.company_id = d.to_company_id and m.accepted
            union select c.owner_id from public.companies c where c.id = d.to_company_id and c.owner_id is not null) p
          where d.from_user = auth.uid() and d.status in ('delivered','closed','hired','confirmed','approved','agreed')
    union select distinct d.from_user from public.deals d where d.status in ('delivered','closed','hired','confirmed','approved','agreed')
          and public.company_has_member(d.to_company_id, auth.uid())
  ) x
  where x.party is not null and x.party <> auth.uid()
    and not exists (select 1 from public.job_lists l where l.list = 'black' and (l.until is null or l.until >= current_date)
                    and ((l.owner = auth.uid() and l.target = x.party) or (l.owner = x.party and l.target = auth.uid())))
$$;

-- ── 2. F-35: a block works both ways and nobody is told who blocked whom ───────
-- the client gets only its own list; the other direction is applied by the server (jobs policy, open_candidates, my_interactions).
-- The helper lives in a schema the API does not expose (PostgREST serves `public` only): policies can use it, nobody can call it.
create schema if not exists private;
grant usage on schema private to anon, authenticated;
create or replace function public.jobs_hidden_for_me()
returns table (party uuid) language sql stable security definer set search_path = public as $$
  select target from public.job_lists where owner = auth.uid() and list = 'black' and (until is null or until >= current_date)
$$;
create or replace function private.blocked_parties() returns uuid[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct x.p), '{}') from (
    select target as p from public.job_lists where owner = auth.uid() and list = 'black' and (until is null or until >= current_date)
    union all
    select owner from public.job_lists where target = auth.uid() and list = 'black' and (until is null or until >= current_date)) x
$$;
revoke all on function private.blocked_parties() from public; grant execute on function private.blocked_parties() to anon, authenticated;
create index if not exists idx_job_lists_target on public.job_lists (target) where list = 'black';
-- restrictive: ANDed with the existing read policy, so a blocked employer's jobs are simply not there (one lookup per query)
drop policy if exists "jobs: hidden between blocked people" on public.jobs;
create policy "jobs: hidden between blocked people" on public.jobs as restrictive for select
  using (user_id <> all (coalesce((select private.blocked_parties()), '{}'::uuid[])));
create or replace function public.open_candidates(p_limit int default 40)
returns setof public.profiles language sql stable security invoker set search_path = public as $$
  select * from public.profiles where open_to_work and id <> coalesce(auth.uid(), '00000000-0000-0000-0000-000000000000'::uuid)
    and id <> all (coalesce((select private.blocked_parties()), '{}'::uuid[]))
  order by created_at desc limit least(greatest(coalesce(p_limit, 40), 1), 100)
$$;

-- ── 3. F-11: work references from a verified company's team, matched on the company itself ──
create or replace function public.work_reference_rules()
returns trigger language plpgsql security definer set search_path = public as $$
declare worked boolean; has_company boolean; cname text;
begin
  -- the author must be an ACCEPTED owner/admin/HR member of a VERIFIED company (never profiles.company free text)
  select exists (select 1 from public.company_members m join public.companies c on c.id = m.company_id
                 where m.user_id = NEW.author and m.accepted and m.role in ('owner','admin','hr') and c.status = 'verified')
    into has_company;
  if not has_company then
    raise exception 'Only an owner, admin or HR member of a verified company can write a work reference' using errcode = '42501';
  end if;
  -- "worked with you": the person lists that company in their experience — by id, or by its exact (normalised) name
  select exists (
    select 1 from public.company_members m join public.companies c on c.id = m.company_id,
         public.profiles p, jsonb_array_elements(coalesce(p.experience, '[]'::jsonb)) e
    where m.user_id = NEW.author and m.accepted and m.role in ('owner','admin','hr') and c.status = 'verified'
      and p.id = NEW.candidate
      and ( ((e->>'company_id') ~ '^[0-9]{1,15}$' and (e->>'company_id')::bigint = c.id)
            or lower(regexp_replace(coalesce(e->>'company',''), '\s+', ' ', 'g')) = lower(regexp_replace(c.name, '\s+', ' ', 'g'))
            or (c.name_ar is not null and lower(regexp_replace(coalesce(e->>'company',''), '\s+', ' ', 'g')) = lower(regexp_replace(c.name_ar, '\s+', ' ', 'g'))) )
  ) into worked;
  if not worked then
    select string_agg(c.name, ' / ') into cname from public.company_members m join public.companies c on c.id = m.company_id
     where m.user_id = NEW.author and m.accepted and m.role in ('owner','admin','hr') and c.status = 'verified';
    raise exception 'This person has not listed % in their work experience, so you cannot write a work reference for them', coalesce(cname, 'your company');
  end if;
  if NEW.kind = 'honor' then
    NEW.status := 'published'; NEW.category := null; NEW.expires_at := null; NEW.evidence_path := null;
  else
    -- the evidence must be a real object in the author's own folder of the private bucket
    if NEW.evidence_path is null or NEW.evidence_path not like NEW.author::text || '/%'
       or not exists (select 1 from storage.objects o where o.bucket_id = 'reference-evidence' and o.name = NEW.evidence_path) then
      raise exception 'A warning needs an evidence document uploaded by you' using errcode = '23514';
    end if;
    NEW.status := 'pending';                                  -- moderated before anyone else sees it
    NEW.expires_at := now() + interval '2 years';
  end if;
  NEW.reply := null; NEW.replied_at := null; NEW.disputed_at := null; NEW.decided_by := null; NEW.decided_at := null;
  insert into public.notifications(user_id, type, from_user, message)
  values (NEW.candidate, 'work_reference', NEW.author,
          case when NEW.kind = 'honor' then 'added an honorable work record to your profile'
               else 'submitted a work reference about you — you can reply or dispute it before it is published' end);
  return NEW;
end; $$;

-- ── 4. F-33: a warning is disputed once; after the moderator decides, only a reply is possible ──
alter table public.work_references add column if not exists disputed_at timestamptz;
alter table public.work_references add column if not exists decided_by  uuid references public.profiles(id) on delete set null;
alter table public.work_references add column if not exists decided_at  timestamptz;
create or replace function public.reply_to_reference(ref_id bigint, reply_text text, dispute boolean default false)
returns void language plpgsql security definer set search_path = public as $$
declare w public.work_references;
begin
  select * into w from public.work_references where id = ref_id and candidate = auth.uid() for update;
  if w.id is null then raise exception 'Reference not found' using errcode = 'P0002'; end if;
  if coalesce(dispute, false) and w.kind = 'warn' then
    if w.disputed_at is not null or w.status not in ('pending','published') then          -- once; a rejected warning stays rejected
      raise exception 'This reference was already disputed and reviewed — you can still reply to it' using errcode = '42501';
    end if;
    update public.work_references set reply = left(reply_text, 2000), replied_at = now(), status = 'disputed', disputed_at = now() where id = w.id;
  else
    update public.work_references set reply = left(reply_text, 2000), replied_at = now() where id = w.id;
  end if;
end; $$;
create or replace function public.moderate_reference(ref_id bigint, new_status text)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not public.is_moderator() then raise exception 'Moderators only' using errcode = '42501'; end if;
  if new_status not in ('published','rejected','pending') then raise exception 'Invalid status' using errcode = '22023'; end if;
  -- publishing or rejecting is the decision; a decided dispute cannot be reopened by the person
  update public.work_references set status = new_status,
         decided_by = case when new_status in ('published','rejected') then auth.uid() else decided_by end,
         decided_at = case when new_status in ('published','rejected') then now() else decided_at end
   where id = ref_id;
  if not found then raise exception 'Reference not found' using errcode = 'P0002'; end if;
end; $$;

-- ── 5. F-13 / F-108: certificates belong to the site's own company; suspended companies are not served ──
delete from public.site_certificates t using public.company_sites s where s.id = t.site_id and s.company_id <> t.company_id;   -- forged by definition
create unique index if not exists company_sites_id_company_uq on public.company_sites (id, company_id);
do $$ begin
  alter table public.site_certificates add constraint site_certificates_site_company_fk
    foreign key (site_id, company_id) references public.company_sites (id, company_id) on delete cascade on update cascade;
exception when duplicate_object then null; end $$;
-- only Drugbox (admins / server-side work) may claim 'public_list' provenance or set checked_at
create or replace function public.site_certificates_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or public.is_platform_admin() then return new; end if;
  if new.source = 'public_list' then new.source := 'company'; end if;
  if tg_op = 'INSERT' then new.checked_at := null;
  elsif new.name is distinct from old.name or new.expiry is distinct from old.expiry or new.checked_at is distinct from old.checked_at then new.checked_at := null; end if;
  return new;
end $$;
create or replace function public.company_sites_public(p_slug text)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', s.id, 'name', s.name, 'type', s.type, 'city', s.city, 'gov', s.governorate,
         'forms', s.dosage_forms, 'min_batch', s.min_batch, 'capacity', s.capacity, 'free_slots', s.free_slots,
         'certs', (select coalesce(json_agg(json_build_object('name', t.name, 'expiry', t.expiry, 'source', t.source, 'checked', t.checked_at) order by t.name), '[]'::json)
                   from public.site_certificates t where t.site_id = s.id and t.company_id = s.company_id)) order by s.id), '[]'::json)
  from public.company_sites s join public.companies c on c.id = s.company_id where c.slug = p_slug and c.status <> 'suspended'
$$;
create or replace function public.search_companies(q text default null, p_sector text default null, p_gov text default null,
                                                   p_limit int default 20, p_after bigint default null)
returns setof public.companies language sql stable as $$
  select c.* from public.companies c
  where c.status <> 'suspended'
    and (p_sector is null or p_sector = any(c.sectors))
    and (p_gov is null or c.governorate = p_gov)
    and (p_after is null or c.id > p_after)
    and (q is null or q = '' or c.name ilike '%' || q || '%' or c.name_ar ilike '%' || q || '%'
         or exists (select 1 from public.company_products p where p.company_id = c.id
                    and (p.name ilike '%' || q || '%' or p.active_ingredient ilike '%' || q || '%' or p.active_ingredient_ar ilike '%' || q || '%')))
  order by c.id
  limit least(greatest(p_limit, 1), 50)
$$;
-- F-109: the directory's LIMIT needs a deterministic ORDER BY (verified pages first, then VIP, then by name) — same projection as 0011
-- F-30: a VIP plan counts only until vip_until (same rule as is_vip() in 0023, written out here because 0023 runs later)
create or replace function public.directory_companies(p_limit int default 5000)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(x order by x.name), '[]'::json) from (
    select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
           c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours,
           case when c.plan = 'vip' and (c.vip_until is null or c.vip_until > now()) then 'vip' else 'free' end as plan,
           c.logo_url, c.follower_count, c.profile, c.created_at, c.intro_video,
           public.company_tier(c.id) as tier, public.is_company_member(c.id) as mine,
           (select coalesce(json_agg(distinct s.name), '[]'::json) from public.site_certificates s where s.company_id = c.id and (s.expiry is null or s.expiry >= current_date)) as certs,
           (select coalesce(json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                   'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name), '[]'::json) from public.company_products p where p.company_id = c.id) as products,
           public.company_track_record(c.id) as track
    from (select * from public.companies where status <> 'suspended'
          order by (status = 'verified') desc, (plan = 'vip' and (vip_until is null or vip_until > now())) desc, name, id
          limit least(greatest(coalesce(p_limit, 5000), 1), 10000)) c) x
$$;

-- ── 6. F-14: a company edit to a verified / under-review document clears the verification ──
create or replace function public.company_documents_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or public.is_platform_admin() then return new; end if;   -- server-side work and Drugbox: unrestricted
  if new.status = 'verified' and (tg_op = 'INSERT' or old.status is distinct from 'verified') then
    raise exception 'Only Drugbox can mark a document as verified' using errcode = '42501';
  end if;
  if tg_op = 'UPDATE' and old.status in ('verified','review')
     and (new.type is distinct from old.type or new.product is distinct from old.product or new.number is distinct from old.number
          or new.expiry is distinct from old.expiry or new.file_path is distinct from old.file_path or new.company_id is distinct from old.company_id) then
    new.status := 'declared';                                                     -- Drugbox never saw the new content
  end if;
  return new;
end $$;

-- ── 7. F-37 / F-38: the team — the owner cannot be removed, routing points only at current members ──
create or replace function public.company_members_guard() returns trigger language plpgsql as $$
declare cid bigint := coalesce(new.company_id, old.company_id);
        is_owner boolean := public.is_company_member(cid, array['owner']);
        is_admin boolean := public.is_company_member(cid, array['owner','admin']);
begin
  -- definer functions (the creator's owner row, an approved claim), cascades of a deleted page, and Drugbox: no team rules
  if current_user not in ('anon', 'authenticated') or public.is_platform_admin() then return coalesce(new, old); end if;
  if tg_op = 'DELETE' then
    if exists (select 1 from public.companies c where c.id = old.company_id and c.owner_id = old.user_id) then
      raise exception 'The page owner cannot be removed from the team' using errcode = '42501';
    end if;
    if old.role in ('owner','admin') and old.user_id <> auth.uid() and not is_owner then
      raise exception 'Only an owner can remove an owner or admin' using errcode = '42501';
    end if;
    return old;
  end if;
  if tg_op = 'INSERT' then
    if new.role in ('owner','admin') and not is_owner then raise exception 'Only an owner can add an owner or admin' using errcode = '42501'; end if;
    if new.user_id <> auth.uid() then new.accepted := false; new.show_public := false; end if;   -- consent belongs to the person
    return new;
  end if;
  if new.company_id <> old.company_id or new.user_id <> old.user_id then raise exception 'Membership cannot be moved' using errcode = '42501'; end if;
  if new.role <> old.role then
    if not is_admin then raise exception 'Only owners/admins change roles' using errcode = '42501'; end if;
    if (new.role in ('owner','admin') or old.role in ('owner','admin')) and not is_owner then raise exception 'Only an owner can grant or remove owner/admin' using errcode = '42501'; end if;
  end if;
  if (new.accepted <> old.accepted or new.show_public <> old.show_public) and old.user_id <> auth.uid() then
    raise exception 'Only the person can give or withdraw consent to be listed' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_company_members_guard on public.company_members;
create trigger trg_company_members_guard before insert or update or delete on public.company_members for each row
  when (auth.uid() is not null)
  execute function public.company_members_guard();

-- a request can be routed only to someone on the team today
create or replace function public.company_routing_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if not public.company_has_member(new.company_id, new.user_id) then
    raise exception 'Requests can only be routed to a member of the team' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_company_routing_guard on public.company_routing;
create trigger trg_company_routing_guard before insert or update on public.company_routing for each row execute function public.company_routing_guard();
-- …and routing to someone who left (or withdrew consent) is dropped with them
create or replace function public.company_members_cleanup() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'DELETE' or (old.accepted and not new.accepted) then
    delete from public.company_routing r where r.company_id = old.company_id and r.user_id = old.user_id
      and not exists (select 1 from public.companies c where c.id = old.company_id and c.owner_id = old.user_id);
  end if;
  return null;
end $$;
drop trigger if exists trg_company_members_cleanup on public.company_members;
create trigger trg_company_members_cleanup after update or delete on public.company_members for each row execute function public.company_members_cleanup();
-- who receives a request: the routed person while they are still on the team, else the owner, else the first owner/admin
create or replace function public.deal_receiver(p_company bigint, p_type text) returns uuid language sql stable security definer set search_path = public as $$
  select coalesce(
    (select r.user_id from public.company_routing r where r.company_id = p_company
       and r.request_type = case p_type when 'group' then 'group_order' else p_type end
       and public.company_has_member(p_company, r.user_id)),
    (select c.owner_id from public.companies c where c.id = p_company),
    (select m.user_id from public.company_members m where m.company_id = p_company and m.role in ('owner','admin') and m.accepted order by m.created_at limit 1))
$$;

-- ── 8. F-36: a company page with deals, orders or AVL entries on record cannot be deleted (RESTRICT, not cascade) ──
-- Chosen: RESTRICT with a clear message. The counterparty's history and the public track record survive; a page with history is
-- closed by Drugbox (status 'suspended'), a page without history can still be deleted by its owner. Constraint names are kept
-- (the adapter embeds through approved_suppliers_*_fkey).
do $$ declare k record; begin
  for k in select * from (values
      ('public.deals',              'deals_from_company_id_fkey',              'from_company_id'),
      ('public.deals',              'deals_to_company_id_fkey',                'to_company_id'),
      ('public.deal_members',       'deal_members_company_id_fkey',            'company_id'),
      ('public.approved_suppliers', 'approved_suppliers_buyer_company_id_fkey','buyer_company_id'),
      ('public.approved_suppliers', 'approved_suppliers_supplier_company_id_fkey','supplier_company_id')) v(tbl, con, col) loop
    if exists (select 1 from pg_constraint where conname = k.con and conrelid = k.tbl::regclass and confdeltype <> 'r') then
      execute format('alter table %s drop constraint %I', k.tbl, k.con);
      execute format('alter table %s add constraint %I foreign key (%I) references public.companies(id) on delete restrict', k.tbl, k.con, k.col);
    end if;
  end loop;
end $$;
-- (definer: it must see every counterparty's rows, whatever the deleting person may read)
create or replace function public.companies_before_delete() returns trigger language plpgsql security definer set search_path = public as $$
begin
  -- server work and Drugbox: the RESTRICT keys above still protect other companies' history
  if auth.uid() is null or public.is_platform_admin() then return old; end if;
  if exists (select 1 from public.deals d where d.from_company_id = old.id or d.to_company_id = old.id)
     or exists (select 1 from public.deal_members m where m.company_id = old.id)
     or exists (select 1 from public.approved_suppliers a where a.buyer_company_id = old.id or a.supplier_company_id = old.id) then
    raise exception 'This company has deals on record and cannot be deleted — ask Drugbox to close the page' using errcode = '42501';
  end if;
  return old;
end $$;
drop trigger if exists trg_companies_before_delete on public.companies;
create trigger trg_companies_before_delete before delete on public.companies for each row execute function public.companies_before_delete();

-- ── 9. F-42 / F-168: claiming a page, and the review queues for moderators ──
alter table public.verification_requests add column if not exists claim boolean not null default false;   -- "this page is mine" (no documents yet)
-- CONTRACT for the adapter: claim_company(p_company_id, p_note) → the request id. The page must be unclaimed; Drugbox reviews it in
-- Admin → Review (verification requests); approval makes the claimant the owner and the page 'pending' (then it gets verified as usual).
create or replace function public.claim_company(p_company_id bigint, p_note text default null) returns bigint
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); c public.companies; rid bigint;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into c from public.companies where id = p_company_id;
  if c.id is null then raise exception 'Company not found' using errcode = 'P0002'; end if;
  if c.status <> 'unclaimed' or c.owner_id is not null then raise exception 'This page is already claimed' using errcode = '42501'; end if;
  if exists (select 1 from public.verification_requests v where v.company_id = c.id and v.submitted_by = me and v.claim and v.status = 'pending') then
    raise exception 'Your claim is already under review' using errcode = '42501';
  end if;
  if (select count(*) from public.verification_requests v where v.submitted_by = me and v.claim and v.created_at > now() - interval '1 day') >= 5 then
    raise exception 'Too many claims today — please try again tomorrow' using errcode = '42501';
  end if;
  insert into public.verification_requests (company_id, submitted_by, registry, note, claim)
  values (c.id, me, coalesce(nullif(trim(c.registry), ''), 'claim-' || c.id), left(nullif(trim(p_note), ''), 1000), true)
  returning id into rid;
  return rid;
end $$;
revoke all on function public.claim_company(bigint, text) from public, anon; grant execute on function public.claim_company(bigint, text) to authenticated;

create or replace function public.verification_requests_apply() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> old.status then
    if auth.uid() is not null and not public.is_moderator() then raise exception 'Only Drugbox reviews verification requests' using errcode = '42501'; end if;
    if new.status = 'approved' and auth.uid() is not null and not public.is_platform_admin() then
      raise exception 'Only a Drugbox admin can approve a verification' using errcode = '42501';
    end if;
    new.reviewed_by := auth.uid(); new.reviewed_at := now();
    if new.status = 'approved' then
      if new.claim then
        -- the claimant becomes the owner; the page goes 'pending' and is verified through a normal request with documents
        update public.companies set owner_id = new.submitted_by, status = case when status = 'unclaimed' then 'pending' else status end
         where id = new.company_id and owner_id is null;
        if not found then raise exception 'This page is already claimed' using errcode = '42501'; end if;
        insert into public.company_members (company_id, user_id, role, accepted, show_public) values (new.company_id, new.submitted_by, 'owner', true, true)
          on conflict (company_id, user_id) do update set role = 'owner', accepted = true;
      else
        update public.companies set status = 'verified', registry = new.registry, tax_verified = true,
               licensed = licensed or new.licence_path is not null where id = new.company_id;
      end if;
    end if;
  end if;
  return new;
end $$;
create or replace function public.verification_decided_notify() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> old.status and new.status in ('approved','rejected') then
    insert into public.notifications (user_id, type, from_user, message)
    values (new.submitted_by, 'verification', auth.uid(),
            case when new.status = 'approved' and new.claim then 'Your claim was approved — the company page is yours; submit the registry and licence to get verified'
                 when new.status = 'approved' then 'Your company is verified ✓'
                 else 'Verification needs another look: ' || coalesce(new.note, 'please check your documents') end);
  end if;
  return null;
end $$;
drop policy if exists "verification: team and Drugbox read" on public.verification_requests;
create policy "verification: team and Drugbox read" on public.verification_requests for select
  using (public.is_company_member(company_id) or submitted_by = (select auth.uid()) or public.is_moderator());
drop policy if exists "verification: Drugbox reviews" on public.verification_requests;
create policy "verification: Drugbox reviews" on public.verification_requests for update using (public.is_moderator());
drop policy if exists "reports: reporter, the company and Drugbox read" on public.company_reports;
create policy "reports: reporter, the company and Drugbox read" on public.company_reports for select
  using (reporter = (select auth.uid()) or public.is_company_member(company_id, array['owner','admin']) or public.is_moderator());
drop policy if exists "reports: the company or Drugbox close" on public.company_reports;
create policy "reports: the company or Drugbox close" on public.company_reports for update
  using (public.is_company_member(company_id, array['owner','admin']) or public.is_moderator())
  with check (public.is_company_member(company_id, array['owner','admin']) or public.is_moderator());
-- moderators open the verification documents they review (payment receipts stay with admins)
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator())
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    else false end
$$;

-- ── 10. F-28: the applicant applies and withdraws; the employer sets the status ──
drop policy if exists "job_apps: applicant manages own" on public.job_applications;
drop policy if exists "job_apps: applicant reads own" on public.job_applications;
create policy "job_apps: applicant reads own" on public.job_applications for select using ((select auth.uid()) = user_id);
drop policy if exists "job_apps: applicant applies as themself" on public.job_applications;
create policy "job_apps: applicant applies as themself" on public.job_applications for insert with check ((select auth.uid()) = user_id);
drop policy if exists "job_apps: applicant edits own note and CV" on public.job_applications;
create policy "job_apps: applicant edits own note and CV" on public.job_applications for update
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "job_apps: applicant withdraws" on public.job_applications;
create policy "job_apps: applicant withdraws" on public.job_applications for delete using ((select auth.uid()) = user_id);
drop policy if exists "job_apps: poster sets the status" on public.job_applications;
create policy "job_apps: poster sets the status" on public.job_applications for update
  using (exists (select 1 from public.jobs j where j.id = job_id and j.user_id = (select auth.uid())))
  with check (exists (select 1 from public.jobs j where j.id = job_id and j.user_id = (select auth.uid())));
-- which columns each side may write. Named so it runs BEFORE trg_fast_track_preferred (alphabetical), which may then shortlist.
create or replace function public.job_applications_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or current_user not in ('anon', 'authenticated') or public.is_platform_admin() then return new; end if;
  if tg_op = 'INSERT' then
    if exists (select 1 from public.jobs j where j.id = new.job_id and j.user_id = new.user_id) then raise exception 'You cannot apply to your own job' using errcode = '42501'; end if;
    if not exists (select 1 from public.jobs j where j.id = new.job_id and j.active) then raise exception 'This job is no longer open' using errcode = '42501'; end if;
    new.status := 'submitted'; new.created_at := now();
    return new;
  end if;
  if new.job_id <> old.job_id or new.user_id <> old.user_id or new.created_at is distinct from old.created_at then
    raise exception 'An application cannot be moved' using errcode = '42501';
  end if;
  if auth.uid() = old.user_id then
    if new.status is distinct from old.status then raise exception 'The status of an application is set by the employer' using errcode = '42501'; end if;
  elsif new.note is distinct from old.note or new.cv_path is distinct from old.cv_path then
    raise exception 'Only the status can be changed by the employer' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_application_guard on public.job_applications;
create trigger trg_application_guard before insert or update on public.job_applications for each row execute function public.job_applications_guard();

-- ── 11. F-29: private groups — members and invited people see them, invitations let people join ──
create table if not exists public.group_invites (
  group_id   bigint not null references public.groups(id) on delete cascade,
  user_id    uuid   not null references public.profiles(id) on delete cascade,
  invited_by uuid   references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  primary key (group_id, user_id)
);
create index if not exists idx_group_invites_user on public.group_invites (user_id);
create index if not exists idx_group_invites_invited_by on public.group_invites (invited_by);   -- set null when the inviter's account goes
alter table public.group_invites enable row level security;
do $$ begin
  create policy "group invites: the person and the group's admins read" on public.group_invites for select
    using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin']));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "group invites: admins invite" on public.group_invites for insert
    with check (invited_by = (select auth.uid()) and public.is_group_member(group_id, array['admin']));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "group invites: the person declines, or an admin withdraws" on public.group_invites for delete
    using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin']));
exception when duplicate_object then null; end $$;
drop policy if exists "groups: public read" on public.groups;
drop policy if exists "groups: public, own, member or invited read" on public.groups;
create policy "groups: public, own, member or invited read" on public.groups for select
  using (type = 'public' or created_by = (select auth.uid()) or public.is_group_member(id)
         or exists (select 1 from public.group_invites i where i.group_id = groups.id and i.user_id = (select auth.uid())));
drop policy if exists "group members: join a public group yourself" on public.group_members;
drop policy if exists "group members: join a public group or one you were invited to" on public.group_members;
create policy "group members: join a public group or one you were invited to" on public.group_members for insert
  with check (user_id = (select auth.uid()) and role = 'member'
              and (exists (select 1 from public.groups g where g.id = group_members.group_id and g.type = 'public')
                   or exists (select 1 from public.group_invites i where i.group_id = group_members.group_id and i.user_id = (select auth.uid()))));
-- an admin changes roles only: membership rows are never moved to another person or group
create or replace function public.group_members_guard() returns trigger language plpgsql as $$
begin
  if new.group_id <> old.group_id or new.user_id <> old.user_id then raise exception 'Membership cannot be moved' using errcode = '42501'; end if;
  new.joined_at := old.joined_at;
  return new;
end $$;
drop trigger if exists trg_group_members_guard on public.group_members;
create trigger trg_group_members_guard before update on public.group_members for each row execute function public.group_members_guard();
-- the invitation is used up by joining
create or replace function public.group_members_after_join() returns trigger language plpgsql security definer set search_path = public as $$
begin
  delete from public.group_invites where group_id = new.group_id and user_id = new.user_id;
  return null;
end $$;
drop trigger if exists trg_group_members_after_join on public.group_members;
create trigger trg_group_members_after_join after insert on public.group_members for each row execute function public.group_members_after_join();
-- member_count and created_by are kept by the database, not written from the browser. 0020's server_columns() already does
-- this for API callers (trg_groups_server_columns); the guard below is created only when that trigger is not there.
create or replace function public.groups_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or current_user not in ('anon', 'authenticated') or public.is_platform_admin() then return new; end if;   -- the counter trigger
  if tg_op = 'INSERT' then new.member_count := 0; else new.member_count := old.member_count; new.created_by := old.created_by; end if;
  return new;
end $$;
drop trigger if exists trg_groups_guard on public.groups;
do $$ begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_groups_server_columns' and tgrelid = 'public.groups'::regclass) then
    create trigger trg_groups_guard before insert or update on public.groups for each row execute function public.groups_guard();
  end if;
end $$;

-- ── 12. deals engine: F-15, F-16, F-39, F-40, F-105, F-106, F-107, F-167 ──
-- an open buying group can be cancelled by the organiser or declined by the supplier
create or replace function public.deal_flow() returns jsonb language sql immutable as $$ select '{
  "quote":   {"first":"sent","acts":{"sent":{"to":["quote","decline"],"from":["cancel"]},"quoted":{"from":["accept","counter","decline"],"to":["revise"]},"countered":{"to":["quote","decline"],"from":["cancel"]},"accepted":{"to":["confirm"]},"confirmed":{"to":["ship"]},"shipped":{"from":["receive"]},"delivered":{"from":["rate"]}}},
  "service": {"first":"sent","acts":{"sent":{"to":["propose","decline"],"from":["cancel"]},"proposed":{"from":["accept","decline"]},"accepted":{"to":["start"]},"in_progress":{"to":["deliver"]},"delivered":{"from":["rate"]}}},
  "surplus": {"first":"offered","acts":{"offered":{"to":["accept_offer","counter_offer","decline"],"from":["cancel"]},"countered":{"from":["accept_counter","decline"]},"accepted":{"to":["confirm"]},"confirmed":{"to":["ship"]},"shipped":{"from":["receive"]},"delivered":{"from":["rate"]}}},
  "questionnaire": {"first":"sent","acts":{"sent":{"to":["answer"]},"answered":{"from":["approve","reject"]}}},
  "dossier": {"first":"requested","acts":{"requested":{"to":["sign_nda","decline"]},"nda_signed":{"to":["share"]},"shared":{"from":["agree","decline"],"to":["decline"]}}},
  "job":     {"first":"applied","acts":{"applied":{"to":["shortlist","reject"]},"shortlisted":{"to":["interview","reject"]},"interview":{"to":["offer","reject"]},"offer":{"from":["accept_job","decline"]}}},
  "group":   {"first":"open","acts":{"open":{"from":["cancel"],"to":["decline"]},"target_reached":{"to":["confirm_group","decline"]}}}
}'::jsonb $$;

-- F-15: a deal's "from" side is the originating COMPANY (its current team); from_user alone counts only for person-originated job applications
drop policy if exists "deals: the two sides read" on public.deals;
create policy "deals: the two sides read" on public.deals for select
  using ((from_company_id is null and from_user = (select auth.uid()))
         or public.is_company_member(to_company_id)
         or (from_company_id is not null and public.is_company_member(from_company_id)));

create or replace function public.deal_create(p_type text, p_to_slug text, p_from_slug text, p_title text, p_lines jsonb default '{}'::jsonb,
                                              p_message text default '', p_group text default null, p_ref text default null)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v_to public.companies; v_from public.companies; d public.deals; first text; tgt numeric;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if public.deal_flow() -> p_type is null then raise exception 'Unknown request type' using errcode = '22023'; end if;
  -- F-16: a buying group's target is a finite number the engine can reach (NaN / Infinity / text never close or close at once)
  if p_type = 'group' then
    begin tgt := (p_lines ->> 'target')::numeric; exception when others then tgt := null; end;
    if tgt is null or tgt = 'NaN'::numeric or not (tgt >= 1 and tgt <= 1000000000) then
      raise exception 'Enter a group target between 1 and 1,000,000,000' using errcode = '22023';
    end if;
  end if;
  select * into v_to from public.companies where slug = p_to_slug and status <> 'suspended';
  if v_to.id is null then raise exception 'Company not found' using errcode = 'P0002'; end if;
  if v_to.status = 'unclaimed' or v_to.owner_id is null then raise exception 'This company has not claimed its page yet, so it cannot receive requests' using errcode = '42501'; end if;
  if p_type <> 'job' then
    select * into v_from from public.companies where slug = p_from_slug;
    if v_from.id is null or not public.is_company_member(v_from.id) then raise exception 'You can send this only on behalf of a company you belong to' using errcode = '42501'; end if;
    if v_from.status = 'suspended' then raise exception 'Your company is suspended and cannot send requests' using errcode = '42501'; end if;
    if v_from.id = v_to.id then raise exception 'You cannot send this to your own company' using errcode = '42501'; end if;
  end if;
  -- F-105: flood limits per person and hour (every request creates a deal, an event and a notification for the other side)
  if (select count(*) from public.deals x where x.from_user = me and x.created_at > now() - interval '1 hour') >= 30 then
    raise exception 'Too many requests in one hour — please try again later' using errcode = '42501';
  end if;
  if (select count(*) from public.deals x where x.from_user = me and x.to_company_id = v_to.id and x.created_at > now() - interval '1 hour') >= 10 then
    raise exception 'You have already sent several requests to this company in the last hour — please try again later' using errcode = '42501';
  end if;
  first := public.deal_flow() -> p_type ->> 'first';
  insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, lines, status, group_key, assignee)
  values (coalesce(nullif(p_ref, ''), 'D' || substr(md5(random()::text || clock_timestamp()::text), 1, 8)), p_type, p_title, v_from.id, me, v_to.id,
          coalesce(p_lines, '{}'::jsonb), first, p_group, public.deal_receiver(v_to.id, p_type))
  returning * into d;
  insert into public.deal_events (deal_id, side, action, note, actor) values (d.id, 'from', first, coalesce(p_message, ''), me);
  if d.assignee is not null and d.assignee <> me then
    insert into public.notifications (user_id, type, from_user, message) values (d.assignee, 'deal', me, p_title);
  end if;
  return d;
end $$;

-- F-16: a share is a finite whole number (NaN = NaN is TRUE in PostgreSQL: compare with 'NaN' or use a bounded range)
-- Existing shares that are NaN / Infinity can only come from that exploit (deal_join floored every real quantity): they are
-- removed. Any other older row outside the range keeps the constraint NOT VALID (it still applies to every new share).
do $$ declare n int; begin
  delete from public.deal_members where qty = 'NaN'::numeric or qty in ('Infinity'::numeric, '-Infinity'::numeric);
  get diagnostics n = row_count;
  if n > 0 then raise notice 'DRUGBOX 0021: removed % buying-group share(s) of NaN / Infinity', n; end if;
end $$;
alter table public.deal_members drop constraint if exists deal_members_qty_check;
alter table public.deal_members add constraint deal_members_qty_check check (qty >= 1 and qty <= 1000000000 and qty = floor(qty)) not valid;
do $$ begin
  alter table public.deal_members validate constraint deal_members_qty_check;
exception when check_violation then
  raise notice 'DRUGBOX 0021: deal_members has older shares outside 1..1e9 or not whole — the rule applies to new shares';
end $$;
create or replace function public.deal_join(p_ref text, p_from_slug text, p_qty numeric)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; v public.companies; total numeric; by_date date; q numeric;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref for update;
  if d.id is null or d.type <> 'group' then raise exception 'Buying group not found' using errcode = 'P0002'; end if;
  if d.status <> 'open' then raise exception 'This buying group is closed' using errcode = '42501'; end if;
  q := floor(p_qty);
  if q is null or q = 'NaN'::numeric or not (q >= 1 and q <= 1000000000) then raise exception 'Enter a quantity greater than zero' using errcode = '22023'; end if;
  begin by_date := (d.lines ->> 'by')::date; exception when others then by_date := null; end;
  if by_date is not null and by_date < current_date then raise exception 'This buying group closed on %', by_date using errcode = '42501'; end if;
  select * into v from public.companies where slug = p_from_slug;
  if v.id is null or not public.is_company_member(v.id) then raise exception 'You can join only on behalf of a company you belong to' using errcode = '42501'; end if;
  if v.status = 'suspended' then raise exception 'Your company is suspended and cannot join buying groups' using errcode = '42501'; end if;
  if v.id = d.to_company_id then raise exception 'The supplier cannot join its own buying group' using errcode = '42501'; end if;
  insert into public.deal_members as m (deal_id, company_id, qty) values (d.id, v.id, q)
    on conflict (deal_id, company_id) do update set qty = m.qty + q;
  insert into public.deal_events (deal_id, side, action, note, actor)
    values (d.id, 'member', 'join', v.name || ' joined with ' || q::text || ' ' || coalesce(d.lines ->> 'unit', ''), me);
  select sum(qty) into total from public.deal_members where deal_id = d.id;
  if total >= coalesce((d.lines ->> 'target')::numeric, 0) and coalesce((d.lines ->> 'target')::numeric, 0) > 0 then
    update public.deals set status = 'target_reached', updated_at = now() where id = d.id returning * into d;
    insert into public.deal_events (deal_id, side, action, note) values (d.id, 'system', 'target', 'Target reached (' || total::text || ' ' || coalesce(d.lines ->> 'unit', '') || ')');
    insert into public.notifications (user_id, type, from_user, message)
      select public.deal_receiver(d.to_company_id, 'group'), 'deal', me, 'Buying group reached its target: ' || d.title
      where public.deal_receiver(d.to_company_id, 'group') is not null;
  else
    update public.deals set updated_at = now() where id = d.id returning * into d;
  end if;
  return d;
end $$;

create or replace function public.deal_act(p_ref text, p_action text, p_data jsonb default '{}'::jsonb, p_side text default null)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; side text; allowed jsonb; days text; nxt text; notify uuid; mb record; o public.deals; from_side boolean; gprice text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref for update;
  if d.id is null then raise exception 'Request not found' using errcode = 'P0002'; end if;
  -- which side is the caller on? the "from" side is the company's current team; a person only for their own job application (F-15)
  from_side := (d.from_company_id is null and d.from_user = me) or (d.from_company_id is not null and public.is_company_member(d.from_company_id));
  if p_side = 'to' and public.is_company_member(d.to_company_id) then side := 'to';
  elsif p_side = 'from' and from_side then side := 'from';
  elsif p_side is null and public.is_company_member(d.to_company_id) then side := 'to';
  elsif p_side is null and from_side then side := 'from';
  else raise exception 'You are not part of this request' using errcode = '42501'; end if;
  allowed := public.deal_flow() -> d.type -> 'acts' -> d.status -> side;
  if allowed is null or not (allowed ? p_action) then raise exception 'That step is not available now' using errcode = '42501'; end if;
  -- F-40: qualifying a supplier writes the buyer's approved list — the quality team's decision (as the AVL policy says)
  if d.type = 'questionnaire' and p_action in ('approve','reject') and not public.is_company_member(d.from_company_id, array['owner','admin','quality']) then
    raise exception 'Only the owner, an admin or the quality team can approve or reject a supplier questionnaire' using errcode = '42501';
  end if;
  if p_action = 'accept' and d.offer is not null and d.offer_at is not null then
    days := substring(coalesce(d.offer ->> 'validity', '') from '([0-9]+)\s*day');          -- ASCII digits, as the interface reads it
    if days is not null and length(days) <= 3 and d.offer_at + make_interval(days => days::int) < now() then
      raise exception 'This offer expired — ask for a new quote (counter-offer)' using errcode = '42501';
    end if;
  end if;
  nxt := public.deal_next_status(d.type, p_action);
  p_data := coalesce(p_data, '{}'::jsonb);
  if p_action in ('quote','revise','propose') then
    -- F-16: the validity the supplier types must make sense (1–365 days); text without a number never expires
    days := substring(coalesce(p_data ->> 'validity', '') from '([0-9]+)\s*day');
    if days is not null and (length(days) > 3 or days::int not between 1 and 365) then
      raise exception 'Offer validity must be between 1 and 365 days' using errcode = '22023';
    end if;
    d.offer := jsonb_build_object('price', p_data ->> 'price', 'validity', coalesce(p_data ->> 'validity', '14 days'), 'terms', coalesce(p_data ->> 'terms', d.lines ->> 'inc', ''),
                                  'lead', coalesce(p_data ->> 'lead', p_data ->> 'timeline', ''), 'note', coalesce(p_data ->> 'note', ''));
    d.offer_at := now();
  elsif p_action in ('counter','counter_offer') then d.counter := jsonb_build_object('price', p_data ->> 'price', 'note', coalesce(p_data ->> 'note', ''));
  elsif p_action = 'accept_counter' and d.counter is not null then d.offer := jsonb_build_object('price', d.counter ->> 'price', 'validity', '7 days', 'terms', coalesce(d.lines ->> 'inc', '')); d.offer_at := now();
  elsif p_action = 'accept_offer' then d.offer := jsonb_build_object('price', d.lines ->> 'price', 'validity', 'agreed', 'terms', coalesce(d.lines ->> 'inc', 'EXW'));
  elsif p_action = 'answer' then d.answers := coalesce(p_data -> 'answers', d.answers);
  elsif p_action = 'receive' then d.ontime := coalesce(p_data ->> 'ontime', 'yes') <> 'no';
  elsif p_action = 'rate' then
    if coalesce((p_data ->> 'stars')::int, 0) not between 1 and 5 then raise exception 'Rating must be 1 to 5 stars' using errcode = '22023'; end if;
  elsif p_action = 'confirm_group' then
    -- F-107: the supplier may set the final group price when confirming (the organiser's "To be confirmed" is replaced)
    gprice := nullif(trim(coalesce(p_data ->> 'price', '')), '');
    if gprice is not null then d.lines := d.lines || jsonb_build_object('price', gprice); end if;
  end if;
  update public.deals set status = nxt, offer = d.offer, offer_at = d.offer_at, counter = d.counter, answers = d.answers, ontime = d.ontime, lines = d.lines, updated_at = now()
   where id = d.id returning * into d;
  insert into public.deal_events (deal_id, side, action, note, data, actor) values (d.id, side, p_action, coalesce(p_data ->> 'note', p_data ->> 'text', ''), p_data, me);
  -- the supplier confirmed the pooled price → one order per member, already accepted at the group price
  if d.type = 'group' and p_action = 'confirm_group' then
    for mb in select m.company_id, m.qty, c.name from public.deal_members m join public.companies c on c.id = m.company_id where m.deal_id = d.id loop
      insert into public.deals (type, title, from_company_id, from_user, to_company_id, lines, status, offer, offer_at, group_of, assignee)
      values ('quote', coalesce(d.lines ->> 'product', d.title) || ' — ' || mb.qty::text || ' ' || coalesce(d.lines ->> 'unit', '') || ' (group order)',
              mb.company_id, coalesce((select owner_id from public.companies where id = mb.company_id), d.from_user), d.to_company_id,
              jsonb_build_object('qty', mb.qty, 'unit', d.lines ->> 'unit', 'inc', coalesce(d.lines ->> 'inc', 'EXW')), 'accepted',
              jsonb_build_object('price', d.lines ->> 'price', 'validity', 'group price', 'terms', coalesce(d.lines ->> 'inc', 'EXW')), now(), d.id, d.assignee)
      returning * into o;
      -- F-167: the member's share is the member's own step; the supplier's confirmation is the supplier's
      insert into public.deal_events (deal_id, side, action, note, actor) values (o.id, 'from', 'sent', 'Share in group ' || d.title, o.from_user),
                                                                                 (o.id, 'to', 'accept', 'Group price confirmed: ' || coalesce(d.lines ->> 'price', ''), me);
      insert into public.notifications (user_id, type, from_user, message) select o.from_user, 'deal', me, o.title where o.from_user <> me;
    end loop;
  end if;
  -- an approved qualification questionnaire puts the supplier on the buyer's approved list
  if d.type = 'questionnaire' and p_action = 'approve' and d.from_company_id is not null then
    insert into public.approved_suppliers (buyer_company_id, supplier_company_id, status, note, updated_at)
    values (d.from_company_id, d.to_company_id, 'approved', 'Qualification questionnaire ' || d.ref, now())
    on conflict (buyer_company_id, supplier_company_id) do update set status = 'approved', note = excluded.note, updated_at = now();
  end if;
  -- tell the other side: the sender while they are still on their company's team, else whoever receives that company's requests
  notify := case when side = 'to' then
              (case when d.from_company_id is null or public.company_has_member(d.from_company_id, d.from_user) then d.from_user
                    else public.deal_receiver(d.from_company_id, d.type) end)
            else coalesce(d.assignee, public.deal_receiver(d.to_company_id, d.type)) end;
  if notify is not null and notify <> me then
    insert into public.notifications (user_id, type, from_user, message) values (notify, 'deal', me, d.title || ' — ' || replace(p_action, '_', ' '));
  end if;
  return d;
end $$;

-- F-39: a company's track record counts only real business from unrelated companies (no self-rating through a second company run
-- by the same people), and member orders created by confirm_group (answered the same instant) do not shape the response time.
-- "Related" = the two companies share an accepted team member (every owner has an accepted owner row, created with the page and
-- impossible to remove through the API, so a shared owner is a shared member).
create or replace function public.company_track_record(p_company bigint) returns json language sql stable security definer set search_path = public as $$
  with recv as (
    select d.*, (select min(e.created_at) from public.deal_events e where e.deal_id = d.id and e.side = 'to') as first_reply
    from public.deals d where d.to_company_id = p_company and d.type <> 'job'
      and not exists (select 1 from public.company_members a join public.company_members b on b.user_id = a.user_id
                      where a.company_id = p_company and a.accepted and b.company_id = d.from_company_id and b.accepted)),
  asked as (select * from recv where group_of is null),
  done as (select * from recv where type in ('quote','surplus','service') and status in ('delivered','closed'))
  select json_build_object(
    'orders',    (select count(*) from done),
    'ontime',    (select round(100.0 * count(*) filter (where ontime is not false) / nullif(count(*), 0)) from done),
    'rating',    (select round(avg((e.data ->> 'stars')::numeric), 1) from public.deal_events e join recv x on x.id = e.deal_id where e.action = 'rate'),
    'reviews',   (select count(*) from public.deal_events e join recv x on x.id = e.deal_id where e.action = 'rate'),
    'response',  (select round((percentile_cont(0.5) within group (order by extract(epoch from (first_reply - created_at)) / 3600))::numeric, 1) from asked where first_reply is not null),
    'requests',  (select count(*) from asked),
    'answered',  (select count(*) from asked where first_reply is not null))
$$;
-- F-167 (hygiene): the API roles never truncate engine tables
revoke truncate on public.deals, public.deal_events, public.deal_members, public.company_listings from anon, authenticated;
-- trigger functions are not RPCs: no EXECUTE for the API roles (a fresh build then matches a re-run of 0020)
revoke all on function public.companies_before_delete(), public.company_members_cleanup(), public.company_routing_guard(),
  public.group_members_after_join(), public.group_members_guard(), public.groups_guard(), public.job_applications_guard(),
  public.job_reviews_guard() from public, anon;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
