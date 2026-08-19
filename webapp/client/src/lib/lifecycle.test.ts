import { describe, expect, it } from "vitest";
import { emptyLifecycle, type LifecycleGraphState } from "./lifecycle";

describe("AEGIS lifecycle presentation boundary", () => {
  it("keeps the unavailable fallback free of inferred nodes, edges, and decisions", () => {
    const graph = emptyLifecycle();
    expect(graph.nodes).toEqual([]);
    expect(graph.edges).toEqual([]);
    expect(graph.decision).toBe("NOT_EVALUATED");
  });

  it("preserves a canonical backend graph without deriving a replacement state", () => {
    const graph: LifecycleGraphState = {
      case_id: "controlled_silent_corruption", mode: "TEST_DOUBLE_CONTROLLED_REPLAY", activeNodeId: "COMMIT", activeEdgeIds: ["RISK->COMMIT"], currentStage: "COMMIT", severity: "ANOMALY", provenance: "TEST_DOUBLE", decision: "REJECT", evidenceRefs: ["contract://fixture"], message: "Backend-owned projection", edges: [{ id: "RISK->COMMIT", source: "RISK", target: "COMMIT", status: "BROKEN", provenance: "TEST_DOUBLE", evidenceRefs: ["contract://fixture"] }], nodes: [{ id: "RISK", label: "Risk", status: "ANOMALY", provenance: "TEST_DOUBLE", detail: "REJECT", evidenceRefs: ["contract://fixture"] }, { id: "COMMIT", label: "Commit gate", status: "BLOCKED", provenance: "TEST_DOUBLE", detail: "Output ineligible", evidenceRefs: ["contract://fixture"] }],
    };
    expect(graph.nodes.find((node) => node.id === "COMMIT")?.status).toBe("BLOCKED");
    expect(graph.decision).toBe("REJECT");
  });
});
