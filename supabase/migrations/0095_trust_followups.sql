-- 0095 · w-trust: held offers are out of reach until Drugbox decides (independent verification of 0090–0094)
-- A held offer (0091 review_hold) was hidden from reads by the restrictive policies, but the security-definer actions on an offer read the
-- row themselves: anyone with its id could still answer a held deal-room listing (a deal titled with the held words), message the owner
-- about a held marketplace offer, quote on a held request or count a view. Each now treats a held offer as not there (the same answer as a
-- missing one — nothing about the hold leaks). Bodies are 0054 / 0061 with that one condition added.

-- ── 1. held offers: the actions on an offer treat a held one as not there ────
create or replace function public.listing_view(p_id bigint) returns boolean language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); v_owner uuid;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select user_id into v_owner from public.products where id = p_id and active and not review_hold;   -- w-trust: a held offer is not there for others
  if v_owner is null or v_owner = me then return false; end if;
  insert into public.listing_views (listing_id, viewer) values (p_id, me) on conflict do nothing;
  return found;
end $$;
revoke all on function public.listing_view(bigint) from public, anon, authenticated, service_role;
grant execute on function public.listing_view(bigint) to authenticated, service_role;

create or replace function public.listing_contact(p_id bigint, p_body text) returns bigint language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p record; v_body text := left(trim(coalesce(p_body, '')), 3800); mid bigint;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select id, user_id, name, type into p from public.products where id = p_id and active and not review_hold;   -- w-trust: as if it were not there
  if p.id is null then raise exception 'This listing is not available any more' using errcode = 'P0002'; end if;
  if p.user_id = me then raise exception 'This is your own listing' using errcode = '22023'; end if;
  if v_body = '' then raise exception 'Write a message' using errcode = '22023'; end if;
  if exists (select 1 from public.user_blocks b where (b.blocker = p.user_id and b.blocked = me) or (b.blocker = me and b.blocked = p.user_id)) then
    raise exception 'You cannot message this member' using errcode = '42501';
  end if;
  insert into public.messages (sender_id, receiver_id, body)
  values (me, p.user_id, 'Re: ' || p.name || ' (listing #' || p.id || ')' || chr(10) || v_body) returning id into mid;
  insert into public.listing_inquiries (listing_id, user_id) values (p.id, me) on conflict do nothing;
  return mid;
