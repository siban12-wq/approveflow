import { lazy, Suspense, useState } from "react";
import { Fallback2D } from "@/3d/Fallback2D";
import type { Quality } from "@/3d/useWebGLSupport";

const HeroScene = lazy(() => import("@/3d/HeroScene"));
const StagePipeline3D = lazy(() => import("@/3d/StagePipeline3D"));
const RegionTiles3D = lazy(() => import("@/3d/RegionTiles3D"));
const LoginObject3D = lazy(() => import("@/3d/LoginObject3D"));

export default function Dev3D() {
  const [quality, setQuality] = useState<Quality>("high");
  const [fallback, setFallback] = useState(false);
  return (
    <div className="space-y-6 bg-white p-6">
      <h1 className="text-2xl font-extrabold">3D sandbox</h1>
      <label className="mr-4 text-sm">
        Quality
        <select className="ml-2 rounded-lg border border-line p-1" value={quality} onChange={(e) => setQuality(e.target.value as Quality)}>
          <option>low</option>
          <option>medium</option>
          <option>high</option>
        </select>
      </label>
      <label className="text-sm">
        <input type="checkbox" className="mr-2" checked={fallback} onChange={(e) => setFallback(e.target.checked)} />
        Force CSS fallback
      </label>
      <p className="text-xs text-slate-500">Quality hint: {quality}. Canvases stay under 1.5 DPR and pause off-screen in production pages.</p>
      <Suspense fallback={<Fallback2D />}>
        <HeroScene forceFallback={fallback} />
        <StagePipeline3D
          forceFallback={fallback}
          stages={[
            { code: "SCRUTINY", name: "Scrutiny", count: 12, health: "on_track" },
            { code: "EVC_QUEUE", name: "EVC", count: 8, health: "approaching" },
            { code: "SAC_SHC", name: "SAC/SHC", count: 3, health: "overdue" },
            { code: "DECISION_PENDING", name: "Decision", count: 5, health: "on_track" },
          ]}
          onSelect={() => undefined}
        />
        <RegionTiles3D
          forceFallback={fallback}
          data={[
            { id: 1, code: "ER", name: "Eastern", pending: 10, overdue: 2 },
            { id: 2, code: "WR", name: "Western", pending: 6, overdue: 0 },
            { id: 3, code: "NR", name: "Northern", pending: 14, overdue: 4 },
            { id: 4, code: "SR", name: "Southern", pending: 7, overdue: 1 },
            { id: 5, code: "CR", name: "Central", pending: 5, overdue: 1 },
            { id: 6, code: "NWR", name: "North-Western", pending: 4, overdue: 0 },
            { id: 7, code: "SWR", name: "South-Western", pending: 9, overdue: 3 },
          ]}
          onSelect={() => undefined}
        />
        <LoginObject3D forceFallback={fallback} />
      </Suspense>
    </div>
  );
}
