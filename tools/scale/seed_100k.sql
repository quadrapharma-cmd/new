-- ═════════════════════════════════════════════════════════════════════
-- Drugbox — staging load seed: 100,000 members and the volume behind every hot path
--
--   psql "$STAGING_DB_URL" -v ON_ERROR_STOP=1 -f tools/scale/seed_100k.sql
--   psql "$STAGING_DB_URL" -v ON_ERROR_STOP=1 -v scale_users=2000 -f tools/scale/seed_100k.sql     (a quick smoke run)
--
-- Members member<N>@scale.test (N = 1 … users), password Scale-pass-2026, e-mail confirmed. Their ids are
-- md5('drugbox-scale-' || N) as a uuid, so tools/scale/seed_auth_admin.mjs (Auth Admin API, when direct auth.users
-- rows cannot sign in on your Supabase version) creates the SAME ids and this script then only adds the rest.
-- Volume (users = 100,000): 5k companies (60 % verified, 35 % pending, 5 % unclaimed), 1.02M connections
-- (20 accepted per member, one row per pair), 300k posts + 30k media, ~1M likes, 100k comments, 400k messages in
-- ~80k conversations, ~600k notifications, 20k jobs + 100k applications, 20k listings, 20k products, 10k enquiries,
-- 20k deals with 60k events, 2k groups with ~200k members, trust data (reviews, references, lists).
-- Heavy members: member1 … member10 (500 extra connections, 100 conversations x 20 messages, 200 posts each,
-- member1 owns company 1 with ~200 deals) — tools/scale/timings.py measures member1 and a typical member.
--
-- Run it AFTER every migration, as `postgres` (the Supabase SQL owner) on a DIRECT connection
-- (db.<ref>.supabase.co:5432 or the session pooler — not the transaction pooler on :6543, which drops `set`).
-- Server-managed columns are written directly: is_server_call() is true for this role, so the 0020 guards allow
-- them; for speed each section turns its table's own triggers off (ALTER TABLE … DISABLE TRIGGER USER — the
-- foreign keys stay on) inside ONE transaction and rebuilds what those triggers maintain (counters, conversation
-- heads, owner/creator rows) set-based before turning them back on. A failure rolls the section back, triggers
-- included. While a section runs its tables are locked: seed staging, never production.
-- Idempotent: a completed seed is detected and skipped; a partial one is removed (tools/scale/unseed.sql) and
-- redone. Only @scale.test members, their companies (co<N>@scale.test) and what hangs off them are touched.
-- Every section prints its time; the summary at the end lists them. Target: < 15 min on 4 cores.
-- ═════════════════════════════════════════════════════════════════════
\set ON_ERROR_STOP on
\set QUIET on
\pset pager off
\pset footer off
\if :{?scale_users}
\else
  \set scale_users 100000
\endif
set statement_timeout = 0;
set lock_timeout = '30s';
set synchronous_commit = off;
set work_mem = '256MB';
set maintenance_work_mem = '512MB';
set client_min_messages = warning;
set search_path = public, extensions;           -- pgcrypto lives in `extensions` on Supabase (and in the local stub)

-- ── already done? ───────────────────────────────────────────────────────────
select to_regclass('scale.kv') is not null as has_kv \gset
\if :has_kv
  select exists (select 1 from scale.kv where k = 'done') as seeded \gset
\else
  \set seeded false
\endif
\if :seeded
  \echo 'scale seed: already complete (scale.kv done) — nothing to do. To redo: psql -f tools/scale/unseed.sql first.'
  select k, v from scale.kv order by k;
  \quit
\endif
-- a production project (many real accounts) is refused unless -v prod=1 is given explicitly
select count(*) > 2000 as looks_prod from auth.users where email not like '%@scale.test' \gset
\if :looks_prod
  \if :{?prod}
    \echo 'scale seed: -v prod=1 given — seeding a database with many real accounts'
  \else
    do $$ begin raise exception 'scale seed: this database has more than 2,000 real accounts (production?) — refusing; pass -v prod=1 only if you really mean it'; end $$;
  \endif
\endif
-- a database that deploy/supabase_deploy.sh stamped 'production' is refused the same way (a new production project has few accounts)
select to_regclass('drugbox_deploy.environment') is not null as has_stamp \gset
\if :has_stamp
  select exists (select 1 from drugbox_deploy.environment where name = 'production') as stamped_prod \gset
\else
  \set stamped_prod false
\endif
\if :stamped_prod
  \if :{?prod}
    \echo 'scale seed: -v prod=1 given — seeding a database stamped PRODUCTION'
  \else
    do $$ begin raise exception 'scale seed: this database is stamped PRODUCTION (drugbox_deploy.environment) — refusing; the load seed is for staging'; end $$;
  \endif
\endif
select exists (select 1 from auth.users where email like '%@scale.test') or to_regclass('scale.kv') is not null as partial \gset
\if :partial
  \echo 'scale seed: a partial seed is present — removing it first (unseed.sql)'
  \ir unseed.sql
  set search_path = public, extensions;
\endif

\echo 'scale seed: users =' :scale_users
create schema scale;
revoke all on schema scale from public;
create table scale.kv (k text primary key, v bigint not null);
create table scale.txt (k text primary key, v text not null);
create table scale.log (section text primary key, started timestamptz not null, finished timestamptz);
insert into scale.kv values ('users', :scale_users);
-- the member's id, from N (immutable: inlined into every set-based insert)
create function scale.u(n bigint) returns uuid language sql immutable parallel safe as
  $$ select md5('drugbox-scale-' || n)::uuid $$;
create function scale.n(key text) returns bigint language sql stable as $$ select v from scale.kv where k = key $$;
-- a stable pseudo-random number 0 … m-1 for (salt, i): the same data on every run
create function scale.h(salt text, i bigint, m bigint) returns bigint language sql immutable parallel safe as
  $$ select (abs(hashtextextended(salt || ':' || i, 0)) % greatest(m, 1)) $$;
