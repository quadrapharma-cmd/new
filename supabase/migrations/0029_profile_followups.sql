-- 0029 — Phase 1 profile follow-ups (docs/PRODUCT-GAPS-2026-10.md S-01, S-15).
-- S-15: the sign-up form asks for a company and a specialty; the new profile row now keeps them (they were dropped, so a new
--       member's profile showed only a name). The specialty is the member's first headline; both stay editable in Edit Profile.
-- S-01: Edit Profile writes website, phone and certifications, which had no size limit (F-43 covered the other columns), and a
--       website the browser refuses (javascript:, data:…) could be stored through the API. Limits and an http(s)/domain-only
--       website are now checked by the database too (the interface checks first and explains).
-- Re-run safe. Grants: no new table or function — handle_new_user keeps 0026's grants (restated here).

-- ── 1. S-15 handle_new_user copies company and specialty from the sign-up metadata ──
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare m jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
begin
  insert into public.profiles (id, name, company, headline)
  values (new.id,
          left(coalesce(nullif(trim(m->>'name'), ''), nullif(split_part(coalesce(new.email, ''), '@', 1), ''), 'Member'), 120),
          left(nullif(trim(m->>'company'), ''), 200),
          left(nullif(trim(m->>'specialty'), ''), 300));
  return new;
end;
$$;
revoke all on function public.handle_new_user() from public, anon, authenticated, service_role;
grant execute on function public.handle_new_user() to authenticated, service_role;

-- ── 2. S-01 contact fields: size limits and a website that can only be a web address ──
-- Same pattern as 0022 F-43: added NOT VALID, validated when existing rows allow it (older rows keep working; new and
-- edited rows must pass). Website: empty, or [http(s)://]host.tld[:port][/path…] with no spaces, quotes or angle brackets.
do $$ declare k record; begin
  for k in select * from (values
      ('profiles', 'profiles_contact_len', 'length(website) <= 300 and length(phone) <= 40 and length(certs) <= 500'),
      ('profiles', 'profiles_website_web', $c$website is null or website = '' or website ~* '^(https?://)?[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+(:[0-9]{1,5})?([/?#][^[:space:]"''<>`\\]*)?$'$c$)
    ) v(tbl, con, chk) loop
    if not exists (select 1 from pg_constraint where conname = k.con and conrelid = ('public.' || k.tbl)::regclass) then
      execute format('alter table public.%I add constraint %I check (%s) not valid', k.tbl, k.con, k.chk);
    end if;
    begin
      execute format('alter table public.%I validate constraint %I', k.tbl, k.con);
    exception when check_violation then
      raise notice 'DRUGBOX 0029: % has older rows that do not pass — the rule applies to new and edited rows', k.con;
    end;
  end loop;
end $$;

notify pgrst, 'reload schema';
