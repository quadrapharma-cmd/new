-- 0096 · w-trust: the independent verifier's other findings on 0090–0095 (F5, F7, F8, F11, F13–F16)
--   F5  comments are checked by the W-17 rules too: a comment that reads like a sale to patients / pharmacies, a controlled substance,
--       import for others, sham papers or an outside invite link is not posted, and the member is told why (DX418) — a comment has no
--       review queue of its own; the member can write it again without those words
--   F7  a company that loses the Drugbox badge (pending, rejected, suspended) has its company offers paused / switched off / closed, its
--       owner is told, and none of them goes back on while the company is not verified (DX412)
--   F8  phone_verify_start no longer says whether a number is verified on another account (said on confirm, to whoever got the code),
--       and codes are limited per number across accounts as well as per account
--   F11 a broker's authorisation and a trade report's evidence cannot be deleted while they are used
--   F13 a member removed by a group's admins does not come back through an invite link (DX429); a link stops working once its maker is
--       no longer an admin of the group
--   F14 a partner group that changes its name loses the badge until Drugbox approves it again; Drugbox can withdraw the badge
--   F15 group_activity (the cards' "N posts this week") counts only posts the members can see
--   F16 group_accept_rules no longer answers for a private group the member was not invited to (an invite link is joined by
--       group_join_by_link, which accepts the rules itself)

-- ── F5 comments ────
create or replace function public.comments_review_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or exists (select 1 from public.profiles p where p.id = auth.uid() and p.role in ('admin', 'moderator')) then return new; end if;
  if tg_op = 'UPDATE' and new.body is not distinct from old.body then return new; end if;
  if cardinality(private.review_topics(new.body)) > 0 then
    raise exception 'This comment looks outside Drugbox trade (a sale to patients, pharmacies or the public, controlled substances, import for others, sham papers or an invite link to an outside group) — it was not posted'
      using errcode = 'P0001', hint = 'DX418';
  end if;
  return new;
end $$;
revoke all on function public.comments_review_guard() from public, anon, authenticated, service_role;
grant execute on function public.comments_review_guard() to authenticated, service_role;
drop trigger if exists trg_comments_review_guard on public.comments;
create trigger trg_comments_review_guard before insert or update of body on public.comments for each row execute function public.comments_review_guard();

-- ── F7 a company that loses the badge ────
create or replace function public.company_badge_withdrawn() returns trigger language plpgsql security definer set search_path = public as $$
declare n int := 0; k int;
begin
  update public.products set status = 'paused' where company_id = new.id and posted_as = 'company' and status = 'active'; get diagnostics k = row_count; n := n + k;
  update public.company_listings set active = false where company_id = new.id and active; get diagnostics k = row_count; n := n + k;
  update public.group_listings set status = 'closed' where company_id = new.id and posted_as = 'company' and status = 'open'; get diagnostics k = row_count; n := n + k;
  if new.owner_id is not null and n > 0 then
    insert into public.notifications (user_id, type, from_user, message, data)
    values (new.owner_id, 'company_badge_withdrawn', null, null, jsonb_build_object('company', new.name, 'offers', n));
  end if;
  return null;
end $$;
revoke all on function public.company_badge_withdrawn() from public, anon, authenticated, service_role;
grant execute on function public.company_badge_withdrawn() to service_role;
drop trigger if exists trg_companies_badge_withdrawn on public.companies;
create trigger trg_companies_badge_withdrawn after update of status on public.companies for each row
  when (old.status = 'verified' and new.status is distinct from 'verified') execute function public.company_badge_withdrawn();

-- an offer posted as a company goes (back) on only while the company is verified (an edit of an offer that stays off is fine)
create or replace function public.trade_badge_on_guard() returns trigger language plpgsql set search_path = public as $$
declare n jsonb := to_jsonb(new); o jsonb := to_jsonb(old); turning_on boolean;
begin
  if public.is_server_call() then return new; end if;
  turning_on := case tg_table_name
    when 'products' then n ->> 'posted_as' = 'company' and ((n ->> 'status') = 'active' and (o ->> 'status') is distinct from 'active'
                                                          or (n ->> 'active')::boolean and not coalesce((o ->> 'active')::boolean, false))
    when 'group_listings' then n ->> 'posted_as' = 'company' and (n ->> 'status') = 'open' and (o ->> 'status') is distinct from 'open'
    else (n ->> 'active')::boolean and not coalesce((o ->> 'active')::boolean, false) end;
  if turning_on and not exists (select 1 from public.companies c where c.id = (n ->> 'company_id')::bigint and c.status = 'verified') then
    raise exception 'Only a company page with the Drugbox verification badge posts trade offers as the company — get it verified (free), or post as yourself'
      using errcode = '42501', hint = 'DX412';
  end if;
  return new;
end $$;
revoke all on function public.trade_badge_on_guard() from public, anon, authenticated, service_role;
grant execute on function public.trade_badge_on_guard() to authenticated, service_role;
do $$ declare t text; begin
  foreach t in array array['products', 'company_listings', 'group_listings'] loop
    execute format('drop trigger if exists trg_%s_badge_on on public.%I', t, t);
    execute format('create trigger trg_%s_badge_on before update on public.%I for each row execute function public.trade_badge_on_guard()', t, t);
  end loop;
end $$;

-- ── F8 phone codes ────
alter table private.phone_code_log add column if not exists phone_hash text;
create index if not exists idx_phone_code_log_phone on private.phone_code_log (phone_hash, sent_at desc);
create or replace function public.phone_verify_start(p_phone text) returns jsonb
language plpgsql security definer set search_path = public, extensions as $$
declare me uuid := auth.uid(); ph text := private.phone_norm(p_phone); code text; h text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if private.is_suspended(me) then raise exception 'Your account is suspended' using errcode = '42501'; end if;
  if ph is null then raise exception 'Enter a mobile number (e.g. 010 1234 5678 or +971 50 123 4567)' using errcode = '22023', hint = 'DX440'; end if;
  h := encode(sha256(convert_to('drugbox-phone:' || ph, 'UTF8')), 'hex');
  -- 0096 (F8): whether the number is verified on another account is said only on confirm, to whoever got the code
  if (select count(*) from private.phone_code_log l where l.user_id = me and l.sent_at > now() - interval '1 hour') >= 3
     or (select count(*) from private.phone_code_log l where l.user_id = me and l.sent_at > now() - interval '1 day') >= 6
     or (select count(*) from private.phone_code_log l where l.phone_hash = h and l.sent_at > now() - interval '1 hour') >= 3   -- per number, every account together
     or (select count(*) from private.phone_code_log l where l.phone_hash = h and l.sent_at > now() - interval '1 day') >= 5 then
    raise exception 'Too many codes — try again later' using errcode = 'P0001', hint = 'DX442'; end if;
  code := lpad((floor(random() * 1000000))::int::text, 6, '0');
  insert into private.phone_codes (user_id, phone, code_hash, tries, expires_at)
  values (me, ph, encode(sha256(convert_to(me::text || ':' || code, 'UTF8')), 'hex'), 0, now() + interval '10 minutes')
  on conflict (user_id) do update set phone = excluded.phone, code_hash = excluded.code_hash, tries = 0, expires_at = excluded.expires_at;
  insert into private.phone_code_log (user_id, phone_hash) values (me, h);
  insert into private.sms_outbox (phone, body) values (ph, 'Drugbox code: ' || code || ' — رمز Drugbox: ' || code || '. It expires in 10 minutes.');
  return jsonb_build_object('sent', true, 'to', left(ph, 4) || repeat('•', greatest(char_length(ph) - 6, 0)) || right(ph, 2), 'minutes', 10);
end $$;
revoke all on function public.phone_verify_start(text) from public, anon, authenticated, service_role;
grant execute on function public.phone_verify_start(text) to authenticated, service_role;

-- ── F11 files in use ────
create or replace function public.document_in_use(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.deal_files where path = p_name)
      or exists (select 1 from public.company_documents where file_path = p_name)
      or exists (select 1 from public.site_certificates where file_path = p_name)
      or exists (select 1 from public.verification_requests where p_name in (registry_path, tax_card_path, licence_path))
      or exists (select 1 from public.job_applications where cv_path = p_name)
      or exists (select 1 from public.products where coa_path = p_name or broker_auth_path = p_name)        -- 0096 (F11): a broker's authorisation
      or exists (select 1 from public.group_listings where broker_auth_path = p_name)
      or exists (select 1 from public.trader_reports where p_name = any(evidence) or p_name = any(reply_evidence))   -- a report's evidence
      or exists (select 1 from public.payment_orders where receipt_path = p_name)
$$;
revoke all on function public.document_in_use(text) from public, anon, authenticated, service_role;
grant execute on function public.document_in_use(text) to authenticated, service_role;

-- ── F13 removed members, links of former admins ────
create table if not exists private.group_removals (
  group_id   bigint not null,
  user_id    uuid not null,
  removed_by uuid,
  removed_at timestamptz not null default now(),
  primary key (group_id, user_id)
);
revoke all on table private.group_removals from public, anon, authenticated;
grant select, insert, update, delete on table private.group_removals to service_role;
create or replace function public.group_members_removed() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'DELETE' then
    -- removed by someone else (an admin, Drugbox) while the group stays; leaving by oneself is not a removal
    if auth.uid() is not null and auth.uid() <> old.user_id and exists (select 1 from public.groups g where g.id = old.group_id) then
      insert into private.group_removals (group_id, user_id, removed_by) values (old.group_id, old.user_id, auth.uid())
      on conflict (group_id, user_id) do update set removed_by = excluded.removed_by, removed_at = now();
    end if;
    return null;
  end if;
  delete from private.group_removals where group_id = new.group_id and user_id = new.user_id;   -- added back by the admins
  return null;
end $$;
revoke all on function public.group_members_removed() from public, anon, authenticated, service_role;
grant execute on function public.group_members_removed() to service_role;
drop trigger if exists trg_group_members_removed on public.group_members;
create trigger trg_group_members_removed after insert or delete on public.group_members for each row execute function public.group_members_removed();
create or replace function private.link_maker_ok(l public.group_invite_links) returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.group_members m where m.group_id = l.group_id and m.user_id = l.created_by and m.role in ('admin', 'moderator'))
      or exists (select 1 from public.profiles p where p.id = l.created_by and p.role in ('admin', 'moderator'))