-- a believable name: three in four transliterated, one in four in Arabic script (the interface is bilingual)
create function scale.person_name(n bigint) returns text language sql immutable parallel safe as $$
  select case when n % 4 = 0
    then (array['أحمد','محمد','منى','سارة','خالد','ياسمين','عمرو','نهى','مريم','يوسف'])[1 + (n / 4) % 10] || ' '
         || (array['عبد الله','حسن','إبراهيم','مصطفى','سليمان','الشريف','منصور'])[1 + (n / 40) % 7]
    else (array['Ahmed','Mohamed','Mona','Sara','Khaled','Yasmin','Amr','Noha','Mariam','Youssef','Omar','Heba','Karim','Dina','Tarek',
                'Rania','Hossam','Salma','Mahmoud','Nour'])[1 + n % 20] || ' '
         || (array['Abdallah','Hassan','Ibrahim','Mostafa','Soliman','El-Sherif','Mansour','Fawzy','Gaber','Hamdy','Kamel','Lotfy','Nasser',
                   'Ragab','Saleh','Tawfik','Zaki','Farouk','Galal','Morsy','Shawky','Yassin','Ashour','Badawy','Darwish'])[1 + (n / 20) % 25]
  end $$;
create procedure scale.start(s text) language plpgsql as $$
begin insert into scale.log (section, started) values (s, clock_timestamp()); raise notice 'scale seed: % …', s; end $$;
create procedure scale.done(s text) language plpgsql as $$
declare t interval;
begin update scale.log set finished = clock_timestamp() where section = s returning finished - started into t;
      raise notice 'scale seed: % done in % s', s, round(extract(epoch from t)::numeric, 1); end $$;
-- reserve a block of ids from a table's own sequence (serial or identity) so rows can be addressed as base + i
create function scale.reserve(tbl text, n bigint) returns bigint language plpgsql as $$
declare seq text := pg_get_serial_sequence('public.' || tbl, 'id'); b bigint;
begin
  b := nextval(seq);
  perform setval(seq, b + n);
  insert into scale.kv values (tbl, b) on conflict (k) do update set v = excluded.v;
  return b;   -- rows use b + 1 … b + n (b itself is skipped)
end $$;
set client_min_messages = notice;

-- ═════ 1. members: auth.users (+ auth.identities on Supabase) and profiles ═════
call scale.start('1 members');
-- bcrypt ONCE (cost 6), the same hash for every member
insert into scale.txt values ('pw', crypt('Scale-pass-2026', gen_salt('bf', 6)));
-- an id already used by another e-mail, or a scale e-mail with a foreign id, would break the mapping: stop early
do $$ declare bad int; begin
  select count(*) into bad from auth.users u, generate_series(1, scale.n('users')) n
   where u.id = scale.u(n) and u.email is distinct from 'member' || n || '@scale.test';
  if bad > 0 then raise exception 'scale seed: % auth.users rows hold a scale id with another e-mail', bad; end if;
  select count(*) into bad from auth.users u where u.email like 'member%@scale.test'
     and u.id <> scale.u(nullif(substring(u.email from '^member([0-9]+)@scale\.test$'), '')::bigint);
  if bad > 0 then raise exception 'scale seed: % scale e-mails exist with other ids — run unseed.sql (or seed_auth_admin.mjs with the same ids)', bad; end if;
end $$;
-- auth.users: only the columns this database has (Supabase GoTrue needs the token columns as '' not NULL,
-- instance_id/aud/role and a confirmed e-mail; the local stub has a handful)
do $$
declare
  c text[]; cols text := ''; vals text := ''; ok boolean;
  cand text[] := array[
    'id', 'scale.u(n)',
    'instance_id', '''00000000-0000-0000-0000-000000000000''::uuid',
    'aud', '''authenticated''',
    'role', '''authenticated''',
    'email', '''member'' || n || ''@scale.test''',
    'encrypted_password', 'pw.v',
    'email_confirmed_at', 'now()',
    'raw_app_meta_data', '''{"provider":"email","providers":["email"]}''::jsonb',
    'raw_user_meta_data', 'jsonb_build_object(''name'', scale.person_name(n), ''email_verified'', true)',
    'created_at', 'now() - make_interval(days => (scale.h(''uc'', n, 730))::int)',
    'updated_at', 'now()',
    'confirmation_token', '''''', 'recovery_token', '''''', 'email_change_token_new', '''''', 'email_change', '''''',
    'email_change_token_current', '''''', 'phone_change', '''''', 'phone_change_token', '''''', 'reauthentication_token', '''''',
    'is_super_admin', 'false', 'is_sso_user', 'false', 'is_anonymous', 'false'];
begin
  for i in 1 .. array_length(cand, 1) / 2 loop
    select exists (select 1 from information_schema.columns where table_schema = 'auth' and table_name = 'users'
                    and column_name = cand[2 * i - 1] and is_generated = 'NEVER') into ok;
    if ok then cols := cols || case when cols = '' then '' else ', ' end || quote_ident(cand[2 * i - 1]);
               vals := vals || case when vals = '' then '' else ', ' end || cand[2 * i]; end if;
  end loop;
  execute format('insert into auth.users (%s) select %s from generate_series(1, %s) n, scale.txt pw where pw.k = ''pw'' on conflict (id) do nothing',
                 cols, vals, scale.n('users'));
end $$ ;
-- Supabase (GoTrue ≥ 2.x) signs in through auth.identities: one 'email' identity per member, when the table exists
do $$
declare has_pid boolean; id_type text;
begin
  if to_regclass('auth.identities') is null then raise notice 'scale seed: no auth.identities (local stand-in) — skipped'; return; end if;
  select exists (select 1 from information_schema.columns where table_schema = 'auth' and table_name = 'identities' and column_name = 'provider_id') into has_pid;
  select data_type into id_type from information_schema.columns where table_schema = 'auth' and table_name = 'identities' and column_name = 'id';
  if has_pid then
    execute format($f$insert into auth.identities (id, user_id, provider_id, provider, identity_data, last_sign_in_at, created_at, updated_at)
      select %s, scale.u(n), scale.u(n)::text, 'email',
             jsonb_build_object('sub', scale.u(n)::text, 'email', 'member' || n || '@scale.test', 'email_verified', true, 'phone_verified', false),
             now(), now(), now()
      from generate_series(1, scale.n('users')) n
      where not exists (select 1 from auth.identities i where i.user_id = scale.u(n) and i.provider = 'email')$f$,
      case when id_type = 'uuid' then 'gen_random_uuid()' else 'scale.u(n)::text' end);
  else   -- older GoTrue: id = the user id as text, no provider_id
    insert into auth.identities (id, user_id, provider, identity_data, last_sign_in_at, created_at, updated_at)
    select scale.u(n)::text, scale.u(n), 'email', jsonb_build_object('sub', scale.u(n)::text, 'email', 'member' || n || '@scale.test'), now(), now(), now()
    from generate_series(1, scale.n('users')) n
    where not exists (select 1 from auth.identities i where i.user_id = scale.u(n) and i.provider = 'email');
  end if;
