"""Provider-free verification and risk projection for actual Mission 041B rerun output."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aegis.audit_store import _to_jsonable
from aegis.commit_gate import CommitGate, OutputEligibilityBoundary
from aegis.healing import RepairCandidate
from aegis.models import ProviderProvenance
from aegis.risk import RiskGovernor
from aegis.verification import IndependentEvidence, VerificationContext, VerificationProvenance, verify_candidate
from scripts.mission033_lifecycle import FIELDS, _observation_from_run, _read_json, _write_json, mission033_contract
from scripts.mission033_verify_candidate import _canonical_row


MISSION_DIR = ROOT / "experiments" / "mission_041_post_heal_rerun"
MISSION033_DIR = ROOT / "experiments" / "mission_033_live_bright_data_success"


def main() -> int:
    output = _read_json(MISSION_DIR / "post_heal_output.json")
    rows = output.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise RuntimeError("Mission 041B requires recorded structured real-provider rows.")
    target_contract = _read_json(MISSION033_DIR / "target_contract.json")
    initial_run = _read_json(MISSION033_DIR / "initial_run.json")
    target_url = str(target_contract["target_url"])
    baseline = _observation_from_run(initial_run, target_url=target_url, target_version="v1")
    normalized_history = replace(baseline, output=tuple(_canonical_row(row) for row in baseline.output), schema=FIELDS, row_count=len(baseline.output))
    candidate = RepairCandidate(
        candidate_id="candidate_m041b_real_rerun",
        repair_request_id="repair_m033_compatible",
        collector_reference=str(output["collector_id"]),
        provider_operation_reference="mission041b-rerun-c_mt09pib13nxqz1coi",
        provider_status="COMPLETED",
        preview_result=rows,
        diff_summary="Actual post-approval rerun output",
        approval_command=None,
        raw_evidence_ref="evidence://mission-041/post-heal-output.json",
        provenance=ProviderProvenance.BRIGHT_DATA,
        latency_ms=int(_read_json(MISSION_DIR / "rerun_result.json")["elapsed_ms"]),
    )
    expected = {"title": "AEGIS Verification Widget", "price": {"currency": "USD", "value": 599}, "availability": "Available"}
    independent = IndependentEvidence(
        evidence_id="independent_m033_owned_target_contract_v2",
        source="AEGIS-owned public target contract and direct v2 target snapshot",
        rows=(expected,),
        provenance=VerificationProvenance.DETERMINISTIC,
        source_group="AEGIS_OWNED_TARGET_DIRECT_FETCH",
        evidence_refs=("evidence://mission-033/target-contract.json", "evidence://mission-033/independent-target-snapshot.html"),
        correlation_id="mission041b-rerun-c_mt09pib13nxqz1coi",
    )
    verification = verify_candidate(VerificationContext(
        candidate=candidate,
        contract=mission033_contract(),
        candidate_output=tuple(_canonical_row(row) for row in rows),
        history=(normalized_history,),
        independent_evidence=independent,
        correlation_id="mission041b-rerun-c_mt09pib13nxqz1coi",
        evidence_refs=("evidence://mission-041/post-heal-output.json", "evidence://mission-033/target-contract.json"),
        semantic_expectations=expected,
        history_source_group="BRIGHT_DATA_LIVE_COLLECTION",
    ))
    risk = RiskGovernor().decide(verification, candidate, correlation_id=verification.correlation_id)
    commit = CommitGate().evaluate(candidate, verification, risk, mission033_contract(), known_good_version=None, authorization=None, correlation_id=verification.correlation_id)
    eligibility = OutputEligibilityBoundary.evaluate(commit)
    _write_json(MISSION_DIR / "verification.json", _to_jsonable(verification))
    _write_json(MISSION_DIR / "risk_decision.json", _to_jsonable(risk))
    _write_json(MISSION_DIR / "commit_decision.json", _to_jsonable(commit))
    _write_json(MISSION_DIR / "output_eligibility.json", _to_jsonable(eligibility))
    print(json.dumps({"verification": _to_jsonable(verification), "risk": _to_jsonable(risk), "commit": _to_jsonable(commit)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
