/**
 * Tensioned Signal Web: this route is an honest entry point to evidence inspection, with replay never confused for a live case.
 */
import { AppShell } from "@/components/AppShell";
import { SensingField } from "@/components/SensingField";
import { emptyLifecycle } from "@/lib/lifecycle";
import { ArrowRight, FileSearch, ShieldCheck } from "lucide-react";
import { Link } from "wouter";

export default function Evidence() {
  return (
    <AppShell>
      <main className="evidence-page">
        <section className="evidence-page-copy">
          <span className="eyebrow">Evidence</span>
          <h1>Evidence is the <span className="bone-emphasis">nervous system.</span></h1>
          <p>When a backend exposes redacted AuditEvent history, this surface is where a case’s immutable collection, observation, detection, verification, and decision evidence belongs.</p>
          <div className="evidence-page-actions">
            <Link href="/judge" className="signal-button"><FileSearch size={16} /> Open recorded replay</Link>
            <Link href="/" className="quiet-link">Create a case <ArrowRight size={15} /></Link>
          </div>
        </section>
        <section className="evidence-page-art" aria-hidden="true">
          <div className="evidence-art-image"><SensingField state={emptyLifecycle()} presentation="provenance" /></div>
          <div className="evidence-art-rule"><ShieldCheck size={17} /> A provider result is evidence, not authority.</div>
        </section>
        <section className="evidence-path-declaration" aria-label="Evidence decision path"><span>Contract</span><i /><span>Observation</span><i /><span>Verification</span><i /><span>Decision</span><p>Each link must be attributable before a product decision can be made.</p></section>
      </main>
    </AppShell>
  );
}
