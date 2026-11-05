"use client";

import { useState } from "react";
import { ArrowRight, Building2, Database, Settings2 } from "lucide-react";
import {
  ActionButton,
  DashboardShell,
  EmptyState,
  MetricCard,
  Panel,
  PageHeader,
  Toast,
} from "@/components/dashboard-ui";

const metrics = [
  { title: "Organization Units", icon: "brands" },
  { title: "Configured Processes", icon: "processes", tone: "teal" as const },
  { title: "Workforce Teams", icon: "pods" },
  { title: "System Readiness", icon: "security" },
] as const;

export default function RosterIQSystem() {
  const [toast, setToast] = useState("");

  function showUnavailable() {
    setToast("This action requires connected workspace data.");
    window.setTimeout(() => setToast(""), 3000);
  }

  return (
    <DashboardShell activeSection="RosterIQ System">
      <PageHeader
        title="RosterIQ System"
        description="Review the organization workspace and the configuration areas that support roster operations."
      >
        <ActionButton onClick={showUnavailable}>
          <Database aria-hidden="true" className="h-[18px] w-[18px]" />
          Data connections
        </ActionButton>
        <ActionButton variant="primary" onClick={showUnavailable}>
          <Settings2 aria-hidden="true" className="h-[18px] w-[18px]" />
          Configure workspace
        </ActionButton>
      </PageHeader>

      <section
        aria-label="System overview"
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

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-12">
        <Panel
          title="Organization Workspace"
          subtitle="Organization structure and roster configuration."
          className="xl:col-span-8"
          action={<Building2 aria-hidden="true" className="h-5 w-5 text-[#777587]" />}
        >
          <div className="rounded-lg border border-[#e2e7ff] bg-[#f7f8ff]">
            <EmptyState
              title="No workspace data available"
              description="Organization units, teams, and process configuration will appear when workspace data is connected."
            />
          </div>
        </Panel>

        <Panel
          title="System Configuration"
          subtitle="Workspace services and settings."
          className="xl:col-span-4"
          action={
            <button
              type="button"
              onClick={showUnavailable}
              className="flex items-center gap-1 text-[12px] font-semibold text-[#3525cd]"
            >
              Manage
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </button>
          }
        >
          <div className="rounded-lg border border-[#e2e7ff] bg-[#f7f8ff]">
            <EmptyState
              title="No configuration available"
              description="Workspace settings will appear here when system data is connected."
              compact
            />
          </div>
        </Panel>
      </div>
      <Toast message={toast} />
    </DashboardShell>
  );
}