end $$;
-- profiles: handle_new_user made them; filled here (the guard leaves server calls alone; triggers off for speed)
begin;
alter table public.profiles disable trigger user;
insert into public.profiles (id, name) select scale.u(n), scale.person_name(n) from generate_series(1, :scale_users) n on conflict (id) do nothing;
update public.profiles p set
  name = s.name,
  headline = (array['Regulatory Affairs Specialist','QA Manager','QC Analyst','Production Pharmacist','Medical Representative','Business Development Manager',
                    'Supply Chain Lead','R&D Formulation Scientist','Pharmacovigilance Officer','Plant Manager','Export Manager','Tender Specialist',
                    'أخصائي شؤون تنظيمية','مدير توكيد الجودة','صيدلي إنتاج','مندوب دعاية طبية'])[1 + s.n % 16]
             || ' at ' || 'Scale Pharma ' || (1 + s.n % greatest(:scale_users / 20, 1)),
  company = 'Scale Pharma ' || (1 + s.n % greatest(:scale_users / 20, 1)),
  country = (array['EG','EG','EG','EG','EG','EG','EG','SA','AE','JO','KW','EG'])[1 + s.n % 12],
  location = (array['Cairo','Giza','Alexandria','10th of Ramadan','6th of October','Mansoura','Riyadh','Dubai','Amman','Sadat City'])[1 + s.n % 10],
  bio = (array['Ten years in regulatory affairs: CTD dossiers, EDA variations and GCC submissions.',
               'QA lead for solid and liquid dosage forms; PIC/S inspections, CAPA and annual product reviews.',
               'Pharmacist working on tenders and hospital supply across Egypt and the Gulf.',
               'خبرة في تسجيل المستحضرات لدى هيئة الدواء المصرية وملفات التصدير للخليج.'])[1 + s.n % 4],
  experience = jsonb_build_array(jsonb_build_object('title', 'Specialist', 'company', 'Scale Pharma ' || (1 + s.n % 997), 'period', '2019-2024', 'years', 1 + s.n % 15)),
  skills = string_to_array((array['GMP,EDA,CTD', 'ICH Q7,Validation,CAPA', 'Tenders,KAM,Distribution', 'Formulation,Stability,BE'])[1 + s.n % 4], ','),
  languages = array['Arabic','English'],
  years_experience = 1 + s.n % 25,
  open_to_work = s.n % 10 = 3, hiring = s.n % 25 = 7, verified = s.n % 10 = 1,
  profile_views = scale.h('pv', s.n, 900)::int,
  created_at = now() - make_interval(days => (scale.h('uc', s.n, 730))::int),
  available_since = case when s.n % 10 = 3 then now() - make_interval(days => (s.n % 60)::int) end
from (select n, scale.u(n) as id, scale.person_name(n) as name from generate_series(1, :scale_users) n) s
where p.id = s.id;
alter table public.profiles enable trigger user;
commit;
call scale.done('1 members');

-- ═════ 2. companies: 5k (+ team, products, sites, certificates, followers) ═════
call scale.start('2 companies');
begin;
alter table public.companies disable trigger user;
alter table public.company_members disable trigger user;
alter table public.company_followers disable trigger user;
alter table public.site_certificates disable trigger user;
select greatest(:scale_users / 20, 1) as companies_n \gset
select scale.reserve('companies', :companies_n) as companies \gset
insert into scale.kv values ('companies_n', :companies_n);
-- company i (1 … C): owner member (i*7 mod users)+1 — company 1 is member1's; every 20th is an unclaimed public-list row
insert into public.companies (id, owner_id, name, name_ar, slug, type, location, country, bio, tagline, status, source, registry, tax_verified, licensed,
                              sectors, governorate, city, plan, vip_until, email, phone, employees, founded, profile, follower_count, created_at, updated_at)
select :companies + i,
       case when i % 20 = 0 then null else scale.u(1 + ((i - 1) * 7) % :scale_users) end,
       (array['Nile','Delta','Sinai','Pyramids','Lotus','Horus','Memphis','Faros','Red Sea','Oasis'])[1 + i % 10] || ' '
         || (array['Pharmaceuticals','Pharma Industries','Medical Supplies','Chemicals','Laboratories','Healthcare','Biotech'])[1 + (i / 10) % 7] || ' ' || i,
       'شركة ' || (array['النيل','الدلتا','سيناء','الأهرام','اللوتس'])[1 + i % 5] || ' للأدوية ' || i,
       'scale-co-' || i,
       (array['Manufacturer','Distributor','CMO','API supplier','Scientific office','Consultancy'])[1 + i % 6],
       'Industrial zone ' || (1 + i % 40), 'EG',
       'Manufacturer of solid and liquid dosage forms for the Egyptian and Gulf markets; EDA-registered portfolio of ' || (20 + i % 200) || ' products.',
       'Quality medicines since ' || (1980 + i % 40),
       case when i % 20 = 0 then 'unclaimed' when i % 20 < 8 then 'pending' else 'verified' end,
       case when i % 20 = 0 then 'public_list' else 'company' end,
       case when i % 20 >= 8 then 'CR-' || (500000 + i) end,
       i % 20 >= 8 and i % 3 = 0, i % 20 >= 8 and i % 2 = 0,
       array[(array['Finished dosage','API','CMO','Distribution','Cosmetics','Medical devices'])[1 + i % 6]],
       (array['Cairo','Giza','Alexandria','Sharqia','Qalyubia','Dakahlia','Monufia'])[1 + i % 7], 'City ' || (1 + i % 60),
       case when i % 50 = 0 then 'vip' else 'free' end, case when i % 50 = 0 then now() + interval '200 days' end,
       'co' || i || '@scale.test', '+20 2 ' || (2000000 + i), (array['1-10','11-50','51-200','201-500','500+'])[1 + i % 5], 1980 + i % 44,
       jsonb_build_object('services', array['Toll manufacturing','Packaging','Stability studies'], 'address', 'Plot ' || i || ', industrial zone', 'colour', '#1a56db'),
       0, now() - make_interval(days => (scale.h('cc', i, 900))::int), now() - make_interval(days => (scale.h('cu', i, 90))::int)
