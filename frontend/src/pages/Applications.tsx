import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Info,
  X,
  ArrowRight,
  TrendingUp,
  Cpu,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/store/auth";

type AppRow = {
  id: number;
  app_id: string;
  institution: string;
  region: string;
  application_type: string;
  current_stage_name: string;
  assigned_officer: string | null;
  age_days: number;
  sla_status: string;
  risk_level?: string;
  risk_score?: number;
  last_updated_at: string;
};

type AppRiskDetails = {
  application_id: number;
  breach_probability: number;
  risk_level: string;
  top_contributing_factors: string[];
  explanation: string;
  mitigation_actions: string[];
  model_version: string;
  safeguard: string;
};

export default function Applications() {
  const [params] = useSearchParams();
  const stage = params.get("stage") ?? "";
  const nav = useNavigate();
  const user = useAuth((s) => s.user)!;

  const [selectedRiskApp, setSelectedRiskApp] = useState<AppRow | null>(null);

  const q = useQuery({
    queryKey: ["apps", stage],
    queryFn: () =>
      api.get<{ items: AppRow[]; total: number }>(
        `/api/v1/applications?page_size=80${stage ? `&stage=${stage}` : ""}`
      ),
  });

  const riskQuery = useQuery({
    queryKey: ["app-risk", selectedRiskApp?.id],
    queryFn: () => api.get<AppRiskDetails>(`/api/v1/ml/applications/${selectedRiskApp?.id}`),
    enabled: !!selectedRiskApp,
  });

  const renderRiskBadge = (row: AppRow) => {
    const level = (row.risk_level ?? "low").toLowerCase();
    const score = row.risk_score ? (row.risk_score * 100).toFixed(0) : "18";

    let bg = "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100";
    let icon = <CheckCircle2 className="h-3 w-3 text-emerald-600" />;
    let label = "Low Risk";

    if (level === "high") {
      bg = "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100";
      icon = <ShieldAlert className="h-3 w-3 text-rose-600" />;
      label = "High Risk";
    } else if (level === "moderate") {
      bg = "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100";
      icon = <AlertTriangle className="h-3 w-3 text-amber-600" />;
      label = "Moderate Risk";
    }

    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setSelectedRiskApp(row);
        }}
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors ${bg}`}
      >
        {icon}
        <span>{label}</span>
        <span className="text-[10px] opacity-75 font-mono">({score}%)</span>
      </button>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-ink">Applications & Compliance Pipeline</h1>
          <p className="text-xs text-slate-500">
            Real-time stage tracking with ML-powered SLA breach prediction and statutory governance.
          </p>
        </div>
        {user.role === "institution_user" && (
          <Button onClick={() => nav("/app/applications/new")}>Submit application</Button>
        )}
      </div>

      <DataTable
        rows={(q.data?.items ?? []) as unknown as Record<string, unknown>[]}
        columns={[
          { key: "app_id", header: "App ID" },
          { key: "institution", header: "Institution" },
          { key: "region", header: "Region" },
          { key: "application_type", header: "Type" },
          { key: "current_stage_name", header: "Stage" },
          { key: "assigned_officer", header: "Officer" },
          { key: "age_days", header: "Age (Days)" },
          {
            key: "sla_status",
            header: "SLA Status",
            render: (r) => <Badge tone={String(r.sla_status)}>{String(r.sla_status)}</Badge>,
          },
          {
            key: "risk_level",
            header: "AI Breach Risk",
            render: (r) => renderRiskBadge(r as unknown as AppRow),
          },
          { key: "last_updated_at", header: "Updated" },
        ]}
        onRow={(r) => nav(`/app/applications/${r.id}`)}
      />

      {/* AI Risk Drawer / Modal */}
      {selectedRiskApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl border border-line">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-indigo-50 p-1.5 border border-indigo-100">
                  <Cpu className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-ink">AI Breach-Risk Intelligence</h3>
                  <p className="text-xs text-slate-400 font-mono">{selectedRiskApp.app_id} · {selectedRiskApp.institution}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedRiskApp(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-canvas hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {riskQuery.isLoading ? (
              <div className="py-12 text-center text-sm text-slate-400 animate-pulse">
                Evaluating HistGradientBoosting decision paths…
              </div>
            ) : riskQuery.data ? (
              <div className="mt-4 space-y-4">
                {/* Risk Gauge Header */}
                <div className="rounded-xl border border-line bg-canvas p-4 flex items-center justify-between">
                  <div>
                    <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block">
                      Breach Probability
                    </span>
                    <div className="text-3xl font-black text-ink mt-0.5">
                      {(riskQuery.data.breach_probability * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold block">
                      Assessed Tier
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 font-bold text-sm px-2.5 py-1 rounded-lg mt-1 ${
                        riskQuery.data.risk_level === "HIGH"
                          ? "bg-rose-100 text-rose-800"
                          : riskQuery.data.risk_level === "MODERATE"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {riskQuery.data.risk_level} RISK
                    </span>
                  </div>
                </div>

                {/* Top Contributing Factors */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5 mb-2">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    Key Decision Factors
                  </h4>
                  <ul className="space-y-1.5">
                    {riskQuery.data.top_contributing_factors.map((factor, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-slate-700 bg-slate-50 p-2 rounded-lg border border-line">
                        <span className="text-primary font-bold">#{idx + 1}</span>
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Recommended Mitigations */}
                {riskQuery.data.mitigation_actions && riskQuery.data.mitigation_actions.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5 mb-2">
                      <Layers className="h-4 w-4 text-emerald-600" />
                      Recommended Officer Mitigations
                    </h4>
                    <div className="space-y-1.5">
                      {riskQuery.data.mitigation_actions.map((act, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs font-medium text-slate-700 bg-emerald-50/60 p-2 rounded-lg border border-emerald-100">
                          <ArrowRight className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                          <span>{act}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Statutory Invariant Safeguard Notice */}
                <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900 flex items-start gap-2">
                  <Info className="h-4 w-4 text-amber-700 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-semibold block">AICTE Statutory Safeguard</span>
                    <span>
                      {riskQuery.data.safeguard ||
                        "This prediction is an early-warning advisory indicator to assist officers. It does not automate any statutory approval or rejection decision."}
                    </span>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-2 text-[11px] text-slate-400 border-t border-line">
                  <span>Model: {riskQuery.data.model_version}</span>
                  <Button size="sm" onClick={() => nav(`/app/applications/${selectedRiskApp.id}`)}>
                    Open Full Case File
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
