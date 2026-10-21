-- ═════════════════════════════════════════════════════════════════════
-- 0051 — a company's team on Drugbox (B-04; J-BUSINESS-15, 17)
--   "Invite a colleague" said "Invitation sent" and nothing happened; "Ask to join the team" only showed a toast. This adds:
--   1. company_members.pending: 'invite' (the company invited the person — waiting for the person to accept) or 'request' (the
--      person asked to join — waiting for an owner / admin). A pending row is not a member (accepted stays false): it gives no
--      access anywhere (is_company_member). New role 'management' (the interface's "Management").
--   2. company_invite(company, email, name, role): owners / admins invite by e-mail. A member with that e-mail gets the pending
--      invitation and a notification at once; an address nobody uses yet is kept in company_invites and becomes the invitation
--      when that person signs up. Only an owner invites an admin; nobody invites an owner.
--   3. company_invite_respond(company, accept): the invited person accepts (now a member, not shown publicly until they choose
--      "Show me") or declines (the row goes). The inviter is told.
--   4. company_join_request(company, role, note): a signed-in person asks to join a claimed company; its owners and admins are
--      notified. company_join_decide(company, person, ok, role): an owner / admin approves (with the role) or declines; the
--      person is told.
--   5. Who receives what (company_routing) follows the team without undoing the owner's choices: a member who leaves loses
--      their routes (the owner answers); a member who joins or whose role changes drops the kinds the new role does not take
--      and picks up the role's kinds nobody receives yet (questionnaire → Quality / Regulatory, dossier → Regulatory, job → HR…).
--   Every function is SECURITY DEFINER, checks the caller itself, and is granted to signed-in members only.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

alter table public.company_members add column if not exists pending    text;
alter table public.company_members add column if not exists invited_by uuid references public.profiles(id) on delete set null;
alter table public.company_members add column if not exists note       text;
do $$ begin
  alter table public.company_members add constraint company_members_pending_chk check (pending is null or (pending in ('invite','request') and not accepted));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.company_members add constraint company_members_note_len check (length(note) <= 300);
exception when duplicate_object then null; end $$;
alter table public.company_members drop constraint if exists company_members_role_check;
alter table public.company_members add constraint company_members_role_check check (role in ('owner','admin','management','sales','quality','regulatory','hr','member'));
create index if not exists idx_company_members_invited_by on public.company_members (invited_by) where invited_by is not null;
create index if not exists idx_company_members_pending on public.company_members (company_id) where pending is not null;

-- invitations to an address that has no account yet
create table if not exists public.company_invites (
  id          bigint generated always as identity primary key,
  company_id  bigint not null references public.companies(id) on delete cascade,
  email       text not null check (length(email) between 3 and 320 and email = lower(email) and email like '%_@_%'),
  name        text check (length(name) <= 120),
  role        text not null check (role in ('admin','management','sales','quality','regulatory','hr','member')),
  invited_by  uuid references public.profiles(id) on delete set null,
  created_at  timestamptz not null default now(),
  unique (company_id, email)
);
create index if not exists idx_company_invites_email on public.company_invites (email);
create index if not exists idx_company_invites_by on public.company_invites (invited_by) where invited_by is not null;
alter table public.company_invites enable row level security;
do $$ begin
  create policy "company invites: owners/admins read" on public.company_invites for select to authenticated using (public.is_company_member(company_id, array['owner','admin']));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "company invites: owners/admins cancel" on public.company_invites for delete to authenticated using (public.is_company_member(company_id, array['owner','admin']));
exception when duplicate_object then null; end $$;
revoke all on public.company_invites from public, anon, authenticated;
grant select, delete on public.company_invites to authenticated;
grant all on public.company_invites to service_role;
revoke all on sequence public.company_invites_id_seq from public, anon, authenticated, service_role;
grant usage, select, update on sequence public.company_invites_id_seq to authenticated, service_role;
grant select on public.company_invites to anon;   -- F-26: a signed-out query returns no rows (every policy is for signed-in members), never an error

-- the interface's roles (the database's names)
create or replace function public.team_role(p text) returns text language sql immutable set search_path = public as $$
  select case lower(trim(coalesce(p, ''))) when 'admin' then 'admin' when 'management' then 'management' when 'sales' then 'sales'
    when 'quality' then 'quality' when 'regulatory' then 'regulatory' when 'hr' then 'hr' when 'member' then 'member' else null end
