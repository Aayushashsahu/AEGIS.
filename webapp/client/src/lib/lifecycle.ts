/**
 * Presentation types only. The backend returns canonical AegisGraphState after
 * invoking existing Python AEGIS domain modules; React never derives lifecycle,
 * verification, risk, or commit decisions.
 */
import type { CaseGraph } from "./aegisApi";

export type LifecycleStage = string;
export type LifecycleStatus = "CONFIGURED" | "ACTIVE" | "PENDING" | "ANOMALY" | "VERIFIED" | "QUARANTINED" | "BLOCKED" | "UNAVAILABLE";
export type LifecycleProvenance = "USER_CONFIGURED" | "NORMALIZED_CASE" | "REAL_PROVIDER" | "REPLAY" | "TEST_DOUBLE" | "CONTROLLED_DEMONSTRATOR" | "AEGIS_DETERMINISTIC";
export type LifecycleNode = { id: LifecycleStage; label: string; domain_status: string; display_status: LifecycleStatus; provenance: LifecycleProvenance; detail: string; evidenceRefs: string[]; timestamp?: string; provider?: string };
export type LifecycleEdge = { id: string; source: LifecycleStage; target: LifecycleStage; domain_status: string; display_status: "PENDING" | "ACTIVE" | "BROKEN" | "VERIFIED" | "UNAVAILABLE"; provenance: LifecycleProvenance; evidenceRefs: string[] };
export type GraphSeverity = "UNKNOWN" | "HEALTHY" | "ANOMALY" | "QUARANTINE" | "BLOCKED";
export type GraphDecision = "NOT_EVALUATED" | "ACCEPT" | "REJECT" | "QUARANTINE" | "BLOCKED";
export type GraphEdgeStatus = LifecycleEdge["display_status"];
export type LifecycleGraphState = Omit<CaseGraph, "nodes" | "edges" | "activeNodeId" | "currentStage" | "severity" | "provenance" | "domain_decision" | "display_decision"> & { nodes: LifecycleNode[]; edges: LifecycleEdge[]; activeNodeId: LifecycleStage; currentStage: LifecycleStage; severity: GraphSeverity; provenance: LifecycleProvenance; domain_decision: string; display_decision: GraphDecision };

export function emptyLifecycle(): LifecycleGraphState {
  return {
    case_id: "unavailable", mode: "EMPTY", nodes: [], edges: [], activeNodeId: "TARGET", activeEdgeIds: [], currentStage: "TARGET", severity: "UNKNOWN", provenance: "NORMALIZED_CASE", domain_decision: "not_evaluated", display_decision: "NOT_EVALUATED", evidenceRefs: [], message: "No canonical lifecycle projection is available.",
  };
}
