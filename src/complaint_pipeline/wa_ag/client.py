"""WA State Attorney General consumer complaint client."""

import csv
import logging
from pathlib import Path

import httpx

from complaint_pipeline.models import WaAgComplaint

logger = logging.getLogger(__name__)

BASE_URL = "https://data.wa.gov/resource/gpri-47xz.json"
DEFAULT_LIMIT = 1000
MAX_LIMIT = 50000


def fetch_complaints(
    since: str | None = None,
    business_type: str | None = None,
    status: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[WaAgComplaint]:
    """Fetch consumer complaints from WA State AG via Socrata API."""
    params: dict[str, str | int] = {
        "$limit": min(limit, MAX_LIMIT),
        "$offset": offset,
        "$order": "openeddate DESC",
    }

    where_clauses = []
    if since:
        where_clauses.append(f"openeddate >= '{since}'")
    if business_type:
        where_clauses.append(f"businesscategory = '{business_type}'")
    if status:
        where_clauses.append(f"status = '{status}'")
    if where_clauses:
        params["$where"] = " AND ".join(where_clauses)

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    logger.info("Fetched %d WA AG complaints (offset=%d)", len(data), offset)
    return [WaAgComplaint.from_api_response(item) for item in data]


def fetch_all(
    output_dir: Path,
    since: str | None = None,
    business_type: str | None = None,
    batch_size: int = DEFAULT_LIMIT,
) -> list[WaAgComplaint]:
    """Fetch all matching complaints with pagination and write CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    all_complaints: list[WaAgComplaint] = []
    offset = 0

    while True:
        batch = fetch_complaints(
            since=since,
            business_type=business_type,
            limit=batch_size,
            offset=offset,
        )
        if not batch:
            break
        all_complaints.extend(batch)
        offset += len(batch)
        if len(batch) < batch_size:
            break

    if all_complaints:
        write_csv(all_complaints, output_dir / "wa_ag_complaints.csv")

    logger.info("Fetched %d total WA AG complaints", len(all_complaints))
    return all_complaints


def write_csv(complaints: list[WaAgComplaint], path: Path) -> None:
    """Write WA AG complaints to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not complaints:
        return
    fieldnames = list(complaints[0].to_dict().keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(c.to_dict() for c in complaints)
    logger.info("Wrote %d complaints to %s", len(complaints), path)


def load_complaints_csv(path: Path) -> list[WaAgComplaint]:
    """Load WA AG complaints from a CSV file."""
    if not path.exists():
        return []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [WaAgComplaint.from_csv_row(row) for row in reader]
