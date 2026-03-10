import importlib.util
import pytest


MODULE_PATH = "utils.contract_entitlements"


def test_contract_entitlements_p2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("contract entitlements module not available")

    from utils.contract_entitlements import build_entitlement_plan, entitlement_snapshot

    plan_a = build_entitlement_plan(seats=75, support_tier="enterprise")
    plan_b = build_entitlement_plan(seats=20, support_tier="standard")

    snapshot = entitlement_snapshot({"a": plan_a, "b": plan_b})

    assert snapshot["total_accounts"] == 2
    assert snapshot["enterprise_accounts"] == 1
    assert snapshot["analytics_enabled"] == 1
