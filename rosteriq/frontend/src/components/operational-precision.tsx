"use client";

import { useState } from "react";
import { CalendarDays, Download, ShieldCheck } from "lucide-react";
import {
  ActionButton,
  DashboardShell,
  EmptyState,
  FilterSearch,
  FilterSelect,
  MetricCard,
  Panel,
  PageHeader,
  Toast,
} from "@/components/dashboard-ui";

const metrics = [
  { title: "Rostered Employees", icon: "people" },
  { title: "Schedule Coverage", icon: "trending_up", tone: "teal" as const },
  { title: "Open Shift Gaps", icon: "warning", tone: "error" as const },
  { title: "Schedule Readiness", icon: "security" },
] as const;

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function OperationalPrecision() {
  const [toast, setToast] = useState("");

  function showUnavailable() {
    setToast("This action requires connected roster data.");
    window.setTimeout(() => setToast(""), 3000);
  }

  return (
    <DashboardShell activeSection="Operational Precision">
      <PageHeader
        title="Operational Precision"
        description="Review workforce assignments and schedule coverage in a focused roster workspace."
      >
        <ActionButton onClick={showUnavailable}>
          <CalendarDays aria-hidden="true" className="h-[18px] w-[18px]" />
          Select Cycle
        </ActionButton>
        <ActionButton onClick={showUnavailable}>
          <Download aria-hidden="true" className="h-[18px] w-[18px]" />
          Export Roster
        </ActionButton>
        <ActionButton variant="primary" onClick={showUnavailable}>
          <ShieldCheck aria-hidden="true" className="h-[18px] w-[18px]" />
          Validate Schedule
        </ActionButton>
      </PageHeader>

      <section
        aria-label="Operational metrics"
        className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        {metrics.map((metric) => (
          <MetricCard
            key={metric.title}
            title={metric.title}
            icon={metric.icon}
            note="No data available"
            tone={"tone" in metric ? metric.tone : "default"}
          />
        ))}
      </section>

      <section className="mb-6 rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <FilterSearch placeholder="Search roster" />
          <FilterSelect label="Cycle" />
          <FilterSelect label="Brand" />
          <FilterSelect label="Team" />
          <FilterSelect label="Process" />
        </div>
      </section>

      <Panel
        title="Operational Roster Matrix"
        subtitle="Review assignments across the operating week."
        action={
          <span className="rounded-md bg-[#f2f3ff] px-2.5 py-1 text-[11px] font-medium text-[#464555]">
            Schedule data unavailable
          </span>
        }
      >
        <div className="overflow-x-auto rounded-lg border border-[#e2e7ff]">
          <table className="w-full min-w-[960px] border-collapse text-left">
            <thead className="sticky top-0 bg-[#f7f8ff]">
              <tr>
                <th
                  scope="col"
                  className="sticky left-0 z-10 min-w-48 border-b border-r border-[#e2e7ff] bg-[#f7f8ff] px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-[#464555]"
                >
                  Employee
                </th>
                <th
                  scope="col"
                  className="min-w-36 border-b border-r border-[#e2e7ff] px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-[#464555]"
                >
                  Team / Process
                </th>
                {weekdays.map((day) => (
                  <th
                    key={day}
                    scope="col"
                    className="min-w-24 border-b border-r border-[#e2e7ff] px-3 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-[#464555] last:border-r-0"
                  >
                    {day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={weekdays.length + 2} className="p-0">
                  <EmptyState
                    title="No roster data available"
                    description="Employee assignments will appear here when roster data is connected."
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>
      <Toast message={toast} />
    </DashboardShell>
  );
}