from generate_series(1, :companies_n) i;
-- the owner row companies_after_insert would add, plus two colleagues (sales, quality)
insert into public.company_members (company_id, user_id, role, accepted, show_public)
select c.id, c.owner_id, 'owner', true, true from public.companies c
where c.id between :companies + 1 and :companies + :companies_n and c.owner_id is not null
on conflict do nothing;
insert into public.company_members (company_id, user_id, role, accepted, show_public)
select :companies + i, scale.u(1 + (i * 13 + k * 101) % :scale_users), (array['sales','quality'])[k], true, true
from generate_series(1, :companies_n) i, generate_series(1, 2) k
where i % 20 <> 0
on conflict do nothing;
insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, dosage_form, strength, role, registration_no)
select :companies + i,
       (array['Glucophage','Amoxil','Panadol','Lipitor','Nexium','Brufen','Augmentin','Concor','Zithromax','Voltaren'])[1 + (i + k) % 10] || ' generic ' || i || '-' || k,
       (array['Metformin','Amoxicillin','Paracetamol','Atorvastatin','Esomeprazole','Ibuprofen','Amoxicillin/Clavulanate','Bisoprolol','Azithromycin','Diclofenac'])[1 + (i + k) % 10],
       (array['ميتفورمين','أموكسيسيلين','باراسيتامول','أتورفاستاتين','إيزوميبرازول'])[1 + (i + k) % 5],
       (array['Tablet','Capsule','Syrup','Injection','Cream'])[1 + k % 5], (array['500 mg','250 mg','20 mg','5 mg','1 g'])[1 + (i * k) % 5],
       (array['manufacturer','registration_holder','supplier'])[1 + k % 3], 'REG-' || i || '-' || k
from generate_series(1, :companies_n) i, generate_series(1, 5) k;
insert into public.company_sites (company_id, name, type, city, governorate, dosage_forms, capacity)
select c.id, 'Main plant', 'factory', c.city, c.governorate, array['Tablet','Capsule'], '50M units / year'
from public.companies c where c.id between :companies + 1 and :companies + :companies_n;
insert into public.site_certificates (site_id, company_id, name, expiry, source, checked_at)
select s.id, s.company_id, (array['GMP','ISO 9001','ISO 17025','GDP'])[1 + ((s.company_id + k) % 4)::int],
       current_date + ((s.company_id * k) % 900 - 100)::int, 'company', case when (s.company_id + k) % 2 = 0 then now() end
from public.company_sites s, generate_series(1, 2) k
where s.company_id between :companies + 1 and :companies + :companies_n;
insert into public.company_followers (company_id, user_id, created_at)
select :companies + 1 + scale.h('fc', i, :companies_n), scale.u(1 + scale.h('fu', i, :scale_users)), now() - make_interval(days => (i % 365)::int)
from generate_series(1, :scale_users / 2) i
on conflict do nothing;
update public.companies c set follower_count = f.k
from (select company_id, count(*) k from public.company_followers
      where company_id between :companies + 1 and :companies + :companies_n group by company_id) f
where c.id = f.company_id;
alter table public.companies enable trigger user;
alter table public.company_members enable trigger user;
alter table public.company_followers enable trigger user;
alter table public.site_certificates enable trigger user;
commit;
call scale.done('2 companies');

-- ═════ 3. connections: 20 accepted per member (one row per pair), pending requests, heavy members ═════
call scale.start('3 connections');
begin;
alter table public.connections disable trigger user;
-- member i ↔ i + d (mod users) for 10 offsets d < users/2: every pair once, 10 sent + 10 received = 20 per member;
-- small offsets give friends-of-friends overlap, so suggest_people has real mutuals to rank
insert into public.connections (requester, addressee, status, created_at)
select scale.u(i), scale.u(1 + (i - 1 + d) % :scale_users), 'accepted', now() - make_interval(days => (scale.h('cn', i * 100 + d, 700))::int)
from generate_series(1, :scale_users) i, unnest(array[1,2,3,5,8,13,21,34,55,89]) d
where d < :scale_users / 2;
-- pending requests (every 5th member, offset 144)
insert into public.connections (requester, addressee, status, created_at)
select scale.u(i), scale.u(1 + (i - 1 + 144) % :scale_users), 'pending', now() - make_interval(days => (i % 20)::int)
from generate_series(1, :scale_users) i where i % 5 = 0 and 144 < :scale_users / 2;
-- heavy members 1 … 10: 500 more accepted connections each
insert into public.connections (requester, addressee, status, created_at)
select scale.u(h), scale.u(1 + (1000 + h * 600 + k) % :scale_users), 'accepted', now() - make_interval(days => (k % 300)::int)
from generate_series(1, least(10, :scale_users)) h, generate_series(1, 500) k
where 1 + (1000 + h * 600 + k) % :scale_users > 10
on conflict do nothing;
-- profiles.followers_count = accepted connections (what trg_connections_followers_count maintains)
update public.profiles p set followers_count = x.k
from (select id, count(*) k from (select requester id from public.connections where status = 'accepted' and requester in (select scale.u(n) from generate_series(1, :scale_users) n)
                                  union all
                                  select addressee from public.connections where status = 'accepted' and addressee in (select scale.u(n) from generate_series(1, :scale_users) n)) y
      group by id) x
where p.id = x.id;
alter table public.connections enable trigger user;
commit;
call scale.done('3 connections');

