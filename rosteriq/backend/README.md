# Scheduling API

Apply `../database/scheduling_intelligence.sql` after the existing Supabase schema
and `../database/roster_relationships.sql`. The migration only adds scheduling
rules and preserves the existing roster tables and authenticated RLS model.

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
