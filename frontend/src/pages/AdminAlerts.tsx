import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useUi } from "@/store/ui";
import { useState } from "react";

type Rule = { id: number; code: string; entity_type: string; offset_days: number; severity: string; is_active: boolean };
type Tpl = { id: number; code: string; subject: string; body: string };

export default function AdminAlerts() {
  const toast = useUi((s) => s.toast);
  const rules = useQuery({ queryKey: ["arules"], queryFn: () => api.get<Rule[]>("/api/v1/admin/alert-rules") });
  const tpls = useQuery({ queryKey: ["ntpls"], queryFn: () => api.get<Tpl[]>("/api/v1/admin/notification-templates") });
  const esc = useQuery({ queryKey: ["erules"], queryFn: () => api.get<{ id: number; level: number; threshold_days_overdue: number; escalate_to_role: string }[]>("/api/v1/admin/escalation-rules") });
  const [preview, setPreview] = useState("{institution} due {due_date} ({days_left} days left)");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">Alert rules</h1>
      <Card>
        <h2 className="font-semibold">Template preview</h2>
        <p className="text-xs text-slate-500">Placeholders: {"{institution} {app_id} {due_date} {days_left} {days_overdue} {stage} {officer}"}</p>
        <textarea className="mt-2 w-full rounded-xl border border-line p-2 text-sm" value={preview} onChange={(e) => setPreview(e.target.value)} />
        <p className="mt-2 rounded-xl bg-canvas p-3 text-sm">
          {preview
            .replace("{institution}", "Northern Institute of Applied Sciences")
            .replace("{due_date}", "2026-11-01")
            .replace("{days_left}", "7")
            .replace("{app_id}", "APP-2026-0042")
            .replace("{days_overdue}", "0")
            .replace("{stage}", "Scrutiny")
            .replace("{officer}", "Regional Officer")}
        </p>
      </Card>
      {(rules.data ?? []).map((r) => (
        <Card key={r.id} className="flex items-center justify-between">
          <div>
            <div className="font-medium">{r.code}</div>
            <div className="text-xs text-slate-500">
              {r.entity_type} · offset {r.offset_days} · {r.severity}
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={async () => {
              await api.put(`/api/v1/admin/alert-rules/${r.id}`, { is_active: !r.is_active });
              toast("Rule updated");
              rules.refetch();
            }}
          >
            {r.is_active ? "Disable" : "Enable"}
          </Button>
        </Card>
      ))}
      <h2 className="font-semibold">Escalation ladder</h2>
      {(esc.data ?? []).map((e) => (
        <Card key={e.id}>
          Level {e.level} at +{e.threshold_days_overdue} days → {e.escalate_to_role}
        </Card>
      ))}
      <h2 className="font-semibold">Notification templates</h2>
      {(tpls.data ?? []).map((t) => (
        <Card key={t.id}>
          <div className="font-medium">{t.code}</div>
          <div className="text-sm">{t.subject}</div>
        </Card>
      ))}
    </div>
  );
}
