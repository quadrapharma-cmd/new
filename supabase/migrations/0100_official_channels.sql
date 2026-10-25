-- ═════════════════════════════════════════════════════════════════════
-- 0100 — Official Drugbox channels, the content scheduler and therapeutic tags (AREA w-growth: W-41, W-21)
--   1. channels      groups.official / channel_key / name_ar / description_ar / thera: four channels (News, Jobs, Regulatory,
--                    Market) owned by Drugbox — no member is their admin; only Drugbox admins post to them, and only through
--                    the scheduler (channel_publish_now / the runner), so every post there is Drugbox speaking as Drugbox
--                    (posts.as_drugbox, shown as "Drugbox" with the official badge; the publishing admin is kept for the record)
--   2. scheduler     channel_schedule: draft → scheduled (date/time in Africa/Cairo) → published by the runner, edit / cancel
--                    before that; channel_templates: the W-41 content plan as ready templates (daily «مطلوب النهارده» 21:00,
--                    weekly bulletin / file ads / agency market / practical guide / shortages)
--   3. thera         W-21 therapeutic areas (biologics, veterinary, agriculture, GLP-1, oncology, growth hormone, fertility,
--                    insulin): read from the text of posts and marketplace products by a small dictionary
--                    (private.thera_terms), plus the tags a channel post is given; feed_thera() and market_search_thera()
--                    filter on the server
--   4. runner        growth_tick() (service role only): publishes what is due and sends the reminders of later migrations;
--                    pg_cron runs it every minute when the project has pg_cron (deploy/supabase_deploy.sh schedules it too),
--                    the local stack calls it from tools/local-supabase/functions-local.js
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. channels ─────────────────────────────────────────────────────────────────────────────────────────
alter table public.groups add column if not exists official       boolean not null default false;
alter table public.groups add column if not exists channel_key    text;
alter table public.groups add column if not exists name_ar        text;
alter table public.groups add column if not exists description_ar text;
alter table public.groups add column if not exists thera          text[] not null default '{}';
do $$ begin
  alter table public.groups add constraint groups_channel_key_chk check (channel_key is null or (official and channel_key in ('news', 'jobs', 'regulatory', 'market')));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.groups add constraint groups_ar_len check (length(name_ar) <= 120 and length(description_ar) <= 2000);
exception when duplicate_object then null; end $$;
create unique index if not exists idx_groups_channel_key on public.groups (channel_key) where channel_key is not null;
create index if not exists idx_groups_official on public.groups (id) where official;

-- the W-21 therapeutic areas (one list for groups, posts and products)
create or replace function public.thera_ok(t text[]) returns boolean language sql immutable as $$
  select coalesce(t <@ array['biologics', 'veterinary', 'agriculture', 'glp1', 'oncology', 'growth_hormone', 'fertility', 'insulin']::text[], true)
     and coalesce(cardinality(t), 0) <= 8
$$;
revoke all on function public.thera_ok(text[]) from public, anon, authenticated, service_role;
grant execute on function public.thera_ok(text[]) to authenticated, service_role;
do $$ begin
  alter table public.groups add constraint groups_thera_chk check (public.thera_ok(thera));
exception when duplicate_object then null; end $$;
create index if not exists idx_groups_thera on public.groups using gin (thera);

-- official, channel_key and the Arabic texts / tags are Drugbox's: a group's own admins cannot set them, and nobody but a Drugbox
-- admin (or the server) changes an official group at all; nobody creates one from the browser
create or replace function public.groups_official_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then
    if new.official or new.channel_key is not null then raise exception 'Only Drugbox makes official channels' using errcode = '42501'; end if;
    new.name_ar := null; new.description_ar := null; new.thera := '{}';
    return new;
  end if;
  if (new.official, new.channel_key, new.name_ar, new.description_ar, new.thera) is distinct from (old.official, old.channel_key, old.name_ar, old.description_ar, old.thera)
     or old.official then
    if not public.is_platform_admin() then raise exception 'Only a Drugbox admin changes an official channel' using errcode = '42501'; end if;
    if new.official is distinct from old.official or new.channel_key is distinct from old.channel_key then
      raise exception 'A channel stays a channel' using errcode = '42501'; end if;
    if new.official and (new.type <> 'public' or new.post_policy <> 'admins') then raise exception 'An official channel is public and only Drugbox posts there' using errcode = '42501'; end if;
  end if;
  return new;
end $$;
revoke all on function public.groups_official_guard() from public, anon, authenticated, service_role;
grant execute on function public.groups_official_guard() to service_role;
drop trigger if exists trg_groups_official_guard on public.groups;
create trigger trg_groups_official_guard before insert or update on public.groups for each row execute function public.groups_official_guard();

-- a Drugbox admin edits a channel's settings (the "admins edit the settings" policy is for the group's own admins)
drop policy if exists "groups: Drugbox admins edit official channels" on public.groups;
create policy "groups: Drugbox admins edit official channels" on public.groups for update to authenticated
  using (official and public.is_platform_admin()) with check (official and public.is_platform_admin());

