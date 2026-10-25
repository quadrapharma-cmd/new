-- 0099 · w-trust: the independent verifier's fourth round (the last number of this slice's range 0090–0099)
--   B1 (blocking) an owner could not delete a company that had company offers: the cascade (company_id set null) went through the guards —
--      now the offers become their authors' own, paused / closed
--   B2 (blocking, from 0098 F9) a published item could be rewritten into new banned words of the same topic: it stays published only while its
--      words are the ones Drugbox read (content_holds.text_key: its letters; prices, quantities and other numbers may change)
--   M1 a number's cap across accounts let strangers lock its owner out: dropped (per account: 3 an hour, 6 a day, 3 a number a day,
--      3 numbers a day — SMS to one number grow only with new accounts, each of which needs a confirmed e-mail)
--   M2 "-free" no longer lets an offer through ("Tramadol free delivery"); a "codeine-free …" mention is held for a human again
--   M3 a negation strips only a plain statement: a question, "only", "but", "unless", «بس», «كمان»… keep the whole text checked
--   M4 a group's name, description and rules are checked by the W-17 rules too (refused with the reason, DX439)
--   minor: more look-alike letters, plural / suffixed drug names, more link services, import and "any date" papers, «بنوصل لحد الصيدلية»;
--      «البيع للجمهور ممنوع» passes; the partner badge also goes with a new topic or type; the group-name claims verifiers found;
--      company owners / admins manage held deal-room listings of the company

-- ── rules v5: the text ────
create or replace function private.review_norm(p text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(
           regexp_replace(
             regexp_replace(
               translate(
                 regexp_replace(translate(replace(lower(normalize(coalesce(p, ''), NFKC)), '%2e', '.'), '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'), '[ً-ٰٟـ؜᠎​-‏‪-‮⁠-⁤⁦-⁯﻿­͏︀-️]', '', 'g'),
                 'أإآٱةىؤئ。｡․аеорсухіјѕԁԛԝкмтнвαεικνορτυχӏɑʈʀᴀᴍᴅᴏʟ', 'ااااهيوي...aeopcyxijsdqwkmthbaeikvoptuxlatramdol'),
               '\s*(\[\.\]|\(\.\)|\{\.\}|\(dot\)|\[dot\]|\s(dot|نقطه)\s|\.)\s*', '.', 'g'),
             '\s+/', '/', 'g'),
           '\s+', ' ', 'g')
$$;
revoke all on function private.review_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.review_norm(text) to authenticated, service_role;
create or replace function private.review_neg(n text) returns text language sql immutable set search_path = public as $$
  select case when coalesce(n, '') ~ '[?؟]|(?<!distributors )(?<!wholesalers )(?<!companies )(?<!factories )(?<!manufacturers )(?<!warehouses )\monly\M|\m(too|also|but|except|unless|however|wrong|exception|instead|anyway|guaranteed|made to order|any date)\M|(^|[^ء-ي])(بس|كمان|الا|لكن|خالص|برضه|برضو|غير ان)([^ء-ي]|$)'
    then coalesce(n, '') else
  regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(coalesce(n, ''),
    '\m(we (do not|don''t|never|won''t|will not)|do not|don''t|never|no|not)( directly| ever)? (sell|sale|sales|selling|supply|supplying|deliver|delivery|distribute|distributing)( directly)?( to| for)? (the |any |retail )?(public|pharmac(y|ies|ists?)|drugstores?|patients|consumers)\M( or (the )?(public|pharmac(y|ies|ists?)|patients|consumers)\M)?', ' ', 'g'),
    '\mnot for (retail )?sale( to (the )?(public|pharmac(y|ies)|patients|consumers))?\M', ' ', 'g'),
    '\m(sale|sales|selling|delivery) to (the )?(public|pharmac(y|ies)|patients|consumers) (is|are) (not allowed|forbidden|prohibited|not permitted)\M', ' ', 'g'),
    '\m(no|spot|spotting|detect|detecting|detection of|against|beware of) (sham|fake|fictitious|forged|backdated) [a-z]+( (and|or) (sham|fake|fictitious|forged|backdated) [a-z]+)?', ' ', 'g'),
    '\m(sham|fake|fictitious|forged|backdated) [a-z]+ (detection|training|awareness)\M', ' ', 'g'),
    '(^|[^ء-ي])(لا|مش|مبن|ما|ممنوع|غير مسموح) ?(نبيع|بنبيع|بيع|البيع|نوزع|بنوزع|يوجد توصيل|توصيل|التوصيل) (لل|ل|علي ال)?(صيادله|صيدليات|صيدليه|مرضي|جمهور)([^ء-ي]|$)', '\1 \6', 'g'),
    '(^|[^ء-ي])(البيع|بيع|التوصيل|توصيل) (لل|ل)(صيادله|صيدليات|صيدليه|مرضي|جمهور) (ممنوع|غير مسموح)([^ء-ي]|$)', '\1 \6', 'g') end
