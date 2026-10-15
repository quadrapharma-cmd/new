-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0030 — network follow-ups (product gaps S-04, S-10, S-11, J-SOCIAL-29…34)
-- 1. person_followers: follow a person without connecting (S-11), like company_followers. One counter on
--    profiles.followers_count, a "started following you" notice (once per pair).
--    followers_count(x) = people connected with x + people who follow x without being connected (no double count:
--    the connections counter and the follow counter each skip the pair the other already counts).
-- 2. people_dismissed: "People you may know" suggestions a member hid stay hidden (J-SOCIAL-34).
-- 3. suggest_people: leaves out dismissed people; colleagues (same company) come right after mutual connections.
-- 4. connections: the sender of a request that was declined cannot delete the declined row and ask again at once
--    (no repeat requests); the person who declined it still can (and asking them back clears it, 0020).
-- Re-runnable; every new object is granted explicitly (0026).
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. following a person ────────────────────────────────────────────────────────────────────
create table if not exists public.person_followers (
  person_id  uuid not null references public.profiles(id) on delete cascade,   -- the person followed
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,   -- the follower
  created_at timestamptz not null default now(),
  primary key (person_id, user_id),
  constraint person_followers_not_self check (person_id <> user_id)
);
create index if not exists idx_person_followers_user on public.person_followers (user_id);
alter table public.person_followers enable row level security;
drop policy if exists "person followers: you and the person followed see the follow" on public.person_followers;
create policy "person followers: you and the person followed see the follow" on public.person_followers for select to authenticated
  using (user_id = (select auth.uid()) or person_id = (select auth.uid()));
drop policy if exists "person followers: follow as yourself" on public.person_followers;
create policy "person followers: follow as yourself" on public.person_followers for insert to authenticated
  with check (user_id = (select auth.uid()));
drop policy if exists "person followers: unfollow yourself" on public.person_followers;
create policy "person followers: unfollow yourself" on public.person_followers for delete to authenticated
  using (user_id = (select auth.uid()));
revoke all on table public.person_followers from public, anon, authenticated, service_role;
grant select on table public.person_followers to anon;                    -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.person_followers to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.person_followers to service_role;

-- a follow from someone already connected is not counted again (the connection already counts them)
create or replace function public.person_followers_count() returns trigger language plpgsql security definer set search_path = public as $$
declare f uuid := coalesce(new.user_id, old.user_id); p uuid := coalesce(new.person_id, old.person_id);
        linked boolean;
begin
  linked := exists (select 1 from public.connections c where c.status = 'accepted'
                     and ((c.requester = f and c.addressee = p) or (c.requester = p and c.addressee = f)));
  if tg_op = 'INSERT' then
    if not linked then update public.profiles set followers_count = followers_count + 1 where id = p; end if;
    insert into public.notifications (user_id, type, from_user, message) values (p, 'follow', f, 'started following you') on conflict do nothing;
  elsif tg_op = 'DELETE' then
    if not linked then update public.profiles set followers_count = greatest(followers_count - 1, 0) where id = p; end if;
  end if;
  return null;
end $$;
revoke all on function public.person_followers_count() from public, anon, authenticated, service_role;
grant execute on function public.person_followers_count() to service_role;
drop trigger if exists trg_person_followers_count on public.person_followers;
create trigger trg_person_followers_count after insert or delete on public.person_followers for each row execute function public.person_followers_count();
-- one "started following you" notice per pair: following again after an unfollow does not notify again
create unique index if not exists idx_notifs_follow_once on public.notifications (user_id, from_user) where type = 'follow';

-- the connections counter (0020): a side that already follows the other is counted by the follow, not again by the connection
create or replace function public.profiles_followers_count() returns trigger language plpgsql security definer set search_path = public as $$
declare was boolean := tg_op <> 'INSERT' and old.status = 'accepted';
        now_on boolean := tg_op <> 'DELETE' and new.status = 'accepted';
        r uuid := coalesce(new.requester, old.requester); a uuid := coalesce(new.addressee, old.addressee);
        d int;
begin
  if now_on = was then return null; end if;
  d := case when now_on then 1 else -1 end;
  update public.profiles set followers_count = greatest(followers_count + d, 0)
   where (id = r and not exists (select 1 from public.person_followers f where f.person_id = r and f.user_id = a))
      or (id = a and not exists (select 1 from public.person_followers f where f.person_id = a and f.user_id = r));
  return null;
end $$;
revoke all on function public.profiles_followers_count() from public, anon, authenticated, service_role;
grant execute on function public.profiles_followers_count() to service_role;

