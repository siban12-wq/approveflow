import { useEffect, useRef, useState } from "react";

/** Pause R3F when the canvas is off-screen or the tab is hidden. */
export function usePauseWhenHidden() {
  const ref = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const el = ref.current;
    const vis = () => setPaused(document.hidden || (el ? !isInView(el) : false));
    const io = el
      ? new IntersectionObserver(
          (entries) => {
            const hit = entries[0];
            setPaused(document.hidden || !hit?.isIntersecting);
          },
          { threshold: 0.05 },
        )
      : null;
    if (el) io?.observe(el);
    document.addEventListener("visibilitychange", vis);
    return () => {
      io?.disconnect();
      document.removeEventListener("visibilitychange", vis);
    };
  }, []);

  return { ref, paused };
}

function isInView(el: HTMLElement) {
  const r = el.getBoundingClientRect();
  return r.bottom > 0 && r.top < window.innerHeight;
}
