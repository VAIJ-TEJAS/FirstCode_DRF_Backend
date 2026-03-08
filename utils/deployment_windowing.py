"""Release window helpers for orchestrated backend deployments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class WindowRule:
    name: str
    start_hour_utc: int
    end_hour_utc: int
    weekdays: List[int]


DEFAULT_WINDOW_RULES = [
    WindowRule(name="weekday-morning", start_hour_utc=6, end_hour_utc=12, weekdays=[0, 1, 2, 3, 4]),
    WindowRule(name="weekday-evening", start_hour_utc=16, end_hour_utc=21, weekdays=[0, 1, 2, 3, 4]),
]


def _normalize_hour(hour: int) -> int:
    if hour < 0:
        return 0
    if hour > 23:
        return 23
    return hour


def is_within_window(moment: datetime, rule: WindowRule) -> bool:
    hour = _normalize_hour(moment.hour)
    weekday = moment.weekday()

    if weekday not in rule.weekdays:
        return False

    return rule.start_hour_utc <= hour < rule.end_hour_utc


def active_windows(moment: datetime, rules: Iterable[WindowRule] | None = None) -> List[str]:
    catalog = list(rules or DEFAULT_WINDOW_RULES)
    return [rule.name for rule in catalog if is_within_window(moment, rule)]


def next_window(moment: datetime, rules: Iterable[WindowRule] | None = None) -> Dict[str, object]:
    catalog = list(rules or DEFAULT_WINDOW_RULES)

    if not catalog:
        return {"name": "none", "eta_hours": None}

    current = active_windows(moment, catalog)
    if current:
        return {"name": current[0], "eta_hours": 0}

    for hour_offset in range(1, 24 * 7):
        candidate = moment.replace(minute=0, second=0, microsecond=0) + timedelta(hours=hour_offset)
        names = active_windows(candidate, catalog)
        if names:
            return {"name": names[0], "eta_hours": hour_offset}

    return {"name": "none", "eta_hours": None}


def release_window_snapshot(now_utc: datetime | None = None) -> Dict[str, object]:
    stamp = now_utc or datetime.now(timezone.utc)
    active = active_windows(stamp)

    return {
        "timestamp_utc": stamp.isoformat(),
        "active_windows": active,
        "can_deploy_now": len(active) > 0,
    }
