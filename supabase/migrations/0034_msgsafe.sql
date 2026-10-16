-- ═════════════════════════════════════════════════════════════════════
-- 0034 — messages and sign-up say the same thing in every language (phase 1b: S-15, B-05 notification text)
--   1. A "messaged <Company>" notification (company_message, 0032) was stored as an English sentence, so an Arabic reader saw
--      English. The notification now keeps only its data: the company (notifications.company_id, new) and the words of the
--      message (message = the first 80 characters); the app writes the sentence at display time in the reader's language.
--      Rows written before this keep their English sentence; the app shows them as they are (translated by the interface).
--      The "one notification a day per sender and company" rule matches both kinds of row.
--   2. S-15: the sign-up "Role" list stored its Arabic label ('الشؤون التنظيمية') when the interface was in Arabic. The list now
--      always sends the same English value (shown translated); the six Arabic labels the Arabic sign-up could have stored are
--      turned into that value here. Only a headline that is EXACTLY one of those six labels changes (the same role in the
--      canonical form, which the Arabic interface still shows in Arabic) — nothing a member wrote themselves is touched, and
--      the English "Regulatory Affairs" that the old preselected choice gave many members is left alone: whether they chose it
--      cannot be known, so it stays theirs to edit.
-- No new table or function (company_message is replaced; its grants are restated, 0026). Safe to run twice.
-- ═════════════════════════════════════════════════════════════════════

-- ── 1. company_message: data, not an English sentence ──
alter table public.notifications add column if not exists company_id bigint references public.companies (id) on delete cascade;
create index if not exists notifications_company_idx on public.notifications (company_id) where company_id is not null;

create or replace function public.company_message(p_company bigint, p_body text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  me uuid := (select auth.uid());
  v_to uuid; v_name text; v_id bigint;
  v_body text := btrim(coalesce(p_body, ''));
begin
  if me is null then raise exception 'Sign in to send a message' using errcode = '42501'; end if;
  if v_body = '' then raise exception 'Write a message first' using errcode = '22023'; end if;
  select a.user_id into v_to from public.company_answerer(p_company, 'quote') a;
  select name into v_name from public.companies where id = p_company;
  if v_to is null then
    raise exception 'Nobody at % answers messages on Drugbox yet — use the phone, email or WhatsApp on its Contact tab', coalesce(v_name, 'this company')
      using errcode = 'P0002';
  end if;
  if v_to = me then raise exception 'You answer this company''s messages yourself' using errcode = '22023'; end if;
  insert into public.messages (sender_id, receiver_id, body) values (me, v_to, v_body) returning id into v_id;
  if not exists (select 1 from public.notifications n where n.user_id = v_to and n.from_user = me and n.type = 'company_message'
                   and n.created_at > now() - interval '1 day'
                   and (n.company_id = p_company
                        or (n.company_id is null and n.message like 'messaged ' || replace(replace(replace(v_name, '\', '\\'), '%', '\%'), '_', '\_') || ': %'))) then
    insert into public.notifications (user_id, type, from_user, company_id, message)
    values (v_to, 'company_message', me, p_company, left(v_body, 80) || case when length(v_body) > 80 then '…' else '' end);
  end if;
  return jsonb_build_object('id', v_id, 'to', v_to);
end $$;
revoke all on function public.company_message(bigint, text) from public, anon, authenticated, service_role;
grant execute on function public.company_message(bigint, text) to authenticated, service_role;

-- ── 2. S-15: one stored value per sign-up role, whatever the interface language ──
update public.profiles set headline = case headline
    when 'الشؤون التنظيمية' then 'Regulatory Affairs'
    when 'مراقبة الجودة / ضمان الجودة' then 'Quality Control / QA'
    when 'المبيعات وتطوير الأعمال' then 'Sales & Business Dev'
    when 'الإنتاج' then 'Production'
    when 'البحث والتطوير / التركيبات' then 'R&D / Formulation'
    when 'الإدارة العليا' then 'CEO / Management' end
 where headline in ('الشؤون التنظيمية', 'مراقبة الجودة / ضمان الجودة', 'المبيعات وتطوير الأعمال', 'الإنتاج', 'البحث والتطوير / التركيبات', 'الإدارة العليا');

notify pgrst, 'reload schema';
