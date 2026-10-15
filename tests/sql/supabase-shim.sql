-- Imitação mínima do que o Supabase já traz pronto, para testar admin/supabase/schema.sql no PGlite.
-- (No Supabase de verdade isto NÃO roda: auth.*, os papéis e auth.jwt() já existem.)
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;

create schema auth;
create table auth.users (id uuid primary key, email text);
create table auth.sessions (id uuid primary key default gen_random_uuid(), user_id uuid);
create table auth.mfa_factors (id uuid primary key default gen_random_uuid(), user_id uuid, status text);

create function auth.jwt() returns jsonb language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb
$$;
create function auth.uid() returns uuid language sql stable as $$
  select nullif(auth.jwt() ->> 'sub', '')::uuid
$$;

grant usage on schema auth to anon, authenticated, service_role;
grant execute on all functions in schema auth to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;
-- O Supabase dá privilégios amplos por padrão; o schema.sql precisa revogar o que não deve existir.
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant execute on functions to anon, authenticated, service_role;
