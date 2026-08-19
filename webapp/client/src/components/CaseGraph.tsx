/**
 * Tensioned Signal Web: the graph is a semantic map of AEGIS relationships and stays intentionally unpopulated until real evidence exists.
 */
import { Network, CircleDashed } from "lucide-react";
import type { ReliabilityCase } from "@/lib/aegis";

const graphNodes = [
  { label: "Collector", x: 11, y: 56 },
  { label: "Observation", x: 28, y: 25 },
  { label: "Detection", x: 47, y: 62 },
  { label: "Diagnosis", x: 62, y: 30 },
  { label: "Repair request", x: 79, y: 56 },
  { label: "Candidate", x: 89, y: 22 },
  { label: "Verification", x: 67, y: 83 },
  { label: "Decision", x: 39, y: 88 },
];

export function CaseGraph({ caseData }: { caseData: ReliabilityCase }) {
  return (
    <section className="graph-panel" aria-labelledby="graph-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Case web</span>
          <h2 id="graph-title">Relationships will appear as evidence arrives.</h2>
        </div>
        <span className="source-pill source-local"><CircleDashed size={13} /> no evidence nodes</span>
      </div>

      <div className="graph-canvas" aria-label={`Lifecycle graph for ${caseData.name}`}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path d="M11 56 L28 25 L47 62 L62 30 L79 56 L89 22 M47 62 L67 83 L39 88 L11 56 M62 30 L67 83" />
          <path className="graph-branch" d="M28 25 L39 88" />
        </svg>
        {graphNodes.map((node) => (
          <span className="graph-node" key={node.label} style={{ left: `${node.x}%`, top: `${node.y}%` }}>
            <i />{node.label}
          </span>
        ))}
        <div className="graph-empty-callout"><Network size={18} /><span>Run a baseline through the documented AEGIS boundary to connect this case graph.</span></div>
      </div>
    </section>
  );
}
