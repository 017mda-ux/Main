#!/usr/bin/env python3
"""
GP Sourcing Agent — CLI entrypoint

An institutional LP tool for sourcing, profiling, and evaluating
General Partners across PE buyout, growth equity, and venture capital.

Commands:
  chat     Interactive GP research session (recommended)
  search   Quick registry search for GP firms by name/keyword
  profile  Deep-dive LP profile on a specific GP firm
  ask      Single non-interactive question

Usage examples:
  python gp_main.py chat
  python gp_main.py search "healthcare buyout New York"
  python gp_main.py profile "Vista Equity Partners"
  python gp_main.py ask "What makes a strong growth equity GP?"
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()

console = Console()


def _check_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY is not set.\n"
            "Copy [bold].env.example[/bold] to [bold].env[/bold] and add your key."
        )
        sys.exit(1)


def _get_agent():
    from gp_sourcer.agent import GPSourcingAgent
    return GPSourcingAgent()


# ──────────────────────────────────────────────────────────────────────
#  Commands
# ──────────────────────────────────────────────────────────────────────

def cmd_chat(_args) -> None:
    """Interactive GP sourcing research session."""
    _check_api_key()
    agent = _get_agent()

    console.print(
        Panel(
            "[bold cyan]GP Sourcing Agent[/bold cyan]\n\n"
            "Research General Partners across [bold]PE buyout[/bold], "
            "[bold]growth equity[/bold], and [bold]venture capital[/bold].\n\n"
            "Examples:\n"
            "  • [dim]Profile Vista Equity Partners for a potential commitment[/dim]\n"
            "  • [dim]Find top healthcare buyout GPs with AUM under $5B[/dim]\n"
            "  • [dim]Compare KKR vs Blackstone vs Apollo on terms and LP base[/dim]\n"
            "  • [dim]What Form D filings has Warburg Pincus made since 2021?[/dim]\n\n"
            "[dim]Commands: 'reset' to clear history · 'quit' / 'exit' to leave[/dim]",
            border_style="cyan",
            expand=False,
        )
    )

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit", "q"}:
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.lower() == "reset":
            agent.reset()
            console.print("[dim]Conversation history cleared.[/dim]")
            continue

        console.print("\n[bold magenta]GP Analyst[/bold magenta]")
        try:
            for chunk in agent.chat(user_input):
                console.print(chunk, end="")
        except anthropic.APIError as exc:
            console.print(f"\n[red]API error: {exc}[/red]")
        except KeyboardInterrupt:
            console.print("\n[dim](interrupted)[/dim]")
        console.print()


def cmd_search(args) -> None:
    """Quick GP registry search."""
    _check_api_key()
    query = " ".join(args.query)

    console.print(
        Panel.fit(
            f"[bold cyan]GP Registry Search[/bold cyan]\n"
            f"Query: [italic]{query}[/italic]",
            border_style="cyan",
        )
    )

    agent = _get_agent()
    prompt = (
        f"Search the SEC registry and web for GP firms matching: '{query}'. "
        f"Return a concise table: Firm Name | AUM | HQ | CRD/SEC | Key Signal. "
        f"Then give a 1-sentence preliminary view on each."
    )

    console.print("\n[bold magenta]GP Analyst[/bold magenta]")
    try:
        for chunk in agent.chat(prompt):
            console.print(chunk, end="")
    except anthropic.APIError as exc:
        console.print(f"\n[red]API error: {exc}[/red]")
    console.print()


def cmd_profile(args) -> None:
    """Deep-dive LP profile on a specific GP firm."""
    _check_api_key()
    firm = " ".join(args.firm)

    console.print(
        Panel.fit(
            f"[bold cyan]GP LP Profile[/bold cyan]\n"
            f"Firm: [italic]{firm}[/italic]\n"
            f"[dim]Running SEC registry · Form ADV · Form D · web research...[/dim]",
            border_style="cyan",
        )
    )

    agent = _get_agent()
    strategy_hint = f" (strategy: {args.strategy})" if args.strategy else ""
    prompt = (
        f"Generate a full LP profile for {firm}{strategy_hint}. "
        f"Follow the full research protocol: SEC registry → Form ADV → Form D → "
        f"web research → website → LP base → evaluation framework. "
        f"Output the complete structured tearsheet with LP Fit Score and recommendation."
    )

    console.print("\n[bold magenta]GP Analyst[/bold magenta]")
    try:
        for chunk in agent.chat(prompt):
            console.print(chunk, end="")
    except anthropic.APIError as exc:
        console.print(f"\n[red]API error: {exc}[/red]")
    console.print()


def cmd_ask(args) -> None:
    """Ask a single non-interactive question."""
    _check_api_key()
    agent = _get_agent()
    question = " ".join(args.question)

    console.print(f"\n[bold]Q:[/bold] {question}\n")
    console.print("[bold magenta]GP Analyst:[/bold magenta]")

    try:
        for chunk in agent.chat(question):
            console.print(chunk, end="")
    except anthropic.APIError as exc:
        console.print(f"\n[red]API error: {exc}[/red]")
        sys.exit(1)
    console.print()


# ──────────────────────────────────────────────────────────────────────
#  CLI argument parsing
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gp_main.py",
        description="GP Sourcing Agent — institutional LP tool for researching fund managers",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # chat
    sub.add_parser("chat", help="Launch interactive GP research session")

    # search
    p_search = sub.add_parser("search", help="Quick registry search for GP firms")
    p_search.add_argument("query", nargs="+", help="Search query (firm name, strategy, geography)")

    # profile
    p_profile = sub.add_parser("profile", help="Full LP profile on a specific GP firm")
    p_profile.add_argument("firm", nargs="+", help="GP firm name")
    p_profile.add_argument(
        "--strategy",
        choices=["buyout", "growth", "vc", "credit", "real_assets"],
        default=None,
        help="Fund strategy hint (optional)",
    )

    # ask
    p_ask = sub.add_parser("ask", help="Ask a single question")
    p_ask.add_argument("question", nargs="+", help="The question to ask")

    args = parser.parse_args()
    dispatch = {
        "chat": cmd_chat,
        "search": cmd_search,
        "profile": cmd_profile,
        "ask": cmd_ask,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    import anthropic
    main()
