-- ═══════════════════════════════════════════════════════════════════════
-- DRUGBOX — 0001 initial schema (fresh project)
-- Consolidates the verified schema: core + demo features + jobs trust + company hub.
-- Later migrations (0002+) add deals, company listings, personalization, admin.
-- ═══════════════════════════════════════════════════════════════════════

-- ─────────────── from 001_complete_schema.sql ───────────────
-- ══════════════════════════════════════════════════════════════
-- DRUGBOX — Complete Database Schema
-- نسخ هذا الملف كله في Supabase SQL Editor ثم اضغط Run
-- ══════════════════════════════════════════════════════════════

-- ── 1. PROFILES (المستخدمين) ─────────────────────────────────
create table public.profiles (
  id           uuid primary key references auth.users on delete cascade,
  name         text not null,
  headline     text,
  company      text,
  country      char(2) default 'EG',
  bio          text,
  avatar_url   text,
  cover_url    text,
  website      text,
  phone        text,
  certs        text,
  role         text default 'user' check (role in ('user','admin','moderator')),
  verified     boolean default false,
  account_type text default 'professional' check (account_type in ('professional','company','admin')),
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

-- ── 2. POSTS (البوستات) ──────────────────────────────────────
create table public.posts (
  id           bigserial primary key,
  user_id      uuid references public.profiles on delete cascade not null,
  body         text not null check (length(body) between 1 and 5000),
  category     text default 'general' check (category in ('general','regulatory','market','innovation','job')),
  like_count   int default 0,
  comment_count int default 0,
  pinned       boolean default false,
  created_at   timestamptz default now()
);

-- ── 3. POST MEDIA (صور وملفات البوستات) ─────────────────────
create table public.post_media (
  id         bigserial primary key,
  post_id    bigint references public.posts on delete cascade,
  url        text not null,
  type       text default 'image' check (type in ('image','file')),
  name       text,
  size       bigint,
  created_at timestamptz default now()
);

-- ── 4. REACTIONS (اللايكات) ──────────────────────────────────
create table public.reactions (
  post_id    bigint references public.posts on delete cascade,
  user_id    uuid references public.profiles on delete cascade,
  kind       text default 'like' check (kind in ('like','love','insightful','celebrate','curious')),
  created_at timestamptz default now(),
  primary key (post_id, user_id)
);

-- ── 5. COMMENTS (التعليقات) ──────────────────────────────────
create table public.comments (
  id         bigserial primary key,
  post_id    bigint references public.posts on delete cascade,
  user_id    uuid references public.profiles on delete cascade not null,
  parent_id  bigint references public.comments,
  body       text not null check (length(body) between 1 and 2000),
  created_at timestamptz default now()
);

-- ── 6. CONNECTIONS (الاتصالات) ───────────────────────────────
create table public.connections (
  id         bigserial primary key,
  requester  uuid references public.profiles on delete cascade not null,
  addressee  uuid references public.profiles on delete cascade not null,
  status     text default 'pending' check (status in ('pending','accepted','rejected')),
  created_at timestamptz default now(),
  unique (requester, addressee),
  check (requester <> addressee)
);

-- ── 7. MESSAGES (الرسايل) ────────────────────────────────────
create table public.messages (
  id          bigserial primary key,
  sender_id   uuid references public.profiles on delete cascade not null,
  receiver_id uuid references public.profiles on delete cascade not null,
  body        text,
  image_url   text,
  read_at     timestamptz,
  created_at  timestamptz default now(),
  check (sender_id <> receiver_id),
  check (body is not null or image_url is not null)
);

-- ── 8. PRODUCTS (المنتجات - Marketplace) ─────────────────────
create table public.products (
  id          bigserial primary key,
  user_id     uuid references public.profiles on delete cascade not null,
  name        text not null,
  category    text check (category in ('api','finished','cmo','registration','equipment','service','other')),
  type        text default 'supply' check (type in ('supply','demand')),
  price       text,
  unit        text,
  moq         text,
  description text,
  emoji       text default '📦',
  tag         text,
  docs        text[],
  urgent      boolean default false,
  active      boolean default true,
  created_at  timestamptz default now()
);

-- ── 9. ENQUIRIES (Market Board - PharmaCompass style) ────────
create table public.enquiries (
  id          text primary key, -- ENQ2601
  user_id     uuid references public.profiles on delete cascade not null,
  type        text not null check (type in ('supply','demand')),
  category    text check (category in ('api','finished','cmo','registration','service','equipment','other')),
  country     text,
  flag        text,
  title       text not null,
  body        text not null,
  docs        text[],
  urgent      boolean default false,
  status      text default 'active' check (status in ('active','closed','pending')),
  reply_count int default 0,
  created_at  timestamptz default now()
);

-- ── 10. COMPANIES (صفحات الشركات) ───────────────────────────
create table public.companies (
  id          bigserial primary key,
  owner_id    uuid references public.profiles on delete cascade not null,
  name        text not null,
  type        text,
  location    text,
  country     char(2) default 'EG',
  bio         text,
  logo_emoji  text default '🏭',
  logo_url    text,
  cover_url   text,
  website     text,
  phone       text,
  founded     int,
  employees   text,
  specialties text[],
  verified    boolean default false,
  follower_count int default 0,
  created_at  timestamptz default now()
);

create table public.company_followers (
  company_id bigint references public.companies on delete cascade,
  user_id    uuid references public.profiles on delete cascade,
  created_at timestamptz default now(),
  primary key (company_id, user_id)
);

-- ── 11. GROUPS (المجموعات) ───────────────────────────────────
create table public.groups (
  id           bigserial primary key,
  name         text not null,
  description  text,
  emoji        text default '👥',
  cover_url    text,
  type         text default 'public' check (type in ('public','private')),
  member_count int default 0,
  created_by   uuid references public.profiles,
  created_at   timestamptz default now()
);

create table public.group_members (
  group_id   bigint references public.groups on delete cascade,
  user_id    uuid references public.profiles on delete cascade,
  role       text default 'member' check (role in ('member','admin')),
  joined_at  timestamptz default now(),
  primary key (group_id, user_id)
);

-- ── 12. JOBS (الوظايف) ──────────────────────────────────────
create table public.jobs (
  id          bigserial primary key,
  user_id     uuid references public.profiles on delete cascade not null,
  title       text not null,
  company     text,
  location    text,
  country     char(2) default 'EG',
  type        text default 'full-time',
  seniority   text,
  description text,
  tags        text[],
  salary      text,
  active      boolean default true,
  created_at  timestamptz default now()
);

-- ── 13. NOTIFICATIONS (الإشعارات) ───────────────────────────
create table public.notifications (
  id          bigserial primary key,
  user_id     uuid references public.profiles on delete cascade not null,
  type        text not null,
  from_user   uuid references public.profiles,
  post_id     bigint references public.posts,
  message     text,
  read        boolean default false,
  created_at  timestamptz default now()
);

-- ── 14. SAVED POSTS (البوستات المحفوظة) ─────────────────────
create table public.saved_posts (
  user_id    uuid references public.profiles on delete cascade,
  post_id    bigint references public.posts on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, post_id)
);

-- ── 15. SETTINGS (إعدادات الموقع - CMS) ─────────────────────
-- هذا الجدول هو قلب الـ Admin Panel
-- كل إعداد في الموقع بيتخزن هنا
create table public.settings (
  key        text primary key,
  value      text,
  type       text default 'text' check (type in ('text','color','font','image','json','boolean','number')),
  label      text,      -- الاسم اللي بيظهر في الـ Admin Panel
  group_name text,      -- التجميع: design, content, ticker, sponsors
  sort_order int default 0
);

-- ── 16. TICKER ITEMS (نصوص الشريط المتحرك) ──────────────────
create table public.ticker_items (
  id         bigserial primary key,
  label      text not null,  -- Supply / Demand / CMO
  text       text not null,  -- Metformin HCl GMP $5.80/kg
  active     boolean default true,
  sort_order int default 0,
  created_at timestamptz default now()
);

