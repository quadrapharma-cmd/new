-- ═════════════════════════════════════════════════════════════════════
-- 0046 — a connection's phone number, when they chose to share it (area social: S-24; Settings → Privacy)
--   connection_phone(p_user)   the phone of p_user for the signed-in member — only when the two are connected, neither has
--                              blocked the other, and p_user switched on "Let my connections see my phone number"
--                              (member_settings.phone_connections). Otherwise null. The phone column itself stays private (0036).
-- Every function grants its own privileges (0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════
create or replace function public.connection_phone(p_user uuid) returns text
language sql stable security definer set search_path = public as $$
  select p.phone from public.profiles p
    join public.member_settings s on s.user_id = p.id and s.phone_connections
   where p.id = p_user and auth.uid() is not null and p_user <> auth.uid() and p.account_type is distinct from 'deleted'
     and exists (select 1 from public.connections c where c.status = 'accepted'
                  and ((c.requester = auth.uid() and c.addressee = p_user) or (c.requester = p_user and c.addressee = auth.uid())))
     and not private.blocked_between(auth.uid(), p_user)
     and nullif(trim(p.phone), '') is not null
$$;
revoke all on function public.connection_phone(uuid) from public, anon, authenticated, service_role;
grant execute on function public.connection_phone(uuid) to authenticated;

notify pgrst, 'reload schema';
