-- Additive scheduling structures for the existing RosterIQ Step 5 schema.
-- Run after the core schema and roster_relationships.sql.

alter table public.roster_assignments
  drop constraint if exists roster_assignments_status_check;
alter table public.roster_assignments
  add constraint roster_assignments_status_check
  check (status in ('scheduled', 'completed', 'cancelled', 'published'));

create table if not exists public.process_operating_rules (
  process_id uuid primary key references public.processes (id) on delete cascade,
  operating_days smallint[] not null default array[0, 1, 2, 3, 4, 5, 6]::smallint[],
  operates_on_public_holidays boolean not null default false,
  constraint process_operating_days_valid
    check (operating_days <@ array[0, 1, 2, 3, 4, 5, 6]::smallint[])
);

create table if not exists public.process_operating_overrides (
  process_id uuid not null references public.processes (id) on delete cascade,
  operating_date date not null,
  is_operating boolean not null,
  primary key (process_id, operating_date)
);

create table if not exists public.process_coverage_requirements (
  id uuid primary key default gen_random_uuid(),
  process_id uuid not null references public.processes (id) on delete cascade,
  shift_id uuid references public.shifts (id) on delete cascade,
  target_date date,
  day_of_week smallint,
  minimum_staff integer not null check (minimum_staff >= 0),
  constraint process_coverage_day_valid
    check (day_of_week is null or day_of_week between 0 and 6),
  constraint process_coverage_single_date_selector
    check (num_nonnulls(target_date, day_of_week) <= 1)
);

create index if not exists process_coverage_process_date_idx
  on public.process_coverage_requirements (process_id, target_date, day_of_week);

create table if not exists public.public_holidays (
  organization_id uuid not null references public.organizations (id) on delete cascade,
  holiday_date date not null,
  name text not null,
  primary key (organization_id, holiday_date)
);

create table if not exists public.employee_weekly_offs (
  employee_id uuid not null references public.employees (id) on delete cascade,
  day_of_week smallint not null check (day_of_week between 0 and 6),
  primary key (employee_id, day_of_week)
);

create table if not exists public.employee_time_off (
  id uuid primary key default gen_random_uuid(),
  employee_id uuid not null references public.employees (id) on delete cascade,
  start_date date not null,
  end_date date not null,
  kind text not null check (kind in ('leave', 'comp_off', 'unavailability')),
  status text not null check (status in ('planned', 'approved', 'pending', 'rejected', 'active')),
  reason text,
  constraint employee_time_off_valid_range check (end_date >= start_date)
);

create index if not exists employee_time_off_employee_dates_idx
  on public.employee_time_off (employee_id, start_date, end_date);

create table if not exists public.employee_preferences (
  id uuid primary key default gen_random_uuid(),
  employee_id uuid not null references public.employees (id) on delete cascade,
  process_id uuid references public.processes (id) on delete cascade,
  preferred_shift_id uuid references public.shifts (id) on delete cascade,
  preferred_days_of_week smallint[] not null default array[]::smallint[],
  avoid_days_of_week smallint[] not null default array[]::smallint[],
  constraint employee_preferred_days_valid
    check (preferred_days_of_week <@ array[0, 1, 2, 3, 4, 5, 6]::smallint[]),
  constraint employee_avoided_days_valid
    check (avoid_days_of_week <@ array[0, 1, 2, 3, 4, 5, 6]::smallint[])
);

create index if not exists employee_preferences_employee_idx
  on public.employee_preferences (employee_id);

alter table public.process_operating_rules enable row level security;
alter table public.process_operating_overrides enable row level security;
alter table public.process_coverage_requirements enable row level security;
alter table public.public_holidays enable row level security;
alter table public.employee_weekly_offs enable row level security;
alter table public.employee_time_off enable row level security;
alter table public.employee_preferences enable row level security;

drop policy if exists "RosterIQ members can manage process operating rules"
  on public.process_operating_rules;
