import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useUi } from "@/store/ui";
import { useState } from "react";
import { useAuth } from "@/store/auth";

const JOBS = ["sla_checker", "evc_reminder_job", "undertaking_reminder_job", "document_expiry_job", "escalation_job", "digest_job"];

export default function AdminMonitor() {
  const toast = useUi((s) => s.toast);
  const user = useAuth((s) => s.user)!;
  const [days, setDays] = useState(7);
  const runs = useQuery({ queryKey: ["jobruns"], queryFn: () => api.get<{ name: string; started_at: string; alerts_created: number; items_checked: number }[]>("/api/v1/admin/jobs/runs") });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">Monitoring console</h1>
      <p className="text-sm text-slate-500">Jobs write notifications and SYSTEM audit rows. They never approve or reject applications.</p>
      <div className="grid gap-3 md:grid-cols-3">
        {JOBS.map((j) => (
          <Card key={j}>
            <div className="font-semibold">{j}</div>
            <Button
              className="mt-3"
              size="sm"
              onClick={async () => {
                const res = await api.post<{ alerts_created: number; items_checked: number }>(`/api/v1/admin/jobs/${j}/run`);
                toast(`${j}: ${res.alerts_created} alerts / ${res.items_checked} checked`);
                runs.refetch();
              }}
            >
              Run now
            </Button>
          </Card>
        ))}
      </div>
      {user.role === "super_admin" && (
        <Card>
          <h2 className="font-semibold">Demo clock</h2>
          <input type="range" min={0} max={30} value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-full" />
          <p className="text-sm">Advance +{days} days to show alerts firing live.</p>
          <div className="mt-2 flex gap-2">
            <Button
              size="sm"
              onClick={async () => {
                const res = await api.post<{ now: string }>(`/api/v1/admin/demo/advance-clock?days=${days}`);
                toast(`Clock now ${res.now}`);
              }}
            >
              Advance clock
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={async () => {
                await api.post("/api/v1/admin/demo/reset");
                toast("Demo data restored. Sign in again if sessions look stale.", "warn");
              }}
            >
              Reset demo data
            </Button>
          </div>
        </Card>
      )}
      <Card>
        <h2 className="mb-2 font-semibold">Last runs</h2>
        <ul className="text-sm">
          {(runs.data ?? []).map((r, i) => (
            <li key={i}>
              {r.name} · checked {r.items_checked} · alerts {r.alerts_created} · {r.started_at}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
