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

update private.review_rules set pattern = $r$\m(retail|consumer) (sale|sales|customers?|buyers?)\M$r$ where pattern = $r$\m(retail|consumer) (sale|sales|price|customers?|buyers?)\M$r$;
update private.review_rules set pattern = $r$\m(sell|selling|sold|sale|sales|supply|supplying|deliver|delivering|delivery|distribute|distributing)( directly| direct| straight)? (to|for) (the )?(public|consumers?|pharmac(y|ies)|patients)\M$r$ where pattern = $r$\m(sell|selling|sale|supply|supplying|deliver|delivery) (to|for) (the )?(public|consumers?|pharmac(y|ies))\M$r$;
update private.review_rules set pattern = $r$\m((loose|opened?) (box|boxes|packs?|strips?)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$ where pattern = $r$\m(single|one|loose|open(ed)?) (box|pack|strip)s?\M$r$;
update private.review_rules set pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ where pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)\M$r$;
update private.review_rules set pattern = $r$\m(controlled (substances?|drugs?|medicines?)|psychotropics?|(?<!non-)(?<!non )narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M$r$ where pattern = $r$\m(controlled (substances?|drugs?|medicines?)|psychotropics?|narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M$r$;
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|للصيدليه|لصيدليتي|لصيدليتك|لصيدليتكم|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|لصيدليتي|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)$r$;
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|فرط|بالفرط|بالشريط)([^ء-ي]|$)$r$;
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدر(?! موضعي)|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|من الجدول|مخدر|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$;
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسمك|استيراد باسمكم|استيراد باسم الغير|استيراد باسم شركتك|استيراد باسم شركتكم|استيراد باسم حضرتك|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسم|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)$r$;
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه|مزوره|مزور|تزوير)([^ء-ي]|$)$r$;
update private.review_rules set pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|\mt\.me(/|\M)|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$ where pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite)|t\.me/|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/$r$;
insert into private.review_rules (topic, squashed, pattern) values
  ('sham', false, $r$(^|[^ء-ي])(?<!غير )(?<!ضد )(?<!مكافحه )(?<!مقاومه )(و|ف)?(مزوره|مزور|تزوير)([^ء-ي]|$)$r$),
  ('retail', false, $r$(^|[^ء-ي])(و|ف)?(بيع للمرضي|توصيل للمرضي|متاح للمرضي|للمرضي مباشره|للعيانين)([^ء-ي]|$)$r$),
  ('controlled', false, $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول)([^ء-ي]|$)$r$),
  ('controlled', true, $r$tramadol|tapentadol|pregabalin|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine$r$),
  ('controlled', true, $r$ترامادول|ترمادول|بريجابالين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين$r$)
on conflict (pattern) do nothing;

-- ── 3. group rules (0094): the outside-link rule is the W-17 invite rule (one list, the new spellings included), and a duplicate is the
--      same letters and digits (a space, a dot or an emoji more was a new post) ────
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
      select count(*) into n from public.posts p where p.group_id = g.id and p.user_id = me and p.created_at >= day0;
      if n >= g.daily_post_limit then
        raise exception 'This group allows % post(s) a day per member — you can post again tomorrow', g.daily_post_limit using errcode = 'P0001', hint = 'DX420';
      end if;
    end if;
    if g.slow_mode_minutes is not null then
      select max(p.created_at) into last_at from public.posts p where p.group_id = g.id and p.user_id = me;
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

notify pgrst, 'reload schema';
