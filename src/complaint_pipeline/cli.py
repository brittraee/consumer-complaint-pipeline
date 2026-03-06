"""CLI entry point for the consumer complaint pipeline.

Usage:
    complaint-pipeline cfpb fetch --output data/cfpb-complaints/
    complaint-pipeline cfpb analyze --input data/cfpb-complaints/ --output reports/
    complaint-pipeline sec fetch --output data/sec-filings/
    complaint-pipeline report compare --input data/cfpb-complaints/ --output reports/
"""

import logging
from pathlib import Path

import click

from complaint_pipeline.cfpb import client as cfpb_client
from complaint_pipeline.reports import markdown
from complaint_pipeline.sec import edgar


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """Consumer Complaint Pipeline — CFPB + SEC data pipeline."""
    _setup_logging(verbose)


# ---------- CFPB subcommands ----------

@main.group()
def cfpb() -> None:
    """CFPB complaint data commands."""


@cfpb.command()
@click.option(
    "--company",
    type=click.Choice(["incomm", "blackhawk", "all"], case_sensitive=False),
    default="all",
    help="Which company to fetch complaints for.",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("data/cfpb-complaints"),
    help="Output directory for CSV files.",
)
def fetch(company: str, output: Path) -> None:
    """Fetch complaint data from the CFPB API."""
    if company == "all":
        results = cfpb_client.fetch_all(output)
        for name, complaints in results.items():
            summary = markdown.company_summary(complaints, name.title())
            markdown.write_report(summary, output / f"{name}_summary.md")
        click.echo(f"Fetched complaints for {len(results)} companies to {output}/")
    else:
        search_terms = {"incomm": "InComm", "blackhawk": "Blackhawk"}
        term = search_terms[company]
        complaints = cfpb_client.fetch_complaints(term)
        cfpb_client.write_csv(complaints, output / f"{company}_complaints.csv")
        summary = markdown.company_summary(complaints, term)
        markdown.write_report(summary, output / f"{company}_summary.md")
        click.echo(f"Fetched {len(complaints)} complaints for {term}")


@cfpb.command()
@click.option(
    "--input", "-i", "input_dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/cfpb-complaints"),
    help="Directory containing complaint CSVs.",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("reports"),
    help="Output directory for analysis reports.",
)
def analyze(input_dir: Path, output: Path) -> None:
    """Analyze downloaded CFPB complaint data."""
    incomm = cfpb_client.load_complaints_csv(input_dir / "incomm_complaints.csv")
    bhn = cfpb_client.load_complaints_csv(input_dir / "blackhawk_complaints.csv")

    if not incomm and not bhn:
        click.echo("No complaint data found. Run 'complaint-pipeline cfpb fetch' first.")
        raise SystemExit(1)

    click.echo(f"Loaded {len(incomm)} InComm, {len(bhn)} Blackhawk complaints")

    report = markdown.comparison_report(incomm, bhn)
    report_path = output / "cfpb_comparison.md"
    markdown.write_report(report, report_path)
    click.echo(f"Comparison report: {report_path}")


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
    categories = list(SCAM_TYPE_SIGNALS.keys())
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


# ---------- SEC subcommands ----------

@main.group()
def sec() -> None:
    """SEC EDGAR filing commands."""


@sec.command("fetch")
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("data/sec-filings"),
    help="Output directory for filing data.",
)
def sec_fetch(output: Path) -> None:
    """Fetch Pathward Financial SEC filings from EDGAR."""
    results = edgar.fetch_pathward(output)

    # Write reports
    if results["insider"]:
        report = markdown.insider_trading_report(results["insider"])
        markdown.write_report(report, output / "pathward_insider_trading.md")

    summary = markdown.sec_summary_report(
        company_name=results["company_name"],
        cik=results["cik"],
        amended=results["amended"],
        insider=results["insider"],
        regular=results["regular"],
    )
    markdown.write_report(summary, output / "pathward_filing_summary.md")

    click.echo(
        f"Fetched {len(results['amended'])} amended, "
        f"{len(results['insider'])} insider, "
        f"{len(results['regular'])} regular filings"
    )


# ---------- Report subcommands ----------

@main.group()
def report() -> None:
    """Report generation commands."""


@report.command()
@click.option(
    "--input", "-i", "input_dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/cfpb-complaints"),
    help="Directory containing complaint CSVs.",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("reports"),
    help="Output directory for reports.",
)
def compare(input_dir: Path, output: Path) -> None:
    """Generate InComm vs Blackhawk comparison report."""
    incomm = cfpb_client.load_complaints_csv(input_dir / "incomm_complaints.csv")
    bhn = cfpb_client.load_complaints_csv(input_dir / "blackhawk_complaints.csv")

    if not incomm and not bhn:
        click.echo("No complaint data found. Run 'complaint-pipeline cfpb fetch' first.")
        raise SystemExit(1)

    click.echo(f"Comparing {len(incomm)} InComm vs {len(bhn)} Blackhawk complaints")

    report_text = markdown.comparison_report(incomm, bhn)
    report_path = output / "cfpb_comparison.md"
    markdown.write_report(report_text, report_path)
    click.echo(f"Report written to {report_path}")
