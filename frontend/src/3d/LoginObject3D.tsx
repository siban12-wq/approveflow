import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float } from "@react-three/drei";
import { Suspense, useRef } from "react";
import * as THREE from "three";
import { useWebGLSupport } from "./useWebGLSupport";
import { Fallback2D } from "./Fallback2D";

function Shield() {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.25;
  });
  return (
    <Float speed={1.4} floatIntensity={0.4}>
      <group ref={ref}>
        <mesh>
          <cylinderGeometry args={[1.05, 1.15, 0.12, 6]} />
          <meshPhysicalMaterial transmission={0.85} thickness={0.4} roughness={0.12} color="#ffffff" ior={1.3} />
        </mesh>
        <mesh position={[0, 0, 0.08]}>
          <boxGeometry args={[0.7, 0.9, 0.04]} />
          <meshStandardMaterial color="#f8fafc" />
        </mesh>
      </group>
    </Float>
  );
}

export default function LoginObject3D({ forceFallback = false }: { forceFallback?: boolean }) {
  const { ok } = useWebGLSupport(forceFallback);
  if (!ok) return <Fallback2D variant="login" />;
  return (
    <div className="h-64 w-full max-w-sm" aria-hidden="true">
      <Suspense fallback={<Fallback2D variant="login" />}>
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 4.2], fov: 40 }}>
          <ambientLight intensity={0.8} />
          <directionalLight position={[2, 3, 2]} />
          <Environment preset="studio" />
          <Shield />
        </Canvas>
      </Suspense>
    </div>
  );
}
