-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0016 — private documents (step E1b)
-- Bucket "documents": cv/<applicant>/… readable by the applicant and by the employer of the job that CV was sent to;
-- verification/<company id>/… readable by the company's owners/admins and Drugbox. Evidence for warnings uses the
-- existing "reference-evidence" bucket (author + moderators).
-- ═════════════════════════════════════════════════════════════════════
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documents', 'documents', false, 10485760, array['application/pdf','image/jpeg','image/png',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/msword'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

alter table public.job_applications add column if not exists cv_path text;
do $$ begin alter table public.job_applications add constraint job_applications_cv_path check (cv_path is null or cv_path like 'cv/' || user_id::text || '/%');
exception when duplicate_object then null; end $$;
alter table public.verification_requests add column if not exists registry_path text;

create or replace function public.can_read_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
                   or exists (select 1 from public.job_applications a join public.jobs j on j.id = a.job_id where a.cv_path = p_name and j.user_id = auth.uid())
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$'
                   and (public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin']) or public.is_platform_admin())
    else false end
$$;
create or replace function public.can_write_document(p_name text) returns boolean language sql stable security definer set search_path = public as $$
  select case (storage.foldername(p_name))[1]
    when 'cv' then (storage.foldername(p_name))[2] = auth.uid()::text
    when 'verification' then (storage.foldername(p_name))[2] ~ '^\d+$' and public.is_company_member(((storage.foldername(p_name))[2])::bigint, array['owner','admin'])
    else false end
$$;
do $$ begin
  create policy "documents: read when allowed" on storage.objects for select to authenticated using (bucket_id = 'documents' and public.can_read_document(name));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "documents: upload to your own folder" on storage.objects for insert to authenticated with check (bucket_id = 'documents' and public.can_write_document(name));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "documents: delete your own" on storage.objects for delete to authenticated using (bucket_id = 'documents' and public.can_write_document(name));
exception when duplicate_object then null; end $$;

notify pgrst, 'reload schema';
