"""JSON fixtures aligned with FirstCode_React_Frontend changeRiskFixtures.ts."""

from __future__ import annotations

from typing import Any, Dict


def base_batch(batch_id: str) -> Dict[str, Any]:
    return {
        "batchId": batch_id,
        "environment": "production",
        "primarySurface": "web",
        "changedFiles": 8,
        "addedLines": 420,
        "deletedLines": 180,
        "churnLines": 300,
        "newTestFiles": 2,
        "f2pTestFiles": 1,
        "p2pTestFiles": 1,
        "testRegressions": 0,
        "migrationCount": 0,
        "majorDependencyBumps": 0,
        "touchesAuth": False,
        "touchesPayments": False,
        "touchesSecurityPolicy": False,
        "breakingApiChange": False,
        "hasRollbackPlan": True,
        "sloErrorBudgetRemainingPct": 45,
        "inFreezeWindow": False,
        "oncallAssigned": True,
    }


BATCH_HEALTHY = base_batch("batch-healthy")

BATCH_LARGE_THIN_TESTS: Dict[str, Any] = {
    **base_batch("batch-thin-tests"),
    "changedFiles": 22,
    "addedLines": 3200,
    "deletedLines": 900,
    "churnLines": 2800,
    "newTestFiles": 0,
    "f2pTestFiles": 0,
    "p2pTestFiles": 0,
}

BATCH_PAYMENTS_NO_ROLLBACK: Dict[str, Any] = {
    **base_batch("batch-pay"),
    "touchesPayments": True,
    "hasRollbackPlan": False,
    "addedLines": 800,
    "deletedLines": 200,
}

BATCH_FREEZE_LOW_BUDGET: Dict[str, Any] = {
    **base_batch("batch-freeze"),
    "inFreezeWindow": True,
    "sloErrorBudgetRemainingPct": 6,
    "oncallAssigned": False,
}

BATCH_MIGRATION_HEAVY: Dict[str, Any] = {
    **base_batch("batch-mig"),
    "migrationCount": 5,
    "hasRollbackPlan": True,
    "addedLines": 1200,
    "deletedLines": 400,
}
