import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { Suspense, useState } from "react";
import { useWebGLSupport } from "./useWebGLSupport";
import { Fallback2D } from "./Fallback2D";

export type PipelineStage = { code: string; name: string; count: number; health: string };

function Node({
  stage,
  index,
  pulse,
  onSelect,
}: {
  stage: PipelineStage;
  index: number;
  pulse?: string | null;
  onSelect: (code: string) => void;
}) {
  const color = stage.health === "overdue" ? "#ef4444" : stage.health === "approaching" ? "#f59e0b" : "#10b981";
  const scale = pulse === stage.code ? 1.15 : 1;
  return (
    <group position={[index * 2.2 - 3.3, 0, 0]} scale={scale}>
      <mesh
        onClick={() => onSelect(stage.code)}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[0.55, 32, 32]} />
        <meshPhysicalMaterial color="#ffffff" roughness={0.18} metalness={0.05} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <torusGeometry args={[0.62, 0.035, 12, 40]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.45} />
      </mesh>
      {index < 3 && (
        <mesh position={[1.1, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.03, 0.03, 1.1, 12]} />
          <meshStandardMaterial color="#e2e8f0" />
        </mesh>
      )}
      <Html position={[0, 1.05, 0]} center>
        <div className="rounded-xl border border-line bg-white/90 px-2 py-1 text-center text-xs shadow-card backdrop-blur">
          <div className="font-semibold">{stage.name}</div>
          <div>{stage.count} apps</div>
        </div>
      </Html>
    </group>
  );
}

export default function StagePipeline3D({
  stages,
  onSelect,
  pulse,
  forceFallback = false,
}: {
  stages: PipelineStage[];
  onSelect: (code: string) => void;
  pulse?: string | null;
  forceFallback?: boolean;
}) {
  const { ok } = useWebGLSupport(forceFallback);
  const [hover, setHover] = useState<string | null>(null);
  if (!ok) return <Fallback2D variant="pipeline" />;
  return (
    <div className="h-64 w-full" aria-hidden="true">
      <Suspense fallback={<Fallback2D variant="pipeline" />}>
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 2.4, 7.2], fov: 40 }}>
          <ambientLight intensity={0.8} />
          <directionalLight position={[3, 5, 4]} intensity={1} />
          <group rotation={[-0.35, 0.15, 0]}>
            {stages.map((s, i) => (
              <group key={s.code}>
                {i < stages.length - 1 && (
                  <mesh position={[i * 2.2 - 3.3 + 1.1, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
                    <cylinderGeometry args={[0.035, 0.035, 1.1, 12]} />
                    <meshStandardMaterial color="#e2e8f0" />
                  </mesh>
                )}
                <Node stage={s} index={i} pulse={pulse} onSelect={(c) => { onSelect(c); setHover(c); }} />
              </group>
            ))}
          </group>
          <OrbitControls enablePan={false} maxPolarAngle={1.3} minPolarAngle={0.7} />
        </Canvas>
      </Suspense>
      <p className="sr-only">Stage pipeline. Hovered {hover ?? "none"}.</p>
    </div>
  );
}
