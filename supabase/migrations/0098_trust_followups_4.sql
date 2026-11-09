-- 0098 · w-trust: the independent verifier's third round
--   F1 (blocking, from 0097) a member with an active company offer could not leave the company (nor an owner delete it): the guard saw the
--      leaver pausing their own offer — company_member_left now marks its own writes
--   F2 a member no longer on the team took a company offer as "Individual" and switched it back on: the guard now reads the OLD row too, and
--      such a member does not delete it either; company owners / admins manage deal-room listings posted as the company too
--   F3 a company admin moved a member's offer to another company: only the author moves an offer or changes who posts it (DX438)
--   F4 one account still filled a number's daily cap: per account 3 codes a number a day; a number's cap counts only other accounts (10)
--   F5/F6 W-17 rules v4: compliant and negated statements are not offers ("we do not sell to pharmacies", «لا نبيع للصيدليات», "no fake COAs",
--      "not for sale to the public"); "pharmacists welcome", talk about WhatsApp groups, "import for clients is regulated", e-mails like t.me@…
--      and «جدول اول الشحنات» are not held; Cyrillic / Greek look-alikes, @ and $ inside words, %2E, link shorteners, common misspellings and
--      the listed EN / AR misses are caught
--   F7 a group name is refused only for claiming to be Drugbox's own; the partner badge goes with a new name, description or cover
--   F9 an item Drugbox published is not held again for the same reasons on a later edit (a price, a sold quantity)
--   F10 a company's owners / admins read its held offers (no raw policy error); company and individual offers carry no broker fields

-- ── rules v4: the text ────
create or replace function private.review_norm(p text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(
           regexp_replace(
             regexp_replace(
               translate(
                 regexp_replace(translate(replace(lower(normalize(coalesce(p, ''), NFKC)), '%2e', '.'), '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'), '[ً-ٰٟـ؜᠎​-‏‪-‮⁠-⁤⁦-⁯﻿­͏︀-️]', '', 'g'),
                 'أإآٱةىؤئ。｡․аеорсухіјѕԁԛԝкмтнвαεικνορτυχ', 'ااااهيوي...aeopcyxijsdqwkmthbaeikvoptux'),
               '\s*(\[\.\]|\(\.\)|\{\.\}|\(dot\)|\[dot\]|\s(dot|نقطه)\s|\.)\s*', '.', 'g'),
             '\s+/', '/', 'g'),
           '\s+', ' ', 'g')
$$;
revoke all on function private.review_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.review_norm(text) to authenticated, service_role;
create or replace function private.review_squash(p text) returns text language sql immutable set search_path = public as $$
  select coalesce(string_agg(case when w ~ '[a-z]' and w ~ '[0-9@$]' then translate(w, '013457@$', 'oieastas') else w end, ' ' order by i), '')
    from regexp_split_to_table(regexp_replace(private.review_norm(p), '(?<![a-z0-9ء-ي])([a-z0-9ء-ي])[ .*_-]+(?=[a-z0-9ء-ي](?![a-z0-9ء-ي]))', '\1', 'g'), ' ')
         with ordinality as t(w, i)
$$;
revoke all on function private.review_squash(text) from public, anon, authenticated, service_role;
grant execute on function private.review_squash(text) to authenticated, service_role;
-- negated / compliant statements are not offers: "we do not sell to pharmacies", «لا نبيع للصيدليات», "no fake COAs", "not for sale to the public"
create or replace function private.review_neg(n text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(coalesce(n, ''),
    '\m(we (do not|don''t|never|won''t|will not)|do not|don''t|never|no|not)( directly| ever)? (sell|sale|sales|selling|supply|supplying|deliver|delivery|distribute|distributing)( directly)?( to| for)? (the |any |retail )?(public|pharmac(y|ies|ists?)|drugstores?|patients|consumers)\M( or (the )?(public|pharmac(y|ies|ists?)|patients|consumers)\M)?', ' ', 'g'),
    '\mnot for (retail )?sale( to (the )?(public|pharmac(y|ies)|patients|consumers))?\M', ' ', 'g'),
    '\m(sale|sales|selling|delivery) to (the )?(public|pharmac(y|ies)|patients|consumers) (is|are) (not allowed|forbidden|prohibited|not permitted)\M', ' ', 'g'),
    '\m(no|spot|spotting|detect|detecting|detection of|avoid|avoiding|against|beware of|report|reporting) (sham|fake|fictitious|forged|backdated) [a-z]+', ' ', 'g'),
    '\m(sham|fake|fictitious|forged|backdated) [a-z]+ (detection|check|checks|checking|training|awareness)\M', ' ', 'g'),
    '(^|[^ء-ي])(لا|مش|مبن|ما|ممنوع|غير مسموح) ?(نبيع|بنبيع|بيع|البيع|نوزع|بنوزع|يوجد توصيل|توصيل|التوصيل) (لل|ل|علي ال)?(صيادله|صيدليات|صيدليه|مرضي|جمهور)([^ء-ي]|$)', '\1 \6', 'g')
