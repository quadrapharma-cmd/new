-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0002 — feed paging (step B2)
-- Keyset paging reads exactly one page however many posts exist.
-- ═════════════════════════════════════════════════════════════════════
create index if not exists idx_posts_created_id on public.posts (created_at desc, id desc);      -- feed pages
create index if not exists idx_comments_post_created on public.comments (post_id, created_at, id); -- comments of a post, in order
create index if not exists idx_reactions_user_post on public.reactions (user_id, post_id);         -- "did I react to these?"

-- refresh the API's schema cache so new tables, functions and relationships are usable at once
notify pgrst, 'reload schema';
