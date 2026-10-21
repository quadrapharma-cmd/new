-- ═════════════════════════════════════════════════════════════════════
-- 0049 — a like on a comment tells the comment's author (area social: S-13, found by the independent check)
--   comment_like_notice   one 'comment_like' notice per liker and comment (a like taken back and given again adds none);
--                         never for one's own comment; the notice opens the post with its comments (post_id, comment_id)
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════
create or replace function public.comment_like_notice() returns trigger
language plpgsql security definer set search_path = public as $$
declare c record;
begin
  select x.user_id, x.post_id, left(x.body, 140) as body into c from public.comments x where x.id = new.comment_id;
  if not found or c.user_id = new.user_id then return null; end if;
  if not exists (select 1 from public.notifications n where n.user_id = c.user_id and n.from_user = new.user_id and n.type = 'comment_like' and n.comment_id = new.comment_id) then
    insert into public.notifications (user_id, type, from_user, post_id, comment_id, message) values (c.user_id, 'comment_like', new.user_id, c.post_id, new.comment_id, c.body);
  end if;
  return null;
end $$;
revoke all on function public.comment_like_notice() from public, anon, authenticated, service_role;
grant execute on function public.comment_like_notice() to service_role;
drop trigger if exists trg_comment_like_notice on public.comment_reactions;
create trigger trg_comment_like_notice after insert on public.comment_reactions for each row execute function public.comment_like_notice();

notify pgrst, 'reload schema';
