"""Complaint narrative text mining — extract patterns from unstructured complaint text.

Extracts structured signals from free-text complaint narratives:
  - Geographic clustering (state + zip prefix + date window)
  - Purchase-to-drain time deltas
  - Denomination targeting ($100, $200, $500)
  - Retailer mentions (Walgreens, CVS, Dollar General, Walmart, etc.)
  - Complaint type classification via keyword scoring
  - Company response pattern analysis

All functions are PURE: data in, results out, no side effects.
"""

import re
from collections import Counter, defaultdict

from complaint_pipeline.models import Complaint

# --- Dollar amount extraction ---

_DOLLAR_RE = re.compile(
    r"""
    (?:
        \{\$([0-9,]+(?:\.\d{2})?)\}   # CFPB redacted format: {$500.00}
        | \$([0-9,]+(?:\.\d{2})?)      # Standard: $500.00 or $500
    )
    """,
    re.VERBOSE,
)

# Common gift card denominations
_GIFT_CARD_DENOMINATIONS = {25, 50, 75, 100, 150, 200, 250, 300, 400, 500}


def extract_dollar_amounts(text: str) -> list[float]:
    """Extract dollar amounts from narrative text.

    Handles both CFPB redacted format {$500.00} and standard $500.00.
    """
    amounts = []
    for match in _DOLLAR_RE.finditer(text):
        raw = match.group(1) or match.group(2)
        try:
            amounts.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return amounts


def denomination_targeting(complaints: list[Complaint]) -> dict[str, int | list]:
    """Analyze which denominations appear most in complaints.

    Returns dict with:
      - denomination_counts: Counter of amounts matching common denominations
      - all_amounts: Counter of all dollar amounts mentioned
      - total_narratives: number of complaints with narrative text
    """
    denom_counts: Counter[float] = Counter()
    all_amounts: Counter[float] = Counter()
    narratives_with_amounts = 0

    for c in complaints:
        if not c.narrative:
            continue
        amounts = extract_dollar_amounts(c.narrative)
        if amounts:
            narratives_with_amounts += 1
        for amt in amounts:
            all_amounts[amt] += 1
            if amt in _GIFT_CARD_DENOMINATIONS:
                denom_counts[amt] += 1

    return {
        "denomination_counts": dict(denom_counts.most_common()),
        "all_amounts_top20": dict(all_amounts.most_common(20)),
        "narratives_with_amounts": narratives_with_amounts,
        "total_narratives": sum(1 for c in complaints if c.narrative),
    }


# --- Date extraction and time-delta analysis ---

_DATE_PATTERNS = [
    # XX/XX/XXXX or XX/XX/year> (CFPB redacted)
    re.compile(r"XX/XX/(\d{4}|year>|XXXX)"),
    # "on [month] [day], [year]" or "on [month] [day]"
    re.compile(
        r"(?:on|around|about)\s+"
        r"(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"\s+\d{1,2}(?:,?\s+\d{4})?",
        re.IGNORECASE,
    ),
]

# Keywords indicating purchase vs drain events
_PURCHASE_KEYWORDS = [
    "purchased", "bought", "received", "gifted", "activated",
    "buying", "purchase", "got the card", "bought the card",
]
_DRAIN_KEYWORDS = [
    "drained", "zero balance", "$0", "no balance", "empty",
    "unauthorized", "missing", "gone", "stolen", "used without",
    "was used", "someone used", "balance was", "funds were",
    "wiped", "depleted",
]


def purchase_to_drain_patterns(complaints: list[Complaint]) -> dict[str, int | float]:
    """Classify complaints by how quickly cards were drained after purchase.

    Categories:
      - immediate: drained before first use attempt (same day or never used)
      - days: drained within days (mentions waiting days/a week)
      - weeks: drained after weeks
      - months: drained after months
      - unknown: can't determine timing

    Also counts pre-activation drains (card drained before buyer ever activated).
    """
    timing = Counter({"immediate": 0, "days": 0, "weeks": 0, "months": 0, "unknown": 0})
    pre_activation = 0
    total_with_narrative = 0

    immediate_phrases = [
        "never activated", "never used", "first time", "first attempt",
        "just purchased", "just bought", "same day", "right away",
        "immediately", "brand new", "unopened", "still sealed",
        "before i could", "before i even",
    ]
    days_phrases = ["few days", "next day", "day later", "days later", "a week", "one week"]
    weeks_phrases = ["weeks later", "few weeks", "two weeks", "three weeks", "a month"]
    months_phrases = ["months later", "several months", "few months", "a year"]

    for c in complaints:
        if not c.narrative:
            continue
        total_with_narrative += 1
        text = c.narrative.lower()

        # Check for pre-activation drain
        if any(phrase in text for phrase in ["never activated", "before activation",
                                             "not yet activated", "hadn't activated",
                                             "before i activated"]):
            pre_activation += 1

        # Classify timing
        if any(phrase in text for phrase in immediate_phrases):
            timing["immediate"] += 1
        elif any(phrase in text for phrase in days_phrases):
            timing["days"] += 1
        elif any(phrase in text for phrase in weeks_phrases):
            timing["weeks"] += 1
        elif any(phrase in text for phrase in months_phrases):
            timing["months"] += 1
        else:
            timing["unknown"] += 1

    return {
        "timing_distribution": dict(timing),
        "pre_activation_drains": pre_activation,
        "total_with_narrative": total_with_narrative,
        "immediate_pct": round(100 * timing["immediate"] / total_with_narrative, 1)
        if total_with_narrative > 0
        else 0,
    }


