import importlib.util
import pytest


MODULE_PATH = "utils.billing_reconciliation"


def test_billing_reconciliation_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("billing reconciliation module not available")

    from utils.billing_reconciliation import InvoiceLine, reconciliation_report

    report = reconciliation_report([
        InvoiceLine(invoice_id="inv-1", amount=12000, paid=12000),
        InvoiceLine(invoice_id="inv-2", amount=8000, paid=3000),
    ])

    assert report["paid_count"] == 1
    assert report["open_count"] == 1
    assert report["outstanding"] == 5000
