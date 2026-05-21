/*
 * SPEC-041 — react-force-graph-2d wrapper. Step-2 (benchmark) ships PLACEHOLDER
 * rendering: default circle nodes colored by type/health, links colored by state.
 * The custom globe + orbital radial force + custom node rendering land in Step-3
 * (so this benchmark is a LOWER bound — custom canvas drawing will add cost).
 */
import type { MutableRefObject } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { ConstellationGraph, ConstellationLink, ConstellationNode } from "./fixtures";

// Placeholder palette (Step-3 replaces with the §22 link-state tokens + health tiers).
const LINK_COLOR: Record<string, string> = {
  active: "#6B46C1",
  inactive: "rgba(148,163,184,0.35)",
  churn: "#E11D48",
};
function nodeColor(n: ConstellationNode): string {
  if (n.type === "globe") return "#6B46C1";
  if (n.type === "manager") return "#4B2E91";
  if (n.type === "rm") return "#5B35B1";
  const h = n.health ?? 5;
  return h >= 7 ? "#047857" : h >= 4 ? "#B45309" : "#E11D48"; // emerald / amber / rose
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
      nodeVal={(n: ConstellationNode) => n.size}
      nodeColor={(n: ConstellationNode) => nodeColor(n)}
      nodeLabel={(n: ConstellationNode) => n.label}
      linkColor={(l: ConstellationLink) => LINK_COLOR[l.state] ?? "#cbd5e1"}
      linkWidth={1}
      cooldownTicks={100}
      onNodeClick={(n: ConstellationNode) => onNodeClick?.(n)}
    />
  );
}
