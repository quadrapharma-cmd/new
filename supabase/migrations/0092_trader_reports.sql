-- ═════════════════════════════════════════════════════════════════════
-- 0092 — a trade problem is reported to Drugbox, not shouted in a group (area w-trust: W-19)
--   1. trader_reports: a member reports a trader with evidence (1–5 files in private storage, documents/trader-reports/<me>/…),
--      a reason and what happened (optionally the deal it is about). The reported member is told at once and has the RIGHT TO
--      REPLY (their side + their own evidence) — the reporter's words, the reason and the evidence are shown to them.
--      TWO Drugbox moderators decide: a report is upheld or dismissed when two different moderators vote the same way (the first
--      vote waits; a split waits for a third). Nobody votes before the reply, unless 7 days passed without one. A moderator who
--      is a party votes on nothing about it. Both sides are told the outcome; the decision is logged (admin_actions
--      'trader_report'). One open report per reporter and trader, at most 5 new reports a day.
--      An upheld report counts on the trader's card (trade_card.reports_upheld) — a count Drugbox checked, never the accusation.
--   2. deal_ratings: after a deal is delivered (or closed) the supplier rates the buyer too (the buyer already rates the supplier
--      through deal_act 'rate'), once, 1–5 stars and a note. buyer_rating(company | member) is what other suppliers see.
--   3. can_read_document / can_write_document: the trader-reports folder (author; the reported member for the evidence of a report
--      about them; Drugbox moderators) and the broker's authorisation of 0090 (documents/listings/…), on top of 0059 / 0060.
-- Every new table / function has its own GRANT / REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. reports ────
create table if not exists public.trader_reports (
  id              bigint generated always as identity primary key,
  reporter        uuid references public.profiles(id) on delete set null,
  reported        uuid not null references public.profiles(id) on delete cascade,
  deal_id         bigint references public.deals(id) on delete set null,
  reason          text not null,
  details         text not null,
  evidence        text[] not null,
  reply           text,
  reply_evidence  text[] not null default '{}',
  replied_at      timestamptz,
  status          text not null default 'open',
  decided_at      timestamptz,
  created_at      timestamptz not null default now(),
  constraint trader_reports_reason check (reason in ('non_payment', 'non_delivery', 'counterfeit', 'misrepresentation', 'sham_papers', 'other')),
  constraint trader_reports_status check (status in ('open', 'upheld', 'dismissed')),
  constraint trader_reports_len check (char_length(details) between 20 and 2000 and char_length(coalesce(reply, '')) <= 2000
                                       and cardinality(evidence) between 1 and 5 and cardinality(reply_evidence) <= 5),
  constraint trader_reports_not_self check (reporter is distinct from reported)
);
create index if not exists idx_trader_reports_reported on public.trader_reports (reported, status);
create index if not exists idx_trader_reports_reporter on public.trader_reports (reporter, created_at desc);
create index if not exists idx_trader_reports_open on public.trader_reports (created_at) where status = 'open';
create index if not exists idx_trader_reports_deal on public.trader_reports (deal_id) where deal_id is not null;
create unique index if not exists idx_trader_reports_one_open on public.trader_reports (reporter, reported) where status = 'open';
alter table public.trader_reports enable row level security;
drop policy if exists "trader reports: the two sides and Drugbox read" on public.trader_reports;
create policy "trader reports: the two sides and Drugbox read" on public.trader_reports for select to authenticated
  using (reporter = (select auth.uid()) or reported = (select auth.uid()) or (select public.is_moderator()));
revoke all on table public.trader_reports from public, anon, authenticated, service_role;
grant select on table public.trader_reports to anon, authenticated;              -- written through the functions below only
grant select, insert, update, delete, truncate, references, trigger on table public.trader_reports to service_role;
revoke all on sequence public.trader_reports_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.trader_reports_id_seq to service_role;

create table if not exists public.trader_report_votes (
  report_id  bigint not null references public.trader_reports(id) on delete cascade,
  moderator  uuid not null references public.profiles(id) on delete cascade,
  uphold     boolean not null,
  note       text check (char_length(coalesce(note, '')) <= 500),
  created_at timestamptz not null default now(),
  primary key (report_id, moderator)
);
create index if not exists idx_trader_report_votes_mod on public.trader_report_votes (moderator);
alter table public.trader_report_votes enable row level security;
drop policy if exists "trader report votes: Drugbox reads" on public.trader_report_votes;
create policy "trader report votes: Drugbox reads" on public.trader_report_votes for select to authenticated using ((select public.is_moderator()));
revoke all on table public.trader_report_votes from public, anon, authenticated, service_role;
grant select on table public.trader_report_votes to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.trader_report_votes to service_role;

