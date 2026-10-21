-- ═════════════════════════════════════════════════════════════════════
-- 0040 — account (area social: X-01 Settings, delete my account, download my data; S-05/S-06 password checks)
--   1. member_settings      one row per member: which notifications also come by e-mail, the e-mail summary, privacy choices
--                           (show my name on profile visits, phone to connections), the e-mail language, the Terms version
--                           accepted at sign-up; created with the profile, read and changed only by its member
--   2. verify_my_password   the signed-in member's password is checked by the database (Settings → Change password and
--                           Delete account ask for it); at most 5 wrong tries in 15 minutes
--   3. account deletion     account_delete_begin (the member: password + the word DELETE) → the account-delete Edge Function
--                           removes the member's files through the Storage API → account_anonymise (server only): every row
--                           that belongs to the member is deleted (or loses the reference), the profile becomes a tombstone
--                           "Deleted member" (account_type 'deleted', hidden from everyone), messages stay with the other
--                           person, payment orders stay for the tax records (buyer name kept in private.billing_archive)
--   4. export_my_data       everything about the signed-in member as one JSON document (Settings → Download my data)
-- No column is added to public.profiles: functions that return setof profiles list its columns (0036). Every table and
-- function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. member_settings ───────────────────────────────────────────────────────────────────────────────────
create table if not exists public.member_settings (
  user_id           uuid primary key default auth.uid() references public.profiles(id) on delete cascade,
  email_messages    boolean not null default true,
  email_connections boolean not null default true,
  email_comments    boolean not null default true,
  email_mentions    boolean not null default true,
  email_reactions   boolean not null default false,
  email_follows     boolean not null default false,
  email_jobs        boolean not null default true,
  digest            text not null default 'off',
  show_visits       boolean not null default true,
  phone_connections boolean not null default false,
  lang              text not null default 'en',
  terms_version     text,
  terms_accepted_at timestamptz,
  unsub_token       uuid not null default gen_random_uuid(),
  updated_at        timestamptz not null default now(),
  constraint member_settings_digest_chk check (digest in ('off', 'daily', 'weekly')),
  constraint member_settings_lang_chk check (lang in ('en', 'ar')),
  constraint member_settings_terms_len check (length(terms_version) <= 40)
);
create unique index if not exists idx_member_settings_unsub on public.member_settings (unsub_token);
alter table public.member_settings enable row level security;
do $$ begin
  create policy "settings: own read" on public.member_settings for select using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "settings: own add" on public.member_settings for insert with check (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "settings: own change" on public.member_settings for update using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.member_settings from public, anon, authenticated, service_role;
grant select on table public.member_settings to anon;                          -- no policy for anon → an empty answer (F-26)
grant select on table public.member_settings to authenticated;
-- what a member may write: the choices (the token, the Terms record and the timestamps are the server's)
grant insert (user_id, email_messages, email_connections, email_comments, email_mentions, email_reactions, email_follows, email_jobs, digest, show_visits, phone_connections, lang)
  on table public.member_settings to authenticated;
grant update (email_messages, email_connections, email_comments, email_mentions, email_reactions, email_follows, email_jobs, digest, show_visits, phone_connections, lang)
  on table public.member_settings to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.member_settings to service_role;

create or replace function public.member_settings_touch() returns trigger language plpgsql as $$
begin new.updated_at := now(); if tg_op = 'UPDATE' then new.user_id := old.user_id; new.unsub_token := old.unsub_token; new.terms_version := old.terms_version; new.terms_accepted_at := old.terms_accepted_at; end if; return new; end $$;
revoke all on function public.member_settings_touch() from public, anon, authenticated, service_role;
grant execute on function public.member_settings_touch() to authenticated, service_role;
drop trigger if exists trg_member_settings_touch on public.member_settings;
create trigger trg_member_settings_touch before insert or update on public.member_settings for each row execute function public.member_settings_touch();

-- a new profile gets its settings row, with the Terms version the sign-up form agreed to (sent as user metadata "terms")
create or replace function public.member_settings_for_new_profile() returns trigger
language plpgsql security definer set search_path = public as $$
declare t text;
begin
  select left(nullif(trim(u.raw_user_meta_data->>'terms'), ''), 40) into t from auth.users u where u.id = new.id;
  insert into public.member_settings (user_id, terms_version, terms_accepted_at)
  values (new.id, t, case when t is null then null else now() end) on conflict (user_id) do nothing;
  return new;
end $$;
revoke all on function public.member_settings_for_new_profile() from public, anon, authenticated, service_role;
grant execute on function public.member_settings_for_new_profile() to service_role;
drop trigger if exists trg_profiles_settings on public.profiles;
create trigger trg_profiles_settings after insert on public.profiles for each row execute function public.member_settings_for_new_profile();
insert into public.member_settings (user_id) select p.id from public.profiles p on conflict (user_id) do nothing;   -- the members who already exist

-- ── 2. verify_my_password ────────────────────────────────────────────────────────────────────────────────
create schema if not exists private;
create table if not exists private.password_attempts (user_id uuid not null, at timestamptz not null default now());
create index if not exists idx_password_attempts on private.password_attempts (user_id, at);
revoke all on table private.password_attempts from public, anon, authenticated;

create or replace function private.check_password(p_user uuid, p_password text) returns boolean
language plpgsql security definer set search_path = public, extensions as $$
declare ok boolean;
begin
  if p_user is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  delete from private.password_attempts where at < now() - interval '1 day';
  if (select count(*) from private.password_attempts a where a.user_id = p_user and a.at > now() - interval '15 minutes') >= 5 then
    raise exception 'Too many wrong passwords — wait 15 minutes and try again' using errcode = 'P0001';
  end if;
  select u.encrypted_password is not null and u.encrypted_password = extensions.crypt(coalesce(p_password, ''), u.encrypted_password) into ok
    from auth.users u where u.id = p_user;
  if not coalesce(ok, false) then insert into private.password_attempts (user_id) values (p_user); return false; end if;
  return true;
end $$;
revoke all on function private.check_password(uuid, text) from public, anon, authenticated, service_role;

create or replace function public.verify_my_password(p_password text) returns boolean
language sql security definer set search_path = public as $$ select private.check_password(auth.uid(), p_password) $$;
revoke all on function public.verify_my_password(text) from public, anon, authenticated, service_role;
grant execute on function public.verify_my_password(text) to authenticated;

-- ── 3. account deletion ──────────────────────────────────────────────────────────────────────────────────
-- a deleted member is a tombstone: account_type 'deleted', every personal field emptied, seen by nobody (their old messages
-- show "Deleted member" to the other person through the conversation functions, which read the name as stored)
alter table public.profiles drop constraint if exists profiles_account_type_check;
alter table public.profiles add constraint profiles_account_type_check check (account_type = any (array['professional', 'company', 'admin', 'deleted']));
drop policy if exists "profiles: everyone can read" on public.profiles;
create policy "profiles: everyone can read" on public.profiles for select to authenticated using (account_type is distinct from 'deleted');   -- members only (0020), never the tombstone

create table if not exists private.account_deletions (user_id uuid primary key, started_at timestamptz not null default now());
create table if not exists private.deleted_accounts (user_id uuid primary key, deleted_at timestamptz not null default now());
create table if not exists private.billing_archive (order_id bigint primary key, user_id uuid not null, buyer_name text, buyer_email text, archived_at timestamptz not null default now());
revoke all on table private.account_deletions, private.deleted_accounts, private.billing_archive from public, anon, authenticated;

-- step 1 (the member): password and the word DELETE; answers the member's files for the Edge Function to remove
create or replace function public.account_delete_begin(p_password text, p_confirm text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); files jsonb;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if upper(trim(coalesce(p_confirm, ''))) not in ('DELETE', 'حذف') then raise exception 'Type DELETE to confirm' using errcode = '22023'; end if;
  if not private.check_password(me, p_password) then raise exception 'Your password is not correct' using errcode = '28P01'; end if;
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

-- step 2 (the server, after the files are gone): the member's rows, found from the foreign keys to profiles — so a table added
-- later is covered without changing this function. Kept: messages (the other person's conversation), the other person's
-- conversation heads, payment orders (tax records).
create or replace function public.account_anonymise(p_user uuid) returns void
language plpgsql security definer set search_path = public as $$
declare r record;
begin
  if not exists (select 1 from private.account_deletions d where d.user_id = p_user and d.started_at > now() - interval '30 minutes') then
    raise exception 'This account deletion was not confirmed by its member' using errcode = '42501';
  end if;
  insert into private.billing_archive (order_id, user_id, buyer_name, buyer_email)
    select o.id, p_user, p.name, u.email from public.payment_orders o join public.profiles p on p.id = o.user_id left join auth.users u on u.id = o.user_id
     where o.user_id = p_user and o.status in ('paid', 'refunded', 'review')
    on conflict (order_id) do nothing;
  for r in select c.conrelid::regclass as tbl, a.attname as col, c.confdeltype as act
             from pg_constraint c join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
            where c.contype = 'f' and c.confrelid = 'public.profiles'::regclass and array_length(c.conkey, 1) = 1
            order by c.conrelid::regclass::text, a.attname loop
    continue when r.tbl::text in ('messages', 'public.messages', 'payment_orders', 'public.payment_orders');
    continue when r.tbl::text in ('conversation_heads', 'public.conversation_heads') and r.col = 'partner';
    if r.act = 'c' then execute format('delete from %s where %I = $1', r.tbl, r.col) using p_user;
    elsif r.act = 'n' then execute format('update %s set %I = null where %I = $1', r.tbl, r.col, r.col) using p_user;
    end if;
  end loop;
  update public.profiles set name = 'Deleted member', headline = null, company = null, bio = null, avatar_url = null, cover_url = null, website = null,
         phone = null, certs = null, location = null, experience = '[]', education = '[]', certifications = '[]', skills = '{}', languages = '{}',
         open_to_work = false, hiring = false, years_experience = null, desired_role = null, remote_ok = false, available_since = null,
         intro_video = null, intents = '{}', verified = false, role = 'user', account_type = 'deleted', profile_views = 0, followers_count = 0, updated_at = now()
   where id = p_user;
  delete from private.account_deletions where user_id = p_user;
  delete from private.password_attempts where user_id = p_user;
  insert into private.deleted_accounts (user_id) values (p_user) on conflict (user_id) do update set deleted_at = now();
end $$;
revoke all on function public.account_anonymise(uuid) from public, anon, authenticated, service_role;
grant execute on function public.account_anonymise(uuid) to service_role;

-- the other person keeps the conversation: it lists the partner as "Deleted member" (the tombstone is hidden from reads, so the
-- join is a left join), and nobody can write to a deleted member
-- (merge: the same columns as 0039_names_rule_2 — company, city and the name-rule fields — so it applies on top of the name rule)
drop function if exists public.my_conversations(int);
create function public.my_conversations(p_limit int default 30)
returns table (partner uuid, name text, headline text, verified boolean, avatar_url text,
               last_body text, last_at timestamptz, last_from_me boolean, unread int, company text, location text, name_needs_fix boolean,
               name_key text, name_twins int)
language sql stable security invoker set search_path = public as $$
  select h.partner, coalesce(p.name, 'Deleted member'), p.headline, coalesce(p.verified, false), p.avatar_url, h.last_body, h.last_at, h.last_from_me, h.unread,
         p.company, p.location, coalesce(p.name_needs_fix, false), p.name_key,
         case when p.name_key is null then 0 else (select count(*)::int from public.profiles t where t.name_key = p.name_key and t.id <> p.id and t.id <> h.owner) end
  from public.conversation_heads h left join public.profiles p on p.id = h.partner
  where h.owner = (select auth.uid())
  order by h.last_at desc
  limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;
revoke all on function public.my_conversations(int) from public, anon, authenticated, service_role;
grant execute on function public.my_conversations(int) to authenticated, service_role;
create or replace function public.messages_to_deleted_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.profiles p where p.id = new.receiver_id and p.account_type = 'deleted') then
    raise exception 'This member deleted their account' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.messages_to_deleted_guard() from public, anon, authenticated, service_role;
grant execute on function public.messages_to_deleted_guard() to service_role;
drop trigger if exists trg_messages_to_deleted on public.messages;
create trigger trg_messages_to_deleted before insert on public.messages for each row execute function public.messages_to_deleted_guard();

-- ── 4. export_my_data — as the member (row-level security decides what is theirs); phone through my_profile() ─────────────
create or replace function public.export_my_data() returns jsonb
language plpgsql stable set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  return jsonb_build_object(
    'exported_at', now(), 'format', 'Drugbox personal data export v1',
    'profile', (select to_jsonb(p) from public.my_profile() p),
    'settings', (select to_jsonb(s) - 'unsub_token' from public.member_settings s where s.user_id = me),
    'posts', coalesce((select jsonb_agg(jsonb_build_object('id', x.id, 'body', x.body, 'category', x.category, 'created_at', x.created_at,
                 'media', (select coalesce(jsonb_agg(jsonb_build_object('url', m.url, 'name', m.name, 'type', m.type)), '[]'::jsonb) from public.post_media m where m.post_id = x.id))
                 order by x.created_at) from public.posts x where x.user_id = me), '[]'::jsonb),
    'comments', coalesce((select jsonb_agg(jsonb_build_object('post', c.post_id, 'body', c.body, 'created_at', c.created_at) order by c.created_at) from public.comments c where c.user_id = me), '[]'::jsonb),
    'reactions', coalesce((select jsonb_agg(jsonb_build_object('post', r.post_id, 'kind', r.kind)) from public.reactions r where r.user_id = me), '[]'::jsonb),
    'saved_posts', coalesce((select jsonb_agg(s.post_id) from public.saved_posts s where s.user_id = me), '[]'::jsonb),
    'connections', coalesce((select jsonb_agg(jsonb_build_object('with', case when c.requester = me then c.addressee else c.requester end,
                 'name', (select q.name from public.profiles q where q.id = case when c.requester = me then c.addressee else c.requester end), 'status', c.status, 'sent_by_me', c.requester = me))
                 from public.connections c where c.requester = me or c.addressee = me), '[]'::jsonb),
    'following', coalesce((select jsonb_agg(f.person_id) from public.person_followers f where f.user_id = me), '[]'::jsonb),
    'messages', coalesce((select jsonb_agg(jsonb_build_object('from_me', m.sender_id = me, 'with', case when m.sender_id = me then m.receiver_id else m.sender_id end,
                 'body', m.body, 'created_at', m.created_at, 'read_at', m.read_at) order by m.id)
                 from (select * from public.messages m2 where m2.sender_id = me or m2.receiver_id = me order by m2.id desc limit 10000) m), '[]'::jsonb),
    'job_applications', coalesce((select jsonb_agg(to_jsonb(a)) from public.job_applications a where a.user_id = me), '[]'::jsonb),
    'saved_jobs', coalesce((select jsonb_agg(s.job_id) from public.saved_jobs s where s.user_id = me), '[]'::jsonb),
    'listings', coalesce((select jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'category', p.category, 'created_at', p.created_at)) from public.products p where p.user_id = me), '[]'::jsonb),
    'jobs_posted', coalesce((select jsonb_agg(jsonb_build_object('id', j.id, 'title', j.title, 'created_at', j.created_at)) from public.jobs j where j.user_id = me), '[]'::jsonb),
    'groups', coalesce((select jsonb_agg(jsonb_build_object('group', g.group_id, 'role', g.role)) from public.group_members g where g.user_id = me), '[]'::jsonb),
    'companies', coalesce((select jsonb_agg(jsonb_build_object('company', m.company_id, 'role', m.role)) from public.company_members m where m.user_id = me), '[]'::jsonb),
    'payments', coalesce((select jsonb_agg(jsonb_build_object('reference', o.merchant_ref, 'product', o.product_code, 'amount_egp', o.amount_cents / 100.0, 'method', o.method, 'status', o.status, 'created_at', o.created_at, 'paid_at', o.paid_at))
                 from public.payment_orders o where o.user_id = me), '[]'::jsonb),
    'notifications', coalesce((select jsonb_agg(jsonb_build_object('type', n.type, 'message', n.message, 'created_at', n.created_at) order by n.id desc) from (select * from public.notifications n2 where n2.user_id = me order by n2.id desc limit 1000) n), '[]'::jsonb)
  );
end $$;
revoke all on function public.export_my_data() from public, anon, authenticated, service_role;
grant execute on function public.export_my_data() to authenticated;

notify pgrst, 'reload schema';
