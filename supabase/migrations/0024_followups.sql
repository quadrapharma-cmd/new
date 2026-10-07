-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 0024 — follow-ups after the October 2026 verification (docs/FIX-STATUS-2026-10.md, round 2)
-- Database only: the approved interface is untouched. Every block is re-runnable (tools/migration_check.py).
--   F-115  Fawry: an order is paid only with the Fawry reference number payments-create received for it (the signed string
--          has no separators, so a genuine notification re-cut as merchantRefNumber 'DBX182' + paymentAmount '850.00' paid
--          another order). The webhook also requires paymentAmount = orderAmount (supabase/functions/fawry-webhook).
--   N-1    my_interactions(): set-based (no function call per deal): 3-4 ms instead of 115-145 ms at 20k deals
--   F-10   a review's role follows the relationship: 'employer' only after applying to that person's job (or to a job at a
--          company they run); 'candidate' only for someone who applied to the reviewer's job / company, or — as the approved
--          Jobs page says ("you can review a candidate after contacting them") — a candidate the reviewer, who hires through
--          Drugbox, has an accepted connection and a conversation in both directions with. A conversation alone no longer
--          makes anyone reviewable as an employer.
--   F-17   deleting the account of a company owner keeps the company and its history: companies.owner_id ON DELETE SET NULL,
--          the page becomes 'unclaimed' and the old owner's membership row goes (deals / buying groups are RESTRICT, F-36);
--          deals.from_user ON DELETE SET NULL, so a company's deals and buying groups outlive the member who sent them
--   F-18   one job_application notification per job and applicant (withdraw + re-apply adds none); a deleted comment takes
--          its notification; purge_old_notifications(p_days) (service role; daily via pg_cron when the extension exists)
--   F-32   the reported company cannot change a report's status (Drugbox decides) and never sees who reported it: the table
--          is read by the reporter and Drugbox; the company reads company_reports_received() (no reporter column)
--   F-26   PRIVACY-FIRST DEFAULT — nothing of the content graph is readable with the anon key: posts, comments, reactions,
--          post_media, jobs, products, enquiries, company_members, company_sites, company_products, site_certificates,
--          company_listings, work_references, groups, group_members, sponsored_suppliers are for signed-in members only.
--          The live app reads nothing before sign-in (checked: the logged-out app makes no REST call). Still public: settings,
--          ticker_items, payment_products, training_courses (no personal data). REVERSIBLE: to publish a table again (e.g. a
--          public landing page), run  alter policy "<policy name>" on public.<table> to public;  — the names are listed below.
--   F-44   indexes for the last ten foreign keys without one (+ the new notification keys)
--   admin  Drugbox admins can set profiles.verified (and role / account type) for a person — nothing else of someone else's profile
--   F-05   the old whole-directory RPC directory_companies() is no longer callable from the API (the app pages it)
-- supabase/tests/followups.rls.sql checks each item.
-- ═════════════════════════════════════════════════════════════════════════════

-- ── 1. F-115 Fawry: paid only with the reference issued for this order ─────────────────────────
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
  -- Fawry: the notification must carry the reference number Fawry issued for THIS order (stored by payments-create)
  if p_provider = 'fawry' and (o.provider_ref is null or p_provider_ref is distinct from o.provider_ref) then return 'reference mismatch'; end if;
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

