-- ═════════════════════════════════════════════════════════════════════
-- 0037 — names a person can tell apart, round 3; conversations say who the other person is (phase 1b, S-03)
--   1. clean_person_name() (0036) listed the invisible characters and the dot look-alikes one by one, so others got through:
--      "Dr. Hala X ꞏ Pharco X" (U+A78F) or "… ⸳ …" (U+2E33) passed for the Pharco Dr. Hala X in the ✎ New message picker,
--      and "Dr. Zeina X" + U+1D173 (a default-ignorable character) looked exactly like "Dr. Zeina X". The rule is now
--      generated from the Unicode properties (tools/names/name_rule.mjs) and is the same in the live app (nmClean):
--        1. remove every Default_Ignorable_Code_Point, every format (Cf) and control (Cc) character, and blank-drawing
--           characters (U+2800, U+1D159)        2. NFKC        3. every kind of space or line break is one space
--        4. a combining mark with no letter before it is removed (it would draw a free dot: "X ˙ Y" is "X  ̇ Y" after NFKC)
--        5. every dot or bullet look-alike (52 of them, any script) and an Arabic-Indic zero standing alone become " - "
--        6. one space between words, none at the ends
--      supabase/tests/name_rule.sql compares this function with the app's nmClean for every Unicode code point.
--      Existing names are cleaned again here.
--   2. my_conversations() also returns the other person's company and city, so a conversation the other person started
--      shows what tells two members with the same name apart (the list and the chat header), and the app knows WHICH
--      member a conversation is with when 👤 or 📞 is pressed (it used to look the person up by name and could open the
--      other twin's profile and count the view on them).
-- Every function keeps its own GRANT/REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. one rule for names (the app's nmClean is the same) ───────────
create or replace function public.clean_person_name(s text)
returns text language sql immutable parallel safe as $$
  select nullif(btrim(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
    normalize(regexp_replace(coalesce(s, ''),
      -- 1. invisible: Default_Ignorable_Code_Point, Cf, Cc (not tab or line breaks), U+2800, U+1D159
      U&'[!0001-!0008!000E-!001F!007F-!0084!0086-!009F!00AD!034F!0600-!0605!061C!06DD!070F!0890-!0891!08E2!115F-!1160!17B4-!17B5!180B-!180F!200B-!200F'
      '!202A-!202E!2060-!206F!2800!3164!FE00-!FE0F!FEFF!FFA0!FFF0-!FFFB!+0110BD!+0110CD!+013430-!+01343F!+01BCA0-!+01BCA3!+01D159!+01D173-!+01D17A'
      '!+0E0000-!+0E0FFF]' uescape '!', '', 'g'), NFKC),
      -- 3. every kind of space, tab or line break
      U&'[!0009-!000D!0020!0085!00A0!1680!2000-!200A!2028-!2029!202F!205F!3000]' uescape '!', ' ', 'g'),
      -- 4. a combining mark at the start or after a space (no letter to sit on)
      '(^| )' || U&'[!0300-!034E!0350-!036F!0483-!0489!0591-!05BD!05BF!05C1-!05C2!05C4-!05C5!05C7!0610-!061A!064B-!065F!0670!06D6-!06DC!06DF-!06E4!06E7-!06E8!06EA-!06ED'
      '!0711!0730-!074A!07A6-!07B0!07EB-!07F3!07FD!0816-!0819!081B-!0823!0825-!0827!0829-!082D!0859-!085B!0897-!089F!08CA-!08E1!08E3-!0903!093A-!093C'
      '!093E-!094F!0951-!0957!0962-!0963!0981-!0983!09BC!09BE-!09C4!09C7-!09C8!09CB-!09CD!09D7!09E2-!09E3!09FE!0A01-!0A03!0A3C!0A3E-!0A42!0A47-!0A48'
      '!0A4B-!0A4D!0A51!0A70-!0A71!0A75!0A81-!0A83!0ABC!0ABE-!0AC5!0AC7-!0AC9!0ACB-!0ACD!0AE2-!0AE3!0AFA-!0AFF!0B01-!0B03!0B3C!0B3E-!0B44!0B47-!0B48'
      '!0B4B-!0B4D!0B55-!0B57!0B62-!0B63!0B82!0BBE-!0BC2!0BC6-!0BC8!0BCA-!0BCD!0BD7!0C00-!0C04!0C3C!0C3E-!0C44!0C46-!0C48!0C4A-!0C4D!0C55-!0C56!0C62-!0C63'
      '!0C81-!0C83!0CBC!0CBE-!0CC4!0CC6-!0CC8!0CCA-!0CCD!0CD5-!0CD6!0CE2-!0CE3!0CF3!0D00-!0D03!0D3B-!0D3C!0D3E-!0D44!0D46-!0D48!0D4A-!0D4D!0D57!0D62-!0D63'
      '!0D81-!0D83!0DCA!0DCF-!0DD4!0DD6!0DD8-!0DDF!0DF2-!0DF3!0E31!0E34-!0E3A!0E47-!0E4E!0EB1!0EB4-!0EBC!0EC8-!0ECE!0F18-!0F19!0F35!0F37!0F39!0F3E-!0F3F'
      '!0F71-!0F84!0F86-!0F87!0F8D-!0F97!0F99-!0FBC!0FC6!102B-!103E!1056-!1059!105E-!1060!1062-!1064!1067-!106D!1071-!1074!1082-!108D!108F!109A-!109D'
      '!135D-!135F!1712-!1715!1732-!1734!1752-!1753!1772-!1773!17B6-!17D3!17DD!1885-!1886!18A9!1920-!192B!1930-!193B!1A17-!1A1B!1A55-!1A5E!1A60-!1A7C!1A7F'
      '!1AB0-!1ACE!1B00-!1B04!1B34-!1B44!1B6B-!1B73!1B80-!1B82!1BA1-!1BAD!1BE6-!1BF3!1C24-!1C37!1CD0-!1CD2!1CD4-!1CE8!1CED!1CF4!1CF7-!1CF9!1DC0-!1DFF'
      '!20D0-!20F0!2CEF-!2CF1!2D7F!2DE0-!2DFF!302A-!302F!3099-!309A!A66F-!A672!A674-!A67D!A69E-!A69F!A6F0-!A6F1!A802!A806!A80B!A823-!A827!A82C!A880-!A881'
      '!A8B4-!A8C5!A8E0-!A8F1!A8FF!A926-!A92D!A947-!A953!A980-!A983!A9B3-!A9C0!A9E5!AA29-!AA36!AA43!AA4C-!AA4D!AA7B-!AA7D!AAB0!AAB2-!AAB4!AAB7-!AAB8'
      '!AABE-!AABF!AAC1!AAEB-!AAEF!AAF5-!AAF6!ABE3-!ABEA!ABEC-!ABED!FB1E!FE20-!FE2F!+0101FD!+0102E0!+010376-!+01037A!+010A01-!+010A03!+010A05-!+010A06'
      '!+010A0C-!+010A0F!+010A38-!+010A3A!+010A3F!+010AE5-!+010AE6!+010D24-!+010D27!+010D69-!+010D6D!+010EAB-!+010EAC!+010EFC-!+010EFF!+010F46-!+010F50'
      '!+010F82-!+010F85!+011000-!+011002!+011038-!+011046!+011070!+011073-!+011074!+01107F-!+011082!+0110B0-!+0110BA!+0110C2!+011100-!+011102'
      '!+011127-!+011134!+011145-!+011146!+011173!+011180-!+011182!+0111B3-!+0111C0!+0111C9-!+0111CC!+0111CE-!+0111CF!+01122C-!+011237!+01123E!+011241'
      '!+0112DF-!+0112EA!+011300-!+011303!+01133B-!+01133C!+01133E-!+011344!+011347-!+011348!+01134B-!+01134D!+011357!+011362-!+011363!+011366-!+01136C'
      '!+011370-!+011374!+0113B8-!+0113C0!+0113C2!+0113C5!+0113C7-!+0113CA!+0113CC-!+0113D0!+0113D2!+0113E1-!+0113E2!+011435-!+011446!+01145E'
      '!+0114B0-!+0114C3!+0115AF-!+0115B5!+0115B8-!+0115C0!+0115DC-!+0115DD!+011630-!+011640!+0116AB-!+0116B7!+01171D-!+01172B!+01182C-!+01183A'
      '!+011930-!+011935!+011937-!+011938!+01193B-!+01193E!+011940!+011942-!+011943!+0119D1-!+0119D7!+0119DA-!+0119E0!+0119E4!+011A01-!+011A0A'
      '!+011A33-!+011A39!+011A3B-!+011A3E!+011A47!+011A51-!+011A5B!+011A8A-!+011A99!+011C2F-!+011C36!+011C38-!+011C3F!+011C92-!+011CA7!+011CA9-!+011CB6'
      '!+011D31-!+011D36!+011D3A!+011D3C-!+011D3D!+011D3F-!+011D45!+011D47!+011D8A-!+011D8E!+011D90-!+011D91!+011D93-!+011D97!+011EF3-!+011EF6'
      '!+011F00-!+011F01!+011F03!+011F34-!+011F3A!+011F3E-!+011F42!+011F5A!+013440!+013447-!+013455!+01611E-!+01612F!+016AF0-!+016AF4!+016B30-!+016B36'
      '!+016F4F!+016F51-!+016F87!+016F8F-!+016F92!+016FE4!+016FF0-!+016FF1!+01BC9D-!+01BC9E!+01CF00-!+01CF2D!+01CF30-!+01CF46!+01D165-!+01D169'
      '!+01D16D-!+01D172!+01D17B-!+01D182!+01D185-!+01D18B!+01D1AA-!+01D1AD!+01D242-!+01D244!+01DA00-!+01DA36!+01DA3B-!+01DA6C!+01DA75!+01DA84'
      '!+01DA9B-!+01DA9F!+01DAA1-!+01DAAF!+01E000-!+01E006!+01E008-!+01E018!+01E01B-!+01E021!+01E023-!+01E024!+01E026-!+01E02A!+01E08F!+01E130-!+01E136'
      '!+01E2AE!+01E2EC-!+01E2EF!+01E4EC-!+01E4EF!+01E5EE-!+01E5EF!+01E8D0-!+01E8D6!+01E944-!+01E94A]' uescape '!' || '+', '\1', 'g'),
      -- 5a. an Arabic-Indic zero standing alone draws a mid-height dot
      '(^| )' || U&'[!0660!06F0]' uescape '!' || '+(?= |$)', '\1-', 'g'),
      -- 5b. a dot or bullet look-alike: the picker's "·"
      ' *' || U&'[!00B7!02D1!0387!0887!0888!0971!0F0B!0F0C!119E!1427!16EB!16EC!18DF!2022!2023!2027!2043!204C!204D!2219!22C5!25CF!25D8!25E6!2619!26AB!2765!2767!2981!29BE'
      
      '!29BF!2B24!2E30!2E31!2E33!30FB!318D!A78F!FE45!FE46!FF65!+010101!+01091F!+010A50!+010AF4!+011049!+01123A!+0115C4!+011A41!+011A9A!+011C43!+01F784]' uescape '!' || '+ *', ' - ', 'g'),
    ' +', ' ', 'g'), ' '), '')
