"""Provider-free parsing and normalization helpers for the Mission 056 evidence flow."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup


REQUIRED_FIELDS = ("title", "price", "availability")
_PRICE_RE = re.compile(r"^\$(?P<value>[0-9]+(?:\.[0-9]{1,2})?)$")


def field_state(row: Mapping[str, Any], field: str) -> str:
    if field not in row:
        return "MISSING"
    value = row[field]
    if value is None:
        return "NULL"
    if isinstance(value, str) and not value.strip():
        return "EMPTY"
    return "PRESENT"


def candidate_field_states(preview: Sequence[Mapping[str, Any]] | None) -> dict[str, str]:
    first = preview[0] if preview else {}
    return {field: field_state(first, field) for field in REQUIRED_FIELDS}


def candidate_is_complete(preview: Sequence[Mapping[str, Any]] | None) -> bool:
    return bool(preview) and all(state == "PRESENT" for state in candidate_field_states(preview).values())


def normalize_candidate_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project only declared fields and transparently decode a USD `$NNN.NN` price."""

    price: Any = row.get("price")
    if isinstance(price, Mapping):
        price = {key: price[key] for key in ("currency", "value") if key in price}
    elif isinstance(price, str):
        match = _PRICE_RE.fullmatch(price.strip())
        if match:
            price = {"currency": "USD", "value": float(match.group("value"))}
    return {"title": row.get("title"), "price": price, "availability": row.get("availability")}


def target_facts_from_html(raw_html: bytes, *, variant: str) -> dict[str, Any]:
    """Extract expected target facts from a direct controlled-target response only."""

    soup = BeautifulSoup(raw_html, "html.parser")
    selector = {
        "baseline": {
            "title": "[data-aegis-field='title']",
            "price": "[data-aegis-field='price']",
            "availability": "[data-aegis-field='availability']",
        },
        "drift": {
            "title": "[data-testid='product-title']",
            "price": "[data-testid='product-price']",
            "availability": "[data-testid='product-availability']",
        },
    }.get(variant)
    if selector is None:
        raise ValueError("variant must be baseline or drift")
    nodes = {field: soup.select_one(css) for field, css in selector.items()}
    if any(node is None for node in nodes.values()):
        raise ValueError("controlled target response is missing a required extraction fact")
    title = nodes["title"].get_text(" ", strip=True)  # type: ignore[union-attr]
    price_node = nodes["price"]
    availability = nodes["availability"].get_text(" ", strip=True)  # type: ignore[union-attr]
    price_text = price_node.get_text(" ", strip=True)  # type: ignore[union-attr]
    currency = price_node.get("data-currency") or price_node.get("data-money-currency")  # type: ignore[union-attr]
    value = price_node.get("data-value") or price_node.get("data-money-value")  # type: ignore[union-attr]
    if not all(isinstance(item, str) and item for item in (title, price_text, availability, currency, value)):
        raise ValueError("controlled target response has incomplete title, price, or availability metadata")
    try:
        numeric_value = float(value)
    except ValueError as exc:
        raise ValueError("controlled target price value is not numeric") from exc
    return {"title": title, "price": {"currency": currency, "value": numeric_value}, "availability": availability}
