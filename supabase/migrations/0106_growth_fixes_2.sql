-- ═════════════════════════════════════════════════════════════════════
-- 0106 · AREA w-growth — the third verifier round
--   1. a Drugbox post is removed only by a Drugbox admin, whatever the way (admin_delete_post and post_report_decide check
--      is_moderator(); the posts policy of 0100 says platform admins only) — one guard on the table
--   2. a report on a Drugbox channel post reaches Drugbox: official channels have no group admins, so the report goes to
--      Admin → Review (post_reports) — from the channel (group_post_reports) or from Saved (post_reports refused group posts)
--   3. a restored Drugbox post is linked again to its published plan (Admin → Channels)
--   4. Admin → Posts names a Drugbox post "Drugbox" (no member author since 0105) and finds it by that name
--   5. the dictionary: «العلاج الكيماوي» (with the article) is oncology again
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. only a Drugbox admin removes a Drugbox post ─────────────────────────────────────────────────────
create or replace function public.posts_drugbox_delete_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if old.as_drugbox and auth.uid() is not null and not public.is_platform_admin() then
    raise exception 'A Drugbox post is removed by a Drugbox admin only' using errcode = '42501';
  end if;
  return old;
end $$;
revoke all on function public.posts_drugbox_delete_guard() from public, anon, authenticated, service_role;
grant execute on function public.posts_drugbox_delete_guard() to authenticated, service_role;
drop trigger if exists trg_posts_drugbox_delete_guard on public.posts;
create trigger trg_posts_drugbox_delete_guard before delete on public.posts for each row when (old.as_drugbox) execute function public.posts_drugbox_delete_guard();

-- ── 2. reports on Drugbox posts go to Admin → Review ───────────────────────────────────────────────────
create or replace function public.post_reports_before_insert() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  select id, user_id, body, group_id, as_drugbox into p from public.posts where id = new.post_id;
  if p.id is null then raise exception 'This post is no longer available' using errcode = 'P0002'; end if;
  if p.group_id is not null and not p.as_drugbox then raise exception 'Report group posts to the group admins' using errcode = '42501'; end if;
  if p.user_id = new.reporter then raise exception 'You cannot report your own post' using errcode = '42501'; end if;
  new.post_author := p.user_id;
  new.post_excerpt := left(coalesce(p.body, ''), 600);
  new.status := 'open'; new.decided_by := null; new.decision_note := null; new.decided_at := null; new.created_at := now();
  return new;
end; $$;
revoke all on function public.post_reports_before_insert() from public, anon, authenticated, service_role;
grant execute on function public.post_reports_before_insert() to service_role;

-- a report made inside an official channel (the group's own report button) is passed to Drugbox's queue
create or replace function public.group_post_reports_to_drugbox() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.posts p where p.id = new.post_id and p.as_drugbox) then
    insert into public.post_reports (post_id, reporter, reason)
    values (new.post_id, new.reporter, case when new.reason in ('spam', 'counterfeit', 'misleading', 'abusive') then new.reason else 'other' end)
    on conflict (post_id, reporter) do nothing;
  end if;
  return null;
end $$;
revoke all on function public.group_post_reports_to_drugbox() from public, anon, authenticated, service_role;
grant execute on function public.group_post_reports_to_drugbox() to service_role;
drop trigger if exists trg_group_post_reports_to_drugbox on public.group_post_reports;
create trigger trg_group_post_reports_to_drugbox after insert on public.group_post_reports for each row execute function public.group_post_reports_to_drugbox();

-- ── 3. a restored Drugbox post finds its plan again ────────────────────────────────────────────────────
create or replace function public.posts_drugbox_relink() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update public.channel_schedule s set post_id = new.id
   where s.id = (select x.id from public.channel_schedule x
                  where x.post_id is null and x.status = 'published' and x.group_id = new.group_id and x.body = new.body
                  order by x.published_at desc nulls last limit 1);
  return null;
end $$;
revoke all on function public.posts_drugbox_relink() from public, anon, authenticated, service_role;
grant execute on function public.posts_drugbox_relink() to service_role;
drop trigger if exists trg_posts_drugbox_relink on public.posts;
create trigger trg_posts_drugbox_relink after insert on public.posts for each row when (new.as_drugbox) execute function public.posts_drugbox_relink();

-- ── 4. Admin → Posts: a Drugbox post reads "Drugbox" ──────────────────────────────────────────────────
create or replace function public.admin_posts(p_q text default null, p_limit int default 50, p_offset int default 0)
returns table (id bigint, user_id uuid, author text, body text, group_id bigint, like_count int, comment_count int, created_at timestamptz, total bigint)
language plpgsql stable security definer set search_path = public as $$
declare q text := lower(trim(coalesce(p_q, '')));
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  return query
    select p.id, p.user_id, case when p.as_drugbox then 'Drugbox' else a.name end, left(p.body, 500), p.group_id, coalesce(p.like_count, 0), coalesce(p.comment_count, 0), p.created_at, count(*) over ()
      from public.posts p left join public.profiles a on a.id = p.user_id
     where q = '' or lower(p.body || ' ' || case when p.as_drugbox then 'drugbox' else coalesce(a.name, '') end) like '%' || replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_') || '%'
     order by p.created_at desc
     limit least(greatest(coalesce(p_limit, 50), 1), 200) offset greatest(coalesce(p_offset, 0), 0);
end $$;
revoke all on function public.admin_posts(text, int, int) from public, anon, authenticated, service_role;
grant execute on function public.admin_posts(text, int, int) to authenticated, service_role;

-- ── 5. the dictionary ──────────────────────────────────────────────────────────────────────────────────
insert into private.thera_terms (tag, term) values ('oncology', 'العلاج الكيماوي') on conflict do nothing;
update public.posts set thera = (select coalesce(array_agg(distinct x order by x), '{}') from unnest(thera || private.thera_of(body)) x)
 where position('العلاج الكيماوي' in body) > 0 and not ('oncology' = any (thera));
update public.products set thera = private.thera_of(coalesce(name, '') || ' ' || coalesce(description, ''))
 where position('العلاج الكيماوي' in coalesce(name, '') || ' ' || coalesce(description, '')) > 0 and not ('oncology' = any (thera));

notify pgrst, 'reload schema';