# --- Retailer mention analysis ---

_RETAILERS = [
    "walgreens", "cvs", "walmart", "target", "dollar general",
    "dollar tree", "family dollar", "rite aid", "kroger", "safeway",
    "costco", "sam's club", "7-eleven", "7 eleven", "circle k",
    "speedway", "wawa", "sheetz", "publix", "meijer",
    "best buy", "home depot", "lowe's", "lowes",
    "amazon", "ebay", "online",
    "gas station", "convenience store", "grocery store",
    "woolworths",  # Australian TCN complaints
]


def retailer_mentions(
    complaints: list[Complaint],
    retailers: list[str] | None = None,
) -> dict[str, int]:
    """Count retailer mentions in complaint narratives.

    Args:
        complaints: List of complaints to analyze.
        retailers: Optional custom retailer list. Defaults to _RETAILERS.

    Returns {retailer: count} sorted by count descending.
    """
    retailer_list = retailers if retailers is not None else _RETAILERS
    counts: Counter[str] = Counter()
    for c in complaints:
        if not c.narrative:
            continue
        text = c.narrative.lower()
        for retailer in retailer_list:
            if retailer in text:
                counts[retailer] += 1
    return dict(counts.most_common())


# --- Complaint type classification ---

def classify_fraud_type(
    complaints: list[Complaint],
    signals: dict[str, list[str]] | None = None,
) -> dict[str, int | list]:
    """Classify each complaint narrative by signal categories.

    When signals is None (default), uses prepaid-card-specific pre-shelf vs
    post-activation classification. When signals is provided, scores each
    narrative against the custom signal categories.

    Args:
        complaints: List of complaints to analyze.
        signals: Optional dict of {category_name: [keywords]}.
            If None, uses built-in prepaid card pre-shelf/post-activation signals.
    """
    if signals is not None:
        return _classify_custom_signals(complaints, signals)

    # Default prepaid card classification
    pre_shelf = 0
    post_activation = 0
    unclear = 0
    total = 0

    pre_shelf_signals = [
        "never activated", "never used", "brand new",
        "before i could use", "before i even used",
        "zero balance", "no balance", "empty",
        "first time i tried", "first attempt",
        "tampered", "packaging", "seal", "scratch",
        "just purchased", "just bought",
        "immediately", "right away", "same day",
        "still in the package", "still sealed",
    ]
    post_activation_signals = [
        "was working", "used it before", "had been using",
        "balance decreased", "remaining balance",
        "unauthorized transaction", "unauthorized charge",
        "someone used", "was used without",
        "after i used", "after using",
        "balance went down", "balance dropped",
    ]

    for c in complaints:
        if not c.narrative:
            continue
        total += 1
        text = c.narrative.lower()

        pre_score = sum(1 for s in pre_shelf_signals if s in text)
        post_score = sum(1 for s in post_activation_signals if s in text)

        if pre_score > post_score and pre_score > 0:
            pre_shelf += 1
        elif post_score > pre_score and post_score > 0:
            post_activation += 1
        else:
            unclear += 1

    return {
        "pre_shelf_drain": pre_shelf,
        "post_activation_drain": post_activation,
        "unclear": unclear,
        "total_classified": total,
        "pre_shelf_pct": round(100 * pre_shelf / total, 1) if total > 0 else 0,
        "post_activation_pct": round(100 * post_activation / total, 1) if total > 0 else 0,
    }


def _classify_custom_signals(
    complaints: list[Complaint],
    signals: dict[str, list[str]],
) -> dict[str, int | list]:
    """Classify complaints using custom signal categories.

    Scores each narrative against all signal categories. The category with the
    highest match count wins; ties go to 'unclear'.
    """
    categories = list(signals.keys())
    counts = {cat: 0 for cat in categories}
    counts["unclear"] = 0
    total = 0

    for c in complaints:
        if not c.narrative:
            continue
        total += 1
        text = c.narrative.lower()

        scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in signals.items()}
        max_score = max(scores.values())

        if max_score == 0:
            counts["unclear"] += 1
        else:
            winners = [cat for cat, s in scores.items() if s == max_score]
            if len(winners) == 1:
                counts[winners[0]] += 1
            else:
                counts["unclear"] += 1

    result: dict[str, int | list] = {
        "total_classified": total,
        "unclear": counts["unclear"],
    }
    for cat in categories:
        result[cat] = counts[cat]
        result[f"{cat}_pct"] = round(100 * counts[cat] / total, 1) if total > 0 else 0

    return result


