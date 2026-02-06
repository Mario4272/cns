"""
CNS Beta Showcase v1.
Demonstrates:
1. Temporal Evolution (ASOF queries).
2. Belief Revision (Math & Explanations).
3. Provenance & Receipts.
"""

import json
import sys
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

# Add project root
sys.path.append(".")
from cns_py.cql.executor import cql

console = Console()


def run_query(title, query):
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]\n[dim]{query}[/dim]", border_style="cyan"))

    t0 = datetime.now()
    res = cql(query)
    dt = (datetime.now() - t0).total_seconds() * 1000

    # Render Results
    if "results" in res and res["results"]:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Subject")
        table.add_column("Predicate")
        table.add_column("Object")
        table.add_column("Conf")
        table.add_column("Time (Observed)")
        table.add_column("Fiber ID")

        for r in res["results"]:
            subj = r["subject_label"]
            pred = r["predicate"]
            obj = r["object_label"]
            conf = f"{r['confidence']:.2f}"
            obs = r["observed_at"] or "N/A"
            fid = str(r["fiber_id"])
            table.add_row(subj, pred, obj, conf, obs, fid)

        console.print(table)
        console.print(f"[dim italic]Query took {dt:.1f}ms[/dim italic]\n")
        return res
    else:
        console.print("[yellow]No results found.[/yellow]\n")
        return None


def main():
    console.print(Markdown("# CNS Beta Showcase 🚀"))

    # 1. Temporal Evolution
    run_query(
        "1. Time Travel: What did FrameworkX support in 2024?",
        'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2024-12-31T12:00:00Z RETURN',
    )

    run_query(
        "2. Time Travel: What does it support in 2025?",
        'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T12:00:00Z RETURN',
    )

    # 2. Receipts & Explanations
    res = run_query(
        "3. Explain & Receipts: Why is the confidence 0.98?",
        'MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T12:00:00Z RETURN EXPLAIN',
    )

    if res and "explain" in res:
        console.print(Panel("[bold green]Receipt Breakdown[/bold green]", border_style="green"))
        # Show specific terms from the first result if available
        # Note: In a real demo we'd parse the 'belief_details' from the result item
        item = res["results"][0]
        if "belief_details" in item:
            details = item["belief_details"]
            console.print(json.dumps(details, indent=2))

    # 3. Provenance
    if res and "results" in res:
        item = res["results"][0]
        if "provenance" in item:
            console.print(Panel("[bold blue]Provenance Chains[/bold blue]", border_style="blue"))
            console.print(json.dumps(item["provenance"], indent=2))


if __name__ == "__main__":
    main()
