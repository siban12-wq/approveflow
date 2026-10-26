import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";
import {
  Clock,
  Building,
  Cpu,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Calendar,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Safeguard } from "@/components/layout/Safeguard";
import { Fallback2D } from "@/3d/Fallback2D";

const HeroScene = lazy(() => import("@/3d/HeroScene"));

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white via-canvas to-slate-100/50 text-ink">
      {/* Navigation Header */}
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[#0B1B3A] to-[#1D4ED8] text-white shadow-md font-black">
            AF
          </div>
          <div>
            <strong className="text-lg font-black text-ink block leading-tight">AICTE ApproveFlow</strong>
            <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">Regulation Bureau Prototype</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/login">
            <Button variant="ghost" size="sm">Sign In</Button>
          </Link>
          <Link to="/signup">
            <Button size="sm">Institution Registration</Button>
          </Link>
        </div>
      </header>

      {/* Hero Section with Interactive 3D Hub */}
      <section className="relative mx-auto max-w-7xl px-6 pt-4">
        <div className="text-center max-w-3xl mx-auto mb-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary mb-3">
            <Sparkles className="h-3.5 w-3.5" />
            AICTE Regulation Bureau Automated Prototype
          </div>
          <h1 className="font-extrabold leading-tight text-4xl md:text-6xl tracking-tight">
            Every statutory approval. <br />
            <span className="bg-gradient-to-r from-primary via-indigo-600 to-cyan-500 bg-clip-text text-transparent">
              On time. On record. Governed.
            </span>
          </h1>
          <p className="mt-4 text-base text-slate-600 leading-relaxed">
            Unified working-day statutory deadlines, PyMuPDF OCR land lease extraction, AI SLA breach-risk intelligence, and strict human authority invariants.
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link to="/login">
              <Button size="md" className="shadow-lg shadow-primary/25 flex items-center gap-2">
                Launch Workbench <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="outline" size="md">Explore Interactive Roles</Button>
            </Link>
          </div>
        </div>

        {/* 3D Scene Viewport */}
        <div className="mt-4 rounded-3xl border border-line bg-gradient-to-b from-white to-canvas/80 p-2 shadow-2xl backdrop-blur-sm overflow-hidden">
          <Suspense fallback={<Fallback2D />}>
            <HeroScene />
          </Suspense>
        </div>
      </section>

      {/* Core Architectural Pillars */}
      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-2xl md:text-3xl font-extrabold text-ink">
            Engineered for Statutory Integrity & Speed
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Four interconnected engines solve pendency bottlenecks while ensuring no automated statutory decisions ever bypass designated AICTE officers.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="rounded-xl bg-blue-50 p-3 w-fit text-primary mb-4 border border-blue-100">
              <Clock className="h-6 w-6" />
            </div>
            <h3 className="text-base font-bold text-ink">Unified Deadline Engine</h3>
            <p className="mt-2 text-xs text-slate-600 leading-relaxed">
              Consolidates Application Stage SLAs, EVC Scheduling, Institutional Undertakings, and Document Expiry into a synchronized, pauseable statutory clock.
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="rounded-xl bg-cyan-50 p-3 w-fit text-cyan-600 mb-4 border border-cyan-100">
              <Calendar className="h-6 w-6" />
            </div>
            <h3 className="text-base font-bold text-ink">Working-Day Calendar Engine</h3>
            <p className="mt-2 text-xs text-slate-600 leading-relaxed">
              Calculates due dates by skipping weekends and Indian Gazetted public holidays. Provides emergency freezes, officer leave compensation, and statutory pause audit logs.
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="rounded-xl bg-indigo-50 p-3 w-fit text-indigo-600 mb-4 border border-indigo-100">
              <Cpu className="h-6 w-6" />
            </div>
            <h3 className="text-base font-bold text-ink">AI SLA Breach Predictor</h3>
            <p className="mt-2 text-xs text-slate-600 leading-relaxed">
              HistGradientBoosting pipeline trained on 15,000 synthetic records (ROC-AUC: 0.817) flags high-risk applications early with top contributing factors.
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="rounded-xl bg-emerald-50 p-3 w-fit text-emerald-600 mb-4 border border-emerald-100">
              <Building className="h-6 w-6" />
            </div>
            <h3 className="text-base font-bold text-ink">PyMuPDF OCR + Human Review</h3>
            <p className="mt-2 text-xs text-slate-600 leading-relaxed">
              Automated extraction of land lease commencement, expiry, registered premises, and renewal clauses paired with mandatory Human-in-the-Loop officer confirmation.
            </p>
          </div>
        </div>
      </section>

      {/* Statutory Safeguard & Governance */}
      <section className="mx-auto max-w-7xl px-6 pb-20">
        <Safeguard />
      </section>
    </div>
  );
}
