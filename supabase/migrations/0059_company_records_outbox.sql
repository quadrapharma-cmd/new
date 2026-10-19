-- ═════════════════════════════════════════════════════════════════════
-- 0059 — a company's records, and news that reaches people outside the app (B-11, B-13, B-18, B-19; J-BUSINESS-16, 20, 23)
--   1. Compliance documents with their file (B-11): company_documents keep the PDF in the private documents bucket under
--      companydocs/<company id>/… — the company's team and Drugbox's reviewers read it, nobody else; only its owners / admins /
--      regulatory / quality add or remove it. A document with a file waits for Drugbox ('review'); Drugbox verifies or rejects it
--      in Admin → Review (document_review) and the person who added it is told why. Its type, number and status stay public:
--      that is the company's compliance passport.
--   2. Memberships (B-18): a chamber / export council membership is a company document of type 'Membership' that Drugbox
--      confirms the same way; only then does the page show it as confirmed.
--   3. Activity log (B-19): company_activity — who in the team did what (page edits, deals, team changes), readable and written
--      by the company's own team only, newest first; the database keeps the author and the time.
--   4. E-mail outbox (B-13): every notification of a kind worth an e-mail (deals, payments, invitations, reviews, documents…)
--      is queued in notification_outbox for the person — unless they turned e-mails off (notification_prefs). The
--      notify-dispatch function (service role, provider secrets only as function secrets) sends and marks them; nobody else
--      can read or change the queue.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. documents with their file ────
alter table public.company_documents drop constraint if exists company_documents_type_check;
alter table public.company_documents add constraint company_documents_type_check check (type in ('CEP','DMF (US)','ASMF (EU)','WHO PQ','GDP certificate','ISO 9001','Stability data (Zone IVb)','Site master file','Manufacturing licence','Membership'));
alter table public.company_documents add column if not exists file_name   text;
alter table public.company_documents add column if not exists review_note text;
alter table public.company_documents add column if not exists reviewed_by uuid references public.profiles(id) on delete set null;
alter table public.company_documents add column if not exists reviewed_at timestamptz;
do $$ begin
  alter table public.company_documents add constraint company_documents_more_len check (length(file_name) <= 160 and length(review_note) <= 300 and length(file_path) <= 300 and length(product) <= 200);
exception when duplicate_object then null; end $$;
create index if not exists idx_company_docs_review on public.company_documents (created_at) where status = 'review';
create index if not exists idx_company_docs_reviewed_by on public.company_documents (reviewed_by) where reviewed_by is not null;

create or replace function public.company_documents_guard() returns trigger language plpgsql as $$
begin
  if auth.uid() is null or public.is_platform_admin() then return new; end if;   -- server-side work and Drugbox: unrestricted
  if new.status = 'verified' and (tg_op = 'INSERT' or old.status is distinct from 'verified') then
    raise exception 'Only Drugbox can mark a document as verified' using errcode = '42501';
  end if;
  if new.status = 'rejected' and (tg_op = 'INSERT' or old.status is distinct from 'rejected') then
    raise exception 'Only Drugbox can reject a document' using errcode = '42501';
  end if;
  if tg_op = 'INSERT' or new.file_path is distinct from old.file_path then
    if new.file_path is not null and (new.file_path !~ ('^companydocs/' || new.company_id::text || '/[A-Za-z0-9._-]{1,140}$')
       or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = new.file_path)) then
      raise exception 'Upload the document file for this company first' using errcode = '42501';
    end if;
  end if;
  if tg_op = 'INSERT' then
    new.status := case when new.file_path is not null then 'review' else 'declared' end; new.review_note := null; new.reviewed_by := null; new.reviewed_at := null;
    new.created_by := auth.uid(); new.created_at := now();
  elsif new.type is distinct from old.type or new.product is distinct from old.product or new.number is distinct from old.number
        or new.expiry is distinct from old.expiry or new.file_path is distinct from old.file_path or new.company_id is distinct from old.company_id then
    new.status := case when new.file_path is not null then 'review' else 'declared' end;    -- Drugbox never saw the new content
    new.review_note := null; new.reviewed_by := null; new.reviewed_at := null;
  elsif new.review_note is distinct from old.review_note or new.reviewed_by is distinct from old.reviewed_by or new.reviewed_at is distinct from old.reviewed_at then
    raise exception 'The review is written by Drugbox' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.company_documents_guard() from public, anon, authenticated, service_role;

-- the person who added a document may take it back; owners and admins may remove any
alter policy "documents: owners/admins delete" on public.company_documents
  using (public.is_company_member(company_id, array['owner','admin'])
         or (created_by = (select auth.uid()) and public.is_company_member(company_id, array['regulatory','quality'])));

