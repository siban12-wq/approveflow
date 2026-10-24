import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { api } from "@/lib/api";
import { Tabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StageStepper } from "@/components/workflow/StageStepper";
import { ActionBar } from "@/components/workflow/ActionBar";
import { EscalationTimeline } from "@/components/EscalationTimeline";

type Detail = {
  id: number;
  app_id: string;
  institution: string;
  region: string;
  application_type: string;
  current_stage: string;
  current_stage_name: string;
  status: string;
  sla_status: string;
  sla_due_at: string | null;
  assigned_officer: string | null;
  stages: { id: number; code: string; name: string }[];
  allowed_actions: (string | { code: string; label?: string })[];
  history: { from_stage: string; to_stage: string; action: string; actor_role: string; reason: string | null; created_at: string }[];
  deficiencies: { id: number; description: string; status: string; response_text: string | null }[];
  case_summary: { label: string; text: string };
  decision: string | null;
};

export default function ApplicationDetail() {
  const { id } = useParams();
  const [tab, setTab] = useState("overview");
  const q = useQuery({
    queryKey: ["app", id],
    queryFn: () => api.get<Detail>(`/api/v1/applications/${id}`),
  });
  const a = q.data;
  if (!a) return <div className="h-40 animate-pulse rounded-card bg-white" />;
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs text-slate-500">Simulated demo data</p>
        <h1 className="text-2xl font-extrabold">{a.app_id}</h1>
        <p className="text-slate-600">
          {a.institution} · {a.region} · {a.application_type}
        </p>
        <div className="mt-2 flex gap-2">
          <Badge tone={a.sla_status}>{a.sla_status}</Badge>
          <Badge tone={a.status}>{a.status}</Badge>
        </div>
      </div>
      <ActionBar appId={a.id} actions={a.allowed_actions} onDone={() => q.refetch()} />
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "docs", label: "Documents" },
          { id: "scrutiny", label: "Scrutiny" },
          { id: "history", label: "Stage history" },
          { id: "evc", label: "EVC" },
          { id: "audit", label: "Audit trail" },
          { id: "summary", label: "Case summary" },
        ]}
      />
      {tab === "overview" && (
        <Card>
          <StageStepper stages={a.stages} current={a.current_stage} returned={a.status === "returned"} />
          <p className="mt-4 text-sm">Officer: {a.assigned_officer ?? "Unassigned"}</p>
          <p className="text-sm">SLA due: {a.sla_due_at ?? "—"}</p>
          <div className="mt-4">
            <h3 className="mb-2 font-semibold">Escalation ladder</h3>
            <EscalationTimeline entityType="APPLICATION" entityId={a.id} />
          </div>
        </Card>
      )}
      {tab === "docs" && <Card>Uploaded files are versioned with SHA-256. Preview is available after official verification. PDF/JPG/PNG, max 10MB.</Card>}
      {tab === "scrutiny" && (
        <Card>
          <h3 className="font-semibold">Deficiencies</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {a.deficiencies.map((d) => (
              <li key={d.id} className="rounded-xl border border-line p-3">
                <Badge>{d.status}</Badge>
                <p className="mt-1">{d.description}</p>
                {d.response_text && <p className="text-slate-500">Response: {d.response_text}</p>}
              </li>
            ))}
            {a.deficiencies.length === 0 && <p>No open observations.</p>}
          </ul>
        </Card>
      )}
      {tab === "history" && (
        <Card>
          <ol className="space-y-3">
            {a.history.map((h, i) => (
              <li key={i} className="border-l-2 border-line pl-3 text-sm">
                <div className="font-medium">
                  {h.action}: {h.from_stage ?? "—"} → {h.to_stage}
                </div>
                <div className="text-xs text-slate-500">
                  {h.actor_role} · {h.created_at}
                </div>
                {h.reason && <div className="text-amber-800">Reason: {h.reason}</div>}
              </li>
            ))}
          </ol>
        </Card>
      )}
      {tab === "evc" && <Card>Linked EVC visit details appear in the EVC queue when this path includes an expert visit.</Card>}
      {tab === "audit" && <Card>Every movement is append-only. Open the Audit trail page to export the hash-chained log.</Card>}
      {tab === "summary" && (
        <Card className="print:shadow-none">
          <p className="text-xs uppercase text-amber-700">{a.case_summary.label}</p>
          <p className="mt-2">{a.case_summary.text}</p>
          <p className="mt-4 text-sm font-medium">Recorded decision: {a.decision ?? "not recorded by a competent authority"}</p>
        </Card>
      )}
    </div>
  );
}
