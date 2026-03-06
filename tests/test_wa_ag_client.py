"""Tests for WA State AG consumer complaint client."""

from unittest.mock import MagicMock, patch

import pytest

from complaint_pipeline.models import WaAgComplaint
from complaint_pipeline.wa_ag.client import (
    BASE_URL,
    fetch_complaints,
    load_complaints_csv,
    write_csv,
)


def _complaint(**overrides) -> WaAgComplaint:
    defaults = {
        "complaint_id": "1",
        "open_date": "2025-01-15",
        "close_date": "2025-02-20",
        "status": "Closed",
        "company_name": "Acme Corp",
        "business_type": "Retail",
        "complaint_category": "Billing",
        "resolution": "Resolved",
        "consumer_city": "Seattle",
        "consumer_state": "WA",
        "consumer_zip": "98101",
    }
    defaults.update(overrides)
    return WaAgComplaint(**defaults)


class TestWaAgComplaintModel:
    def test_from_api_response_basic(self):
        item = {
            "id": "42",
            "open_date": "2025-01-15T00:00:00.000",
            "close_date": "2025-02-20T00:00:00.000",
            "status": "Closed",
            "company_name": "Acme Corp",
            "business_type": "Retail",
            "complaint_category": "Billing",
            "resolution": "Resolved",
            "consumer_city": "Seattle",
            "consumer_state": "WA",
            "consumer_zip": "98101",
        }
        c = WaAgComplaint.from_api_response(item)
        assert c.complaint_id == "42"
        assert c.open_date == "2025-01-15"
        assert c.close_date == "2025-02-20"
        assert c.company_name == "Acme Corp"

    def test_from_api_response_missing_fields(self):
        c = WaAgComplaint.from_api_response({})
        assert c.complaint_id == ""
        assert c.open_date == ""
        assert c.company_name == ""

    def test_from_api_response_truncates_datetime(self):
        item = {"open_date": "2025-06-15T12:30:45.000", "close_date": ""}
        c = WaAgComplaint.from_api_response(item)
        assert c.open_date == "2025-06-15"
        assert c.close_date == ""

    def test_from_csv_row(self):
        row = {
            "complaint_id": "99",
            "open_date": "2025-03-01",
            "company_name": "Test Co",
            "status": "Open",
        }
        c = WaAgComplaint.from_csv_row(row)
        assert c.complaint_id == "99"
        assert c.company_name == "Test Co"

    def test_to_dict_roundtrip(self):
        c = _complaint()
        d = c.to_dict()
        assert d["complaint_id"] == "1"
        assert d["company_name"] == "Acme Corp"


class TestFetchComplaints:
    @patch("complaint_pipeline.wa_ag.client.httpx.Client")
    def test_basic_fetch(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": "1", "company_name": "Test Corp", "status": "Open"}
        ]
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = fetch_complaints()
        assert len(result) == 1
        assert result[0].company_name == "Test Corp"

    @patch("complaint_pipeline.wa_ag.client.httpx.Client")
    def test_fetch_with_filters(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        fetch_complaints(since="2025-01-01", business_type="Retail", status="Closed")
        call_args = mock_client.get.call_args
        params = call_args[1].get("params", call_args[0][1] if len(call_args[0]) > 1 else {})
        where = params.get("$where", "")
        assert "openeddate >= '2025-01-01'" in where
        assert "businesscategory = 'Retail'" in where

    @patch("complaint_pipeline.wa_ag.client.httpx.Client")
    def test_fetch_empty(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = fetch_complaints()
        assert result == []


class TestCsvRoundtrip:
    def test_write_and_load(self, tmp_path):
        complaints = [_complaint(complaint_id="1"), _complaint(complaint_id="2")]
        csv_path = tmp_path / "test.csv"
        write_csv(complaints, csv_path)
        loaded = load_complaints_csv(csv_path)
        assert len(loaded) == 2
        assert loaded[0].complaint_id == "1"
        assert loaded[1].company_name == "Acme Corp"

    def test_load_missing_file(self, tmp_path):
        result = load_complaints_csv(tmp_path / "nope.csv")
        assert result == []

    def test_write_empty_list(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        write_csv([], csv_path)
        assert not csv_path.exists()
