import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, Environment, Float, Sparkles, Text } from "@react-three/drei";
import { Suspense, useMemo, useRef } from "react";
import * as THREE from "three";
import { damp3 } from "maath/easing";
import { useWebGLSupport } from "./useWebGLSupport";
import { Fallback2D } from "./Fallback2D";
import { usePauseWhenHidden } from "./usePauseWhenHidden";

const CARDS = ["Scrutiny", "EVC", "SAC/SHC", "Lease", "Undertaking", "Approved by Authority", "Audit"];

function GlassCard({ label, position }: { label: string; position: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  return (
    <Float speed={1.2} rotationIntensity={0.15} floatIntensity={0.6}>
      <mesh ref={ref} position={position} castShadow>
        <boxGeometry args={[1.35, 1.85, 0.06]} />
        <meshPhysicalMaterial
          transmission={0.9}
          thickness={0.5}
          roughness={0.1}
          ior={1.3}
          color="#ffffff"
          transparent
          opacity={0.95}
        />
        <Text position={[0, 0, 0.05]} fontSize={0.12} color="#0B1B3A" maxWidth={1.1} textAlign="center">
          {label}
        </Text>
      </mesh>
    </Float>
  );
}

function PipelineRing() {
  const group = useRef<THREE.Group>(null);
  const nodes = useMemo(() => {
    const colors = ["#4F46E5", "#38BDF8", "#14B8A6"];
    return new Array(9).fill(0).map((_, i) => ({
      color: colors[i % 3],
      t: i / 9,
    }));
  }, []);
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.15;
  });
  return (
    <group ref={group} rotation={[0.4, 0, 0]}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.4, 0.035, 16, 80]} />
        <meshPhysicalMaterial color="#eef2ff" roughness={0.2} metalness={0.1} />
      </mesh>
      {nodes.map((n, i) => {
        const a = n.t * Math.PI * 2;
        return (
          <mesh key={i} position={[Math.cos(a) * 2.4, 0, Math.sin(a) * 2.4]}>
            <sphereGeometry args={[0.07, 16, 16]} />
            <meshStandardMaterial color={n.color} emissive={n.color} emissiveIntensity={0.6} />
          </mesh>
        );
      })}
    </group>
  );
}

function ParallaxRig({ paused }: { paused: boolean }) {
  const { camera } = useThree();
  useFrame((state, dt) => {
    if (paused) return;
    const t = 1 - Math.min(1, window.scrollY / 900);
    damp3(camera.position, [state.pointer.x * 0.6, 1.2 + state.pointer.y * 0.3, 6.2 + (1 - t) * 2.4], 0.25, dt);
    camera.lookAt(0, 0.2, 0);
  });
  return null;
}

function Scene({ paused }: { paused: boolean }) {
  return (
    <>
      <color attach="background" args={["#ffffff"]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[4, 6, 4]} intensity={1.1} />
      <Environment preset="studio" />
      <ParallaxRig paused={paused} />
      {CARDS.map((label, i) => {
        const a = (i / CARDS.length) * Math.PI * 2;
        return <GlassCard key={label} label={label} position={[Math.cos(a) * 1.6, Math.sin(a * 1.3) * 0.45, Math.sin(a) * 1.2]} />;
      })}
      <PipelineRing />
      <Sparkles count={120} scale={8} size={2} speed={0.3} color="#dbeafe" />
      <ContactShadows opacity={0.25} blur={2.5} position={[0, -1.6, 0]} />
    </>
  );
}

export default function HeroScene({ forceFallback = false }: { forceFallback?: boolean }) {
  const { ok, quality } = useWebGLSupport(forceFallback);
  const { ref, paused } = usePauseWhenHidden();
  const dpr: [number, number] = quality === "high" ? [1, 1.5] : [1, 1];
  if (!ok) return <Fallback2D />;
  return (
    <div ref={ref} className="h-[520px] w-full" aria-hidden="true">
      <Suspense fallback={<Fallback2D />}>
        <Canvas
          dpr={dpr}
          frameloop={paused ? "demand" : "always"}
          camera={{ position: [0, 1.2, 6.2], fov: 42 }}
          gl={{ antialias: true, alpha: true }}
        >
          <Scene paused={paused} />
        </Canvas>
      </Suspense>
    </div>
  );
}
