"""Tests for scam-type signal definitions and multi-label classifier."""

from complaint_pipeline.cfpb.scam_signals import (
    SCAM_TYPE_SIGNALS,
    SCAM_RESPONSE_PATTERNS,
    SCAM_NARRATIVE_KEYWORDS,
)
from complaint_pipeline.cfpb.narrative import classify_scam_types
from complaint_pipeline.models import Complaint
from complaint_pipeline.reports.markdown import generate_scam_report


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


class TestClassifyScamTypes:
    def test_single_category_match(self):
        complaints = [_complaint(
            "they called about my computer has virus and used remote access to get into teamviewer"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["tech_support"] >= 1

    def test_multi_label_match(self):
        """A complaint about a fake charge leading to remote access should hit both categories."""
        complaints = [_complaint(
            "got a text saying unauthorized purchase charge of $499 call this number. "
            "They had me download anydesk for remote access to fix the problem."
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["fake_charge_alert"] >= 1
        assert result["tech_support"] >= 1
        assert result["multi_label_count"] >= 1

    def test_unclassified_below_threshold(self):
        complaints = [_complaint("I have a general problem with my account")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["unclassified"] == 1

    def test_threshold_of_one(self):
        """With threshold=1, a single keyword match should classify."""
        complaints = [_complaint("something about bitcoin")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS, threshold=1)
        assert result["pig_butchering"] == 1

    def test_threshold_default_requires_two(self):
        """Default threshold=2 means single keyword match is not enough."""
        complaints = [_complaint("something about bitcoin")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["pig_butchering"] == 0
        assert result["unclassified"] == 1

    def test_co_occurrences_tracked(self):
        complaints = [_complaint(
            "they impersonated the irs and claimed warrant for arrest, "
            "told me to buy gift card itunes and read the code scratched off"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        co = result["co_occurrences"]
        # Check either key ordering
        assert co.get(("gift_card", "impersonation"), 0) == 1 or \
               co.get(("impersonation", "gift_card"), 0) == 1

    def test_empty_input(self):
        result = classify_scam_types([], signals=SCAM_TYPE_SIGNALS)
        assert result["total"] == 0
        assert result["unclassified"] == 0

    def test_percentages_included(self):
        complaints = [
            _complaint("remote access virus teamviewer computer infected tech support"),
            _complaint("just a normal complaint"),
        ]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "tech_support_pct" in result
        assert result["total"] == 2

    def test_skips_empty_narratives(self):
        complaints = [_complaint(""), _complaint("remote access virus teamviewer tech support")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["total"] == 1


class TestClassifyScamTypesPerCategory:
    """One test per scam category to verify classification works."""

    def test_pig_butchering(self):
        complaints = [_complaint(
            "met someone on whatsapp who showed me a trading platform for crypto bitcoin investment"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["pig_butchering"] >= 1

    def test_romance_scam(self):
        complaints = [_complaint(
            "met online on dating site, fell in love, asked for money for emergency overseas"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["romance_scam"] >= 1

    def test_tech_support(self):
        complaints = [_complaint(
            "pop-up said computer infected with virus, called tech support, they used remote access"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["tech_support"] >= 1

    def test_impersonation(self):
        complaints = [_complaint(
            "called claiming to be irs, said warrant for arrest, threatened legal action"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["impersonation"] >= 1

    def test_bank_impersonation(self):
        complaints = [_complaint(
            "fraud department called about suspicious activity, said verify your account via zelle"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["bank_impersonation"] >= 1

    def test_gift_card(self):
        complaints = [_complaint(
            "told to buy apple gift card itunes, scratched off and read the code over the phone"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["gift_card"] >= 1

    def test_phishing(self):
        complaints = [_complaint(
            "got suspicious email that looked like my bank, clicked link to fake website, entered my information and password"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["phishing"] >= 1

    def test_cloud_storage_scam(self):
        complaints = [_complaint(
            "got text saying icloud storage full and photos will be deleted, asked to upgrade storage and verify apple id"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["cloud_storage_scam"] >= 1

    def test_fake_charge_alert(self):
        complaints = [_complaint(
            "text saying apple pay charge of $499 wasn't you call this number to dispute suspicious charge"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["fake_charge_alert"] >= 1

    def test_identity_theft(self):
        complaints = [_complaint(
            "someone opened a new account in my name using my social security number without my knowledge"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["identity_theft"] >= 1


class TestGenerateScamReport:
    def test_report_contains_header(self):
        complaints = [
            _complaint("remote access virus teamviewer computer infected tech support pop-up"),
            _complaint("icloud storage full photos will be deleted upgrade storage verify apple id"),
            _complaint("general complaint about something"),
        ]
        report = generate_scam_report(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "# Scam-Type Classification Report" in report
        assert "Total Complaints Analyzed" in report

    def test_report_contains_category_table(self):
        complaints = [
            _complaint("remote access virus teamviewer computer infected tech support pop-up"),
        ]
        report = generate_scam_report(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "| Category |" in report
        assert "tech_support" in report

    def test_report_contains_co_occurrences(self):
        complaints = [_complaint(
            "irs warrant arrest impersonation legal action "
            "told to buy gift card itunes read the code scratched off"
        )]
        report = generate_scam_report(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "Co-Occurrence" in report

    def test_report_empty_input(self):
        report = generate_scam_report([], signals=SCAM_TYPE_SIGNALS)
        assert "No complaints" in report
