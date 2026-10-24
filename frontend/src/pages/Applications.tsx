import { useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
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
  last_updated_at: string;
};

export default function Applications() {
  const [params] = useSearchParams();
  const stage = params.get("stage") ?? "";
  const nav = useNavigate();
  const user = useAuth((s) => s.user)!;
  const q = useQuery({
    queryKey: ["apps", stage],
    queryFn: () => api.get<{ items: AppRow[]; total: number }>(`/api/v1/applications?page_size=80${stage ? `&stage=${stage}` : ""}`),
  });
  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">Applications</h1>
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
          { key: "age_days", header: "Age" },
          { key: "sla_status", header: "SLA", render: (r) => <Badge tone={String(r.sla_status)}>{String(r.sla_status)}</Badge> },
          { key: "last_updated_at", header: "Updated" },
        ]}
        onRow={(r) => nav(`/app/applications/${r.id}`)}
      />
    </div>
  );
}