$$;
revoke all on function private.review_neg(text) from public, anon, authenticated, service_role;
grant execute on function private.review_neg(text) to authenticated, service_role;
create or replace function private.review_topics(p text) returns text[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct r.topic order by r.topic), '{}'::text[])
    from (select private.review_neg(private.review_norm(p)) as n) y,
         lateral (select y.n as n, private.review_squash(y.n) as s) x, private.review_rules r
   where r.active and (case when r.squashed then x.s else x.n end) ~* r.pattern
$$;
revoke all on function private.review_topics(text) from public, anon, authenticated, service_role;
grant execute on function private.review_topics(text) to authenticated, service_role;

-- ── rules v4 (the third verifier round) ────
delete from private.review_rules where pattern = $r$\m(we|i|we can|we will|we also|ready to)( directly| also)? (sell|supply|deliver|distribute)( directly| direct| straight)? (to|for) (the |your )?(public|consumers?|pharmac(y|ies|ists?)|drugstores?|patients)\M|\m(sale|sales|selling) (directly )?(to|for) (the )?(public|consumers?|pharmac(y|ies)|drugstores?|patients)\M|\msell(ing)? to (pharmac(y|ies)|drugstores?)\M|\m(to|for) your pharmacy\M|\mpharmacy orders?( are)? welcome\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(we|i|we can|we will|we also|ready to)( directly| also)? (sell|supply|deliver|distribute)( directly| direct| straight)? (to|for) (the |your |retail )?(public|consumers?|pharmac(y|ies|ists?)|drugstores?|patients)\M|\m(we|i)( also)? (sell|supply|deliver) (retail )?pharmacies\M|\msupplying (retail )?pharmacies\M|\m(sale|sales|selling) (directly )?(to|for) (the |retail )?(public|consumers?|pharmac(y|ies)|drugstores?|patients)\M|\msell(ing)? to (retail )?(pharmac(y|ies)|drugstores?)\M|\m(to|for) your pharmacy\M|\mpharmacy orders?( are)? welcome\M|\mfor pharmacies at (the )?public price\M|\msupply for patients\M|\mby the box for pharmacists\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(we|i|we can|we will|we also|ready to)( directly| also)? (sell|supply|deliver|distribute)( directly| direct| straight)? (to|for) (the |your |retail )?(public|consumers?|pharmac(y|ies|ists?)|drugstores?|patients)\M|\m(we|i)( also)? (sell|supply|deliver) (retail )?pharmacies\M|\msupplying (retail )?pharmacies\M|\m(sale|sales|selling) (directly )?(to|for) (the |retail )?(public|consumers?|pharmac(y|ies)|drugstores?|patients)\M|\msell(ing)? to (retail )?(pharmac(y|ies)|drugstores?)\M|\m(to|for) your pharmacy\M|\mpharmacy orders?( are)? welcome\M|\mfor pharmacies at (the )?public price\M|\msupply for patients\M|\mby the box for pharmacists\M$r$ where pattern = $r$\m(we|i|we can|we will|we also|ready to)( directly| also)? (sell|supply|deliver|distribute)( directly| direct| straight)? (to|for) (the |your )?(public|consumers?|pharmac(y|ies|ists?)|drugstores?|patients)\M|\m(sale|sales|selling) (directly )?(to|for) (the )?(public|consumers?|pharmac(y|ies)|drugstores?|patients)\M|\msell(ing)? to (pharmac(y|ies)|drugstores?)\M|\m(to|for) your pharmacy\M|\mpharmacy orders?( are)? welcome\M$r$;
delete from private.review_rules where pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$ where pattern = $r$\m(tramadol|tramal|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$;
delete from private.review_rules where pattern = $r$\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e|under your name|for you)|\mwe (can )?import (for you|under your name|on your behalf)\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(we|i)( can| will| also| do)? import(ing)? (on behalf of|for others|for clients|for a client|for you|under your (name|licen[cs]e|company name)|on your (licen[cs]e|card))\M|\mimport(ing)? services? for (others|clients)\M|\mimport(ing)? (under|on) your (licen[cs]e|company name|card)\M|\mimport(ing)? on behalf of (clients|others|a client|your)\M|\mimport(ing)? under our licen[cs]e for (you|clients|others)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(we|i)( can| will| also| do)? import(ing)? (on behalf of|for others|for clients|for a client|for you|under your (name|licen[cs]e|company name)|on your (licen[cs]e|card))\M|\mimport(ing)? services? for (others|clients)\M|\mimport(ing)? (under|on) your (licen[cs]e|company name|card)\M|\mimport(ing)? on behalf of (clients|others|a client|your)\M|\mimport(ing)? under our licen[cs]e for (you|clients|others)\M$r$ where pattern = $r$\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e|under your name|for you)|\mwe (can )?import (for you|under your name|on your behalf)\M$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده(?! عينه)|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده(?! عينه)|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|بالفرط|بيع فرط|فرط شرايط|بالشريط)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترامال|تامول|ليريكا|بريجابالين|كودايين|كوديين|مورفين|فنتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترامال|تامول|ليريكا|بريجابالين|كودايين|كوديين|مورفين|فنتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.\-])t\.me(?![a-z0-9.\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|telegram ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$chat ?\.? ?whatsapp ?\.? ?(com|dot com)|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.@\-])t\.me(?![a-z0-9.@\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|(telegram|tele|تليجرام|تيليجرام|تلجرام) ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/|\m(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|shorturl\.at|is\.gd|t\.co)/$r$);   -- re-run safe
update private.review_rules set pattern = $r$chat ?\.? ?whatsapp ?\.? ?(com|dot com)|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.@\-])t\.me(?![a-z0-9.@\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|(telegram|tele|تليجرام|تيليجرام|تلجرام) ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/|\m(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|shorturl\.at|is\.gd|t\.co)/$r$ where pattern = $r$chat\.whatsapp\.com|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.\-])t\.me(?![a-z0-9.\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|telegram ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(بيع للمرضي|توصيل للمرضي|متاح للمرضي|للمرضي مباشره|للعيانين)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(بيع للمرضي|نبيع للمرضي|بنبيع للمرضي|توصيل للمرضي|متاح للمرضي|للمرضي مباشره|للعيانين)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(بيع للمرضي|نبيع للمرضي|بنبيع للمرضي|توصيل للمرضي|متاح للمرضي|للمرضي مباشره|للعيانين)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(بيع للمرضي|توصيل للمرضي|متاح للمرضي|للمرضي مباشره|للعيانين)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول|بريجابلين)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول|بريجابلين|كودين|كبتجون|كابتاجون|ابتريل|فينتانيل)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول|بريجابلين|كودين|كبتجون|كابتاجون|ابتريل|فينتانيل)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترمادول|ترامدول|بريجابلين)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^a-z])(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^a-z])(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$ where pattern = $r$\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|zanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)(?![a-z])$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترمادول|بريجابالين|بريجابلين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(?:ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(?:ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترمادول|بريجابالين|بريجابلين|ليريكا|مورفين|فنتانيل|زاناكس|ريفوتريل|كلونازيبام|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(جروب|جروبات|مجموعه) (ال)?(واتس|واتساب|الواتس|تليجرام|تلجرام|تيليجرام)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(هضيفك|اضيفك|هنضيفك|نضيفك|ادخل) (لل|علي ال|ع ال|في ال|ال)?(جروب|مجموعه) (ع|علي|في) (ال)?(واتس|واتساب|تليجرام|تلجرام)([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(هضيفك|اضيفك|هنضيفك|نضيفك|ادخل) (لل|علي ال|ع ال|في ال|ال)?(جروب|مجموعه) (ع|علي|في) (ال)?(واتس|واتساب|تليجرام|تلجرام)([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(جروب|جروبات|مجموعه) (ال)?(واتس|واتساب|الواتس|تليجرام|تلجرام|تيليجرام)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(هضيفك|اضيفك|هنضيفك|نضيفك) (لل|علي ال|ع ال|في ال)?(جروب|مجموعه)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(واتس|واتساب|تليجرام|تلجرام)[^.؟!\n]{0,30}((لينك|رابط) (ال)?(جروب|مجموعه)|(هضيفك|اضيفك|هنضيفك|نضيفك) ?(لل|علي ال|ع ال|في ال)?(جروب|مجموعه))|(لينك|رابط) (ال)?(جروب|مجموعه)[^.؟!\n]{0,30}(واتس|واتساب|تليجرام|تلجرام|البايو)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(واتس|واتساب|تليجرام|تلجرام)[^.؟!\n]{0,30}((لينك|رابط) (ال)?(جروب|مجموعه)|(هضيفك|اضيفك|هنضيفك|نضيفك) ?(لل|علي ال|ع ال|في ال)?(جروب|مجموعه))|(لينك|رابط) (ال)?(جروب|مجموعه)[^.؟!\n]{0,30}(واتس|واتساب|تليجرام|تلجرام|البايو)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(هضيفك|اضيفك|هنضيفك|نضيفك) (لل|علي ال|ع ال|في ال)?(جروب|مجموعه)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite|send)|(?<![a-z0-9.\-])t\.me/$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite|send)|(?<![a-z0-9.@\-])t\.me/$r$);   -- re-run safe
update private.review_rules set pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite|send)|(?<![a-z0-9.@\-])t\.me/$r$ where pattern = $r$chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite|send)|(?<![a-z0-9.\-])t\.me/$r$;
delete from private.review_rules where pattern = $r$\m(whatsapp|telegram|viber) (group|channel)s?\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(join|add you to|link to|invite you to|link of) (our|my|the) (whatsapp|telegram|viber) (group|channel)s?\M|\m(whatsapp|telegram) (group|channel) (link|invite)\M|\mlink in (my|our) bio\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(join|add you to|link to|invite you to|link of) (our|my|the) (whatsapp|telegram|viber) (group|channel)s?\M|\m(whatsapp|telegram) (group|channel) (link|invite)\M|\mlink in (my|our) bio\M$r$ where pattern = $r$\m(whatsapp|telegram|viber) (group|channel)s?\M$r$;
delete from private.review_rules where pattern = $r$\mdelivery (to|for) (pharmac(y|ies)|drugstores?)\M|\mpharmac(ies|ists) (are )?welcome\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\mdelivery (to|for) (pharmac(y|ies)|drugstores?)\M|\mpharmacies (are )?welcome to (order|buy)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\mdelivery (to|for) (pharmac(y|ies)|drugstores?)\M|\mpharmacies (are )?welcome to (order|buy)\M$r$ where pattern = $r$\mdelivery (to|for) (pharmac(y|ies)|drugstores?)\M|\mpharmac(ies|ists) (are )?welcome\M$r$;
insert into private.review_rules (topic, squashed, pattern) values
  ('import', false, $r$(^|[^ء-ي])(و|ف)?(نستورد|بنستورد|استيراد) (علي|ع) (رخصتك|رخصتكم|بطاقتك|بطاقتكم|سجلك|سجلكم|بطاقتك الاستيراديه)([^ء-ي]|$)$r$),
  ('sham', false, $r$(^|[^ء-ي])(و|ف)?(شهاده تحليل مضروبه|شهادات تحليل مضروبه|فاتوره مضروبه|شهادات تحليل مزيفه)([^ء-ي]|$)$r$)
on conflict (pattern) do nothing;

-- ── F1/F2/F3 company offers ────
create or replace function public.trade_badge_on_guard() returns trigger language plpgsql set search_path = public as $$
declare n jsonb := to_jsonb(new); o jsonb := to_jsonb(old); turning_on boolean;
begin
  -- 0097 (N1): security-definer actions (listing_renew, a moderator's Publish) run as the server but for a signed-in person: only writes with
  -- no signed-in user (imports, the server's own jobs) skip this
  if auth.uid() is null then return new; end if;
  -- N3: a member who is no longer on the company's team does not change its offers (the company's owners / admins do)
  if current_setting('drugbox.member_left', true) = '1' then return new; end if;   -- 0098 (F1): company_member_left pausing the leaver's offers
  -- N3 / 0098 (F2): an offer that WAS the company's stays the company's: a member no longer on the team neither changes it nor takes it as their own
  if tg_table_name in ('products', 'group_listings') and o ->> 'posted_as' = 'company' and (o ->> 'user_id')::uuid = auth.uid()
     and not public.is_company_member((o ->> 'company_id')::bigint) and not public.is_moderator() then
    raise exception 'You are no longer on this company''s team — its offers are managed by the company' using errcode = '42501', hint = 'DX419';
  end if;
  -- 0098 (F3): someone else on the team (an owner / admin) manages the offer but does not move it to another company or change who posts it
  if tg_table_name in ('products', 'group_listings') and (o ->> 'user_id')::uuid is distinct from auth.uid() and not public.is_moderator()
     and ((n ->> 'company_id') is distinct from (o ->> 'company_id') or (n ->> 'posted_as') is distinct from (o ->> 'posted_as')) then
    raise exception 'Only the person who posted an offer moves it to another company or changes who posts it' using errcode = '42501', hint = 'DX438';
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
create or replace function public.company_member_left() returns trigger language plpgsql security definer set search_path = public as $$
declare n int := 0; k int;
begin
  perform set_config('drugbox.member_left', '1', true);   -- 0098 (F1): the leaver's own offers are paused here, not refused
  update public.products set status = 'paused' where company_id = old.company_id and user_id = old.user_id and posted_as = 'company' and status = 'active';
  get diagnostics k = row_count; n := n + k;
  update public.group_listings set status = 'closed' where company_id = old.company_id and user_id = old.user_id and posted_as = 'company' and status = 'open';
  get diagnostics k = row_count; n := n + k;
  perform set_config('drugbox.member_left', '', true);
  if n > 0 then
    insert into public.notifications (user_id, type, from_user, message, data)
    select c.owner_id, 'company_member_offers_paused', old.user_id, null, jsonb_build_object('company', c.name, 'offers', n)
      from public.companies c where c.id = old.company_id and c.owner_id is not null and c.owner_id <> old.user_id;
  end if;
  return null;
end $$;
revoke all on function public.company_member_left() from public, anon, authenticated, service_role;
grant execute on function public.company_member_left() to service_role;
-- a member no longer on the team does not delete the company's offer (the company's owners / admins do)
create or replace function public.company_offer_delete_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if auth.uid() is null or current_setting('drugbox.member_left', true) = '1' or current_setting('drugbox.hold_decision', true) = '1' then return old; end if;
  if old.posted_as = 'company' and old.user_id = auth.uid() and not public.is_company_member(old.company_id) and not public.is_moderator()
     and exists (select 1 from public.companies c where c.id = old.company_id) then
    raise exception 'You are no longer on this company''s team — its offers are managed by the company' using errcode = '42501', hint = 'DX419';
  end if;
  return old;
end $$;
revoke all on function public.company_offer_delete_guard() from public, anon, authenticated, service_role;
grant execute on function public.company_offer_delete_guard() to authenticated, service_role;
do $$ declare t text; begin
  foreach t in array array['products', 'group_listings'] loop
    execute format('drop trigger if exists trg_%s_company_delete on public.%I', t, t);
    execute format('create trigger trg_%s_company_delete before delete on public.%I for each row execute function public.company_offer_delete_guard()', t, t);
  end loop;
end $$;
drop policy if exists "group listings: the company's owners and admins manage its listings" on public.group_listings;
create policy "group listings: the company's owners and admins manage its listings" on public.group_listings for update to authenticated
  using (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']))
  with check (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']));
drop policy if exists "group listings: the company's owners and admins delete its listings" on public.group_listings;
create policy "group listings: the company's owners and admins delete its listings" on public.group_listings for delete to authenticated
  using (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin']));
-- F10: the company's owners / admins read a held offer of the company (they manage it)
drop policy if exists "products: held for review" on public.products;
create policy "products: held for review" on public.products as restrictive for select
  using (not review_hold or user_id = (select auth.uid()) or (select public.is_moderator())
         or (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin'])));
-- F10: broker fields only on a broker's offer
create or replace function public.offer_broker_clean() returns trigger language plpgsql set search_path = public as $$
begin
  if new.posted_as is distinct from 'broker' then new.broker_for := null; new.broker_commission := null; new.broker_auth_path := null; end if;
  return new;
end $$;
revoke all on function public.offer_broker_clean() from public, anon, authenticated, service_role;
grant execute on function public.offer_broker_clean() to authenticated, service_role;
do $$ declare t text; begin
  foreach t in array array['products', 'group_listings'] loop
    execute format('drop trigger if exists trg_%s_zb_broker_clean on public.%I', t, t);
    execute format('create trigger trg_%s_zb_broker_clean before insert or update on public.%I for each row execute function public.offer_broker_clean()', t, t);
  end loop;
end $$;

-- ── F4 phone codes ────
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
     -- 0098 (F4): one account sends a number at most 3 codes a day; a number's cap counts only OTHER accounts (10 a day), so nobody locks out its owner
     or (select count(*) from private.phone_code_log l where l.phone_hash = h and l.user_id = me and l.sent_at > now() - interval '1 day') >= 3
     or (select count(*) from private.phone_code_log l where l.phone_hash = h and l.user_id <> me and l.sent_at > now() - interval '1 day') >= 10 then
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

-- ── F9 published items ────
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
  -- 0098 (F9): an item Drugbox published is not held again for the same reasons (a price or quantity edit); new reasons hold it again
  if tg_op = 'UPDATE' and exists (select 1 from public.content_holds h where h.kind = private.hold_kind(tg_table_name) and h.item_id = new.id and h.status = 'published'
                                    and h.topics @> private.review_topics(txt)) then return new; end if;
  if cardinality(private.review_topics(txt)) > 0 then
    new.review_hold := true;
    if prod and (to_jsonb(new) ->> 'status') = 'active' then new := jsonb_populate_record(new, jsonb_build_object('status', 'paused')); end if;
    if cl then new := jsonb_populate_record(new, jsonb_build_object('active', false)); end if;
  end if;
  return new;
end $$;
revoke all on function public.review_hold_before() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_before() to authenticated, service_role;

-- ── F7 group names and the partner badge ────
create or replace function public.groups_partner_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then new.partner_at := null; elsif new.partner_at is distinct from old.partner_at then new.partner_at := old.partner_at; end if;
  -- 0096 (F14): Drugbox approved the group under its name — a new name asks again (the badge is not carried to "Drugbox Official …")
  if tg_op = 'UPDATE' and old.partner_at is not null and (new.name, new.description, new.cover_url) is distinct from (old.name, old.description, old.cover_url) then new.partner_at := null; end if;   -- 0098 (F7): name, description or cover
  return new;
end $$;
revoke all on function public.groups_partner_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_partner_guard() to authenticated, service_role;
create or replace function public.groups_drugbox_name_guard() returns trigger language plpgsql set search_path = public as $$
declare t text := regexp_replace(regexp_replace(private.review_squash(concat_ws(' ', new.name, new.description)), 'drug ?box', 'drugbox', 'g'), '(دروج|دراج|دراغ|درج) ?بوكس', 'drugbox', 'g');
begin
  if public.is_server_call() or public.is_moderator() then return new; end if;
  if tg_op = 'UPDATE' and new.name is not distinct from old.name and new.description is not distinct from old.description then return new; end if;
  -- 0098 (F7): only a claim of being Drugbox's own ("official Drugbox group", "run by Drugbox", "Drugbox team"), not every name that mentions Drugbox
  if t ~ '\m(official drugbox(?! partner)|drugbox official|drugbox''s own|(run|managed|owned|moderated) by (the )?drugbox|drugbox (team|staff|admins?|support|management)\M)'
     or t ~ 'drugbox ?(الرسمي|الرسميه)|(الرسمي|الرسميه|التابع|تابع|تابعه) (ل|لـ ?)?drugbox|(فريق|اداره|ادمن|مشرفين) drugbox' then
    raise exception 'Only Drugbox''s team names or describes a group as Drugbox''s own — ask for the partner badge instead' using errcode = '42501', hint = 'DX437';
  end if;
  return new;
end $$;
revoke all on function public.groups_drugbox_name_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_drugbox_name_guard() to authenticated, service_role;

notify pgrst, 'reload schema';
