-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0011 — intro videos (company video, personal introduction)
-- Bucket "videos": anyone can watch; a person uploads only under people/<their id>/,
-- a company's owners/admins only under companies/<company id>/. Size and type limits are enforced by Storage.
-- The video's path, poster path and length are kept on the company / profile row.
-- ═════════════════════════════════════════════════════════════════════
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('videos', 'videos', true, 104857600, array['video/mp4','video/webm','video/quicktime','image/jpeg'])
on conflict (id) do update set public = true, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

alter table public.profiles  add column if not exists intro_video jsonb;     -- {path, poster, duration, v}
alter table public.companies add column if not exists intro_video jsonb;

create or replace function public.can_write_video(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'people'    then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'companies' then (storage.foldername(p_name))[2] ~ '^\d+$' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
    else false end
$$;

do $$ begin
  create policy "videos: anyone can watch" on storage.objects for select using (bucket_id = 'videos');
  create policy "videos: upload to your own folder" on storage.objects for insert to authenticated with check (bucket_id = 'videos' and public.can_write_video(name));
  create policy "videos: replace your own" on storage.objects for update to authenticated using (bucket_id = 'videos' and public.can_write_video(name)) with check (bucket_id = 'videos' and public.can_write_video(name));
  create policy "videos: delete your own" on storage.objects for delete to authenticated using (bucket_id = 'videos' and public.can_write_video(name));
exception when duplicate_object then null; end $$;

-- the directory carries each company's video (path/poster/length only)
create or replace function public.directory_companies(p_limit int default 5000)
returns json language sql stable security invoker set search_path = public as $$
  select coalesce(json_agg(x order by x.name), '[]'::json) from (
    select c.id, c.slug, c.name, c.name_ar, c.status, c.registry, c.licensed, c.sectors, c.governorate, c.city, c.location, c.tagline, c.bio,
           c.founded, c.employees, c.website, c.phone, c.email, c.whatsapp, c.hours, c.plan, c.logo_url, c.follower_count, c.profile, c.created_at, c.intro_video,
           public.company_tier(c.id) as tier, public.is_company_member(c.id) as mine,
           (select coalesce(json_agg(distinct s.name), '[]'::json) from public.site_certificates s where s.company_id = c.id and (s.expiry is null or s.expiry >= current_date)) as certs,
           (select coalesce(json_agg(json_build_object('name', p.name, 'ingredient', p.active_ingredient, 'ingredient_ar', p.active_ingredient_ar,
                   'form', p.dosage_form, 'strength', p.strength, 'role', p.role) order by p.name), '[]'::json) from public.company_products p where p.company_id = c.id) as products,
           public.company_track_record(c.id) as track
    from public.companies c where c.status <> 'suspended'
    limit least(greatest(coalesce(p_limit, 5000), 1), 10000)) x
$$;

notify pgrst, 'reload schema';
