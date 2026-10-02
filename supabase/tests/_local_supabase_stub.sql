-- Minimal Supabase environment so migrations and RLS run exactly as on Supabase
create extension if not exists pgcrypto;
create schema if not exists auth; create schema if not exists storage; create schema if not exists extensions;
do $$ begin create role anon nologin; exception when duplicate_object then null; end $$;
do $$ begin create role authenticated nologin; exception when duplicate_object then null; end $$;
do $$ begin create role service_role nologin bypassrls; exception when duplicate_object then null; end $$;
create table if not exists auth.users (id uuid primary key default gen_random_uuid(), email text unique, encrypted_password text, raw_user_meta_data jsonb default '{}'::jsonb, created_at timestamptz default now());
alter table auth.users add column if not exists encrypted_password text;
create or replace function auth.uid() returns uuid language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.sub', true), ''), (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'))::uuid $$;
create or replace function auth.role() returns text language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.role', true), ''), (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role'), 'anon') $$;
create or replace function auth.jwt() returns jsonb language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;
create table if not exists storage.buckets (id text primary key, name text, public boolean default false, file_size_limit bigint, allowed_mime_types text[]);
create table if not exists storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text, name text, owner uuid, created_at timestamptz default now(), metadata jsonb);
alter table storage.objects enable row level security;
create or replace function storage.foldername(name text) returns text[] language sql immutable as $$ select string_to_array(name, '/') $$;
grant usage on schema public, auth, storage to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
alter default privileges in schema public grant execute on functions to anon, authenticated, service_role;

-- PostgREST connects as `authenticator` and switches to anon / authenticated per request (as on Supabase)
do $$ begin create role authenticator login password 'local-only' noinherit; exception when duplicate_object then null; end $$;
grant anon, authenticated, service_role to authenticator;
-- storage.objects needs a name per bucket (as on Supabase) for replace/remove
do $$ begin alter table storage.objects add constraint objects_bucket_name_uq unique (bucket_id, name); exception when duplicate_object or duplicate_table then null; end $$;
grant select, insert, update, delete on storage.objects to authenticated; grant select on storage.objects to anon; grant select on storage.buckets to anon, authenticated;