$$;
revoke all on function public.team_role(text) from public, anon, authenticated, service_role;
grant execute on function public.team_role(text) to authenticated, service_role;

-- ── who receives what follows the roles ────
-- who receives what follows the team without ever undoing the owner's own choices in "Who receives what":
--   a member who leaves (or is no longer accepted) loses their routes — the kind falls back to the owner (deal_receiver);
--   a member who joins (accepts an invitation, is approved) or whose role changes drops the kinds the new role does not
--   take, and picks up the kinds of the role that nobody receives yet. A route someone already has is never moved.
create or replace function public.team_kinds(p_role text) returns text[] language sql immutable set search_path = public as $$
  select coalesce(array_agg(k), '{}') from (values ('quote', array['sales','management','admin','owner']), ('service', array['sales','management','admin','owner']),
      ('surplus', array['sales','admin','owner']), ('group_order', array['sales','admin','owner']), ('questionnaire', array['quality','regulatory','admin','owner']),
      ('dossier', array['regulatory','management','admin','owner']), ('job', array['hr','management','admin','owner'])) v(k, pref) where p_role = any(pref)
$$;
revoke all on function public.team_kinds(text) from public, anon, authenticated, service_role;
grant execute on function public.team_kinds(text) to service_role;
drop function if exists public.company_reroute(bigint);

create or replace function public.company_members_reroute() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'DELETE' or (tg_op = 'UPDATE' and old.accepted and not new.accepted) then
    delete from public.company_routing where company_id = old.company_id and user_id = old.user_id;
  elsif tg_op = 'UPDATE' and new.accepted and (new.role is distinct from old.role or not old.accepted) then
    delete from public.company_routing where company_id = new.company_id and user_id = new.user_id and not (request_type = any(public.team_kinds(new.role)));
    insert into public.company_routing (company_id, request_type, user_id)
    select new.company_id, k, new.user_id from unnest(public.team_kinds(new.role)) k
     where new.role not in ('owner', 'admin')                -- an admin keeps answering what the owner gave them, nothing more by itself
       and not exists (select 1 from public.company_routing r where r.company_id = new.company_id and r.request_type = k);
  end if;
  return null;
end $$;
revoke all on function public.company_members_reroute() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_members_reroute on public.company_members;
create trigger trg_company_members_reroute after update or delete on public.company_members for each row execute function public.company_members_reroute();

-- ── invite ────
create or replace function public.company_invite(p_company bigint, p_email text, p_name text default null, p_role text default 'sales')
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v_email text := lower(trim(coalesce(p_email, ''))); v_role text := public.team_role(p_role);
        v_user uuid; v_co record; v_name text := nullif(left(trim(coalesce(p_name, '')), 120), ''); v_me text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select id, name, status into v_co from public.companies where id = p_company;
  if v_co.id is null or v_co.status = 'suspended' then raise exception 'This company page is not available' using errcode = 'P0002'; end if;
  if not public.is_company_member(p_company, array['owner','admin']) then raise exception 'Only the page''s owner or admins can invite' using errcode = '42501'; end if;
  if v_role is null then raise exception 'Choose a role' using errcode = '22023'; end if;
  if v_role = 'admin' and not public.is_company_member(p_company, array['owner']) then raise exception 'Only the owner can invite an admin' using errcode = '42501'; end if;
  if v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' or length(v_email) > 320 then raise exception 'Enter a valid e-mail address' using errcode = '22023'; end if;
  -- at most 50 open invitations per company (an inbox nobody answers is not a team)
  if (select count(*) from public.company_members where company_id = p_company and pending = 'invite')
     + (select count(*) from public.company_invites where company_id = p_company) >= 50 then
    raise exception 'This company already has 50 open invitations' using errcode = 'P0001';
  end if;
  select u.id into v_user from auth.users u where lower(u.email) = v_email limit 1;
  if v_user is null then
    insert into public.company_invites (company_id, email, name, role, invited_by) values (p_company, v_email, v_name, v_role, me)
    on conflict (company_id, email) do update set role = excluded.role, name = coalesce(excluded.name, company_invites.name), invited_by = excluded.invited_by, created_at = now();
    return 'invited';                                          -- the same answer whether the address has an account or not
  end if;
  if exists (select 1 from public.company_members where company_id = p_company and user_id = v_user and (accepted or pending = 'request')) then
    raise exception 'This person is already on the team or has asked to join — see Team' using errcode = '23505';
  end if;
  -- one notice per invitation: asking again (or changing the role) does not notify again, and a company sends at most 30
  -- invitation notices a day — an invitation is not a way to send people messages
  if exists (select 1 from public.company_members where company_id = p_company and user_id = v_user and pending = 'invite') then
    update public.company_members set role = v_role, invited_by = me where company_id = p_company and user_id = v_user;
    return 'invited';
  end if;
  if (select count(*) from public.notifications where company_id = p_company and type = 'company_invite' and created_at > now() - interval '1 day') >= 30 then
    raise exception 'This company has sent 30 invitations today — try again tomorrow' using errcode = 'P0001';
  end if;
  insert into public.company_members (company_id, user_id, role, accepted, show_public, pending, invited_by)
  values (p_company, v_user, v_role, false, false, 'invite', me)
  on conflict (company_id, user_id) do update set role = excluded.role, invited_by = excluded.invited_by, pending = 'invite';
  insert into public.notifications (user_id, type, from_user, company_id, data)          -- cancelled and sent again: still one notice a week per person
  select v_user, 'company_invite', me, p_company, jsonb_build_object('company', v_co.name, 'role', v_role)
   where not exists (select 1 from public.notifications n where n.user_id = v_user and n.company_id = p_company and n.type = 'company_invite' and n.created_at > now() - interval '7 days');
  return 'invited';
