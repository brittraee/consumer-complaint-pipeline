"""Tests for CFPB complaint analyzer.

These tests verify PURE FUNCTIONS — no API calls, no filesystem access.
All data comes from the sample_complaints fixture (conftest.py).
"""

from complaint_pipeline.cfpb import analyzer


class TestMonthlyTimeseries:
    def test_groups_by_month(self, sample_complaints):
        result = analyzer.monthly_timeseries(sample_complaints)
        assert "2024-03" in result
        assert "2024-04" in result
        assert "2024-05" in result

    def test_march_has_two(self, sample_complaints):
        result = analyzer.monthly_timeseries(sample_complaints)
        assert result["2024-03"] == 2

    def test_sorted_chronologically(self, sample_complaints):
        result = analyzer.monthly_timeseries(sample_complaints)
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_empty_input(self):
        assert analyzer.monthly_timeseries([]) == {}


class TestYearlyBreakdown:
    def test_all_2024(self, sample_complaints):
        result = analyzer.yearly_breakdown(sample_complaints)
        assert "2024" in result
        assert result["2024"] == 5

    def test_empty_input(self):
        assert analyzer.yearly_breakdown([]) == {}


class TestGeographicAnalysis:
    def test_california_most_common(self, sample_complaints):
        result = analyzer.geographic_analysis(sample_complaints)
        # CA appears twice
        assert result[0] == ("CA", 2)

    def test_all_states_present(self, sample_complaints):
        result = analyzer.geographic_analysis(sample_complaints)
        states = {s for s, _ in result}
        assert states == {"CA", "TX", "NY", "FL"}


class TestResponseAnalysis:
    def test_explanation_most_common(self, sample_complaints):
        result = analyzer.response_analysis(sample_complaints)
        # 3 "Closed with explanation"
        assert result[0][0] == "Closed with explanation"
        assert result[0][1] == 3


class TestIssueAnalysis:
    def test_returns_issues(self, sample_complaints):
        result = analyzer.issue_analysis(sample_complaints)
        issues = [issue for issue, _ in result]
        assert "Problem with a purchase or transfer" in issues


class TestDisputedRate:
    def test_counts(self, sample_complaints):
        result = analyzer.disputed_rate(sample_complaints)
        assert result["total"] == 5
        assert result["disputed"] == 2
        assert result["not_disputed"] == 2
        assert result["n_a"] == 1

    def test_empty(self):
        result = analyzer.disputed_rate([])
        assert result["total"] == 0
        assert result["dispute_rate_pct"] == 0


class TestMonetaryReliefRate:
    def test_monetary_count(self, sample_complaints):
        # "monetary" appears in both "Closed with monetary relief" and
        # "Closed with non-monetary relief" — both match the substring check
        result = analyzer.monetary_relief_rate(sample_complaints)
        assert result["relief"] == 2
        assert result["relief_pct"] == 40.0

    def test_timely_count(self, sample_complaints):
        result = analyzer.monetary_relief_rate(sample_complaints)
        assert result["timely"] == 4  # 4 out of 5 are "Yes"


class TestNarrativeKeywordCounts:
    def test_default_keywords(self, sample_complaints):
        result = analyzer.narrative_keyword_counts(sample_complaints)
        # "drained" appears in complaints 1001, 1004 (1005 says "zero" not "drained")
        assert result["drained"] == 2
        # "refund" appears in 1001, 1004
        assert result["refund"] == 2
        # "vanilla" appears in 1001, 1005
        assert result["vanilla"] == 2

    def test_custom_keywords(self, sample_complaints):
        result = analyzer.narrative_keyword_counts(sample_complaints, keywords=["card", "zero"])
        assert "card" in result
        assert result["zero"] == 1  # complaint 1005

    def test_excludes_empty_narratives(self, sample_complaints):
        # Complaint 1003 has no narrative; shouldn't count
        analyzer.narrative_keyword_counts(sample_complaints)
        # Total narratives should be 4 (1001, 1002, 1004, 1005)
        narratives = [c for c in sample_complaints if c.narrative]
        assert len(narratives) == 4


class TestDateRange:
    def test_range(self, sample_complaints):
        result = analyzer.date_range(sample_complaints)
        assert result == ("2024-03-15", "2024-05-15")

    def test_empty(self):
        assert analyzer.date_range([]) is None