-- ── 17. SPONSORED SUPPLIERS (الممولين في Market Board) ───────
create table public.sponsored_suppliers (
  id         bigserial primary key,
  company_id bigint references public.companies,
  name       text not null,
  banner     text,
  description text,
  color      text default '#1a56db',
  logo_emoji text default '🏭',
  active     boolean default true,
  sort_order int default 0,
  created_at timestamptz default now()
);

-- ══════════════════════════════════════════════════════════════
-- INDEXES (الفهارس — بتخلي الموقع سريع)
-- ══════════════════════════════════════════════════════════════

create index idx_posts_user      on public.posts(user_id);
create index idx_posts_created   on public.posts(created_at desc);
create index idx_posts_category  on public.posts(category);
create index idx_posts_pinned    on public.posts(pinned) where pinned = true;
create index idx_reactions_post  on public.reactions(post_id);
create index idx_comments_post   on public.comments(post_id);
create index idx_conn_requester  on public.connections(requester);
create index idx_conn_addressee  on public.connections(addressee);
create index idx_conn_status     on public.connections(status);
create index idx_msgs_sender     on public.messages(sender_id);
create index idx_msgs_receiver   on public.messages(receiver_id);
create index idx_msgs_created    on public.messages(created_at desc);
create index idx_notifs_user     on public.notifications(user_id, read);
create index idx_products_cat    on public.products(category, active);
create index idx_enquiries_cat   on public.enquiries(category, status);
create index idx_enquiries_type  on public.enquiries(type);
create index idx_settings_group  on public.settings(group_name);

-- Full Text Search
create index idx_posts_fts on public.posts
  using gin(to_tsvector('english', body));
create index idx_products_fts on public.products
  using gin(to_tsvector('english', name || ' ' || coalesce(description,'')));

-- ══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (الأمان — مين يشوف إيه)
-- ══════════════════════════════════════════════════════════════

alter table public.profiles           enable row level security;
alter table public.posts              enable row level security;
alter table public.post_media         enable row level security;
alter table public.reactions          enable row level security;
alter table public.comments           enable row level security;
alter table public.connections        enable row level security;
alter table public.messages           enable row level security;
alter table public.products           enable row level security;
alter table public.enquiries          enable row level security;
alter table public.companies          enable row level security;
alter table public.company_followers  enable row level security;
alter table public.groups             enable row level security;
alter table public.group_members      enable row level security;
alter table public.jobs               enable row level security;
alter table public.notifications      enable row level security;
alter table public.saved_posts        enable row level security;
alter table public.settings           enable row level security;
alter table public.ticker_items       enable row level security;
alter table public.sponsored_suppliers enable row level security;

-- Profiles
create policy "profiles: everyone can read"
  on public.profiles for select using (true);
create policy "profiles: own update"
  on public.profiles for update using ((select auth.uid()) = id);

-- Posts
create policy "posts: everyone can read"
  on public.posts for select using (true);
create policy "posts: own insert"
  on public.posts for insert with check ((select auth.uid()) = user_id);
create policy "posts: own delete"
  on public.posts for delete using ((select auth.uid()) = user_id);
create policy "posts: admin can delete"
  on public.posts for delete using (
    exists (select 1 from public.profiles where id = (select auth.uid()) and role = 'admin')
  );

-- Reactions
create policy "reactions: everyone can read"
  on public.reactions for select using (true);
create policy "reactions: own manage"
  on public.reactions for all using ((select auth.uid()) = user_id);

-- Comments
create policy "comments: everyone can read"
  on public.comments for select using (true);
create policy "comments: own insert"
  on public.comments for insert with check ((select auth.uid()) = user_id);
create policy "comments: own delete"
  on public.comments for delete using ((select auth.uid()) = user_id);

-- Messages (الرسايل — بس الطرفين اللي يشوفوها)
create policy "messages: own read"
  on public.messages for select
  using ((select auth.uid()) = sender_id or (select auth.uid()) = receiver_id);
create policy "messages: own send"
  on public.messages for insert
  with check ((select auth.uid()) = sender_id);

-- Products
create policy "products: everyone can read"
  on public.products for select using (active = true);
create policy "products: own manage"
  on public.products for all using ((select auth.uid()) = user_id);

-- Enquiries
create policy "enquiries: everyone can read"
  on public.enquiries for select using (true);
create policy "enquiries: own manage"
  on public.enquiries for all using ((select auth.uid()) = user_id);

-- Companies
create policy "companies: everyone can read"
  on public.companies for select using (true);
create policy "companies: own manage"
  on public.companies for all using ((select auth.uid()) = owner_id);

-- Groups
create policy "groups: public read"
  on public.groups for select using (type = 'public');
create policy "groups: own manage"
  on public.groups for all using ((select auth.uid()) = created_by);

-- Jobs
create policy "jobs: everyone can read"
  on public.jobs for select using (active = true);
create policy "jobs: own manage"
  on public.jobs for all using ((select auth.uid()) = user_id);

-- Notifications
create policy "notifications: own"
  on public.notifications for all using ((select auth.uid()) = user_id);

-- Saved posts
create policy "saved: own"
  on public.saved_posts for all using ((select auth.uid()) = user_id);

-- Settings (الكل يقرأ، Admin بس يعدل)
create policy "settings: everyone can read"
  on public.settings for select using (true);
create policy "settings: admin write"
  on public.settings for all using (
    exists (select 1 from public.profiles where id = (select auth.uid()) and role = 'admin')
  );

-- Ticker & Sponsors (الكل يقرأ، Admin بس يعدل)
create policy "ticker: everyone can read"
  on public.ticker_items for select using (active = true);
create policy "ticker: admin write"
  on public.ticker_items for all using (
    exists (select 1 from public.profiles where id = (select auth.uid()) and role = 'admin')
  );
create policy "sponsors: everyone can read"
  on public.sponsored_suppliers for select using (active = true);
create policy "sponsors: admin write"
  on public.sponsored_suppliers for all using (
    exists (select 1 from public.profiles where id = (select auth.uid()) and role = 'admin')
  );

-- ══════════════════════════════════════════════════════════════
-- TRIGGERS (أحداث تلقائية)
-- ══════════════════════════════════════════════════════════════

-- إنشاء profile تلقائياً لما حد يسجل
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'name', split_part(new.email,'@',1))
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- تحديث like_count تلقائياً
create or replace function public.update_like_count()
returns trigger language plpgsql as $$
begin
  if TG_OP = 'INSERT' then
    update public.posts set like_count = like_count + 1 where id = NEW.post_id;
  elsif TG_OP = 'DELETE' then
    update public.posts set like_count = greatest(0, like_count - 1) where id = OLD.post_id;
  end if;
  return null;
end;
$$;

create trigger trg_like_count
  after insert or delete on public.reactions
  for each row execute procedure public.update_like_count();

-- تحديث comment_count تلقائياً
create or replace function public.update_comment_count()
returns trigger language plpgsql as $$
begin
  if TG_OP = 'INSERT' then
    update public.posts set comment_count = comment_count + 1 where id = NEW.post_id;
  elsif TG_OP = 'DELETE' then
    update public.posts set comment_count = greatest(0, comment_count - 1) where id = OLD.post_id;
  end if;
  return null;
end;
$$;

create trigger trg_comment_count
  after insert or delete on public.comments
  for each row execute procedure public.update_comment_count();

-- تحديث follower_count للشركات
create or replace function public.update_follower_count()
returns trigger language plpgsql as $$
begin
  if TG_OP = 'INSERT' then
    update public.companies set follower_count = follower_count + 1 where id = NEW.company_id;
  elsif TG_OP = 'DELETE' then
    update public.companies set follower_count = greatest(0, follower_count - 1) where id = OLD.company_id;
  end if;
  return null;
end;
$$;

create trigger trg_follower_count
  after insert or delete on public.company_followers
  for each row execute procedure public.update_follower_count();

-- ══════════════════════════════════════════════════════════════
-- SEED DATA (بيانات أولية)
-- ══════════════════════════════════════════════════════════════

