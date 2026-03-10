from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GuardrailInput:
    list_price: float
    floor_price: float
    discount_rate: float
    region: str


@dataclass(frozen=True)
class GuardrailDecision:
    approved: bool
    effective_price: float
    notes: List[str]


def evaluate_guardrails(input_data: GuardrailInput) -> GuardrailDecision:
    notes: List[str] = []
    effective_price = round(input_data.list_price * (1 - input_data.discount_rate), 2)
    approved = True

    if effective_price < input_data.floor_price:
        approved = False
        notes.append("below_floor")
    if input_data.discount_rate > 0.4:
        approved = False
        notes.append("excess_discount")
    if input_data.region.lower() in {"emea", "apac"} and input_data.discount_rate > 0.3:
        notes.append("regional_review")

    return GuardrailDecision(approved=approved, effective_price=effective_price, notes=notes)