end $$;
revoke all on function public.listing_contact(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.listing_contact(bigint, text) to authenticated, service_role;

create or replace function public.listing_quote(p_id bigint, p_from_slug text, p_price text, p_qty text default null, p_lead text default null, p_note text default null)
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); p record; v_sup public.companies; v_buyer bigint; d public.deals; v_price text := nullif(left(trim(coalesce(p_price, '')), 60), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into p from public.products where id = p_id and active and not review_hold and type = 'demand';   -- w-trust
  if p.id is null then raise exception 'This request is not open any more' using errcode = 'P0002'; end if;
  if v_price is null or v_price !~ '\d' then raise exception 'Enter your price' using errcode = '22023'; end if;
  select * into v_sup from public.companies where slug = p_from_slug;
  if v_sup.id is null or not public.is_company_member(v_sup.id) then raise exception 'Quote on behalf of a company you belong to — create or claim your company page first' using errcode = '42501'; end if;
  if v_sup.status = 'suspended' then raise exception 'Your company is suspended and cannot send quotes' using errcode = '42501'; end if;
  if p.user_id = me then raise exception 'This is your own request' using errcode = '22023'; end if;
  -- the buyer's company: the one the request was posted for, else the buyer's own page
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

create or replace function public.group_listing_respond(p_listing bigint, p_from_slug text, p_message text default '', p_price text default null, p_lead text default null)
returns text language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); l public.group_listings; to_slug text; d public.deals; t text;
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  select * into l from public.group_listings where id = p_listing;
  if l.id is null or l.review_hold then raise exception 'This listing is no longer available' using errcode = 'P0002'; end if;
  if not public.is_group_member(l.group_id) then raise exception 'Join the group to answer its listings' using errcode = '42501'; end if;
  if l.status <> 'open' or not private.group_open(l.group_id) then raise exception 'This listing is closed' using errcode = '42501'; end if;
  if l.user_id = me then raise exception 'This is your own listing' using errcode = '42501'; end if;
  if exists (select 1 from public.group_listing_responses r where r.listing_id = l.id and r.user_id = me) then
    raise exception 'You already answered this listing — follow it in your Deals' using errcode = '23505'; end if;
  select c.slug into to_slug from public.companies c where c.id = l.company_id;
  if to_slug is null then raise exception 'This listing has no company page — message its author instead' using errcode = '42501'; end if;
  t := left(l.title, 160);
  d := public.deal_create(case when l.kind = 'rfq' then 'surplus' else 'quote' end, to_slug, p_from_slug, t,
         jsonb_strip_nulls(jsonb_build_object('listing', l.id, 'group', l.group_id, 'price', nullif(left(coalesce(p_price, ''), 60), ''), 'lead', nullif(left(coalesce(p_lead, ''), 60), ''))),
         left(coalesce(p_message, ''), 600));
  -- the deals engine told the listing's company with the bare title: say what came in and from where
  update public.notifications n set message = left(case when l.kind = 'rfq' then 'sent an offer for your request "' else 'sent a quote request for your listing "' end
           || t || '" in the deal room "' || coalesce((select g.name from public.groups g where g.id = l.group_id), '') || '"', 400),
         data = coalesce(n.data, '{}'::jsonb) || jsonb_build_object('deal', d.ref, 'listing', l.id)
   where n.id = (select max(x.id) from public.notifications x where x.type = 'deal' and x.from_user = me and x.user_id = d.assignee and x.message = t);
  insert into public.group_listing_responses (listing_id, user_id, deal_ref) values (l.id, me, d.ref);
  update public.group_listings set responses = responses + 1 where id = l.id;
  return d.ref;
end $$;
revoke all on function public.group_listing_respond(bigint, text, text, text, text) from public, anon, authenticated, service_role;
grant execute on function public.group_listing_respond(bigint, text, text, text, text) to authenticated, service_role;


