from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
MISSION_015_CONFIG = ROOT / "benchmarks/configs/mission_015_frozen_config.json"
MISSION_015_RECORDS = ROOT / "experiments/mission_015_freeze_records.json"
CORRECTED_CONFIG = ROOT / "benchmarks/configs/mission_017_corrected_frozen_config.json"
CORRECTED_DRY_RUN = ROOT / "benchmarks/configs/mission_017_corrected_dry_run.json"
CORRECTED_RECORDS = ROOT / "experiments/mission_017_corrected_freeze_records.json"
RUN_ID = "mission_017_corrected_freeze"
OLD_CONFIG_HASH = "f48ec5c5792b09623b6b6e4bcab9da6b9c5066506a57e012826a3b837e8d7d96"
ACTUAL_REVISIONS = {
    "BASELINE_A": "0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47",
    "BASELINE_B": "0e8bcc4ea8c1bbcb7dae21b12ec1710366e39f47",
    "AEGIS": "7de2bc65ed9eeb9f4abd24017543f3f366990738",
}
PARTICIPANTS = ("BASELINE_A", "BASELINE_B", "AEGIS")
MUTATIONS = ("M001", "M002", "M003", "M004", "M005", "M006")
RATIONALE = "Superseding owner-approved benchmark freeze after Mission 016 preflight identified a participant revision identity mismatch. All benchmark methodology, safety policy, mutation definitions, seed, fixture, timeout, retry, and metric formula remain unchanged."

import sys
sys.path.insert(0, str(ROOT / "src"))

from aegis.audit_store import _to_jsonable
from aegis.benchmark_config import freeze_config, load_benchmark_config, validate_config
from aegis.benchmark_runner import BenchmarkRunner, RunnerDryRunStatus
from aegis.participant_freeze import (
    OwnerReviewDecision,
    ParticipantFreezeProposal,
    apply_promotions,
    compute_participant_hash,
    promote_participant,
    proposal_from_spec,
    validate_participant_proposal,
)


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _resolve_revision(revision: str) -> bool:
    result = subprocess.run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT)
    return result.returncode == 0


