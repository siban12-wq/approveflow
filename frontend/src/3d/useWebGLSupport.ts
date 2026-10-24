import { useEffect, useState } from "react";

export type Quality = "low" | "medium" | "high";

export function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

export function useWebGLSupport(forceFallback = false) {
  const [ok, setOk] = useState(true);
  const [quality, setQuality] = useState<Quality>("medium");

  useEffect(() => {
    const mobile = window.matchMedia("(max-width: 768px)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const cores = navigator.hardwareConcurrency || 8;
    const webgl = detectWebGL();
    const lowPower = mobile || cores <= 4 || reduced || !webgl || forceFallback;
    setOk(!lowPower);
    setQuality(mobile ? "low" : cores >= 8 ? "high" : "medium");
  }, [forceFallback]);

  return { ok, quality, setQuality };
}