end $$;
revoke all on function public.company_invite(bigint, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.company_invite(bigint, text, text, text) to authenticated, service_role;

-- an address invited before it had an account: the invitation is there when that person signs up
create or replace function public.company_invites_claim() returns trigger language plpgsql security definer set search_path = public as $$
declare v_email text; i record;
begin
  select lower(email) into v_email from auth.users where id = new.id;
  if v_email is null then return null; end if;
  for i in delete from public.company_invites where email = v_email returning * loop
    insert into public.company_members (company_id, user_id, role, accepted, show_public, pending, invited_by)
    values (i.company_id, new.id, i.role, false, false, 'invite', i.invited_by) on conflict do nothing;
    insert into public.notifications (user_id, type, from_user, company_id, data)
    select new.id, 'company_invite', i.invited_by, i.company_id, jsonb_build_object('company', c.name, 'role', i.role) from public.companies c where c.id = i.company_id;
  end loop;
  return null;
end $$;
revoke all on function public.company_invites_claim() from public, anon, authenticated, service_role;
drop trigger if exists trg_profiles_company_invites on public.profiles;
create trigger trg_profiles_company_invites after insert on public.profiles for each row execute function public.company_invites_claim();

create or replace function public.company_invite_respond(p_company bigint, p_accept boolean)
returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); m record; v_co text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into m from public.company_members where company_id = p_company and user_id = me and pending = 'invite' for update;
  if m.user_id is null then raise exception 'There is no open invitation from this company' using errcode = 'P0002'; end if;
  select name into v_co from public.companies where id = p_company;
  if p_accept then update public.company_members set accepted = true, pending = null where company_id = p_company and user_id = me;
  else delete from public.company_members where company_id = p_company and user_id = me; end if;
  delete from public.notifications where user_id = me and type = 'company_invite' and company_id = p_company;
  if m.invited_by is not null and m.invited_by <> me then
    insert into public.notifications (user_id, type, from_user, company_id, data)
    values (m.invited_by, 'company_invite_answer', me, p_company, jsonb_build_object('company', v_co, 'accepted', p_accept, 'role', m.role));
  end if;
  return true;
end $$;
revoke all on function public.company_invite_respond(bigint, boolean) from public, anon, authenticated, service_role;
grant execute on function public.company_invite_respond(bigint, boolean) to authenticated, service_role;

