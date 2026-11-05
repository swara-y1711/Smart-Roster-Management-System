"use client";

import { useState } from "react";
import {
  ArrowRight,
  Download,
  Filter,
  Search,
  ShieldCheck,
  SlidersHorizontal,
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

export type WorkforceResilienceData = {
  metrics?: Partial<Record<"readiness" | "failurePoints" | "unbackedProcesses" | "dependency", string>>;
  certificationRows?: {
    id: string;
    employee: string;
    pod: string;
    qualifications: string[];
  }[];
  trainingOpportunities?: { title: string; detail: string }[];
  brandRedundancy?: { name: string; score: string; status: string }[];
};

const metrics = [
  { title: "Backup Readiness Index", icon: "security", key: "readiness", tone: "teal" as const },
  { title: "Single Points of Failure", icon: "warning", key: "failurePoints", tone: "error" as const },
  { title: "Unbacked Processes", icon: "processes", key: "unbackedProcesses" },
  { title: "Staffing Dependency", icon: "brands", key: "dependency", tone: "error" as const },
] as const;

export default function WorkforceResilience({ data }: { data?: WorkforceResilienceData }) {
  const [toast, setToast] = useState("");

  function showUnavailable() {
    setToast("This action requires connected workforce data.");
    window.setTimeout(() => setToast(""), 3000);
  }

  return (
    <DashboardShell activeSection="Workforce Resilience">
      <PageHeader
        title="Workforce Resilience"
        description="Understand staffing vulnerabilities, backup readiness, and workforce continuity."
      >
        <ActionButton variant="primary" onClick={showUnavailable}>
          <ShieldCheck aria-hidden="true" className="h-[18px] w-[18px]" />
          Run Resilience Audit
        </ActionButton>
        <ActionButton onClick={showUnavailable}>
          <Download aria-hidden="true" className="h-[18px] w-[18px]" />
          Export Resilience Matrix
        </ActionButton>
      </PageHeader>

      <section className="mb-6 rounded-xl bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <FilterSelect label="Cycle" />
          <FilterSelect label="Brand" />
          <FilterSelect label="Pod" />
          <FilterSelect label="Process" />
          <div className="ml-auto flex items-center gap-2 rounded-xl bg-[#f2f3ff] px-3 py-2 text-[11px] text-[#464555]">
            <span className="h-2 w-2 rounded-full bg-[#777587]" />
            Resilience data unavailable
          </div>
        </div>
      </section>

      <section aria-label="Resilience metrics" className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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

      <Panel
        title="Critical Process Resilience"
        subtitle="Review process dependencies and continuity coverage."
        action={<span className="rounded-full bg-[#f2f3ff] px-2.5 py-1 text-[11px] text-[#464555]">Process overview</span>}
        className="mb-6"
      >
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-xl border border-[#eaedff] bg-[#f7f8ff] p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#777587]">Process overview</span>
              <span className="rounded bg-[#eaedff] px-2 py-1 text-[10px] font-semibold text-[#464555]">Status unavailable</span>
            </div>
            <EmptyState
              title="No data available"
              description="Process coverage and workforce dependency details will appear when data is connected."
              compact
            />
          </div>
          <div className="rounded-xl border border-[#eaedff] bg-white p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="font-display text-[15px] font-semibold">Backup Recommendation</h3>
              <span className="text-[11px] text-[#777587]">Recommendation</span>
            </div>
            <EmptyState
              title="No data available"
              description="Recommendations will appear when workforce qualifications are available."
              compact
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <ActionButton variant="primary" onClick={showUnavailable}>Review Recommendation</ActionButton>
              <ActionButton onClick={showUnavailable}>View Alternatives</ActionButton>
            </div>
          </div>
        </div>
      </Panel>

      <Panel
        title="Cross-Brand Skill & Backup Certification Matrix"
        subtitle="View qualifications and backup coverage by process."
        className="mb-6"
        action={
          <div className="flex items-center gap-2">
            <label className="relative hidden sm:block">
              <Search aria-hidden="true" className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#777587]" />
              <input aria-label="Search workforce matrix" placeholder="Search workforce" className="h-9 w-48 rounded-lg bg-[#f2f3ff] pl-9 pr-3 text-[11px]" />
            </label>
            <button onClick={showUnavailable} className="flex h-9 items-center gap-1.5 rounded-lg bg-[#f2f3ff] px-3 text-[11px] font-medium">
              <Filter aria-hidden="true" className="h-4 w-4" />
              Filters
            </button>
          </div>
        }
      >
        <div className="mb-4 flex flex-wrap gap-2 rounded-lg bg-[#f7f8ff] p-3 text-[10px] text-[#464555]">
          <span className="font-semibold uppercase tracking-wider">Legend:</span>
          <span>Primary assignment</span>
          <span>Qualified backup</span>
          <span>Training required</span>
          <span>Not qualified</span>
        </div>
        <EmptyTable
          columns={["Employee & ID / Pod", "Process", "Primary assignment", "Qualified backup", "Training"]}
          rows={data?.certificationRows?.map((row) => ({
            key: row.id,
            cells: [
              row.employee,
              row.pod,
              ...row.qualifications.slice(0, 3),
              ...Array.from({ length: Math.max(0, 3 - row.qualifications.length) }, () => "—"),
            ],
          }))}
        />
      </Panel>

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-2">
        <Panel
          title="Cross-Training Opportunities"
          subtitle="Prioritized training pipeline."
          action={
            <button onClick={showUnavailable} className="flex items-center gap-1 text-[12px] font-semibold text-[#3525cd]">
              View All
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </button>
          }
        >
          <div className="mb-3 flex items-center justify-between text-[11px] text-[#777587]">
            <span>Training pipeline</span>
            <SlidersHorizontal aria-hidden="true" className="h-4 w-4" />
          </div>
          {data?.trainingOpportunities?.length ? (
            data.trainingOpportunities.map((item, index) => (
              <article key={`${item.title}-${index}`} className="mb-3 rounded-xl bg-[#f7f8ff] p-4 last:mb-0">
                <h3 className="text-[13px] font-semibold">{item.title}</h3>
                <p className="mt-1 text-[11px] text-[#464555]">{item.detail}</p>
              </article>
            ))
          ) : (
            <EmptyState title="No data available" description="Training opportunities will appear when data is connected." />
          )}
        </Panel>

        <Panel
          title="Brand-Level Redundancy Index"
          subtitle="Backup coverage and continuity by brand."
          action={<SlidersHorizontal aria-hidden="true" className="h-4 w-4 text-[#777587]" />}
        >
          {data?.brandRedundancy?.length ? (
            data.brandRedundancy.map((brand) => (
              <article key={brand.name} className="mb-3 flex items-center justify-between gap-3 rounded-xl bg-[#f7f8ff] p-4 last:mb-0">
                <span className="font-display text-[13px] font-semibold">{brand.name}</span>
                <span className="text-[12px] text-[#464555]">{brand.status}</span>
                <span className="font-display text-[14px] font-bold text-[#3525cd]">{brand.score}</span>
              </article>
            ))
          ) : (
            <EmptyState title="No data available" description="Brand-level resilience details will appear when data is connected." />
          )}
        </Panel>
      </div>
      <Toast message={toast} />
    </DashboardShell>
  );
}
