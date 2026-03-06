"""Tests for scam-type signal definitions and multi-label classifier."""

from complaint_pipeline.cfpb.scam_signals import (
    SCAM_TYPE_SIGNALS,
    SCAM_RESPONSE_PATTERNS,
    SCAM_NARRATIVE_KEYWORDS,
)
from complaint_pipeline.models import Complaint


def _complaint(narrative="", **kwargs):
    """Helper to create a Complaint with narrative text."""
    return Complaint(narrative=narrative, **kwargs)


class TestScamSignalDefinitions:
    def test_type_signals_has_expected_keys(self):
        expected = {
            "pig_butchering", "romance_scam", "tech_support",
            "impersonation", "bank_impersonation", "gift_card",
            "phishing", "cloud_storage_scam", "fake_charge_alert",
            "identity_theft",
        }
        assert set(SCAM_TYPE_SIGNALS.keys()) == expected

    def test_response_patterns_has_expected_keys(self):
        expected = {
            "investigation_concluded", "denied_claim",
            "delay_runaround", "referred_to_law_enforcement",
            "account_closed", "refund_issued",
        }
        assert set(SCAM_RESPONSE_PATTERNS.keys()) == expected

    def test_narrative_keywords_is_nonempty_list(self):
        assert isinstance(SCAM_NARRATIVE_KEYWORDS, list)
        assert len(SCAM_NARRATIVE_KEYWORDS) > 10

    def test_all_signal_values_are_lists_of_strings(self):
        for signals in [SCAM_TYPE_SIGNALS, SCAM_RESPONSE_PATTERNS]:
            for key, value in signals.items():
                assert isinstance(value, list), f"{key} should be a list"
                for item in value:
                    assert isinstance(item, str), f"{key} items should be strings"

    def test_each_category_has_at_least_5_keywords(self):
        for cat, keywords in SCAM_TYPE_SIGNALS.items():
            assert len(keywords) >= 5, f"{cat} needs at least 5 keywords, has {len(keywords)}"
