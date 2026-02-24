"""Tests for complaint narrative mining functions."""


from complaint_pipeline.cfpb.narrative import (
    classify_fraud_type,
    denomination_targeting,
    extract_dollar_amounts,
    full_narrative_analysis,
    geographic_clustering,
    purchase_to_drain_patterns,
    response_patterns,
    retailer_mentions,
)
from complaint_pipeline.models import Complaint


def _complaint(narrative="", state="", zip_code="", date_received="", **kwargs):
    """Helper to create a Complaint with narrative text."""
    return Complaint(
        narrative=narrative,
        state=state,
        zip_code=zip_code,
        date_received=date_received,
        **kwargs,
    )


class TestExtractDollarAmounts:
    def test_cfpb_format(self):
        assert extract_dollar_amounts("lost {$500.00}") == [500.0]

    def test_standard_format(self):
        assert extract_dollar_amounts("paid $200") == [200.0]

    def test_multiple_amounts(self):
        result = extract_dollar_amounts("bought {$100.00} and {$200.00}")
        assert result == [100.0, 200.0]

    def test_no_amounts(self):
        assert extract_dollar_amounts("no money mentioned") == []

    def test_comma_format(self):
        assert extract_dollar_amounts("{$1,000.00}") == [1000.0]


class TestDenominationTargeting:
    def test_counts_denominations(self):
        complaints = [
            _complaint("bought a {$500.00} card"),
            _complaint("lost {$100.00} on gift card"),
            _complaint("my {$500.00} vanilla card"),
        ]
        result = denomination_targeting(complaints)
        assert result["denomination_counts"][500.0] == 2
        assert result["denomination_counts"][100.0] == 1

    def test_skips_empty_narratives(self):
        complaints = [_complaint(""), _complaint("{$100.00}")]
        result = denomination_targeting(complaints)
        assert result["total_narratives"] == 1

    def test_empty_input(self):
        result = denomination_targeting([])
        assert result["total_narratives"] == 0


class TestPurchaseToDrainPatterns:
    def test_immediate(self):
        complaints = [_complaint("I just purchased it and it was empty")]
        result = purchase_to_drain_patterns(complaints)
        assert result["timing_distribution"]["immediate"] == 1

    def test_days(self):
        complaints = [_complaint("a few days later the balance was zero")]
        result = purchase_to_drain_patterns(complaints)
        assert result["timing_distribution"]["days"] == 1

    def test_pre_activation(self):
        complaints = [_complaint("the card was never activated but drained")]
        result = purchase_to_drain_patterns(complaints)
        assert result["pre_activation_drains"] == 1

    def test_unknown_timing(self):
        complaints = [_complaint("my card had problems")]
        result = purchase_to_drain_patterns(complaints)
        assert result["timing_distribution"]["unknown"] == 1

    def test_empty(self):
        result = purchase_to_drain_patterns([])
        assert result["total_with_narrative"] == 0


class TestRetailerMentions:
    def test_finds_retailers(self):
        complaints = [
            _complaint("bought at Walgreens"),
            _complaint("purchased from CVS pharmacy"),
            _complaint("got it at Walmart"),
            _complaint("bought at Walgreens again"),
        ]
        result = retailer_mentions(complaints)
        assert result["walgreens"] == 2
        assert result["cvs"] == 1
        assert result["walmart"] == 1

    def test_case_insensitive(self):
        complaints = [_complaint("bought at WALGREENS")]
        result = retailer_mentions(complaints)
        assert result["walgreens"] == 1

    def test_no_retailers(self):
        complaints = [_complaint("bought at a store")]
        result = retailer_mentions(complaints)
        assert "walgreens" not in result


class TestClassifyFraudType:
    def test_pre_shelf(self):
        complaints = [_complaint("brand new card, never used, zero balance")]
        result = classify_fraud_type(complaints)
        assert result["pre_shelf_drain"] == 1

    def test_post_activation(self):
        complaints = [_complaint("was working fine, then unauthorized transaction appeared")]
        result = classify_fraud_type(complaints)
        assert result["post_activation_drain"] == 1

    def test_unclear(self):
        complaints = [_complaint("I have a problem with my card")]
        result = classify_fraud_type(complaints)
        assert result["unclear"] == 1

    def test_empty(self):
        result = classify_fraud_type([])
        assert result["total_classified"] == 0


class TestGeographicClustering:
    def test_state_distribution(self):
        complaints = [
            _complaint(state="CA", zip_code="900XX", date_received="2024-01-15"),
            _complaint(state="CA", zip_code="900XX", date_received="2024-02-10"),
            _complaint(state="NY", zip_code="100XX", date_received="2024-01-20"),
        ]
        result = geographic_clustering(complaints)
        assert result["state_distribution"]["CA"] == 2
        assert result["state_distribution"]["NY"] == 1

    def test_finds_clusters(self):
        complaints = [
            _complaint(state="GA", zip_code="303XX", date_received="2024-01-15"),
            _complaint(state="GA", zip_code="303XX", date_received="2024-02-10"),
            _complaint(state="GA", zip_code="303XX", date_received="2024-03-05"),
        ]
        result = geographic_clustering(complaints)
        assert result["total_clusters"] >= 1
        cluster = result["clusters"][0]
        assert cluster["state"] == "GA"
        assert cluster["count"] >= 2

    def test_empty(self):
        result = geographic_clustering([])
        assert result["total_clusters"] == 0


class TestResponsePatterns:
    def test_delay_pattern(self):
        complaints = [_complaint("called multiple times, still waiting, no response")]
        result = response_patterns(complaints)
        assert result["narrative_patterns"]["delay_runaround"] == 1

    def test_denied_claim(self):
        complaints = [_complaint("my claim was denied")]
        result = response_patterns(complaints)
        assert result["narrative_patterns"]["denied_claim"] == 1

    def test_geographic_impossibility(self):
        complaints = [_complaint("card was used in a different state, I have never been there")]
        result = response_patterns(complaints)
        assert result["narrative_patterns"]["geographic_impossibility"] == 1

    def test_company_response_field(self):
        complaints = [
            Complaint(company_response="Closed with explanation"),
            Complaint(company_response="Closed with explanation"),
            Complaint(company_response="Closed with monetary relief"),
        ]
        result = response_patterns(complaints)
        assert result["company_responses"]["Closed with explanation"] == 2


class TestFullNarrativeAnalysis:
    def test_returns_all_sections(self):
        text = "bought a {$500.00} card at Walgreens, just purchased, zero balance"
        complaints = [_complaint(text, state="CA", zip_code="900XX",
                                 date_received="2024-01-15")]
        result = full_narrative_analysis(complaints)
        assert "denomination_targeting" in result
        assert "purchase_to_drain" in result
        assert "retailer_mentions" in result
        assert "fraud_classification" in result
        assert "geographic_clustering" in result
        assert "response_patterns" in result
        assert "summary" in result
        assert result["summary"]["total_complaints"] == 1