-- ── ask to join ────
create or replace function public.company_join_request(p_company bigint, p_role text default 'member', p_note text default null)
returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v_role text := public.team_role(p_role); v_co record; v_note text := nullif(left(trim(coalesce(p_note, '')), 300), ''); m record;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select id, name, status, owner_id into v_co from public.companies where id = p_company;
  if v_co.id is null or v_co.status = 'suspended' then raise exception 'This company page is not available' using errcode = 'P0002'; end if;
  if v_co.status = 'unclaimed' or v_co.owner_id is null then raise exception 'Nobody manages this page yet — claim it instead' using errcode = '22023'; end if;
  if v_role is null or v_role = 'admin' then raise exception 'Choose a role (an owner makes admins)' using errcode = '22023'; end if;
  select * into m from public.company_members where company_id = p_company and user_id = me;
  if m.user_id is not null and m.accepted then raise exception 'You are already on this team' using errcode = '23505'; end if;
  if m.user_id is not null and m.pending = 'invite' then raise exception 'This company has invited you — accept the invitation in your notifications' using errcode = '23505'; end if;
  if m.user_id is not null then return true; end if;                                   -- asked already: one request, one notice
  if (select count(*) from public.company_members where user_id = me and pending = 'request') >= 10 then
    raise exception 'You have 10 open requests — wait for an answer first' using errcode = 'P0001';
  end if;
  insert into public.company_members (company_id, user_id, role, accepted, show_public, pending, note) values (p_company, me, v_role, false, false, 'request', v_note);
  insert into public.notifications (user_id, type, from_user, company_id, data)
  select x.user_id, 'company_join_request', me, p_company, jsonb_build_object('company', v_co.name, 'role', v_role)
    from (select v_co.owner_id as user_id union select a.user_id from public.company_members a where a.company_id = p_company and a.accepted and a.role in ('owner','admin')) x
   where x.user_id is not null and x.user_id <> me;
  return true;
end $$;
revoke all on function public.company_join_request(bigint, text, text) from public, anon, authenticated, service_role;
grant execute on function public.company_join_request(bigint, text, text) to authenticated, service_role;

create or replace function public.company_join_decide(p_company bigint, p_user uuid, p_ok boolean, p_role text default null)
returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); m record; v_role text; v_co text;
begin
  if me is null or not public.is_company_member(p_company, array['owner','admin']) then raise exception 'Only the page''s owner or admins can answer' using errcode = '42501'; end if;
  select * into m from public.company_members where company_id = p_company and user_id = p_user and pending = 'request' for update;
  if m.user_id is null then raise exception 'This request was answered already' using errcode = 'P0002'; end if;
  v_role := coalesce(public.team_role(p_role), m.role);
  if v_role = 'admin' and not public.is_company_member(p_company, array['owner']) then raise exception 'Only the owner can make someone an admin' using errcode = '42501'; end if;
  select name into v_co from public.companies where id = p_company;
  if p_ok then update public.company_members set accepted = true, pending = null, role = v_role where company_id = p_company and user_id = p_user;
  else delete from public.company_members where company_id = p_company and user_id = p_user; end if;
  delete from public.notifications where type = 'company_join_request' and company_id = p_company and from_user = p_user;
  insert into public.notifications (user_id, type, from_user, company_id, data)
  values (p_user, 'company_join_answer', me, p_company, jsonb_build_object('company', v_co, 'accepted', p_ok, 'role', v_role));
  return true;
end $$;
revoke all on function public.company_join_decide(bigint, uuid, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.company_join_decide(bigint, uuid, boolean, text) to authenticated, service_role;

-- a person's own open invitations and requests (the Team list of each company shows its own)
create or replace function public.my_company_invites() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('company_id', m.company_id, 'slug', c.slug, 'name', c.name, 'role', m.role, 'pending', m.pending) order by m.created_at desc), '[]'::json)
  from public.company_members m join public.companies c on c.id = m.company_id
  where m.user_id = auth.uid() and m.pending is not null and c.status <> 'suspended'
$$;
revoke all on function public.my_company_invites() from public, anon, authenticated, service_role;
grant execute on function public.my_company_invites() to authenticated, service_role;

-- the pending rows are not members: the person may not turn their own invitation or request into membership directly
create or replace function public.company_members_pending_guard() returns trigger language plpgsql as $$
begin
  if current_user not in ('anon', 'authenticated') or public.is_platform_admin() then return coalesce(new, old); end if;
  if tg_op = 'INSERT' then
    if new.pending is not null or new.invited_by is not null then raise exception 'Invite or ask to join through Team' using errcode = '42501'; end if;
    return new;
  end if;
  if tg_op = 'UPDATE' and (old.pending is not null or new.pending is distinct from old.pending or new.invited_by is distinct from old.invited_by) then
    raise exception 'Answer invitations and requests through Team or your notifications' using errcode = '42501';
  end if;
  return coalesce(new, old);
end $$;
revoke all on function public.company_members_pending_guard() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_members_pending_guard on public.company_members;
create trigger trg_company_members_pending_guard before insert or update on public.company_members for each row execute function public.company_members_pending_guard();


notify pgrst, 'reload schema';
