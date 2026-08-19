import { describe, expect, it } from "vitest";
import { mission033TargetHtml, mission033TargetVersion } from "./mission033Target";

describe("Mission 033 owned public target", () => {
  it("exposes the v2 controlled markup drift while retaining the public business facts", () => {
    const html = mission033TargetHtml();

    expect(mission033TargetVersion).toBe("v2");
    expect(html).toContain('data-target-version="v2"');
    expect(html).toContain("AEGIS Verification Widget");
    expect(html).toContain("USD 599.00");
    expect(html).toContain("Available");
    expect(html).not.toContain("product-price");
  });
});
