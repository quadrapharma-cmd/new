-- ═════════════════════════════════════════════════════════════════════
-- 0110 — web push for the installable app (slice w-pwa)
--   1. push_subscriptions   one row per device a member switched notifications on (endpoint + its two public keys). A member reads
--                           and removes only their own rows; adding one goes through push_subscribe() — it checks the push
--                           service's address against private.push_hosts (no other server can be made a target), moves an address
--                           that was another account's on this device to the caller, and keeps at most 10 devices per member.
--   2. member_settings      push_* switches per kind (Settings → this device), next to the e-mail switches
--   3. push outbox          a notice of a kind the member allows is queued for each member with a device (private.push_outbox);
--                           never for a notice from someone either side blocked, or a muted conversation. The notify-email
--                           function (service role, every minute) claims the queue (push_outbox_claim), sends through the push
--                           services with VAPID, and reports back (push_outbox_done) — devices the service no longer knows
--                           (404 / 410) are removed. Members never read or write the outbox.
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. devices ───────────────────────────────────────────────────────────────────────────────────────────
-- the push services browsers use (a host or a parent domain); http only for a host marked so (the local test stand-in)
create table if not exists private.push_hosts (
  host       text primary key,
  allow_http boolean not null default false
);
revoke all on table private.push_hosts from public, anon, authenticated;
grant select, insert, update, delete on table private.push_hosts to service_role;
insert into private.push_hosts (host) values
  ('fcm.googleapis.com'),                 -- Chrome, Edge on Android, Samsung Internet, Opera, Brave
  ('push.services.mozilla.com'),          -- Firefox (updates.push.services.mozilla.com)
  ('push.apple.com'),                     -- Safari on macOS and iPhone/iPad 16.4+ (web.push.apple.com)
  ('notify.windows.com')                  -- Edge on Windows (*.notify.windows.com)
on conflict (host) do nothing;

create or replace function private.push_endpoint_ok(p_endpoint text) returns boolean
language sql stable security definer set search_path = private, public as $$
  select coalesce(length(p_endpoint) between 20 and 1024 and exists (
    select 1 from private.push_hosts h,
           lateral (select (regexp_match(p_endpoint, '^(https?)://([A-Za-z0-9.-]+)(:[0-9]{1,5})?/[!-~]*$'))) m(x)
     where m.x is not null and (lower(m.x[2]) = h.host or lower(m.x[2]) like '%.' || h.host)
       and (m.x[1] = 'https' or h.allow_http)), false)
$$;
revoke all on function private.push_endpoint_ok(text) from public, anon, authenticated;
grant execute on function private.push_endpoint_ok(text) to service_role;

create table if not exists public.push_subscriptions (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  endpoint    text not null,
  p256dh      text not null,
  auth        text not null,
  created_at  timestamptz not null default now(),
  last_ok_at  timestamptz,
  constraint push_subscriptions_endpoint_key unique (endpoint),   -- the address is checked by push_subscribe and again when sending
                                                                   -- (not a CHECK: it reads private.push_hosts, which a restore loads in any order)
  constraint push_subscriptions_p256dh_chk check (p256dh ~ '^[A-Za-z0-9_-]{87}$'),      -- 65-byte P-256 point, base64url
  constraint push_subscriptions_auth_chk check (auth ~ '^[A-Za-z0-9_-]{22}$')            -- 16-byte secret, base64url
);
create index if not exists idx_push_subscriptions_user on public.push_subscriptions (user_id);
alter table public.push_subscriptions enable row level security;
do $$ begin
  create policy "push: own read" on public.push_subscriptions for select to authenticated using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "push: own remove" on public.push_subscriptions for delete to authenticated using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.push_subscriptions from public, anon, authenticated, service_role;
grant select (id, endpoint, created_at, last_ok_at), delete on table public.push_subscriptions to authenticated;   -- the device keys stay server-side
grant select, insert, update, delete on table public.push_subscriptions to service_role;
revoke all on sequence public.push_subscriptions_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.push_subscriptions_id_seq to service_role;

