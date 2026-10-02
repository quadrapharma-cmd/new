-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0004 — messages (step B4)
-- Conversation index (both directions), read receipts (receiver may set read_at only),
-- my_conversations() and conversation_messages() — each reads one page, however many messages exist.
-- ═════════════════════════════════════════════════════════════════════
create index if not exists idx_msgs_pair on public.messages
  (least(sender_id, receiver_id), greatest(sender_id, receiver_id), created_at desc, id desc);
create index if not exists idx_msgs_unread on public.messages (receiver_id, sender_id) where read_at is null;
create index if not exists idx_msgs_receiver_id on public.messages (receiver_id, id);

-- read receipts: the receiver may set read_at, and nothing else
do $$ begin
  create policy "messages: receiver marks read" on public.messages for update
    using (receiver_id = auth.uid()) with check (receiver_id = auth.uid());
exception when duplicate_object then null; end $$;
create or replace function public.messages_guard() returns trigger language plpgsql as $$
begin
  if new.body is distinct from old.body or new.image_url is distinct from old.image_url or new.sender_id <> old.sender_id
     or new.receiver_id <> old.receiver_id or new.created_at <> old.created_at then
    raise exception 'Messages cannot be edited' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_messages_guard on public.messages;
create trigger trg_messages_guard before update on public.messages for each row execute function public.messages_guard();
do $$ begin
  alter table public.messages add constraint messages_not_self check (sender_id <> receiver_id);
exception when duplicate_object then null; end $$;

create or replace function public.my_conversations(p_limit int default 30)
returns table (partner uuid, name text, headline text, verified boolean, avatar_url text,
               last_body text, last_at timestamptz, last_from_me boolean, unread int)
language sql stable security invoker set search_path = public as $$
  with me as (select auth.uid() as uid),
  last as (
    select distinct on (partner) partner, body, image_url, created_at, from_me from (
      select case when m.sender_id = me.uid then m.receiver_id else m.sender_id end as partner, m.body, m.image_url, m.created_at, m.id,
             m.sender_id = me.uid as from_me
      from public.messages m, me where m.sender_id = me.uid or m.receiver_id = me.uid) x
    order by partner, created_at desc, id desc),
  unread as (select m.sender_id as partner, count(*)::int as n from public.messages m, me where m.receiver_id = me.uid and m.read_at is null group by 1)
  select l.partner, p.name, p.headline, p.verified, p.avatar_url,
         coalesce(nullif(l.body, ''), case when l.image_url is not null then '📷 Photo' end), l.created_at, l.from_me, coalesce(u.n, 0)
  from last l join public.profiles p on p.id = l.partner left join unread u on u.partner = l.partner
  order by l.created_at desc
  limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;

create or replace function public.conversation_messages(p_partner uuid, p_before_id bigint default null, p_limit int default 50)
returns setof public.messages language sql stable security invoker set search_path = public as $$
  select m.* from public.messages m
  where least(m.sender_id, m.receiver_id) = least(auth.uid(), p_partner)
    and greatest(m.sender_id, m.receiver_id) = greatest(auth.uid(), p_partner)
    and (p_before_id is null or m.id < p_before_id)
  order by m.created_at desc, m.id desc
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
$$;

revoke all on function public.my_conversations(int) from public, anon;
revoke all on function public.conversation_messages(uuid, bigint, int) from public, anon;
grant execute on function public.my_conversations(int) to authenticated;
grant execute on function public.conversation_messages(uuid, bigint, int) to authenticated;

-- live updates on Supabase: messages and notifications are published to Realtime (skipped where Realtime is absent)
do $$ begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    begin alter publication supabase_realtime add table public.messages; exception when duplicate_object then null; end;
    begin alter publication supabase_realtime add table public.notifications; exception when duplicate_object then null; end;
  end if;
end $$;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
