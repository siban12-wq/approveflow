import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useUi } from "@/store/ui";
import { useState } from "react";

type Stage = { id: number; name: string; sla_days: number; allowed_roles: string[]; stage_code: string };
type Tpl = { id: number; code: string; name: string; description: string; stages: Stage[]; version: number };

export default function AdminRules() {
  const toast = useUi((s) => s.toast);
  const q = useQuery({ queryKey: ["tpls"], queryFn: () => api.get<Tpl[]>("/api/v1/admin/workflow-templates") });
  const [draft, setDraft] = useState<Record<number, number>>({});

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">Workflow templates</h1>
      <p className="text-sm text-slate-500">Editable without a code change. Human-only stages never auto-complete a decision.</p>
      {(q.data ?? []).map((t) => (
        <Card key={t.id}>
          <h2 className="font-semibold">
            {t.name} <span className="text-xs text-slate-400">{t.code} v{t.version}</span>
          </h2>
          <p className="text-sm text-slate-500">{t.description}</p>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th>Stage</th>
                <th>SLA days</th>
                <th>Allowed roles</th>
              </tr>
            </thead>
            <tbody>
              {t.stages.map((s) => (
                <tr key={s.id} className="border-t border-line">
                  <td className="py-2">{s.name}</td>
                  <td>
                    <input
                      type="number"
                      className="w-20 rounded-lg border border-line px-2 py-1"
                      defaultValue={s.sla_days}
                      onChange={(e) => setDraft((d) => ({ ...d, [s.id]: Number(e.target.value) }))}
                    />
                  </td>
                  <td className="text-xs">{(s.allowed_roles ?? []).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Button
            className="mt-3"
            size="sm"
            onClick={async () => {
              await api.put(`/api/v1/admin/workflow-templates/${t.id}`, {
                stages: t.stages.map((s) => ({ id: s.id, sla_days: draft[s.id] ?? s.sla_days })),
              });
              toast("Template saved");
              q.refetch();
            }}
          >
            Save SLA
          </Button>
        </Card>
      ))}
    </div>
  );
}