$$;
revoke all on function private.link_maker_ok(public.group_invite_links) from public, anon, authenticated, service_role;
grant execute on function private.link_maker_ok(public.group_invite_links) to authenticated, service_role;
create or replace function public.group_join_by_link(p_token text, p_accept_rules boolean default false) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); l public.group_invite_links; g public.groups;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if private.is_suspended(me) then raise exception 'Your account is suspended' using errcode = '42501'; end if;
  select * into l from public.group_invite_links where token = p_token for update;
  if l.id is null then raise exception 'This invite link is not valid — check that you copied all of it' using errcode = 'P0002', hint = 'DX427'; end if;
  select * into g from public.groups where id = l.group_id;
  if l.revoked_at is not null or (l.expires_at is not null and l.expires_at <= now()) or (l.max_uses is not null and l.uses >= l.max_uses) or g.archived_at is not null
     or not private.link_maker_ok(l) then
    raise exception 'This invite link no longer works — ask the group''s admin for a new one' using errcode = '42501', hint = 'DX428'; end if;
  if exists (select 1 from public.group_members m where m.group_id = g.id and m.user_id = me) then return 'already'; end if;
  if exists (select 1 from private.group_removals r where r.group_id = g.id and r.user_id = me) then        -- 0096 (F13)
    raise exception 'The group''s admins removed you from this group — ask them to add you again' using errcode = '42501', hint = 'DX429'; end if;
  if exists (select 1 from public.user_blocks b join public.group_members m on m.user_id = b.blocker
              where m.group_id = g.id and m.role = 'admin' and b.blocked = me) then
    raise exception 'You cannot join this group' using errcode = '42501'; end if;
  if g.rules_required then
    if not coalesce(p_accept_rules, false) then raise exception 'Read and accept the group''s rules first' using errcode = '42501', hint = 'DX425'; end if;
    insert into public.group_rule_acceptances (group_id, user_id) values (g.id, me) on conflict (group_id, user_id) do update set accepted_at = now();
  end if;
  insert into public.group_members (group_id, user_id, role) values (g.id, me, 'member') on conflict do nothing;
  delete from public.group_join_requests where group_id = g.id and user_id = me;
  update public.group_invite_links set uses = uses + 1 where id = l.id;
  return 'member';
