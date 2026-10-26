import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, Environment, Float, Sparkles, Text, Html } from "@react-three/drei";
import { Suspense, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { damp3 } from "maath/easing";
import { useWebGLSupport } from "./useWebGLSupport";
import { Fallback2D } from "./Fallback2D";
import { usePauseWhenHidden } from "./usePauseWhenHidden";

// Key connected statutory workflow nodes
const WORKFLOW_NODES = [
  { id: "institutions", label: "Institutions\n(Colleges)", color: "#38BDF8", pos: [-2.6, 0.4, 0.2] as const },
  { id: "regional", label: "Regional\nOffices", color: "#60A5FA", pos: [-1.8, 1.4, -0.6] as const },
  { id: "scrutiny", label: "Scrutiny\nCommittee", color: "#818CF8", pos: [-0.6, 1.8, -0.9] as const },
  { id: "evc", label: "EVC Experts\n(GPS Tagged)", color: "#34D399", pos: [0.8, 1.7, -0.8] as const },
  { id: "sac_shc", label: "SAC / SHC\nCommittees", color: "#F59E0B", pos: [1.9, 1.2, -0.5] as const },
  { id: "bureau", label: "Approval\nBureau", color: "#6366F1", pos: [2.5, 0.3, 0.2] as const },
  { id: "authority", label: "Competent\nAuthority", color: "#10B981", pos: [0, -1.3, 0.8] as const },
];

// Floating live-style indicator panels around the hub
const FLOATING_INDICATORS = [
  {
    title: "Unified Deadline Engine",
    subtitle: "Working-Day SLA Math",
    metric: "15d Target",
    badge: "Active",
    badgeColor: "bg-emerald-500",
    pos: [-2.2, -0.8, 0.9] as const,
  },
  {
    title: "AI Risk Predictor",
    subtitle: "HistGradientBoosting v1.0",
    metric: "81.7% AUC",
    badge: "Calibrated",
    badgeColor: "bg-blue-500",
    pos: [2.2, -0.7, 0.9] as const,
  },
  {
    title: "Lease Document Validity",
    subtitle: "PyMuPDF OCR + Human Sign-off",
    metric: "30-Yr Horizon",
    badge: "Verified",
    badgeColor: "bg-cyan-500",
    pos: [0, 2.1, 0.4] as const,
  },
];

function CentralHub() {
  const meshRef = useRef<THREE.Group>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((_, dt) => {
    if (meshRef.current) meshRef.current.rotation.y += dt * 0.12;
    if (ringRef.current) ringRef.current.rotation.z -= dt * 0.18;
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Central Rotating Institutional Core */}
      <group ref={meshRef}>
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[0.75, 0.95, 0.4, 8]} />
          <meshPhysicalMaterial
            color="#0B1B3A"
            metalness={0.7}
            roughness={0.2}
            clearcoat={0.8}
            reflectivity={0.9}
          />
        </mesh>
        <mesh position={[0, 0.22, 0]}>
          <cylinderGeometry args={[0.5, 0.5, 0.08, 32]} />
          <meshStandardMaterial color="#1D4ED8" emissive="#38BDF8" emissiveIntensity={0.35} />
        </mesh>
        {/* Greek institutional pillars accent */}
        {[-0.25, 0, 0.25].map((x, i) => (
          <mesh key={i} position={[x, 0.4, 0]}>
            <cylinderGeometry args={[0.04, 0.04, 0.28, 12]} />
            <meshStandardMaterial color="#E2E8F0" metalness={0.5} roughness={0.2} />
          </mesh>
        ))}
        {/* Pediment Roof */}
        <mesh position={[0, 0.58, 0]} rotation={[0, 0, 0]}>
          <coneGeometry args={[0.38, 0.14, 4]} />
          <meshStandardMaterial color="#38BDF8" metalness={0.6} roughness={0.2} />
        </mesh>
      </group>

      {/* Orbiting Statutory Ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 2.3, 0.2, 0]}>
        <torusGeometry args={[1.35, 0.025, 16, 100]} />
        <meshStandardMaterial color="#60A5FA" emissive="#38BDF8" emissiveIntensity={0.6} />
      </mesh>
    </group>
  );
}

function WorkflowNode({
  node,
}: {
  node: (typeof WORKFLOW_NODES)[number];
}) {
  const [hovered, setHovered] = useState(false);
  const ref = useRef<THREE.Group>(null);

  return (
    <Float speed={1.5} rotationIntensity={0.1} floatIntensity={0.4}>
      <group
        ref={ref}
        position={node.pos}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={() => setHovered(false)}
      >
        <mesh castShadow>
          <sphereGeometry args={[hovered ? 0.22 : 0.18, 24, 24]} />
          <meshPhysicalMaterial
            color={node.color}
            emissive={node.color}
            emissiveIntensity={hovered ? 0.8 : 0.35}
            roughness={0.2}
            metalness={0.3}
          />
        </mesh>
        {/* Label Text */}
        <Text
          position={[0, -0.32, 0]}
          fontSize={0.11}
          color="#0B1B3A"
          anchorX="center"
          anchorY="middle"
          textAlign="center"
          outlineWidth={0.015}
          outlineColor="#FFFFFF"
        >
          {node.label}
        </Text>
      </group>
    </Float>
  );
}

