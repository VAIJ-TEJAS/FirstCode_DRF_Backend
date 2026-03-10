from __future__ import annotations

import importlib.util
import pytest


def test_f2p_1899_catalog_digest_available_when_module_present() -> None:
    if importlib.util.find_spec("utils.enterprise_catalog") is None:
        pytest.skip("catalog module not available")

    from utils.enterprise_catalog import CatalogItem, catalog_digest

    digest = catalog_digest([
        CatalogItem("c1", "bootcamp", 1200.0, True, 50),
        CatalogItem("c2", "bootcamp", 900.0, False, 0),
        CatalogItem("c3", "enterprise", 2000.0, True, 80),
    ])

    assert digest["active_items"] == 2
    assert digest["seat_capacity"] == 130
