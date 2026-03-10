import importlib.util
import pytest


MODULE_PATH = "utils.payment_recovery"


def test_payment_recovery_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("payment recovery module not available")

    from utils.payment_recovery import PaymentAttempt, recovery_summary

    summary = recovery_summary([
        PaymentAttempt(invoice_id="inv-1", amount=5000, method="card", success=False),
        PaymentAttempt(invoice_id="inv-1", amount=5000, method="card", success=False),
        PaymentAttempt(invoice_id="inv-2", amount=8000, method="bank", success=True),
    ])

    assert summary["total_outstanding"] == 10000
    assert summary["active_recoveries"] == 1
