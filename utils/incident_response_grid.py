"""Incident response grid and escalation routing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class IncidentSignal:
    signal_id: str
    service: str
    severity: str
    customer_impact_percent: float
    error_rate_percent: float
    owner_team: str


@dataclass(frozen=True)
class EscalationDecision:
    signal_id: str
    urgency: str
    bridge_required: bool
    channels: List[str]
    runbook: str


def evaluate_incident(signal: IncidentSignal) -> EscalationDecision:
    impact = max(0.0, signal.customer_impact_percent)
    error_rate = max(0.0, signal.error_rate_percent)

    urgency = "normal"
    bridge = False
    channels = ["slack-ops"]

    if signal.severity.lower() in {"high", "critical"} or impact >= 20 or error_rate >= 8:
        urgency = "high"
        channels.append("pager-duty")

    if signal.severity.lower() == "critical" or impact >= 40 or error_rate >= 15:
        urgency = "critical"
        bridge = True
        channels.append("incident-bridge")

    runbook = f"runbook:{signal.service}:{urgency}"

    return EscalationDecision(
        signal_id=signal.signal_id,
        urgency=urgency,
        bridge_required=bridge,
        channels=channels,
        runbook=runbook,
    )


def team_incident_load(signals: Iterable[IncidentSignal]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for item in signals:
        summary[item.owner_team] = summary.get(item.owner_team, 0) + 1
    return dict(sorted(summary.items(), key=lambda row: row[0]))


def critical_services(signals: Iterable[IncidentSignal]) -> List[str]:
    services = {
        item.service
        for item in signals
        if evaluate_incident(item).urgency == "critical"
    }
    return sorted(services)


def urgency_summary(signals: Iterable[IncidentSignal]) -> Dict[str, int]:
    summary = {"normal": 0, "high": 0, "critical": 0}
    for signal in signals:
        decision = evaluate_incident(signal)
        summary[decision.urgency] += 1
    return summary


def channel_usage(signals: Iterable[IncidentSignal]) -> Dict[str, int]:
    usage: Dict[str, int] = {}
    for signal in signals:
        decision = evaluate_incident(signal)
        for channel in decision.channels:
            usage[channel] = usage.get(channel, 0) + 1
    return dict(sorted(usage.items(), key=lambda row: row[0]))


def incident_digest(signals: Iterable[IncidentSignal]) -> Dict[str, object]:
    rows = list(signals)
    decisions = [evaluate_incident(row) for row in rows]
    return {
        "total_signals": len(rows),
        "urgency_summary": urgency_summary(rows),
        "critical_services": critical_services(rows),
        "bridge_required_count": len([item for item in decisions if item.bridge_required]),
        "channel_usage": channel_usage(rows),
    }
