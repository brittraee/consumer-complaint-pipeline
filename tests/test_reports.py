"""Tests for report generation."""

from complaint_pipeline.reports.markdown import (
    company_summary,
    comparison_report,
    insider_trading_report,
)


class TestCompanySummary:
    def test_contains_header(self, sample_complaints):
        result = company_summary(sample_complaints, "InComm")
        assert "# CFPB Complaint Summary: InComm" in result

    def test_contains_total(self, sample_complaints):
        result = company_summary(sample_complaints, "InComm")
        assert "**Total complaints**: 5" in result

    def test_contains_date_range(self, sample_complaints):
        result = company_summary(sample_complaints, "InComm")
        assert "2024-03-15" in result
        assert "2024-05-15" in result

    def test_empty_complaints(self):
        result = company_summary([], "Nobody")
        assert "No complaints found" in result


class TestComparisonReport:
    def test_header(self, sample_complaints):
        result = comparison_report(sample_complaints, sample_complaints[:2])
        assert "InComm vs Blackhawk" in result

    def test_volume_ratio(self, sample_complaints):
        result = comparison_report(sample_complaints, sample_complaints[:2])
        assert "Volume ratio" in result

    def test_methodology(self, sample_complaints):
        result = comparison_report(sample_complaints, sample_complaints[:2])
        assert "Methodology" in result


class TestInsiderTradingReport:
    def test_header(self, sample_filings):
        insider = [f for f in sample_filings if f.form_type == "4"]
        result = insider_trading_report(insider)
        assert "Form 4 Insider Transaction" in result

    def test_filing_count(self, sample_filings):
        insider = [f for f in sample_filings if f.form_type == "4"]
        result = insider_trading_report(insider)
        assert f"**Total Form 4 filings found**: {len(insider)}" in result
