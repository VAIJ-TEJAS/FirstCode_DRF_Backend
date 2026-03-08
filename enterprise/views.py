"""Enterprise monitoring API endpoints."""

from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from enterprise.health import build_liveness_payload, build_readiness_payload


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
