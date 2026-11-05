"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import {
  ArrowLeftRight,
  BadgeCheck,
  BarChart3,
  Bell,
  Building2,
  CalendarDays,
  CalendarX,
  ChevronRight,
  ChevronsUpDown,
  FileDown,
  LayoutDashboard,
  LayoutGrid,
  Menu,
  MoreVertical,
  Network,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Store,
  TriangleAlert,
  TrendingUp,
  Umbrella,
  UserRound,
  UsersRound,
  Workflow,
  type LucideIcon,
} from "lucide-react";

export type DashboardSection =
  | "Dashboard"
  | "Roster Planner"
  | "Coverage & Conflicts"
  | "Workforce Resilience"
  | "Operational Precision"
  | "RosterIQ System";

const iconMap: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  calendar: CalendarDays,
  alert: TriangleAlert,
  warning: TriangleAlert,
  shield: ShieldCheck,
  people: UsersRound,
  brands: Building2,
  processes: Workflow,
  pods: Network,
  leave: CalendarX,
  import: ArrowLeftRight,
  reports: BarChart3,
  settings: Settings,
  precision: CalendarDays,
  system: LayoutGrid,
  badge: BadgeCheck,
  store: Store,
  trending_up: TrendingUp,
  beach_access: Umbrella,
  security: ShieldCheck,
};

const navGroups: { label: string; links: { label: string; icon: string; href?: string }[] }[] = [
  {
    label: "Workspace",
    links: [
      { label: "Dashboard", icon: "dashboard", href: "/" },
      { label: "Roster Planner", icon: "calendar", href: "/roster-planner" },
      { label: "Coverage & Conflicts", icon: "alert", href: "/coverage-conflicts" },
      { label: "Workforce Resilience", icon: "shield", href: "/workforce-resilience" },
      { label: "Operational Precision", icon: "precision", href: "/operational-precision" },
      { label: "RosterIQ System", icon: "system", href: "/rosteriq-system" },
    ],
  },
  {
    label: "Organization",
    links: [
      { label: "Employees", icon: "people" },
      { label: "Brands", icon: "brands" },
      { label: "Processes", icon: "processes" },
      { label: "Pods & Teams", icon: "pods" },
      { label: "Availability & Leaves", icon: "leave" },
    ],
  },
  {
    label: "Data & Analytics",
    links: [
      { label: "CSV Import & Export", icon: "import" },
      { label: "Reports & Analytics", icon: "reports" },
    ],
  },
  { label: "System", links: [{ label: "Settings", icon: "settings" }] },
];

export function Icon({ name, className = "" }: { name: string; className?: string }) {
  const Component = iconMap[name];
  return Component ? <Component aria-hidden="true" className={`h-5 w-5 shrink-0 ${className}`} focusable="false" /> : null;
}

