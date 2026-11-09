-- 0097 · w-trust: the independent verifier's second round (N1–N12)
--   N1/N2 an offer posted as a company goes on only while the company is verified — also through listing_renew and a moderator's Publish
--         (the guard now skips only writes with no signed-in user; Publish clears the hold and leaves a company offer off while the badge is gone)
--   N3    a member who leaves a company (or is removed) stops posting as it: their company offers are paused / closed, they cannot edit them
--         (DX419), and the company's owners / admins can pause, edit or delete offers posted as the company
--   N4    W-17 rules, third version: the "squashed" text joins only spelled-out letters ("t r a m a d o l") and reads digits as letters only
--         inside a word that mixes both ("tramad0l", "lyr1ca", "c0m") — "code in Egypt", "Rita Lin", "cap tag", «الأمور فين» no longer read as
--         codeine / ritalin / captagon / morphine; bare «مخدر» (anaesthetic), "retail sales of …", "opened box", "a distributor who can deliver to
--         pharmacies" and domains ending in "t.me.eg" are no longer held; the misses the verifier listed are caught
--   N5    products.docs and products.emoji are checked too
--   N8    phone codes: per account 3 an hour / 6 a day and at most 3 different numbers a day; per number 6 a day across accounts (one account can
--         no longer lock a number out)
--   N9    a member the admins removed does not rejoin a public group by themselves (DX429) — an invitation or an admin brings them back
--   N11   Arabic-Indic and Persian digits are read as digits (review_norm dropped them with the harakat range): duplicate posts ٥٠٠ / ٢٠٠ differ
--   N12   only Drugbox's team names or describes a group as Drugbox's own (DX437)