-- ── 2. F-10 a review's role follows the relationship ──────────────────────────────────────────
create or replace function public.can_review(p_reviewer uuid, p_reviewee uuid, p_role text) returns boolean
language sql stable security definer set search_path = public as $$
  select p_reviewer = auth.uid() and p_reviewee is not null and p_reviewer <> p_reviewee
     and case p_role
           -- an employer: the reviewer applied to their job, or to a job at a company they run
           when 'employer' then exists (select 1 from public.job_applications ja join public.jobs j on j.id = ja.job_id
                                        where ja.user_id = p_reviewer and j.user_id = p_reviewee)
                             or exists (select 1 from public.deals d where d.type = 'job' and d.from_user = p_reviewer
                                        and public.company_has_member(d.to_company_id, p_reviewee))
           -- a candidate: they applied to the reviewer's job / company, or the reviewer (who hires through Drugbox) contacted
           -- them: an accepted connection and messages in both directions
           when 'candidate' then exists (select 1 from public.job_applications ja join public.jobs j on j.id = ja.job_id
                                         where ja.user_id = p_reviewee and j.user_id = p_reviewer)
                              or exists (select 1 from public.deals d where d.type = 'job' and d.from_user = p_reviewee
                                         and public.company_has_member(d.to_company_id, p_reviewer))
                              or (exists (select 1 from public.jobs j where j.user_id = p_reviewer)
                                  and exists (select 1 from public.profiles p where p.id = p_reviewee
                                              and (p.open_to_work or exists (select 1 from public.job_applications ja where ja.user_id = p_reviewee)))
                                  and exists (select 1 from public.connections c where c.status = 'accepted'
                                              and ((c.requester = p_reviewer and c.addressee = p_reviewee) or (c.requester = p_reviewee and c.addressee = p_reviewer)))
                                  and exists (select 1 from public.messages m where m.sender_id = p_reviewer and m.receiver_id = p_reviewee)
                                  and exists (select 1 from public.messages m where m.sender_id = p_reviewee and m.receiver_id = p_reviewer))
           else false end
$$;
revoke all on function public.can_review(uuid, uuid, text) from public, anon; grant execute on function public.can_review(uuid, uuid, text) to authenticated;

-- ── 3. N-1 my_interactions(): the same rules as can_review, set-based ──────────────────────────
-- The Jobs page unlocks Review exactly where the insert will succeed. "My companies" come once from my_company_ids();
-- no function is called per deal (the 0021 version scanned every deal and cost 115-180 ms at 20k deals).
create or replace function public.my_interactions() returns table (party uuid) language sql stable security definer set search_path = public as $$
  with me as (select auth.uid() as id)
  select x.party from (
    -- employers whose job I applied to
    select j.user_id as party from public.job_applications a join public.jobs j on j.id = a.job_id, me where a.user_id = me.id
    -- the team of a company whose job I applied to
    union select m.user_id from public.deals d join public.company_members m on m.company_id = d.to_company_id and m.accepted, me
          where d.from_user = me.id and d.type = 'job'
    union select c.owner_id from public.deals d join public.companies c on c.id = d.to_company_id, me
          where d.from_user = me.id and d.type = 'job'
    -- candidates who applied to my job or to my company
    union select a.user_id from public.job_applications a join public.jobs j on j.id = a.job_id, me where j.user_id = me.id
    union select d.from_user from public.deals d where d.type = 'job' and d.to_company_id in (select public.my_company_ids())
    -- candidates I contacted, when I hire through Drugbox: an accepted connection and messages both ways
    union select m.receiver_id from public.messages m, me
          where m.sender_id = me.id and exists (select 1 from public.jobs j where j.user_id = me.id)
            and exists (select 1 from public.messages m2 where m2.sender_id = m.receiver_id and m2.receiver_id = me.id)
            and exists (select 1 from public.connections c where c.status = 'accepted'
                        and ((c.requester = me.id and c.addressee = m.receiver_id) or (c.requester = m.receiver_id and c.addressee = me.id)))
            and exists (select 1 from public.profiles p where p.id = m.receiver_id
                        and (p.open_to_work or exists (select 1 from public.job_applications ja where ja.user_id = m.receiver_id)))
  ) x, me
  where x.party is not null and x.party <> me.id
    and not exists (select 1 from public.job_lists l where l.list = 'black' and (l.until is null or l.until >= current_date)
                    and ((l.owner = me.id and l.target = x.party) or (l.owner = x.party and l.target = me.id)))
