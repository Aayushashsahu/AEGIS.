from __future__ import annotations

import json
from pathlib import Path

from aegis.mission059_evidence import candidate_status, extract_provider_identifiers, provider_id_status


ROOT = Path(__file__).resolve().parents[2]


def _raw(path: str) -> object:
    return json.loads((ROOT / path).read_bytes().decode("utf-8"))


def test_real_failed_payloads_have_no_observed_provider_identifier() -> None:
    mission053 = _raw("experiments/mission_053_candidate_only/raw_provider_response.bin")
    mission056 = _raw("experiments/mission_056_full_scale_recovery/heal_raw.bin")
    assert extract_provider_identifiers(mission053) == {}
    assert extract_provider_identifiers(mission056) == {}
    assert provider_id_status(mission053) == "ABSENT"
    assert provider_id_status(mission056) == "ABSENT"


def test_real_success_payload_is_complete_without_synthesizing_provider_identifiers() -> None:
    payload = _raw("experiments/mission_033_live_bright_data_success/provider_operations/operation_001_heal.json")["stdout"]
    status, preview, fields = candidate_status(payload)
    assert status == "COMPLETE"
    assert preview is not None
    assert fields == {"title": "PRESENT", "price": "PRESENT", "availability": "PRESENT"}
    assert extract_provider_identifiers(payload) == {}
