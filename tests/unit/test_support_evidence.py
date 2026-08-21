from __future__ import annotations

import hashlib

import pytest

from aegis.support_evidence import (
    SupportDiagnosisClass,
    SupportResponseInput,
    normalize_support_response,
)


def test_support_normalizer_classifies_only_explicit_code_fixer_language() -> None:
    response = SupportResponseInput(
        support_case_id="case-1",
        message_id="message-1",
        received_at="2026-08-21T00:00:00Z",
        sender="support@example.invalid",
        subject="Diagnostic",
        body="The code_fixer was unable to generate working code for this request.",
    )

    result = normalize_support_response(response, extracted_metadata={"provider_job_id": "j_example"})

    assert result.diagnosis is SupportDiagnosisClass.PROVIDER_CODE_FIXER_FAILURE
    assert result.confidence == "MEDIUM"
    assert result.provider_job_id == "j_example"
    assert result.raw_message_sha256 == hashlib.sha256(response.body.encode("utf-8")).hexdigest()


def test_support_normalizer_leaves_unclassified_text_unknown() -> None:
    response = SupportResponseInput(
        support_case_id=None,
        message_id=None,
        received_at=None,
        sender="support@example.invalid",
        subject="Update",
        body="We are reviewing the matter and will follow up.",
    )

    result = normalize_support_response(response)

    assert result.diagnosis is SupportDiagnosisClass.UNKNOWN
    assert result.confidence == "LOW"
    assert result.evidence_phrases == ()


def test_support_normalizer_rejects_empty_real_response_input() -> None:
    with pytest.raises(ValueError, match="required"):
        SupportResponseInput(None, None, None, "", "Subject", "Body")