-- a file of mine in documents/trader-reports/<me>/ that exists
create or replace function private.own_report_files(p_files text[]) returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(bool_and(f ~ ('^trader-reports/' || auth.uid()::text || '/[A-Za-z0-9._-]{1,120}$')
                           and exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = f)), true)
    from unnest(coalesce(p_files, '{}'::text[])) f
$$;
revoke all on function private.own_report_files(text[]) from public, anon, authenticated, service_role;
grant execute on function private.own_report_files(text[]) to service_role;

create or replace function public.trader_report(p_user uuid, p_reason text, p_details text, p_evidence text[], p_deal_ref text default null) returns bigint
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; rid bigint; v_details text := btrim(coalesce(p_details, ''));
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if private.is_suspended(me) then raise exception 'Your account is suspended' using errcode = '42501'; end if;
  if p_user is null or p_user = me then raise exception 'Choose the trader you are reporting' using errcode = '22023'; end if;
  if not exists (select 1 from public.profiles p where p.id = p_user and p.account_type is distinct from 'deleted') then
    raise exception 'This member is not on Drugbox' using errcode = 'P0002'; end if;
  if p_reason is null or p_reason not in ('non_payment', 'non_delivery', 'counterfeit', 'misrepresentation', 'sham_papers', 'other') then
    raise exception 'Choose what happened' using errcode = '22023'; end if;
  if char_length(v_details) < 20 then raise exception 'Say what happened in at least 20 characters' using errcode = '22023', hint = 'DX430'; end if;
  if coalesce(cardinality(p_evidence), 0) = 0 then raise exception 'Attach at least one piece of evidence (an invoice, a chat, a delivery note…)' using errcode = '22023', hint = 'DX431'; end if;
  if cardinality(p_evidence) > 5 or not private.own_report_files(p_evidence) then
    raise exception 'Upload the evidence first (at most 5 files)' using errcode = '42501', hint = 'DX431'; end if;
  if exists (select 1 from public.trader_reports r where r.reporter = me and r.reported = p_user and r.status = 'open') then
    raise exception 'You already have an open report about this member — Drugbox is checking it' using errcode = 'P0001', hint = 'DX432'; end if;
  if (select count(*) from public.trader_reports r where r.reporter = me and r.created_at > now() - interval '1 day') >= 5 then
    raise exception 'You sent 5 reports today — try again tomorrow' using errcode = 'P0001'; end if;
  if nullif(btrim(coalesce(p_deal_ref, '')), '') is not null then
    select * into d from public.deals where ref = btrim(p_deal_ref);
    if d.id is null or not public.deal_is_party(d.id) then raise exception 'You can name only a deal you are part of' using errcode = '42501'; end if;
  end if;
  insert into public.trader_reports (reporter, reported, deal_id, reason, details, evidence)
  values (me, p_user, d.id, p_reason, left(v_details, 2000), p_evidence) returning id into rid;
  insert into public.notifications (user_id, type, from_user, message, data)
  values (p_user, 'trader_report', null, null, jsonb_build_object('report', rid, 'reason', p_reason, 'reply_by', to_char(now() + interval '7 days', 'YYYY-MM-DD')));
  return rid;
end $$;
revoke all on function public.trader_report(uuid, text, text, text[], text) from public, anon, authenticated, service_role;
grant execute on function public.trader_report(uuid, text, text, text[], text) to authenticated, service_role;

