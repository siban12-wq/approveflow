import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Clock,
  AlertTriangle,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Search,
  Filter,
  Calendar,
  Layers,
  FileText,
  Building,
  ShieldAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useUi } from "@/store/ui";
import { useAuth } from "@/store/auth";

interface DeadlineItem {
  id: number;
  title: string;
  deadline_type: string;
  status: string;
  linked_entity_type: string;
  linked_entity_id: number;
  target_due_date: string;
  days_remaining: number;
  is_overdue: boolean;
  is_paused: boolean;
  total_working_days: number | null;
  working_days_consumed: number | null;
  working_days_remaining: number | null;
  pause_reason: string | null;
  paused_at: string | null;
  pause_accumulated_days: number;
  urgency: string;
}

interface DeadlineSummary {
  total_active: number;
  approaching: number;
  overdue: number;
  paused: number;
  by_type: Record<string, number>;
}

export default function Deadlines() {
  const queryClient = useQueryClient();
  const toast = useUi((s) => s.toast);
  const user = useAuth((s) => s.user)!;

  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Pause / Resume modal state
  const [selectedDeadline, setSelectedDeadline] = useState<DeadlineItem | null>(null);
  const [pauseModalOpen, setPauseModalOpen] = useState(false);
  const [pauseReason, setPauseReason] = useState("officer_leave");
  const [pauseNotes, setPauseNotes] = useState("");

  const summaryQuery = useQuery({
    queryKey: ["deadlines-summary"],
    queryFn: () => api.get<DeadlineSummary>("/api/v1/deadlines/summary"),
  });

  const deadlinesQuery = useQuery({
    queryKey: ["deadlines", typeFilter, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (typeFilter !== "all") params.append("deadline_type", typeFilter);
      if (statusFilter !== "all") params.append("status", statusFilter);
      return api.get<DeadlineItem[]>(`/api/v1/deadlines?${params.toString()}`);
    },
  });

  const syncMutation = useMutation({
    mutationFn: () => api.post<{ message: string; synced_count: number }>("/api/v1/deadlines/batch-sync", {}),
    onSuccess: (data) => {
      toast(data.message || `Synchronized ${data.synced_count} deadlines`);
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
      queryClient.invalidateQueries({ queryKey: ["deadlines-summary"] });
    },
    onError: (err: any) => {
      toast(err.message || "Failed to synchronize deadlines");
    },
  });

  const pauseMutation = useMutation({
    mutationFn: ({ id, reason, notes }: { id: number; reason: string; notes: string }) =>
      api.post(`/api/v1/deadlines/${id}/pause`, { reason, notes }),
    onSuccess: () => {
      toast("Deadline calculation paused");
      setPauseModalOpen(false);
      setSelectedDeadline(null);
      setPauseNotes("");
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
      queryClient.invalidateQueries({ queryKey: ["deadlines-summary"] });
    },
    onError: (err: any) => {
      toast(err.message || "Failed to pause deadline");
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => api.post(`/api/v1/deadlines/${id}/resume`, {}),
    onSuccess: () => {
      toast("Deadline resumed with adjusted due date");
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
      queryClient.invalidateQueries({ queryKey: ["deadlines-summary"] });
    },
    onError: (err: any) => {
      toast(err.message || "Failed to resume deadline");
    },
  });

  const isPrivileged = ["super_admin", "bureau_officer", "regional_officer"].includes(user.role);

  const filteredItems = (deadlinesQuery.data ?? []).filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.deadline_type.toLowerCase().includes(q) ||
      item.linked_entity_type.toLowerCase().includes(q)
    );
  });

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "stage_sla":
        return "Application Stage SLA";
      case "evc_completion":
        return "EVC Visit & Report";
      case "undertaking_compliance":
        return "Institutional Undertaking";
      case "document_expiry":
        return "Lease Document Expiry";
      default:
        return type;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "stage_sla":
        return <Layers className="h-4 w-4 text-indigo-500" />;
      case "evc_completion":
        return <Calendar className="h-4 w-4 text-cyan-500" />;
      case "undertaking_compliance":
        return <FileText className="h-4 w-4 text-amber-500" />;
      case "document_expiry":
        return <Building className="h-4 w-4 text-rose-500" />;
      default:
        return <Clock className="h-4 w-4 text-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-ink flex items-center gap-2">
            <Clock className="h-7 w-7 text-primary" />
            Unified Deadline Engine
          </h1>
          <p className="text-sm text-slate-500">
            Automated statutory SLA monitoring, working-day adjustments, and multi-stream compliance tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isPrivileged && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${syncMutation.isPending ? "animate-spin" : ""}`} />
              Batch Sync Deadlines
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="border-l-4 border-l-primary bg-gradient-to-br from-white to-blue-50/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Deadlines</span>
            <Layers className="h-5 w-5 text-primary" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-ink">{summaryQuery.data?.total_active ?? 0}</div>
          <div className="mt-1 text-xs text-slate-400">Tracked across 4 statutory streams</div>
        </Card>

        <Card className="border-l-4 border-l-amber-500 bg-gradient-to-br from-white to-amber-50/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-700">Approaching (≤3 Days)</span>
            <AlertTriangle className="h-5 w-5 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-amber-900">{summaryQuery.data?.approaching ?? 0}</div>
          <div className="mt-1 text-xs text-amber-600">Action required promptly</div>
        </Card>

        <Card className="border-l-4 border-l-rose-500 bg-gradient-to-br from-white to-rose-50/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-700">Breached / Overdue</span>
            <ShieldAlert className="h-5 w-5 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-rose-900">{summaryQuery.data?.overdue ?? 0}</div>
          <div className="mt-1 text-xs text-rose-600">Requires escalation/justification</div>
        </Card>

        <Card className="border-l-4 border-l-slate-400 bg-gradient-to-br from-white to-slate-50/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Calculation Paused</span>
            <PauseCircle className="h-5 w-5 text-slate-500" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-slate-800">{summaryQuery.data?.paused ?? 0}</div>
          <div className="mt-1 text-xs text-slate-500">Statutory freeze or approved leave</div>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by title, entity, or keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-line bg-canvas pl-9 pr-3 py-2 text-sm focus:border-primary focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Filter className="h-3.5 w-3.5" />
              <span>Stream:</span>
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-xl border border-line bg-white px-3 py-1.5 text-xs font-medium text-slate-700 focus:outline-none focus:border-primary"
            >
              <option value="all">All Statutory Streams</option>
              <option value="stage_sla">Application Stage SLA</option>
              <option value="evc_completion">EVC Completion</option>
              <option value="undertaking_compliance">Undertakings</option>
              <option value="document_expiry">Document Expiry</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl border border-line bg-white px-3 py-1.5 text-xs font-medium text-slate-700 focus:outline-none focus:border-primary"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="paused">Paused</option>
              <option value="breached">Breached / Overdue</option>
              <option value="met">Met / Completed</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Deadlines Table */}
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-canvas border-b border-line text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3">Deadline & Stream</th>
                <th className="px-4 py-3">Linked Entity</th>
                <th className="px-4 py-3">Target Due Date</th>
                <th className="px-4 py-3">Working Days Progress</th>
                <th className="px-4 py-3">Countdown / Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    No deadlines matching current criteria.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const targetDate = item.target_due_date ? new Date(item.target_due_date) : null;
                  const formattedDate = targetDate
                    ? targetDate.toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })
                    : "Not scheduled";

                  return (
                    <tr key={item.id} className="hover:bg-canvas/50 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-start gap-2.5">
                          <div className="mt-0.5 rounded-lg bg-canvas p-1.5 border border-line">
                            {getTypeIcon(item.deadline_type)}
                          </div>
                          <div>
                            <div className="font-semibold text-ink">{item.title}</div>
                            <div className="text-xs text-slate-400">{getTypeLabel(item.deadline_type)}</div>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-mono font-medium text-slate-700">
                          {item.linked_entity_type.toUpperCase()} #{item.linked_entity_id}
                        </span>
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="font-medium text-slate-700">{formattedDate}</div>
                        {item.is_paused && (
                          <span className="text-[11px] text-amber-600 font-medium">Clock paused</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 min-w-[180px]">
                        {item.total_working_days ? (
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs text-slate-500">
                              <span>
                                {item.working_days_consumed ?? 0} / {item.total_working_days} working days
                              </span>
                              <span>
                                {Math.round(
                                  Math.min(
                                    100,
                                    (((item.working_days_consumed ?? 0) / item.total_working_days) * 100)
                                  )
                                )}
                                %
                              </span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  item.is_overdue
                                    ? "bg-rose-500"
                                    : (item.working_days_consumed ?? 0) / item.total_working_days > 0.8
                                    ? "bg-amber-500"
                                    : "bg-primary"
                                }`}
                                style={{
                                  width: `${Math.min(
                                    100,
                                    (((item.working_days_consumed ?? 0) / item.total_working_days) * 100)
                                  )}%`,
                                }}
                              />
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">Fixed calendar date</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5">
                        {item.is_paused ? (
                          <Badge tone="paused">
                            <PauseCircle className="mr-1 h-3 w-3 inline" /> Paused
                          </Badge>
                        ) : item.is_overdue ? (
                          <Badge tone="danger">
                            <AlertTriangle className="mr-1 h-3 w-3 inline" />
                            Overdue ({Math.abs(item.days_remaining)}d)
                          </Badge>
                        ) : item.days_remaining <= 3 ? (
                          <Badge tone="warning">
                            <Clock className="mr-1 h-3 w-3 inline" />
                            {item.days_remaining === 0 ? "Due today" : `${item.days_remaining}d remaining`}
                          </Badge>
                        ) : (
                          <Badge tone="success">
                            <CheckCircle2 className="mr-1 h-3 w-3 inline" />
                            {item.days_remaining}d remaining
                          </Badge>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        {isPrivileged && (
                          <div className="inline-flex items-center gap-1">
                            {item.is_paused ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => resumeMutation.mutate(item.id)}
                                disabled={resumeMutation.isPending}
                                className="text-xs flex items-center gap-1 text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                              >
                                <PlayCircle className="h-3.5 w-3.5" />
                                Resume
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setSelectedDeadline(item);
                                  setPauseModalOpen(true);
                                }}
                                className="text-xs flex items-center gap-1 text-slate-600 hover:text-ink"
                              >
                                <PauseCircle className="h-3.5 w-3.5" />
                                Pause SLA
                              </Button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Pause Modal */}
      {pauseModalOpen && selectedDeadline && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-line">
            <h3 className="text-lg font-bold text-ink flex items-center gap-2">
              <PauseCircle className="h-5 w-5 text-amber-500" />
              Pause SLA Calculation
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Pausing stops the statutory clock from advancing. Resuming will automatically append paused calendar days to the target due date.
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700">Deadline Item</label>
                <div className="mt-1 text-sm font-medium text-ink bg-canvas p-2.5 rounded-xl border border-line">
                  {selectedDeadline.title}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Official Pause Reason</label>
                <select
                  value={pauseReason}
                  onChange={(e) => setPauseReason(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="officer_leave">Designated Officer Leave / Deputation</option>
                  <option value="natural_disaster">Natural Disaster / Emergency Disruption</option>
                  <option value="legal_stay">Court Order / Legal Stay</option>
                  <option value="system_maintenance">Portal Statutory Maintenance</option>
                  <option value="other">Other Competent Authority Order</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Official Notes & Approval Reference</label>
                <textarea
                  rows={3}
                  value={pauseNotes}
                  onChange={(e) => setPauseNotes(e.target.value)}
                  placeholder="Reference memo number or statutory rationale..."
                  className="mt-1 w-full rounded-xl border border-line bg-canvas p-2.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPauseModalOpen(false);
                  setSelectedDeadline(null);
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() =>
                  pauseMutation.mutate({
                    id: selectedDeadline.id,
                    reason: pauseReason,
                    notes: pauseNotes,
                  })
                }
                disabled={pauseMutation.isPending}
              >
                {pauseMutation.isPending ? "Pausing..." : "Confirm SLA Pause"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
