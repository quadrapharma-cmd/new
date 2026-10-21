-- ═════════════════════════════════════════════════════════════════════
-- 0048 — search that stays fast with 100,000 members (area social: S-18, J-SOCIAL-28/45/46; tools/scale/timings.py)
--   Row-level security keeps the trigram indexes out of a search: "ilike" is not leakproof, so under RLS PostgreSQL must check
--   every row's policy first and scans the whole table (search_all took 200–700 ms, the people search 57 ms at 100k).
--   1. search_all(q, n)              now SECURITY DEFINER and applies each table's read rule itself — the same as the policies:
--                                    members only; no deleted profile; posts outside groups; active listings and jobs; groups
--                                    that are public, listed, mine, joined or invited to; nobody blocked either way
--   3. export_my_data()              v2: also endorsements, reposts, comment likes, mentions, saved searches, my reports, my blocks
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
    || ' limit 400) x order by (x.id = any ($6)) desc,'
    || ' x.verified desc nulls last, x.name limit $5'   -- my connections first (a picker names the colleague I mean)   -- the first 400 matches, then ordered: a common word stays fast
    using me, bl, sp, upper(left(coalesce(p_country, ''), 2)), n,
          array(select case when c.requester = me then c.addressee else c.requester end from public.connections c
                 where c.status = 'accepted' and (c.requester = me or c.addressee = me) limit 5000);
end $$;
revoke all on function public.find_people(text, text, text, int) from public, anon, authenticated, service_role;
grant execute on function public.find_people(text, text, text, int) to authenticated;

-- 3. the data export (Settings → Download my data) also lists what the area social tables keep about the member
create or replace function public.export_my_data() returns jsonb
language plpgsql stable set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'Sign in first' using errcode = '42501'; end if;
  return jsonb_build_object(
    'exported_at', now(), 'format', 'Drugbox personal data export v2',
    'profile', (select to_jsonb(p) from public.my_profile() p),
    'settings', (select to_jsonb(s) - 'unsub_token' from public.member_settings s where s.user_id = me),
    'posts', coalesce((select jsonb_agg(jsonb_build_object('id', x.id, 'body', x.body, 'category', x.category, 'created_at', x.created_at,
                 'media', (select coalesce(jsonb_agg(jsonb_build_object('url', m.url, 'name', m.name, 'type', m.type)), '[]'::jsonb) from public.post_media m where m.post_id = x.id))
                 order by x.created_at) from public.posts x where x.user_id = me), '[]'::jsonb),
    'comments', coalesce((select jsonb_agg(jsonb_build_object('post', c.post_id, 'body', c.body, 'created_at', c.created_at) order by c.created_at) from public.comments c where c.user_id = me), '[]'::jsonb),
    'reactions', coalesce((select jsonb_agg(jsonb_build_object('post', r.post_id, 'kind', r.kind)) from public.reactions r where r.user_id = me), '[]'::jsonb),
    'saved_posts', coalesce((select jsonb_agg(s.post_id) from public.saved_posts s where s.user_id = me), '[]'::jsonb),
    'connections', coalesce((select jsonb_agg(jsonb_build_object('with', case when c.requester = me then c.addressee else c.requester end,
                 'name', (select q.name from public.profiles q where q.id = case when c.requester = me then c.addressee else c.requester end), 'status', c.status, 'sent_by_me', c.requester = me))
                 from public.connections c where c.requester = me or c.addressee = me), '[]'::jsonb),
    'following', coalesce((select jsonb_agg(f.person_id) from public.person_followers f where f.user_id = me), '[]'::jsonb),
    'messages', coalesce((select jsonb_agg(jsonb_build_object('from_me', m.sender_id = me, 'with', case when m.sender_id = me then m.receiver_id else m.sender_id end,
                 'body', m.body, 'created_at', m.created_at, 'read_at', m.read_at) order by m.id)
                 from (select * from public.messages m2 where m2.sender_id = me or m2.receiver_id = me order by m2.id desc limit 10000) m), '[]'::jsonb),
    'job_applications', coalesce((select jsonb_agg(to_jsonb(a)) from public.job_applications a where a.user_id = me), '[]'::jsonb),
    'saved_jobs', coalesce((select jsonb_agg(s.job_id) from public.saved_jobs s where s.user_id = me), '[]'::jsonb),
    'listings', coalesce((select jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'category', p.category, 'created_at', p.created_at)) from public.products p where p.user_id = me), '[]'::jsonb),
    'jobs_posted', coalesce((select jsonb_agg(jsonb_build_object('id', j.id, 'title', j.title, 'created_at', j.created_at)) from public.jobs j where j.user_id = me), '[]'::jsonb),
    'groups', coalesce((select jsonb_agg(jsonb_build_object('group', g.group_id, 'role', g.role)) from public.group_members g where g.user_id = me), '[]'::jsonb),
    'companies', coalesce((select jsonb_agg(jsonb_build_object('company', m.company_id, 'role', m.role)) from public.company_members m where m.user_id = me), '[]'::jsonb),
    'payments', coalesce((select jsonb_agg(jsonb_build_object('reference', o.merchant_ref, 'product', o.product_code, 'amount_egp', o.amount_cents / 100.0, 'method', o.method, 'status', o.status, 'created_at', o.created_at, 'paid_at', o.paid_at))
                 from public.payment_orders o where o.user_id = me), '[]'::jsonb),
    'skills_endorsed_by_me', coalesce((select jsonb_agg(jsonb_build_object('person', e.profile_id, 'skill', e.skill, 'created_at', e.created_at)) from public.skill_endorsements e where e.endorser = me), '[]'::jsonb),
    'my_endorsements', coalesce((select jsonb_agg(jsonb_build_object('skill', e.skill, 'by', e.endorser)) from public.skill_endorsements e where e.profile_id = me), '[]'::jsonb),
    'reposts', coalesce((select jsonb_agg(jsonb_build_object('post', r.post_id, 'note', r.note, 'created_at', r.created_at)) from public.reposts r where r.user_id = me), '[]'::jsonb),
    'comment_likes', coalesce((select jsonb_agg(c.comment_id) from public.comment_reactions c where c.user_id = me), '[]'::jsonb),
    'mentioned_in', coalesce((select jsonb_agg(m.post_id) from public.post_mentions m where m.user_id = me), '[]'::jsonb),
    'saved_searches', coalesce((select jsonb_agg(jsonb_build_object('name', s.name, 'query', s.q, 'filters', s.filters, 'alert', s.alert)) from public.saved_searches s where s.user_id = me), '[]'::jsonb),
    'reports_i_made', coalesce((select jsonb_agg(jsonb_build_object('person', r.reported, 'reason', r.reason, 'note', r.note, 'status', r.status, 'created_at', r.created_at)) from public.member_reports r where r.reporter = me), '[]'::jsonb),
    'people_i_blocked', coalesce((select jsonb_agg(b.blocked) from public.user_blocks b where b.blocker = me), '[]'::jsonb),
    'notifications', coalesce((select jsonb_agg(jsonb_build_object('type', n.type, 'message', n.message, 'created_at', n.created_at) order by n.id desc) from (select * from public.notifications n2 where n2.user_id = me order by n2.id desc limit 1000) n), '[]'::jsonb)
  );
end $$;
revoke all on function public.export_my_data() from public, anon, authenticated, service_role;
grant execute on function public.export_my_data() to authenticated;

notify pgrst, 'reload schema';
