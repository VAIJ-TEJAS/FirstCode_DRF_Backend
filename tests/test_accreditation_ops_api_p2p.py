from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory

from enterprise.views import AccreditationOpsEvaluateAPIView
from utils.accreditation_ops import load_evidence_catalog


@pytest.mark.django_db
def test_p2p_acc_api_001_post() -> None:
    rows = load_evidence_catalog()[:25]
    submission = {row.id: {"status": "complete", "confidence": 0.9} for row in rows}
    body = {"institutionId": "inst-z", "cycleLabel": "2026-Q1", "submission": submission}
    factory = APIRequestFactory()
    request = factory.post("/enterprise/accreditation-ops/evaluate/", body, format="json")
    view = AccreditationOpsEvaluateAPIView.as_view()
    response = view(request)
    assert response.status_code == 200
    assert response.data["institutionId"] == "inst-z"
    assert "score" in response.data
