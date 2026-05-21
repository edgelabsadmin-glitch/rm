/*
 * SPEC-041 Step-4 — Constellation interaction + talent drill-down.
 * Click→destination matrix (spec §51 + amendments): globe→/ceo; manager single→
 * zoom-to-cluster, modifier→/actions?manager=; RM→/actions?rm=; account single→
 * inline orbital talent drill-down, modifier→per-account view; empty space→collapse
 * talent. Talent capped at MAX_TALENT_PER_ACCOUNT (audit Dim 10); side-panel is the
 * documented fallback (D10) if the orbital approach degrades at full density.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { ForceGraph } from "./ForceGraph";
import {
  buildBenchmarkGraph,
  buildTalentFor,
  type ConstellationGraph,
  type ConstellationNode,
} from "./fixtures";

const BASE = buildBenchmarkGraph();

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
  const navigate = useNavigate();
  const { setSelectedAccountId } = useSelectedAccount();

  const [size, setSize] = useState({ w: 800, h: 600 });
  const [fps, setFps] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null); // account id with talent shown

  // Compose the rendered graph = base + (talent for the expanded account).
  const graph: ConstellationGraph = useMemo(() => {
    if (!expanded) return BASE;
    const acct = BASE.nodes.find((n) => n.id === expanded);
    if (!acct) return BASE;
    const t = buildTalentFor(acct);
    return { nodes: [...BASE.nodes, ...t.nodes], links: [...BASE.links, ...t.links] };
  }, [expanded]);

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

  // Spacing tuning for breathing room (Amendment 6).
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg?.d3Force) return;
    fg.d3Force("charge")?.strength(-55);
    fg.d3Force("link")?.distance(36);
    fg.d3ReheatSimulation?.();
  }, []);

  // FPS sampler + window export (dev/perf instrumentation).
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
          nodes: graph.nodes.length,
          links: graph.links.length,
          heapMB: mem ? Math.round(mem / 1048576) : null,
        };
        frames = 0;
        last = now;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [graph]);

  function handleNodeClick(n: ConstellationNode, event: MouseEvent) {
    const mod = event.metaKey || event.ctrlKey;
    switch (n.type) {
      case "globe":
        navigate("/ceo");
        break;
      case "manager":
        if (mod) navigate(`/actions?manager=${encodeURIComponent(n.id)}`);
        else {
          const x = (n as { x?: number }).x ?? 0;
          const y = (n as { y?: number }).y ?? 0;
          fgRef.current?.centerAt?.(x, y, 600);
          fgRef.current?.zoom?.(3, 600);
        }
        break;
      case "rm":
        navigate(`/actions?rm=${encodeURIComponent(n.id)}`);
        break;
      case "account":
        if (mod) {
          setSelectedAccountId(n.id);
          navigate("/accounts");
        } else {
          setExpanded((cur) => (cur === n.id ? null : n.id)); // toggle talent orbit
        }
        break;
      // talent → no-op
    }
  }

  return (
    <div className="relative h-[calc(100vh-160px)] w-full" ref={boxRef}>
      <div className="absolute left-4 top-4 z-10 rounded-2xl border border-line-strong bg-surface-card/90 px-3 py-2 text-xs text-ink-secondary">
        <span className="font-mono text-ink-primary">{graph.nodes.length}</span> nodes ·{" "}
        <span className="font-mono text-ink-primary">{fps}</span> fps
        {expanded && <span className="ml-1 text-brand">· talent shown</span>}
      </div>
      <ForceGraph
        fgRef={fgRef}
        graph={graph}
        width={size.w}
        height={size.h}
        onNodeClick={handleNodeClick}
        onBackgroundClick={() => setExpanded(null)}
      />
    </div>
  );
}
