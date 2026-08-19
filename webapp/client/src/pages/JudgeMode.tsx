/**
 * Tensioned Signal Web: Judge Mode is a separated, evidence-first replay surface; it never casts a recorded collection as a successful repair.
 */
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { InteractiveLifecycleGraph } from "@/components/InteractiveLifecycleGraph";
import type { LifecycleGraphState } from "@/lib/lifecycle";
import { ArrowLeft, ArrowRight, Check, CircleAlert, Database, FileText, LockKeyhole, Play, ShieldAlert } from "lucide-react";
import { Link } from "wouter";
import { aegisApi, type RecordedReplay } from "@/lib/aegisApi";

const story = [
  ["Real Bright Data collector", "A named provider collector appears only when its recorded evidence is selected."],
  ["Recorded provider collection", "Collection facts are rendered from the selected artifact."],
  ["AEGIS establishes a baseline", "No baseline event is present in this selected artifact."],
  ["Controlled corruption", "No controlled corruption record is selected."],
  ["Signal detected", "No detection event is present in this selected artifact."],
  ["Diagnosis", "No diagnosis event is present in this selected artifact."],
  ["Bright Data heal", "No provider heal attempt is present in this selected artifact."],
  ["Unverified candidate", "No repair candidate is present in this selected artifact."],
  ["Independent evidence", "Contract, history, semantic, and independent evidence cannot be evaluated without a candidate."],
  ["Risk decision", "No Risk Governor decision is present in this selected artifact."],
  ["Commit gate", "No commit decision is present in this selected artifact."],
  ["Data shipped or blocked", "No shipment status is present in this selected artifact."],
];

