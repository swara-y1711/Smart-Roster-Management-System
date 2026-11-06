"use client";

import { useCallback, useMemo, useState } from "react";
import { BarChart3, RefreshCw, SlidersHorizontal, Zap } from "lucide-react";
import { ActionButton, DashboardShell, EmptyState, MetricCard, Panel } from "@/components/dashboard-ui";
import { api, apiErrorMessage } from "@/lib/api";
import { displayName, useDashboardData } from "@/lib/use-roster-data";
import { useCurrentDate } from "@/lib/use-current-date";

type CoverageRow = { brand_id?: string; brand?: string; process_id?: string; process?: string; required_staff: number; actual_staff: number; unfilled_positions?: string[] };
type ScheduleReport = { coverage_summary: CoverageRow[]; conflicts: { severity: string; conflict_type: string; explanation: string }[]; required_staffing: number; actual_staffing: number };

export default function ExecutiveDashboard() {
  const data = useDashboardData();
  const currentDate = useCurrentDate();
  const [report, setReport] = useState<ScheduleReport | null>(null);
  const [reportError, setReportError] = useState("");
  const [podFilter, setPodFilter] = useState("");
  const [loadingReport, setLoadingReport] = useState(false);
  const [employeePage, setEmployeePage] = useState(1);

  const loadReport = useCallback(async () => {
    if (!data.organizations.length) return;
    setLoadingReport(true);
    try {
      const now = new Date();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const monthPrefix = `${now.getFullYear()}-${month}-`;
      const savedAssignments = data.assignments.filter((assignment) =>
        assignment.assignment_date.startsWith(monthPrefix)
        && ["scheduled", "published", "assigned", "confirmed"].includes(assignment.status?.toLowerCase() || "scheduled"),
      );
      if (!savedAssignments.length) {
        setReport(null);
        setReportError("");
        return;
      }
      const reports = await Promise.all(data.organizations.map((organization) =>
        api.post<ScheduleReport>("/scheduling/validate", {
          organization_id: organization.id,
          year: now.getFullYear(),
          month: now.getMonth() + 1,
          assignments: savedAssignments
            .filter((assignment) =>
              data.employees.some((employee) =>
                employee.id === assignment.employee_id && employee.organization_id === organization.id,
              )
            )
            .map(({ employee_id, shift_id, assignment_date }) => ({
              employee_id,
              shift_id,
              assignment_date,
            })),
        }),
      ));
      setReport({
        coverage_summary: reports.flatMap((item) => item.coverage_summary),
        conflicts: reports.flatMap((item) => item.conflicts),
        required_staffing: reports.reduce((total, item) => total + item.required_staffing, 0),
        actual_staffing: reports.reduce((total, item) => total + item.actual_staffing, 0),
      });
      setReportError("");
    } catch (error) { setReportError(apiErrorMessage(error)); }
    finally { setLoadingReport(false); }
  }, [data.assignments, data.employees, data.organizations]);

  const podEmployees = useMemo(() => {
    const counts = new Map<string, number>();
    data.employeePods.forEach((item) => counts.set(item.pod_id, (counts.get(item.pod_id) || 0) + 1));
    return data.pods.filter((pod) => !podFilter || pod.id === podFilter).map((pod) => {
      const process = data.processes.find((item) => item.id === pod.process_id);
      const brand = data.brands.find((item) => item.id === process?.brand_id);
      const lead = data.employeePods.find((item) => item.pod_id === pod.id && item.is_primary);
      return { ...pod, process, brand, count: counts.get(pod.id) || 0, lead: displayName(data.employees.find((item) => item.id === lead?.employee_id)) };
    });
  }, [data, podFilter]);

  const workforceRows = useMemo(() => data.employees.map((employee) => {
    const membership = data.employeePods.find((item) => item.employee_id === employee.id && item.is_primary)
      || data.employeePods.find((item) => item.employee_id === employee.id);
    const pod = data.pods.find((item) => item.id === membership?.pod_id);
    const process = data.processes.find((item) => item.id === pod?.process_id);
    return { employee, pod, process };
  }), [data]);

  const employeePageSize = 10;
  const employeePageCount = Math.max(1, Math.ceil(workforceRows.length / employeePageSize));
  const currentEmployeePage = Math.min(employeePage, employeePageCount);
  const visibleWorkforceRows = workforceRows.slice(
    (currentEmployeePage - 1) * employeePageSize,
    currentEmployeePage * employeePageSize,
  );
  const reportPeriod = currentDate
    ? new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(new Date(`${currentDate.slice(0, 7)}-01T00:00:00`))
    : "Current month";
  const coveragePercent = report?.required_staffing ? Math.round((report.actual_staffing / report.required_staffing) * 100) : "—";
  const hasEmployeeStatus = data.employees.some((employee) => employee.status);
  const activeEmployees = data.employees.filter((employee) => employee.status?.toLowerCase() === "active").length;
  const errors = report?.conflicts.filter((conflict) => conflict.severity === "error") || [];
  const filteredCoverage = report?.coverage_summary.filter((row) => !podFilter || data.pods.some((pod) => pod.id === podFilter && pod.process_id === row.process_id)) || [];

  return (
    <DashboardShell activeSection="Dashboard">
      <section className="mb-8 flex flex-col justify-between gap-5 xl:flex-row xl:items-center">
        <div><h1 className="font-display text-[28px] font-bold">Operations Overview</h1><p className="mt-2 text-[13px] text-[#464555]">Live workforce, brand, process, pod and roster coverage intelligence.</p></div>
        <div className="flex flex-wrap gap-3">
          <label className="flex h-10 items-center gap-2 rounded-xl bg-white px-3 text-[12px] shadow-sm"><SlidersHorizontal className="h-4 w-4 text-[#777587]" /><span>Pod</span><select aria-label="Pod filter" value={podFilter} onChange={(event) => setPodFilter(event.target.value)} className="bg-transparent font-medium"><option value="">All pods</option>{data.pods.map((pod) => <option key={pod.id} value={pod.id}>{pod.name}</option>)}</select></label>
          <ActionButton onClick={() => void data.refresh(true)}><RefreshCw className="h-4 w-4" />{data.loading ? "Refreshing…" : "Refresh"}</ActionButton>
          <ActionButton variant="primary" onClick={() => void loadReport()} disabled={!data.organizations.length || loadingReport}><Zap className="h-4 w-4" />{loadingReport ? "Generating…" : "Refresh coverage"}</ActionButton>
        </div>
      </section>
      {(data.error || reportError) && <p role="alert" className="mb-5 rounded-xl bg-[#ffdad6] px-4 py-3 text-sm text-[#93000a]">{data.error || reportError}</p>}
      <section className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard title="Employees" icon="people" value={String(data.employees.length)} note={hasEmployeeStatus ? `${activeEmployees} active` : "Employment status not provided"} />
        <MetricCard title="Brands" icon="store" value={String(data.brands.length)} note="Available in roster data" tone="teal" />
        <MetricCard title="Processes" icon="processes" value={String(data.processes.length)} note="Assigned processes" />
        <MetricCard title="Operational pods" icon="pods" value={String(data.pods.length)} note="Configured pods" />
        <MetricCard title="Active employees" icon="badge" value={hasEmployeeStatus ? String(activeEmployees) : "—"} note={hasEmployeeStatus ? `${data.employees.length - activeEmployees} inactive` : "Employment status not provided"} />
        <MetricCard title="Saved roster coverage" icon="trending_up" value={report ? `${coveragePercent}%` : "No saved roster"} note={report ? `${report.actual_staffing}/${report.required_staffing} valid positions · ${reportPeriod}` : `${reportPeriod} has no saved assignments`} tone={report && coveragePercent !== "—" && Number(coveragePercent) < 100 ? "error" : "teal"} />
      </section>
      <div className="grid gap-6 xl:grid-cols-7">
        <Panel scroll ariaLabel="Stored roster coverage list" title="Stored roster coverage" subtitle={`Required versus valid actual staffing for the ${reportPeriod} database roster.`} className="xl:col-span-4" action={<BarChart3 className="h-5 w-5 text-[#777587]" />}>
          {filteredCoverage.length ? <div className="space-y-3">{filteredCoverage.slice(0, 12).map((row, index) => <div key={`${row.process}-${index}`}><div className="mb-1 flex justify-between text-[12px]"><span>{row.brand} / {row.process}</span><span className={row.actual_staff < row.required_staff ? "font-semibold text-[#93000a]" : "text-[#006983]"}>{row.actual_staff}/{row.required_staff}</span></div><div className="h-2 rounded-full bg-[#eaedff]"><div className={`h-2 rounded-full ${row.actual_staff < row.required_staff ? "bg-[#ba1a1a]" : "bg-[#4f46e5]"}`} style={{ width: `${Math.min(100, row.required_staff ? (row.actual_staff / row.required_staff) * 100 : 0)}%` }} /></div></div>)}</div> : <EmptyState title={report ? "No operating coverage rows" : "Coverage unavailable"} description="Generate a roster to calculate current-period coverage." compact />}
        </Panel>
        <Panel scroll ariaLabel="Scheduling alerts list" title="Scheduling alerts" subtitle="Mandatory gaps and validation findings." className="xl:col-span-3">
          {errors.length ? <div className="space-y-3">{errors.slice(0, 8).map((error, index) => <div key={`${error.conflict_type}-${index}`} className="rounded-xl bg-[#fff0ef] p-3"><p className="text-[12px] font-semibold text-[#93000a]">{error.conflict_type}</p><p className="mt-1 text-[12px] text-[#464555]">{error.explanation}</p></div>)}</div> : <EmptyState title="No mandatory conflicts" description={report ? "The generated roster has no error-level findings." : "Generate a roster to inspect alerts."} compact />}
        </Panel>
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Panel scroll ariaLabel="Brand coverage list" title="Brand coverage" subtitle="Assigned processes and staffing health.">
          {data.brands.length ? <div className="space-y-3">{data.brands.map((brand) => { const processes = data.processes.filter((process) => process.brand_id === brand.id); const processIds = new Set(processes.map((process) => process.id)); const podIds = new Set(data.pods.filter((pod) => processIds.has(pod.process_id)).map((pod) => pod.id)); const staff = data.employeePods.filter((item) => podIds.has(item.pod_id)); return <div key={brand.id} className="flex items-center justify-between rounded-xl bg-[#f7f8ff] p-3"><div><p className="text-[13px] font-semibold">{brand.name}</p><p className="text-[11px] text-[#777587]">{processes.length} processes · {staff.length} pod allocations</p></div><span className="rounded-full bg-[#eaedff] px-3 py-1 text-[11px] font-semibold text-[#3525cd]">{report ? "Engine tracked" : "Not generated"}</span></div>; })}</div> : <EmptyState title="No brands available" compact />}
        </Panel>
        <Panel scroll ariaLabel="Pod allocation list" title="Pod allocation" subtitle="Pod leads, employee counts and process ownership.">
          {podEmployees.length ? <div className="space-y-3">{podEmployees.map((pod) => <div key={pod.id} className="flex items-center justify-between rounded-xl bg-[#f7f8ff] p-3"><div><p className="text-[13px] font-semibold">{pod.name}</p><p className="text-[11px] text-[#777587]">{pod.brand?.name || "—"} / {pod.process?.name || "—"} · Lead: {pod.lead}</p></div><span className="text-[12px] font-semibold">{pod.count} employees</span></div>)}</div> : <EmptyState title="No pods available" compact />}
        </Panel>
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Panel scroll ariaLabel="Dashboard employees list" title="Employees" subtitle="Current workforce and assigned process.">
          {workforceRows.length ? <>
            <div className="space-y-2">{visibleWorkforceRows.map(({ employee, pod, process }) => <div key={employee.id} className="flex items-center justify-between gap-4 rounded-xl bg-[#f7f8ff] p-3"><div className="min-w-0"><p className="truncate text-[13px] font-semibold">{displayName(employee)}</p><p className="mt-1 truncate text-[11px] text-[#777587]">{employee.employee_code} · {employee.designation || "Employee"}</p></div><p className="shrink-0 text-right text-[11px] text-[#464555]">{pod?.name || "Unassigned"}{process ? ` · ${process.name}` : ""}</p></div>)}</div>
            <div className="mt-4 flex items-center justify-between gap-3 text-[12px] text-[#777587]">
              <span>Showing {(currentEmployeePage - 1) * employeePageSize + 1}–{Math.min(currentEmployeePage * employeePageSize, workforceRows.length)} of {workforceRows.length}</span>
              <div className="flex gap-2">
                <ActionButton onClick={() => setEmployeePage(Math.max(1, currentEmployeePage - 1))} disabled={currentEmployeePage === 1}>Previous</ActionButton>
                <ActionButton onClick={() => setEmployeePage(Math.min(employeePageCount, currentEmployeePage + 1))} disabled={currentEmployeePage === employeePageCount}>Next</ActionButton>
              </div>
            </div>
          </> : <EmptyState title="No employees available" compact />}
        </Panel>
        <Panel scroll ariaLabel="Dashboard processes list" title="Processes" subtitle="Processes and their operating pods.">
          {data.processes.length ? <div className="space-y-2">{data.processes.map((process) => { const brand = data.brands.find((item) => item.id === process.brand_id); const pods = data.pods.filter((item) => item.process_id === process.id); return <div key={process.id} className="flex items-center justify-between rounded-xl bg-[#f7f8ff] p-3"><div><p className="text-[13px] font-semibold">{process.name}</p><p className="mt-1 text-[11px] text-[#777587]">{brand?.name || "Brand"}</p></div><p className="text-[11px] text-[#464555]">{pods.map((item) => item.name).join(", ") || "No pods"}</p></div>; })}</div> : <EmptyState title="No processes available" compact />}
        </Panel>
      </div>
    </DashboardShell>
  );
}
