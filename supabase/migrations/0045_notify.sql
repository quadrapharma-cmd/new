-- ═════════════════════════════════════════════════════════════════════
-- 0045 — notifications that reach the member (area social: S-20, J-SOCIAL-41/42/44/47)
--   1. 'message' notices      a new message tells the receiver once per conversation while it is unread (not when the
--                             receiver muted the sender); reading the conversation marks the notice read
--      a reply to the post author's own comment is one 'reply' notice (not also 'comment'); comment likes are counted again
--   2. saved-search notices   carry the matching item's title, so the notice opens it
--      saved searches: the 20-per-member limit moves from the insert policy (it recursed) to a trigger
--   3. e-mail outbox          a notice of a kind the member switched on in Settings → Notifications is queued for e-mail
--                             (private.email_outbox); kinds switched off wait for the daily / weekly digest when one is chosen.
--                             The notify-email function (service role, scheduled every minute) claims and sends them through
--                             Resend; members never read or write the outbox
--   4. explicit grants the earlier area migrations left to the defaults (anon reads of two tables, three sequences)
-- Every table and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. messages → one notice per unread conversation ─────────────────────────────────────────────────────
create or replace function public.notify_message() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.conversation_mutes m where m.owner = new.receiver_id and m.partner = new.sender_id) then return null; end if;
  if exists (select 1 from public.notifications n where n.user_id = new.receiver_id and n.from_user = new.sender_id and n.type in ('message', 'company_message') and not coalesce(n.read, false)) then return null; end if;   -- a message to a company is announced as such (0032)
  insert into public.notifications (user_id, type, from_user, message) values (new.receiver_id, 'message', new.sender_id, 'sent you a message');
  return null;
end $$;
revoke all on function public.notify_message() from public, anon, authenticated, service_role;
grant execute on function public.notify_message() to service_role;
drop trigger if exists trg_messages_notify on public.messages;
-- at the end of the transaction: company_message() writes its own notice after the message (0034)
create constraint trigger trg_messages_notify after insert on public.messages deferrable initially deferred for each row execute function public.notify_message();

create or replace function public.notify_message_read() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.read_at is not null and old.read_at is null
     and not exists (select 1 from public.messages m where m.receiver_id = new.receiver_id and m.sender_id = new.sender_id and m.read_at is null and m.id <> new.id) then
    update public.notifications set read = true where user_id = new.receiver_id and from_user = new.sender_id and type = 'message' and not coalesce(read, false);
  end if;
  return null;
end $$;
revoke all on function public.notify_message_read() from public, anon, authenticated, service_role;
grant execute on function public.notify_message_read() to service_role;
drop trigger if exists trg_messages_notify_read on public.messages;
create trigger trg_messages_notify_read after update of read_at on public.messages for each row execute function public.notify_message_read();

-- a reply to the post author's own comment tells the author once ('reply'), not also 'comment'
create or replace function public.notify_comment() returns trigger
language plpgsql security definer set search_path = public as $$
declare owner uuid;
begin
  select user_id into owner from public.posts where id = new.post_id;
  if owner is not null and owner <> new.user_id
     and not (new.parent_id is not null and exists (select 1 from public.comments c where c.id = new.parent_id and c.user_id = owner)) then
    insert into public.notifications(user_id, type, from_user, post_id, comment_id, message)
    values (owner, 'comment', new.user_id, new.post_id, new.id, left(new.body, 140));   -- removed with the comment (FK cascade)
  end if;
  return null;
end $$;
revoke all on function public.notify_comment() from public, anon, authenticated, service_role;
grant execute on function public.notify_comment() to authenticated, service_role;

-- comment likes are counted: the reply guard kept the old count on every update, so the counter's own update was undone too.
-- A member's update (trigger depth 1) still cannot change the count or the thread; the like counter (a nested trigger) can.
create or replace function public.comments_reply_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  if tg_op = 'INSERT' then new.like_count := 0;
  else new.parent_id := old.parent_id; if pg_trigger_depth() <= 1 then new.like_count := old.like_count; end if; end if;
  if tg_op = 'INSERT' and new.parent_id is not null then
    select c.post_id, c.parent_id into p from public.comments c where c.id = new.parent_id;
    if not found or p.post_id <> new.post_id then raise exception 'You can only reply to a comment of this post' using errcode = '22023'; end if;
    if p.parent_id is not null then new.parent_id := p.parent_id; end if;          -- one level: a reply to a reply joins its thread
  end if;
  return new;
end $$;
revoke all on function public.comments_reply_guard() from public, anon, authenticated, service_role;
grant execute on function public.comments_reply_guard() to authenticated, service_role;
update public.comments c set like_count = x.n from (select comment_id, count(*)::int as n from public.comment_reactions group by 1) x
 where x.comment_id = c.id and c.like_count is distinct from x.n;                -- counts lost so far

