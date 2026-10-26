import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Eye, Plus, Shield, ShieldAlert, UserCheck, UserX, X } from "lucide-react";
import { api, ROLE_LABELS } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { useUi } from "@/store/ui";

type UserRow = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  role_name: string;
  region: string | null;
  institution: string | null;
  account_status: string;
  is_active: boolean;
  email_verified: boolean;
  mobile: string | null;
  requested_role: string | null;
  requested_institution_name: string | null;
  created_at: string | null;
  status_reason: string | null;
};

export default function AdminAccounts() {
  const toast = useUi((s) => s.toast);
  const [activeTab, setActiveTab] = useState<"pending" | "active" | "all">("pending");
  const [actionUser, setActionUser] = useState<UserRow | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | "suspend" | "reactivate" | null>(null);
  const [reason, setReason] = useState("");
  const [provisionOpen, setProvisionOpen] = useState(false);

  // Form state for privileged user provisioning
  const [provEmail, setProvEmail] = useState("");
  const [provName, setProvName] = useState("");
  const [provRole, setProvRole] = useState("scrutiny_officer");
  const [provReason, setProvReason] = useState("");
  const [provPass, setProvPass] = useState("");

  const q = useQuery({
    queryKey: ["admin-users", activeTab],
    queryFn: () =>
      api.get<UserRow[]>(
        `/api/v1/admin/users${activeTab === "pending" ? "?status=pending" : activeTab === "active" ? "?status=active" : ""}`
      ),
  });

  const users = q.data ?? [];
  const pendingCount = users.filter((u) => u.account_status === "pending").length;

  async function handleActionSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!actionUser || !actionType || !reason) return;
    try {
      await api.post(`/api/v1/admin/accounts/${actionUser.id}/${actionType}`, { reason });
      toast(`Account ${actionType}d successfully`, "ok");
      setActionUser(null);
      setActionType(null);
      setReason("");
      q.refetch();
    } catch (err) {
      toast((err as Error).message || "Action failed", "err");
    }
  }

  async function handleProvisionSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/v1/admin/accounts/provision", {
        email: provEmail,
        full_name: provName,
        role: provRole,
        reason: provReason,
        password: provPass || "Demo@123",
      });
      toast(`Privileged account provisioned for ${provName}`, "ok");
      setProvisionOpen(false);
      setProvEmail("");
      setProvName("");
      setProvReason("");
      setProvPass("");
      q.refetch();
    } catch (err) {
      toast((err as Error).message || "Provisioning failed", "err");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">User & Account Governance</h1>
          <p className="text-sm text-slate-500">
            Review institution registration requests, enforce least privilege, and provision official accounts.
          </p>
        </div>
        <Button onClick={() => setProvisionOpen(true)} className="flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Provision Officer Account
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-line pb-3">
        <button
          onClick={() => setActiveTab("pending")}
          className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all ${
            activeTab === "pending" ? "bg-amber-500 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100"
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5" /> Pending Verification
          {pendingCount > 0 && <span className="rounded-full bg-white/30 px-1.5 py-0.2 text-[10px]">{pendingCount}</span>}
        </button>
        <button
          onClick={() => setActiveTab("active")}
          className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all ${
            activeTab === "active" ? "bg-brand-600 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100"
          }`}
        >
          Active Accounts
        </button>
        <button
          onClick={() => setActiveTab("all")}
          className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all ${
            activeTab === "all" ? "bg-slate-800 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100"
          }`}
        >
          All Accounts
        </button>
      </div>

      {/* Users Table */}
      <DataTable
        rows={users as unknown as Record<string, unknown>[]}
        columns={[
          {
            key: "full_name",
            header: "User / Contact",
            render: (r) => (
              <div>
                <p className="font-semibold text-ink">{String(r.full_name)}</p>
                <p className="text-xs text-slate-500">{String(r.email)}</p>
                {Boolean(r.mobile) && <p className="text-[11px] text-slate-400">Mobile: {String(r.mobile)}</p>}
              </div>
            ),
          },
          {
            key: "role",
            header: "Role",
            render: (r) => (
              <Badge tone={String(r.role).includes("admin") ? "indigo" : "slate"}>
                {ROLE_LABELS[String(r.role)] || String(r.role)}
              </Badge>
            ),
          },
          {
            key: "institution",
            header: "Institution / Jurisdiction",
            render: (r) => (
              <div className="text-xs">
                <p className="font-medium text-ink">{String(r.institution || r.requested_institution_name || "—")}</p>
                <p className="text-slate-400">{String(r.region || "All Regions")}</p>
              </div>
            ),
          },
          {
            key: "account_status",
            header: "Status",
            render: (r) => {
              const st = String(r.account_status || "active");
              const tone = st === "active" ? "emerald" : st === "pending" ? "amber" : "rose";
              return <Badge tone={tone}>{st.toUpperCase()}</Badge>;
            },
          },
          {
            key: "actions",
            header: "Actions",
            render: (r) => {
              const u = r as unknown as UserRow;
              return (
                <div className="flex items-center gap-1.5">
                  {u.account_status === "pending" ? (
                    <>
                      <Button
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-2.5 py-1"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActionUser(u);
                          setActionType("approve");
                          setReason("Identity verified against AICTE Institution Master Register");
                        }}
                      >
                        <Check className="h-3.5 w-3.5 mr-1" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-rose-600 hover:bg-rose-50 border-rose-200 text-xs px-2.5 py-1"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActionUser(u);
                          setActionType("reject");
                          setReason("Institution credentials could not be verified");
                        }}
                      >
                        <X className="h-3.5 w-3.5 mr-1" /> Reject
                      </Button>
                    </>
                  ) : u.account_status === "active" ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-slate-600 text-xs px-2.5 py-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActionUser(u);
                        setActionType("suspend");
                        setReason("Administrative compliance review");
                      }}
                    >
                      <UserX className="h-3.5 w-3.5 mr-1" /> Suspend
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-emerald-700 text-xs px-2.5 py-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActionUser(u);
                        setActionType("reactivate");
                        setReason("Account reactivated following review");
                      }}
                    >
                      <UserCheck className="h-3.5 w-3.5 mr-1" /> Reactivate
                    </Button>
                  )}
                </div>
              );
            },
          },
        ]}
      />

      {/* Action Reason Confirmation Modal */}
      {actionUser && actionType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-ink capitalize">
              {actionType} Account: {actionUser.full_name}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Regulatory governance requires a mandatory recorded reason for all administrative account status transitions.
            </p>

            <form onSubmit={handleActionSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Reason for {actionType}
                </label>
                <textarea
                  rows={3}
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="State statutory verification or justification reason..."
                  className="w-full rounded-xl border border-line p-2.5 text-sm"
                />
              </div>

              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" size="sm" onClick={() => setActionUser(null)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" className="capitalize">
                  Confirm {actionType}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Provision Officer Modal */}
      {provisionOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-ink">Provision Privileged Officer Account</h3>
            <p className="mt-1 text-xs text-slate-500">
              Create an official AICTE scrutiny officer, regional bureau officer, or EVC committee account.
            </p>

            <form onSubmit={handleProvisionSubmit} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Officer Full Name
                </label>
                <input
                  required
                  value={provName}
                  onChange={(e) => setProvName(e.target.value)}
                  placeholder="e.g. Smt. Radha Murthy"
                  className="w-full rounded-xl border border-line p-2.5 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Official Email Address
                </label>
                <input
                  type="email"
                  required
                  value={provEmail}
                  onChange={(e) => setProvEmail(e.target.value)}
                  placeholder="e.g. radha.murthy@aicte-india.org"
                  className="w-full rounded-xl border border-line p-2.5 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Assigned Role
                </label>
                <select
                  value={provRole}
                  onChange={(e) => setProvRole(e.target.value)}
                  className="w-full rounded-xl border border-line p-2.5 text-sm bg-white"
                >
                  <option value="scrutiny_officer">Scrutiny Officer</option>
                  <option value="regional_officer">Regional Officer</option>
                  <option value="bureau_officer">Bureau Officer</option>
                  <option value="committee_member">EVC Committee Member</option>
                  <option value="competent_authority">Competent Authority</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Temporary Password
                </label>
                <input
                  type="text"
                  value={provPass}
                  onChange={(e) => setProvPass(e.target.value)}
                  placeholder="Demo@123 (or custom password)"
                  className="w-full rounded-xl border border-line p-2.5 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Administrative Justification / Office Order Ref
                </label>
                <input
                  required
                  value={provReason}
                  onChange={(e) => setProvReason(e.target.value)}
                  placeholder="e.g. As per AICTE Northern Region Bureau Order No. 412/2026"
                  className="w-full rounded-xl border border-line p-2.5 text-sm"
                />
              </div>

              <div className="pt-2 flex gap-2 justify-end">
                <Button type="button" variant="outline" size="sm" onClick={() => setProvisionOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm">
                  Provision Account
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
