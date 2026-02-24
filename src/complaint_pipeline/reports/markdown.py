"""Markdown report generation.

Refactored from: generate_summary() in cfpb_complaint_pull.py
                  generate_comparison_report() in complaint_analysis.py
                  analyze_insider_trading() in sec_filing_analysis.py

Principle: SEPARATE CONCERNS
Fetching, analyzing, and reporting are three different jobs.
This module only knows how to format results as Markdown.
"""

from datetime import datetime
from pathlib import Path

from complaint_pipeline.cfpb import analyzer
from complaint_pipeline.models import Complaint, Filing


def company_summary(complaints: list[Complaint], company_label: str) -> str:
    """Generate a single-company CFPB complaint summary."""
    lines = [
        f"# CFPB Complaint Summary: {company_label}",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total complaints**: {len(complaints)}",
        "",
    ]

    if not complaints:
        lines.append("No complaints found.")
        return "\n".join(lines)

    # Companies in results
    companies = analyzer.company_breakdown(complaints)
    lines.append("## Companies in Results")
    for co, count in companies:
        lines.append(f"- {co}: {count}")
    lines.append("")

    # Date range
    dr = analyzer.date_range(complaints)
    if dr:
        lines.append(f"**Date range**: {dr[0]} to {dr[1]}")
        lines.append("")

    # Yearly breakdown
    years = analyzer.yearly_breakdown(complaints)
    if years:
        lines.append("## Complaints by Year")
        lines.append("")
        lines.append("| Year | Count |")
        lines.append("|------|-------|")
        for year, count in years.items():
            lines.append(f"| {year} | {count} |")
        lines.append("")

    # Products
    products = analyzer.product_breakdown(complaints)
    if products:
        lines.append("## By Product")
        for product, count in products:
            lines.append(f"- {product}: {count}")
        lines.append("")

    # Top issues
    issues = analyzer.issue_analysis(complaints)
    if issues:
        lines.append("## Top Issues")
        for issue, count in issues[:15]:
            lines.append(f"- {issue}: {count}")
        lines.append("")

    # Company responses
    responses = analyzer.response_analysis(complaints)
    if responses:
        lines.append("## Company Response Breakdown")
        lines.append("")
        lines.append("| Response | Count | % |")
        lines.append("|----------|-------|---|")
        for resp, count in responses:
            pct = 100 * count / len(complaints)
            lines.append(f"| {resp} | {count} | {pct:.1f}% |")
        lines.append("")

    # Relief rates
    relief = analyzer.monetary_relief_rate(complaints)
    r_rate = f"{relief['relief']}/{relief['total']} ({relief['relief_pct']}%)"
    e_rate = f"{relief['explanation']}/{relief['total']} ({relief['explanation_pct']}%)"
    t_rate = f"{relief['timely']}/{relief['total']} ({relief['timely_pct']}%)"
    lines.append(f"**Monetary Relief Rate**: {r_rate}")
    lines.append(f"**Closed with Explanation**: {e_rate}")
    lines.append(f"**Timely Response Rate**: {t_rate}")
    lines.append("")

    # Top states
    geo = analyzer.geographic_analysis(complaints)
    if geo:
        lines.append("## Top 10 States")
        for state, count in geo[:10]:
            lines.append(f"- {state}: {count}")
        lines.append("")

    # Narrative keywords
    narratives = [c for c in complaints if c.narrative]
    if narratives:
        lines.append(f"## Narrative Analysis ({len(narratives)} narratives available)")
        lines.append("")
        kw_counts = analyzer.narrative_keyword_counts(complaints)
        lines.append("| Keyword | Count | % of Narratives |")
        lines.append("|---------|-------|-----------------|")
        for kw, count in kw_counts.items():
            pct = 100 * count / len(narratives) if narratives else 0
            lines.append(f"| {kw} | {count} | {pct:.1f}% |")
        lines.append("")

    return "\n".join(lines)


def comparison_report(
    incomm: list[Complaint],
    bhn: list[Complaint],
) -> str:
    """Generate InComm vs Blackhawk comparison report."""
    lines = [
        "# CFPB Complaint Comparison: InComm vs Blackhawk Network",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Overview",
        "",
        "| Metric | InComm Financial Services | Blackhawk Network |",
        "|--------|---------------------------|-------------------|",
        f"| Total Complaints | {len(incomm)} | {len(bhn)} |",
    ]

    # Date ranges
    for name, records in [("InComm", incomm), ("BHN", bhn)]:
        dr = analyzer.date_range(records)
        if dr:
            lines.append(f"| Date Range ({name}) | {dr[0]} to {dr[1]} | |")

    # InComm section
    lines.extend(["", "## InComm Financial Services", ""])
    _add_company_analysis(lines, incomm)

    # BHN section
    lines.extend(["---", "", "## Blackhawk Network", ""])
    _add_company_analysis(lines, bhn)

    # Key findings
    lines.extend(["---", "", "## Key Findings", ""])
    lines.append(
        f"1. **Volume ratio**: InComm receives {len(incomm)} "
        f"complaints vs BHN's {len(bhn)}"
    )
    if incomm and bhn:
        ratio = len(incomm) / len(bhn) if len(bhn) > 0 else float("inf")
        lines.append(f"   - InComm has **{ratio:.1f}x** more complaints than BHN")

    incomm_relief = analyzer.monetary_relief_rate(incomm)
    bhn_relief = analyzer.monetary_relief_rate(bhn)
    lines.append(
        f"2. **Monetary relief rate**: InComm {incomm_relief['relief_pct']}% "
        f"vs BHN {bhn_relief['relief_pct']}%"
    )

    lines.extend([
        "",
        "## Methodology",
        "- Data source: CFPB Consumer Complaint Database API",
        "- Complaints are self-selected; disproportionately represent negative experiences",
        "- Volume differences may partly reflect market share differences",
        "- Company response categories defined by CFPB, not by the companies",
    ])

    return "\n".join(lines)


