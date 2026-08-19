import { createTRPCClient, httpBatchLink } from "@trpc/client";
import superjson from "superjson";
import type { AppRouter } from "../../../server/routers";

/**
 * Tensioned Signal Web: browser code only renders normalized AEGIS API records.
 * It never invokes a provider, model, verification, risk, commit, or benchmark operation directly.
 */
export type ApiField = { name: string; type: "text" | "number" | "url" | "boolean" | "date"; description: string };
export type CaseSummary = { case_id: string; name: string; target_url: string; created_at: string; evidence_status: string; event_count: number };
export type ApiCase = {
  case_id: string;
  name: string;
  target_url: string;
  collector_id?: string | null;
  description?: string | null;
  monitoring?: { cadence?: string; enabled?: boolean } | null;
  fields: ApiField[];
  invariants: string[];
  correlation_id: string;
  created_at: string;
  updated_at: string;
  lifecycle: { current_status: string; event_count: number; latest_event_type: string | null; evidence_refs: string[] };
  actions: string[];
  action_policy: string;
};
export type EvidenceEvent = { event_id: string; event_type: string; label: string; timestamp: string; provenance: string; correlation_id?: string; schema_version?: string; status: string; evidence_refs: string[]; payload?: Record<string, unknown> };
export type CaseGraph = { case_id: string; mode: "CASE" | "REPLAY" | "CONTROLLED_DEMONSTRATOR" | "EMPTY" | "REAL_PROVIDER" | "TEST_DOUBLE_CONTROLLED_REPLAY" | "CONFIGURED_CASE"; nodes: Array<{ id: "TARGET" | "COLLECTOR" | "OBSERVATION" | "DETECTION" | "DIAGNOSIS" | "REPAIR" | "CANDIDATE" | "VERIFICATION" | "RISK" | "COMMIT"; label: string; domain_status: string; display_status: "CONFIGURED" | "ACTIVE" | "PENDING" | "ANOMALY" | "VERIFIED" | "QUARANTINED" | "BLOCKED" | "UNAVAILABLE"; provenance: "USER_CONFIGURED" | "NORMALIZED_CASE" | "REAL_PROVIDER" | "REPLAY" | "TEST_DOUBLE" | "CONTROLLED_DEMONSTRATOR"; detail: string; evidenceRefs: string[]; provider?: string }>; edges: Array<{ id: string; source: string; target: string; domain_status: string; display_status: "PENDING" | "ACTIVE" | "BROKEN" | "VERIFIED" | "UNAVAILABLE"; provenance: "USER_CONFIGURED" | "NORMALIZED_CASE" | "REAL_PROVIDER" | "REPLAY" | "TEST_DOUBLE" | "CONTROLLED_DEMONSTRATOR"; evidenceRefs: string[] }>; activeNodeId: "TARGET" | "COLLECTOR" | "OBSERVATION" | "DETECTION" | "DIAGNOSIS" | "REPAIR" | "CANDIDATE" | "VERIFICATION" | "RISK" | "COMMIT"; activeEdgeIds: string[]; currentStage: "TARGET" | "COLLECTOR" | "OBSERVATION" | "DETECTION" | "DIAGNOSIS" | "REPAIR" | "CANDIDATE" | "VERIFICATION" | "RISK" | "COMMIT"; severity: "UNKNOWN" | "HEALTHY" | "ANOMALY" | "QUARANTINE" | "BLOCKED"; provenance: "USER_CONFIGURED" | "NORMALIZED_CASE" | "REAL_PROVIDER" | "REPLAY" | "TEST_DOUBLE" | "CONTROLLED_DEMONSTRATOR"; domain_decision: string; display_decision: "NOT_EVALUATED" | "ACCEPT" | "REJECT" | "QUARANTINE" | "BLOCKED"; evidenceRefs: string[]; message: string };
export type RecordedReplay = { status: string; presentation: string; provenance?: string; artifact_path?: string; artifacts?: string[]; evidence?: Array<Record<string, unknown>>; collection?: { collector_id: string; target_url: string; row_count: number; run_behavior: string; batch_job_id?: string }; trust_status?: string; candidate_status?: string; verification_status?: string; risk_status?: string; commit_status?: string; reason?: string };
export type BenchmarkSummary = { status: string; classification: string; reason?: string; artifact_root?: string; summary?: { run_id?: string; execution?: { planned_opportunities: number; completed_opportunities: number; failed_opportunities: number; provider_operations: number; healing_operations: number; metric_results_generated: number }; protocol?: { participants: string[]; seed: number; trials_per_mutation: number; nvidia_model: string; nvidia_provider_limit: string; nvidia_throttle: string }; controlled_aegis_metrics?: { provenance: string; caveat: string; detection_rate: { numerator: number; denominator: number }; l5_detection_rate: { numerator: number; denominator: number }; l5_bad_data_shipped: { numerator: number; denominator: number } } }; artifacts?: string[] };
export type DownstreamOutput = { status: string; provenance: "TEST_DOUBLE"; mode: "CONTROLLED_REPLAY"; product: { product_id: string; title: string; url: string; expected_price: number; observed_price: number }; verification: { status: string; checks: Array<{ channel: string; status: string; critical: boolean; message: string; evidence_refs: string[] }> }; risk: { decision: string; reason_code: string }; commit: { eligibility: string; reason_code: string; block_reasons: string[] }; output: { status: "BLOCKED" | "ELIGIBLE"; eligible: boolean; consumer_message: string }; evidence_refs: string[] };

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}

const client = createTRPCClient<AppRouter>({ links: [httpBatchLink({ url: "/api/trpc", transformer: superjson })] });
async function request<T>(operation: () => Promise<T>): Promise<T> { try { return await operation(); } catch (error) { throw new ApiError(error instanceof Error ? error.message : "AEGIS API unavailable", 500); } }

export const aegisApi = {
  listCases: () => request(() => client.aegis.listCases.query()) as Promise<{ cases: CaseSummary[] }>,
  createCase: (payload: { target_url: string; fields: ApiField[]; invariants: string[]; name?: string; collector_id?: string; description?: string; monitoring?: { cadence?: string; enabled?: boolean } }) => request(() => client.aegis.createCase.mutate({ targetUrl: payload.target_url, fields: payload.fields, invariants: payload.invariants, name: payload.name, collectorId: payload.collector_id, description: payload.description })) as Promise<ApiCase>,
  getCase: async (caseId: string) => ((await request(() => client.aegis.caseLifecycle.query({ caseId }))) as any).case as ApiCase,
  getEvidence: async (caseId: string) => { const payload = (await request(() => client.aegis.caseLifecycle.query({ caseId }))) as any; return { case_id: caseId, mode: payload.graph.mode, events: payload.events as EvidenceEvent[] }; },
  getGraph: async (caseId: string) => ((await request(() => client.aegis.caseLifecycle.query({ caseId }))) as any).graph as CaseGraph,
  getReplay: () => request(() => client.aegis.caseLifecycle.query({ caseId: "controlled_silent_corruption" })) as Promise<RecordedReplay>,
  getHistoricalProviderReplay: async () => ((await request(() => client.aegis.caseLifecycle.query({ caseId: "mission_029_real_provider" }))) as any).replay as RecordedReplay,
  getBenchmark: () => request(() => client.aegis.benchmark.query()) as Promise<BenchmarkSummary>,
  getDownstream: () => request(() => client.aegis.downstream.query()) as Promise<DownstreamOutput>,
};
