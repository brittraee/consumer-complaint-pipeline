"""BNPL-specific signal definitions for CFPB narrative mining."""

# For classify_fraud_type() — replaces prepaid card pre-shelf/post-activation signals
BNPL_ISSUE_SIGNALS = {
    "loan_terms_confusion": [
        "didn't know", "wasn't told", "hidden fees", "interest rate",
        "didn't realize", "no one explained", "fine print", "misleading",
        "thought it was", "didn't understand", "surprised by",
        "higher than expected", "more than expected",
    ],
    "merchant_dispute": [
        "never received", "returned item", "merchant closed",
        "defective", "wrong item", "canceled order", "refund not processed",
        "store went out of business", "didn't arrive", "not as described",
    ],
    "collection_practices": [
        "sent to collections", "credit report", "harassment",
        "debt collector", "collection agency", "credit score",
        "negative mark", "reported to credit", "credit bureau",
        "threatening", "calling my job", "calling my family",
    ],
    "autopay_issues": [
        "unauthorized charge", "couldn't cancel", "charged after return",
        "automatic payment", "autopay", "auto-pay", "kept charging",
        "double charged", "overcharged", "wrong amount",
        "charged twice", "extra payment", "couldn't stop",
    ],
}

# For response_patterns() — replaces prepaid card response patterns
BNPL_RESPONSE_PATTERNS = {
    "investigation_concluded": [
        "investigation", "investigated", "concluded", "determined",
        "found that", "our records show", "records indicate",
    ],
    "denied_dispute": [
        "denied", "decline", "not eligible", "unable to assist",
        "valid charge", "valid transaction", "merchant confirmed",
    ],
    "credit_report_threat": [
        "report to credit", "credit bureau", "negative impact",
        "delinquent", "past due", "late payment",
    ],
    "delay_runaround": [
        "no response", "never heard back", "waiting",
        "called multiple times", "called again", "still waiting",
        "months later", "weeks later", "run around", "runaround",
    ],
    "partial_resolution": [
        "partial refund", "partial credit", "fee waived",
        "late fee removed", "adjusted balance",
    ],
}

# For retailer_mentions() — BNPL merchant categories instead of physical retailers
BNPL_MERCHANTS = [
    "amazon", "walmart", "target", "best buy", "wayfair",
    "peloton", "casper", "purple", "dyson", "apple",
    "nike", "adidas", "sephora", "ulta",
    "expedia", "booking", "airbnb",
    "wish", "shein", "temu",
    "dental", "medical", "veterinary", "healthcare",
    "mattress", "furniture", "appliance",
    "online", "website", "app",
]

# Default narrative keywords for analyzer.narrative_keyword_counts()
BNPL_NARRATIVE_KEYWORDS = [
    "denied", "refund", "fraud", "unauthorized",
    "interest", "fees", "late fee", "penalty",
    "credit report", "credit score", "collections",
    "autopay", "payment plan", "installment",
    "merchant", "returned", "canceled", "dispute",
    "customer service", "no response", "misleading",
]
