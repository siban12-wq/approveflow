import { cn } from "@/lib/cn";

export function StageStepper({
  stages,
  current,
  returned,
}: {
  stages: { code: string; name: string }[];
  current?: string | null;
  returned?: boolean;
}) {
  const idx = stages.findIndex((s) => s.code === current);
  return (
    <ol className="flex flex-wrap gap-2">
      {stages.map((s, i) => {
        const done = idx > i;
        const active = idx === i;
        return (
          <li
            key={s.code}
            className={cn(
              "flex items-center gap-2 rounded-full border px-3 py-1 text-xs",
              done && "border-emerald-200 bg-emerald-50 text-emerald-800",
              active && !returned && "border-indigo/40 bg-indigo/10 font-semibold",
              active && returned && "border-amber-300 bg-amber-50 text-amber-800",
              !done && !active && "border-line text-slate-500",
            )}
          >
            <span className="grid h-5 w-5 place-items-center rounded-full bg-white text-[10px]">{done ? "✓" : i + 1}</span>
            {s.name}
          </li>
        );
      })}
    </ol>
  );
}
