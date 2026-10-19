-- ═════════════════════════════════════════════════════════════════════
-- 0048 — search that stays fast with 100,000 members (area social: S-18, J-SOCIAL-28/45/46; tools/scale/timings.py)
--   Row-level security keeps the trigram indexes out of a search: "ilike" is not leakproof, so under RLS PostgreSQL must check
--   every row's policy first and scans the whole table (search_all took 200–700 ms, the people search 57 ms at 100k).
--   1. search_all(q, n)              now SECURITY DEFINER and applies each table's read rule itself — the same as the policies:
--                                    members only; no deleted profile; posts outside groups; active listings and jobs; groups
--                                    that are public, listed, mine, joined or invited to; nobody blocked either way
--   2. find_people(q, spec, country) the Network page's people search and the @mention / Send pickers: name, company or
--                                    headline, a specialty (headline words) and a country; no deleted or blocked people, not me
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

create or replace function public.search_all(p_q text, p_limit int default 6) returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); q text := regexp_replace(trim(coalesce(p_q, '')), '\s+', ' ', 'g'); pat text; pre text;
        n int := least(greatest(coalesce(p_limit, 6), 1), 20); bl uuid[];
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  if length(q) < 2 or length(q) > 80 then return jsonb_build_object('q', q); end if;
  pre := replace(replace(replace(q, '\', '\\'), '%', '\%'), '_', '\_'); pat := '%' || pre || '%'; pre := pre || '%';
  bl := private.blocks_with_me();
  return jsonb_build_object('q', q,
    'people', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select p.id, p.name, p.headline, p.company, p.avatar_url, p.verified, p.location, p.country from public.profiles p
         where (p.name ilike pat or p.company ilike pat or p.headline ilike pat) and p.account_type is distinct from 'deleted' and p.id <> me and p.id <> all (bl)
         order by (p.name ilike pre) desc, (p.name ilike pat) desc, length(p.name), p.created_at desc limit n) x),
    'companies', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select c.id, c.slug, c.name, c.city, c.country, c.verified, c.logo_emoji, c.type from public.companies c
         where (c.name ilike pat or c.name_ar ilike pat) order by (c.name ilike pre) desc, c.verified desc nulls last, length(c.name) limit n) x),
    'products', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select r.id, r.name, r.category, r.price, r.unit, r.emoji, r.user_id, (select s.name from public.profiles s where s.id = r.user_id) as seller from public.products r
         where r.active and r.name ilike pat and r.user_id <> all (bl) order by (r.name ilike pre) desc, r.created_at desc limit n) x),
    'jobs', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select j.id, j.title, j.company, j.location, j.type, j.user_id from public.jobs j
         where j.active and (j.title ilike pat or j.company ilike pat) and j.user_id <> all (bl) order by (j.title ilike pre) desc, j.created_at desc limit n) x),
    'groups', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select g.id, g.name, g.emoji, g.type, g.member_count from public.groups g
         where g.name ilike pat
           and (g.type = 'public' or g.listed or g.created_by = me or public.is_group_member(g.id)
                or exists (select 1 from public.group_invites i where i.group_id = g.id and i.user_id = me))
         order by (g.name ilike pre) desc, g.member_count desc limit n) x),
    'posts', (select coalesce(jsonb_agg(to_jsonb(x)), '[]') from (
        select o.id, left(o.body, 240) as body, o.user_id, o.created_at, (select a.name from public.profiles a where a.id = o.user_id) as author from public.posts o
         where o.group_id is null and o.body ilike pat and o.user_id <> all (bl) order by o.created_at desc limit n) x));
end $$;
revoke all on function public.search_all(text, int) from public, anon, authenticated, service_role;
grant execute on function public.search_all(text, int) to authenticated, service_role;

create or replace function public.find_people(p_q text default null, p_spec text default null, p_country text default null, p_limit int default 30)
returns table (id uuid, name text, headline text, company text, country text, verified boolean, avatar_url text, location text,
               followers_count int, open_to_work boolean, hiring boolean)
language plpgsql stable security definer set search_path = public as $$
declare me uuid := auth.uid(); words text[]; sp text[]; bl uuid[]; n int := least(greatest(coalesce(p_limit, 30), 1), 60);
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  words := array(select '%' || replace(replace(replace(w, '\', '\\'), '%', '\%'), '_', '\_') || '%'
                   from unnest(regexp_split_to_array(left(trim(coalesce(p_q, '')), 80), '\s+')) w where w <> '' limit 5);
  sp := case p_spec
    when 'regulatory' then array['%regulat%', '%registration%', '%dossier%']
    when 'quality' then array['%QA %', '%QC %', '%quality%', '%GMP%']
    when 'procurement' then array['%procure%', '%purchas%', '%sourcing%', '%buyer%']
    when 'production' then array['%production%', '%manufactur%', '%plant%', '%operations%']
    when 'sales' then array['%sales%', '%marketing%', '%business development%', '%commercial%']
    when 'rnd' then array['%R&D%', '%research%', '%formulat%']
    when 'supply' then array['%supply%', '%distribut%', '%logistic%', '%import%', '%export%']
    when 'medical' then array['%medical%', '%pharmacist%', '%clinical%', '%doctor%', '%physician%']
    when 'management' then array['%CEO%', '%founder%', '%director%', '%chairman%', '%general manager%', '%managing%']
    else null end;
  if coalesce(array_length(words, 1), 0) = 0 and sp is null and nullif(p_country, '') is null then return; end if;
  bl := private.blocks_with_me();
  -- built per call so each word is a plain "ilike" the trigram indexes serve (a generic plan would scan)
  return query execute 'select * from (select p.id, p.name, p.headline, p.company, p.country::text, p.verified, p.avatar_url, p.location, p.followers_count, p.open_to_work, p.hiring
      from public.profiles p where p.id <> $1 and p.account_type is distinct from ''deleted'' and p.id <> all ($2)'
    || (select coalesce(string_agg(format(' and (p.name ilike %1$L or p.company ilike %1$L or p.headline ilike %1$L)', w), ''), '') from unnest(words) w)
    || case when sp is null then '' else ' and p.headline ilike any ($3)' end
    || case when nullif(p_country, '') is null then '' else ' and p.country = $4' end
    || ' limit 400) x order by x.verified desc nulls last, x.name limit $5'   -- the first 400 matches, then ordered: a common word stays fast
    using me, bl, sp, upper(left(coalesce(p_country, ''), 2)), n;
end $$;
revoke all on function public.find_people(text, text, text, int) from public, anon, authenticated, service_role;
grant execute on function public.find_people(text, text, text, int) to authenticated;

notify pgrst, 'reload schema';
