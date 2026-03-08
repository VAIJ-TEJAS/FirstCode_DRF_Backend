from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from course.planner.engine import run_planner
from course.planner.serializers import PlannerRequestSerializer, PlannerResponseSerializer


class LearningPathPlannerAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_serializer = PlannerRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        payload = request_serializer.validated_data

        profile = {
            "user_id": request.user.id,
            "current_level": payload["current_level"],
            "target_level": payload["target_level"],
            "weekly_hours": payload["weekly_hours"],
            "goal": payload["goal"],
            "preference": payload["preference"],
            "active_days": payload["active_days"],
        }

        result = run_planner(
            profile=profile,
            include_assessment=payload["include_assessment"],
            max_weeks=payload["max_weeks"],
            start_week=payload["start_week"],
            rebalance_overload=payload["rebalance_overload"],
        )

        response_serializer = PlannerResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        response_status = status.HTTP_200_OK if not result["validation_errors"] else status.HTTP_400_BAD_REQUEST
        return Response(response_serializer.data, status=response_status)