-- ═════ 4. feed: 300k posts, 30k media, ~1M likes, 100k comments, saves ═════
call scale.start('4 posts');
begin;
alter table public.posts disable trigger user;
alter table public.post_media disable trigger user;
alter table public.reactions disable trigger user;
alter table public.comments disable trigger user;
alter table public.saved_posts disable trigger user;
select :scale_users * 3 as posts_n \gset
select scale.reserve('posts', :posts_n) as posts \gset
insert into scale.kv values ('posts_n', :posts_n);
-- post i: the first 2,000 belong to the heavy members, the rest spread over everyone; recent days are busier
insert into public.posts (id, user_id, body, category, pinned, created_at, view_count, share_count, like_count, comment_count)
select :posts + i,
       case when i <= 2000 then scale.u(1 + i % least(10, :scale_users)) else scale.u(1 + (i::bigint * 7919) % :scale_users) end,
       (array['New EDA guideline on stability data for climatic zone IVb — what changes for your pending files?',
              'We just passed our PIC/S inspection with zero critical observations. Proud of the QA team!',
              'Looking for a CMO with a beta-lactam line for 2M tablets/month. DM me.',
              'Price of Metformin API went up 12% this quarter. Anyone sourcing from India seeing the same?',
              'هل حد جرب يقدّم ملف تسجيل إلكتروني على المنظومة الجديدة لهيئة الدواء؟ محتاج نصيحة.',
              'Hiring: two QC analysts (HPLC, dissolution) for our 10th of Ramadan plant.',
              'Webinar next Tuesday: bioequivalence waivers under the new EDA rules.',
              'Surplus stock: 500 kg Paracetamol DC grade, expiry 2027-06, CoA available.',
              'فرصة تصنيع لدى الغير: خط سوائل غير معقمة متاح من الشهر القادم.',
              'Serialization deadline is close — how far along is your GS1 implementation?',
              'Sharing our checklist for annual product quality reviews (APQR). Comments welcome.',
              'Congratulations to the team on the first export shipment to Saudi Arabia!'])[1 + i % 12] || ' #' || i,
       (array['general','regulatory','market','innovation','job'])[1 + i % 5], false,
       now() - make_interval(secs => (power(scale.h('pc', i, 1000000) / 1000000.0, 2) * 365 * 86400)::int),
       scale.h('pv', i, 3000)::int, (i % 20)::int, 0, 0
from generate_series(1, :posts_n) i;
insert into public.post_media (post_id, url, type, name, size)
select :posts + i * 10, 'https://picsum.photos/seed/drugbox' || i || '/800/600', 'image', 'photo.jpg', 120000 + i % 50000
from generate_series(1, :posts_n / 10) i;
-- likes: ~10 per member spread over all posts, plus 30 on each heavy-member post
insert into public.reactions (post_id, user_id, kind, created_at)
select :posts + 1 + scale.h('rp', i, :posts_n), scale.u(1 + scale.h('ru', i, :scale_users)),
       (array['like','like','like','love','insightful','support','celebrate'])[1 + i % 7], now() - make_interval(secs => (scale.h('rt', i, 365 * 86400))::int)
from generate_series(1, :scale_users * 10) i
on conflict do nothing;
insert into public.reactions (post_id, user_id, kind, created_at)
select :posts + p, scale.u(1 + scale.h('hr', p * 100 + k, :scale_users)), 'like', now() - make_interval(secs => (scale.h('ht', p * 100 + k, 30 * 86400))::int)
from generate_series(1, least(2000, :posts_n)) p, generate_series(1, 30) k
on conflict do nothing;
insert into public.comments (post_id, user_id, body, created_at)
select :posts + 1 + scale.h('cp', i, :posts_n), scale.u(1 + scale.h('cu', i, :scale_users)),
       (array['Agree — this changes the dossier timeline.','Thanks for sharing!','Can you send the details by message?','مبروك، بالتوفيق دايماً','Same experience here.','Which grade exactly?'])[1 + i % 6],
       now() - make_interval(secs => (scale.h('ct', i, 365 * 86400))::int)
from generate_series(1, :scale_users) i;
insert into public.saved_posts (user_id, post_id)
select scale.u(1 + scale.h('su', i, :scale_users)), :posts + 1 + scale.h('sp', i, :posts_n)
from generate_series(1, :scale_users) i on conflict do nothing;
-- the counters trg_like_count / trg_comment_count maintain
update public.posts p set like_count = x.l, comment_count = x.c
from (select id, coalesce(l, 0) l, coalesce(c, 0) c from
        (select post_id id, count(*) l from public.reactions where post_id between :posts + 1 and :posts + :posts_n group by 1) a
        full join (select post_id id, count(*) c from public.comments where post_id between :posts + 1 and :posts + :posts_n group by 1) b using (id)) x
where p.id = x.id;
alter table public.posts enable trigger user;
alter table public.post_media enable trigger user;
alter table public.reactions enable trigger user;
alter table public.comments enable trigger user;
alter table public.saved_posts enable trigger user;
commit;
call scale.done('4 posts');

-- ═════ 5. messages: ~80k conversations x 5 (most members have one or two) + heavy members 100 x 20, with conversation heads ═════
call scale.start('5 messages');
begin;
alter table public.messages disable trigger user;
alter table public.conversation_heads disable trigger user;
create temp table scale_msg on commit drop as
select a, b, k, t + make_interval(mins => k::int) as at, last_k from (
  select scale.u(1 + (c - 1) % :scale_users) a, scale.u(1 + scale.h('mb', c, :scale_users)) b, k, 5 last_k,
         now() - make_interval(secs => (power(scale.h('mt', c, 1000000) / 1000000.0, 2) * 300 * 86400)::int) - interval '10 minutes' t
  from generate_series(1, (:scale_users * 8) / 10) c, generate_series(1, 5) k
  union all
  select scale.u(h), scale.u(1 + (20000 + h * 150 + j) % :scale_users), k, 20,
         now() - make_interval(hours => (j * 3)::int) - interval '30 minutes'
  from generate_series(1, least(10, :scale_users)) h, generate_series(1, 100) j, generate_series(1, 20) k
  where 1 + (20000 + h * 150 + j) % :scale_users > 10) s
where a <> b;
select count(*) as messages_n from scale_msg \gset
select scale.reserve('messages', :messages_n) as messages \gset
insert into scale.kv values ('messages_n', :messages_n);
-- ids follow time (new_messages polls by id); the last message of a conversation stays unread a third of the time
insert into public.messages (id, sender_id, receiver_id, body, read_at, created_at)
select :messages + row_number() over (order by at, a, b, k),
       case when k % 2 = 1 then a else b end, case when k % 2 = 1 then b else a end,
       (array['Hello, can you send the CoA for batch 0421?','Sure — sending it today.','What is your best price for 500 kg?','USD 5.80/kg CIF Alexandria, 30 days.',
              'Can we schedule a call tomorrow?','تمام، هبعتلك العرض النهارده','Please share the stability data.','Thanks, received.'])[1 + (k % 8)::int] || ' (' || k || ')',
       case when k < last_k or scale.h('mr', k, 3) <> 0 then at + interval '5 minutes' end, at
