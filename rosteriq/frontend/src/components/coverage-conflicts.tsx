"use client";

import { useState } from "react";
import {
  ArrowUpDown,
  CalendarDays,
  CircleAlert,
  Download,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";
import {
  ActionButton,
  DashboardShell,
  EmptyState,
  EmptyTable,
  FilterSelect,
  MetricCard,
  Panel,
  PageHeader,
  Toast,
} from "@/components/dashboard-ui";

export type CoverageConflictData = {
  metrics?: Partial<Record<"total" | "critical" | "warnings" | "brands" | "unresolved", string>>;
  conflicts?: {
    id: string;
    severity: string;
    dateWindow: string;
    brandProcess: string;
    employee: string;
    conflict: string;
  }[];
};

const metrics = [
  { title: "Total Conflicts", icon: "alert", key: "total" },
  { title: "Critical Coverage Gaps", icon: "warning", key: "critical", tone: "error" as const },
  { title: "Warnings Requiring Review", icon: "alert", key: "warnings" },
  { title: "Affected Brands", icon: "brands", key: "brands" },
  { title: "Unresolved Conflicts", icon: "calendar", key: "unresolved", tone: "teal" as const },
] as const;

const tabs = ["All", "Critical Gaps", "Warnings", "Resolved"] as const;

export default function CoverageConflicts({ data }: { data?: CoverageConflictData }) {
  const [selectedTab, setSelectedTab] = useState<(typeof tabs)[number]>("All");
  const [toast, setToast] = useState("");

  function showUnavailable() {
    setToast("This action requires connected roster data.");
    window.setTimeout(() => setToast(""), 3000);
  }

  return (
    <DashboardShell activeSection="Coverage & Conflicts">
      <PageHeader
        title="Coverage & Conflicts"
        description="Review schedule risks, coverage gaps, and policy conflicts across teams."
      >
        <ActionButton onClick={showUnavailable}>
          <Download aria-hidden="true" className="h-[18px] w-[18px]" />
          Export Audit Log
        </ActionButton>
        <ActionButton variant="primary" onClick={showUnavailable}>
          <RefreshCw aria-hidden="true" className="h-[18px] w-[18px]" />
          Revalidate Schedule
        </ActionButton>
      </PageHeader>

      <section className="mb-5 rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <label className="relative min-w-[220px] flex-1">
            <Search aria-hidden="true" className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#777587]" />
            <input aria-label="Search conflicts" placeholder="Search conflicts" className="h-10 w-full rounded-xl bg-[#f2f3ff] pl-9 pr-3 text-[12px]" />
          </label>
          <FilterSelect label="Cycle" />
          <FilterSelect label="Brand" />
          <FilterSelect label="Pod" />
          <FilterSelect label="Process" />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap rounded-lg bg-[#f2f3ff] p-1" role="group" aria-label="Conflict status filter">
            {tabs.map((tab) => (
              <button
                key={tab}
                aria-pressed={selectedTab === tab}
                onClick={() => setSelectedTab(tab)}
                className={`rounded-md px-3 py-2 text-[12px] transition-colors ${
                  selectedTab === tab ? "bg-white font-semibold text-[#131b2e] shadow-sm" : "text-[#464555]"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
          <span className="flex items-center gap-2 text-[11px] text-[#777587]">
            <CircleAlert aria-hidden="true" className="h-4 w-4" />
            Schedule validation
          </span>
        </div>
      </section>

      <section aria-label="Conflict metrics" className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
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

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-12">
        <div className="flex flex-col gap-5 xl:col-span-7">
          <Panel
            title="Active Deficit Ledger"
            subtitle="Schedule conflicts and coverage findings."
            action={
              <div className="flex items-center gap-3 text-[11px] text-[#464555]">
                <button className="flex items-center gap-1.5 rounded-lg bg-[#f2f3ff] px-2.5 py-2">
                  <ArrowUpDown aria-hidden="true" className="h-4 w-4" />
                  Sort
                </button>
                <button className="flex items-center gap-1.5 rounded-lg bg-[#f2f3ff] px-2.5 py-2">
                  <Filter aria-hidden="true" className="h-4 w-4" />
                  Columns
                </button>
              </div>
            }
          >
            <EmptyTable
              columns={["Severity", "Date & Window", "Brand & Process", "Employee", "Conflict"]}
              rows={data?.conflicts?.map((conflict) => ({
                key: conflict.id,
                cells: [
                  conflict.severity,
                  conflict.dateWindow,
                  conflict.brandProcess,
                  conflict.employee,
                  conflict.conflict,
                ],
              }))}
            />
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-[11px] text-[#777587]">
              <span>No data available</span>
              <div className="flex items-center gap-2">
                <button className="rounded-lg bg-[#f2f3ff] px-3 py-2">Previous</button>
                <span>—</span>
                <button className="rounded-lg bg-[#f2f3ff] px-3 py-2">Next</button>
              </div>
            </div>
          </Panel>

          <Panel
            title="Weekly Risk Distribution Heatmap"
            subtitle="Risk distribution across the selected period."
            action={<span className="text-[11px] text-[#777587]">Selected period</span>}
          >
            <div className="rounded-xl bg-[#f7f8ff]">
              <EmptyState
                title="No data available"
                description="The risk heatmap will appear when conflict data is connected."
              />
            </div>
          </Panel>
        </div>

        <Panel
          title="Conflict Inspector"
          subtitle="Select an item to inspect its details."
          className="xl:col-span-5"
          action={<CalendarDays aria-hidden="true" className="h-5 w-5 text-[#777587]" />}
        >
          <div className="rounded-xl bg-[#f7f8ff]">
            <EmptyState
              title="No data available"
              description="Conflict details and resolution options will appear when schedule data is connected."
            />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <ActionButton onClick={showUnavailable}>Simulate Impact</ActionButton>
            <ActionButton onClick={showUnavailable}>Override with Note</ActionButton>
          </div>
          <ActionButton variant="primary" onClick={showUnavailable}>
            Approve Resolution
          </ActionButton>
        </Panel>
      </div>
      <Toast message={toast} />
    </DashboardShell>
  );
}
