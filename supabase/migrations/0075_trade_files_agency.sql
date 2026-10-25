-- ═════════════════════════════════════════════════════════════════════
-- 0075 — trust around registration files, the agency deal both ways, the distributor profile (W-04, W-05, W-15, W-18)
--   1. listing_private: the notification number (رقم الإخطار), the registration and licence numbers and the documents of a
--      listing — read only by its owner, Drugbox moderators and the members the owner shared them with
--      (listing_private_share) or who agreed a file deal on it; listing_private_get() is the one way to read them.
--   2. Documents seen by Drugbox («مستندات اتشافت»): the owner submits the documents (private storage, documents/listings/<owner>/…)
--      → Admin → Review → Trade documents (listing_docs_queue) → listing_docs_review sets products.docs_checked_at (or refuses with
--      a reason); nobody reviews their own listing; the owner is notified ('document_reviewed', e-mailed through 0059).
--   3. «اتفقنا» on a file deal (dossier: agree) needs the checklist — five boxes, all ticked — kept with the event.
--   4. The deals engine gains 'agency' (requested → talks → agreed; either side declines, the sender cancels).
--      listing_respond(id, from_slug, note): a company answers a file, toll, agency or distributor listing of another company →
--      the right deal ('dossier', 'service', 'agency'); a member without a company page writes to the lister instead.
--   5. distributor_profiles: a distributor's governorates, categories, warehouses, cold chain, fleet — on its company page.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. the private box ────
create table if not exists public.listing_private (
  listing_id    bigint primary key references public.products(id) on delete cascade,
  notif_no      text check (length(notif_no) <= 60),
  reg_no        text check (length(reg_no) <= 60),
  licence_no    text check (length(licence_no) <= 60),
  doc_paths     text[] not null default '{}' check (cardinality(doc_paths) <= 6),
  review_status text check (review_status in ('waiting', 'seen', 'rejected')),
  review_note   text check (length(review_note) <= 500),
  submitted_at  timestamptz,
  updated_at    timestamptz not null default now());