-- ── 2. saved-search notices name the item ────────────────────────────────────────────────────────────────
create or replace function public.saved_search_matches() returns trigger
language plpgsql security definer set search_path = public as $$
declare k text := case when tg_table_name = 'jobs' then 'jobs' else 'market' end; t text; title text; s record; r jsonb := to_jsonb(new);
begin
  if not coalesce((r->>'active')::boolean, true) then return null; end if;
  title := coalesce(case when k = 'jobs' then r->>'title' else r->>'name' end, '');           /* read as JSON: one function for two tables */
  t := lower(title || ' ' || coalesce(case when k = 'jobs' then r->>'company' end, ''));
  for s in select ss.id, ss.user_id, ss.name from public.saved_searches ss
            where ss.kind = k and ss.alert <> 'off' and ss.q <> '' and ss.user_id <> (r->>'user_id')::uuid and position(lower(ss.q) in t) > 0
              and not exists (select 1 from public.user_blocks b where (b.blocker = ss.user_id and b.blocked = (r->>'user_id')::uuid) or (b.blocker = (r->>'user_id')::uuid and b.blocked = ss.user_id))
            limit 200 loop
    insert into public.notifications (user_id, type, from_user, job_id, message, data)
    values (s.user_id, 'saved_search', (r->>'user_id')::uuid, case when k = 'jobs' then (r->>'id')::bigint end,
            'New match for your saved search “' || left(s.name, 80) || '”: ' || left(title, 120),
            jsonb_build_object('kind', k, 'id', (r->>'id')::bigint, 'search', s.id, 'title', left(title, 120)));
  end loop;
  return null;
end $$;
revoke all on function public.saved_search_matches() from public, anon, authenticated, service_role;
grant execute on function public.saved_search_matches() to service_role;

-- at most 20 saved searches each — checked by a trigger (a policy that counts its own table recurses)
drop policy if exists "saved searches: own add" on public.saved_searches;
create policy "saved searches: own add" on public.saved_searches for insert with check (user_id = (select auth.uid()));
create or replace function public.saved_searches_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from public.saved_searches s where s.user_id = new.user_id) >= 20 then
    raise exception 'You can keep up to 20 saved searches — delete one first' using errcode = '23514';
  end if;
  return new;
end $$;
revoke all on function public.saved_searches_limit() from public, anon, authenticated, service_role;
grant execute on function public.saved_searches_limit() to service_role;
drop trigger if exists trg_saved_searches_limit on public.saved_searches;
create trigger trg_saved_searches_limit before insert on public.saved_searches for each row execute function public.saved_searches_limit();

-- ── 3. e-mail ────────────────────────────────────────────────────────────────────────────────────────────
alter table public.member_settings add column if not exists digest_sent_at timestamptz;
create table if not exists private.email_outbox (
  id              bigint generated always as identity primary key,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  notification_id bigint references public.notifications(id) on delete cascade,
  kind            text not null default 'notice',
  due_at          timestamptz not null default now(),
  claimed_at      timestamptz,
  sent_at         timestamptz,
  tries           int not null default 0,
  error           text,
  created_at      timestamptz not null default now(),
  constraint email_outbox_kind_chk check (kind in ('notice', 'digest'))
);
create index if not exists idx_email_outbox_due on private.email_outbox (due_at) where sent_at is null;
create index if not exists idx_email_outbox_user on private.email_outbox (user_id);
create index if not exists idx_email_outbox_notification on private.email_outbox (notification_id);
revoke all on table private.email_outbox from public, anon, authenticated;
grant select, insert, update, delete on table private.email_outbox to service_role;

-- which Settings switch covers a notice kind (null: never e-mailed on its own)
create or replace function private.email_pref(s public.member_settings, kind text) returns boolean language sql immutable as $$
  select case
    when kind = 'message' then s.email_messages
    when kind in ('connection_request', 'connection_accepted') then s.email_connections
    when kind in ('comment', 'reply') then s.email_comments
    when kind = 'mention' then s.email_mentions
    when kind in ('like', 'comment_like', 'repost') then s.email_reactions
    when kind = 'follow' then s.email_follows
    when kind in ('job_application', 'saved_search') then s.email_jobs
  end
$$;
revoke all on function private.email_pref(public.member_settings, text) from public, anon;
grant execute on function private.email_pref(public.member_settings, text) to service_role, authenticated;

create or replace function public.notifications_email() returns trigger
language plpgsql security definer set search_path = public as $$
declare s public.member_settings;
begin
  if new.user_id = new.from_user then return null; end if;
  select * into s from public.member_settings where user_id = new.user_id;
  if not found then return null; end if;
  if coalesce(private.email_pref(s, new.type), false) then
    insert into private.email_outbox (user_id, notification_id) values (new.user_id, new.id);
  end if;
  return null;
