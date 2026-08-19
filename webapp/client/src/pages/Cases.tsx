/** Tensioned Signal Web: cases are backend-persisted configurations, not local browser fixtures. */
import { useEffect, useState } from "react";
import { Link } from "wouter";
import { AppShell } from "@/components/AppShell";
import { SensingField } from "@/components/SensingField";
import { ApiError, aegisApi, type CaseSummary } from "@/lib/aegisApi";
import { emptyLifecycle } from "@/lib/lifecycle";
import { ArrowRight, CircleDashed, Database, Plus, RefreshCw } from "lucide-react";

export default function Cases() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  async function loadCases() {
    setState("loading");
    try {
      const payload = await aegisApi.listCases();
      setCases(payload.cases);
      setState("ready");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The case API is unavailable.");
      setState("error");
    }
  }

  useEffect(() => { void loadCases(); }, []);

  return <AppShell><main className="cases-page">
    <section className="cases-head">
      <div><p className="eyebrow">Reliability cases</p><h1>What is AEGIS<br /><span className="bone-emphasis">protecting?</span></h1></div>
      <Link className="signal-button" href="/#create"><Plus size={16} /> New case</Link>
    </section>
    {state === "loading" && <section className="cases-status"><CircleDashed size={19} className="spin-once" /><div><span className="eyebrow">Loading backend cases</span><p>Reading persisted case configurations without starting any provider action.</p></div></section>}
    {state === "error" && <section className="cases-empty-system cases-api-boundary"><div className="cases-empty-art" aria-hidden="true"><SensingField state={emptyLifecycle()} presentation="unlit" /></div><div className="cases-empty-copy"><span className="eyebrow danger-text">Case API unavailable</span><h2>The sensing path <span className="danger-text">cannot read its records.</span></h2><p>{error} Persisted target, contract, artifact, and decision records remain unavailable until the local AEGIS API returns.</p><button type="button" className="outline-button" onClick={() => void loadCases()}><RefreshCw size={15} /> Retry connection</button></div><ol className="empty-evidence-spine is-unavailable" aria-label="Unavailable reliability case evidence path"><li><i />Target<br /><small>backend unavailable</small></li><li><i />Contract<br /><small>backend unavailable</small></li><li><i />Artifact<br /><small>backend unavailable</small></li><li><i />Decision<br /><small>backend unavailable</small></li></ol></section>}
    {state === "ready" && (cases.length ? <section className="case-list" aria-label="Persisted reliability cases">{cases.map((item, index) => <Link key={item.case_id} href={`/cases/${item.case_id}`} className="case-list-row"><span className="case-list-index">{String(index + 1).padStart(2, "0")}</span><div><h2>{item.name}</h2><p>{item.target_url}</p></div><span className="case-list-state">{item.evidence_status.replaceAll("_", " ")}</span><span className="case-list-events">{item.event_count} evidence event{item.event_count === 1 ? "" : "s"}</span><ArrowRight size={18} /></Link>)}</section> : <section className="cases-empty-system"><div className="cases-empty-art" aria-hidden="true"><SensingField state={emptyLifecycle()} presentation="unlit" /></div><div className="cases-empty-copy"><span className="eyebrow">No persisted cases</span><h2>A web change is <span className="bone-emphasis">not yet being watched.</span></h2><p>Protect a public target to persist a target, its extraction contract, and its invariants. A baseline is still required before AEGIS can form an observation.</p><Link className="signal-button" href="/#create">Create first case <ArrowRight size={15} /></Link></div><ol className="empty-evidence-spine" aria-label="Reliability case evidence path"><li><i />Target<br /><small>not configured</small></li><li><i />Contract<br /><small>not defined</small></li><li><i />Artifact<br /><small>not observed</small></li><li><i />Decision<br /><small>not evaluated</small></li></ol></section>) }
  </main></AppShell>;
}
