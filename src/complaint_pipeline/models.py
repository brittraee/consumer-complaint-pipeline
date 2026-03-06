"""Data models for consumer complaint analysis."""

from dataclasses import asdict, dataclass


@dataclass
class Complaint:
    """A single CFPB complaint record."""

    complaint_id: str = ""
    date_received: str = ""
    date_sent_to_company: str = ""
    company: str = ""
    product: str = ""
    sub_product: str = ""
    issue: str = ""
    sub_issue: str = ""
    narrative: str = ""
    company_response: str = ""
    company_public_response: str = ""
    timely_response: str = ""
    consumer_disputed: str = ""
    state: str = ""
    zip_code: str = ""
    submitted_via: str = ""
    tags: str = ""

    @classmethod
    def from_api_response(cls, item: dict) -> "Complaint":
        """Create a Complaint from a CFPB API response item.

        Handles both nested (_source) and flat formats.
        """
        src = item.get("_source", item)
        return cls(
            complaint_id=str(src.get("complaint_id", "")),
            date_received=src.get("date_received", ""),
            date_sent_to_company=src.get("date_sent_to_company", ""),
            company=src.get("company", ""),
            product=src.get("product", ""),
            sub_product=src.get("sub_product", ""),
            issue=src.get("issue", ""),
            sub_issue=src.get("sub_issue", ""),
            narrative=src.get("complaint_what_happened", ""),
            company_response=src.get("company_response", ""),
            company_public_response=src.get("company_public_response", ""),
            timely_response=src.get("timely", ""),
            consumer_disputed=src.get("consumer_disputed", ""),
            state=src.get("state", ""),
            zip_code=src.get("zip_code", ""),
            submitted_via=src.get("submitted_via", ""),
            tags=src.get("tags", ""),
        )

    @classmethod
    def from_csv_row(cls, row: dict) -> "Complaint":
        """Create a Complaint from a CSV DictReader row."""
        return cls(**{k: row.get(k, "") for k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FccComplaint:
    """A single FCC consumer complaint record (Unwanted Calls dataset)."""

    complaint_id: str = ""
    issue_date: str = ""
    issue_time: str = ""
    issue_type: str = ""
    method: str = ""
    issue: str = ""
    caller_id_number: str = ""
    call_type: str = ""
    advertiser_business_phone_number: str = ""
    state: str = ""
    zip_code: str = ""

    @classmethod
    def from_api_response(cls, item: dict) -> "FccComplaint":
        """Create an FccComplaint from a Socrata API response item."""
        # Normalize the ISO datetime to date-only string
        raw_date = item.get("issue_date", "")
        date_str = raw_date[:10] if raw_date else ""

        return cls(
            complaint_id=str(item.get("id", "")),
            issue_date=date_str,
            issue_time=item.get("issue_time", ""),
            issue_type=item.get("issue_type", ""),
            method=item.get("method", ""),
            issue=item.get("issue", ""),
            caller_id_number=item.get("caller_id_number", ""),
            # Note: the FCC API has a typo — "messge" instead of "message"
            call_type=item.get("type_of_call_or_messge", ""),
            advertiser_business_phone_number=item.get("advertiser_business_phone_number", ""),
            state=item.get("state", ""),
            zip_code=item.get("zip", ""),
        )

    @classmethod
    def from_csv_row(cls, row: dict) -> "FccComplaint":
        """Create an FccComplaint from a CSV DictReader row."""
        return cls(**{k: row.get(k, "") for k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Filing:
    """A single SEC EDGAR filing record."""

    form_type: str = ""
    filing_date: str = ""
    accession_number: str = ""
    primary_document: str = ""
    description: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
