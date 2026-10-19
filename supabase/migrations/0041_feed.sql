-- ═════════════════════════════════════════════════════════════════════
-- 0041 — feed (area social: S-08 repost, S-12 edit my post, S-13 replies and comment likes, S-22 mentions and hashtags)
--   1. posts.edited_at       set by the database when the author changes the text or the category (the card says "edited")
--   2. reposts               one per member and post, with an optional comment; posts.share_count counts them (one trigger);
--                            the author is told once ('repost')
--   3. replies               comments.parent_id (0001) must name a comment of the same post; a reply to a reply hangs under the
--                            same top comment; the comment's author is told ('reply')
--   4. comment_reactions     a like per member and comment; comments.like_count counts them (one trigger)
--   5. post_mentions         who a post names with @ — written by the post's author, at most 20; the person is told ('mention')
--   6. post_tags             the #hashtags of every post, kept by the database from the text (never written by the browser);
--                            a tag's page reads them through an index
-- Every table, sequence and function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. edited ────────────────────────────────────────────────────────────────────────────────────────────
alter table public.posts add column if not exists edited_at timestamptz;
grant select (edited_at) on public.posts to anon, authenticated;
create or replace function public.posts_edited_mark() returns trigger language plpgsql as $$
begin
  if public.is_server_call() then return new; end if;
  if tg_op = 'INSERT' then new.edited_at := null; return new; end if;
  new.edited_at := case when new.body is distinct from old.body or new.category is distinct from old.category then now() else old.edited_at end;
  return new;
end $$;
revoke all on function public.posts_edited_mark() from public, anon, authenticated, service_role;
grant execute on function public.posts_edited_mark() to authenticated, service_role;
drop trigger if exists trg_posts_edited_mark on public.posts;
-- after server_columns (names fire in order): an edit by anyone but the author is undone there first, so it never counts as one
create trigger trg_posts_zz_edited_mark before insert or update on public.posts for each row execute function public.posts_edited_mark();

