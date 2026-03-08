from __future__ import annotations

import os
from typing import Iterator

import pytest


@pytest.fixture(autouse=True)
def default_env_setup(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Provide deterministic env defaults for runtime/config tests.

    Tests in this folder are intentionally isolated from the full Django runtime.
    """

    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.test.local")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.test.local")

    yield


@pytest.fixture
def sample_profile() -> dict[str, object]:
    return {
        "user_id": 99,
        "current_level": "beginner",
        "target_level": "advanced",
        "weekly_hours": 8,
        "goal": "job-switch",
        "preference": "daily-practice",
        "active_days": ["monday", "tuesday", "thursday", "saturday"],
    }
