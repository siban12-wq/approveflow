import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function EscalationTimeline({ entityType, entityId }: { entityType: string; entityId: number }) {
  const q = useQuery({
    queryKey: ["esc", entityType, entityId],
    queryFn: () =>
      api.get<{ ladder: { level: number; label: string }[]; events: { level: number; triggered_at: string; resolved_at: string | null }[] }>(
        `/api/v1/notifications/escalations/${entityType}/${entityId}`,
      ),
  });
  const events = q.data?.events ?? [];
  return (
    <ol className="space-y-2">
      {(q.data?.ladder ?? []).map((l) => {
        const ev = events.find((e) => e.level === l.level);
        return (
          <li key={l.level} className="flex items-start gap-3 rounded-xl border border-line bg-white p-3 text-sm">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-canvas text-xs font-bold">L{l.level}</span>
            <div>
              <div className="font-medium">{l.label}</div>
              <div className="text-xs text-slate-500">
                {ev ? `${ev.triggered_at}${ev.resolved_at ? " · resolved" : ""}` : "Not yet reached"}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
