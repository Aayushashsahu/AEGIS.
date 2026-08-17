"""AEGIS Mission 002: collection, immutable observation, and detection."""

from .adapter import AdapterError, BrightDataCliAdapter, CommandResult
from .contracts import default_extraction_contract
from .detection import evaluate_detection
from .models import (
    CollectionHandle,
    CollectionMode,
    CollectionResult,
    CollectionState,
    CollectorHandle,
    CollectorRequest,
    DetectionResult,
    DetectionSignal,
    ExtractionContract,
    FieldContract,
    Observation,
    ProviderProvenance,
)
from .test_double import DeterministicBrightDataTestDouble, TestDoubleScenario

__all__ = [
    "AdapterError",
    "BrightDataCliAdapter",
    "CollectionHandle",
    "CollectionMode",
    "CollectionResult",
    "CollectionState",
    "CollectorHandle",
    "CollectorRequest",
    "CommandResult",
    "default_extraction_contract",
    "DetectionResult",
    "DetectionSignal",
    "DeterministicBrightDataTestDouble",
    "evaluate_detection",
    "ExtractionContract",
    "FieldContract",
    "Observation",
    "ProviderProvenance",
    "TestDoubleScenario",
]