-- nobody is a channel's admin or moderator: membership there is reading (join / leave)
create or replace function public.group_members_official_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.role <> 'member' and exists (select 1 from public.groups g where g.id = new.group_id and g.official) then
    raise exception 'Official channels have no member admins — Drugbox runs them' using errcode = '42501';
  end if;
  return new;
end $$;
revoke all on function public.group_members_official_guard() from public, anon, authenticated, service_role;
grant execute on function public.group_members_official_guard() to service_role;
drop trigger if exists trg_group_members_official_guard on public.group_members;
create trigger trg_group_members_official_guard before insert or update on public.group_members for each row execute function public.group_members_official_guard();

-- posts: as_drugbox is the server's (only the channel publisher sets it); thera is read from the text
alter table public.posts add column if not exists as_drugbox boolean not null default false;
alter table public.posts add column if not exists thera text[] not null default '{}';
do $$ begin
  alter table public.posts add constraint posts_thera_chk check (public.thera_ok(thera));
exception when duplicate_object then null; end $$;
create index if not exists idx_posts_thera on public.posts using gin (thera) where group_id is null;
create index if not exists idx_posts_drugbox on public.posts (group_id, created_at desc) where as_drugbox;

-- a Drugbox post is Drugbox's: its publishing admin keeps no own-post rights over it once no longer a Drugbox admin
drop policy if exists "posts: a Drugbox post is changed by Drugbox admins only" on public.posts;
create policy "posts: a Drugbox post is changed by Drugbox admins only" on public.posts as restrictive for update to authenticated
  using (not as_drugbox or public.is_platform_admin()) with check (not as_drugbox or public.is_platform_admin());
drop policy if exists "posts: a Drugbox post is removed by Drugbox admins only" on public.posts;
create policy "posts: a Drugbox post is removed by Drugbox admins only" on public.posts as restrictive for delete to authenticated
  using (not as_drugbox or public.is_platform_admin());

-- nobody posts into an official channel from the browser (members, group admins, Drugbox admins alike): only the publisher does
create or replace function private.can_post_in_group(p_group bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.groups g where g.id = p_group and g.archived_at is null and not g.official
                   and (g.post_policy = 'members' or public.is_group_member(g.id, array['admin', 'moderator'])))
$$;
revoke all on function private.can_post_in_group(bigint) from public, anon, authenticated, service_role;
grant execute on function private.can_post_in_group(bigint) to authenticated, service_role;

-- ── 3. thera dictionary (before the posts trigger that reads it) ────────────────────────────────────────
create table if not exists private.thera_terms (
  tag   text not null,
  term  text not null,            -- lower case; Latin terms match as whole words, Arabic ones as written
  primary key (tag, term)
);
revoke all on table private.thera_terms from public, anon, authenticated, service_role;
grant select, insert, update, delete on table private.thera_terms to service_role;
delete from private.thera_terms where (tag, term) in (('fertility', 'hmg'), ('oncology', 'كيماوي'));   -- matched HMG-CoA (statins) and كيماويات (chemicals)
insert into private.thera_terms (tag, term) values
  ('biologics', 'biologic'), ('biologics', 'biologics'), ('biologics', 'biological'), ('biologics', 'biosimilar'), ('biologics', 'biosimilars'),
  ('biologics', 'monoclonal'), ('biologics', 'mab'), ('biologics', 'بيولوجي'), ('biologics', 'بيولوجية'), ('biologics', 'بايولوجي'), ('biologics', 'بيوسيميلر'),
  ('veterinary', 'veterinary'), ('veterinary', 'vet'), ('veterinary', 'poultry'), ('veterinary', 'livestock'), ('veterinary', 'بيطري'), ('veterinary', 'بيطرية'),
  ('veterinary', 'دواجن'), ('veterinary', 'ماشية'),
  ('agriculture', 'agriculture'), ('agriculture', 'agricultural'), ('agriculture', 'agro'), ('agriculture', 'pesticide'), ('agriculture', 'pesticides'),
  ('agriculture', 'fertilizer'), ('agriculture', 'fertilizers'), ('agriculture', 'زراعي'), ('agriculture', 'زراعية'), ('agriculture', 'مبيد'), ('agriculture', 'مبيدات'),
  ('agriculture', 'أسمدة'), ('agriculture', 'سماد'),
  ('glp1', 'glp-1'), ('glp1', 'glp1'), ('glp1', 'semaglutide'), ('glp1', 'liraglutide'), ('glp1', 'tirzepatide'), ('glp1', 'dulaglutide'),
  ('glp1', 'سيماجلوتايد'), ('glp1', 'سيماجلوتيد'), ('glp1', 'ليراجلوتايد'),
  ('oncology', 'oncology'), ('oncology', 'oncologic'), ('oncology', 'cancer'), ('oncology', 'chemotherapy'), ('oncology', 'cytotoxic'), ('oncology', 'أورام'),
  ('oncology', 'اورام'), ('oncology', 'الأورام'), ('oncology', 'سرطان'), ('oncology', 'علاج كيماوي'),
  ('growth_hormone', 'growth hormone'), ('growth_hormone', 'somatropin'), ('growth_hormone', 'هرمون النمو'), ('growth_hormone', 'هرمون نمو'), ('growth_hormone', 'سوماتروبين'),
  ('fertility', 'fertility'), ('fertility', 'ivf'), ('fertility', 'gonadotropin'), ('fertility', 'gonadotrophin'), ('fertility', 'menotropin'), ('fertility', 'fsh'),
  ('fertility', 'خصوبة'), ('fertility', 'الخصوبة'), ('fertility', 'حقن مجهري'), ('fertility', 'تأخر الإنجاب'),
  ('insulin', 'insulin'), ('insulin', 'insulins'), ('insulin', 'انسولين'), ('insulin', 'إنسولين'), ('insulin', 'الانسولين'), ('insulin', 'الإنسولين')
