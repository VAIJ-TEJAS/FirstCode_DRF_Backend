"""Enterprise monitoring API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from enterprise.health import build_liveness_payload, build_readiness_payload
from utils.change_risk_gate import decision_to_camel_dict, evaluate_change_batch, parse_batch_from_json


class LivenessAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        payload = build_liveness_payload()
        return Response(payload, status=status.HTTP_200_OK)


class ReadinessAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        payload = build_readiness_payload()
        http_status = status.HTTP_200_OK if payload["status"] in {"up", "degraded"} else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)


class ChangeRiskEvaluateAPIView(APIView):
    """
    Evaluate a change batch using the same rules as the React `enterpriseRuntime` change-risk module.
    Accepts camelCase JSON (ChangeBatchInput) and returns camelCase JSON (ChangeGateDecision).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        body = request.data
        if not isinstance(body, dict):
            return Response({"detail": "Expected a JSON object body."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            batch = parse_batch_from_json(body)
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        decision = evaluate_change_batch(batch, now_iso)
        return Response(decision_to_camel_dict(decision), status=status.HTTP_200_OK)