-- the reported member's side (while the report is open; they can correct it until Drugbox decides)
create or replace function public.trader_report_reply(p_report bigint, p_reply text, p_evidence text[] default '{}') returns void
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); r public.trader_reports; v text := btrim(coalesce(p_reply, ''));
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into r from public.trader_reports where id = p_report for update;
  if r.id is null or r.reported <> me then raise exception 'This report is not about you' using errcode = '42501'; end if;
  if r.status <> 'open' then raise exception 'Drugbox already decided this report' using errcode = '22023', hint = 'DX409'; end if;
  if char_length(v) < 10 then raise exception 'Write your side in at least 10 characters' using errcode = '22023'; end if;
  if coalesce(cardinality(p_evidence), 0) > 5 or not private.own_report_files(p_evidence) then raise exception 'Upload your files first (at most 5)' using errcode = '42501'; end if;
  update public.trader_reports set reply = left(v, 2000), reply_evidence = coalesce(p_evidence, '{}'), replied_at = now() where id = r.id;
  if r.reporter is not null then
    insert into public.notifications (user_id, type, from_user, message, data)
    values (r.reporter, 'trader_report_reply', null, null, jsonb_build_object('report', r.id));
  end if;
end $$;
revoke all on function public.trader_report_reply(bigint, text, text[]) from public, anon, authenticated, service_role;
grant execute on function public.trader_report_reply(bigint, text, text[]) to authenticated, service_role;

-- a moderator's vote; the second matching vote decides
create or replace function public.trader_report_vote(p_report bigint, p_uphold boolean, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); r public.trader_reports; n int; out text; v_note text := nullif(left(btrim(coalesce(p_note, '')), 500), '');
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  if p_uphold is null then raise exception 'Uphold or dismiss' using errcode = '22023'; end if;
  select * into r from public.trader_reports where id = p_report for update;
  if r.id is null then raise exception 'This report is not in the queue' using errcode = 'P0002'; end if;
  if r.status <> 'open' then raise exception 'Already decided (%)', r.status using errcode = 'DX409'; end if;
  if me in (r.reporter, r.reported) then raise exception 'You are a party to this report — another moderator decides' using errcode = '42501'; end if;
  if r.replied_at is null and r.created_at > now() - interval '7 days' then
    raise exception 'The member has until % to reply — decide after their reply', to_char(r.created_at + interval '7 days', 'YYYY-MM-DD') using errcode = '22023', hint = 'DX433';
  end if;
  if exists (select 1 from public.trader_report_votes v where v.report_id = r.id and v.moderator = me) then
    raise exception 'You already voted — a second moderator decides' using errcode = 'P0001', hint = 'DX434'; end if;
  insert into public.trader_report_votes (report_id, moderator, uphold, note) values (r.id, me, p_uphold, v_note);
  select count(*) into n from public.trader_report_votes v where v.report_id = r.id and v.uphold = p_uphold;
  if n < 2 then return 'voted'; end if;
  out := case when p_uphold then 'upheld' else 'dismissed' end;
  update public.trader_reports set status = out, decided_at = now() where id = r.id;
  insert into public.notifications (user_id, type, from_user, message, data)
  select x.u, 'trader_report_decided', null, null, jsonb_build_object('report', r.id, 'outcome', out, 'side', x.side)
    from (values (r.reporter, 'reporter'), (r.reported, 'reported')) x(u, side) where x.u is not null;
  perform private.log_decision('trader_report', r.id::text,
    left(coalesce((select name from public.profiles where id = r.reporter), 'A member') || ' → ' || coalesce((select name from public.profiles where id = r.reported), 'a member'), 300),
    out, v_note, jsonb_build_object('reason', r.reason, 'votes', (select jsonb_agg(jsonb_build_object('by', private.who(v.moderator), 'uphold', v.uphold)) from public.trader_report_votes v where v.report_id = r.id)));
  return out;
end $$;
revoke all on function public.trader_report_vote(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.trader_report_vote(bigint, boolean, text) to authenticated, service_role;

create or replace function public.trader_reports_queue(p_limit int default 100) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not public.is_moderator() then null else coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at) from (
    select r.id, r.reason, r.details, r.evidence, r.reply, r.reply_evidence, r.replied_at, r.created_at,
           r.reporter, (select p.name from public.profiles p where p.id = r.reporter) as reporter_name,
           r.reported, (select p.name from public.profiles p where p.id = r.reported) as reported_name,
           (select d.ref from public.deals d where d.id = r.deal_id) as deal_ref,
           to_char(r.created_at + interval '7 days', 'YYYY-MM-DD') as reply_by,
           (r.replied_at is not null or r.created_at <= now() - interval '7 days') as can_vote,
           (select coalesce(jsonb_agg(jsonb_build_object('by', private.who(v.moderator), 'mine', v.moderator = auth.uid(), 'uphold', v.uphold, 'note', v.note) order by v.created_at), '[]'::jsonb)
              from public.trader_report_votes v where v.report_id = r.id) as votes
      from public.trader_reports r where r.status = 'open' order by r.created_at limit least(greatest(coalesce(p_limit, 100), 1), 300)) x), '[]'::jsonb) end