-- الإعدادات الافتراضية للـ CMS
insert into public.settings (key, value, type, label, group_name, sort_order) values
  -- التصميم
  ('color_primary',    '#1a56db', 'color',  'اللون الرئيسي',     'design', 1),
  ('color_secondary',  '#0a1f4d', 'color',  'اللون الثانوي',     'design', 2),
  ('color_accent',     '#f59e0b', 'color',  'لون التمييز',       'design', 3),
  ('color_bg',         '#f0f4fb', 'color',  'لون الخلفية',       'design', 4),
  ('color_sidebar',    '#ffffff', 'color',  'لون الـ Sidebar',   'design', 5),
  ('color_ticker_bg',  '#0a1f4d', 'color',  'خلفية الـ Ticker',  'design', 6),
  ('color_text',       '#1c1e21', 'color',  'لون النص',          'design', 7),
  -- الخط
  ('font_family',      'Inter',   'font',   'نوع الخط',          'design', 8),
  ('font_size_base',   '14',      'number', 'حجم الخط (px)',     'design', 9),
  -- الموقع
  ('site_name',        'Drugbox', 'text',   'اسم الموقع',        'content', 1),
  ('site_tagline',     'The B2B Pharma Professional Network', 'text', 'وصف الموقع', 'content', 2),
  ('site_logo_url',    '/logo.png','image', 'الـ Logo',          'content', 3),
  -- الأيقونات
  ('icon_feed',        '🏠',      'text',   'أيقونة Home',       'icons', 1),
  ('icon_market',      '🛒',      'text',   'أيقونة Market',     'icons', 2),
  ('icon_messages',    '💬',      'text',   'أيقونة Messages',   'icons', 3),
  ('icon_network',     '👥',      'text',   'أيقونة Network',    'icons', 4),
  ('icon_notifications','🔔',     'text',   'أيقونة Alerts',     'icons', 5),
  ('icon_profile',     '👤',      'text',   'أيقونة Profile',    'icons', 6),
  ('icon_groups',      '👥',      'text',   'أيقونة Groups',     'icons', 7),
  ('icon_jobs',        '💼',      'text',   'أيقونة Jobs',       'icons', 8),
  ('icon_companies',   '🏭',      'text',   'أيقونة Companies',  'icons', 9),
  ('icon_training',    '🎓',      'text',   'أيقونة Training',   'icons', 10),
  ('icon_saved',       '🔖',      'text',   'أيقونة Saved',      'icons', 11);

-- نصوص الـ Ticker
insert into public.ticker_items (label, text, sort_order) values
  ('Supply',      'Metformin HCl GMP $5.80/kg',                1),
  ('Demand',      'Ciprofloxacin HCl 2MT/month',               2),
  ('License',     'EDA Cosmetic Registration For Sale',         3),
  ('CMO',         'WHO-GMP Tablets — Quadra Pharm',            4),
  ('Equipment',   'Fette 1200 Tablet Press $45K',              5),
  ('Job',         'Senior RA Specialist — Giza, Egypt',        6),
  ('Supply',      'Hyaluronic Acid 99% Cosmetic Grade',        7),
  ('Deal closed', 'Amoxicillin 500kg ✓',                      8);

-- ══════════════════════════════════════════════════════════════
-- STORAGE BUCKETS (شغّل في Supabase Dashboard → Storage)
-- ══════════════════════════════════════════════════════════════
-- insert into storage.buckets (id, name, public) values
--   ('avatars',     'avatars',     true),
--   ('post-images', 'post-images', true),
--   ('documents',   'documents',   false);
--
-- create policy "avatars public read"
--   on storage.objects for select using (bucket_id = 'avatars');
-- create policy "avatars own upload"
--   on storage.objects for insert with check (bucket_id = 'avatars' and auth.uid()::text = (storage.foldername(name))[1]);
-- create policy "post-images public read"
--   on storage.objects for select using (bucket_id = 'post-images');
-- create policy "post-images own upload"
--   on storage.objects for insert with check (bucket_id = 'post-images' and auth.uid() is not null);
-- create policy "documents own access"
--   on storage.objects for all using (bucket_id = 'documents' and auth.uid()::text = (storage.foldername(name))[1]);

-- ─────────────── from 002_demo_features.sql ───────────────
-- ══════════════════════════════════════════════════════════════
-- DRUGBOX — 002 Demo features (run AFTER 001_complete_schema.sql)
-- آمن للتشغيل أكتر من مرة — مابيمسحش أي بيانات
-- انسخ الملف كله في Supabase → SQL Editor → Run
-- ══════════════════════════════════════════════════════════════

-- ── 1. PROFILES: LinkedIn-style profile ──────────────────────
alter table public.profiles add column if not exists location        text;
alter table public.profiles add column if not exists experience      jsonb   default '[]'::jsonb;  -- [{title,company,period,years,desc}]
alter table public.profiles add column if not exists education       jsonb   default '[]'::jsonb;  -- [{degree,school,year}]
alter table public.profiles add column if not exists certifications  jsonb   default '[]'::jsonb;  -- [{name,issuer,date,expiry}]
alter table public.profiles add column if not exists skills          text[]  default '{}';
alter table public.profiles add column if not exists languages       text[]  default '{}';
alter table public.profiles add column if not exists open_to_work    boolean default false;
alter table public.profiles add column if not exists hiring          boolean default false;
alter table public.profiles add column if not exists profile_views   int     default 0;
alter table public.profiles add column if not exists followers_count int     default 0;

-- ── 2. POSTS: views + reposts; 6 reaction kinds ─────────────
alter table public.posts add column if not exists view_count  int default 0;
alter table public.posts add column if not exists share_count int default 0;

alter table public.reactions drop constraint if exists reactions_kind_check;
alter table public.reactions add constraint reactions_kind_check
  check (kind in ('like','love','support','insightful','celebrate','appreciation','curious'));

-- ── 3. JOBS: salary / remote / deadline / benefits / applicants
alter table public.jobs add column if not exists remote          boolean default false;
alter table public.jobs add column if not exists deadline        date;
alter table public.jobs add column if not exists benefits        text[] default '{}';
alter table public.jobs add column if not exists requirements    text[] default '{}';
alter table public.jobs add column if not exists applicant_count int    default 0;

create table if not exists public.job_applications (
  job_id     bigint references public.jobs on delete cascade,
  user_id    uuid   references public.profiles on delete cascade,
  note       text,
  status     text default 'submitted' check (status in ('submitted','viewed','shortlisted','rejected')),
  created_at timestamptz default now(),
  primary key (job_id, user_id)
);
create table if not exists public.saved_jobs (
  user_id    uuid   references public.profiles on delete cascade,
  job_id     bigint references public.jobs on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, job_id)
);

-- ── 4. PRODUCTS: B2B trade details ───────────────────────────
alter table public.products add column if not exists price_tiers      jsonb   default '[]'::jsonb; -- [{qty,price}]
alter table public.products add column if not exists specs            jsonb   default '{}'::jsonb; -- {"Purity":"≥99%"}
alter table public.products add column if not exists incoterms        text;
alter table public.products add column if not exists payment_terms    text;
alter table public.products add column if not exists lead_time        text;
alter table public.products add column if not exists stock            text;
alter table public.products add column if not exists sample_available boolean default false;
-- (certifications/documents use the existing products.docs text[] column)

-- ── 5. INDEXES ───────────────────────────────────────────────
create index if not exists idx_job_apps_user   on public.job_applications(user_id);
create index if not exists idx_saved_jobs_user on public.saved_jobs(user_id);
create index if not exists idx_jobs_active     on public.jobs(active, created_at desc);
create index if not exists idx_reactions_kind  on public.reactions(post_id, kind);
create index if not exists idx_notifs_created  on public.notifications(user_id, created_at desc);

-- ── 6. RLS ───────────────────────────────────────────────────
alter table public.job_applications enable row level security;
alter table public.saved_jobs       enable row level security;

drop policy if exists "job_apps: applicant manages own" on public.job_applications;
create policy "job_apps: applicant manages own" on public.job_applications
  for all using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

