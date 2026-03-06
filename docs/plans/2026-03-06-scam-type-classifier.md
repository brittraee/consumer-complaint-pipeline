# Scam-Type Classifier Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a multi-label scam-type classifier that categorizes CFPB complaint narratives into 10 scam types with co-occurrence tracking.

**Architecture:** New `scam_signals.py` signal dictionary (same pattern as `bnpl_signals.py`) + new `classify_scam_types()` function in `narrative.py` supporting multi-label output. CLI command and markdown report for output.

**Tech Stack:** Python, Click, existing complaint_pipeline infrastructure. No new dependencies.

**Design doc:** `docs/plans/2026-03-06-scam-type-classifier-design.md`

---

### Task 1: Signal Dictionary — `scam_signals.py`

**Files:**
- Create: `src/complaint_pipeline/cfpb/scam_signals.py`
- Test: `tests/test_scam_signals.py`

**Step 1: Write the failing test — signal definition structure**

Create `tests/test_scam_signals.py`:

```python
"""Tests for scam-type signal definitions and multi-label classifier."""

from complaint_pipeline.cfpb.scam_signals import (
    SCAM_TYPE_SIGNALS,
    SCAM_RESPONSE_PATTERNS,
    SCAM_NARRATIVE_KEYWORDS,
)
from complaint_pipeline.models import Complaint


def _complaint(narrative="", **kwargs):
    """Helper to create a Complaint with narrative text."""
    return Complaint(narrative=narrative, **kwargs)


class TestScamSignalDefinitions:
    def test_type_signals_has_expected_keys(self):
        expected = {
            "pig_butchering", "romance_scam", "tech_support",
            "impersonation", "bank_impersonation", "gift_card",
            "phishing", "cloud_storage_scam", "fake_charge_alert",
            "identity_theft",
        }
        assert set(SCAM_TYPE_SIGNALS.keys()) == expected

    def test_response_patterns_has_expected_keys(self):
        expected = {
            "investigation_concluded", "denied_claim",
            "delay_runaround", "referred_to_law_enforcement",
            "account_closed", "refund_issued",
        }
        assert set(SCAM_RESPONSE_PATTERNS.keys()) == expected

    def test_narrative_keywords_is_nonempty_list(self):
        assert isinstance(SCAM_NARRATIVE_KEYWORDS, list)
        assert len(SCAM_NARRATIVE_KEYWORDS) > 10

    def test_all_signal_values_are_lists_of_strings(self):
        for signals in [SCAM_TYPE_SIGNALS, SCAM_RESPONSE_PATTERNS]:
            for key, value in signals.items():
                assert isinstance(value, list), f"{key} should be a list"
                for item in value:
                    assert isinstance(item, str), f"{key} items should be strings"

    def test_each_category_has_at_least_5_keywords(self):
        for cat, keywords in SCAM_TYPE_SIGNALS.items():
            assert len(keywords) >= 5, f"{cat} needs at least 5 keywords, has {len(keywords)}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scam_signals.py::TestScamSignalDefinitions -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'complaint_pipeline.cfpb.scam_signals'`

**Step 3: Write the signal dictionary**

Create `src/complaint_pipeline/cfpb/scam_signals.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scam_signals.py::TestScamSignalDefinitions -v`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add src/complaint_pipeline/cfpb/scam_signals.py tests/test_scam_signals.py
git commit -m "Add scam-type signal definitions with tests"
```

---

### Task 2: Multi-Label Classifier — `classify_scam_types()`

**Files:**
- Modify: `src/complaint_pipeline/cfpb/narrative.py` (add function after line 317)
- Test: `tests/test_scam_signals.py` (append new test classes)

**Step 1: Write the failing tests — classification behavior**

Append to `tests/test_scam_signals.py`:

```python
from complaint_pipeline.cfpb.narrative import classify_scam_types


