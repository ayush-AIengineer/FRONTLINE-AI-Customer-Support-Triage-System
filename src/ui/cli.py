"""
FRONTLINE — CLI Interface (Level 3 UI)
Rich terminal table displaying triage results.

Usage:
  python src/ui/cli.py                          # run all messages
  python src/ui/cli.py --message "I need help"  # triage single message
  python src/ui/cli.py --results outputs/triage_results_*.json  # display saved results
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

PRIORITY_COLORS = {
    "P0": "bold red",
    "P1": "red",
    "P2": "yellow",
    "P3": "green",
}

CATEGORY_ICONS = {
    "billing": "💳",
    "order_issue": "📦",
    "technical_bug": "🐛",
    "technical_outage": "🔥",
    "account_support": "🔑",
    "security": "🔒",
    "feature_request": "✨",
    "general_inquiry": "❓",
    "out_of_scope": "🚫",
    "adversarial": "⚠️",
    "unclear": "🤷",
    "positive_feedback": "💚",
    "complaint": "😤",
}


def display_results(results: list[dict]):
    """Renders triage results as a Rich terminal table."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]FRONTLINE — AI Triage Results[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
        expand=True,
    )

    table.add_column("ID", style="dim", width=8)
    table.add_column("Priority", width=8, justify="center")
    table.add_column("Category", width=18)
    table.add_column("Summary", width=40)
    table.add_column("Human?", width=8, justify="center")
    table.add_column("Conf.", width=7, justify="right")
    table.add_column("Flags", width=20)

    for r in results:
        priority = r.get("priority", "P3")
        priority_color = PRIORITY_COLORS.get(priority, "white")

        category = r.get("category", "unclear")
        icon = CATEGORY_ICONS.get(category, "❔")

        needs_human = r.get("needs_human", False)
        human_str = "🚨 YES" if needs_human else "✅ no"

        confidence = r.get("confidence", 0.0)
        conf_color = "green" if confidence >= 0.8 else "yellow" if confidence >= 0.6 else "red"

        flags = r.get("flags", [])
        flags_str = ", ".join(flags) if flags else "—"

        summary = r.get("summary", "")[:80]

        table.add_row(
            r.get("id", "?"),
            Text(priority, style=priority_color),
            f"{icon} {category}",
            summary,
            human_str,
            Text(f"{confidence:.2f}", style=conf_color),
            flags_str,
        )

    console.print(table)

    # Stats summary
    total = len(results)
    humans = sum(1 for r in results if r.get("needs_human"))
    p0 = sum(1 for r in results if r.get("priority") == "P0")
    adversarial = sum(1 for r in results if r.get("category") == "adversarial")

    console.print()
    console.print(Panel(
        f"[bold]Total:[/bold] {total} messages  |  "
        f"[bold red]P0 Critical:[/bold red] {p0}  |  "
        f"[bold yellow]Needs Human:[/bold yellow] {humans}  |  "
        f"[bold magenta]Adversarial:[/bold magenta] {adversarial}",
        title="Summary",
        border_style="cyan",
    ))
    console.print()


def main():
    parser = argparse.ArgumentParser(description="FRONTLINE AI Triage CLI")
    parser.add_argument("--message", "-m", type=str, help="Triage a single message")
    parser.add_argument("--results", "-r", type=str, help="Path to saved results JSON file")
    parser.add_argument("--evaluate", "-e", action="store_true", help="Run evaluation after processing")
    parser.add_argument("--provider", type=str, help="LLM provider: openai or gemini")
    parser.add_argument("--model", type=str, help="Model name override")
    args = parser.parse_args()

    # Load or generate results
    if args.results:
        with open(args.results, "r", encoding="utf-8") as f:
            results = json.load(f)
        display_results(results)
    elif args.message:
        from src.triage.processor import process_single
        console.print(f"\n[cyan]Triaging:[/cyan] {args.message[:100]}\n")
        result = process_single(args.message, provider=args.provider, model=args.model)
        results = [{"id": "SINGLE", "original_text": args.message, **result}]
        display_results(results)
    else:
        # Run full batch
        from src.triage.processor import process_all
        results = process_all(provider=args.provider, model=args.model)
        display_results(results)

        if args.evaluate:
            from evaluation.evaluate import evaluate, print_evaluation_report
            metrics = evaluate(results)
            print_evaluation_report(metrics)


if __name__ == "__main__":
    main()
