"""CFPB complaint analysis — pure functions over Complaint data."""

from collections import Counter

from complaint_pipeline.models import Complaint


def monthly_timeseries(complaints: list[Complaint]) -> dict[str, int]:
    """Monthly complaint counts, sorted chronologically."""
    monthly: Counter[str] = Counter()
    for c in complaints:
        if c.date_received and len(c.date_received) >= 7:
            monthly[c.date_received[:7]] += 1
    return dict(sorted(monthly.items()))


def yearly_breakdown(complaints: list[Complaint]) -> dict[str, int]:
    """Yearly complaint counts, sorted chronologically."""
    years: Counter[str] = Counter()
    for c in complaints:
        if c.date_received and len(c.date_received) >= 4:
            years[c.date_received[:4]] += 1
    return dict(sorted(years.items()))


def geographic_analysis(complaints: list[Complaint]) -> list[tuple[str, int]]:
    """Top states by complaint count."""
    states = Counter(c.state for c in complaints if c.state)
    return states.most_common()


def response_analysis(complaints: list[Complaint]) -> list[tuple[str, int]]:
    """Company response type distribution."""
    responses = Counter(c.company_response for c in complaints if c.company_response)
    return responses.most_common()


def issue_analysis(complaints: list[Complaint]) -> list[tuple[str, int]]:
    """Issue category distribution (top 20)."""
    issues = Counter(c.issue for c in complaints if c.issue)
    return issues.most_common(20)


def product_breakdown(complaints: list[Complaint]) -> list[tuple[str, int]]:
    """Product type distribution."""
    products = Counter(c.product for c in complaints if c.product)
    return products.most_common()


def company_breakdown(complaints: list[Complaint]) -> list[tuple[str, int]]:
    """Companies found in results."""
    companies = Counter(c.company for c in complaints)
    return companies.most_common()


def disputed_rate(complaints: list[Complaint]) -> dict:
    """Consumer dispute rate statistics."""
    total = len(complaints)
    disputed = sum(1 for c in complaints if c.consumer_disputed == "Yes")
    not_disputed = sum(1 for c in complaints if c.consumer_disputed == "No")
    return {
        "total": total,
        "disputed": disputed,
        "not_disputed": not_disputed,
        "n_a": total - disputed - not_disputed,
        "dispute_rate_pct": round(100 * disputed / total, 1) if total > 0 else 0,
    }


def monetary_relief_rate(complaints: list[Complaint]) -> dict:
    """Monetary relief and closure statistics."""
    total = len(complaints)
    if total == 0:
        return {"total": 0, "relief": 0, "explanation": 0, "timely": 0}

    relief = sum(1 for c in complaints if "monetary" in c.company_response.lower())
    explanation = sum(1 for c in complaints if "explanation" in c.company_response.lower())
    timely = sum(1 for c in complaints if c.timely_response == "Yes")

    return {
        "total": total,
        "relief": relief,
        "relief_pct": round(100 * relief / total, 1),
        "explanation": explanation,
        "explanation_pct": round(100 * explanation / total, 1),
        "timely": timely,
        "timely_pct": round(100 * timely / total, 1),
    }


def narrative_keyword_counts(
    complaints: list[Complaint],
    keywords: list[str] | None = None,
) -> dict[str, int]:
    """Count keyword occurrences in complaint narratives.

    Only counts complaints that have narrative text (not all do).
    Returns {keyword: count} sorted by count descending.
    """
    if keywords is None:
        keywords = [
            "denied", "refund", "fraud", "unauthorized", "stolen",
            "drained", "scam", "replacement", "no response",
            "investigation", "vanilla", "gift card", "balance", "activated",
        ]

    narratives = [c for c in complaints if c.narrative]
    counts: dict[str, int] = {kw: 0 for kw in keywords}
    for c in narratives:
        text = c.narrative.lower()
        for kw in keywords:
            if kw in text:
                counts[kw] += 1

    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def date_range(complaints: list[Complaint]) -> tuple[str, str] | None:
    """Earliest and latest date_received, or None if no dates."""
    dates = sorted(c.date_received for c in complaints if c.date_received)
    if not dates:
        return None
    return dates[0], dates[-1]
