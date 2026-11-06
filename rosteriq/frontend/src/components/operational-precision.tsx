"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Pencil, RefreshCw, Save, Trash2, X } from "lucide-react";
import {
  ActionButton,
  DashboardShell,
  EmptyState,
  Panel,
  PageHeader,
  Toast,
} from "@/components/dashboard-ui";
import { api, apiErrorMessage } from "@/lib/api";
import { displayName, useRosterData } from "@/lib/use-roster-data";

type Tab = "rules" | "coverage" | "holidays" | "employee";
type CoverageRequirement = {
  id: string;
  process_id: string;
  shift_id: string | null;
  target_date: string | null;
  day_of_week: number | null;
  minimum_staff: number;
};
type PublicHoliday = { holiday_date: string; name: string };
type WeeklyOff = { day_of_week: number };
type TimeOff = {
  id: string;
  start_date: string;
  end_date: string;
  kind: "leave" | "comp_off" | "unavailability";
  status: "planned" | "approved" | "pending" | "rejected" | "active";
  reason: string | null;
};
type EmployeePreference = {
  id: string;
  process_id: string | null;
  preferred_shift_id: string | null;
  preferred_days_of_week: number[];
  avoid_days_of_week: number[];
};
type OperatingOverride = {
  operating_date: string;
  is_operating: boolean;
};
type OperatingRule = {
  operating_days: number[];
  operates_on_public_holidays: boolean;
};
type CoverageForm = {
  process_id: string;
  shift_id: string;
  target_date: string;
  day_of_week: string;
  minimum_staff: string;
};
type TimeOffForm = {
  start_date: string;
  end_date: string;
  kind: TimeOff["kind"];
  status: TimeOff["status"];
  reason: string;
};
type PreferenceForm = {
  process_id: string;
  preferred_shift_id: string;
  preferred_days_of_week: number[];
  avoid_days_of_week: number[];
};

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const inputClass = "mt-1 block h-10 rounded-xl bg-[#f2f3ff] px-3 text-[12px]";
const panelClass = "rounded-xl bg-[#f7f8ff] p-4";
const emptyCoverageForm: CoverageForm = {
  process_id: "",
  shift_id: "",
  target_date: "",
  day_of_week: "",
  minimum_staff: "1",
};
const emptyTimeOffForm: TimeOffForm = {
  start_date: "",
  end_date: "",
  kind: "leave",
  status: "planned",
  reason: "",
};
const emptyPreferenceForm: PreferenceForm = {
  process_id: "",
  preferred_shift_id: "",
  preferred_days_of_week: [],
  avoid_days_of_week: [],
};

