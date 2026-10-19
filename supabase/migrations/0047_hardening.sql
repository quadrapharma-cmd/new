-- ═════════════════════════════════════════════════════════════════════
-- 0047 — hardening after the independent security check of the area social work (0040–0046)
--   1. a deleted account writes nothing: a token issued before the deletion (valid up to an hour) is refused like a suspension
--   2. a suspension stops changes too, not only new rows: posts, comments and the member's profile cannot be edited, and no
--      group or company can be created while suspended
--   3. deleting the account no longer undoes the record of a wrong password: account_delete_begin answers {error} instead of
--      raising (a raise rolled the attempt back, so the 5-wrong-in-15-minutes lock could be bypassed)
--   4. a block also covers replies to the blocker's comments; nobody can connect to, follow or mention a deleted member
--   5. profile photo / cover addresses: exactly <host>/storage/v1/object/public/avatars/<own id>/<file>.(jpg|jpeg|png|webp) —
--      no "..", no query, no other path in front
--   6. a digest chosen just now waits one period (it was sent at once)
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1 + 2. deleted or suspended members write nothing ────────────────────────────────────────────────────
create or replace function public.writer_not_suspended() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then return coalesce(new, old); end if;
  if exists (select 1 from public.profiles p where p.id = auth.uid() and p.account_type = 'deleted') then
    raise exception 'This account was deleted' using errcode = '42501';
  end if;
  if exists (select 1 from public.account_suspensions s where s.user_id = auth.uid()) then
    raise exception 'Your account is suspended' using errcode = '42501';
  end if;
  return coalesce(new, old);
end $$;
revoke all on function public.writer_not_suspended() from public, anon, authenticated, service_role;
grant execute on function public.writer_not_suspended() to service_role;
do $$ declare t text; begin
  -- new rows (as 0044, plus groups and companies)
  foreach t in array array['posts', 'comments', 'messages', 'reactions', 'reposts', 'comment_reactions', 'connections', 'person_followers', 'products', 'jobs',
                           'enquiries', 'skill_endorsements', 'post_mentions', 'member_reports', 'post_reports', 'message_reports', 'groups', 'companies',
                           'saved_searches', 'user_blocks'] loop
    if to_regclass('public.' || t) is not null then
      execute format('drop trigger if exists trg_%s_not_suspended on public.%I', t, t);
      execute format('create trigger trg_%s_not_suspended before insert on public.%I for each row execute function public.writer_not_suspended()', t, t);
    end if;
  end loop;
  -- changes to what they wrote, and to their profile
  foreach t in array array['posts', 'comments', 'products', 'jobs', 'enquiries', 'profiles'] loop
    if to_regclass('public.' || t) is not null then
      execute format('drop trigger if exists trg_%s_not_suspended_upd on public.%I', t, t);
      execute format('create trigger trg_%s_not_suspended_upd before update on public.%I for each row execute function public.writer_not_suspended()', t, t);
    end if;
  end loop;
end $$;

-- ── 3. the deletion check keeps its wrong-password record ────────────────────────────────────────────────
create or replace function public.account_delete_begin(p_password text, p_confirm text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); files jsonb;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if upper(trim(coalesce(p_confirm, ''))) not in ('DELETE', 'حذف') then raise exception 'Type DELETE to confirm' using errcode = '22023'; end if;
  -- no raise here: the wrong attempt check_password records must be committed, or the lock could be bypassed
  if not private.check_password(me, p_password) then return jsonb_build_object('error', 'Your password is not correct'); end if;
  insert into private.account_deletions (user_id) values (me) on conflict (user_id) do update set started_at = now();
  select coalesce(jsonb_agg(jsonb_build_object('bucket', o.bucket_id, 'name', o.name)), '[]'::jsonb) into files
    from storage.objects o
   where o.owner = me
      or (o.bucket_id = 'avatars' and o.name like me::text || '/%')
      or (o.bucket_id = 'videos' and o.name like 'people/' || me::text || '/%')
      or (o.bucket_id = 'post-media' and o.name like 'posts/' || me::text || '/%')
      or (o.bucket_id = 'message-media' and o.name like me::text || '/%')
      or (o.bucket_id = 'documents' and o.name like 'cv/' || me::text || '/%')
      or (o.bucket_id = 'reference-evidence' and o.name like me::text || '/%');
  return jsonb_build_object('user', me, 'files', files);
