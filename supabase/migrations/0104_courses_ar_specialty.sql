-- ═════════════════════════════════════════════════════════════════════
-- 0104 — Two of the owner's pending decisions (AREA w-growth)
--   Decision 7: the six courses get their Arabic title and description now (training_courses.title_ar / description_ar,
--               shown in the Arabic interface); they stay free until the owner sends their content and prices.
--   Decision 9: members whose headline is still the old sign-up default "Regulatory Affairs" are asked ONCE to confirm or
--               change their specialty (member_prompts records the answer; specialty_prompt_due() / specialty_answer()) — accounts
--               made before this migration ran (newer ones chose their specialty on a sign-up form with no default).
-- Every table and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── decision 7 ──────────────────────────────────────────────────────────────────────────────────────────
alter table public.training_courses add column if not exists title_ar       text;
alter table public.training_courses add column if not exists description_ar text;
do $$ begin
  alter table public.training_courses add constraint training_courses_ar_len check (length(title_ar) <= 160 and length(description_ar) <= 2000);
exception when duplicate_object then null; end $$;
-- the browser reads them like the other catalog columns (0062 names the columns it grants)
do $$ begin
  if exists (select 1 from information_schema.column_privileges where table_schema = 'public' and table_name = 'training_courses' and grantee = 'authenticated' and privilege_type = 'SELECT') then
    grant select (title_ar, description_ar) on table public.training_courses to authenticated;
  end if;
  if exists (select 1 from information_schema.column_privileges where table_schema = 'public' and table_name = 'training_courses' and grantee = 'anon' and privilege_type = 'SELECT') then
    grant select (title_ar, description_ar) on table public.training_courses to anon;
  end if;
end $$;
update public.training_courses c set title_ar = v.t, description_ar = v.d
  from (values
    ('GMP Fundamentals',          'أساسيات التصنيع الجيد (GMP)',   'ممارسات التصنيع الجيد لإنتاج الدواء وأنظمة الجودة.'),
    ('EDA Registration Process',  'خطوات التسجيل في هيئة الدواء',  'دليل كامل لتجهيز ملف التسجيل في هيئة الدواء المصرية وتقديمه.'),
    ('ICH Guidelines',            'إرشادات ICH',                   'إرشادات المجلس الدولي للتنسيق من Q1 إلى Q14.'),
    ('Cosmetics Regulation',      'تنظيم مستحضرات التجميل',        'إخطار مستحضرات التجميل في مصر والخليج والبطاقة والالتزام بالاشتراطات.'),
    ('Stability Studies',         'دراسات الثبات',                 'تصميم بروتوكولات الثبات للمنطقتين IVa وIVb وفق ICH Q1A وQ1E.'),
    ('GCC Market Access',         'دخول أسواق الخليج',             'مسارات التسجيل في السعودية والإمارات والكويت والبحرين وقطر.')
  ) as v(en, t, d)
 where c.title = v.en and c.title_ar is null;

-- ── decision 9 ──────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.member_prompts (
  user_id     uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  key         text not null check (key in ('specialty')),
  answer      text check (length(answer) <= 120),
  answered_at timestamptz not null default now(),
  primary key (user_id, key)
);
alter table public.member_prompts enable row level security;
drop policy if exists "member prompts: own" on public.member_prompts;
create policy "member prompts: own" on public.member_prompts for select to authenticated using (user_id = (select auth.uid()));
revoke all on table public.member_prompts from public, anon, authenticated, service_role;
grant select on table public.member_prompts to anon, authenticated;              -- writes through specialty_answer() only
grant select, insert, update, delete, truncate, references, trigger on table public.member_prompts to service_role;

-- the moment this migration first ran: accounts made after it chose their specialty on the new sign-up form (no default)
create table if not exists private.growth_marks (key text primary key, at timestamptz not null default now());
revoke all on table private.growth_marks from public, anon, authenticated, service_role;
grant select on table private.growth_marks to service_role;
insert into private.growth_marks (key) values ('specialty_prompt_from') on conflict (key) do nothing;

-- is the one-time question due for me? (an account from before, whose headline is exactly the old default, that has not answered)
create or replace function public.specialty_prompt_due() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles p where p.id = auth.uid() and p.headline = 'Regulatory Affairs'
                   and p.created_at < (select at from private.growth_marks where key = 'specialty_prompt_from'))
     and not exists (select 1 from public.member_prompts m where m.user_id = auth.uid() and m.key = 'specialty')
$$;
revoke all on function public.specialty_prompt_due() from public, anon, authenticated, service_role;
grant execute on function public.specialty_prompt_due() to authenticated, service_role;

-- the answer: kept as it is (p_headline null or "Regulatory Affairs") or the specialty the member chose. A changed specialty is
-- written to the member's own profile row by the member (Edit Profile's own update, under the profile's rules: 0020 columns,
-- suspension) before this records the answer — so no server function writes profiles for it (privacy_names.rls.sql's write paths)
create or replace function public.specialty_answer(p_headline text) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); h text := nullif(trim(coalesce(p_headline, '')), '');
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if h is not null and (length(h) < 2 or length(h) > 120) then raise exception 'A specialty is 2 to 120 characters' using errcode = '22023'; end if;
  if h is not null and h ~ '[<>]' then raise exception 'A specialty cannot contain < or >' using errcode = '22023'; end if;
  insert into public.member_prompts (user_id, key, answer) values (me, 'specialty', coalesce(h, 'Regulatory Affairs'))
  on conflict (user_id, key) do update set answer = excluded.answer, answered_at = now();
  return coalesce(h, 'Regulatory Affairs');
end $$;
revoke all on function public.specialty_answer(text) from public, anon, authenticated, service_role;
grant execute on function public.specialty_answer(text) to authenticated, service_role;

notify pgrst, 'reload schema';
