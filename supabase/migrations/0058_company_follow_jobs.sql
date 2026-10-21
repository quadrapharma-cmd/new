-- ═════════════════════════════════════════════════════════════════════
-- 0058 — following a company brings its news (J-BUSINESS-05); a company's open positions on its page (J-BUSINESS-11)
--   A member who follows a company is told when that company publishes something new in the marketplace: a listing posted by
--   the company (or by its owner), a surplus offer or a licensing dossier. One notification per new listing per follower
--   (type 'company_listing', data: company, listing, kind; message: the listing's title) — never to the lister. Notices are kept short and as data (the app
--   writes the sentence in the reader's language).
--   company_jobs(company): the open positions the company's own team posted under its name (jobs.company = the company's
--   name, posted by a member) — what its page's Jobs tab lists; an application from there is a job deal to the company.
-- Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

create or replace function public.notify_company_followers(p_companies bigint[], p_actor uuid, p_title text, p_kind text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_companies is null or cardinality(p_companies) = 0 then return; end if;
  insert into public.notifications (user_id, type, from_user, company_id, message, data)
  select distinct on (f.user_id) f.user_id, 'company_listing', p_actor, f.company_id, left(coalesce(p_title, ''), 200),
         jsonb_build_object('company', c.name, 'listing', left(coalesce(p_title, ''), 200), 'kind', p_kind)
    from public.company_followers f join public.companies c on c.id = f.company_id
   where f.company_id = any(p_companies) and f.user_id is distinct from p_actor and c.status <> 'suspended'
   order by f.user_id, f.company_id;
end $$;
revoke all on function public.notify_company_followers(bigint[], uuid, text, text) from public, anon, authenticated, service_role;

-- a new marketplace listing: its company (products.company_id once the marketplace stores it), else the companies its lister owns
create or replace function public.products_notify_followers() returns trigger language plpgsql security definer set search_path = public as $$
declare v_co bigint := nullif(to_jsonb(new) ->> 'company_id', '')::bigint;
begin
  if coalesce(new.active, true) is not true then return null; end if;
  perform public.notify_company_followers(
    case when v_co is not null then array[v_co] else array(select id from public.companies where owner_id = new.user_id and status <> 'suspended' limit 5) end,
    new.user_id, new.name, coalesce(new.type, 'supply'));
  return null;
end $$;
revoke all on function public.products_notify_followers() from public, anon, authenticated, service_role;
drop trigger if exists trg_products_notify_followers on public.products;
create trigger trg_products_notify_followers after insert on public.products for each row execute function public.products_notify_followers();

create or replace function public.company_listings_notify_followers() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.active is not true then return null; end if;
  perform public.notify_company_followers(array[new.company_id], new.created_by, new.product, new.kind);
  return null;
end $$;
revoke all on function public.company_listings_notify_followers() from public, anon, authenticated, service_role;
drop trigger if exists trg_company_listings_notify_followers on public.company_listings;
create trigger trg_company_listings_notify_followers after insert on public.company_listings for each row execute function public.company_listings_notify_followers();

create or replace function public.company_jobs(p_company bigint) returns json language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object('id', j.id, 'title', j.title, 'type', j.type, 'location', j.location, 'created_at', j.created_at) order by j.created_at desc), '[]'::json)
  from public.companies c join public.jobs j on lower(btrim(j.company)) = lower(btrim(c.name))
  where c.id = p_company and c.status <> 'suspended' and j.active and auth.uid() is not null and public.company_has_member(c.id, j.user_id)
$$;
create index if not exists idx_jobs_company_key on public.jobs (lower(btrim(company))) where active;
revoke all on function public.company_jobs(bigint) from public, anon, authenticated, service_role;
grant execute on function public.company_jobs(bigint) to authenticated, service_role;

notify pgrst, 'reload schema';