$$;
revoke all on function private.review_neg(text) from public, anon, authenticated, service_role;
grant execute on function private.review_neg(text) to authenticated, service_role;

-- ── rules v5 ────
delete from private.review_rules where pattern = $r$\m(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(tramado+l+e?s?|tram+ad+o+l+e?s?|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(tramado+l+e?s?|tram+ad+o+l+e?s?|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])$r$ where pattern = $r$\m(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$;
delete from private.review_rules where pattern = $r$(^|[^a-z])(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^a-z])(tramado+l+e?s?|tram+ad+o+l+e?s?|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^a-z])(tramado+l+e?s?|tram+ad+o+l+e?s?|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])$r$ where pattern = $r$(^|[^a-z])(tramadol|tram+ad+o+l|tramal|tapentadol|pregabal[ie]n|lyrica|codeine|codiene|morphine|morfin|fentan[iy]l|oxycodone|methadone|alprazolam|[xz]ana(x|ks)|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine?|methylphenidate|ritalin|[ck]apt[ae]g[oa]ne?|fenethylline|nalbuphine|pethidine|buprenorphine|apetryl|abetryl)(?![a-z])(?!-free| free)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)(ات)?([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)(ات)?([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(?:ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(?:ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)(ات)?([^ء-ي]|$)$r$);   -- re-run safe
update private.review_rules set pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(?:ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)(ات)?([^ء-ي]|$)$r$ where pattern = $r$(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(?:ترامادو+ل|ترمادول|ترامدول|ترامال|تامول|ليريكا|بريجابالين|بريجابلين|كودايين|كوديين|كودين|مورفين|فنتانيل|فينتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|كبتجون|كابتاجون|نالبوفين|بيثيدين|ابتريل)([^ء-ي]|$)$r$;
delete from private.review_rules where pattern = $r$chat ?\.? ?whatsapp ?\.? ?(com|dot com)|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.@\-])t\.me(?![a-z0-9.@\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|(telegram|tele|تليجرام|تيليجرام|تلجرام) ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/|\m(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|shorturl\.at|is\.gd|t\.co)/$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$chat ?\.? ?whatsapp ?\.? ?(com|dot com)|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.@\-])t\.me(?![a-z0-9.@\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|(telegram|tele|تليجرام|تيليجرام|تلجرام) ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/|\m(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|shorturl\.at|is\.gd|t\.co)/|\m(t\.ly|s\.id|linktr\.ee)/|signal\.group/|\mtg ?:? ?@[a-z0-9_]{4,}$r$);   -- re-run safe
update private.review_rules set pattern = $r$chat ?\.? ?whatsapp ?\.? ?(com|dot com)|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.@\-])t\.me(?![a-z0-9.@\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|(telegram|tele|تليجرام|تيليجرام|تلجرام) ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/|\m(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|shorturl\.at|is\.gd|t\.co)/|\m(t\.ly|s\.id|linktr\.ee)/|signal\.group/|\mtg ?:? ?@[a-z0-9_]{4,}$r$ where pattern = $r$chat ?\.? ?whatsapp ?\.? ?(com|dot com)|wa\.me/|wa\.link/|api\.whatsapp\.com/send|whatsapp\.com/(channel|invite|send)|whatsapp://|(?<![a-z0-9.@\-])t\.me(?![a-z0-9.@\-])|tg://|telegram\.(me|dog)/|telegram\.org/joinchat|(telegram|tele|تليجرام|تيليجرام|تلجرام) ?:? ?@[a-z0-9_]{4,}|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/|facebook\.com/groups/|fb\.com/groups?/|m\.me/j/|\m(bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|shorturl\.at|is\.gd|t\.co)/$r$;
delete from private.review_rules where pattern = $r$\m(join|add you to|link to|invite you to|link of) (our|my|the) (whatsapp|telegram|viber) (group|channel)s?\M|\m(whatsapp|telegram) (group|channel) (link|invite)\M|\mlink in (my|our) bio\M$r$ and exists (select 1 from private.review_rules x where x.pattern = $r$\m(join|add you to|link to|invite you to|link of) (our|my|the) (whatsapp|telegram|viber) (group|channel)s?\M|\m(whatsapp|telegram) (group|channel) (link|invite)\M|\mlink in (my|our) bio\M|\m(whatsapp|telegram) communit(y|ies)\M$r$);   -- re-run safe
update private.review_rules set pattern = $r$\m(join|add you to|link to|invite you to|link of) (our|my|the) (whatsapp|telegram|viber) (group|channel)s?\M|\m(whatsapp|telegram) (group|channel) (link|invite)\M|\mlink in (my|our) bio\M|\m(whatsapp|telegram) communit(y|ies)\M$r$ where pattern = $r$\m(join|add you to|link to|invite you to|link of) (our|my|the) (whatsapp|telegram|viber) (group|channel)s?\M|\m(whatsapp|telegram) (group|channel) (link|invite)\M|\mlink in (my|our) bio\M$r$;
insert into private.review_rules (topic, squashed, pattern) values
  ('import', false, $r$\m(imports?|importing|handle imports?) (under|on|in) your (licen[cs]e|name|company name)\M|\mhandle imports? for (clients|others)\M|\mimport (it )?(on your behalf|in your name)\M$r$),
  ('import', false, $r$(^|[^ء-ي])(و|ف)?(استيراد لحسابك|استيراد لحسابكم|نستورد لحساب الغير|بنستورد لحساب الغير|نستورد لحسابك|بنستورد لحسابك)([^ء-ي]|$)$r$),
  ('sham', false, $r$\m(coas?|invoices?|certificates?|papers?|documents?)\M[^.;\n]{0,30}\many (date|batch)\M$r$),
  ('sham', false, $r$(شهاده|شهادات|فاتوره|فواتير)[^.؟\n]{0,25}(باي|ب اي) تاريخ$r$),
  ('retail', false, $r$(^|[^ء-ي])(و|ف)?(نوصل|بنوصل|هنوصل) (لحد |لل|ل)?(الصيدليه|صيدليه|الصيدليات|صيدليات|صيدليتك)([^ء-ي]|$)$r$)
on conflict (pattern) do nothing;

-- ── B2 the words Drugbox read ────
alter table public.content_holds add column if not exists text_key text;
create or replace function private.text_key(p text) returns text language sql immutable set search_path = public as $$
  -- its letters, without numbers and the words of a price or a quantity (currency, unit, pack): editing those does not change it
  select md5(regexp_replace(regexp_replace(private.review_norm(p),
    '\m(usd|us|egp|eur|sar|aed|le|kg|kgs|g|gm|mg|mcg|ml|l|mt|ton|tons|box|boxes|pack|packs|per|x|pcs|unit|units|vial|vials|strips?|جنيه|ج|دولار|يورو|كجم|كيلو|جم|مجم|طن|علبه|علب|شريط)\M', ' ', 'g'),
    '[^[:alpha:]]+', '', 'g'))
$$;
revoke all on function private.text_key(text) from public, anon, authenticated, service_role;
grant execute on function private.text_key(text) to authenticated, service_role;
create or replace function private.item_text(p_kind text, p_id bigint) returns text language sql stable security definer set search_path = public as $$
  select case p_kind when 'post' then (select private.review_text('posts', to_jsonb(x)) from public.posts x where x.id = p_id)
                     when 'offer' then (select private.review_text('products', to_jsonb(x)) from public.products x where x.id = p_id)
                     when 'company' then (select private.review_text('company_listings', to_jsonb(x)) from public.company_listings x where x.id = p_id)
                     else (select private.review_text('group_listings', to_jsonb(x)) from public.group_listings x where x.id = p_id) end
$$;
revoke all on function private.item_text(text, bigint) from public, anon, authenticated, service_role;
grant execute on function private.item_text(text, bigint) to authenticated, service_role;

-- ── M4 a group's name, description and rules ────
create or replace function public.groups_review_guard() returns trigger language plpgsql security definer set search_path = public as $$
declare t text[];
begin
  if auth.uid() is null or exists (select 1 from public.profiles p where p.id = auth.uid() and p.role in ('admin', 'moderator')) then return new; end if;
  if tg_op = 'UPDATE' and (new.name, new.description, new.rules) is not distinct from (old.name, old.description, old.rules) then return new; end if;
  t := private.review_topics(concat_ws(' ', new.name, new.description, new.rules::text));
  if cardinality(t) > 0 then
    raise exception 'This group''s name, description or rules look outside Drugbox trade (a sale to patients, pharmacies or the public, controlled substances, import for others, sham papers or an invite link to an outside group) — change them'
      using errcode = 'P0001', hint = 'DX439';
  end if;
  return new;
end $$;
revoke all on function public.groups_review_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_review_guard() to authenticated, service_role;
drop trigger if exists trg_groups_review_guard on public.groups;
create trigger trg_groups_review_guard before insert or update on public.groups for each row execute function public.groups_review_guard();

-- ── B1 deleting a company ────
create or replace function public.trade_badge_on_guard() returns trigger language plpgsql set search_path = public as $$
declare n jsonb := to_jsonb(new); o jsonb := to_jsonb(old); turning_on boolean;
begin
  -- 0097 (N1): security-definer actions (listing_renew, a moderator's Publish) run as the server but for a signed-in person: only writes with
  -- no signed-in user (imports, the server's own jobs) skip this
  if auth.uid() is null then return new; end if;
  -- N3: a member who is no longer on the company's team does not change its offers (the company's owners / admins do)
  if current_setting('drugbox.member_left', true) = '1' then return new; end if;
  -- 0099 (B1): the company itself is being deleted (company_id set null by the cascade): its offers become the authors' own, paused / closed
  if (o ->> 'company_id') is not null and (n ->> 'company_id') is null and not exists (select 1 from public.companies c where c.id = (o ->> 'company_id')::bigint) then
    if tg_table_name = 'products' then new := jsonb_populate_record(new, jsonb_build_object('posted_as', 'individual', 'status', case when (o ->> 'status') = 'active' then 'paused' else o ->> 'status' end));
    elsif tg_table_name = 'group_listings' then new := jsonb_populate_record(new, jsonb_build_object('posted_as', 'individual', 'status', 'closed')); end if;
    return new;
  end if;   -- 0098 (F1): company_member_left pausing the leaver's offers
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

-- ── B2 ────
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
  -- 0098 (F9): an item Drugbox published is not held again on a price or quantity edit…
  -- 0099 (B2): … only while its words are the ones Drugbox read (prices, quantities and other numbers may change); new words are checked again
  if tg_op = 'UPDATE' and exists (select 1 from public.content_holds h where h.kind = private.hold_kind(tg_table_name) and h.item_id = new.id and h.status = 'published'
                                    and h.text_key = private.text_key(txt)) then return new; end if;
  if cardinality(private.review_topics(txt)) > 0 then
    new.review_hold := true;
    if prod and (to_jsonb(new) ->> 'status') = 'active' then new := jsonb_populate_record(new, jsonb_build_object('status', 'paused')); end if;
    if cl then new := jsonb_populate_record(new, jsonb_build_object('active', false)); end if;
  end if;
  return new;
end $$;
revoke all on function public.review_hold_before() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_before() to authenticated, service_role;
create or replace function public.held_review_decide(p_hold bigint, p_publish boolean, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare h public.content_holds; me uuid := auth.uid(); v_note text := nullif(left(trim(coalesce(p_note, '')), 500), ''); out text; c public.company_listings;
begin
  if me is null or not public.is_moderator() then raise exception 'Only the Drugbox team can do this' using errcode = '42501'; end if;
  select * into h from public.content_holds where id = p_hold for update;
  if h.id is null then raise exception 'This item is not in the queue' using errcode = 'P0002'; end if;
  if h.status <> 'held' then raise exception 'Already decided by % (%)', private.who(h.decided_by), h.status using errcode = 'DX409'; end if;
  out := case when p_publish then 'published' else 'removed' end;
  update public.content_holds set status = out, decided_by = me, decided_at = now(), note = v_note,
         text_key = case when p_publish then private.text_key(private.item_text(h.kind, h.item_id)) end where id = h.id;   -- 0099 (B2): the words Drugbox read
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

-- ── M1 phone codes ────
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
     -- 0098 (F4): one account sends a number at most 3 codes a day
     or (select count(*) from private.phone_code_log l where l.phone_hash = h and l.user_id = me and l.sent_at > now() - interval '1 day') >= 3 then   -- 0099 (M1): no cap on a number across accounts — any such cap lets strangers lock its owner out
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

-- ── groups: the partner badge, Drugbox's name, held company listings ────
create or replace function public.groups_partner_guard() returns trigger language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then new.partner_at := null; elsif new.partner_at is distinct from old.partner_at then new.partner_at := old.partner_at; end if;
  -- 0096 (F14): Drugbox approved the group under its name — a new name asks again (the badge is not carried to "Drugbox Official …")
  if tg_op = 'UPDATE' and old.partner_at is not null and (new.name, new.description, new.cover_url, new.topic, new.type) is distinct from (old.name, old.description, old.cover_url, old.topic, old.type) then new.partner_at := null; end if;   -- 0098 (F7): name, description or cover
  return new;
end $$;
revoke all on function public.groups_partner_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_partner_guard() to authenticated, service_role;
create or replace function public.groups_drugbox_name_guard() returns trigger language plpgsql set search_path = public as $$
declare t text := regexp_replace(regexp_replace(regexp_replace(regexp_replace(private.review_squash(concat_ws(' ', new.name, new.description)), '[®™©_]', ' ', 'g'),
                           'drug[ .\-]?box', 'drugbox', 'g'), '(دروج|دراج|دراغ|درج) ?بوكس', 'drugbox', 'g'), 'drugbox(official|team|staff|admins?|hq|support)', 'drugbox \1', 'g');
begin
  if public.is_server_call() or public.is_moderator() then return new; end if;
  if tg_op = 'UPDATE' and new.name is not distinct from old.name and new.description is not distinct from old.description then return new; end if;
  -- 0098 (F7): only a claim of being Drugbox's own ("official Drugbox group", "run by Drugbox", "Drugbox team"), not every name that mentions Drugbox
  -- 0099: the claims verifiers found ("Drugbox HQ", "operated by Drugbox", "Drugbox Verified Traders", «Drugbox الاصلي», a partner claim without the badge)
  if t ~ '\m(official drugbox(?! partner)|drugbox official|drugbox''s own|(run|managed|owned|moderated|operated) by (the )?drugbox|drugbox (team|staff|admins?|moderators?|support|management|hq|customer (care|service)|verified)\M(?![ -](building|picks|ideas|talk|tips|spirit)))'
     or (t ~ '\mdrugbox partner' and new.partner_at is null)
     or t ~ 'drugbox ?(الرسمي|الرسميه|الاصلي|الاصليه)|(الرسمي|الرسميه|التابع|تابع|تابعه) (ل|لـ ?)?drugbox|(فريق|اداره|ادمن|مشرفين) drugbox' then
    raise exception 'Only Drugbox''s team names or describes a group as Drugbox''s own — ask for the partner badge instead' using errcode = '42501', hint = 'DX437';
  end if;
  return new;
end $$;
revoke all on function public.groups_drugbox_name_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_drugbox_name_guard() to authenticated, service_role;
drop policy if exists "group listings: held for review" on public.group_listings;
create policy "group listings: held for review" on public.group_listings as restrictive for select
  using (not review_hold or user_id = (select auth.uid()) or (select public.is_moderator())
         or (posted_as = 'company' and public.is_company_member(company_id, array['owner', 'admin'])));

notify pgrst, 'reload schema';