$$;
revoke all on function public.clean_person_name(text) from public, anon, authenticated, service_role;
grant execute on function public.clean_person_name(text) to authenticated, service_role;   -- the name trigger runs as the writer

update public.profiles set name = left(coalesce(public.clean_person_name(name), 'Member'), 200)
 where name is distinct from left(coalesce(public.clean_person_name(name), 'Member'), 200);

-- ── 2. conversations carry the other person's company and city ───────
drop function if exists public.my_conversations(int);
create function public.my_conversations(p_limit int default 30)
returns table (partner uuid, name text, headline text, verified boolean, avatar_url text,
               last_body text, last_at timestamptz, last_from_me boolean, unread int, company text, location text)
language sql stable security invoker set search_path = public as $$
  select h.partner, p.name, p.headline, p.verified, p.avatar_url, h.last_body, h.last_at, h.last_from_me, h.unread, p.company, p.location
  from public.conversation_heads h join public.profiles p on p.id = h.partner
  where h.owner = (select auth.uid())
  order by h.last_at desc
  limit least(greatest(coalesce(p_limit, 30), 1), 100)
$$;
revoke all on function public.my_conversations(int) from public, anon, authenticated, service_role;
grant execute on function public.my_conversations(int) to authenticated, service_role;

notify pgrst, 'reload schema';
