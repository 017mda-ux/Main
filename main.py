#!/usr/bin/env python3
"""
AI Investment Analyst — CLI entrypoint

Commands:
  build-kb   Scrape Acquired transcripts and build the vector knowledge base
  chat       Launch the interactive investment analyst chat
  ask        Ask a single question (non-interactive)
  status     Show knowledge base stats

Usage examples:
  python main.py build-kb                          # full scrape + index
  python main.py build-kb --max-episodes 20        # quick test with 20 episodes
  python main.py chat                              # interactive REPL
  python main.py ask "Analyse Nvidia's moat"       # single question
  python main.py status                            # KB info
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

load_dotenv()

console = Console()


# ──────────────────────────────────────────────────────────────────────
#  Lazy imports (avoid slow sentence-transformers load on status/help)
# ──────────────────────────────────────────────────────────────────────

def _get_vector_store():
    from src.vector_store import VectorStore
    db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
    return VectorStore(db_path=db_path)


def _get_agent(vs):
    from src.agent import InvestmentAnalystAgent
    return InvestmentAnalystAgent(vs)


def _get_scraper():
    from src.scraper import AcquiredScraper
    transcripts_path = os.getenv("TRANSCRIPTS_PATH", "./data/transcripts")
    return AcquiredScraper(cache_dir=transcripts_path)


# ──────────────────────────────────────────────────────────────────────
#  Commands
# ──────────────────────────────────────────────────────────────────────

def cmd_build_kb(args):
    """Scrape Acquired podcast and build / update the vector knowledge base."""
    console.print(
        Panel.fit(
            "[bold cyan]Acquired Podcast Knowledge Base Builder[/bold cyan]\n"
            "Scraping transcripts from acquired.fm and indexing into ChromaDB…",
            border_style="cyan",
        )
    )

    scraper = _get_scraper()
    vs = _get_vector_store()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching episode list…", total=None)

        episodes_meta = scraper.get_episodes(max_episodes=args.max_episodes)
        progress.update(task, description=f"Found {len(episodes_meta)} episodes. Fetching transcripts…")

        episodes_with_transcripts = []
        for i, ep in enumerate(episodes_meta):
            progress.update(
                task,
                description=f"[{i+1}/{len(episodes_meta)}] {ep['title'][:60]}…",
            )
            transcript = scraper.get_transcript(ep)
            if transcript:
                episodes_with_transcripts.append({**ep, "transcript": transcript})

        progress.update(task, description="Ingesting into vector store…")
        total_chunks = vs.ingest_episodes(episodes_with_transcripts, verbose=False)

    console.print(
        f"\n[bold green]✓ Done![/bold green] "
        f"Indexed {len(episodes_with_transcripts)} episodes / "
        f"{total_chunks} new chunks into the knowledge base.\n"
        f"Total chunks in DB: [bold]{vs.count()}[/bold]"
    )


def cmd_status(_args):
    """Show knowledge base statistics."""
    vs = _get_vector_store()
    count = vs.count()
    if count == 0:
        console.print(
            "[yellow]Knowledge base is empty.[/yellow] "
            "Run [bold]python main.py build-kb[/bold] to populate it."
        )
        return

    slugs = vs.get_episode_slugs()
    console.print(
        Panel.fit(
            f"[bold]Knowledge Base Status[/bold]\n\n"
            f"Chunks indexed : [cyan]{count:,}[/cyan]\n"
            f"Episodes       : [cyan]{len(slugs)}[/cyan]\n"
            f"DB path        : [dim]{os.getenv('CHROMA_DB_PATH', './data/chroma_db')}[/dim]",
            border_style="green",
        )
    )
    if slugs:
        console.print("\n[bold]Indexed episodes:[/bold]")
        for s in slugs:
            console.print(f"  • {s}")


def cmd_chat(_args):
    """Interactive investment analyst REPL."""
    _check_api_key()
    vs = _get_vector_store()
    agent = _get_agent(vs)

    console.print(
        Panel(
            "[bold cyan]Acquired Investment Analyst[/bold cyan]\n\n"
            "Ask me about any company, investment thesis, competitive moat, "
            "or business model. I'm trained on all Acquired podcast episodes.\n\n"
            "[dim]Commands: 'reset' to clear history, 'quit' / 'exit' to leave.[/dim]",
            border_style="cyan",
            expand=False,
        )
    )

    if vs.is_empty():
        console.print(
            "[yellow]⚠  Knowledge base is empty.[/yellow] "
            "Run [bold]python main.py build-kb[/bold] first for best results. "
            "Continuing with base model knowledge only.\n"
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

        console.print("\n[bold magenta]Analyst[/bold magenta]")
        response_text = ""
        try:
            for chunk in agent.chat(user_input):
                console.print(chunk, end="")
                response_text += chunk
        except anthropic.APIError as exc:
            console.print(f"\n[red]API error: {exc}[/red]")
            continue
        except KeyboardInterrupt:
            console.print("\n[dim](interrupted)[/dim]")
            continue

        console.print()   # newline after response


def cmd_ask(args):
    """Ask a single non-interactive question."""
    _check_api_key()
    vs = _get_vector_store()
    agent = _get_agent(vs)

    question = " ".join(args.question)
    console.print(f"\n[bold]Q:[/bold] {question}\n")
    console.print("[bold magenta]Analyst:[/bold magenta]")

    response_parts = []
    try:
        for chunk in agent.chat(question):
            console.print(chunk, end="")
            response_parts.append(chunk)
    except anthropic.APIError as exc:
        console.print(f"\n[red]API error: {exc}[/red]")
        sys.exit(1)

    console.print()


# ──────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────

def _check_api_key():
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.\n"
            "Copy [bold].env.example[/bold] to [bold].env[/bold] and add your key."
        )
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────
#  CLI argument parsing
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="AI Investment Analyst trained on Acquired podcast transcripts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build-kb
    p_build = sub.add_parser("build-kb", help="Scrape and index Acquired transcripts")
    p_build.add_argument(
        "--max-episodes",
        type=int,
        default=None,
        metavar="N",
        help="Limit to N episodes (useful for testing; default: all)",
    )

    # chat
    sub.add_parser("chat", help="Launch interactive chat")

    # ask
    p_ask = sub.add_parser("ask", help="Ask a single question")
    p_ask.add_argument("question", nargs="+", help="The question to ask")

    # status
    sub.add_parser("status", help="Show knowledge base stats")

    args = parser.parse_args()
    dispatch = {
        "build-kb": cmd_build_kb,
        "chat": cmd_chat,
        "ask": cmd_ask,
        "status": cmd_status,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    import anthropic   # needed for exception handling in cmd_chat/cmd_ask
    main()
