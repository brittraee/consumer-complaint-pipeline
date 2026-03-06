"""FCC consumer complaint client — fetch unwanted calls/robocall data from the FCC open data portal.

Data source: https://opendata.fcc.gov/Consumer/Consumer-Complaints-Data-Unwanted-Calls/vakf-fz8e
API: Socrata Open Data API (SODA)
"""

import csv
import logging
from pathlib import Path
from urllib.parse import urlencode

import httpx

from complaint_pipeline.models import FccComplaint

logger = logging.getLogger(__name__)

# Socrata SODA endpoint for the FCC Unwanted Calls dataset
BASE_URL = "https://opendata.fcc.gov/resource/vakf-fz8e.json"

HEADERS = {"User-Agent": "ComplaintPipeline research@example.com"}

# Default Socrata page size (max 50000)
DEFAULT_LIMIT = 1000


def fetch_complaints(
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    state: str | None = None,
    call_type: str | None = None,
    since: str | None = None,
) -> list[FccComplaint]:
    """Fetch unwanted-call complaints from the FCC Socrata API.

    Args:
        limit: Max records to return (Socrata caps at 50000).
        offset: Pagination offset.
        state: Optional 2-letter state filter (e.g. "CA").
        call_type: Optional call type filter (e.g. "Prerecorded Voice").
        since: Optional ISO date string — only return complaints on or after this date.
    """
    params: dict[str, str | int] = {
        "$limit": limit,
        "$offset": offset,
        "$order": "issue_date DESC",
    }

    where_clauses: list[str] = []
    if state:
        where_clauses.append(f"state='{state}'")
    if call_type:
        # API field has a typo: "messge" not "message"
        where_clauses.append(f"type_of_call_or_messge='{call_type}'")
    if since:
        where_clauses.append(f"issue_date>='{since}'")
    if where_clauses:
        params["$where"] = " AND ".join(where_clauses)

    url = f"{BASE_URL}?{urlencode(params)}"
    logger.info("Fetching FCC complaints (limit=%d, offset=%d)", limit, offset)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("HTTP %d fetching FCC complaints: %s", e.response.status_code, e)
        return []
    except Exception as e:
        logger.error("Error fetching FCC complaints: %s", e)
        return []

    if not isinstance(data, list):
        logger.warning("Unexpected response format from FCC API")
        return []

    complaints = [FccComplaint.from_api_response(item) for item in data]
    logger.info("Fetched %d FCC complaints", len(complaints))
    return complaints


def write_csv(complaints: list[FccComplaint], filepath: Path) -> None:
    """Write FCC complaint records to CSV."""
    if not complaints:
        logger.warning("No records to write for %s", filepath.name)
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(FccComplaint.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(c.to_dict() for c in complaints)
    logger.info("Wrote %d records to %s", len(complaints), filepath)


def load_complaints_csv(filepath: Path) -> list[FccComplaint]:
    """Load FCC complaint records from a CSV file."""
    if not filepath.exists():
        logger.warning("File not found: %s", filepath)
        return []
    with open(filepath, encoding="utf-8") as f:
        return [FccComplaint.from_csv_row(row) for row in csv.DictReader(f)]
