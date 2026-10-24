import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { useUi } from "@/store/ui";

type Note = {
  id: number;
  entity_type: string;
  severity: string;
  title: string;
  body: string;
  status: string;
  created_at: string;
};

const TABS = [
  { id: "ALL", label: "All" },
  { id: "APPLICATION", label: "Pending" },
  { id: "EVC", label: "EVC" },
  { id: "UNDERTAKING", label: "Compliance" },
  { id: "DOCUMENT", label: "Document Expiry" },
  { id: "DIGEST", label: "Escalation / digest" },
];

export default function Notifications() {
  const [tab, setTab] = useState("ALL");
  const toast = useUi((s) => s.toast);
  const q = useQuery({
    queryKey: ["notes", tab],
    queryFn: () => api.get<{ unread: number; items: Note[] }>(`/api/v1/notifications${tab === "ALL" ? "" : `?entity_type=${tab}`}`),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">Notification centre</h1>
      <Tabs tabs={TABS} value={tab} onChange={setTab} />
      {(q.data?.items ?? []).map((n) => (
        <div key={n.id} className="rounded-card border border-line bg-white p-4 shadow-card">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Badge tone={n.severity}>{n.severity}</Badge>
              <h3 className="mt-1 font-semibold">{n.title}</h3>
              <p className="text-sm text-slate-600">{n.body}</p>
              <p className="text-xs text-slate-400">{n.created_at}</p>
            </div>
            <div className="flex flex-col gap-2">
              <Button size="sm" variant="outline" onClick={async () => { await api.post(`/api/v1/notifications/${n.id}/read`); q.refetch(); }}>
                Mark read
              </Button>
              <Button size="sm" variant="ghost" onClick={async () => { await api.post(`/api/v1/notifications/${n.id}/acknowledge`); q.refetch(); }}>
                Acknowledge
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={async () => {
                  try {
                    await api.post(`/api/v1/notifications/${n.id}/snooze`, { days: 1, reason: "Reviewed; following up with the institution tomorrow." });
                    q.refetch();
                  } catch (e) {
                    toast((e as Error).message, "err");
                  }
                }}
              >
                Snooze
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
