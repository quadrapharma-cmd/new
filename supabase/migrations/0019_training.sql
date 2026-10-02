-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0019 — training (step E3)
-- Courses (read by everyone, managed by Drugbox) and enrollments (each person manages their own).
-- Seeded with the six courses of the approved page. One enrollment counter.
-- ═════════════════════════════════════════════════════════════════════
create table if not exists public.training_courses (
  id          bigint generated always as identity primary key,
  title       text not null check (length(trim(title)) between 3 and 160),
  description text not null default '' check (length(description) <= 2000),
  emoji       text not null default '🎓',
  duration    text not null default '',
  level       text not null default 'Beginner' check (level in ('Beginner','Intermediate','Advanced')),
  enrolled_count int not null default 0,
  active      boolean not null default true,
  sort_order  int not null default 100,
  created_at  timestamptz not null default now(),
  unique (title)
);
create table if not exists public.course_enrollments (
  course_id   bigint not null references public.training_courses(id) on delete cascade,
  user_id     uuid   not null references public.profiles(id) on delete cascade,
  status      text   not null default 'enrolled' check (status in ('enrolled','completed')),
  enrolled_at timestamptz not null default now(),
  completed_at timestamptz,
  primary key (course_id, user_id)
);
create index if not exists idx_course_enrollments_user on public.course_enrollments (user_id);
alter table public.training_courses enable row level security;
alter table public.course_enrollments enable row level security;
do $$ begin
  create policy "courses: everyone reads active" on public.training_courses for select using (active or public.is_platform_admin());
  create policy "courses: Drugbox manages" on public.training_courses for all using (public.is_platform_admin()) with check (public.is_platform_admin());
  create policy "enrollments: you see yours (Drugbox sees all)" on public.course_enrollments for select using (user_id = (select auth.uid()) or public.is_platform_admin());
  create policy "enrollments: enroll yourself" on public.course_enrollments for insert with check (user_id = (select auth.uid()) and status = 'enrolled'
    and exists (select 1 from public.training_courses c where c.id = course_id and c.active));
  create policy "enrollments: leave a course" on public.course_enrollments for delete using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
create or replace function public.course_enrolled_count() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then update public.training_courses set enrolled_count = enrolled_count + 1 where id = new.course_id;
  else update public.training_courses set enrolled_count = greatest(0, enrolled_count - 1) where id = old.course_id; end if;
  return null;
end $$;
drop trigger if exists trg_course_enrolled_count on public.course_enrollments;
create trigger trg_course_enrolled_count after insert or delete on public.course_enrollments for each row execute function public.course_enrolled_count();

insert into public.training_courses (title, description, emoji, duration, level, sort_order) values
  ('GMP Fundamentals', 'Good Manufacturing Practices for pharmaceutical production and quality systems.', '🏭', '4 hours', 'Beginner', 10),
  ('EDA Registration Process', 'Complete guide to Egyptian Drug Authority dossier preparation and submission.', '📋', '6 hours', 'Intermediate', 20),
  ('ICH Guidelines', 'International Conference on Harmonisation Q1-Q14 guidelines.', '⚗️', '8 hours', 'Advanced', 30),
  ('Cosmetics Regulation', 'EDA and GCC cosmetic product notification, labeling, and compliance.', '🧴', '3 hours', 'Beginner', 40),
  ('Stability Studies', 'Designing Zone IVa/IVb stability protocols per ICHQ1A/Q1E.', '🔬', '5 hours', 'Intermediate', 50),
  ('GCC Market Access', 'Registration pathways in Saudi Arabia, UAE, Kuwait, Bahrain, Qatar.', '🌍', '4 hours', 'Intermediate', 60)
on conflict (title) do nothing;

notify pgrst, 'reload schema';