create policy "RosterIQ members can manage process operating rules"
  on public.process_operating_rules for all to authenticated
  using (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = process_operating_rules.process_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = process_operating_rules.process_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage process operating overrides"
  on public.process_operating_overrides;
create policy "RosterIQ members can manage process operating overrides"
  on public.process_operating_overrides for all to authenticated
  using (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = process_operating_overrides.process_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = process_operating_overrides.process_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage process coverage requirements"
  on public.process_coverage_requirements;
create policy "RosterIQ members can manage process coverage requirements"
  on public.process_coverage_requirements for all to authenticated
  using (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = process_coverage_requirements.process_id
        and om.manager_id = (select auth.uid())
        and (
          process_coverage_requirements.shift_id is null
          or exists (
            select 1
            from public.shifts s
            join public.pods coverage_pod on coverage_pod.id = s.pod_id
            where s.id = process_coverage_requirements.shift_id
              and coverage_pod.process_id = p.id
          )
        )
    )
  )
  with check (
    exists (
      select 1
      from public.processes p
      join public.brands b on b.id = p.brand_id
      join public.organization_members om on om.organization_id = b.organization_id
      where p.id = process_coverage_requirements.process_id
        and om.manager_id = (select auth.uid())
        and (
          process_coverage_requirements.shift_id is null
          or exists (
            select 1
            from public.shifts s
            join public.pods coverage_pod on coverage_pod.id = s.pod_id
            where s.id = process_coverage_requirements.shift_id
              and coverage_pod.process_id = p.id
          )
        )
    )
  );

drop policy if exists "RosterIQ members can manage public holidays"
  on public.public_holidays;
create policy "RosterIQ members can manage public holidays"
  on public.public_holidays for all to authenticated
  using (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = public_holidays.organization_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1 from public.organization_members om
      where om.organization_id = public_holidays.organization_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage employee weekly offs"
  on public.employee_weekly_offs;
create policy "RosterIQ members can manage employee weekly offs"
  on public.employee_weekly_offs for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_weekly_offs.employee_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_weekly_offs.employee_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage employee time off"
  on public.employee_time_off;
create policy "RosterIQ members can manage employee time off"
  on public.employee_time_off for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_time_off.employee_id
        and om.manager_id = (select auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_time_off.employee_id
        and om.manager_id = (select auth.uid())
    )
  );

drop policy if exists "RosterIQ members can manage employee preferences"
  on public.employee_preferences;
create policy "RosterIQ members can manage employee preferences"
  on public.employee_preferences for all to authenticated
  using (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_preferences.employee_id
        and om.manager_id = (select auth.uid())
        and (
          employee_preferences.process_id is null
          or exists (
            select 1
            from public.processes preference_process
            join public.brands preference_brand
              on preference_brand.id = preference_process.brand_id
            where preference_process.id = employee_preferences.process_id
              and preference_brand.organization_id = e.organization_id
          )
        )
        and (
          employee_preferences.preferred_shift_id is null
          or exists (
            select 1
            from public.shifts preference_shift
            join public.pods preference_pod
              on preference_pod.id = preference_shift.pod_id
            join public.processes preference_process
              on preference_process.id = preference_pod.process_id
            join public.brands preference_brand
              on preference_brand.id = preference_process.brand_id
            where preference_shift.id = employee_preferences.preferred_shift_id
              and preference_brand.organization_id = e.organization_id
              and (
                employee_preferences.process_id is null
                or employee_preferences.process_id = preference_process.id
              )
          )
        )
    )
  )
  with check (
    exists (
      select 1
      from public.employees e
      join public.organization_members om on om.organization_id = e.organization_id
      where e.id = employee_preferences.employee_id
        and om.manager_id = (select auth.uid())
        and (
          employee_preferences.process_id is null
          or exists (
            select 1
            from public.processes preference_process
            join public.brands preference_brand
              on preference_brand.id = preference_process.brand_id
            where preference_process.id = employee_preferences.process_id
              and preference_brand.organization_id = e.organization_id
          )
        )
        and (
          employee_preferences.preferred_shift_id is null
          or exists (
            select 1
            from public.shifts preference_shift
            join public.pods preference_pod
              on preference_pod.id = preference_shift.pod_id
            join public.processes preference_process
              on preference_process.id = preference_pod.process_id
            join public.brands preference_brand
              on preference_brand.id = preference_process.brand_id
            where preference_shift.id = employee_preferences.preferred_shift_id
              and preference_brand.organization_id = e.organization_id
              and (
                employee_preferences.process_id is null
                or employee_preferences.process_id = preference_process.id
              )
          )
        )
    )
  );

grant select, insert, update, delete on table
  public.process_operating_rules,
  public.process_operating_overrides,
  public.process_coverage_requirements,
  public.public_holidays,
  public.employee_weekly_offs,
  public.employee_time_off,
  public.employee_preferences
to authenticated;
