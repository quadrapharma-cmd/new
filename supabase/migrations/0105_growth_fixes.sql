-- ═════════════════════════════════════════════════════════════════════
-- 0105 · AREA w-growth — the second verifier round on 0100–0104
--   1. a Drugbox channel post has NO member as its author (posts.user_id null, as_drugbox): it survives any admin's account
--      being deleted (0040 removes a member's rows through the cascading keys) and no API embed of the author can name the admin
--      who published it; who published is kept for Drugbox in channel_schedule.published_by. A notice to nobody is dropped.
--      Removing / restoring a channel post (0063) keeps it Drugbox's, with its therapeutic tags, and tells no admin about "their" post.
--   2. a signed-out visitor's company page shows the company's real verification (a registry on file as «•••», never its number:
--      the page works out its level from it, 0103 made a verified company read "Not verified")
--   3. the therapeutic dictionary: «ماشية» alone matched «الأمور ماشية» ("things are going fine")
--   4. Ask an expert: a session past its end is not "upcoming" (expert_sessions_list.ended); the expert member is what the admin
--      sets on each save (null removes them); the expert gets the link only until the end and answers only visible questions,
--      until a week after the end
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. Drugbox posts belong to no member ───────────────────────────────────────────────────────────────
alter table public.channel_schedule add column if not exists published_by uuid references public.profiles(id) on delete set null;
create index if not exists idx_channel_schedule_published_by on public.channel_schedule (published_by) where published_by is not null;
update public.channel_schedule s set published_by = p.user_id from public.posts p where p.id = s.post_id and s.published_by is null and p.user_id is not null;

alter table public.posts alter column user_id drop not null;
do $$ begin
  if not exists (select 1 from pg_constraint where conrelid = 'public.posts'::regclass and conname = 'posts_author_or_drugbox') then
    alter table public.posts add constraint posts_author_or_drugbox check (user_id is not null or as_drugbox) not valid;
  end if;
end $$;
update public.posts set user_id = null where as_drugbox and user_id is not null;   -- the server (is_server_call): as_drugbox stays
alter table public.posts validate constraint posts_author_or_drugbox;

-- a notice addressed to nobody (a Drugbox post's "author") is not an error: it is dropped
create or replace function public.notifications_nobody() returns trigger
language plpgsql set search_path = public as $$
begin
  return null;
end $$;
revoke all on function public.notifications_nobody() from public, anon, authenticated, service_role;
grant execute on function public.notifications_nobody() to service_role;
drop trigger if exists trg_notifications_a_nobody on public.notifications;
create trigger trg_notifications_a_nobody before insert on public.notifications for each row when (new.user_id is null) execute function public.notifications_nobody();

create or replace function private.channel_publish(p_id bigint) returns bigint
language plpgsql security definer set search_path = public as $$
declare r public.channel_schedule; pid bigint; who uuid; g public.groups;
begin
  select * into r from public.channel_schedule where id = p_id for update skip locked;
  if not found or r.status not in ('draft', 'scheduled') then return null; end if;
  select * into g from public.groups where id = r.group_id;
  if g.id is null or not g.official or g.archived_at is not null then
    update public.channel_schedule set status = 'failed', error = 'the channel is closed', updated_at = now() where id = p_id;
    return null;
  end if;
  -- Drugbox's record of who did it (the post itself names nobody): who pressed "Publish now", else who last changed it, else who wrote it
  who := coalesce(case when public.is_platform_admin() then auth.uid() end, r.updated_by, r.created_by);
  insert into public.posts (user_id, body, category, group_id, as_drugbox, thera)
  values (null, r.body, case g.channel_key when 'regulatory' then 'regulatory' when 'market' then 'market' when 'jobs' then 'job' else 'general' end,
          r.group_id, true, r.thera)
  returning id into pid;
  update public.channel_schedule set status = 'published', post_id = pid, published_at = now(), published_by = who, updated_at = now(), error = null where id = p_id;
  return pid;
end $$;
revoke all on function private.channel_publish(bigint) from public, anon, authenticated, service_role;
grant execute on function private.channel_publish(bigint) to service_role;

-- the members of a channel are told of a new post (0100: "<> new.user_id" was null for an authorless post — nobody was told)
create or replace function public.notify_group_post() returns trigger
language plpgsql security definer set search_path = public as $$
declare gname text; frm uuid := case when new.as_drugbox then null else new.user_id end;
        extra jsonb := case when new.as_drugbox then jsonb_build_object('drugbox', true) else '{}'::jsonb end;
begin
  if new.group_id is null then return null; end if;
  select name into gname from public.groups where id = new.group_id;
  insert into public.notifications (user_id, type, from_user, group_id, post_id, message, data)
  select m.user_id, 'group_post', frm, new.group_id, new.id, 'posted in "' || left(coalesce(gname, ''), 120) || '"', jsonb_build_object('n', 1) || extra
    from public.group_members m
   where m.group_id = new.group_id and m.user_id is distinct from new.user_id and not m.muted
  on conflict (user_id, group_id) where type = 'group_post' and read = false
  do update set from_user = excluded.from_user, post_id = excluded.post_id, created_at = now(),
                data = jsonb_build_object('n', coalesce((public.notifications.data ->> 'n')::int, 1) + 1) || extra,
                message = (coalesce((public.notifications.data ->> 'n')::int, 1) + 1)::text || ' new posts in "' || left(coalesce(gname, ''), 120) || '"';
  return null;
end $$;
revoke all on function public.notify_group_post() from public, anon, authenticated, service_role;
grant execute on function public.notify_group_post() to service_role;

-- 0063's removal, with a Drugbox post logged as Drugbox's and its author told only when it has one
create or replace function public.admin_delete_post(p_post bigint, p_reason text) returns bigint
language plpgsql security definer set search_path = public as $$
declare p public.posts; snap jsonb; aid bigint;
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  if length(trim(coalesce(p_reason, ''))) < 3 then raise exception 'Give the reason — the author sees it' using errcode = '22023'; end if;
  select * into p from public.posts where id = p_post;
  if p.id is null then raise exception 'This post is already gone' using errcode = 'P0002'; end if;
  snap := jsonb_build_object('post', to_jsonb(p), 'media', coalesce((select jsonb_agg(to_jsonb(m)) from public.post_media m where m.post_id = p.id), '[]'::jsonb));
  aid := private.log_decision('post', p.id::text, case when p.as_drugbox then 'Drugbox' else coalesce((select name from public.profiles where id = p.user_id), 'Member') end || ' · ' || left(p.body, 120), 'removed', p_reason, snap);
  with done as (update public.post_reports set status = 'removed', decided_by = auth.uid(), decided_at = now(), decision_note = left(trim(p_reason), 500)
                 where post_id = p.id and status = 'open' returning reporter)
  insert into public.notifications (user_id, type, from_user, message)
  select distinct reporter, 'report_closed', null::uuid, 'Drugbox reviewed your report and removed the post.' from done;
  delete from public.posts where id = p.id;
  if p.user_id is not null and not p.as_drugbox then
    insert into public.notifications (user_id, type, message, data)
    values (p.user_id, 'post_removed', 'Drugbox removed your post: ' || left(trim(p_reason), 300), jsonb_build_object('excerpt', left(p.body, 80), 'note', left(trim(p_reason), 300)));
  end if;
  return aid;
end $$;
revoke all on function public.admin_delete_post(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.admin_delete_post(bigint, text) to authenticated, service_role;

-- 0063's restore, bringing back a Drugbox post as Drugbox's (no author) with the tags it had
create or replace function public.admin_restore_post(p_action bigint) returns bigint
language plpgsql security definer set search_path = public as $$
declare a public.admin_actions; p jsonb; dbx boolean;
begin
  if not public.is_moderator() then raise exception 'Drugbox team only' using errcode = '42501'; end if;
  select * into a from public.admin_actions where id = p_action for update;
  if a.id is null or a.kind <> 'post' or a.decision <> 'removed' or a.data is null then raise exception 'There is no removed post to restore here' using errcode = 'P0002'; end if;
  if a.undone_at is not null then raise exception 'Already restored by %', private.who(a.undone_by) using errcode = 'DX409'; end if;
  p := a.data -> 'post';
  dbx := coalesce((p ->> 'as_drugbox')::boolean, false);
  if not dbx and not exists (select 1 from public.profiles where id = (p ->> 'user_id')::uuid) then raise exception 'The author''s account no longer exists' using errcode = 'P0002'; end if;
  if (p ->> 'group_id') is not null and not exists (select 1 from public.groups where id = (p ->> 'group_id')::bigint) then raise exception 'The post''s group no longer exists' using errcode = 'P0002'; end if;
  insert into public.posts (id, user_id, body, category, group_id, created_at, as_drugbox, thera)
  values ((p ->> 'id')::bigint, case when dbx then null else (p ->> 'user_id')::uuid end, p ->> 'body', p ->> 'category', (p ->> 'group_id')::bigint, (p ->> 'created_at')::timestamptz,
          dbx, coalesce((select array_agg(x) from jsonb_array_elements_text(case when jsonb_typeof(p -> 'thera') = 'array' then p -> 'thera' else '[]'::jsonb end) x), '{}'))
  on conflict (id) do nothing;
  update public.admin_actions set undone_at = now(), undone_by = auth.uid() where id = a.id;
  if not dbx then
    insert into public.notifications (user_id, type, message) values ((p ->> 'user_id')::uuid, 'post_restored', 'Drugbox restored your post — its likes, comments and attached files could not be brought back');
  end if;
  return (p ->> 'id')::bigint;
end $$;
revoke all on function public.admin_restore_post(bigint) from public, anon, authenticated, service_role;
grant execute on function public.admin_restore_post(bigint) to authenticated, service_role;

-- ── 2. a visitor sees the company's verification: a registry on file (•••), never its number ─────────────
create or replace function private.public_company_strip(c jsonb) returns jsonb language sql immutable as $$
  select (c - array['phone', 'email', 'whatsapp', 'registry', 'hours', 'owner_id', 'source_ref', 'vip_until', 'vip_reminded_at', 'mine', 'tax_verified',
                    'location', 'website', 'profile', 'source'])
         || jsonb_build_object('mine', false, 'profile', jsonb_strip_nulls(jsonb_build_object('services', c -> 'profile' -> 'services')))   -- what it offers, never its address
         || case when length(trim(coalesce(c ->> 'registry', ''))) > 0
                 then jsonb_build_object('registry', '•••')
                 else '{}'::jsonb end
$$;
revoke all on function private.public_company_strip(jsonb) from public, anon, authenticated, service_role;
grant execute on function private.public_company_strip(jsonb) to service_role;

-- the Regulatory channel's Arabic description in the interface's register (it is shown now: the Arabic interface reads name_ar / description_ar)
update public.groups set description_ar = 'قناة Drugbox الرسمية: النشرة التنظيمية الأسبوعية (هيئة الدواء، هيئة سلامة الغذاء) وكيفية قراءة إعلان ملف تسجيل.'
 where official and channel_key = 'regulatory' and description_ar like '%وإزاي تقرا%';

-- ── 3. the dictionary ──────────────────────────────────────────────────────────────────────────────────
delete from private.thera_terms where (tag, term) in (('veterinary', 'ماشية'));
insert into private.thera_terms (tag, term) values ('veterinary', 'الماشية'), ('veterinary', 'للماشية') on conflict do nothing;
update public.posts set thera = (select coalesce(array_agg(distinct x order by x), '{}') from unnest(private.thera_of(body)) x)
 where 'veterinary' = any (thera) and not as_drugbox and position('ماشية' in body) > 0;
update public.products set thera = private.thera_of(coalesce(name, '') || ' ' || coalesce(description, ''))
 where 'veterinary' = any (thera) and position('ماشية' in coalesce(name, '') || ' ' || coalesce(description, '')) > 0;

-- ── 4. Ask an expert ───────────────────────────────────────────────────────────────────────────────────
create or replace function public.expert_session_save(p_id bigint, p_topic text, p_title text, p_title_ar text, p_about text, p_expert_name text,
                                                       p_expert_line text, p_local text, p_minutes int, p_seats int, p_join_url text, p_expert_user uuid default null)
returns bigint language plpgsql security definer set search_path = public as $$
declare at timestamptz; old public.expert_sessions; nid bigint; tname text;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin schedules expert sessions' using errcode = '42501'; end if;
  if not exists (select 1 from public.expert_topics where key = p_topic) then raise exception 'Pick a topic' using errcode = '22023'; end if;
  if length(trim(coalesce(p_title, ''))) < 3 then raise exception 'Give the session a title' using errcode = '22023'; end if;
  if length(trim(coalesce(p_expert_name, ''))) < 2 then raise exception 'Name the expert' using errcode = '22023'; end if;
  if nullif(trim(coalesce(p_join_url, '')), '') is not null and (length(trim(p_join_url)) > 400 or trim(p_join_url) !~* '^https://[^\s<>"]{4,}$') then raise exception 'The meeting link must start with https://' using errcode = '22023'; end if;
  begin at := (to_timestamp(trim(coalesce(p_local, '')), 'YYYY-MM-DD HH24:MI')::timestamp at time zone 'Africa/Cairo');
  exception when others then raise exception 'Give the date and time as YYYY-MM-DD HH:MM (Cairo time)' using errcode = '22023'; end;
  if at is null then raise exception 'Give the date and time as YYYY-MM-DD HH:MM (Cairo time)' using errcode = '22023'; end if;
  if p_expert_user is not null and not exists (select 1 from public.profiles where id = p_expert_user and account_type <> 'deleted') then raise exception 'That member is not on Drugbox' using errcode = '22023'; end if;
  if p_id is null then
    if at <= now() then raise exception 'Pick a time in the future' using errcode = '22023'; end if;
    insert into public.expert_sessions (topic, title, title_ar, about, expert_name, expert_line, expert_user, starts_at, minutes, seats, join_url, created_by)
    values (p_topic, trim(p_title), nullif(trim(coalesce(p_title_ar, '')), ''), nullif(trim(coalesce(p_about, '')), ''), trim(p_expert_name), nullif(trim(coalesce(p_expert_line, '')), ''),
            p_expert_user, at, coalesce(p_minutes, 60), coalesce(p_seats, 100), nullif(trim(coalesce(p_join_url, '')), ''), auth.uid())
    returning id into nid;
    select title_en into tname from public.expert_topics where key = p_topic;
    insert into public.notifications (user_id, type, message, data)
    select r.user_id, 'expert_session', 'An expert session you asked for: "' || left(trim(p_title), 120) || '"', jsonb_build_object('session', nid, 'topic', p_topic)
      from public.expert_requests r where r.topic = p_topic;
    return nid;
  end if;
  select * into old from public.expert_sessions where id = p_id for update;
  if not found then raise exception 'This session is gone' using errcode = 'P0002'; end if;
  if old.status <> 'scheduled' then raise exception 'This session is %', old.status using errcode = '55000'; end if;
  if at is distinct from old.starts_at and at <= now() then raise exception 'Pick a time in the future' using errcode = '22023'; end if;
  if p_seats is not null and p_seats < old.registered_count then raise exception '% members are already registered — the seats cannot be fewer', old.registered_count using errcode = '23514'; end if;
  -- the expert member is what this save says (null: none) — a member once named is not kept for good
  update public.expert_sessions set topic = p_topic, title = trim(p_title), title_ar = nullif(trim(coalesce(p_title_ar, '')), ''), about = nullif(trim(coalesce(p_about, '')), ''),
         expert_name = trim(p_expert_name), expert_line = nullif(trim(coalesce(p_expert_line, '')), ''), expert_user = p_expert_user,
         starts_at = at, minutes = coalesce(p_minutes, minutes), seats = coalesce(p_seats, seats), join_url = nullif(trim(coalesce(p_join_url, '')), ''), updated_at = now()
   where id = p_id;
  if at is distinct from old.starts_at then
    update public.expert_registrations set reminded_day = false, reminded_hour = false where session_id = p_id;
    insert into public.notifications (user_id, type, message, data)
    select g.user_id, 'expert_session', 'The expert session "' || left(trim(p_title), 120) || '" moved to a new time', jsonb_build_object('session', p_id, 'moved', true)
      from public.expert_registrations g where g.session_id = p_id;
  end if;
  return p_id;
end $$;
revoke all on function public.expert_session_save(bigint, text, text, text, text, text, text, text, int, int, text, uuid) from public, anon, authenticated, service_role;
grant execute on function public.expert_session_save(bigint, text, text, text, text, text, text, text, int, int, text, uuid) to authenticated, service_role;

create or replace function public.expert_session_link(p_id bigint) returns text
language plpgsql stable security definer set search_path = public as $$
declare s public.expert_sessions; me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into s from public.expert_sessions where id = p_id;
  if not found then raise exception 'This session is gone' using errcode = 'P0002'; end if;
  if public.is_platform_admin() then return s.join_url; end if;
  if not coalesce(s.expert_user = me, false) and not exists (select 1 from public.expert_registrations g where g.session_id = p_id and g.user_id = me) then
    raise exception 'Register for the session to get its link' using errcode = '42501'; end if;
  if s.status <> 'scheduled' then raise exception 'This session is %', s.status using errcode = '55000'; end if;
  if now() > s.starts_at + make_interval(mins => s.minutes) then raise exception 'This session has ended — its questions and answers stay here' using errcode = '55000'; end if;
  if not coalesce(s.expert_user = me, false) and now() < s.starts_at - interval '1 hour' then raise exception 'The link opens an hour before the session' using errcode = '55000'; end if;
  return s.join_url;
end $$;
revoke all on function public.expert_session_link(bigint) from public, anon, authenticated, service_role;
grant execute on function public.expert_session_link(bigint) to authenticated, service_role;

create or replace function public.expert_answer(p_question bigint, p_answer text) returns void
language plpgsql security definer set search_path = public as $$
declare q public.expert_questions; s public.expert_sessions; a text := nullif(trim(coalesce(p_answer, '')), '');
begin
  select * into q from public.expert_questions where id = p_question for update;
  if not found then raise exception 'This question is gone' using errcode = 'P0002'; end if;
  select * into s from public.expert_sessions where id = q.session_id;
  if not public.is_platform_admin() then
    if not coalesce(s.expert_user = auth.uid(), false) then raise exception 'Only Drugbox or the session''s expert answers' using errcode = '42501'; end if;
    -- the expert answers the questions members can see, until a week after the session (Drugbox: always)
    if q.hidden then raise exception 'This question was hidden by Drugbox' using errcode = '42501'; end if;
    if s.status = 'cancelled' or now() > s.starts_at + make_interval(mins => s.minutes) + interval '7 days' then
      raise exception 'Answers to this session are closed — Drugbox can still answer' using errcode = '55000'; end if;
  end if;
  if a is null then raise exception 'Write the answer' using errcode = '22023'; end if;
  if length(a) > 4000 then raise exception 'An answer is at most 4,000 characters' using errcode = '22023'; end if;
  update public.expert_questions set answer = a, answered_by = auth.uid(), answered_at = now() where id = p_question;
  if q.user_id <> auth.uid() then
    insert into public.notifications (user_id, type, message, data)
    values (q.user_id, 'expert_answer', 'Your question in "' || left(s.title, 120) || '" was answered', jsonb_build_object('session', s.id, 'question', q.id));
  end if;
end $$;
revoke all on function public.expert_answer(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.expert_answer(bigint, text) to authenticated, service_role;

-- the Training page: "ended" — a session past its end is not upcoming even when nobody marked it done
drop function if exists public.expert_sessions_list(int);   -- its row shape changed while unreleased: replaced, not altered
create or replace function public.expert_sessions_list(p_limit int default 30)
returns table (id bigint, topic text, title text, title_ar text, about text, expert_name text, expert_line text, starts_at timestamptz, starts_local text,
               minutes int, seats int, registered_count int, status text, registered boolean, questions int, has_link boolean, started boolean, ended boolean)
language sql stable security definer set search_path = public as $$
  select s.id, s.topic, s.title, s.title_ar, s.about, s.expert_name, s.expert_line, s.starts_at, to_char(s.starts_at at time zone 'Africa/Cairo', 'YYYY-MM-DD HH24:MI'),
         s.minutes, s.seats, s.registered_count, s.status,
         exists (select 1 from public.expert_registrations g where g.session_id = s.id and g.user_id = auth.uid()),
         (select count(*)::int from public.expert_questions q where q.session_id = s.id and (not q.hidden or q.user_id = auth.uid())),
         s.join_url is not null, s.starts_at <= now(), s.starts_at + make_interval(mins => s.minutes) <= now()
    from public.expert_sessions s
   where auth.uid() is not null and (s.status <> 'cancelled' or s.starts_at > now() - interval '7 days')
   order by (s.status = 'scheduled' and s.starts_at + make_interval(mins => s.minutes) > now()) desc,
            case when s.status = 'scheduled' and s.starts_at + make_interval(mins => s.minutes) > now() then s.starts_at end asc,
            s.starts_at desc
   limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;
revoke all on function public.expert_sessions_list(int) from public, anon, authenticated, service_role;
grant execute on function public.expert_sessions_list(int) to authenticated, service_role;

notify pgrst, 'reload schema';
