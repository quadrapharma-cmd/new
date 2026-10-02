-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 0007 — deals engine (step C2)
-- The demo's flows (who may do what at each stage) are enforced HERE, in the database:
-- a step out of turn, by the wrong side, on an expired offer, or with your own company is refused
-- however it is called. Deals change only through deal_create() and deal_act().
-- ═════════════════════════════════════════════════════════════════════════════
create table if not exists public.deals (
  id              bigint generated always as identity primary key,
  ref             text not null unique default ('D' || substr(md5(random()::text || clock_timestamp()::text), 1, 8)),
  type            text not null check (type in ('quote','service','surplus','questionnaire','dossier','job','group')),
  title           text not null check (length(title) between 2 and 200),
  from_company_id bigint references public.companies(id) on delete cascade,
  from_user       uuid   not null references public.profiles(id) on delete cascade,
  to_company_id   bigint not null references public.companies(id) on delete cascade,
  lines           jsonb  not null default '{}'::jsonb,
  status          text   not null,
  offer           jsonb,
  counter         jsonb,
  answers         jsonb,
  ontime          boolean,
  group_key       text,
  assignee        uuid references public.profiles(id) on delete set null,
  offer_at        timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (from_company_id is null or from_company_id <> to_company_id),      -- no dealing with your own company
  check (type = 'job' or from_company_id is not null)                        -- only job applications come from a person
);
create index if not exists idx_deals_to on public.deals (to_company_id, updated_at desc);
create index if not exists idx_deals_from on public.deals (from_company_id, updated_at desc);
create index if not exists idx_deals_user on public.deals (from_user, updated_at desc);
create index if not exists idx_deals_group on public.deals (group_key) where group_key is not null;

create table if not exists public.deal_events (
  id         bigint generated always as identity primary key,
  deal_id    bigint not null references public.deals(id) on delete cascade,
  side       text   not null check (side in ('from','to')),
  action     text   not null,
  note       text,
  data       jsonb  not null default '{}'::jsonb,
  actor      uuid   references public.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);
create index if not exists idx_deal_events_deal on public.deal_events (deal_id, id);

-- the demo's FLOWS and NEXT tables, as data
create or replace function public.deal_flow() returns jsonb language sql immutable as $$ select '{
  "quote":   {"first":"sent","acts":{"sent":{"to":["quote","decline"],"from":["cancel"]},"quoted":{"from":["accept","counter","decline"],"to":["revise"]},"countered":{"to":["quote","decline"],"from":["cancel"]},"accepted":{"to":["confirm"]},"confirmed":{"to":["ship"]},"shipped":{"from":["receive"]},"delivered":{"from":["rate"]}}},
  "service": {"first":"sent","acts":{"sent":{"to":["propose","decline"],"from":["cancel"]},"proposed":{"from":["accept","decline"]},"accepted":{"to":["start"]},"in_progress":{"to":["deliver"]},"delivered":{"from":["rate"]}}},
  "surplus": {"first":"offered","acts":{"offered":{"to":["accept_offer","counter_offer","decline"],"from":["cancel"]},"countered":{"from":["accept_counter","decline"]},"accepted":{"to":["confirm"]},"confirmed":{"to":["ship"]},"shipped":{"from":["receive"]},"delivered":{"from":["rate"]}}},
  "questionnaire": {"first":"sent","acts":{"sent":{"to":["answer"]},"answered":{"from":["approve","reject"]}}},
  "dossier": {"first":"requested","acts":{"requested":{"to":["sign_nda","decline"]},"nda_signed":{"to":["share"]},"shared":{"from":["agree","decline"],"to":["decline"]}}},
  "job":     {"first":"applied","acts":{"applied":{"to":["shortlist","reject"]},"shortlisted":{"to":["interview","reject"]},"interview":{"to":["offer","reject"]},"offer":{"from":["accept_job","decline"]}}},
  "group":   {"first":"open","acts":{"target_reached":{"to":["confirm_group","decline"]}}}
}'::jsonb $$;
create or replace function public.deal_next_status(p_type text, p_action text) returns text language sql immutable as $$
  select case when p_type = 'service' and p_action = 'accept' then 'accepted' else ('{
    "quote":"quoted","revise":"quoted","counter":"countered","accept":"accepted","confirm":"confirmed","ship":"shipped","receive":"delivered","rate":"closed",
    "decline":"declined","cancel":"cancelled","propose":"proposed","start":"in_progress","deliver":"delivered","accept_offer":"accepted","counter_offer":"countered",
    "accept_counter":"accepted","answer":"answered","approve":"approved","reject":"rejected","sign_nda":"nda_signed","share":"shared","agree":"agreed",
    "shortlist":"shortlisted","interview":"interview","offer":"offer","accept_job":"hired","confirm_group":"confirmed"}'::jsonb ->> p_action) end
$$;

-- who receives a request: the routed person for that request type, else the owner
create or replace function public.deal_receiver(p_company bigint, p_type text) returns uuid language sql stable security definer set search_path = public as $$
  select coalesce(
    (select r.user_id from public.company_routing r where r.company_id = p_company
       and r.request_type = case p_type when 'group' then 'group_order' else p_type end),
    (select c.owner_id from public.companies c where c.id = p_company),
    (select m.user_id from public.company_members m where m.company_id = p_company and m.role in ('owner','admin') order by m.created_at limit 1))
$$;

