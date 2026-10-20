-- ═════════════════════════════════════════════════════════════════════
-- 0063 — Admin (A-01, A-03; J-COMMUNITY-41 … 50)
--   1. the decision log   admin_actions: every Drugbox decision (verification, claim, warning reference, site certificate, company
--                         report, InstaPay payment, reported post, suspension, role, profile badge, post removal) with who, when,
--                         the outcome and the note; read by Drugbox moderators (Admin → Review → Decided)
--   2. decide once        a decided item is never decided again by a second moderator ("Already decided by …"); admin_undo()
--                         reopens a decision where that is safe (never a payment, never a claim; a removed post comes back
--                         through admin_restore_post)
--   3. site certificates  checked or rejected with a note through cert_decide(); the company's owner and admins are told
--   4. company reports    the reporter is told the outcome; who decided and when is kept
--   5. accounts           account_suspensions (a suspended member cannot post, comment, message, connect, list or post jobs, and
--                         is told why); admin_suspend / admin_unsuspend / admin_set_role / admin_verify_profile; admin_users();
--                         admin_delete_post (the author is told; the post is kept in the log) / admin_restore_post; admin_posts()
-- Server-only work is SECURITY DEFINER and checks the caller is Drugbox. Every table, sequence and function grants its own
-- privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. the decision log ─────────────────────────────────────────────────────────────────────────────────
create table if not exists public.admin_actions (
  id         bigint generated always as identity primary key,
  actor      uuid references public.profiles(id) on delete set null,
  kind       text not null,
  item_id    text not null,
  label      text not null default '',
  decision   text not null,
  note       text,
  data       jsonb,
  undone_at  timestamptz,
  undone_by  uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint admin_actions_kind check (kind in ('verification', 'claim', 'reference', 'certificate', 'report', 'payment', 'post', 'suspension', 'role', 'badge')),
  constraint admin_actions_len check (length(label) <= 300 and length(coalesce(note, '')) <= 1000 and (data is null or pg_column_size(data) <= 65536))
);
create index if not exists idx_admin_actions_recent on public.admin_actions (created_at desc);
create index if not exists idx_admin_actions_item on public.admin_actions (kind, item_id);
create index if not exists idx_admin_actions_actor on public.admin_actions (actor);
create index if not exists idx_admin_actions_undone_by on public.admin_actions (undone_by);
alter table public.admin_actions enable row level security;
drop policy if exists "decisions: Drugbox reads" on public.admin_actions;
create policy "decisions: Drugbox reads" on public.admin_actions for select to authenticated using ((select public.is_moderator()));
revoke all on table public.admin_actions from public, anon, authenticated, service_role;
grant select on table public.admin_actions to anon, authenticated;              -- anon: no policy → empty (F-26); written by the server only
grant select, insert, update, delete, truncate, references, trigger on table public.admin_actions to service_role;
revoke all on sequence public.admin_actions_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.admin_actions_id_seq to service_role;

create or replace function private.log_decision(p_kind text, p_item text, p_label text, p_decision text, p_note text default null, p_data jsonb default null)
returns bigint language sql security definer set search_path = public as $$
  insert into public.admin_actions (actor, kind, item_id, label, decision, note, data) values (auth.uid(), p_kind, p_item, left(coalesce(p_label, ''), 300), p_decision, left(p_note, 1000), p_data)
  returning id
$$;
revoke all on function private.log_decision(text, text, text, text, text, jsonb) from public, anon, authenticated, service_role;
grant execute on function private.log_decision(text, text, text, text, text, jsonb) to service_role;
create or replace function private.who(p_user uuid) returns text language sql stable security definer set search_path = public as $$
  select coalesce((select nullif(trim(name), '') from public.profiles where id = p_user), 'another moderator')
$$;
revoke all on function private.who(uuid) from public, anon, authenticated, service_role;
grant execute on function private.who(uuid) to service_role;
-- admin_undo() sets this for its own transaction: a reopened item may be decided again
create or replace function private.undoing() returns boolean language sql stable as $$ select coalesce(current_setting('drugbox.undo', true), '') = '1' $$;
revoke all on function private.undoing() from public, anon, authenticated, service_role;
grant execute on function private.undoing() to authenticated, service_role;