$$;
revoke all on function public.my_interactions() from public, anon; grant execute on function public.my_interactions() to authenticated;
-- (the job applications to my companies use idx_deals_to (to_company_id, updated_at): measured as fast as a new
--  (to_company_id, status) index, so none is added — deals stay as cheap to write as before)

-- ── 4. F-17 an owner's account can be erased; the company and its history stay ─────────────────
-- companies.owner_id cascaded into the RESTRICT keys of deals / deal_members / approved_suppliers (F-36), so deleting the
-- account of an owner whose page had history failed with 23503. Now the page loses its owner: it becomes 'unclaimed'
-- (anyone can claim it through Admin → Review, F-42) and the old owner's membership goes. Drugbox removing an owner
-- (owner_id set to null on the server) does the same.
do $$ begin
  if exists (select 1 from pg_constraint where conname = 'companies_owner_id_fkey' and conrelid = 'public.companies'::regclass and confdeltype <> 'n') then
    alter table public.companies drop constraint companies_owner_id_fkey;
    alter table public.companies add constraint companies_owner_id_fkey foreign key (owner_id) references public.profiles (id) on delete set null;
  end if;
end $$;
create or replace function public.companies_owner_gone() returns trigger language plpgsql security definer set search_path = public as $$
begin
  new.status := 'unclaimed';
  delete from public.company_members m where m.company_id = old.id and m.user_id = old.owner_id;
  return new;
end $$;
revoke all on function public.companies_owner_gone() from public, anon, authenticated;
drop trigger if exists trg_companies_owner_gone on public.companies;
create trigger trg_companies_owner_gone before update of owner_id on public.companies for each row
  when (old.owner_id is not null and new.owner_id is null) execute function public.companies_owner_gone();
-- A company's deals and buying groups outlive the account of the member who sent them: the sender becomes unknown (null)
-- and the deal engine already answers through the company's current team (F-15). A person's own job requests to a company
-- (type 'job', no "from" company) are their personal data and go with the account.
do $$ begin
  if exists (select 1 from pg_constraint where conname = 'deals_from_user_fkey' and conrelid = 'public.deals'::regclass and confdeltype <> 'n') then
    alter table public.deals alter column from_user drop not null;
    alter table public.deals drop constraint deals_from_user_fkey;
    alter table public.deals add constraint deals_from_user_fkey foreign key (from_user) references public.profiles (id) on delete set null;
  end if;
end $$;
create or replace function public.profiles_erase_person_deals() returns trigger language plpgsql security definer set search_path = public as $$
begin
  delete from public.deals where from_user = old.id and from_company_id is null;
  return old;
end $$;
revoke all on function public.profiles_erase_person_deals() from public, anon, authenticated;
drop trigger if exists trg_profiles_erase_person_deals on public.profiles;
create trigger trg_profiles_erase_person_deals before delete on public.profiles for each row execute function public.profiles_erase_person_deals();

-- ── 5. F-18 notifications: one per application, none for a deleted comment, a retention limit ──
alter table public.notifications add column if not exists job_id bigint references public.jobs (id) on delete cascade;
alter table public.notifications add column if not exists comment_id bigint references public.comments (id) on delete cascade;
create index if not exists idx_notifs_job on public.notifications (job_id) where job_id is not null;
create index if not exists idx_notifs_comment on public.notifications (comment_id) where comment_id is not null;
create unique index if not exists idx_notifs_application_once on public.notifications (user_id, from_user, job_id)
  where type = 'job_application' and job_id is not null;
-- once: "commented" notifications whose author has no comment left on that post
delete from public.notifications n
 where n.type = 'comment' and n.comment_id is null and n.post_id is not null and n.from_user is not null
   and not exists (select 1 from public.comments c where c.post_id = n.post_id and c.user_id = n.from_user);

