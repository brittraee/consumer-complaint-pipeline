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
class FtcComplaint:
    """A single FTC Do Not Call complaint record.

    Data source: https://api.ftc.gov/v0/dnc-complaints
    """

    complaint_id: str = ""
    created_date: str = ""
    violation_date: str = ""
    company_phone_number: str = ""
    consumer_city: str = ""
    consumer_state: str = ""
    consumer_area_code: str = ""
    subject: str = ""
    is_robocall: str = ""

    @classmethod
    def from_api_response(cls, item: dict) -> "FtcComplaint":
        """Create an FtcComplaint from an FTC API response item.

        The FTC API wraps fields in an 'attributes' object with
        hyphenated keys (JSON:API style).
        """
        attrs = item.get("attributes", {})
        robocall_raw = attrs.get("recorded-message-or-robocall", "")
        return cls(
            complaint_id=str(item.get("id", "")),
            created_date=attrs.get("created-date", ""),
            violation_date=attrs.get("violation-date", ""),
            company_phone_number=attrs.get("company-phone-number", ""),
            consumer_city=attrs.get("consumer-city", ""),
            consumer_state=attrs.get("consumer-state", ""),
            consumer_area_code=attrs.get("consumer-area-code", ""),
            subject=attrs.get("subject", ""),
            is_robocall=robocall_raw,
        )

    @classmethod
    def from_csv_row(cls, row: dict) -> "FtcComplaint":
        """Create an FtcComplaint from a CSV DictReader row."""
        return cls(**{k: row.get(k, "") for k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WaAgComplaint:
    """A single WA State Attorney General consumer complaint record.

    Data source: https://data.wa.gov/resource/gpri-47xz.json
    """

    complaint_id: str = ""
    open_date: str = ""
    close_date: str = ""
    status: str = ""
    company_name: str = ""
    business_type: str = ""
    complaint_category: str = ""
    resolution: str = ""
    consumer_city: str = ""
    consumer_state: str = ""
    consumer_zip: str = ""

    @classmethod
    def from_api_response(cls, item: dict) -> "WaAgComplaint":
        """Create a WaAgComplaint from a Socrata API response item."""
        raw_open = item.get("open_date", "")
        open_date = raw_open[:10] if raw_open else ""
        raw_close = item.get("close_date", "")
        close_date = raw_close[:10] if raw_close else ""

        return cls(
            complaint_id=str(item.get("id", item.get("complaint_id", ""))),
            open_date=open_date,
            close_date=close_date,
            status=item.get("status", ""),
            company_name=item.get("company_name", item.get("business_name", "")),
            business_type=item.get("business_type", ""),
            complaint_category=item.get("complaint_category", item.get("naics_code", "")),
            resolution=item.get("resolution", ""),
            consumer_city=item.get("consumer_city", item.get("city", "")),
            consumer_state=item.get("consumer_state", item.get("state", "")),
            consumer_zip=item.get("consumer_zip", item.get("zip", "")),
        )

    @classmethod
    def from_csv_row(cls, row: dict) -> "WaAgComplaint":
        """Create a WaAgComplaint from a CSV DictReader row."""
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
