/** Judge Mode is an evidence-first replay surface and never casts recorded collection output as a successful repair. */
import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { InteractiveLifecycleGraph } from "@/components/InteractiveLifecycleGraph";
import type { LifecycleGraphState } from "@/lib/lifecycle";
import { ArrowLeft, ArrowRight, Check, CircleAlert, Database, FileText, LockKeyhole, Play, ShieldAlert } from "lucide-react";
import { Link } from "wouter";
import { aegisApi, type LifecyclePayload, type RecordedReplay, type SupportLedgerStatus } from "@/lib/aegisApi";

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
  const [causalBoundary, setCausalBoundary] = useState<LifecyclePayload | null>(null);
  const [controlledGraph, setControlledGraph] = useState<LifecycleGraphState | null>(null);
  const [supportStatus, setSupportStatus] = useState<SupportLedgerStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([
      aegisApi.getHistoricalProviderReplay(),
      aegisApi.getGraph("mission_029_real_provider"),
      aegisApi.getLifecycle("mission_050_real_provider_causal_boundary"),
      aegisApi.getGraph("controlled_silent_corruption"),
      aegisApi.getSupportStatus(),
    ]).then(([replay, historicalState, causalState, controlledState, support]) => {
      setHistorical(replay);
      setHistoricalGraph(historicalState as LifecycleGraphState);
      setCausalBoundary(causalState);
      setControlledGraph(controlledState as LifecycleGraphState);
      setSupportStatus(support);
    }).catch(() => {
      setError("Historical provider evidence availability could not be read.");
      setHistorical({ status: "NOT_AVAILABLE", presentation: "HISTORICAL_REAL_PROVIDER_EVIDENCE", reason: "Historical provider evidence availability could not be read." });
    });
  }, []);

  const hasHistorical = historical?.status === "AVAILABLE" && historicalGraph?.mode === "REAL_PROVIDER";
  const causalReplay = causalBoundary?.replay as { real_provider_chain?: Record<string, string | number | string[]>; cause?: string; confidence?: string; reason?: string; evidence_records?: Array<{ mission: string; label: string; provenance: string; status: string; path: string }>; controlled_replay_boundary?: { provenance: string; status: string; statement: string } } | undefined;
  const causalGraph = causalBoundary?.graph as LifecycleGraphState | undefined;

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
            <Link href="/cases/mission_033_real_provider_candidate" className="outline-button">Open Mission 033 real candidate evidence <ArrowRight size={16} /></Link>
          </div>
          <span className="judge-count">01 — 12</span>
        </section>

        <section className="judge-path-spine" aria-label="Historical provider and controlled replay boundary"><span className={hasHistorical ? "source-pill source-real" : "source-pill source-local"}>historical → controlled</span><ol><li className={hasHistorical ? "is-supported" : "is-boundary"}><i /><b>Mission 029 evidence</b><small>{hasHistorical ? "canonical artifact present" : "artifact unavailable"}</small></li><li className={hasHistorical ? "is-supported" : "is-boundary"}><i /><b>Provider record</b><small>{hasHistorical ? "historical evidence only" : "not asserted"}</small></li><li className={controlled ? "is-supported" : ""}><i /><b>Controlled candidate</b><small>{controlled ? "replay boundary entered" : "separate replay"}</small></li><li className={controlled ? "is-boundary" : ""}><i /><b>Decision gate</b><small>{controlled ? "blocked in replay" : "not evaluated"}</small></li></ol></section>

        {causalReplay && causalGraph && <section className="judge-causal-boundary" aria-labelledby="causal-boundary-title">
          <div className="panel-heading"><div><span className="eyebrow">Real provider / observed output boundary</span><h2 id="causal-boundary-title">HTTP success did not make the output <span className="bone-emphasis">safe.</span></h2></div><span className="source-pill source-real">real provider</span></div>
          <div className="causal-state-rail" aria-label="Real provider output fail-closed state"><div><b>REAL PROVIDER</b><small>HTTP {causalReplay.real_provider_chain?.http_status}</small></div><div><b>EXTRACTED OUTPUT</b><small>input.url only</small></div><div className="is-missing"><b>REQUIRED FIELDS</b><small>title · price · availability<br />MISSING</small></div><div className="is-fail"><b>AEGIS VERIFICATION</b><small>{causalReplay.real_provider_chain?.verification}</small></div><div className="is-fail"><b>RISK</b><small>{causalReplay.real_provider_chain?.risk}</small></div><div className="is-fail"><b>COMMIT</b><small>{causalReplay.real_provider_chain?.commit}</small></div><div className="is-fail"><b>DATA SHIPPED</b><small>{causalReplay.real_provider_chain?.data_shipped}</small></div></div>
          <div className="causal-forensic-boundary"><span className="source-pill source-local">forensic boundary</span><div><span className="eyebrow">Provider runtime cause</span><h3>{causalReplay.cause} <small>confidence {causalReplay.confidence}</small></h3><p>{causalReplay.reason}</p></div></div>
          <InteractiveLifecycleGraph state={causalGraph} title="Real provider causal-boundary graph" />
          <div className="causal-evidence-ledger"><div><span className="eyebrow">Separate provenance records</span><h3>Evidence stays separate until correlation is proven.</h3></div><ol>{causalReplay.evidence_records?.map((record) => <li key={record.mission}><b>Mission {record.mission}</b><span>{record.label}</span><small>{record.provenance} / {record.status}</small><code>{record.path}</code></li>)}</ol><p><strong>{causalReplay.controlled_replay_boundary?.provenance}</strong> / {causalReplay.controlled_replay_boundary?.status}: {causalReplay.controlled_replay_boundary?.statement}</p></div>
        </section>}

        <section className="candidate-boundary" aria-labelledby="support-ledger-title">
          <span className="source-pill source-local">Bright Data support / evidence ledger</span>
          <h2 id="support-ledger-title">{supportStatus?.status === "DIAGNOSIS_RECEIVED" ? "Diagnosis received." : "Diagnosis pending."}<br /><span className="bone-emphasis">The provider lane remains frozen.</span></h2>
          <p>{supportStatus?.recommendedAction ?? "Support ledger status is unavailable; AEGIS will not infer a provider diagnosis."}</p>
          <div className="candidate-channels"><span>Provider diagnosis<small>{supportStatus?.diagnosis ?? "not received"}</small></span><span>Provider error<small>{supportStatus?.providerError ?? "not asserted"}</small></span><span>Evidence reference<small>{supportStatus?.evidenceReference ?? "unavailable"}</small></span><span>Provider calls<small>{supportStatus?.providerCalls ?? 0} / mutations {supportStatus?.providerMutations ?? 0}</small></span></div>
        </section>

        {controlled && controlledGraph && <section className="judge-semantic-workspace"><div className="panel-heading"><div><span className="eyebrow">Controlled replay / candidate to decision</span><h2>Later stages are <span className="bone-emphasis">demonstrated, not claimed.</span></h2></div><span className="source-pill source-replay">controlled replay</span></div><InteractiveLifecycleGraph state={controlledGraph} title="Controlled candidate-to-decision graph" /><p className="controlled-graph-note"><CircleAlert size={15} /> {controlledGraph.message}</p><div className="judge-replay-actions"><Link href="/silent-corruption" className="outline-button">Open silent corruption decision screen <ArrowRight size={16} /></Link><Link href="/downstream" className="outline-button">Open blocked downstream proof <ArrowRight size={16} /></Link></div></section>}

        <section className="story-rail" aria-label="Judge Mode narrative">{story.map(([entry, detail], index) => <div className={`story-step ${hasHistorical && index < 2 ? "is-supported" : ""} ${controlled && index > 1 ? "is-supported" : ""} ${!hasHistorical && index < 2 ? "is-unavailable" : ""} ${!controlled && index > 1 ? "is-unavailable" : ""}`} key={entry}><span>{String(index + 1).padStart(2, "0")}</span><div><h2>{entry}</h2><p>{detail}</p></div>{(hasHistorical && index < 2) || (controlled && index > 1) ? <Check size={18} /> : <span className="step-dot" />}</div>)}</section>

        {hasHistorical ? <section className="recorded-evidence" aria-labelledby="replay-title"><div className="recorded-evidence-main"><div className="source-pill source-real"><span className="live-dot" /> real provider / historical record</div><p className="eyebrow">Mission 029 opening evidence</p><h2 id="replay-title">Provider record available. <em>Trust still withheld.</em></h2><p>The historical provider artifacts establish only the facts they contain. Later repair, candidate, verification, risk, and commit claims remain unavailable unless their own evidence appears.</p></div><dl className="evidence-facts"><div><dt>Provenance</dt><dd>REAL PROVIDER</dd></div><div><dt>Artifacts</dt><dd>{historical.artifacts?.length ?? 0}</dd></div><div><dt>Authority</dt><dd>Evidence only</dd></div><div><dt>Commit</dt><dd className="danger-text">Not implied</dd></div></dl></section> : <section className="evidence-empty-hero"><FileText size={24} /><div><span className="eyebrow">Mission 029 historical boundary</span><h2>{error ? "Historical opening unavailable." : "No canonical Mission 029 artifact is installed."}</h2><p>{error || "The product preserves the real-provider opening as unavailable rather than filling it with inferred collector, anomaly, or heal-failure claims."}</p></div></section>}

        <section className="truth-grid"><div><Database size={19} /><span className="eyebrow">Bright Data</span><h3>Collection and healing infrastructure</h3><p>Provider activity is shown as recorded operational evidence, never relabeled as an AEGIS decision.</p></div><div><ShieldAlert size={19} /><span className="eyebrow">AEGIS</span><h3>Verification, risk, and commit control</h3><p>Candidate data remains unverified until deterministic channels and the Risk Governor have produced an evidence-backed result.</p></div><div><LockKeyhole size={19} /><span className="eyebrow">Safety boundary</span><h3>No candidate, no verification, no shipment</h3><p>The selected collection artifact does not prove a repair; it cannot be turned into a successful healing story by the interface.</p></div></section>

        <section className="candidate-boundary"><span className="source-pill source-local">candidate gate</span><h2>AI proposes.<br /><span className="bone-emphasis">Evidence decides.</span></h2><div className="candidate-channels"><span>Contract<small>not evaluable</small></span><span>History<small>not evaluable</small></span><span>Semantic<small>not evaluable</small></span><span>Independent evidence<small>not evaluable</small></span></div><p>No candidate exists in the selected record, so AEGIS cannot activate verification, Risk Governor, or commit gate states.</p></section>

        <section className="candidate-boundary mission033-judge-boundary"><span className="source-pill source-real">Mission 033 / real provider candidate</span><h2>Verification passed.<br /><span className="bone-emphasis">Later output was still blocked.</span></h2><div className="candidate-channels"><span>Contract<small>PASS / deterministic</small></span><span>History<small>PASS / deterministic</small></span><span>Semantic<small>PASS / deterministic</small></span><span>Independent evidence<small>PASS / owned target</small></span></div><p>This real-provider path records an awaiting-approval preview, AEGIS verification PASS, and risk ACCEPT. Mission 040 approval and the Mission 041B rerun are preserved separately above: the rerun returned input.url only, so verification failed, risk rejected, commit blocked, and no data shipped. This panel does not claim corrected live output.</p><Link href="/cases/mission_033_real_provider_candidate" className="outline-button">Inspect the real candidate boundary <ArrowRight size={16} /></Link></section>

        <Link href="/" className="back-link"><ArrowLeft size={16} /> Return to cases</Link>
      </main>
    </AppShell>
  );
}
