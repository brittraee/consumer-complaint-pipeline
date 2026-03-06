# Scam-Type Classifier Design

**Date:** 2026-03-06
**Status:** Approved

## Goal

Add a multi-label scam-type classifier to consumer-complaint-pipeline. Classifies CFPB complaint narratives into scam categories derived from FBI IC3/FTC/FCC research. Serves dual purpose: functional analysis tool and portfolio piece.

## Approach

Approach B — Enhanced classifier with multi-label support. Uses the existing pluggable signal dictionary pattern (`bnpl_signals.py`) with one new classification function that supports multi-label output and co-occurrence tracking.

## Scam Categories (10)

| Category | Tier | Description |
|----------|------|-------------|
| `pig_butchering` | 1 - Long-game | Investment/crypto fraud with relationship buildup |
| `romance_scam` | 1 - Long-game | Dating/relationship-based money extraction |
| `tech_support` | 2 - One-session | Remote access, fake virus alerts |
| `impersonation` | 2 - One-session | Government agency impersonation (IRS, SSA, FBI) |
| `bank_impersonation` | 2 - One-session | Fraud department calls, "transfer to safe account" |
| `gift_card` | 3 - Extraction | Gift card purchase and code reading |
| `phishing` | 4 - Credential | Generic link/email credential harvesting |
| `cloud_storage_scam` | 4 - Credential | iCloud/Google storage full, photos will be deleted |
| `fake_charge_alert` | 4 - Credential | Fake Apple Pay/bank charge, "call this number" |
| `identity_theft` | 4 - Credential | Unauthorized accounts, stolen SSN |

## New Files

### `src/complaint_pipeline/cfpb/scam_signals.py`

Signal dictionaries following `bnpl_signals.py` pattern:
- `SCAM_TYPE_SIGNALS` — category → keyword list for `classify_scam_types()`
- `SCAM_RESPONSE_PATTERNS` — company response keyword groups
- `SCAM_NARRATIVE_KEYWORDS` — flat keyword list for general counting

### New function in `narrative.py`

```python
def classify_scam_types(
    complaints: list[Complaint],
    signals: dict[str, list[str]] | None = None,
    threshold: int = 2,
) -> dict:
```

- Multi-label: returns all categories meeting threshold (2+ keyword matches)
- Complaints matching nothing → `"unclassified"`
- Output includes per-category counts, co-occurrence pairs, and multi-label stats

Output structure:
```python
{
    "tech_support": 47,
    "fake_charge_alert": 31,
    ...
    "unclassified": 12,
    "co_occurrences": {
        ("fake_charge_alert", "tech_support"): 18,
        ...
    },
    "total": 200,
    "multi_label_count": 42,
    "multi_label_pct": 21.0,
}
```

### New CLI command

```
complaint-pipeline cfpb classify-scams --input data/cfpb-complaints/ --output reports/
```

Loads CSVs, runs classifier, prints summary to terminal, writes markdown report if `--output` provided.

### New function in `reports/markdown.py`

`generate_scam_report()` — category breakdown table, co-occurrence matrix, top example narrative excerpts per category.

## Tests

Following `test_bnpl_signals.py` patterns:
- One test per category with crafted narrative
- Multi-label test (narrative hitting two categories)
- Threshold test (single match below threshold → unclassified)
- Co-occurrence counting test
- Empty input → empty results
- Uses `_complaint()` helper factory

## Files Changed

| File | Change |
|------|--------|
| `cfpb/scam_signals.py` | New — signal dictionaries |
| `cfpb/narrative.py` | Add `classify_scam_types()` |
| `cli.py` | Add `classify-scams` subcommand |
| `reports/markdown.py` | Add `generate_scam_report()` |
| `tests/test_scam_signals.py` | New — classifier tests |