-- ── 2. reposts ───────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.reposts (
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  post_id    bigint not null references public.posts(id) on delete cascade,
  note       text,
  created_at timestamptz not null default now(),
  primary key (user_id, post_id),
  constraint reposts_note_len check (length(note) <= 1000)
);
create index if not exists idx_reposts_post on public.reposts (post_id);
create index if not exists idx_reposts_created on public.reposts (created_at desc);
alter table public.reposts enable row level security;
do $$ begin
  create policy "reposts: read with the post" on public.reposts for select using (exists (select 1 from public.posts p where p.id = reposts.post_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "reposts: own add" on public.reposts for insert with check (user_id = (select auth.uid()) and exists (select 1 from public.posts p where p.id = reposts.post_id and p.group_id is null));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "reposts: own remove" on public.reposts for delete using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.reposts from public, anon, authenticated, service_role;
grant select on table public.reposts to anon;
grant select, insert, delete on table public.reposts to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.reposts to service_role;

create or replace function public.reposts_counted() returns trigger
language plpgsql security definer set search_path = public as $$
declare owner uuid;
begin
  if tg_op = 'INSERT' then
    new.created_at := now();
    update public.posts set share_count = share_count + 1 where id = new.post_id returning user_id into owner;
    if owner is not null and owner <> new.user_id and not exists (select 1 from public.notifications n where n.user_id = owner and n.from_user = new.user_id and n.post_id = new.post_id and n.type = 'repost') then
      insert into public.notifications (user_id, type, from_user, post_id, message) values (owner, 'repost', new.user_id, new.post_id, 'reposted your post');
    end if;
    return new;
  end if;
  update public.posts set share_count = greatest(0, share_count - 1) where id = old.post_id;
  return old;
end $$;
revoke all on function public.reposts_counted() from public, anon, authenticated, service_role;
grant execute on function public.reposts_counted() to service_role;
drop trigger if exists trg_reposts_share_count on public.reposts;
create trigger trg_reposts_share_count before insert or delete on public.reposts for each row execute function public.reposts_counted();

-- ── 3. replies ───────────────────────────────────────────────────────────────────────────────────────────
alter table public.comments add column if not exists like_count integer not null default 0;
grant select (like_count) on public.comments to anon, authenticated;
create or replace function public.comments_reply_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare p record;
begin
  if tg_op = 'INSERT' then new.like_count := 0; else new.like_count := old.like_count; new.parent_id := old.parent_id; end if;
  if tg_op = 'INSERT' and new.parent_id is not null then
    select c.post_id, c.parent_id into p from public.comments c where c.id = new.parent_id;
    if not found or p.post_id <> new.post_id then raise exception 'You can only reply to a comment of this post' using errcode = '22023'; end if;
    if p.parent_id is not null then new.parent_id := p.parent_id; end if;          -- one level: a reply to a reply joins its thread
  end if;
  return new;
end $$;
revoke all on function public.comments_reply_guard() from public, anon, authenticated, service_role;
grant execute on function public.comments_reply_guard() to authenticated, service_role;
drop trigger if exists trg_comments_reply_guard on public.comments;
create trigger trg_comments_reply_guard before insert or update on public.comments for each row execute function public.comments_reply_guard();

create or replace function public.notify_reply() returns trigger
language plpgsql security definer set search_path = public as $$
declare who uuid;
begin
  if new.parent_id is null then return null; end if;
  select user_id into who from public.comments where id = new.parent_id;
  if who is not null and who <> new.user_id then
    insert into public.notifications (user_id, type, from_user, post_id, comment_id, message) values (who, 'reply', new.user_id, new.post_id, new.id, left(new.body, 140));
  end if;
  return null;
end $$;
revoke all on function public.notify_reply() from public, anon, authenticated, service_role;
grant execute on function public.notify_reply() to service_role;
drop trigger if exists trg_notify_reply on public.comments;
create trigger trg_notify_reply after insert on public.comments for each row execute function public.notify_reply();

-- ── 4. comment likes ─────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.comment_reactions (
  comment_id bigint not null references public.comments(id) on delete cascade,
  user_id    uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (comment_id, user_id)
);
create index if not exists idx_comment_reactions_user on public.comment_reactions (user_id);
alter table public.comment_reactions enable row level security;
do $$ begin
  create policy "comment likes: read with the comment" on public.comment_reactions for select using (exists (select 1 from public.comments c where c.id = comment_reactions.comment_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "comment likes: own add" on public.comment_reactions for insert with check (user_id = (select auth.uid()) and exists (select 1 from public.comments c where c.id = comment_reactions.comment_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "comment likes: own remove" on public.comment_reactions for delete using (user_id = (select auth.uid()));
exception when duplicate_object then null; end $$;
revoke all on table public.comment_reactions from public, anon, authenticated, service_role;
grant select on table public.comment_reactions to anon;
grant select, insert, delete on table public.comment_reactions to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.comment_reactions to service_role;
create or replace function public.comment_like_count() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then update public.comments set like_count = like_count + 1 where id = new.comment_id;
  else update public.comments set like_count = greatest(0, like_count - 1) where id = old.comment_id; end if;
  return null;
end $$;
revoke all on function public.comment_like_count() from public, anon, authenticated, service_role;
grant execute on function public.comment_like_count() to service_role;
drop trigger if exists trg_comment_like_count on public.comment_reactions;
create trigger trg_comment_like_count after insert or delete on public.comment_reactions for each row execute function public.comment_like_count();

-- ── 5. mentions ──────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.post_mentions (
  post_id    bigint not null references public.posts(id) on delete cascade,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (post_id, user_id)
);
create index if not exists idx_post_mentions_user on public.post_mentions (user_id);
alter table public.post_mentions enable row level security;
do $$ begin
  create policy "mentions: read with the post" on public.post_mentions for select using (exists (select 1 from public.posts p where p.id = post_mentions.post_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "mentions: the post's author names people" on public.post_mentions for insert
    with check (exists (select 1 from public.posts p where p.id = post_mentions.post_id and p.user_id = (select auth.uid())) and user_id <> (select auth.uid()));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy "mentions: the post's author removes them" on public.post_mentions for delete using (exists (select 1 from public.posts p where p.id = post_mentions.post_id and p.user_id = (select auth.uid())));
exception when duplicate_object then null; end $$;
revoke all on table public.post_mentions from public, anon, authenticated, service_role;
grant select on table public.post_mentions to anon;
grant select, insert, delete on table public.post_mentions to authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.post_mentions to service_role;
create or replace function public.post_mentions_added() returns trigger
language plpgsql security definer set search_path = public as $$
declare author uuid;
begin
  if (select count(*) from public.post_mentions m where m.post_id = new.post_id) >= 20 then raise exception 'A post can mention at most 20 people' using errcode = '23514'; end if;
  if exists (select 1 from public.profiles p where p.id = new.user_id and p.account_type = 'deleted') then raise exception 'This member deleted their account' using errcode = '42501'; end if;
  if exists (select 1 from public.user_blocks b join public.posts p on p.id = new.post_id where (b.blocker = new.user_id and b.blocked = p.user_id) or (b.blocker = p.user_id and b.blocked = new.user_id)) then
    raise exception 'You can''t mention this person' using errcode = '42501';
  end if;
  new.created_at := now();
  select user_id into author from public.posts where id = new.post_id;
  insert into public.notifications (user_id, type, from_user, post_id, message) values (new.user_id, 'mention', author, new.post_id, 'mentioned you in a post');
  return new;
end $$;
revoke all on function public.post_mentions_added() from public, anon, authenticated, service_role;
grant execute on function public.post_mentions_added() to service_role;
drop trigger if exists trg_post_mentions_added on public.post_mentions;
create trigger trg_post_mentions_added before insert on public.post_mentions for each row execute function public.post_mentions_added();

-- ── 6. hashtags ──────────────────────────────────────────────────────────────────────────────────────────
create table if not exists public.post_tags (
  post_id bigint not null references public.posts(id) on delete cascade,
  tag     text not null,
  primary key (post_id, tag),
  constraint post_tags_tag_len check (length(tag) between 1 and 60)
);
create index if not exists idx_post_tags_tag on public.post_tags (tag, post_id desc);
alter table public.post_tags enable row level security;
do $$ begin
  create policy "tags: read with the post" on public.post_tags for select using (exists (select 1 from public.posts p where p.id = post_tags.post_id));
exception when duplicate_object then null; end $$;
revoke all on table public.post_tags from public, anon, authenticated, service_role;
grant select on table public.post_tags to anon, authenticated;
grant select, insert, update, delete, truncate, references, trigger on table public.post_tags to service_role;
-- a tag is "#" + letters, digits or _ (Arabic letters too), up to 60, stored in lower case; at most 30 per post
create or replace function public.post_tags_sync() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'UPDATE' and new.body is not distinct from old.body then return null; end if;
  delete from public.post_tags where post_id = new.id;
  insert into public.post_tags (post_id, tag)
    select distinct new.id, lower(left(m[1], 60)) from regexp_matches(coalesce(new.body, ''), '(?:^|[^[:alnum:]_&])#([[:alnum:]_]+)', 'g') as m limit 30
  on conflict do nothing;
  return null;
end $$;
revoke all on function public.post_tags_sync() from public, anon, authenticated, service_role;
grant execute on function public.post_tags_sync() to service_role;
drop trigger if exists trg_post_tags_sync on public.posts;
create trigger trg_post_tags_sync after insert or update of body on public.posts for each row execute function public.post_tags_sync();
-- the posts written before this migration
insert into public.post_tags (post_id, tag)
  select distinct p.id, lower(left(m[1], 60)) from public.posts p, regexp_matches(coalesce(p.body, ''), '(?:^|[^[:alnum:]_&])#([[:alnum:]_]+)', 'g') as m
on conflict do nothing;

notify pgrst, 'reload schema';
