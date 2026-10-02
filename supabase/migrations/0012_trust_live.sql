-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0012 — jobs trust layer in the live app (step D2b)
-- Reviews for many people in one call (anonymity respected, hidden reviews excluded), open-to-work candidates,
-- and the people I have really interacted with (who I may review).
-- ═════════════════════════════════════════════════════════════════════
create or replace function public.get_reviews_many(p_ids uuid[], p_role text)
returns table (reviewee uuid, id bigint, author text, anonymous boolean, c1 smallint, c2 smallint, c3 smallint, c4 smallint, body text, created_at timestamptz, mine boolean)
language sql stable security definer set search_path = public as $$
  select r.reviewee, r.id, case when r.anonymous then null else p.name end, r.anonymous, r.c1, r.c2, r.c3, r.c4, r.body, r.created_at, r.reviewer = auth.uid()
  from public.job_reviews r join public.profiles p on p.id = r.reviewer
  where r.reviewee = any(p_ids) and r.reviewee_role = p_role and not coalesce(r.hidden, false)
  order by r.created_at desc limit 2000
$$;
create or replace function public.open_candidates(p_limit int default 40)
returns setof public.profiles language sql stable security invoker set search_path = public as $$
  select * from public.profiles where open_to_work and id <> coalesce(auth.uid(), '00000000-0000-0000-0000-000000000000'::uuid)
  order by created_at desc limit least(greatest(coalesce(p_limit, 40), 1), 100)
$$;
create or replace function public.my_interactions() returns table (party uuid) language sql stable security definer set search_path = public as $$
  select j.user_id from public.job_applications a join public.jobs j on j.id = a.job_id where a.user_id = auth.uid()
  union select a.user_id from public.job_applications a join public.jobs j on j.id = a.job_id where j.user_id = auth.uid()
  union select case when m.sender_id = auth.uid() then m.receiver_id else m.sender_id end from public.messages m where auth.uid() in (m.sender_id, m.receiver_id)
$$;
create index if not exists idx_profiles_open_to_work on public.profiles (created_at desc) where open_to_work;
revoke all on function public.get_reviews_many(uuid[], text) from public;
grant execute on function public.get_reviews_many(uuid[], text) to anon, authenticated;
grant execute on function public.open_candidates(int) to authenticated;
revoke all on function public.my_interactions() from public, anon; grant execute on function public.my_interactions() to authenticated;

notify pgrst, 'reload schema';
