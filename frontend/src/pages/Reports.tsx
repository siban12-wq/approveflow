import { useQuery } from "@tanstack/react-query";
import { api, getToken } from "@/lib/api";
import { DataTable } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function Reports() {
  const q = useQuery({
    queryKey: ["report"],
    queryFn: () => api.get<{ rows: Record<string, string>[] }>("/api/v1/reports/pendency"),
  });
  const rows = q.data?.rows ?? [];
  const byStage: Record<string, number> = {};
  for (const r of rows) byStage[r.stage] = (byStage[r.stage] ?? 0) + 1;

  async function download(kind: "csv" | "pdf") {
    const token = getToken();
    const res = await fetch(`/api/v1/reports/export.${kind}`, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `pendency.${kind}`;
    a.click();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">Reports</h1>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => download("csv")}>
            CSV
          </Button>
          <Button size="sm" onClick={() => download("pdf")}>
            PDF
          </Button>
        </div>
      </div>
      <Card className="print:shadow-none">
        <h2 className="mb-2 font-semibold">Stage-wise ageing snapshot</h2>
        <div className="h-52">
          <ResponsiveContainer>
            <BarChart data={Object.entries(byStage).map(([stage, count]) => ({ stage, count }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="stage" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#14B8A6" radius={8} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <DataTable
        rows={rows as unknown as Record<string, unknown>[]}
        columns={[
          { key: "app_id", header: "App ID" },
          { key: "institution", header: "Institution" },
          { key: "region", header: "Region" },
          { key: "stage", header: "Stage" },
          { key: "sla_status", header: "SLA" },
          { key: "status", header: "Status" },
        ]}
      />
    </div>
  );
}
