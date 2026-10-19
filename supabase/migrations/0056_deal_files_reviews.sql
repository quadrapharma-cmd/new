-- ═════════════════════════════════════════════════════════════════════
-- 0056 — the paperwork and the reviews of a deal (B-12, B-17; J-BUSINESS-07, 08, 24, 26, 28, 29)
--   1. deal_files: documents inside a deal (PO, CoA, invoice, specification, NDA, data room, deliverables, questionnaire evidence,
--      the CV of a job application).
--      The file is in the private documents bucket under deals/<deal id>/…; only the two parties of the deal (the sender — the
--      person for a job application, else the sending company's team — and the receiving company's team) can list it, upload to
--      it or open it (signed links). deal_attach() records it, adds a "Document attached" step to the deal's history and tells
--      the other side. Nothing about a deal's files is visible to anyone else (group deals included).
--   2. Reviews of completed orders (the deal's "rate" step): company_reviews(company) lists them for the public page and the
--      workspace; the company answers publicly (review_reply), or asks Drugbox to check one (review_dispute — it stays visible
--      meanwhile); Drugbox keeps or removes it (review_decide, Admin → Review → Reviews) and both sides are told. A removed review
--      counts in no rating (company_ratings, company_track_record).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- the two parties of a deal (as deal_act decides them)
create or replace function public.deal_is_party(p_deal bigint) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.deals d where d.id = p_deal and auth.uid() is not null and (
      public.is_company_member(d.to_company_id)
   or (d.from_company_id is null and d.from_user = auth.uid())
   or (d.from_company_id is not null and public.is_company_member(d.from_company_id))))
$$;
revoke all on function public.deal_is_party(bigint) from public, anon, authenticated, service_role;
grant execute on function public.deal_is_party(bigint) to authenticated, service_role;

create table if not exists public.deal_files (
  id          bigint generated always as identity primary key,
  deal_id     bigint not null references public.deals(id) on delete cascade,
  uploader    uuid references public.profiles(id) on delete set null,
  side        text not null check (side in ('from', 'to')),
  kind        text not null check (kind in ('PO', 'CoA', 'Invoice', 'Specification', 'NDA', 'Data room', 'Deliverable', 'Questionnaire evidence', 'CV', 'Other')),
  name        text not null check (length(name) between 1 and 160),
  path        text not null unique check (length(path) <= 300),
  created_at  timestamptz not null default now()
);
create index if not exists idx_deal_files_deal on public.deal_files (deal_id, created_at);
create index if not exists idx_deal_files_uploader on public.deal_files (uploader) where uploader is not null;
alter table public.deal_files enable row level security;
do $$ begin
  create policy "deal files: the two parties read" on public.deal_files for select to authenticated using (public.deal_is_party(deal_id));
exception when duplicate_object then null; end $$;
revoke all on public.deal_files from public, anon, authenticated;
grant select on public.deal_files to authenticated;
grant all on public.deal_files to service_role;

