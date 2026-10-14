-- ═════════════════════════════════════════════════════════════════════
-- 0039 — messages: mute, block and report a conversation (J-SOCIAL-40, the messages part of S-09)
--   1. conversation_mutes  one row per (owner, partner): the owner's badges and "new message" notices skip that partner;
--                          the messages themselves still arrive
--   2. user_blocks         one row per (blocker, blocked): the database refuses a message between the two in either direction
--                          (the blocked person reads "You can't message this person")
--   3. message_reports     a member reports a conversation; the reported person's last 20 messages to the reporter are copied
--                          into the report by the database (the moderator cannot read private messages, and the reporter cannot
--                          make them up); Drugbox moderators read and close them in Admin → Review
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. mute ─────────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.conversation_mutes (
  owner      uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  partner    uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (owner, partner),
  constraint conversation_mutes_not_self check (owner <> partner)
);
alter table public.conversation_mutes enable row level security;
do $$ begin
  create policy "mutes: own read" on public.conversation_mutes for select using (owner = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "mutes: own add" on public.conversation_mutes for insert with check (owner = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "mutes: own remove" on public.conversation_mutes for delete using (owner = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.conversation_mutes from public, anon, authenticated, service_role;
grant select on table public.conversation_mutes to anon;                       -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.conversation_mutes to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.conversation_mutes to service_role;

-- ── 2. block ────────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.user_blocks (
  blocker    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  blocked    uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker, blocked),
  constraint user_blocks_not_self check (blocker <> blocked)
);
alter table public.user_blocks enable row level security;
do $$ begin
  create policy "blocks: own read" on public.user_blocks for select using (blocker = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "blocks: own add" on public.user_blocks for insert with check (blocker = (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "blocks: own remove" on public.user_blocks for delete using (blocker = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.user_blocks from public, anon, authenticated, service_role;
grant select on table public.user_blocks to anon;                              -- no policy for anon → an empty answer (F-26)
grant select, insert, delete on table public.user_blocks to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.user_blocks to service_role;

-- a message between two people when either has blocked the other is refused (the definer reads both people's blocks; the
-- primary key answers each check with one index probe)
create or replace function public.messages_block_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.user_blocks b where b.blocker = new.receiver_id and b.blocked = new.sender_id) then
    raise exception 'You can''t message this person' using errcode = '42501';
  end if;
  if exists (select 1 from public.user_blocks b where b.blocker = new.sender_id and b.blocked = new.receiver_id) then
    raise exception 'You blocked this person — unblock them to send a message' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.messages_block_guard() from public, anon, authenticated, service_role;
grant execute on function public.messages_block_guard() to service_role;
drop trigger if exists trg_messages_block_guard on public.messages;
create trigger trg_messages_block_guard before insert on public.messages for each row execute function public.messages_block_guard();

-- ── 3. report ───────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.message_reports (
  id          bigint generated by default as identity primary key,
  reporter    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  reported    uuid not null references public.profiles(id) on delete cascade,
  reason      text not null constraint message_reports_reason_check check (char_length(reason) between 1 and 120),
  details     text constraint message_reports_details_check check (details is null or char_length(details) <= 2000),
  excerpt     jsonb not null default '[]'::jsonb,
  status      text not null default 'open' check (status in ('open', 'actioned', 'dismissed')),
  decided_by  uuid references public.profiles(id) on delete set null,
  decided_at  timestamptz,
  created_at  timestamptz not null default now(),
  constraint message_reports_not_self check (reporter <> reported)
);
create index if not exists idx_message_reports_open on public.message_reports (created_at) where status = 'open';
create index if not exists idx_message_reports_reporter on public.message_reports (reporter, created_at desc);
create index if not exists idx_message_reports_reported on public.message_reports (reported);
alter table public.message_reports enable row level security;

-- the database writes what a report holds: who reports (the caller), the reported messages (copied, newest 20 the reported
-- person sent the reporter) and the open status; only a moderator changes the status, and nothing else, afterwards
create or replace function public.message_reports_before_write() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    if auth.uid() is not null then new.reporter := auth.uid(); end if;
    new.status := 'open'; new.decided_by := null; new.decided_at := null; new.created_at := now();
    select coalesce(jsonb_agg(jsonb_build_object('id', x.id, 'body', x.body, 'at', x.created_at,
                                                  'file', x.attachment ->> 'name') order by x.id), '[]'::jsonb)
      into new.excerpt
      from (select m.id, m.body, m.created_at, m.attachment from public.messages m
             where m.sender_id = new.reported and m.receiver_id = new.reporter order by m.id desc limit 20) x;
    if new.excerpt = '[]'::jsonb then
      raise exception 'This person has not sent you any messages to report' using errcode = '42501';
    end if;
    return new;
  end if;
  if auth.uid() is not null and not public.is_moderator() then
    raise exception 'Only the Drugbox team can close a report' using errcode = '42501';
  end if;
  if new.reporter <> old.reporter or new.reported <> old.reported or new.reason is distinct from old.reason
     or new.details is distinct from old.details or new.excerpt <> old.excerpt or new.created_at <> old.created_at then
    raise exception 'A report cannot be edited' using errcode = '42501';
  end if;
  if new.status is distinct from old.status then new.decided_by := auth.uid(); new.decided_at := now(); end if;
  return new;
end $$;
revoke all on function public.message_reports_before_write() from public, anon, authenticated, service_role;
grant execute on function public.message_reports_before_write() to service_role;
drop trigger if exists trg_message_reports_before_write on public.message_reports;
create trigger trg_message_reports_before_write before insert or update on public.message_reports
  for each row execute function public.message_reports_before_write();

do $$ begin
  create policy "message reports: file as yourself" on public.message_reports for insert
    with check (reporter = (select auth.uid()) and status = 'open');
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "message reports: the reporter and Drugbox read" on public.message_reports for select
    using (reporter = (select auth.uid()) or (select public.is_moderator()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "message reports: Drugbox decides" on public.message_reports for update
    using ((select public.is_moderator())) with check ((select public.is_moderator()));
exception when duplicate_object then null; end $$;
revoke all on table public.message_reports from public, anon, authenticated, service_role;
grant select on table public.message_reports to anon;                          -- no policy for anon → an empty answer (F-26)
grant select, insert, update on table public.message_reports to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.message_reports to service_role;
revoke all on sequence public.message_reports_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.message_reports_id_seq to authenticated, service_role;

notify pgrst, 'reload schema';
