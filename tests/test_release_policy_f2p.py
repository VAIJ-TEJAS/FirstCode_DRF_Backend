from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import build_release_context, decision_to_dict, evaluate_release_policy, release_window_names


def test_f2p_009_release_denied_when_ci_fails() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=False,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert any("CI pipeline" in blocker for blocker in decision.blockers)


def test_f2p_010_release_denied_when_outside_window() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 2, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert any("outside approved release windows" in blocker for blocker in decision.blockers)


def test_f2p_011_release_denied_when_branch_is_not_allowed() -> None:
    decision = evaluate_release_policy(
        branch_name="feature/new-ui",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert any("only allowed" in blocker for blocker in decision.blockers)


def test_f2p_012_release_denied_when_runtime_contains_errors() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.09",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 2, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert decision.risk_level == "critical"


def test_f2p_013_release_approved_for_compliant_rollout() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=400,
    )

    assert decision.approved is True


def test_f2p_014_window_names_are_exposed_for_observability() -> None:
    names = release_window_names()
    assert "weekday-morning" in names


def test_f2p_015_decision_to_dict_contains_expected_keys() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    payload = decision_to_dict(decision)

    assert set(payload.keys()) == {
        "approved",
        "reason",
        "blockers",
        "risk_level",
        "requires_rollback_plan",
    }


def test_f2p_016_release_context_contains_decision_payload() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=250,
    )

    assert "decision" in context
    assert isinstance(context["decision"], dict)


def test_f2p_017_large_change_size_requires_rollback_even_without_warnings() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1300,
    )

    payload = decision_to_dict(decision)
    assert payload["requires_rollback_plan"] is True


def test_f2p_018_small_change_size_keeps_rollback_plan_optional() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=350,
    )

    payload = decision_to_dict(decision)
    assert payload["requires_rollback_plan"] is False
