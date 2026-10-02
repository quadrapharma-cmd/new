-- ═════════════════════════════════════════════════════════════════════
-- DRUGBOX 0009 — buy requests get an id automatically (step D1)
-- enquiries.id was text with no default (a demo-era shape), so inserts from the app failed.
-- ═════════════════════════════════════════════════════════════════════
alter table public.enquiries alter column id set default ('E' || substr(md5(random()::text || clock_timestamp()::text), 1, 10));
create index if not exists idx_enquiries_live on public.enquiries (type, status, created_at desc);
create index if not exists idx_products_live on public.products (type, active, created_at desc);

notify pgrst, 'reload schema';
