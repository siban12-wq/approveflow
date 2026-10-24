import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";

type Row = {
  id: number;
  institution: string;
  condition_text: string;
  category: string;
  due_date: string;
  status: string;
  evidence_required: string;
};

export default function Undertakings() {
  const user = useAuth((s) => s.user)!;
  const toast = useUi((s) => s.toast);
  const q = useQuery({ queryKey: ["ut"], queryFn: () => api.get<Row[]>("/api/v1/undertakings") });
  const official = ["regional_officer", "bureau_officer", "super_admin"].includes(user.role);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">Time-bound undertakings</h1>
      <p className="text-sm text-slate-500">Verification is always the official's own action. The engine only reminds and records.</p>
      {(q.data ?? []).map((u) => (
        <Card key={u.id}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <Badge>{u.status}</Badge>
              <p className="mt-2 font-medium">{u.institution}</p>
              <p className="text-sm">{u.condition_text}</p>
              <p className="text-xs text-slate-500">
                Due {u.due_date} · {u.evidence_required}
              </p>
            </div>
            <div className="flex gap-2">
              {user.role === "institution_user" && (
                <Button
                  size="sm"
                  onClick={async () => {
                    const res = await api.post<{ receipt: string }>(`/api/v1/undertakings/${u.id}/submit-evidence`, { notes: "Occupancy certificate uploaded." });
                    toast(`Receipt ${res.receipt}`);
                    q.refetch();
                  }}
                >
                  Upload evidence
                </Button>
              )}
              {official && (
                <>
                  <Button size="sm" onClick={async () => { await api.post(`/api/v1/undertakings/${u.id}/verify`, { action: "accept" }); q.refetch(); }}>
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={async () => {
                      await api.post(`/api/v1/undertakings/${u.id}/verify`, { action: "reject", reason: "Evidence incomplete for the workshop block." });
                      q.refetch();
                    }}
                  >
                    Reject with reason
                  </Button>
                </>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
