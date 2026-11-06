"use client";

import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ActionButton, DashboardShell, EmptyState, MetricCard, Panel, PageHeader, Toast } from "@/components/dashboard-ui";
import { apiErrorMessage } from "@/lib/api";
import { useRosterData } from "@/lib/use-roster-data";
import { useCurrentDate } from "@/lib/use-current-date";
import { generateWorkspaceReport, validateWorkspaceReport, type ScheduleReport } from "@/lib/workspace-scheduling";

type Conflict = { date: string; brand?: string; process?: string; employee_id?: string; conflict_type: string; severity: "error" | "warning"; explanation: string; suggested_resolution?: string };
type Report = ScheduleReport;

export default function CoverageConflicts() {
  const data = useRosterData();
  const currentDate = useCurrentDate();
  const [selectedPeriod, setSelectedPeriod] = useState("");
  const period = selectedPeriod || currentDate.slice(0, 7);
  const [year = 0, month = 0] = period.split("-").map(Number);
  const [report, setReport] = useState<Report | null>(null);
  const [severity, setSeverity] = useState("");
  const [brand, setBrand] = useState("");
  const [process, setProcess] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Conflict | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [conflictLimit, setConflictLimit] = useState(50);
  const validate = async () => { if (!data.organizations.length) return; setBusy(true); setError(""); try { const generated = await generateWorkspaceReport(data.organizations, year, month); const validated = await validateWorkspaceReport(data.organizations, data.employees, generated, year, month); setReport(validated); setToast("Full-workforce schedule validation completed."); } catch (e) { setError(apiErrorMessage(e)); } finally { setBusy(false); } };
  const conflicts = useMemo(() => (report?.conflicts || []).filter((item) => (!severity || item.severity === severity) && (!brand || item.brand === data.brands.find((entry) => entry.id === brand)?.name) && (!process || item.process === data.processes.find((entry) => entry.id === process)?.name) && (!search || `${item.conflict_type} ${item.explanation} ${item.brand} ${item.process}`.toLowerCase().includes(search.toLowerCase()))), [report, severity, brand, process, search, data.brands, data.processes]);
  const coverage = report?.required_staffing ? Math.round(report.actual_staffing / report.required_staffing * 100) : 0;
  return <DashboardShell activeSection="Coverage & Conflicts">
    <PageHeader title="Coverage & Conflicts" description="Inspect validation results for the full manager-visible workforce's generated monthly proposal, including coverage gaps and real constraint findings."><ActionButton variant="primary" onClick={() => void validate()} disabled={busy || data.loading}><RefreshCw className="h-4 w-4" />{busy ? "Validating…" : "Revalidate schedule"}</ActionButton></PageHeader>
    {(data.error || error) && <p role="alert" className="mb-5 rounded-xl bg-[#ffdad6] px-4 py-3 text-sm text-[#93000a]">{data.error || error}</p>}
    <section className="mb-5 rounded-xl bg-white p-4 shadow-sm"><div className="flex flex-wrap items-end gap-3"><label className="text-[11px] font-semibold">Cycle<input type="month" value={period} onChange={(event) => setSelectedPeriod(event.target.value)} className="mt-1 block h-10 rounded-xl bg-[#f2f3ff] px-3 text-[12px]" /></label><label className="min-w-[220px] flex-1 text-[11px] font-semibold">Search<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search conflicts" className="mt-1 h-10 w-full rounded-xl bg-[#f2f3ff] px-3 text-[12px]" /></label><Select label="Severity" value={severity} onChange={setSeverity} options={[["error", "Errors"], ["warning", "Warnings"]]} /><Select label="Brand" value={brand} onChange={setBrand} options={data.brands.map((item) => [item.id, item.name])} /><Select label="Process" value={process} onChange={setProcess} options={data.processes.map((item) => [item.id, item.name])} /></div></section>
    <section className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5"><MetricCard title="Validation" icon="security" value={report ? report.is_valid ? "Valid" : "Action needed" : "—"} note="Mandatory constraints" tone={report && !report.is_valid ? "error" : "teal"} /><MetricCard title="Required staffing" icon="people" value={String(report?.required_staffing || 0)} note="Positions" /><MetricCard title="Actual staffing" icon="badge" value={String(report?.actual_staffing || 0)} note={report ? `${coverage}% coverage` : "No report"} /><MetricCard title="Errors" icon="warning" value={String(report?.conflicts.filter((item) => item.severity === "error").length || 0)} note="Mandatory violations" tone="error" /><MetricCard title="Warnings" icon="alert" value={String(report?.conflicts.filter((item) => item.severity === "warning").length || 0)} note="Preference findings" /></section>
    <div className="grid items-start gap-6 xl:grid-cols-7"><Panel scroll height="clamp(360px, 65vh, 640px)" ariaLabel="Coverage ledger table" title="Coverage ledger" subtitle="Required versus actual staffing by date, brand and process." className="xl:col-span-4">{report ? <table className="w-full min-w-[680px] whitespace-nowrap text-left text-[12px]"><thead className="sticky top-0 z-10 bg-[#f7f8ff]"><tr>{["Date", "Brand", "Process", "Required", "Actual", "Gaps"].map((item) => <th key={item} className="border-b border-[#e2e7ff] bg-[#f7f8ff] px-3 py-3 text-[11px] uppercase">{item}</th>)}</tr></thead><tbody>{report.coverage_summary.map((row, index) => <tr key={`${row.date}-${row.process}-${index}`} className="hover:bg-[#f7f8ff]"><td className="border-b border-[#eaedff] px-3 py-2">{row.date}</td><td className="border-b border-[#eaedff] px-3 py-2">{row.brand}</td><td className="border-b border-[#eaedff] px-3 py-2">{row.process}</td><td className="border-b border-[#eaedff] px-3 py-2">{row.required_staff}</td><td className="border-b border-[#eaedff] px-3 py-2">{row.actual_staff}</td><td className={`border-b border-[#eaedff] px-3 py-2 font-semibold ${row.unfilled_positions.length ? "text-[#93000a]" : "text-[#15803d]"}`}>{row.unfilled_positions.length || "—"}</td></tr>)}</tbody></table> : <EmptyState title="Run validation" description="Choose a cycle and validate the generated proposal to inspect coverage." />}</Panel>
      <Panel scroll height="clamp(360px, 65vh, 640px)" ariaLabel="Conflict findings list" title="Conflict inspector" subtitle="Errors are mandatory failures; warnings are preference trade-offs." className="xl:col-span-3">{report ? <div className="space-y-2">{conflicts.length ? conflicts.slice(0, conflictLimit).map((item, index) => <button key={`${item.date}-${item.conflict_type}-${index}`} onClick={() => setSelected(item)} className={`block w-full rounded-xl p-3 text-left ${item.severity === "error" ? "bg-[#fff0ef]" : "bg-[#fff8df]"}`}><div className="flex justify-between gap-2 text-[10px] font-bold"><span>{item.severity.toUpperCase()} · {item.conflict_type}</span><span>{item.date}</span></div><p className="mt-1 text-[12px]">{item.explanation}</p></button>) : <EmptyState title="No matching findings" compact />}{conflicts.length > conflictLimit && <button type="button" onClick={() => setConflictLimit((limit) => Math.min(limit + 50, conflicts.length))} className="w-full rounded-xl bg-[#eaedff] px-3 py-2 text-[12px] font-semibold text-[#3525cd]">Show more findings ({conflicts.length - conflictLimit} remaining)</button>} {selected && <div className="rounded-xl border border-[#e2e7ff] bg-white p-3 text-[12px]"><p className="font-semibold">{selected.brand || "—"} / {selected.process || "—"}</p><p className="mt-1">Employee: {selected.employee_id || "Process-level"}</p>{selected.suggested_resolution && <p className="mt-2 text-[#464555]">Suggested resolution: {selected.suggested_resolution}</p>}</div>}</div> : <EmptyState title="No validation results" description="Validation findings will be listed here." />}</Panel></div>
    <Toast message={toast} />
  </DashboardShell>;
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: [string, string][] }) { return <label className="text-[11px] font-semibold">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 block h-10 max-w-[180px] rounded-xl bg-[#f2f3ff] px-3 text-[12px]"><option value="">All</option>{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>; }
