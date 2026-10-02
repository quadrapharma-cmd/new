-- RLS & guard tests for 004. Each check prints PASS/FAIL. Runs as real API roles with a JWT subject.
\set QUIET on
set client_min_messages = warning;
begin;
-- people
insert into auth.users (id, email) values ('11111111-1111-1111-1111-111111111111','owner@x'),('22222222-2222-2222-2222-222222222222','member@x'),
  ('33333333-3333-3333-3333-333333333333','outsider@x'),('44444444-4444-4444-4444-444444444444','admin@x') on conflict do nothing;
insert into public.profiles (id, name) values ('11111111-1111-1111-1111-111111111111','Owner'),('22222222-2222-2222-2222-222222222222','Member'),
  ('33333333-3333-3333-3333-333333333333','Outsider'),('44444444-4444-4444-4444-444444444444','Admin') on conflict (id) do nothing;
update public.profiles set role='admin' where id='44444444-4444-4444-4444-444444444444';
create temp table r (n serial, name text, ok boolean);
grant all on r to authenticated; grant all on r_n_seq to authenticated;
create or replace function pg_temp.as_user(u text) returns void language plpgsql as $$ begin perform set_config('request.jwt.claim.sub', u, true); perform set_config('role','authenticated', true); end $$;

-- owner creates a company → becomes owner member automatically
select pg_temp.as_user('11111111-1111-1111-1111-111111111111');
insert into public.companies (owner_id, name, type) values ('11111111-1111-1111-1111-111111111111','Test Pharma','Manufacturer');
insert into r(name,ok) select 'creator becomes owner member', exists(select 1 from public.company_members m join public.companies c on c.id=m.company_id where c.name='Test Pharma' and m.role='owner');
insert into r(name,ok) select 'slug filled automatically', (select slug like 'test-pharma-%' from public.companies where name='Test Pharma');
-- owner adds a member (consent starts off)
insert into public.company_members (company_id, user_id, role, accepted, show_public) select id,'22222222-2222-2222-2222-222222222222','sales',true,true from public.companies where name='Test Pharma';
insert into r(name,ok) select 'added member: consent off until they agree', (select not accepted and not show_public from public.company_members where user_id='22222222-2222-2222-2222-222222222222');
insert into public.company_sites (company_id, name, type) select id,'Giza plant','factory' from public.companies where name='Test Pharma';
insert into public.site_certificates (site_id, company_id, name, expiry) select s.id, s.company_id, 'WHO-GMP', '2027-04-01' from public.company_sites s where s.name='Giza plant';
insert into public.company_documents (company_id, type, product, number, created_by, file_path) select id,'CEP','Metformin HCl','R1-CEP 2019-1','11111111-1111-1111-1111-111111111111','private/cep.pdf' from public.companies where name='Test Pharma';

-- member: can give consent, cannot promote themself
select pg_temp.as_user('22222222-2222-2222-2222-222222222222');
update public.company_members set accepted=true, show_public=true where user_id='22222222-2222-2222-2222-222222222222';
insert into r(name,ok) select 'member can give their own consent', (select accepted from public.company_members where user_id='22222222-2222-2222-2222-222222222222');
do $$ begin begin update public.company_members set role='owner' where user_id='22222222-2222-2222-2222-222222222222'; insert into r(name,ok) values ('member cannot promote themself to owner', false);
  exception when others then insert into r(name,ok) values ('member cannot promote themself to owner', true); end; end $$;
do $$ begin begin insert into public.company_sites (company_id,name) select id,'Fake site' from public.companies where name='Test Pharma'; insert into r(name,ok) values ('sales member cannot add sites', false);
  exception when others then insert into r(name,ok) values ('sales member cannot add sites', true); end; end $$;

-- outsider: reads public data, cannot edit anything, cannot see private file path
select pg_temp.as_user('33333333-3333-3333-3333-333333333333');
insert into r(name,ok) select 'outsider reads the company, sites and certificates', (select count(*) from public.site_certificates where name='WHO-GMP')=1;
update public.companies set name='Hacked' where name='Test Pharma';
insert into r(name,ok) select 'outsider cannot rename the company (0 rows changed)', exists(select 1 from public.companies where name='Test Pharma');
do $$ begin begin perform file_path from public.company_documents limit 1; insert into r(name,ok) values ('outsider cannot read private document file paths', false);
  exception when insufficient_privilege then insert into r(name,ok) values ('outsider cannot read private document file paths', true); end; end $$;