class TestClassifyScamTypes:
    def test_single_category_match(self):
        complaints = [_complaint(
            "they called about my computer has virus and used remote access to get into teamviewer"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["tech_support"] >= 1

    def test_multi_label_match(self):
        """A complaint about a fake charge leading to remote access should hit both categories."""
        complaints = [_complaint(
            "got a text saying unauthorized purchase charge of $499 call this number. "
            "They had me download anydesk for remote access to fix the problem."
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["fake_charge_alert"] >= 1
        assert result["tech_support"] >= 1
        assert result["multi_label_count"] >= 1

    def test_unclassified_below_threshold(self):
        complaints = [_complaint("I have a general problem with my account")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["unclassified"] == 1

    def test_threshold_of_one(self):
        """With threshold=1, a single keyword match should classify."""
        complaints = [_complaint("something about bitcoin")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS, threshold=1)
        assert result["pig_butchering"] == 1

    def test_threshold_default_requires_two(self):
        """Default threshold=2 means single keyword match is not enough."""
        complaints = [_complaint("something about bitcoin")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["pig_butchering"] == 0
        assert result["unclassified"] == 1

    def test_co_occurrences_tracked(self):
        complaints = [_complaint(
            "they impersonated the irs and claimed warrant for arrest, "
            "told me to buy gift card itunes and read the code"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["co_occurrences"][("gift_card", "impersonation")] == 1 or \
               result["co_occurrences"][("impersonation", "gift_card")] == 1

    def test_empty_input(self):
        result = classify_scam_types([], signals=SCAM_TYPE_SIGNALS)
        assert result["total"] == 0
        assert result["unclassified"] == 0

    def test_percentages_included(self):
        complaints = [
            _complaint("remote access virus teamviewer computer infected tech support"),
            _complaint("just a normal complaint"),
        ]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "tech_support_pct" in result
        assert result["total"] == 2

    def test_skips_empty_narratives(self):
        complaints = [_complaint(""), _complaint("remote access virus teamviewer tech support")]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["total"] == 1


class TestClassifyScamTypesPerCategory:
    """One test per scam category to verify classification works."""

    def test_pig_butchering(self):
        complaints = [_complaint(
            "met someone on whatsapp who showed me a trading platform for crypto bitcoin investment"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["pig_butchering"] >= 1

    def test_romance_scam(self):
        complaints = [_complaint(
            "met online on dating site, fell in love, asked for money for emergency overseas"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["romance_scam"] >= 1

    def test_tech_support(self):
        complaints = [_complaint(
            "pop-up said computer infected with virus, called tech support, they used remote access"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["tech_support"] >= 1

    def test_impersonation(self):
        complaints = [_complaint(
            "called claiming to be irs, said warrant for arrest, threatened legal action"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["impersonation"] >= 1

    def test_bank_impersonation(self):
        complaints = [_complaint(
            "fraud department called about suspicious activity, said verify your account via zelle"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["bank_impersonation"] >= 1

    def test_gift_card(self):
        complaints = [_complaint(
            "told to buy apple gift card itunes, scratched off and read the code over the phone"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["gift_card"] >= 1

    def test_phishing(self):
        complaints = [_complaint(
            "got suspicious email that looked like my bank, clicked link to fake website, entered my information and password"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["phishing"] >= 1

    def test_cloud_storage_scam(self):
        complaints = [_complaint(
            "got text saying icloud storage full and photos will be deleted, asked to upgrade storage and verify apple id"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["cloud_storage_scam"] >= 1

    def test_fake_charge_alert(self):
        complaints = [_complaint(
            "text saying apple pay charge of $499 wasn't you call this number to dispute suspicious charge"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["fake_charge_alert"] >= 1

    def test_identity_theft(self):
        complaints = [_complaint(
            "someone opened a new account in my name using my social security number without my knowledge"
        )]
        result = classify_scam_types(complaints, signals=SCAM_TYPE_SIGNALS)
        assert result["identity_theft"] >= 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scam_signals.py::TestClassifyScamTypes -v`
Expected: FAIL with `ImportError: cannot import name 'classify_scam_types'`

**Step 3: Implement `classify_scam_types()` in `narrative.py`**

Add after line 317 (after `_classify_custom_signals`), before the geographic clustering section:

```python
def classify_scam_types(
    complaints: list[Complaint],
    signals: dict[str, list[str]] | None = None,
    threshold: int = 2,
) -> dict[str, int | float | dict]:
    """Multi-label scam-type classifier with co-occurrence tracking.

    Unlike classify_fraud_type() which picks a single winner, this assigns
    ALL categories that meet the keyword match threshold. A complaint about
    a fake charge alert leading to remote access scores in both categories.

    Args:
        complaints: List of complaints to classify.
        signals: Dict of {category: [keywords]}. Required.
        threshold: Minimum keyword matches to assign a category (default: 2).

    Returns dict with per-category counts, co-occurrence pairs,
    and multi-label statistics.
    """
    if signals is None:
        signals = {}

    categories = list(signals.keys())
    counts = {cat: 0 for cat in categories}
    counts["unclassified"] = 0
    co_occurrences: Counter[tuple[str, ...]] = Counter()
    total = 0
    multi_label_count = 0

    for c in complaints:
        if not c.narrative:
            continue
        total += 1
        text = c.narrative.lower()

        scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in signals.items()}
        matched = sorted(cat for cat, score in scores.items() if score >= threshold)

        if not matched:
            counts["unclassified"] += 1
        else:
            for cat in matched:
                counts[cat] += 1
            if len(matched) > 1:
                multi_label_count += 1
                # Track all pairs of co-occurring categories
                for i in range(len(matched)):
                    for j in range(i + 1, len(matched)):
                        co_occurrences[(matched[i], matched[j])] += 1

    result: dict[str, int | float | dict] = {
        "total": total,
        "unclassified": counts["unclassified"],
        "multi_label_count": multi_label_count,
        "multi_label_pct": round(100 * multi_label_count / total, 1) if total > 0 else 0,
        "co_occurrences": dict(co_occurrences.most_common()),
    }
    for cat in categories:
        result[cat] = counts[cat]
        result[f"{cat}_pct"] = round(100 * counts[cat] / total, 1) if total > 0 else 0

    return result
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scam_signals.py -v`
Expected: ALL PASS

**Step 5: Run full test suite to check nothing broke**

Run: `pytest -v`
Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add src/complaint_pipeline/cfpb/narrative.py tests/test_scam_signals.py
git commit -m "Add multi-label scam-type classifier with co-occurrence tracking"
```

---

### Task 3: Scam Report Generation

**Files:**
- Modify: `src/complaint_pipeline/reports/markdown.py` (add function after line 280)
- Test: `tests/test_scam_signals.py` (append report test)

**Step 1: Write the failing test**

Append to `tests/test_scam_signals.py`:

```python
from complaint_pipeline.reports.markdown import generate_scam_report


class TestGenerateScamReport:
    def test_report_contains_header(self):
        complaints = [
            _complaint("remote access virus teamviewer computer infected tech support pop-up"),
            _complaint("icloud storage full photos will be deleted upgrade storage verify apple id"),
            _complaint("general complaint about something"),
        ]
        report = generate_scam_report(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "# Scam-Type Classification Report" in report
        assert "Total Complaints Analyzed" in report

    def test_report_contains_category_table(self):
        complaints = [
            _complaint("remote access virus teamviewer computer infected tech support pop-up"),
        ]
        report = generate_scam_report(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "| Category |" in report
        assert "tech_support" in report

    def test_report_contains_co_occurrences(self):
        complaints = [_complaint(
            "irs warrant arrest impersonation legal action "
            "told to buy gift card itunes read the code scratched off"
        )]
        report = generate_scam_report(complaints, signals=SCAM_TYPE_SIGNALS)
        assert "Co-Occurrence" in report

    def test_report_empty_input(self):
        report = generate_scam_report([], signals=SCAM_TYPE_SIGNALS)
        assert "No complaints" in report
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scam_signals.py::TestGenerateScamReport -v`
Expected: FAIL with `ImportError: cannot import name 'generate_scam_report'`

**Step 3: Implement `generate_scam_report()`**

Add to `src/complaint_pipeline/reports/markdown.py` before `write_report()` (before line 282):

```python
def generate_scam_report(
    complaints: list[Complaint],
    signals: dict[str, list[str]],
    threshold: int = 2,
) -> str:
    """Generate a scam-type classification report.

    Runs classify_scam_types() and formats results as Markdown with
    category breakdown, co-occurrence matrix, and example excerpts.
    """
    from complaint_pipeline.cfpb.narrative import classify_scam_types

    lines = [
        "# Scam-Type Classification Report",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total Complaints Analyzed**: {len(complaints)}",
        f"**Threshold**: {threshold} keyword matches",
        "",
    ]

    if not complaints:
        lines.append("No complaints to classify.")
        return "\n".join(lines)

    result = classify_scam_types(complaints, signals=signals, threshold=threshold)

    # Summary stats
    lines.extend([
        "## Summary",
        "",
        f"- **Classified**: {result['total'] - result['unclassified']} / {result['total']}",
        f"- **Unclassified**: {result['unclassified']}",
        f"- **Multi-label**: {result['multi_label_count']} ({result['multi_label_pct']}%)",
        "",
    ])

    # Category breakdown table
    categories = [k for k in signals.keys()]
    lines.extend([
        "## Category Breakdown",
        "",
        "| Category | Count | % |",
        "|----------|-------|---|",
    ])
    for cat in sorted(categories, key=lambda c: result.get(c, 0), reverse=True):
        count = result.get(cat, 0)
        pct = result.get(f"{cat}_pct", 0)
        lines.append(f"| {cat} | {count} | {pct}% |")
    lines.extend([
        f"| unclassified | {result['unclassified']} | "
        f"{round(100 * result['unclassified'] / result['total'], 1) if result['total'] > 0 else 0}% |",
        "",
    ])

    # Co-occurrence section
    co = result.get("co_occurrences", {})
    if co:
        lines.extend([
            "## Co-Occurrence Patterns",
            "",
            "Complaints matching multiple scam categories — shows how tactics chain together.",
            "",
            "| Category A | Category B | Count |",
            "|------------|------------|-------|",
        ])
        for (cat_a, cat_b), count in sorted(co.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat_a} | {cat_b} | {count} |")
        lines.append("")

    # Example excerpts per category (top 3 per category, truncated)
    lines.extend([
        "## Example Narratives",
        "",
    ])
    for cat in sorted(categories, key=lambda c: result.get(c, 0), reverse=True):
        if result.get(cat, 0) == 0:
            continue
        lines.append(f"### {cat}")
        lines.append("")
        examples = 0
        for c in complaints:
            if not c.narrative or examples >= 3:
                break
            text = c.narrative.lower()
            score = sum(1 for kw in signals[cat] if kw in text)
            if score >= threshold:
                excerpt = c.narrative[:200].replace("\n", " ")
                if len(c.narrative) > 200:
                    excerpt += "..."
                lines.append(f"> {excerpt}")
                lines.append("")
                examples += 1

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scam_signals.py::TestGenerateScamReport -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/complaint_pipeline/reports/markdown.py tests/test_scam_signals.py
git commit -m "Add scam-type classification report generation"
```

---

### Task 4: CLI Command — `classify-scams`

**Files:**
- Modify: `src/complaint_pipeline/cli.py` (add command after `analyze` at line 100)

**Step 1: Write the failing test**

Append to `tests/test_scam_signals.py`:

```python
from click.testing import CliRunner
from complaint_pipeline.cli import main


class TestClassifyScamsCli:
    def test_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["cfpb", "classify-scams", "--help"])
        assert result.exit_code == 0
        assert "Classify complaint narratives" in result.output

    def test_no_data_shows_error(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, [
            "cfpb", "classify-scams",
            "--input", str(tmp_path),
        ])
        assert "No complaint data found" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scam_signals.py::TestClassifyScamsCli -v`
Expected: FAIL with `Usage: main cfpb [OPTIONS] COMMAND` (no classify-scams command)

**Step 3: Implement the CLI command**

Add to `src/complaint_pipeline/cli.py` after the `analyze` command (after line 100), before the SEC subcommands section:

```python
@cfpb.command("classify-scams")
@click.option(
    "--input", "-i", "input_dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/cfpb-complaints"),
    help="Directory containing complaint CSVs.",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for classification report.",
)
@click.option(
    "--threshold", "-t",
    type=int,
    default=2,
    help="Minimum keyword matches per category (default: 2).",
)
def classify_scams(input_dir: Path, output: Path | None, threshold: int) -> None:
    """Classify complaint narratives by scam type."""
    from complaint_pipeline.cfpb.narrative import classify_scam_types
    from complaint_pipeline.cfpb.scam_signals import SCAM_TYPE_SIGNALS
    from complaint_pipeline.reports.markdown import generate_scam_report

    # Load all CSVs from input directory
    csv_files = list(input_dir.glob("*_complaints.csv"))
    if not csv_files:
        click.echo("No complaint data found. Run 'complaint-pipeline cfpb fetch' first.")
        raise SystemExit(1)

    all_complaints = []
    for csv_file in csv_files:
        complaints = cfpb_client.load_complaints_csv(csv_file)
        all_complaints.extend(complaints)
        click.echo(f"Loaded {len(complaints)} complaints from {csv_file.name}")

    click.echo(f"\nClassifying {len(all_complaints)} total complaints (threshold={threshold})...")

    result = classify_scam_types(all_complaints, signals=SCAM_TYPE_SIGNALS, threshold=threshold)

    # Print summary table
    click.echo(f"\n{'Category':<25} {'Count':>6} {'%':>7}")
    click.echo("-" * 40)
    categories = [k for k in SCAM_TYPE_SIGNALS.keys()]
    for cat in sorted(categories, key=lambda c: result.get(c, 0), reverse=True):
        count = result.get(cat, 0)
        pct = result.get(f"{cat}_pct", 0)
        if count > 0:
            click.echo(f"{cat:<25} {count:>6} {pct:>6.1f}%")
    click.echo(f"{'unclassified':<25} {result['unclassified']:>6}")
    click.echo(f"\nMulti-label: {result['multi_label_count']} ({result['multi_label_pct']}%)")

    # Co-occurrences
    co = result.get("co_occurrences", {})
    if co:
        click.echo(f"\nTop co-occurrences:")
        for (a, b), count in list(co.items())[:10]:
            click.echo(f"  {a} + {b}: {count}")

    # Write report if output specified
    if output:
        report = generate_scam_report(all_complaints, signals=SCAM_TYPE_SIGNALS, threshold=threshold)
        report_path = output / "scam_classification.md"
        markdown.write_report(report, report_path)
        click.echo(f"\nReport written to {report_path}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scam_signals.py::TestClassifyScamsCli -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/complaint_pipeline/cli.py tests/test_scam_signals.py
git commit -m "Add classify-scams CLI command"
```

---

### Task 5: Integration Test & Final Verification

**Step 1: Run full test suite**

Run: `pytest -v --tb=short`
Expected: All tests pass, no regressions

**Step 2: Verify CLI help output**

Run: `cd ~/Sync/Work/portfolio/consumer-complaint-pipeline && uv run complaint-pipeline cfpb --help`
Expected: `classify-scams` appears in the command list

**Step 3: Verify import chain**

Run:
```bash
uv run python -c "
from complaint_pipeline.cfpb.scam_signals import SCAM_TYPE_SIGNALS
from complaint_pipeline.cfpb.narrative import classify_scam_types
from complaint_pipeline.reports.markdown import generate_scam_report
print(f'{len(SCAM_TYPE_SIGNALS)} scam categories loaded')
print('All imports OK')
"
```
Expected: `10 scam categories loaded` and `All imports OK`

**Step 4: Final commit if any cleanup needed**

```bash
git status
# Only commit if there are changes
```
