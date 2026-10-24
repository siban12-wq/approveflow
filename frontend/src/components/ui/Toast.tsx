import { useUi } from "@/store/ui";
import { cn } from "@/lib/cn";

export function Toasts() {
  const { toasts, dismiss } = useUi();
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[70] flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => dismiss(t.id)}
          className={cn(
            "pointer-events-auto rounded-2xl border border-line bg-white/90 p-3 text-left text-sm shadow-card backdrop-blur",
            t.tone === "err" && "border-rose-200",
            t.tone === "warn" && "border-amber-200",
          )}
        >
          {t.title}
        </button>
      ))}
    </div>
  );
}
