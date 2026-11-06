"use client";

import { useMemo, useState } from "react";
import { Check, RefreshCw, Save, WandSparkles } from "lucide-react";
import { ActionButton, DashboardShell, EmptyState, MetricCard, Panel, PageHeader, Toast } from "@/components/dashboard-ui";
import { apiErrorMessage } from "@/lib/api";
import { displayName, useRosterData, type RosterAssignment } from "@/lib/use-roster-data";
import { useCurrentDate } from "@/lib/use-current-date";
import { generateWorkspaceReport, publishWorkspaceRoster, saveWorkspaceRoster, validateWorkspaceReport, type ScheduleReport } from "@/lib/workspace-scheduling";

type Assignment = RosterAssignment & { employee_name?: string; brand_id?: string; process_id?: string; pod_id?: string; brand?: string; process?: string; pod?: string; shift?: string };
type Report = ScheduleReport & { assignments: Assignment[] };

const monthLabel = (year: number, month: number) => new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(new Date(year, month - 1, 1));

export default function RosterPlanner() {
  const data = useRosterData();
  const currentDate = useCurrentDate();
  const [selectedPeriod, setSelectedPeriod] = useState("");
  const period = selectedPeriod || currentDate.slice(0, 7);
  const [year = 0, month = 0] = period.split("-").map(Number);
  const [report, setReport] = useState<Report | null>(null);
  const [brand, setBrand] = useState(""); const [process, setProcess] = useState(""); const [pod, setPod] = useState(""); const [employee, setEmployee] = useState(""); const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(""); const [error, setError] = useState(""); const [toast, setToast] = useState(""); const [saved, setSaved] = useState(false); const [published, setPublished] = useState(false);

  const generate = async () => {
    if (!data.organizations.length || !year || !month) return;
    setBusy("generate"); setError(""); setSaved(false); setPublished(false);
    try { setReport(await generateWorkspaceReport(data.organizations, year, month) as Report); setToast("Roster proposal generated for the full workforce."); }
    catch (e) { setError(apiErrorMessage(e)); }
    finally { setBusy(""); }
  };
  const validate = async () => {
    if (!data.organizations.length || !report || !year || !month) return;
    setBusy("validate"); setError("");
    try { setReport(await validateWorkspaceReport(data.organizations, data.employees, report, year, month) as Report); setToast("Proposal validated against current workforce rules."); }
    catch (e) { setError(apiErrorMessage(e)); }
    finally { setBusy(""); }
  };
  const save = async () => {
    if (!data.organizations.length || !report || !year || !month) return;
    setBusy("save"); setError("");
    try { await saveWorkspaceRoster(data.organizations, data.employees, report, year, month); setSaved(true); setToast("Validated roster saved as scheduled."); await data.refresh(true); }
    catch (e) { setError(apiErrorMessage(e)); }
    finally { setBusy(""); }
  };
  const publish = async () => {
    if (!data.organizations.length || !saved || !year || !month) return;
    setBusy("publish"); setError("");
    try { await publishWorkspaceRoster(data.organizations, year, month); setPublished(true); setToast("Roster published successfully."); await data.refresh(true); }
    catch (e) { setError(apiErrorMessage(e)); }
    finally { setBusy(""); }
  };
  const edit = (index: number, key: "employee_id" | "shift_id", value: string) => setReport((current) => current ? { ...current, assignments: current.assignments.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value, employee_name: key === "employee_id" ? displayName(data.employees.find((employeeItem) => employeeItem.id === value)) : item.employee_name } : item), is_valid: false } : current);
  const filtered = useMemo(() => (report?.assignments || []).filter((item) => (!brand || item.brand_id === brand || item.brand === data.brands.find((entry) => entry.id === brand)?.name) && (!process || item.process_id === process) && (!pod || item.pod_id === pod) && (!employee || item.employee_id === employee) && (!search || `${item.employee_name} ${item.brand} ${item.process} ${item.pod}`.toLowerCase().includes(search.toLowerCase()))), [report, brand, process, pod, employee, search, data.brands]);
  const coverage = report?.required_staffing ? Math.round(report.actual_staffing / report.required_staffing * 100) : 0;
  const unscheduled = report?.employee_diagnostics?.filter((item) => item.scheduled_assignments === 0) || [];
  const getIndex = (item: Assignment) => report?.assignments.findIndex((candidate) => candidate === item) ?? -1;

  return <DashboardShell activeSection="Roster Planner">
    <PageHeader title="Monthly Roster Planner" description="Generate a proposal for all workforce records visible to this manager, review coverage, make controlled edits, then validate and publish it."><ActionButton onClick={() => void data.refresh(true)}><RefreshCw className="h-4 w-4" />{data.loading ? "Refreshing…" : "Refresh"}</ActionButton><ActionButton variant="subtle" onClick={() => void validate()} disabled={!data.organizations.length || !report || Boolean(busy)}><Check className="h-4 w-4" />{busy === "validate" ? "Validating…" : "Validate"}</ActionButton><ActionButton variant="primary" onClick={() => void generate()} disabled={!data.organizations.length || Boolean(busy)}><WandSparkles className="h-4 w-4" />{busy === "generate" ? "Generating…" : "Generate roster"}</ActionButton></PageHeader>
    {data.source === "sample" && <p role="status" className="mb-5 rounded-xl bg-[#fff4d6] px-4 py-3 text-sm text-[#624b00]">The default Faker workforce is available for review. Generating, saving, and publishing rosters require database-backed workforce records.</p>}
    {(data.error || error) && <p role="alert" className="mb-5 rounded-xl bg-[#ffdad6] px-4 py-3 text-sm text-[#93000a]">{data.error || error}</p>}
    <section className="mb-5 rounded-xl bg-white p-4 shadow-sm"><div className="flex flex-wrap items-end gap-3"><label className="text-[11px] font-semibold text-[#464555]">Month<input type="month" value={period} onChange={(event) => setSelectedPeriod(event.target.value)} className="mt-1 block h-10 rounded-xl bg-[#f2f3ff] px-3 text-[12px]" /></label><label className="min-w-[220px] flex-1 text-[11px] font-semibold text-[#464555]">Search<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Employee, brand, process or pod" className="mt-1 h-10 w-full rounded-xl bg-[#f2f3ff] px-3 text-[12px]" /></label><Select label="Brand" value={brand} onChange={setBrand} options={data.brands.map((item) => [item.id, item.name])} /><Select label="Process" value={process} onChange={setProcess} options={data.processes.map((item) => [item.id, item.name])} /><Select label="Pod" value={pod} onChange={setPod} options={data.pods.map((item) => [item.id, item.name])} /><Select label="Employee" value={employee} onChange={setEmployee} options={data.employees.map((item) => [item.id, displayName(item)])} /></div></section>
    <section className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-5"><MetricCard title="Proposal" icon="calendar" value={report ? monthLabel(year, month) : "—"} note={report ? (saved ? published ? "Published" : "Saved" : "Generated, not saved") : "Select a month"} /><MetricCard title="Employees scheduled" icon="people" value={String(new Set((report?.assignments || []).map((item) => item.employee_id)).size)} note={`Of ${data.employees.length} visible employees`} /><MetricCard title="Assignments" icon="reports" value={String(report?.assignments.length || 0)} note="Working assignments" /><MetricCard title="Coverage" icon="trending_up" value={report ? `${coverage}%` : "—"} note={report ? `${report.actual_staffing}/${report.required_staffing} positions` : "No proposal"} tone={coverage < 100 && report ? "error" : "teal"} /><MetricCard title="Unfilled" icon="warning" value={String(report?.statistics.unfilled_positions || 0)} note="Mandatory gaps" tone="error" /></section>
    {unscheduled.length ? <Panel scroll ariaLabel="Employees not scheduled list" title="Employees not scheduled" subtitle="Each reason is returned by the scheduling engine from pod, availability, time-off, weekly-off, shift and staffing rules." className="mb-6"><div className="grid min-w-max gap-2 md:grid-cols-2">{unscheduled.map((item) => <div key={item.employee_id} className="rounded-xl bg-[#fff8df] p-3 text-[12px] whitespace-nowrap"><p className="font-semibold">{displayName(data.employees.find((entry) => entry.id === item.employee_id))}</p><p className="mt-1 text-[#464555]">{item.reason}</p></div>)}</div></Panel> : null}
    <Panel scroll ariaLabel="Roster proposal table" direction="both" height="clamp(420px, 65vh, 640px)" title="Roster proposal" subtitle={report ? `${monthLabel(year, month)} · ${report.is_valid ? "Valid" : "Requires review"}` : "No proposal generated yet."} action={<div className="flex gap-2"><ActionButton onClick={() => void save()} disabled={!data.organization || !report || Boolean(busy)}>{busy === "save" ? "Saving…" : <><Save className="h-4 w-4" />Save validated</>}</ActionButton><ActionButton variant="primary" onClick={() => void publish()} disabled={!data.organization || !saved || Boolean(busy)}>{busy === "publish" ? "Publishing…" : published ? "Published" : "Publish"}</ActionButton></div>}>
      {!report ? <EmptyState title="Generate a monthly proposal" description={data.source === "sample" ? "The sample workforce is read-only. Database-backed workforce records are required for roster scheduling." : "The scheduling engine will use all visible employee, availability, skill, pod, shift and staffing configuration records."} /> : <table className="w-full min-w-[900px] whitespace-nowrap text-left text-[12px]"><thead className="sticky top-0 z-10 bg-[#f7f8ff]"><tr>{["Date", "Employee", "Brand / Process", "Pod", "Shift", "Status"].map((title) => <th key={title} className="border-b border-[#e2e7ff] bg-[#f7f8ff] px-3 py-3 text-[11px] uppercase tracking-wider">{title}</th>)}</tr></thead><tbody>{filtered.slice(0, 250).map((item) => { const index = getIndex(item); const employeeItem = data.employees.find((entry) => entry.id === item.employee_id); const shiftItem = data.shifts.find((entry) => entry.id === item.shift_id); return <tr key={`${item.assignment_date}-${item.employee_id}-${item.shift_id}-${index}`} className="hover:bg-[#f7f8ff]"><td className="border-b border-[#eaedff] px-3 py-2">{item.assignment_date}</td><td className="border-b border-[#eaedff] px-3 py-2"><select aria-label="Assignment employee" value={item.employee_id} onChange={(event) => edit(index, "employee_id", event.target.value)} className="max-w-[190px] rounded bg-[#f2f3ff] px-2 py-1"><option value={item.employee_id}>{item.employee_name || displayName(employeeItem)}</option>{data.employees.map((entry) => <option key={entry.id} value={entry.id}>{displayName(entry)}</option>)}</select></td><td className="border-b border-[#e2e7ff] px-3 py-2">{item.brand} / {item.process}</td><td className="border-b border-[#e2e7ff] px-3 py-2">{item.pod}</td><td className="border-b border-[#eaedff] px-3 py-2"><select aria-label="Assignment shift" value={item.shift_id} onChange={(event) => edit(index, "shift_id", event.target.value)} className="rounded bg-[#f2f3ff] px-2 py-1"><option value={item.shift_id}>{item.shift || shiftItem?.shift_name || "Shift"}</option>{data.shifts.filter((entry) => entry.pod_id === item.pod_id).map((entry) => <option key={entry.id} value={entry.id}>{entry.shift_name}</option>)}</select></td><td className="border-b border-[#eaedff] px-3 py-2"><span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${item.status === "published" ? "bg-[#dcfce7] text-[#15803d]" : report.is_valid ? "bg-[#dcfce7] text-[#15803d]" : "bg-[#fef3c7] text-[#b45309]"}`}>{item.status || (report.is_valid ? "Valid proposal" : "Review")}</span></td></tr>; })}</tbody></table>}
    </Panel>
    {report?.conflicts.length ? <Panel scroll ariaLabel="Roster conflict findings" title="Conflict inspector" subtitle="Errors block saving; warnings document preference trade-offs." className="mt-6"><div className="space-y-2">{report.conflicts.map((conflict, index) => <div key={`${conflict.date}-${conflict.conflict_type}-${index}`} className={`min-w-max rounded-xl p-3 ${conflict.severity === "error" ? "bg-[#fff0ef]" : "bg-[#fff8df]"}`}><div className="flex flex-wrap justify-between gap-2 whitespace-nowrap text-[11px] font-semibold"><span>{conflict.severity.toUpperCase()} · {conflict.conflict_type}</span><span>{conflict.date} · {conflict.brand || "—"} / {conflict.process || "—"}</span></div><p className="mt-1 text-[12px]">{conflict.explanation}</p>{conflict.suggested_resolution && <p className="mt-1 text-[11px] text-[#464555]">Suggested: {conflict.suggested_resolution}</p>}</div>)}</div></Panel> : null}
    <Toast message={toast} />
  </DashboardShell>;
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: [string, string][] }) { return <label className="text-[11px] font-semibold text-[#464555]">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 block h-10 max-w-[180px] rounded-xl bg-[#f2f3ff] px-3 text-[12px]"><option value="">All</option>{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>; }
