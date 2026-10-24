import { lazy, Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/store/auth";
import { Fallback2D } from "@/3d/Fallback2D";
import { StageStepper } from "@/components/workflow/StageStepper";

const StagePipeline3D = lazy(() => import("@/3d/StagePipeline3D"));
const RegionTiles3D = lazy(() => import("@/3d/RegionTiles3D"));

type Dash = {
  kpis: Record<string, number>;
  pipeline: { code: string; name: string; count: number; health: string }[];
  regions: { id: number; code: string; name: string; pending: number; overdue: number }[];
  ageing: Record<string, number>;
  stage_pendency: { stage: string; count: number }[];
  bottlenecks: { label: string; avg_days: number; count: number }[];
  workload: { officer: string; count: number }[];
  my_actions: { id: number; app_id: string; title: string; urgency: string }[];
  alerts: { id: number; title: string; severity: string }[];
  monthly: { month: string; intake: number; disposal: number }[];
  role: string;
  safeguard: string;
};

export default function Dashboard() {
  const user = useAuth((s) => s.user)!;
  const nav = useNavigate();
  const [pulse, setPulse] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["dash", user.role], queryFn: () => api.get<Dash>("/api/v1/dashboard") });
  const d = q.data;
  if (!d) return <div className="h-40 animate-pulse rounded-card bg-white" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Workbench</h1>
        <p className="text-sm text-slate-500">{d.safeguard}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <StatCard label="Total applications" value={d.kpis.total} />
        <StatCard label="In scrutiny" value={d.kpis.in_scrutiny} />
        <StatCard label="In EVC" value={d.kpis.in_evc} />
        <StatCard label="Pending SAC/SHC" value={d.kpis.sac_shc} />
        <StatCard label="Approaching deadline" value={d.kpis.approaching} />
        <StatCard label="Overdue" value={d.kpis.overdue} />
        <StatCard label="Escalated" value={d.kpis.escalated} />
        <StatCard label="Compliance due" value={d.kpis.compliance_30} hint="Open undertakings" />
        <StatCard label="Documents expiring" value={d.kpis.docs_60} />
      </div>

      {user.role === "institution_user" && (
        <Card>
          <h2 className="font-semibold">Your application path</h2>
          <p className="mb-3 text-sm text-slate-500">Track status, upcoming deadlines and required actions for your institution only.</p>
          <StageStepper
            stages={[
              { code: "SUBMITTED", name: "Submitted" },
              { code: "SCRUTINY", name: "Scrutiny" },
              { code: "EVC_QUEUE", name: "EVC" },
              { code: "DECISION_PENDING", name: "Decision" },
            ]}
            current="SCRUTINY"
          />
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-semibold">3D stage pipeline</h2>
          <Suspense fallback={<Fallback2D variant="pipeline" />}>
            <StagePipeline3D
              stages={d.pipeline}
              pulse={pulse}
              onSelect={(code) => {
                setPulse(code);
                nav(`/app/applications?stage=${code}`);
              }}
            />
          </Suspense>
          <table className="mt-2 w-full text-sm">
            <tbody>
              {d.pipeline.map((p) => (
                <tr key={p.code}>
                  <td>{p.name}</td>
                  <td>{p.count}</td>
                  <td>
                    <Badge tone={p.health}>{p.health}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card>
          <h2 className="mb-2 font-semibold">Region density</h2>
          <Suspense fallback={<Fallback2D variant="regions" />}>
            <RegionTiles3D data={d.regions} onSelect={() => nav("/app/reports")} />
          </Suspense>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-2 font-semibold">Stage-wise pendency</h3>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={d.stage_pendency}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="stage" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#4F46E5" radius={8} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 font-semibold">Ageing buckets</h3>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={Object.entries(d.ageing).map(([k, v]) => ({ bucket: k, count: v }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bucket" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#38BDF8" radius={8} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 font-semibold">Monthly intake vs disposal</h3>
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={d.monthly ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line dataKey="intake" stroke="#4F46E5" />
                <Line dataKey="disposal" stroke="#14B8A6" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 font-semibold">Region performance</h3>
          <div className="h-56">
            <ResponsiveContainer>
              <RadarChart data={d.regions}>
                <PolarGrid />
                <PolarAngleAxis dataKey="name" />
                <Radar dataKey="pending" stroke="#4F46E5" fill="#4F46E5" fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <h3 className="font-semibold">Bottlenecks</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {d.bottlenecks.map((b) => (
              <li key={b.label} className="flex justify-between">
                <span>{b.label}</span>
                <span>{b.avg_days}d avg · {b.count}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h3 className="font-semibold">My actions today</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {d.my_actions.map((a) => (
              <li key={a.id}>
                <button type="button" className="text-left" onClick={() => nav(`/app/applications/${a.id}`)}>
                  {a.title} <Badge tone={a.urgency}>{a.urgency}</Badge>
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h3 className="font-semibold">Live alert feed</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {d.alerts.map((a) => (
              <li key={a.id}>
                <Badge tone={a.severity}>{a.severity}</Badge> {a.title}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