export default function JudgeMode() {
  const [controlled, setControlled] = useState(false);
  const [historical, setHistorical] = useState<RecordedReplay | null>(null);
  const [historicalGraph, setHistoricalGraph] = useState<LifecycleGraphState | null>(null);
  const [controlledGraph, setControlledGraph] = useState<LifecycleGraphState | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { void Promise.all([aegisApi.getHistoricalProviderReplay(), aegisApi.getGraph("mission_029_real_provider"), aegisApi.getGraph("controlled_silent_corruption")]).then(([replay, historicalState, controlledState]) => { setHistorical(replay); setHistoricalGraph(historicalState as LifecycleGraphState); setControlledGraph(controlledState as LifecycleGraphState); }).catch(() => { setError("Historical provider evidence availability could not be read."); setHistorical({ status: "NOT_AVAILABLE", presentation: "HISTORICAL_REAL_PROVIDER_EVIDENCE", reason: "Historical provider evidence availability could not be read." }); }); }, []);
  const hasHistorical = historical?.status === "AVAILABLE" && historicalGraph?.mode === "REAL_PROVIDER";

  return (
    <AppShell>
      <main className="judge-page">
        <section className="judge-hero">
          <div className="judge-hero-copy">
            <span className={hasHistorical ? "source-pill source-real" : "source-pill source-local"}><Database size={12} /> Mission 029 / historical provider opening</span>
            <p className="eyebrow">Judge mode / evidence boundary</p>
            <h1>Start with what the provider <span className="bone-emphasis">actually recorded.</span></h1>
            <p className="judge-intro">Mission 029 is the real-provider opening when its canonical artifact is present. Candidate, verification, risk, and decision belong to a separate controlled replay unless persisted evidence exists.</p>
            {hasHistorical ? <p className="historical-boundary"><Check size={14} /> Canonical Mission 029 evidence is available. Its artifact paths are listed below; no later lifecycle state is inferred from it.</p> : <p className="historical-boundary"><CircleAlert size={14} /> {historical?.reason ?? "Mission 029 historical provider evidence is not installed in the canonical artifact directory."} AEGIS will not claim its collector, anomaly, or heal-failure details without that evidence.</p>}
            <button className="signal-button" onClick={() => setControlled(true)}><Play size={16} fill="currentColor" /> Enter controlled decision replay</button>
          </div>
          <span className="judge-count">01 — 12</span>
        </section>

        <section className="judge-path-spine" aria-label="Historical provider and controlled replay boundary"><span className={hasHistorical ? "source-pill source-real" : "source-pill source-local"}>historical → controlled</span><ol><li className={hasHistorical ? "is-supported" : "is-boundary"}><i /><b>Mission 029 evidence</b><small>{hasHistorical ? "canonical artifact present" : "artifact unavailable"}</small></li><li className={hasHistorical ? "is-supported" : "is-boundary"}><i /><b>Provider record</b><small>{hasHistorical ? "historical evidence only" : "not asserted"}</small></li><li className={controlled ? "is-supported" : ""}><i /><b>Controlled candidate</b><small>{controlled ? "replay boundary entered" : "separate replay"}</small></li><li className={controlled ? "is-boundary" : ""}><i /><b>Decision gate</b><small>{controlled ? "blocked in replay" : "not evaluated"}</small></li></ol></section>

        {controlled && controlledGraph && <section className="judge-semantic-workspace"><div className="panel-heading"><div><span className="eyebrow">Controlled replay / candidate to decision</span><h2>Later stages are <span className="bone-emphasis">demonstrated, not claimed.</span></h2></div><span className="source-pill source-replay">controlled replay</span></div><InteractiveLifecycleGraph state={controlledGraph} title="Controlled candidate-to-decision graph" /><p className="controlled-graph-note"><CircleAlert size={15} /> {controlledGraph.message}</p><Link href="/silent-corruption" className="outline-button">Open silent corruption decision screen <ArrowRight size={16} /></Link></section>}

        <section className="story-rail" aria-label="Judge Mode narrative">
          {story.map(([entry, detail], index) => (
            <div className={`story-step ${hasHistorical && index < 2 ? "is-supported" : ""} ${controlled && index > 1 ? "is-supported" : ""} ${!hasHistorical && index < 2 ? "is-unavailable" : ""} ${!controlled && index > 1 ? "is-unavailable" : ""}`} key={entry}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><h2>{entry}</h2><p>{detail}</p></div>
              {(hasHistorical && index < 2) || (controlled && index > 1) ? <Check size={18} /> : <span className="step-dot" />}
            </div>
          ))}
        </section>

        {hasHistorical ? (
          <section className="recorded-evidence" aria-labelledby="replay-title">
            <div className="recorded-evidence-main">
              <div className="source-pill source-real"><span className="live-dot" /> real provider / historical record</div>
              <p className="eyebrow">Mission 029 opening evidence</p>
              <h2 id="replay-title">Provider record available. <em>Trust still withheld.</em></h2>
              <p>The historical provider artifacts establish only the facts they contain. Later repair, candidate, verification, risk, and commit claims remain unavailable unless their own evidence appears.</p>
            </div>
            <dl className="evidence-facts"><div><dt>Provenance</dt><dd>REAL PROVIDER</dd></div><div><dt>Artifacts</dt><dd>{historical.artifacts?.length ?? 0}</dd></div><div><dt>Authority</dt><dd>Evidence only</dd></div><div><dt>Commit</dt><dd className="danger-text">Not implied</dd></div></dl>
          </section>
        ) : (
          <section className="evidence-empty-hero">
            <FileText size={24} />
            <div><span className="eyebrow">Mission 029 historical boundary</span><h2>{error ? "Historical opening unavailable." : "No canonical Mission 029 artifact is installed."}</h2><p>{error || "The product preserves the real-provider opening as unavailable rather than filling it with inferred collector, anomaly, or heal-failure claims."}</p></div>
          </section>
        )}

        <section className="truth-grid">
          <div><Database size={19} /><span className="eyebrow">Bright Data</span><h3>Collection and healing infrastructure</h3><p>Provider activity is shown as recorded operational evidence, never relabeled as an AEGIS decision.</p></div>
          <div><ShieldAlert size={19} /><span className="eyebrow">AEGIS</span><h3>Verification, risk, and commit control</h3><p>Candidate data remains unverified until deterministic channels and the Risk Governor have produced an evidence-backed result.</p></div>
          <div><LockKeyhole size={19} /><span className="eyebrow">Safety boundary</span><h3>No candidate, no verification, no shipment</h3><p>The selected collection artifact does not prove a repair; it cannot be turned into a successful healing story by the interface.</p></div>
        </section>

        <section className="candidate-boundary"><span className="source-pill source-local">candidate gate</span><h2>AI proposes.<br /><span className="bone-emphasis">Evidence decides.</span></h2><div className="candidate-channels"><span>Contract<small>not evaluable</small></span><span>History<small>not evaluable</small></span><span>Semantic<small>not evaluable</small></span><span>Independent evidence<small>not evaluable</small></span></div><p>No candidate exists in the selected record, so AEGIS cannot activate verification, Risk Governor, or commit gate states.</p></section>

        <Link href="/" className="back-link"><ArrowLeft size={16} /> Return to cases</Link>
      </main>
    </AppShell>
  );
}
