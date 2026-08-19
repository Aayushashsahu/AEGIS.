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

from aegis.audit_store import _redact, _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.mission030_evidence import Mission029ArtifactLoader
from aegis.risk import RiskGovernor
from aegis.verification import verify_candidate
from aegis.verification_double import VerificationFixture, build_verification_fixture
from scripts.mission031_build_demo_snapshot import RECOVERY_RUN_ID, build_snapshot


ROOT = Path(__file__).resolve().parents[1]
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


def _configured(payload: Mapping[str, Any]) -> dict[str, Any]:
    case_id = str(payload["case_id"])
    fields = list(payload.get("fields", []))
    case = {**payload, "lifecycle": {"current_status": "CONFIGURED", "event_count": 0, "latest_event_type": None, "evidence_refs": []}, "actions": [], "action_policy": "Configuration is persisted, but no collection, observation, repair, verification, risk, or commit evidence has been recorded."}
    nodes = [_node("TARGET", "CONFIGURED", "USER_CONFIGURED", str(payload["target_url"]), domain_status="user_configured")]
    graph = _graph(case_id, "CONFIGURED_CASE", nodes, "This case has only user-configured target and contract data. AEGIS has not inferred lifecycle evidence.", "NOT_EVALUATED")
    return {"case": case, "events": [], "graph": graph, "fields": fields}


def dispatch(root: Path, request: Mapping[str, Any]) -> Mapping[str, Any]:
    action = str(request.get("action", ""))
    historical = _historical(root)
    controlled = _controlled(root)
    if action == "seed_cases":
        return {"cases": [historical["case"], controlled["case"]]}
    if action == "historical":
        return historical
    if action == "controlled":
        return controlled
    if action == "configured":
        config = request.get("case")
        if not isinstance(config, Mapping):
            raise ValueError("configured action requires a case object")
        return _configured(config)
    if action == "benchmark":
        snapshot = build_snapshot(root)
        return {"status": "AVAILABLE", "classification": "READ_ONLY_REPRODUCIBLE_ARTIFACT", "artifact_root": f"benchmarks/runs/{RECOVERY_RUN_ID}", "summary": snapshot["benchmark"], "artifacts": [f"benchmarks/runs/{RECOVERY_RUN_ID}/execution_log.json", f"benchmarks/runs/{RECOVERY_RUN_ID}/reports/mission-022-metric-boundary-compatibility.json"]}
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
