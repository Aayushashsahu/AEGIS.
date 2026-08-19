import { describe, expect, it } from "vitest";
import { mission033TargetHtml, mission033TargetVersion } from "./mission033Target";

describe("Mission 033 owned public target", () => {
  it("exposes the initial stable contract before the controlled markup drift", () => {
    const html = mission033TargetHtml();

    expect(mission033TargetVersion).toBe("v1");
    expect(html).toContain('data-target-version="v1"');
    expect(html).toContain("AEGIS Verification Widget");
    expect(html).toContain("$599.00");
    expect(html).toContain("Available");
  });
});
