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

  it("projects the real-provider incomplete-output causal boundary without inventing a provider cause", () => {
    const result = invokeAegis({ action: "mission050" });
    expect(result.graph.mode).toBe("REAL_PROVIDER_CAUSAL_BOUNDARY");
    expect(result.graph.provenance).toBe("REAL_PROVIDER");
    expect(result.replay.real_provider_chain).toMatchObject({ http_status: 200, verification: "FAIL", risk: "REJECT", commit: "BLOCKED", data_shipped: "NO" });
    expect(result.replay.real_provider_chain.required_fields).toEqual({ title: "MISSING", price: "MISSING", availability: "MISSING" });
    expect(result.replay.cause).toBe("UNKNOWN");
    expect(result.replay.output_eligible).toBe(false);
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

  it("projects a controlled downstream output that is blocked by canonical verification, risk, and commit decisions", () => {
    const result = invokeAegis({ action: "downstream" });
    expect(result.provenance).toBe("TEST_DOUBLE");
    expect(result.product.expected_price).toBe(599);
    expect(result.product.observed_price).toBe(29.99);
    expect(result.verification.status).toBe("FAIL");
    expect(result.risk.decision).toBe("REJECT");
    expect(result.commit.eligibility).toBe("BLOCKED");
    expect(result.output.eligible).toBe(false);
  });
});
