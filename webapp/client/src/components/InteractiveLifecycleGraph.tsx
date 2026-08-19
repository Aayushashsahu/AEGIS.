/**
 * AEGIS lifecycle graph: a selectable web of product stages with provenance,
 * evidence references, and explicit unavailable or fail-closed states.
 */
import { useEffect, useState } from "react";
import { ArrowRight, ExternalLink, ShieldAlert } from "lucide-react";
import type { LifecycleGraphState, LifecycleNode, LifecycleStage } from "@/lib/lifecycle";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { StatusBadge } from "./StatusBadge";

const positions: Record<LifecycleStage, { x: number; y: number }> = {
  TARGET: { x: 7, y: 50 }, COLLECTOR: { x: 20, y: 22 }, OBSERVATION: { x: 34, y: 50 }, DETECTION: { x: 47, y: 22 }, DIAGNOSIS: { x: 60, y: 50 }, REPAIR: { x: 73, y: 22 }, CANDIDATE: { x: 83, y: 50 }, VERIFICATION: { x: 73, y: 78 }, RISK: { x: 47, y: 78 }, COMMIT: { x: 20, y: 78 },
};

export function InteractiveLifecycleGraph({ state, title = "AEGIS lifecycle graph" }: { state: LifecycleGraphState; title?: string }) {
  const [selectedId, setSelectedId] = useState<LifecycleStage>(state.activeNodeId);
  useEffect(() => setSelectedId(state.activeNodeId), [state.activeNodeId]);
  const selected = state.nodes.find((node) => node.id === selectedId) ?? state.nodes[0];
  if (!selected) return <section className="interactive-lifecycle is-empty" aria-label={title}><p>{state.message}</p></section>;

  return <section className={`interactive-lifecycle mode-${state.mode.toLowerCase()}`} aria-label={title}>
    <div className="lifecycle-canvas">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <g className="lifecycle-web-guides"><path d="M7 50 L20 22 L47 8 L73 22 L93 50 L73 78 L47 92 L20 78 Z" /><path d="M20 22 L34 50 L47 22 L60 50 L73 22 M20 78 L47 78 L73 78 M7 50 L34 50 L60 50 L93 50" /><path d="M47 8 L47 92 M20 22 L73 78 M73 22 L20 78" /></g>
        {state.edges.map((edge) => <line key={edge.id} className={`is-${edge.display_status.toLowerCase()} edge-${edge.provenance.toLowerCase()} ${state.activeEdgeIds.includes(edge.id) ? "is-active-edge" : ""}`} x1={positions[edge.source].x} y1={positions[edge.source].y} x2={positions[edge.target].x} y2={positions[edge.target].y} />)}
      </svg>
      {state.nodes.map((node) => <button type="button" key={node.id} className={`lifecycle-node node-${node.display_status.toLowerCase()} ${selected.id === node.id ? "is-selected" : ""}`} style={{ left: `${positions[node.id].x}%`, top: `${positions[node.id].y}%` }} onClick={() => setSelectedId(node.id)} aria-pressed={selected.id === node.id} aria-label={`${node.label}: ${node.display_status}. ${node.detail}`}><i /><span>{node.label}</span><small>{node.display_status.replaceAll("_", " ")}</small></button>)}
    </div>
    <div className="lifecycle-inspector" aria-live="polite">
      <div className="lifecycle-inspector-heading"><div><span className="eyebrow">Selected lifecycle node</span><h3>{selected.label}</h3></div><StatusBadge status={selected.display_status} /></div>
      <p>{selected.detail}</p>
      <div className="lifecycle-inspector-meta"><ProvenanceBadge provenance={selected.provenance} />{selected.provider && <span className="provider-badge">Bright Data Scraper Studio</span>}{selected.timestamp && <time>{new Date(selected.timestamp).toLocaleString()}</time>}</div>
      {selected.evidenceRefs.length > 0 ? <div className="lifecycle-evidence-ref"><ShieldAlert size={15} /><span>Evidence</span>{selected.evidenceRefs.map((ref) => <code key={ref}>{ref}</code>)}</div> : <div className="lifecycle-evidence-ref is-empty"><ArrowRight size={15} /><span>No evidence reference is available for this node.</span></div>}
      {selected.display_status === "BLOCKED" && <p className="lifecycle-fail-closed"><ExternalLink size={14} /> The commit path is fail-closed until the missing evidence boundary is satisfied.</p>}
    </div>
  </section>;
}
