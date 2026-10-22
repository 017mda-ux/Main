#!/usr/bin/env python3
"""
Nomad investment agent — CLI

  python nomad_cli.py chat                       # interactive
  python nomad_cli.py ask "Is Costco still sharing scale economies?"
  python nomad_cli.py memo "Duolingo"            # full write-up on one company
"""

import argparse
import sys

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt

load_dotenv()
console = Console()

MEMO_PROMPT = (
    "Write a full investment memo on {company} using the output format in your instructions. "
    "Search for current figures first, run the calculators on whatever numbers you find, "
    "and finish with the moat scorecard."
)


def _stream(agent, text: str) -> None:
    try:
        for chunk in agent.chat(text):
            console.print(chunk, end="", markup=False, highlight=False)
    except anthropic.AuthenticationError:
        console.print("\n[red]No valid API key. Set ANTHROPIC_API_KEY (see .env.example).[/red]")
        sys.exit(1)
    except anthropic.RateLimitError:
        console.print("\n[red]Rate limited — try again shortly.[/red]")
    except anthropic.APIConnectionError:
        console.print("\n[red]Network error reaching the API.[/red]")
    except anthropic.APIStatusError as exc:
        console.print(f"\n[red]API error {exc.status_code}: {exc.message}[/red]")
    console.print()


def main() -> None:
    from nomad.agent import NomadAgent

    p = argparse.ArgumentParser(description="Long-term investment agent inspired by the Nomad letters")
    p.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("chat")
    a = sub.add_parser("ask")
    a.add_argument("question", nargs="+")
    m = sub.add_parser("memo")
    m.add_argument("company", nargs="+")
    args = p.parse_args()

    agent = NomadAgent(effort=args.effort)

    if args.cmd == "ask":
        _stream(agent, " ".join(args.question))
    elif args.cmd == "memo":
        _stream(agent, MEMO_PROMPT.format(company=" ".join(args.company)))
    else:
        console.print("[bold cyan]Nomad investment agent[/bold cyan]  [dim]'reset' clears, 'quit' exits[/dim]")
        while True:
            try:
                q = Prompt.ask("\n[bold green]You[/bold green]").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in {"quit", "exit", "q"}:
                break
            if q.lower() == "reset":
                agent.reset()
                continue
            if q:
                console.print("\n[bold magenta]Analyst[/bold magenta]")
                _stream(agent, q)


if __name__ == "__main__":
    main()