-- ── N4/N5 rules v3 ────
create or replace function private.review_norm(p text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(
           regexp_replace(
             regexp_replace(
               translate(
                 regexp_replace(translate(lower(normalize(coalesce(p, ''), NFKC)), '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'), '[ً-ٰٟـ؜᠎​-‏‪-‮⁠-⁤⁦-⁯﻿­͏︀-️]', '', 'g'),
                 'أإآٱةىؤئ。｡․', 'ااااهيوي...'),
               '\s*(\[\.\]|\(\.\)|\{\.\}|\(dot\)|\[dot\]|\s(dot|نقطه)\s|\.)\s*', '.', 'g'),
             '\s+/', '/', 'g'),
           '\s+', ' ', 'g')
$$;
revoke all on function private.review_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.review_norm(text) to authenticated, service_role;
-- spelled-out letters joined ("t r a m a d o l", "t.r.a.m.a.d.o.l"); 0 1 3 4 5 7 read as o i e a s t only in a word that has letters and digits
create or replace function private.review_squash(p text) returns text language sql immutable set search_path = public as $$
  select coalesce(string_agg(case when w ~ '[a-z]' and w ~ '[0-9]' then translate(w, '013457', 'oieast') else w end, ' ' order by i), '')
    from regexp_split_to_table(regexp_replace(private.review_norm(p), '(?<![a-z0-9ء-ي])([a-z0-9ء-ي])[ .*_-]+(?=[a-z0-9ء-ي](?![a-z0-9ء-ي]))', '\1', 'g'), ' ')
         with ordinality as t(w, i)
$$;
revoke all on function private.review_squash(text) from public, anon, authenticated, service_role;
grant execute on function private.review_squash(text) to authenticated, service_role;

delete from private.review_rules where pattern = $r$\m(retail|consumer) (sale|sales|customers?|buyers?)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(for|by|in|at) (retail|consumer) (sale|sales)\M|\m(retail|consumer) (customers?|buyers?)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(for|by|in|at) (retail|consumer) (sale|sales)\M|\m(retail|consumer) (customers?|buyers?)\M$r$ where pattern = $r$\m(retail|consumer) (sale|sales|customers?|buyers?)\M$r$;
delete from private.review_rules where pattern = $r$\m(sell|selling|sold|sale|sales|supply|supplying|deliver|delivering|delivery|distribute|distributing)( directly| direct| straight)? (to|for) (the )?(public|consumers?|pharmac(y|ies)|patients)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(we|i|we can|we will|we also|ready to)( directly| also)? (sell|supply|deliver|distribute)( directly| direct| straight)? (to|for) (the |your )?(public|consumers?|pharmac(y|ies|ists?)|drugstores?|patients)\M|\m(sale|sales|selling) (directly )?(to|for) (the )?(public|consumers?|pharmac(y|ies)|drugstores?|patients)\M|\msell(ing)? to (pharmac(y|ies)|drugstores?)\M|\m(to|for) your pharmacy\M|\mpharmacy orders?( are)? welcome\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(we|i|we can|we will|we also|ready to)( directly| also)? (sell|supply|deliver|distribute)( directly| direct| straight)? (to|for) (the |your )?(public|consumers?|pharmac(y|ies|ists?)|drugstores?|patients)\M|\m(sale|sales|selling) (directly )?(to|for) (the )?(public|consumers?|pharmac(y|ies)|drugstores?|patients)\M|\msell(ing)? to (pharmac(y|ies)|drugstores?)\M|\m(to|for) your pharmacy\M|\mpharmacy orders?( are)? welcome\M$r$ where pattern = $r$\m(sell|selling|sold|sale|sales|supply|supplying|deliver|delivering|delivery|distribute|distributing)( directly| direct| straight)? (to|for) (the )?(public|consumers?|pharmac(y|ies)|patients)\M$r$;
delete from private.review_rules where pattern = $r$\m((loose|opened?) (box|boxes|packs?|strips?)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(loose (strips?|tablets?|capsules?|packs?|boxes)|opened (packs|strips)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(loose (strips?|tablets?|capsules?|packs?|boxes)|opened (packs|strips)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$ where pattern = $r$\m((loose|opened?) (box|boxes|packs?|strips?)|(sell|selling|sold|sale of|by the) (single|one) (box|pack|strip)s?)\M$r$;
delete from private.review_rules where pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ where pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$;
delete from private.review_rules where pattern = $r$\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e|under your name|for you)|\mwe (can )?import (for you|under your name|on your behalf)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e|under your name|for you)|\mwe (can )?import (for you|under your name|on your behalf)\M$r$ where pattern = $r$\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e)$r$;
delete from private.review_rules where pattern = $r$\m(sham|fake|fictitious) (contracts?|invoices?|tenders?|coas?|certificates?|papers?)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(sham|fake|fictitious|forged) (contracts?|invoices?|tenders?|coas?|certificates?|papers?|documents?)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(sham|fake|fictitious|forged) (contracts?|invoices?|tenders?|coas?|certificates?|papers?|documents?)\M$r$ where pattern = $r$\m(sham|fake|fictitious) (contracts?|invoices?|tenders?|coas?|certificates?|papers?)\M$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدر(?! موضعي)|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدر(?! موضعي)|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره صوريه|فواتير صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره صوريه|فواتير صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|\mt\.me(/|\M)|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.\-])t\.me(?![a-z0-9.\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|telegram ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$);   -- re-run safe
update private.review_rules set pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.\-])t\.me(?![a-z0-9.\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|telegram ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$ where pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|\mt\.me(/|\M)|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(?<!غير )(?<!ضد )(?<!مكافحه )(?<!مقاومه )(و|ف)?(مزوره|مزور|تزوير)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(?<!غير )(?<!ضد )(?<!مكافحه )(?<!مقاومه )(و|ف)?(مزوره|مزور|تزوير|مزيفه|مزيف)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(?<!غير )(?<!ضد )(?<!مكافحه )(?<!مقاومه )(و|ف)?(مزوره|مزور|تزوير|مزيفه|مزيف)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(?<!غير )(?<!ضد )(?<!مكافحه )(?<!مقاومه )(و|ف)?(مزوره|مزور|تزوير)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول|بريجابلين)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول|بريجابلين)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$tramadol|tapentadol|pregabalin|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ where pattern = $r$tramadol|tapentadol|pregabalin|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine$r$;
delete from private.review_rules where pattern = $r$ترامادول|ترمادول|بريجابالين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترمادول|بريجابالين|بريجابلين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترمادول|بريجابالين|بريجابلين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)$r$ where pattern = $r$ترامادول|ترمادول|بريجابالين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين$r$;
insert into private.review_rules (topic, squashed, pattern) values
  ('retail', false, $r$(^|[^ء-ي])(و|ف)?(نبيع للصيادله|بنبيع للصيادله|بيع للصيادله|للصيادله فقط|نوزع علي الصيدليات|بنوزع علي الصيدليات|توصيل للصيدليه|توصيل للصيدليات|توصيل لحد الصيدليه|توصيل لباب الصيدليه)([^ء-ي]|$)$r$),
  ('import', false, $r$(^|[^ء-ي])(و|ف)?(نستورد لحضرتك|بنستورد لحضرتك|نستورد لحسابك|نستورد باسمك|بنستورد باسمك|نستورد باسم شركتك|بنستورد باسم شركتك|نستورد علي سجلك)([^ء-ي]|$)$r$),
  ('invite', false, $r$(^|[^ء-ي])(و|ف)?(جروب|جروبات|مجموعه) (ال)?(واتس|واتساب|الواتس|تليجرام|تلجرام|تيليجرام)([^ء-ي]|$)$r$),
  ('invite', false, $r$(^|[^ء-ي])(و|ف)?(هضيفك|اضيفك|هنضيفك|نضيفك) (لل|علي ال|ع ال|في ال)?(جروب|مجموعه)([^ء-ي]|$)$r$),
  ('invite', true, $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite|send)|(?<![a-z0-9.\-])t\.me/$r$),
  ('invite', false, $r$\m(whatsapp|telegram|viber) (group|channel)s?\M$r$),
  ('retail', false, $r$\mdelivery (to|for) (pharmac(y|ies)|drugstores?)\M|\mpharmac(ies|ists) (are )?welcome\M$r$)