-- ── 2. W-17 rules, second version (the verifier's phrase table: 11 ordinary trade phrases were held, 22 sensitive spellings passed) ────
-- the text is compared after NFKC (full-width and Arabic presentation forms read as plain letters), with more invisible characters
-- dropped (U+061C, U+2060…, variation selectors) and dots written apart ("chat.whatsapp .com", "chat[.]whatsapp[.]com", " dot ") joined;
-- a rule marked `squashed` reads the text with no spaces or punctuation and 0 1 3 4 5 7 as o i e a s t ("t r a m a d o l", "tramad0l")
alter table private.review_rules add column if not exists squashed boolean not null default false;
create or replace function private.review_norm(p text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(
           regexp_replace(
             translate(
               regexp_replace(lower(normalize(coalesce(p, ''), NFKC)), '[ً-ٰٟـ؜᠎​-‏‪-‮⁠-⁤⁦-⁯﻿­͏︀-️]', '', 'g'),
               'أإآٱةىؤئ', 'ااااهيوي'),
             '\s*(\[\.\]|\(\.\)|\{\.\}|\s(dot|نقطه)\s|\.)\s*', '.', 'g'),
           '\s+', ' ', 'g')
$$;
revoke all on function private.review_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.review_norm(text) to authenticated, service_role;
create or replace function private.review_squash(p text) returns text language sql immutable set search_path = public as $$
  select translate(regexp_replace(private.review_norm(p), '[^a-z0-9ء-ي]+', '', 'g'), '013457', 'oieast')
$$;
revoke all on function private.review_squash(text) from public, anon, authenticated, service_role;
grant execute on function private.review_squash(text) to authenticated, service_role;
create or replace function private.review_topics(p text) returns text[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct r.topic order by r.topic), '{}'::text[])
    from (select private.review_norm(p) as n, private.review_squash(p) as s) x, private.review_rules r
   where r.active and (case when r.squashed then x.s else x.n end) ~* r.pattern
$$;
revoke all on function private.review_topics(text) from public, anon, authenticated, service_role;
grant execute on function private.review_topics(text) to authenticated, service_role;

delete from private.review_rules where pattern = $r$\m(retail|consumer) (sale|sales|price|customers?|buyers?)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(retail|consumer) (sale|sales|customers?|buyers?)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(retail|consumer) (sale|sales|customers?|buyers?)\M$r$ where pattern = $r$\m(retail|consumer) (sale|sales|price|customers?|buyers?)\M$r$;
delete from private.review_rules where pattern = $r$\m(sell|selling|sale|supply|supplying|deliver|delivery) (to|for) (the )?(public|consumers?|pharmac(y|ies))\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(sell|selling|sold|sale|sales|supply|supplying|deliver|delivering|delivery|distribute|distributing)( directly| direct| straight)? (to|for) (the )?(public|consumers?|pharmac(y|ies)|patients)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(sell|selling|sold|sale|sales|supply|supplying|deliver|delivering|delivery|distribute|distributing)( directly| direct| straight)? (to|for) (the )?(public|consumers?|pharmac(y|ies)|patients)\M$r$ where pattern = $r$\m(sell|selling|sale|supply|supplying|deliver|delivery) (to|for) (the )?(public|consumers?|pharmac(y|ies))\M$r$;
delete from private.review_rules where pattern = $r$\m(single|one|loose|open(ed)?) (box|pack|strip)s?\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m((loose|opened?) (box|boxes|packs?|strips?)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m((loose|opened?) (box|boxes|packs?|strips?)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$ where pattern = $r$\m(single|one|loose|open(ed)?) (box|pack|strip)s?\M$r$;
delete from private.review_rules where pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ where pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)\M$r$;
delete from private.review_rules where pattern = $r$\m(controlled (substances?|drugs?|medicines?)|psychotropics?|narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(controlled (substances?|drugs?|medicines?)|psychotropics?|(?<!non-)(?<!non )narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(controlled (substances?|drugs?|medicines?)|psychotropics?|(?<!non-)(?<!non )narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M$r$ where pattern = $r$\m(controlled (substances?|drugs?|medicines?)|psychotropics?|narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|لصيدليتي|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|للصيدليه|لصيدليتي|لصيدليتك|لصيدليتكم|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|للصيدليه|لصيدليتي|لصيدليتك|لصيدليتكم|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|لصيدليتي|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|فرط|بالفرط|بالشريط)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|فرط|بالفرط|بالشريط)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|من الجدول|مخدر|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدر(?! موضعي)|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدر(?! موضعي)|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|من الجدول|مخدر|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسم|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسمك|استيراد باسمكم|استيراد باسم الغير|استيراد باسم شركتك|استيراد باسم شركتكم|استيراد باسم حضرتك|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسمك|استيراد باسمكم|استيراد باسم الغير|استيراد باسم شركتك|استيراد باسم شركتكم|استيراد باسم حضرتك|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسم|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه|مزوره|مزور|تزوير)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه|مزوره|مزور|تزوير)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite)|t\.me/|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|\mt\.me(/|\M)|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$);   -- re-run safe
update private.review_rules set pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|\mt\.me(/|\M)|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$ where pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite)|t\.me/|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/$r$;
insert into private.review_rules (topic, squashed, pattern) values
  ('sham', false, $r$(^|[^ء-ي])(?<!غير )(?<!ضد )(?<!مكافحه )(?<!مقاومه )(و|ف)?(مزوره|مزور|تزوير)([^ء-ي]|$)$r$),
  ('retail', false, $r$(^|[^ء-ي])(و|ف)?(بيع للمرضي|توصيل للمرضي|متاح للمرضي|للمرضي مباشره|للعيانين)([^ء-ي]|$)$r$),
  ('controlled', false, $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول)([^ء-ي]|$)$r$),
  ('controlled', true, $r$tramadol|tapentadol|pregabalin|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine$r$),
  ('controlled', true, $r$ترامادول|ترمادول|بريجابالين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين$r$)
