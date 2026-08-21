#!/usr/bin/env python3
"""Read-only JSON-lines adapter from canonical AEGIS records to web lifecycle views.

The adapter is intentionally a projection boundary.  It invokes existing AEGIS
domain logic for the controlled replay and reads committed Mission 029/030 and
Mission 028 artifacts for historical views.  It never invokes Bright Data,
NVIDIA, Gemini, approval, commit, rollback, or benchmark execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aegis.audit_store import _redact, _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.mission030_evidence import Mission029ArtifactLoader
from aegis.risk import RiskGovernor
from aegis.verification import verify_candidate
from aegis.verification_double import VerificationFixture, build_verification_fixture
from scripts.mission031_build_demo_snapshot import RECOVERY_RUN_ID, build_snapshot


ORDER = ("TARGET", "COLLECTOR", "OBSERVATION", "DETECTION", "DIAGNOSIS", "REPAIR", "CANDIDATE", "VERIFICATION", "RISK", "COMMIT")


def _node(
    stage: str,
    display_status: str,
    provenance: str,
    detail: str,
    refs: tuple[str, ...] = (),
    *,
    provider: str | None = None,
    domain_status: str | None = None,
) -> dict[str, Any]:
    default_domain_status = {
        "CONFIGURED": "configured",
        "ACTIVE": "evidence_recorded",
        "PENDING": "not_evaluated",
        "ANOMALY": "anomaly_detected",
        "VERIFIED": "verified",
        "QUARANTINED": "quarantined",
        "BLOCKED": "blocked",
        "UNAVAILABLE": "not_run",
    }[display_status]
    return {
        "id": stage,
        "label": {"TARGET": "Target", "COLLECTOR": "Collector", "OBSERVATION": "Observation", "DETECTION": "Detection", "DIAGNOSIS": "Diagnosis", "REPAIR": "Repair request", "CANDIDATE": "Candidate", "VERIFICATION": "Verification", "RISK": "Risk", "COMMIT": "Commit gate"}[stage],
        "domain_status": domain_status or default_domain_status,
        "display_status": display_status,
        "provenance": provenance,
        "detail": detail,
        "evidenceRefs": list(refs),
        "provider": provider,
    }


def _edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statuses = {str(node["id"]): str(node["display_status"]) for node in nodes}
    output: list[dict[str, Any]] = []
    for source, target in zip(ORDER, ORDER[1:]):
        target_status = statuses.get(target, "PENDING")
        edge_status = "ACTIVE"
        if target_status in {"ANOMALY", "QUARANTINED", "BLOCKED"}:
            edge_status = "BROKEN"
        elif target_status == "UNAVAILABLE":
            edge_status = "UNAVAILABLE"
        elif target_status == "PENDING":
            edge_status = "PENDING"
        elif target_status == "VERIFIED":
            edge_status = "VERIFIED"
        target_node = next((node for node in nodes if node["id"] == target), None)
        output.append({"id": f"{source}->{target}", "source": source, "target": target, "display_status": edge_status, "domain_status": str(target_node["domain_status"]) if target_node else "not_evaluated", "provenance": target_node["provenance"] if target_node else "NORMALIZED_CASE", "evidenceRefs": target_node["evidenceRefs"] if target_node else []})
    return output


def _graph(case_id: str, mode: str, nodes: list[dict[str, Any]], message: str, decision: str) -> dict[str, Any]:
    active = next((node for node in reversed(nodes) if node["display_status"] in {"ACTIVE", "ANOMALY", "VERIFIED", "QUARANTINED"}), nodes[0])
    refs = sorted({ref for node in nodes for ref in node["evidenceRefs"]})
    severity = "UNKNOWN"
    if any(node["display_status"] == "QUARANTINED" for node in nodes):
        severity = "QUARANTINE"
    elif any(node["display_status"] == "ANOMALY" for node in nodes):
        severity = "ANOMALY"
    elif any(node["display_status"] == "BLOCKED" for node in nodes):
        severity = "BLOCKED"
    elif any(node["display_status"] == "VERIFIED" for node in nodes):
        severity = "HEALTHY"
    return {
        "case_id": case_id,
        "mode": mode,
        "nodes": nodes,
        "edges": _edges(nodes),
        "activeNodeId": active["id"],
        "activeEdgeIds": [edge["id"] for edge in _edges(nodes) if edge["display_status"] in {"ACTIVE", "BROKEN", "VERIFIED"}],
        "currentStage": active["id"],
        "severity": severity,
        "provenance": "REAL_PROVIDER" if any(node["provenance"] == "REAL_PROVIDER" for node in nodes) else nodes[0]["provenance"],
        "domain_decision": decision.lower(),
        "display_decision": decision,
        "evidenceRefs": refs,
        "message": message,
    }


def _historical(root: Path) -> dict[str, Any]:
    evidence = Mission029ArtifactLoader(root / "experiments" / "mission_029").load()
    snapshot = build_snapshot(root)
    live = snapshot["live_lane"]
    stages = {stage.stage_id: stage for stage in evidence.stages}
    refs = tuple(live["artifact_hashes"].keys())
    nodes = [
        _node("TARGET", "CONFIGURED", "REAL_PROVIDER", evidence.target_url, refs, domain_status="target_configured"),
        _node("COLLECTOR", "ACTIVE", "REAL_PROVIDER", evidence.collector_id, refs, provider="Bright Data Scraper Studio", domain_status="collector_run_completed"),
        _node("OBSERVATION", "ACTIVE", "REAL_PROVIDER", f"Recorded live collection contains {evidence.row_count} rows.", refs, domain_status="observation_recorded"),
        _node("DETECTION", "ANOMALY", "CONTROLLED_DEMONSTRATOR", stages["detection"].detail, refs, domain_status="l3_anomaly_detected"),
        _node("DIAGNOSIS", "ANOMALY", "CONTROLLED_DEMONSTRATOR", stages["diagnosis"].detail, refs, domain_status="diagnosis_ambiguous"),
        _node("REPAIR", "ANOMALY", "REAL_PROVIDER", live["provider_heal"]["error_code"], refs, provider="Bright Data Scraper Studio", domain_status="provider_heal_failed"),
        _node("CANDIDATE", "UNAVAILABLE", "REAL_PROVIDER", "Provider terminal record confirms no candidate was created.", refs, domain_status="candidate_absent"),
        _node("VERIFICATION", "UNAVAILABLE", "REAL_PROVIDER", "No candidate exists; verification was not invoked.", refs, domain_status="verification_not_run"),
        _node("RISK", "UNAVAILABLE", "REAL_PROVIDER", "No candidate exists; risk was not invoked.", refs, domain_status="risk_not_run"),
        _node("COMMIT", "BLOCKED", "REAL_PROVIDER", "No candidate, approval, or production commit occurred.", refs, domain_status="production_commit_blocked"),
    ]
    graph = _graph("mission_029_real_provider", "REAL_PROVIDER", nodes, "Canonical Mission 029/030 evidence reaches a terminal provider failure before a candidate. Downstream stages remain unavailable rather than fabricated.", "BLOCKED")
    events = [
        {"event_id": f"mission029-{stage.stage_id}", "event_type": stage.stage_id.upper(), "label": stage.label, "timestamp": "2026-08-18T14:35:30+00:00", "provenance": stage.provenance, "status": stage.status, "evidence_refs": list(refs)}
        for stage in evidence.stages
    ]
    case = {
        "case_id": "mission_029_real_provider",
        "name": "Mission 029 / Bright Data Hacker News",
        "target_url": evidence.target_url,
        "collector_id": evidence.collector_id,
        "description": "Immutable real-provider collection with a terminal no-candidate heal record.",
        "fields": [{"name": name, "type": "number" if name in {"points", "comment_count"} else "url" if name == "url" else "text", "description": "Committed Mission 029 schema field"} for name in ("title", "url", "points", "author", "comment_count")],
        "invariants": ["non_negative_numeric", "valid_url"],
        "correlation_id": "mission_029_historical",
        "created_at": "2026-08-18T14:00:00+00:00",
        "updated_at": "2026-08-18T14:35:30+00:00",
        "lifecycle": {"current_status": "HEAL_FAILED_BEFORE_CANDIDATE", "event_count": len(events), "latest_event_type": "COMMIT", "evidence_refs": list(refs)},
        "actions": [],
        "action_policy": "Historical provider evidence is read-only. The terminal no-candidate boundary blocks verification, risk, approval, and commit.",
    }
    replay = {
        "status": "AVAILABLE",
        "presentation": "HISTORICAL_REAL_PROVIDER_EVIDENCE",
        "provenance": "REAL_PROVIDER",
        "artifact_path": "experiments/mission_029",
        "artifacts": list(refs),
        "collection": {
            "collector_id": evidence.collector_id,
            "target_url": evidence.target_url,
            "row_count": evidence.row_count,
            "run_behavior": "RECORDED",
        },
        "candidate_status": "UNAVAILABLE",
        "verification_status": "UNAVAILABLE",
        "risk_status": "UNAVAILABLE",
        "commit_status": "BLOCKED",
    }
    return {"case": case, "events": events, "graph": graph, "replay": replay}


def _mission033(root: Path) -> dict[str, Any]:
    """Project preserved Mission 033 real-provider candidate evidence read-only."""

    evidence_root = root / "experiments" / "mission_033_live_bright_data_success"
    required = {
        "creation": evidence_root / "collector_creation.json",
        "drifted_run": evidence_root / "provider_operations" / "operation_002_run.json",
        "candidate": evidence_root / "candidate_preview.json",
        "verification": evidence_root / "verification.json",
        "risk": evidence_root / "risk_decision.json",
        "commit": evidence_root / "commit_decision.json",
        "approval": evidence_root / "approval.json",
        "post_heal": evidence_root / "post_heal_run.json",
        "observation": evidence_root / "corruption_observation.json",
        "heal": evidence_root / "provider_operations" / "operation_001_heal.json",
    }
    if not all(path.is_file() for path in required.values()):
        raise RuntimeError("Mission 033 evidence bundle is incomplete; refusing to project partial provider state.")
    records = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in required.items()}
    creation = records["creation"]
    drifted_run = records["drifted_run"]
    candidate = records["candidate"]
    verification = records["verification"]
    risk = records["risk"]
    commit = records["commit"]
    approval = records["approval"]
    post_heal = records["post_heal"]
    observation = records["observation"]
    heal = records["heal"]
    refs = tuple(f"evidence://mission-033/{path.relative_to(evidence_root)}" for path in required.values())
    collector_id = str(candidate["collector_id"])
    target_url = str(observation["target_url"])
    nodes = [
        _node("TARGET", "CONFIGURED", "REAL_PROVIDER", "AEGIS-owned public target; v1→v2 markup drift at the same URL.", refs, domain_status="owned_target_v2"),
        _node("COLLECTOR", "ACTIVE", "REAL_PROVIDER", collector_id, refs, provider="Bright Data Scraper Studio", domain_status="collector_created_and_reused"),
        _node("OBSERVATION", "ACTIVE", "REAL_PROVIDER", "Baseline contained all contract fields; v2 run returned only the input URL.", refs, domain_status="contract_deviation_observed"),
        _node("DETECTION", "ANOMALY", "REAL_PROVIDER", "Canonical schema detector found title, price, and availability missing.", refs, domain_status="schema_drift_detected"),
        _node("DIAGNOSIS", "ANOMALY", "REAL_PROVIDER", "Deterministic diagnosis: SCHEMA_DRIFT.", refs, domain_status="schema_drift_diagnosed"),
        _node("REPAIR", "ACTIVE", "REAL_PROVIDER", f"One bounded heal completed in {heal['elapsed_ms']} ms and returned awaiting_approval.", refs, provider="Bright Data Scraper Studio", domain_status="provider_heal_awaiting_approval"),
        _node("CANDIDATE", "ACTIVE", "REAL_PROVIDER", "Provider preview exists and remains UNVERIFIED until AEGIS evaluation; approval was not executed.", refs, provider="Bright Data Scraper Studio", domain_status="candidate_unverified"),
        _node("VERIFICATION", "VERIFIED", "AEGIS_DETERMINISTIC", f"{verification['overall_status']}: contract, history, semantics, and independent owned-target evidence passed.", refs, domain_status="verification_pass"),
        _node("RISK", "VERIFIED", "AEGIS_DETERMINISTIC", f"{risk['decision']}: eligible only for a future commit stage.", refs, domain_status="risk_accept"),
        _node("COMMIT", "BLOCKED", "AEGIS_DETERMINISTIC", f"{commit['reason_code']}; provider approval={approval['status']}; post-heal run={post_heal['status']}.", refs, domain_status="provider_approval_and_output_blocked"),
    ]
    graph = _graph(
        "mission_033_real_provider_candidate",
        "REAL_PROVIDER_CANDIDATE_AWAITING_APPROVAL",
        nodes,
        "Mission 033 is a real Bright Data create → run → owned-target drift → heal → candidate → deterministic verification story. The candidate passed deterministic checks, but AEGIS still blocks provider approval, a post-heal run, and downstream output until separately authorised.",
        "BLOCKED",
    )
    events = [
        {"event_id": "m033-create", "event_type": "COLLECTOR", "label": "Fresh collector created", "timestamp": creation["completed_at"], "provenance": "REAL_PROVIDER", "status": "COMPLETED", "evidence_refs": list(refs)},
        {"event_id": "m033-drift", "event_type": "DETECTION", "label": "Same collector observed v2 contract drift", "timestamp": drifted_run["completed_at"], "provenance": "REAL_PROVIDER", "status": "SCHEMA_DRIFT", "evidence_refs": list(refs)},
        {"event_id": "m033-heal", "event_type": "REPAIR", "label": "One Bright Data heal returned an awaiting-approval preview", "timestamp": heal["completed_at"], "provenance": "REAL_PROVIDER", "status": candidate["provider_status"], "evidence_refs": list(refs)},
        {"event_id": "m033-verification", "event_type": "VERIFICATION", "label": "Deterministic candidate verification", "timestamp": verification["completed_at"], "provenance": "AEGIS_DETERMINISTIC", "status": verification["overall_status"], "evidence_refs": list(refs)},
        {"event_id": "m033-risk", "event_type": "RISK_DECISION", "label": "Risk governor", "timestamp": risk["created_at"], "provenance": "AEGIS_DETERMINISTIC", "status": risk["decision"], "evidence_refs": list(refs)},
        {"event_id": "m033-commit", "event_type": "COMMIT_DECISION", "label": "Approval and downstream-output boundary", "timestamp": commit["created_at"], "provenance": "AEGIS_DETERMINISTIC", "status": commit["eligibility"], "evidence_refs": list(refs)},
    ]
    case = {
        "case_id": "mission_033_real_provider_candidate",
        "name": "Mission 033 / Bright Data real candidate",
        "target_url": target_url,
        "collector_id": collector_id,
        "description": "Real Bright Data candidate preview following an AEGIS-owned controlled markup drift; no provider approval or post-heal run was authorised.",
        "fields": [{"name": name, "type": "text", "description": "Mission 033 owned-product contract field"} for name in ("title", "price", "availability")],
        "invariants": ["same_collector_id", "exact_owned_product_contract", "independent_owned_target_evidence"],
        "correlation_id": str(verification["correlation_id"]),
        "created_at": str(heal["started_at"]),
        "updated_at": str(commit["created_at"]),
        "lifecycle": {"current_status": "AWAITING_PROVIDER_APPROVAL_COMMIT_BLOCKED", "event_count": len(events), "latest_event_type": "COMMIT_DECISION", "evidence_refs": list(refs)},
        "actions": [],
        "action_policy": "Read-only real-provider evidence. AEGIS verification passed and risk accepted, but the provider candidate remains unapproved; provider approval, post-heal run, and output consumption are blocked.",
    }
    return {"case": case, "events": events, "graph": graph, "replay": {"candidate": candidate, "verification": verification, "risk": risk, "commit": commit, "approval": approval, "post_heal": post_heal, "output_eligible": False}}


def _controlled(root: Path) -> dict[str, Any]:
    context = build_verification_fixture(VerificationFixture.SILENT_CORRUPTION)
    verification = verify_candidate(context)
    risk = RiskGovernor().decide(verification, context.candidate, correlation_id=context.correlation_id)
    commit = CommitGate().evaluate(context.candidate, verification, risk, context.contract, known_good_version=None, authorization=None, correlation_id=context.correlation_id, quarantine_record=None)
    eligibility = OutputEligibilityBoundary.evaluate(commit)
    refs = tuple(verification.evidence_refs)
    nodes = [
        _node("TARGET", "CONFIGURED", "TEST_DOUBLE", "Controlled silent-corruption fixture target.", refs, domain_status="fixture_configured"),
        _node("COLLECTOR", "ACTIVE", "TEST_DOUBLE", "No Bright Data operation was invoked.", refs, provider="TEST_DOUBLE", domain_status="test_double_no_provider"),
        _node("OBSERVATION", "ACTIVE", "TEST_DOUBLE", "Deterministic fixture observation.", refs, domain_status="fixture_observation_recorded"),
        _node("DETECTION", "ANOMALY", "TEST_DOUBLE", "Silent corruption fixture is selected.", refs, domain_status="silent_corruption_selected"),
        _node("DIAGNOSIS", "ACTIVE", "TEST_DOUBLE", "Controlled deterministic diagnosis context.", refs, domain_status="controlled_diagnosis"),
        _node("REPAIR", "ACTIVE", "TEST_DOUBLE", "Controlled candidate lifecycle only; no provider repair occurred.", refs, domain_status="no_provider_repair"),
        _node("CANDIDATE", "ACTIVE", "TEST_DOUBLE", "Candidate contains a plausible but incorrect price.", refs, domain_status="test_double_candidate_created"),
        _node("VERIFICATION", "ANOMALY", "TEST_DOUBLE", verification.overall_status.value, refs, domain_status="verification_failed"),
        _node("RISK", "ANOMALY", "TEST_DOUBLE", risk.decision.value, refs, domain_status="risk_reject"),
        _node("COMMIT", "BLOCKED", "TEST_DOUBLE", f"{commit.reason_code}; output eligible={eligibility.eligible}", refs, domain_status="commit_ineligible"),
    ]
    graph = _graph("controlled_silent_corruption", "TEST_DOUBLE_CONTROLLED_REPLAY", nodes, "Controlled replay uses canonical verification, risk, and commit-gate modules. It is not a Bright Data candidate.", risk.decision.value)
    events = [
        {"event_id": "controlled-candidate", "event_type": "CANDIDATE", "label": "TEST_DOUBLE candidate", "timestamp": "2026-08-18T15:00:00+00:00", "provenance": "TEST_DOUBLE", "status": context.candidate.verification_status.value, "evidence_refs": list(refs)},
        {"event_id": "controlled-verification", "event_type": "VERIFICATION", "label": "Deterministic verification", "timestamp": "2026-08-18T15:00:01+00:00", "provenance": "TEST_DOUBLE", "status": verification.overall_status.value, "evidence_refs": list(refs)},
        {"event_id": "controlled-risk", "event_type": "RISK_DECISION", "label": "Risk governor", "timestamp": "2026-08-18T15:00:02+00:00", "provenance": "TEST_DOUBLE", "status": risk.decision.value, "evidence_refs": list(refs)},
        {"event_id": "controlled-commit", "event_type": "COMMIT_DECISION", "label": "Commit eligibility", "timestamp": "2026-08-18T15:00:03+00:00", "provenance": "TEST_DOUBLE", "status": commit.eligibility.value, "evidence_refs": list(refs)},
    ]
    case = {
        "case_id": "controlled_silent_corruption", "name": "Controlled replay / silent corruption", "target_url": "https://controlled.aegis.invalid/product", "collector_id": None,
        "description": "Explicit TEST_DOUBLE fixture demonstrating candidate through commit eligibility.",
        "fields": [{"name": field.name, "type": "number" if float in field.expected_types or int in field.expected_types else "url" if field.name == "url" else "text", "description": "Canonical fixture contract field"} for field in context.contract.fields],
        "invariants": list(context.contract.invariants), "correlation_id": context.correlation_id, "created_at": "2026-08-18T15:00:00+00:00", "updated_at": "2026-08-18T15:00:03+00:00",
        "lifecycle": {"current_status": commit.eligibility.value, "event_count": len(events), "latest_event_type": "COMMIT_DECISION", "evidence_refs": list(refs)}, "actions": [],
        "action_policy": "Controlled replay only. Canonical verification and risk modules reject the candidate; output remains blocked.",
    }
    return {"case": case, "events": events, "graph": graph, "replay": {"candidate": _to_jsonable(context.candidate), "verification": _to_jsonable(verification), "risk": _to_jsonable(risk), "commit": _to_jsonable(commit), "output_eligible": eligibility.eligible}}


def _mission050(root: Path) -> dict[str, Any]:
    """Project the evidence-bounded real-provider causal boundary read-only.

    This projection intentionally separates the observed unsafe output from any
    unproven provider-internal explanation, and it never contacts a provider.
    """

    evidence_path = root / "experiments" / "mission_050" / "causal_boundary.json"
    if not evidence_path.is_file():
        raise RuntimeError("Mission 050 causal-boundary evidence is incomplete; refusing to project inferred state.")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    chain = evidence["real_provider_chain"]
    boundary = evidence["causal_boundary"]
    records = evidence["evidence_records"]
    refs = tuple(f"evidence://{record['mission']}/{record['path']}" for record in records)
    nodes = [
        _node("TARGET", "CONFIGURED", "REAL_PROVIDER", "Recorded AEGIS-owned target and contract boundary.", refs, domain_status="historical_target_reused"),
        _node("COLLECTOR", "ACTIVE", "REAL_PROVIDER", str(evidence["collector_id"]), refs, provider="Bright Data Scraper Studio", domain_status="collector_execution_recorded"),
        _node("OBSERVATION", "ACTIVE", "REAL_PROVIDER", f"HTTP {chain['http_status']} with crawl success; observed structured output contained only input.url.", refs, domain_status="provider_http_success_output_incomplete"),
        _node("DETECTION", "ANOMALY", "AEGIS_DETERMINISTIC", "Required contract fields title, price, and availability were missing from the provider response.", refs, domain_status="required_fields_missing"),
        _node("DIAGNOSIS", "ACTIVE", "AEGIS_DETERMINISTIC", f"Provider runtime cause {boundary['cause']}; confidence {boundary['confidence']}. No exact runtime template, revision, projection, or trace is uniquely bound.", refs, domain_status="causal_boundary_unknown_low"),
        _node("REPAIR", "ACTIVE", "REAL_PROVIDER", "Historical approval and provider self-healing completion are recorded; Mission 050 performs no provider action.", refs, provider="Bright Data Scraper Studio", domain_status="historical_repair_recorded_no_new_action"),
        _node("CANDIDATE", "UNAVAILABLE", "REAL_PROVIDER", "No uniquely bound corrected runtime output or provider template/revision candidate is available for causal attribution.", refs, domain_status="runtime_candidate_unavailable"),
        _node("VERIFICATION", "ANOMALY", "AEGIS_DETERMINISTIC", str(chain["verification"]), refs, domain_status="verification_failed_incomplete_output"),
        _node("RISK", "ANOMALY", "AEGIS_DETERMINISTIC", str(chain["risk"]), refs, domain_status="risk_reject_after_verification_failure"),
        _node("COMMIT", "BLOCKED", "AEGIS_DETERMINISTIC", f"{chain['commit']}; data shipped={chain['data_shipped']}.", refs, domain_status="commit_blocked_data_not_shipped"),
    ]
    graph = _graph(
        "mission_050_real_provider_causal_boundary",
        "REAL_PROVIDER_CAUSAL_BOUNDARY",
        nodes,
        "AEGIS knows the provider output is unsafe and fails closed. It does not claim an unproven provider-internal cause.",
        str(chain["risk"]),
    )
    events = [
        {"event_id": f"mission050-{record['mission'].lower()}", "event_type": "PROVENANCE_RECORD", "label": record["label"], "timestamp": "2026-08-21T00:00:00+00:00", "provenance": record["provenance"], "status": record["status"], "evidence_refs": [f"evidence://{record['mission']}/{record['path']}"]}
        for record in records
    ]
    case = {
        "case_id": "mission_050_real_provider_causal_boundary",
        "name": "Mission 050 / Real provider causal boundary",
        "target_url": _mission033(root)["case"]["target_url"],
        "collector_id": evidence["collector_id"],
        "description": "Real-provider incomplete-output evidence with an explicit unknown provider-runtime causal boundary; AEGIS fails closed without asserting an unproven cause.",
        "fields": [{"name": name, "type": "text", "description": "Required provider output contract field"} for name in ("title", "price", "availability")],
        "invariants": ["required_fields_present", "verification_failure_rejects_risk", "commit_blocked", "data_not_shipped", "no_unproven_cause"],
        "correlation_id": "mission048c-rerun-c_mt09pib13nxqz1coi-20260821T042811Z",
        "created_at": "2026-08-21T04:28:11+00:00",
        "updated_at": "2026-08-21T04:28:11+00:00",
        "lifecycle": {"current_status": "REAL_PROVIDER_OUTPUT_REJECTED_CAUSE_UNKNOWN", "event_count": len(events), "latest_event_type": "PROVENANCE_RECORD", "evidence_refs": list(refs)},
        "actions": [],
        "action_policy": "Read-only evidence boundary. The output is unsafe and blocked; the provider-internal cause remains UNKNOWN/LOW until exact runtime correlation exists.",
    }
    replay = {
        "real_provider_chain": chain,
        "cause": boundary["cause"],
        "confidence": boundary["confidence"],
        "reason": boundary["reason"],
        "evidence_records": records,
        "controlled_replay_boundary": evidence["controlled_replay_boundary"],
        "provider_operations_this_mission": evidence["provider_operations_this_mission"],
        "new_provider_requests_this_mission": evidence["new_provider_requests_this_mission"],
        "output_eligible": False,
    }
    return {"case": case, "events": events, "graph": graph, "replay": replay}


def _configured(payload: Mapping[str, Any]) -> dict[str, Any]:
    case_id = str(payload["case_id"])
    fields = list(payload.get("fields", []))
    case = {**payload, "lifecycle": {"current_status": "CONFIGURED", "event_count": 0, "latest_event_type": None, "evidence_refs": []}, "actions": [], "action_policy": "Configuration is persisted, but no collection, observation, repair, verification, risk, or commit evidence has been recorded."}
    nodes = [_node("TARGET", "CONFIGURED", "USER_CONFIGURED", str(payload["target_url"]), domain_status="user_configured")]
    graph = _graph(case_id, "CONFIGURED_CASE", nodes, "This case has only user-configured target and contract data. AEGIS has not inferred lifecycle evidence.", "NOT_EVALUATED")
    return {"case": case, "events": [], "graph": graph, "fields": fields}


def _downstream(root: Path) -> dict[str, Any]:
    """Project the canonical controlled decision into a consumer-safe output view.

    This is deliberately not a second verification or risk implementation. It
    runs the existing deterministic fixture and domain modules through
    ``_controlled`` and exposes only the resulting output boundary.
    """
    context = build_verification_fixture(VerificationFixture.SILENT_CORRUPTION)
    controlled = _controlled(root)
    candidate_row = dict(context.candidate_output[0])
    expected_price = context.semantic_expectations.get("price")
    verification = controlled["replay"]["verification"]
    risk = controlled["replay"]["risk"]
    commit = controlled["replay"]["commit"]
    checks = [
        {
            "channel": check["channel"],
            "status": check["status"],
            "critical": check["critical"],
            "message": check["message"],
            "evidence_refs": check["evidence_refs"],
        }
        for check in verification["checks"]
    ]
    return {
        "status": "AVAILABLE",
        "provenance": "TEST_DOUBLE",
        "mode": "CONTROLLED_REPLAY",
        "product": {
            "product_id": candidate_row["product_id"],
            "title": candidate_row["title"],
            "url": candidate_row["url"],
            "expected_price": expected_price,
            "observed_price": candidate_row["price"],
        },
        "verification": {"status": verification["overall_status"], "checks": checks},
        "risk": {"decision": risk["decision"], "reason_code": risk["reason_code"]},
        "commit": {"eligibility": commit["eligibility"], "reason_code": commit["reason_code"], "block_reasons": commit["block_reasons"]},
        "output": {
            "status": "BLOCKED" if not controlled["replay"]["output_eligible"] else "ELIGIBLE",
            "eligible": controlled["replay"]["output_eligible"],
            "consumer_message": "Output is withheld because the controlled candidate failed deterministic verification and cannot pass the Commit Gate.",
        },
        "evidence_refs": sorted(set(verification["evidence_refs"] + commit["evidence_refs"])),
    }


def _mission034(root: Path) -> dict[str, Any]:
    """Project the append-only Mission 034 corrected preflight read-only."""

    evidence_root = root / "experiments" / "mission_034_bright_data_approval_rerun"
    required = {
        "authorization": evidence_root / "authorization_corrected.json",
        "preflight": evidence_root / "preflight_corrected.json",
        "ledger": evidence_root / "operation_ledger_corrected.json",
        "summary": evidence_root / "summary_corrected.json",
        "hashes": evidence_root / "artifact_hashes.json",
    }
    if not all(path.is_file() for path in required.values()):
        raise RuntimeError("Mission 034 corrected evidence bundle is incomplete; refusing to project partial state.")
    records = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in required.items()}
    authorization = records["authorization"]
    preflight = records["preflight"]
    ledger = records["ledger"]
    summary = records["summary"]
    refs = tuple(f"evidence://mission-034/{path.relative_to(evidence_root)}" for path in required.values())
    target_url = _mission033(root)["case"]["target_url"]
    nodes = [
        _node("TARGET", "CONFIGURED", "REAL_PROVIDER", "Existing AEGIS-owned target; no Mission 034 target mutation occurred.", refs, domain_status="historical_target_reused"),
        _node("COLLECTOR", "ACTIVE", "REAL_PROVIDER", str(authorization["collector_id"]), refs, provider="Bright Data Scraper Studio", domain_status="historical_collector_reused"),
        _node("OBSERVATION", "ACTIVE", "REAL_PROVIDER", "Mission 033 candidate and deterministic evidence were rechecked read-only.", refs, domain_status="historical_evidence_rechecked"),
        _node("DETECTION", "ANOMALY", "REAL_PROVIDER", "Historical schema drift remains the only recorded provider failure.", refs, domain_status="historical_schema_drift"),
        _node("DIAGNOSIS", "ANOMALY", "REAL_PROVIDER", "Historical deterministic diagnosis remains SCHEMA_DRIFT.", refs, domain_status="historical_schema_drift_diagnosis"),
        _node("REPAIR", "BLOCKED", "AEGIS_DETERMINISTIC", str(preflight["stop_reason"]), refs, domain_status="approval_rerun_transport_unavailable"),
        _node("CANDIDATE", "ACTIVE", "REAL_PROVIDER", "The existing awaiting-approval candidate remains unchanged; no approval request was sent.", refs, domain_status="historical_candidate_unapproved"),
        _node("VERIFICATION", "VERIFIED", "AEGIS_DETERMINISTIC", "Historical candidate verification remains PASS; no post-heal output exists to verify.", refs, domain_status="historical_candidate_verification_pass"),
        _node("RISK", "VERIFIED", "AEGIS_DETERMINISTIC", "Historical candidate risk remains ACCEPT; no post-heal output risk evaluation exists.", refs, domain_status="historical_candidate_risk_accept"),
        _node("COMMIT", "BLOCKED", "AEGIS_DETERMINISTIC", "No approval, rerun, or real provider output occurred; automatic commit remains prohibited.", refs, domain_status="no_provider_mutation_commit_blocked"),
    ]
    graph = _graph("mission_034_transport_blocked", "REAL_PROVIDER_TRANSPORT_BLOCKED", nodes, "Mission 034 corrected authorization passed evidence and credential-probe gates but stopped before provider mutation because the documented approval/rerun transport is unavailable.", "BLOCKED")
    events = [
        {"event_id": "m034-authorization", "event_type": "AUTHORIZATION", "label": "Corrected bounded authorization recorded", "timestamp": authorization["authorized_at"], "provenance": "OWNER_AUTHORIZATION", "status": authorization["status"], "evidence_refs": list(refs)},
        {"event_id": "m034-preflight", "event_type": "PREFLIGHT", "label": "No-mutation transport preflight", "timestamp": authorization["authorized_at"], "provenance": "AEGIS_DETERMINISTIC", "status": preflight["status"], "evidence_refs": list(refs)},
        {"event_id": "m034-commit", "event_type": "COMMIT_DECISION", "label": "No provider mutation; commit remains blocked", "timestamp": authorization["authorized_at"], "provenance": "AEGIS_DETERMINISTIC", "status": summary["commit"], "evidence_refs": list(refs)},
    ]
    case = {
        "case_id": "mission_034_transport_blocked",
        "name": "Mission 034 / Bright Data transport-blocked authorization",
        "target_url": target_url,
        "collector_id": authorization["collector_id"],
        "description": "Corrected bounded authorization and valid credential probe; no documented approval/rerun transport was available, so no provider mutation occurred.",
        "fields": [{"name": name, "type": "text", "description": "Mission 033 owned-product contract field"} for name in ("title", "price", "availability")],
        "invariants": ["same_collector_id", "one_approval_maximum", "one_rerun_maximum", "zero_retries", "no_automatic_commit"],
        "correlation_id": "mission_034_transport_blocked",
        "created_at": authorization["authorized_at"],
        "updated_at": authorization["authorized_at"],
        "lifecycle": {"current_status": summary["terminal_state"], "event_count": len(events), "latest_event_type": "COMMIT_DECISION", "evidence_refs": list(refs)},
        "actions": [],
        "action_policy": "Read-only corrected-preflight evidence. The existing real candidate remains unapproved; no provider rerun, output, or commit may be implied.",
    }
    replay = {"authorization": authorization, "preflight": preflight, "operations": ledger["operations"], "summary": summary, "output_eligible": False}
    return {"case": case, "events": events, "graph": graph, "replay": replay}


def dispatch(root: Path, request: Mapping[str, Any]) -> Mapping[str, Any]:
    action = str(request.get("action", ""))
    historical = _historical(root)
    controlled = _controlled(root)
    if action == "seed_cases":
        return {"cases": [historical["case"], _mission033(root)["case"], _mission034(root)["case"], _mission050(root)["case"], controlled["case"]]}
    if action == "historical":
        return historical
    if action == "controlled":
        return controlled
    if action == "mission033":
        return _mission033(root)
    if action == "mission034":
        return _mission034(root)
    if action == "mission050":
        return _mission050(root)
    if action == "configured":
        config = request.get("case")
        if not isinstance(config, Mapping):
            raise ValueError("configured action requires a case object")
        return _configured(config)
    if action == "benchmark":
        snapshot = build_snapshot(root)
        return {"status": "AVAILABLE", "classification": "READ_ONLY_REPRODUCIBLE_ARTIFACT", "artifact_root": f"benchmarks/runs/{RECOVERY_RUN_ID}", "summary": snapshot["benchmark"], "artifacts": [f"benchmarks/runs/{RECOVERY_RUN_ID}/execution_log.json", f"benchmarks/runs/{RECOVERY_RUN_ID}/reports/mission-022-metric-boundary-compatibility.json"]}
    if action == "downstream":
        return _downstream(root)
    raise ValueError(f"unsupported AEGIS lifecycle action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    request = json.load(sys.stdin)
    if not isinstance(request, Mapping):
        raise ValueError("lifecycle request must be a JSON object")
    response = dispatch(args.root.resolve(), request)
    json.dump(_redact(_to_jsonable(response)), sys.stdout, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
