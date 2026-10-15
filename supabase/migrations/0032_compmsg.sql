-- ═════════════════════════════════════════════════════════════════════
-- 0032 — talking to a company from its page reaches a real person (B-05, J-BUSINESS-06)
--   A company page's "Message" / "Send a message" opened a window addressed to "<Company> team" in the live app: the team and
--   the request routing (company_routing) are readable only by the company's own members, so a buyer's browser never knew who
--   answers, and nothing could be sent. This adds:
--   1. company_contacts(company): who answers each kind of request at a company (quote, service, surplus, group, dossier,
--      questionnaire, job — the approved "Who answers" / "Who receives what" sections) — the person
--      the company routed that kind of request to (while still on the team AND listed publicly: a member who did not agree to be
--      shown is never named — Law 151/2020), else the page's owner, else the first publicly listed owner/admin. Only the id,
--      name and role of that one person per kind are returned; the team list and the routing table stay members-only. The
--      company's own members (who can read the team anyway) see the routing exactly as the deals engine uses it
--      (deal_receiver: unlisted members included) — the workspace's "Who receives what".
--      Nobody (unclaimed page, suspended page) → null for that kind.
--   2. company_message(company, body): the buyer's message goes to that quote contact, chosen by the database (never by a name
--      or an id the browser sends), as an ordinary direct message (it appears in Messages for both); the receiver also gets one
--      notification "messaged <Company>" per sender and company per day (so a conversation does not flood notifications).
--   Both are SECURITY DEFINER, signed-in members only (granted explicitly — 0026's rule).
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- the person who answers one kind of request at a company (internal: no grant to the API roles); p_team: as the company's own
-- members see it (unlisted members too)
create or replace function public.company_answerer(p_company bigint, p_type text, p_team boolean default false)
returns table (user_id uuid, role text) language sql stable security definer set search_path = public as $$
  with c as (select id, owner_id from public.companies where id = p_company and status is distinct from 'suspended')
  select x.user_id, x.role from (
    -- 1. routed, still on the team, and publicly listed (or the owner)
    select r.user_id, case when r.user_id = c.owner_id then 'owner' else m.role end as role, 1 as rank, now() as at
      from c join public.company_routing r on r.company_id = c.id
             and r.request_type = case p_type when 'group' then 'group_order' else p_type end
        left join public.company_members m on m.company_id = c.id and m.user_id = r.user_id
     where r.user_id = c.owner_id or (m.accepted and (m.show_public or p_team))
    union all
    -- 2. the page's owner
    select c.owner_id, 'owner', 2, now() from c where c.owner_id is not null
    union all
    -- 3. the first publicly listed owner/admin
    select m.user_id, m.role, 3, m.created_at from c join public.company_members m on m.company_id = c.id
     where m.role in ('owner', 'admin') and m.accepted and (m.show_public or p_team)
  ) x join public.profiles p on p.id = x.user_id
  order by x.rank, x.at limit 1
$$;
revoke all on function public.company_answerer(bigint, text, boolean) from public, anon, authenticated, service_role;
grant execute on function public.company_answerer(bigint, text, boolean) to service_role;

-- who answers at a company, per kind of request: {"quote": {"id", "name", "role"} | null, "service": …, …, "job": …}
create or replace function public.company_contacts(p_company bigint) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_object_agg(k.kind, (select jsonb_build_object('id', a.user_id, 'name', p.name, 'role', a.role)
                                     from public.company_answerer(p_company, k.kind, public.is_company_member(p_company)) a
                                     join public.profiles p on p.id = a.user_id))
    from (values ('quote'), ('service'), ('surplus'), ('group'), ('dossier'), ('questionnaire'), ('job')) k(kind)
   where (select auth.uid()) is not null
$$;
revoke all on function public.company_contacts(bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_contacts(bigint) to authenticated, service_role;

-- a message to a company: delivered to its quote contact (+ one notification a day per sender and company)
create or replace function public.company_message(p_company bigint, p_body text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  me uuid := (select auth.uid());
  v_to uuid; v_name text; v_id bigint; v_note text;
  v_body text := btrim(coalesce(p_body, ''));
begin
  if me is null then raise exception 'Sign in to send a message' using errcode = '42501'; end if;
  if v_body = '' then raise exception 'Write a message first' using errcode = '22023'; end if;
  select a.user_id into v_to from public.company_answerer(p_company, 'quote') a;
  select name into v_name from public.companies where id = p_company;
  if v_to is null then
    raise exception 'Nobody at % answers messages on Drugbox yet — use the phone, email or WhatsApp on its Contact tab', coalesce(v_name, 'this company')
      using errcode = 'P0002';
  end if;
  if v_to = me then raise exception 'You answer this company''s messages yourself' using errcode = '22023'; end if;
  insert into public.messages (sender_id, receiver_id, body) values (me, v_to, v_body) returning id into v_id;
  v_note := 'messaged ' || v_name || ': "' || left(v_body, 80) || case when length(v_body) > 80 then '…' else '' end || '"';
  if not exists (select 1 from public.notifications n where n.user_id = v_to and n.from_user = me and n.type = 'company_message'
                   and n.created_at > now() - interval '1 day' and n.message like 'messaged ' || replace(replace(replace(v_name, '\', '\\'), '%', '\%'), '_', '\_') || ': %') then
    insert into public.notifications (user_id, type, from_user, message) values (v_to, 'company_message', me, v_note);
  end if;
  return jsonb_build_object('id', v_id, 'to', v_to);
end $$;
revoke all on function public.company_message(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.company_message(bigint, text) to authenticated, service_role;

notify pgrst, 'reload schema';
