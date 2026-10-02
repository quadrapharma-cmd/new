-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0017 — moderation (step E2)
-- Company reports ("wrong information"), and notifications when Drugbox decides on a verification request
-- or publishes a warning (the person gets their right of reply).
-- ═════════════════════════════════════════════════════════════════════
create table if not exists public.company_reports (
  id         bigint generated always as identity primary key,
  company_id bigint not null references public.companies(id) on delete cascade,
  reporter   uuid   not null references public.profiles(id) on delete cascade,
  section    text   not null check (section in ('About','Products','Sites','Certificates','Contact')),
  issue      text   not null check (length(trim(issue)) between 3 and 1000),
  correction text   check (correction is null or length(correction) <= 1000),
  status     text   not null default 'open' check (status in ('open','resolved','dismissed')),
  created_at timestamptz not null default now()
);
create index if not exists idx_company_reports_open on public.company_reports (status, created_at desc);
alter table public.company_reports enable row level security;
do $$ begin
  create policy "reports: file as yourself" on public.company_reports for insert with check (reporter = (select auth.uid()) and status = 'open');
  create policy "reports: reporter, the company and Drugbox read" on public.company_reports for select
    using (reporter = (select auth.uid()) or public.is_company_member(company_id, array['owner','admin']) or public.is_platform_admin());
  create policy "reports: the company or Drugbox close" on public.company_reports for update
    using (public.is_company_member(company_id, array['owner','admin']) or public.is_platform_admin())
    with check (public.is_company_member(company_id, array['owner','admin']) or public.is_platform_admin());
exception when duplicate_object then null; end $$;

create or replace function public.verification_decided_notify() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> old.status and new.status in ('approved','rejected') then
    insert into public.notifications (user_id, type, from_user, message)
    values (new.submitted_by, 'verification', auth.uid(),
            case when new.status = 'approved' then 'Your company is verified ✓' else 'Verification needs another look: ' || coalesce(new.note, 'please check your documents') end);
  end if;
  return null;
end $$;
drop trigger if exists trg_verification_decided_notify on public.verification_requests;
create trigger trg_verification_decided_notify after update of status on public.verification_requests for each row execute function public.verification_decided_notify();

create or replace function public.reference_published_notify() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> old.status and new.status = 'published' and new.kind = 'warn' then
    insert into public.notifications (user_id, type, from_user, message)
    values (new.candidate, 'reference', new.author, 'A work reference about you was published — you can reply to it');
  end if;
  return null;
end $$;
drop trigger if exists trg_reference_published_notify on public.work_references;
create trigger trg_reference_published_notify after update of status on public.work_references for each row execute function public.reference_published_notify();

notify pgrst, 'reload schema';
