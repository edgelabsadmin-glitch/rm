/*
 * SPEC-041 Step-4 — Constellation interaction + talent drill-down.
 * Click→destination matrix (spec §51 + amendments): globe→/executive; manager single→
 * zoom-to-cluster, modifier→/actions?manager=; RM→/actions?rm=; account single→
 * inline orbital talent drill-down, modifier→per-account view; empty space→collapse
 * talent. Talent capped at MAX_TALENT_PER_ACCOUNT (audit Dim 10); side-panel is the
 * documented fallback (D10) if the orbital approach degrades at full density.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth/AuthContext";
import { useSelectedAccount } from "@/session/SelectedAccountProvider";
import { ForceGraph } from "./ForceGraph";
import {
  DEMO_ACCOUNTS,
  DEMO_RMS,
  DEMO_TALENT,
  type DemoAccountId,
} from "@/fixtures/demo_characters";
import { DEMO_TIER_JUMP_EVENTS } from "@/fixtures/demo_tier_jump_events";
import {
  composeCapacityImbalance,
  type CapacityImbalanceCard,
} from "./composers/rm_capacity_composer";
import {
  composeEscalationTierJumps,
  type EscalationTierJumpCard,
} from "./composers/escalation_tier_jump_composer";
import { clusterCentroid, DEMO_PATTERNS, type PatternCard } from "./demo_patterns";
import { ClusterPatternOverlay } from "./overlays/ClusterPatternOverlay";
import { EscalationTierJumpOverlay } from "./overlays/EscalationTierJumpOverlay";
import { RmCapacityImbalanceOverlay } from "./overlays/RmCapacityImbalanceOverlay";
import {
  ConstellationEmpty,
  ConstellationError,
  ConstellationLoading,
} from "./states/ConstellationStates";
import {
  buildConstellationGraph,
  buildTalentFor,
  type ConstellationGraph,
  type ConstellationNode,
} from "./fixtures";

// Phase-1 data is derived synchronously, so 'loading'/'error' are reached only by the
// Phase-2 async pulse-api fetch (the state components exist + are tested for that wiring).
// Phase-1 resolves to 'empty' (scope yields zero accounts) or 'ready'.
type Status = "loading" | "error" | "empty" | "ready";

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    __fg?: any;
    __cstBench?: { fps: number; nodes: number; links: number; heapMB: number | null };
  }
}

export interface ConstellationProps {
  /**
   * RBAC visibility scope (spec 042, Week 4): whitelist of account ids the viewer may see.
   * undefined = no scoping (all accounts, the Phase-1 default). [] = nothing in scope →
   * empty state. The manager/RM scaffold always renders; only account leaves are scoped.
   */
  accountScope?: DemoAccountId[];
}