drop policy if exists "job_apps: poster reads" on public.job_applications;
create policy "job_apps: poster reads" on public.job_applications
  for select using (exists (select 1 from public.jobs j where j.id = job_id and j.user_id = (select auth.uid())));

drop policy if exists "saved_jobs: own" on public.saved_jobs;
create policy "saved_jobs: own" on public.saved_jobs
  for all using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

-- Allow users to change their reaction kind (update) — "own manage" already covers it.

-- ── 7. COUNTERS via SECURITY DEFINER functions (no direct writes needed)
create or replace function public.increment_post_views(post_ids bigint[])
returns void language sql security definer set search_path = public as $$
  update public.posts set view_count = view_count + 1 where id = any(post_ids);
$$;

create or replace function public.increment_post_share(p_id bigint)
returns int language sql security definer set search_path = public as $$
  update public.posts set share_count = share_count + 1 where id = p_id returning share_count;
$$;

create or replace function public.increment_profile_view(target uuid)
returns void language sql security definer set search_path = public as $$
  update public.profiles set profile_views = profile_views + 1
  where id = target and target <> auth.uid();
$$;

grant execute on function public.increment_post_views(bigint[])  to authenticated;
grant execute on function public.increment_post_share(bigint)     to authenticated;
grant execute on function public.increment_profile_view(uuid)     to authenticated;

-- applicant_count trigger
create or replace function public.update_applicant_count()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if TG_OP = 'INSERT' then
    update public.jobs set applicant_count = applicant_count + 1 where id = NEW.job_id;
  elsif TG_OP = 'DELETE' then
    update public.jobs set applicant_count = greatest(0, applicant_count - 1) where id = OLD.job_id;
  end if;
  return null;
end; $$;
drop trigger if exists trg_applicant_count on public.job_applications;
create trigger trg_applicant_count after insert or delete on public.job_applications
  for each row execute procedure public.update_applicant_count();

-- ── 8. NOTIFICATIONS via triggers ────────────────────────────
-- Fixes a bug: RLS on notifications only allows inserting rows for yourself,
-- so client-side inserts for other users were silently rejected.
create or replace function public.notify_reaction()
returns trigger language plpgsql security definer set search_path = public as $$
declare owner uuid;
begin
  select user_id into owner from public.posts where id = NEW.post_id;
  if owner is not null and owner <> NEW.user_id then
    insert into public.notifications(user_id, type, from_user, post_id)
    values (owner, 'like', NEW.user_id, NEW.post_id);
  end if;
  return null;
end; $$;
drop trigger if exists trg_notify_reaction on public.reactions;
create trigger trg_notify_reaction after insert on public.reactions
  for each row execute procedure public.notify_reaction();

create or replace function public.notify_comment()
returns trigger language plpgsql security definer set search_path = public as $$
declare owner uuid;
begin
  select user_id into owner from public.posts where id = NEW.post_id;
  if owner is not null and owner <> NEW.user_id then
    insert into public.notifications(user_id, type, from_user, post_id, message)
    values (owner, 'comment', NEW.user_id, NEW.post_id, left(NEW.body, 140));
  end if;
  return null;
end; $$;
drop trigger if exists trg_notify_comment on public.comments;
create trigger trg_notify_comment after insert on public.comments
  for each row execute procedure public.notify_comment();

create or replace function public.notify_connection()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if TG_OP = 'INSERT' and NEW.status = 'pending' then
    insert into public.notifications(user_id, type, from_user)
    values (NEW.addressee, 'connection_request', NEW.requester);
  elsif TG_OP = 'UPDATE' and NEW.status = 'accepted' and OLD.status <> 'accepted' then
    insert into public.notifications(user_id, type, from_user)
    values (NEW.requester, 'connection_accepted', NEW.addressee);
  end if;
  return null;
end; $$;
drop trigger if exists trg_notify_connection on public.connections;
create trigger trg_notify_connection after insert or update on public.connections
  for each row execute procedure public.notify_connection();

create or replace function public.notify_job_application()
returns trigger language plpgsql security definer set search_path = public as $$
declare poster uuid;
begin
  select user_id into poster from public.jobs where id = NEW.job_id;
  if poster is not null and poster <> NEW.user_id then
    insert into public.notifications(user_id, type, from_user, message)
    select poster, 'job_application', NEW.user_id, 'applied to ' || title from public.jobs where id = NEW.job_id;
  end if;
  return null;
end; $$;
drop trigger if exists trg_notify_job_application on public.job_applications;
create trigger trg_notify_job_application after insert on public.job_applications
  for each row execute procedure public.notify_job_application();

-- Connections: the addressee must be able to accept/reject (was missing)
alter table public.connections enable row level security;
drop policy if exists "connections: parties read" on public.connections;
create policy "connections: parties read" on public.connections
  for select using ((select auth.uid()) in (requester, addressee));
drop policy if exists "connections: request" on public.connections;
create policy "connections: request" on public.connections
  for insert with check ((select auth.uid()) = requester);
drop policy if exists "connections: addressee responds" on public.connections;
create policy "connections: addressee responds" on public.connections
  for update using ((select auth.uid()) = addressee);
drop policy if exists "connections: parties delete" on public.connections;
create policy "connections: parties delete" on public.connections
  for delete using ((select auth.uid()) in (requester, addressee));


-- ── 9. FIX: counters stayed at 0 ─────────────────────────────
-- The 001 counter triggers ran with the caller's rights, and RLS on posts /
-- companies has no UPDATE policy for other users, so the counts never moved.
-- Re-create them as SECURITY DEFINER (same logic).
create or replace function public.update_like_count()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if TG_OP = 'INSERT' then
    update public.posts set like_count = like_count + 1 where id = NEW.post_id;
  elsif TG_OP = 'DELETE' then
    update public.posts set like_count = greatest(0, like_count - 1) where id = OLD.post_id;
  end if;
  return null;
end; $$;

create or replace function public.update_comment_count()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if TG_OP = 'INSERT' then
    update public.posts set comment_count = comment_count + 1 where id = NEW.post_id;
  elsif TG_OP = 'DELETE' then
    update public.posts set comment_count = greatest(0, comment_count - 1) where id = OLD.post_id;
  end if;
  return null;
end; $$;

create or replace function public.update_follower_count()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if TG_OP = 'INSERT' then
    update public.companies set follower_count = follower_count + 1 where id = NEW.company_id;
  elsif TG_OP = 'DELETE' then
    update public.companies set follower_count = greatest(0, follower_count - 1) where id = OLD.company_id;
  end if;
  return null;
end; $$;

-- one-time resync of existing counts
update public.posts p set
  like_count    = (select count(*) from public.reactions r where r.post_id = p.id),
  comment_count = (select count(*) from public.comments  c where c.post_id = p.id);

-- Upcoming events for the feed sidebar (editable from settings)
insert into public.settings (key, value, type, label, group_name, sort_order) values
  ('feed_events', '[{"name":"CPhI Middle East","place":"Riyadh","month":"Dec"},{"name":"Africa Health ExCon","place":"Cairo","month":"Jun"},{"name":"Arab Health","place":"Dubai","month":"Jan"}]',
   'json', 'فعاليات الفيد', 'content', 10)
on conflict (key) do nothing;

-- ─────────────── from 003_jobs_trust.sql ───────────────
-- ══════════════════════════════════════════════════════════════
-- DRUGBOX — 003 Jobs trust layer   (run AFTER 001 and 002)
-- Public reviews made by users + ranking · Honor / Warning work references
-- Private whitelist / blacklist for employers and candidates
-- Every rule below is enforced by the database, not only by the UI.
-- Safe to run more than once.
-- ══════════════════════════════════════════════════════════════

-- ── 0. candidate profile fields used by the Jobs page ─────────
alter table public.profiles add column if not exists years_experience int check (years_experience between 0 and 60);
alter table public.profiles add column if not exists desired_role     text;
alter table public.profiles add column if not exists desired_type     text default 'Full-time';
alter table public.profiles add column if not exists remote_ok        boolean default false;
alter table public.profiles add column if not exists available_since  timestamptz;

