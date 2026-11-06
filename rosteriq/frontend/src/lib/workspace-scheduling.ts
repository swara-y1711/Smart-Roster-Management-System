import { api } from "@/lib/api";
import type { Employee, Organization } from "@/lib/use-roster-data";

export type ScheduleAssignment = {
  id?: string;
  employee_id: string;
  shift_id: string;
  assignment_date: string;
  employee_name?: string;
  brand_id?: string;
  process_id?: string;
  pod_id?: string;
  brand?: string;
  process?: string;
  pod?: string;
  shift?: string;
  status?: string;
};

export type ScheduleConflict = {
  date: string;
  brand_id?: string;
  brand?: string;
  process_id?: string;
  process?: string;
  employee_id?: string;
  conflict_type: string;
  severity: "error" | "warning";
  explanation: string;
  suggested_resolution?: string;
};

export type EmployeeDiagnostic = {
  employee_id: string;
  scheduled_assignments: number;
  eligible_requirement_slots: number;
  reason: string;
};

export type ScheduleReport = {
  is_valid: boolean;
  assignments: ScheduleAssignment[];
  coverage_summary: {
    date: string;
    brand_id?: string;
    brand: string;
    process_id?: string;
    process: string;
    shift_id?: string | null;
    required_staff: number;
    actual_staff: number;
    unfilled_positions: string[];
  }[];
  conflicts: ScheduleConflict[];
  required_staffing: number;
  actual_staffing: number;
  unfilled_positions?: unknown[];
  warnings?: ScheduleConflict[];
  statistics: Record<string, number>;
  employee_diagnostics?: EmployeeDiagnostic[];
};

function mergeReports(reports: ScheduleReport[]): ScheduleReport {
  const statistics = reports.reduce<Record<string, number>>((merged, report) => {
    for (const [key, value] of Object.entries(report.statistics || {})) {
      merged[key] = key === "days_in_period"
        ? Math.max(merged[key] || 0, value)
        : (merged[key] || 0) + value;
    }
    return merged;
  }, {});
  const assignments = reports.flatMap((report) => report.assignments || []);
  const conflicts = reports.flatMap((report) => report.conflicts || []);
  return {
    is_valid: reports.every((report) => report.is_valid),
    assignments,
    coverage_summary: reports.flatMap((report) => report.coverage_summary || []),
    conflicts,
    required_staffing: reports.reduce((total, report) => total + report.required_staffing, 0),
    actual_staffing: reports.reduce((total, report) => total + report.actual_staffing, 0),
    unfilled_positions: reports.flatMap((report) => report.unfilled_positions || []),
    warnings: conflicts.filter((conflict) => conflict.severity === "warning"),
    employee_diagnostics: reports.flatMap((report) => report.employee_diagnostics || []),
    statistics: {
      ...statistics,
      employee_count: new Set(assignments.map((assignment) => assignment.employee_id)).size,
    },
  };
}

export async function generateWorkspaceReport(organizations: Organization[], year: number, month: number) {
  const reports = await Promise.all(
    organizations.map((organization) => api.post<ScheduleReport>("/scheduling/generate", {
      organization_id: organization.id,
      year,
      month,
    })),
  );
  return mergeReports(reports);
}

export async function validateWorkspaceReport(
  organizations: Organization[],
  employees: Employee[],
  report: ScheduleReport,
  year: number,
  month: number,
) {
  const employeeOrganization = new Map(employees.map((employee) => [employee.id, employee.organization_id]));
  const assignmentsByOrganization = new Map<string, ScheduleAssignment[]>();
  for (const assignment of report.assignments) {
    const organizationId = employeeOrganization.get(assignment.employee_id);
    if (!organizationId) continue;
    const assignments = assignmentsByOrganization.get(organizationId) || [];
    assignments.push(assignment);
    assignmentsByOrganization.set(organizationId, assignments);
  }
  const reports = await Promise.all(
    organizations.map((organization) => api.post<ScheduleReport>("/scheduling/validate", {
      organization_id: organization.id,
      year,
      month,
      assignments: (assignmentsByOrganization.get(organization.id) || []).map(({ employee_id, shift_id, assignment_date }) => ({ employee_id, shift_id, assignment_date })),
    })),
  );
  return mergeReports(reports);
}

export async function saveWorkspaceRoster(
  organizations: Organization[],
  employees: Employee[],
  report: ScheduleReport,
  year: number,
  month: number,
) {
  const employeeOrganization = new Map(employees.map((employee) => [employee.id, employee.organization_id]));
  await Promise.all(organizations.map((organization) => api.post("/roster-assignments/validated", {
    organization_id: organization.id,
    year,
    month,
    assignments: report.assignments
      .filter((assignment) => employeeOrganization.get(assignment.employee_id) === organization.id)
      .map(({ employee_id, shift_id, assignment_date }) => ({ employee_id, shift_id, assignment_date })),
    status: "scheduled",
  })));
}

export async function publishWorkspaceRoster(organizations: Organization[], year: number, month: number) {
  await Promise.all(organizations.map((organization) => api.post("/roster-assignments/publish", {
    organization_id: organization.id,
    year,
    month,
  })));
}
