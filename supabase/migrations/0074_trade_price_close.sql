-- ═════════════════════════════════════════════════════════════════════
-- 0074 — «اسأل عن السعر», «محجوز / اتباع», and the rating after a sale (W-02, W-09)
--   1. listing_price_ask(id, line, qty, note, from_slug): asking the price of an open listing (not one's own, not reserved, not
--      someone blocked either way). When the asker acts for a company and the listing was posted by a company → a 'quote'
--      request in the deals engine (deal_create), linked to the listing and the line, which the seller answers with a price.
--      Otherwise → a message to the lister naming the listing and the item, and a 'price_ask' notice. One inquiry is counted.
--      At most 30 asks an hour a member.
--   2. listing_quote (0054) answers only an open request — not a reserved one.
--   3. listing_close(id, outcome, counterpart, note) — the owner only: 'reserved' (محجوز: shown with its badge, quotes and price
--      asks closed), 'reopen' (back to open), 'withdrawn' (closed), 'sold' (closed, closed_reason 'sold', and a trade_outcomes row
--      naming the member it was sold to / bought from — chosen among those who wrote, asked or quoted on it: listing_counterparts —
--      or nobody). The counterpart is asked to confirm and rate (trade_outcome_confirm); the poster may rate them back
--      (trade_outcome_rate). A confirmed sale between two companies is also recorded in the deals engine (a 'quote' deal, closed,
--      with the counterpart's stars) so it counts in the company's track record (0021).
--   4. trade_record(member): confirmed sales and purchases and the stars received — for the trade profile (trust session).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- deals that name a listing (quotes on a request, price asks, recorded sales) are found by it
create index if not exists idx_deals_listing on public.deals ((lines ->> 'listing_id')) where (lines ->> 'listing_id') is not null;

-- ── 1. ask the price ────
create or replace function public.listing_price_ask(p_id bigint, p_line bigint default null, p_qty text default null, p_note text default null, p_from_slug text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; l public.listing_lines; v_from public.companies; v_to public.companies; d public.deals; mid bigint;
        item text; qty text := nullif(left(btrim(coalesce(p_qty, '')), 60), ''); note text := nullif(left(btrim(coalesce(p_note, '')), 500), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and active;
  if p.id is null then raise exception 'This listing is not available any more' using errcode = 'P0002'; end if;
  if p.status = 'reserved' then raise exception 'This listing is reserved — the seller is not taking price requests now' using errcode = '42501'; end if;
  if p.user_id = me then raise exception 'This is your own listing' using errcode = '22023'; end if;
  if exists (select 1 from public.user_blocks b where (b.blocker = p.user_id and b.blocked = me) or (b.blocker = me and b.blocked = p.user_id)) then
    raise exception 'You cannot message this member' using errcode = '42501';
  end if;
  if (select count(*) from public.notifications n where n.from_user = me and n.type = 'price_ask' and n.created_at > now() - interval '1 hour')
     + (select count(*) from public.deals x where x.from_user = me and x.type = 'quote' and x.lines ? 'price_ask' and x.created_at > now() - interval '1 hour') >= 30 then
    raise exception 'Too many price requests in one hour — please try again later' using errcode = '42501';
  end if;
  if (select count(*) from public.notifications n where n.user_id = p.user_id and n.from_user = me and n.type = 'price_ask' and n.data ->> 'listing' = p.id::text
        and n.created_at > now() - interval '1 day') >= 3 then
    raise exception 'You already asked this seller three times today — wait for the answer in Messages' using errcode = '42501';
  end if;
  if p_line is not null then
    select * into l from public.listing_lines where id = p_line and listing_id = p.id;
    if l.id is null then raise exception 'This item is not on the listing' using errcode = 'P0002'; end if;
  end if;
  item := coalesce(l.name || coalesce(' ' || l.strength, '') || coalesce(' ' || l.form, ''), p.name);
  insert into public.listing_inquiries (listing_id, user_id) values (p.id, me) on conflict do nothing;
  -- company to company: a quote request in Requests & deals
  if p_from_slug is not null and p.company_id is not null then
    select * into v_from from public.companies where slug = p_from_slug;
    select * into v_to from public.companies where id = p.company_id;
    if v_from.id is not null and public.is_company_member(v_from.id) and v_from.id <> v_to.id and v_from.status <> 'suspended'
       and v_to.status <> 'suspended' and v_to.owner_id is not null then
      d := public.deal_create('quote', v_to.slug, v_from.slug, left('Price request: ' || item, 200),
             jsonb_build_object('product', item, 'qty', coalesce(qty, ''), 'listing_id', p.id, 'line', l.id, 'price_ask', true),
             coalesce(note, 'Price request from the Marketplace'));
      return jsonb_build_object('kind', 'deal', 'ref', d.ref);
    end if;
  end if;
  -- person to person: a message naming the listing and the item, and a notice
  insert into public.messages (sender_id, receiver_id, body)
  values (me, p.user_id, left('Price request: ' || item || ' (listing #' || p.id || ')' || coalesce(chr(10) || 'Quantity: ' || qty, '') || coalesce(chr(10) || note, ''), 3900))
  returning id into mid;
  insert into public.notifications (user_id, type, from_user, message, data)
  values (p.user_id, 'price_ask', me, left('Price request: ' || item, 300), jsonb_build_object('listing', p.id, 'line', l.id, 'name', left(item, 200), 'qty', qty, 'message', mid));
  return jsonb_build_object('kind', 'message', 'id', mid);
end $$;
revoke all on function public.listing_price_ask(bigint, bigint, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_price_ask(bigint, bigint, text, text, text) to authenticated, service_role;

-- ── 2. quotes answer an open request only (0054, with status = 'active') ────
create or replace function public.listing_quote(p_id bigint, p_from_slug text, p_price text, p_qty text default null, p_lead text default null, p_note text default null)
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p record; v_sup public.companies; v_buyer bigint; d public.deals; v_price text := nullif(left(trim(coalesce(p_price, '')), 60), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and active and type = 'demand';
  if p.id is null then raise exception 'This request is not open any more' using errcode = 'P0002'; end if;
  if p.status = 'reserved' then raise exception 'This request is reserved — the buyer is not taking quotes now' using errcode = '42501'; end if;
  if v_price is null or v_price !~ '\d' then raise exception 'Enter your price' using errcode = '22023'; end if;
  select * into v_sup from public.companies where slug = p_from_slug;
  if v_sup.id is null or not public.is_company_member(v_sup.id) then raise exception 'Quote on behalf of a company you belong to — create or claim your company page first' using errcode = '42501'; end if;
  if v_sup.status = 'suspended' then raise exception 'Your company is suspended and cannot send quotes' using errcode = '42501'; end if;
  if p.user_id = me then raise exception 'This is your own request' using errcode = '22023'; end if;
  v_buyer := coalesce(p.company_id, (select c.id from public.companies c where c.owner_id = p.user_id and c.status <> 'suspended' order by c.created_at limit 1),
                      (select m.company_id from public.company_members m where m.user_id = p.user_id and m.accepted order by m.created_at limit 1));
  if v_buyer is null then raise exception 'This buyer has no company page yet — message them instead' using errcode = '22023'; end if;
  if v_buyer = v_sup.id then raise exception 'You cannot quote to your own company' using errcode = '22023'; end if;
  if exists (select 1 from public.deals x where x.to_company_id = v_sup.id and x.lines ->> 'listing_id' = p.id::text and x.status in ('quoted', 'countered', 'sent')) then
    raise exception 'Your company has already quoted on this request — revise it in Requests & deals' using errcode = '23505';
  end if;
  if (select count(*) from public.deal_events e where e.actor = me and e.created_at > now() - interval '1 hour') >= 60 then
    raise exception 'Too many actions in one hour — please try again later' using errcode = '42501';
  end if;
  insert into public.deals (type, title, from_company_id, from_user, to_company_id, lines, status, offer, offer_at, assignee)
  values ('quote', left(p.name, 200), v_buyer, p.user_id, v_sup.id,
          jsonb_build_object('product', p.name, 'qty', coalesce(nullif(trim(p_qty), ''), p.moq, ''), 'listing_id', p.id),
          'quoted', jsonb_build_object('price', v_price, 'validity', '14 days', 'lead', coalesce(left(trim(p_lead), 60), ''), 'note', coalesce(left(trim(p_note), 500), '')), now(), me)
  returning * into d;
  insert into public.deal_events (deal_id, side, action, note, actor) values (d.id, 'from', 'sent', 'Request posted in the Marketplace: ' || p.name, p.user_id);
  insert into public.deal_events (deal_id, side, action, note, actor, data)
  values (d.id, 'to', 'quote', 'Send quote: ' || v_price || coalesce(' · lead time ' || nullif(trim(p_lead), ''), '') || coalesce(' — ' || nullif(trim(p_note), ''), ''), me,
          jsonb_build_object('price', v_price, 'lead', coalesce(p_lead, ''), 'note', coalesce(p_note, '')));
  insert into public.notifications (user_id, type, from_user, message) values (p.user_id, 'deal', me, left(v_sup.name || ': Send quote — ' || p.name, 300));
  return d.ref;
end $$;
revoke all on function public.listing_quote(bigint, text, text, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_quote(bigint, text, text, text, text, text) to authenticated, service_role;

-- ── 3. reserved / sold ────
create table if not exists public.trade_outcomes (
  id                bigint generated always as identity primary key,
  listing_id        bigint references public.products(id) on delete set null,
  listing_name      text not null,
  listing_type      text not null check (listing_type in ('supply', 'demand')),
  poster            uuid not null references public.profiles(id) on delete cascade,
  counterpart       uuid references public.profiles(id) on delete set null,
  status            text not null default 'pending' check (status in ('pending', 'confirmed', 'declined', 'none')),
  note              text check (length(note) <= 500),
  counterpart_stars smallint check (counterpart_stars between 1 and 5),     -- the counterpart's rating of the poster
  counterpart_note  text check (length(counterpart_note) <= 500),
  poster_stars      smallint check (poster_stars between 1 and 5),          -- the poster's rating of the counterpart
  poster_note       text check (length(poster_note) <= 500),
  deal_id           bigint references public.deals(id) on delete set null,
  created_at        timestamptz not null default now(),
  confirmed_at      timestamptz);
create index if not exists idx_trade_outcomes_poster on public.trade_outcomes (poster, created_at desc);
create index if not exists idx_trade_outcomes_counterpart on public.trade_outcomes (counterpart, created_at desc);
create index if not exists idx_trade_outcomes_listing on public.trade_outcomes (listing_id);
create index if not exists idx_trade_outcomes_deal on public.trade_outcomes (deal_id);
alter table public.trade_outcomes enable row level security;
do $$ begin
  create policy "trade outcomes: the two members read" on public.trade_outcomes for select to authenticated
    using (poster = (select auth.uid()) or counterpart = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on public.trade_outcomes from public, anon, authenticated;
grant select on public.trade_outcomes to anon, authenticated;      -- writes only through the functions below
grant all on public.trade_outcomes to service_role;
revoke all on sequence public.trade_outcomes_id_seq from public, anon, authenticated, service_role;
grant usage, select, update on sequence public.trade_outcomes_id_seq to authenticated, service_role;

-- who may be named as the other side of a sale: members who wrote about it, asked its price, or quoted / were quoted on it
create or replace function public.listing_counterparts(p_id bigint) returns jsonb language sql stable security definer set search_path = public as $$
  with p as (select * from public.products where id = p_id and user_id = auth.uid()),
  ids as (
    select i.user_id as uid from public.listing_inquiries i, p where i.listing_id = p.id
    union select coalesce(d.assignee, d.from_user) from public.deals d, p where d.lines ->> 'listing_id' = p.id::text and d.from_user = p.user_id      -- suppliers who quoted on my request
    union select d.from_user from public.deals d, p where d.lines ->> 'listing_id' = p.id::text and d.from_user <> p.user_id)                         -- buyers who asked through a company
  select coalesce(jsonb_agg(jsonb_build_object('id', pr.id, 'name', pr.name, 'company', pr.company) order by pr.name), '[]')
    from ids join public.profiles pr on pr.id = ids.uid, p
   where ids.uid is not null and ids.uid <> p.user_id and pr.account_type is distinct from 'deleted'
$$;
revoke all on function public.listing_counterparts(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_counterparts(bigint) to authenticated, service_role;

create or replace function public.listing_close(p_id bigint, p_outcome text, p_counterpart uuid default null, p_note text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; o public.trade_outcomes;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and user_id = me for update;
  if p.id is null then raise exception 'Only the listing''s owner can do this' using errcode = '42501'; end if;
  if p_outcome = 'reserved' then
    if p.status <> 'active' then raise exception 'Only an open listing can be reserved' using errcode = '22023'; end if;
    update public.products set status = 'reserved' where id = p.id;
  elsif p_outcome = 'reopen' then
    if p.status <> 'reserved' then raise exception 'This listing is not reserved' using errcode = '22023'; end if;
    update public.products set status = 'active' where id = p.id;
  elsif p_outcome = 'withdrawn' then
    if p.status in ('closed', 'draft') then raise exception 'This listing is not open' using errcode = '22023'; end if;
    update public.products set status = 'closed', closed_reason = 'withdrawn' where id = p.id;
  elsif p_outcome = 'sold' then
    if p.status not in ('active', 'reserved', 'paused') then raise exception 'This listing is not open' using errcode = '22023'; end if;
    if p_counterpart is not null and not exists (select 1 from jsonb_array_elements(public.listing_counterparts(p.id)) x where x ->> 'id' = p_counterpart::text) then
      raise exception 'Choose someone who wrote to you, asked the price or quoted on this listing' using errcode = '22023';
    end if;
    update public.products set status = 'closed', closed_reason = 'sold' where id = p.id;
    insert into public.trade_outcomes (listing_id, listing_name, listing_type, poster, counterpart, status, note)
    values (p.id, left(p.name, 200), p.type, me, p_counterpart, case when p_counterpart is null then 'none' else 'pending' end, nullif(left(btrim(coalesce(p_note, '')), 500), ''))
    returning * into o;
    if p_counterpart is not null then
      insert into public.notifications (user_id, type, from_user, message, data)
      values (p_counterpart, 'trade_outcome', me, left(case when p.type = 'supply' then 'Did you buy “' else 'Did you sell “' end || p.name || '”? Confirm and rate', 300),
              jsonb_build_object('outcome', o.id, 'listing', p.id, 'name', left(p.name, 200), 'ask', 'confirm', 'side', case when p.type = 'supply' then 'buyer' else 'seller' end));
    end if;
    return jsonb_build_object('status', 'closed', 'outcome', o.id);
  else
    raise exception 'Unknown step' using errcode = '22023';
  end if;
  return jsonb_build_object('status', (select status from public.products where id = p.id));
end $$;
revoke all on function public.listing_close(bigint, text, uuid, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_close(bigint, text, uuid, text) to authenticated, service_role;

-- the other side confirms (with stars) or says it did not happen
create or replace function public.trade_outcome_confirm(p_id bigint, p_yes boolean, p_stars int default null, p_note text default null, p_from_slug text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); o public.trade_outcomes; p public.products; v_mine public.companies; v_their bigint; d public.deals; seller_co bigint; buyer_co bigint;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into o from public.trade_outcomes where id = p_id for update;
  if o.id is null or o.counterpart is distinct from me then raise exception 'This sale does not name you' using errcode = '42501'; end if;
  if o.status <> 'pending' then raise exception 'You already answered' using errcode = '22023'; end if;
  if not coalesce(p_yes, false) then
    update public.trade_outcomes set status = 'declined', confirmed_at = now() where id = o.id;
    insert into public.notifications (user_id, type, from_user, message, data)
    values (o.poster, 'trade_outcome', me, left('Not confirmed: ' || o.listing_name, 300), jsonb_build_object('outcome', o.id, 'listing', o.listing_id, 'name', o.listing_name, 'answer', 'declined'));
    return jsonb_build_object('status', 'declined');
  end if;
  if p_stars is null or p_stars not between 1 and 5 then raise exception 'Rating must be 1 to 5 stars' using errcode = '22023'; end if;
  update public.trade_outcomes set status = 'confirmed', confirmed_at = now(), counterpart_stars = p_stars, counterpart_note = nullif(left(btrim(coalesce(p_note, '')), 500), '')
   where id = o.id returning * into o;
  -- two companies: the sale also counts in the deals engine (closed, with the stars), never between related companies
  select * into p from public.products where id = o.listing_id;
  if p_from_slug is not null and p.company_id is not null then
    select * into v_mine from public.companies where slug = p_from_slug;
    v_their := p.company_id;
    if v_mine.id is not null and public.is_company_member(v_mine.id) and v_mine.id <> v_their
       and not exists (select 1 from public.company_members a join public.company_members b on b.user_id = a.user_id where a.company_id = v_mine.id and a.accepted and b.company_id = v_their and b.accepted) then
      seller_co := case when o.listing_type = 'supply' then v_their else v_mine.id end;
      buyer_co := case when o.listing_type = 'supply' then v_mine.id else v_their end;
      insert into public.deals (type, title, from_company_id, from_user, to_company_id, lines, status, offer, offer_at, assignee, ontime)
      values ('quote', left(o.listing_name, 200), buyer_co, case when o.listing_type = 'supply' then me else o.poster end, seller_co,
              jsonb_build_object('product', o.listing_name, 'listing_id', o.listing_id, 'outcome', o.id), 'closed',
              jsonb_build_object('price', 'agreed in the Marketplace', 'validity', 'agreed', 'terms', ''), now(),
              case when o.listing_type = 'supply' then o.poster else me end, true)
      returning * into d;
      insert into public.deal_events (deal_id, side, action, note, actor) values
        (d.id, 'from', 'sent', 'Marketplace sale recorded: ' || o.listing_name, case when o.listing_type = 'supply' then me else o.poster end),
        (d.id, 'to', 'deliver', 'Sold through the Marketplace (confirmed by both sides)', case when o.listing_type = 'supply' then o.poster else me end);
      -- the buyer's stars rate the seller (the deals engine rates from the buyer's side)
      if o.listing_type = 'supply' then
        insert into public.deal_events (deal_id, side, action, note, actor, data) values (d.id, 'from', 'rate', coalesce(o.counterpart_note, ''), me, jsonb_build_object('stars', p_stars));
      end if;
      update public.trade_outcomes set deal_id = d.id where id = o.id;
    end if;
  end if;
  insert into public.notifications (user_id, type, from_user, message, data)
  values (o.poster, 'trade_outcome', me, left('Confirmed with ' || p_stars || '★: ' || o.listing_name || ' — rate them back', 300),
          jsonb_build_object('outcome', o.id, 'listing', o.listing_id, 'name', o.listing_name, 'answer', 'confirmed', 'ask', 'rate'));
  return jsonb_build_object('status', 'confirmed', 'deal', d.ref);
end $$;
revoke all on function public.trade_outcome_confirm(bigint, boolean, int, text, text) from public, anon, authenticated, service_role;
grant execute on function public.trade_outcome_confirm(bigint, boolean, int, text, text) to authenticated, service_role;

create or replace function public.trade_outcome_rate(p_id bigint, p_stars int, p_note text default null) returns jsonb language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); o public.trade_outcomes;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into o from public.trade_outcomes where id = p_id for update;
  if o.id is null or o.poster is distinct from me then raise exception 'Only the member who posted the listing rates here' using errcode = '42501'; end if;
  if o.status <> 'confirmed' then raise exception 'The other side has not confirmed this sale' using errcode = '22023'; end if;
  if o.poster_stars is not null then raise exception 'You already rated' using errcode = '22023'; end if;
  if p_stars is null or p_stars not between 1 and 5 then raise exception 'Rating must be 1 to 5 stars' using errcode = '22023'; end if;
  update public.trade_outcomes set poster_stars = p_stars, poster_note = nullif(left(btrim(coalesce(p_note, '')), 500), '') where id = o.id;
  -- a request (demand) closed as bought: the poster is the buyer, so their stars rate the seller in the deals engine too
  if o.deal_id is not null and o.listing_type = 'demand' then
    insert into public.deal_events (deal_id, side, action, note, actor, data) values (o.deal_id, 'from', 'rate', coalesce(nullif(btrim(coalesce(p_note, '')), ''), ''), me, jsonb_build_object('stars', p_stars));
  end if;
  insert into public.notifications (user_id, type, from_user, message, data)
  values (o.counterpart, 'trade_outcome', me, left('Rated you ' || p_stars || '★: ' || o.listing_name, 300), jsonb_build_object('outcome', o.id, 'listing', o.listing_id, 'name', o.listing_name, 'answer', 'rated'));
  return jsonb_build_object('status', 'rated');
end $$;
revoke all on function public.trade_outcome_rate(bigint, int, text) from public, anon, authenticated, service_role;
grant execute on function public.trade_outcome_rate(bigint, int, text) to authenticated, service_role;

-- my sales and purchases (both sides), newest first
create or replace function public.my_trade_outcomes() returns jsonb language sql stable security invoker set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'listing_id', o.listing_id, 'name', o.listing_name, 'type', o.listing_type, 'status', o.status,
           'mine', o.poster = auth.uid(), 'other', (select jsonb_build_object('id', pr.id, 'name', pr.name) from public.profiles pr where pr.id = case when o.poster = auth.uid() then o.counterpart else o.poster end),
           'stars_given', case when o.poster = auth.uid() then o.poster_stars else o.counterpart_stars end,
           'stars_got', case when o.poster = auth.uid() then o.counterpart_stars else o.poster_stars end, 'at', o.created_at) order by o.created_at desc), '[]')
  from (select * from public.trade_outcomes where poster = auth.uid() or counterpart = auth.uid() order by created_at desc limit 100) o
$$;
revoke all on function public.my_trade_outcomes() from public, anon, authenticated, service_role;
grant execute on function public.my_trade_outcomes() to authenticated, service_role;

-- ── 4. a member's trade record (confirmed by the other side only) ────
create or replace function public.trade_record(p_user uuid) returns jsonb language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else jsonb_build_object(
    'confirmed', (select count(*) from public.trade_outcomes o where o.status = 'confirmed' and (o.poster = p_user or o.counterpart = p_user)),
    'stars', (select round(avg(s), 1) from (select o.counterpart_stars s from public.trade_outcomes o where o.poster = p_user and o.status = 'confirmed' and o.counterpart_stars is not null
                                           union all select o.poster_stars from public.trade_outcomes o where o.counterpart = p_user and o.status = 'confirmed' and o.poster_stars is not null) x),
    'ratings', (select count(*) from (select 1 from public.trade_outcomes o where o.poster = p_user and o.status = 'confirmed' and o.counterpart_stars is not null
                                      union all select 1 from public.trade_outcomes o where o.counterpart = p_user and o.status = 'confirmed' and o.poster_stars is not null) x)) end
$$;
revoke all on function public.trade_record(uuid) from public, anon, authenticated, service_role;
grant execute on function public.trade_record(uuid) to authenticated, service_role;

notify pgrst, 'reload schema';