on conflict do nothing;

-- the areas a text is about (whole words for Latin terms, as written for Arabic ones)
create or replace function private.thera_of(p_text text) returns text[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct t.tag order by t.tag), '{}')
    from private.thera_terms t
   where p_text is not null and length(p_text) > 0
     and case when t.term ~ '[a-z]'
              then lower(p_text) ~ ('(^|[^a-z0-9])' || regexp_replace(t.term, '([.\-+])', '\\\1', 'g') || '([^a-z0-9]|$)')
              else position(t.term in p_text) > 0 end
$$;
revoke all on function private.thera_of(text) from public, anon, authenticated, service_role;
grant execute on function private.thera_of(text) to authenticated, service_role;

-- posts: the server sets as_drugbox (never the browser) and the areas (the text's own, plus a channel post's chosen tags)
create or replace function public.posts_growth_columns() returns trigger
language plpgsql set search_path = public as $$
declare picked text[] := '{}';
begin
  if public.is_server_call() then
    if new.group_id is not null and exists (select 1 from public.groups g where g.id = new.group_id and g.official) then new.as_drugbox := true; end if;   -- a restore too
    if tg_op = 'UPDATE' and new.body is not distinct from old.body and new.thera is not distinct from old.thera then return new; end if;
    picked := coalesce(new.thera, '{}');                                          -- the publisher passes the tags it was given
  else
    if tg_op = 'INSERT' then new.as_drugbox := false; else new.as_drugbox := old.as_drugbox; end if;
    if tg_op = 'UPDATE' and old.as_drugbox and new.body is distinct from old.body then
      raise exception 'A Drugbox channel post is changed from Admin → Channels only' using errcode = '42501'; end if;
    if tg_op = 'UPDATE' and new.body is not distinct from old.body then new.thera := old.thera; return new; end if;   -- the tags follow the text only
  end if;
  new.thera := (select coalesce(array_agg(distinct x order by x), '{}') from unnest(picked || private.thera_of(new.body)) x);
  return new;
end $$;
revoke all on function public.posts_growth_columns() from public, anon, authenticated, service_role;
grant execute on function public.posts_growth_columns() to service_role;
drop trigger if exists trg_posts_growth_columns on public.posts;
create trigger trg_posts_growth_columns before insert or update on public.posts for each row execute function public.posts_growth_columns();

-- marketplace products: the areas from the name and description
alter table public.products add column if not exists thera text[] not null default '{}';
create index if not exists idx_products_thera on public.products using gin (thera) where active;
create or replace function public.products_thera() returns trigger
language plpgsql set search_path = public as $$
begin
  if tg_op = 'UPDATE' and (new.name, new.description) is not distinct from (old.name, old.description) then new.thera := old.thera; return new; end if;
  new.thera := private.thera_of(coalesce(new.name, '') || ' ' || coalesce(new.description, ''));
  return new;
end $$;
revoke all on function public.products_thera() from public, anon, authenticated, service_role;
grant execute on function public.products_thera() to service_role;
drop trigger if exists trg_products_thera on public.products;
create trigger trg_products_thera before insert or update on public.products for each row execute function public.products_thera();
-- the rows already there (a no-op for empty tables; small at launch)
update public.products set thera = private.thera_of(coalesce(name, '') || ' ' || coalesce(description, '')) where thera = '{}' and private.thera_of(coalesce(name, '') || ' ' || coalesce(description, '')) <> '{}';
update public.posts set thera = private.thera_of(body) where thera = '{}' and private.thera_of(body) <> '{}';

-- a new channel post tells the channel's members as Drugbox (no member's name); other groups as before (0061)
create or replace function public.notify_group_post() returns trigger
language plpgsql security definer set search_path = public as $$
declare gname text; frm uuid := case when new.as_drugbox then null else new.user_id end;
        extra jsonb := case when new.as_drugbox then jsonb_build_object('drugbox', true) else '{}'::jsonb end;
