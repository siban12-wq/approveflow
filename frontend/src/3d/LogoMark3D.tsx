import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float, useTexture } from "@react-three/drei";
import { Suspense, useRef } from "react";
import * as THREE from "three";
import { useWebGLSupport } from "./useWebGLSupport";
import { Fallback2D } from "./Fallback2D";

function Emblem() {
  const group = useRef<THREE.Group>(null);
  const texture = useTexture(`${import.meta.env.BASE_URL}logo.png`);
  texture.colorSpace = THREE.SRGBColorSpace;
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.18;
  });
  return (
    <Float speed={1.1} floatIntensity={0.28} rotationIntensity={0.08}>
      <group ref={group}>
        <mesh rotation={[0, 0, 0]} position={[0, 0, -0.04]}>
          <boxGeometry args={[2.35, 1.7, 0.08]} />
          <meshPhysicalMaterial
            color="#0B1B3A"
            roughness={0.18}
            metalness={0.35}
            clearcoat={0.6}
            transmission={0.08}
          />
        </mesh>
        <mesh position={[0, 0.05, 0.06]}>
          <planeGeometry args={[2.1, 1.45]} />
          <meshBasicMaterial map={texture} transparent />
        </mesh>
        <mesh position={[0, -0.95, 0]}>
          <boxGeometry args={[1.6, 0.04, 0.4]} />
          <meshStandardMaterial color="#1d4ed8" emissive="#38bdf8" emissiveIntensity={0.25} />
        </mesh>
      </group>
    </Float>
  );
}

export default function LogoMark3D({ forceFallback = false }: { forceFallback?: boolean }) {
  const { ok } = useWebGLSupport(forceFallback);
  if (!ok) {
    return (
      <div className="flex h-64 w-full max-w-md items-center justify-center">
        <img src={`${import.meta.env.BASE_URL}logo.png`} alt="ApproveFlow" className="h-48 w-auto drop-shadow-2xl" />
      </div>
    );
  }
  return (
    <div className="h-72 w-full max-w-lg" aria-hidden="true">
      <Suspense fallback={<Fallback2D variant="login" />}>
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0.15, 4.4], fov: 38 }} gl={{ antialias: true, alpha: true }}>
          <color attach="background" args={["#06122c"]} />
          <ambientLight intensity={0.7} />
          <spotLight position={[3, 4, 4]} intensity={18} angle={0.4} color="#93c5fd" />
          <directionalLight position={[-2, 2, 3]} intensity={1.1} />
          <Environment preset="city" />
          <Emblem />
        </Canvas>
      </Suspense>
    </div>
  );
}
