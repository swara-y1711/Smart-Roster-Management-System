"use client";

import { useState } from "react";
import {
  ArrowRight,
  BarChart3,
  Download,
  SlidersHorizontal,
  Zap,
} from "lucide-react";
import {
  ActionButton,
  DashboardShell,
  EmptyState,
  MetricCard,
  Panel,
  Toast,
} from "@/components/dashboard-ui";

export type ExecutiveDashboardData = {
  metrics?: Partial<Record<"workforce" | "brands" | "coverage" | "conflicts" | "offDuty" | "resilience", string>>;
  coverage?: { label: string; value: number; category?: "nominal" | "surge" | "gap" }[];
  coverageTarget?: number;
  coverageSummary?: string;
  brands?: { name: string; coverage: string; status: string }[];
  alerts?: { title: string; description: string }[];
  pods?: { name: string; capacity: string; staffing: string }[];
  activity?: { title: string; detail: string }[];
};

const metricCards = [
  { title: "Total Workforce", icon: "badge", key: "workforce" },
  { title: "Active Brands", icon: "store", key: "brands", tone: "teal" as const },
  { title: "Monthly Coverage", icon: "trending_up", key: "coverage" },
  { title: "Shift Conflicts", icon: "warning", key: "conflicts", tone: "error" as const },
  { title: "Off-Duty Today", icon: "beach_access", key: "offDuty" },
  { title: "Resilience Index", icon: "security", key: "resilience", tone: "teal" as const },
] as const;