alter table public.job_applications drop constraint if exists job_applications_status_check;
alter table public.job_applications add constraint job_applications_status_check
  check (status in ('submitted','viewed','shortlisted','interviewed','hired','rejected','no_show'));

-- helper: has the user had a real interaction with the other party?
-- employer ↔ candidate: the candidate applied to one of the employer's jobs, or they exchanged messages
create or replace function public.jobs_interacted(a uuid, b uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.job_applications ja join public.jobs j on j.id = ja.job_id
                 where (ja.user_id = a and j.user_id = b) or (ja.user_id = b and j.user_id = a))
      or exists (select 1 from public.messages m
                 where (m.sender_id = a and m.receiver_id = b) or (m.sender_id = b and m.receiver_id = a));
$$;

-- ── 1. PUBLIC REVIEWS (made by users, visible to everyone) ────
create table if not exists public.job_reviews (
  id            bigserial primary key,
  reviewer      uuid not null references public.profiles on delete cascade,
  reviewee      uuid not null references public.profiles on delete cascade,
  reviewee_role text not null check (reviewee_role in ('employer','candidate')),
  c1 smallint not null check (c1 between 1 and 5),
  c2 smallint not null check (c2 between 1 and 5),
  c3 smallint not null check (c3 between 1 and 5),
  c4 smallint not null check (c4 between 1 and 5),
  body          text not null check (length(trim(body)) between 20 and 3000),
  anonymous     boolean not null default false,
  hidden        boolean not null default false,            -- moderators can hide abusive reviews
  created_at    timestamptz default now(),
  updated_at    timestamptz default now(),
  unique (reviewer, reviewee, reviewee_role),                 -- one review per person, editable
  check (reviewer <> reviewee),
  check (not (anonymous and reviewee_role = 'candidate'))     -- companies sign their reviews of people
);
-- criteria:  employer → c1 interview experience, c2 salary transparency, c3 work environment, c4 respect for time
--            candidate → c1 professionalism, c2 technical skills, c3 reliability, c4 communication
create index if not exists idx_job_reviews_reviewee on public.job_reviews(reviewee, reviewee_role) where not hidden;

alter table public.job_reviews enable row level security;
drop policy if exists "reviews: write after a real interaction" on public.job_reviews;
create policy "reviews: write after a real interaction" on public.job_reviews
  for insert with check ((select auth.uid()) = reviewer and public.jobs_interacted(reviewer, reviewee));
drop policy if exists "reviews: edit own" on public.job_reviews;
create policy "reviews: edit own" on public.job_reviews
  for update using ((select auth.uid()) = reviewer) with check ((select auth.uid()) = reviewer and public.jobs_interacted(reviewer, reviewee));
drop policy if exists "reviews: delete own" on public.job_reviews;
create policy "reviews: delete own" on public.job_reviews for delete using ((select auth.uid()) = reviewer);
-- raw rows are readable by their author only; everyone reads them through get_reviews(), which hides anonymous authors
drop policy if exists "reviews: author reads" on public.job_reviews;
create policy "reviews: author reads" on public.job_reviews for select using ((select auth.uid()) = reviewer);

create or replace function public.get_reviews(p uuid, p_role text)
returns table (id bigint, author text, anonymous boolean, c1 smallint, c2 smallint, c3 smallint, c4 smallint, body text, created_at timestamptz, mine boolean)
language sql stable security definer set search_path = public as $$
  select r.id,
         case when r.anonymous then 'Verified applicant' else coalesce(nullif(pr.company, ''), pr.name) end,
         r.anonymous, r.c1, r.c2, r.c3, r.c4, r.body, r.created_at, r.reviewer = auth.uid()
  from public.job_reviews r join public.profiles pr on pr.id = r.reviewer
  where r.reviewee = p and r.reviewee_role = p_role and not r.hidden
  order by r.created_at desc;
$$;

-- ratings + fair (Bayesian) ranking: a single 5★ can't beat many strong reviews
create or replace function public.get_ratings(p_role text, ids uuid[] default null)
returns table (party uuid, n int, avg numeric, c1 numeric, c2 numeric, c3 numeric, c4 numeric, bayes numeric, rank int)
language sql stable security definer set search_path = public as $$
  with agg as (
    select reviewee as party, count(*)::int as n, avg((c1 + c2 + c3 + c4) / 4.0) as avg,
           avg(c1) c1, avg(c2) c2, avg(c3) c3, avg(c4) c4
    from public.job_reviews where reviewee_role = p_role and not hidden group by reviewee
  ), g as (select coalesce(sum(avg * n) / nullif(sum(n), 0), 4) as m from agg)
  select a.party, a.n, round(a.avg, 2), round(a.c1, 2), round(a.c2, 2), round(a.c3, 2), round(a.c4, 2),
         round((3 * g.m + a.avg * a.n) / (3 + a.n), 3) as bayes,
         (rank() over (order by (3 * g.m + a.avg * a.n) / (3 + a.n) desc))::int
  from agg a, g
  where ids is null or a.party = any(ids);
$$;

-- ── 2. WORK REFERENCES: Honor list (public) / Warning list (verified employers only) ──
create table if not exists public.work_references (
  id            bigserial primary key,
  author        uuid not null references public.profiles on delete cascade,     -- the employer account
  candidate     uuid not null references public.profiles on delete cascade,
  kind          text not null check (kind in ('honor','warn')),
  role_title    text not null check (length(trim(role_title)) between 2 and 120),
  from_month    date not null,
  to_month      date not null,
  category      text check (category in ('Left without notice','False documents or certificates',
                                         'Misconduct confirmed by an internal investigation','Breach of confidentiality')),
  body          text not null check (length(trim(body)) between 40 and 3000),
  evidence_path text,                                                           -- private storage, moderators only
  status        text not null default 'pending' check (status in ('pending','published','disputed','rejected')),
  reply         text check (reply is null or length(reply) <= 2000),
  replied_at    timestamptz,
  expires_at    timestamptz,
  created_at    timestamptz default now(),
  check (author <> candidate),
  check (from_month <= to_month and to_month <= (current_date + 31)),
  check (kind = 'honor' or (category is not null and evidence_path is not null))  -- a warning needs a reason from the list + evidence
);
create index if not exists idx_refs_candidate on public.work_references(candidate, kind, status);

-- rules applied on every new reference
create or replace function public.work_reference_rules()
returns trigger language plpgsql security definer set search_path = public as $$
declare comp text; worked boolean;
begin
  select company into comp from public.profiles where id = NEW.author;
  -- "worked with you": the person lists this company in their experience
  select exists (select 1 from public.profiles p, jsonb_array_elements(coalesce(p.experience, '[]'::jsonb)) e
                 where p.id = NEW.candidate and comp is not null and length(comp) > 1
                   and lower(e->>'company') like '%' || lower(comp) || '%') into worked;
  if not worked then
    raise exception 'This person has not listed % in their work experience, so you cannot write a work reference for them', coalesce(comp, 'your company');
  end if;
  if NEW.kind = 'honor' then
    NEW.status := 'published'; NEW.category := null; NEW.expires_at := null;
  else
    NEW.status := 'pending';                                  -- moderated before anyone else sees it
    NEW.expires_at := now() + interval '2 years';
  end if;
  insert into public.notifications(user_id, type, from_user, message)
  values (NEW.candidate, 'work_reference', NEW.author,
          case when NEW.kind = 'honor' then 'added an honorable work record to your profile'
               else 'submitted a work reference about you — you can reply or dispute it before it is published' end);
  return NEW;
end; $$;
drop trigger if exists trg_work_reference_rules on public.work_references;
create trigger trg_work_reference_rules before insert on public.work_references
  for each row execute procedure public.work_reference_rules();

alter table public.work_references enable row level security;
drop policy if exists "refs: employer writes" on public.work_references;
create policy "refs: employer writes" on public.work_references
  for insert with check ((select auth.uid()) = author);