insert into r(name,ok) select 'outsider still sees the passport metadata', (select count(*) from public.company_documents_public where type='CEP')=1;
do $$ begin begin insert into public.company_members (company_id,user_id,role) select id,'33333333-3333-3333-3333-333333333333','admin' from public.companies where name='Test Pharma'; insert into r(name,ok) values ('outsider cannot add themself to a team', false);
  exception when others then insert into r(name,ok) values ('outsider cannot add themself to a team', true); end; end $$;
do $$ begin begin insert into public.verification_requests (company_id, submitted_by, registry) select id,'33333333-3333-3333-3333-333333333333','999' from public.companies where name='Test Pharma'; insert into r(name,ok) values ('outsider cannot submit verification for another company', false);
  exception when others then insert into r(name,ok) values ('outsider cannot submit verification for another company', true); end; end $$;

-- owner: cannot self-verify a document or a verification request
select pg_temp.as_user('11111111-1111-1111-1111-111111111111');
do $$ begin begin update public.company_documents set status='verified' where number='R1-CEP 2019-1'; insert into r(name,ok) values ('owner cannot mark their own document verified', false);
  exception when others then insert into r(name,ok) values ('owner cannot mark their own document verified', true); end; end $$;
update public.companies set status='pending', registry=null where name='Test Pharma';
insert into public.verification_requests (company_id, submitted_by, registry, licence_path) select id,'11111111-1111-1111-1111-111111111111','123456','private/lic.pdf' from public.companies where name='Test Pharma';
update public.verification_requests set status='approved' where registry='123456';
insert into r(name,ok) select 'owner cannot approve their own verification', (select status='pending' from public.verification_requests where registry='123456');
insert into r(name,ok) select 'level before approval = 0', public.company_tier((select id from public.companies where name='Test Pharma'))=0;

-- platform admin approves → company becomes verified + licensed; checks the certificate → level 3
select pg_temp.as_user('44444444-4444-4444-4444-444444444444');
update public.verification_requests set status='approved' where registry='123456';
insert into r(name,ok) select 'admin approval verifies the company', (select status='verified' and tax_verified and licensed from public.companies where name='Test Pharma');
insert into r(name,ok) select 'level after approval = 2 (certificate not yet checked)', public.company_tier((select id from public.companies where name='Test Pharma'))=2;
update public.site_certificates set checked_at=now() where name='WHO-GMP';
insert into r(name,ok) select 'level with a checked valid GMP certificate = 3', public.company_tier((select id from public.companies where name='Test Pharma'))=3;
update public.company_documents set status='verified' where number='R1-CEP 2019-1';
insert into r(name,ok) select 'admin can verify a document', (select status='verified' from public.company_documents where number='R1-CEP 2019-1');

-- owner edits the checked certificate's expiry → check is cleared, level drops back to 2
select pg_temp.as_user('11111111-1111-1111-1111-111111111111');
update public.site_certificates set expiry='2028-01-01' where name='WHO-GMP';
insert into r(name,ok) select 'company edit of a checked certificate clears the check', (select checked_at is null from public.site_certificates where name='WHO-GMP');
insert into r(name,ok) select 'level returns to 2 until Drugbox re-checks', public.company_tier((select id from public.companies where name='Test Pharma'))=2;
do $$ begin begin update public.site_certificates set checked_at=now() where name='WHO-GMP'; 
  insert into r(name,ok) select 'owner cannot mark a certificate checked', (select checked_at is null from public.site_certificates where name='WHO-GMP');
  exception when others then insert into r(name,ok) values ('owner cannot mark a certificate checked', true); end; end $$;

-- search by active ingredient in Arabic
reset role;
select set_config('role','postgres',true);
insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, role) select id,'Metforal 500 mg','Metformin HCl','ميتفورمين','manufacturer' from public.companies where name='Test Pharma';
select pg_temp.as_user('33333333-3333-3333-3333-333333333333');
insert into r(name,ok) select 'directory search finds the company by Arabic active ingredient', exists(select 1 from public.search_companies('ميتفورمين') where name='Test Pharma');

reset role;
select (case when ok then 'PASS  ' else 'FAIL  ' end) || name from r order by n;
select 'TOTAL ' || count(*) filter (where ok) || ' / ' || count(*) from r;
rollback;