on conflict (pattern) do nothing;

-- ── 3. group rules (0094): the outside-link rule is the W-17 invite rule (one list, the new spellings included); a duplicate is the
--      same letters and digits (a space, a dot or an emoji more was a new post); the daily limit and slow mode count every post written,
--      also one deleted since (deleting today's post freed the slot) ────
create table if not exists private.group_post_log (
  group_id   bigint not null,
  user_id    uuid not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_group_post_log on private.group_post_log (group_id, user_id, created_at desc);
revoke all on table private.group_post_log from public, anon, authenticated;
grant select, insert, update, delete on table private.group_post_log to service_role;
create or replace function public.posts_group_log() returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into private.group_post_log (group_id, user_id, created_at) values (new.group_id, new.user_id, new.created_at);
  delete from private.group_post_log where created_at < now() - interval '2 days' and group_id = new.group_id and user_id = new.user_id;
  return null;
end $$;
revoke all on function public.posts_group_log() from public, anon, authenticated, service_role;
grant execute on function public.posts_group_log() to service_role;
insert into private.group_post_log (group_id, user_id, created_at)           -- the last two days' posts, once (re-run safe)
select p.group_id, p.user_id, p.created_at from public.posts p
 where p.group_id is not null and p.created_at > now() - interval '2 days' and not exists (select 1 from private.group_post_log);
drop trigger if exists trg_posts_group_log on public.posts;
create trigger trg_posts_group_log after insert on public.posts for each row when (new.group_id is not null) execute function public.posts_group_log();
create or replace function public.posts_group_rules() returns trigger language plpgsql security definer set search_path = public as $$
declare g public.groups; me uuid := auth.uid(); n int; last_at timestamptz; nb text; sq text; day0 timestamptz;
begin
  if new.group_id is null then new.group_pending := false; return new; end if;
  if tg_op = 'UPDATE' then
    if current_setting('drugbox.group_publish', true) = '1' then return new; end if;
    new.group_pending := old.group_pending;                                          -- only group_publish_post changes it
    if new.body is not distinct from old.body or me is null then return new; end if;
  else
    new.group_pending := false;
  end if;
  if me is null then return new; end if;                                             -- server writes (imports, fixtures)
  select * into g from public.groups where id = new.group_id;
  if g.id is null or public.is_group_member(g.id, array['admin', 'moderator']) or public.is_moderator() then return new; end if;
  nb := private.review_norm(new.body);
  if g.block_links and exists (select 1 from private.review_rules r where r.topic = 'invite' and r.active and nb ~* r.pattern) then   -- 0095: the W-17 invite rule
    raise exception 'Links to outside chat groups are not allowed in this group' using errcode = '42501', hint = 'DX423';
  end if;
  if tg_op = 'INSERT' then
    if g.require_category and coalesce(new.category, 'general') = 'general' then
      raise exception 'This group asks every post to say what it is — choose a category' using errcode = '22023', hint = 'DX424';
    end if;
    if g.daily_post_limit is not null then
      day0 := (date_trunc('day', now() at time zone 'Africa/Cairo')) at time zone 'Africa/Cairo';
      select count(*) into n from private.group_post_log p where p.group_id = g.id and p.user_id = me and p.created_at >= day0;
      if n >= g.daily_post_limit then
        raise exception 'This group allows % post(s) a day per member — you can post again tomorrow', g.daily_post_limit using errcode = 'P0001', hint = 'DX420';
      end if;
    end if;
    if g.slow_mode_minutes is not null then
      select max(p.created_at) into last_at from private.group_post_log p where p.group_id = g.id and p.user_id = me;
      if last_at is not null and last_at > now() - make_interval(mins => g.slow_mode_minutes) then
        raise exception 'Slow mode: this group allows one post every % minute(s) — wait % more', g.slow_mode_minutes,
          greatest(1, ceil(extract(epoch from (last_at + make_interval(mins => g.slow_mode_minutes) - now())) / 60))::int using errcode = 'P0001', hint = 'DX421';
      end if;
    end if;
  end if;
  sq := private.review_squash(new.body);                                             -- 0095: letters and digits only, so a space or a dot more is the same post
  if g.block_duplicates and char_length(sq) >= 10 and exists (
       select 1 from public.posts p where p.group_id = g.id and p.id is distinct from new.id and p.created_at > now() - interval '7 days'
          and p.user_id = me and private.review_squash(p.body) = sq) then
    raise exception 'You already posted this in the group this week — edit the earlier post instead of posting it again' using errcode = 'P0001', hint = 'DX422';
  end if;
  if tg_op = 'INSERT' and g.review_posts then new.group_pending := true; end if;
  return new;
end $$;
revoke all on function public.posts_group_rules() from public, anon, authenticated, service_role;
grant execute on function public.posts_group_rules() to authenticated, service_role;
drop trigger if exists trg_posts_c_group_rules on public.posts;
create trigger trg_posts_c_group_rules before insert or update on public.posts for each row execute function public.posts_group_rules();


-- ── 4. a company's surplus lots and dossiers (company_listings, the company workspace) are trade offers too: held like the others ────
-- a held one is inactive (the existing read rule shows inactive listings to the company's own team only), cannot be switched back on
-- (DX417), tells no follower; publishing switches it on and tells the followers then; removing deletes it
alter table public.company_listings add column if not exists review_hold boolean not null default false;
create index if not exists idx_company_listings_review_hold on public.company_listings (id) where review_hold;
alter table public.content_holds drop constraint if exists content_holds_kind_check;
alter table public.content_holds add constraint content_holds_kind_check check (kind in ('post', 'offer', 'listing', 'company'));

create or replace function private.review_text(p_table text, r jsonb) returns text language sql immutable set search_path = public as $$
  select case p_table when 'posts' then r ->> 'body'
                      when 'products' then concat_ws(' ', r ->> 'name', r ->> 'description', r ->> 'price', r ->> 'moq', r ->> 'broker_for', r ->> 'unit', r ->> 'tag',
                                                     r ->> 'incoterms', r ->> 'payment_terms', r ->> 'lead_time', r ->> 'stock', r ->> 'specs', r ->> 'price_tiers')   -- every field people type (F4)
                      when 'company_listings' then concat_ws(' ', r ->> 'product', r ->> 'qty', r ->> 'batch', r ->> 'expiry', r ->> 'price', r ->> 'reg_status', r ->> 'deal_kind', r ->> 'markets')
                      else concat_ws(' ', r ->> 'title', r ->> 'details', r ->> 'price', r ->> 'broker_for') end
$$;
revoke all on function private.review_text(text, jsonb) from public, anon, authenticated, service_role;
grant execute on function private.review_text(text, jsonb) to authenticated, service_role;
create or replace function private.hold_kind(p_table text) returns text language sql immutable set search_path = public as $$
  select case p_table when 'posts' then 'post' when 'products' then 'offer' when 'company_listings' then 'company' else 'listing' end
$$;
revoke all on function private.hold_kind(text) from public, anon, authenticated, service_role;
grant execute on function private.hold_kind(text) to authenticated, service_role;

create or replace function public.review_hold_before() returns trigger language plpgsql security definer set search_path = public as $$
declare txt text := private.review_text(tg_table_name, to_jsonb(new)); prod boolean := tg_table_name = 'products'; cl boolean := tg_table_name = 'company_listings';
begin
  if tg_op = 'UPDATE' then
    if current_setting('drugbox.hold_decision', true) = '1' then return new; end if;   -- held_review_decide() sets / clears it
    new.review_hold := old.review_hold;
    -- a held offer stays off: neither its status nor its active flag (products derive one from the other after this trigger — F1) turns it on
    if new.review_hold and ((prod and (to_jsonb(new) ->> 'status') = 'active' and (to_jsonb(old) ->> 'status') <> 'active')
                         or ((prod or cl) and (to_jsonb(new) ->> 'active')::boolean and not (to_jsonb(old) ->> 'active')::boolean)) then
      raise exception 'This offer is waiting for Drugbox review — it shows again once it is checked' using errcode = '42501', hint = 'DX417';
    end if;
    if txt is not distinct from private.review_text(tg_table_name, to_jsonb(old)) then return new; end if;
  else
    new.review_hold := false;
  end if;
  if new.review_hold then return new; end if;                                    -- already waiting: an edit keeps it waiting
  -- Drugbox's own team is not held (it posts as Drugbox and decides the queue); server writes (imports, fixtures) neither
  if auth.uid() is null or exists (select 1 from public.profiles p where p.id = auth.uid() and p.role in ('admin', 'moderator')) then return new; end if;
  if cardinality(private.review_topics(txt)) > 0 then
    new.review_hold := true;
    if prod and (to_jsonb(new) ->> 'status') = 'active' then new := jsonb_populate_record(new, jsonb_build_object('status', 'paused')); end if;
    if cl then new := jsonb_populate_record(new, jsonb_build_object('active', false)); end if;
  end if;
  return new;
end $$;
revoke all on function public.review_hold_before() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_before() to authenticated, service_role;

create or replace function public.review_hold_after() returns trigger language plpgsql security definer set search_path = public as $$
declare k text := private.hold_kind(tg_table_name); j jsonb := to_jsonb(new); t text[]; ex text; who uuid := coalesce(j ->> 'user_id', j ->> 'created_by')::uuid;
begin
  if not new.review_hold or (tg_op = 'UPDATE' and old.review_hold) then return null; end if;
  if exists (select 1 from public.content_holds h where h.kind = k and h.item_id = new.id and h.status = 'held') then return null; end if;
  t := private.review_topics(private.review_text(tg_table_name, j));
  ex := left(regexp_replace(case tg_table_name when 'posts' then coalesce(j ->> 'body', '')
                                               when 'products' then concat_ws(' — ', j ->> 'name', j ->> 'description')
                                               when 'company_listings' then concat_ws(' — ', j ->> 'product', j ->> 'qty', j ->> 'price', j ->> 'markets')
                                               else concat_ws(' — ', j ->> 'title', j ->> 'details') end, '\s+', ' ', 'g'), 200);
  insert into public.content_holds (kind, item_id, user_id, topics, excerpt) values (k, new.id, who, t, ex);
  if who is not null then
    insert into public.notifications (user_id, type, from_user, message, data)
    values (who, 'auto_review', null, null, jsonb_build_object('kind', k, 'topics', to_jsonb(t), 'excerpt', left(ex, 80) || case when char_length(ex) > 80 then '…' else '' end));
  end if;
  return null;
end $$;
revoke all on function public.review_hold_after() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_after() to service_role;

create or replace function public.review_hold_gone() returns trigger language plpgsql security definer set search_path = public as $$
begin
  update public.content_holds set status = 'removed', decided_at = coalesce(decided_at, now())
   where kind = private.hold_kind(tg_table_name) and item_id = old.id and status = 'held';
  return null;
end $$;
revoke all on function public.review_hold_gone() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_gone() to service_role;

-- before the other company_listings triggers (not_suspended, trade_guard: b < n < t), as on the other tables
drop trigger if exists trg_company_listings_b_review_hold on public.company_listings;
create trigger trg_company_listings_b_review_hold before insert or update on public.company_listings for each row execute function public.review_hold_before();
drop trigger if exists trg_company_listings_review_hold_after on public.company_listings;
create trigger trg_company_listings_review_hold_after after insert or update on public.company_listings for each row execute function public.review_hold_after();
drop trigger if exists trg_company_listings_review_hold_gone on public.company_listings;
create trigger trg_company_listings_review_hold_gone after delete on public.company_listings for each row when (old.review_hold) execute function public.review_hold_gone();
drop policy if exists "company listings: held for review" on public.company_listings;
create policy "company listings: held for review" on public.company_listings as restrictive for select
  using (not review_hold or public.is_company_member(company_id) or (select public.is_moderator()));

create or replace function public.held_review_queue(p_limit int default 100) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not public.is_moderator() then null else coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at) from (
    select h.id, h.kind, h.item_id, h.topics, h.excerpt, h.created_at, h.user_id,
           (select p.name from public.profiles p where p.id = h.user_id) as author,
           case h.kind when 'post' then (select o.body from public.posts o where o.id = h.item_id)
                       when 'offer' then (select concat_ws(' — ', r.name, r.description) from public.products r where r.id = h.item_id)
                       when 'company' then (select concat_ws(' — ', c.product, c.qty, c.batch, c.expiry, c.price, c.reg_status, c.deal_kind, c.markets) from public.company_listings c where c.id = h.item_id)
                       else (select concat_ws(' — ', l.title, l.details) from public.group_listings l where l.id = h.item_id) end as body,
           -- where it was posted: the group, or the company page
           case h.kind when 'post' then (select g.name from public.posts o join public.groups g on g.id = o.group_id where o.id = h.item_id)
                       when 'listing' then (select g.name from public.group_listings l join public.groups g on g.id = l.group_id where l.id = h.item_id)
                       when 'company' then (select co.name from public.company_listings c join public.companies co on co.id = c.company_id where c.id = h.item_id) end as group_name
      from public.content_holds h where h.status = 'held' order by h.created_at limit least(greatest(coalesce(p_limit, 100), 1), 300)) x), '[]'::jsonb) end
