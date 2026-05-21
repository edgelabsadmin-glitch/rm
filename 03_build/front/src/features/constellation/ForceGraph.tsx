/*
 * SPEC-041 Step-3 — react-force-graph-2d wrapper, real galactic scaffold.
 * Amendment 5 encoding: nodes are BRAND PURPLE across all health tiers (calm + brand-
 * cohesive); node SIZE = composite-health × activity. Health is NOT a node color.
 * Links carry the signal state (active/inactive/churn) via the §22 link-state tokens;
 * CHURN links get animated emphasis (directional particles) — red reserved for the
 * failing connection. Center globe is custom-rendered; managers/RMs are pinned on
 * orbital rings (fx/fy from the fixture); accounts free-float.
 */
import type { MutableRefObject } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { ConstellationGraph, ConstellationLink, ConstellationNode } from "./fixtures";

// Resolve Tier-0 tokens from CSS once (canvas needs concrete colors).
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
const BRAND = cssVar("--color-brand-primary", "#6B46C1");
const BRAND_DEEP = cssVar("--color-brand-primary-deep", "#4B2E91");
const BRAND_GLOW = cssVar("--color-brand-primary-glow", "rgba(107,70,193,0.2)");
const LINK_COLOR: Record<string, string> = {
  active: cssVar("--color-link-active", BRAND),
  inactive: cssVar("--color-link-inactive", "rgba(148,163,184,0.35)"),
  churn: cssVar("--color-link-churn", "#E11D48"),
};

/** Radius in canvas px from the node's size dimension. */
function radius(n: ConstellationNode): number {
  return Math.max(2, Math.sqrt(n.size) * 1.6);
}

function drawNode(n: ConstellationNode, ctx: CanvasRenderingContext2D, scale: number) {
  const x = (n as { x?: number }).x ?? 0;
  const y = (n as { y?: number }).y ?? 0;
  if (n.type === "globe") {
    // Brand-mark anchor: glow halo + solid brand disc + a small bolt glyph.
    const r = 14;
    ctx.beginPath();
    ctx.arc(x, y, r + 8, 0, 2 * Math.PI);
    ctx.fillStyle = BRAND_GLOW;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = BRAND;
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.font = `${r}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("⚡", x, y + 0.5); // ⚡
    return;
  }
  // Managers/RMs/accounts: all brand purple (Amendment 5). Managers slightly deeper
  // for a subtle tier read; never health-colored.
  ctx.beginPath();
  ctx.arc(x, y, radius(n), 0, 2 * Math.PI);
  ctx.fillStyle = n.type === "manager" ? BRAND_DEEP : BRAND;
  ctx.fill();
  // Labels for managers/RMs only above a zoom threshold (LOD — keeps the galaxy calm).
  if (n.type !== "account" && scale > 1.5) {
    ctx.fillStyle = BRAND_DEEP;
    ctx.font = "4px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(n.label, x, y - radius(n) - 2);
  }
}

export interface ForceGraphProps {
  graph: ConstellationGraph;
  width: number;
  height: number;
  onNodeClick?: (n: ConstellationNode) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fgRef?: MutableRefObject<any>;
}

export function ForceGraph({ graph, width, height, onNodeClick, fgRef }: ForceGraphProps) {
  return (
    <ForceGraph2D
      ref={fgRef}
      width={width}
      height={height}
      graphData={graph}
      nodeId="id"
      nodeLabel={(n: ConstellationNode) => n.label}
      nodeCanvasObject={(n: ConstellationNode, ctx: CanvasRenderingContext2D, scale: number) =>
        drawNode(n, ctx, scale)
      }
      nodePointerAreaPaint={(n: ConstellationNode, color: string, ctx: CanvasRenderingContext2D) => {
        const x = (n as { x?: number }).x ?? 0;
        const y = (n as { y?: number }).y ?? 0;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, n.type === "globe" ? 16 : radius(n), 0, 2 * Math.PI);
        ctx.fill();
      }}
      linkColor={(l: ConstellationLink) => LINK_COLOR[l.state] ?? LINK_COLOR.inactive}
      linkWidth={(l: ConstellationLink) => (l.state === "churn" ? 1.6 : 0.7)}
      // Churn-only animated emphasis (directional particle flow) — the urgent state.
      linkDirectionalParticles={(l: ConstellationLink) => (l.state === "churn" ? 3 : 0)}
      linkDirectionalParticleWidth={2}
      linkDirectionalParticleColor={() => LINK_COLOR.churn}
      cooldownTicks={120}
      onNodeClick={(n: ConstellationNode) => onNodeClick?.(n)}
    />
  );
}
