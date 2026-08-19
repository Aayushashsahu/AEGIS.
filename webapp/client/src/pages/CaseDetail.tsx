/** Tensioned Signal Web: case state, evidence, and graph nodes are always read from the normalized API. */
import { useEffect, useState } from "react";
import { Link, useRoute } from "wouter";
import { AppShell } from "@/components/AppShell";
import { InteractiveLifecycleGraph } from "@/components/InteractiveLifecycleGraph";
import { SensingField } from "@/components/SensingField";
import { ApiError, aegisApi, type ApiCase, type CaseGraph, type EvidenceEvent } from "@/lib/aegisApi";
import { Activity, ArrowLeft, CircleDashed, Database, ExternalLink, FileText, Network, ShieldAlert } from "lucide-react";

type View = "overview" | "evidence" | "web";

const nodePositions = [[12, 58], [30, 26], [48, 63], [63, 32], [79, 56], [89, 21], [68, 83], [40, 87]];

function StatusBlock({ status }: { status: string }) {
  const statusText = status.replaceAll("_", " ");
  return <div className={`state-block ${status === "NOT_FOUND" ? "is-pending" : ""}`}><span className="eyebrow">Current health</span><strong>{statusText}</strong><p>{status === "NOT_FOUND" ? "Baseline required before health can be determined." : "Derived from append-only AEGIS evidence."}</p></div>;
}