from scale_msg;
-- conversation_heads exactly as the 0005 triggers keep them: one row per (owner, partner) with the last message and the unread count
insert into public.conversation_heads (owner, partner, last_message, last_body, last_at, last_from_me, unread)
select x.owner, x.partner, x.id, x.body, x.created_at, x.owner = x.sender_id,
       coalesce((select count(*) from public.messages u where u.receiver_id = x.owner and u.sender_id = x.partner and u.read_at is null), 0)
from (select distinct on (owner, partner) owner, partner, id, body, created_at, sender_id from (
        select m.sender_id owner, m.receiver_id partner, m.id, m.body, m.created_at, m.sender_id from public.messages m
         where m.id between :messages + 1 and :messages + :messages_n
        union all
        select m.receiver_id, m.sender_id, m.id, m.body, m.created_at, m.sender_id from public.messages m
         where m.id between :messages + 1 and :messages + :messages_n) y
      order by owner, partner, created_at desc, id desc) x
on conflict (owner, partner) do nothing;
alter table public.messages enable trigger user;
alter table public.conversation_heads enable trigger user;
commit;
call scale.done('5 messages');

-- ═════ 6. jobs: 20k jobs, 100k applications, saved jobs ═════
call scale.start('6 jobs');
begin;
alter table public.jobs disable trigger user;
alter table public.job_applications disable trigger user;
select greatest(:scale_users / 5, 1) as jobs_n \gset
select scale.reserve('jobs', :jobs_n) as jobs \gset
insert into scale.kv values ('jobs_n', :jobs_n);
insert into public.jobs (id, user_id, title, company, location, country, type, seniority, description, salary, active, remote, category, applicant_count, created_at, requirements, benefits)
select :jobs + j,
       case when j <= 200 then scale.u(1 + j % least(3, :scale_users)) else scale.u(1 + (j * 31) % :scale_users) end,
       (array['Regulatory Affairs Specialist','QC Analyst','Production Supervisor','Medical Representative','R&D Pharmacist','QA Officer'])[1 + j % 6] || ' (' || j || ')',
       (array['Nile','Delta','Sinai','Pyramids','Lotus','Horus','Memphis','Faros','Red Sea','Oasis'])[1 + j % 10] || ' Pharmaceuticals ' || (1 + j % greatest(:scale_users / 20, 1)),
       (array['Cairo','Giza','Alexandria','10th of Ramadan','6th of October'])[1 + j % 5], 'EG',
       (array['full-time','full-time','contract','part-time'])[1 + j % 4], (array['junior','mid','senior','lead'])[1 + j % 4],
       'Prepare and follow up CTD dossiers and EDA submissions; coordinate with QA and production; 3+ years in a GMP plant.',
       case when j % 3 = 0 then 'EGP ' || (15 + j % 30) || 'k / month' end,
       j % 10 <> 0, j % 7 = 0, (array['regulatory','qaqc','production','sales','rd','other'])[1 + j % 6], 0,
       now() - make_interval(days => (scale.h('jc', j, 120))::int), array['B.Pharm','GMP'], array['Medical insurance','Transport']
from generate_series(1, :jobs_n) j;
insert into public.job_applications (job_id, user_id, note, status, created_at)
select :jobs + 1 + scale.h('aj', i, :jobs_n), scale.u(1 + scale.h('au', i, :scale_users)), 'I am interested — CV attached in my profile.',
       (array['submitted','submitted','viewed','shortlisted','interviewed','rejected','hired'])[1 + i % 7], now() - make_interval(days => (scale.h('ac', i, 100))::int)
from generate_series(1, :scale_users) i
on conflict do nothing;
insert into public.saved_jobs (user_id, job_id)
select scale.u(1 + scale.h('sju', i, :scale_users)), :jobs + 1 + scale.h('sjj', i, :jobs_n)
from generate_series(1, (:scale_users * 3) / 10) i on conflict do nothing;
update public.jobs j set applicant_count = a.k
from (select job_id, count(*) k from public.job_applications where job_id between :jobs + 1 and :jobs + :jobs_n group by 1) a
where j.id = a.job_id;
alter table public.jobs enable trigger user;
alter table public.job_applications enable trigger user;
commit;
call scale.done('6 jobs');

-- ═════ 7. notifications: likes, comments, connections, applications (~600k) ═════
call scale.start('7 notifications');
begin;
alter table public.notifications disable trigger user;
insert into public.notifications (user_id, type, from_user, post_id, comment_id, job_id, message, read, created_at)
select user_id, type, from_user, post_id, comment_id, job_id, message, created_at < now() - interval '3 days', created_at from (
  select p.user_id, 'like' type, r.user_id from_user, r.post_id, null::bigint comment_id, null::bigint job_id, null message, r.created_at
  from public.reactions r join public.posts p on p.id = r.post_id
  where r.post_id between :posts + 1 and :posts + :posts_n and r.user_id <> p.user_id
    and (r.post_id <= :posts + 2000 or scale.h('nl', r.post_id, 3) = 0)
  union all
  select p.user_id, 'comment', c.user_id, c.post_id, c.id, null, left(c.body, 80), c.created_at
  from public.comments c join public.posts p on p.id = c.post_id
  where c.post_id between :posts + 1 and :posts + :posts_n and c.user_id <> p.user_id
  union all
  select c.requester, 'connection_accepted', c.addressee, null, null, null, null, c.created_at
  from public.connections c where c.status = 'accepted' and c.requester in (select scale.u(n) from generate_series(1, :scale_users) n) and scale.h('na', c.id, 5) = 0
  union all
  select c.addressee, 'connection_request', c.requester, null, null, null, null, c.created_at
  from public.connections c where c.status = 'pending' and c.requester in (select scale.u(n) from generate_series(1, :scale_users) n)
  union all
  select j.user_id, 'job_application', a.user_id, null, null, a.job_id, 'applied to ' || j.title, a.created_at
  from public.job_applications a join public.jobs j on j.id = a.job_id
  where a.job_id between :jobs + 1 and :jobs + :jobs_n and a.user_id <> j.user_id
) n
order by created_at
on conflict do nothing;
alter table public.notifications enable trigger user;
commit;
call scale.done('7 notifications');

