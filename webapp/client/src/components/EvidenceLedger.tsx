/**
 * Tensioned Signal Web: the ledger is a sparse vertical evidence rail that distinguishes local configuration from durable provider evidence.
 */
import { FileText, CircleDashed, Database, Info } from "lucide-react";
import type { ReliabilityCase } from "@/lib/aegis";

export function EvidenceLedger({ caseData }: { caseData: ReliabilityCase }) {
  return (
    <section className="ledger-panel" aria-labelledby="ledger-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Evidence ledger</span>
          <h2 id="ledger-title">Nothing is implied.</h2>
        </div>
        <span className="source-pill source-local"><CircleDashed size={13} /> local configuration</span>
      </div>

      <div className="ledger-spine">
        <article className="ledger-event">
          <span className="ledger-node"><FileText size={15} /></span>
          <div className="ledger-copy">
            <span className="ledger-type">Extraction contract prepared</span>
            <p>{caseData.fields.length} field{caseData.fields.length === 1 ? "" : "s"} and {caseData.invariants.length} invariant{caseData.invariants.length === 1 ? "" : "s"} were authored in this browser.</p>
          </div>
          <time dateTime={caseData.createdAt}>{new Date(caseData.createdAt).toLocaleString()}</time>
        </article>

        <article className="ledger-event is-muted">
          <span className="ledger-node"><Database size={15} /></span>
          <div className="ledger-copy">
            <span className="ledger-type">Provider evidence</span>
            <p>No collection, observation, or provider operation has been loaded for this case.</p>
          </div>
          <span className="ledger-state">not available</span>
        </article>

        <article className="ledger-event is-muted">
          <span className="ledger-node"><Info size={15} /></span>
          <div className="ledger-copy">
            <span className="ledger-type">Decision evidence</span>
            <p>Verification, Risk Governor, and Commit Gate remain unavailable until real candidate evidence is received.</p>
          </div>
          <span className="ledger-state">not evaluated</span>
        </article>
      </div>
    </section>
  );
}