create index if not exists idx_listing_private_waiting on public.listing_private (submitted_at) where review_status = 'waiting';
alter table public.listing_private enable row level security;
do $$ begin
  create policy "listing private: the owner reads" on public.listing_private for select to authenticated
    using (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "listing private: the owner writes" on public.listing_private for insert to authenticated
    with check (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "listing private: the owner edits" on public.listing_private for update to authenticated
    using (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())))
    with check (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
revoke all on public.listing_private from public, anon, authenticated;
grant select on public.listing_private to anon, authenticated;
grant insert (listing_id, notif_no, reg_no, licence_no) on public.listing_private to authenticated;   -- documents and review: through the functions
grant update (notif_no, reg_no, licence_no) on public.listing_private to authenticated;
grant all on public.listing_private to service_role;

create table if not exists public.listing_private_shares (
  listing_id bigint not null references public.products(id) on delete cascade,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (listing_id, user_id));
create index if not exists idx_listing_private_shares_user on public.listing_private_shares (user_id);
alter table public.listing_private_shares enable row level security;
do $$ begin
  create policy "private shares: the owner and the member read" on public.listing_private_shares for select to authenticated
    using (user_id = (select auth.uid()) or exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "private shares: the owner removes" on public.listing_private_shares for delete to authenticated
    using (exists (select 1 from public.products p where p.id = listing_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
revoke all on public.listing_private_shares from public, anon, authenticated;
grant select, delete on public.listing_private_shares to authenticated;
grant select on public.listing_private_shares to anon;
grant all on public.listing_private_shares to service_role;

-- the owner shares the box with one member who wrote, asked or quoted on the listing (0074: listing_counterparts)
create or replace function public.listing_private_share(p_id bigint, p_user uuid) returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not exists (select 1 from public.products where id = p_id and user_id = me) then raise exception 'Only the listing''s owner can share this' using errcode = '42501'; end if;
  if not exists (select 1 from jsonb_array_elements(public.listing_counterparts(p_id)) x where x ->> 'id' = p_user::text) then
    raise exception 'Share it with someone who wrote to you, asked the price or quoted on this listing' using errcode = '22023';
  end if;
  insert into public.listing_private_shares (listing_id, user_id) values (p_id, p_user) on conflict do nothing;
  if found then
    insert into public.notifications (user_id, type, from_user, message, data)
    values (p_user, 'trade_outcome', me, left('The registration details of “' || (select name from public.products where id = p_id) || '” were shared with you', 300),
            jsonb_build_object('listing', p_id, 'name', (select left(name, 200) from public.products where id = p_id), 'ask', 'private'));
  end if;
  return true;
end $$;
revoke all on function public.listing_private_share(bigint, uuid) from public, anon, authenticated, service_role;
grant execute on function public.listing_private_share(bigint, uuid) to authenticated, service_role;

-- reading the box: the owner, Drugbox, a member it was shared with, or the requesting company of an agreed file deal on it
create or replace function public.listing_private_get(p_id bigint) returns jsonb language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; b public.listing_private; owner_ boolean;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id;
  if p.id is null then raise exception 'This listing does not exist' using errcode = 'P0002'; end if;
  owner_ := p.user_id = me;
  if not (owner_ or public.is_moderator()
          or exists (select 1 from public.listing_private_shares s where s.listing_id = p.id and s.user_id = me)
          or exists (select 1 from public.deals d where d.lines ->> 'listing_id' = p.id::text and d.type = 'dossier' and d.status = 'agreed'
                      and d.from_company_id is not null and public.is_company_member(d.from_company_id))) then
    raise exception 'The owner has not shared these details with you' using errcode = '42501';
  end if;
  select * into b from public.listing_private where listing_id = p.id;
  return jsonb_build_object('notif_no', b.notif_no, 'reg_no', b.reg_no, 'licence_no', b.licence_no,
    'docs', case when owner_ or public.is_moderator() then to_jsonb(coalesce(b.doc_paths, '{}')) else '[]'::jsonb end,   -- the documents: the owner and Drugbox only
    'review_status', case when owner_ or public.is_moderator() then b.review_status end, 'review_note', case when owner_ then b.review_note end,
    'checked_at', p.docs_checked_at);
end $$;
revoke all on function public.listing_private_get(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_private_get(bigint) to authenticated, service_role;

-- ── 2. documents seen by Drugbox ────
create or replace function public.listing_docs_submit(p_id bigint, p_paths text[]) returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); x text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not exists (select 1 from public.products where id = p_id and user_id = me and kind in ('file_sale', 'toll', 'company_sale', 'agency')) then
    raise exception 'Only the owner of a file, toll, company or agency listing sends documents' using errcode = '42501';
  end if;
  if coalesce(cardinality(p_paths), 0) = 0 or cardinality(p_paths) > 6 then raise exception 'Send one to six documents' using errcode = '22023'; end if;
  foreach x in array p_paths loop
    if x !~ ('^listings/' || me::text || '/doc-[A-Za-z0-9._-]{1,120}$') or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = x) then
      raise exception 'Upload the documents first' using errcode = '42501';
    end if;
  end loop;
  insert into public.listing_private (listing_id, doc_paths, review_status, submitted_at, review_note) values (p_id, p_paths, 'waiting', now(), null)
  on conflict (listing_id) do update set doc_paths = excluded.doc_paths, review_status = 'waiting', submitted_at = now(), review_note = null, updated_at = now();
  update public.products set docs_checked_at = null, docs_checked_by = null where id = p_id;      -- new papers: Drugbox looks again
  return 'waiting';
end $$;
revoke all on function public.listing_docs_submit(bigint, text[]) from public, anon, authenticated, service_role;
grant execute on function public.listing_docs_submit(bigint, text[]) to authenticated, service_role;

create or replace function public.listing_docs_queue() returns jsonb language sql stable security definer set search_path = public as $$
  select case when not public.is_moderator() then '[]'::jsonb else coalesce((select jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'kind', p.kind, 'attrs', p.attrs,
           'owner', (select jsonb_build_object('id', pr.id, 'name', pr.name) from public.profiles pr where pr.id = p.user_id), 'mine', p.user_id = auth.uid(),
           'docs', to_jsonb(b.doc_paths), 'notif_no', b.notif_no, 'reg_no', b.reg_no, 'licence_no', b.licence_no, 'at', b.submitted_at) order by b.submitted_at)
    from public.listing_private b join public.products p on p.id = b.listing_id where b.review_status = 'waiting'), '[]') end
$$;
revoke all on function public.listing_docs_queue() from public, anon, authenticated, service_role;
grant execute on function public.listing_docs_queue() to authenticated, service_role;

create or replace function public.listing_docs_review(p_id bigint, p_ok boolean, p_note text default null) returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; v text := nullif(left(btrim(coalesce(p_note, '')), 500), '');
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id;
  if p.id is null or not exists (select 1 from public.listing_private b where b.listing_id = p_id and b.review_status = 'waiting') then
    raise exception 'Nothing waits for a check on this listing' using errcode = 'P0002'; end if;
  if p.user_id = me then raise exception 'Someone else on the Drugbox team checks your own listing' using errcode = '42501'; end if;
  if not coalesce(p_ok, false) and v is null then raise exception 'Write the reason' using errcode = '22023'; end if;
  update public.listing_private set review_status = case when p_ok then 'seen' else 'rejected' end, review_note = v, updated_at = now() where listing_id = p_id;
  update public.products set docs_checked_at = case when p_ok then now() end, docs_checked_by = case when p_ok then me end where id = p_id;
  insert into public.notifications (user_id, type, from_user, message, data)
  values (p.user_id, 'document_reviewed', me,
          left(case when p_ok then 'Drugbox saw the documents of “' || p.name || '”' else 'Drugbox could not accept the documents of “' || p.name || '”: ' || v end, 300),
          jsonb_build_object('listing', p.id, 'name', left(p.name, 200), 'ok', coalesce(p_ok, false), 'reason', v));
  return case when p_ok then 'seen' else 'rejected' end;
end $$;
revoke all on function public.listing_docs_review(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_docs_review(bigint, boolean, text) to authenticated, service_role;

-- ── 3. «اتفقنا» on a file deal needs the checklist ────
create or replace function public.trade_agree_checklist() returns text[] language sql immutable set search_path = public as $$
  select array['notif_seen', 'stage_understood', 'price_increase_checked', 'transfer_needs_approval', 'docs_reviewed']
$$;
revoke all on function public.trade_agree_checklist() from public, anon;
grant execute on function public.trade_agree_checklist() to authenticated, service_role;
create or replace function public.deal_events_agree_guard() returns trigger language plpgsql set search_path = public as $$
declare k text;
begin
  if new.action <> 'agree' or not exists (select 1 from public.deals d where d.id = new.deal_id and d.type = 'dossier') then return new; end if;
  foreach k in array public.trade_agree_checklist() loop
    if coalesce(new.data -> 'checklist' ->> k, '') <> 'true' then
      raise exception 'Tick every box of the checklist before agreeing (%)', k using errcode = '22023';
    end if;
  end loop;
  new.data := jsonb_build_object('checklist', new.data -> 'checklist') || (coalesce(new.data, '{}') - 'checklist');
  return new;
end $$;
revoke all on function public.deal_events_agree_guard() from public, anon, authenticated, service_role;
drop trigger if exists trg_deal_events_agree_guard on public.deal_events;
create trigger trg_deal_events_agree_guard before insert on public.deal_events for each row execute function public.deal_events_agree_guard();

-- ── 4. the agency deal ────
alter table public.deals drop constraint if exists deals_type_check;
alter table public.deals add constraint deals_type_check check (type = any (array['quote', 'service', 'surplus', 'questionnaire', 'dossier', 'job', 'group', 'agency']));
create or replace function public.deal_flow() returns jsonb language sql immutable as $$ select '{
  "quote":   {"first":"sent","acts":{"sent":{"to":["quote","decline"],"from":["cancel"]},"quoted":{"from":["accept","counter","decline"],"to":["revise"]},"countered":{"to":["quote","decline"],"from":["cancel"]},"accepted":{"to":["confirm"]},"confirmed":{"to":["ship"]},"shipped":{"from":["receive"]},"delivered":{"from":["rate"]}}},
  "service": {"first":"sent","acts":{"sent":{"to":["propose","decline"],"from":["cancel"]},"proposed":{"from":["accept","decline"]},"accepted":{"to":["start"]},"in_progress":{"to":["deliver"]},"delivered":{"from":["rate"]}}},
  "surplus": {"first":"offered","acts":{"offered":{"to":["accept_offer","counter_offer","decline"],"from":["cancel"]},"countered":{"from":["accept_counter","decline"]},"accepted":{"to":["confirm"]},"confirmed":{"to":["ship"]},"shipped":{"from":["receive"]},"delivered":{"from":["rate"]}}},
  "questionnaire": {"first":"sent","acts":{"sent":{"to":["answer"]},"answered":{"from":["approve","reject"]}}},
  "dossier": {"first":"requested","acts":{"requested":{"to":["sign_nda","decline"]},"nda_signed":{"to":["share"]},"shared":{"from":["agree","decline"],"to":["decline"]}}},
  "job":     {"first":"applied","acts":{"applied":{"to":["shortlist","reject"]},"shortlisted":{"to":["interview","reject"]},"interview":{"to":["offer","reject"]},"offer":{"from":["accept_job","decline"]}}},
  "group":   {"first":"open","acts":{"open":{"from":["cancel"],"to":["decline"]},"target_reached":{"to":["confirm_group","decline"]}}},
  "agency":  {"first":"requested","acts":{"requested":{"to":["talk","decline"],"from":["cancel"]},"talks":{"to":["agree","decline"],"from":["cancel","decline"]}}}
}'::jsonb $$;
revoke all on function public.deal_flow() from public, anon, authenticated, service_role;
grant execute on function public.deal_flow() to authenticated, service_role;
create or replace function public.deal_next_status(p_type text, p_action text) returns text language sql immutable as $$
  select case when p_type = 'service' and p_action = 'accept' then 'accepted' else ('{
    "quote":"quoted","revise":"quoted","counter":"countered","accept":"accepted","confirm":"confirmed","ship":"shipped","receive":"delivered","rate":"closed",
    "decline":"declined","cancel":"cancelled","propose":"proposed","start":"in_progress","deliver":"delivered","accept_offer":"accepted","counter_offer":"countered",
    "accept_counter":"accepted","answer":"answered","approve":"approved","reject":"rejected","sign_nda":"nda_signed","share":"shared","agree":"agreed",
    "shortlist":"shortlisted","interview":"interview","offer":"offer","accept_job":"hired","confirm_group":"confirmed","talk":"talks"}'::jsonb ->> p_action) end
$$;
revoke all on function public.deal_next_status(text, text) from public, anon, authenticated, service_role;
grant execute on function public.deal_next_status(text, text) to authenticated, service_role;

-- a company answers another company's structured listing with the right deal
create or replace function public.listing_respond(p_id bigint, p_from_slug text, p_note text default null) returns jsonb language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p public.products; v_me public.companies; v_them public.companies; t text; d public.deals; v_from bigint; v_to bigint; v_from_user uuid; first text;
        note text := nullif(left(btrim(coalesce(p_note, '')), 500), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and status = 'active';
  if p.id is null then raise exception 'This listing is not open' using errcode = 'P0002'; end if;
  if p.user_id = me then raise exception 'This is your own listing' using errcode = '22023'; end if;
  t := case when p.kind in ('agency', 'distributor') then 'agency' when p.kind in ('file_sale', 'file_wanted') then 'dossier' when p.kind in ('toll', 'toll_wanted') then 'service' end;
  if t is null then raise exception 'Write to the lister about this listing' using errcode = '22023'; end if;
  if exists (select 1 from public.user_blocks b where (b.blocker = p.user_id and b.blocked = me) or (b.blocker = me and b.blocked = p.user_id)) then
    raise exception 'You cannot message this member' using errcode = '42501';
  end if;
  select * into v_me from public.companies where slug = p_from_slug;
  select * into v_them from public.companies where id = p.company_id;
  if v_me.id is null or not public.is_company_member(v_me.id) or v_me.status = 'suspended' then
    raise exception 'Answer on behalf of a company you belong to — or write to the lister' using errcode = '42501'; end if;
  if v_them.id is null or v_them.status = 'suspended' or v_them.owner_id is null then
    raise exception 'This listing was posted by a member, not a company — write to them instead' using errcode = '22023'; end if;
  if v_me.id = v_them.id then raise exception 'This listing is your own company''s' using errcode = '22023'; end if;
  if exists (select 1 from public.deals x where x.lines ->> 'listing_id' = p.id::text and x.status not in ('declined', 'cancelled', 'agreed', 'closed', 'rejected')
               and (x.from_company_id = v_me.id or x.to_company_id = v_me.id)) then
    raise exception 'Your company already has an open request on this listing — see Requests & deals' using errcode = '23505'; end if;
  if (select count(*) from public.deals x where x.from_user = me and x.created_at > now() - interval '1 hour') >= 30 then
    raise exception 'Too many requests in one hour — please try again later' using errcode = '42501'; end if;
  -- who asks (from) and who answers (to): the one who wants the file / the capacity / the products asks;
  -- for an agency, the distributor asks the owner of the products
  if p.kind in ('file_sale', 'toll', 'agency') then v_from := v_me.id; v_from_user := me; v_to := v_them.id;
  else v_from := v_them.id; v_from_user := p.user_id; v_to := v_me.id; end if;
  first := public.deal_flow() -> t ->> 'first';
  insert into public.deals (type, title, from_company_id, from_user, to_company_id, lines, status, assignee)
  values (t, left(p.name, 200), v_from, v_from_user, v_to,
          jsonb_build_object('product', p.name, 'listing_id', p.id, 'kind', p.kind, 'note', coalesce(note, '')), first,
          case when v_to = v_me.id then me else public.deal_receiver(v_to, t) end)
  returning * into d;
  insert into public.deal_events (deal_id, side, action, note, actor) values (d.id, case when v_from = v_me.id then 'from' else 'to' end, case when v_from = v_me.id then first else 'answer_listing' end,
    coalesce(note, 'Answered the Marketplace listing: ' || p.name), me);
  insert into public.listing_inquiries (listing_id, user_id) values (p.id, me) on conflict do nothing;
  insert into public.notifications (user_id, type, from_user, message) values (p.user_id, 'deal', me, left(v_me.name || ': ' || p.name, 300));
  return jsonb_build_object('kind', 'deal', 'ref', d.ref, 'type', t);
end $$;
revoke all on function public.listing_respond(bigint, text, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_respond(bigint, text, text) to authenticated, service_role;

-- ── 5. the distributor's profile ────
create table if not exists public.distributor_profiles (
  company_id  bigint primary key references public.companies(id) on delete cascade,
  govs        text[] not null default '{}',
  cats        text[] not null default '{}',
  warehouses  int check (warehouses between 0 and 10000),
  cold_chain  boolean not null default false,
  fleet       int check (fleet between 0 and 100000),
  agencies    int check (agencies between 0 and 10000),
  note        text check (length(note) <= 500),
  updated_by  uuid references public.profiles(id) on delete set null,
  updated_at  timestamptz not null default now(),
  constraint distributor_profiles_lists check (govs <@ (public.trade_govs() || 'all'::text) and cats <@ array['medicines', 'supplements', 'cosmetics', 'devices', 'veterinary', 'herbal', 'baby', 'hospital']
    and cardinality(govs) <= 28 and cardinality(cats) <= 8));
create index if not exists idx_distributor_profiles_updated_by on public.distributor_profiles (updated_by) where updated_by is not null;
alter table public.distributor_profiles enable row level security;
do $$ begin
  create policy "distributor profiles: members read" on public.distributor_profiles for select to authenticated using (true);
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "distributor profiles: the company's team writes" on public.distributor_profiles for insert to authenticated
    with check (public.is_company_member(company_id, array['owner', 'admin', 'sales']));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "distributor profiles: the company's team edits" on public.distributor_profiles for update to authenticated
    using (public.is_company_member(company_id, array['owner', 'admin', 'sales'])) with check (public.is_company_member(company_id, array['owner', 'admin', 'sales']));
exception when duplicate_object then null; end $$;
revoke all on public.distributor_profiles from public, anon, authenticated;
grant select on public.distributor_profiles to anon;
grant select, insert, update on public.distributor_profiles to authenticated;
grant all on public.distributor_profiles to service_role;
create or replace function public.distributor_profiles_stamp() returns trigger language plpgsql set search_path = public as $$
begin
  new.updated_at := now(); new.updated_by := coalesce(auth.uid(), new.updated_by);
  if tg_op = 'UPDATE' and new.company_id is distinct from old.company_id then raise exception 'The profile stays with its company' using errcode = '42501'; end if;
  return new;
end $$;
revoke all on function public.distributor_profiles_stamp() from public, anon, authenticated, service_role;
drop trigger if exists trg_distributor_profiles_stamp on public.distributor_profiles;
create trigger trg_distributor_profiles_stamp before insert or update on public.distributor_profiles for each row execute function public.distributor_profiles_stamp();

notify pgrst, 'reload schema';