def _add_company_analysis(lines: list[str], complaints: list[Complaint]) -> None:
    """Add analysis sections for one company (helper to avoid duplication)."""
    monthly = analyzer.monthly_timeseries(complaints)
    if monthly:
        lines.append("### Monthly Complaint Volume")
        lines.append("")
        lines.append("| Month | Count |")
        lines.append("|-------|-------|")
        for month, count in monthly.items():
            lines.append(f"| {month} | {count} |")
        lines.append("")

    issues = analyzer.issue_analysis(complaints)
    if issues:
        lines.append("### Top Issues")
        lines.append("")
        for issue, count in issues[:10]:
            lines.append(f"- {issue}: {count}")
        lines.append("")

    responses = analyzer.response_analysis(complaints)
    if responses:
        lines.append("### Company Responses")
        lines.append("")
        for resp, count in responses:
            pct = 100 * count / len(complaints) if complaints else 0
            lines.append(f"- {resp}: {count} ({pct:.1f}%)")
        lines.append("")

    geo = analyzer.geographic_analysis(complaints)
    if geo:
        lines.append("### Top States")
        lines.append("")
        for state, count in geo[:10]:
            lines.append(f"- {state}: {count}")
        lines.append("")

    dispute = analyzer.disputed_rate(complaints)
    lines.append(f"### Consumer Dispute Rate: {dispute['dispute_rate_pct']}%")
    lines.append("")


def insider_trading_report(filings: list[Filing]) -> str:
    """Generate Form 4 insider transaction analysis report."""
    lines = [
        "# Pathward Financial — Form 4 Insider Transaction Analysis",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Insider Transactions",
        "",
        "| Filing Date | Accession | Document |",
        "|-------------|-----------|----------|",
    ]
    for f in filings:
        doc_link = f"[{f.primary_document}]({f.url})"
        lines.append(f"| {f.filing_date} | {f.accession_number} | {doc_link} |")

    lines.extend([
        "",
        f"**Total Form 4 filings found**: {len(filings)}",
        "",
        "## Key Dates for Cross-Reference",
        "- 2025-05-12: Form 12b-25 (late filing) for Q2 FY2025 10-Q",
        "- 2025-05-22: First Nasdaq deficiency notice",
        "- 2025-08-11: Second Form 12b-25 for Q3 FY2025 10-Q",
        "- 2025-08-26: Second Nasdaq deficiency notice",
        "- 2025-08-29: 10-K/A restating FY2024",
        "- 2025-09-03: 10-Q/A restating Q1 FY2025",
        "",
        "**Analysis**: Cross-reference Form 4 filing dates above with these key dates.",
        "Look for transaction patterns in the 30-60 days prior to restatement disclosures.",
    ])
    return "\n".join(lines)


def sec_summary_report(
    company_name: str,
    cik: str,
    amended: list[Filing],
    insider: list[Filing],
    regular: list[Filing],
) -> str:
    """Generate SEC filing summary report."""
    lines = [
        f"# {company_name} (CASH) — SEC Filing Summary",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Company**: {company_name}",
        f"**CIK**: {cik}",
        "",
        "## Amended Filings",
        "",
    ]
    for f in amended:
        lines.append(f"- **{f.form_type}** ({f.filing_date}): [{f.primary_document}]({f.url})")

    lines.extend([
        "",
        f"## Insider Transactions: {len(insider)} Form 4 filings",
        f"## Regular Filings: {len(regular)} 10-K/10-Q filings",
        "",
        "## Key Restatement Timeline",
        "- 2025-05-12: Form 12b-25 (late Q2 FY2025 10-Q)",
        "- 2025-05-22: First Nasdaq deficiency",
        "- 2025-08-11: Second Form 12b-25 (late Q3 FY2025 10-Q)",
        "- 2025-08-26: Second Nasdaq deficiency",
        "- 2025-08-29: 10-K/A (FY2024 restatement)",
        "- 2025-09-03: 10-Q/A (Q1 FY2025 restatement)",
        "- 2025-11-13: Nasdaq compliance deadline",
        "",
        "See pathward_insider_trading.md for Form 4 cross-reference analysis.",
    ])
    return "\n".join(lines)


def write_report(content: str, filepath: Path) -> None:
    """Write a report string to a file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