function FloatingIndicator({
  item,
}: {
  item: (typeof FLOATING_INDICATORS)[number];
}) {
  return (
    <Float speed={1.3} rotationIntensity={0.08} floatIntensity={0.5}>
      <group position={item.pos}>
        <Html transform distanceFactor={5.5} center>
          <div className="w-52 select-none rounded-xl border border-white/40 bg-white/85 p-2.5 shadow-xl backdrop-blur-md transition-transform hover:scale-105 pointer-events-none">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {item.title}
              </span>
              <span
                className={`inline-block h-2 w-2 rounded-full ${item.badgeColor} ring-2 ring-white`}
              />
            </div>
            <div className="mt-1 flex items-baseline justify-between">
              <span className="text-base font-black text-ink">{item.metric}</span>
              <span className="text-[10px] font-semibold text-primary">{item.badge}</span>
            </div>
            <div className="mt-0.5 text-[9px] text-slate-400">{item.subtitle}</div>
          </div>
        </Html>
      </group>
    </Float>
  );
}

function PulseRings() {
  const group = useRef<THREE.Group>(null);
  const pulses = useMemo(
    () =>
      WORKFLOW_NODES.map((n) => {
        const points = [
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(n.pos[0] * 0.5, n.pos[1] * 0.5 + 0.2, n.pos[2] * 0.5),
          new THREE.Vector3(n.pos[0], n.pos[1], n.pos[2]),
        ];
        const curve = new THREE.CatmullRomCurve3(points);
        return { curve, color: n.color };
      }),
    []
  );

  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.04;
  });

  return (
    <group ref={group}>
      {pulses.map((p, idx) => {
        const points = p.curve.getPoints(24);
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        return (
          <primitive key={idx} object={new THREE.Line(
            geometry,
            new THREE.LineBasicMaterial({
              color: new THREE.Color(p.color),
              transparent: true,
              opacity: 0.35,
            })
          )} />
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
    damp3(
      camera.position,
      [state.pointer.x * 0.5, 0.9 + state.pointer.y * 0.25, 5.8 + (1 - t) * 2.2],
      0.25,
      dt
    );
    camera.lookAt(0, 0.1, 0);
  });
  return null;
}

function Scene({ paused }: { paused: boolean }) {
  return (
    <>
      <color attach="background" args={["#ffffff"]} />
      <ambientLight intensity={0.8} />
      <directionalLight position={[5, 7, 5]} intensity={1.2} />
      <spotLight position={[-4, 6, 2]} intensity={8} color="#93C5FD" angle={0.4} />
      <Environment preset="studio" />
      <ParallaxRig paused={paused} />

      <CentralHub />
      <PulseRings />

      {WORKFLOW_NODES.map((node) => (
        <WorkflowNode key={node.id} node={node} />
      ))}

      {FLOATING_INDICATORS.map((item, idx) => (
        <FloatingIndicator key={idx} item={item} />
      ))}

      <Sparkles count={80} scale={7} size={2.2} speed={0.25} color="#93C5FD" />
      <ContactShadows opacity={0.25} blur={2.2} position={[0, -1.8, 0]} />
    </>
  );
}

export default function HeroScene({ forceFallback = false }: { forceFallback?: boolean }) {
  const { ok, quality } = useWebGLSupport(forceFallback);
  const { ref, paused } = usePauseWhenHidden();
  const dpr: [number, number] = quality === "high" ? [1, 1.5] : [1, 1];
  if (!ok) return <Fallback2D />;
  return (
    <div ref={ref} className="h-[540px] w-full" aria-hidden="true">
      <Suspense fallback={<Fallback2D />}>
        <Canvas
          dpr={dpr}
          frameloop={paused ? "demand" : "always"}
          camera={{ position: [0, 0.9, 5.8], fov: 42 }}
          gl={{ antialias: true, alpha: true }}
        >
          <Scene paused={paused} />
        </Canvas>
      </Suspense>
    </div>
  );
}
