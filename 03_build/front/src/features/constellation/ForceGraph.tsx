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
import {
  accountARR,
  bookARR,
  DEMO_ACCOUNTS,
  DEMO_RMS,
  formatARR,
  managerBookARR,
  rmBookARR,
} from "@/fixtures/demo_characters";
import { DEMO_ACTIONS } from "@/features/queue/demo_actions";
import {
  composeTeamWorkload,
  type ThroughputIndicator,
} from "@/features/executive/composers/team_workload_composer";
import type { UserRole } from "@/lib/rbac/types";
import type { ConstellationGraph, ConstellationLink, ConstellationNode } from "./fixtures";

const THROUGHPUT_LABEL: Record<ThroughputIndicator, string> = {
  rising: "↑ Rising",
  steady: "→ Steady",
  declining: "↓ Declining",
  flat: "→ Flat",
};

// Hover tooltip text per node type, carrying ARR via the revenue heuristic helpers
// (SPEC-041 Step-4 revenue enrichment). Globe = total book; manager/RM = aggregate
// book + span; account = book value + owning RM. Talent keeps the plain name.
//
// SPEC-042 Step-8 (§6.7): for Executive + Admin viewers ONLY, RM nodes append a second
// workload line (pending · approved this week · throughput) derived from the same
// composeTeamWorkload pure function the Team workload panel uses. Other roles (RM /
// Manager) and other node types are unchanged. `nodeLabel` is rendered as HTML by
// react-force-graph, so the <br/> produces a real second line. Exported for unit testing
// (the canvas tooltip itself never mounts under jsdom — Step-8 constraint).
export function nodeTooltip(n: ConstellationNode, viewerRole?: UserRole): string {
  switch (n.type) {
    case "globe":
      return `EDGE Pulse · ${formatARR(bookARR())} total book`;
    case "manager": {
      const rms = DEMO_RMS.filter((r) => r.managerId === n.id).length;
      return `${n.label} · ${formatARR(managerBookARR(n.id))} book · ${rms} RMs`;
    }
    case "rm": {
      const accounts = DEMO_ACCOUNTS.filter((a) => a.rmId === n.id).length;
      const base = `${n.label} · ${formatARR(rmBookARR(n.id))} book · ${accounts} account${accounts === 1 ? "" : "s"}`;
      if (viewerRole === "executive" || viewerRole === "admin") {
        const w = composeTeamWorkload(DEMO_RMS, DEMO_ACTIONS).find((r) => r.rmId === n.id);
        if (w) {
          return `${base}<br/>${w.pendingCount} pending · ${w.approvedThisWeek} approved this week · ${THROUGHPUT_LABEL[w.throughputIndicator]}`;
        }
      }
      return base;
    }
    case "account": {
      const rmName = DEMO_RMS.find((r) => r.id === n.rm_id)?.name;
      return `${n.label} · ${formatARR(accountARR(n.id))}${rmName ? ` · ${rmName}` : ""}`;
    }
    default:
      return n.label;
  }
}

// Resolve Tier-0 tokens from CSS once (canvas needs concrete colors).
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
const BRAND = cssVar("--color-brand-primary", "#4a0f70");
const BRAND_DEEP = cssVar("--color-brand-primary-deep", "#350A50");
const BRAND_GLOW = cssVar("--color-brand-primary-glow", "rgba(74,15,112,0.2)");
const INK_SECONDARY = cssVar("--color-text-secondary", "rgb(100,116,139)");
const LINK_COLOR: Record<string, string> = {
  active: cssVar("--color-link-active", BRAND),
  inactive: cssVar("--color-link-inactive", "rgba(148,163,184,0.35)"),
  churn: cssVar("--color-link-churn", "#E11D48"),
};

/** Radius in canvas px from the node's size dimension. */
function radius(n: ConstellationNode): number {
  return Math.max(2, Math.sqrt(n.size) * 1.6);
}