-- ── 2. verification requests and claims: decided once, logged ───────────────────────────────────────────
create or replace function public.verification_requests_once() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status is distinct from old.status and old.status <> 'pending' and not private.undoing() then
    raise exception 'Already decided by % (%)', private.who(old.reviewed_by), old.status using errcode = 'DX409';
  end if;
  return new;
end $$;
revoke all on function public.verification_requests_once() from public, anon, authenticated, service_role;
grant execute on function public.verification_requests_once() to service_role;
drop trigger if exists trg_verification_requests_aa_once on public.verification_requests;   -- "aa": before the approval trigger
create trigger trg_verification_requests_aa_once before update on public.verification_requests for each row execute function public.verification_requests_once();

create or replace function public.verification_requests_log() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status is distinct from old.status and new.status in ('approved', 'rejected') and auth.uid() is not null then
    perform private.log_decision(case when new.claim then 'claim' else 'verification' end, new.id::text,
      coalesce((select name from public.companies where id = new.company_id), 'Company') || coalesce(' · registry ' || nullif(new.registry, ''), ''), new.status, new.note);
  end if;
  return null;
end $$;
revoke all on function public.verification_requests_log() from public, anon, authenticated, service_role;
grant execute on function public.verification_requests_log() to service_role;
drop trigger if exists trg_verification_requests_log on public.verification_requests;
create trigger trg_verification_requests_log after update on public.verification_requests for each row execute function public.verification_requests_log();

-- ── warning references: decided once, logged ───────────────────────────────────────────────────────────
create or replace function public.moderate_reference(ref_id bigint, new_status text) returns void
language plpgsql security definer set search_path = public as $$
declare r public.work_references;
begin
  if not public.is_moderator() then raise exception 'Moderators only' using errcode = '42501'; end if;
  if new_status not in ('published','rejected','pending') then raise exception 'Invalid status' using errcode = '22023'; end if;
  select * into r from public.work_references where id = ref_id for update;
  if r.id is null then raise exception 'Reference not found' using errcode = 'P0002'; end if;
  if r.status in ('published', 'rejected') and new_status <> r.status and not private.undoing() then
    raise exception 'Already decided by % (%)', private.who(r.decided_by), r.status using errcode = 'DX409';
  end if;
  if r.status = new_status then return; end if;
  update public.work_references set status = new_status,
         decided_by = case when new_status in ('published','rejected') then auth.uid() else null end,
         decided_at = case when new_status in ('published','rejected') then now() else null end
   where id = ref_id;
  if new_status in ('published', 'rejected') then
    perform private.log_decision('reference', ref_id::text, coalesce((select name from public.profiles where id = r.author), 'Employer') || ' → ' || coalesce((select name from public.profiles where id = r.candidate), 'candidate')
                                 || coalesce(' · ' || r.category, ''), new_status);
  end if;
