"""Enterprise catalog management helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    category: str
    price: float
    active: bool
    seats_supported: int


@dataclass(frozen=True)
class CatalogSummary:
    total_items: int
    active_items: int
    average_price: float
    seat_capacity: int


def summarize_catalog(items: Iterable[CatalogItem]) -> CatalogSummary:
    rows = list(items)
    if not rows:
        return CatalogSummary(0, 0, 0.0, 0)

    total = len(rows)
    active = len([row for row in rows if row.active])
    avg_price = round(sum(max(0.0, row.price) for row in rows) / total, 2)
    seat_capacity = sum(max(0, row.seats_supported) for row in rows if row.active)

    return CatalogSummary(total, active, avg_price, seat_capacity)


def category_mix(items: Iterable[CatalogItem]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in items:
        counts[row.category] = counts.get(row.category, 0) + 1
    return counts


def active_items(items: Iterable[CatalogItem]) -> List[str]:
    return [row.item_id for row in items if row.active]


def catalog_digest(items: Iterable[CatalogItem]) -> Dict[str, object]:
    summary = summarize_catalog(items)
    return {
        "total_items": summary.total_items,
        "active_items": summary.active_items,
        "average_price": summary.average_price,
        "seat_capacity": summary.seat_capacity,
        "category_mix": category_mix(items),
        "active_ids": active_items(items),
    }


def price_bands(items: Iterable[CatalogItem]) -> Dict[str, int]:
    bands = {"budget": 0, "standard": 0, "premium": 0}
    for row in items:
        if row.price < 800:
            bands["budget"] += 1
        elif row.price < 1500:
            bands["standard"] += 1
        else:
            bands["premium"] += 1
    return bands


def catalog_rankings(items: Iterable[CatalogItem]) -> List[str]:
    return [row.item_id for row in sorted(items, key=lambda item: (-item.seats_supported, item.item_id))]


def catalog_health(items: Iterable[CatalogItem]) -> Dict[str, object]:
    summary = summarize_catalog(items)
    return {
        "active_ratio": round((summary.active_items / max(1, summary.total_items)) * 100.0, 2),
        "price_bands": price_bands(items),
        "top_items": catalog_rankings(items)[:3],
    }


def catalog_report(items: Iterable[CatalogItem]) -> Dict[str, object]:
    summary = summarize_catalog(items)
    return {
        "summary": summary.__dict__,
        "health": catalog_health(items),
        "category_mix": category_mix(items),
        "active_items": active_items(items),
    }
