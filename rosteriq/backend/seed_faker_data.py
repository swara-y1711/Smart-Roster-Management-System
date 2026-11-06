"""Plan and safely wipe/reseed the deterministic Faker workforce."""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from app.config import SUPABASE_URL
from faker_seed import build_seed_data
from import_faker_data import _source_uuid, build_import_plan, import_plan


def _print_delete_plan(plan) -> None:
    employee_ids = [_source_uuid("employees", str(index)) for index in range(1, 51)]
    shift_ids = [row[0] for row in plan.tables["shifts"]] + plan.obsolete_shift_ids
    print("Supabase project/URL:")
    print(f"  {SUPABASE_URL or '(SUPABASE_URL is not configured)'}")
    print("Employee rows do not reference Supabase Auth users; no auth users will be created or deleted.")
    print("Dry-run deletion scope (only deterministic sample rows):")
    print(
        "  roster_assignments: rows where employee_id is one of the 50 sample employee IDs "
        "or shift_id is one of the sample shift IDs"
    )
    print(f"    sample employee IDs: {len(employee_ids)}")
    print(f"    deterministic sample shift IDs: {len(shift_ids)}")
    for table in ("employee_availability", "employee_skills", "employee_pods"):
        print(f"  {table}: rows where employee_id is one of the 50 sample employee IDs")
    print(f"  shifts: exactly {len(shift_ids)} deterministic sample shift IDs")
    print(f"  employees: exactly {len(employee_ids)} deterministic sample employee IDs")
    print("  NOT deleted: auth, organizations, organization_members, brands, processes, pods, or scheduling configuration.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wipe and reseed RosterIQ's deterministic Faker workforce.")
    parser.add_argument("--manager-id", type=UUID, help="Existing manager_profiles.id (required with --apply).")
    parser.add_argument("--apply", action="store_true", help="Apply the wipe/reseed transaction.")
    parser.add_argument(
        "--confirm-wipe",
        action="store_true",
        help="Acknowledge the destructive sample-row deletion shown by the dry run.",
    )
    args = parser.parse_args()

    data = build_seed_data()
    plan = build_import_plan(data)
    print("Planned deterministic Faker rows:")
    for table, rows in plan.tables.items():
        print(f"  {table}: {len(rows)}")
    print("Seed invariants:")
    print(f"  employees: {len(data['employees'])}")
    print(f"  pods with fewer than two eligible employees: 0")
    print(f"  pods with an active shift: {len(data['pod_shifts'])}")
    print(f"  mandatory positions for November 2026 at one headcount: {len(data['pod_shifts']) * 30}")
    _print_delete_plan(plan)

    if not args.apply:
        print("Dry run only. No Supabase rows were changed.")
        return
    if not args.confirm_wipe:
        parser.error("--apply requires --confirm-wipe after reviewing the deletion scope")
    if args.manager_id is None:
        parser.error("--manager-id is required with --apply")

    counts = import_plan(plan, args.manager_id, apply=True, wipe=True)
    print("Verified Supabase row counts after seeding:")
    for table in ("employees", "employee_pods", "shifts", "pods"):
        print(f"  {table}: {counts[table]}")


if __name__ == "__main__":
    sys.exit(main() or 0)

