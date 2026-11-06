do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'brands'
      and column_name = 'organization_id'
  ) and exists (select 1 from public.brands) then
    raise exception 'Brands already contain data. Assign each existing brand to an organization before applying this migration.';
  end if;

  if (
    not exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'employees'
        and column_name = 'organization_id'
    )
    or not exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'employees'
        and column_name = 'designation'
    )
  ) and exists (select 1 from public.employees) then
    raise exception 'Employees already contain data. Assign each employee to an organization and designation before applying this migration.';
  end if;
end;
$$;

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.organization_members (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null
    constraint organization_members_organization_id_fkey
    references public.organizations (id) on delete cascade,
  manager_id uuid not null
    constraint organization_members_manager_id_fkey
    references public.manager_profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint organization_members_org_manager_key unique (organization_id, manager_id)
);

alter table public.brands
  add column if not exists organization_id uuid;
alter table public.employees
  add column if not exists organization_id uuid,
  add column if not exists designation text;

alter table public.brands alter column organization_id set not null;
alter table public.employees
  alter column organization_id set not null,
  alter column designation set not null,
  alter column status set not null;

alter table public.brands drop constraint if exists brands_name_key;
alter table public.employees
  drop constraint if exists employees_email_key,
  drop constraint if exists employees_employee_code_key;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.brands'::regclass
      and conname = 'brands_organization_id_fkey'
  ) then
    alter table public.brands
      add constraint brands_organization_id_fkey
      foreign key (organization_id) references public.organizations (id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.brands'::regclass
      and conname = 'brands_org_name_key'
  ) then
    alter table public.brands
      add constraint brands_org_name_key unique (organization_id, name);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.employees'::regclass
      and conname = 'employees_organization_id_fkey'
  ) then
    alter table public.employees
      add constraint employees_organization_id_fkey
      foreign key (organization_id) references public.organizations (id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.employees'::regclass
      and conname = 'employees_org_email_key'
  ) then
    alter table public.employees
      add constraint employees_org_email_key unique (organization_id, email);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.employees'::regclass
      and conname = 'employees_org_code_key'
  ) then
    alter table public.employees
      add constraint employees_org_code_key unique (organization_id, employee_code);
  end if;
end;
$$;

create index if not exists organization_members_manager_id_idx
  on public.organization_members (manager_id);

alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;
alter table public.brands enable row level security;
alter table public.processes enable row level security;
alter table public.pods enable row level security;
alter table public.employees enable row level security;
alter table public.employee_pods enable row level security;
alter table public.employee_availability enable row level security;
alter table public.employee_skills enable row level security;
alter table public.shifts enable row level security;
alter table public.roster_assignments enable row level security;

create or replace function public.rosteriq_add_creator_as_organization_member()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is not null then
    insert into public.organization_members (organization_id, manager_id)
    values (new.id, auth.uid())
    on conflict (organization_id, manager_id) do nothing;
  end if;

  return new;
end;
$$;

revoke all on function public.rosteriq_add_creator_as_organization_member() from public, anon, authenticated;

drop trigger if exists rosteriq_add_creator_membership on public.organizations;
create trigger rosteriq_add_creator_membership
  after insert on public.organizations
  for each row execute function public.rosteriq_add_creator_as_organization_member();

