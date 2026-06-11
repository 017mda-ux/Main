"""
GP Sourcer Dashboard
Interactive terminal UI for LP due diligence on General Partners.

Usage:
    python -m gp_sourcer.dashboard

Commands inside the dashboard:
    list [status|stage|sector|search=<value>]   Browse GPs (with optional filter)
    view <N>                                     Full GP profile
    analyze <N>                                  AI-powered LP due-diligence memo
    outreach <N>                                 Generate personalised outreach message
    update <N>                                   Change pipeline status
    note <N>                                     Add a note
    score <N> <1-10>                             Set fit score
    pipeline                                     Kanban-style pipeline view
    clear                                        Clear active filters
    help                                         Show this help
    quit / q                                     Exit
"""

from __future__ import annotations

import os
import shlex
import sys
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .models import GP, PIPELINE_STAGES, STATUS_COLORS, STATUS_LABELS, GPStore
from .sample_data import SAMPLE_GPS

load_dotenv()

console = Console()

DATA_PATH = os.getenv("GP_PIPELINE_PATH", "./data/gp_pipeline.json")

# ── helpers ───────────────────────────────────────────────────────────


def _status_text(status: str) -> Text:
    color = STATUS_COLORS.get(status, "white")
    return Text(STATUS_LABELS.get(status, status), style=color)


def _score_str(score: Optional[int]) -> str:
    if score is None:
        return "—"
    stars = "●" * score + "○" * (10 - score)
    color = "green" if score >= 8 else "yellow" if score >= 6 else "red"
    return f"[{color}]{score}/10[/{color}]"


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _fund_str(m: Optional[float]) -> str:
    if m is None:
        return "—"
    if m >= 1000:
        return f"${m / 1000:.1f}B"
    return f"${m:.0f}M"


# ── display functions ─────────────────────────────────────────────────


def show_header(store: GPStore) -> None:
    stats = store.pipeline_stats()
    today = datetime.now().strftime("%B %d, %Y")

    console.print(Panel(
        f"[bold cyan]GP SOURCER DASHBOARD[/bold cyan]\n"
        f"[dim]LP Due Diligence Pipeline  •  {today}[/dim]",
        border_style="cyan",
    ))

    stat_table = Table.grid(padding=(0, 4))
    for _ in range(7):
        stat_table.add_column(justify="center")

    stat_table.add_row(
        f"[bold]{stats['total']}[/bold]",
        f"[dim]{stats['prospect']}[/dim]",
        f"[cyan]{stats['contacted']}[/cyan]",
        f"[yellow]{stats['meeting']}[/yellow]",
        f"[blue]{stats['diligence']}[/blue]",
        f"[bold green]{stats['committed']}[/bold green]",
        f"[red]{stats['passed']}[/red]",
    )
    stat_table.add_row(
        "Total",
        "[dim]Prospect[/dim]",
        "[cyan]Contacted[/cyan]",
        "[yellow]Meeting[/yellow]",
        "[blue]Diligence[/blue]",
        "[bold green]Committed[/bold green]",
        "[red]Passed[/red]",
    )

    console.print(Panel(stat_table, border_style="dim"))


