"""Network and entity co-occurrence analysis for consumer complaints.

Builds co-occurrence graphs between entities (companies, products, issues,
phone numbers) to identify patterns and clusters. Uses only stdlib.
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from complaint_pipeline.models import Complaint, FccComplaint, FtcComplaint


# --- Entity extraction ---

_PHONE_RE = re.compile(
    r"""
    (?<!\d)              # no digit before
    1?[-.\s]?            # optional country code "1" with optional separator
    \(?\d{3}\)?          # area code, optionally in parens
    [-.\s]?              # optional separator
    \d{3}                # exchange
    [-.\s]?              # optional separator
    \d{4}                # subscriber
    (?!\d)               # no digit after
    """,
    re.VERBOSE,
)


def extract_phone_numbers(text: str) -> list[str]:
    """Extract US phone numbers from text, normalized to 10 digits."""
    numbers = []
    for match in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if len(digits) == 10:
            numbers.append(digits)
        elif len(digits) == 11 and digits.startswith("1"):
            numbers.append(digits[1:])
    return numbers


# --- Co-occurrence graph ---

@dataclass
class Edge:
    """A weighted edge between two entities."""
    source: str
    target: str
    weight: int = 0
    complaints: list[str] = field(default_factory=list)


@dataclass
class EntityGraph:
    """Lightweight co-occurrence graph."""
    nodes: set[str] = field(default_factory=set)
    edges: dict[tuple[str, str], Edge] = field(default_factory=dict)

    def add_edge(self, a: str, b: str, complaint_id: str = "") -> None:
        key = (min(a, b), max(a, b))
        self.nodes.add(a)
        self.nodes.add(b)
        if key not in self.edges:
            self.edges[key] = Edge(source=key[0], target=key[1])
        self.edges[key].weight += 1
        if complaint_id:
            self.edges[key].complaints.append(complaint_id)

    def top_edges(self, n: int = 20) -> list[Edge]:
        return sorted(self.edges.values(), key=lambda e: e.weight, reverse=True)[:n]

    def node_degree(self) -> dict[str, int]:
        degrees: Counter[str] = Counter()
        for (a, b), edge in self.edges.items():
            degrees[a] += edge.weight
            degrees[b] += edge.weight
        return dict(degrees.most_common())

    def connected_components(self) -> list[set[str]]:
        """Find connected components using union-find."""
        parent: dict[str, str] = {n: n for n in self.nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for (a, b) in self.edges:
            union(a, b)

        components: dict[str, set[str]] = defaultdict(set)
        for node in self.nodes:
            components[find(node)].add(node)

        return sorted(components.values(), key=len, reverse=True)


def build_company_product_graph(complaints: list[Complaint]) -> EntityGraph:
    """Build co-occurrence graph of companies and products.

    An edge between company A and product B means complaints about
    company A frequently involve product B.
    """
    graph = EntityGraph()
    for c in complaints:
        if c.company and c.product:
            graph.add_edge(
                f"company:{c.company}",
                f"product:{c.product}",
                c.complaint_id,
            )
        if c.company and c.issue:
            graph.add_edge(
                f"company:{c.company}",
                f"issue:{c.issue}",
                c.complaint_id,
            )
    return graph


def build_company_issue_graph(complaints: list[Complaint]) -> EntityGraph:
    """Build co-occurrence graph between companies and issues."""
    graph = EntityGraph()
    for c in complaints:
        if c.company and c.issue:
            graph.add_edge(
                f"company:{c.company}",
                f"issue:{c.issue}",
                c.complaint_id,
            )
    return graph


def build_phone_number_graph(
    fcc_complaints: list[FccComplaint] | None = None,
    ftc_complaints: list[FtcComplaint] | None = None,
) -> EntityGraph:
    """Build graph of phone numbers linked by shared complaint patterns.

    Connects phone numbers that appear in complaints from the same
    state or share the same call type -- indicates coordinated campaigns.
    """
    graph = EntityGraph()

    # Group FCC complaints by state to find co-occurring numbers
    if fcc_complaints:
        by_state: dict[str, list[FccComplaint]] = defaultdict(list)
        for c in fcc_complaints:
            if c.state and c.caller_id_number:
                by_state[c.state].append(c)

        for state, state_complaints in by_state.items():
            numbers = list({c.caller_id_number for c in state_complaints if c.caller_id_number})
            # Connect numbers that hit the same state (likely same campaign)
            for i in range(len(numbers)):
                for j in range(i + 1, len(numbers)):
                    if i != j:
                        graph.add_edge(
                            f"phone:{numbers[i]}",
                            f"phone:{numbers[j]}",
                        )

    # Group FTC complaints by area code
    if ftc_complaints:
        by_area: dict[str, list[str]] = defaultdict(list)
        for c in ftc_complaints:
            if c.company_phone_number and c.consumer_area_code:
                by_area[c.consumer_area_code].append(c.company_phone_number)

        for area, phones in by_area.items():
            unique_phones = list(set(phones))
            for i in range(len(unique_phones)):
                for j in range(i + 1, len(unique_phones)):
                    graph.add_edge(
                        f"phone:{unique_phones[i]}",
                        f"phone:{unique_phones[j]}",
                    )

    return graph


# --- Complaint clustering ---

def cluster_by_entity(
    complaints: list[Complaint],
    entity_field: str = "company",
) -> dict[str, list[Complaint]]:
    """Group complaints by a shared entity field.

    Args:
        complaints: List of complaints.
        entity_field: Field name to group by (company, product, issue, state).

    Returns: {entity_value: [complaints]}
    """
    clusters: dict[str, list[Complaint]] = defaultdict(list)
    for c in complaints:
        value = getattr(c, entity_field, "")
        if value:
            clusters[value].append(c)
    return dict(sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True))


def entity_summary(complaints: list[Complaint]) -> dict:
    """Generate entity co-occurrence summary stats.

    Returns:
        {
            "top_companies": [(company, count), ...],
            "top_products": [(product, count), ...],
            "top_issues": [(issue, count), ...],
            "company_product_pairs": [((company, product), count), ...],
            "company_issue_pairs": [((company, issue), count), ...],
        }
    """
    company_counts: Counter[str] = Counter()
    product_counts: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    company_product: Counter[tuple[str, str]] = Counter()
    company_issue: Counter[tuple[str, str]] = Counter()

    for c in complaints:
        if c.company:
            company_counts[c.company] += 1
        if c.product:
            product_counts[c.product] += 1
        if c.issue:
            issue_counts[c.issue] += 1
        if c.company and c.product:
            company_product[(c.company, c.product)] += 1
        if c.company and c.issue:
            company_issue[(c.company, c.issue)] += 1

    return {
        "top_companies": company_counts.most_common(20),
        "top_products": product_counts.most_common(20),
        "top_issues": issue_counts.most_common(20),
        "company_product_pairs": company_product.most_common(20),
        "company_issue_pairs": company_issue.most_common(20),
    }


def dollar_amounts_by_scam_type(
    complaints: list[Complaint],
    signals: dict[str, list[str]],
    threshold: int = 2,
) -> dict[str, dict]:
    """Extract dollar amounts grouped by scam category.

    Combines existing dollar extraction with scam classification
    to show financial impact per scam type.

    Returns: {
        category: {
            "total": float,
            "count": int,
            "avg": float,
            "max": float,
            "amounts": [float, ...],
        }
    }
    """
    from complaint_pipeline.cfpb.narrative import extract_dollar_amounts

    category_amounts: dict[str, list[float]] = defaultdict(list)

    for c in complaints:
        if not c.narrative:
            continue
        text = c.narrative.lower()
        amounts = extract_dollar_amounts(c.narrative)
        if not amounts:
            continue

        for cat, keywords in signals.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits >= threshold:
                category_amounts[cat].extend(amounts)

    result = {}
    for cat, amounts in sorted(category_amounts.items()):
        if amounts:
            result[cat] = {
                "total": round(sum(amounts), 2),
                "count": len(amounts),
                "avg": round(sum(amounts) / len(amounts), 2),
                "max": max(amounts),
                "amounts": sorted(amounts, reverse=True)[:10],  # top 10 only
            }
    return result
