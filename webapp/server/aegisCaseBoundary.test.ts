import { describe, expect, it, beforeEach } from "vitest";
import { CaseBoundaryError, enforcePublicCaseCreationRateLimit, normalizeCreateCaseInput, resetCaseBoundaryRateLimitsForTest } from "./aegisCaseBoundary";
import { SEEDED_CASE_METADATA } from "./aegisSeedMetadata";

describe("public AEGIS case boundary", () => {
  beforeEach(resetCaseBoundaryRateLimitsForTest);
  it("normalizes a bounded public demo configuration", () => {
    const normalized = normalizeCreateCaseInput({ targetUrl: "HTTPS://Example.test/catalog/?b=2&a=1#ignored", fields: [{ name: " title ", type: "text", description: " title " }], invariants: [" title_present "], name: " Demo ", description: " bounded " });
    expect(normalized.targetUrl).toBe("https://example.test/catalog?a=1&b=2");
    expect(normalized.fields[0]?.name).toBe("title");
    expect(normalized.invariants).toEqual(["title_present"]);
  });
  it("rejects credential-bearing URLs and duplicate field names", () => {
    expect(() => normalizeCreateCaseInput({ targetUrl: "https://user:password@example.test", fields: [{ name: "x", type: "text", description: "" }], invariants: [] })).toThrow(CaseBoundaryError);
    expect(() => normalizeCreateCaseInput({ targetUrl: "https://example.test", fields: [{ name: "title", type: "text", description: "" }, { name: "TITLE", type: "text", description: "" }], invariants: [] })).toThrow("Field names must be unique");
  });
  it("rate-limits public demo creation while leaving the static list projection provider-free", () => {
    for (let index = 0; index < 5; index += 1) enforcePublicCaseCreationRateLimit("test-client", 1_000 + index);
    expect(() => enforcePublicCaseCreationRateLimit("test-client", 1_100)).toThrow("rate-limited");
    expect(SEEDED_CASE_METADATA.map((item) => item.case_id)).toEqual(["mission_029_real_provider", "mission_033_real_provider_candidate", "controlled_silent_corruption"]);
  });
});
