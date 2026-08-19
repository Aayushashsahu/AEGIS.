/**
 * AEGIS case experience: this is a controlled decision replay, not a provider run.
 * The graph makes independent evidence a branch before the fail-closed shipment gate.
 */
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ArrowLeft, ArrowRight, CircleAlert, LockKeyhole, Network, ShieldCheck } from "lucide-react";
import { Link } from "wouter";

type EvidenceNode = "expected" | "observed" | "contract" | "history" | "independent" | "untrusted" | "blocked";

const details: Record<EvidenceNode, { label: string; state: string; copy: string }> = {
  expected: { label: "Expected", state: "CONTRACT", copy: "The extraction contract expects a price bound to the intended product. This is controlled replay input, not a live target assertion." },
  observed: { label: "Observed", state: "SEMANTIC MISMATCH", copy: "The value remains structurally valid but is inconsistent with the intended product binding. This is the silent-corruption condition demonstrated by the replay." },
  contract: { label: "Contract evidence", state: "TYPE VALID / MEANING UNSUPPORTED", copy: "Schema and type alone do not establish that the observed price belongs to the expected product." },
  history: { label: "Historical evidence", state: "DIVERGENCE", copy: "Historical behavior is an independent channel only when a trusted baseline exists. In this replay it is explicitly modeled as a separate check." },
  independent: { label: "Independent evidence", state: "CONFLICT", copy: "A separate evidence source disagrees with the observed semantic binding. It is not double-counted with contract or history checks." },
  untrusted: { label: "Untrusted", state: "FAIL CLOSED", copy: "AEGIS withholds trust. A structurally valid output is not allowed to pass simply because it looks healthy." },
  blocked: { label: "Data not shipped", state: "COMMIT REFUSED", copy: "The commit gate remains closed. This controlled replay demonstrates a safety outcome, not a production decision." },
};

export default function SilentCorruption() {
  const [selected, setSelected] = useState<EvidenceNode>("observed");
  const node = details[selected];
  return <AppShell><main className="silent-case-page">
    <section className="silent-case-hero">
      <span className="source-pill source-replay">controlled decision replay</span>
      <p className="eyebrow">Case experience / silent corruption</p>
      <h1>Valid shape.<br /><span className="bone-emphasis">Wrong meaning.</span></h1>
      <p>This is the failure AEGIS is built to stop: an output can satisfy a schema and still be semantically wrong. The graph below is a controlled replay and does not claim a live provider result.</p>
    </section>

    <section className="silent-decision-map" aria-labelledby="silent-map-title">
      <div className="silent-map-heading"><div><span className="eyebrow">Decision web</span><h2 id="silent-map-title">Expected → observed → evidence → <span className="danger-text">untrusted</span> → data not shipped.</h2></div><span className="source-pill source-replay">branching evidence</span></div>
      <div className="silent-graph" role="group" aria-label="Controlled silent corruption evidence graph">
        <button className={`silent-node expected ${selected === "expected" ? "is-selected" : ""}`} onClick={() => setSelected("expected")}><small>01</small><b>Expected</b><span>contract binding</span></button>
        <span className="silent-edge edge-a" aria-hidden="true" />
        <button className={`silent-node observed ${selected === "observed" ? "is-selected" : ""}`} onClick={() => setSelected("observed")}><small>02</small><b>Observed</b><span>plausible value</span></button>
        <span className="silent-edge edge-b" aria-hidden="true" />
        <div className="evidence-branch" aria-label="Independent evidence channels">
          <button className={`silent-node evidence ${selected === "contract" ? "is-selected" : ""}`} onClick={() => setSelected("contract")}><small>03A</small><b>Contract</b><span>type valid</span></button>
          <button className={`silent-node evidence ${selected === "history" ? "is-selected" : ""}`} onClick={() => setSelected("history")}><small>03B</small><b>History</b><span>divergence</span></button>
          <button className={`silent-node evidence independent ${selected === "independent" ? "is-selected" : ""}`} onClick={() => setSelected("independent")}><small>03C</small><b>Independent</b><span>conflict</span></button>
        </div>
        <span className="silent-edge edge-c" aria-hidden="true" />
        <button className={`silent-node untrusted ${selected === "untrusted" ? "is-selected" : ""}`} onClick={() => setSelected("untrusted")}><small>04</small><b>Untrusted</b><span>fail closed</span></button>
        <span className="silent-edge edge-d" aria-hidden="true" />
        <button className={`silent-node blocked ${selected === "blocked" ? "is-selected" : ""}`} onClick={() => setSelected("blocked")}><small>05</small><b>Data not shipped</b><span>commit refused</span></button>
      </div>
      <aside className="silent-inspector" aria-live="polite"><span className="eyebrow">Selected boundary</span><h3>{node.label}</h3><strong>{node.state}</strong><p>{node.copy}</p><div><ShieldCheck size={15} /> Evidence channels are branches, not a weighted claim of independence.</div></aside>
    </section>

    <section className="silent-outcome"><div><CircleAlert size={20} /><span className="eyebrow">Safety outcome</span><h2>STRUCTURALLY VALID.<br /><span className="danger-text">SEMANTICALLY WRONG.</span></h2></div><div className="outcome-chain"><span>Expected</span><ArrowRight size={16} /><span>Observed</span><ArrowRight size={16} /><span>Evidence</span><ArrowRight size={16} /><b>Untrusted</b><ArrowRight size={16} /><strong><LockKeyhole size={15} /> Data not shipped</strong></div><p>There is no provider action, repair candidate, or live commit decision in this screen. It exists to make the fail-closed policy inspectable.</p></section>
    <Link href="/judge" className="back-link"><ArrowLeft size={16} /> Return to evidence replay</Link>
  </main></AppShell>;
}
