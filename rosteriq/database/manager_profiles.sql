create table if not exists public.manager_profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null,
  work_email text not null,
  employee_id text not null unique,
  created_at timestamptz not null default now()
);

alter table public.manager_profiles enable row level security;

drop policy if exists "Managers can read their own profile" on public.manager_profiles;
create policy "Managers can read their own profile"
  on public.manager_profiles
  for select
  to authenticated
  using ((select auth.uid()) = id);

drop policy if exists "Managers can create their own profile" on public.manager_profiles;
create policy "Managers can create their own profile"
  on public.manager_profiles
  for insert
  to authenticated
  with check ((select auth.uid()) = id);

drop policy if exists "Managers can update their own profile" on public.manager_profiles;
create policy "Managers can update their own profile"
  on public.manager_profiles
  for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

grant select, insert, update on table public.manager_profiles to authenticated;
