import { describe, expect, it } from "vitest";
import { existsSync } from "node:fs";
import { invokeAegis, resolvePythonExecutable, resolveRepositoryRoot } from "./aegisBridge";

describe("canonical AEGIS lifecycle adapter", () => {
  it("resolves the canonical root and never a vendored webapp duplicate", () => {
    const root = resolveRepositoryRoot();
    expect(existsSync(`${root}/src/aegis`)).toBe(true);
    expect(existsSync(`${root}/webapp/aegis_backend`)).toBe(false);
    expect(resolvePythonExecutable()).toMatch(/python/i);
  });

  it("projects the recorded Mission 029 terminal no-candidate boundary", () => {
    const result = invokeAegis({ action: "historical" });
    expect(result.case.case_id).toBe("mission_029_real_provider");
    expect(result.graph.mode).toBe("REAL_PROVIDER");
    expect(result.graph.domain_decision).toBe("blocked");
    expect(result.graph.display_decision).toBe("BLOCKED");
    expect(result.graph.nodes.find((node: { id: string }) => node.id === "CANDIDATE").display_status).toBe("UNAVAILABLE");
    expect(result.graph.nodes.find((node: { id: string }) => node.id === "COMMIT").display_status).toBe("BLOCKED");
  });

  it("projects the controlled replay with canonical verification, risk, and commit outcomes", () => {
    const result = invokeAegis({ action: "controlled" });
    expect(result.graph.mode).toBe("TEST_DOUBLE_CONTROLLED_REPLAY");
    expect(result.graph.domain_decision).toBe("reject");
    expect(result.graph.display_decision).toBe("REJECT");
    expect(result.replay.verification.overall_status).toBe("FAIL");
    expect(result.replay.output_eligible).toBe(false);
  });

  it("returns a read-only benchmark projection with controlled-harness provenance", () => {
    const result = invokeAegis({ action: "benchmark" });
    expect(result.status).toBe("AVAILABLE");
    expect(result.summary.controlled_aegis_metrics.provenance).toBe("TEST_DOUBLE_CONTROLLED_HARNESS");
  });
});
