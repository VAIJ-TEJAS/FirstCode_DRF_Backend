from __future__ import annotations

"""
Integration-style tests for ChangeRiskEvaluateAPIView without resolving the full URLconf.

Using APIClient against real URLs imports `course.views` → WeasyPrint, which fails on
Windows CI/dev machines without GTK. Calling the view directly only imports enterprise.views.
"""

import pytest
from rest_framework.test import APIRequestFactory

from enterprise.views import ChangeRiskEvaluateAPIView

from tests.change_risk_fixtures import BATCH_HEALTHY


@pytest.mark.django_db
def test_p2p_cr_api_001_evaluate_returns_camel_case_decision() -> None:
    factory = APIRequestFactory()
    request = factory.post("/enterprise/change-risk/evaluate/", BATCH_HEALTHY, format="json")
    view = ChangeRiskEvaluateAPIView.as_view()
    response = view(request)
    assert response.status_code == 200
    body = response.data
    assert body["batchId"] == "batch-healthy"
    assert body["verdict"] in {"pass", "warn", "block"}
    assert "score" in body and "overall" in body["score"]
    assert "issues" in body and isinstance(body["issues"], list)
    assert "recommendedActions" in body
    assert "generatedAtISO" in body


@pytest.mark.django_db
def test_p2p_cr_api_002_missing_field_returns_400() -> None:
    factory = APIRequestFactory()
    bad = {k: v for k, v in BATCH_HEALTHY.items() if k != "batchId"}
    request = factory.post("/enterprise/change-risk/evaluate/", bad, format="json")
    view = ChangeRiskEvaluateAPIView.as_view()
    response = view(request)
    assert response.status_code == 400