function Sidebar({
  activeSection,
  isOpen,
  onClose,
}: {
  activeSection: DashboardSection;
  isOpen: boolean;
  onClose: () => void;
}) {
  return (
    <>
      {isOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[248px] flex-col justify-between overflow-y-auto bg-[#131b2e] px-5 py-6 text-white transition-transform duration-200 lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div>
          <Link href="/" className="mb-6 flex items-center gap-3" onClick={onClose}>
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#4f46e5]">
              <LayoutGrid aria-hidden="true" className="h-5 w-5" />
            </span>
            <span>
              <span className="block font-display text-[18px] font-bold tracking-tight">RosterIQ</span>
              <span className="block text-[11px] font-medium text-[#dad7ff]">Workforce Intelligence</span>
            </span>
          </Link>
          <button className="mb-6 flex w-full items-center justify-between rounded-xl bg-[#283044]/80 p-2.5 text-left hover:bg-[#343e56]">
            <span className="flex min-w-0 items-center gap-2.5">
              <span className="h-2 w-2 shrink-0 rounded-full bg-[#b9eaff]" />
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-semibold">Operations Workspace</span>
                <span className="block truncate text-[11px] text-[#c7c9d8]">Roster management</span>
              </span>
            </span>
            <ChevronsUpDown aria-hidden="true" className="h-[18px] w-[18px] text-[#dae2fd]" />
          </button>
          <nav aria-label="Main navigation">
            {navGroups.map((group) => (
              <div key={group.label}>
                <div className="mb-2 mt-4 text-[11px] font-bold uppercase tracking-wider text-[#c3c0ff]">
                  {group.label}
                </div>
                <div className="mb-4 flex flex-col gap-1">
                  {group.links.map((item) => {
                    const active = item.label === activeSection;
                    const content = (
                      <>
                        <Icon name={item.icon} />
                        <span>{item.label}</span>
                      </>
                    );
                    const className = `flex min-h-9 items-center gap-3 rounded-xl px-3 py-2 text-left text-[14px] transition-colors ${
                      active
                        ? "bg-[#4f46e5] font-semibold text-white shadow-sm"
                        : "text-[#dad7ff] hover:bg-[#283044] hover:text-white"
                    }`;
                    return item.href ? (
                      <Link
                        key={item.label}
                        aria-current={active ? "page" : undefined}
                        href={item.href}
                        onClick={onClose}
                        className={className}
                      >
                        {content}
                      </Link>
                    ) : (
                      <button key={item.label} className={className} type="button">
                        {content}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
        </div>
        <button className="mt-5 flex items-center justify-between rounded-xl bg-[#283044]/80 p-3 text-left hover:bg-[#343e56]">
          <span className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#3525cd]">
              <UserRound aria-hidden="true" className="h-[18px] w-[18px]" />
            </span>
            <span>
              <span className="block text-[13px] font-semibold">Workspace User</span>
              <span className="block text-[11px] text-[#c7c9d8]">Operations</span>
            </span>
          </span>
          <MoreVertical aria-hidden="true" className="h-[18px] w-[18px] text-[#dae2fd]" />
        </button>
      </aside>
    </>
  );
}

export function DashboardShell({
  activeSection,
  children,
}: {
  activeSection: DashboardSection;
  children: ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#faf8ff] text-[#131b2e]">
      <Sidebar
        activeSection={activeSection}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <header className="fixed left-0 right-0 top-0 z-30 flex h-16 items-center justify-between gap-4 bg-white/95 px-4 shadow-[0_1px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl lg:left-[248px] lg:px-7">
        <div className="flex min-w-0 items-center gap-2 text-[14px] text-[#464555]">
          <button
            aria-label="Open navigation"
            className="mr-1 rounded-lg p-2 hover:bg-[#f2f3ff] lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu aria-hidden="true" className="h-5 w-5" />
          </button>
          <span className="hidden sm:inline">Operations Hub</span>
          <ChevronRight aria-hidden="true" className="hidden h-4 w-4 sm:inline" />
          <span className="hidden md:inline">RosterIQ</span>
          <ChevronRight aria-hidden="true" className="hidden h-4 w-4 md:inline" />
          <span className="truncate font-semibold text-[#131b2e]">{activeSection}</span>
        </div>
        <div className="flex min-w-0 items-center justify-end gap-2 sm:gap-3">
          <label className="relative hidden w-52 min-w-0 md:block xl:w-64">
            <Search
              aria-hidden="true"
              className="absolute left-3 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-[#777587]"
            />
            <input
              aria-label="Search"
              className="h-10 w-full rounded-xl bg-[#f2f3ff] pl-9 pr-3 text-[13px] text-[#131b2e] placeholder:text-[#777587] focus:bg-white"
              placeholder="Search..."
            />
          </label>
          <button
            aria-label="Notifications"
            className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-[#f2f3ff] text-[#777587] hover:bg-[#e2e7ff]"
          >
            <Bell aria-hidden="true" className="h-5 w-5" />
          </button>
          <button
            className="hidden h-10 items-center gap-2 rounded-xl bg-[#f2f3ff] px-3 text-[13px] font-medium text-[#131b2e] hover:bg-[#e2e7ff] xl:flex"
          >
            <RefreshCw aria-hidden="true" className="h-[18px] w-[18px] text-[#464555]" />
            <span>Revalidate Schedule</span>
          </button>
          <button className="flex h-10 items-center gap-2 rounded-xl bg-[#4f46e5] px-3.5 text-[13px] font-semibold text-white shadow-sm hover:bg-[#3525cd]">
            <Plus aria-hidden="true" className="h-[18px] w-[18px]" />
            <span className="hidden sm:inline">Quick Action</span>
          </button>
        </div>
      </header>
      <main className="min-h-screen pt-16 lg:pl-[248px]">
        <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8 xl:p-10">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <section className="mb-8 flex flex-col justify-between gap-5 xl:flex-row xl:items-center">
      <div>
        <h1 className="font-display text-[26px] font-bold leading-tight tracking-tight sm:text-[28px]">
          {title}
        </h1>
        <p className="mt-2 max-w-3xl text-[13px] leading-relaxed text-[#464555]">{description}</p>
      </div>
      {children && <div className="flex flex-wrap items-center gap-3">{children}</div>}
    </section>
  );
}

export function ActionButton({
  children,
  variant = "secondary",
  onClick,
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "subtle";
  onClick?: () => void;
}) {
  const style =
    variant === "primary"
      ? "bg-[#4f46e5] text-white hover:bg-[#3525cd]"
      : variant === "subtle"
        ? "bg-[#eaedff] text-[#3525cd] hover:bg-[#e2e7ff]"
        : "bg-white text-[#131b2e] shadow-sm hover:bg-[#f2f3ff]";
  return (
    <button
      className={`flex h-10 items-center gap-2 rounded-xl px-4 text-[12px] font-semibold transition-colors ${style}`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

export function EmptyState({
  title = "No data available",
  description,
  compact = false,
}: {
  title?: string;
  description?: string;
  compact?: boolean;
}) {
  return (
    <div className={`flex flex-col items-center justify-center text-center text-[#777587] ${compact ? "min-h-28 p-4" : "min-h-48 p-6"}`}>
      <BarChart3 aria-hidden="true" className="mb-3 h-7 w-7 text-[#777587]/70" />
      <p className="text-[13px] font-semibold text-[#464555]">{title}</p>
      {description && <p className="mt-1 max-w-md text-[12px] leading-relaxed">{description}</p>}
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl bg-white p-5 shadow-sm sm:p-7 ${className}`}>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-[19px] font-semibold tracking-tight">{title}</h2>
          {subtitle && <p className="mt-1 text-[13px] text-[#464555]">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function MetricCard({
  title,
  icon,
  value = "—",
  note = "No data available",
  tone = "default",
}: {
  title: string;
  icon: string;
  value?: string;
  note?: string;
  tone?: "default" | "error" | "teal";
}) {
  const toneClass =
    tone === "error" ? "text-[#93000a]" : tone === "teal" ? "text-[#004f64]" : "text-[#131b2e]";
  return (
    <article className="flex min-h-[148px] flex-col justify-between rounded-xl bg-white p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span
          className={`text-[12px] font-semibold uppercase tracking-wider ${
            tone === "error" ? "text-[#93000a]" : "text-[#464555]"
          }`}
        >
          {title}
        </span>
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
            tone === "error" ? "bg-[#ffdad6] text-[#93000a]" : "bg-[#eaedff] text-[#4f46e5]"
          }`}
        >
          <Icon name={icon} className="h-[18px] w-[18px]" />
        </span>
      </div>
      <div>
        <div className={`font-display text-[26px] font-bold leading-tight tracking-tight sm:text-[30px] ${toneClass}`}>
          {value}
        </div>
        <div className="mt-2 text-[11px] font-medium leading-snug text-[#464555]">{note}</div>
      </div>
    </article>
  );
}

export function FilterSelect({
  label,
  options = [],
}: {
  label: string;
  options?: string[];
}) {
  return (
    <label className="flex h-10 items-center gap-2 rounded-xl bg-[#f2f3ff] px-3 text-[12px] text-[#464555]">
      <span>{label}:</span>
      <select aria-label={label} className="max-w-[200px] bg-transparent font-medium text-[#131b2e] outline-none">
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function FilterSearch({ placeholder }: { placeholder: string }) {
  return (
    <label className="relative block min-w-[210px] flex-1">
      <Search
        aria-hidden="true"
        className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#777587]"
      />
      <input
        aria-label={placeholder}
        className="h-10 w-full rounded-xl bg-[#f2f3ff] pl-9 pr-3 text-[12px] placeholder:text-[#777587]"
        placeholder={placeholder}
      />
    </label>
  );
}

export function EmptyTable({
  columns,
  title = "No data available",
  rows = [],
}: {
  columns: string[];
  title?: string;
  rows?: { key: string; cells: ReactNode[] }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-left">
        <thead className="bg-[#f7f8ff]">
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                scope="col"
                className="border-b border-[#e2e7ff] px-3 py-3 text-[11px] font-semibold uppercase tracking-wider text-[#464555]"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.key} className="hover:bg-[#f7f8ff]">
                {row.cells.map((cell, index) => (
                  <td key={`${row.key}-${index}`} className="border-b border-[#eaedff] px-3 py-3 text-[12px] text-[#131b2e]">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length} className="border-b border-[#eaedff]">
                <EmptyState title={title} compact />
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Toast({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-5 left-1/2 z-[60] max-w-[calc(100%-2rem)] -translate-x-1/2 rounded-xl bg-[#131b2e] px-4 py-3 text-center text-[13px] text-white shadow-xl"
    >
      {message}
    </div>
  );
}

export const DashboardIcons = {
  Bell,
  FileDown,
  RefreshCw,
};
