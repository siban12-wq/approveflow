import { useNavigate } from "react-router-dom";
import { useUi } from "@/store/ui";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useMemo, useState } from "react";

export function CommandPalette() {
  const open = useUi((s) => s.commandOpen);
  const setCommand = useUi((s) => s.setCommand);
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const apps = useQuery({
    queryKey: ["apps-cmd"],
    queryFn: () => api.get<{ items: { id: number; app_id: string; institution: string }[] }>("/api/v1/applications?page_size=80"),
    enabled: open,
  });
  const hits = useMemo(() => {
    const n = q.toLowerCase();
    return (apps.data?.items ?? []).filter((a) => a.app_id.toLowerCase().includes(n) || a.institution.toLowerCase().includes(n)).slice(0, 8);
  }, [apps.data, q]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] bg-ink/20 p-4 backdrop-blur-sm" onClick={() => setCommand(false)}>
      <div className="glass mx-auto mt-24 max-w-lg rounded-card p-3 shadow-lift" onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Jump to an application or institution"
          className="w-full rounded-xl border border-line px-3 py-2"
        />
        <ul className="mt-2">
          {hits.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                className="w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-canvas"
                onClick={() => {
                  nav(`/app/applications/${h.id}`);
                  setCommand(false);
                }}
              >
                {h.app_id} · {h.institution}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
