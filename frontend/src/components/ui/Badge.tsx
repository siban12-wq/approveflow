import { cn } from "@/lib/cn";

const tones: Record<string, string> = {
  on_track: "bg-emerald-50 text-emerald-700",
  approaching: "bg-amber-50 text-amber-700",
  overdue: "bg-rose-50 text-rose-700",
  escalated: "bg-violet-50 text-violet-700",
  closed: "bg-slate-100 text-slate-600",
  INFO: "bg-sky-50 text-sky-700",
  WARNING: "bg-amber-50 text-amber-700",
  CRITICAL: "bg-rose-50 text-rose-700",
  open: "bg-indigo-50 text-indigo-700",
  returned: "bg-amber-50 text-amber-800",
  decided: "bg-teal-50 text-teal-700",
};

export function Badge({ children, tone = "closed" }: { children: React.ReactNode; tone?: string }) {
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize", tones[tone] || tones.closed)}>
      {children}
    </span>
  );
}