end $$;
revoke all on function public.group_join_by_link(text, boolean) from public, anon, authenticated, service_role;
grant execute on function public.group_join_by_link(text, boolean) to authenticated, service_role;
create or replace function public.group_link_preview(p_token text) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else (
    select jsonb_build_object('group_id', g.id, 'name', g.name, 'emoji', g.emoji, 'description', g.description, 'type', g.type, 'rules', g.rules,
                              'rules_required', g.rules_required, 'member_count', g.member_count, 'partner', g.partner_at is not null,
                              'member', public.is_group_member(g.id),
                              'ok', l.revoked_at is null and (l.expires_at is null or l.expires_at > now()) and (l.max_uses is null or l.uses < l.max_uses) and g.archived_at is null and private.link_maker_ok(l)
                                    and not exists (select 1 from private.group_removals r where r.group_id = g.id and r.user_id = auth.uid()))
      from public.group_invite_links l join public.groups g on g.id = l.group_id where l.token = p_token) end
$$;
revoke all on function public.group_link_preview(text) from public, anon, authenticated, service_role;
grant execute on function public.group_link_preview(text) to authenticated, service_role;

-- ── F14 partner badge ────
create or replace function public.groups_partner_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then new.partner_at := null; elsif new.partner_at is distinct from old.partner_at then new.partner_at := old.partner_at; end if;
  -- 0096 (F14): Drugbox approved the group under its name — a new name asks again (the badge is not carried to "Drugbox Official …")
  if tg_op = 'UPDATE' and old.partner_at is not null and new.name is distinct from old.name then new.partner_at := null; end if;
  return new;