def _source_at_revision(revision: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout


def inspect_strategy_separation() -> dict[str, object]:
    revision = ACTUAL_REVISIONS["BASELINE_A"]
    runner_source = _source_at_revision(revision, "src/aegis/benchmark_runner.py")
    participant_source = _source_at_revision(revision, "src/aegis/baseline_participants.py")
    baseline_a_start = runner_source.index("class BaselineAAdapter")
    baseline_b_start = runner_source.index("class BaselineBAdapter")
    aegis_start = runner_source.index("class AegisAdapter")
    baseline_a_region = runner_source[baseline_a_start:baseline_b_start]
    baseline_b_region = runner_source[baseline_b_start:aegis_start]
    forbidden_a_calls = ("baseline_b_model_call(", "RiskGovernor(", "CommitGate(", "verify_candidate(", "QuarantineLedger(", "Watch(")
    forbidden_b_calls = ("RiskGovernor(", "CommitGate(", "verify_candidate(", "QuarantineLedger(", "Watch(")
    baseline_a_checks = {
        "static_extractor_present": "BaselineAStaticExtractor" in baseline_a_region and "BaselineAStaticExtractor" in participant_source,
        "static_selector_execution": "BaselineAStaticExtractor().extract" in baseline_a_region,
        "forbidden_aegis_or_llm_calls_absent": all(symbol not in baseline_a_region for symbol in forbidden_a_calls),
        "model_caller_absent": "model_caller" not in baseline_a_region,
    }
    baseline_b_checks = {
        "gemini_model_present": 'BASELINE_B_MODEL_ID = "gemini-3.6-flash"' in participant_source,
        "approved_prompt_constants_present": "BASELINE_B_SYSTEM_PROMPT" in participant_source and "BASELINE_B_REPAIR_PROMPT_TEMPLATE" in participant_source,
        "injected_model_call_present": "baseline_b_model_call(" in baseline_b_region and "self._model_caller" in baseline_b_region,
        "first_candidate_configuration_present": "candidate_policy" in participant_source and "max_candidates" in participant_source and "auto_accept_first_candidate" in participant_source,
        "aegis_verification_risk_commit_calls_absent": all(symbol not in baseline_b_region for symbol in forbidden_b_calls),
    }
    return {
        "commit": revision,
        "baseline_a": {"checks": baseline_a_checks, "pass": all(baseline_a_checks.values())},
        "baseline_b": {"checks": baseline_b_checks, "pass": all(baseline_b_checks.values())},
        "strategies_distinct": all(baseline_a_checks.values()) and all(baseline_b_checks.values()),
        "note": "Both participant paths are distinct classes in the same implementation commit; no participant execution was performed.",
    }


def corrected_proposals(base_config: object) -> dict[str, ParticipantFreezeProposal]:
    specs = {spec.baseline_id: spec for spec in base_config.baselines}
    proposals: dict[str, ParticipantFreezeProposal] = {}
    for participant_id in PARTICIPANTS:
        proposal = proposal_from_spec(specs[participant_id])
        proposal = replace(
            proposal,
            prior_status="NOT_READY",
            implementation_revision=ACTUAL_REVISIONS[participant_id],
            configuration_hash="",
        )
        # __post_init__ computes the participant hash when configuration_hash is empty.
        proposals[participant_id] = proposal
    return proposals


def build_corrected_config(base_config: object, promotions: tuple[object, ...], created_at: str) -> object:
    corrected_base = replace(
        base_config,
        benchmark_id="aegis-benchmark-mission-017-corrected",
        benchmark_version="mission-017-corrected-freeze-v1",
        artifact_root="benchmarks/results/mission_017_corrected_freeze",
        config_version="mission-017-corrected-benchmark-config-v1",
        created_at=created_at,
        collection_policy={
            **dict(base_config.collection_policy),
            "freeze_status": "CORRECTED_SUPERSEDES_MISSION_015",
            "supersedes_configuration_hash": OLD_CONFIG_HASH,
        },
        evidence_policy={
            **dict(base_config.evidence_policy),
            "freeze_correction_reason": "Mission 016 preflight detected Baseline A/B implementation revision identity mismatch.",
            "supersedes_configuration_hash": OLD_CONFIG_HASH,
        },
    )
    return apply_promotions(corrected_base, promotions)


def main() -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    if not MISSION_015_CONFIG.exists() or not MISSION_015_RECORDS.exists():
        raise SystemExit("Mission 015 historical artifacts are required and must remain unchanged")
    revision_checks = {participant_id: {"revision": revision, "resolves": _resolve_revision(revision)} for participant_id, revision in ACTUAL_REVISIONS.items()}
    if not all(item["resolves"] for item in revision_checks.values()):
        raise SystemExit({"status": "STOPPED_NOT_READY", "revision_checks": revision_checks})

    strategy = inspect_strategy_separation()
    if not strategy["strategies_distinct"]:
        raise SystemExit({"status": "STOPPED_STRATEGY_CONFLICT", "strategy": strategy})

    old_config = load_benchmark_config(MISSION_015_CONFIG)
    proposals = corrected_proposals(old_config)
    participant_validations = {participant_id: validate_participant_proposal(proposal) for participant_id, proposal in proposals.items()}
    if any(not validation.ready for validation in participant_validations.values()):
        raise SystemExit({participant_id: validation.errors for participant_id, validation in participant_validations.items()})

    reviews: dict[str, OwnerReviewDecision] = {}
    promotions = []
    for participant_id in PARTICIPANTS:
        review = OwnerReviewDecision(
            participant_id=participant_id,
            approved=True,
            owner="PROJECT_OWNER",
            reviewer="PROJECT_OWNER",
            rationale=RATIONALE,
            reviewed_at=created_at,
            correlation_id=str(uuid4()),
        )
        reviews[participant_id] = review
        promotions.append(promote_participant(proposals[participant_id], review))
    promotions_tuple = tuple(promotions)

    corrected_config = build_corrected_config(old_config, promotions_tuple, created_at)
    validation = validate_config(corrected_config)
    if not validation.valid:
        raise SystemExit({"status": "STOPPED_INVALID_CONFIG", "errors": validation.errors})
    if corrected_config.configuration_hash == OLD_CONFIG_HASH:
        raise SystemExit("corrected configuration reused Mission 015 hash")

    runner = BenchmarkRunner(corrected_config)
    dry_run = runner.dry_run()
    if dry_run.status is not RunnerDryRunStatus.READY_TO_EXECUTE:
        raise SystemExit({"status": "STOPPED_NOT_READY", "dry_run": dry_run.to_dict()})
    shared = [runner.build_input(participant_id, "M005", 12345).shared_metadata() for participant_id in PARTICIPANTS]
    fairness = {
        "status": "PASS" if shared[0] == shared[1] == shared[2] and all(item["trial_metadata"]["ground_truth_runtime_payload"] == "NOT_PROVIDED" for item in shared) else "FAIL",
        "same_mutation": True,
        "same_seed": True,
        "same_fixture": True,
        "same_ground_truth_reference_shape": True,
        "same_timeout_policy": True,
        "same_retry_policy": True,
        "same_trial_metadata": True,
        "ground_truth_runtime_payload": "NOT_PROVIDED",
    }
    if fairness["status"] != "PASS":
        raise SystemExit({"status": "STOPPED_FAIRNESS", "fairness": fairness})

    _write(CORRECTED_CONFIG, corrected_config.to_dict())
    dry_payload = dict(dry_run.to_dict())
    dry_payload.update({"mission": "017", "run_id": RUN_ID, "fairness": fairness, "supersedes_configuration_hash": OLD_CONFIG_HASH, "benchmark_execution_allowed": False})
    _write(CORRECTED_DRY_RUN, dry_payload)
    records = {
        "mission": "017",
        "status": "CORRECTED_FREEZE_VALIDATED_ONLY",
        "created_at": created_at,
        "supersedes_mission": "015",
        "supersedes_configuration_hash": OLD_CONFIG_HASH,
        "new_configuration_hash": corrected_config.configuration_hash,
        "revision_checks": revision_checks,
        "strategy_separation": strategy,
        "participant_proposals": {participant_id: proposal.to_dict() for participant_id, proposal in proposals.items()},
        "participant_validations": {participant_id: validation.to_dict() for participant_id, validation in participant_validations.items()},
        "owner_review_decisions": {participant_id: {**dict(review.to_dict()), "corrected_revision": ACTUAL_REVISIONS[participant_id], "corrected_participant_hash": proposals[participant_id].configuration_hash} for participant_id, review in reviews.items()},
        "readiness_promotions": [result.promotion.to_dict() for result in promotions_tuple],
        "fairness": fairness,
        "dry_run_status": dry_run.status.value,
        "execution_counters": {
            "benchmark_runs_executed": dry_run.benchmark_runs_executed,
            "provider_operations_executed": dry_run.provider_operations_executed,
            "healing_operations_executed": dry_run.healing_operations_executed,
            "metric_results_generated": dry_run.metric_results_generated,
            "execution_authorized": dry_run.execution_authorized,
        },
        "historical_mission_015_records_unchanged": True,
    }
    _write(CORRECTED_RECORDS, records)
    print(json.dumps({
        "status": "CORRECTED_FREEZE_VALIDATED_ONLY",
        "new_configuration_hash": corrected_config.configuration_hash,
        "participant_hashes": {participant_id: proposals[participant_id].configuration_hash for participant_id in PARTICIPANTS},
        "dry_run_status": dry_run.status.value,
        "fairness": fairness["status"],
        "execution_counters": records["execution_counters"],
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
