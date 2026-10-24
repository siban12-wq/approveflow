export function Fallback2D({ variant = "hero" }: { variant?: "hero" | "pipeline" | "regions" | "login" }) {
  if (variant === "pipeline") {
    return (
      <div className="flex gap-3 overflow-x-auto py-4" aria-hidden="false">
        {["Scrutiny", "EVC", "SAC/SHC", "Decision"].map((s) => (
          <div key={s} className="min-w-[140px] rounded-2xl border border-line bg-white p-4 shadow-card">
            <div className="h-3 w-3 rounded-full bg-gradient-to-r from-indigo to-teal" />
            <p className="mt-2 font-semibold">{s}</p>
            <p className="text-xs text-slate-500">Accessible stage summary</p>
          </div>
        ))}
      </div>
    );
  }
  if (variant === "regions") {
    return (
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {["Eastern", "Western", "Northern", "Southern", "Central", "North-Western", "South-Western"].map((r) => (
          <div key={r} className="rounded-xl border border-line bg-white p-3 text-sm shadow-card">
            {r}
          </div>
        ))}
      </div>
    );
  }
  if (variant === "login") {
    return (
      <div className="mx-auto h-40 w-40 rounded-full border border-line bg-gradient-to-br from-white via-sky/10 to-indigo/10 shadow-card" />
    );
  }
  return (
    <div className="relative h-[420px] overflow-hidden rounded-card bg-gradient-to-b from-white to-canvas">
      <div className="absolute inset-0">
        {["Scrutiny", "EVC", "SAC/SHC", "Lease"].map((label, i) => (
          <div
            key={label}
            className="absolute h-28 w-40 rounded-2xl border border-white/80 bg-white/70 shadow-card backdrop-blur animate-[float_6s_ease-in-out_infinite]"
            style={{ left: `${12 + i * 18}%`, top: `${20 + (i % 2) * 18}%`, animationDelay: `${i * 0.4}s` }}
          >
            <p className="p-3 text-xs font-semibold text-ink">{label}</p>
          </div>
        ))}
      </div>
      <style>{`@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }`}</style>
    </div>
  );
}