drop policy if exists "refs: who can read" on public.work_references;
create policy "refs: who can read" on public.work_references for select using (
      author = (select auth.uid())
   or candidate = (select auth.uid())
   or (kind = 'honor' and status = 'published')
   or (kind = 'warn' and status = 'published' and (expires_at is null or expires_at > now())
       and exists (select 1 from public.profiles v where v.id = (select auth.uid()) and v.verified))
   or exists (select 1 from public.profiles a where a.id = (select auth.uid()) and a.role in ('admin','moderator'))
);
drop policy if exists "refs: author withdraws" on public.work_references;
create policy "refs: author withdraws" on public.work_references for delete using ((select auth.uid()) = author);

-- the person concerned replies (shown next to the reference) or disputes (hidden until resolved)
create or replace function public.reply_to_reference(ref_id bigint, reply_text text, dispute boolean default false)
returns void language plpgsql security definer set search_path = public as $$
begin
  update public.work_references
     set reply = left(reply_text, 2000), replied_at = now(),
         status = case when dispute and kind = 'warn' then 'disputed' else status end
   where id = ref_id and candidate = auth.uid();
  if not found then raise exception 'Reference not found'; end if;
end; $$;

-- moderators publish / reject / restore
create or replace function public.moderate_reference(ref_id bigint, new_status text)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from public.profiles where id = auth.uid() and role in ('admin','moderator')) then
    raise exception 'Moderators only';
  end if;
  if new_status not in ('published','rejected','pending') then raise exception 'Invalid status'; end if;
  update public.work_references set status = new_status where id = ref_id;
end; $$;

-- evidence bucket (private)
insert into storage.buckets (id, name, public) values ('reference-evidence', 'reference-evidence', false)
on conflict (id) do nothing;
drop policy if exists "evidence: employer uploads" on storage.objects;
create policy "evidence: employer uploads" on storage.objects for insert
  with check (bucket_id = 'reference-evidence' and (storage.foldername(name))[1] = (select auth.uid())::text);
drop policy if exists "evidence: moderators read" on storage.objects;
create policy "evidence: moderators read" on storage.objects for select
  using (bucket_id = 'reference-evidence' and (
         (storage.foldername(name))[1] = (select auth.uid())::text
      or exists (select 1 from public.profiles where id = (select auth.uid()) and role in ('admin','moderator'))));

-- ── 3. PRIVATE WHITELIST / BLACKLIST ──────────────────────────
create table if not exists public.job_lists (
  owner      uuid not null references public.profiles on delete cascade,
  target     uuid not null references public.profiles on delete cascade,
  side       text not null check (side in ('employer','candidate')),   -- employer lists candidates; candidate lists companies
  list       text not null check (list in ('white','black')),
  reason     text,
  note       text check (note is null or length(note) <= 300),
  until      date,
  created_at timestamptz default now(),
  primary key (owner, target, side),
  check (owner <> target)
);
-- an employer's block needs a reason from the fixed list (NULL is not accepted) and always ends (max 12 months, see trigger)
alter table public.job_lists drop constraint if exists job_lists_reason_check;
alter table public.job_lists add constraint job_lists_reason_check check (
  list = 'white' or side = 'candidate'
  or coalesce(reason, '') in ('No-show at interview','False documents or credentials','Unprofessional conduct','Spam or scam','Other'));
create or replace function public.job_list_rules()
returns trigger language plpgsql as $$
begin
  if NEW.list = 'black' and NEW.side = 'employer' and (NEW.until is null or NEW.until > current_date + 366) then
    NEW.until := current_date + 365;
  end if;
  return NEW;
end; $$;
drop trigger if exists trg_job_list_rules on public.job_lists;
create trigger trg_job_list_rules before insert or update on public.job_lists for each row execute procedure public.job_list_rules();
alter table public.job_lists enable row level security;
drop policy if exists "lists: private to owner" on public.job_lists;
create policy "lists: private to owner" on public.job_lists
  for all using ((select auth.uid()) = owner) with check ((select auth.uid()) = owner);

-- who must be hidden from me in Jobs (a block works both ways, nobody is told)
create or replace function public.jobs_hidden_for_me()
returns table (party uuid) language sql stable security definer set search_path = public as $$
  select target from public.job_lists where owner = auth.uid() and list = 'black' and (until is null or until >= current_date)
  union
  select owner from public.job_lists where target = auth.uid() and list = 'black' and (until is null or until >= current_date);
$$;

-- whitelisted candidates go straight to the shortlist, and the employer is told
create or replace function public.fast_track_preferred()
returns trigger language plpgsql security definer set search_path = public as $$
declare poster uuid;
begin
  select user_id into poster from public.jobs where id = NEW.job_id;
  if exists (select 1 from public.job_lists where owner = poster and target = NEW.user_id and side = 'employer' and list = 'white') then
    NEW.status := 'shortlisted';
    insert into public.notifications(user_id, type, from_user, message) values (poster, 'job_application', NEW.user_id, 'A preferred candidate applied — added to your shortlist');
  end if;
  return NEW;
end; $$;
drop trigger if exists trg_fast_track_preferred on public.job_applications;
create trigger trg_fast_track_preferred before insert on public.job_applications for each row execute procedure public.fast_track_preferred();

grant execute on function public.jobs_interacted(uuid, uuid)                 to authenticated;
grant execute on function public.get_reviews(uuid, text)                     to authenticated;
grant execute on function public.get_ratings(text, uuid[])                   to authenticated;
grant execute on function public.reply_to_reference(bigint, text, boolean)   to authenticated;
grant execute on function public.moderate_reference(bigint, text)            to authenticated;
grant execute on function public.jobs_hidden_for_me()                        to authenticated;

-- ─────────────── from 004_company_hub.sql ───────────────
-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 004 — Company hub (ported from the demo)
-- The company is the core entity: team & roles, request routing, sites with their
-- own certificates, products with roles, compliance documents, verification,
-- approved suppliers. Additive only: no existing column or policy is changed.
-- Safe to run more than once.
-- ═════════════════════════════════════════════════════════════════════════════
create extension if not exists pg_trgm;

-- ── 1. companies: identity, status, verification facts ──────────────────────
alter table public.companies
  add column if not exists slug          text,
  add column if not exists name_ar       text,
  add column if not exists tagline       text,
  add column if not exists status        text not null default 'verified',   -- existing rows were created by their owners
  add column if not exists source        text not null default 'company',
  add column if not exists registry      text,                              -- commercial registry number
  add column if not exists tax_verified  boolean not null default false,
  add column if not exists licensed      boolean not null default false,    -- EDA / industrial licence on file
  add column if not exists sectors       text[] not null default '{}',
  add column if not exists governorate   text,
  add column if not exists city          text,
  add column if not exists email         text,
  add column if not exists whatsapp      text,
  add column if not exists hours         text,
  add column if not exists plan          text not null default 'free',
  add column if not exists vip_until     timestamptz,
  add column if not exists updated_at    timestamptz not null default now();

