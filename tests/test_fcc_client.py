"""Tests for FCC client module.

Tests the data parsing/writing logic — NOT live API calls.
"""

import csv

from complaint_pipeline.fcc.client import load_complaints_csv, write_csv
from complaint_pipeline.models import FccComplaint


# -- Fixtures (local to this module) ------------------------------------------

SAMPLE_API_RECORDS = [
    {
        "id": "4957510",
        "issue_date": "2021-08-12T00:00:00.000",
        "issue_time": "1:17 p.m.",
        "issue_type": "Phone",
        "method": "Wired",
        "issue": "Unwanted Calls",
        "caller_id_number": "203-760-1637",
        "type_of_call_or_messge": "Prerecorded Voice",
        "advertiser_business_phone_number": "203-760-1637",
        "state": "CT",
        "zip": "06712",
    },
    {
        "id": "5396122",
        "issue_date": "2022-03-25T00:00:00.000",
        "issue_time": "6:53 pm",
        "issue_type": "Phone",
        "method": "Wireless (cell phone/other mobile device)",
        "issue": "Unwanted Calls",
        "caller_id_number": "None",
        "type_of_call_or_messge": "Live Voice",
        "advertiser_business_phone_number": "None",
        "state": "VA",
        "zip": "20194",
    },
]


class TestFccComplaintModel:
    def test_from_api_response(self):
        """API response dict should parse into FccComplaint correctly."""
        c = FccComplaint.from_api_response(SAMPLE_API_RECORDS[0])
        assert c.complaint_id == "4957510"
        assert c.issue_date == "2021-08-12"
        assert c.issue_time == "1:17 p.m."
        assert c.method == "Wired"
        assert c.caller_id_number == "203-760-1637"
        assert c.call_type == "Prerecorded Voice"
        assert c.state == "CT"
        assert c.zip_code == "06712"

    def test_from_api_response_missing_fields(self):
        """Missing fields should default to empty strings."""
        c = FccComplaint.from_api_response({"id": "1"})
        assert c.complaint_id == "1"
        assert c.state == ""
        assert c.caller_id_number == ""
        assert c.issue_date == ""

    def test_from_api_response_date_normalization(self):
        """ISO datetime should be trimmed to date-only string."""
        c = FccComplaint.from_api_response(SAMPLE_API_RECORDS[1])
        assert c.issue_date == "2022-03-25"

    def test_to_dict(self):
        """to_dict() should return a plain dict with all fields."""
        c = FccComplaint(complaint_id="99", state="TX", call_type="Live Voice")
        d = c.to_dict()
        assert d["complaint_id"] == "99"
        assert d["state"] == "TX"
        assert d["call_type"] == "Live Voice"
        assert isinstance(d, dict)

    def test_from_csv_row(self):
        """CSV row dict should map to FccComplaint fields."""
        row = {
            "complaint_id": "500",
            "state": "NY",
            "caller_id_number": "555-123-4567",
            "call_type": "Prerecorded Voice",
        }
        c = FccComplaint.from_csv_row(row)
        assert c.complaint_id == "500"
        assert c.state == "NY"
        assert c.caller_id_number == "555-123-4567"
        # Missing fields default to empty string
        assert c.method == ""


class TestWriteAndLoadCSV:
    def _make_complaints(self) -> list[FccComplaint]:
        return [FccComplaint.from_api_response(r) for r in SAMPLE_API_RECORDS]

    def test_roundtrip(self, tmp_path):
        """Write complaints to CSV, read them back, verify data survives."""
        complaints = self._make_complaints()
        csv_path = tmp_path / "fcc_complaints.csv"
        write_csv(complaints, csv_path)

        assert csv_path.exists()

        loaded = load_complaints_csv(csv_path)
        assert len(loaded) == len(complaints)
        assert loaded[0].complaint_id == complaints[0].complaint_id
        assert loaded[0].state == complaints[0].state
        assert loaded[0].caller_id_number == complaints[0].caller_id_number

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
        assert "caller_id_number" in headers
        assert "state" in headers
        assert "call_type" in headers
