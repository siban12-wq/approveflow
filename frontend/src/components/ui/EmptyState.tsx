export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-line bg-canvas/60 py-16 text-center">
      <div className="h-16 w-24 rounded-2xl bg-gradient-to-br from-indigo/20 via-sky/20 to-teal/20" />
      <p className="mt-4 font-semibold">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
    </div>
  );
}
