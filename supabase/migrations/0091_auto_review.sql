-- ═════════════════════════════════════════════════════════════════════
-- 0091 — sensitive posts go to Drugbox review by themselves (area w-trust: W-17)
--   Drugbox trade is business-to-business before the pharmacy. A post, a marketplace offer or a deal-room listing whose words
--   look like one of these is HELD — nothing is deleted, nobody else sees it until a Drugbox moderator decides, and the author
--   is told why at once:
--     retail     — a sale to consumers / patients / pharmacies, a "case" for a patient, loose or opened packs
--     controlled — controlled substances (narcotics, psychotropics, "the schedule")
--     import     — importing for others / renting an import licence or registration
--     sham       — sham contracts, fake invoices / certificates, forged papers
--     invite     — invite links to outside chat groups (WhatsApp, Telegram …)
--   1. private.review_rules: the words (EN + AR, written in the trade's own words) as case-insensitive regular expressions over
--      the normalised text (private.review_norm: lower case, Arabic letter variants folded, harakat / tatweel / invisible
--      characters removed). Drugbox can add or switch off a rule with a plain row — no new code.
--   2. review_hold on posts, products and group_listings: set by the database only (insert, and an edit of the words); a held
--      post / listing is read by its author and the Drugbox team only (restrictive policies); a held offer is paused and its
--      owner cannot resume it; search_all leaves held posts out.
--   3. content_holds: one row per held item (what, who, which rules, an excerpt) — the Admin → Review queue "Held for review".
--      held_review_queue() / held_review_decide(id, publish, note): Publish lets it show (an offer becomes active again),
--      Remove deletes it — both tell the author; decided once (DX409), logged in admin_actions ('held').
--   4. The author's notice: notifications type 'auto_review' (data: kind, topics, excerpt) and 'auto_review_decided'
--      (data: kind, outcome, excerpt, note).
-- Every new table / function has its own GRANT / REVOKE (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. the rules ────
create table if not exists private.review_rules (
  id       bigint generated always as identity primary key,
  topic    text not null check (topic in ('retail', 'controlled', 'import', 'sham', 'invite')),
  pattern  text not null unique,
  active   boolean not null default true
);
revoke all on table private.review_rules from public, anon, authenticated;
grant select, insert, update, delete on table private.review_rules to service_role;

-- lower case; أ إ آ ٱ → ا, ة → ه, ى → ي, ؤ → و, ئ → ي; harakat, tatweel and invisible characters removed; spaces collapsed
create or replace function private.review_norm(p text) returns text language sql immutable set search_path = public as $$
  select regexp_replace(
           translate(
             regexp_replace(lower(coalesce(p, '')), '[ً-ٰٟـ​-‏‪-‮⁦-⁩﻿­]', '', 'g'),
             'أإآٱةىؤئ', 'ااااهيوي'),
           '\s+', ' ', 'g')
$$;
revoke all on function private.review_norm(text) from public, anon, authenticated, service_role;
grant execute on function private.review_norm(text) to authenticated, service_role;

insert into private.review_rules (topic, pattern) values
  -- retail: consumers, patients, pharmacies as buyers, loose packs (normalised Arabic: ة→ه, ى→ي, أ→ا)
  ('retail', '\m(for|to) (a|my|the|our|this) patient\M'),
  ('retail', '\mpatient (needs|is looking|urgently)'),
  ('retail', '\m(retail|consumer) (sale|sales|price|customers?|buyers?)\M'),
  ('retail', '\m(sell|selling|sale|supply|supplying|deliver|delivery) (to|for) (the )?(public|consumers?|pharmac(y|ies))\M'),
  ('retail', '\mhome delivery\M'),
  ('retail', '\m(single|one|loose|open(ed)?) (box|pack|strip)s?\M'),
  ('retail', '\mper (box|strip) (to|for) (the )?public\M'),
  -- controlled substances
  ('controlled', '\m(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)\M'),
  ('controlled', '\m(controlled (substances?|drugs?|medicines?)|psychotropics?|narcotics?|schedule (i|ii|1|2) (drugs?|medicines?|products?))\M'),
  -- import for others
  ('import', '\mimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e)'),
  ('import', '\m(rent|hire|lend)(ing)? (an |my |our )?import (licen[cs]e|card|registration)'),
  -- sham papers
  ('sham', '\m(sham|fake|fictitious) (contracts?|invoices?|tenders?|coas?|certificates?|papers?)\M'),
  ('sham', '\m(backdated|forged) (contracts?|invoices?|papers?|documents?|certificates?)\M'),
  -- Arabic (normalised): whole words — no Arabic letter before or after; drug names also with و ف ب ل ك ال
  ('retail', '(^|[^ء-ي])(و|ف)?(لمريض|للمريض|لمريضه|للمريضه|للعيان|لعيان|حاله انسانيه|حالات انسانيه|محتاج دوا|محتاجه دوا)([^ء-ي]|$)'),
  ('retail', '(^|[^ء-ي])(و|ف)?(روشته|بالروشته|الروشته|قطاعي|بالقطاعي|للجمهور|توصيل للمنازل|توصيل للبيت|دليفري)([^ء-ي]|$)'),
  ('retail', '(^|[^ء-ي])(و|ف)?(للصيدليات|لصيدليه|لصيدليتي|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه)([^ء-ي]|$)'),
  ('retail', '(^|[^ء-ي])(و|ف)?(علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|فرط|بالفرط|بالشريط)([^ء-ي]|$)'),
  ('controlled', '(^|[^ء-ي])(و|ف)?(ب|ل|ك)?(ال|ل)?(ترامادول|ترامال|تامول|ليريكا|بريجابالين|كودايين|كوديين|مورفين|فنتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين)([^ء-ي]|$)'),
  ('controlled', '(^|[^ء-ي])(و|ف)?(ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|من الجدول|مخدر|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه)([^ء-ي]|$)'),
  ('import', '(^|[^ء-ي])(و|ف)?(استيراد لحساب|استيراد للغير|استيراد باسم|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا)([^ء-ي]|$)'),
  ('import', '(^|[^ء-ي])(و|ف)?(تاجير سجل|تاجير بطاقه استيراد|بطاقه استيراديه للايجار|سجل مستوردين للايجار|ايجار سجل)([^ء-ي]|$)'),
  ('sham', '(^|[^ء-ي])(و|ف)?(عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه|مزوره|مزور|تزوير)([^ء-ي]|$)'),
  -- invite links to outside groups
  ('invite', 'chat\.whatsapp\.com|wa\.me/|whatsapp\.com/(channel|invite)|t\.me/|telegram\.(me|dog)/|telegram\.org/joinchat|discord\.(gg|com/invite)|invite\.viber\.com|vb\.me/')
on conflict (pattern) do nothing;

-- the topics a text matches (an empty array when none)
create or replace function private.review_topics(p text) returns text[]
language sql stable security definer set search_path = public as $$
  select coalesce(array_agg(distinct r.topic order by r.topic), '{}'::text[])
    from private.review_rules r where r.active and private.review_norm(p) ~* r.pattern
$$;
revoke all on function private.review_topics(text) from public, anon, authenticated, service_role;
grant execute on function private.review_topics(text) to authenticated, service_role;

-- ── 3. the queue (needed by the triggers) ────
create table if not exists public.content_holds (
  id          bigint generated always as identity primary key,
  kind        text not null check (kind in ('post', 'offer', 'listing')),
  item_id     bigint not null,
  user_id     uuid references public.profiles(id) on delete cascade,
  topics      text[] not null default '{}',
  excerpt     text not null default '',
  status      text not null default 'held' check (status in ('held', 'published', 'removed')),
  decided_by  uuid references public.profiles(id) on delete set null,
  decided_at  timestamptz,
  note        text,
  created_at  timestamptz not null default now(),
  constraint content_holds_len check (char_length(excerpt) <= 400 and char_length(coalesce(note, '')) <= 500 and cardinality(topics) <= 5)
);
create unique index if not exists idx_content_holds_open on public.content_holds (kind, item_id) where status = 'held';
create index if not exists idx_content_holds_queue on public.content_holds (created_at) where status = 'held';
create index if not exists idx_content_holds_user on public.content_holds (user_id);
create index if not exists idx_content_holds_decided_by on public.content_holds (decided_by);
alter table public.content_holds enable row level security;
drop policy if exists "holds: the author and Drugbox read" on public.content_holds;
create policy "holds: the author and Drugbox read" on public.content_holds for select to authenticated
  using (user_id = (select auth.uid()) or (select public.is_moderator()));
revoke all on table public.content_holds from public, anon, authenticated, service_role;
grant select on table public.content_holds to anon, authenticated;            -- written by the database only
grant select, insert, update, delete, truncate, references, trigger on table public.content_holds to service_role;
revoke all on sequence public.content_holds_id_seq from public, anon, authenticated, service_role;
grant usage, select on sequence public.content_holds_id_seq to service_role;

-- ── 2. the holds ────
alter table public.posts add column if not exists review_hold boolean not null default false;
alter table public.products add column if not exists review_hold boolean not null default false;
alter table public.group_listings add column if not exists review_hold boolean not null default false;
grant select (review_hold) on table public.posts to anon, authenticated;
grant select (review_hold) on table public.products to anon, authenticated;
grant select (review_hold) on table public.group_listings to authenticated;
create index if not exists idx_posts_review_hold on public.posts (id) where review_hold;

-- BEFORE: decide the hold (the browser can never set or clear it); an offer that is held is paused
create or replace function private.review_text(p_table text, r jsonb) returns text language sql immutable set search_path = public as $$
  select case p_table when 'posts' then r ->> 'body'
                      when 'products' then concat_ws(' ', r ->> 'name', r ->> 'description', r ->> 'price', r ->> 'moq', r ->> 'broker_for')
                      else concat_ws(' ', r ->> 'title', r ->> 'details', r ->> 'price', r ->> 'broker_for') end
$$;
revoke all on function private.review_text(text, jsonb) from public, anon, authenticated, service_role;
grant execute on function private.review_text(text, jsonb) to authenticated, service_role;

create or replace function public.review_hold_before() returns trigger language plpgsql security definer set search_path = public as $$
declare txt text := private.review_text(tg_table_name, to_jsonb(new)); prod boolean := tg_table_name = 'products';
begin
  if tg_op = 'UPDATE' then
    if current_setting('drugbox.hold_decision', true) = '1' then return new; end if;   -- held_review_decide() sets / clears it
    new.review_hold := old.review_hold;
    if prod and new.review_hold then
      if (to_jsonb(new) ->> 'status') = 'active' and (to_jsonb(old) ->> 'status') <> 'active' then
        raise exception 'This offer is waiting for Drugbox review — it shows again once it is checked' using errcode = '42501', hint = 'DX417';
      end if;
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
    if prod then
      if (to_jsonb(new) ->> 'status') = 'active' then new := jsonb_populate_record(new, jsonb_build_object('status', 'paused')); end if;
    end if;
  end if;
  return new;
end $$;
revoke all on function public.review_hold_before() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_before() to authenticated, service_role;

-- AFTER: the queue row and the author's notice (once per hold)
create or replace function public.review_hold_after() returns trigger language plpgsql security definer set search_path = public as $$
declare k text := case tg_table_name when 'posts' then 'post' when 'products' then 'offer' else 'listing' end; j jsonb := to_jsonb(new); t text[]; ex text;
begin
  if not new.review_hold or (tg_op = 'UPDATE' and old.review_hold) then return null; end if;
  if exists (select 1 from public.content_holds h where h.kind = k and h.item_id = new.id and h.status = 'held') then return null; end if;
  t := private.review_topics(private.review_text(tg_table_name, j));
  ex := left(regexp_replace(case tg_table_name when 'posts' then coalesce(j ->> 'body', '')
                                               when 'products' then concat_ws(' — ', j ->> 'name', j ->> 'description')
                                               else concat_ws(' — ', j ->> 'title', j ->> 'details') end, '\s+', ' ', 'g'), 200);
  insert into public.content_holds (kind, item_id, user_id, topics, excerpt) values (k, new.id, (j ->> 'user_id')::uuid, t, ex);
  insert into public.notifications (user_id, type, from_user, message, data)
  values ((j ->> 'user_id')::uuid, 'auto_review', null, null, jsonb_build_object('kind', k, 'topics', to_jsonb(t), 'excerpt', left(ex, 80) || case when char_length(ex) > 80 then '…' else '' end));
  return null;
end $$;
revoke all on function public.review_hold_after() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_after() to service_role;

do $$ declare t text; begin
  foreach t in array array['posts', 'products', 'group_listings'] loop
    execute format('drop trigger if exists trg_%s_review_hold on public.%I', t, t);
    -- products: after products_market_guard (a_…) so its status rule runs first; before the derive (zz_…) so active follows
    execute format('drop trigger if exists trg_%s_b_review_hold on public.%I', t, t);
    execute format('create trigger trg_%s_b_review_hold before insert or update on public.%I for each row execute function public.review_hold_before()', t, t);
    execute format('drop trigger if exists trg_%s_review_hold_after on public.%I', t, t);
    execute format('create trigger trg_%s_review_hold_after after insert or update on public.%I for each row execute function public.review_hold_after()', t, t);
  end loop;
end $$;
-- a deleted item leaves no open hold behind
create or replace function public.review_hold_gone() returns trigger language plpgsql security definer set search_path = public as $$
begin
  update public.content_holds set status = 'removed', decided_at = coalesce(decided_at, now())
   where kind = case tg_table_name when 'posts' then 'post' when 'products' then 'offer' else 'listing' end and item_id = old.id and status = 'held';
  return null;
end $$;
revoke all on function public.review_hold_gone() from public, anon, authenticated, service_role;
grant execute on function public.review_hold_gone() to service_role;
do $$ declare t text; begin
  foreach t in array array['posts', 'products', 'group_listings'] loop
    execute format('drop trigger if exists trg_%s_review_hold_gone on public.%I', t, t);
    execute format('create trigger trg_%s_review_hold_gone after delete on public.%I for each row when (old.review_hold) execute function public.review_hold_gone()', t, t);
  end loop;
end $$;

-- who reads a held item: its author and the Drugbox team (restrictive: added to every other read rule)
drop policy if exists "posts: held for review" on public.posts;
create policy "posts: held for review" on public.posts as restrictive for select
  using (not review_hold or user_id = (select auth.uid()) or (select public.is_moderator()));
drop policy if exists "products: held for review" on public.products;
create policy "products: held for review" on public.products as restrictive for select
  using (not review_hold or user_id = (select auth.uid()) or (select public.is_moderator()));
drop policy if exists "group listings: held for review" on public.group_listings;
create policy "group listings: held for review" on public.group_listings as restrictive for select
  using (not review_hold or user_id = (select auth.uid()) or (select public.is_moderator()));

-- a held group post tells nobody in the group (0061's notice, unchanged otherwise); it is told on publish
create or replace function public.notify_group_post() returns trigger
language plpgsql security definer set search_path = public as $$
declare gname text;
begin
  if new.group_id is null or new.review_hold then return null; end if;
  if tg_op = 'UPDATE' and not (old.review_hold and not new.review_hold) then return null; end if;
  select name into gname from public.groups where id = new.group_id;
  insert into public.notifications (user_id, type, from_user, group_id, post_id, message, data)
  select m.user_id, 'group_post', new.user_id, new.group_id, new.id, 'posted in "' || left(coalesce(gname, ''), 120) || '"', jsonb_build_object('n', 1)
    from public.group_members m
   where m.group_id = new.group_id and m.user_id <> new.user_id and not m.muted
  on conflict (user_id, group_id) where type = 'group_post' and read = false
  do update set from_user = excluded.from_user, post_id = excluded.post_id, created_at = now(),
                data = jsonb_build_object('n', coalesce((public.notifications.data ->> 'n')::int, 1) + 1),
                message = (coalesce((public.notifications.data ->> 'n')::int, 1) + 1)::text || ' new posts in "' || left(coalesce(gname, ''), 120) || '"';
  return null;
end $$;
revoke all on function public.notify_group_post() from public, anon, authenticated, service_role;
grant execute on function public.notify_group_post() to service_role;
drop trigger if exists trg_notify_group_post on public.posts;
create trigger trg_notify_group_post after insert on public.posts for each row when (new.group_id is not null) execute function public.notify_group_post();
drop trigger if exists trg_notify_group_post_released on public.posts;
create trigger trg_notify_group_post_released after update of review_hold on public.posts for each row
  when (new.group_id is not null and old.review_hold and not new.review_hold) execute function public.notify_group_post();

-- ── 3b. the moderators' side ────
alter table public.admin_actions drop constraint if exists admin_actions_kind;
alter table public.admin_actions add constraint admin_actions_kind check (kind in ('verification', 'claim', 'reference', 'certificate', 'report', 'payment', 'post',
  'suspension', 'role', 'badge', 'held', 'trader_report', 'partner'));

create or replace function public.held_review_queue(p_limit int default 100) returns jsonb
language sql stable security definer set search_path = public as $$
  select case when not public.is_moderator() then null else coalesce((select jsonb_agg(to_jsonb(x) order by x.created_at) from (
    select h.id, h.kind, h.item_id, h.topics, h.excerpt, h.created_at, h.user_id,
           (select p.name from public.profiles p where p.id = h.user_id) as author,
           case h.kind when 'post' then (select o.body from public.posts o where o.id = h.item_id)
                       when 'offer' then (select concat_ws(' — ', r.name, r.description) from public.products r where r.id = h.item_id)
                       else (select concat_ws(' — ', l.title, l.details) from public.group_listings l where l.id = h.item_id) end as body,
           case h.kind when 'post' then (select g.name from public.posts o join public.groups g on g.id = o.group_id where o.id = h.item_id)
                       when 'listing' then (select g.name from public.group_listings l join public.groups g on g.id = l.group_id where l.id = h.item_id) end as group_name
      from public.content_holds h where h.status = 'held' order by h.created_at limit least(greatest(coalesce(p_limit, 100), 1), 300)) x), '[]'::jsonb) end
$$;
revoke all on function public.held_review_queue(int) from public, anon, authenticated, service_role;
grant execute on function public.held_review_queue(int) to authenticated, service_role;

create or replace function public.held_review_decide(p_hold bigint, p_publish boolean, p_note text default null) returns text
language plpgsql security definer set search_path = public as $$
declare h public.content_holds; me uuid := auth.uid(); v_note text := nullif(left(trim(coalesce(p_note, '')), 500), ''); out text;
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
    else update public.group_listings set review_hold = false where id = h.item_id; end if;
  else
    if h.kind = 'post' then delete from public.posts where id = h.item_id;
    elsif h.kind = 'offer' then delete from public.products where id = h.item_id;
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

-- ── search leaves held posts out (0065's search_all, with that one filter) ────
create or replace function public.search_all(p_q text, p_limit int default 6) returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); q text := regexp_replace(trim(coalesce(p_q, '')), '\s+', ' ', 'g'); pat text; pre text;
        n int := least(greatest(coalesce(p_limit, 6), 1), 20); bl uuid[];
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if length(q) < 2 or length(q) > 80 then return jsonb_build_object('q', q); end if;
  pre := replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_'); pat := '%' || pre || '%'; pre := pre || '%';
  bl := private.blocks_with_me();
  return jsonb_build_object('q', q,
    'people', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select p.id, p.name, p.headline, p.company, p.avatar_url, p.verified, p.location, p.country from public.profiles p
         where (p.name ilike pat or p.company ilike pat or p.headline ilike pat) and p.account_type is distinct from 'deleted' and p.id <> me and p.id <> all (bl)
           and not exists (select 1 from public.account_suspensions s where s.user_id = p.id)
         order by (p.name ilike pre) desc, (p.name ilike pat) desc, length(p.name), p.created_at desc limit n) x),
    'companies', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select c.id, c.slug, c.name, c.city, c.country, c.verified, c.logo_emoji, c.type from public.companies c
         where c.status <> 'suspended'
           and (c.name ilike pat or c.name_ar ilike pat
                or c.id in (select k.company_id from public.company_products k where k.name ilike pat or k.active_ingredient ilike pat or k.active_ingredient_ar ilike pat limit 200))
         order by (c.name ilike pre) desc, c.verified desc nulls last, length(c.name) limit n) x),
    'products', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select r.id, r.name, r.category, r.price, r.unit, r.emoji, r.user_id, (select s.name from public.profiles s where s.id = r.user_id) as seller from public.products r
         where r.active and (r.expires_at is null or r.expires_at > now()) and r.name ilike pat and r.user_id <> all (bl) order by (r.name ilike pre) desc, r.created_at desc limit n) x),
    'jobs', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select j.id, j.title, j.company, j.location, j.type, j.user_id from public.jobs j
         where j.active and (j.deadline is null or j.deadline >= current_date) and (j.title ilike pat or j.company ilike pat) and j.user_id <> all (bl) order by (j.title ilike pre) desc, j.created_at desc limit n) x),
    'groups', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select g.id, g.name, g.emoji, g.type, g.member_count from public.groups g
         where g.name ilike pat and (g.archived_at is null or public.is_group_member(g.id))
           and (g.type = 'public' or g.listed or g.created_by = me or public.is_group_member(g.id)
                or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = me))
         order by (g.name ilike pre) desc, g.member_count desc limit n) x),
    'posts', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select o.id, left(o.body, 240) as body, o.user_id, o.created_at, (select a.name from public.profiles a where a.id = o.user_id) as author from public.posts o
         where o.group_id is null and not o.review_hold and o.body ilike pat and o.user_id <> all (bl) order by o.created_at desc limit n) x));
end $$;
revoke all on function public.search_all(text, int) from public, anon, authenticated, service_role;
grant execute on function public.search_all(text, int) to authenticated, service_role;

notify pgrst, 'reload schema';