export default function CaseDetail() {
  const [, params] = useRoute("/cases/:caseId");
  const caseId = params?.caseId ?? "";
  const [caseData, setCaseData] = useState<ApiCase | null>(null);
  const [events, setEvents] = useState<EvidenceEvent[]>([]);
  const [graph, setGraph] = useState<CaseGraph | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [view, setView] = useState<View>("web");
  const lifecycle = graph;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setState("loading");
      try {
        const [loadedCase, evidence, loadedGraph] = await Promise.all([aegisApi.getCase(caseId), aegisApi.getEvidence(caseId), aegisApi.getGraph(caseId)]);
        if (cancelled) return;
        setCaseData(loadedCase); setEvents(evidence.events); setGraph(loadedGraph); setState("ready");
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof ApiError ? cause.message : "The case API is unavailable."); setState("error");
      }
    }
    void load(); return () => { cancelled = true; };
  }, [caseId]);

  return <AppShell><main className="case-workspace">
    <Link href="/cases" className="back-link"><ArrowLeft size={15} /> Cases</Link>
    {state === "loading" && <section className="cases-status"><CircleDashed size={19} className="spin-once" /><div><span className="eyebrow">Loading case</span><p>Reading canonical case configuration and append-only evidence.</p></div></section>}
    {state === "error" && <section className="cases-status is-error"><Database size={20} /><div><span className="eyebrow">Case unavailable</span><h2>AEGIS could not load this case.</h2><p>{error}</p></div><Link className="outline-button" href="/cases">Return to cases</Link></section>}
    {state === "ready" && caseData && <>
      <header className="case-header"><div className="case-breadcrumb"><span>Cases</span><span> / </span><span className="mono">{caseData.case_id}</span></div><div className="case-heading-grid"><div><p className="eyebrow">Reliability case</p><h1>{caseData.name}</h1><a className="case-target" href={caseData.target_url} target="_blank" rel="noreferrer">{caseData.target_url}<ExternalLink size={14} /></a>{caseData.description && <p className="case-description">{caseData.description}</p>}</div><StatusBlock status={caseData.lifecycle.current_status} /></div><div className="case-facts"><span><Database size={14} /> Backend persisted</span><span><FileText size={14} /> {caseData.fields.length} field{caseData.fields.length === 1 ? "" : "s"}</span><span><Activity size={14} /> {caseData.invariants.length} invariant{caseData.invariants.length === 1 ? "" : "s"}</span><span><Network size={14} /> {caseData.lifecycle.event_count} evidence event{caseData.lifecycle.event_count === 1 ? "" : "s"}</span><span><Network size={14} /> Bright Data provider boundary</span>{caseData.collector_id && <span><Network size={14} /> Collector configured</span>}</div></header>
      <div className="workspace-tabs" role="tablist" aria-label="Case views">{(["overview", "evidence", "web"] as View[]).map((item) => <button key={item} type="button" role="tab" aria-selected={view === item} className={view === item ? "is-active" : ""} onClick={() => setView(item)}>{item === "web" ? "Lifecycle graph" : item}</button>)}</div>
      {view === "overview" && <><section className="workspace-focus"><div className="focus-copy"><span className="source-pill source-local"><Database size={13} /> persisted configuration</span><p className="eyebrow">Next safe action</p><h2>Await evidence before <span className="bone-emphasis">making a claim.</span></h2><p>{caseData.action_policy}</p></div><div className="focus-image">{lifecycle && <SensingField state={lifecycle} presentation="case" />}</div><div className="focus-callout"><ShieldAlert size={16} /> Bright Data collection or repair is not invoked by this case configuration.</div></section><section className="contract-summary"><div><span className="eyebrow">Configured protection boundary</span><h2>The case knows what to protect.</h2></div><div className="contract-columns"><div><span className="summary-label">Fields</span>{caseData.fields.map((field) => <p key={field.name}><b>{field.name}</b><span>{field.type}</span>{field.description && <small>{field.description}</small>}</p>)}</div><div><span className="summary-label">Invariants</span>{caseData.invariants.length ? caseData.invariants.map((invariant) => <p className="invariant-summary mono" key={invariant}>{invariant}</p>) : <p className="empty-copy">No invariants were supplied.</p>}<span className="summary-label case-config-label">Collection boundary</span><p className="case-config-detail"><b>Provider</b><span>Bright Data Scraper Studio</span>{caseData.collector_id ? <small>Configured collector: {caseData.collector_id}</small> : <small>No collector reference is configured.</small>}<small>No scheduler or monitoring action is connected to this case.</small></p></div></div></section></>}
      {view === "evidence" && <section className="ledger-panel"><div className="panel-heading"><div><span className="eyebrow">Evidence ledger</span><h2>What AEGIS can <span className="bone-emphasis">prove.</span></h2></div><span className="source-pill source-local">append-only audit projection</span></div>{events.length ? <div className="ledger-spine">{events.map((event) => <article className="ledger-event" key={event.event_id}><span className="ledger-node"><FileText size={15} /></span><div className="ledger-copy"><span className="ledger-type">{event.label}</span><p>{event.provenance.replaceAll("_", " ")} · {event.status.replaceAll("_", " ")}</p><small className="event-meta">Correlation: {event.correlation_id ?? caseData.correlation_id} · Event: {event.event_id}</small>{event.evidence_refs.length ? <small className="event-ref">{event.evidence_refs.join(" · ")}</small> : <small className="event-ref is-empty">No evidence reference attached.</small>}</div><time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleString()}</time></article>)}</div> : <section className="evidence-empty-hero"><FileText size={24} /><div><span className="eyebrow">No lifecycle evidence</span><h2>Configuration is not evidence.</h2><p>A collector, observation, and AEGIS lifecycle event have not yet been persisted for this case.</p></div></section>}</section>}
      {view === "web" && lifecycle && <section className="case-semantic-workspace"><div className="panel-heading"><div><span className="eyebrow">Interactive lifecycle graph</span><h2>What happened, why, evidence, and <span className="bone-emphasis">what comes next.</span></h2></div><span className="source-pill source-local">normalized case + audit evidence</span></div><div className="case-graph-primary"><InteractiveLifecycleGraph state={lifecycle} title="Case lifecycle graph" /><aside className="case-graph-summary"><div><span className="eyebrow">Current state</span><b>{caseData.lifecycle.current_status.replaceAll("_", " ")}</b></div><div><span className="eyebrow">Next action</span><p>{caseData.action_policy}</p></div><div><span className="eyebrow">Evidence summary</span><p>{events.length ? `${events.length} append-only event${events.length === 1 ? "" : "s"} can be inspected in the ledger.` : "No observation or lifecycle evidence is recorded yet."}</p></div></aside></div><div className="case-graph-policy"><span>Provider boundary: Bright Data Scraper Studio proposes collection or repair only when a documented operation exists.</span><span>AEGIS authority: evidence, verification, risk, quarantine, and commit eligibility.</span></div></section>}
    </>}
  </main></AppShell>;
}
