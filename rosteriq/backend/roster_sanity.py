"""Generate a proposal and run independent roster sanity checks."""

from __future__ import annotations

import argparse
import calendar
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import DATABASE_URL
from routers.scheduling import load_schedule_data
from services.scheduling import (
    Assignment,
    ScheduleData,
    _overlaps,
    _shift_bounds,
    _shift_duration,
    generate_monthly_roster,
)


TABLES = {
    "organizations",
    "brands",
    "processes",
    "pods",
    "employees",
    "employee_pods",
    "employee_availability",
    "employee_skills",
    "employee_weekly_offs",
    "employee_time_off",
    "employee_preferences",
    "process_operating_rules",
    "process_operating_overrides",
    "process_coverage_requirements",
    "public_holidays",
    "shifts",
}


class PostgresQuery:
    def __init__(self, connection: psycopg.Connection[Any], table: str):
        if table not in TABLES:
            raise ValueError(f"Unsupported table: {table}")
        self.connection = connection
        self.table_name = table
        self.filters: list[tuple[str, str, Any]] = []
        self.start = 0
        self.end: int | None = None

    def select(self, _columns: str) -> "PostgresQuery":
        return self

    def eq(self, column: str, value: Any) -> "PostgresQuery":
        self.filters.append((column, "eq", value))
        return self

    def in_(self, column: str, values: list[Any]) -> "PostgresQuery":
        self.filters.append((column, "in", values))
        return self

    def gte(self, column: str, value: Any) -> "PostgresQuery":
        self.filters.append((column, "gte", value))
        return self

    def lte(self, column: str, value: Any) -> "PostgresQuery":
        self.filters.append((column, "lte", value))
        return self

    def range(self, start: int, end: int) -> "PostgresQuery":
        self.start, self.end = start, end
        return self

    def execute(self):
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f'SELECT * FROM public."{self.table_name}"')
            rows = list(cursor.fetchall())
        for column, operator, expected in self.filters:
            if operator == "eq":
                rows = [row for row in rows if str(row.get(column)) == str(expected)]
            elif operator == "in":
                values = {str(value) for value in expected}
                rows = [row for row in rows if str(row.get(column)) in values]
            elif operator in {"gte", "lte"}:
                def normalized(value: Any) -> str:
                    return str(value)[:10]

                if operator == "gte":
                    rows = [row for row in rows if normalized(row.get(column)) >= normalized(expected)]
                else:
                    rows = [row for row in rows if normalized(row.get(column)) <= normalized(expected)]
        if self.end is not None:
            rows = rows[self.start:self.end + 1]
        return type("Response", (), {"data": rows})()


class PostgresDatabase:
    def __init__(self, connection: psycopg.Connection[Any]):
        self.connection = connection

    def table(self, name: str) -> PostgresQuery:
        return PostgresQuery(self.connection, name)


def _check(name: str, failures: list[str], detail: str) -> None:
    print(f"{'FAIL' if failures else 'PASS'} {name}: {detail}")


def _capacity(data: ScheduleData, first_day: date, last_day: date) -> int:
    capacity = 0
    for employee in data.employees.values():
        if not employee.active:
            continue
        for offset in range((last_day - first_day).days + 1):
            day = first_day + timedelta(days=offset)
            if day.weekday() in employee.weekly_off_days:
                continue
            if any(
                record.start_date <= day <= record.end_date
                and record.kind.lower() in {"leave", "comp_off", "unavailability"}
                and record.status.lower() in {"planned", "approved", "active"}
                for record in employee.time_off
            ):
                continue
            if employee.availability:
                rows = [row for row in employee.availability if row.day_of_week == day.weekday()]
                if not any(row.is_available for row in rows):
                    continue
            capacity += 1
    return capacity