on conflict (pattern) do nothing;

create or replace function private.review_text(p_table text, r jsonb) returns text language sql immutable set search_path = public as $$
  select case p_table when 'posts' then r ->> 'body'
                      when 'products' then concat_ws(' ', r ->> 'name', r ->> 'description', r ->> 'price', r ->> 'moq', r ->> 'broker_for', r ->> 'unit', r ->> 'tag',
                                                     r ->> 'incoterms', r ->> 'payment_terms', r ->> 'lead_time', r ->> 'stock', r ->> 'specs', r ->> 'price_tiers', r ->> 'docs', r ->> 'emoji')   -- 0097: docs and emoji too (N5)   -- every field people type (F4)
                      when 'company_listings' then concat_ws(' ', r ->> 'product', r ->> 'qty', r ->> 'batch', r ->> 'expiry', r ->> 'price', r ->> 'reg_status', r ->> 'deal_kind', r ->> 'markets')
                      else concat_ws(' ', r ->> 'title', r ->> 'details', r ->> 'price', r ->> 'broker_for') end
$$;
revoke all on function private.review_text(text, jsonb) from public, anon, authenticated, service_role;
grant execute on function private.review_text(text, jsonb) to authenticated, service_role;

-- ── N1/N2/N3 company offers follow the badge and the team ────
create or replace function public.trade_badge_on_guard() returns trigger language plpgsql set search_path = public as $$
declare n jsonb := to_jsonb(new); o jsonb := to_jsonb(old); turning_on boolean;
begin
  -- 0097 (N1): security-definer actions (listing_renew, a moderator's Publish) run as the server but for a signed-in person: only writes with
  -- no signed-in user (imports, the server's own jobs) skip this
  if auth.uid() is null then return new; end if;
  -- N3: a member who is no longer on the company's team does not change its offers (the company's owners / admins do)
  if tg_table_name in ('products', 'group_listings') and n ->> 'posted_as' = 'company' and (n ->> 'user_id')::uuid = auth.uid()
     and not public.is_company_member((n ->> 'company_id')::bigint) and not public.is_moderator() then
    raise exception 'You are no longer on this company''s team — its offers are managed by the company' using errcode = '42501', hint = 'DX419';
  end if;
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
    -- 0097 (N2): a company offer goes back on only while the company is verified; otherwise it stays paused (the owner resumes it once verified)
    elsif h.kind = 'offer' then update public.products p set review_hold = false,
                                    status = case when p.status = 'paused' and (p.posted_as is distinct from 'company' or exists (select 1 from public.companies cc where cc.id = p.company_id and cc.status = 'verified'))
                                                  then 'active' else p.status end where p.id = h.item_id;
    elsif h.kind = 'company' then
      update public.company_listings x set review_hold = false, active = exists (select 1 from public.companies co where co.id = x.company_id and co.status = 'verified')
       where x.id = h.item_id returning * into c;
      if c.id is not null and c.active then perform public.notify_company_followers(array[c.company_id], c.created_by, c.product, c.kind); end if;   -- told now, not when it was held
    else update public.group_listings l set review_hold = false,
                status = case when l.posted_as = 'company' and not exists (select 1 from public.companies co where co.id = l.company_id and co.status = 'verified') then 'closed' else l.status end
          where l.id = h.item_id; end if;
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

-- a member who leaves the company (or is removed): their offers posted as the company are paused / closed, the owners are told
create or replace function public.company_member_left() returns trigger language plpgsql security definer set search_path = public as $$
declare n int := 0; k int;
begin
  update public.products set status = 'paused' where company_id = old.company_id and user_id = old.user_id and posted_as = 'company' and status = 'active';
  get diagnostics k = row_count; n := n + k;
  update public.group_listings set status = 'closed' where company_id = old.company_id and user_id = old.user_id and posted_as = 'company' and status = 'open';
  get diagnostics k = row_count; n := n + k;
  if n > 0 then
    insert into public.notifications (user_id, type, from_user, message, data)
    select c.owner_id, 'company_member_offers_paused', old.user_id, null, jsonb_build_object('company', c.name, 'offers', n)
      from public.companies c where c.id = old.company_id and c.owner_id is not null and c.owner_id <> old.user_id;
  end if;
  return null;
end $$;
revoke all on function public.company_member_left() from public, anon, authenticated, service_role;
grant execute on function public.company_member_left() to service_role;
drop trigger if exists trg_company_members_left on public.company_members;
create trigger trg_company_members_left after delete on public.company_members for each row execute function public.company_member_left();
-- the company's owners / admins manage the offers posted as the company (pause, edit, delete)
drop policy if exists "products: the company's owners and admins manage its offers" on public.products;
create policy "products: the company's owners and admins manage its offers" on public.products for update to authenticated
  using (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']))
  with check (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']));
drop policy if exists "products: the company's owners and admins delete its offers" on public.products;
create policy "products: the company's owners and admins delete its offers" on public.products for delete to authenticated
  using (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']));
drop policy if exists "products: the company's team reads its offers" on public.products;
create policy "products: the company's team reads its offers" on public.products for select to authenticated
  using (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']));

-- ── N8 phone codes ────
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
     -- 0097 (N8): at most 3 different numbers an account a day, and 6 codes a number a day across accounts (no single account locks a number out)
     or (select count(distinct l.phone_hash) from private.phone_code_log l where l.user_id = me and l.sent_at > now() - interval '1 day' and l.phone_hash is distinct from h) >= 3
     or (select count(*) from private.phone_code_log l where l.phone_hash = h and l.sent_at > now() - interval '1 day') >= 6 then
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

-- ── N9 a removed member does not rejoin a public group by themselves ────
create or replace function public.group_members_removed_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is not null and new.user_id = auth.uid()
     and exists (select 1 from private.group_removals r where r.group_id = new.group_id and r.user_id = new.user_id)
     and not exists (select 1 from public.group_invites i where i.group_id = new.group_id and i.user_id = new.user_id) then
    raise exception 'The group''s admins removed you from this group — ask them to add you again' using errcode = '42501', hint = 'DX429';
  end if;
  return new;
end $$;
revoke all on function public.group_members_removed_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_members_removed_guard() to authenticated, service_role;
drop trigger if exists trg_group_members_removed_guard on public.group_members;
create trigger trg_group_members_removed_guard before insert on public.group_members for each row execute function public.group_members_removed_guard();

-- ── N11 duplicates: every kind of digit is a digit ────
create or replace function private.dup_key(p text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(translate(private.review_norm(p), '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'), '[^[:alnum:]]+', '', 'g')
$$;
revoke all on function private.dup_key(text) from public, anon, authenticated, service_role;
grant execute on function private.dup_key(text) to authenticated, service_role;
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
  sq := private.dup_key(new.body);                                             -- 0095: letters and digits only, so a space or a dot more is the same post
  if g.block_duplicates and char_length(sq) >= 10 and exists (
       select 1 from public.posts p where p.group_id = g.id and p.id is distinct from new.id and p.created_at > now() - interval '7 days'
          and p.user_id = me and private.dup_key(p.body) = sq) then
    raise exception 'You already posted this in the group this week — edit the earlier post instead of posting it again' using errcode = 'P0001', hint = 'DX422';
  end if;
  if tg_op = 'INSERT' and g.review_posts then new.group_pending := true; end if;
  return new;
end $$;
revoke all on function public.posts_group_rules() from public, anon, authenticated, service_role;
grant execute on function public.posts_group_rules() to authenticated, service_role;

-- ── N12 only Drugbox names a group as its own ────
create or replace function public.groups_drugbox_name_guard() returns trigger language plpgsql set search_path = public as $$
declare t text := private.review_norm(concat_ws(' ', new.name, new.description));
begin
  if public.is_server_call() or public.is_moderator() then return new; end if;
  if tg_op = 'UPDATE' and new.name is not distinct from old.name and new.description is not distinct from old.description then return new; end if;
  if t ~ 'drugbox|دراجبوكس|دروجبوكس|دراغبوكس' and t ~ '\m(official|officially|run by|managed by|team|staff|admins?)\M|رسمي|الرسمي|تابع ل|اداره|فريق' then
    raise exception 'Only Drugbox''s team names or describes a group as Drugbox''s own — ask for the partner badge instead' using errcode = '42501', hint = 'DX437';
  end if;
  return new;
end $$;
revoke all on function public.groups_drugbox_name_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_drugbox_name_guard() to authenticated, service_role;
drop trigger if exists trg_groups_drugbox_name on public.groups;
create trigger trg_groups_drugbox_name before insert or update on public.groups for each row execute function public.groups_drugbox_name_guard();

notify pgrst, 'reload schema';
