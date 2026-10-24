import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { Suspense } from "react";
import { useWebGLSupport } from "./useWebGLSupport";
import { Fallback2D } from "./Fallback2D";

export type RegionDatum = { id: number; code: string; name: string; pending: number; overdue: number };

const LAYOUT: [number, number][] = [
  [0, 1.4],
  [-1.6, 0.4],
  [1.6, 0.4],
  [-1.2, -1.1],
  [1.2, -1.1],
  [-2.6, -0.5],
  [2.6, -0.5],
];

export default function RegionTiles3D({
  data,
  onSelect,
  forceFallback = false,
}: {
  data: RegionDatum[];
  onSelect: (id: number) => void;
  forceFallback?: boolean;
}) {
  const { ok } = useWebGLSupport(forceFallback);
  if (!ok) return <Fallback2D variant="regions" />;
  const max = Math.max(1, ...data.map((d) => d.pending));
  return (
    <div className="h-72 w-full" aria-hidden="true">
      <Suspense fallback={<Fallback2D variant="regions" />}>
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 5, 7], fov: 42 }}>
          <ambientLight intensity={0.85} />
          <directionalLight position={[4, 8, 3]} intensity={1} />
          {data.slice(0, 7).map((r, i) => {
            const h = 0.3 + (r.pending / max) * 1.6;
            const density = r.pending ? r.overdue / r.pending : 0;
            const top = density > 0.25 ? "#ef4444" : density > 0.1 ? "#f59e0b" : "#10b981";
            const [x, z] = LAYOUT[i];
            return (
              <group key={r.id} position={[x, h / 2, z]} onClick={() => onSelect(r.id)}>
                <mesh>
                  <boxGeometry args={[1.3, h, 1.1]} />
                  <meshPhysicalMaterial color="#ffffff" roughness={0.25} />
                </mesh>
                <mesh position={[0, h / 2 + 0.03, 0]}>
                  <boxGeometry args={[1.3, 0.06, 1.1]} />
                  <meshStandardMaterial color={top} />
                </mesh>
                <Html position={[0, h / 2 + 0.35, 0]} center>
                  <div className="rounded-lg bg-white/90 px-2 py-1 text-[10px] shadow-card">
                    {r.name}
                    <div>
                      {r.pending} pending · {r.overdue} overdue
                    </div>
                  </div>
                </Html>
              </group>
            );
          })}
          <OrbitControls enablePan={false} />
        </Canvas>
      </Suspense>
    </div>
  );
}
