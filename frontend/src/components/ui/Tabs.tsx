import { cn } from "@/lib/cn";

export function Tabs({
  tabs,
  value,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-2xl bg-canvas p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => onChange(t.id)}
          className={cn(
            "rounded-xl px-3 py-1.5 text-sm",
            value === t.id ? "bg-white font-semibold shadow-sm" : "text-slate-500",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
