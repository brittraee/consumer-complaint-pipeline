"""CFPB complaint data client.

Refactored from: scripts/cfpb_complaint_pull.py

Key changes:
  subprocess.run(["curl"...]) → httpx.get()     (Replace shell call with library)
  print() → logging                              (Structured output)
  Hardcoded OUTPUT_DIR → function parameters      (Parameterize)
  Returns list[dict] → list[Complaint]            (Extract structure)
"""

import csv
import logging
from pathlib import Path
from urllib.parse import quote_plus, urlencode

import httpx

from complaint_pipeline.models import Complaint

logger = logging.getLogger(__name__)

BASE_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"

# Browser-like User-Agent is required — CFPB returns 403 to default clients.
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

COMPANIES = {
    "InComm": "incomm",
    "Blackhawk": "blackhawk",
}

BNPL_COMPANIES = {
    "Affirm": "affirm",
    "Klarna": "klarna",
    "Afterpay": "afterpay",
    "PayPal Credit": "paypal_credit",
    "Zip": "zip_quadpay",
}


def fetch_complaints(search_term: str, size: int = 1000) -> list[Complaint]:
    """Fetch complaints from the CFPB API for a search term.

    Before: subprocess.run(["curl", "-s", "-H", "User-Agent: ...", url])
    After:  httpx.get(url, headers=HEADERS)

    Why? Curl via subprocess is a shell call — you get stdout as a string,
    have to parse JSON manually, and error handling is clunky. httpx gives you
    a typed Response object with .json(), .status_code, .raise_for_status().
    """
    params = {
        "search_term": search_term,
        "size": size,
        "format": "json",
    }
    url = f"{BASE_URL}?{urlencode(params, quote_via=quote_plus)}"
    logger.info("Fetching complaints for '%s' from CFPB API", search_term)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP %d fetching complaints for '%s': %s",
            e.response.status_code, search_term, e,
        )
        return []
    except Exception as e:
        logger.error("Error fetching complaints for '%s': %s", search_term, e)
        return []

    # CFPB API returns either a flat list or nested {hits: {hits: [...]}}
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict) and "hits" in data:
        raw_items = data.get("hits", {}).get("hits", [])
    else:
        raw_items = []

    complaints = [Complaint.from_api_response(item) for item in raw_items]
    logger.info("Fetched %d complaints for '%s'", len(complaints), search_term)
    return complaints


def write_csv(complaints: list[Complaint], filepath: Path) -> None:
    """Write complaint records to CSV.

    Before: hardcoded os.path.join(OUTPUT_DIR, filename)
    After:  caller passes the full path — portable, testable.
    """
    if not complaints:
        logger.warning("No records to write for %s", filepath.name)
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(Complaint.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(c.to_dict() for c in complaints)
    logger.info("Wrote %d records to %s", len(complaints), filepath)


def load_complaints_csv(filepath: Path) -> list[Complaint]:
    """Load complaint records from a CSV file."""
    if not filepath.exists():
        logger.warning("File not found: %s", filepath)
        return []
    with open(filepath, encoding="utf-8") as f:
        return [Complaint.from_csv_row(row) for row in csv.DictReader(f)]


def fetch_all(
    output_dir: Path,
    companies: dict[str, str] | None = None,
) -> dict[str, list[Complaint]]:
    """Fetch complaints for all configured companies and write CSVs.

    Before: main() did everything — fetch, write, summarize, all hardcoded.
    After:  fetch_all() handles fetch + write, returns data for downstream use.

    Args:
        output_dir: Directory to write CSV files.
        companies: Optional dict of {search_term: short_name}. Defaults to COMPANIES.
    """
    if companies is None:
        companies = COMPANIES

    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for search_term, short_name in companies.items():
        complaints = fetch_complaints(search_term)
        csv_path = output_dir / f"{short_name}_complaints.csv"
        write_csv(complaints, csv_path)
        results[short_name] = complaints

    return results
