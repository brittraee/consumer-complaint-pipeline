"""Tests for network and entity co-occurrence analysis."""

import pytest

from complaint_pipeline.analysis.network import (
    Edge,
    EntityGraph,
    build_company_product_graph,
    build_company_issue_graph,
    build_phone_number_graph,
    cluster_by_entity,
    dollar_amounts_by_scam_type,
    entity_summary,
    extract_phone_numbers,
)
from complaint_pipeline.models import Complaint, FccComplaint, FtcComplaint


def _complaint(**overrides) -> Complaint:
    defaults = {
        "complaint_id": "1",
        "company": "Acme Corp",
        "product": "Prepaid card",
        "issue": "Fraud or scam",
        "narrative": "",
        "state": "CA",
    }
    defaults.update(overrides)
    return Complaint(**defaults)


class TestExtractPhoneNumbers:
    def test_standard_format(self):
        assert extract_phone_numbers("Call 555-123-4567") == ["5551234567"]

    def test_parens_format(self):
        assert extract_phone_numbers("Call (555) 123-4567") == ["5551234567"]

    def test_dots_format(self):
        assert extract_phone_numbers("Call 555.123.4567") == ["5551234567"]

    def test_multiple(self):
        text = "Call 555-111-2222 or 555-333-4444"
        result = extract_phone_numbers(text)
        assert len(result) == 2

    def test_no_match(self):
        assert extract_phone_numbers("no numbers here") == []

    def test_eleven_digits_with_country_code(self):
        assert extract_phone_numbers("Call 15551234567") == ["5551234567"]


class TestEntityGraph:
    def test_add_edge(self):
        g = EntityGraph()
        g.add_edge("A", "B", "c1")
        g.add_edge("A", "B", "c2")
        assert len(g.nodes) == 2
        assert len(g.edges) == 1
        edge = list(g.edges.values())[0]
        assert edge.weight == 2
        assert len(edge.complaints) == 2

    def test_edge_key_ordering(self):
        g = EntityGraph()
        g.add_edge("B", "A")
        g.add_edge("A", "B")
        assert len(g.edges) == 1
        assert list(g.edges.values())[0].weight == 2

    def test_top_edges(self):
        g = EntityGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "B")
        g.add_edge("C", "D")
        top = g.top_edges(1)
        assert len(top) == 1
        assert top[0].weight == 2

    def test_node_degree(self):
        g = EntityGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        degrees = g.node_degree()
        assert degrees["A"] == 2

    def test_connected_components(self):
        g = EntityGraph()
        g.add_edge("A", "B")
        g.add_edge("C", "D")
        components = g.connected_components()
        assert len(components) == 2

    def test_connected_components_single(self):
        g = EntityGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        components = g.connected_components()
        assert len(components) == 1
        assert components[0] == {"A", "B", "C"}


class TestBuildGraphs:
    def test_company_product_graph(self):
        complaints = [
            _complaint(company="Acme", product="Card"),
            _complaint(company="Acme", product="Card"),
            _complaint(company="Beta", product="Loan"),
        ]
        g = build_company_product_graph(complaints)
        assert len(g.nodes) > 0
        top = g.top_edges(1)
        assert top[0].weight == 2

    def test_company_issue_graph(self):
        complaints = [
            _complaint(company="Acme", issue="Fraud"),
            _complaint(company="Acme", issue="Fraud"),
        ]
        g = build_company_issue_graph(complaints)
        assert g.top_edges(1)[0].weight == 2

    def test_phone_number_graph_fcc(self):
        fcc = [
            FccComplaint(caller_id_number="5551111111", state="CA"),
            FccComplaint(caller_id_number="5552222222", state="CA"),
            FccComplaint(caller_id_number="5553333333", state="NY"),
        ]
        g = build_phone_number_graph(fcc_complaints=fcc)
        # Two CA numbers should be connected
        assert len(g.edges) >= 1

    def test_phone_number_graph_empty(self):
        g = build_phone_number_graph()
        assert len(g.nodes) == 0


class TestClusterByEntity:
    def test_cluster_by_company(self):
        complaints = [
            _complaint(company="Acme"),
            _complaint(company="Acme"),
            _complaint(company="Beta"),
        ]
        clusters = cluster_by_entity(complaints, "company")
        assert len(clusters["Acme"]) == 2
        assert len(clusters["Beta"]) == 1

    def test_cluster_by_state(self):
        complaints = [
            _complaint(state="CA"),
            _complaint(state="NY"),
            _complaint(state="CA"),
        ]
        clusters = cluster_by_entity(complaints, "state")
        assert len(clusters["CA"]) == 2

    def test_empty(self):
        assert cluster_by_entity([], "company") == {}


class TestEntitySummary:
    def test_basic(self):
        complaints = [
            _complaint(company="Acme", product="Card", issue="Fraud"),
            _complaint(company="Acme", product="Card", issue="Fraud"),
            _complaint(company="Beta", product="Loan", issue="Billing"),
        ]
        result = entity_summary(complaints)
        assert result["top_companies"][0] == ("Acme", 2)
        assert len(result["company_product_pairs"]) > 0

    def test_empty(self):
        result = entity_summary([])
        assert result["top_companies"] == []


class TestDollarAmountsByScamType:
    def test_basic(self):
        signals = {"gift_card": ["gift card", "card code"]}
        complaints = [
            _complaint(narrative="I bought a gift card for {$500.00} and they read the card code"),
            _complaint(narrative="no scam here"),
        ]
        result = dollar_amounts_by_scam_type(complaints, signals)
        assert "gift_card" in result
        assert result["gift_card"]["total"] == 500.0

    def test_empty(self):
        result = dollar_amounts_by_scam_type([], {"a": ["x"]})
        assert result == {}

    def test_multiple_amounts(self):
        signals = {"gift_card": ["gift card", "card code"]}
        complaints = [
            _complaint(narrative="gift card {$200.00} and another card code {$300.00}"),
        ]
        result = dollar_amounts_by_scam_type(complaints, signals)
        assert result["gift_card"]["total"] == 500.0
        assert result["gift_card"]["count"] == 2
        assert result["gift_card"]["avg"] == 250.0
