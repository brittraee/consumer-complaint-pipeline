"""Tests for CFPB client module.

Tests the data parsing/writing logic — NOT live API calls.
Live API tests would be integration tests (Phase 2).
"""

import csv

from complaint_pipeline.cfpb.client import load_complaints_csv, write_csv


class TestWriteAndLoadCSV:
    def test_roundtrip(self, tmp_path, sample_complaints):
        """Write complaints to CSV, read them back, verify data survives."""
        csv_path = tmp_path / "test_complaints.csv"
        write_csv(sample_complaints, csv_path)

        assert csv_path.exists()

        loaded = load_complaints_csv(csv_path)
        assert len(loaded) == len(sample_complaints)
        assert loaded[0].complaint_id == sample_complaints[0].complaint_id
        assert loaded[0].company == sample_complaints[0].company

    def test_write_empty_list(self, tmp_path):
        """Writing empty list should not create a file."""
        csv_path = tmp_path / "empty.csv"
        write_csv([], csv_path)
        assert not csv_path.exists()

    def test_load_missing_file(self, tmp_path):
        """Loading from nonexistent file should return empty list."""
        result = load_complaints_csv(tmp_path / "nonexistent.csv")
        assert result == []

    def test_csv_has_headers(self, tmp_path, sample_complaints):
        """CSV should have proper column headers."""
        csv_path = tmp_path / "headers.csv"
        write_csv(sample_complaints, csv_path)

        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert "complaint_id" in headers
        assert "company" in headers
        assert "narrative" in headers
