/**
 * AEGIS product entry: the only primary action is protecting a user-owned
 * scraper contract. The lifecycle graph is explicitly a controlled visual.
 */
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "wouter";
import { toast } from "sonner";
import { AppShell } from "@/components/AppShell";
import { InteractiveLifecycleGraph } from "@/components/InteractiveLifecycleGraph";
import { SensingField } from "@/components/SensingField";
import { createId, fieldTypes, hostFromTarget, type FieldDefinition, type InvariantDefinition } from "@/lib/aegis";
import { aegisApi, ApiError } from "@/lib/aegisApi";
import { emptyLifecycle, type LifecycleGraphState } from "@/lib/lifecycle";
import { ArrowDown, ArrowRight, ArrowUpRight, Check, Info, Network, Plus, ShieldAlert, Trash2 } from "lucide-react";

const emptyField = (): FieldDefinition => ({ id: createId("field"), name: "", type: "text", description: "" });
const emptyInvariant = (): InvariantDefinition => ({ id: createId("invariant"), expression: "" });
export default function Home() {
  const [, setLocation] = useLocation();
  const [targetUrl, setTargetUrl] = useState("");
  const [fields, setFields] = useState<FieldDefinition[]>([emptyField()]);
  const [invariants, setInvariants] = useState<InvariantDefinition[]>([emptyInvariant()]);
  const [collectorId, setCollectorId] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lifecycle, setLifecycle] = useState<LifecycleGraphState | null>(null);

  const caseName = useMemo(() => hostFromTarget(targetUrl.trim()), [targetUrl]);
  useEffect(() => { void aegisApi.getGraph("controlled_silent_corruption").then(setLifecycle).catch(() => setLifecycle(emptyLifecycle())); }, []);
  const graph = lifecycle ?? emptyLifecycle();

  function updateField(id: string, patch: Partial<FieldDefinition>) {
    setFields((current) => current.map((field) => field.id === id ? { ...field, ...patch } : field));
  }

  function updateInvariant(id: string, expression: string) {
    setInvariants((current) => current.map((invariant) => invariant.id === id ? { ...invariant, expression } : invariant));
  }

  async function handleCreateCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanFields = fields.filter((field) => field.name.trim());
    const cleanInvariants = invariants.filter((invariant) => invariant.expression.trim());
    try { new URL(targetUrl); } catch { toast.error("Enter a complete public URL, including https://."); return; }
    if (!cleanFields.length) { toast.error("Add at least one extraction field before protecting this scraper."); return; }
    setSubmitting(true);
    try {
      const created = await aegisApi.createCase({
        target_url: targetUrl,
        fields: cleanFields.map(({ name, type, description: fieldDescription }) => ({ name, type, description: fieldDescription })),
        invariants: cleanInvariants.map((item) => item.expression),
        name: caseName || undefined,
        collector_id: collectorId.trim() || undefined,
        description: description.trim() || undefined,
      });
      toast.success("Reliability case persisted by the local AEGIS API.");
      setLocation(`/cases/${created.case_id}`);
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : "Case persistence is unavailable. Start the local AEGIS API and try again.");
    } finally { setSubmitting(false); }
  }

  return <AppShell><main>
    <section className="landing-hero sensing-hero is-calm">
      <div className="landing-hero-copy">
        <p className="eyebrow">AEGIS / evidence-led scraper reliability</p>
        <h1>Your scraper<br />can be green<br /><span>and still be wrong.</span></h1>
        <div className="hero-lines"><span>Silent corruption.</span><span>Evidence first.</span><span>Fail closed.</span></div>
        <p className="landing-body">AEGIS detects silent corruption, investigates the evidence, and verifies repairs before bad scraped data reaches production.</p>
        <div className="hero-actions"><a href="#create" className="signal-button"><ShieldAlert size={17} /> Protect a scraper <ArrowUpRight size={16} /></a><Link href="/judge" className="hero-secondary-action">See how AEGIS thinks <ArrowRight size={16} /></Link></div>
      </div>
      <div className="hero-sensing-object"><div className="sensing-object-label"><span>Lifecycle instrument</span><i /><b>Configured target</b></div><SensingField state={graph} presentation="hero" /><div className="sensing-object-stages" aria-hidden="true"><span>Observe</span><span>Verify</span><span>Commit gate</span></div></div>
    </section>

    <section className="landing-lifecycle" aria-labelledby="lifecycle-title"><div className="landing-lifecycle-head"><div><span className="eyebrow">Lifecycle contract</span><h2 id="lifecycle-title">A web that watches the <span className="bone-emphasis">entire decision path.</span></h2></div><p>Inspect each boundary to see what AEGIS can know after a case has evidence, and where the fail-closed rule applies.</p></div><InteractiveLifecycleGraph state={graph} title="Canonical AEGIS lifecycle" /><p className="controlled-graph-note"><Info size={15} /> {graph.message}</p></section>

    <section className="impact-interruption" aria-labelledby="impact-title"><div className="impact-copy"><span className="eyebrow">Why this matters</span><h2 id="impact-title">Bad scraped data becomes a <span className="bone-emphasis">business decision.</span></h2><p>Price monitoring, market intelligence, news aggregation, competitive intelligence, and research pipelines all depend on extraction that is more than syntactically valid.</p><Link href="/silent-corruption" className="outline-button">See the interruption <ArrowRight size={16} /></Link></div><div className="impact-chain" aria-label="AEGIS interrupts untrusted scraped data before downstream use"><div><small>01</small><b>Scraped data</b></div><ArrowDown size={15} /><div className="is-danger"><small>02</small><b>Silent corruption</b></div><ArrowDown size={15} /><div><small>03</small><b>Database</b></div><ArrowDown size={15} /><div><small>04</small><b>Dashboard</b></div><ArrowDown size={15} /><div className="is-danger"><small>05</small><b>Business decision</b></div><span className="impact-break">AEGIS</span><div className="is-safe"><small>Evidence</small><b>Verified data<br />or blocked shipment</b></div></div></section>

    <section id="create" className="case-builder" aria-labelledby="create-title">
      <aside className="builder-intro"><span className="eyebrow">01 / Create reliability case</span><h2 id="create-title">Tell AEGIS what<br /><span className="bone-emphasis">deserves protection.</span></h2><p>Start with a public target and an extraction contract. AEGIS persists configuration before it has authority to describe observations or health.</p><div className="builder-principles"><span><Check size={14} /> User-owned contract</span><span><Check size={14} /> Evidence-led lifecycle</span><span><Check size={14} /> No blind commit</span></div></aside>
      <form className="case-form" onSubmit={handleCreateCase}>
        <label className="form-label" htmlFor="target-url">Target URL</label><div className="target-input-wrap"><Network size={18} /><input id="target-url" type="url" inputMode="url" placeholder="https://your-public-target/path" value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} required />{targetUrl && <span className="target-host">{caseName}</span>}</div><p className="form-help">A public URL is required. Provider credentials and secrets never belong here.</p>
        <div className="form-section configuration-section"><div className="form-section-title"><div><span className="eyebrow">Case context</span><h3>Describe the source without invoking it.</h3></div></div><div className="configuration-grid"><label><span>Collector ID <small>optional</small></span><input placeholder="Existing collector reference" value={collectorId} onChange={(event) => setCollectorId(event.target.value)} /></label></div><label className="description-field"><span>Case description <small>optional</small></span><textarea placeholder="What downstream decision depends on this data?" value={description} onChange={(event) => setDescription(event.target.value)} rows={3} /></label><p className="form-help">This persists only the case context; observation and provider activity require their own recorded evidence.</p></div>
        <div className="form-section"><div className="form-section-title"><div><span className="eyebrow">Extraction contract</span><h3>Which fields must remain trustworthy?</h3></div><button type="button" className="text-button" onClick={() => setFields((current) => [...current, emptyField()])}><Plus size={15} /> Add field</button></div><div className="field-editor" aria-label="Extraction fields">{fields.map((field, index) => <div className="field-row" key={field.id}><span className="field-index">{String(index + 1).padStart(2, "0")}</span><input aria-label={`Field ${index + 1} name`} placeholder="Field name" value={field.name} onChange={(event) => updateField(field.id, { name: event.target.value })} /><select aria-label={`Field ${index + 1} type`} value={field.type} onChange={(event) => updateField(field.id, { type: event.target.value as FieldDefinition["type"] })}>{fieldTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select><input aria-label={`Field ${index + 1} intent`} placeholder="Optional extraction intent" value={field.description} onChange={(event) => updateField(field.id, { description: event.target.value })} /><button type="button" className="icon-button" aria-label={`Remove field ${index + 1}`} onClick={() => setFields((current) => current.length === 1 ? current : current.filter((item) => item.id !== field.id))}><Trash2 size={16} /></button></div>)}</div></div>
        <div className="form-section invariant-section"><div className="form-section-title"><div><span className="eyebrow">Invariants</span><h3>What must always be true?</h3></div><button type="button" className="text-button" onClick={() => setInvariants((current) => [...current, emptyInvariant()])}><Plus size={15} /> Add rule</button></div><div className="invariant-editor" aria-label="Invariants">{invariants.map((invariant, index) => <div className="invariant-row" key={invariant.id}><span className="field-index">{String(index + 1).padStart(2, "0")}</span><input aria-label={`Invariant ${index + 1}`} placeholder="Example: price >= 0" value={invariant.expression} onChange={(event) => updateInvariant(invariant.id, event.target.value)} /><button type="button" className="icon-button" aria-label={`Remove invariant ${index + 1}`} onClick={() => setInvariants((current) => current.length === 1 ? current : current.filter((item) => item.id !== invariant.id))}><Trash2 size={16} /></button></div>)}</div></div>
        <div className="form-footer"><p><Info size={15} /> This persists a case configuration. Bright Data collection and repair remain unavailable until an implemented orchestration boundary is connected.</p><button className="signal-button" type="submit" disabled={submitting}>{submitting ? "Persisting case" : "Protect this scraper"} <ArrowUpRight size={16} /></button></div>
      </form>
    </section>
  </main></AppShell>;
}