create or replace function public.create_organization(organization_name text)
returns table (id uuid, name text, created_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then
    raise exception 'Authentication is required to create an organization.'
      using errcode = '42501';
  end if;

  return query
    insert into public.organizations as organization (name)
    values (organization_name)
    returning organization.id, organization.name, organization.created_at;
end;
$$;

revoke all on function public.create_organization(text) from public, anon, authenticated;
grant execute on function public.create_organization(text) to authenticated;

drop policy if exists "RosterIQ members can read their organizations" on public.organizations;
create policy "RosterIQ members can read their organizations"
  on public.organizations for select to authenticated
  using (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = organizations.id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ authenticated users can create organizations" on public.organizations;
create policy "RosterIQ authenticated users can create organizations"
  on public.organizations for insert to authenticated
  with check ((select auth.uid()) is not null);

drop policy if exists "RosterIQ members can update their organizations" on public.organizations;
create policy "RosterIQ members can update their organizations"
  on public.organizations for update to authenticated
  using (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = organizations.id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = organizations.id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can delete their organizations" on public.organizations;
create policy "RosterIQ members can delete their organizations"
  on public.organizations for delete to authenticated
  using (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = organizations.id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can read their memberships" on public.organization_members;
create policy "RosterIQ members can read their memberships"
  on public.organization_members for select to authenticated
  using (manager_id = (select auth.uid()));

drop policy if exists "RosterIQ members can manage their brands" on public.brands;
create policy "RosterIQ members can manage their brands"
  on public.brands for all to authenticated
  using (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = brands.organization_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = brands.organization_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage their processes" on public.processes;
create policy "RosterIQ members can manage their processes"
  on public.processes for all to authenticated
  using (
    exists (
      select 1
      from public.brands b
      join public.organization_members om on om.organization_id = b.organization_id
      where b.id = processes.brand_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.brands b
      join public.organization_members om on om.organization_id = b.organization_id
      where b.id = processes.brand_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage their pods" on public.pods;
create policy "RosterIQ members can manage their pods"
  on public.pods for all to authenticated
  using (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = pods.process_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = pods.process_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage their employees" on public.employees;
create policy "RosterIQ members can manage their employees"
  on public.employees for all to authenticated
  using (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = employees.organization_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = employees.organization_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage their employee pods" on public.employee_pods;
create policy "RosterIQ members can manage their employee pods"
  on public.employee_pods for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.pods p on p.id = employee_pods.pod_id
      join public.processes pr on pr.id = p.process_id
      join public.brands b on b.id = pr.brand_id
      join public.organization_members om
        on om.organization_id = e.organization_id
       and om.organization_id = b.organization_id
      where e.id = employee_pods.employee_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.pods p on p.id = employee_pods.pod_id
      join public.processes pr on pr.id = p.process_id
      join public.brands b on b.id = pr.brand_id
      join public.organization_members om
        on om.organization_id = e.organization_id
       and om.organization_id = b.organization_id
      where e.id = employee_pods.employee_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage employee availability" on public.employee_availability;
create policy "RosterIQ members can manage employee availability"
  on public.employee_availability for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_availability.employee_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_availability.employee_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage employee skills" on public.employee_skills;
create policy "RosterIQ members can manage employee skills"
  on public.employee_skills for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_skills.employee_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_skills.employee_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage their shifts" on public.shifts;
create policy "RosterIQ members can manage their shifts"
  on public.shifts for all to authenticated
  using (
    exists (
      select 1
      from public.pods p
      join public.processes pr on pr.id = p.process_id
      join public.brands b on b.id = pr.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = shifts.pod_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.pods p
      join public.processes pr on pr.id = p.process_id
      join public.brands b on b.id = pr.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = shifts.pod_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage roster assignments" on public.roster_assignments;
create policy "RosterIQ members can manage roster assignments"
  on public.roster_assignments for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.shifts s on s.id = roster_assignments.shift_id
      join public.pods p on p.id = s.pod_id
      join public.processes pr on pr.id = p.process_id
      join public.brands b on b.id = pr.brand_id
      join public.organization_members om
        on om.organization_id = e.organization_id
       and om.organization_id = b.organization_id
      where e.id = roster_assignments.employee_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.shifts s on s.id = roster_assignments.shift_id
      join public.pods p on p.id = s.pod_id
      join public.processes pr on pr.id = p.process_id
      join public.brands b on b.id = pr.brand_id
      join public.organization_members om
        on om.organization_id = e.organization_id
       and om.organization_id = b.organization_id
      where e.id = roster_assignments.employee_id
        and om.manager_id = (select auth.uid())
    )
  );

grant select, insert, update, delete
  on table public.organizations, public.brands, public.processes, public.pods, public.employees,
  public.employee_pods, public.employee_availability, public.employee_skills, public.shifts,
  public.roster_assignments
  to authenticated;
grant select on table public.organization_members to authenticated;