end $$;
revoke all on function public.notifications_email() from public, anon, authenticated, service_role;
grant execute on function public.notifications_email() to service_role;
drop trigger if exists trg_notifications_email on public.notifications;
create trigger trg_notifications_email after insert on public.notifications for each row execute function public.notifications_email();

-- the sender function: claims what is due (and digests that are due), returns everything it needs to write each e-mail
create or replace function public.email_outbox_claim(p_limit int default 50) returns jsonb
language plpgsql security definer set search_path = public as $$
declare n int := least(greatest(coalesce(p_limit, 50), 1), 200); out jsonb;
begin
  -- digests: members with a digest whose period has passed and who have unread notices not e-mailed on their own
  insert into private.email_outbox (user_id, kind)
  select s.user_id, 'digest' from public.member_settings s
   where s.digest <> 'off'
     and coalesce(s.digest_sent_at, s.updated_at - interval '8 days') < now() - case s.digest when 'daily' then interval '1 day' else interval '7 days' end
     and exists (select 1 from public.notifications x where x.user_id = s.user_id and not coalesce(x.read, false) and x.created_at > coalesce(s.digest_sent_at, now() - interval '7 days')
                  and not coalesce(private.email_pref(s, x.type), false))
     and not exists (select 1 from private.email_outbox o where o.user_id = s.user_id and o.kind = 'digest' and o.sent_at is null)
   limit 500;
  update public.member_settings s set digest_sent_at = now() where s.user_id in (select o.user_id from private.email_outbox o where o.kind = 'digest' and o.sent_at is null and o.claimed_at is null);

  with c as (
    select o.id from private.email_outbox o
     where o.sent_at is null and o.due_at <= now() and o.tries < 5 and (o.claimed_at is null or o.claimed_at < now() - interval '10 minutes')
     order by o.due_at limit n for update skip locked),
  u as (update private.email_outbox o set claimed_at = now(), tries = o.tries + 1 from c where o.id = c.id returning o.*)
  select coalesce(jsonb_agg(jsonb_build_object(
      'id', u.id, 'kind', u.kind, 'to', au.email, 'name', p.name, 'lang', coalesce(s.lang, 'en'),
      'notice', case when x.id is not null then jsonb_build_object('type', x.type, 'from', a.name, 'from_id', x.from_user, 'post_id', x.post_id,
                       'job_id', x.job_id, 'group_id', x.group_id, 'message', left(x.message, 300), 'data', x.data, 'read', coalesce(x.read, false)) end,
      'digest', case when u.kind = 'digest' then (select coalesce(jsonb_agg(jsonb_build_object('type', y.type, 'from', b.name, 'message', left(y.message, 200)) order by y.created_at desc), '[]')
                  from (select * from public.notifications y0 where y0.user_id = u.user_id and not coalesce(y0.read, false) order by y0.created_at desc limit 20) y
                  left join public.profiles b on b.id = y.from_user) end)), '[]')
    into out
    from u join auth.users au on au.id = u.user_id join public.profiles p on p.id = u.user_id
    left join public.member_settings s on s.user_id = u.user_id
    left join public.notifications x on x.id = u.notification_id
    left join public.profiles a on a.id = x.from_user
   where p.account_type is distinct from 'deleted' and au.email not like '%@deleted.invalid';
  return out;
end $$;
revoke all on function public.email_outbox_claim(int) from public, anon, authenticated, service_role;
grant execute on function public.email_outbox_claim(int) to service_role;

create or replace function public.email_outbox_done(p_id bigint, p_ok boolean, p_error text default null) returns void
language sql security definer set search_path = public as $$
  update private.email_outbox set sent_at = case when p_ok then now() end, error = case when p_ok then null else left(p_error, 500) end,
         claimed_at = case when p_ok then claimed_at end, due_at = case when p_ok then due_at else now() + interval '5 minutes' end
   where id = p_id
$$;
revoke all on function public.email_outbox_done(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.email_outbox_done(bigint, boolean, text) to service_role;

-- ── 4. privileges the earlier area migrations left to the platform's defaults (0026: every grant is explicit) ─────────────
grant select on table public.skill_endorsements to anon;                          -- no policy for anon → an empty answer (F-26)
grant select on table public.moderation_log to anon;
revoke all on sequence public.saved_searches_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.saved_searches_id_seq to authenticated, service_role;
revoke all on sequence public.member_reports_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.member_reports_id_seq to authenticated, service_role;
revoke all on sequence public.moderation_log_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.moderation_log_id_seq to service_role;
revoke all on sequence private.email_outbox_id_seq from public, anon, authenticated;
grant usage, select on sequence private.email_outbox_id_seq to service_role;

notify pgrst, 'reload schema';
