-- ═════════════════════════════════════════════════════════════════════
-- 0057 — buying groups: change your quantity, leave, and groups that close below target (J-BUSINESS-32, 33)
--   1. deal_member_set(group, company, qty): a member company sets its quantity in an open group (0 = leave). The organiser
--      can change its own share but not leave (it withdraws the group instead). The group's progress, the target test and the
--      notifications are the database's (as deal_join, 0008/0021).
--   2. group_close_expired(group): a group still open after its closing date ("by") and below its target closes as 'expired'
--      — nobody can join any more, no orders are made, and the organiser and every member are told once. Anyone who can see
--      the group may ask; the database checks the date and the total itself (the browser asks when it shows such a group).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

create or replace function public.deal_member_set(p_ref text, p_from_slug text, p_qty numeric)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; v public.companies; q numeric := floor(p_qty); old numeric; total numeric; by_date date; tgt numeric;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref for update;
  if d.id is null or d.type <> 'group' then raise exception 'Buying group not found' using errcode = 'P0002'; end if;
  if d.status <> 'open' then raise exception 'This buying group is closed' using errcode = '42501'; end if;
  begin by_date := (d.lines ->> 'by')::date; exception when others then by_date := null; end;
  if by_date is not null and by_date < current_date then raise exception 'This buying group closed on %', by_date using errcode = '42501'; end if;
  if q is null or q = 'NaN'::numeric or not (q >= 0 and q <= 1000000000) then raise exception 'Enter a quantity (0 to leave)' using errcode = '22023'; end if;
  select * into v from public.companies where slug = p_from_slug;
  if v.id is null or not public.is_company_member(v.id) then raise exception 'You can change only the share of a company you belong to' using errcode = '42501'; end if;
  select qty into old from public.deal_members where deal_id = d.id and company_id = v.id for update;
  if old is null then raise exception 'Your company is not in this group — join it first' using errcode = 'P0002'; end if;
  if q = 0 and v.id = d.from_company_id then raise exception 'The organiser stays in its group — withdraw the group instead' using errcode = '42501'; end if;
  if q = 0 then
    delete from public.deal_members where deal_id = d.id and company_id = v.id;
    insert into public.deal_events (deal_id, side, action, note, actor) values (d.id, 'member', 'leave', v.name || ' left the group', me);
  else
    update public.deal_members set qty = q where deal_id = d.id and company_id = v.id;
    insert into public.deal_events (deal_id, side, action, note, actor)
    values (d.id, 'member', 'change', v.name || ' changed its quantity to ' || q::text || ' ' || coalesce(d.lines ->> 'unit', ''), me);
  end if;
  select coalesce(sum(qty), 0) into total from public.deal_members where deal_id = d.id;
  tgt := coalesce((d.lines ->> 'target')::numeric, 0);
  if tgt > 0 and total >= tgt then
    update public.deals set status = 'target_reached', updated_at = now() where id = d.id returning * into d;
    insert into public.deal_events (deal_id, side, action, note) values (d.id, 'system', 'target', 'Target reached (' || total::text || ' ' || coalesce(d.lines ->> 'unit', '') || ')');
    insert into public.notifications (user_id, type, from_user, message)
      select public.deal_receiver(d.to_company_id, 'group'), 'deal', me, 'Buying group reached its target: ' || d.title
      where public.deal_receiver(d.to_company_id, 'group') is not null;
  else
    update public.deals set updated_at = now() where id = d.id returning * into d;
  end if;
  return d;
end $$;
revoke all on function public.deal_member_set(text, text, numeric) from public, anon, authenticated, service_role;
grant execute on function public.deal_member_set(text, text, numeric) to authenticated, service_role;

create or replace function public.group_close_expired(p_ref text) returns text language plpgsql security definer set search_path = public as $$
declare d public.deals; by_date date; total numeric; tgt numeric;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref and type = 'group' for update;
  if d.id is null then raise exception 'Buying group not found' using errcode = 'P0002'; end if;
  if d.status <> 'open' then return d.status; end if;
  begin by_date := (d.lines ->> 'by')::date; exception when others then by_date := null; end;
  select coalesce(sum(qty), 0) into total from public.deal_members where deal_id = d.id;
  tgt := coalesce((d.lines ->> 'target')::numeric, 0);
  if by_date is null or by_date >= current_date or (tgt > 0 and total >= tgt) then return d.status; end if;
  update public.deals set status = 'expired', updated_at = now() where id = d.id;
  insert into public.deal_events (deal_id, side, action, note) values (d.id, 'system', 'expired', 'Closed on ' || by_date::text || ' below its target (' || total::text || ' of ' || tgt::text || ' ' || coalesce(d.lines ->> 'unit', '') || ') — no orders are made');
  insert into public.notifications (user_id, type, from_user, message)
    select distinct r, 'deal', null::uuid, 'Buying group closed below its target — no orders: ' || d.title
      from (select public.deal_receiver(m.company_id, 'group') as r from public.deal_members m where m.deal_id = d.id
            union select d.from_user) x where r is not null;
  return 'expired';
end $$;
revoke all on function public.group_close_expired(text) from public, anon, authenticated, service_role;
grant execute on function public.group_close_expired(text) to authenticated, service_role;

notify pgrst, 'reload schema';
