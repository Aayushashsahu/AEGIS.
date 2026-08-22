/** AEGIS provenance badge: prevents real, replay, and controlled records from being conflated. */
import type { LifecycleProvenance } from "@/lib/lifecycle";

const labels: Record<LifecycleProvenance, string> = { USER_CONFIGURED: "user configured", NORMALIZED_CASE: "persisted evidence", REAL_PROVIDER: "real provider", REPLAY: "replay", TEST_DOUBLE: "test double", CONTROLLED_DEMONSTRATOR: "controlled demonstrator", AEGIS_DETERMINISTIC: "AEGIS deterministic" };

export function ProvenanceBadge({ provenance }: { provenance: LifecycleProvenance }) {
  return <span className={`provenance-badge provenance-${provenance.toLowerCase()}`}>{labels[provenance]}</span>;
}