create or replace function public.notify_comment()
returns trigger language plpgsql security definer set search_path = public as $$
declare owner uuid;
begin
  select user_id into owner from public.posts where id = new.post_id;
  if owner is not null and owner <> new.user_id then
    insert into public.notifications(user_id, type, from_user, post_id, comment_id, message)
    values (owner, 'comment', new.user_id, new.post_id, new.id, left(new.body, 140));   -- removed with the comment (FK cascade)
  end if;
  return null;
end; $$;

create or replace function public.notify_job_application()
returns trigger language plpgsql security definer set search_path = public as $$
declare poster uuid; t text;
begin
  select user_id, title into poster, t from public.jobs where id = new.job_id;
  if poster is not null and poster <> new.user_id then
    insert into public.notifications(user_id, type, from_user, job_id, message)
    values (poster, 'job_application', new.user_id, new.job_id, 'applied to ' || t)
    on conflict (user_id, from_user, job_id) where type = 'job_application' and job_id is not null do nothing;   -- re-applying adds none
  end if;
  return null;
end; $$;

-- whitelisted candidates go straight to the shortlist, and the employer is told (this notice replaces the plain one)
create or replace function public.fast_track_preferred()
returns trigger language plpgsql security definer set search_path = public as $$
declare poster uuid;
begin
  select user_id into poster from public.jobs where id = new.job_id;
  if exists (select 1 from public.job_lists where owner = poster and target = new.user_id and side = 'employer' and list = 'white') then
    new.status := 'shortlisted';
    insert into public.notifications(user_id, type, from_user, job_id, message)
    values (poster, 'job_application', new.user_id, new.job_id, 'A preferred candidate applied — added to your shortlist')
    on conflict (user_id, from_user, job_id) where type = 'job_application' and job_id is not null do nothing;
  end if;
  return new;
end; $$;

-- retention: notifications older than p_days (default 180) are removed; server only
create or replace function public.purge_old_notifications(p_days int default 180) returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if p_days is null or p_days < 7 then raise exception 'Keep at least 7 days of notifications' using errcode = '22023'; end if;
  delete from public.notifications where created_at < now() - make_interval(days => p_days);
  get diagnostics n = row_count; return n;
end $$;
revoke all on function public.purge_old_notifications(int) from public, anon, authenticated;
grant execute on function public.purge_old_notifications(int) to service_role;
-- daily at 02:23 UTC when pg_cron is enabled (Supabase → Database → Extensions → pg_cron); re-running replaces the job
do $$ begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    execute $q$select cron.schedule('drugbox-purge-notifications', '23 2 * * *', 'select public.purge_old_notifications(180)')$q$;
  end if;
exception when others then raise warning 'pg_cron job not scheduled: %', sqlerrm;
end $$;

-- ── 6. F-32 reports: Drugbox decides, the company never sees the reporter ─────────────────────
drop policy if exists "reports: reporter, the company and Drugbox read" on public.company_reports;
drop policy if exists "reports: the reporter and Drugbox read" on public.company_reports;
create policy "reports: the reporter and Drugbox read" on public.company_reports for select
  using (reporter = (select auth.uid()) or public.is_moderator());
drop policy if exists "reports: the company or Drugbox close" on public.company_reports;
drop policy if exists "reports: Drugbox decides" on public.company_reports;
create policy "reports: Drugbox decides" on public.company_reports for update
  using (public.is_moderator()) with check (public.is_moderator());

create or replace function public.company_reports_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if new.status = 'fixed' then new.status := 'resolved'; end if;
  if current_user not in ('anon', 'authenticated') or public.is_moderator() then return new; end if;
  raise exception 'Drugbox checks the page and closes the report' using errcode = '42501';
end $$;
revoke all on function public.company_reports_guard() from public, anon, authenticated;

