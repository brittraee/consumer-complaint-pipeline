"""Tests for FTC client module.

Tests the data parsing/writing logic — NOT live API calls.
"""

import csv

from complaint_pipeline.ftc.client import load_complaints_csv, write_csv
from complaint_pipeline.models import FtcComplaint


# -- Fixtures (local to this module) ------------------------------------------

SAMPLE_API_RECORDS = [
    {
        "type": "dnc_complaint",
        "id": "2dae54c3d3c06d1960689139d39c3138",
        "attributes": {
            "company-phone-number": "6785050054",
            "created-date": "2020-02-27 04:23:11",
            "violation-date": "2020-02-26 16:00:00",
            "consumer-city": "Earlysville",
            "consumer-state": "Virginia",
            "consumer-area-code": "434",
            "subject": "Computer & technical support",
            "recorded-message-or-robocall": "N",
        },
        "relationships": [],
        "meta": [],
        "links": {
            "self": "https://api.ftc.gov/v0/dnc-complaints/2dae54c3d3c06d1960689139d39c3138"
        },
    },
    {
        "type": "dnc_complaint",
        "id": "2dae54c3d3c06d1960689139d39c2fb3",
        "attributes": {
            "company-phone-number": "5162681355",
            "created-date": "2020-02-27 04:13:57",
            "violation-date": "2020-02-25 00:00:00",
            "consumer-city": "Marion",
            "consumer-state": "Illinois",
            "consumer-area-code": "618",
            "subject": "Lotteries, prizes & sweepstakes",
            "recorded-message-or-robocall": "Y",
        },
        "relationships": [],
        "meta": [],
        "links": {
            "self": "https://api.ftc.gov/v0/dnc-complaints/2dae54c3d3c06d1960689139d39c2fb3"
        },
    },
]


class TestFtcComplaintModel:
    def test_from_api_response(self):
        """API response dict should parse into FtcComplaint correctly."""
        c = FtcComplaint.from_api_response(SAMPLE_API_RECORDS[0])
        assert c.complaint_id == "2dae54c3d3c06d1960689139d39c3138"
        assert c.created_date == "2020-02-27 04:23:11"
        assert c.violation_date == "2020-02-26 16:00:00"
        assert c.company_phone_number == "6785050054"
        assert c.consumer_city == "Earlysville"
        assert c.consumer_state == "Virginia"
        assert c.consumer_area_code == "434"
        assert c.subject == "Computer & technical support"
        assert c.is_robocall == "N"

    def test_from_api_response_missing_fields(self):
        """Missing fields should default to empty strings."""
        c = FtcComplaint.from_api_response({"id": "abc123"})
        assert c.complaint_id == "abc123"
        assert c.consumer_state == ""
        assert c.company_phone_number == ""
        assert c.subject == ""
        assert c.is_robocall == ""

    def test_from_api_response_robocall_flag(self):
        """Robocall flag should carry through from API."""
        c = FtcComplaint.from_api_response(SAMPLE_API_RECORDS[1])
        assert c.is_robocall == "Y"

    def test_to_dict(self):
        """to_dict() should return a plain dict with all fields."""
        c = FtcComplaint(
            complaint_id="abc",
            consumer_state="Virginia",
            subject="Debt reduction",
        )
        d = c.to_dict()
        assert d["complaint_id"] == "abc"
        assert d["consumer_state"] == "Virginia"
        assert d["subject"] == "Debt reduction"
        assert isinstance(d, dict)

    def test_from_csv_row(self):
        """CSV row dict should map to FtcComplaint fields."""
        row = {
            "complaint_id": "xyz789",
            "consumer_state": "Texas",
            "company_phone_number": "5551234567",
            "subject": "Medical & prescriptions",
            "is_robocall": "Y",
        }
        c = FtcComplaint.from_csv_row(row)
        assert c.complaint_id == "xyz789"
        assert c.consumer_state == "Texas"
        assert c.company_phone_number == "5551234567"
        assert c.is_robocall == "Y"
        # Missing fields default to empty string
        assert c.consumer_city == ""


class TestWriteAndLoadCSV:
    def _make_complaints(self) -> list[FtcComplaint]:
        return [FtcComplaint.from_api_response(r) for r in SAMPLE_API_RECORDS]

    def test_roundtrip(self, tmp_path):
        """Write complaints to CSV, read them back, verify data survives."""
        complaints = self._make_complaints()
        csv_path = tmp_path / "ftc_complaints.csv"
        write_csv(complaints, csv_path)

        assert csv_path.exists()

        loaded = load_complaints_csv(csv_path)
        assert len(loaded) == len(complaints)
        assert loaded[0].complaint_id == complaints[0].complaint_id
        assert loaded[0].consumer_state == complaints[0].consumer_state
        assert loaded[0].company_phone_number == complaints[0].company_phone_number
        assert loaded[0].subject == complaints[0].subject
        assert loaded[0].is_robocall == complaints[0].is_robocall

    def test_write_empty_list(self, tmp_path):
        """Writing empty list should not create a file."""
        csv_path = tmp_path / "empty.csv"
        write_csv([], csv_path)
        assert not csv_path.exists()

    def test_load_missing_file(self, tmp_path):
        """Loading from nonexistent file should return empty list."""
        result = load_complaints_csv(tmp_path / "nonexistent.csv")
        assert result == []

    def test_csv_has_headers(self, tmp_path):
        """CSV should have proper column headers."""
        complaints = self._make_complaints()
        csv_path = tmp_path / "headers.csv"
        write_csv(complaints, csv_path)

        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert "complaint_id" in headers
        assert "company_phone_number" in headers
        assert "consumer_state" in headers
        assert "subject" in headers
        assert "is_robocall" in headers
