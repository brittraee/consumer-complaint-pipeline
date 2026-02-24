"""Shared test fixtures.

These fixtures provide sample data so tests never hit live APIs.
"""

import json
from pathlib import Path

import pytest

from complaint_pipeline.models import Complaint, Filing

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_api_response() -> dict:
    """Raw CFPB API response (nested format)."""
    return json.loads((FIXTURES_DIR / "sample_cfpb_response.json").read_text())


@pytest.fixture
def sample_complaints(sample_api_response) -> list[Complaint]:
    """5 sample Complaint objects parsed from API response."""
    hits = sample_api_response["hits"]["hits"]
    return [Complaint.from_api_response(item) for item in hits]


@pytest.fixture
def sample_filings() -> list[Filing]:
    """Sample SEC Filing objects."""
    return [
        Filing(
            form_type="4",
            filing_date="2025-07-15",
            accession_number="0001-23-456789",
            primary_document="xslF345X02/filing.xml",
            description="FORM 4",
            url="https://www.sec.gov/Archives/edgar/data/907471/000123456789/filing.xml",
        ),
        Filing(
            form_type="4",
            filing_date="2025-08-20",
            accession_number="0001-23-456790",
            primary_document="xslF345X02/filing2.xml",
            description="FORM 4",
            url="https://www.sec.gov/Archives/edgar/data/907471/000123456790/filing2.xml",
        ),
        Filing(
            form_type="10-K/A",
            filing_date="2025-08-29",
            accession_number="0001-23-456791",
            primary_document="pathward10ka.htm",
            description="10-K/A",
            url="https://www.sec.gov/Archives/edgar/data/907471/000123456791/pathward10ka.htm",
        ),
    ]
