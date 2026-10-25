-- ═════════════════════════════════════════════════════════════════════
-- 0073 — publishing a trade offer: matching «عندي / محتاج», saved searches, limited renewal (W-03, W-07)
--   1. trade_matches: each pair of listings that match, kept once (a renewal never notifies again). Pairs: stock ↔ wanted,
--      materials ↔ wanted, file_sale ↔ file_wanted, toll ↔ toll_wanted, agency ↔ distributor; both open, different members who
--      do not block each other, overlapping roots (one item's words inside the other's; forms for toll; categories + a common
--      governorate for agency / distributor). The other side's owner gets a 'trade_match' notice (at most 50 a publication),
--      the poster one summary. my_trade_matches() lists them.
--   2. When a listing goes live the first time (inserted active, or a draft published): matching, the marketplace saved
--      searches on canonical words (replaces the substring check of 0043 for listings), the company's followers for a published
--      draft (0058 told them only for listings inserted active). published_at is set by the database.
--   3. listing_renew: free once every 7 days a listing — it moves the listing up (bumped_at) and extends it; sooner → the error
--      names the date (the page offers «ميّز إعلانك», the paid Boost / Featured). A sold listing is not renewed.
--   4. 'trade_match', 'price_ask' and 'trade_outcome' notices join the e-mail outbox kinds (0059).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. pairs ────
create table if not exists public.trade_matches (
  a          bigint not null references public.products(id) on delete cascade,
  b          bigint not null references public.products(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (a, b),
  constraint trade_matches_order check (a < b));
create index if not exists idx_trade_matches_b on public.trade_matches (b);
alter table public.trade_matches enable row level security;
do $$ begin
  create policy "trade matches: the owners of either listing read" on public.trade_matches for select to authenticated
    using (exists (select 1 from public.products p where p.id in (a, b) and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
revoke all on public.trade_matches from public, anon, authenticated;
grant select on public.trade_matches to anon, authenticated;     -- anon: no rows, never an error
grant all on public.trade_matches to service_role;

create or replace function public.trade_counter_kinds(p_kind text) returns text[] language sql immutable set search_path = public as $$
  select case p_kind when 'stock' then array['wanted'] when 'materials' then array['wanted'] when 'wanted' then array['stock', 'materials']
                     when 'file_sale' then array['file_wanted'] when 'file_wanted' then array['file_sale'] when 'toll' then array['toll_wanted']
                     when 'toll_wanted' then array['toll'] when 'agency' then array['distributor'] when 'distributor' then array['agency'] else '{}'::text[] end
$$;

revoke all on function public.trade_counter_kinds(text) from public, anon, authenticated;
grant execute on function public.trade_counter_kinds(text) to service_role;

create or replace function public.trade_match_run(p_id bigint) returns int language plpgsql security definer set search_path = public as $$
declare me public.products; c record; n int := 0; mine_govs jsonb;
begin
  select * into me from public.products where id = p_id;
  if me.id is null or me.kind is null or me.status <> 'active' or cardinality(me.root_words) = 0 then return 0; end if;
  mine_govs := coalesce(me.attrs -> 'govs', '[]');
  for c in
    select x.id, x.user_id, x.name, x.kind from public.products x
     where x.kind = any(public.trade_counter_kinds(me.kind)) and x.status = 'active' and (x.expires_at is null or x.expires_at > now())
       and x.user_id <> me.user_id and x.root_words && me.root_words
       and not exists (select 1 from public.user_blocks bl where (bl.blocker = x.user_id and bl.blocked = me.user_id) or (bl.blocker = me.user_id and bl.blocked = x.user_id))
       and not exists (select 1 from public.account_suspensions s where s.user_id = x.user_id)
       and exists (select 1 from unnest(me.roots) ra, unnest(x.roots) rb
                    where string_to_array(ra, ' ') <@ string_to_array(rb, ' ') or string_to_array(rb, ' ') <@ string_to_array(ra, ' '))
       and (me.kind not in ('agency', 'distributor') or mine_govs ? 'all' or coalesce(x.attrs -> 'govs', '[]') ? 'all'
            or exists (select 1 from jsonb_array_elements_text(mine_govs) g where coalesce(x.attrs -> 'govs', '[]') ? g))
     order by coalesce(x.bumped_at, x.created_at) desc, x.id desc limit 200
  loop
    insert into public.trade_matches (a, b) values (least(me.id, c.id), greatest(me.id, c.id)) on conflict do nothing;
    if not found then continue; end if;
    n := n + 1;
    if n <= 50 then
      insert into public.notifications (user_id, type, from_user, message, data)
      values (c.user_id, 'trade_match', me.user_id,
              left(case when me.type = 'demand' then 'A buyer is looking for what you offer: ' else 'A new offer matches what you need: ' end || me.name, 300),
              jsonb_build_object('listing', me.id, 'mine', c.id, 'name', left(me.name, 200), 'kind', me.kind, 'mine_name', left(c.name, 200)));
    end if;
  end loop;
  if n > 0 then
    insert into public.notifications (user_id, type, from_user, message, data)
    values (me.user_id, 'trade_match', null, left(n || case when n = 1 then ' listing matches ' else ' listings match ' end || me.name, 300),
            jsonb_build_object('mine', me.id, 'count', n, 'mine_name', left(me.name, 200), 'kind', me.kind));
  end if;
  return n;
end $$;
revoke all on function public.trade_match_run(bigint) from public, anon, authenticated, service_role;

-- my matches: each pair where one listing is mine and the other is still open
create or replace function public.my_trade_matches(p_limit int default 50) returns jsonb language sql stable security definer set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object('mine', m.mine, 'mine_name', mp.name, 'id', op.id, 'name', op.name, 'kind', op.kind, 'type', op.type, 'price', op.price,
           'price_mode', op.price_mode, 'discount_pct', op.discount_pct, 'currency', op.currency, 'user_id', op.user_id, 'at', m.created_at,
           'owner', (select jsonb_build_object('name', pr.name, 'verified', pr.verified) from public.profiles pr where pr.id = op.user_id),
           'co', (select jsonb_build_object('slug', c.slug, 'name', c.name, 'verified', c.status = 'verified') from public.companies c where c.id = op.company_id))
           order by m.created_at desc), '[]')
  from (select case when pa.user_id = auth.uid() then t.a else t.b end as mine, case when pa.user_id = auth.uid() then t.b else t.a end as other, t.created_at
          from public.trade_matches t join public.products pa on pa.id = t.a join public.products pb on pb.id = t.b
         where auth.uid() is not null and (pa.user_id = auth.uid() or pb.user_id = auth.uid())
         order by t.created_at desc limit least(greatest(coalesce(p_limit, 50), 1), 200)) m
  join public.products mp on mp.id = m.mine join public.products op on op.id = m.other
  where op.status in ('active', 'reserved') and (op.expires_at is null or op.expires_at > now())
$$;
revoke all on function public.my_trade_matches(int) from public, anon, authenticated, service_role;
grant execute on function public.my_trade_matches(int) to authenticated, service_role;

-- ── 2. saved searches on canonical words (W-03 «بحث محفوظ»; 0043 kept the substring check for jobs) ────
create or replace function public.trade_saved_search_run(p_id bigint) returns int language plpgsql security definer set search_path = public as $$
declare p public.products; s record; n int := 0;
begin
  select * into p from public.products where id = p_id;
  if p.id is null or not p.active then return 0; end if;
  for s in select ss.id, ss.user_id, ss.name, ss.q from public.saved_searches ss
            where ss.kind = 'market' and ss.alert <> 'off' and ss.q <> '' and ss.user_id <> p.user_id
              and not exists (select 1 from public.user_blocks b where (b.blocker = ss.user_id and b.blocked = p.user_id) or (b.blocker = p.user_id and b.blocked = ss.user_id))
            limit 2000 loop
    -- the canonical words (Arabic ⇄ English, digits, forms), or the search written inside the name as 0045 matched it
    if not ((cardinality(public.trade_query_patterns(s.q)) > 0 and p.search_text like all (public.trade_query_patterns(s.q))) or position(lower(s.q) in lower(p.name)) > 0) then continue; end if;
    insert into public.notifications (user_id, type, from_user, message, data)
    values (s.user_id, 'saved_search', p.user_id, 'New match for your saved search “' || left(s.name, 80) || '”: ' || left(p.name, 120),
            jsonb_build_object('kind', 'market', 'id', p.id, 'search', s.id, 'title', left(p.name, 120)));
    n := n + 1; exit when n >= 200;
  end loop;
  return n;
end $$;
revoke all on function public.trade_saved_search_run(bigint) from public, anon, authenticated, service_role;

-- ── 3. going live: published_at, matching, saved searches, followers ────
create or replace function public.products_trade_live() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> 'active' then return null; end if;
  if tg_op = 'UPDATE' and old.status not in ('draft') then return null; end if;      -- a resumed or renewed listing: not again
  update public.products set published_at = coalesce(published_at, now()) where id = new.id and published_at is null;
  perform public.trade_match_run(new.id);
  perform public.trade_saved_search_run(new.id);
  if tg_op = 'UPDATE' then                                                         -- inserted active, 0058's trigger told the followers already
    perform public.notify_company_followers(
      case when new.company_id is not null then array[new.company_id] else array(select id from public.companies where owner_id = new.user_id and status <> 'suspended' limit 5) end,
      new.user_id, new.name, coalesce(new.type, 'supply'));
  end if;
  return null;
end $$;
revoke all on function public.products_trade_live() from public, anon, authenticated, service_role;
drop trigger if exists trg_products_trade_live on public.products;
create trigger trg_products_trade_live after insert or update of status on public.products for each row execute function public.products_trade_live();
drop trigger if exists trg_products_saved_search on public.products;     -- listings: trade_saved_search_run above (jobs keep 0043's trigger)

-- ── 4. renew: free once every 7 days ────
create or replace function public.listing_renew(p_id bigint) returns timestamptz language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; v timestamptz; last_ timestamptz;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and user_id = me for update;
  if p.id is null then raise exception 'Only the listing''s owner can renew it' using errcode = '42501'; end if;
  if p.status = 'draft' then raise exception 'Publish the draft first' using errcode = '22023'; end if;
  if p.closed_reason = 'sold' then raise exception 'A sold listing is not renewed — post a new one' using errcode = '22023'; end if;
  last_ := coalesce(p.bumped_at, p.renewed_at, p.created_at);
  if last_ > now() - interval '7 days' then
    raise exception 'RENEW_LIMIT:% — a listing is renewed free once every 7 days; feature it to reach the top now', to_char(last_ + interval '7 days', 'YYYY-MM-DD') using errcode = '42501';
  end if;
  update public.products set renewed_at = now(), bumped_at = now(), status = case when status = 'closed' then 'active' else status end,
         closed_reason = case when status = 'closed' then null else closed_reason end
   where id = p_id returning expires_at into v;
  return v;
end $$;
revoke all on function public.listing_renew(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_renew(bigint) to authenticated, service_role;

-- ── 5. e-mail outbox: the trade notices (0059's list, plus these) ────
create or replace function public.notification_to_outbox() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.type in ('deal', 'payment', 'company_invite', 'company_join_request', 'company_join_answer', 'company_message', 'verification', 'cert_checked', 'cert_rejected',
                  'document_reviewed', 'review_reply', 'review_decided', 'report_decided', 'company_listing', 'trade_match', 'price_ask', 'trade_outcome')
     and not exists (select 1 from public.notification_prefs p where p.user_id = new.user_id and not p.email) then
    insert into public.notification_outbox (notification_id, user_id, kind) values (new.id, new.user_id, new.type);
  end if;
  return null;
end $$;
revoke all on function public.notification_to_outbox() from public, anon, authenticated, service_role;

notify pgrst, 'reload schema';