export function Constellation({ accountScope }: ConstellationProps = {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { setSelectedAccountId } = useSelectedAccount();
  // SPEC-042 Step-4: scope comes from the logged-in user (AuthContext). An explicit
  // `accountScope` prop still overrides (RBAC test harness / future server scope).
  const { user, accountScope: authScope } = useAuth();
  const effectiveScope = accountScope ?? authScope;

  const [size, setSize] = useState({ w: 800, h: 600 });
  const [fps, setFps] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null); // account id with talent shown
  // Step-5: screen positions for the cluster-pattern overlays (centroid of each
  // pattern's support accounts, in screen px). Recomputed on engine tick + zoom/pan.
  const [overlays, setOverlays] = useState<{ pattern: PatternCard; x: number; y: number }[]>([]);
  const [capacityOverlays, setCapacityOverlays] = useState<
    { card: CapacityImbalanceCard; x: number; y: number }[]
  >([]);
  const [escalationOverlays, setEscalationOverlays] = useState<
    { card: EscalationTierJumpCard; x: number; y: number }[]
  >([]);

  // Base graph, scoped by the effective RBAC whitelist (spec 042). Memoized on the scope.
  const base = useMemo(() => buildConstellationGraph(effectiveScope), [effectiveScope]);

  // Phase-1 status: empty when a scope is given but resolves to zero accounts; else ready.
  // (loading/error are Phase-2 async states — components exist + tested, not reached here.)
  const status = useMemo<Status>(() => {
    if (effectiveScope && base.nodes.every((n) => n.type !== "account")) return "empty";
    return "ready";
  }, [effectiveScope, base]);

  // Step-4: overlay composers honor the effective scope (closes watched concern #26).
  const capacityCards = useMemo(
    () => composeCapacityImbalance(DEMO_ACCOUNTS, DEMO_RMS, effectiveScope),
    [effectiveScope],
  );
  const escalationCards = useMemo(
    () => composeEscalationTierJumps(DEMO_TIER_JUMP_EVENTS, effectiveScope),
    [effectiveScope],
  );
  // Cluster patterns: partial-scope filter-out — a pattern is hidden unless ALL of its
  // support accounts are in scope (spec §6 edge case).
  const scopedPatterns = useMemo(
    () =>
      effectiveScope
        ? DEMO_PATTERNS.filter((p) => p.support_account_ids.every((id) => effectiveScope.includes(id)))
        : DEMO_PATTERNS,
    [effectiveScope],
  );

  // Compose the rendered graph = base + (talent for the expanded account).
  const graph: ConstellationGraph = useMemo(() => {
    if (!expanded) return base;
    const acct = base.nodes.find((n) => n.id === expanded);
    if (!acct) return base;
    const t = buildTalentFor(acct);
    return { nodes: [...base.nodes, ...t.nodes], links: [...base.links, ...t.links] };
  }, [base, expanded]);

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

  // Recompute each pattern overlay's screen position from the live centroid of its
  // support-account nodes (node x/y are mutated in place by the sim). Cheap for the
  // demo's single pattern; skips a state write when nothing moved meaningfully.
  const recomputeOverlays = useCallback(() => {
    const fg = fgRef.current;
    if (!fg?.graph2ScreenCoords) return;
    const next: { pattern: PatternCard; x: number; y: number }[] = [];
    for (const pattern of scopedPatterns) {
      const c = clusterCentroid(pattern.support_account_ids, graph.nodes);
      if (!c) continue;
      const s = fg.graph2ScreenCoords(c.x, c.y);
      next.push({ pattern, x: s.x, y: s.y });
    }
    setOverlays((prev) => {
      if (
        prev.length === next.length &&
        prev.every((p, i) => Math.abs(p.x - next[i].x) < 0.5 && Math.abs(p.y - next[i].y) < 0.5)
      ) {
        return prev;
      }
      return next;
    });

    // Step-6: capacity-imbalance overlays, anchored at the top-loaded RM's account cluster.
    const cap: { card: CapacityImbalanceCard; x: number; y: number }[] = [];
    for (const card of capacityCards) {
      const ids = DEMO_ACCOUNTS.filter((a) => a.rmId === card.topLoadedRmId).map((a) => a.id);
      const c = clusterCentroid(ids, graph.nodes);
      if (!c) continue;
      const s = fg.graph2ScreenCoords(c.x, c.y);
      cap.push({ card, x: s.x, y: s.y });
    }
    setCapacityOverlays((prev) => {
      if (
        prev.length === cap.length &&
        prev.every((p, i) => Math.abs(p.x - cap[i].x) < 0.5 && Math.abs(p.y - cap[i].y) < 0.5)
      ) {
        return prev;
      }
      return cap;
    });

    // Step-7: escalation tier-jump overlays, anchored directly at the affected account node.
    const esc: { card: EscalationTierJumpCard; x: number; y: number }[] = [];
    for (const card of escalationCards) {
      const c = clusterCentroid([card.accountId], graph.nodes);
      if (!c) continue;
      const s = fg.graph2ScreenCoords(c.x, c.y);
      esc.push({ card, x: s.x, y: s.y });
    }
    setEscalationOverlays((prev) => {
      if (
        prev.length === esc.length &&
        prev.every((p, i) => Math.abs(p.x - esc[i].x) < 0.5 && Math.abs(p.y - esc[i].y) < 0.5)
      ) {
        return prev;
      }
      return esc;
    });
  }, [graph, scopedPatterns, capacityCards, escalationCards]);

  function handleInvestigate(pattern: PatternCard) {
    navigate(`/actions?pattern=${encodeURIComponent(pattern.id)}`);
  }

  function handleInvestigateCapacity(card: CapacityImbalanceCard) {
    navigate(`/actions?rm=${encodeURIComponent(card.topLoadedRmId)}`);
  }

  function handleInvestigateEscalation(card: EscalationTierJumpCard) {
    navigate(`/accounts/${encodeURIComponent(card.accountId)}`);
  }

  function handleNodeClick(n: ConstellationNode, event: MouseEvent) {
    const mod = event.metaKey || event.ctrlKey;
    switch (n.type) {
      case "globe":
        navigate("/executive");
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

  // Defensive states. Phase-1 only reaches 'empty'; 'loading'/'error' are wired by the
  // Phase-2 async pulse-api fetch (components exist + are unit-tested for that).
  if (status !== "ready") {
    return (
      <div className="relative h-[calc(100vh-160px)] w-full">
        {status === "loading" && <ConstellationLoading />}
        {status === "error" && <ConstellationError onRetry={() => window.location.reload()} />}
        {status === "empty" && <ConstellationEmpty />}
      </div>
    );
  }

  return (
    <div className="relative h-[calc(100vh-160px)] w-full" ref={boxRef}>
      {/* Polish #27: dev mode shows perf instrumentation; production shows live counts. */}
      {import.meta.env.DEV ? (
        <DevPerfChip nodes={graph.nodes.length} fps={fps} expanded={!!expanded} />
      ) : (
        <ProductionCountsChip
          accountCount={DEMO_ACCOUNTS.length}
          talentCount={DEMO_TALENT.filter((t) => t.stage === "Active").length}
          rmCount={DEMO_RMS.length}
        />
      )}
      <ForceGraph
        fgRef={fgRef}
        graph={graph}
        width={size.w}
        height={size.h}
        onNodeClick={handleNodeClick}
        onBackgroundClick={() => setExpanded(null)}
        onEngineTick={recomputeOverlays}
        onZoom={recomputeOverlays}
        viewerRole={user.role}
      />

      {/* Step-5: cluster-pattern alert overlays, positioned over the canvas. */}
      {overlays.map(({ pattern, x, y }) => (
        <ClusterPatternOverlay
          key={pattern.id}
          pattern={pattern}
          x={x}
          y={y}
          onInvestigate={handleInvestigate}
        />
      ))}

      {/* Step-6: RM capacity-imbalance overlays. */}
      {capacityOverlays.map(({ card, x, y }) => (
        <RmCapacityImbalanceOverlay
          key={card.id}
          card={card}
          x={x}
          y={y}
          onInvestigate={handleInvestigateCapacity}
        />
      ))}

      {/* Step-7: escalation tier-jump overlays. */}
      {escalationOverlays.map(({ card, x, y }) => (
        <EscalationTierJumpOverlay
          key={card.id}
          card={card}
          x={x}
          y={y}
          onInvestigate={handleInvestigateEscalation}
        />
      ))}
    </div>
  );
}

const CHIP_CLASS =
  "absolute left-4 top-4 z-10 rounded-md border border-line-strong bg-surface-card/90 px-3 py-2 text-[11px] tracking-wider text-ink-secondary";

/** Dev-only perf instrumentation (node count + FPS). */
function DevPerfChip({ nodes, fps, expanded }: { nodes: number; fps: number; expanded: boolean }) {
  return (
    <div className={CHIP_CLASS}>
      <span className="font-mono text-ink-primary">{nodes}</span> nodes ·{" "}
      <span className="font-mono text-ink-primary">{fps}</span> fps
      {expanded && <span className="ml-1 text-brand">· talent shown</span>}
    </div>
  );
}

/** Production chip — live book counts (all derived from demo_characters.ts). */
function ProductionCountsChip({
  accountCount,
  talentCount,
  rmCount,
}: {
  accountCount: number;
  talentCount: number;
  rmCount: number;
}) {
  return (
    <div className={CHIP_CLASS}>
      <span className="font-mono text-ink-primary">{accountCount}</span> accounts ·{" "}
      <span className="font-mono text-ink-primary">{talentCount}</span> active talent ·{" "}
      <span className="font-mono text-ink-primary">{rmCount}</span> RMs
    </div>
  );
}
