/// <reference types="vite/client" />

declare module "maath/easing" {
  import type { Vector3 } from "three";
  export function damp3(current: Vector3, target: [number, number, number], smoothTime: number, delta: number): Vector3;
}
