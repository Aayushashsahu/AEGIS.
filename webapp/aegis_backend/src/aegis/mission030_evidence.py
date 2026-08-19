"""Read-only Mission 029 evidence normalization for the Evidence Ledger.

This module reads committed JSON artifacts only. It neither contacts providers
nor writes, approves, verifies, risks, commits, or synthesizes missing stages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ArtifactLoadError(ValueError):
    """Raised when an expected, safe evidence artifact cannot be used."""


@dataclass(frozen=True)
class EvidenceStage:
    stage_id: str
    label: str
    status: str
    evidence_file: str
    record_id: str | None
    detail: str
    provenance: str


@dataclass(frozen=True)
class NormalizedDemoEvidence:
    mission: str
    status: str
    target_url: str
    collector_id: str
    row_count: int
    collection_mode: str
    collection_latency_ms: int | None
    provider_operation_ids: Mapping[str, str]
    observation_id: str | None
    detection_id: str | None
    diagnosis_id: str | None
    repair_request_id: str | None
    candidate_id: str | None
    verification_id: str | None
    risk_decision_id: str | None
    commit_decision_id: str | None
    error_code: str | None
    error_message: str | None
    provider_operation_counts: Mapping[str, int]
    stages: tuple[EvidenceStage, ...]
    provenance: Mapping[str, str]


class Mission029ArtifactLoader:
    """Normalize the committed Mission 029 JSON bundle without mutating it."""

    FILES = {
        "manifest": "demo_manifest.json",
        "collection": "collection_summary_reconciled.json",
        "observation": "observation_original.json",
        "mutation": "demo_mutation.json",
        "detection": "detection_result.json",
        "diagnosis": "diagnosis.json",
        "repair": "repair_request.json",
        "heal": "healing_failure.json",
        "termination": "pipeline_termination.json",
    }
    _SENSITIVE = {"authorization", "cookie", "password", "api_key", "apikey", "token", "secret"}

    def __init__(self, evidence_root: str | Path) -> None:
        self.evidence_root = Path(evidence_root)

    def _read(self, key: str) -> Mapping[str, Any]:
        path = self.evidence_root / self.FILES[key]
        if not path.is_file():
            raise ArtifactLoadError(f"missing Mission 029 artifact: {self.FILES[key]}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ArtifactLoadError(f"malformed Mission 029 artifact: {self.FILES[key]}") from exc
        if not isinstance(payload, dict):
            raise ArtifactLoadError(f"expected object Mission 029 artifact: {self.FILES[key]}")
        self._assert_redacted(payload, self.FILES[key])
        return payload

    def _assert_redacted(self, value: Any, source: str) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if str(key).lower() in self._SENSITIVE:
                    raise ArtifactLoadError(f"sensitive field present in Mission 029 artifact: {source}")
                self._assert_redacted(nested, source)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                self._assert_redacted(nested, source)

    def load(self) -> NormalizedDemoEvidence:
        manifest = self._read("manifest")
        collection = self._read("collection")
        observation = self._read("observation")
        mutation = self._read("mutation")
        detection = self._read("detection")
        diagnosis = self._read("diagnosis")
        repair = self._read("repair")
        heal = self._read("heal")
        termination = self._read("termination")
        collector_id = str(collection.get("collector_id", ""))
        if not collector_id or collector_id != str(manifest.get("collector_id", "")):
            raise ArtifactLoadError("collector identity mismatch between Mission 029 artifacts")
        target_url = str(manifest.get("target_url", ""))
        if not target_url.startswith("https://"):
            raise ArtifactLoadError("Mission 029 target URL is missing or unsafe")
        row_count = int(collection.get("row_count", -1))
        if row_count < 0 or row_count != int(manifest.get("row_count", -2)):
            raise ArtifactLoadError("row-count mismatch between Mission 029 artifacts")
        candidate_created = bool(termination.get("candidate_created", False))
        stages = (
            EvidenceStage("collector", "Collector", "SUCCESS", self.FILES["collection"], collector_id, "Committed Bright Data collector/run evidence.", "REAL_PROVIDER_EVIDENCE"),
            EvidenceStage("observation", "Observation", "RECORDED", self.FILES["observation"], self._nullable_id(observation, "observation_id"), "Untrusted AEGIS observation recorded from live output.", "REAL_PROVIDER_EVIDENCE"),
            EvidenceStage("mutation", "Mutation", f"{mutation.get('mutation_id', 'UNKNOWN')} / {detection.get('severity', 'UNKNOWN')}", self.FILES["mutation"], str(mutation.get("mutation_id", "")) or None, "Controlled reversible AEGIS-only evidence mutation.", "DEMO_CONTROLLED"),
            EvidenceStage("detection", "Detection", "DETECTED" if detection.get("detected") else "NOT_DETECTED", self.FILES["detection"], self._nullable_id(diagnosis, "detection_id"), "Deterministic detection result from the controlled observation.", "DEMO_CONTROLLED"),
            EvidenceStage("diagnosis", "Diagnosis", str(diagnosis.get("certainty", "NOT_RUN")), self.FILES["diagnosis"], self._nullable_id(diagnosis, "diagnosis_id"), "Existing deterministic diagnosis; ambiguity is retained.", "DEMO_CONTROLLED"),
            EvidenceStage("repair_request", "Repair request", "CREATED", self.FILES["repair"], self._nullable_id(repair, "repair_request_id"), "Canonical provider-neutral repair intent exists.", "DEMO_CONTROLLED"),
            EvidenceStage("bright_data_heal", "Bright Data heal", "FAILED / PROMPT_LIMIT", self.FILES["heal"], self._nullable_id(heal, "heal_id"), "The historical provider request failed before a candidate was created.", "REAL_PROVIDER_EVIDENCE"),
            EvidenceStage("candidate", "Candidate", "UNVERIFIED" if candidate_created else "NOT_CREATED", self.FILES["termination"], None, "No candidate record is synthesized when the provider did not create one.", "NOT_CREATED"),
            EvidenceStage("verification", "Verification", "NOT_RUN", self.FILES["termination"], None, "No candidate exists, so verification was not invoked.", "NOT_RUN"),
            EvidenceStage("risk", "Risk", "NOT_RUN", self.FILES["termination"], None, "No candidate exists, so RiskGovernor was not invoked.", "NOT_RUN"),
            EvidenceStage("commit", "Commit", "NOT_PERFORMED", self.FILES["termination"], None, "No candidate, approval, or production commit occurred.", "NOT_RUN"),
        )
        counts = {str(key): int(value) for key, value in dict(manifest.get("provider_operation_counts", {})).items()}
        return NormalizedDemoEvidence(
            mission=str(manifest.get("mission", "MISSION_029")),
            status=str(manifest.get("status", "UNKNOWN")),
            target_url=target_url,
            collector_id=collector_id,
            row_count=row_count,
            collection_mode=str(collection.get("mode", "UNKNOWN")),
            collection_latency_ms=self._nullable_int(collection, "latency_ms"),
            provider_operation_ids={str(key): str(value) for key, value in dict(collection.get("provider_operation_ids", {})).items()},
            observation_id=self._nullable_id(observation, "observation_id"),
            detection_id=self._nullable_id(diagnosis, "detection_id"),
            diagnosis_id=self._nullable_id(diagnosis, "diagnosis_id"),
            repair_request_id=self._nullable_id(repair, "repair_request_id"),
            candidate_id=None,
            verification_id=None,
            risk_decision_id=None,
            commit_decision_id=None,
            error_code=self._nullable_id(heal, "error_code"),
            error_message=self._nullable_id(heal, "error_message"),
            provider_operation_counts=counts,
            stages=stages,
            provenance={
                "collector_run": "REAL_PROVIDER_EVIDENCE",
                "heal": "REAL_PROVIDER_EVIDENCE",
                "mutation_detection": "DEMO_CONTROLLED",
                "candidate": "NOT_CREATED",
            },
        )

    @staticmethod
    def _nullable_id(payload: Mapping[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return str(value) if value not in {None, ""} else None

    @staticmethod
    def _nullable_int(payload: Mapping[str, Any], key: str) -> int | None:
        value = payload.get(key)
        return int(value) if isinstance(value, (int, float)) else None