def show_gp_list(gps: List[GP], title: str = "GP Pipeline") -> None:
    if not gps:
        console.print("[dim]No GPs match the current filters.[/dim]\n")
        return

    table = Table(
        title=title,
        border_style="dim",
        header_style="bold",
        show_lines=False,
        expand=True,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Name", min_width=18)
    table.add_column("Firm", min_width=20)
    table.add_column("Focus", min_width=22)
    table.add_column("Stage", min_width=18)
    table.add_column("Fund", justify="right", min_width=8)
    table.add_column("Fit", justify="center", width=6)
    table.add_column("Status", min_width=14)

    for i, gp in enumerate(gps, 1):
        focus = _truncate(", ".join(gp.focus_areas[:2]), 24)
        stage = _truncate(", ".join(gp.stage[:2]), 20)
        status_color = STATUS_COLORS.get(gp.status, "white")
        status_label = STATUS_LABELS.get(gp.status, gp.status)

        table.add_row(
            str(i),
            gp.name,
            _truncate(gp.firm, 22),
            focus,
            stage,
            _fund_str(gp.fund_size_m),
            _score_str(gp.fit_score),
            Text(status_label, style=status_color),
        )

    console.print(table)
    console.print(f"[dim]{len(gps)} GP(s) shown. Use [bold]view <N>[/bold] for details.[/dim]\n")


def show_gp_detail(gp: GP) -> None:
    console.print(Rule(f"[bold]{gp.name}[/bold]  |  [cyan]{gp.firm}[/cyan]", style="cyan"))

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold dim", min_width=16)
    info.add_column()

    info.add_row("Role", gp.role)
    info.add_row("Focus", ", ".join(gp.focus_areas))
    info.add_row("Stage", ", ".join(gp.stage))
    info.add_row("Geography", ", ".join(gp.geography))
    info.add_row("Fund Size", _fund_str(gp.fund_size_m))
    info.add_row("AUM", _fund_str(gp.aum_m))
    info.add_row("Status", _status_text(gp.status))
    info.add_row("Fit Score", Text(_score_str(gp.fit_score)))
    if gp.last_contacted:
        info.add_row("Last Contact", gp.last_contacted)
    info.add_row("Added", gp.added_date)
    if gp.twitter:
        info.add_row("Twitter", gp.twitter)
    if gp.website:
        info.add_row("Website", gp.website)
    if gp.tags:
        info.add_row("Tags", "  ".join(f"[dim cyan]{t}[/dim cyan]" for t in gp.tags))

    console.print(Panel(info, title="Profile", border_style="dim"))

    console.print(Panel(gp.bio, title="Bio", border_style="dim"))

    if gp.portfolio_highlights:
        port_table = Table.grid(padding=(0, 2))
        port_table.add_column(style="bold dim", min_width=16)
        port_table.add_column()
        port_table.add_row("Portfolio", ", ".join(gp.portfolio_highlights))
        port_table.add_row("Notable Exits", ", ".join(gp.notable_exits) if gp.notable_exits else "—")
        console.print(Panel(port_table, title="Track Record", border_style="dim"))

    if gp.notes:
        notes_text = "\n".join(f"  • {n}" for n in gp.notes)
        console.print(Panel(notes_text, title=f"Notes ({len(gp.notes)})", border_style="yellow"))
    else:
        console.print("[dim]No notes yet. Use [bold]note <N>[/bold] to add one.[/dim]")

    console.print()


def show_pipeline(store: GPStore) -> None:
    console.print(Rule("[bold]Pipeline Overview[/bold]", style="cyan"))
    for stage in PIPELINE_STAGES:
        gps = [g for g in store.all() if g.status == stage]
        if not gps:
            continue
        color = STATUS_COLORS.get(stage, "white")
        label = STATUS_LABELS.get(stage, stage)
        names = "  •  ".join(
            f"[{color}]{g.name}[/{color}] [dim]({g.firm})[/dim]" for g in gps
        )
        console.print(f"[{color}]{label}[/{color}] [{len(gps)}]   {names}")
    console.print()


def show_help() -> None:
    help_text = """\
[bold cyan]GP Sourcer Commands[/bold cyan]

  [bold]list[/bold]                              Show all GPs
  [bold]list status=contacted[/bold]             Filter by status (prospect/contacted/meeting/diligence/committed/passed)
  [bold]list stage=seed[/bold]                   Filter by investment stage
  [bold]list sector=fintech[/bold]               Filter by focus sector
  [bold]list search=<query>[/bold]               Full-text search
  [bold]clear[/bold]                             Clear all active filters

  [bold]view <N>[/bold]                          Full GP profile for row N
  [bold]analyze <N>[/bold]                       AI-powered LP due-diligence memo (requires API key)
  [bold]outreach <N>[/bold]                      Generate personalised outreach message

  [bold]update <N>[/bold]                        Change pipeline status
  [bold]note <N>[/bold]                          Add a note
  [bold]score <N> <1-10>[/bold]                  Set fit score

  [bold]pipeline[/bold]                          Kanban-style pipeline summary
  [bold]header[/bold]                            Refresh stats header

  [bold]help[/bold]                              Show this help
  [bold]quit[/bold] / [bold]q[/bold]             Exit
"""
    console.print(Panel(help_text, border_style="cyan", title="Help"))


# ── command handlers ──────────────────────────────────────────────────


def cmd_list(store: GPStore, active_filters: dict, args: list[str]) -> List[GP]:
    """Parse filter args, apply to store, render table. Returns current GP list."""
    for arg in args:
        if "=" in arg:
            k, v = arg.split("=", 1)
            active_filters[k.lower().strip()] = v.strip()

    gps = store.filter(
        status=active_filters.get("status"),
        stage=active_filters.get("stage"),
        sector=active_filters.get("sector"),
        search=active_filters.get("search"),
    )

    filter_parts = [f"{k}=[cyan]{v}[/cyan]" for k, v in active_filters.items()]
    title = "GP Pipeline"
    if filter_parts:
        title += "  [dim](filtered: " + "  ".join(filter_parts) + ")[/dim]"

    show_gp_list(gps, title=title)
    return gps


def cmd_view(store: GPStore, current_list: List[GP], args: list[str]) -> None:
    if not args or not args[0].isdigit():
        console.print("[red]Usage: view <N>[/red]")
        return
    gp = store.get_by_index(int(args[0]), current_list)
    if gp is None:
        console.print(f"[red]No GP at position {args[0]}. Run [bold]list[/bold] first.[/red]")
        return
    show_gp_detail(gp)


def cmd_analyze(store: GPStore, current_list: List[GP], args: list[str]) -> None:
    if not args or not args[0].isdigit():
        console.print("[red]Usage: analyze <N>[/red]")
        return
    gp = store.get_by_index(int(args[0]), current_list)
    if gp is None:
        console.print(f"[red]No GP at position {args[0]}.[/red]")
        return

    from .analyzer import analyze_gp

    console.print(Panel(
        f"[bold]AI Analysis — {gp.name}, {gp.firm}[/bold]\n[dim]Generating LP due-diligence memo…[/dim]",
        border_style="cyan",
    ))
    text = ""
    with console.status("[cyan]Thinking…[/cyan]", spinner="dots"):
        chunks = list(analyze_gp(gp))
    for chunk in chunks:
        text += chunk
    console.print(Markdown(text))
    console.print()


def cmd_outreach(store: GPStore, current_list: List[GP], args: list[str]) -> None:
    if not args or not args[0].isdigit():
        console.print("[red]Usage: outreach <N>[/red]")
        return
    gp = store.get_by_index(int(args[0]), current_list)
    if gp is None:
        console.print(f"[red]No GP at position {args[0]}.[/red]")
        return

    from .analyzer import generate_outreach

    console.print(Rule(f"[bold]Outreach — {gp.name}[/bold]", style="cyan"))
    text = ""
    with console.status("[cyan]Drafting message…[/cyan]", spinner="dots"):
        chunks = list(generate_outreach(gp))
    for chunk in chunks:
        text += chunk
    console.print(Panel(text.strip(), border_style="yellow", title="Suggested Outreach"))
    console.print()


def cmd_update(store: GPStore, current_list: List[GP], args: list[str]) -> None:
    if not args or not args[0].isdigit():
        console.print("[red]Usage: update <N>[/red]")
        return
    gp = store.get_by_index(int(args[0]), current_list)
    if gp is None:
        console.print(f"[red]No GP at position {args[0]}.[/red]")
        return

    console.print(f"Current status: {_status_text(gp.status)}")
    console.print("Stages: " + "  ".join(
        f"[{STATUS_COLORS.get(s, 'white')}]{s}[/{STATUS_COLORS.get(s, 'white')}]"
        for s in PIPELINE_STAGES
    ))
    new_status = Prompt.ask("New status", choices=PIPELINE_STAGES, default=gp.status)
    if new_status != gp.status:
        gp.status = new_status
        if new_status == "contacted":
            gp.last_contacted = datetime.now().strftime("%Y-%m-%d")
        store.update(gp)
        console.print(f"[green]Updated {gp.name} → {_status_text(new_status)}[/green]\n")
    else:
        console.print("[dim]No change.[/dim]\n")


def cmd_note(store: GPStore, current_list: List[GP], args: list[str]) -> None:
    if not args or not args[0].isdigit():
        console.print("[red]Usage: note <N>[/red]")
        return
    gp = store.get_by_index(int(args[0]), current_list)
    if gp is None:
        console.print(f"[red]No GP at position {args[0]}.[/red]")
        return

    note = Prompt.ask(f"Note for [bold]{gp.name}[/bold]")
    if note.strip():
        dated = f"[{datetime.now().strftime('%Y-%m-%d')}] {note.strip()}"
        gp.notes.append(dated)
        store.update(gp)
        console.print(f"[green]Note saved.[/green]\n")
    else:
        console.print("[dim]Empty note — skipped.[/dim]\n")


def cmd_score(store: GPStore, current_list: List[GP], args: list[str]) -> None:
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        console.print("[red]Usage: score <N> <1-10>[/red]")
        return
    gp = store.get_by_index(int(args[0]), current_list)
    if gp is None:
        console.print(f"[red]No GP at position {args[0]}.[/red]")
        return
    score = max(1, min(10, int(args[1])))
    gp.fit_score = score
    store.update(gp)
    console.print(f"[green]{gp.name} fit score → {_score_str(score)}[/green]\n")


# ── main REPL ─────────────────────────────────────────────────────────


def run() -> None:
    store = GPStore(DATA_PATH)

    if store.is_empty():
        console.print(
            Panel(
                "[bold]Welcome to GP Sourcer![/bold]\n\n"
                "No pipeline data found — loading sample GP profiles to get you started.\n"
                f"Data will be saved to [dim]{DATA_PATH}[/dim]",
                border_style="cyan",
            )
        )
        for gp in SAMPLE_GPS:
            store.add(gp)
        console.print(f"[green]Loaded {len(SAMPLE_GPS)} sample GPs.[/green]\n")

    show_header(store)

    active_filters: dict = {}
    current_list: List[GP] = store.all()

    console.print(
        "[dim]Type [bold]help[/bold] for commands, [bold]list[/bold] to browse, "
        "[bold]quit[/bold] to exit.[/dim]\n"
    )

    while True:
        try:
            raw = Prompt.ask("[bold cyan]gp-sourcer[/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not raw:
            continue

        try:
            tokens = shlex.split(raw)
        except ValueError:
            tokens = raw.split()

        cmd = tokens[0].lower()
        args = tokens[1:]

        if cmd in {"quit", "q", "exit"}:
            console.print("[dim]Goodbye.[/dim]")
            break

        elif cmd in {"list", "l", "ls"}:
            current_list = cmd_list(store, active_filters, args)

        elif cmd in {"view", "v"}:
            cmd_view(store, current_list, args)

        elif cmd in {"analyze", "a", "analyse"}:
            cmd_analyze(store, current_list, args)

        elif cmd in {"outreach", "o"}:
            cmd_outreach(store, current_list, args)

        elif cmd in {"update", "u"}:
            cmd_update(store, current_list, args)

        elif cmd in {"note", "n"}:
            cmd_note(store, current_list, args)

        elif cmd in {"score", "s"}:
            cmd_score(store, current_list, args)

        elif cmd == "pipeline":
            show_pipeline(store)

        elif cmd in {"header", "stats"}:
            show_header(store)

        elif cmd == "clear":
            active_filters.clear()
            console.print("[dim]Filters cleared.[/dim]\n")

        elif cmd in {"help", "h", "?"}:
            show_help()

        else:
            console.print(
                f"[red]Unknown command '[bold]{cmd}[/bold]'.[/red] "
                "Type [bold]help[/bold] for available commands.\n"
            )


if __name__ == "__main__":
    run()
