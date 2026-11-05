"use client";

import { useState } from "react";
import {
  CalendarDays,
  Check,
  CircleAlert,
  Download,
  Plus,
  WandSparkles,
  Zap,
} from "lucide-react";
import {
  ActionButton,
  DashboardShell,
  EmptyTable,
  FilterSearch,
  FilterSelect,
  Icon,
  MetricCard,
  Panel,
  PageHeader,
  Toast,
} from "@/components/dashboard-ui";

export type RosterPlannerData = {
  metrics?: Partial<Record<"scheduled" | "cycle" | "coverage" | "weeklyOff" | "leaves" | "conflicts", string>>;
  employees?: {
    id: string;
    name: string;
    pod: string;
    brand: string;
    process: string;
    hours: string;
    schedule: string[];
  }[];
};

const metrics = [
  { title: "Total Scheduled", icon: "people", key: "scheduled" },
  { title: "Operating Cycle", icon: "calendar", key: "cycle" },
  { title: "Overall Coverage", icon: "reports", key: "coverage", tone: "teal" as const },
  { title: "Allocated Weekly Off", icon: "calendar", key: "weeklyOff" },
  { title: "Approved Leaves", icon: "leave", key: "leaves" },
  { title: "Conflicts", icon: "alert", key: "conflicts", tone: "error" as const },
] as const;

const shiftLegend = [
  { label: "Working", code: "W", color: "bg-[#dcfce7] text-[#15803d]" },
  { label: "Coverage gap", code: "!", color: "bg-[#fee2e2] text-[#b91c1c]" },
  { label: "Warning", code: "?", color: "bg-[#fef3c7] text-[#b45309]" },
  { label: "Backup", code: "B", color: "bg-[#dbeafe] text-[#1d4ed8]" },
  { label: "Holiday duty", code: "H", color: "bg-[#dbeafe] text-[#1d4ed8]" },
  { label: "Approved leave", code: "L", color: "bg-[#ede9fe] text-[#6d28d9]" },
  { label: "Comp-off", code: "CO", color: "bg-[#cffafe] text-[#0e7490]" },
  { label: "Weekly off", code: "WO", color: "bg-[#f1f5f9] text-[#475569]" },
];

export default function RosterPlanner({ data }: { data?: RosterPlannerData }) {
  const [view, setView] = useState<"Month View" | "Week View" | "Brand Matrix">("Month View");
  const [toast, setToast] = useState("");

  function showUnavailable() {
    setToast("This action requires connected roster data.");
    window.setTimeout(() => setToast(""), 3000);
  }

  return (
    <DashboardShell activeSection="Roster Planner">
      <PageHeader
        title="Monthly Roster Planner"
        description="Plan and review workforce schedules across teams and processes."
      >
        <ActionButton onClick={showUnavailable}>
          <CalendarDays aria-hidden="true" className="h-[18px] w-[18px]" />
          Select Cycle
        </ActionButton>
        <ActionButton onClick={showUnavailable}>
          <Download aria-hidden="true" className="h-[18px] w-[18px]" />
          Export
        </ActionButton>
        <ActionButton onClick={showUnavailable}>
          <Plus aria-hidden="true" className="h-[18px] w-[18px]" />
          Add Assignment
        </ActionButton>
        <ActionButton variant="subtle" onClick={showUnavailable}>
          <Zap aria-hidden="true" className="h-[18px] w-[18px]" />
          Validate Schedule
        </ActionButton>
        <ActionButton variant="primary" onClick={showUnavailable}>
          <WandSparkles aria-hidden="true" className="h-[18px] w-[18px]" />
          Generate Roster
        </ActionButton>
      </PageHeader>

      <section aria-label="Roster metrics" className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
        {metrics.map((metric) => (
          <MetricCard
            key={metric.key}
            title={metric.title}
            icon={metric.icon}
            value={data?.metrics?.[metric.key] ?? "—"}
            note={data?.metrics?.[metric.key] ? "" : "No data available"}
            tone={"tone" in metric ? metric.tone : "default"}
          />
        ))}
      </section>

      <section className="mb-5 rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <FilterSearch placeholder="Search roster" />
          <FilterSelect label="Pod" />
          <FilterSelect label="Brand" />
          <FilterSelect label="Process" />
          <FilterSelect label="Status" />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center rounded-lg bg-[#f2f3ff] p-1" role="group" aria-label="Roster view">
            {(["Month View", "Week View", "Brand Matrix"] as const).map((item) => (
              <button
                key={item}
                aria-pressed={view === item}
                className={`rounded-md px-3 py-2 text-[12px] transition-colors ${
                  view === item ? "bg-white font-semibold text-[#131b2e] shadow-sm" : "text-[#464555]"
                }`}
                onClick={() => setView(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <span className="text-[12px] text-[#777587]">{view}</span>
        </div>
      </section>

      <section className="mb-5 rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[#464555]">
          <CircleAlert aria-hidden="true" className="h-4 w-4" />
          Shift Legend
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {shiftLegend.map((entry) => (
            <span key={entry.code} className="flex items-center gap-1.5 text-[12px] text-[#464555]">
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${entry.color}`}>{entry.code}</span>
              {entry.label}
            </span>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-12">
        <Panel
          title="Active Roster Schedule"
          subtitle="Schedule overview by employee and assignment."
          className="xl:col-span-8"
          action={
            <div className="flex items-center gap-2 text-[11px] text-[#777587]">
              <Check aria-hidden="true" className="h-4 w-4" />
              Schedule view
            </div>
          }
        >
          <EmptyTable
            columns={["Employee", "Pod", "Brand", "Process", "Hours", "Schedule"]}
            rows={data?.employees?.map((employee) => ({
              key: employee.id,
              cells: [
                employee.name,
                employee.pod,
                employee.brand,
                employee.process,
                employee.hours,
                employee.schedule.join(", "),
              ],
            }))}
          />
        </Panel>
        <Panel
          title="Docked Conflict Inspector"
          subtitle="Review schedule details and conflicts."
          className="xl:col-span-4"
          action={<span className="rounded-full bg-[#f2f3ff] px-2.5 py-1 text-[11px] text-[#464555]">Inspector</span>}
        >
          <div className="rounded-xl bg-[#f7f8ff]">
            <EmptyTable
              columns={["Severity", "Schedule item", "Details"]}
              title="No data available"
            />
          </div>
          <button
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#f2f3ff] px-3 py-2.5 text-[12px] font-semibold text-[#464555] hover:bg-[#e2e7ff]"
            onClick={showUnavailable}
          >
            <Icon name="reports" className="h-4 w-4" />
            Inspect selected schedule
          </button>
        </Panel>
      </div>
      <Toast message={toast} />
    </DashboardShell>
  );
}