# --- Geographic clustering ---

def geographic_clustering(
    complaints: list[Complaint],
    date_window_months: int = 3,
) -> dict[str, list | dict]:
    """Group complaints by state + zip prefix + date window to find geographic clusters.

    A cluster = multiple complaints from the same state + zip3 prefix within a date window.
    Clusters may indicate a regional pattern in the complaint data.
    """
    # Group by state + zip3 + quarter
    clusters: dict[str, list[Complaint]] = defaultdict(list)
    state_counts: Counter[str] = Counter()
    zip3_counts: Counter[str] = Counter()

    for c in complaints:
        if not c.state:
            continue
        state_counts[c.state] += 1

        # Extract zip3 prefix (first 3 digits, CFPB often gives "123XX" format)
        zip3 = ""
        if c.zip_code:
            digits = re.sub(r"[^0-9]", "", c.zip_code)
            if len(digits) >= 3:
                zip3 = digits[:3]
                zip3_counts[zip3] += 1

        # Extract quarter from date
        quarter = ""
        if c.date_received and len(c.date_received) >= 7:
            year_month = c.date_received[:7]
            year = year_month[:4]
            month = int(year_month[5:7])
            q = (month - 1) // date_window_months + 1
            quarter = f"{year}-Q{q}"

        key = f"{c.state}|{zip3}|{quarter}"
        clusters[key].append(c)

    # Find clusters with 2+ complaints
    significant_clusters = []
    for key, group in sorted(clusters.items(), key=lambda x: -len(x[1])):
        if len(group) >= 2:
            parts = key.split("|")
            significant_clusters.append({
                "state": parts[0],
                "zip3": parts[1],
                "period": parts[2],
                "count": len(group),
                "complaint_ids": [c.complaint_id for c in group[:10]],
            })

    return {
        "state_distribution": dict(state_counts.most_common()),
        "zip3_distribution": dict(zip3_counts.most_common(30)),
        "clusters": significant_clusters[:50],
        "total_clusters": len(significant_clusters),
    }


# --- Company response pattern analysis ---

def response_patterns(
    complaints: list[Complaint],
    pattern_keywords: dict[str, list[str]] | None = None,
) -> dict[str, int | dict]:
    """Analyze company response patterns in complaint narratives.

    Args:
        complaints: List of complaints to analyze.
        pattern_keywords: Optional custom pattern dict. If None, uses built-in
            prepaid card response patterns.

    Looks for keyword groups in narratives and counts matches per pattern.
    """
    patterns: Counter[str] = Counter()
    total_with_narrative = 0

    if pattern_keywords is None:
        pattern_keywords = {
            "investigation_concluded": [
                "investigation", "investigated", "concluded", "determined",
                "found that", "our records show", "records indicate",
            ],
            "physically_present": [
                "physically present", "card was present", "chip was read",
                "pin was entered", "in-person", "in person",
            ],
            "denied_claim": [
                "denied", "decline", "not eligible", "unable to assist",
                "not responsible", "no liability", "denied my claim",
            ],
            "delay_runaround": [
                "no response", "never heard back", "waiting",
                "called multiple times", "called again", "still waiting",
                "months later", "weeks later", "run around", "runaround",
                "keep asking", "same information", "reset the clock",
            ],
            "refund_issued": [
                "refund", "reimbursed", "replacement card", "new card",
                "credit issued", "credited",
            ],
            "police_report_required": [
                "police report", "file a report", "law enforcement",
                "statutory declaration",
            ],
            "geographic_impossibility": [
                "different state", "another state", "never been to",
                "miles away", "across the country", "another city",
                "was not in", "wasn't in", "have never been",
            ],
        }

    for c in complaints:
        if not c.narrative:
            continue
        total_with_narrative += 1
        text = c.narrative.lower()

        for pattern_name, keywords in pattern_keywords.items():
            if any(kw in text for kw in keywords):
                patterns[pattern_name] += 1

    # Also analyze company_response field
    response_types: Counter[str] = Counter()
    for c in complaints:
        if c.company_response:
            response_types[c.company_response] += 1

    return {
        "narrative_patterns": dict(patterns.most_common()),
        "company_responses": dict(response_types.most_common()),
        "total_with_narrative": total_with_narrative,
    }


# --- Comprehensive analysis runner ---

def full_narrative_analysis(complaints: list[Complaint]) -> dict[str, dict]:
    """Run all narrative analysis functions and return combined results."""
    return {
        "denomination_targeting": denomination_targeting(complaints),
        "purchase_to_drain": purchase_to_drain_patterns(complaints),
        "retailer_mentions": retailer_mentions(complaints),
        "fraud_classification": classify_fraud_type(complaints),
        "geographic_clustering": geographic_clustering(complaints),
        "response_patterns": response_patterns(complaints),
        "summary": {
            "total_complaints": len(complaints),
            "with_narrative": sum(1 for c in complaints if c.narrative),
            "without_narrative": sum(1 for c in complaints if not c.narrative),
        },
    }
