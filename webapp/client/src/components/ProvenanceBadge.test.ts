import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProvenanceBadge } from "./ProvenanceBadge";

describe("ProvenanceBadge", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders the deterministic AEGIS provenance label", () => {
    vi.stubGlobal("React", { createElement });
    const markup = renderToStaticMarkup(createElement(ProvenanceBadge, { provenance: "AEGIS_DETERMINISTIC" }));

    expect(markup).toContain("AEGIS deterministic");
    expect(markup).toContain("provenance-aegis_deterministic");
  });
});
