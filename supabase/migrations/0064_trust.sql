-- 0064 — AREA community: trust (J-COMMUNITY-30 … 33)
-- The person or company reviewed is told (an anonymous review stays anonymous: the notice has no sender); editing a review
-- tells nobody again. Deleting my own review, withdrawing my own reference and replying to / disputing one about me use the
-- policies and reply_to_reference() of 0001/0021 — supabase/tests/trust.rls.sql checks them together.
-- Re-run safe.

create or replace function public.job_reviews_told() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.hidden then return null; end if;
  insert into public.notifications (user_id, type, from_user, message)
  values (new.reviewee, 'review', case when new.anonymous then null else new.reviewer end,
          case when new.anonymous then 'A verified applicant reviewed your company on Drugbox Jobs'
               when new.reviewee_role = 'employer' then 'reviewed your company on Drugbox Jobs'
               else 'reviewed you on Drugbox Jobs' end);
  return null;
end $$;
revoke all on function public.job_reviews_told() from public, anon, authenticated, service_role;
grant execute on function public.job_reviews_told() to authenticated, service_role;
drop trigger if exists trg_job_reviews_told on public.job_reviews;
create trigger trg_job_reviews_told after insert on public.job_reviews for each row execute function public.job_reviews_told();

notify pgrst, 'reload schema';
