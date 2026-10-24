import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useState } from "react";
import { useUi } from "@/store/ui";

type Visit = {
  id: number;
  app_id: string;
  institution: string;
  status: string;
  priority_new: boolean;
  days_since_eligible: number;
  scheduling_deadline: string;
  scheduled_at: string | null;
  venue: string | null;
};

export default function Evc() {
  const toast = useUi((s) => s.toast);
  const [view, setView] = useState<"list" | "month">("list");
  const q = useQuery({ queryKey: ["evc"], queryFn: () => api.get<Visit[]>("/api/v1/evc/queue") });
  const items = q.data ?? [];

  async function schedule(id: number) {
    const when = new Date();
    when.setDate(when.getDate() + 3);
    try {
      await api.post(`/api/v1/evc/${id}/schedule`, {
        scheduled_at: when.toISOString(),
        venue: "Institution campus",
        member_ids: [],
      });
      toast("Visit scheduled");
      q.refetch();
    } catch (e) {
      toast((e as Error).message, "err");
    }
  }

  async function report(id: number) {
    try {
      await api.post(`/api/v1/evc/${id}/report`, {
        recommendation: "Infrastructure found broadly compliant. Recommendation only — not a decision.",
      });
      toast("Recommendation recorded");
      q.refetch();
    } catch (e) {
      toast((e as Error).message, "err");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">EVC queue</h1>
        <div className="flex gap-2">
          <Button size="sm" variant={view === "list" ? "primary" : "outline"} onClick={() => setView("list")}>
            List
          </Button>
          <Button size="sm" variant={view === "month" ? "primary" : "outline"} onClick={() => setView("month")}>
            Month
          </Button>
        </div>
      </div>
      <p className="text-sm text-slate-500">New institutions are highlighted. Countdown chips use days since eligible. Visit reports are recommendations, never decisions.</p>
      {view === "month" && (
        <Card>
          <p className="text-sm">Scheduled visits this cycle</p>
          <ul className="mt-2 text-sm">
            {items.filter((v) => v.scheduled_at).map((v) => (
              <li key={v.id}>
                {v.scheduled_at} · {v.app_id} · {v.venue}
              </li>
            ))}
          </ul>
        </Card>
      )}
      <div className="grid gap-3">
        {items.map((v) => (
          <Card key={v.id} className={v.priority_new ? "border-indigo/40" : ""}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-semibold">
                  {v.app_id} · {v.institution} {v.priority_new && <Badge tone="INFO">New institution</Badge>}
                </div>
                <div className="text-sm text-slate-500">
                  {v.status} · eligible {v.days_since_eligible}d · deadline {v.scheduling_deadline}
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => schedule(v.id)}>
                  Schedule
                </Button>
                <Button size="sm" onClick={() => report(v.id)}>
                  Upload recommendation
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