-- recount every member (people connected with them ∪ people following them)
update public.profiles p set followers_count = coalesce(n.k, 0)
  from public.profiles q left join (
    select x.pid, count(distinct x.other) as k from (
      select requester as pid, addressee as other from public.connections where status = 'accepted'
      union all select addressee, requester from public.connections where status = 'accepted'
      union all select person_id, user_id from public.person_followers) x group by x.pid) n on n.pid = q.id
 where q.id = p.id and p.followers_count is distinct from coalesce(n.k, 0);

-- ── 2. suggestions a member dismissed ───────────────────────────────────────────────────────
create table if not exists public.people_dismissed (
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  person_id  uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, person_id)
);
create index if not exists idx_people_dismissed_person on public.people_dismissed (person_id);   -- the foreign key's own index (F-44)
alter table public.people_dismissed enable row level security;
drop policy if exists "dismissed people: your own" on public.people_dismissed;
create policy "dismissed people: your own" on public.people_dismissed for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "dismissed people: dismiss as yourself" on public.people_dismissed;
create policy "dismissed people: dismiss as yourself" on public.people_dismissed for insert to authenticated with check (user_id = (select auth.uid()));
drop policy if exists "dismissed people: undo your own" on public.people_dismissed;
create policy "dismissed people: undo your own" on public.people_dismissed for delete to authenticated using (user_id = (select auth.uid()));
revoke all on table public.people_dismissed from public, anon, authenticated, service_role;
grant select on table public.people_dismissed to anon;                    -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.people_dismissed to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.people_dismissed to service_role;

-- ── 3. suggest_people: mutual connections, then colleagues, then the newest members; never someone dismissed ──
create index if not exists idx_profiles_company_key on public.profiles (lower(btrim(company)));
create or replace function public.suggest_people(p_limit int default 12)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean, mutual int)
language sql stable security definer set search_path = public as $$
  with me as (select auth.uid() as uid),
  lim as (select least(greatest(coalesce(p_limit, 12), 1), 50) as n),
  mine as (select nullif(lower(btrim(p.company)), '') as co from public.profiles p, me where p.id = me.uid),
  friends as materialized (select case when c.requester = me.uid then c.addressee else c.requester end as fid
              from public.connections c, me where c.status = 'accepted' and (c.requester = me.uid or c.addressee = me.uid)
              order by c.created_at desc nulls last limit 300),
  known as materialized (select case when c.requester = me.uid then c.addressee else c.requester end as pid
            from public.connections c, me where c.requester = me.uid or c.addressee = me.uid
            union all select d.person_id from public.people_dismissed d, me where d.user_id = me.uid),
  second as (select x.pid, count(*)::int as mutual
             from friends f cross join lateral (
               (select c.addressee as pid from public.connections c where c.requester = f.fid and c.status = 'accepted' limit 200)
               union all
               (select c.requester from public.connections c where c.addressee = f.fid and c.status = 'accepted' limit 200)) x
             group by x.pid),
  ranked as (select s.pid, s.mutual from second s, me where s.pid <> me.uid and s.pid not in (select pid from known)
             order by s.mutual desc limit (select n from lim)),
  colleagues as (select p.id as pid, 0 as mutual from public.profiles p, me, mine
                  where mine.co is not null and lower(btrim(p.company)) = mine.co and p.id <> me.uid and p.id not in (select pid from known)
                  order by p.created_at desc limit (select n from lim)),
  fill as (select p.id as pid, 0 as mutual from public.profiles p, me where p.id <> me.uid
             and p.id not in (select pid from known) and p.id not in (select pid from ranked)
           order by p.created_at desc limit (select n from lim)),
  picked as materialized (select u.pid, max(u.mutual) as mutual from (select * from ranked union all select * from colleagues union all select * from fill) u group by u.pid)
  select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring, x.mutual
  from picked x join public.profiles p on p.id = x.pid
  where auth.uid() is not null and p.id = any(array(select pid from picked))
  order by x.mutual desc, (lower(btrim(p.company)) is not distinct from (select co from mine) and (select co from mine) is not null) desc, p.created_at desc
  limit (select n from lim)
$$;
revoke all on function public.suggest_people(p_limit integer) from public, anon, authenticated, service_role;
grant execute on function public.suggest_people(p_limit integer) to authenticated, service_role;

-- ── 4. a declined request stays declined for its sender ─────────────────────────────────────
alter policy "connections: parties delete" on public.connections
  using ((select auth.uid()) = addressee or ((select auth.uid()) = requester and status <> 'rejected'));

notify pgrst, 'reload schema';