begin
  if new.group_id is null then return null; end if;
  select name into gname from public.groups where id = new.group_id;
  insert into public.notifications (user_id, type, from_user, group_id, post_id, message, data)
  select m.user_id, 'group_post', frm, new.group_id, new.id, 'posted in "' || left(coalesce(gname, ''), 120) || '"', jsonb_build_object('n', 1) || extra
    from public.group_members m
   where m.group_id = new.group_id and m.user_id <> new.user_id and not m.muted
  on conflict (user_id, group_id) where type = 'group_post' and read = false
  do update set from_user = excluded.from_user, post_id = excluded.post_id, created_at = now(),
                data = jsonb_build_object('n', coalesce((public.notifications.data ->> 'n')::int, 1) + 1) || extra,
                message = (coalesce((public.notifications.data ->> 'n')::int, 1) + 1)::text || ' new posts in "' || left(coalesce(gname, ''), 120) || '"';
  return null;
end $$;
revoke all on function public.notify_group_post() from public, anon, authenticated, service_role;
grant execute on function public.notify_group_post() to service_role;

create or replace function public.notifications_drugbox_owner() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.post_id is not null and exists (select 1 from public.posts p where p.id = new.post_id and p.as_drugbox and p.user_id = new.user_id) then
    return null;                                    -- likes, comments, removals of a Drugbox post are not the publisher's personal news
  end if;
  return new;
end $$;
revoke all on function public.notifications_drugbox_owner() from public, anon, authenticated, service_role;
grant execute on function public.notifications_drugbox_owner() to service_role;
drop trigger if exists trg_notifications_drugbox_owner on public.notifications;
create trigger trg_notifications_drugbox_owner before insert on public.notifications for each row when (new.post_id is not null) execute function public.notifications_drugbox_owner();