$$;
revoke all on function public.held_review_queue(int) from public, anon, authenticated, service_role;
grant execute on function public.held_review_queue(int) to authenticated, service_role;

create or replace function public.held_review_decide(p_hold bigint, p_publish boolean, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare h public.content_holds; me uuid := auth.uid(); v_note text := nullif(left(trim(coalesce(p_note, '')), 500), ''); out text; c public.company_listings;
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into h from public.content_holds where id = p_hold for update;
  if h.id is null then raise exception 'This item is not in the queue' using errcode = 'P0002'; end if;
  if h.status <> 'held' then raise exception 'Already decided by % (%)', private.who(h.decided_by), h.status using errcode = 'DX409'; end if;
  out := case when p_publish then 'published' else 'removed' end;
  update public.content_holds set status = out, decided_by = me, decided_at = now(), note = v_note where id = h.id;
  perform set_config('drugbox.hold_decision', '1', true);
  if p_publish then
    if h.kind = 'post' then update public.posts set review_hold = false where id = h.item_id;
    elsif h.kind = 'offer' then update public.products set review_hold = false, status = case when status = 'paused' then 'active' else status end where id = h.item_id;
    elsif h.kind = 'company' then
      update public.company_listings set review_hold = false, active = true where id = h.item_id returning * into c;
      if c.id is not null then perform public.notify_company_followers(array[c.company_id], c.created_by, c.product, c.kind); end if;   -- told now, not when it was held
    else update public.group_listings set review_hold = false where id = h.item_id; end if;
  else
    if h.kind = 'post' then delete from public.posts where id = h.item_id;
    elsif h.kind = 'offer' then delete from public.products where id = h.item_id;
    elsif h.kind = 'company' then delete from public.company_listings where id = h.item_id;
    else delete from public.group_listings where id = h.item_id; end if;
  end if;
  perform set_config('drugbox.hold_decision', '', true);
  if h.user_id is not null then
    insert into public.notifications (user_id, type, from_user, message, data)
    values (h.user_id, 'auto_review_decided', null, null, jsonb_strip_nulls(jsonb_build_object('kind', h.kind, 'outcome', out,
            'excerpt', left(h.excerpt, 80) || case when char_length(h.excerpt) > 80 then '…' else '' end, 'note', v_note)));
  end if;
  perform private.log_decision('held', h.id::text, left(coalesce((select name from public.profiles where id = h.user_id), 'A member') || ' · ' || h.excerpt, 300), out, v_note,
                               jsonb_build_object('kind', h.kind, 'item', h.item_id, 'topics', to_jsonb(h.topics)));
  return out;
end $$;
revoke all on function public.held_review_decide(bigint, boolean, text) from public, anon, authenticated, service_role;
grant execute on function public.held_review_decide(bigint, boolean, text) to authenticated, service_role;

notify pgrst, 'reload schema';