-- ═════ 8. marketplace: listings, products, enquiries ═════
call scale.start('8 market');
begin;
alter table public.products disable trigger user;
alter table public.enquiries disable trigger user;
insert into public.company_listings (company_id, kind, product, qty, batch, expiry, price, off, reg_status, markets, deal_kind, active, created_at)
select :companies + 1 + (i % :companies_n), case when i % 2 = 0 then 'surplus' else 'dossier' end,
       (array['Paracetamol 500 mg tablets','Amoxicillin 250 mg/5 ml','Metformin 850 mg','Omeprazole 20 mg capsules','Atorvastatin 20 mg'])[1 + i % 5] || ' lot ' || i,
       (100 + i % 900) || ' kg', 'B' || i, '2027-' || lpad((1 + i % 12)::text, 2, '0'), 'USD ' || (5 + i % 40) || '/kg', (i % 60)::int,
       'Registered', 'Egypt, KSA', 'licence', i % 10 <> 0, now() - make_interval(days => (scale.h('lc', i, 365))::int)
from generate_series(1, greatest(:scale_users / 5, 1)) i;
insert into public.products (user_id, name, category, type, price, unit, moq, description, active, created_at, lead_time, docs)
select scale.u(1 + (i * 13) % :scale_users),
       (array['Metformin HCl','Paracetamol DC','Amoxicillin trihydrate','Ibuprofen 50','Omeprazole pellets 8.5%'])[1 + i % 5] || ' lot ' || i,
       (array['api','finished','cmo','registration','equipment','service','other'])[1 + i % 7], case when i % 5 = 0 then 'demand' else 'supply' end,
       '$' || (3 + i % 20) || '.80', 'kg', '100 kg', 'GMP grade, DMF and CoA available, shipment within 3 weeks.', i % 10 <> 0,
       now() - make_interval(days => (scale.h('pr', i, 365))::int), '3 weeks', array['CoA','DMF']
from generate_series(1, greatest(:scale_users / 5, 1)) i;
insert into public.enquiries (user_id, type, category, country, title, body, status, created_at)
select scale.u(1 + (i * 17) % :scale_users), 'demand', (array['api','finished','cmo','registration','service','equipment','other'])[1 + i % 7], 'EG',
       'Need ' || (array['Ciprofloxacin','Azithromycin','Vitamin D3','Gelatin capsules','Blister foil'])[1 + i % 5] || ' — ' || i,
       'Looking for 2 MT per month, GMP certified supplier, delivery to 6th of October.', case when i % 10 = 0 then 'closed' else 'active' end,
       now() - make_interval(days => (scale.h('ec', i, 365))::int)
from generate_series(1, greatest(:scale_users / 10, 1)) i;
alter table public.products enable trigger user;
alter table public.enquiries enable trigger user;
commit;
call scale.done('8 market');

-- ═════ 9. deals: 20k with 60k events and group members ═════
call scale.start('9 deals');
begin;
select greatest(:scale_users / 5, 1) as deals_n \gset
select scale.reserve('deals', :deals_n) as deals \gset
insert into scale.kv values ('deals_n', :deals_n);
create temp table scale_deal on commit drop as
select i, ty,
       case when ty = 'job' then null::bigint else fc end fc,
       case when tc = fc then 1 + tc % :companies_n else tc end tc
from (select i, (array['quote','service','surplus','questionnaire','dossier','job','group'])[1 + i % 7] ty,
             case when i <= 100 then 1 else 1 + scale.h('dfc', i, :companies_n) end fc,
             case when i > 100 and i <= 200 then 1 else 1 + scale.h('dtc', i, :companies_n) end tc
      from generate_series(1, :deals_n) i) s;
-- from_user: the member who sent it (the owner of the sending company, or a candidate for a job)
insert into public.deals (id, type, title, from_company_id, from_user, to_company_id, lines, status, ontime, group_key, offer, offer_at, created_at, updated_at)
overriding system value
select :deals + d.i, d.ty, initcap(d.ty) || ' request #' || d.i,
       case when d.fc is null then null else :companies + d.fc end,
       case when d.ty = 'job' then scale.u(1 + scale.h('dju', d.i, :scale_users)) else coalesce(fo.owner_id, scale.u(1 + d.fc % :scale_users)) end,
       :companies + d.tc,
       jsonb_build_object('product', 'Metformin HCl', 'qty', 100 + d.i % 900, 'unit', 'kg', 'price', 'USD 5.8'),
       (array['sent','quoted','accepted','delivered','closed','declined'])[1 + d.i % 6], case when d.i % 6 = 3 then d.i % 5 <> 0 end,
       case when d.ty = 'group' then 'G' || d.i end,
       case when d.i % 6 >= 1 then jsonb_build_object('price', 'USD 5.5', 'validity', '14 days') end,
       case when d.i % 6 >= 1 then now() - interval '10 days' end,
       now() - make_interval(days => (scale.h('dc', d.i, 365))::int) - interval '1 day', now() - make_interval(hours => (scale.h('du', d.i, 24 * 120))::int)
from scale_deal d left join public.companies fo on fo.id = :companies + d.fc;
insert into public.deal_events (deal_id, side, action, note, data, actor, created_at)
select d.id, (array['from','to','from'])[k], (array['sent','quote','accept'])[k], (array['Request sent','Quotation attached','Accepted — PO follows'])[k],
       '{}'::jsonb, case when k = 2 then null else d.from_user end, d.created_at + make_interval(hours => k)
from public.deals d, generate_series(1, 3) k
where d.id between :deals + 1 and :deals + :deals_n;
insert into public.deal_members (deal_id, company_id, qty)
select d.id, :companies + 1 + scale.h('dm', d.id * 10 + k, :companies_n), 100 * k
from public.deals d, generate_series(1, 3) k
where d.id between :deals + 1 and :deals + :deals_n and d.type = 'group'
on conflict do nothing;
commit;
call scale.done('9 deals');

