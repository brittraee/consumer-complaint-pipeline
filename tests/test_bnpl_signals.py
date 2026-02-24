"""Tests for BNPL signal definitions and narrative mining with custom signals."""

from complaint_pipeline.cfpb.analyzer import narrative_keyword_counts
from complaint_pipeline.cfpb.bnpl_signals import (
    BNPL_ISSUE_SIGNALS,
    BNPL_MERCHANTS,
    BNPL_NARRATIVE_KEYWORDS,
    BNPL_RESPONSE_PATTERNS,
)
from complaint_pipeline.cfpb.narrative import (
    classify_fraud_type,
    response_patterns,
    retailer_mentions,
)
from complaint_pipeline.models import Complaint


def _complaint(narrative="", **kwargs):
    """Helper to create a Complaint with narrative text."""
    return Complaint(narrative=narrative, **kwargs)


# --- Signal definition tests ---


class TestBnplSignalDefinitions:
    def test_issue_signals_has_expected_keys(self):
        expected = {
            "loan_terms_confusion", "merchant_dispute",
            "collection_practices", "autopay_issues",
        }
        assert set(BNPL_ISSUE_SIGNALS.keys()) == expected

    def test_response_patterns_has_expected_keys(self):
        expected = {
            "investigation_concluded", "denied_dispute", "credit_report_threat",
            "delay_runaround", "partial_resolution",
        }
        assert set(BNPL_RESPONSE_PATTERNS.keys()) == expected

    def test_merchants_is_nonempty_list(self):
        assert isinstance(BNPL_MERCHANTS, list)
        assert len(BNPL_MERCHANTS) > 10

    def test_narrative_keywords_is_nonempty_list(self):
        assert isinstance(BNPL_NARRATIVE_KEYWORDS, list)
        assert len(BNPL_NARRATIVE_KEYWORDS) > 10

    def test_all_signal_values_are_lists_of_strings(self):
        for signals in [BNPL_ISSUE_SIGNALS, BNPL_RESPONSE_PATTERNS]:
            for key, value in signals.items():
                assert isinstance(value, list), f"{key} should be a list"
                for item in value:
                    assert isinstance(item, str), f"{key} items should be strings"


# --- classify_fraud_type with BNPL signals ---


class TestClassifyWithBnplSignals:
    def test_loan_terms_confusion(self):
        complaints = [_complaint("I didn't know there would be hidden fees and interest rate")]
        result = classify_fraud_type(complaints, signals=BNPL_ISSUE_SIGNALS)
        assert result["loan_terms_confusion"] == 1

    def test_merchant_dispute(self):
        complaints = [_complaint("I returned item but refund not processed by the merchant")]
        result = classify_fraud_type(complaints, signals=BNPL_ISSUE_SIGNALS)
        assert result["merchant_dispute"] == 1

    def test_collection_practices(self):
        complaints = [_complaint("they sent to collections and it hurt my credit score")]
        result = classify_fraud_type(complaints, signals=BNPL_ISSUE_SIGNALS)
        assert result["collection_practices"] == 1

    def test_autopay_issues(self):
        complaints = [_complaint("couldn't cancel the autopay and they kept charging me")]
        result = classify_fraud_type(complaints, signals=BNPL_ISSUE_SIGNALS)
        assert result["autopay_issues"] == 1

    def test_unclear_with_no_signals(self):
        complaints = [_complaint("I have a general problem")]
        result = classify_fraud_type(complaints, signals=BNPL_ISSUE_SIGNALS)
        assert result["unclear"] == 1

    def test_total_classified(self):
        complaints = [
            _complaint("hidden fees surprised me"),
            _complaint("never received my order"),
            _complaint("just a problem"),
        ]
        result = classify_fraud_type(complaints, signals=BNPL_ISSUE_SIGNALS)
        assert result["total_classified"] == 3

    def test_default_still_works(self):
        """Calling without signals should use default behavior."""
        complaints = [_complaint("brand new card, never used, zero balance")]
        result = classify_fraud_type(complaints)
        assert result["pre_shelf_drain"] == 1


# --- response_patterns with BNPL patterns ---


class TestResponsePatternsWithBnpl:
    def test_denied_dispute(self):
        complaints = [_complaint("my dispute was denied, they said valid charge")]
        result = response_patterns(complaints, pattern_keywords=BNPL_RESPONSE_PATTERNS)
        assert result["narrative_patterns"]["denied_dispute"] == 1

    def test_credit_report_threat(self):
        complaints = [_complaint("they said it would be past due and report to credit bureau")]
        result = response_patterns(complaints, pattern_keywords=BNPL_RESPONSE_PATTERNS)
        assert result["narrative_patterns"]["credit_report_threat"] == 1

    def test_partial_resolution(self):
        complaints = [_complaint("they offered a partial refund but not the full amount")]
        result = response_patterns(complaints, pattern_keywords=BNPL_RESPONSE_PATTERNS)
        assert result["narrative_patterns"]["partial_resolution"] == 1

    def test_company_response_field_still_counted(self):
        complaints = [Complaint(company_response="Closed with explanation")]
        result = response_patterns(complaints, pattern_keywords=BNPL_RESPONSE_PATTERNS)
        assert result["company_responses"]["Closed with explanation"] == 1

    def test_default_still_works(self):
        """Calling without pattern_keywords should use defaults."""
        complaints = [_complaint("my claim was denied")]
        result = response_patterns(complaints)
        assert result["narrative_patterns"]["denied_claim"] == 1


# --- retailer_mentions with BNPL merchants ---


class TestRetailerMentionsWithBnpl:
    def test_finds_bnpl_merchants(self):
        complaints = [
            _complaint("bought from amazon using affirm"),
            _complaint("purchased on wayfair"),
            _complaint("ordered from shein"),
        ]
        result = retailer_mentions(complaints, retailers=BNPL_MERCHANTS)
        assert result["amazon"] == 1
        assert result["wayfair"] == 1
        assert result["shein"] == 1

    def test_default_still_works(self):
        """Calling without retailers should use default retailer list."""
        complaints = [_complaint("bought at Walgreens")]
        result = retailer_mentions(complaints)
        assert result["walgreens"] == 1


# --- narrative_keyword_counts with BNPL keywords ---


class TestNarrativeKeywordsWithBnpl:
    def test_bnpl_keywords(self):
        complaints = [
            _complaint("denied my dispute, unauthorized charge, sent to collections"),
            _complaint("misleading interest rate, late fee applied"),
        ]
        result = narrative_keyword_counts(complaints, keywords=BNPL_NARRATIVE_KEYWORDS)
        assert result["denied"] == 1
        assert result["unauthorized"] == 1
        assert result["collections"] == 1
        assert result["misleading"] == 1
        assert result["late fee"] == 1

    def test_default_still_works(self):
        """Calling without keywords should use defaults."""
        complaints = [_complaint("the gift card was drained and stolen")]
        result = narrative_keyword_counts(complaints)
        assert result["drained"] == 1
        assert result["stolen"] == 1
