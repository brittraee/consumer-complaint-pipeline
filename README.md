# Consumer Complaint Pipeline

A Python data pipeline for analyzing consumer complaint patterns using the CFPB and SEC EDGAR public APIs. Fetches complaint data, mines narrative text for patterns, and generates comparison reports — with a Click CLI for reproducible data collection.

## Technical Highlights

- **Dual-API data pipeline** — Fetches CFPB consumer complaints and SEC EDGAR filings via `httpx` with proper User-Agent handling and error recovery
- **Text mining engine** — Regex-based extraction of dollar amounts, dates, retailer mentions, and timing patterns from unstructured complaint narratives
- **Keyword-scoring classifier** — Categorizes complaints by type, timing, and geographic clustering using configurable signal definitions
- **Pluggable signal definitions** — Swap keyword dictionaries (e.g., BNPL signals) to analyze different complaint domains with the same pipeline
- **Markdown report generation** — Auto-generates comparison reports with timeseries, geographic breakdowns, and response analysis
- **Click CLI** — Subcommands for fetch, analyze, and report with `--help` generation and path validation

## Architecture

```
CFPB API ──► cfpb/client.py ──► Complaint dataclass ──► cfpb/analyzer.py ──┐
                                                        cfpb/narrative.py ──┤
SEC EDGAR ──► sec/edgar.py ──► Filing dataclass ────────────────────────────┤
                                                                            ▼
                                                        reports/markdown.py ──► .md reports
                                                              ▲
                                                         cli.py (Click)
```

## Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| HTTP | httpx (async-capable, typed responses) |
| Data Models | dataclasses with factory methods |
| Text Mining | re (regex), collections.Counter |
| CLI | Click (subcommands, options, help generation) |
| Reports | Markdown generation |
| Build | hatchling (PEP 517) |
| Visualization | matplotlib (Jupyter notebooks) |
| Testing | pytest (86 tests) |
| Linting | Ruff |

## Project Structure

```
consumer-complaint-pipeline/
├── src/complaint_pipeline/
│   ├── models.py              # Complaint + Filing dataclasses
│   ├── cli.py                 # Click CLI entry point
│   ├── cfpb/
│   │   ├── client.py          # CFPB API client (httpx, CSV I/O)
│   │   ├── analyzer.py        # Pure analysis functions
│   │   ├── narrative.py       # Text mining + pattern classification
│   │   └── bnpl_signals.py    # Pluggable BNPL signal definitions
│   ├── sec/
│   │   └── edgar.py           # SEC EDGAR API client
│   └── reports/
│       └── markdown.py        # Report generation
├── notebooks/                 # Jupyter analysis notebook
├── tests/                     # 86 tests with fixtures
├── pyproject.toml             # Hatchling build config
└── LICENSE
```

## How It Works

### Data Pipeline

The pipeline has three stages: **fetch → analyze → report**.

1. **Fetch**: `cfpb/client.py` calls the CFPB Consumer Complaint API and parses responses into typed `Complaint` dataclasses. `sec/edgar.py` does the same for SEC EDGAR filing metadata.
2. **Analyze**: `cfpb/analyzer.py` runs pure functions (timeseries, geographic, response analysis) over complaint data. `cfpb/narrative.py` mines free-text narratives for dollar amounts, timing patterns, retailer mentions, and complaint classifications.
3. **Report**: `reports/markdown.py` formats analysis results into Markdown reports with tables and statistics.

### Text Mining (`narrative.py`)

Extracts structured signals from unstructured CFPB complaint narratives:
- **Dollar extraction** — Handles both CFPB redacted format `{$500.00}` and standard `$500.00` via regex
- **Timing classification** — Categorizes complaints as immediate/days/weeks/months based on phrase matching
- **Keyword scoring** — Classifies complaint type by counting signal matches per category; highest score wins
- **Geographic clustering** — Groups complaints by state + zip3 prefix + quarter to find regional patterns

### Pluggable Signals

The `bnpl_signals.py` module demonstrates how the same analysis functions work with different keyword sets. Pass custom signal dictionaries to `classify_fraud_type()` or `response_patterns()` to analyze different complaint domains without changing any pipeline code.

## Setup

```bash
git clone https://github.com/brittraee/consumer-complaint-pipeline.git
cd consumer-complaint-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Fetch CFPB complaints
complaint-pipeline cfpb fetch --company all --output data/cfpb-complaints/

# Analyze downloaded data
complaint-pipeline cfpb analyze --input data/cfpb-complaints/ --output reports/

# Fetch SEC EDGAR filings
complaint-pipeline sec fetch --output data/sec-filings/

# Generate comparison report
complaint-pipeline report compare --input data/cfpb-complaints/ --output reports/

# See all options
complaint-pipeline --help
```

## Notebooks

The `notebooks/` directory contains an interactive analysis notebook that imports the pipeline and visualizes live CFPB data with matplotlib:

- **complaint_analysis.ipynb** — Fetches complaint data, runs all analysis functions, and charts monthly trends, geographic distribution, denomination targeting, timing patterns, fraud classification, and response analysis

```bash
pip install -e ".[notebooks]"
jupyter notebook notebooks/
```

## Testing

```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov              # With coverage
```

Tests use fixture data (no live API calls). All analysis functions are pure — data in, results out, no side effects.

## AI Usage

This project was developed with AI assistance (Claude). AI was used for:
- Boilerplate and scaffolding (CLI structure, CSV I/O, test fixtures)
- Code review and refactoring guidance (monolithic scripts → modular package)
- Research on CFPB API endpoints and SEC EDGAR data formats

Core logic (text mining patterns, classification algorithm, API client design, data modeling) was authored manually. All code was reviewed, tested, and understood before inclusion.

## License

MIT