-- ═════ 10. groups: 2k groups, ~200k memberships ═════
call scale.start('10 groups');
begin;
alter table public.groups disable trigger user;
alter table public.group_members disable trigger user;
select greatest(:scale_users / 50, 1) as groups_n \gset
select scale.reserve('groups', :groups_n) as groups \gset
insert into scale.kv values ('groups_n', :groups_n);
insert into public.groups (id, name, description, emoji, type, topic, member_count, created_by, created_at)
select :groups + g, (array['Regulatory Affairs Egypt','QA/QC Professionals','Pharma Exporters','Medical Reps Network','CMO & Toll Manufacturing','Pharmacovigilance MENA'])[1 + g % 6] || ' ' || g,
       'A place to share guidelines, jobs and opportunities.', (array['👥','📋','🧪','🌍','🏭','💊'])[1 + g % 6], case when g % 10 = 0 then 'private' else 'public' end,
       case when g % 15 = 0 then 'DEAL ROOM' else 'DISCUSS' end, 0, scale.u(1 + (g * 53) % :scale_users), now() - make_interval(days => (scale.h('gc', g, 700))::int)
from generate_series(1, :groups_n) g;
insert into public.group_members (group_id, user_id, role, joined_at)
select :groups + g, scale.u(1 + (g * 53) % :scale_users), 'admin', now() - interval '700 days' from generate_series(1, :groups_n) g
on conflict do nothing;
insert into public.group_members (group_id, user_id, role, joined_at)
select :groups + 1 + scale.h('gg', i, :groups_n), scale.u(1 + scale.h('gu', i, :scale_users)), 'member', now() - make_interval(days => (i % 600)::int)
from generate_series(1, :scale_users * 2) i
on conflict do nothing;
insert into public.group_members (group_id, user_id, role) select :groups + g, scale.u(1), 'member' from generate_series(1, least(50, :groups_n)) g on conflict do nothing;
update public.groups g set member_count = m.k
from (select group_id, count(*) k from public.group_members where group_id between :groups + 1 and :groups + :groups_n group by 1) m
where g.id = m.group_id;
alter table public.groups enable trigger user;
alter table public.group_members enable trigger user;
commit;
call scale.done('10 groups');

-- ═════ 11. trust layer: reviews, references, lists ═════
call scale.start('11 trust');
begin;
alter table public.job_reviews disable trigger user;
alter table public.work_references disable trigger user;
alter table public.job_lists disable trigger user;
-- reviews concentrate on the first 2 % of members (the employers and candidates people actually look at)
insert into public.job_reviews (reviewer, reviewee, reviewee_role, c1, c2, c3, c4, body, anonymous, created_at)
select r, e, role, 1 + i % 5, 1 + (i / 2) % 5, 1 + (i / 3) % 5, 1 + (i / 4) % 5,
       'Professional and transparent about salary; interviews started on time and feedback came within a week.',
       role = 'employer' and i % 7 = 0, now() - make_interval(days => (i % 365)::int)
from (select i, scale.u(1 + scale.h('rr', i, :scale_users)) r, scale.u(1 + scale.h('re', i, greatest(:scale_users / 50, 2))) e,
             case when i % 2 = 0 then 'employer' else 'candidate' end role
      from generate_series(1, :scale_users / 5) i) s
where r <> e
on conflict do nothing;
insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, body, status, created_at)
select a, c, 'honor', 'Regulatory Affairs Specialist', date '2021-01-01', date '2023-06-01',
       'Worked with us for two and a half years and delivered every dossier on time, with excellent documentation.', 'published', now() - make_interval(days => (i % 365)::int)
from (select i, scale.u(1 + (i * 3) % :scale_users) a, scale.u(1 + (i * 7 + 1) % greatest(:scale_users / 50, 2)) c from generate_series(1, :scale_users / 20) i) s
where a <> c;
insert into public.job_lists (owner, target, side, list, reason, until)
select o, t, side, list, case when list = 'black' and side = 'employer' then 'No-show at interview' end,
       case when list = 'black' and side = 'employer' then current_date + 365 end
from (select scale.u(1 + (i * 3) % :scale_users) o, scale.u(1 + (i * 11 + 5) % :scale_users) t,
             case when i % 2 = 0 then 'employer' else 'candidate' end side, case when i % 3 = 0 then 'black' else 'white' end list
      from generate_series(1, :scale_users / 10) i) s
where o <> t
on conflict do nothing;
alter table public.job_reviews enable trigger user;
alter table public.work_references enable trigger user;
alter table public.job_lists enable trigger user;
commit;
call scale.done('11 trust');

-- ═════ 12. statistics ═════
call scale.start('12 analyze');
set client_min_messages = warning;
analyze auth.users;
analyze public.profiles; analyze public.companies; analyze public.company_members; analyze public.company_products; analyze public.company_sites;
analyze public.site_certificates; analyze public.company_followers; analyze public.connections; analyze public.posts; analyze public.post_media;
analyze public.reactions; analyze public.comments; analyze public.saved_posts; analyze public.messages; analyze public.conversation_heads;
analyze public.jobs; analyze public.job_applications; analyze public.saved_jobs; analyze public.notifications; analyze public.company_listings;
analyze public.products; analyze public.enquiries; analyze public.deals; analyze public.deal_events; analyze public.deal_members;
analyze public.groups; analyze public.group_members; analyze public.job_reviews; analyze public.work_references; analyze public.job_lists;
set client_min_messages = notice;
call scale.done('12 analyze');

insert into scale.kv values ('done', extract(epoch from now())::bigint);
\echo ''
\echo '═════ scale seed: summary ═════'
select section, round(extract(epoch from finished - started)::numeric, 1) as seconds from scale.log order by started;
select round(extract(epoch from max(finished) - min(started))::numeric, 1) as total_seconds from scale.log;
select 'members' what, count(*) n from auth.users where email like '%@scale.test'
union all select 'companies', count(*) from public.companies where email like '%@scale.test'
union all select 'connections', count(*) from public.connections c where c.requester in (select scale.u(n) from generate_series(1, :scale_users) n)
union all select 'posts', :posts_n
union all select 'reactions', count(*) from public.reactions where post_id between :posts + 1 and :posts + :posts_n
union all select 'messages', :messages_n
union all select 'notifications', count(*) from public.notifications n where n.user_id in (select scale.u(k) from generate_series(1, :scale_users) k)
union all select 'deals', :deals_n;
\echo 'sign in as member1@scale.test … member' :scale_users '@scale.test with Scale-pass-2026'