end $$;
revoke all on function public.moderate_reference(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.moderate_reference(bigint, text) to authenticated, service_role;

-- ── 3. site certificates: checked or rejected (with a note) once; the company is told ─────────────────────
alter table public.site_certificates add column if not exists checked_by  uuid references public.profiles(id) on delete set null;
alter table public.site_certificates add column if not exists rejected_at timestamptz;
alter table public.site_certificates add column if not exists reject_note text;
create index if not exists idx_site_certificates_checked_by on public.site_certificates (checked_by);
do $$ begin
  alter table public.site_certificates add constraint site_certificates_reject_len check (length(coalesce(reject_note, '')) <= 500);
exception when duplicate_object then null; end $$;
-- 0011's guard let only Drugbox admins set checked_at; moderators check certificates too (through cert_decide)
create or replace function public.site_certificates_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if auth.uid() is null or public.is_moderator() then return new; end if;
  if new.source = 'public_list' then new.source := 'company'; end if;
  if tg_op = 'INSERT' then new.checked_at := null;
  elsif new.name is distinct from old.name or new.expiry is distinct from old.expiry or new.checked_at is distinct from old.checked_at then new.checked_at := null; end if;
  return new;
end $$;
revoke all on function public.site_certificates_guard() from public, anon, authenticated, service_role;
grant execute on function public.site_certificates_guard() to authenticated, service_role;
-- the company changes the certificate (a new scan, a new expiry): it is checked again from scratch
create or replace function public.site_certificates_recheck() returns trigger language plpgsql set search_path = public as $$
begin
  if auth.uid() is null or public.is_moderator() then return new; end if;
  new.checked_by := null; new.rejected_at := null; new.reject_note := null;
  return new;
end $$;
revoke all on function public.site_certificates_recheck() from public, anon, authenticated, service_role;
grant execute on function public.site_certificates_recheck() to service_role;
drop trigger if exists trg_site_certificates_recheck on public.site_certificates;
create trigger trg_site_certificates_recheck before insert or update on public.site_certificates for each row execute function public.site_certificates_recheck();

create or replace function public.cert_decide(p_id bigint, p_ok boolean, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare c public.site_certificates; cname text; msg text;
begin
  if not public.is_moderator() then raise exception 'Only the Drugbox team checks certificates' using errcode = '42501'; end if;
  if p_ok is null then raise exception 'Check or reject' using errcode = '22023'; end if;
  select * into c from public.site_certificates where id = p_id for update;
  if c.id is null then raise exception 'This certificate is no longer available' using errcode = 'P0002'; end if;
  if (c.checked_at is not null or c.rejected_at is not null) and not private.undoing() then
    raise exception 'Already decided by % (%)', private.who(c.checked_by), case when c.checked_at is not null then 'checked' else 'rejected' end using errcode = 'DX409';
  end if;
  if not p_ok and length(trim(coalesce(p_note, ''))) < 3 then raise exception 'Say why the certificate is rejected — the company sees it' using errcode = '22023'; end if;
  update public.site_certificates set checked_at = case when p_ok then now() end, checked_by = auth.uid(),
         rejected_at = case when p_ok then null else now() end, reject_note = case when p_ok then null else left(trim(p_note), 500) end
   where id = p_id;
  select name into cname from public.companies where id = c.company_id;
  msg := case when p_ok then 'checked your certificate "' || left(c.name, 120) || '" — it shows as verified on ' || coalesce(cname, 'your company page')
              else 'could not accept your certificate "' || left(c.name, 120) || '": ' || left(trim(p_note), 300) end;
  insert into public.notifications (user_id, type, from_user, company_id, message)
  select distinct m.uid, 'certificate_review', auth.uid(), c.company_id, msg
    from (select owner_id as uid from public.companies where id = c.company_id
          union select user_id from public.company_members where company_id = c.company_id and role in ('owner', 'admin') and accepted) m
   where m.uid is not null;
  perform private.log_decision('certificate', p_id::text, coalesce(cname, 'Company') || ' · ' || c.name, case when p_ok then 'checked' else 'rejected' end, p_note);
  return case when p_ok then 'checked' else 'rejected' end;
end $$;
revoke all on function public.cert_decide(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.cert_decide(bigint, boolean, text) to authenticated, service_role;

-- ── 4. company reports: decided once; the reporter is told ──────────────────────────────────────────────
alter table public.company_reports add column if not exists decided_by uuid references public.profiles(id) on delete set null;
alter table public.company_reports add column if not exists decided_at timestamptz;
create index if not exists idx_company_reports_decided_by on public.company_reports (decided_by);
create or replace function public.company_reports_decided() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status is distinct from old.status then
    if old.status <> 'open' and new.status <> 'open' and not private.undoing() then
      raise exception 'Already decided by % (%)', private.who(old.decided_by), old.status using errcode = 'DX409';
    end if;
    if new.status = 'open' then new.decided_by := null; new.decided_at := null;
    elsif auth.uid() is not null then new.decided_by := auth.uid(); new.decided_at := now(); end if;
  end if;
  return new;
end $$;
revoke all on function public.company_reports_decided() from public, anon, authenticated, service_role;
grant execute on function public.company_reports_decided() to service_role;
drop trigger if exists trg_company_reports_zz_decided on public.company_reports;   -- after company_reports_guard (which maps 'fixed')
create trigger trg_company_reports_zz_decided before update on public.company_reports for each row execute function public.company_reports_decided();
create or replace function public.company_reports_told() returns trigger language plpgsql security definer set search_path = public as $$
declare cname text;
begin
  if new.status is distinct from old.status and new.status in ('resolved', 'dismissed') then
    select name into cname from public.companies where id = new.company_id;
    if new.reporter is not null then
      insert into public.notifications (user_id, type, from_user, company_id, message)
      values (new.reporter, 'report_closed', null, new.company_id,
              case when new.status = 'resolved' then 'Thank you — your report about ' || coalesce(cname, 'a company page') || ' was checked and the page is corrected'
                   else 'Your report about ' || coalesce(cname, 'a company page') || ' was checked — the page stays as it is' end);
    end if;
    if auth.uid() is not null then
      perform private.log_decision('report', new.id::text, coalesce(cname, 'Company') || ' · ' || coalesce(new.section, '') || ' · ' || left(coalesce(new.issue, ''), 120), new.status);
    end if;
  end if;
  return null;
end $$;
revoke all on function public.company_reports_told() from public, anon, authenticated, service_role;
grant execute on function public.company_reports_told() to service_role;
drop trigger if exists trg_company_reports_told on public.company_reports;
create trigger trg_company_reports_told after update on public.company_reports for each row execute function public.company_reports_told();

-- ── InstaPay payments and reported posts: logged ───────────────────────────────────────────────────────
create or replace function public.payment_orders_log() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if old.status = 'review' and new.status in ('paid', 'failed') and auth.uid() is not null then
    perform private.log_decision('payment', new.id::text, new.merchant_ref || ' · ' || coalesce((select name from public.profiles where id = new.user_id), 'Member') || ' · EGP '
                                 || to_char(new.amount_cents / 100.0, 'FM999,999,990.00') || coalesce(' · transfer ' || new.transfer_ref, ''), new.status);
  end if;
  return null;
end $$;
revoke all on function public.payment_orders_log() from public, anon, authenticated, service_role;
grant execute on function public.payment_orders_log() to service_role;
drop trigger if exists trg_payment_orders_log on public.payment_orders;
create trigger trg_payment_orders_log after update on public.payment_orders for each row execute function public.payment_orders_log();

create or replace function public.post_reports_log() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if old.status = 'open' and new.status <> 'open' and auth.uid() is not null
     and not exists (select 1 from public.admin_actions a where a.kind = 'post' and a.item_id = coalesce(new.post_id, 0)::text and a.created_at > now() - interval '5 seconds') then
    perform private.log_decision('post', coalesce(new.post_id, 0)::text, coalesce((select name from public.profiles where id = new.post_author), 'Member') || ' · ' || left(coalesce(new.post_excerpt, ''), 120),
                                 new.status, new.decision_note);
  end if;
  return null;
end $$;
revoke all on function public.post_reports_log() from public, anon, authenticated, service_role;
grant execute on function public.post_reports_log() to service_role;
drop trigger if exists trg_post_reports_log on public.post_reports;
create trigger trg_post_reports_log after update on public.post_reports for each row execute function public.post_reports_log();

-- ── 5. accounts: suspension, role, the profile badge ──────────────────────────────────────────────────
create table if not exists public.account_suspensions (
  user_id    uuid primary key references public.profiles(id) on delete cascade,
  reason     text not null,
  by_user    uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint account_suspensions_reason check (length(trim(reason)) between 3 and 500)
);
create index if not exists idx_account_suspensions_by on public.account_suspensions (by_user);
alter table public.account_suspensions enable row level security;
drop policy if exists "suspensions: the member and Drugbox read" on public.account_suspensions;
create policy "suspensions: the member and Drugbox read" on public.account_suspensions for select to authenticated
  using (user_id = (select auth.uid()) or (select public.is_moderator()));
revoke all on table public.account_suspensions from public, anon, authenticated, service_role;
grant select on table public.account_suspensions to anon, authenticated;        -- anon: empty (F-26); written by admin_suspend() only
grant select, insert, update, delete, truncate, references, trigger on table public.account_suspensions to service_role;

create or replace function private.not_suspended() returns boolean language sql stable security definer set search_path = public as $$
  select not exists (select 1 from public.account_suspensions s where s.user_id = auth.uid())
$$;
revoke all on function private.not_suspended() from public, anon, authenticated, service_role;
grant execute on function private.not_suspended() to anon, authenticated, service_role;
do $$ declare t text; begin
  foreach t in array array['posts', 'comments', 'messages', 'connections', 'products', 'jobs'] loop
    execute format('drop policy if exists "a suspended account does not write" on public.%I', t);
    execute format('create policy "a suspended account does not write" on public.%I as restrictive for insert to authenticated with check ((select private.not_suspended()))', t);
  end loop;
end $$;

create or replace function public.admin_suspend(p_user uuid, p_reason text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin suspends accounts' using errcode = '42501'; end if;
  if p_user = auth.uid() then raise exception 'You cannot suspend your own account' using errcode = '22023'; end if;
  if exists (select 1 from public.profiles where id = p_user and role = 'admin') then raise exception 'An admin account cannot be suspended — change its role first' using errcode = '22023'; end if;
  if length(trim(coalesce(p_reason, ''))) < 3 then raise exception 'Give the reason — the member sees it' using errcode = '22023'; end if;
  if exists (select 1 from public.account_suspensions where user_id = p_user) then raise exception 'This account is already suspended' using errcode = 'DX409'; end if;
  insert into public.account_suspensions (user_id, reason, by_user) values (p_user, left(trim(p_reason), 500), auth.uid());
  perform private.log_decision('suspension', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), 'suspended', p_reason);
end $$;
revoke all on function public.admin_suspend(uuid, text) from public, anon, authenticated, service_role;
grant execute on function public.admin_suspend(uuid, text) to authenticated, service_role;

create or replace function public.admin_unsuspend(p_user uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin restores accounts' using errcode = '42501'; end if;
  delete from public.account_suspensions where user_id = p_user;
  if not found then raise exception 'This account is not suspended' using errcode = 'P0002'; end if;
  insert into public.notifications (user_id, type, message) values (p_user, 'account', 'Your Drugbox account is active again');
  perform private.log_decision('suspension', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), 'restored');
end $$;
revoke all on function public.admin_unsuspend(uuid) from public, anon, authenticated, service_role;
grant execute on function public.admin_unsuspend(uuid) to authenticated, service_role;

create or replace function public.admin_set_role(p_user uuid, p_role text) returns void
language plpgsql security definer set search_path = public as $$
declare old_role text;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin changes roles' using errcode = '42501'; end if;
  if p_role not in ('user', 'moderator', 'admin') then raise exception 'Unknown role' using errcode = '22023'; end if;
  if p_user = auth.uid() and p_role <> 'admin' then raise exception 'You cannot take away your own admin role' using errcode = '22023'; end if;
  select role into old_role from public.profiles where id = p_user; if old_role is null then raise exception 'Member not found' using errcode = 'P0002'; end if;
  if old_role = p_role then return; end if;
  update public.profiles set role = p_role where id = p_user;
  perform private.log_decision('role', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), p_role, null, jsonb_build_object('from', old_role));
end $$;
revoke all on function public.admin_set_role(uuid, text) from public, anon, authenticated, service_role;
grant execute on function public.admin_set_role(uuid, text) to authenticated, service_role;

create or replace function public.admin_verify_profile(p_user uuid, p_on boolean) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin gives the profile badge' using errcode = '42501'; end if;
  update public.profiles set verified = coalesce(p_on, false) where id = p_user;
  if not found then raise exception 'Member not found' using errcode = 'P0002'; end if;
  if p_on then insert into public.notifications (user_id, type, message) values (p_user, 'account', 'Drugbox verified your profile ✓'); end if;
  perform private.log_decision('badge', p_user::text, coalesce((select name from public.profiles where id = p_user), 'Member'), case when p_on then 'verified' else 'unverified' end);
end $$;
revoke all on function public.admin_verify_profile(uuid, boolean) from public, anon, authenticated, service_role;
grant execute on function public.admin_verify_profile(uuid, boolean) to authenticated, service_role;

-- Admin → Users: search, a page at a time, with the account's state (moderators read; admins act)
create or replace function public.admin_users(p_q text default null, p_limit int default 50, p_offset int default 0)
returns table (id uuid, name text, headline text, company text, role text, verified boolean, created_at timestamptz, suspended boolean, suspended_reason text, posts bigint, total bigint)
language plpgsql stable security definer set search_path = public as $$
declare q text := lower(trim(coalesce(p_q, '')));
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  return query
    with m as (select p.* from public.profiles p
                where q = '' or lower(coalesce(p.name, '') || ' ' || coalesce(p.headline, '') || ' ' || coalesce(p.company, '')) like '%' || replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_') || '%')
    select m.id, m.name, m.headline, m.company, m.role, m.verified, m.created_at, s.user_id is not null, s.reason,
           (select count(*) from public.posts x where x.user_id = m.id), count(*) over ()
      from m left join public.account_suspensions s on s.user_id = m.id
     order by m.created_at desc
     limit least(greatest(coalesce(p_limit, 50), 1), 200) offset greatest(coalesce(p_offset, 0), 0);
end $$;
revoke all on function public.admin_users(text, int, int) from public, anon, authenticated, service_role;
grant execute on function public.admin_users(text, int, int) to authenticated, service_role;

-- Admin → Posts: the newest posts with their author, a page at a time, searchable
create or replace function public.admin_posts(p_q text default null, p_limit int default 50, p_offset int default 0)
returns table (id bigint, user_id uuid, author text, body text, group_id bigint, like_count int, comment_count int, created_at timestamptz, total bigint)
language plpgsql stable security definer set search_path = public as $$
declare q text := lower(trim(coalesce(p_q, '')));
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  return query
    select p.id, p.user_id, a.name, left(p.body, 500), p.group_id, coalesce(p.like_count, 0), coalesce(p.comment_count, 0), p.created_at, count(*) over ()
      from public.posts p left join public.profiles a on a.id = p.user_id
     where q = '' or lower(p.body || ' ' || coalesce(a.name, '')) like '%' || replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_') || '%'
     order by p.created_at desc
     limit least(greatest(coalesce(p_limit, 50), 1), 200) offset greatest(coalesce(p_offset, 0), 0);
end $$;
revoke all on function public.admin_posts(text, int, int) from public, anon, authenticated, service_role;
grant execute on function public.admin_posts(text, int, int) to authenticated, service_role;

-- a post Drugbox removes: the author is told why; the post (with its pictures and files) is kept in the log, so it can be restored
create or replace function public.admin_delete_post(p_post bigint, p_reason text) returns bigint
language plpgsql security definer set search_path = public as $$
declare p public.posts; snap jsonb; aid bigint;
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  if length(trim(coalesce(p_reason, ''))) < 3 then raise exception 'Give the reason — the author sees it' using errcode = '22023'; end if;
  select * into p from public.posts where id = p_post;
  if p.id is null then raise exception 'This post is already gone' using errcode = 'P0002'; end if;
  snap := jsonb_build_object('post', to_jsonb(p), 'media', coalesce((select jsonb_agg(to_jsonb(m)) from public.post_media m where m.post_id = p.id), '[]'::jsonb));
  aid := private.log_decision('post', p.id::text, coalesce((select name from public.profiles where id = p.user_id), 'Member') || ' · ' || left(p.body, 120), 'removed', p_reason, snap);
  delete from public.posts where id = p.id;
  insert into public.notifications (user_id, type, message, data)
  values (p.user_id, 'post_removed', 'Drugbox removed your post: ' || left(trim(p_reason), 300), jsonb_build_object('excerpt', left(p.body, 80)));
  return aid;
end $$;
revoke all on function public.admin_delete_post(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.admin_delete_post(bigint, text) to authenticated, service_role;

create or replace function public.admin_restore_post(p_action bigint) returns bigint
language plpgsql security definer set search_path = public as $$
declare a public.admin_actions; p jsonb;
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  select * into a from public.admin_actions where id = p_action for update;
  if a.id is null or a.kind <> 'post' or a.decision <> 'removed' or a.data is null then raise exception 'There is no removed post to restore here' using errcode = 'P0002'; end if;
  if a.undone_at is not null then raise exception 'Already restored by %', private.who(a.undone_by) using errcode = 'DX409'; end if;
  p := a.data -> 'post';
  if not exists (select 1 from public.profiles where id = (p ->> 'user_id')::uuid) then raise exception 'The author''s account no longer exists' using errcode = 'P0002'; end if;
  if (p ->> 'group_id') is not null and not exists (select 1 from public.groups where id = (p ->> 'group_id')::bigint) then raise exception 'The post''s group no longer exists' using errcode = 'P0002'; end if;
  insert into public.posts (id, user_id, body, category, group_id, created_at)
  values ((p ->> 'id')::bigint, (p ->> 'user_id')::uuid, p ->> 'body', p ->> 'category', (p ->> 'group_id')::bigint, (p ->> 'created_at')::timestamptz)
  on conflict (id) do nothing;
  insert into public.post_media (post_id, url, type, name, size)
  select (m ->> 'post_id')::bigint, m ->> 'url', m ->> 'type', m ->> 'name', (m ->> 'size')::bigint from jsonb_array_elements(coalesce(a.data -> 'media', '[]'::jsonb)) m;
  update public.admin_actions set undone_at = now(), undone_by = auth.uid() where id = a.id;
  insert into public.notifications (user_id, type, message) values ((p ->> 'user_id')::uuid, 'post_restored', 'Drugbox restored your post — its likes and comments could not be brought back');
  return (p ->> 'id')::bigint;
end $$;
revoke all on function public.admin_restore_post(bigint) from public, anon, authenticated, service_role;
grant execute on function public.admin_restore_post(bigint) to authenticated, service_role;

-- ── undo: a decision reopened where that is safe ───────────────────────────────────────────────────────
create or replace function public.admin_undo(p_action bigint) returns text
language plpgsql security definer set search_path = public as $$
declare a public.admin_actions; n int;
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  select * into a from public.admin_actions where id = p_action for update;
  if a.id is null then raise exception 'Decision not found' using errcode = 'P0002'; end if;
  if a.undone_at is not null then raise exception 'Already undone by %', private.who(a.undone_by) using errcode = 'DX409'; end if;
  if a.kind in ('payment', 'claim') then raise exception 'A % decision cannot be undone here', a.kind using errcode = '22023'; end if;
  if a.kind = 'post' then
    if a.decision = 'removed' then return 'restore'; end if;             -- the interface calls admin_restore_post
    update public.post_reports set status = 'open', decided_by = null, decided_at = null, decision_note = null where post_id = a.item_id::bigint and status = a.decision;
    get diagnostics n = row_count;
  elsif a.kind = 'suspension' then
    if a.decision = 'suspended' then delete from public.account_suspensions where user_id = a.item_id::uuid; get diagnostics n = row_count;
    else raise exception 'Suspend the account again from Users' using errcode = '22023'; end if;
  elsif a.kind = 'role' then
    if not public.is_platform_admin() then raise exception 'Only a Drugbox admin changes roles' using errcode = '42501'; end if;
    update public.profiles set role = coalesce(a.data ->> 'from', 'user') where id = a.item_id::uuid; get diagnostics n = row_count;
  elsif a.kind = 'badge' then
    if not public.is_platform_admin() then raise exception 'Only a Drugbox admin gives the profile badge' using errcode = '42501'; end if;
    update public.profiles set verified = (a.decision <> 'verified') where id = a.item_id::uuid; get diagnostics n = row_count;
  else
    perform set_config('drugbox.undo', '1', true);
    if a.kind = 'verification' then
      if a.decision = 'approved' then
        if not public.is_platform_admin() then raise exception 'Only a Drugbox admin takes a verification back' using errcode = '42501'; end if;
        update public.companies set status = 'pending' where id = (select company_id from public.verification_requests where id = a.item_id::bigint) and status = 'verified';
      end if;
      update public.verification_requests set status = 'pending', reviewed_by = null, reviewed_at = null, note = null where id = a.item_id::bigint; get diagnostics n = row_count;
      insert into public.notifications (user_id, type, message) select submitted_by, 'verification', 'Your verification request is being reviewed again' from public.verification_requests where id = a.item_id::bigint;
    elsif a.kind = 'reference' then
      perform public.moderate_reference(a.item_id::bigint, 'pending'); n := 1;
    elsif a.kind = 'certificate' then
      update public.site_certificates set checked_at = null, checked_by = null, rejected_at = null, reject_note = null where id = a.item_id::bigint; get diagnostics n = row_count;
    elsif a.kind = 'report' then
      update public.company_reports set status = 'open' where id = a.item_id::bigint; get diagnostics n = row_count;
    end if;
    perform set_config('drugbox.undo', '', true);
  end if;
  if n = 0 then raise exception 'The item is no longer there' using errcode = 'P0002'; end if;
  update public.admin_actions set undone_at = now(), undone_by = auth.uid() where id = a.id;
  return 'reopened';
end $$;
revoke all on function public.admin_undo(bigint) from public, anon, authenticated, service_role;
grant execute on function public.admin_undo(bigint) to authenticated, service_role;

notify pgrst, 'reload schema';
