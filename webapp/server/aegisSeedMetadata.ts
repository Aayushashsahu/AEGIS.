/** Cheap static metadata; full lifecycle projections remain detail-only. */
export const SEEDED_CASE_METADATA = [
  { case_id: "mission_029_real_provider", name: "Mission 029 / Bright Data Hacker News", target_url: "https://news.ycombinator.com", created_at: "2026-08-18T14:00:00+00:00", evidence_status: "HEAL_FAILED_BEFORE_CANDIDATE", event_count: 11 },
  { case_id: "mission_033_real_provider_candidate", name: "Mission 033 / Bright Data real candidate", target_url: "https://3000-in40pq5v22nvlswgg4ddl-0b71e979.sg1.manus.computer/mission-033/target", created_at: "2026-08-20T00:00:00+00:00", evidence_status: "AWAITING_PROVIDER_APPROVAL_COMMIT_BLOCKED", event_count: 6 },
  { case_id: "mission_034_transport_blocked", name: "Mission 034 / Bright Data transport-blocked authorization", target_url: "https://3000-in40pq5v22nvlswgg4ddl-0b71e979.sg1.manus.computer/mission-033/target", created_at: "2026-08-20T05:17:06+00:00", evidence_status: "BLOCKED_TRANSPORT_UNAVAILABLE", event_count: 3 },
  { case_id: "mission_050_real_provider_causal_boundary", name: "Mission 050 / Real provider causal boundary", target_url: "https://3000-in40pq5v22nvlswgg4ddl-0b71e979.sg1.manus.computer/mission-033/target", created_at: "2026-08-21T04:28:11+00:00", evidence_status: "REAL_PROVIDER_OUTPUT_REJECTED_CAUSE_UNKNOWN", event_count: 4 },
  { case_id: "controlled_silent_corruption", name: "Controlled replay / silent corruption", target_url: "https://controlled.aegis.invalid/product", created_at: "2026-08-18T15:00:00+00:00", evidence_status: "BLOCKED", event_count: 4 },
] as const;