create or replace function public.deal_attach(p_ref text, p_kind text, p_path text, p_name text)
returns bigint language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; v_side text; v_id bigint; notify uuid; v_name text := left(trim(coalesce(p_name, '')), 160);
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref;
  if d.id is null then raise exception 'Request not found' using errcode = 'P0002'; end if;
  if public.is_company_member(d.to_company_id) then v_side := 'to';
  elsif (d.from_company_id is null and d.from_user = me) or (d.from_company_id is not null and public.is_company_member(d.from_company_id)) then v_side := 'from';
  else raise exception 'You are not part of this request' using errcode = '42501'; end if;
  if v_name = '' then raise exception 'The file has no name' using errcode = '22023'; end if;
  if p_path is null or p_path !~ ('^deals/' || d.id::text || '/[A-Za-z0-9._-]{1,120}$')
     or not exists (select 1 from storage.objects o where o.bucket_id = 'documents' and o.name = p_path and o.owner = me) then
    raise exception 'Upload the file to this deal first' using errcode = '42501';
  end if;
  if (select count(*) from public.deal_files where deal_id = d.id) >= 50 then raise exception 'A deal holds up to 50 documents' using errcode = '54000'; end if;
  insert into public.deal_files (deal_id, uploader, side, kind, name, path)
  values (d.id, me, v_side, case when p_kind in ('PO', 'CoA', 'Invoice', 'Specification', 'NDA', 'Data room', 'Deliverable', 'Questionnaire evidence', 'CV') then p_kind else 'Other' end, v_name, p_path)
  returning id into v_id;
  insert into public.deal_events (deal_id, side, action, note, data, actor)
  values (d.id, v_side, 'file', p_kind || ': ' || v_name, jsonb_build_object('text', coalesce(nullif(p_kind, ''), 'Other') || ': ' || v_name, 'file', v_id), me);
  update public.deals set updated_at = now() where id = d.id;
  notify := case when v_side = 'to' then
              (case when d.from_company_id is null or public.company_has_member(d.from_company_id, d.from_user) then d.from_user else public.deal_receiver(d.from_company_id, d.type) end)
            else coalesce(d.assignee, public.deal_receiver(d.to_company_id, d.type)) end;
  if notify is not null and notify <> me then
    insert into public.notifications (user_id, type, from_user, message) values (notify, 'deal', me, d.title || ' — document attached: ' || v_name);
  end if;
  return v_id;
end $$;
revoke all on function public.deal_attach(text, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.deal_attach(text, text, text, text) to authenticated, service_role;

-- documents bucket: deals/<deal id>/… for the two parties (the cases before are 0052's)
create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_moderator()
                        or (storage.filename(p_name) like 'cert-%' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['quality'])))
    when 'payments' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_platform_admin()
    when 'claims' then (storage.foldername(p_name))[2] = auth.uid()::text or public.is_moderator()
    when 'deals' then (storage.foldername(p_name))[2] ~ '^\d{1,18}$' and public.deal_is_party(((storage.foldername(p_name))[2])::bigint)
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
    else false end
$$;

-- ── reviews of completed orders ────
create table if not exists public.review_responses (
  deal_id      bigint primary key references public.deals(id) on delete cascade,
  reply        text check (length(reply) <= 1000),
  replied_by   uuid references public.profiles(id) on delete set null,
  replied_at   timestamptz,
  disputed_at  timestamptz,
  dispute_note text check (length(dispute_note) <= 500),
  disputed_by  uuid references public.profiles(id) on delete set null,
  decision     text check (decision in ('kept', 'removed')),
  decided_by   uuid references public.profiles(id) on delete set null,
  decided_at   timestamptz
);
create index if not exists idx_review_resp_open on public.review_responses (disputed_at) where disputed_at is not null and decision is null;
create index if not exists idx_review_resp_replied_by on public.review_responses (replied_by) where replied_by is not null;
create index if not exists idx_review_resp_disputed_by on public.review_responses (disputed_by) where disputed_by is not null;
create index if not exists idx_review_resp_decided_by on public.review_responses (decided_by) where decided_by is not null;
alter table public.review_responses enable row level security;
do $$ begin
  create policy "review responses: Drugbox reads" on public.review_responses for select to authenticated using (public.is_moderator());
exception when duplicate_object then null; end $$;
revoke all on public.review_responses from public, anon, authenticated;
grant select on public.review_responses to authenticated;
grant all on public.review_responses to service_role;