end $$;
revoke all on function public.groups_partner_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_partner_guard() to authenticated, service_role;
alter table public.group_partner_requests drop constraint if exists group_partner_requests_status_check;
alter table public.group_partner_requests add constraint group_partner_requests_status_check check (status in ('pending', 'approved', 'rejected', 'withdrawn'));
create or replace function public.group_partner_withdraw(p_group bigint, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare v_note text := nullif(left(btrim(coalesce(p_note, '')), 500), ''); g public.groups;
begin
  if not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into g from public.groups where id = p_group for update;
  if g.id is null or g.partner_at is null then raise exception 'This group is not a partner group' using errcode = 'P0002'; end if;
  update public.groups set partner_at = null where id = p_group;
  update public.group_partner_requests set status = 'withdrawn', decided_by = auth.uid(), decision_note = v_note, decided_at = now() where group_id = p_group;
  insert into public.notifications (user_id, type, from_user, group_id, message, data)
  select m.user_id, 'group_partner_decided', null, p_group, null, jsonb_strip_nulls(jsonb_build_object('outcome', 'withdrawn', 'group', g.name, 'note', v_note))
    from public.group_members m where m.group_id = p_group and m.role = 'admin';
  perform private.log_decision('partner', p_group::text, left(coalesce(g.name, 'Group'), 300), 'withdrawn', v_note, null);
  return 'withdrawn';
end $$;
revoke all on function public.group_partner_withdraw(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.group_partner_withdraw(bigint, text) to authenticated, service_role;

-- ── F15 group activity counts what members see ────
create or replace function public.group_activity(p_ids bigint[])
returns table (group_id bigint, posts_today int, posts_week int, last_post_at timestamptz)
language sql stable security definer set search_path = public as $$
  select g.id,
         (select count(*)::int from (select 1 from public.posts p where p.group_id = g.id and not p.review_hold and not p.group_pending and p.created_at >= date_trunc('day', now()) limit 1000) x),
         (select count(*)::int from (select 1 from public.posts p where p.group_id = g.id and not p.review_hold and not p.group_pending and p.created_at >= now() - interval '7 days' limit 1000) x),
         (select max(p.created_at) from public.posts p where p.group_id = g.id and not p.review_hold and not p.group_pending)
    from public.groups g
   where auth.uid() is not null and g.id = any(p_ids[1:100])
     and (g.type = 'public' or g.listed or g.created_by = auth.uid() or public.is_group_member(g.id)
          or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = auth.uid()))
$$;
revoke all on function public.group_activity(bigint[]) from public, anon, authenticated, service_role;
grant execute on function public.group_activity(bigint[]) to authenticated, service_role;

-- ── F16 accepting a group's rules needs a group the member can see ────
create or replace function public.group_accept_rules(p_group bigint) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not exists (select 1 from public.groups g where g.id = p_group and g.archived_at is null
                   and (g.type = 'public' or g.listed or public.is_group_member(g.id)
                        or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = auth.uid()))) then
    raise exception 'Group not found' using errcode = 'P0002'; end if;
  insert into public.group_rule_acceptances (group_id, user_id) values (p_group, auth.uid())
  on conflict (group_id, user_id) do update set accepted_at = now();
end $$;
revoke all on function public.group_accept_rules(bigint) from public, anon, authenticated, service_role;
grant execute on function public.group_accept_rules(bigint) to authenticated, service_role;

notify pgrst, 'reload schema';
