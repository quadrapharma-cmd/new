-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0010 — jobs in the live app (step D2a)
-- category (the jobs page filters by it), applicant count kept by the database, paging index.
-- ═════════════════════════════════════════════════════════════════════
alter table public.jobs add column if not exists category text not null default 'other';
do $$ begin
  alter table public.jobs add constraint jobs_category_chk check (category in ('regulatory','qaqc','production','sales','rd','other'));
exception when duplicate_object then null; end $$;
create index if not exists idx_jobs_live on public.jobs (active, created_at desc);
create index if not exists idx_job_apps_user on public.job_applications (user_id, created_at desc);

create or replace function public.jobs_applicant_count() returns trigger language plpgsql security definer set search_path = public as $$
begin
  update public.jobs set applicant_count = (select count(*) from public.job_applications where job_id = coalesce(new.job_id, old.job_id))
   where id = coalesce(new.job_id, old.job_id);
  return null;
end $$;
drop trigger if exists trg_jobs_applicant_count on public.job_applications;
create trigger trg_jobs_applicant_count after insert or delete on public.job_applications for each row execute function public.jobs_applicant_count();

notify pgrst, 'reload schema';
