"use client";

import { DashboardShell, EmptyState, MetricCard, Panel, PageHeader } from "@/components/dashboard-ui";
import { displayName, useRosterData } from "@/lib/use-roster-data";

export default function WorkforceData() {
  const data = useRosterData();

  return (
    <DashboardShell activeSection="Workforce Data">
      <PageHeader
        title="Workforce Data"
        description="The employees, brands, processes, and pods used for roster planning."
      />
      {data.error && (
        <p role="alert" className="mb-5 rounded-xl bg-[#ffdad6] px-4 py-3 text-sm text-[#93000a]">
          {data.error}
        </p>
      )}
      <section aria-label="Workforce totals" className="mb-6 grid grid-cols-2 gap-4 xl:grid-cols-4">
        <MetricCard title="Employees" icon="people" value={String(data.employees.length)} note="Available for roster planning" />
        <MetricCard title="Brands" icon="brands" value={String(data.brands.length)} note="In the default dataset" tone="teal" />
        <MetricCard title="Processes" icon="processes" value={String(data.processes.length)} note="Across available brands" />
        <MetricCard title="Pods" icon="pods" value={String(data.pods.length)} note="Across available processes" />
      </section>
      <div className="variable-card-grid">
        <Panel scroll height="clamp(360px, 45vh, 460px)" ariaLabel="Employees list" title="Employees" subtitle="Current workforce and primary pod assignments.">
          {data.employees.length ? (
            <div className="min-w-max space-y-2">
              {data.employees.map((employee) => {
                const membership = data.employeePods.find((item) => item.employee_id === employee.id && item.is_primary)
                  || data.employeePods.find((item) => item.employee_id === employee.id);
                const pod = data.pods.find((item) => item.id === membership?.pod_id);
                return (
                  <div key={employee.id} className="flex min-w-max items-center justify-between gap-4 whitespace-nowrap rounded-xl bg-[#f7f8ff] p-3">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-semibold">{displayName(employee)}</p>
                      <p className="mt-1 truncate text-[11px] text-[#777587]">
                        {employee.employee_code} · {employee.designation || "Employee"}
                      </p>
                    </div>
                    <p className="shrink-0 text-right text-[11px] text-[#464555]">
                      {pod?.name || "Unassigned"}
                    </p>
                  </div>
                );
              })}
            </div>
          ) : <EmptyState title="No employees available" compact />}
        </Panel>
        <Panel scroll height="clamp(360px, 45vh, 460px)" ariaLabel="Brands list" title="Brands" subtitle="Brands in the roster dataset.">
          {data.brands.length ? (
            <div className="min-w-max space-y-2">
              {data.brands.map((brand) => (
                <div key={brand.id} className="flex min-w-max items-center justify-between whitespace-nowrap rounded-xl bg-[#f7f8ff] p-3">
                  <p className="text-[13px] font-semibold">{brand.name}</p>
                  <p className="text-[11px] text-[#777587]">{brand.industry || "Brand"}</p>
                </div>
              ))}
            </div>
          ) : <EmptyState title="No brands available" compact />}
        </Panel>
        <Panel scroll height="clamp(360px, 45vh, 460px)" ariaLabel="Processes list" title="Processes" subtitle="Operational processes grouped by brand.">
          {data.processes.length ? (
            <div className="min-w-max space-y-2">
              {data.processes.map((process) => {
                const brand = data.brands.find((item) => item.id === process.brand_id);
                return (
                  <div key={process.id} className="flex min-w-max items-center justify-between whitespace-nowrap rounded-xl bg-[#f7f8ff] p-3">
                    <p className="text-[13px] font-semibold">{process.name}</p>
                    <p className="text-[11px] text-[#777587]">{brand?.name || "Brand"}</p>
                  </div>
                );
              })}
            </div>
          ) : <EmptyState title="No processes available" compact />}
        </Panel>
        <Panel scroll height="clamp(360px, 45vh, 460px)" ariaLabel="Pods list" title="Pods" subtitle="Teams and their process ownership.">
          {data.pods.length ? (
            <div className="min-w-max space-y-2">
              {data.pods.map((pod) => {
                const process = data.processes.find((item) => item.id === pod.process_id);
                return (
                  <div key={pod.id} className="flex min-w-max items-center justify-between whitespace-nowrap rounded-xl bg-[#f7f8ff] p-3">
                    <p className="text-[13px] font-semibold">{pod.name}</p>
                    <p className="text-[11px] text-[#777587]">{process?.name || "Process"}</p>
                  </div>
                );
              })}
            </div>
          ) : <EmptyState title="No pods available" compact />}
        </Panel>
      </div>
    </DashboardShell>
  );
}