create or replace function public.deal_create(p_type text, p_to_slug text, p_from_slug text, p_title text, p_lines jsonb default '{}'::jsonb,
                                              p_message text default '', p_group text default null, p_ref text default null)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v_to public.companies; v_from public.companies; d public.deals; first text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if public.deal_flow() -> p_type is null then raise exception 'Unknown request type' using errcode = '22023'; end if;
  select * into v_to from public.companies where slug = p_to_slug and status <> 'suspended';
  if v_to.id is null then raise exception 'Company not found' using errcode = 'P0002'; end if;
  if p_type <> 'job' then
    select * into v_from from public.companies where slug = p_from_slug;
    if v_from.id is null or not public.is_company_member(v_from.id) then raise exception 'You can send this only on behalf of a company you belong to' using errcode = '42501'; end if;
    if v_from.id = v_to.id then raise exception 'You cannot send this to your own company' using errcode = '42501'; end if;
  end if;
  first := public.deal_flow() -> p_type ->> 'first';
  insert into public.deals (ref, type, title, from_company_id, from_user, to_company_id, lines, status, group_key, assignee)
  values (coalesce(nullif(p_ref, ''), 'D' || substr(md5(random()::text || clock_timestamp()::text), 1, 8)), p_type, p_title, v_from.id, me, v_to.id,
          coalesce(p_lines, '{}'::jsonb), first, p_group, public.deal_receiver(v_to.id, p_type))
  returning * into d;
  insert into public.deal_events (deal_id, side, action, note, actor) values (d.id, 'from', first, coalesce(p_message, ''), me);
  if d.assignee is not null and d.assignee <> me then
    insert into public.notifications (user_id, type, from_user, message) values (d.assignee, 'deal', me, p_title);
  end if;
  return d;
end $$;

create or replace function public.deal_act(p_ref text, p_action text, p_data jsonb default '{}'::jsonb, p_side text default null)
returns public.deals language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; side text; allowed jsonb; days int; nxt text; notify uuid;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref for update;
  if d.id is null then raise exception 'Request not found' using errcode = 'P0002'; end if;
  -- which side is the caller on? (a person can act only on a side they belong to)
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
  notify := case when side = 'to' then d.from_user else coalesce(d.assignee, public.deal_receiver(d.to_company_id, d.type)) end;
  if notify is not null and notify <> me then
    insert into public.notifications (user_id, type, from_user, message) values (notify, 'deal', me, d.title || ' — ' || replace(p_action, '_', ' '));
  end if;
  return d;
end $$;

-- a company's track record (as a supplier), from finished deals; never editable, never bought
create or replace function public.company_track_record(p_company bigint) returns json language sql stable security definer set search_path = public as $$
  with recv as (
    select d.*, (select min(e.created_at) from public.deal_events e where e.deal_id = d.id and e.side = 'to') as first_reply
    from public.deals d where d.to_company_id = p_company),
  done as (select * from recv where type in ('quote','surplus','service') and status in ('delivered','closed'))
  select json_build_object(
    'orders',    (select count(*) from done),
    'ontime',    (select round(100.0 * count(*) filter (where ontime is not false) / nullif(count(*), 0)) from done),
    'rating',    (select round(avg((e.data ->> 'stars')::numeric), 1) from public.deal_events e join recv x on x.id = e.deal_id where e.action = 'rate'),
    'reviews',   (select count(*) from public.deal_events e join recv x on x.id = e.deal_id where e.action = 'rate'),
    'response',  (select round((percentile_cont(0.5) within group (order by extract(epoch from (first_reply - created_at)) / 3600))::numeric, 1) from recv where first_reply is not null),
    'requests',  (select count(*) from recv),
    'answered',  (select count(*) from recv where first_reply is not null))
$$;

alter table public.deals enable row level security;
alter table public.deal_events enable row level security;
do $$ begin
  create policy "deals: the two sides read" on public.deals for select
    using (from_user = (select auth.uid()) or public.is_company_member(to_company_id) or (from_company_id is not null and public.is_company_member(from_company_id)));
  create policy "deal events: the two sides read" on public.deal_events for select
    using (exists (select 1 from public.deals d where d.id = deal_id));
exception when duplicate_object then null; end $$;
revoke insert, update, delete on public.deals, public.deal_events from anon, authenticated;     -- changes only through the two functions
revoke all on function public.deal_create(text, text, text, text, jsonb, text, text, text) from public, anon;
revoke all on function public.deal_act(text, text, jsonb, text) from public, anon;
grant execute on function public.deal_create(text, text, text, text, jsonb, text, text, text) to authenticated;
grant execute on function public.deal_act(text, text, jsonb, text) to authenticated;
grant execute on function public.company_track_record(bigint) to anon, authenticated;

-- the directory shows each company's real rating from rated deals
create or replace function public.directory_companies(p_limit int default 5000)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(x order by x.name), '[]'::json) from (
    select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
           c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours, c.plan, c.logo_url, c.follower_count, c.profile, c.created_at,
           public.company_tier(c.id) as tier, public.is_company_member(c.id) as mine,
           (select coalesce(json_agg(distinct s.name), '[]'::json) from public.site_certificates s where s.company_id = c.id and (s.expiry is null or s.expiry >= current_date)) as certs,
           (select coalesce(json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                   'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name), '[]'::json) from public.company_products p where p.company_id = c.id) as products,
           public.company_track_record(c.id) as track
    from public.companies c where c.status <> 'suspended'
    limit least(greatest(coalesce(p_limit, 5000), 1), 10000)) x
$$;

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
