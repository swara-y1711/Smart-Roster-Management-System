# Scheduling API

Apply `../database/scheduling_intelligence.sql` after the existing Supabase schema
and `../database/roster_relationships.sql`. The migration only adds scheduling
rules and preserves the existing roster tables and authenticated RLS model.

## Default demo workforce

`GET /sample-workforce` returns a read-only view of the existing Faker-generated
CSV dataset for an authenticated manager. It does not import data, modify the
database, or provide CSV upload functionality. Database-backed workforce and
scheduling APIs remain available for managers with assigned records.

`GET /dashboard` returns the manager's RLS-visible organization and workforce
records without selecting a single organization or filtering employees by
status, roster assignment, or availability.

To import the repository's synthetic CSV dataset into an existing manager's
workspace, run this from `backend/`:

```powershell
python import_faker_data.py --manager-id <manager_profiles.id>
python import_faker_data.py --manager-id <manager_profiles.id> --apply
```

To preview the deterministic 50-employee Faker seed and its deletion scope,
run:

```powershell
python seed_faker_data.py
```

The preview prints the configured Supabase URL, planned row counts, and the
exact deterministic sample-row scope. Applying it is intentionally explicit:

```powershell
python seed_faker_data.py --manager-id <manager_profiles.id> --apply --confirm-wipe
```

The apply command deletes only sample-owned roster assignments, employee
availability/skills/pod links, pod-scoped shifts, and employee rows before
reseeding them. It does not touch Supabase Auth, organizations, brands,
processes, pods, or scheduling configuration. The existing manager's
organization memberships are reused; employee records do not map to Auth
users, so no Auth users are created.

After seeding, generate and sanity-check a November proposal with:

```powershell
python roster_sanity.py --organization-id <organization.id> --year 2026 --month 11
```

Rest and consecutive-day checks are reported as not configured unless the
corresponding thresholds are supplied with `--minimum-rest-hours` and
`--max-consecutive-days`.

The first command validates and reports the planned rows only. The import uses
stable UUIDs derived from source IDs, upserts dataset records without deleting
existing rows, and links the CSV organizations to the specified existing
manager. The existing schema requires UUIDs, a brand on each process, and
pod-scoped shifts. Process-brand links are inferred from the CSV assignments
(using the most frequent valid brand; ties are stable), while each global CSV
shift is normalized for each employee pod it is assigned to. Roster assignments
follow the employee's declared pod when the CSV assignment's process differs.
One CSV weekly-off row becomes seven day-of-week availability rows so the
existing scheduler can see the other six days as available.

All endpoints require the existing Supabase bearer token. Requests use the
authenticated Supabase client; organization data is read through RLS. Generated
rosters are proposals and are not written or published.

## Generate a proposal

`POST /scheduling/generate`

```json
{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "year": 2026,
  "month": 11
}
```

The response contains proposed assignments, per-process/shift coverage,
required and actual staffing, unfilled positions, errors, warnings, and
statistics.

## Validate an edited roster

`POST /scheduling/validate` accepts the same organization and month fields plus
an `assignments` array of `{ "employee_id", "shift_id", "assignment_date" }`.
The response marks mandatory constraint violations as errors and unsatisfied
preferences as warnings.

## Assess a change

`POST /scheduling/impact` accepts an organization, a date range, and one proposed
change. Supported `change_type` values are `employee_unavailable`,
`planned_leave`, `approved_leave`, `approved_comp_off`, `coverage_requirement`,
and `operating_calendar`. Calendar changes can target one process or all
processes under one brand. The response revalidates existing scheduled
assignments and identifies invalidated assignments, coverage gaps, and eligible
backup employees. It does not modify existing roster rows.

Calendar and availability weekdays use Python's convention: Monday is `0` and
Sunday is `6`. An unconfigured process defaults to all seven days (including
Sunday), with public holidays closed. Process-specific calendars, date overrides, weekly offs,
approved time off, and coverage requirements take precedence where configured.
Existing `employee_pods` memberships are the employee-to-process resource
allocations. When recurring availability rows exist for an employee, only
weekdays with an available row are treated as available; a weekday with no
availability row is not assumed to be available.
An exact-date coverage requirement takes precedence over a weekday rule; a
process-level requirement takes precedence over its shift-level requirements.

## Scheduling configuration

Managers can configure scheduling rules with the authenticated
`/scheduling/...` endpoints; changes do not require code edits.

| Resource | Collection/read routes | Create | Update | Delete |
|---|---|---|---|---|
| Process operating rules | `GET /scheduling/processes/{process_id}/operating-rules` and `/current` | `POST /scheduling/operating-rules` | `PUT /scheduling/operating-rules/{process_id}` | `DELETE /scheduling/operating-rules/{process_id}` |
| Date overrides | `GET /scheduling/processes/{process_id}/operating-overrides` and `/{operating_date}` | `POST /scheduling/operating-overrides` | `PUT /scheduling/processes/{process_id}/operating-overrides/{operating_date}` | Same path with `DELETE` |
| Minimum coverage | `GET /scheduling/coverage-requirements` (optional `process_id`) and `/{requirement_id}` | `POST /scheduling/coverage-requirements` | `PATCH` or `PUT /scheduling/coverage-requirements/{requirement_id}` | Same path with `DELETE` |
| Public holidays | `GET /scheduling/organizations/{organization_id}/public-holidays` and `/{holiday_date}` | Same collection path with `POST` | `PATCH` or `PUT` on the date path | Same date path with `DELETE` |
| Employee weekly offs | `GET /scheduling/employees/{employee_id}/weekly-offs` | Same path with `POST` | `PUT /scheduling/employees/{employee_id}/weekly-offs/{day_of_week}` | Same path with `DELETE` |
| Leave and comp-offs | `GET /scheduling/employees/{employee_id}/time-off` and `/{record_id}` | Same collection path with `POST` | `PATCH` or `PUT` on the record path | Same record path with `DELETE` |
| Employee preferences | `GET /scheduling/employees/{employee_id}/preferences` and `/{preference_id}` | Same collection path with `POST` | `PATCH` or `PUT` on the preference path | Same preference path with `DELETE` |

Process-based requirements accept either an exact `target_date` or recurring
`day_of_week`, not both. `day_of_week` uses Monday `0` through Sunday `6`.
Employee time-off records distinguish planned/approved leave, approved
comp-offs, and active unavailability. Configuration records are constrained by
the caller's organization membership and RLS.
