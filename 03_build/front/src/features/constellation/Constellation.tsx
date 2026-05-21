/*
 * SPEC-041 Step-2 — Constellation benchmark harness (GATE). Renders the 611-node
 * (+globe) fixture and instruments FPS (rAF sampler), node/link counts, and JS heap.
 * Exposes window.__cstBench (live FPS + counts) and window.__fg (the force-graph ref
 * methods: zoom/zoomToFit) so the perf benchmark can drive fit/mid/max zoom + pan and
 * read results. Step-3 replaces this with the real galactic surface.
 */
import { useEffect, useRef, useState } from "react";
import { ForceGraph } from "./ForceGraph";
import { buildBenchmarkGraph } from "./fixtures";

const GRAPH = buildBenchmarkGraph();

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    __fg?: any;
    __cstBench?: { fps: number; nodes: number; links: number; heapMB: number | null };
  }
}

export function Constellation() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [fps, setFps] = useState(0);

  // Measure container.
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Amendment 6 — slightly more spacing for breathing room (charge repulsion +
  // link distance), enough to de-densify the cluster without breaking the galaxy.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg?.d3Force) return;
    fg.d3Force("charge")?.strength(-55);
    fg.d3Force("link")?.distance(36);
    fg.d3ReheatSimulation?.();
  }, []);

  // FPS sampler (rolling 1s) + window export for the benchmark harness.
  useEffect(() => {
    window.__fg = fgRef.current;
    let frames = 0;
    let last = performance.now();
    let raf = 0;
    const tick = () => {
      frames++;
      const now = performance.now();
      if (now - last >= 1000) {
        const f = Math.round((frames * 1000) / (now - last));
        setFps(f);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const mem = (performance as any).memory?.usedJSHeapSize;
        window.__cstBench = {
          fps: f,
          nodes: GRAPH.nodes.length,
          links: GRAPH.links.length,
          heapMB: mem ? Math.round(mem / 1048576) : null,
        };
        frames = 0;
        last = now;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="relative h-[calc(100vh-160px)] w-full" ref={boxRef}>
      <div className="absolute left-4 top-4 z-10 rounded-2xl border border-line-strong bg-surface-card/90 px-3 py-2 text-xs text-ink-secondary">
        <span className="font-mono text-ink-primary">{GRAPH.nodes.length}</span> nodes ·{" "}
        <span className="font-mono text-ink-primary">{GRAPH.links.length}</span> links ·{" "}
        <span className="font-mono text-ink-primary">{fps}</span> fps
        <span className="ml-1 text-ink-muted">(Step-2 benchmark)</span>
      </div>
      <ForceGraph fgRef={fgRef} graph={GRAPH} width={size.w} height={size.h} />
    </div>
  );
}
