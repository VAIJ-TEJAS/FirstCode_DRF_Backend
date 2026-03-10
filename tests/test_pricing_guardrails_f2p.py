import importlib.util
import pytest


MODULE_PATH = "utils.pricing_guardrails"


def test_pricing_guardrails_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("pricing guardrails module not available")

    from utils.pricing_guardrails import GuardrailInput, evaluate_guardrails

    decision = evaluate_guardrails(GuardrailInput(
        list_price=20000,
        floor_price=15000,
        discount_rate=0.2,
        region="NA",
    ))

    assert decision.approved is True
    assert decision.effective_price == 16000
