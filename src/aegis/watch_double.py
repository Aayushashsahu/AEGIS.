"""Deterministic Mission 007 post-commit watch fixtures."""

from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import Any

from .commit_gate_double import CommitGateFixture, build_commit_gate_fixture
from .immutability import deep_thaw
from .models import CollectionMode, ExtractionContract, Observation, ProviderProvenance
from .watch import WatchEngine, WatchRegistration


class WatchFixture(str, Enum):
    __test__ = False
    HEALTHY_AFTER_COMMIT = "HEALTHY_AFTER_COMMIT"
    REGRESSION_SCHEMA = "REGRESSION_SCHEMA"
    REGRESSION_SEMANTIC = "REGRESSION_SEMANTIC"
    REGRESSION_STATISTICAL = "REGRESSION_STATISTICAL"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"


def build_watch_fixture(fixture: WatchFixture) -> tuple[WatchRegistration, Observation, ExtractionContract]:
    candidate, context, verification, risk_decision, known_good, authorization, commit_decision = _committed_baseline()
    contract = context.contract
    rows = [dict(row) for row in deep_thaw(candidate.preview_result)]
    if fixture is WatchFixture.REGRESSION_SCHEMA:
        rows[0].pop("price", None)
    elif fixture is WatchFixture.REGRESSION_SEMANTIC:
        rows[0]["price"] = -1
    elif fixture is WatchFixture.REGRESSION_STATISTICAL:
        contract = replace(contract, max_rows=1)
        rows.append(dict(rows[0], product_id="gpu-2", title="Second GPU", url="https://example.test/gpu-2"))
    evidence_refs = () if fixture is WatchFixture.UNKNOWN_EVIDENCE else (f"evidence://TEST_DOUBLE/mission-007/{fixture.value.lower()}",)
    observation = Observation(
        collection_id=f"watch-collection-{fixture.value.lower()}",
        collector_id=candidate.collector_reference,
        provider_operation_ids={"watch": f"test-double-watch-{fixture.value.lower()}"},
        input={"target_url": "https://example.test/gpu-1"},
        output=rows,
        schema=tuple(sorted({key for row in rows for key in row})),
        row_count=len(rows),
        latency_ms=1,
        collection_mode=CollectionMode.TEST_DOUBLE,
        provider_provenance=ProviderProvenance.TEST_DOUBLE,
        evidence_refs=evidence_refs,
    )
    registration = WatchEngine().register(
        candidate,
        verification,
        risk_decision,
        commit_decision,
        known_good,
        contract,
        pipeline_reference="test-double-pipeline-mission007",
        correlation_id=context.correlation_id,
    )
    return registration, observation, contract


def _committed_baseline():
    candidate, context, verification, risk_decision, known_good, authorization = build_commit_gate_fixture(CommitGateFixture.COMMIT_ELIGIBLE)
    from .commit_gate import CommitGate

    commit_decision = CommitGate().evaluate(
        candidate,
        verification,
        risk_decision,
        context.contract,
        known_good,
        authorization,
        correlation_id=context.correlation_id,
    )
    return candidate, context, verification, risk_decision, known_good, authorization, commit_decision
