import { describe, expect, it } from "vitest";
import { emptyLifecycle, type LifecycleGraphState } from "./lifecycle";

describe("AEGIS lifecycle presentation boundary", () => {
  it("keeps the unavailable fallback free of inferred nodes, edges, and decisions", () => {
    const graph = emptyLifecycle();
    expect(graph.nodes).toEqual([]);
    expect(graph.edges).toEqual([]);
    expect(graph.display_decision).toBe("NOT_EVALUATED");
  });

  it("preserves a canonical backend graph without deriving a replacement state", () => {
    const graph: LifecycleGraphState = {
      case_id: "controlled_silent_corruption", mode: "TEST_DOUBLE_CONTROLLED_REPLAY", activeNodeId: "COMMIT", activeEdgeIds: ["RISK->COMMIT"], currentStage: "COMMIT", severity: "ANOMALY", provenance: "TEST_DOUBLE", domain_decision: "reject", display_decision: "REJECT", evidenceRefs: ["contract://fixture"], message: "Backend-owned projection", edges: [{ id: "RISK->COMMIT", source: "RISK", target: "COMMIT", domain_status: "commit_ineligible", display_status: "BROKEN", provenance: "TEST_DOUBLE", evidenceRefs: ["contract://fixture"] }], nodes: [{ id: "RISK", label: "Risk", domain_status: "risk_reject", display_status: "ANOMALY", provenance: "TEST_DOUBLE", detail: "REJECT", evidenceRefs: ["contract://fixture"] }, { id: "COMMIT", label: "Commit gate", domain_status: "commit_ineligible", display_status: "BLOCKED", provenance: "TEST_DOUBLE", detail: "Output ineligible", evidenceRefs: ["contract://fixture"] }],
    };
    expect(graph.nodes.find((node) => node.id === "COMMIT")?.display_status).toBe("BLOCKED");
    expect(graph.display_decision).toBe("REJECT");
  });
});
