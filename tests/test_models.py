"""Tests for data models."""

from complaint_pipeline.models import Complaint, Filing


def test_complaint_from_api_nested(sample_api_response):
    """API response with _source wrapper should parse correctly."""
    item = sample_api_response["hits"]["hits"][0]
    c = Complaint.from_api_response(item)
    assert c.complaint_id == "1001"
    assert c.company == "InComm Financial Services"
    assert c.state == "CA"
    assert "drained" in c.narrative.lower()


def test_complaint_from_api_flat():
    """Flat API response (no _source) should also work."""
    flat = {"complaint_id": "999", "company": "TestCo", "state": "TX"}
    c = Complaint.from_api_response(flat)
    assert c.complaint_id == "999"
    assert c.company == "TestCo"


def test_complaint_from_csv_row():
    """CSV row dict should map to Complaint fields."""
    row = {
        "complaint_id": "500",
        "company": "InComm",
        "state": "NY",
        "narrative": "my card was drained",
    }
    c = Complaint.from_csv_row(row)
    assert c.complaint_id == "500"
    assert c.state == "NY"
    assert c.narrative == "my card was drained"
    # Missing fields should default to empty string
    assert c.product == ""


def test_complaint_to_dict():
    """to_dict() should roundtrip correctly."""
    c = Complaint(complaint_id="1", company="Test", state="CA")
    d = c.to_dict()
    assert d["complaint_id"] == "1"
    assert d["company"] == "Test"
    assert isinstance(d, dict)


def test_filing_to_dict():
    """Filing to_dict should include all fields."""
    f = Filing(form_type="4", filing_date="2025-01-01")
    d = f.to_dict()
    assert d["form_type"] == "4"
    assert d["filing_date"] == "2025-01-01"
