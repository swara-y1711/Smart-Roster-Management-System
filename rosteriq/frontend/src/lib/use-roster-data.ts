"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { api, apiErrorMessage } from "@/lib/api";

export type Organization = { id: string; name: string };
export type Brand = { id: string; organization_id: string; name: string; industry?: string | null };
export type Process = { id: string; brand_id: string; name: string };
export type Pod = { id: string; process_id: string; name: string; description?: string | null };
export type Employee = { id: string; organization_id: string; employee_code: string; first_name: string; last_name?: string | null; status?: string | null; designation?: string; email?: string };
export type EmployeePod = { employee_id: string; pod_id: string; is_primary?: boolean };
export type Shift = { id: string; pod_id: string; shift_name: string; start_time: string; end_time: string; required_headcount?: number };
export type RosterAssignment = { id?: string; employee_id: string; shift_id: string; assignment_date: string; status?: string };

export type RosterData = {
  organizations: Organization[];
  organization: Organization | null;
  source: "database" | "sample";
  brands: Brand[];
  processes: Process[];
  pods: Pod[];
  employees: Employee[];
  employeePods: EmployeePod[];
  shifts: Shift[];
  assignments: RosterAssignment[];
  loading: boolean;
  error: string;
  refresh: (force?: boolean) => Promise<void>;
};

export type DashboardData = {
  organizations: Organization[];
  brands: Brand[];
  processes: Process[];
  pods: Pod[];
  employees: Employee[];
  employeePods: EmployeePod[];
  employeeSkills: { id: string; employee_id: string; skill_name: string; proficiency?: string | null }[];
  availability: { id: string; employee_id: string; day_of_week: number; is_available: boolean }[];
  shifts: Shift[];
  assignments: RosterAssignment[];
  loading: boolean;
  error: string;
  refresh: (force?: boolean) => Promise<void>;
};

type WorkforceRecords = Pick<
  RosterData,
  "brands" | "processes" | "pods" | "employees" | "employeePods" | "shifts" | "assignments"
>;

type DashboardRecords = Omit<DashboardData, "loading" | "error" | "refresh">;

const CACHE_TTL_MS = 30_000;
let dashboardCache: { userId: string; records: DashboardRecords; cachedAt: number } | null = null;
let rosterCache: { userId: string; records: WorkforceRecords & { organizations: Organization[]; organization: Organization | null; source: "database" | "sample" }; cachedAt: number } | null = null;

export function useDashboardData(): DashboardData {
  const { user, isLoading: authLoading } = useAuth();
  const cached = user && dashboardCache?.userId === user.id && Date.now() - dashboardCache.cachedAt < CACHE_TTL_MS
    ? dashboardCache.records
    : null;
  const [state, setState] = useState<Omit<DashboardData, "refresh">>({
    organizations: [], brands: [], processes: [], pods: [], employees: [],
    employeePods: [], employeeSkills: [], availability: [], shifts: [], assignments: [],
    ...(cached || {}), loading: !cached, error: "",
  });

  const refresh = useCallback(async (force = false) => {
    if (!user) {
      setState({
        organizations: [], brands: [], processes: [], pods: [], employees: [],
        employeePods: [], employeeSkills: [], availability: [], shifts: [], assignments: [],
        loading: false, error: "",
      });
      return;
    }
    const cachedRecords = dashboardCache?.userId === user.id ? dashboardCache.records : null;
    if (!force && cachedRecords && Date.now() - (dashboardCache?.cachedAt || 0) < CACHE_TTL_MS) {
      setState({ ...cachedRecords, loading: false, error: "" });
      return;
    }
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const records = await api.get<DashboardRecords>("/dashboard");
      const organizations = uniqueById(records.organizations);
      const organizationIds = new Set(organizations.map((item) => item.id));
      const brands = uniqueById(records.brands.filter((item) => organizationIds.has(item.organization_id)));
      const brandIds = new Set(brands.map((item) => item.id));
      const processes = uniqueById(records.processes.filter((item) => brandIds.has(item.brand_id)));
      const processIds = new Set(processes.map((item) => item.id));
      const pods = uniqueById(records.pods.filter((item) => processIds.has(item.process_id)));
      const podIds = new Set(pods.map((item) => item.id));
      const employees = uniqueById(records.employees.filter((item) => organizationIds.has(item.organization_id)));
      const employeeIds = new Set(employees.map((item) => item.id));
      const shifts = uniqueById(records.shifts.filter((item) => podIds.has(item.pod_id)));
      const shiftIds = new Set(shifts.map((item) => item.id));
      setState({
        ...records,
        organizations,
        brands,
        processes,
        pods,
        employees,
        employeePods: uniqueByPair(records.employeePods.filter((item) => employeeIds.has(item.employee_id) && podIds.has(item.pod_id)), (item) => `${item.employee_id}:${item.pod_id}`),
        employeeSkills: uniqueById(records.employeeSkills.filter((item) => employeeIds.has(item.employee_id))),
        availability: uniqueById(records.availability.filter((item) => employeeIds.has(item.employee_id))),
        shifts,
        assignments: uniqueById(records.assignments.filter((item) => employeeIds.has(item.employee_id) && shiftIds.has(item.shift_id))),
        loading: false,
        error: "",
      });
      dashboardCache = { userId: user.id, records: { ...records, organizations, brands, processes, pods, employees, employeePods: uniqueByPair(records.employeePods.filter((item) => employeeIds.has(item.employee_id) && podIds.has(item.pod_id)), (item) => `${item.employee_id}:${item.pod_id}`), employeeSkills: uniqueById(records.employeeSkills.filter((item) => employeeIds.has(item.employee_id))), availability: uniqueById(records.availability.filter((item) => employeeIds.has(item.employee_id))), shifts, assignments: uniqueById(records.assignments.filter((item) => employeeIds.has(item.employee_id) && shiftIds.has(item.shift_id))) }, cachedAt: Date.now() };
    } catch (error) {
      setState((current) => ({ ...current, loading: false, error: apiErrorMessage(error) }));
    }
  }, [user]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);
  return { ...state, refresh };
}

