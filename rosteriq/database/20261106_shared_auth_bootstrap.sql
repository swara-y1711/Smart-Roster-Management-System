-- Bootstrap every Supabase Auth user into the single seeded RosterIQ workspace.
-- This migration deliberately leaves the existing RLS policies unchanged.

create table if not exists public.app_settings (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

revoke all on table public.app_settings from public, anon, authenticated;

do $$
declare
  candidate record;
  candidate_count integer;
  selected_organization uuid;
begin
  for candidate in
    select o.id, o.name, count(e.id)::integer as employee_count
    from public.organizations o
    left join public.employees e on e.organization_id = o.id
    group by o.id, o.name
    order by count(e.id) desc, o.created_at asc, o.id asc
  loop
    raise notice 'RosterIQ shared organization candidate: id=%, name=%, employees=%',
      candidate.id, candidate.name, candidate.employee_count;
  end loop;

  select o.id
    into selected_organization
    from public.organizations o
    left join public.employees e on e.organization_id = o.id
   group by o.id, o.created_at
   order by count(e.id) desc, o.created_at asc, o.id asc
   limit 1;

  if selected_organization is null then
    raise exception 'Cannot configure RosterIQ shared organization: no organizations exist.';
  end if;

  select count(*) into candidate_count
    from public.organizations;
  if candidate_count > 1 then
    raise notice 'Using organization % with the most seeded employees as the shared workspace.',
      selected_organization;
  end if;

  insert into public.app_settings (key, value)
  values ('rosteriq.shared_organization_id', selected_organization::text)
  on conflict (key) do nothing;
end;
$$;

create or replace function public.bootstrap_rosteriq_user(
  p_user_id uuid,
  p_email text,
  p_metadata jsonb default '{}'::jsonb
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  shared_organization uuid;
  profile_name text;
  profile_email text;
begin
  select value::uuid
    into shared_organization
    from public.app_settings
   where key = 'rosteriq.shared_organization_id';

  if shared_organization is null then
    raise exception 'RosterIQ shared organization is not configured.';
  end if;

  profile_email := coalesce(nullif(trim(p_email), ''), 'user-' || p_user_id::text || '@invalid.local');
  profile_name := coalesce(
    nullif(trim(p_metadata ->> 'full_name'), ''),
    nullif(trim(p_metadata ->> 'name'), ''),
    profile_email
  );

  insert into public.manager_profiles (id, full_name, work_email, employee_id)
  values (p_user_id, profile_name, profile_email, 'AUTH-' || replace(p_user_id::text, '-', ''))
  on conflict (id) do nothing;

  insert into public.organization_members (organization_id, manager_id)
  values (shared_organization, p_user_id)
  on conflict (organization_id, manager_id) do nothing;
end;
$$;

revoke all on function public.bootstrap_rosteriq_user(uuid, text, jsonb)
  from public, anon, authenticated;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.bootstrap_rosteriq_user(new.id, new.email, new.raw_user_meta_data);
  return new;
end;
$$;

revoke all on function public.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

do $$
declare
  auth_user record;
begin
  for auth_user in
    select id, email, raw_user_meta_data from auth.users
  loop
    perform public.bootstrap_rosteriq_user(
      auth_user.id,
      auth_user.email,
      coalesce(auth_user.raw_user_meta_data, '{}'::jsonb)
    );
  end loop;
end;
$$;

-- The backend calls this RPC before normal reads so a valid user can recover
-- if a profile or membership was removed after the trigger/backfill ran.
create or replace function public.bootstrap_current_user()
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  current_user_id uuid := auth.uid();
  current_email text := (auth.jwt() ->> 'email');
  current_metadata jsonb := coalesce(auth.jwt() -> 'user_metadata', '{}'::jsonb);
begin
  if current_user_id is null then
    raise exception 'Authentication is required.' using errcode = '42501';
  end if;
  perform public.bootstrap_rosteriq_user(current_user_id, current_email, current_metadata);
end;
$$;

revoke all on function public.bootstrap_current_user() from public, anon;
grant execute on function public.bootstrap_current_user() to authenticated;
