from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SettlementLine:
    partner_id: str
    revenue: float
    share_rate: float
    deductions: float


def settlement_amount(line: SettlementLine) -> float:
    gross_share = line.revenue * line.share_rate
    return round(max(gross_share - line.deductions, 0.0), 2)


def settlement_summary(lines: Iterable[SettlementLine]) -> dict:
    totals = {line.partner_id: 0.0 for line in lines}
    for line in lines:
        totals[line.partner_id] = round(totals[line.partner_id] + settlement_amount(line), 2)
    return {
        "partner_totals": totals,
        "total_settlement": round(sum(totals.values()), 2),
    }