-- the reviews of a company, as its page shows them (a removed one is not shown; the dispute note stays with Drugbox)
create or replace function public.company_reviews(p_company bigint) returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('ref', d.ref, 'stars', (e.data ->> 'stars')::int, 'note', coalesce(nullif(e.data ->> 'note', ''), e.note, ''),
           'from', coalesce(fc.name, 'A Drugbox member'), 'at', e.created_at, 'reply', rr.reply, 'disputed', rr.disputed_at is not null and rr.decision is null) order by e.created_at desc), '[]'::json)
  from public.deals d join public.deal_events e on e.deal_id = d.id and e.action = 'rate'
  left join public.companies fc on fc.id = d.from_company_id
  left join public.review_responses rr on rr.deal_id = d.id
  where d.to_company_id = p_company and d.type <> 'job' and auth.uid() is not null and coalesce(rr.decision, 'kept') <> 'removed'
$$;
revoke all on function public.company_reviews(bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_reviews(bigint) to authenticated, service_role;

create or replace function public.review_reply(p_ref text, p_reply text) returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; v text := nullif(left(trim(coalesce(p_reply, '')), 1000), '');
begin
  select * into d from public.deals where ref = p_ref;
  if d.id is null or not exists (select 1 from public.deal_events e where e.deal_id = d.id and e.action = 'rate') then raise exception 'This review does not exist' using errcode = 'P0002'; end if;
  if me is null or not public.is_company_member(d.to_company_id, array['owner','admin','management','sales']) then raise exception 'Only the company''s owner, admins, management or sales can reply' using errcode = '42501'; end if;
  if v is null then raise exception 'Write the reply' using errcode = '22023'; end if;
  insert into public.review_responses (deal_id, reply, replied_by, replied_at) values (d.id, v, me, now())
  on conflict (deal_id) do update set reply = excluded.reply, replied_by = excluded.replied_by, replied_at = now();
  if d.from_user is not null and d.from_user <> me then
    insert into public.notifications (user_id, type, from_user, company_id, data)
    values (d.from_user, 'review_reply', me, d.to_company_id, jsonb_build_object('company', (select name from public.companies where id = d.to_company_id), 'title', d.title));
  end if;
  return true;
end $$;
revoke all on function public.review_reply(text, text) from public, anon, authenticated, service_role;
grant execute on function public.review_reply(text, text) to authenticated, service_role;

create or replace function public.review_dispute(p_ref text, p_note text default null) returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals;
begin
  select * into d from public.deals where ref = p_ref;
  if d.id is null or not exists (select 1 from public.deal_events e where e.deal_id = d.id and e.action = 'rate') then raise exception 'This review does not exist' using errcode = 'P0002'; end if;
  if me is null or not public.is_company_member(d.to_company_id, array['owner','admin']) then raise exception 'Only the company''s owner or admins can ask Drugbox to check a review' using errcode = '42501'; end if;
  insert into public.review_responses (deal_id, disputed_at, dispute_note, disputed_by) values (d.id, now(), nullif(left(trim(coalesce(p_note, '')), 500), ''), me)
  on conflict (deal_id) do update set disputed_at = coalesce(review_responses.disputed_at, now()), dispute_note = coalesce(excluded.dispute_note, review_responses.dispute_note),
    disputed_by = coalesce(review_responses.disputed_by, excluded.disputed_by)
  where review_responses.decision is null;
  return true;
end $$;
revoke all on function public.review_dispute(text, text) from public, anon, authenticated, service_role;
grant execute on function public.review_dispute(text, text) to authenticated, service_role;

create or replace function public.review_decide(p_ref text, p_keep boolean, p_note text default null) returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); d public.deals; v_co text; u uuid;
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into d from public.deals where ref = p_ref;
  if d.id is null then raise exception 'This review does not exist' using errcode = 'P0002'; end if;
  update public.review_responses set decision = case when p_keep then 'kept' else 'removed' end, decided_by = me, decided_at = now()
   where deal_id = d.id and disputed_at is not null and decision is null;
  if not found then return false; end if;                                   -- decided already (another moderator, another tab)
  select name into v_co from public.companies where id = d.to_company_id;
  for u in select x from (select d.from_user as x union select owner_id from public.companies where id = d.to_company_id) y where x is not null loop
    insert into public.notifications (user_id, type, from_user, company_id, data)
    values (u, 'review_decided', null, d.to_company_id, jsonb_build_object('company', v_co, 'outcome', case when p_keep then 'kept' else 'removed' end, 'note', nullif(left(trim(coalesce(p_note, '')), 300), '')));
  end loop;
  return true;
