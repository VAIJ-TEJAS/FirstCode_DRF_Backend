from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    week: int
    minutes: int
    module_id: str


@dataclass(frozen=True)
class Plan:
    weeks: int
    sessions: list[Session]


def total_minutes(plan: Plan) -> int:
    return sum(session.minutes for session in plan.sessions)


def week_load_map(plan: Plan) -> dict[int, int]:
    loads: dict[int, int] = {}
    for session in plan.sessions:
        loads[session.week] = loads.get(session.week, 0) + session.minutes
    return loads


def detect_overload_weeks(plan: Plan, weekly_capacity: int) -> list[int]:
    return sorted([week for week, minutes in week_load_map(plan).items() if minutes > weekly_capacity])


def rebalance_overload(plan: Plan, weekly_capacity: int) -> Plan:
    sessions = list(plan.sessions)
    index = 0

    while index < len(sessions):
        target = sessions[index]
        current_loads = week_load_map(Plan(weeks=plan.weeks, sessions=sessions))
        current_week_load = current_loads.get(target.week, 0)

        if current_week_load <= weekly_capacity:
            index += 1
            continue

        overflow = current_week_load - weekly_capacity
        movable = target.minutes // 2
        move = min(overflow, movable)

        if move < 20:
            index += 1
            continue

        sessions[index] = Session(week=target.week, minutes=target.minutes - move, module_id=target.module_id)
        sessions.append(Session(week=target.week + 1, minutes=move, module_id=f"{target.module_id}-split"))
        index += 1

    return Plan(weeks=max(session.week for session in sessions), sessions=sessions)


def test_p2p_009_total_minutes_matches_sum_of_session_minutes() -> None:
    plan = Plan(
        weeks=3,
        sessions=[
            Session(week=1, minutes=90, module_id="m1"),
            Session(week=1, minutes=60, module_id="m2"),
            Session(week=2, minutes=120, module_id="m3"),
        ],
    )

    assert total_minutes(plan) == 270


def test_p2p_010_week_load_map_groups_by_week() -> None:
    plan = Plan(
        weeks=2,
        sessions=[
            Session(week=1, minutes=90, module_id="m1"),
            Session(week=1, minutes=60, module_id="m2"),
            Session(week=2, minutes=120, module_id="m3"),
        ],
    )

    assert week_load_map(plan) == {1: 150, 2: 120}


def test_p2p_011_detect_overload_weeks_identifies_breaches() -> None:
    plan = Plan(
        weeks=2,
        sessions=[
            Session(week=1, minutes=200, module_id="m1"),
            Session(week=2, minutes=100, module_id="m2"),
        ],
    )

    assert detect_overload_weeks(plan, weekly_capacity=180) == [1]


def test_p2p_012_rebalance_overload_moves_minutes_to_next_week() -> None:
    plan = Plan(
        weeks=2,
        sessions=[
            Session(week=1, minutes=220, module_id="m1"),
            Session(week=1, minutes=110, module_id="m2"),
            Session(week=2, minutes=100, module_id="m3"),
        ],
    )

    rebalanced = rebalance_overload(plan, weekly_capacity=180)

    assert rebalanced.weeks >= 2
    assert any(session.module_id.endswith("-split") for session in rebalanced.sessions)


def test_p2p_013_rebalanced_plan_reduces_or_equalizes_overload_count() -> None:
    plan = Plan(
        weeks=3,
        sessions=[
            Session(week=1, minutes=240, module_id="m1"),
            Session(week=1, minutes=120, module_id="m2"),
            Session(week=2, minutes=100, module_id="m3"),
            Session(week=3, minutes=80, module_id="m4"),
        ],
    )

    before = detect_overload_weeks(plan, weekly_capacity=180)
    after = detect_overload_weeks(rebalance_overload(plan, weekly_capacity=180), weekly_capacity=180)

    assert len(after) <= len(before)


def test_p2p_014_rebalance_keeps_total_minutes_constant() -> None:
    plan = Plan(
        weeks=2,
        sessions=[
            Session(week=1, minutes=260, module_id="m1"),
            Session(week=2, minutes=100, module_id="m2"),
        ],
    )

    rebalanced = rebalance_overload(plan, weekly_capacity=180)

    assert total_minutes(rebalanced) == total_minutes(plan)


def test_p2p_015_no_rebalance_when_plan_already_within_capacity() -> None:
    plan = Plan(
        weeks=2,
        sessions=[
            Session(week=1, minutes=120, module_id="m1"),
            Session(week=2, minutes=120, module_id="m2"),
        ],
    )

    rebalanced = rebalance_overload(plan, weekly_capacity=180)

    assert rebalanced.sessions == plan.sessions


def test_p2p_016_rebalance_handles_multiple_overloaded_weeks() -> None:
    plan = Plan(
        weeks=3,
        sessions=[
            Session(week=1, minutes=220, module_id="m1"),
            Session(week=1, minutes=220, module_id="m2"),
            Session(week=2, minutes=220, module_id="m3"),
            Session(week=2, minutes=220, module_id="m4"),
            Session(week=3, minutes=80, module_id="m5"),
        ],
    )

    rebalanced = rebalance_overload(plan, weekly_capacity=180)

    assert rebalanced.weeks >= 3
    assert len([session for session in rebalanced.sessions if session.module_id.endswith("-split")]) >= 2
