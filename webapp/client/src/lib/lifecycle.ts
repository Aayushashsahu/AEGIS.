/**
 * Presentation types only. The backend returns canonical AegisGraphState after
 * invoking the existing Python AEGIS domain modules; React never derives a
 * lifecycle status, verification result, risk result, or commit decision.
 */
import type { CaseGraph } from "./aegisApi";

export type LifecycleStage = string;
export type LifecycleStatus = "CONFIGURED" | "ACTIVE" | "PENDING" | "ANOMALY" | "VERIFIED" | "QUARANTINED" | "BLOCKED" | "UNAVAILABLE";
export type LifecycleProvenance = "USER_CONFIGURED" | "NORMALIZED_CASE" | "REAL_PROVIDER" | "REPLAY" | "TEST_DOUBLE" | "CONTROLLED_DEMONSTRATOR";
export type LifecycleNode = { id: LifecycleStage; label: string; status: LifecycleStatus; provenance: LifecycleProvenance; detail: string; evidenceRefs: string[]; timestamp?: string; provider?: string };
export type LifecycleEdge = { id: string; source: LifecycleStage; target: LifecycleStage; status: "PENDING" | "ACTIVE" | "BROKEN" | "VERIFIED" | "UNAVAILABLE"; provenance: LifecycleProvenance; evidenceRefs: string[] };
export type GraphSeverity = "UNKNOWN" | "HEALTHY" | "ANOMALY" | "QUARANTINE" | "BLOCKED";
export type GraphDecision = "NOT_EVALUATED" | "ACCEPT" | "REJECT" | "QUARANTINE" | "BLOCKED";
export type GraphEdgeStatus = LifecycleEdge["status"];
export type LifecycleGraphState = Omit<CaseGraph, "nodes" | "edges" | "activeNodeId" | "currentStage" | "severity" | "provenance" | "decision"> & { nodes: LifecycleNode[]; edges: LifecycleEdge[]; activeNodeId: LifecycleStage; currentStage: LifecycleStage; severity: GraphSeverity; provenance: LifecycleProvenance; decision: GraphDecision };

export function emptyLifecycle(): LifecycleGraphState {
  return {
    case_id: "unavailable",
    mode: "EMPTY",
    nodes: [],
    edges: [],
    activeNodeId: "TARGET",
    activeEdgeIds: [],
    currentStage: "TARGET",
    severity: "UNKNOWN",
    provenance: "NORMALIZED_CASE",
    decision: "NOT_EVALUATED",
    evidenceRefs: [],
    message: "No canonical lifecycle projection is available.",
  };
}
