-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0014 — uploads: photos and files in posts (public) and messages (private)
-- post_media had row-level security ON and NO policy, so nobody could attach anything to a post.
-- Message files are private: only the two people in the conversation can read them, through short-lived signed links.
-- ═════════════════════════════════════════════════════════════════════
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types) values
  ('post-media', 'post-media', true, 20971520, array['image/jpeg','image/png','image/webp','image/gif','application/pdf',
     'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','application/zip']),
  ('message-media', 'message-media', false, 20971520, array['image/jpeg','image/png','image/webp','image/gif','application/pdf',
     'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','application/zip'])
on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

do $$ begin
  create policy "post media: anyone can see" on storage.objects for select using (bucket_id = 'post-media');
  create policy "post media: upload to your own folder" on storage.objects for insert to authenticated
    with check (bucket_id = 'post-media' and (storage.foldername(name))[1] = 'posts' and (storage.foldername(name))[2] = auth.uid()::text);
  create policy "post media: delete your own" on storage.objects for delete to authenticated
    using (bucket_id = 'post-media' and (storage.foldername(name))[1] = 'posts' and (storage.foldername(name))[2] = auth.uid()::text);
  -- message files live under <sender>/<receiver>/…; only those two can read them
  create policy "message media: the two people read" on storage.objects for select to authenticated
    using (bucket_id = 'message-media' and auth.uid()::text in ((storage.foldername(name))[1], (storage.foldername(name))[2]));
  create policy "message media: the sender uploads" on storage.objects for insert to authenticated
    with check (bucket_id = 'message-media' and (storage.foldername(name))[1] = auth.uid()::text);
  create policy "message media: the sender deletes" on storage.objects for delete to authenticated
    using (bucket_id = 'message-media' and (storage.foldername(name))[1] = auth.uid()::text);
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "post media rows: everyone reads" on public.post_media for select using (true);
  create policy "post media rows: the post's author adds" on public.post_media for insert
    with check (exists (select 1 from public.posts p where p.id = post_id and p.user_id = (select auth.uid())));
  create policy "post media rows: the post's author removes" on public.post_media for delete
    using (exists (select 1 from public.posts p where p.id = post_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
create index if not exists idx_post_media_post on public.post_media (post_id);

alter table public.messages add column if not exists attachment jsonb;     -- {path, name, size, kind: photo|file}
create or replace function public.messages_guard() returns trigger language plpgsql as $$
begin
  if new.body is distinct from old.body or new.image_url is distinct from old.image_url or new.attachment is distinct from old.attachment
     or new.sender_id <> old.sender_id or new.receiver_id <> old.receiver_id or new.created_at <> old.created_at then
    raise exception 'Messages cannot be edited' using errcode = '42501';
  end if;
  return new;
end $$;
-- an attachment must sit in the sender's own folder for this conversation
do $$ begin
  alter table public.messages add constraint messages_attachment_path check (attachment is null or (attachment->>'path') like sender_id::text || '/' || receiver_id::text || '/%');
exception when duplicate_object then null; end $$;

notify pgrst, 'reload schema';

-- a post may be only photos or a file (no text); the interface still refuses a post with nothing in it
alter table public.posts drop constraint if exists posts_body_check;
do $$ begin alter table public.posts add constraint posts_body_check check (length(body) <= 5000); exception when duplicate_object then null; end $$;
notify pgrst, 'reload schema';