-- what the company's owners and admins see: the report without the reporter
create or replace function public.company_reports_received(p_company bigint default null)
returns table (id bigint, company_id bigint, section text, issue text, correction text, status text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select r.id, r.company_id, r.section, r.issue, r.correction, r.status, r.created_at
  from public.company_reports r
  where (p_company is null or r.company_id = p_company)
    and r.company_id in (select x from public.my_company_ids() x where public.is_company_member(x, array['owner','admin']))
  order by r.created_at desc
  limit 200
$$;
revoke all on function public.company_reports_received(bigint) from public, anon;
grant execute on function public.company_reports_received(bigint) to authenticated;

-- ── 7. F-26 privacy-first: the content graph is for signed-in members (see the header to reverse it) ──
alter policy "posts: everyone can read" on public.posts to authenticated;
alter policy "comments: everyone can read" on public.comments to authenticated;
alter policy "reactions: everyone can read" on public.reactions to authenticated;
alter policy "post media rows: everyone reads" on public.post_media to authenticated;
alter policy "jobs: everyone can read" on public.jobs to authenticated;
alter policy "products: everyone can read" on public.products to authenticated;
alter policy "enquiries: everyone can read" on public.enquiries to authenticated;
alter policy "members: read public or own team" on public.company_members to authenticated;
alter policy "sites: everyone reads" on public.company_sites to authenticated;
alter policy "products: everyone reads" on public.company_products to authenticated;
alter policy "certs: everyone reads" on public.site_certificates to authenticated;
alter policy "listings: everyone reads active" on public.company_listings to authenticated;
alter policy "refs: who can read" on public.work_references to authenticated;
alter policy "groups: public, own, member or invited read" on public.groups to authenticated;
alter policy "group members: visible for public groups or to members" on public.group_members to authenticated;
alter policy "sponsors: everyone can read" on public.sponsored_suppliers to authenticated;

-- ── 8. F-44 the last foreign keys without an index ────────────────────────────────────────────
create index if not exists idx_verif_company        on public.verification_requests (company_id);
create index if not exists idx_verif_submitted_by   on public.verification_requests (submitted_by);
create index if not exists idx_verif_reviewed_by    on public.verification_requests (reviewed_by) where reviewed_by is not null;
create index if not exists idx_company_reports_company  on public.company_reports (company_id);
create index if not exists idx_company_reports_reporter on public.company_reports (reporter);
create index if not exists idx_sponsored_company    on public.sponsored_suppliers (company_id);
create index if not exists idx_company_routing_user on public.company_routing (user_id);
create index if not exists idx_company_docs_created_by on public.company_documents (created_by) where created_by is not null;
create index if not exists idx_refs_decided_by      on public.work_references (decided_by) where decided_by is not null;
create index if not exists idx_payment_orders_product on public.payment_orders (product_code);

-- ── 9. Drugbox admins verify people ───────────────────────────────────────────────────────────
-- profiles_guard already lets an admin change role / verified / account_type; this policy gives the API path. An admin
-- editing someone else's profile may change only those three columns.
drop policy if exists "profiles: Drugbox admins verify people" on public.profiles;
create policy "profiles: Drugbox admins verify people" on public.profiles for update
  using (public.is_platform_admin()) with check (public.is_platform_admin());
create or replace function public.profiles_admin_scope() returns trigger language plpgsql set search_path = public as $$
begin
  if current_user not in ('anon', 'authenticated') or old.id = auth.uid() then return new; end if;
  if (to_jsonb(new) - array['role','verified','account_type','updated_at']) is distinct from (to_jsonb(old) - array['role','verified','account_type','updated_at']) then
    raise exception 'Drugbox changes only the role and verification of someone else''s profile' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.profiles_admin_scope() from public, anon, authenticated;
drop trigger if exists trg_profiles_admin_scope on public.profiles;
create trigger trg_profiles_admin_scope before update on public.profiles for each row execute function public.profiles_admin_scope();

-- ── 10. F-05 the whole-directory RPC is not part of the API any more (the app uses directory_companies_page) ──
revoke execute on function public.directory_companies(int) from public, anon, authenticated;

notify pgrst, 'reload schema';
