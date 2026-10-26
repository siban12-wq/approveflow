import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Calendar as CalendarIcon,
  Calculator,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  Info,
  CalendarDays,
  MapPin,
  CalendarClock,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useUi } from "@/store/ui";

interface Holiday {
  id: number;
  date: string;
  name: string;
  holiday_type: string;
  state: string | null;
  is_national: boolean;
}

interface CalendarPolicy {
  id: number;
  name: string;
  description: string | null;
  working_days_per_week: number;
  working_hours_start: string;
  working_hours_end: string;
  saturday_policy: string;
  emergency_freeze: boolean;
}

interface DueDateCalcResponse {
  start_date: string;
  working_days_added: number;
  due_date: string;
  calendar_days: number;
  holidays_encountered: number;
  weekends_encountered: number;
  policy_used: string;
}

export default function CalendarPage() {
  const toast = useUi((s) => s.toast);

  // SLA Calculator State
  const [calcStartDate, setCalcStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [calcWorkingDays, setCalcWorkingDays] = useState(15);
  const [calcResult, setCalcResult] = useState<DueDateCalcResponse | null>(null);

  const policiesQuery = useQuery({
    queryKey: ["calendar-policies"],
    queryFn: () => api.get<CalendarPolicy[]>("/api/v1/calendar/policies"),
  });

  const holidaysQuery = useQuery({
    queryKey: ["calendar-holidays"],
    queryFn: () => api.get<Holiday[]>("/api/v1/calendar/holidays?year=2026"),
  });

  const calcMutation = useMutation({
    mutationFn: () =>
      api.post<DueDateCalcResponse>("/api/v1/calendar/calculate-due-date", {
        start_date: new Date(calcStartDate).toISOString(),
        working_days: calcWorkingDays,
      }),
    onSuccess: (data) => {
      setCalcResult(data);
      toast("Target SLA due date calculated accurately");
    },
    onError: (err: any) => {
      toast(err.message || "Calculation failed");
    },
  });

  const activePolicy = policiesQuery.data?.[0];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-ink flex items-center gap-2">
          <CalendarIcon className="h-7 w-7 text-primary" />
          Working-Day Calendar Engine
        </h1>
        <p className="text-sm text-slate-500">
          Statutory working calendar policies, Gazetted public holidays, and automated SLA working-day math.
        </p>
      </div>

      {/* Grid: Policy & SLA Calculator */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column: Active Policy & Engine Info */}
        <div className="space-y-6 lg:col-span-5">
          <Card className="border-t-4 border-t-primary">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-ink flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                Statutory Working Calendar Policy
              </h2>
              <Badge tone="success">Active</Badge>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Configured per AICTE Approval Process Handbook (APH) guidelines.
            </p>

            <div className="mt-4 space-y-3 divide-y divide-line text-sm">
              <div className="flex justify-between pt-2">
                <span className="text-slate-500">Policy Name</span>
                <span className="font-semibold text-ink">{activePolicy?.name ?? "Standard AICTE Working Calendar"}</span>
              </div>
              <div className="flex justify-between pt-2">
                <span className="text-slate-500">Working Days / Week</span>
                <span className="font-semibold text-ink">
                  {activePolicy?.working_days_per_week ?? 5} Days (Mon – Fri)
                </span>
              </div>
              <div className="flex justify-between pt-2">
                <span className="text-slate-500">Saturday Policy</span>
                <span className="font-semibold text-ink capitalize">
                  {activePolicy?.saturday_policy?.replace("_", " ") ?? "All Off"}
                </span>
              </div>
              <div className="flex justify-between pt-2">
                <span className="text-slate-500">Working Hours</span>
                <span className="font-semibold text-ink">
                  {activePolicy?.working_hours_start ?? "09:30"} - {activePolicy?.working_hours_end ?? "17:30"} IST
                </span>
              </div>
              <div className="flex justify-between pt-2">
                <span className="text-slate-500">Emergency Statutory Freeze</span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Normal Operations
                </span>
              </div>
            </div>

            <div className="mt-4 rounded-xl bg-blue-50/60 p-3 text-xs text-blue-900 border border-blue-100 flex items-start gap-2">
              <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
              <span>
                Deadlines automatically advance past gazetted holidays and weekends. Clock pause records provide complete statutory audit logs.
              </span>
            </div>
          </Card>

          {/* Interactive Calculator */}
          <Card className="border-t-4 border-t-cyan-500">
            <h2 className="text-lg font-bold text-ink flex items-center gap-2">
              <Calculator className="h-5 w-5 text-cyan-600" />
              Interactive SLA Due Date Calculator
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Calculate exact statutory target date factoring in weekends and Gazetted holidays.
            </p>

            <div className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700">Application / Stage Start Date</label>
                <input
                  type="date"
                  value={calcStartDate}
                  onChange={(e) => setCalcStartDate(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 flex justify-between">
                  <span>Statutory Working Days Required</span>
                  <span className="text-primary font-bold">{calcWorkingDays} Days</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={60}
                  value={calcWorkingDays}
                  onChange={(e) => setCalcWorkingDays(parseInt(e.target.value, 10))}
                  className="mt-2 w-full accent-primary"
                />
                <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                  <span>1 day</span>
                  <span>15d (EVC)</span>
                  <span>30d (SAC/SHC)</span>
                  <span>60d (APH Max)</span>
                </div>
              </div>

              <Button
                className="w-full flex items-center justify-center gap-2"
                onClick={() => calcMutation.mutate()}
                disabled={calcMutation.isPending}
              >
                <Sparkles className="h-4 w-4" />
                {calcMutation.isPending ? "Computing..." : "Calculate Target Due Date"}
              </Button>

              {calcResult && (
                <div className="mt-4 rounded-xl border border-cyan-200 bg-cyan-50/60 p-4 space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-cyan-800">
                    Statutory Calculation Result
                  </div>
                  <div className="text-2xl font-black text-ink">
                    {new Date(calcResult.due_date).toLocaleDateString("en-IN", {
                      weekday: "long",
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })}
                  </div>
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-cyan-200/60 text-xs">
                    <div>
                      <span className="text-slate-500 block">Total Calendar</span>
                      <span className="font-bold text-ink">{calcResult.calendar_days} days</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Weekends Skipped</span>
                      <span className="font-bold text-ink">{calcResult.weekends_encountered} days</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Holidays Skipped</span>
                      <span className="font-bold text-ink">{calcResult.holidays_encountered} days</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Gazetted Holidays Calendar */}
        <div className="space-y-4 lg:col-span-7">
          <Card className="p-0 overflow-hidden">
            <div className="border-b border-line bg-canvas p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <h2 className="text-lg font-bold text-ink flex items-center gap-2">
                  <CalendarDays className="h-5 w-5 text-primary" />
                  Gazetted Public Holidays (Calendar Year 2026)
                </h2>
                <p className="text-xs text-slate-500">
                  Statutory non-working days officially recognized by AICTE Headquarters and Regional Offices.
                </p>
              </div>
              <Badge tone="primary">14 Official Holidays</Badge>
            </div>

            <div className="overflow-x-auto max-h-[680px]">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-white border-b border-line text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Holiday Date</th>
                    <th className="px-4 py-3">Occasion / Description</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Jurisdiction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {(holidaysQuery.data ?? []).map((h) => {
                    const dateObj = new Date(h.date);
                    const formattedDate = dateObj.toLocaleDateString("en-IN", {
                      weekday: "short",
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    });

                    return (
                      <tr key={h.id} className="hover:bg-canvas/50 transition-colors">
                        <td className="px-4 py-3 font-medium text-ink whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <CalendarClock className="h-4 w-4 text-slate-400" />
                            {formattedDate}
                          </div>
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-800">{h.name}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800 capitalize">
                            {h.holiday_type}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {h.is_national ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                              <ShieldCheck className="h-3.5 w-3.5" /> All India
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-600">
                              <MapPin className="h-3.5 w-3.5" /> {h.state}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
