#!/usr/bin/env python3
"""
AI Strategy & Investment Analyst — CLI entrypoint

Frameworks: 7 Powers · Aggregation Theory · Moat Taxonomy · TPS ·
            22 Immutable Laws of Marketing · 15 Commitments ·
            Munger Mental Models · Quantitative PMF ·
            Paul Graham Essays · Acquired Podcast RAG

Commands:
  build-kb   Scrape Acquired transcripts and build the vector knowledge base
  build-pg   Scrape Paul Graham essays and add them to the knowledge base
  chat       Launch the interactive strategy analyst chat
  ask        Ask a single question (non-interactive)
  status     Show knowledge base stats

Usage examples:
  python main.py build-kb                                    # full Acquired scrape + index
  python main.py build-kb --max-episodes 20                  # quick test
  python main.py build-pg                                    # index all PG essays
  python main.py build-pg --priority-only                    # index high-signal essays only
  python main.py chat                                        # interactive REPL
  python main.py ask "Analyse Nvidia's moat"
  python main.py ask "Apply Paul Graham's default alive test to Samsara"
  python main.py ask "Is this founder in founder mode or manager mode?"
  python main.py ask "Score Apple on the 22 Laws of Marketing"
  python main.py status                                      # KB info
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


def _get_pg_scraper():
    from src.scraper import PaulGrahamScraper
    pg_path = os.getenv("PG_ESSAYS_PATH", "./data/pg_essays")
    return PaulGrahamScraper(cache_dir=pg_path)


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


def cmd_build_pg(args):
    """Scrape Paul Graham essays and index them into the knowledge base."""
    console.print(
        Panel.fit(
            "[bold cyan]Paul Graham Essay Knowledge Base Builder[/bold cyan]\n"
            "Scraping essays from paulgraham.com and indexing into ChromaDB…",
            border_style="cyan",
        )
    )

    scraper = _get_pg_scraper()
    vs = _get_vector_store()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching essay list…", total=None)

        essay_list = scraper.get_essay_list()
        label = "priority essays" if args.priority_only else "all essays"
        progress.update(task, description=f"Found {len(essay_list)} essays. Fetching {label}…")

        essays_with_text = []
        for i, essay in enumerate(essay_list):
            progress.update(
                task,
                description=f"[{i+1}/{len(essay_list)}] {essay['title'][:60]}…",
            )
        # Use get_all_essays for caching + filtering
        essays_with_text = scraper.get_all_essays(
            priority_only=args.priority_only,
            max_essays=args.max_essays,
            verbose=False,
        )

        progress.update(task, description="Ingesting into vector store…")
        total_chunks = vs.ingest_pg_essays(essays_with_text, verbose=False)

    console.print(
        f"\n[bold green]✓ Done![/bold green] "
        f"Indexed {len(essays_with_text)} essays / "
        f"{total_chunks} new chunks into the knowledge base.\n"
        f"Total PG chunks in DB: [bold]{vs.count_pg()}[/bold]"
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
    pg_count = vs.count_pg()
    pg_titles = vs.get_pg_essay_titles() if pg_count > 0 else []
    console.print(
        Panel.fit(
            f"[bold]Knowledge Base Status[/bold]\n\n"
            f"[underline]Acquired Podcast[/underline]\n"
            f"  Chunks indexed : [cyan]{count:,}[/cyan]\n"
            f"  Episodes       : [cyan]{len(slugs)}[/cyan]\n\n"
            f"[underline]Paul Graham Essays[/underline]\n"
            f"  Chunks indexed : [cyan]{pg_count:,}[/cyan]\n"
            f"  Essays         : [cyan]{len(pg_titles)}[/cyan]\n\n"
            f"DB path          : [dim]{os.getenv('CHROMA_DB_PATH', './data/chroma_db')}[/dim]",
            border_style="green",
        )
    )
    if slugs:
        console.print("\n[bold]Indexed episodes:[/bold]")
        for s in slugs:
            console.print(f"  • {s}")
    if pg_titles:
        console.print("\n[bold]Indexed PG essays:[/bold]")
        for t in pg_titles:
            console.print(f"  • {t}")


def cmd_chat(_args):
    """Interactive investment analyst REPL."""
    _check_api_key()
    vs = _get_vector_store()
    agent = _get_agent(vs)

    console.print(
        Panel(
            "[bold cyan]AI Strategy & Investment Analyst[/bold cyan]\n\n"
            "Ask me about any company, moat, business model, marketing strategy, "
            "leadership health, or investment thesis.\n"
            "Frameworks: 7 Powers · Aggregation Theory · Moat Taxonomy · TPS · "
            "22 Laws of Marketing · 15 Commitments · Munger · Quantitative PMF · "
            "Paul Graham Essays\n\n"
            "[dim]Commands: 'reset' to clear history, 'quit' / 'exit' to leave.[/dim]",
            border_style="cyan",
            expand=False,
        )
    )

    if vs.is_empty():
        console.print(
            "[yellow]⚠  Acquired KB is empty.[/yellow] "
            "Run [bold]python main.py build-kb[/bold] for Acquired transcripts. "
            "Continuing with base model knowledge only.\n"
        )
    if vs.is_pg_empty():
        console.print(
            "[yellow]⚠  Paul Graham KB is empty.[/yellow] "
            "Run [bold]python main.py build-pg[/bold] to index PG essays.\n"
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

    # build-pg
    p_pg = sub.add_parser("build-pg", help="Scrape and index Paul Graham essays")
    p_pg.add_argument(
        "--priority-only",
        action="store_true",
        default=False,
        help="Only index the curated high-signal essay list (faster)",
    )
    p_pg.add_argument(
        "--max-essays",
        type=int,
        default=None,
        metavar="N",
        help="Limit to N essays (useful for testing; default: all)",
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
        "build-pg": cmd_build_pg,
        "chat": cmd_chat,
        "ask": cmd_ask,
        "status": cmd_status,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    import anthropic   # needed for exception handling in cmd_chat/cmd_ask
    main()
