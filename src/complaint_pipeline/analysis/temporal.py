"""Temporal trend analysis for consumer complaint data.

Provides monthly aggregation, trend detection, and seasonal pattern
analysis using only stdlib -- no external dependencies required.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from complaint_pipeline.models import Complaint


def _parse_month(date_str: str) -> str:
    """Extract YYYY-MM from a date string. Returns '' if unparseable."""
    if not date_str or len(date_str) < 7:
        return ""
    return date_str[:7]


def monthly_counts(complaints: list[Complaint]) -> dict[str, int]:
    """Count complaints per month (YYYY-MM).

    Returns dict sorted chronologically: {"2024-01": 15, "2024-02": 23, ...}
    """
    counts: Counter[str] = Counter()
    for c in complaints:
        month = _parse_month(c.date_received)
        if month:
            counts[month] += 1
    return dict(sorted(counts.items()))


def monthly_counts_by_category(
    complaints: list[Complaint],
    signals: dict[str, list[str]],
    threshold: int = 2,
) -> dict[str, dict[str, int]]:
    """Count complaints per month per scam category.

    Returns: {category: {month: count, ...}, ...}
    Each complaint can appear in multiple categories (multi-label).
    """
    category_months: dict[str, Counter[str]] = defaultdict(Counter)

    for c in complaints:
        if not c.narrative:
            continue
        month = _parse_month(c.date_received)
        if not month:
            continue

        text = c.narrative.lower()
        for cat, keywords in signals.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits >= threshold:
                category_months[cat][month] += 1

    return {
        cat: dict(sorted(months.items()))
        for cat, months in sorted(category_months.items())
    }


def moving_average(values: list[int | float], window: int = 3) -> list[float]:
    """Simple moving average over a list of values.

    Returns list of same length with None-equivalent 0.0 for
    the first (window-1) positions.
    """
    if window < 1 or not values:
        return []
    result = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(0.0)
        else:
            avg = sum(values[i - window + 1 : i + 1]) / window
            result.append(round(avg, 2))
    return result


@dataclass
class ChangePoint:
    """A detected change point in complaint volume."""

    month: str
    before_avg: float
    after_avg: float
    pct_change: float


def detect_change_points(
    monthly: dict[str, int],
    min_pct_change: float = 50.0,
    window: int = 3,
) -> list[ChangePoint]:
    """Detect months where complaint volume changed significantly.

    Compares rolling average before vs after each point.
    A change point is flagged when the percentage change exceeds min_pct_change.

    Args:
        monthly: {month: count} sorted chronologically.
        min_pct_change: Minimum % change to flag (default 50%).
        window: Number of months for rolling average (default 3).

    Returns list of ChangePoint objects sorted by absolute pct_change descending.
    """
    months = list(monthly.keys())
    values = list(monthly.values())

    if len(values) < window * 2:
        return []

    change_points = []
    for i in range(window, len(values) - window + 1):
        before = values[i - window : i]
        after = values[i : i + window]
        before_avg = sum(before) / len(before)
        after_avg = sum(after) / len(after)

        if before_avg == 0:
            continue

        pct = round(100 * (after_avg - before_avg) / before_avg, 1)
        if abs(pct) >= min_pct_change:
            change_points.append(
                ChangePoint(
                    month=months[i],
                    before_avg=round(before_avg, 1),
                    after_avg=round(after_avg, 1),
                    pct_change=pct,
                )
            )

    return sorted(change_points, key=lambda cp: abs(cp.pct_change), reverse=True)


def seasonal_pattern(monthly: dict[str, int]) -> dict[int, float]:
    """Calculate average complaint volume by calendar month (1-12).

    Returns: {1: avg_jan, 2: avg_feb, ...}
    Useful for identifying seasonal spikes (e.g., holiday gift card fraud).
    """
    month_totals: dict[int, list[int]] = defaultdict(list)

    for ym, count in monthly.items():
        try:
            cal_month = int(ym.split("-")[1])
            month_totals[cal_month].append(count)
        except (IndexError, ValueError):
            continue

    return {
        m: round(sum(vals) / len(vals), 1)
        for m, vals in sorted(month_totals.items())
    }


def trend_summary(complaints: list[Complaint]) -> dict:
    """Generate a complete temporal summary for a complaint set.

    Returns:
        {
            "monthly_counts": {month: count},
            "total_months": int,
            "peak_month": (month, count),
            "trough_month": (month, count),
            "change_points": [ChangePoint, ...],
            "seasonal": {cal_month: avg},
            "trend_direction": "increasing" | "decreasing" | "stable",
        }
    """
    monthly = monthly_counts(complaints)

    if not monthly:
        return {
            "monthly_counts": {},
            "total_months": 0,
            "peak_month": ("", 0),
            "trough_month": ("", 0),
            "change_points": [],
            "seasonal": {},
            "trend_direction": "stable",
        }

    values = list(monthly.values())
    months_list = list(monthly.keys())
    peak_idx = values.index(max(values))
    trough_idx = values.index(min(values))

    # Trend direction: compare first-half avg to second-half avg
    mid = len(values) // 2
    if mid > 0:
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / len(values[mid:])
        if second_half > first_half * 1.1:
            direction = "increasing"
        elif second_half < first_half * 0.9:
            direction = "decreasing"
        else:
            direction = "stable"
    else:
        direction = "stable"

    return {
        "monthly_counts": monthly,
        "total_months": len(monthly),
        "peak_month": (months_list[peak_idx], values[peak_idx]),
        "trough_month": (months_list[trough_idx], values[trough_idx]),
        "change_points": detect_change_points(monthly),
        "seasonal": seasonal_pattern(monthly),
        "trend_direction": direction,
    }
