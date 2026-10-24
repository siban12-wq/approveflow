export function Safeguard({ compact }: { compact?: boolean }) {
  return (
    <p className={compact ? "text-xs text-slate-500" : "rounded-2xl border border-line bg-canvas px-4 py-3 text-sm text-slate-600"}>
      Automated alerts and recommendations support, but do not replace, decisions of the competent authority.
    </p>
  );
}