-- the file goes with the row; Drugbox's decision reaches the person who added it
create or replace function public.company_documents_after() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'DELETE' then
    if old.file_path is not null then delete from storage.objects where bucket_id = 'documents' and name = old.file_path; end if;
    return null;
  end if;
  if new.status is distinct from old.status and new.status in ('verified', 'rejected') and new.created_by is not null then
    insert into public.notifications (user_id, type, from_user, company_id, data)
    values (new.created_by, 'document_reviewed', null, new.company_id,
            jsonb_build_object('company', (select name from public.companies where id = new.company_id), 'doc', new.type, 'number', new.number, 'outcome', new.status, 'reason', new.review_note));
  end if;
  return null;
end $$;
revoke all on function public.company_documents_after() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_documents_after on public.company_documents;
create trigger trg_company_documents_after after update or delete on public.company_documents for each row execute function public.company_documents_after();

create or replace function public.document_review(p_id bigint, p_ok boolean, p_reason text default null) returns boolean language plpgsql security definer set search_path = public as $$
declare v_reason text := nullif(left(trim(coalesce(p_reason, '')), 300), '');
begin
  if auth.uid() is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  if not p_ok and v_reason is null then raise exception 'Write the reason for the company' using errcode = '22023'; end if;
  update public.company_documents set status = case when p_ok then 'verified' else 'rejected' end, review_note = case when p_ok then null else v_reason end,
         reviewed_by = auth.uid(), reviewed_at = now()
   where id = p_id and status in ('review', 'declared');
  return found;
