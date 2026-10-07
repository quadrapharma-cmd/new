-- ═════════════════════════════════════════════════════════════════════════════
-- DRUGBOX 0025 — small follow-ups after round 2 (docs/FIX-STATUS-2026-10.md: N-7, N-8, F-74)
-- Database only: the approved interface is untouched. Every block is re-runnable (tools/migration_check.py).
--   N-7    company documents (CEP, DMF, ISO … metadata: type, product, number, expiry, status) are for signed-in members only,
--          like the rest of the content graph since 0024 (F-26 privacy-first). The anon key reads neither company_documents
--          nor company_documents_public (0 rows). The live app never reads them before sign-in (it does not read them at all
--          today). REVERSIBLE: alter policy "documents: everyone reads metadata" on public.company_documents to public;
--   N-8    inviting someone to a private group tells them: a 'group_invite' notification ("<inviter> invited you to join the
--          private group "<name>"") — the live app shows any notification type with its sender and message. It is removed when
--          the invitation is withdrawn or declined without joining, and with the group (notifications.group_id, cascade).
--   F-74   the company address (slug) is made unique by the database: a new company whose slug is taken (two companies with the
--          same name created at the same moment, or a page the browser could not see) gets -2, -3 … (then a short random
--          suffix) instead of a unique violation. Same-slug inserts are serialised with a transaction lock, so a race cannot
--          slip through. An Arabic-only name gets 'company-<id>'. The slug still never changes on update (0020).
-- supabase/tests/small_followups.rls.sql checks each item.
-- ═════════════════════════════════════════════════════════════════════════════

-- ── 1. N-7 company documents: members only ─────────────────────────────────────────────────────
-- Done the 0024 way: the policy, not the grants. The anon key gets an empty answer (never an error), like every table of the
-- content graph — security_core.rls.sql requires that anon can query every table without an error. file_path stays ungranted.
alter policy "documents: everyone reads metadata" on public.company_documents to authenticated;

-- ── 2. N-8 a group invitation notifies the invited person ───────────────────────────────────────
alter table public.notifications add column if not exists group_id bigint references public.groups (id) on delete cascade;
create index if not exists idx_notifs_group on public.notifications (group_id) where group_id is not null;
create unique index if not exists idx_notifs_group_invite_once on public.notifications (user_id, group_id)
  where type = 'group_invite' and group_id is not null;

create or replace function public.notify_group_invite()
returns trigger language plpgsql security definer set search_path = public as $$
declare g text;
begin
  if new.invited_by is null or new.invited_by = new.user_id then return null; end if;   -- nobody to name / inviting yourself
  select name into g from public.groups where id = new.group_id;
  insert into public.notifications (user_id, type, from_user, group_id, message)
  values (new.user_id, 'group_invite', new.invited_by, new.group_id,
          'invited you to join the private group "' || left(coalesce(g, ''), 120) || '"')
  on conflict (user_id, group_id) where type = 'group_invite' and group_id is not null do nothing;
  return null;
end $$;
revoke all on function public.notify_group_invite() from public, anon, authenticated;
drop trigger if exists trg_notify_group_invite on public.group_invites;
create trigger trg_notify_group_invite after insert on public.group_invites for each row execute function public.notify_group_invite();

-- withdrawn or declined (not used up by joining): the notice goes too
create or replace function public.group_invite_withdrawn()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from public.group_members m where m.group_id = old.group_id and m.user_id = old.user_id) then
    delete from public.notifications where user_id = old.user_id and group_id = old.group_id and type = 'group_invite';
  end if;
  return null;
end $$;
revoke all on function public.group_invite_withdrawn() from public, anon, authenticated;
drop trigger if exists trg_group_invite_withdrawn on public.group_invites;
create trigger trg_group_invite_withdrawn after delete on public.group_invites for each row execute function public.group_invite_withdrawn();

-- ── 3. F-74 a unique company slug from the server ──────────────────────────────────────────────
-- security definer: the free-slug lookup must see every company, including pages row security hides from the caller
create or replace function public.companies_before_write() returns trigger
language plpgsql security definer set search_path = public as $$
declare base text; cand text; n int := 1;
begin
  if new.slug is null or new.slug = '' then
    new.slug := coalesce(nullif(public.slugify(new.name), ''), 'company') || '-' || coalesce(new.id::text, substr(md5(random()::text), 1, 6));
  end if;
  if tg_op = 'INSERT' or new.slug is distinct from old.slug then
    base := new.slug; cand := base;
    perform pg_advisory_xact_lock(hashtext('drugbox.company_slug:' || base));   -- the same slug is chosen one at a time
    while exists (select 1 from public.companies c where c.slug = cand and c.id is distinct from new.id) loop
      n := n + 1;
      cand := base || '-' || case when n <= 9 then n::text else substr(md5(random()::text || clock_timestamp()::text), 1, 6) end;
    end loop;
    new.slug := cand;
  end if;
  new.updated_at := now();
  return new;
end $$;
revoke all on function public.companies_before_write() from public, anon, authenticated;
drop trigger if exists trg_companies_before_write on public.companies;
create trigger trg_companies_before_write before insert or update on public.companies for each row execute function public.companies_before_write();

notify pgrst, 'reload schema';
