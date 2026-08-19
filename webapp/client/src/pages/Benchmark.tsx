/**
 * Tensioned Signal Web: benchmark information stays supporting evidence and presents only an honest artifact-availability state.
 */
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { SensingField } from "@/components/SensingField";
import { emptyLifecycle } from "@/lib/lifecycle";
import { Archive, ArrowRight, FileWarning, FlaskConical, LockKeyhole } from "lucide-react";
import { Link } from "wouter";
import { aegisApi, type BenchmarkSummary } from "@/lib/aegisApi";

export default function Benchmark() {
  const [summary, setSummary] = useState<BenchmarkSummary | null>(null);
  useEffect(() => { void aegisApi.getBenchmark().then(setSummary).catch(() => setSummary({ status: "NOT_AVAILABLE", classification: "CONTROLLED_HARNESS_METRICS", reason: "Local AEGIS API is unavailable." })); }, []);
  return (
    <AppShell>
      <main className="benchmark-page">
        <section className="benchmark-head">
          <p className="eyebrow">Benchmark evidence</p>
          <h1>Measured only when<br /><span className="bone-emphasis">the artifact is present.</span></h1>
          <p>AEGIS separates the product workflow from controlled-harness measurement. This static experience will not execute, re-score, or fabricate benchmark results.</p>
        </section>

        <section className="benchmark-empty benchmark-boundary" aria-labelledby="benchmark-empty-title">
          <div className="benchmark-field" aria-hidden="true"><SensingField state={emptyLifecycle()} presentation="harness" /></div>
          <div className="benchmark-icon"><Archive size={32} /></div>
          <div>
            <span className="source-pill source-local"><FileWarning size={13} /> {summary?.classification.replaceAll("_", " ") ?? "loading evidence"}</span>
            <h2 id="benchmark-empty-title">{summary?.status === "AVAILABLE" ? "An immutable benchmark artifact is available." : "No benchmark artifact is available to this frontend."}</h2>
            <p>{summary?.status === "AVAILABLE" ? `Read-only artifact: ${summary.artifact_root}` : "The local evidence inventory returned no benchmark artifact. AEGIS will not infer any recovery or metric result."}</p>
          </div>
          <Link href="/judge" className="outline-button">Inspect recorded replay <ArrowRight size={16} /></Link>
          <div className="benchmark-evidence-spine" aria-label="Benchmark evidence path"><span>Methodology<small>frozen before measurement</small></span><i /><span>Artifact<small>{summary?.status === "AVAILABLE" ? "available" : "unavailable"}</small></span><i /><span>Metric<small>reported only with artifact</small></span><i /><span>Decision<small>never inferred by UI</small></span></div>
        </section>

        <section className="benchmark-rules">
          <div><FlaskConical size={20} /><h3>Controlled ground truth</h3><p>Detection and safety claims require the mutation laboratory’s independent truth; production-like observations alone are not a metric source.</p></div>
          <div><LockKeyhole size={20} /><h3>Frozen methodology</h3><p>Model, prompts, seeds, policies, and environment are recorded before large-scale execution. A frontend cannot silently change them.</p></div>
          <div><FileWarning size={20} /><h3>Unavailable stays unavailable</h3><p>Absent denominators, incomplete evidence, and unrun measurements remain explicit. The product never paints missing results as zero or success.</p></div>
        </section>
      </main>
    </AppShell>
  );
}
