import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";

type Doc = {
  id: number;
  institution: string;
  doc_type: string;
  document_number: string;
  expiry_date: string;
  status: string;
  days_left: number;
  hash: string;
};

export default function Documents() {
  const user = useAuth((s) => s.user)!;
  const toast = useUi((s) => s.toast);
  const q = useQuery({ queryKey: ["docs"], queryFn: () => api.get<Doc[]>("/api/v1/documents") });
  const summary = useQuery({ queryKey: ["docs-sum"], queryFn: () => api.get<Record<string, number>>("/api/v1/documents/expiry-summary") });
  const official = ["regional_officer", "bureau_officer", "super_admin"].includes(user.role);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">Lease and document validity</h1>
      <div className="flex flex-wrap gap-3 text-sm">
        {Object.entries(summary.data ?? {}).map(([k, v]) => (
          <span key={k} className="rounded-full bg-white px-3 py-1 shadow-card">
            {k} days window: {v}
          </span>
        ))}
      </div>
      {(q.data ?? []).map((d) => (
        <Card key={d.id}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <Badge>{d.status}</Badge>
              <p className="mt-1 font-medium">
                {d.institution} · {d.doc_type} · {d.document_number}
              </p>
              <p className="text-xs text-slate-500">
                Expires {d.expiry_date} · {d.days_left} days · SHA-256 {d.hash?.slice(0, 12)}
              </p>
            </div>
            <div className="flex gap-2">
              {user.role === "institution_user" && (
                <Button
                  size="sm"
                  onClick={async () => {
                    const exp = new Date();
                    exp.setFullYear(exp.getFullYear() + 5);
                    await api.post(`/api/v1/documents/${d.id}/renew`, {
                      issue_date: new Date().toISOString(),
                      expiry_date: exp.toISOString(),
                      sha256: "renewed-demo-hash",
                    });
                    toast("Renewal submitted");
                    q.refetch();
                  }}
                >
                  Submit renewal
                </Button>
              )}
              {official && (
                <Button
                  size="sm"
                  onClick={async () => {
                    await api.post(`/api/v1/documents/${d.id}/verify`, { accept: true });
                    q.refetch();
                  }}
                >
                  Verify
                </Button>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
