"""Scam-type signal definitions for CFPB narrative classification.

Categories derived from FBI IC3 2024 Internet Crime Report taxonomy
and FTC consumer fraud research. Designed for multi-label classification
where a single complaint can match multiple scam types.
"""

# For classify_scam_types() — multi-label scam classification
SCAM_TYPE_SIGNALS = {
    # Tier 1: Long-game extraction
    "pig_butchering": [
        "investment", "crypto", "bitcoin", "cryptocurrency",
        "trading platform", "guaranteed returns", "forex",
        "withdrawal fee", "wire transfer", "whatsapp",
        "telegram", "mining", "blockchain", "ethereum",
        "profit", "returns", "trading app",
    ],
    "romance_scam": [
        "dating", "relationship", "met online", "sent money",
        "emergency", "military", "overseas", "love",
        "dating site", "dating app", "romantic",
        "fell in love", "never met", "asked for money",
        "hospital", "stuck abroad", "plane ticket",
    ],

    # Tier 2: One-session extraction
    "tech_support": [
        "remote access", "screen share", "teamviewer",
        "anydesk", "virus", "malware", "microsoft",
        "pop-up", "tech support", "computer infected",
        "remote desktop", "logmein", "ultraviewer",
        "called about my computer", "your computer has",
    ],
    "impersonation": [
        "irs", "social security administration", "government",
        "law enforcement", "warrant", "arrest",
        "suspend", "legal action", "fbi", "dea",
        "marshal", "immigration", "deportation",
        "pretended to be", "claimed to be",
    ],
    "bank_impersonation": [
        "fraud department", "suspicious activity",
        "verify your account", "bank called",
        "transfer to safe account", "zelle",
        "fraud alert", "security department",
        "your account has been compromised",
        "temporary hold", "verify your identity",
    ],

    # Tier 3: Gift card extraction
    "gift_card": [
        "gift card", "itunes", "google play", "steam",
        "prepaid", "read the code", "activation",
        "scratched off", "drained", "balance gone",
        "apple gift card", "target gift card",
        "walmart gift card", "pay with gift card",
    ],

    # Tier 4: Credential harvesting
    "phishing": [
        "clicked link", "text message", "suspicious email",
        "verify", "login", "password", "phishing",
        "fake website", "toll", "unpaid",
        "clicked on", "entered my information",
        "fake email", "spoofed", "look like",
    ],
    "cloud_storage_scam": [
        "icloud", "storage full", "photos will be deleted",
        "cloud storage", "upgrade storage", "apple id",
        "verify apple", "account suspended", "google drive",
        "onedrive", "storage limit", "expired storage",
        "icloud storage", "photos deleted",
    ],
    "fake_charge_alert": [
        "charge of", "wasn't you", "call this number",
        "apple pay", "unauthorized purchase",
        "confirm this transaction", "did you authorize",
        "suspicious charge", "call to dispute",
        "text from bank", "reply yes or no",
        "confirm or deny", "did you make this",
    ],
    "identity_theft": [
        "opened account", "social security number",
        "applied for credit", "didn't authorize",
        "identity", "stolen", "new account",
        "credit report", "not mine", "someone opened",
        "identity theft", "ssn", "fraudulent account",
        "in my name", "without my knowledge",
    ],
}

# For response_patterns() — how companies respond to scam complaints
SCAM_RESPONSE_PATTERNS = {
    "investigation_concluded": [
        "investigation", "investigated", "concluded", "determined",
        "found that", "our records show", "records indicate",
    ],
    "denied_claim": [
        "denied", "decline", "not eligible", "unable to assist",
        "not responsible", "no liability", "denied my claim",
    ],
    "delay_runaround": [
        "no response", "never heard back", "waiting",
        "called multiple times", "called again", "still waiting",
        "months later", "weeks later", "run around", "runaround",
    ],
    "referred_to_law_enforcement": [
        "police report", "file a report", "law enforcement",
        "contact authorities", "report to police", "fbi",
        "identity theft report", "ftc report",
    ],
    "account_closed": [
        "account closed", "closed the account", "shut down",
        "terminated", "frozen", "suspended account",
    ],
    "refund_issued": [
        "refund", "reimbursed", "credited", "returned funds",
        "provisional credit", "temporary credit", "money back",
    ],
}

# Flat keyword list for narrative_keyword_counts()
SCAM_NARRATIVE_KEYWORDS = [
    "scam", "fraud", "scammer", "fraudulent",
    "remote access", "gift card", "wire transfer",
    "bitcoin", "crypto", "zelle", "venmo",
    "phishing", "spoofed", "impersonat",
    "identity theft", "unauthorized",
    "police report", "fbi", "ftc",
    "lost", "stolen", "drained",
    "refund", "denied", "investigation",
]
