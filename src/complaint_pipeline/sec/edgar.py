"""SEC EDGAR filing client for public company filings.

Refactored from: scripts/sec_filing_analysis.py

Key changes:
  urllib.request.urlopen() → httpx.get()   (Consistency — same HTTP lib everywhere)
  Hardcoded OUTPUT_DIR → Path parameters   (Parameterize)
  Returns dicts → returns Filing objects   (Extract structure)
  print() → logging                        (Structured output)
"""

import csv
import logging
import re
from pathlib import Path

import httpx

from complaint_pipeline.models import Filing

logger = logging.getLogger(__name__)

# SEC requires a User-Agent identifying the requester.
USER_AGENT = "ComplaintPipeline research@example.com"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}

# Known Pathward Financial CIK
PATHWARD_CIK = "0000907471"


def fetch_submissions(cik: str = PATHWARD_CIK) -> dict:
    """Fetch a company's filing submissions from EDGAR.

    Before: urllib.request.urlopen(Request(url, headers=...))
    After:  httpx.get(url, headers=...)

    Why switch? httpx gives consistent API with the CFPB client,
    better error messages, and automatic JSON decoding.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    logger.info("Fetching SEC submissions from %s", url)

    response = httpx.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_filings(submissions: dict, form_types: list[str] | None = None) -> list[Filing]:
    """Extract filing records from EDGAR submissions data.

    Before: returned list[dict]
    After:  returns list[Filing] — typed, with named fields.
    """
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    cik = str(submissions.get("cik", PATHWARD_CIK)).lstrip("0")

    filings = []
    for i in range(len(forms)):
        if form_types and forms[i] not in form_types:
            continue

        accession = accessions[i] if i < len(accessions) else ""
        document = documents[i] if i < len(documents) else ""

        url = ""
        if accession and document:
            acc_clean = accession.replace('-', '')
            url = (
                f"https://www.sec.gov/Archives/edgar/data"
                f"/{cik}/{acc_clean}/{document}"
            )

        filings.append(Filing(
            form_type=forms[i],
            filing_date=dates[i] if i < len(dates) else "",
            accession_number=accession,
            primary_document=document,
            description=descriptions[i] if i < len(descriptions) else "",
            url=url,
        ))

    return filings


def write_filings_csv(filings: list[Filing], filepath: Path) -> None:
    """Write filing records to CSV."""
    if not filings:
        logger.warning("No filings to write")
        return

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(Filing.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(filing.to_dict() for filing in filings)
    logger.info("Wrote %d filings to %s", len(filings), filepath)


def fetch_pathward(output_dir: Path) -> dict[str, list[Filing]]:
    """Fetch and categorize all relevant Pathward filings.

    Returns dict with keys: 'amended', 'insider', 'regular'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    submissions = fetch_submissions()
    company_name = submissions.get("name", "Unknown")
    logger.info("Company: %s (CIK: %s)", company_name, submissions.get("cik", "?"))

    amended = extract_filings(submissions, ["10-K/A", "10-Q/A"])
    insider = extract_filings(submissions, ["4"])
    regular = extract_filings(submissions, ["10-K", "10-Q"])

    logger.info("Found %d amended, %d insider (Form 4), %d regular filings",
                len(amended), len(insider), len(regular))

    # Write combined index
    all_filings = amended + insider + regular
    write_filings_csv(all_filings, output_dir / "pathward_filings_index.csv")

    return {
        "amended": amended,
        "insider": insider,
        "regular": regular,
        "company_name": company_name,
        "cik": str(submissions.get("cik", PATHWARD_CIK)),
    }


def fetch_filing_text(url: str) -> str:
    """Download a filing document from SEC EDGAR and extract plain text.

    SEC filings are HTML. Strip tags to get searchable text.
    Uses the re module to strip HTML tags (no bs4 dependency).
    """
    logger.info("Fetching filing text from %s", url)
    response = httpx.get(url, headers=HEADERS, timeout=60, follow_redirects=True)
    response.raise_for_status()
    html = response.text

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse runs of whitespace into single spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def fetch_latest_10k(cik: str = PATHWARD_CIK) -> tuple[Filing, str]:
    """Find the most recent 10-K filing and download its text content.

    Returns (filing_metadata, full_text).
    Looks for form_type "10-K" (not "10-K/A" amendments).
    """
    submissions = fetch_submissions(cik)
    filings = extract_filings(submissions, ["10-K"])

    if not filings:
        raise ValueError(f"No 10-K filings found for CIK {cik}")

    latest = filings[0]  # extract_filings returns in filing order (most recent first)
    logger.info("Latest 10-K: %s filed %s", latest.accession_number, latest.filing_date)

    if not latest.url:
        raise ValueError(f"No URL available for 10-K filing {latest.accession_number}")

    text = fetch_filing_text(latest.url)
    logger.info("Downloaded 10-K text: %d characters", len(text))
    return latest, text
