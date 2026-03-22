from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory

from enterprise.views import SloForecastEvaluateAPIView

from tests.slo_forecaster_fixtures import BATCH_HEALTHY


@pytest.mark.django_db
def test_p2p_sf_api_001_post_returns_forecast() -> None:
    factory = APIRequestFactory()
    request = factory.post("/enterprise/slo-forecast/evaluate/", BATCH_HEALTHY, format="json")
    view = SloForecastEvaluateAPIView.as_view()
    response = view(request)
    assert response.status_code == 200
    body = response.data
    assert body["serviceId"] == "svc-api-healthy"
    assert body["riskTier"] in {"green", "yellow", "orange", "red"}
    assert "metrics" in body and "burnMultiple" in body["metrics"]


@pytest.mark.django_db
def test_p2p_sf_api_002_missing_field_400() -> None:
    factory = APIRequestFactory()
    bad = {k: v for k, v in BATCH_HEALTHY.items() if k != "serviceId"}
    request = factory.post("/enterprise/slo-forecast/evaluate/", bad, format="json")
    view = SloForecastEvaluateAPIView.as_view()
    response = view(request)
    assert response.status_code == 400