do $$ begin
  alter table public.companies add constraint companies_status_chk check (status in ('unclaimed','pending','verified','suspended'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.companies add constraint companies_source_chk check (source in ('company','public_list'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table public.companies add constraint companies_plan_chk check (plan in ('free','vip'));
exception when duplicate_object then null; end $$;

-- slug: stable public address; filled for existing rows
create or replace function public.slugify(t text) returns text language sql immutable as $$
  select trim(both '-' from regexp_replace(lower(coalesce(t,'')), '[^a-z0-9]+', '-', 'g'))
$$;
update public.companies set slug = public.slugify(name) || '-' || id where slug is null;
create unique index if not exists companies_slug_uq on public.companies (slug);
create index if not exists companies_status_idx on public.companies (status);
create index if not exists companies_sectors_gin on public.companies using gin (sectors);
create index if not exists companies_name_trgm on public.companies using gin (name gin_trgm_ops);
create index if not exists companies_name_ar_trgm on public.companies using gin (name_ar gin_trgm_ops);
create index if not exists companies_gov_idx on public.companies (governorate);

create or replace function public.companies_before_write() returns trigger language plpgsql as $$
begin
  if new.slug is null or new.slug = '' then new.slug := public.slugify(new.name) || '-' || coalesce(new.id::text, substr(md5(random()::text),1,6)); end if;
  new.updated_at := now();
  return new;
end $$;
drop trigger if exists trg_companies_before_write on public.companies;
create trigger trg_companies_before_write before insert or update on public.companies for each row execute function public.companies_before_write();

-- ── 2. team, roles, consent to appear publicly ───────────────────────────────
create table if not exists public.company_members (
  company_id  bigint not null references public.companies(id) on delete cascade,
  user_id     uuid   not null references public.profiles(id) on delete cascade,
  role        text   not null default 'member' check (role in ('owner','admin','sales','quality','regulatory','hr','member')),
  accepted    boolean not null default false,          -- the person agreed to be listed (Law 151/2020)
  show_public boolean not null default false,
  created_at  timestamptz not null default now(),
  primary key (company_id, user_id)
);
create index if not exists company_members_user_idx on public.company_members (user_id);

-- helper used by every policy below; SECURITY DEFINER so it can read memberships without recursion
create or replace function public.is_company_member(cid bigint, roles text[] default null) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.company_members m
                 where m.company_id = cid and m.user_id = auth.uid()
                   and (roles is null or m.role = any(roles)))
      or exists (select 1 from public.companies c where c.id = cid and c.owner_id = auth.uid())
$$;
create or replace function public.is_platform_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'admin')
$$;

-- the creator of a company becomes its owner member
create or replace function public.companies_after_insert() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.owner_id is not null then
    insert into public.company_members (company_id, user_id, role, accepted, show_public)
    values (new.id, new.owner_id, 'owner', true, true) on conflict do nothing;
  end if;
  return new;
end $$;
drop trigger if exists trg_companies_after_insert on public.companies;
create trigger trg_companies_after_insert after insert on public.companies for each row execute function public.companies_after_insert();
insert into public.company_members (company_id, user_id, role, accepted, show_public)
  select id, owner_id, 'owner', true, true from public.companies where owner_id is not null on conflict do nothing;

-- ── 3. request routing: who receives each kind of request ────────────────────
create table if not exists public.company_routing (
  company_id   bigint not null references public.companies(id) on delete cascade,
  request_type text   not null check (request_type in ('quote','service','surplus','dossier','job','questionnaire','group_order')),
  user_id      uuid   not null references public.profiles(id) on delete cascade,
  primary key (company_id, request_type)
);

-- ── 4. sites and their own certificates ──────────────────────────────────────
create table if not exists public.company_sites (
  id           bigint generated always as identity primary key,
  company_id   bigint not null references public.companies(id) on delete cascade,
  name         text   not null check (length(name) between 2 and 120),
  type         text   not null default 'factory' check (type in ('factory','warehouse','lab','office','head_office')),
  city         text,
  governorate  text,
  dosage_forms text[] not null default '{}',
  min_batch    text,
  capacity     text,
  free_slots   jsonb  not null default '[]'::jsonb,     -- [{"month":"2026-10","state":"free"}]
  created_at   timestamptz not null default now()
);
create index if not exists company_sites_company_idx on public.company_sites (company_id);
create index if not exists company_sites_forms_gin on public.company_sites using gin (dosage_forms);

create table if not exists public.site_certificates (
  id          bigint generated always as identity primary key,
  site_id     bigint not null references public.company_sites(id) on delete cascade,
  company_id  bigint not null references public.companies(id) on delete cascade,   -- denormalised for RLS and listing
  name        text   not null check (length(name) between 2 and 80),
  expiry      date,
  source      text   not null default 'company' check (source in ('document','public_list','company')),
  checked_at  timestamptz,                              -- set only by a platform admin
  created_at  timestamptz not null default now()
);
create index if not exists site_certs_company_idx on public.site_certificates (company_id);
create index if not exists site_certs_expiry_idx on public.site_certificates (expiry) where expiry is not null;

-- ── 5. products with their role (who holds the registration, who makes it) ──
create table if not exists public.company_products (
  id                bigint generated always as identity primary key,
  company_id        bigint not null references public.companies(id) on delete cascade,
  name              text   not null check (length(name) between 2 and 160),
  active_ingredient text,
  active_ingredient_ar text,
  dosage_form       text,
  strength          text,
  role              text   not null default 'manufacturer' check (role in ('registration_holder','manufacturer','supplier')),
  made_by_company_id bigint references public.companies(id) on delete set null,
  registration_no   text,
  created_at        timestamptz not null default now()
);
create index if not exists company_products_company_idx on public.company_products (company_id);
create index if not exists company_products_ai_trgm on public.company_products using gin (active_ingredient gin_trgm_ops);
create index if not exists company_products_ai_ar_trgm on public.company_products using gin (active_ingredient_ar gin_trgm_ops);
create index if not exists company_products_name_trgm on public.company_products using gin (name gin_trgm_ops);

-- ── 6. compliance passport: documents a company declares ─────────────────────
create table if not exists public.company_documents (
  id          bigint generated always as identity primary key,
  company_id  bigint not null references public.companies(id) on delete cascade,
  type        text   not null check (type in ('CEP','DMF (US)','ASMF (EU)','WHO PQ','GDP certificate','ISO 9001','Stability data (Zone IVb)')),
  product     text,
  number      text   not null check (length(number) between 2 and 80),
  expiry      date,
  status      text   not null default 'declared' check (status in ('declared','review','verified','rejected')),
  file_path   text,                                     -- private storage bucket path; never exposed publicly
  created_by  uuid   references public.profiles(id) on delete set null,
  created_at  timestamptz not null default now()
);
create index if not exists company_documents_company_idx on public.company_documents (company_id);

-- only the platform can mark a document verified
create or replace function public.company_documents_guard() returns trigger language plpgsql as $$
begin
  if new.status = 'verified' and (tg_op = 'INSERT' or old.status is distinct from 'verified') and not public.is_platform_admin() then
    raise exception 'Only Drugbox can mark a document as verified' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_company_documents_guard on public.company_documents;
create trigger trg_company_documents_guard before insert or update on public.company_documents for each row execute function public.company_documents_guard();

-- public passport view: metadata only, no private file paths
create or replace view public.company_documents_public with (security_invoker = true) as
  select id, company_id, type, product, number, expiry, status, created_at from public.company_documents;

-- ── 7. verification requests (registry + tax card + licence) ─────────────────
create table if not exists public.verification_requests (
  id            bigint generated always as identity primary key,
  company_id    bigint not null references public.companies(id) on delete cascade,
  submitted_by  uuid   not null references public.profiles(id) on delete cascade,
  registry      text   not null check (length(registry) between 3 and 40),
  tax_card_path text,
  licence_path  text,
  status        text   not null default 'pending' check (status in ('pending','approved','rejected')),
  note          text,
  reviewed_by   uuid references public.profiles(id),
  reviewed_at   timestamptz,
  created_at    timestamptz not null default now()
);
create index if not exists verification_requests_status_idx on public.verification_requests (status, created_at);

create or replace function public.verification_requests_apply() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status <> old.status then
    if not public.is_platform_admin() then raise exception 'Only Drugbox reviews verification requests' using errcode = '42501'; end if;
    new.reviewed_by := auth.uid(); new.reviewed_at := now();
    if new.status = 'approved' then
      update public.companies set status = 'verified', registry = new.registry, tax_verified = true,
             licensed = licensed or new.licence_path is not null where id = new.company_id;
    end if;
  end if;
  return new;
end $$;
drop trigger if exists trg_verification_requests_apply on public.verification_requests;
create trigger trg_verification_requests_apply before update on public.verification_requests for each row execute function public.verification_requests_apply();

-- ── 8. approved suppliers (a buyer's quality list) ───────────────────────────
create table if not exists public.approved_suppliers (
  buyer_company_id    bigint not null references public.companies(id) on delete cascade,
  supplier_company_id bigint not null references public.companies(id) on delete cascade,
  status              text   not null default 'approved' check (status in ('approved','conditional','blocked')),
  note                text,
  updated_at          timestamptz not null default now(),
  primary key (buyer_company_id, supplier_company_id),
  check (buyer_company_id <> supplier_company_id)
);

-- ── 9. verification level, computed from facts (never stored, never bought) ─
create or replace function public.company_tier(cid bigint) returns int language sql stable as $$
  select case
    when c.status <> 'verified' or c.registry is null then 0
    when not c.licensed then 1
    when exists (select 1 from public.site_certificates s where s.company_id = c.id and s.checked_at is not null
                   and (s.expiry is null or s.expiry >= current_date)
                   and s.name ~* '(GMP|ISO 17025|GDP|ISO 15378|ISO 22716)') then 3
    else 2 end
  from public.companies c where c.id = cid
$$;

-- ── 10. directory search (name, Arabic name, product, active ingredient) ────
create or replace function public.search_companies(q text default null, p_sector text default null, p_gov text default null,
                                                   p_limit int default 20, p_after bigint default null)
returns setof public.companies language sql stable as $$
  select c.* from public.companies c
  where (p_sector is null or p_sector = any(c.sectors))
    and (p_gov is null or c.governorate = p_gov)
    and (p_after is null or c.id > p_after)
    and (q is null or q = '' or c.name ilike '%' || q || '%' or c.name_ar ilike '%' || q || '%'
         or exists (select 1 from public.company_products p where p.company_id = c.id
                    and (p.name ilike '%' || q || '%' or p.active_ingredient ilike '%' || q || '%' or p.active_ingredient_ar ilike '%' || q || '%')))
  order by c.id
  limit least(greatest(p_limit, 1), 50)
$$;

-- ── 11. row-level security ───────────────────────────────────────────────────
alter table public.company_members       enable row level security;
alter table public.company_routing       enable row level security;
alter table public.company_sites         enable row level security;
alter table public.site_certificates     enable row level security;
alter table public.company_products      enable row level security;
alter table public.company_documents     enable row level security;
alter table public.verification_requests enable row level security;
alter table public.approved_suppliers    enable row level security;

do $$ begin
  -- team: public members are visible to all; the whole team is visible to its members
  create policy "members: read public or own team" on public.company_members for select
    using ((accepted and show_public) or public.is_company_member(company_id));
  create policy "members: owners/admins add" on public.company_members for insert
    with check (public.is_company_member(company_id, array['owner','admin']));
  create policy "members: owners/admins or the person update" on public.company_members for update
    using (public.is_company_member(company_id, array['owner','admin']) or user_id = auth.uid());
  create policy "members: owners/admins remove, or leave" on public.company_members for delete
    using (public.is_company_member(company_id, array['owner','admin']) or user_id = auth.uid());

  create policy "routing: team reads" on public.company_routing for select using (public.is_company_member(company_id));
  create policy "routing: owners/admins manage" on public.company_routing for all
    using (public.is_company_member(company_id, array['owner','admin'])) with check (public.is_company_member(company_id, array['owner','admin']));

  create policy "sites: everyone reads" on public.company_sites for select using (true);
  create policy "sites: owners/admins manage" on public.company_sites for all
    using (public.is_company_member(company_id, array['owner','admin'])) with check (public.is_company_member(company_id, array['owner','admin']));

  create policy "certs: everyone reads" on public.site_certificates for select using (true);
  create policy "certs: owners/admins/quality manage" on public.site_certificates for all
    using (public.is_company_member(company_id, array['owner','admin','quality']))
    with check (public.is_company_member(company_id, array['owner','admin','quality']) and (checked_at is null or public.is_platform_admin()));

  create policy "products: everyone reads" on public.company_products for select using (true);
  create policy "products: owners/admins/regulatory manage" on public.company_products for all
    using (public.is_company_member(company_id, array['owner','admin','regulatory']))
    with check (public.is_company_member(company_id, array['owner','admin','regulatory']));

  create policy "documents: everyone reads metadata" on public.company_documents for select using (true);
  create policy "documents: owners/admins/regulatory/quality add" on public.company_documents for insert
    with check (public.is_company_member(company_id, array['owner','admin','regulatory','quality']) and created_by = auth.uid());
  create policy "documents: owners/admins/regulatory/quality or Drugbox update" on public.company_documents for update
    using (public.is_company_member(company_id, array['owner','admin','regulatory','quality']) or public.is_platform_admin());
  create policy "documents: owners/admins delete" on public.company_documents for delete
    using (public.is_company_member(company_id, array['owner','admin']));

  create policy "verification: team and Drugbox read" on public.verification_requests for select
    using (public.is_company_member(company_id) or public.is_platform_admin());
  create policy "verification: owners/admins submit" on public.verification_requests for insert
    with check (public.is_company_member(company_id, array['owner','admin']) and submitted_by = auth.uid() and status = 'pending');
  create policy "verification: Drugbox reviews" on public.verification_requests for update using (public.is_platform_admin());

  create policy "suppliers: buyer quality team only" on public.approved_suppliers for all
    using (public.is_company_member(buyer_company_id, array['owner','admin','quality']))
    with check (public.is_company_member(buyer_company_id, array['owner','admin','quality']));
exception when duplicate_object then null; end $$;

-- certificates: Drugbox confirms checks; any company edit to a checked certificate clears the check
do $$ begin
  create policy "certs: Drugbox checks" on public.site_certificates for update using (public.is_platform_admin()) with check (public.is_platform_admin());
exception when duplicate_object then null; end $$;
create or replace function public.site_certificates_guard() returns trigger language plpgsql as $$
begin
  if not public.is_platform_admin() then
    if tg_op = 'INSERT' then new.checked_at := null;
    elsif new.name is distinct from old.name or new.expiry is distinct from old.expiry or new.checked_at is distinct from old.checked_at then new.checked_at := null; end if;
  end if;
  return new;
end $$;
drop trigger if exists trg_site_certificates_guard on public.site_certificates;
create trigger trg_site_certificates_guard before insert or update on public.site_certificates for each row execute function public.site_certificates_guard();

-- membership guard: a person may only change their own consent; roles are changed by owners/admins,
-- and only an owner can make someone an owner or admin (no self-promotion)
create or replace function public.company_members_guard() returns trigger language plpgsql as $$
declare is_owner boolean := public.is_company_member(coalesce(new.company_id, old.company_id), array['owner']);
        is_admin boolean := public.is_company_member(coalesce(new.company_id, old.company_id), array['owner','admin']);
begin
  if tg_op = 'INSERT' then
    if new.role in ('owner','admin') and not is_owner then raise exception 'Only an owner can add an owner or admin' using errcode = '42501'; end if;
    if new.user_id <> auth.uid() then new.accepted := false; new.show_public := false; end if;   -- consent belongs to the person
    return new;
  end if;
  if new.company_id <> old.company_id or new.user_id <> old.user_id then raise exception 'Membership cannot be moved' using errcode = '42501'; end if;
  if new.role <> old.role then
    if not is_admin then raise exception 'Only owners/admins change roles' using errcode = '42501'; end if;
    if (new.role in ('owner','admin') or old.role in ('owner','admin')) and not is_owner then raise exception 'Only an owner can grant or remove owner/admin' using errcode = '42501'; end if;
  end if;
  if (new.accepted <> old.accepted or new.show_public <> old.show_public) and old.user_id <> auth.uid() then
    raise exception 'Only the person can give or withdraw consent to be listed' using errcode = '42501';
  end if;
  return new;
end $$;
drop trigger if exists trg_company_members_guard on public.company_members;
create trigger trg_company_members_guard before insert or update on public.company_members for each row
  when (auth.uid() is not null)
  execute function public.company_members_guard();

-- private file paths are never readable through the API: table-level SELECT is replaced by a column list
revoke select on public.company_documents from anon, authenticated;
grant select (id, company_id, type, product, number, expiry, status, created_by, created_at) on public.company_documents to anon, authenticated;