end $$;
revoke all on function public.document_review(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.document_review(bigint, boolean, text) to authenticated, service_role;

-- the file side of a document (its name, path, Drugbox's note, who added it) is for the company's team and Drugbox's reviewers only;
-- the columns stay ungranted, so everyone else reads the passport (type, number, status) and nothing more
create or replace function public.company_document_files(p_company bigint)
returns table (id bigint, type text, product text, number text, expiry text, status text, file_name text, file_path text, review_note text,
               created_by uuid, created_by_name text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select d.id, d.type, d.product, d.number, d.expiry::text, d.status, d.file_name, d.file_path, d.review_note, d.created_by, p.name, d.created_at
    from public.company_documents d left join public.profiles p on p.id = d.created_by
   where d.company_id = p_company and auth.uid() is not null and (public.is_company_member(p_company) or public.is_moderator())
   order by d.created_at desc
$$;
revoke all on function public.company_document_files(bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_document_files(bigint) to authenticated, service_role;

-- Admin → Review → Documents: what waits for Drugbox, oldest first
create or replace function public.documents_to_review(p_limit int default 100)
returns table (id bigint, company_id bigint, company text, slug text, type text, product text, number text, expiry text, file_name text, file_path text,
               created_by_name text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select d.id, d.company_id, c.name, c.slug, d.type, d.product, d.number, d.expiry::text, d.file_name, d.file_path, p.name, d.created_at
    from public.company_documents d join public.companies c on c.id = d.company_id left join public.profiles p on p.id = d.created_by
   where d.status = 'review' and public.is_moderator()
   order by d.created_at limit least(greatest(coalesce(p_limit, 100), 1), 500)
$$;
revoke all on function public.documents_to_review(int) from public, anon, authenticated, service_role;
grant execute on function public.documents_to_review(int) to authenticated, service_role;

-- documents bucket: companydocs/<company id>/… (the cases before are 0056's)
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator()
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
    when 'deals' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$' and public.deal_is_party(((storage.foldername(p_name))[2])::bigint)
    when 'companydocs' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint) or public.is_moderator())
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'deals' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$' and public.deal_is_party(((storage.foldername(p_name))[2])::bigint)
    when 'companydocs' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$'
                   and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin','regulatory','quality'])
    else false end
$$;

-- ── 3. activity log ────
create table if not exists public.company_activity (
  id          bigint generated always as identity primary key,
  company_id  bigint not null references public.companies(id) on delete cascade,
  actor       uuid references public.profiles(id) on delete set null,
  text        text not null check (length(text) between 1 and 300),
  created_at  timestamptz not null default now()
);
create index if not exists idx_company_activity_co on public.company_activity (company_id, created_at desc);
create index if not exists idx_company_activity_actor on public.company_activity (actor) where actor is not null;
alter table public.company_activity enable row level security;
do $$ begin
  create policy "company activity: the team reads" on public.company_activity for select to authenticated using (public.is_company_member(company_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "company activity: the team writes as itself" on public.company_activity for insert to authenticated
    with check (public.is_company_member(company_id) and actor = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on public.company_activity from public, anon, authenticated;
grant select, insert on public.company_activity to authenticated;
grant all on public.company_activity to service_role;
create or replace function public.company_activity_stamp() returns trigger language plpgsql as $$
begin new.created_at := now(); return new; end $$;
revoke all on function public.company_activity_stamp() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_activity_stamp on public.company_activity;
create trigger trg_company_activity_stamp before insert on public.company_activity for each row execute function public.company_activity_stamp();

-- ── 4. e-mail outbox ────
create table if not exists public.notification_prefs (
  user_id    uuid primary key references public.profiles(id) on delete cascade,
  email      boolean not null default true,
  updated_at timestamptz not null default now()
);
alter table public.notification_prefs enable row level security;
do $$ begin
  create policy "notification prefs: your own" on public.notification_prefs for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on public.notification_prefs from public, anon, authenticated;
grant select, insert, update on public.notification_prefs to authenticated;
grant all on public.notification_prefs to service_role;

create table if not exists public.notification_outbox (
  id              bigint generated always as identity primary key,
  notification_id bigint references public.notifications(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  kind            text not null,
  status          text not null default 'pending',
  attempts        int not null default 0,
  last_error      text check (length(last_error) <= 500),
  created_at      timestamptz not null default now(),
  sent_at         timestamptz,
  claimed_at      timestamptz
);
alter table public.notification_outbox add column if not exists claimed_at timestamptz;
alter table public.notification_outbox drop constraint if exists notification_outbox_status_check;
alter table public.notification_outbox add constraint notification_outbox_status_check check (status in ('pending', 'sending', 'sent', 'failed', 'skipped'));
drop index if exists public.idx_outbox_pending;
create index if not exists idx_outbox_pending2 on public.notification_outbox (created_at) where status in ('pending', 'sending');
create index if not exists idx_outbox_user on public.notification_outbox (user_id);
create index if not exists idx_outbox_notification on public.notification_outbox (notification_id);
alter table public.notification_outbox enable row level security;
do $$ begin
  create policy "outbox: Drugbox reads" on public.notification_outbox for select to authenticated using (public.is_platform_admin());
exception when duplicate_object then null; end $$;
revoke all on public.notification_outbox from public, anon, authenticated;
grant select on public.notification_outbox to authenticated;
grant all on public.notification_outbox to service_role;

-- the kinds worth an e-mail: business steps a person may be waiting for (not likes, follows or comments)
create or replace function public.notification_to_outbox() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.type in ('deal', 'payment', 'company_invite', 'company_join_request', 'company_join_answer', 'company_message', 'verification', 'cert_checked', 'cert_rejected',
                  'document_reviewed', 'review_reply', 'review_decided', 'report_decided', 'company_listing')
     and not exists (select 1 from public.notification_prefs p where p.user_id = new.user_id and not p.email) then
    insert into public.notification_outbox (notification_id, user_id, kind) values (new.id, new.user_id, new.type);
  end if;
  return null;
end $$;
revoke all on function public.notification_to_outbox() from public, anon, authenticated, service_role;
drop trigger if exists trg_notification_to_outbox on public.notifications;
create trigger trg_notification_to_outbox after insert on public.notifications for each row execute function public.notification_to_outbox();

-- what notify-dispatch sends (service role only): a batch of pending e-mails with the address, name and notice, claimed atomically —
-- a claimed row is 'sending' for 10 minutes, so two runs that overlap never send the same e-mail; one a crashed run left behind
-- is taken again after that
create or replace function public.outbox_claim(p_limit int default 50) returns table (id bigint, email text, name text, kind text, message text, data jsonb, company text)
language plpgsql security definer set search_path = public as $$
begin
  return query
  with c as (select o.id from public.notification_outbox o
               where (o.status = 'pending' or (o.status = 'sending' and o.claimed_at < now() - interval '10 minutes')) and o.attempts < 5
               order by o.created_at limit least(greatest(coalesce(p_limit, 50), 1), 200) for update skip locked),
  u as (update public.notification_outbox o set attempts = o.attempts + 1, status = 'sending', claimed_at = now() from c where o.id = c.id returning o.id, o.notification_id, o.user_id, o.kind)
  select u.id, au.email::text, p.name, u.kind, n.message, n.data, co.name
    from u join auth.users au on au.id = u.user_id join public.profiles p on p.id = u.user_id
    left join public.notifications n on n.id = u.notification_id left join public.companies co on co.id = n.company_id;
end $$;
revoke all on function public.outbox_claim(int) from public, anon, authenticated, service_role;
grant execute on function public.outbox_claim(int) to service_role;
create or replace function public.outbox_done(p_id bigint, p_ok boolean, p_error text default null) returns void language sql security definer set search_path = public as $$
  update public.notification_outbox set status = case when p_ok then 'sent' when attempts >= 5 then 'failed' else 'pending' end, claimed_at = null,
         sent_at = case when p_ok then now() end, last_error = case when p_ok then null else left(p_error, 500) end where id = p_id and status = 'sending'
$$;
revoke all on function public.outbox_done(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.outbox_done(bigint, boolean, text) to service_role;

notify pgrst, 'reload schema';
