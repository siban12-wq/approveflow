import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Safeguard } from "@/components/layout/Safeguard";
import { Fallback2D } from "@/3d/Fallback2D";

const HeroScene = lazy(() => import("@/3d/HeroScene"));

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-canvas">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <strong className="text-lg">AICTE ApproveFlow</strong>
        <Link to="/login">
          <Button size="sm">Login</Button>
        </Link>
      </header>
      <section className="relative mx-auto max-w-6xl px-6">
        <div className="pointer-events-none absolute inset-x-0 top-16 z-10 text-center">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Simulated demo · Human oversight required</p>
          <h1 className="mt-3 font-extrabold leading-tight text-4xl md:text-6xl">
            Every approval. <span className="gradient-text">On time. On record.</span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-slate-600">
            Route scrutiny, EVC and SAC/SHC work, track undertakings and leases, and escalate overdue files — without ever auto-approving an application.
          </p>
          <div className="pointer-events-auto mt-6 flex justify-center gap-3">
            <Link to="/login">
              <Button>Login</Button>
            </Link>
            <Link to="/login">
              <Button variant="outline">Watch Demo Tour</Button>
            </Link>
          </div>
        </div>
        <Suspense fallback={<Fallback2D />}>
          <HeroScene />
        </Suspense>
      </section>
      <section id="stats" className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-6 py-10 md:grid-cols-3">
        {[
          ["150+", "Applications processed in the demo ledger"],
          ["Deadlines tracked", "SLA, EVC, undertakings and lease expiry"],
          ["Alerts sent", "Idempotent reminders — never a decision"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-card border border-line bg-white p-5 shadow-card">
            <div className="text-2xl font-extrabold">{k}</div>
            <p className="text-sm text-slate-500">{v}</p>
          </div>
        ))}
      </section>
      <section id="Scrutiny" className="mx-auto max-w-6xl px-6 pb-16">
        <Safeguard />
      </section>
    </div>
  );
}