export default function ExecutiveDashboard({ data }: { data?: ExecutiveDashboardData }) {
  const [toast, setToast] = useState("");

  function showUnavailable() {
    setToast("This action requires connected roster data.");
    window.setTimeout(() => setToast(""), 3000);
  }

  return (
    <DashboardShell activeSection="Dashboard">
      <div className="flex flex-col">
        <section className="mb-8 flex flex-col justify-between gap-6 xl:flex-row xl:items-center">
          <div className="flex flex-col gap-2">
            <h1 className="font-display text-[26px] font-bold leading-tight tracking-tight sm:text-[28px]">
              Operations Overview
            </h1>
            <p className="max-w-3xl text-[13px] leading-relaxed text-[#464555]">
              Workforce health, shift coverage, and capacity distribution across operational teams.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button className="flex h-10 items-center gap-2 rounded-xl bg-white px-3 text-[12px] font-medium shadow-sm">
              <SlidersHorizontal aria-hidden="true" className="h-[18px] w-[18px] text-[#777587]" />
              <span>All Pods</span>
            </button>
            <ActionButton onClick={showUnavailable}>
              <Download aria-hidden="true" className="h-[18px] w-[18px] text-[#777587]" />
              Export Summary
            </ActionButton>
            <ActionButton variant="primary" onClick={showUnavailable}>
              <Zap aria-hidden="true" className="h-[18px] w-[18px]" />
              Auto-Generate Roster
            </ActionButton>
          </div>
        </section>

        <section aria-label="Workforce metrics" className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
          {metricCards.map((metric) => (
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

        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-12 xl:gap-8">
          <div className="flex flex-col gap-6 xl:col-span-7 xl:gap-8">
            <Panel
              title="Daily Staffing Coverage vs Target"
              subtitle="Coverage trends and target comparison."
              action={
                <span className="rounded bg-[#eaedff] px-2.5 py-1 text-[11px] font-semibold text-[#3525cd]">
                        Coverage target
                </span>
              }
            >
              <div className="rounded-xl bg-[#f7f8ff] p-3 sm:p-4">
                {data?.coverage?.length ? (
                  <div className="flex h-48 items-center sm:h-56">
                    <svg
                      aria-label="Staffing coverage"
                      className="h-full w-full"
                      preserveAspectRatio="none"
                      role="img"
                      viewBox={`0 0 ${Math.max(740, data.coverage.length * 24 + 20)} 220`}
                    >
                      {data.coverageTarget !== undefined && (
                        <line
                          x1="0"
                          x2={Math.max(740, data.coverage.length * 24 + 20)}
                          y1={190 - Math.min(190, data.coverageTarget * 1.7)}
                          y2={190 - Math.min(190, data.coverageTarget * 1.7)}
                          stroke="#c7c4d8"
                          strokeDasharray="5 5"
                        />
                      )}
                      {data.coverage.map((point, index) => {
                        const height = Math.max(1, Math.min(180, point.value * 1.7));
                        const fill =
                          point.category === "gap"
                            ? "#ba1a1a"
                            : point.category === "surge"
                              ? "#006983"
                              : "#4f46e5";
                        return (
                          <g key={`${point.label}-${index}`}>
                            <rect
                              x={10 + index * 24}
                              y={190 - height}
                              width="16"
                              height={height}
                              rx="3"
                              fill={fill}
                            />
                            <title>{`${point.label}: ${point.value}`}</title>
                          </g>
                        );
                      })}
                    </svg>
                  </div>
                ) : (
                  <div className="flex h-48 items-center justify-center sm:h-56">
                    <EmptyState
                      title="No data available"
                      description="Coverage chart will appear when schedule data is connected."
                      compact
                    />
                  </div>
                )}
              </div>
              <div className="mt-4 flex flex-col justify-between gap-3 rounded-lg bg-[#f2f3ff] px-4 py-3 sm:flex-row sm:items-center sm:px-5">
                <div className="flex items-center gap-3 text-[13px] text-[#131b2e]">
                  <BarChart3 aria-hidden="true" className="h-5 w-5 text-[#3525cd]" />
                  <span>{data?.coverageSummary ?? "No data available"}</span>
                </div>
                <span className="text-[11px] font-semibold text-[#464555]">Coverage summary</span>
              </div>
            </Panel>

            <Panel
              title="Brand-wise Coverage Health & Process Integrity"
              subtitle="Coverage and process status by brand."
              action={
                <button onClick={showUnavailable} className="flex items-center gap-1 text-[13px] font-semibold text-[#3525cd]">
                  Detailed Matrix
                  <ArrowRight aria-hidden="true" className="h-4 w-4" />
                </button>
              }
            >
              {data?.brands?.length ? (
                data.brands.map((brand) => (
                  <article key={brand.name} className="mt-3 flex items-center justify-between gap-4 rounded-xl bg-[#f7f8ff] p-4">
                    <span className="font-display text-[14px] font-semibold">{brand.name}</span>
                    <span className="text-[12px] text-[#464555]">{brand.coverage}</span>
                    <span className="rounded-full bg-[#eaedff] px-3 py-1 text-[11px] font-semibold text-[#3525cd]">{brand.status}</span>
                  </article>
                ))
              ) : (
                <EmptyState
                  title="No data available"
                  description="Brand coverage details will appear when data is connected."
                />
              )}
            </Panel>
          </div>

          <div className="flex flex-col gap-6 xl:col-span-5 xl:gap-8">
            <Panel
              title="Operational Alerts"
              subtitle="Current schedule issues and notifications."
              action={<span className="text-[11px] text-[#777587]">Actionable alerts</span>}
            >
              {data?.alerts?.length ? (
                data.alerts.map((alert, index) => (
                  <article key={`${alert.title}-${index}`} className="mt-3 rounded-xl bg-[#f7f8ff] p-4">
                    <h3 className="text-[13px] font-semibold">{alert.title}</h3>
                    <p className="mt-1 text-[12px] text-[#464555]">{alert.description}</p>
                  </article>
                ))
              ) : (
                <EmptyState
                  title="No data available"
                  description="Operational alerts will appear here when data is connected."
                  compact
                />
              )}
            </Panel>

            <Panel
              title="Pod Resilience & Allocation"
              subtitle="Current capacity and staffing by pod."
              action={<span className="text-[11px] text-[#777587]">Current period</span>}
            >
              {data?.pods?.length ? (
                data.pods.map((pod) => (
                  <article key={pod.name} className="mt-3 flex items-center justify-between gap-3 rounded-xl bg-[#f7f8ff] p-3.5">
                    <span className="font-display text-[14px] font-semibold">{pod.name}</span>
                    <span className="text-[12px] text-[#464555]">{pod.capacity}</span>
                    <span className="text-[11px] text-[#464555]">{pod.staffing}</span>
                  </article>
                ))
              ) : (
                <EmptyState
                  title="No data available"
                  description="Pod allocation details will appear when data is connected."
                  compact
                />
              )}
            </Panel>

            <Panel
              title="Automated Engine Audit Log"
              subtitle="Recent schedule and system activity."
              action={<span className="text-[11px] text-[#777587]">Activity</span>}
            >
              <div className="rounded-lg bg-[#f2f3ff]">
                {data?.activity?.length ? (
                  data.activity.map((entry, index) => (
                    <div key={`${entry.title}-${index}`} className="border-b border-[#e2e7ff] p-3 last:border-0">
                      <p className="text-[12px] font-medium text-[#131b2e]">{entry.title}</p>
                      <p className="mt-1 text-[10px] text-[#464555]">{entry.detail}</p>
                    </div>
                  ))
                ) : <EmptyState title="No data available" compact />}
              </div>
            </Panel>

          </div>
        </div>
      </div>
      <Toast message={toast} />
    </DashboardShell>
  );
}