export default function OperationalPrecision() {
  const data = useRosterData();
  const [tab, setTab] = useState<Tab>("rules");
  const [selectedEmployee, setSelectedEmployee] = useState("");
  const [coverage, setCoverage] = useState<CoverageRequirement[]>([]);
  const [holidays, setHolidays] = useState<PublicHoliday[]>([]);
  const [weeklyOffs, setWeeklyOffs] = useState<WeeklyOff[]>([]);
  const [timeOffRows, setTimeOffRows] = useState<TimeOff[]>([]);
  const [preferences, setPreferences] = useState<EmployeePreference[]>([]);
  const [coverageForm, setCoverageForm] = useState(emptyCoverageForm);
  const [editingCoverage, setEditingCoverage] = useState<string | null>(null);
  const [holidayForm, setHolidayForm] = useState({ holiday_date: "", name: "" });
  const [editingHolidayDate, setEditingHolidayDate] = useState<string | null>(null);
  const [weeklyDay, setWeeklyDay] = useState("6");
  const [editingWeeklyDay, setEditingWeeklyDay] = useState<number | null>(null);
  const [timeOffForm, setTimeOffForm] = useState(emptyTimeOffForm);
  const [editingTimeOff, setEditingTimeOff] = useState<string | null>(null);
  const [preferenceForm, setPreferenceForm] = useState(emptyPreferenceForm);
  const [editingPreference, setEditingPreference] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const reportError = useCallback((reason: unknown) => {
    setError(apiErrorMessage(reason));
  }, []);
  const reportToast = useCallback((message: string) => {
    setToast(message);
  }, []);

  const loadBase = useCallback(async () => {
    if (!data.organization) return;
    try {
      const [nextCoverage, nextHolidays] = await Promise.all([
        api.get<CoverageRequirement[]>("/scheduling/coverage-requirements"),
        api.get<PublicHoliday[]>(
          `/scheduling/organizations/${data.organization.id}/public-holidays`,
        ),
      ]);
      setCoverage(nextCoverage);
      setHolidays(nextHolidays);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  }, [data.organization]);

  const loadEmployee = useCallback(async (employeeId: string) => {
    setSelectedEmployee(employeeId);
    if (!employeeId) {
      setWeeklyOffs([]);
      setTimeOffRows([]);
      setPreferences([]);
      return;
    }
    try {
      const [nextWeeklyOffs, nextTimeOff, nextPreferences] = await Promise.all([
        api.get<WeeklyOff[]>(`/scheduling/employees/${employeeId}/weekly-offs`),
        api.get<TimeOff[]>(`/scheduling/employees/${employeeId}/time-off`),
        api.get<EmployeePreference[]>(`/scheduling/employees/${employeeId}/preferences`),
      ]);
      setWeeklyOffs(nextWeeklyOffs);
      setTimeOffRows(nextTimeOff);
      setPreferences(nextPreferences);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  }, []);

  useEffect(() => {
    if (!data.organization) return;
    const timer = window.setTimeout(() => void loadBase(), 0);
    return () => window.clearTimeout(timer);
  }, [data.organization, loadBase]);

  const refresh = () => {
    void loadBase();
    if (selectedEmployee) void loadEmployee(selectedEmployee);
  };

  const saveCoverage = async () => {
    if (!coverageForm.process_id) return;
    const payload = {
      process_id: coverageForm.process_id,
      shift_id: coverageForm.shift_id || null,
      target_date: coverageForm.target_date || null,
      day_of_week: coverageForm.target_date || coverageForm.day_of_week === ""
        ? null
        : Number(coverageForm.day_of_week),
      minimum_staff: Number(coverageForm.minimum_staff),
    };
    try {
      if (editingCoverage) {
        await api.put(`/scheduling/coverage-requirements/${editingCoverage}`, payload);
      } else {
        await api.post("/scheduling/coverage-requirements", payload);
      }
      setCoverageForm(emptyCoverageForm);
      setEditingCoverage(null);
      setToast(editingCoverage ? "Coverage requirement updated." : "Coverage requirement added.");
      await loadBase();
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  };

  const editCoverage = (row: CoverageRequirement) => {
    setCoverageForm({
      process_id: row.process_id,
      shift_id: row.shift_id || "",
      target_date: row.target_date || "",
      day_of_week: row.day_of_week == null ? "" : String(row.day_of_week),
      minimum_staff: String(row.minimum_staff),
    });
    setEditingCoverage(row.id);
  };

  const saveHoliday = async () => {
    if (!data.organization || !holidayForm.holiday_date || !holidayForm.name.trim()) return;
    const path = `/scheduling/organizations/${data.organization.id}/public-holidays`;
    try {
      if (editingHolidayDate) {
        await api.put(`${path}/${editingHolidayDate}`, {
          holiday_date: holidayForm.holiday_date,
          name: holidayForm.name.trim(),
        });
      } else {
        await api.post(path, {
          holiday_date: holidayForm.holiday_date,
          name: holidayForm.name.trim(),
        });
      }
      setHolidayForm({ holiday_date: "", name: "" });
      setEditingHolidayDate(null);
      setToast(editingHolidayDate ? "Public holiday updated." : "Public holiday added.");
      await loadBase();
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  };

  const saveWeeklyOff = async () => {
    if (!selectedEmployee) return;
    try {
      if (editingWeeklyDay !== null) {
        await api.put(
          `/scheduling/employees/${selectedEmployee}/weekly-offs/${editingWeeklyDay}`,
          { day_of_week: Number(weeklyDay) },
        );
        setEditingWeeklyDay(null);
        setToast("Weekly off updated.");
      } else {
        await api.post(`/scheduling/employees/${selectedEmployee}/weekly-offs`, {
          day_of_week: Number(weeklyDay),
        });
        setToast("Weekly off added.");
      }
      await loadEmployee(selectedEmployee);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  };

  const saveTimeOff = async () => {
    if (!selectedEmployee) return;
    const path = `/scheduling/employees/${selectedEmployee}/time-off`;
    const payload = {
      ...timeOffForm,
      reason: timeOffForm.reason.trim() || null,
    };
    try {
      if (editingTimeOff) {
        await api.put(`${path}/${editingTimeOff}`, payload);
      } else {
        await api.post(path, payload);
      }
      setTimeOffForm(emptyTimeOffForm);
      setEditingTimeOff(null);
      setToast(editingTimeOff ? "Time-off record updated." : "Time-off record added.");
      await loadEmployee(selectedEmployee);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  };

  const savePreference = async () => {
    if (!selectedEmployee) return;
    const path = `/scheduling/employees/${selectedEmployee}/preferences`;
    const payload = {
      process_id: preferenceForm.process_id || null,
      preferred_shift_id: preferenceForm.preferred_shift_id || null,
      preferred_days_of_week: preferenceForm.preferred_days_of_week,
      avoid_days_of_week: preferenceForm.avoid_days_of_week,
    };
    try {
      if (editingPreference) {
        await api.put(`${path}/${editingPreference}`, payload);
      } else {
        await api.post(path, payload);
      }
      setPreferenceForm(emptyPreferenceForm);
      setEditingPreference(null);
      setToast(editingPreference ? "Employee preference updated." : "Employee preference added.");
      await loadEmployee(selectedEmployee);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  };

  const remove = async (path: string, refreshEmployee = false) => {
    try {
      await api.delete(path);
      setToast("Record deleted.");
      if (refreshEmployee && selectedEmployee) await loadEmployee(selectedEmployee);
      else await loadBase();
    } catch (reason) {
      setError(apiErrorMessage(reason));
    }
  };

  return (
    <DashboardShell activeSection="Operational Precision">
      <PageHeader
        title="Operational Precision"
        description="Manage the existing scheduling configuration used by the deterministic engine."
      >
        <ActionButton onClick={refresh}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </ActionButton>
      </PageHeader>
      {(data.error || error) && (
        <p role="alert" className="mb-5 rounded-xl bg-[#ffdad6] px-4 py-3 text-sm text-[#93000a]">
          {error || data.error}
        </p>
      )}
      <div className="mb-5 flex flex-wrap gap-2 rounded-xl bg-white p-2 shadow-sm">
        {([
          ["rules", "Operating rules"],
          ["coverage", "Coverage requirements"],
          ["holidays", "Public holidays"],
          ["employee", "Employee calendars"],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-lg px-3 py-2 text-[12px] font-semibold ${
              tab === id ? "bg-[#4f46e5] text-white" : "bg-[#f2f3ff] text-[#464555]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "rules" && (
        <Panel scroll height="clamp(520px, 70vh, 780px)" className="operational-scroll-card" ariaLabel="Operating rules list"
          title="Process operating calendars"
          subtitle="Set recurring operating weekdays, holiday behavior, and date-specific overrides."
        >
          <div className="space-y-3">
            {data.processes.map((process) => (
              <RuleRow
                key={process.id}
                processId={process.id}
                name={`${data.brands.find((brand) => brand.id === process.brand_id)?.name || "Brand"} / ${process.name}`}
                onError={reportError}
                onSaved={reportToast}
              />
            ))}
          </div>
        </Panel>
      )}

      {tab === "coverage" && (
        <Panel scroll height="clamp(520px, 70vh, 780px)" className="operational-scroll-card" ariaLabel="Coverage requirements table"
          title="Coverage requirements"
          subtitle="Minimum staffing rules are consumed by generation and validation."
        >
          <div className="mb-5 flex flex-wrap items-end gap-3">
            <label className="text-[11px] font-semibold">
              Process
              <select
                value={coverageForm.process_id}
                onChange={(event) => setCoverageForm({
                  ...coverageForm,
                  process_id: event.target.value,
                  shift_id: "",
                })}
                className={`${inputClass} min-w-48`}
              >
                <option value="">Choose process</option>
                {data.processes.map((process) => (
                  <option key={process.id} value={process.id}>
                    {data.brands.find((brand) => brand.id === process.brand_id)?.name} / {process.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-[11px] font-semibold">
              Shift (optional)
              <select
                value={coverageForm.shift_id}
                onChange={(event) => setCoverageForm({ ...coverageForm, shift_id: event.target.value })}
                className={`${inputClass} min-w-44`}
              >
                <option value="">All shifts</option>
                {shiftsForProcess(data, coverageForm.process_id).map((shift) => (
                  <option key={shift.id} value={shift.id}>{shift.shift_name}</option>
                ))}
              </select>
            </label>
            <label className="text-[11px] font-semibold">
              Minimum staff
              <input
                type="number"
                min="0"
                value={coverageForm.minimum_staff}
                onChange={(event) => setCoverageForm({ ...coverageForm, minimum_staff: event.target.value })}
                className={`${inputClass} w-28`}
              />
            </label>
            <label className="text-[11px] font-semibold">
              Specific date
              <input
                type="date"
                value={coverageForm.target_date}
                onChange={(event) => setCoverageForm({
                  ...coverageForm,
                  target_date: event.target.value,
                  day_of_week: "",
                })}
                className={inputClass}
              />
            </label>
            <label className="text-[11px] font-semibold">
              Or weekday
              <select
                value={coverageForm.day_of_week}
                onChange={(event) => setCoverageForm({
                  ...coverageForm,
                  day_of_week: event.target.value,
                  target_date: "",
                })}
                className={inputClass}
              >
                <option value="">Every applicable day</option>
                {weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
              </select>
            </label>
            <ActionButton variant="primary" onClick={() => void saveCoverage()}>
              <Save className="h-4 w-4" />
              {editingCoverage ? "Update requirement" : "Add requirement"}
            </ActionButton>
            {editingCoverage && (
              <ActionButton onClick={() => { setEditingCoverage(null); setCoverageForm(emptyCoverageForm); }}>
                <X className="h-4 w-4" /> Cancel
              </ActionButton>
            )}
          </div>
          <RecordTable
            rows={coverage}
            columns={["Process", "Shift", "Minimum", "Applies", "Actions"]}
            getKey={(row) => row.id}
            render={(row) => (
              <>
                <td className="px-3 py-2">{processName(row.process_id, data)}</td>
                <td className="px-3 py-2">{shiftName(row.shift_id, data)}</td>
                <td className="px-3 py-2">{row.minimum_staff}</td>
                <td className="px-3 py-2">
                  {row.target_date || (row.day_of_week == null ? "All applicable days" : weekdays[row.day_of_week])}
                </td>
                <td className="px-3 py-2">
                  <RowActions
                    onEdit={() => editCoverage(row)}
                    onDelete={() => void remove(`/scheduling/coverage-requirements/${row.id}`)}
                  />
                </td>
              </>
            )}
          />
        </Panel>
      )}

      {tab === "holidays" && (
        <Panel scroll height="clamp(520px, 70vh, 780px)" className="operational-scroll-card" ariaLabel="Public holidays table"
          title="Public holidays"
          subtitle={`Company workspace: ${data.organization?.name || "Not available"}`}
        >
          <div className="mb-5 flex flex-wrap items-end gap-3">
            <label className="text-[11px] font-semibold">
              Date
              <input
                type="date"
                value={holidayForm.holiday_date}
                onChange={(event) => setHolidayForm({ ...holidayForm, holiday_date: event.target.value })}
                className={inputClass}
              />
            </label>
            <label className="min-w-[220px] text-[11px] font-semibold">
              Holiday name
              <input
                value={holidayForm.name}
                onChange={(event) => setHolidayForm({ ...holidayForm, name: event.target.value })}
                className={`${inputClass} w-full`}
              />
            </label>
            <ActionButton variant="primary" onClick={() => void saveHoliday()}>
              <Save className="h-4 w-4" />
              {editingHolidayDate ? "Update holiday" : "Add holiday"}
            </ActionButton>
            {editingHolidayDate && (
              <ActionButton onClick={() => { setEditingHolidayDate(null); setHolidayForm({ holiday_date: "", name: "" }); }}>
                <X className="h-4 w-4" /> Cancel
              </ActionButton>
            )}
          </div>
          <RecordTable
            rows={holidays}
            columns={["Date", "Name", "Actions"]}
            getKey={(row) => row.holiday_date}
            render={(row) => (
              <>
                <td className="px-3 py-2">{row.holiday_date}</td>
                <td className="px-3 py-2">{row.name}</td>
                <td className="px-3 py-2">
                  <RowActions
                    onEdit={() => {
                      setHolidayForm({ holiday_date: row.holiday_date, name: row.name });
                      setEditingHolidayDate(row.holiday_date);
                    }}
                    onDelete={() => void remove(
                      `/scheduling/organizations/${data.organization?.id}/public-holidays/${row.holiday_date}`,
                    )}
                  />
                </td>
              </>
            )}
          />
        </Panel>
      )}

      {tab === "employee" && (
        <Panel scroll height="clamp(520px, 70vh, 780px)" className="operational-scroll-card" ariaLabel="Employee calendar and preference tables"
          title="Employee calendars and preferences"
          subtitle="Edit weekly offs, leave and comp-off records, and preferred working days."
        >
          <label className="mb-5 block max-w-md text-[11px] font-semibold">
            Employee
            <select
              value={selectedEmployee}
              onChange={(event) => void loadEmployee(event.target.value)}
              className={`${inputClass} w-full`}
            >
              <option value="">Choose employee</option>
              {data.employees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {displayName(employee)} · {employee.employee_code}
                </option>
              ))}
            </select>
          </label>
          {selectedEmployee ? (
            <div className="grid gap-5 xl:grid-cols-3">
              <section className={panelClass}>
                <h3 className="mb-3 text-[13px] font-semibold">Weekly offs</h3>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={weeklyDay}
                    onChange={(event) => setWeeklyDay(event.target.value)}
                    className={`${inputClass} mt-0 bg-white`}
                  >
                    {weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
                  </select>
                  <ActionButton variant="primary" onClick={() => void saveWeeklyOff()}>
                    <Save className="h-4 w-4" /> {editingWeeklyDay === null ? "Add" : "Update"}
                  </ActionButton>
                  {editingWeeklyDay !== null && (
                    <ActionButton onClick={() => setEditingWeeklyDay(null)}>
                      <X className="h-4 w-4" /> Cancel
                    </ActionButton>
                  )}
                </div>
                <RecordTable
                  rows={weeklyOffs}
                  columns={["Day", "Actions"]}
                  render={(row) => (
                    <>
                      <td className="px-2 py-2">{weekdays[row.day_of_week]}</td>
                      <td className="px-2 py-2">
                        <RowActions
                          onEdit={() => { setWeeklyDay(String(row.day_of_week)); setEditingWeeklyDay(row.day_of_week); }}
                          onDelete={() => void remove(
                            `/scheduling/employees/${selectedEmployee}/weekly-offs/${row.day_of_week}`,
                            true,
                          )}
                        />
                      </td>
                    </>
                  )}
                />
              </section>

              <section className={panelClass}>
                <h3 className="mb-3 text-[13px] font-semibold">Time off</h3>
                <div className="grid gap-2">
                  <label className="text-[11px] font-semibold">
                    Start date
                    <input
                      type="date"
                      value={timeOffForm.start_date}
                      onChange={(event) => setTimeOffForm({ ...timeOffForm, start_date: event.target.value })}
                      className={`${inputClass} w-full`}
                    />
                  </label>
                  <label className="text-[11px] font-semibold">
                    End date
                    <input
                      type="date"
                      value={timeOffForm.end_date}
                      onChange={(event) => setTimeOffForm({ ...timeOffForm, end_date: event.target.value })}
                      className={`${inputClass} w-full`}
                    />
                  </label>
                  <label className="text-[11px] font-semibold">
                    Type
                    <select
                      value={timeOffForm.kind}
                      onChange={(event) => setTimeOffForm({
                        ...timeOffForm,
                        kind: event.target.value as TimeOffForm["kind"],
                      })}
                      className={`${inputClass} w-full`}
                    >
                      <option value="leave">Leave</option>
                      <option value="comp_off">Comp-off</option>
                      <option value="unavailability">Unavailability</option>
                    </select>
                  </label>
                  <label className="text-[11px] font-semibold">
                    Status
                    <select
                      value={timeOffForm.status}
                      onChange={(event) => setTimeOffForm({
                        ...timeOffForm,
                        status: event.target.value as TimeOffForm["status"],
                      })}
                      className={`${inputClass} w-full`}
                    >
                      {["planned", "approved", "pending", "rejected", "active"].map((status) => (
                        <option key={status} value={status}>{status}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-[11px] font-semibold">
                    Reason
                    <input
                      value={timeOffForm.reason}
                      onChange={(event) => setTimeOffForm({ ...timeOffForm, reason: event.target.value })}
                      className={`${inputClass} w-full`}
                    />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <ActionButton variant="primary" onClick={() => void saveTimeOff()}>
                      <Save className="h-4 w-4" /> {editingTimeOff ? "Update" : "Add time off"}
                    </ActionButton>
                    {editingTimeOff && (
                      <ActionButton onClick={() => { setEditingTimeOff(null); setTimeOffForm(emptyTimeOffForm); }}>
                        <X className="h-4 w-4" /> Cancel
                      </ActionButton>
                    )}
                  </div>
                </div>
                <RecordTable
                  rows={timeOffRows}
                  columns={["Dates", "Type / status", "Actions"]}
                  getKey={(row) => row.id}
                  render={(row) => (
                    <>
                      <td className="px-2 py-2">{row.start_date} – {row.end_date}</td>
                      <td className="px-2 py-2">{row.kind} / {row.status}</td>
                      <td className="px-2 py-2">
                        <RowActions
                          onEdit={() => {
                            setTimeOffForm({
                              start_date: row.start_date,
                              end_date: row.end_date,
                              kind: row.kind,
                              status: row.status,
                              reason: row.reason || "",
                            });
                            setEditingTimeOff(row.id);
                          }}
                          onDelete={() => void remove(
                            `/scheduling/employees/${selectedEmployee}/time-off/${row.id}`,
                            true,
                          )}
                        />
                      </td>
                    </>
                  )}
                />
              </section>

              <section className={panelClass}>
                <h3 className="mb-3 text-[13px] font-semibold">Employee preferences</h3>
                <div className="grid gap-2">
                  <label className="text-[11px] font-semibold">
                    Process (optional)
                    <select
                      value={preferenceForm.process_id}
                      onChange={(event) => setPreferenceForm({
                        ...preferenceForm,
                        process_id: event.target.value,
                        preferred_shift_id: "",
                      })}
                      className={`${inputClass} w-full`}
                    >
                      <option value="">Any process</option>
                      {data.processes.map((process) => (
                        <option key={process.id} value={process.id}>{processName(process.id, data)}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-[11px] font-semibold">
                    Preferred shift (optional)
                    <select
                      value={preferenceForm.preferred_shift_id}
                      onChange={(event) => setPreferenceForm({
                        ...preferenceForm,
                        preferred_shift_id: event.target.value,
                      })}
                      className={`${inputClass} w-full`}
                    >
                      <option value="">Any shift</option>
                      {shiftsForProcess(data, preferenceForm.process_id).map((shift) => (
                        <option key={shift.id} value={shift.id}>{shift.shift_name}</option>
                      ))}
                    </select>
                  </label>
                  <DaySelector
                    label="Preferred days"
                    days={preferenceForm.preferred_days_of_week}
                    onChange={(next) => setPreferenceForm({ ...preferenceForm, preferred_days_of_week: next })}
                  />
                  <DaySelector
                    label="Avoid days"
                    days={preferenceForm.avoid_days_of_week}
                    onChange={(next) => setPreferenceForm({ ...preferenceForm, avoid_days_of_week: next })}
                  />
                  <div className="flex flex-wrap gap-2">
                    <ActionButton variant="primary" onClick={() => void savePreference()}>
                      <Save className="h-4 w-4" /> {editingPreference ? "Update" : "Add preference"}
                    </ActionButton>
                    {editingPreference && (
                      <ActionButton onClick={() => {
                        setEditingPreference(null);
                        setPreferenceForm(emptyPreferenceForm);
                      }}>
                        <X className="h-4 w-4" /> Cancel
                      </ActionButton>
                    )}
                  </div>
                </div>
                <RecordTable
                  rows={preferences}
                  columns={["Process / shift", "Preferred", "Avoid", "Actions"]}
                  getKey={(row) => row.id}
                  render={(row) => (
                    <>
                      <td className="px-2 py-2">
                        {row.process_id ? processName(row.process_id, data) : "Any process"}
                        {row.preferred_shift_id && <div>{shiftName(row.preferred_shift_id, data)}</div>}
                      </td>
                      <td className="px-2 py-2">{weekdayNames(row.preferred_days_of_week)}</td>
                      <td className="px-2 py-2">{weekdayNames(row.avoid_days_of_week)}</td>
                      <td className="px-2 py-2">
                        <RowActions
                          onEdit={() => {
                            setPreferenceForm({
                              process_id: row.process_id || "",
                              preferred_shift_id: row.preferred_shift_id || "",
                              preferred_days_of_week: row.preferred_days_of_week || [],
                              avoid_days_of_week: row.avoid_days_of_week || [],
                            });
                            setEditingPreference(row.id);
                          }}
                          onDelete={() => void remove(
                            `/scheduling/employees/${selectedEmployee}/preferences/${row.id}`,
                            true,
                          )}
                        />
                      </td>
                    </>
                  )}
                />
              </section>
            </div>
          ) : (
            <EmptyState title="Choose an employee to edit their calendar" compact />
          )}
        </Panel>
      )}
      <Toast message={toast} />
    </DashboardShell>
  );
}

function RuleRow({
  processId,
  name,
  onError,
  onSaved,
}: {
  processId: string;
  name: string;
  onError: (reason: unknown) => void;
  onSaved: (message: string) => void;
}) {
  const [days, setDays] = useState<number[]>(weekdays.map((_, index) => index));
  const [holiday, setHoliday] = useState(false);
  const [ruleExists, setRuleExists] = useState(false);
  const [overrides, setOverrides] = useState<OperatingOverride[]>([]);
  const [overrideDate, setOverrideDate] = useState("");
  const [overrideOperating, setOverrideOperating] = useState(true);
  const [editingOverride, setEditingOverride] = useState<OperatingOverride | null>(null);

  const load = useCallback(async () => {
    const [rules, nextOverrides] = await Promise.all([
      api.get<OperatingRule[]>(`/scheduling/processes/${processId}/operating-rules`),
      api.get<OperatingOverride[]>(`/scheduling/processes/${processId}/operating-overrides`),
    ]);
    setRuleExists(rules.length > 0);
    setDays(rules[0]?.operating_days || weekdays.map((_, index) => index));
    setHoliday(Boolean(rules[0]?.operates_on_public_holidays));
    setOverrides(nextOverrides);
  }, [processId]);

  useEffect(() => {
    let active = true;
    void Promise.all([
      api.get<OperatingRule[]>(`/scheduling/processes/${processId}/operating-rules`),
      api.get<OperatingOverride[]>(`/scheduling/processes/${processId}/operating-overrides`),
    ]).then(([rules, nextOverrides]) => {
      if (!active) return;
      setRuleExists(rules.length > 0);
      setDays(rules[0]?.operating_days || weekdays.map((_, index) => index));
      setHoliday(Boolean(rules[0]?.operates_on_public_holidays));
      setOverrides(nextOverrides);
    }).catch((reason: unknown) => {
      if (active) onError(reason);
    });
    return () => { active = false; };
  }, [processId, onError]);

  const saveRule = async () => {
    try {
      const payload = {
        process_id: processId,
        operating_days: days,
        operates_on_public_holidays: holiday,
      };
      if (ruleExists) {
        await api.put(`/scheduling/operating-rules/${processId}`, payload);
      } else {
        await api.post("/scheduling/operating-rules", payload);
      }
      setRuleExists(true);
      onSaved("Operating rule saved.");
      await load();
    } catch (reason) {
      onError(reason);
    }
  };

  const deleteRule = async () => {
    try {
      await api.delete(`/scheduling/operating-rules/${processId}`);
      setRuleExists(false);
      setDays(weekdays.map((_, index) => index));
      setHoliday(false);
      onSaved("Operating rule removed; the default calendar is active.");
    } catch (reason) {
      onError(reason);
    }
  };

  const saveOverride = async () => {
    try {
      if (editingOverride) {
        await api.put(
          `/scheduling/processes/${processId}/operating-overrides/${editingOverride.operating_date}`,
          {
            operating_date: overrideDate,
            is_operating: overrideOperating,
          },
        );
        setEditingOverride(null);
        onSaved("Date-specific operating override updated.");
      } else {
        await api.post("/scheduling/operating-overrides", {
          process_id: processId,
          operating_date: overrideDate,
          is_operating: overrideOperating,
        });
        onSaved("Date-specific operating override added.");
      }
      setOverrideDate("");
      await load();
    } catch (reason) {
      onError(reason);
    }
  };

  const deleteOverride = async (day: string) => {
    try {
      await api.delete(`/scheduling/processes/${processId}/operating-overrides/${day}`);
      if (editingOverride?.operating_date === day) setEditingOverride(null);
      onSaved("Date-specific operating override deleted.");
      await load();
    } catch (reason) {
      onError(reason);
    }
  };

  return (
    <div className="rounded-xl bg-[#f7f8ff] p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[13px] font-semibold">{name}</p>
          <div className="mt-2 flex flex-wrap gap-1">
            {weekdays.map((day, index) => (
              <button
                key={day}
                type="button"
                aria-pressed={days.includes(index)}
                onClick={() => setDays(
                  days.includes(index)
                    ? days.filter((value) => value !== index)
                    : [...days, index].sort(),
                )}
                className={`rounded-lg px-2 py-1 text-[10px] ${
                  days.includes(index) ? "bg-[#4f46e5] text-white" : "bg-white text-[#464555]"
                }`}
              >
                {day.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 text-[11px]">
          <input
            type="checkbox"
            checked={holiday}
            onChange={(event) => setHoliday(event.target.checked)}
          />
          Operates on public holidays
        </label>
        <div className="flex gap-2">
          <ActionButton variant="primary" onClick={() => void saveRule()}>
            <Save className="h-4 w-4" /> Save rule
          </ActionButton>
          {ruleExists && (
            <ActionButton onClick={() => void deleteRule()}>
              <Trash2 className="h-4 w-4 text-[#93000a]" /> Reset
            </ActionButton>
          )}
        </div>
      </div>
      <div className="mt-4 border-t border-[#e2e7ff] pt-3">
        <p className="mb-2 text-[11px] font-semibold">Date-specific overrides</p>
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-[10px] font-semibold">
            Date
            <input
              type="date"
              value={overrideDate}
              onChange={(event) => setOverrideDate(event.target.value)}
              className={`${inputClass} bg-white`}
            />
          </label>
          <label className="text-[10px] font-semibold">
            Operating status
            <select
              value={String(overrideOperating)}
              onChange={(event) => setOverrideOperating(event.target.value === "true")}
              className={`${inputClass} bg-white`}
            >
              <option value="true">Operating</option>
              <option value="false">Not operating</option>
            </select>
          </label>
          <ActionButton variant="subtle" onClick={() => void saveOverride()}>
            <Save className="h-4 w-4" /> {editingOverride ? "Update override" : "Add override"}
          </ActionButton>
          {editingOverride && (
            <ActionButton onClick={() => {
              setEditingOverride(null);
              setOverrideDate("");
            }}>
              <X className="h-4 w-4" /> Cancel
            </ActionButton>
          )}
        </div>
        <RecordTable
          rows={overrides}
          columns={["Date", "Status", "Actions"]}
          getKey={(row) => row.operating_date}
          render={(row) => (
            <>
              <td className="px-2 py-2">{row.operating_date}</td>
              <td className="px-2 py-2">{row.is_operating ? "Operating" : "Not operating"}</td>
              <td className="px-2 py-2">
                <RowActions
                  onEdit={() => {
                    setEditingOverride(row);
                    setOverrideDate(row.operating_date);
                    setOverrideOperating(row.is_operating);
                  }}
                  onDelete={() => void deleteOverride(row.operating_date)}
                />
              </td>
            </>
          )}
        />
      </div>
    </div>
  );
}

function RecordTable<T>({
  rows,
  columns,
  render,
  getKey,
}: {
  rows: T[];
  columns: string[];
  render: (row: T) => ReactNode;
  getKey?: (row: T, index: number) => string | number;
}) {
  return (
    <div className="mt-4 min-w-max">
      <table className="w-full text-left text-[11px]">
        <thead className="sticky top-0 z-10 bg-[#f7f8ff]">
          <tr>{columns.map((column) => (
            <th key={column} className="border-b border-[#e2e7ff] px-2 py-2">{column}</th>
          ))}</tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((row, index) => (
            <tr key={getKey ? getKey(row, index) : index} className="border-b border-[#eaedff]">
              {render(row)}
            </tr>
          )) : (
            <tr>
              <td colSpan={columns.length}><EmptyState title="No records" compact /></td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-2">
      <button type="button" aria-label="Edit" onClick={onEdit} className="rounded p-1 hover:bg-[#eaedff]">
        <Pencil className="h-4 w-4 text-[#3525cd]" />
      </button>
      <button type="button" aria-label="Delete" onClick={onDelete} className="rounded p-1 hover:bg-[#ffdad6]">
        <Trash2 className="h-4 w-4 text-[#93000a]" />
      </button>
    </div>
  );
}

function DaySelector({
  label,
  days,
  onChange,
}: {
  label: string;
  days: number[];
  onChange: (days: number[]) => void;
}) {
  return (
    <fieldset>
      <legend className="text-[11px] font-semibold">{label}</legend>
      <div className="mt-2 flex flex-wrap gap-1">
        {weekdays.map((day, index) => (
          <button
            key={day}
            type="button"
            aria-pressed={days.includes(index)}
            onClick={() => onChange(
              days.includes(index)
                ? days.filter((value) => value !== index)
                : [...days, index].sort(),
            )}
            className={`rounded-lg px-2 py-1 text-[10px] ${
              days.includes(index) ? "bg-[#4f46e5] text-white" : "bg-white text-[#464555]"
            }`}
          >
            {day.slice(0, 3)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function shiftsForProcess(data: ReturnType<typeof useRosterData>, processId: string) {
  if (!processId) return [];
  const processPodIds = new Set(
    data.pods.filter((pod) => pod.process_id === processId).map((pod) => pod.id),
  );
  return data.shifts.filter((shift) => processPodIds.has(shift.pod_id));
}

function processName(processId: string, data: ReturnType<typeof useRosterData>) {
  const process = data.processes.find((item) => item.id === processId);
  if (!process) return processId;
  const brand = data.brands.find((item) => item.id === process.brand_id);
  return `${brand?.name || "Brand"} / ${process.name}`;
}

function shiftName(shiftId: string | null, data: ReturnType<typeof useRosterData>) {
  if (!shiftId) return "All shifts";
  return data.shifts.find((shift) => shift.id === shiftId)?.shift_name || shiftId;
}

function weekdayNames(days: number[]) {
  return days.length ? days.map((day) => weekdays[day]).join(", ") : "None";
}