def run(args: argparse.Namespace) -> int:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    first_day = date(args.year, args.month, 1)
    last_day = date(args.year, args.month, calendar.monthrange(args.year, args.month)[1])
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as connection:
        data = load_schedule_data(PostgresDatabase(connection), str(args.organization_id), first_day, last_day)

    report = generate_monthly_roster(data, args.year, args.month)
    assignments = list(report.assignments)
    print(
        f"Proposal {args.year:04d}-{args.month:02d}: employees={report.statistics['employee_count']} "
        f"required={report.statistics['required_positions']} assigned={report.statistics['filled_positions']} "
        f"coverage={round(report.statistics['filled_positions'] / report.statistics['required_positions'] * 100) if report.statistics['required_positions'] else 0}% "
        f"unfilled={report.statistics['unfilled_positions']} errors={sum(item.severity == 'error' for item in report.conflicts)} "
        f"warnings={sum(item.severity == 'warning' for item in report.conflicts)}"
    )

    failures: list[str] = []
    by_employee_day: dict[tuple[str, date], list[Assignment]] = defaultdict(list)
    for assignment in assignments:
        by_employee_day[(assignment.employee_id, assignment.assignment_date)].append(assignment)
    double_booked: list[str] = []
    for (employee_id, day), items in by_employee_day.items():
        for index, assignment in enumerate(items):
            if any(_overlaps(assignment, other, data) for other in items[index + 1:]):
                double_booked.append(f"{employee_id}:{day}")
    if double_booked:
        failures.extend(double_booked)
    _check("no employee double-booked on the same day", failures, f"{len(double_booked)} overlapping employee-days")

    weekly_off_failures = [
        assignment for assignment in assignments
        if assignment.assignment_date.weekday() in data.employees[assignment.employee_id].weekly_off_days
    ]
    failures = [str(item) for item in weekly_off_failures]
    _check("weekly offs respected", failures, f"{len(weekly_off_failures)} violations")

    rest_failures: list[str] = []
    if args.minimum_rest_hours is not None:
        by_employee: dict[str, list[Assignment]] = defaultdict(list)
        for assignment in assignments:
            by_employee[assignment.employee_id].append(assignment)
        for employee_id, items in by_employee.items():
            ordered = sorted(items, key=lambda item: _shift_bounds(data.shifts[item.shift_id], item.assignment_date)[0])
            for previous, current in zip(ordered, ordered[1:]):
                previous_end = _shift_bounds(data.shifts[previous.shift_id], previous.assignment_date)[1]
                current_start = _shift_bounds(data.shifts[current.shift_id], current.assignment_date)[0]
                if (current_start - previous_end) / 60 < args.minimum_rest_hours:
                    rest_failures.append(employee_id)
    _check(
        "minimum rest between shifts",
        rest_failures,
        f"{len(rest_failures)} violations" if args.minimum_rest_hours is not None else "not configured; pass --minimum-rest-hours to evaluate",
    )

    consecutive_failures: list[str] = []
    if args.max_consecutive_days is not None:
        by_employee_dates: dict[str, set[date]] = defaultdict(set)
        for assignment in assignments:
            by_employee_dates[assignment.employee_id].add(assignment.assignment_date)
        for employee_id, dates in by_employee_dates.items():
            streak = longest = 0
            previous_day = None
            for day in sorted(dates):
                streak = streak + 1 if previous_day and day == previous_day + timedelta(days=1) else 1
                longest = max(longest, streak)
                previous_day = day
            if longest > args.max_consecutive_days:
                consecutive_failures.append(employee_id)
    _check(
        "maximum consecutive working days",
        consecutive_failures,
        f"{len(consecutive_failures)} violations" if args.max_consecutive_days is not None else "not configured; pass --max-consecutive-days to evaluate",
    )

    eligibility_failures = [
        assignment for assignment in assignments
        if (assignment.employee_id, data.shifts[assignment.shift_id].pod_id) not in data.employee_pods
    ]
    failures = [str(item) for item in eligibility_failures]
    _check("pod eligibility respected", failures, f"{len(eligibility_failures)} violations")

    theoretical_capacity = _capacity(data, first_day, last_day)
    capacity_failures = ["capacity"] if len(assignments) > theoretical_capacity else []
    _check(
        "total assignments <= theoretical capacity",
        capacity_failures,
        f"{len(assignments)} assignments / {theoretical_capacity} theoretical slots",
    )

    if report.statistics["required_positions"] and (
        report.statistics["filled_positions"] / report.statistics["required_positions"] < 0.9
    ):
        reason_counts: defaultdict[str, int] = defaultdict(int)
        for row in report.coverage:
            for reason in row.unfilled_positions:
                reason_counts[reason] += 1
        print("Likely cause of coverage below 90% (scheduling logic unchanged):")
        print(f"  theoretical capacity: {theoretical_capacity}")
        print(f"  weekly-off/availability-limited capacity: {len(data.employees) * (last_day - first_day).days + len(data.employees) - theoretical_capacity}")
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[:5]:
            print(f"  unfilled reason: {count} · {reason}")

    return 1 if any(
        (double_booked, weekly_off_failures, rest_failures, consecutive_failures, eligibility_failures, capacity_failures)
    ) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run independent sanity checks on a generated monthly proposal.")
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=11)
    parser.add_argument("--minimum-rest-hours", type=float)
    parser.add_argument("--max-consecutive-days", type=int)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

