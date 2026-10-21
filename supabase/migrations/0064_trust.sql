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
          case when new.anonymous then 'Your company got an anonymous review on Drugbox Jobs'
               when new.reviewee_role = 'employer' then 'reviewed your company on Drugbox Jobs'
               else 'reviewed you on Drugbox Jobs' end);
  return null;
end $$;
revoke all on function public.job_reviews_told() from public, anon, authenticated, service_role;
grant execute on function public.job_reviews_told() to authenticated, service_role;
drop trigger if exists trg_job_reviews_told on public.job_reviews;
create trigger trg_job_reviews_told after insert on public.job_reviews for each row execute function public.job_reviews_told();

-- a signed review made anonymous later: the earlier notice stops naming the reviewer
create or replace function public.job_reviews_told_anon() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.anonymous and not old.anonymous then
    update public.notifications set from_user = null, message = 'Your company got an anonymous review on Drugbox Jobs'
     where user_id = new.reviewee and type = 'review' and from_user = new.reviewer;
  end if;
  return null;
end $$;
revoke all on function public.job_reviews_told_anon() from public, anon, authenticated, service_role;
grant execute on function public.job_reviews_told_anon() to authenticated, service_role;
drop trigger if exists trg_job_reviews_told_anon on public.job_reviews;
create trigger trg_job_reviews_told_anon after update of anonymous on public.job_reviews for each row execute function public.job_reviews_told_anon();

notify pgrst, 'reload schema';