end $$;
revoke all on function public.account_delete_begin(text, text) from public, anon, authenticated, service_role;
grant execute on function public.account_delete_begin(text, text) to authenticated;

-- ── 4. blocks cover replies; a deleted member cannot be reached ──────────────────────────────────────────
create or replace function public.block_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare a uuid; b uuid; c uuid; r jsonb := to_jsonb(new);
begin
  case tg_table_name
    when 'connections' then a := (r->>'requester')::uuid; b := (r->>'addressee')::uuid;
    when 'person_followers' then a := (r->>'user_id')::uuid; b := (r->>'person_id')::uuid;
    when 'comments', 'reactions', 'reposts' then a := (r->>'user_id')::uuid; select p.user_id into b from public.posts p where p.id = (r->>'post_id')::bigint;
      if tg_table_name = 'comments' and r->>'parent_id' is not null then select x.user_id into c from public.comments x where x.id = (r->>'parent_id')::bigint; end if;
    when 'comment_reactions' then a := (r->>'user_id')::uuid; select x.user_id into b from public.comments x where x.id = (r->>'comment_id')::bigint;
    else return new;
  end case;
  if a <> b and private.blocked_between(a, b) then raise exception 'You can''t interact with this person' using errcode = '42501'; end if;
  if c is not null and a <> c and private.blocked_between(a, c) then raise exception 'You can''t interact with this person' using errcode = '42501'; end if;
  if tg_table_name in ('connections', 'person_followers') and exists (select 1 from public.profiles p where p.id = b and p.account_type = 'deleted') then
    raise exception 'This member deleted their account' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.block_guard() from public, anon, authenticated, service_role;
grant execute on function public.block_guard() to service_role;

-- ── 5. picture addresses: the member's own avatars file, nothing else ────────────────────────────────────
create or replace function public.profiles_pictures_guard() returns trigger language plpgsql as $$
declare re text := '^https?://[A-Za-z0-9.-]+(:[0-9]+)?/storage/v1/object/public/avatars/' || new.id::text || '/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp)$';
begin
  if public.is_server_call() then return new; end if;
  if new.avatar_url is distinct from (case when tg_op = 'UPDATE' then old.avatar_url end) and new.avatar_url is not null and new.avatar_url !~ re then
    raise exception 'The profile photo must be uploaded to Drugbox' using errcode = '22023';
  end if;
  if new.cover_url is distinct from (case when tg_op = 'UPDATE' then old.cover_url end) and new.cover_url is not null and new.cover_url !~ re then
    raise exception 'The cover image must be uploaded to Drugbox' using errcode = '22023';
  end if;
  return new;
end $$;
revoke all on function public.profiles_pictures_guard() from public, anon, authenticated, service_role;
grant execute on function public.profiles_pictures_guard() to authenticated, service_role;

-- ── 6. a digest starts one period after it is chosen ─────────────────────────────────────────────────────
create or replace function public.member_settings_digest_start() returns trigger language plpgsql as $$
begin
  if new.digest <> 'off' and (tg_op = 'INSERT' or old.digest is distinct from new.digest) then new.digest_sent_at := now(); end if;
  return new;
end $$;
revoke all on function public.member_settings_digest_start() from public, anon, authenticated, service_role;
grant execute on function public.member_settings_digest_start() to authenticated, service_role;
drop trigger if exists trg_member_settings_digest_start on public.member_settings;
create trigger trg_member_settings_digest_start before insert or update of digest on public.member_settings for each row execute function public.member_settings_digest_start();

notify pgrst, 'reload schema';