-- the device's browser hands over its subscription: keep it for the caller (an address of another account on this device moves)
create or replace function public.push_subscribe(p_endpoint text, p_p256dh text, p_auth text) returns bigint
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); out bigint;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not private.push_endpoint_ok(p_endpoint) then raise exception 'This browser''s push service is not supported' using errcode = '22023'; end if;
  if coalesce(p_p256dh, '') !~ '^[A-Za-z0-9_-]{87}$' or coalesce(p_auth, '') !~ '^[A-Za-z0-9_-]{22}$' then
    raise exception 'The browser sent an invalid subscription' using errcode = '22023'; end if;
  insert into public.push_subscriptions (user_id, endpoint, p256dh, auth) values (me, p_endpoint, p_p256dh, p_auth)
  on conflict (endpoint) do update set user_id = me, p256dh = excluded.p256dh, auth = excluded.auth, created_at = now(), last_ok_at = null
  returning id into out;
  delete from public.push_subscriptions s where s.user_id = me and s.id in (
    select s2.id from public.push_subscriptions s2 where s2.user_id = me order by s2.created_at desc, s2.id desc offset 10);   -- at most 10 devices
  return out;
end $$;
revoke all on function public.push_subscribe(text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.push_subscribe(text, text, text) to authenticated;

-- ── 2. which kinds reach the device ──────────────────────────────────────────────────────────────────────
alter table public.member_settings add column if not exists push_messages    boolean not null default true;
alter table public.member_settings add column if not exists push_connections boolean not null default true;
alter table public.member_settings add column if not exists push_comments    boolean not null default true;
alter table public.member_settings add column if not exists push_mentions    boolean not null default true;
alter table public.member_settings add column if not exists push_reactions   boolean not null default false;
alter table public.member_settings add column if not exists push_follows     boolean not null default false;
alter table public.member_settings add column if not exists push_jobs        boolean not null default true;
alter table public.member_settings add column if not exists push_business    boolean not null default true;   -- deals, payments, companies, groups, Drugbox notices
grant insert (push_messages, push_connections, push_comments, push_mentions, push_reactions, push_follows, push_jobs, push_business) on table public.member_settings to authenticated;
grant update (push_messages, push_connections, push_comments, push_mentions, push_reactions, push_follows, push_jobs, push_business) on table public.member_settings to authenticated;

create or replace function private.push_pref(s public.member_settings, kind text) returns boolean language sql immutable as $$
  select case
    when kind in ('message', 'company_message') then s.push_messages
    when kind in ('connection_request', 'connection_accepted') then s.push_connections
    when kind in ('comment', 'reply') then s.push_comments
    when kind = 'mention' then s.push_mentions
    when kind in ('like', 'comment_like', 'repost', 'endorse', 'skill') then s.push_reactions
    when kind = 'follow' then s.push_follows
    when kind in ('job_application', 'saved_search') or kind like 'job%' then s.push_jobs
    else s.push_business
  end
$$;
revoke all on function private.push_pref(public.member_settings, text) from public, anon, authenticated;
grant execute on function private.push_pref(public.member_settings, text) to service_role;

-- ── 3. the queue ─────────────────────────────────────────────────────────────────────────────────────────
create table if not exists private.push_outbox (
  id              bigint generated always as identity primary key,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  notification_id bigint not null references public.notifications(id) on delete cascade,
  created_at      timestamptz not null default now(),
  due_at          timestamptz not null default now(),
  claimed_at      timestamptz,
  sent_at         timestamptz,
  tries           int not null default 0,
  error           text
);
create index if not exists idx_push_outbox_due on private.push_outbox (due_at) where sent_at is null;
create index if not exists idx_push_outbox_user on private.push_outbox (user_id);
create index if not exists idx_push_outbox_notification on private.push_outbox (notification_id);
revoke all on table private.push_outbox from public, anon, authenticated;
grant select, insert, update, delete on table private.push_outbox to service_role;
revoke all on sequence private.push_outbox_id_seq from public, anon, authenticated;
grant usage, select on sequence private.push_outbox_id_seq to service_role;

-- a notice is queued only for a member with a device, of a kind they allow, from nobody either side blocked / muted
create or replace function public.notifications_push() returns trigger
language plpgsql security definer set search_path = public as $$
declare s public.member_settings;
begin
  if new.user_id is not distinct from new.from_user then return null; end if;
  if not exists (select 1 from public.push_subscriptions p where p.user_id = new.user_id) then return null; end if;
  select * into s from public.member_settings where user_id = new.user_id;
  if not found then s := null; s.user_id := new.user_id;
    s.push_messages := true; s.push_connections := true; s.push_comments := true; s.push_mentions := true;
    s.push_reactions := false; s.push_follows := false; s.push_jobs := true; s.push_business := true; end if;   -- the column defaults
  if not coalesce(private.push_pref(s, new.type), false) then return null; end if;
  if new.from_user is not null and (
       exists (select 1 from public.user_blocks b where (b.blocker = new.user_id and b.blocked = new.from_user) or (b.blocker = new.from_user and b.blocked = new.user_id))
    or (new.type in ('message', 'company_message') and exists (select 1 from public.conversation_mutes m where m.owner = new.user_id and m.partner = new.from_user))) then
    return null; end if;
  insert into private.push_outbox (user_id, notification_id) values (new.user_id, new.id);
  return null;
end $$;
revoke all on function public.notifications_push() from public, anon, authenticated, service_role;
grant execute on function public.notifications_push() to service_role;
drop trigger if exists trg_notifications_push on public.notifications;
create trigger trg_notifications_push after insert on public.notifications for each row execute function public.notifications_push();

-- the sender: what is due (at most a day old, not read meanwhile, from nobody blocked since), with the member's devices
create or replace function public.push_outbox_claim(p_limit int default 100) returns jsonb
language plpgsql security definer set search_path = public as $$
declare n int := least(greatest(coalesce(p_limit, 100), 1), 500); out jsonb;
begin
  delete from private.push_outbox o where o.created_at < now() - interval '7 days';                 -- the queue does not grow for ever
  update private.push_outbox o set sent_at = now(), error = 'stale or read'                          -- not worth a buzz any more
   where o.sent_at is null and (o.created_at < now() - interval '1 day' or o.tries >= 5
      or exists (select 1 from public.notifications x where x.id = o.notification_id and coalesce(x.read, false)));
  with c as (
    select o.id from private.push_outbox o
     where o.sent_at is null and o.due_at <= now() and (o.claimed_at is null or o.claimed_at < now() - interval '5 minutes')
     order by o.due_at limit n for update skip locked),
  u as (update private.push_outbox o set claimed_at = now(), tries = o.tries + 1 from c where o.id = c.id returning o.*)
  select coalesce(jsonb_agg(jsonb_build_object(
      'id', u.id, 'lang', coalesce(s.lang, 'en'),
      'notice', jsonb_build_object('type', x.type, 'from', a.name, 'from_id', x.from_user, 'post_id', x.post_id, 'job_id', x.job_id,
                                   'group_id', x.group_id, 'kind', x.data->>'kind', 'at', x.created_at),
      'devices', (select coalesce(jsonb_agg(jsonb_build_object('id', d.id, 'endpoint', d.endpoint, 'p256dh', d.p256dh, 'auth', d.auth) order by d.id), '[]')
                    from public.push_subscriptions d where d.user_id = u.user_id and private.push_endpoint_ok(d.endpoint)))), '[]')
    into out
    from u join public.notifications x on x.id = u.notification_id
    join public.profiles p on p.id = u.user_id
    left join public.member_settings s on s.user_id = u.user_id
    left join public.profiles a on a.id = x.from_user
   where p.account_type is distinct from 'deleted';
  return out;
end $$;
revoke all on function public.push_outbox_claim(int) from public, anon, authenticated, service_role;
grant execute on function public.push_outbox_claim(int) to service_role;

-- the outcome: sent (or failed: tried again in a minute, at most 5 times); devices the push service no longer knows are removed
create or replace function public.push_outbox_done(p_id bigint, p_ok boolean, p_error text default null, p_gone bigint[] default '{}', p_ok_devices bigint[] default '{}') returns void
language sql security definer set search_path = public as $$
  delete from public.push_subscriptions where id = any(coalesce(p_gone, '{}'));
  update public.push_subscriptions set last_ok_at = now() where id = any(coalesce(p_ok_devices, '{}'));
  update private.push_outbox set sent_at = case when p_ok then now() end, error = case when p_ok then null else left(p_error, 500) end,
         claimed_at = case when p_ok then claimed_at end, due_at = case when p_ok then due_at else now() + interval '1 minute' end
   where id = p_id;
$$;
revoke all on function public.push_outbox_done(bigint, boolean, text, bigint[], bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.push_outbox_done(bigint, boolean, text, bigint[], bigint[]) to service_role;

notify pgrst, 'reload schema';
