"""Small standard-library-only helpers for immutable AEGIS records."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


def deep_freeze(value: Any) -> Any:
    """Return a recursively immutable representation of a JSON-like value."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(deep_freeze(item) for item in value)
    return value


def deep_thaw(value: Any) -> Any:
    """Return a mutable JSON-like copy for adapter/test-boundary serialization."""

    if isinstance(value, Mapping):
        return {key: deep_thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [deep_thaw(item) for item in value]
    return value


def freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Freeze a string-keyed mapping while preserving mapping semantics."""

    return deep_freeze(dict(value))
