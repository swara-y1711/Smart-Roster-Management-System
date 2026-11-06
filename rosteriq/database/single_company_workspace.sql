-- Keep organization records as internal workspace boundaries, but prevent
-- authenticated users from creating, renaming, or deleting company workspaces.
drop policy if exists "RosterIQ authenticated users can create organizations"
  on public.organizations;
drop policy if exists "RosterIQ members can update their organizations"
  on public.organizations;
drop policy if exists "RosterIQ members can delete their organizations"
  on public.organizations;
revoke insert, update, delete on table public.organizations from anon, authenticated;

drop function if exists public.create_organization(text);

-- Allow authenticated managers to create only their own profile. The profile
-- ID is the auth.users ID; the frontend insert is guarded by the primary key
-- and recovers an existing same-user profile if creation races.
drop policy if exists "Managers can create their own profile"
  on public.manager_profiles;
create policy "Managers can create their own profile"
  on public.manager_profiles
  for insert
  to authenticated
  with check ((select auth.uid()) = id);

revoke insert on table public.manager_profiles from public, anon;
grant insert on table public.manager_profiles to authenticated;