function drawNode(n: ConstellationNode, ctx: CanvasRenderingContext2D) {
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
  // Managers/RMs/accounts/talent: brand-purple ROUNDED SQUARES (Amendment 6 —
  // resolves the clustered-circles trypophobia trigger + matches Pulse's tile/card
  // vocabulary). Corner radius ≈ 25% of side. Managers slightly deeper for tier read.
  const r = radius(n);
  const side = r * 2;
  const cr = side * 0.25;
  // Step-5: Active talent get a subtle brand-purple glow (all demo talent are Active;
  // terminated → greyed, no glow, v1.5+ #29). Glow via canvas shadow before the fill.
  if (n.type === "talent") {
    ctx.save();
    ctx.shadowColor = BRAND;
    ctx.shadowBlur = 6;
  }
  ctx.beginPath();
  ctx.roundRect(x - r, y - r, side, side, cr);
  ctx.fillStyle = n.type === "manager" ? BRAND_DEEP : BRAND;
  ctx.fill();
  if (n.type === "talent") ctx.restore();
  // Step-7 labels: managers + RMs always show their name BELOW the node (small,
  // ink-secondary). Accounts/talent use the hover pill (nodeLabel); globe has none.
  if (n.type === "manager" || n.type === "rm") {
    ctx.fillStyle = INK_SECONDARY;
    ctx.font = "4px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(n.label, x, y + r + 2);
  }
}

export interface ForceGraphProps {
  graph: ConstellationGraph;
  width: number;
  height: number;
  onNodeClick?: (n: ConstellationNode, event: MouseEvent) => void;
  onBackgroundClick?: () => void;
  // Reposition hooks for HTML overlays (Step-5): engine tick while the sim settles,
  // and zoom/pan transforms. Both trigger a graph2ScreenCoords recompute in the parent.
  onEngineTick?: () => void;
  onZoom?: () => void;
  // SPEC-042 Step-8: viewer role drives the RM-node workload tooltip extension (Exec/Admin only).
  viewerRole?: UserRole;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fgRef?: MutableRefObject<any>;
}

export function ForceGraph({
  graph,
  width,
  height,
  onNodeClick,
  onBackgroundClick,
  onEngineTick,
  onZoom,
  viewerRole,
  fgRef,
}: ForceGraphProps) {
  return (
    <ForceGraph2D
      ref={fgRef}
      width={width}
      height={height}
      graphData={graph}
      nodeId="id"
      nodeLabel={(n: ConstellationNode) => nodeTooltip(n, viewerRole)}
      nodeCanvasObject={(n: ConstellationNode, ctx: CanvasRenderingContext2D) => drawNode(n, ctx)}
      nodePointerAreaPaint={(n: ConstellationNode, color: string, ctx: CanvasRenderingContext2D) => {
        const x = (n as { x?: number }).x ?? 0;
        const y = (n as { y?: number }).y ?? 0;
        ctx.fillStyle = color;
        ctx.beginPath();
        if (n.type === "globe") {
          ctx.arc(x, y, 16, 0, 2 * Math.PI);
        } else {
          const r = radius(n);
          ctx.roundRect(x - r, y - r, r * 2, r * 2, r * 0.5);
        }
        ctx.fill();
      }}
      linkColor={(l: ConstellationLink) => LINK_COLOR[l.state] ?? LINK_COLOR.inactive}
      linkWidth={(l: ConstellationLink) => (l.state === "churn" ? 1.6 : 0.7)}
      // Churn-only animated emphasis (directional particle flow) — the urgent state.
      linkDirectionalParticles={(l: ConstellationLink) => (l.state === "churn" ? 3 : 0)}
      linkDirectionalParticleWidth={2}
      linkDirectionalParticleColor={() => LINK_COLOR.churn}
      cooldownTicks={120}
      onEngineTick={() => onEngineTick?.()}
      onZoom={() => onZoom?.()}
      onNodeClick={(n: ConstellationNode, event: MouseEvent) => onNodeClick?.(n, event)}
      onBackgroundClick={() => onBackgroundClick?.()}
    />
  );
}
