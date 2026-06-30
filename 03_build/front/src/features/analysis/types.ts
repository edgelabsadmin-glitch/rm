/*
 * Analysis-agent DTOs — the per-entity signal matrix snapshot the backend
 * produces (api/analysis.py → core/analysis/store.py). `priority_color` drives
 * the red→green priority dot; `fired_signals` + `narrative` drive the panel.
 */

export type PriorityColor = "red" | "orange" | "amber" | "blue" | "green";
export type Priority = "critical" | "high" | "medium" | "low" | "healthy";

export interface FiredSignal {
  signal_id: string;
  fired: boolean;
  severity: "low" | "medium" | "high" | null;
  confidence?: number;
  evidence?: string[];
}

export interface MatrixDTO {
  entity_type: "account" | "talent";
  entity_id: string;
  analyzed_at: string;
  priority: Priority;
  priority_color: PriorityColor;
  priority_score: number;
  fired_signals: FiredSignal[];
  narrative: string | null;
  model_used: string | null;
  state: "ok" | "needs_review";
}

export interface MatrixSummary {
  entity_id: string;
  priority: Priority;
  priority_color: PriorityColor;
  priority_score: number;
  state: string;
  analyzed_at: string;
}

export interface MatrixHistoryPoint {
  analyzed_at: string;
  priority: Priority;
  priority_color: PriorityColor;
  priority_score: number;
  state: string;
}

export interface AnalysisStatusDTO {
  state: "idle" | "running" | "done" | "error";
  percent: number;
  phase: string | null;
  detail: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}
