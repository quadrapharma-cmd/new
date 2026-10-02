-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0013 — groups in the live app (step D3)
-- group_members had row-level security ON and NO policy, so nobody could join a group or see members.
-- Policies, member count kept by the database, the creator becomes admin, and a topic for the card's tag.
-- ═════════════════════════════════════════════════════════════════════
alter table public.groups add column if not exists topic text not null default 'DISCUSS';
create index if not exists idx_groups_members on public.groups (member_count desc, created_at desc);
create index if not exists idx_group_members_user on public.group_members (user_id);

create or replace function public.is_group_member(gid bigint, roles text[] default null) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.group_members m where m.group_id = gid and m.user_id = auth.uid() and (roles is null or m.role = any(roles)))
$$;
do $$ begin
  create policy "group members: visible for public groups or to members" on public.group_members for select
    using (exists (select 1 from public.groups g where g.id = group_id and g.type = 'public') or public.is_group_member(group_id));
  create policy "group members: join a public group yourself" on public.group_members for insert
    with check (user_id = (select auth.uid()) and role = 'member' and exists (select 1 from public.groups g where g.id = group_id and g.type = 'public'));
  create policy "group members: leave, or an admin removes" on public.group_members for delete
    using (user_id = (select auth.uid()) or public.is_group_member(group_id, array['admin']));
  create policy "group members: admins change roles" on public.group_members for update
    using (public.is_group_member(group_id, array['admin'])) with check (public.is_group_member(group_id, array['admin']));
exception when duplicate_object then null; end $$;

create or replace function public.groups_after_insert() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.created_by is not null then insert into public.group_members (group_id, user_id, role) values (new.id, new.created_by, 'admin') on conflict do nothing; end if;
  return new;
end $$;
drop trigger if exists trg_groups_after_insert on public.groups;
create trigger trg_groups_after_insert after insert on public.groups for each row execute function public.groups_after_insert();

create or replace function public.group_member_count() returns trigger language plpgsql security definer set search_path = public as $$
begin
  update public.groups set member_count = (select count(*) from public.group_members where group_id = coalesce(new.group_id, old.group_id)) where id = coalesce(new.group_id, old.group_id);
  return null;
end $$;
drop trigger if exists trg_group_member_count on public.group_members;
create trigger trg_group_member_count after insert or delete on public.group_members for each row execute function public.group_member_count();

notify pgrst, 'reload schema';
