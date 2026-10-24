import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { DataTable } from "@/components/ui/DataTable";

export default function Audit() {
  const [q, setQ] = useState("");
  const data = useQuery({
    queryKey: ["audit", q],
    queryFn: () => api.get<{ items: Record<string, unknown>[] }>(`/api/v1/audit${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });
  return (
    <div>
      <h1 className="mb-2 text-2xl font-extrabold">Audit trail</h1>
      <p className="mb-4 text-sm text-slate-500">Append-only. Update and delete endpoints are refused. SYSTEM is the actor for automated alerts.</p>
      <input className="mb-4 rounded-xl border border-line px-3 py-2" placeholder="Search action or entity" value={q} onChange={(e) => setQ(e.target.value)} />
      <DataTable
        rows={data.data?.items ?? []}
        columns={[
          { key: "timestamp", header: "Time" },
          { key: "actor_label", header: "Actor" },
          { key: "actor_role", header: "Role" },
          { key: "action", header: "Action" },
          { key: "entity_type", header: "Entity" },
          { key: "entity_id", header: "ID" },
          { key: "reason", header: "Reason" },
          { key: "row_hash", header: "Hash" },
        ]}
      />
    </div>
  );
}
