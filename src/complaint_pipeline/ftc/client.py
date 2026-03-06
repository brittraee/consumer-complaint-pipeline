"""FTC Do Not Call complaint client — fetch robocall/unwanted call data from the FTC API.

Data source: https://api.ftc.gov/v0/dnc-complaints
API docs:    https://www.ftc.gov/developer/api/v0/endpoints/do-not-call-dnc-reported-calls-data-api

Requires a free data.gov API key (https://api.data.gov/signup).
Set FTC_API_KEY env var, or pass api_key to fetch_complaints().
"""

import csv
import logging
import os
from pathlib import Path
from urllib.parse import urlencode

import httpx

from complaint_pipeline.models import FtcComplaint

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ftc.gov/v0/dnc-complaints"

HEADERS = {"User-Agent": "ComplaintPipeline research@example.com"}

# FTC API caps at 50 items per page
DEFAULT_LIMIT = 50


def fetch_complaints(
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    state: str | None = None,
    is_robocall: bool | None = None,
    created_date_from: str | None = None,
    created_date_to: str | None = None,
    api_key: str | None = None,
) -> list[FtcComplaint]:
    """Fetch Do Not Call complaints from the FTC API.

    Args:
        limit: Max records per request (API caps at 50).
        offset: Pagination offset.
        state: Optional state name filter (e.g. "Virginia").
        is_robocall: Optional filter — True for robocalls only, False for non-robocalls.
        created_date_from: Optional ISO date/datetime start filter (e.g. "2024-01-01").
        created_date_to: Optional ISO date/datetime end filter.
        api_key: data.gov API key. Falls back to FTC_API_KEY env var, then DEMO_KEY.
    """
    key = api_key or os.environ.get("FTC_API_KEY", "DEMO_KEY")

    params: dict[str, str | int] = {
        "api_key": key,
        "items_per_page": min(limit, 50),
        "offset": offset,
        "sort_order": "DESC",
    }

    if state:
        params["state"] = f'"{state}"'
    if is_robocall is not None:
        params["is_robocall"] = "true" if is_robocall else "false"
    if created_date_from and created_date_to:
        params["created_date_from"] = f'"{created_date_from}"'
        params["created_date_to"] = f'"{created_date_to}"'

    url = f"{BASE_URL}?{urlencode(params)}"
    logger.info("Fetching FTC DNC complaints (limit=%d, offset=%d)", limit, offset)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("HTTP %d fetching FTC complaints: %s", e.response.status_code, e)
        return []
    except Exception as e:
        logger.error("Error fetching FTC complaints: %s", e)
        return []

    records = data.get("data", [])
    if not isinstance(records, list):
        logger.warning("Unexpected response format from FTC API")
        return []

    complaints = [FtcComplaint.from_api_response(item) for item in records]
    logger.info("Fetched %d FTC complaints", len(complaints))
    return complaints


def write_csv(complaints: list[FtcComplaint], filepath: Path) -> None:
    """Write FTC complaint records to CSV."""
    if not complaints:
        logger.warning("No records to write for %s", filepath.name)
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(FtcComplaint.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(c.to_dict() for c in complaints)
    logger.info("Wrote %d records to %s", len(complaints), filepath)


def load_complaints_csv(filepath: Path) -> list[FtcComplaint]:
    """Load FTC complaint records from a CSV file."""
    if not filepath.exists():
        logger.warning("File not found: %s", filepath)
        return []
    with open(filepath, encoding="utf-8") as f:
        return [FtcComplaint.from_csv_row(row) for row in csv.DictReader(f)]