$$;
revoke all on function public.trader_reports_queue(int) from public, anon, authenticated, service_role;
grant execute on function public.trader_reports_queue(int) to authenticated, service_role;

-- the reports about me and the ones I sent (names of both sides; never the moderators' votes)
create or replace function public.my_trader_reports() returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at desc) from (
    select r.id, r.reason, r.details, r.evidence, r.reply, r.reply_evidence, r.replied_at, r.status, r.created_at, r.decided_at,
           case when r.reported = auth.uid() then 'about_me' else 'sent' end as side,
           (select p.name from public.profiles p where p.id = r.reporter) as reporter_name,
           (select p.name from public.profiles p where p.id = r.reported) as reported_name, r.reported,
           to_char(r.created_at + interval '7 days', 'YYYY-MM-DD') as reply_by
      from public.trader_reports r where r.reporter = auth.uid() or r.reported = auth.uid() limit 200) x), '[]'::jsonb) end
$$;
revoke all on function public.my_trader_reports() from public, anon, authenticated, service_role;
grant execute on function public.my_trader_reports() to authenticated, service_role;

-- ── 2. the supplier rates the buyer ────
create table if not exists public.deal_ratings (
  deal_id     bigint primary key references public.deals(id) on delete cascade,
  by_user     uuid references public.profiles(id) on delete set null,
  by_company  bigint references public.companies(id) on delete set null,
  buyer_user  uuid references public.profiles(id) on delete set null,
  buyer_company bigint references public.companies(id) on delete set null,
  stars       int not null check (stars between 1 and 5),
  note        text check (char_length(coalesce(note, '')) <= 500),
  created_at  timestamptz not null default now()
);
create index if not exists idx_deal_ratings_buyer_company on public.deal_ratings (buyer_company) where buyer_company is not null;
create index if not exists idx_deal_ratings_buyer_user on public.deal_ratings (buyer_user) where buyer_user is not null;
create index if not exists idx_deal_ratings_by_user on public.deal_ratings (by_user);
create index if not exists idx_deal_ratings_by_company on public.deal_ratings (by_company);
alter table public.deal_ratings enable row level security;
drop policy if exists "deal ratings: the deal's parties read" on public.deal_ratings;
create policy "deal ratings: the deal's parties read" on public.deal_ratings for select to authenticated using (public.deal_is_party(deal_id) or (select public.is_moderator()));
revoke all on table public.deal_ratings from public, anon, authenticated, service_role;
grant select on table public.deal_ratings to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.deal_ratings to service_role;

create or replace function public.deal_rate_buyer(p_ref text, p_stars int, p_note text default null) returns void
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if private.is_suspended(me) then raise exception 'Your account is suspended' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref;
  if d.id is null then raise exception 'Request not found' using errcode = 'P0002'; end if;
  if d.to_company_id is null or not public.is_company_member(d.to_company_id) then raise exception 'Only the supplier''s team rates the buyer' using errcode = '42501'; end if;
  if d.status not in ('delivered', 'closed') then raise exception 'Rate the buyer once the deal is delivered' using errcode = '22023', hint = 'DX435'; end if;
  if p_stars is null or p_stars not between 1 and 5 then raise exception 'Choose 1 to 5 stars' using errcode = '22023'; end if;
  if exists (select 1 from public.deal_ratings r where r.deal_id = d.id) then raise exception 'You already rated this buyer' using errcode = 'P0001', hint = 'DX436'; end if;
  insert into public.deal_ratings (deal_id, by_user, by_company, buyer_user, buyer_company, stars, note)
  values (d.id, me, d.to_company_id, d.from_user, d.from_company_id, p_stars, nullif(left(btrim(coalesce(p_note, '')), 500), ''));
  insert into public.deal_events (deal_id, side, action, note, actor, data)
  values (d.id, 'to', 'rate_buyer', 'Rated the buyer ' || p_stars || '/5', me, jsonb_build_object('stars', p_stars));
  insert into public.notifications (user_id, type, from_user, message, data)
  select x.u, 'deal_rated_buyer', me, null, jsonb_build_object('ref', d.ref, 'stars', p_stars, 'title', left(coalesce(d.title, ''), 80))
    from (select coalesce(d.from_user, (select c.owner_id from public.companies c where c.id = d.from_company_id)) u) x where x.u is not null and x.u <> me;