-- the four channels (Drugbox's own pages, no fake members: they start with no member and no post)
insert into public.groups (name, name_ar, description, description_ar, emoji, type, topic, official, channel_key, post_policy, sector, listed)
select v.name, v.name_ar, v.d, v.d_ar, v.emoji, 'public', 'DISCUSS', true, v.k, 'admins', 'pharma', true
  from (values
    ('news', 'Drugbox News', 'Drugbox أخبار', 'Official Drugbox channel: industry news, Drugbox updates and the weekly practical guide.', 'قناة Drugbox الرسمية: أخبار الصناعة وتحديثات Drugbox والدليل العملي الأسبوعي.', '📰'),
    ('jobs', 'Drugbox Jobs', 'Drugbox وظائف', 'Official Drugbox channel: the week''s jobs and hiring news across the industry.', 'قناة Drugbox الرسمية: وظائف الأسبوع وأخبار التوظيف في الصناعة.', '💼'),
    ('regulatory', 'Drugbox Regulatory', 'Drugbox تسجيل ورقابة', 'Official Drugbox channel: the weekly regulatory bulletin (EDA, NFSA) and how to read a registration-file ad.', 'قناة Drugbox الرسمية: النشرة التنظيمية الأسبوعية (هيئة الدواء، هيئة سلامة الغذاء) وإزاي تقرا إعلان ملف تسجيل.', '📋'),
    ('market', 'Drugbox Market', 'Drugbox السوق', 'Official Drugbox channel: «Wanted today» every evening, the week''s shortages and the agency market — business to business only.', 'قناة Drugbox الرسمية: «مطلوب النهارده» كل مساء ونواقص الأسبوع وسوق الوكالات — تجارة بين الشركات فقط.', '📈')
  ) as v(k, name, name_ar, d, d_ar, emoji)
 where not exists (select 1 from public.groups g where g.channel_key = v.k);

-- ── 2. the scheduler ────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.channel_templates (
  key          text primary key,
  channel_key  text not null check (channel_key in ('news', 'jobs', 'regulatory', 'market')),
  cadence      text not null check (cadence in ('daily', 'weekly')),
  weekday      int check (weekday between 0 and 6),            -- 0 = Sunday (weekly only)
  at_time      time not null,                                  -- Africa/Cairo
  title_en     text not null, title_ar text not null,
  body_en      text not null, body_ar  text not null,
  thera        text[] not null default '{}' check (public.thera_ok(thera)),
  sort         int not null default 0
);
alter table public.channel_templates enable row level security;
drop policy if exists "channel templates: Drugbox admins read" on public.channel_templates;
create policy "channel templates: Drugbox admins read" on public.channel_templates for select to authenticated using (public.is_platform_admin());
revoke all on table public.channel_templates from public, anon, authenticated, service_role;
grant select on table public.channel_templates to anon, authenticated;      -- anon: no policy → an empty answer (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.channel_templates to service_role;
insert into public.channel_templates (key, channel_key, cadence, weekday, at_time, title_en, title_ar, body_en, body_ar, sort) values
  ('wanted_today', 'market', 'daily', null, '21:00', 'Wanted today', 'مطلوب النهارده',
   E'🔎 Wanted today — business to business\n\n1. <product / API> — <quantity> — <city>\n2. …\n\nHave it? Answer from the Marketplace (Create Listing → Supply) or message the buyer. Companies and their agents only — no sales to pharmacies or the public.',
   E'🔎 مطلوب النهارده — تجارة بين الشركات\n\n1. <المنتج / المادة الخام> — <الكمية> — <المدينة>\n2. …\n\nعندك؟ رد من الماركت (إعلان جديد ← عرض) أو ابعت للمشتري. للشركات ووكلائها فقط — مفيش بيع لصيدليات أو للجمهور.', 1),
  ('shortages_week', 'market', 'weekly', 4, '21:30', 'This week''s shortages', 'نواقص الأسبوع',
   E'📉 This week''s shortages (from requests on Drugbox)\n\n• <product> — <form / strength> — asked by <n> companies\n• …\n\nSuppliers and agents: post your offer in the Marketplace.',
   E'📉 نواقص الأسبوع (من طلبات Drugbox)\n\n• <المنتج> — <الشكل / التركيز> — طلبته <عدد> شركات\n• …\n\nالموردين والوكلاء: انشروا عرضكم في الماركت.', 2),
  ('regulatory_bulletin', 'regulatory', 'weekly', 0, '21:00', 'Weekly regulatory bulletin', 'النشرة التنظيمية الأسبوعية',
   E'📋 Weekly regulatory bulletin\n\n• EDA: <decree / circular — number — what changes — from when>\n• NFSA: <…>\n• Pricing: <…>\n\nSource links in the comments. Not legal advice — check the official text.',
   E'📋 النشرة التنظيمية الأسبوعية\n\n• هيئة الدواء: <قرار / منشور — الرقم — إيه اللي اتغير — من إمتى>\n• هيئة سلامة الغذاء: <…>\n• التسعير: <…>\n\nروابط المصدر في التعليقات. مش استشارة قانونية — راجع النص الرسمي.', 3),
  ('read_file_ad', 'regulatory', 'weekly', 1, '21:00', 'How to read a registration-file ad', 'إزاي تقرا إعلان ملف تسجيل',
   E'🧾 How to read a registration-file ad\n\n1. Registration number and holder — check them on the authority''s site.\n2. Status: registered / under registration / box.\n3. Expiry and renewals.\n4. Price and who pays the transfer fees.\n5. Never pay before the transfer papers are checked.',
   E'🧾 إزاي تقرا إعلان ملف تسجيل\n\n1. رقم التسجيل وصاحب الملف — اتأكد منهم على موقع الهيئة.\n2. الحالة: مسجّل / تحت التسجيل / بوكس.\n3. تاريخ الانتهاء والتجديدات.\n4. السعر ومين بيدفع رسوم نقل الملكية.\n5. ماتدفعش قبل ما أوراق النقل تتراجع.', 4),
  ('agency_market', 'market', 'weekly', 2, '21:00', 'The agency market this week', 'سوق الوكالات الأسبوع ده',
   E'🤝 The agency market this week\n\n• Principals looking for agents / distributors: <…>\n• Agents looking for lines: <…>\n\nPost yours in the Marketplace (License / Service).',
   E'🤝 سوق الوكالات الأسبوع ده\n\n• شركات بتدور على وكيل / موزّع: <…>\n• وكلاء بيدوروا على خطوط: <…>\n\nانشر طلبك في الماركت (ترخيص / خدمة).', 5),
  ('practical_guide', 'news', 'weekly', 3, '21:00', 'Practical guide of the week', 'الدليل العملي للأسبوع',
   E'🛠 Practical guide of the week: <topic>\n\n1. …\n2. …\n3. …\n\nAsk the expert: Training → Ask an expert.',
   E'🛠 الدليل العملي للأسبوع: <الموضوع>\n\n1. …\n2. …\n3. …\n\nاسأل خبير: التدريب ← اسأل خبير.', 6),
  ('jobs_week', 'jobs', 'weekly', 0, '20:00', 'Jobs of the week', 'وظائف الأسبوع',
   E'💼 Jobs of the week\n\n• <title> — <company> — <city>\n• …\n\nApply from Jobs. Hiring? Post a job for free.',
   E'💼 وظائف الأسبوع\n\n• <المسمى> — <الشركة> — <المدينة>\n• …\n\nقدّم من الوظائف. بتعيّن؟ انشر وظيفة مجاناً.', 7)
on conflict (key) do nothing;

create table if not exists public.channel_schedule (
  id            bigint generated always as identity primary key,
  group_id      bigint not null references public.groups(id) on delete cascade,
  template_key  text references public.channel_templates(key) on delete set null,
  body          text not null,
  thera         text[] not null default '{}',
  status        text not null default 'draft',
  publish_at    timestamptz,                                    -- the moment (stored in UTC; entered as Africa/Cairo)
  post_id       bigint references public.posts(id) on delete set null,
  error         text,
  created_by    uuid references public.profiles(id) on delete set null,
  updated_by    uuid references public.profiles(id) on delete set null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  published_at  timestamptz,
  constraint channel_schedule_status check (status in ('draft', 'scheduled', 'published', 'cancelled', 'failed')),
  constraint channel_schedule_body check (length(body) between 1 and 5000),
  constraint channel_schedule_thera check (public.thera_ok(thera)),
  constraint channel_schedule_when check (status <> 'scheduled' or publish_at is not null)
);
create index if not exists idx_channel_schedule_due on public.channel_schedule (publish_at) where status = 'scheduled';
create index if not exists idx_channel_schedule_list on public.channel_schedule (created_at desc);
create index if not exists idx_channel_schedule_group on public.channel_schedule (group_id);
create index if not exists idx_channel_schedule_post on public.channel_schedule (post_id) where post_id is not null;
create index if not exists idx_channel_schedule_created_by on public.channel_schedule (created_by) where created_by is not null;
create index if not exists idx_channel_schedule_updated_by on public.channel_schedule (updated_by) where updated_by is not null;
create index if not exists idx_channel_schedule_template on public.channel_schedule (template_key) where template_key is not null;
alter table public.channel_schedule enable row level security;
drop policy if exists "channel schedule: Drugbox admins read" on public.channel_schedule;
create policy "channel schedule: Drugbox admins read" on public.channel_schedule for select to authenticated using (public.is_platform_admin());
revoke all on table public.channel_schedule from public, anon, authenticated, service_role;
grant select on table public.channel_schedule to anon, authenticated;           -- writes only through the functions below; anon reads nothing (F-26)
grant select, insert, update, delete, truncate, references, trigger on table public.channel_schedule to service_role;
revoke all on sequence public.channel_schedule_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.channel_schedule_id_seq to service_role;

-- the next slot of a template, as Cairo wall time ('YYYY-MM-DD HH24:MI'), never in the past
create or replace function public.channel_template_next(p_key text) returns text
language plpgsql stable security definer set search_path = public as $$
declare t public.channel_templates; now_c timestamp := (now() at time zone 'Africa/Cairo'); d date; c timestamp;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin plans channel posts' using errcode = '42501'; end if;
  select * into t from public.channel_templates where key = p_key; if not found then raise exception 'Unknown template' using errcode = '22023'; end if;
  d := now_c::date;
  for i in 0..14 loop
    c := (d + i) + t.at_time;
    if c > now_c + interval '5 minutes' and (t.cadence = 'daily' or extract(dow from (d + i)) = t.weekday) then return to_char(c, 'YYYY-MM-DD HH24:MI'); end if;
  end loop;
  return null;
end $$;
revoke all on function public.channel_template_next(text) from public, anon, authenticated, service_role;
grant execute on function public.channel_template_next(text) to authenticated, service_role;

-- save a draft or a scheduled post (new: p_id null). p_local is the Cairo date and time typed in Admin ('YYYY-MM-DD HH24:MI').
create or replace function public.channel_schedule_save(p_id bigint, p_channel text, p_body text, p_local text, p_status text,
                                                         p_thera text[] default '{}', p_template text default null)
returns bigint language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); gid bigint; r public.channel_schedule; at timestamptz; b text := trim(coalesce(p_body, ''));
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin plans channel posts' using errcode = '42501'; end if;
  if p_status not in ('draft', 'scheduled') then raise exception 'Save as a draft or schedule it' using errcode = '22023'; end if;
  if length(b) = 0 then raise exception 'Write the post first' using errcode = '22023'; end if;
  if length(b) > 5000 then raise exception 'A post is at most 5,000 characters' using errcode = '22023'; end if;
  if not public.thera_ok(coalesce(p_thera, '{}')) then raise exception 'Unknown therapeutic area' using errcode = '22023'; end if;
  select id into gid from public.groups where channel_key = p_channel and official;
  if gid is null then raise exception 'Pick one of the Drugbox channels' using errcode = '22023'; end if;
  if nullif(trim(coalesce(p_local, '')), '') is not null then
    begin at := (to_timestamp(trim(p_local), 'YYYY-MM-DD HH24:MI')::timestamp at time zone 'Africa/Cairo');
    exception when others then raise exception 'Give the date and time as YYYY-MM-DD HH:MM (Cairo time)' using errcode = '22023'; end;
  end if;
  if p_status = 'scheduled' and at is null then raise exception 'Pick the date and time to publish (Cairo time)' using errcode = '22023'; end if;
  if p_status = 'scheduled' and at < now() - interval '1 minute' then raise exception 'That time has passed — pick a later one or publish now' using errcode = '22023'; end if;
  if p_template is not null and not exists (select 1 from public.channel_templates where key = p_template) then raise exception 'Unknown template' using errcode = '22023'; end if;
  if p_id is null then
    insert into public.channel_schedule (group_id, template_key, body, thera, status, publish_at, created_by, updated_by)
    values (gid, p_template, b, coalesce(p_thera, '{}'), p_status, at, me, me) returning id into p_id;
    return p_id;
  end if;
  select * into r from public.channel_schedule where id = p_id for update;
  if not found then raise exception 'This planned post is gone' using errcode = 'P0002'; end if;
  if r.status not in ('draft', 'scheduled') then raise exception 'Only a draft or a scheduled post can be changed (this one is %)', r.status using errcode = '55000'; end if;
  update public.channel_schedule set group_id = gid, template_key = coalesce(p_template, template_key), body = b, thera = coalesce(p_thera, '{}'),
         status = p_status, publish_at = at, updated_by = me, updated_at = now(), error = null where id = p_id;
  return p_id;
end $$;
revoke all on function public.channel_schedule_save(bigint, text, text, text, text, text[], text) from public, anon, authenticated, service_role;
grant execute on function public.channel_schedule_save(bigint, text, text, text, text, text[], text) to authenticated, service_role;

create or replace function public.channel_schedule_cancel(p_id bigint) returns void
language plpgsql security definer set search_path = public as $$
declare st text;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin plans channel posts' using errcode = '42501'; end if;
  select status into st from public.channel_schedule where id = p_id for update;
  if st is null then raise exception 'This planned post is gone' using errcode = 'P0002'; end if;
  if st not in ('draft', 'scheduled', 'failed') then raise exception 'Only a draft or a scheduled post can be cancelled (this one is %)', st using errcode = '55000'; end if;
  update public.channel_schedule set status = 'cancelled', updated_by = auth.uid(), updated_at = now() where id = p_id;
end $$;
revoke all on function public.channel_schedule_cancel(bigint) from public, anon, authenticated, service_role;
grant execute on function public.channel_schedule_cancel(bigint) to authenticated, service_role;

-- publishing one planned post (the runner, or "Publish now"): the post is written by the server as Drugbox
create or replace function private.channel_publish(p_id bigint) returns bigint
language plpgsql security definer set search_path = public as $$
declare r public.channel_schedule; pid bigint; author uuid; g public.groups;
begin
  select * into r from public.channel_schedule where id = p_id for update skip locked;
  if not found or r.status not in ('draft', 'scheduled') then return null; end if;
  select * into g from public.groups where id = r.group_id;
  -- the record of who did it: the admin who last changed it, else who wrote it, else any Drugbox admin still in the team
  author := coalesce((select p.id from public.profiles p where p.id = r.updated_by and p.role = 'admin'),
                     (select p.id from public.profiles p where p.id = r.created_by and p.role = 'admin'),
                     (select p.id from public.profiles p where p.role = 'admin' order by p.created_at limit 1));
  if author is null or g.id is null or not g.official or g.archived_at is not null then
    update public.channel_schedule set status = 'failed', error = case when author is null then 'no Drugbox admin left to publish it' else 'the channel is closed' end, updated_at = now() where id = p_id;
    return null;
  end if;
  insert into public.posts (user_id, body, category, group_id, as_drugbox, thera)
  values (author, r.body, case g.channel_key when 'regulatory' then 'regulatory' when 'market' then 'market' when 'jobs' then 'job' else 'general' end,
          r.group_id, true, r.thera)
  returning id into pid;
  update public.channel_schedule set status = 'published', post_id = pid, published_at = now(), updated_at = now(), error = null where id = p_id;
  return pid;
end $$;
revoke all on function private.channel_publish(bigint) from public, anon, authenticated, service_role;
grant execute on function private.channel_publish(bigint) to service_role;

create or replace function public.channel_publish_now(p_id bigint) returns bigint
language plpgsql security definer set search_path = public as $$
declare pid bigint; st text;
begin
  if not public.is_platform_admin() then raise exception 'Only a Drugbox admin publishes to the channels' using errcode = '42501'; end if;
  select status into st from public.channel_schedule where id = p_id;
  if st is null then raise exception 'This planned post is gone' using errcode = 'P0002'; end if;
  if st not in ('draft', 'scheduled') then raise exception 'This post is already %', st using errcode = '55000'; end if;
  update public.channel_schedule set updated_by = auth.uid() where id = p_id;
  pid := private.channel_publish(p_id);
  if pid is null then raise exception 'It could not be published — open it again' using errcode = '55000'; end if;
  return pid;
end $$;
revoke all on function public.channel_publish_now(bigint) from public, anon, authenticated, service_role;
grant execute on function public.channel_publish_now(bigint) to authenticated, service_role;

-- Admin → Channels: the plan, newest first, with the Cairo time to show
drop function if exists public.channel_schedule_list(int);   -- its row shape changed while unreleased: replaced, not altered
create or replace function public.channel_schedule_list(p_limit int default 100)
returns table (id bigint, channel_key text, channel_name text, template_key text, body text, thera text[], status text, publish_local text,
               publish_at timestamptz, post_id bigint, error text, created_by_name text, updated_at timestamptz, published_at timestamptz, published_local text)
language sql stable security definer set search_path = public as $$
  select s.id, g.channel_key, g.name, s.template_key, s.body, s.thera, s.status,
         to_char(s.publish_at at time zone 'Africa/Cairo', 'YYYY-MM-DD HH24:MI'), s.publish_at, s.post_id, s.error,
         (select p.name from public.profiles p where p.id = s.created_by), s.updated_at, s.published_at,
         to_char(s.published_at at time zone 'Africa/Cairo', 'YYYY-MM-DD HH24:MI')
    from public.channel_schedule s join public.groups g on g.id = s.group_id
   where public.is_platform_admin()
   order by (s.status in ('draft', 'scheduled')) desc, coalesce(s.publish_at, s.created_at) asc, s.id desc
   limit least(greatest(coalesce(p_limit, 100), 1), 300)
$$;
revoke all on function public.channel_schedule_list(int) from public, anon, authenticated, service_role;
grant execute on function public.channel_schedule_list(int) to authenticated, service_role;

-- ── 3b. the filters (W-21) ──────────────────────────────────────────────────────────────────────────────
-- Home: the newest posts about one area (main feed, readable by the member); keyset paging by (created_at, id)
create or replace function public.feed_thera(p_tag text, p_before timestamptz default null, p_before_id bigint default null, p_limit int default 20)
returns setof public.posts language sql stable security invoker set search_path = public as $$
  select p.* from public.posts p
   where p.group_id is null and p.thera @> array[p_tag]
     and (p_before is null or (p.created_at, p.id) < (p_before, coalesce(p_before_id, 9223372036854775807)))
   order by p.created_at desc, p.id desc
   limit least(greatest(coalesce(p_limit, 20), 1), 50)
$$;
revoke all on function public.feed_thera(text, timestamptz, bigint, int) from public, anon, authenticated, service_role;
grant execute on function public.feed_thera(text, timestamptz, bigint, int) to authenticated, service_role;

-- Marketplace: market_search (0054/0065) with one more condition — the same rows and paging, only listings about the area
create or replace function public.market_search_thera(p_tag text, p_q text default null, p_type text default null, p_category text default null, p_limit int default 40, p_offset int default 0)
returns jsonb language plpgsql stable security invoker set search_path = public set jit = off as $$
declare v_q text := nullif(left(trim(coalesce(p_q, '')), 100), ''); v_lim int := least(greatest(coalesce(p_limit, 40), 1), 100); v_off int := greatest(coalesce(p_offset, 0), 0);
        v_total int; v_rows jsonb;
begin
  if auth.uid() is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if not public.thera_ok(array[p_tag]) or p_tag is null then raise exception 'Unknown therapeutic area' using errcode = '22023'; end if;
  with hits as (
    select p.id, p.created_at, case when p.featured_until > now() then 2 when p.boosted_until > now() then 1 else 0 end as rank
      from public.products p
     where p.active and (p.expires_at is null or p.expires_at > now()) and p.thera @> array[p_tag]
       and (p_type is null or p.type = p_type) and (p_category is null or p.category = p_category)
       and (v_q is null or p.name ilike '%' || v_q || '%' or p.description ilike '%' || v_q || '%')),
  pg as (select h.id, h.rank from hits h order by h.rank desc, h.created_at desc, h.id desc limit v_lim offset v_off)
  select (select count(*)::int from hits), coalesce((select jsonb_agg(to_jsonb(x) order by x.rank desc, x.created_at desc, x.id desc) from (
      select h.id, h.user_id, h.name, h.category, h.type, h.price, h.unit, h.moq, h.description, h.emoji, h.docs, h.certs_verified, h.lead_time, h.currency,
             h.company_id, h.created_at, h.expires_at, h.boosted_until, h.featured_until, h.view_count, h.inquiry_count, (h.coa_path is not null) as has_coa,
             pg.rank, h.thera,
             (select json_build_object('slug', c.slug, 'name', c.name, 'verified', c.status = 'verified') from public.companies c where c.id = h.company_id) as co
        from pg join public.products h on h.id = pg.id) x), '[]'::jsonb)
    into v_total, v_rows;
  return jsonb_build_object('total', v_total, 'rows', v_rows);
end $$;
revoke all on function public.market_search_thera(text, text, text, text, int, int) from public, anon, authenticated, service_role;
grant execute on function public.market_search_thera(text, text, text, text, int, int) to authenticated, service_role;

-- ── 4. the runner ───────────────────────────────────────────────────────────────────────────────────────
-- growth_tick(): what is due now. Later migrations of this area add their own steps (they replace this function).
create or replace function public.growth_tick() returns jsonb
language plpgsql security definer set search_path = public as $$
declare n int := 0; r record;
begin
  for r in select id from public.channel_schedule where status = 'scheduled' and publish_at <= now() order by publish_at, id limit 50 loop
    if private.channel_publish(r.id) is not null then n := n + 1; end if;
  end loop;
  return jsonb_build_object('published', n);
end $$;
revoke all on function public.growth_tick() from public, anon, authenticated, service_role;
grant execute on function public.growth_tick() to service_role;

do $$ begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    execute $q$select cron.schedule('drugbox-growth-tick', '* * * * *', 'select public.growth_tick()')$q$;
  end if;
exception when others then raise warning 'pg_cron job not scheduled: %', sqlerrm;
end $$;

notify pgrst, 'reload schema';
