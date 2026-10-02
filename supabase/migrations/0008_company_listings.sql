-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 0008 — company listings and group buying (step C3)
-- Surplus and dossier listings; group buying on the deals engine (members, join, target reached);
-- the supplier's confirmation creates one accepted order per member IN THE DATABASE (no one can create
-- orders in another company's name from a browser); questionnaire approval adds the supplier to the AVL.
-- ═════════════════════════════════════════════════════════════════════════════

-- 1. listings: surplus stock and dossiers for licensing / sale
create table if not exists public.company_listings (
  id          bigint generated always as identity primary key,
  ref         text not null unique default ('L' || substr(md5(random()::text || clock_timestamp()::text), 1, 8)),
  company_id  bigint not null references public.companies(id) on delete cascade,
  kind        text   not null check (kind in ('surplus','dossier')),
  product     text   not null check (length(product) between 2 and 200),
  qty         text, batch text, expiry text, price text,
  off         int    check (off between 0 and 95),
  reg_status  text,  markets text, deal_kind text,
  active      boolean not null default true,
  created_by  uuid references public.profiles(id) on delete set null,
  created_at  timestamptz not null default now()
);
create index if not exists idx_listings_kind on public.company_listings (kind, created_at desc) where active;
create index if not exists idx_listings_company on public.company_listings (company_id);
alter table public.company_listings enable row level security;
do $$ begin
  create policy "listings: everyone reads active" on public.company_listings for select using (active or public.is_company_member(company_id));
  create policy "listings: the company's sales/regulatory team posts" on public.company_listings for insert
    with check (public.is_company_member(company_id, array['owner','admin','sales','regulatory']) and created_by = (select auth.uid()));
  create policy "listings: the company's team edits" on public.company_listings for update
    using (public.is_company_member(company_id, array['owner','admin','sales','regulatory'])) with check (public.is_company_member(company_id, array['owner','admin','sales','regulatory']));
  create policy "listings: owners/admins delete" on public.company_listings for delete using (public.is_company_member(company_id, array['owner','admin']));
exception when duplicate_object then null; end $$;

-- 2. the demo's AVL statuses
alter table public.approved_suppliers drop constraint if exists approved_suppliers_status_check;
do $$ begin
  alter table public.approved_suppliers add constraint approved_suppliers_status_check check (status in ('approved','conditional','evaluation','suspended','blocked'));
exception when duplicate_object then null; end $$;

-- 3. group buying: members and their shares; group orders are open to every company
alter table public.deal_events drop constraint if exists deal_events_side_check;
do $$ begin
  alter table public.deal_events add constraint deal_events_side_check check (side in ('from','to','member','system'));
exception when duplicate_object then null; end $$;
alter table public.deals add column if not exists group_of bigint references public.deals(id) on delete set null;
create table if not exists public.deal_members (
  deal_id    bigint not null references public.deals(id) on delete cascade,
  company_id bigint not null references public.companies(id) on delete cascade,
  qty        numeric not null check (qty > 0),
  joined_at  timestamptz not null default now(),
  primary key (deal_id, company_id)
);
alter table public.deal_members enable row level security;
do $$ begin
  create policy "deals: group orders are open to all" on public.deals for select using (type = 'group');
  create policy "deal members: readable with the deal" on public.deal_members for select using (exists (select 1 from public.deals d where d.id = deal_id));
exception when duplicate_object then null; end $$;
revoke insert, update, delete on public.deal_members from anon, authenticated;

create or replace function public.deal_join(p_ref text, p_from_slug text, p_qty numeric)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; v public.companies; total numeric; by_date date;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref for update;
  if d.id is null or d.type <> 'group' then raise exception 'Buying group not found' using errcode = 'P0002'; end if;
  if d.status <> 'open' then raise exception 'This buying group is closed' using errcode = '42501'; end if;
  if coalesce(p_qty, 0) <= 0 then raise exception 'Enter a quantity greater than zero' using errcode = '22023'; end if;
  begin by_date := (d.lines ->> 'by')::date; exception when others then by_date := null; end;
  if by_date is not null and by_date < current_date then raise exception 'This buying group closed on %', by_date using errcode = '42501'; end if;
  select * into v from public.companies where slug = p_from_slug;
  if v.id is null or not public.is_company_member(v.id) then raise exception 'You can join only on behalf of a company you belong to' using errcode = '42501'; end if;
  if v.id = d.to_company_id then raise exception 'The supplier cannot join its own buying group' using errcode = '42501'; end if;
  insert into public.deal_members as m (deal_id, company_id, qty) values (d.id, v.id, floor(p_qty))
    on conflict (deal_id, company_id) do update set qty = m.qty + floor(p_qty);
  insert into public.deal_events (deal_id, side, action, note, actor)
    values (d.id, 'member', 'join', v.name || ' joined with ' || floor(p_qty)::text || ' ' || coalesce(d.lines ->> 'unit', ''), me);
  select sum(qty) into total from public.deal_members where deal_id = d.id;
  if total >= coalesce((d.lines ->> 'target')::numeric, 0) and coalesce((d.lines ->> 'target')::numeric, 0) > 0 then
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
revoke all on function public.deal_join(text, text, numeric) from public, anon;
grant execute on function public.deal_join(text, text, numeric) to authenticated;