export function useRosterData(): RosterData {
  const { user, isLoading: authLoading } = useAuth();
  const cached = user && rosterCache?.userId === user.id && Date.now() - rosterCache.cachedAt < CACHE_TTL_MS
    ? rosterCache.records
    : null;
  const [state, setState] = useState<Omit<RosterData, "refresh">>({
    organizations: [], organization: null, source: "database", brands: [], processes: [], pods: [], employees: [], employeePods: [], shifts: [], assignments: [], error: "",
    ...(cached || {}), loading: !cached,
  });

  const refresh = useCallback(async (force = false) => {
    if (!user) {
      setState({
        organizations: [], organization: null, source: "database", brands: [], processes: [], pods: [], employees: [],
        employeePods: [], shifts: [], assignments: [], loading: false, error: "",
      });
      return;
    }
    const cachedRecords = rosterCache?.userId === user.id ? rosterCache.records : null;
    if (!force && cachedRecords && Date.now() - (rosterCache?.cachedAt || 0) < CACHE_TTL_MS) {
      setState({ ...cachedRecords, loading: false, error: "" });
      return;
    }
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const organizations = await api.get<Organization[]>("/organizations");
      if (!organizations.length) {
        const sample = await api.get<WorkforceRecords>("/sample-workforce");
        const records = { organizations: [], organization: null, source: "sample" as const, ...sample };
        rosterCache = { userId: user.id, records, cachedAt: Date.now() };
        setState({ ...records, loading: false, error: "" });
        return;
      }
      const [allBrands, allProcesses, allPods, allEmployees, allEmployeePods, allShifts, allAssignments] = await Promise.all([
        api.get<Brand[]>("/brands"),
        api.get<Process[]>("/processes"),
        api.get<Pod[]>("/pods"),
        api.get<Employee[]>("/employees"),
        api.get<EmployeePod[]>("/employee-pods"),
        api.get<Shift[]>("/shifts"),
        api.get<RosterAssignment[]>("/roster-assignments"),
      ]);
      const visibleOrganizations = uniqueById(organizations);
      const organizationIds = new Set(visibleOrganizations.map((item) => item.id));
      const brands = uniqueById(allBrands.filter((item) => organizationIds.has(item.organization_id)));
      const brandIds = new Set(brands.map((item) => item.id));
      const processes = uniqueById(allProcesses.filter((item) => brandIds.has(item.brand_id)));
      const processIds = new Set(processes.map((item) => item.id));
      const pods = uniqueById(allPods.filter((item) => processIds.has(item.process_id)));
      const podIds = new Set(pods.map((item) => item.id));
      const employees = uniqueById(allEmployees.filter((item) => organizationIds.has(item.organization_id)));
      const employeeIds = new Set(employees.map((item) => item.id));
      const employeePods = uniqueByPair(
        allEmployeePods.filter((item) => employeeIds.has(item.employee_id) && podIds.has(item.pod_id)),
        (item) => `${item.employee_id}:${item.pod_id}`,
      );
      const shifts = uniqueById(allShifts.filter((item) => podIds.has(item.pod_id)));
      const shiftIds = new Set(shifts.map((item) => item.id));
      const assignments = uniqueById(allAssignments.filter((item) => employeeIds.has(item.employee_id) && shiftIds.has(item.shift_id)));
      const records = { organizations: visibleOrganizations, organization: visibleOrganizations[0] || null, source: "database" as const, brands, processes, pods, employees, employeePods, shifts, assignments };
      rosterCache = { userId: user.id, records, cachedAt: Date.now() };
      setState({ ...records, loading: false, error: "" });
    } catch (error) {
      setState((current) => ({ ...current, loading: false, error: apiErrorMessage(error) }));
    }
  }, [user]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);
  return { ...state, refresh };
}

function uniqueById<T extends { id?: string }>(rows: T[]) {
  return Array.from(new Map(rows.map((row) => [row.id || JSON.stringify(row), row])).values());
}

function uniqueByPair<T>(rows: T[], key: (row: T) => string) {
  return Array.from(new Map(rows.map((row) => [key(row), row])).values());
}

export function displayName(employee?: Employee) {
  return employee ? [employee.first_name, employee.last_name].filter(Boolean).join(" ") : "Unassigned";
}
