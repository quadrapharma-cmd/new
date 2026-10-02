-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0003 — network (step B3)
-- suggest_people: second-degree people ranked by mutual connections, then newest members.
--   Bounded work: reads only my friends' connections + the newest profiles by index (never the whole table).
-- my_network_stats: real numbers for the network sidebar.
-- ═════════════════════════════════════════════════════════════════════
create index if not exists idx_profiles_created on public.profiles (created_at desc);
create index if not exists idx_conn_requester_status on public.connections (requester, status);
create index if not exists idx_conn_addressee_status on public.connections (addressee, status);

create or replace function public.suggest_people(p_limit int default 12)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean, mutual int)
language sql stable security definer set search_path = public as $$
  with me as (select auth.uid() as uid),
  lim as (select least(greatest(coalesce(p_limit, 12), 1), 50) as n),
  friends as (select case when c.requester = me.uid then c.addressee else c.requester end as fid
              from public.connections c, me where c.status = 'accepted' and (c.requester = me.uid or c.addressee = me.uid)),
  known as (select case when c.requester = me.uid then c.addressee else c.requester end as pid
            from public.connections c, me where c.requester = me.uid or c.addressee = me.uid),
  second as (select case when c.requester = f.fid then c.addressee else c.requester end as pid, count(*)::int as mutual
             from public.connections c join friends f on f.fid in (c.requester, c.addressee) where c.status = 'accepted'
             group by 1),
  ranked as (select s.pid, s.mutual from second s, me where s.pid <> me.uid and s.pid not in (select pid from known)
             order by s.mutual desc limit (select n from lim)),
  fill as (select p.id as pid, 0 as mutual from public.profiles p, me where p.id <> me.uid
             and p.id not in (select pid from known) and p.id not in (select pid from ranked)
           order by p.created_at desc limit (select n from lim))
  select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring, x.mutual
  from (select * from ranked union all select * from fill) x join public.profiles p on p.id = x.pid
  where auth.uid() is not null
  order by x.mutual desc, p.created_at desc
  limit (select n from lim)
$$;

create or replace function public.my_network_stats() returns json language sql stable security invoker set search_path = public as $$
  select json_build_object(
    'connections',   (select count(*) from public.connections where status = 'accepted' and auth.uid() in (requester, addressee)),
    'profile_views', (select coalesce(profile_views, 0) from public.profiles where id = auth.uid()),
    'impressions',   (select coalesce(sum(view_count), 0) from public.posts where user_id = auth.uid()))
$$;

revoke all on function public.suggest_people(int) from public, anon;
grant execute on function public.suggest_people(int) to authenticated;
revoke all on function public.my_network_stats() from public, anon;
grant execute on function public.my_network_stats() to authenticated;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
