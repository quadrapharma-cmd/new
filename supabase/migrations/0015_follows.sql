-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0015 — company followers
-- Found by a sweep of every table: company_followers had row-level security ON and NO policy,
-- so nobody could follow a company. Policies; one follower counter (the original +1/−1 trigger).
-- ═════════════════════════════════════════════════════════════════════
do $$ begin
  create policy "followers: you see your own follows" on public.company_followers for select using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "followers: follow as yourself" on public.company_followers for insert with check (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "followers: unfollow yourself" on public.company_followers for delete using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin alter table public.company_followers add constraint company_followers_pk primary key (company_id, user_id); exception when others then null; end $$;
-- the follower count is kept by the original trigger (trg_follower_count, +1/−1). No second counter.
drop trigger if exists trg_company_follower_count on public.company_followers;
drop function if exists public.company_follower_count();
-- 0010 added a second applicant counter next to the original one (trg_applicant_count). Keep one.
drop trigger if exists trg_jobs_applicant_count on public.job_applications;
drop function if exists public.jobs_applicant_count();

notify pgrst, 'reload schema';
