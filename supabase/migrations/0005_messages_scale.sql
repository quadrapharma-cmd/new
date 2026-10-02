-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0005 — messages at scale
-- conversation_heads: one row per person per conversation (last message, unread count), kept by triggers,
-- so the conversation list reads one page however many messages exist.
-- conversation_messages / new_messages compute the caller once, so the pair and receiver indexes are used.
-- ═════════════════════════════════════════════════════════════════════
create table if not exists public.conversation_heads (
  owner        uuid not null references public.profiles(id) on delete cascade,
  partner      uuid not null references public.profiles(id) on delete cascade,
  last_message bigint,
  last_body    text,
  last_at      timestamptz not null default now(),
  last_from_me boolean not null default false,
  unread       int not null default 0 check (unread >= 0),
  primary key (owner, partner)
);
create index if not exists idx_heads_owner_last on public.conversation_heads (owner, last_at desc);
alter table public.conversation_heads enable row level security;
do $$ begin
  create policy "heads: own read" on public.conversation_heads for select using (owner = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke insert, update, delete on public.conversation_heads from anon, authenticated;   -- written only by the triggers below

create or replace function public.messages_heads_on_insert() returns trigger language plpgsql security definer set search_path = public as $$
declare body text := coalesce(nullif(new.body, ''), case when new.image_url is not null then '📷 Photo' end);
begin
  insert into public.conversation_heads as h (owner, partner, last_message, last_body, last_at, last_from_me, unread)
  values (new.sender_id, new.receiver_id, new.id, body, new.created_at, true, 0)
  on conflict (owner, partner) do update set last_message = excluded.last_message, last_body = excluded.last_body, last_at = excluded.last_at, last_from_me = true;
  insert into public.conversation_heads as h (owner, partner, last_message, last_body, last_at, last_from_me, unread)
  values (new.receiver_id, new.sender_id, new.id, body, new.created_at, false, case when new.read_at is null then 1 else 0 end)
  on conflict (owner, partner) do update set last_message = excluded.last_message, last_body = excluded.last_body, last_at = excluded.last_at, last_from_me = false,
    unread = h.unread + case when new.read_at is null then 1 else 0 end;
  return null;
end $$;
drop trigger if exists trg_messages_heads_insert on public.messages;
create trigger trg_messages_heads_insert after insert on public.messages for each row execute function public.messages_heads_on_insert();

create or replace function public.messages_heads_on_read() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if old.read_at is null and new.read_at is not null then
    update public.conversation_heads set unread = greatest(unread - 1, 0) where owner = new.receiver_id and partner = new.sender_id;
  end if;
  return null;
end $$;
drop trigger if exists trg_messages_heads_read on public.messages;
create trigger trg_messages_heads_read after update of read_at on public.messages for each row execute function public.messages_heads_on_read();

-- backfill existing conversations (once)
insert into public.conversation_heads (owner, partner, last_message, last_body, last_at, last_from_me, unread)
select x.owner, x.partner, x.id, coalesce(nullif(x.body, ''), case when x.image_url is not null then '📷 Photo' end), x.created_at, x.owner = x.sender_id,
       (select count(*) from public.messages u where u.receiver_id = x.owner and u.sender_id = x.partner and u.read_at is null)
from (select distinct on (owner, partner) owner, partner, id, body, image_url, created_at, sender_id from (
        select m.sender_id as owner, m.receiver_id as partner, m.* from public.messages m
        union all select m.receiver_id, m.sender_id, m.* from public.messages m) y
      order by owner, partner, created_at desc, id desc) x
on conflict (owner, partner) do nothing;

create or replace function public.my_conversations(p_limit int default 30)
returns table (partner uuid, name text, headline text, verified boolean, avatar_url text,
               last_body text, last_at timestamptz, last_from_me boolean, unread int)
language sql stable security invoker set search_path = public as $$
  select h.partner, p.name, p.headline, p.verified, p.avatar_url, h.last_body, h.last_at, h.last_from_me, h.unread
  from public.conversation_heads h join public.profiles p on p.id = h.partner
  where h.owner = (select auth.uid())
  order by h.last_at desc
  limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;

create or replace function public.conversation_messages(p_partner uuid, p_before_id bigint default null, p_limit int default 50)
returns setof public.messages language plpgsql stable security invoker set search_path = public as $$
declare me uuid := auth.uid(); lo uuid; hi uuid;
begin
  if me is null or p_partner is null then return; end if;
  lo := least(me, p_partner); hi := greatest(me, p_partner);
  return query select m.* from public.messages m
    where least(m.sender_id, m.receiver_id) = lo and greatest(m.sender_id, m.receiver_id) = hi
      and (p_before_id is null or m.id < p_before_id)
    order by least(m.sender_id, m.receiver_id), greatest(m.sender_id, m.receiver_id), m.created_at desc, m.id desc
    limit least(greatest(coalesce(p_limit, 50), 1), 100);
end $$;

create or replace function public.new_messages(p_after bigint default 0)
returns setof public.messages language plpgsql stable security invoker set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then return; end if;
  return query select m.* from public.messages m where m.receiver_id = me and m.id > coalesce(p_after, 0) order by m.receiver_id, m.id limit 50;
end $$;
revoke all on function public.new_messages(bigint) from public, anon;
grant execute on function public.new_messages(bigint) to authenticated;
grant select on public.conversation_heads to authenticated;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