-- 4. deal_act: as in 0007, plus the database-side effects of confirming a group and approving a questionnaire
create or replace function public.deal_act(p_ref text, p_action text, p_data jsonb default '{}'::jsonb, p_side text default null)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; side text; allowed jsonb; days int; nxt text; notify uuid; mb record; o public.deals;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref for update;
  if d.id is null then raise exception 'Request not found' using errcode = 'P0002'; end if;
  if p_side = 'to' and public.is_company_member(d.to_company_id) then side := 'to';
  elsif p_side = 'from' and (d.from_user = me or (d.from_company_id is not null and public.is_company_member(d.from_company_id))) then side := 'from';
  elsif p_side is null and public.is_company_member(d.to_company_id) then side := 'to';
  elsif p_side is null and (d.from_user = me or (d.from_company_id is not null and public.is_company_member(d.from_company_id))) then side := 'from';
  else raise exception 'You are not part of this request' using errcode = '42501'; end if;
  allowed := public.deal_flow() -> d.type -> 'acts' -> d.status -> side;
  if allowed is null or not (allowed ? p_action) then raise exception 'That step is not available now' using errcode = '42501'; end if;
  if p_action = 'accept' and d.offer is not null and d.offer_at is not null then
    days := substring(coalesce(d.offer ->> 'validity', '') from '(\d+)\s*day')::int;
    if days is not null and d.offer_at + make_interval(days => days) < now() then
      raise exception 'This offer expired — ask for a new quote (counter-offer)' using errcode = '42501';
    end if;
  end if;
  nxt := public.deal_next_status(d.type, p_action);
  p_data := coalesce(p_data, '{}'::jsonb);
  if p_action in ('quote','revise','propose') then
    d.offer := jsonb_build_object('price', p_data ->> 'price', 'validity', coalesce(p_data ->> 'validity', '14 days'), 'terms', coalesce(p_data ->> 'terms', d.lines ->> 'inc', ''),
                                  'lead', coalesce(p_data ->> 'lead', p_data ->> 'timeline', ''), 'note', coalesce(p_data ->> 'note', ''));
    d.offer_at := now();
  elsif p_action in ('counter','counter_offer') then d.counter := jsonb_build_object('price', p_data ->> 'price', 'note', coalesce(p_data ->> 'note', ''));
  elsif p_action = 'accept_counter' and d.counter is not null then d.offer := jsonb_build_object('price', d.counter ->> 'price', 'validity', '7 days', 'terms', coalesce(d.lines ->> 'inc', '')); d.offer_at := now();
  elsif p_action = 'accept_offer' then d.offer := jsonb_build_object('price', d.lines ->> 'price', 'validity', 'agreed', 'terms', coalesce(d.lines ->> 'inc', 'EXW'));
  elsif p_action = 'answer' then d.answers := coalesce(p_data -> 'answers', d.answers);
  elsif p_action = 'receive' then d.ontime := coalesce(p_data ->> 'ontime', 'yes') <> 'no';
  elsif p_action = 'rate' then
    if coalesce((p_data ->> 'stars')::int, 0) not between 1 and 5 then raise exception 'Rating must be 1 to 5 stars' using errcode = '22023'; end if;
  end if;
  update public.deals set status = nxt, offer = d.offer, offer_at = d.offer_at, counter = d.counter, answers = d.answers, ontime = d.ontime, updated_at = now()
   where id = d.id returning * into d;
  insert into public.deal_events (deal_id, side, action, note, data, actor) values (d.id, side, p_action, coalesce(p_data ->> 'note', p_data ->> 'text', ''), p_data, me);
  -- the supplier confirmed the pooled price → one order per member, already accepted at the group price
  if d.type = 'group' and p_action = 'confirm_group' then
    for mb in select m.company_id, m.qty, c.name from public.deal_members m join public.companies c on c.id = m.company_id where m.deal_id = d.id loop
      insert into public.deals (type, title, from_company_id, from_user, to_company_id, lines, status, offer, offer_at, group_of, assignee)
      values ('quote', coalesce(d.lines ->> 'product', d.title) || ' — ' || mb.qty::text || ' ' || coalesce(d.lines ->> 'unit', '') || ' (group order)',
              mb.company_id, coalesce((select owner_id from public.companies where id = mb.company_id), d.from_user), d.to_company_id,
              jsonb_build_object('qty', mb.qty, 'unit', d.lines ->> 'unit', 'inc', coalesce(d.lines ->> 'inc', 'EXW')), 'accepted',
              jsonb_build_object('price', d.lines ->> 'price', 'validity', 'group price', 'terms', coalesce(d.lines ->> 'inc', 'EXW')), now(), d.id, d.assignee)
      returning * into o;
      insert into public.deal_events (deal_id, side, action, note, actor) values (o.id, 'from', 'sent', 'Share in group ' || d.title, me),
                                                                                 (o.id, 'to', 'accept', 'Group price confirmed: ' || coalesce(d.lines ->> 'price', ''), me);
      insert into public.notifications (user_id, type, from_user, message) select o.from_user, 'deal', me, o.title where o.from_user <> me;
    end loop;
  end if;
  -- an approved qualification questionnaire puts the supplier on the buyer's approved list
  if d.type = 'questionnaire' and p_action = 'approve' and d.from_company_id is not null then
    insert into public.approved_suppliers (buyer_company_id, supplier_company_id, status, note, updated_at)
    values (d.from_company_id, d.to_company_id, 'approved', 'Qualification questionnaire ' || d.ref, now())
    on conflict (buyer_company_id, supplier_company_id) do update set status = 'approved', note = excluded.note, updated_at = now();
  end if;
  notify := case when side = 'to' then d.from_user else coalesce(d.assignee, public.deal_receiver(d.to_company_id, d.type)) end;
  if notify is not null and notify <> me then
    insert into public.notifications (user_id, type, from_user, message) values (notify, 'deal', me, d.title || ' — ' || replace(p_action, '_', ' '));
  end if;
  return d;
end $$;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