end $$;
revoke all on function public.review_decide(text, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.review_decide(text, boolean, text) to authenticated, service_role;

-- the queue: reviews companies asked Drugbox to check
create or replace function public.review_disputes() returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('ref', d.ref, 'company', tc.name, 'from', fc.name, 'stars', (e.data ->> 'stars')::int, 'note', coalesce(nullif(e.data ->> 'note', ''), e.note, ''),
           'dispute', rr.dispute_note, 'at', rr.disputed_at) order by rr.disputed_at), '[]'::json)
  from public.review_responses rr join public.deals d on d.id = rr.deal_id join public.deal_events e on e.deal_id = d.id and e.action = 'rate'
  join public.companies tc on tc.id = d.to_company_id left join public.companies fc on fc.id = d.from_company_id
  where rr.disputed_at is not null and rr.decision is null and public.is_moderator()
$$;
revoke all on function public.review_disputes() from public, anon, authenticated, service_role;
grant execute on function public.review_disputes() to authenticated, service_role;

-- a removed review counts in no rating
create or replace function public.company_ratings(p_ids bigint[])
returns table (company_id bigint, rating numeric, reviews int)
language plpgsql stable security definer set search_path = public set plan_cache_mode = force_generic_plan as $$
#variable_conflict use_column
begin
  return query
  select d.to_company_id, round(avg((e.data ->> 'stars')::numeric), 1), count(*)::int
  from public.deals d join public.deal_events e on e.deal_id = d.id and e.action = 'rate'
  where d.to_company_id = any(p_ids) and d.type <> 'job'
    and not exists (select 1 from public.company_members a join public.company_members b on b.user_id = a.user_id
                    where a.company_id = d.to_company_id and a.accepted and b.company_id = d.from_company_id and b.accepted)
    and not exists (select 1 from public.review_responses rr where rr.deal_id = d.id and rr.decision = 'removed')   -- a review Drugbox removed counts nowhere
  group by d.to_company_id;
end $$;

create or replace function public.company_track_record(p_company bigint) returns json language sql stable security definer set search_path = public as $$
  with recv as (
    select d.*, (select min(e.created_at) from public.deal_events e where e.deal_id = d.id and e.side = 'to') as first_reply
    from public.deals d where d.to_company_id = p_company and d.type <> 'job'
      and not exists (select 1 from public.company_members a join public.company_members b on b.user_id = a.user_id
                      where a.company_id = p_company and a.accepted and b.company_id = d.from_company_id and b.accepted)),
  asked as (select * from recv where group_of is null),
  done as (select * from recv where type in ('quote','surplus','service') and status in ('delivered','closed')),
  rated as (select e.* from public.deal_events e join recv x on x.id = e.deal_id where e.action = 'rate'
              and not exists (select 1 from public.review_responses rr where rr.deal_id = e.deal_id and rr.decision = 'removed'))
  select json_build_object(
    'orders',    (select count(*) from done),
    'ontime',    (select round(100.0 * count(*) filter (where ontime is not false) / nullif(count(*), 0)) from done),
    'rating',    (select round(avg((data ->> 'stars')::numeric), 1) from rated),
    'reviews',   (select count(*) from rated),
    'response',  (select round((percentile_cont(0.5) within group (order by extract(epoch from (first_reply - created_at)) / 3600))::numeric, 1) from asked where first_reply is not null),
    'requests',  (select count(*) from asked),
    'answered',  (select count(*) from asked where first_reply is not null))
$$;

notify pgrst, 'reload schema';
