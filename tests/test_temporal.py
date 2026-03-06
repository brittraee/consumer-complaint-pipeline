"""Tests for temporal trend analysis."""

import pytest

from complaint_pipeline.analysis.temporal import (
    ChangePoint,
    detect_change_points,
    monthly_counts,
    monthly_counts_by_category,
    moving_average,
    seasonal_pattern,
    trend_summary,
    _parse_month,
)
from complaint_pipeline.models import Complaint


def _complaint(**overrides) -> Complaint:
    defaults = {
        "complaint_id": "1",
        "date_received": "2024-06-15",
        "narrative": "",
    }
    defaults.update(overrides)
    return Complaint(**defaults)


class TestParseMonth:
    def test_full_date(self):
        assert _parse_month("2024-06-15") == "2024-06"

    def test_datetime(self):
        assert _parse_month("2024-06-15T12:30:00") == "2024-06"

    def test_empty(self):
        assert _parse_month("") == ""

    def test_too_short(self):
        assert _parse_month("2024") == ""


class TestMonthlyCounts:
    def test_basic(self):
        complaints = [
            _complaint(date_received="2024-01-15"),
            _complaint(date_received="2024-01-20"),
            _complaint(date_received="2024-02-10"),
        ]
        result = monthly_counts(complaints)
        assert result == {"2024-01": 2, "2024-02": 1}

    def test_sorted_chronologically(self):
        complaints = [
            _complaint(date_received="2024-03-01"),
            _complaint(date_received="2024-01-01"),
            _complaint(date_received="2024-02-01"),
        ]
        result = monthly_counts(complaints)
        assert list(result.keys()) == ["2024-01", "2024-02", "2024-03"]

    def test_empty(self):
        assert monthly_counts([]) == {}

    def test_skips_bad_dates(self):
        complaints = [
            _complaint(date_received="2024-01-15"),
            _complaint(date_received=""),
            _complaint(date_received="bad"),
        ]
        result = monthly_counts(complaints)
        assert result == {"2024-01": 1}


class TestMonthlyCountsByCategory:
    def test_basic(self):
        signals = {"fraud": ["stolen", "unauthorized"]}
        complaints = [
            _complaint(
                date_received="2024-01-15",
                narrative="my card was stolen and unauthorized charges appeared",
            ),
            _complaint(
                date_received="2024-01-20",
                narrative="stolen funds and unauthorized access",
            ),
            _complaint(
                date_received="2024-02-10",
                narrative="nothing relevant here",
            ),
        ]
        result = monthly_counts_by_category(complaints, signals)
        assert result["fraud"]["2024-01"] == 2
        assert "2024-02" not in result.get("fraud", {})

    def test_empty(self):
        assert monthly_counts_by_category([], {"a": ["x"]}) == {}


class TestMovingAverage:
    def test_basic(self):
        result = moving_average([10, 20, 30, 40, 50], window=3)
        assert result == [0.0, 0.0, 20.0, 30.0, 40.0]

    def test_window_1(self):
        result = moving_average([5, 10, 15], window=1)
        assert result == [5.0, 10.0, 15.0]

    def test_empty(self):
        assert moving_average([], window=3) == []


class TestDetectChangePoints:
    def test_detects_spike(self):
        monthly = {
            "2024-01": 10,
            "2024-02": 10,
            "2024-03": 10,
            "2024-04": 50,
            "2024-05": 50,
            "2024-06": 50,
        }
        result = detect_change_points(monthly, min_pct_change=50.0, window=3)
        assert len(result) >= 1
        assert result[0].pct_change > 0

    def test_no_change(self):
        monthly = {f"2024-{m:02d}": 10 for m in range(1, 7)}
        result = detect_change_points(monthly, min_pct_change=50.0, window=3)
        assert result == []

    def test_too_few_months(self):
        monthly = {"2024-01": 10, "2024-02": 20}
        result = detect_change_points(monthly)
        assert result == []


class TestSeasonalPattern:
    def test_basic(self):
        monthly = {"2023-12": 30, "2024-12": 40, "2024-06": 10}
        result = seasonal_pattern(monthly)
        assert result[12] == 35.0
        assert result[6] == 10.0

    def test_empty(self):
        assert seasonal_pattern({}) == {}


class TestTrendSummary:
    def test_increasing_trend(self):
        complaints = []
        for m in range(1, 7):
            for _ in range(m * 10):
                complaints.append(_complaint(date_received=f"2024-{m:02d}-15"))
        result = trend_summary(complaints)
        assert result["trend_direction"] == "increasing"
        assert result["total_months"] == 6

    def test_empty(self):
        result = trend_summary([])
        assert result["total_months"] == 0
        assert result["trend_direction"] == "stable"

    def test_has_peak_and_trough(self):
        complaints = [
            _complaint(date_received="2024-01-15"),
            _complaint(date_received="2024-02-15"),
            _complaint(date_received="2024-02-16"),
            _complaint(date_received="2024-02-17"),
        ]
        result = trend_summary(complaints)
        assert result["peak_month"][0] == "2024-02"
        assert result["trough_month"][0] == "2024-01"
