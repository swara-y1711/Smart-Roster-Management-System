"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { ActionButton, DashboardShell, EmptyState, MetricCard, Panel, PageHeader, Toast } from "@/components/dashboard-ui";
import { api, apiErrorMessage } from "@/lib/api";
import { displayName, useRosterData } from "@/lib/use-roster-data";
import { useCurrentDate } from "@/lib/use-current-date";

type Impact = { invalidated_assignments: { assignment: { assignment_date: string; employee_name?: string; brand?: string; process?: string; pod?: string; shift?: string }; reason: string; conflict_type: string; suggested_resolution?: string; possible_backup_employee_ids: string[] }[]; replacement_assignments: { assignment_date: string; employee_name?: string; employee_id: string; brand?: string; process?: string; shift?: string }[]; coverage_summary: { required_staff: number; actual_staff: number; brand: string; process: string; date: string; unfilled_positions: string[] }[]; conflicts: { severity: string; explanation: string; conflict_type: string }[]; required_staffing: number; actual_staffing: number };

export default function WorkforceResilience() {
  const data = useRosterData();
  const currentDate = useCurrentDate();
  const [employee, setEmployee] = useState("");
  const [selectedStartDate, setSelectedStartDate] = useState<string | null>(null);
  const [selectedEndDate, setSelectedEndDate] = useState<string | null>(null);
  const startDate = selectedStartDate ?? currentDate;
  const endDate = selectedEndDate ?? currentDate;
  const setStartDate = setSelectedStartDate;
  const setEndDate = setSelectedEndDate;
  const [kind, setKind] = useState<"employee_unavailable" | "planned_leave">("employee_unavailable");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const run = async () => {
    if (!employee) {
      setError("Select an employee to run the analysis");
      return;
    }
    if (!data.organization) {
      setError("No organization is available for impact analysis.");
      return;
    }
    setBusy(true);
    setError("");
    setImpact(null);
    try {
      setImpact(await api.post<Impact>("/scheduling/impact", {
        organization_id: data.organization.id,
        start_date: startDate,
        end_date: endDate,
        change: { change_type: kind, employee_id: employee, start_date: startDate, end_date: endDate },
      }));
      setToast("Impact analysis completed without modifying the roster.");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const selectedEmployee = data.employees.find((item) => item.id === employee); const coverage = impact?.required_staffing ? Math.round(impact.actual_staffing / impact.required_staffing * 100) : 0;
  const periodAssignments = data.assignments.filter((item) => item.assignment_date >= startDate && item.assignment_date <= endDate);
  const savedAssignmentsInMonth = data.assignments.some((item) => item.assignment_date.startsWith(startDate.slice(0, 7)));
  const selectedEmployeeHasAssignments = periodAssignments.some((item) => item.employee_id === employee);
  const monthDate = new Date(`${startDate || ""}T00:00:00Z`);
  const safeMonthDate = Number.isNaN(monthDate.getTime()) ? new Date("2026-11-01T00:00:00Z") : monthDate;
  const monthLabel = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" }).format(safeMonthDate);
  const emptyResult = !savedAssignmentsInMonth
    ? `No saved roster for ${monthLabel}. Save a roster in Roster Planner first.`
    : !selectedEmployeeHasAssignments
      ? "No saved assignments for this employee in this period (0 affected)."
      : "No assignments are invalidated";
  return <DashboardShell activeSection="Workforce Resilience">
    <PageHeader title="Workforce Resilience" description="Simulate unavailability and leave against the saved roster to identify affected work and eligible backups."><ActionButton variant="primary" onClick={() => void run()} disabled={!data.organization || !employee || busy}><ShieldCheck className="h-4 w-4" />{busy ? "Running analysis…" : "Run impact analysis"}</ActionButton></PageHeader>
    {(data.error || error) && <p role="alert" className="mb-5 rounded-xl bg-[#ffdad6] px-4 py-3 text-sm text-[#93000a]">{data.error || error}</p>}
    <section className="mb-6 rounded-xl bg-white p-4 shadow-sm"><div className="flex flex-wrap items-end gap-3"><label className="min-w-[240px] text-[11px] font-semibold">Employee<select value={employee} onChange={(event) => { setEmployee(event.target.value); setError(""); }} className="mt-1 block h-10 w-full rounded-xl bg-[#f2f3ff] px-3 text-[12px]"><option value="">Choose existing employee</option>{data.employees.map((item) => <option key={item.id} value={item.id}>{displayName(item)} · {item.employee_code}</option>)}</select>{!employee && <span className="mt-1 block text-[11px] font-medium text-[#93000a]">Select an employee to run the analysis</span>}</label><label className="text-[11px] font-semibold">Change type<select value={kind} onChange={(event) => setKind(event.target.value as typeof kind)} className="mt-1 block h-10 rounded-xl bg-[#f2f3ff] px-3 text-[12px]"><option value="employee_unavailable">Unavailability</option><option value="planned_leave">Planned leave</option></select></label><label className="text-[11px] font-semibold">Start<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="mt-1 block h-10 rounded-xl bg-[#f2f3ff] px-3 text-[12px]" /></label><label className="text-[11px] font-semibold">End<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="mt-1 block h-10 rounded-xl bg-[#f2f3ff] px-3 text-[12px]" /></label><p className="max-w-xs text-[11px] text-[#777587]">This is a simulation. It does not write leave or roster records.</p></div></section>
    <section className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4"><MetricCard title="Selected resource" icon="people" value={selectedEmployee ? displayName(selectedEmployee) : "—"} note="Existing workforce" /><MetricCard title="Affected assignments" icon="warning" value={String(impact?.invalidated_assignments.length || 0)} note="Would be invalidated" tone="error" /><MetricCard title="Backup replacements" icon="security" value={String(impact?.replacement_assignments.length || 0)} note="Engine suggestions" tone="teal" /><MetricCard title="Remaining coverage" icon="trending_up" value={impact ? `${coverage}%` : "—"} note={impact ? `${impact.actual_staffing}/${impact.required_staffing} positions` : "Run an analysis"} /></section>
    <div className="grid items-start gap-6 xl:grid-cols-2"><Panel scroll height="clamp(360px, 65vh, 640px)" ariaLabel="Affected work and backup suggestions list" title="Affected work and backup suggestions" subtitle="Single-resource brands expose every dependent process; multi-resource brands show eligible replacements.">{impact ? impact.invalidated_assignments.length ? <div className="min-w-max space-y-3">{impact.invalidated_assignments.map((item, index) => <article key={`${item.assignment.assignment_date}-${index}`} className="rounded-xl bg-[#fff0ef] p-4"><div className="flex flex-wrap justify-between gap-2 whitespace-nowrap text-[12px] font-semibold"><span>{item.assignment.assignment_date} · {item.assignment.brand || "—"} / {item.assignment.process || "—"}</span><span>{item.conflict_type}</span></div><p className="mt-2 text-[12px]">{item.reason}</p>{item.suggested_resolution && <p className="mt-2 text-[11px] text-[#464555]">Suggested: {item.suggested_resolution}</p>}<p className="mt-2 text-[11px] font-semibold">{item.possible_backup_employee_ids.length ? `Eligible backups: ${item.possible_backup_employee_ids.map((id) => displayName(data.employees.find((entry) => entry.id === id))).join(", ")}` : "No eligible backup exists in the current workforce."}</p></article>)}</div> : <EmptyState title={emptyResult} description={emptyResult === "No assignments are invalidated" ? "The selected employee change can be absorbed by the saved roster for this period." : undefined} /> : <EmptyState title="Choose an employee and run analysis" description="Results are computed by the FastAPI scheduling engine." />}</Panel>
      <Panel scroll height="clamp(360px, 65vh, 640px)" ariaLabel="Coverage after change list" title="Coverage after change" subtitle="The simulated report is returned by the backend and is not persisted.">{impact ? selectedEmployeeHasAssignments && savedAssignmentsInMonth ? <div className="min-w-max space-y-2">{impact.coverage_summary.slice(0, 20).map((row, index) => <div key={`${row.date}-${row.process}-${index}`} className="flex items-center justify-between whitespace-nowrap rounded-xl bg-[#f7f8ff] p-3 text-[12px]"><span>{row.date} · {row.brand} / {row.process}</span><span className={row.actual_staff < row.required_staff ? "font-semibold text-[#93000a]" : "text-[#15803d]"}>{row.actual_staff}/{row.required_staff}</span></div>)}{impact.conflicts.length ? <div className="mt-4 space-y-2">{impact.conflicts.map((item, index) => <div key={`${item.conflict_type}-${index}`} className="rounded-xl bg-[#fff8df] p-3 text-[12px]"><span className="font-semibold">{item.severity} · {item.conflict_type}</span><p className="mt-1">{item.explanation}</p></div>)}</div> : null}</div> : <EmptyState title={emptyResult} compact /> : <EmptyState title="No impact report" compact />}</Panel></div>
    <Toast message={toast} />
  </DashboardShell>;
}