end $$;
revoke all on function public.deal_rate_buyer(text, int, text) from public, anon, authenticated, service_role;
grant execute on function public.deal_rate_buyer(text, int, text) to authenticated, service_role;

-- what suppliers say about a buyer (a company, else a member): average and count, signed-in members only
create or replace function public.buyer_rating(p_company bigint default null, p_user uuid default null) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else (
    select jsonb_build_object('n', count(*), 'avg', round(avg(stars)::numeric, 1))
      from public.deal_ratings r where (p_company is not null and r.buyer_company = p_company) or (p_company is null and p_user is not null and r.buyer_user = p_user and r.buyer_company is null)) end
$$;
revoke all on function public.buyer_rating(bigint, uuid) from public, anon, authenticated, service_role;
grant execute on function public.buyer_rating(bigint, uuid) to authenticated, service_role;

-- ── the trade card (0090) with the upheld reports and the buyer rating ────
create or replace function public.trade_card(p_user uuid) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null or p_user = any (coalesce(private.blocked_parties(), '{}'::uuid[])) then null else (
    select jsonb_build_object(
      'user_id', p.id,
      'member_since', p.created_at,
      'new_account', p.created_at > now() - interval '30 days',
      'profile', (select to_jsonb(t) - 'user_id' from public.trade_profiles t where t.user_id = p.id),
      'offers', (select count(*) from public.products x where x.user_id = p.id and x.status <> 'draft'),
      'offers_active', (select count(*) from public.products x where x.user_id = p.id and x.active and not x.review_hold and (x.expires_at is null or x.expires_at > now())),
      'reports_upheld', (select count(*) from public.trader_reports r where r.reported = p.id and r.status = 'upheld'),
      'buyer_rating', public.buyer_rating(null, p.id),
      'phone_verified', false)
    from public.profiles p where p.id = p_user) end
$$;
revoke all on function public.trade_card(uuid) from public, anon, authenticated, service_role;
grant execute on function public.trade_card(uuid) to authenticated, service_role;

-- ── 3. documents: the trader-reports folder and the broker's authorisation ────
create or replace function public.can_read_document(p_name text)
returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id
                               where a.cv_path = p_name and (j.user_id = auth.uid() or (j.company_id is not null and public.is_company_member(j.company_id, array['owner', 'admin']))))
                   or (exists (select 1 from public.job_seeker_cvs v join public.profiles p on p.id = v.user_id where v.cv_path = p_name and p.open_to_work)
                       and exists (select 1 from public.companies c where c.status = 'verified' and public.is_company_member(c.id)))
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator()
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
    when 'deals' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$' and public.deal_is_party(((storage.foldername(p_name))[2])::bigint)
    when 'listings' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
                   or (auth.uid() is not null and exists (select 1 from public.products p where (p.coa_path = p_name or p.broker_auth_path = p_name) and p.active))
                   or (auth.uid() is not null and exists (select 1 from public.group_listings l where l.broker_auth_path = p_name and not l.review_hold
                                                            and l.group_id in (select public.readable_group_ids())))
    when 'companydocs' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint) or public.is_moderator())
    when 'trader-reports' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
                   or (auth.uid() is not null and exists (select 1 from public.trader_reports r
                        where (r.reported = auth.uid() and p_name = any (r.evidence)) or (r.reporter = auth.uid() and p_name = any (r.reply_evidence))))
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'deals' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$' and public.deal_is_party(((storage.foldername(p_name))[2])::bigint)
    when 'listings' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'companydocs' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$'
                   and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin','regulatory','quality'])
    when 'trader-reports' then (storage.foldername(p_name))[2] = auth.uid()::text
    else false end
$$;
create index if not exists idx_trader_reports_evidence on public.trader_reports using gin (evidence);
create index if not exists idx_trader_reports_reply_evidence on public.trader_reports using gin (reply_evidence);

notify pgrst, 'reload schema';
