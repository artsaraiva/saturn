from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def status_color(status: str) -> str:
    colors = {
        "active": "green",
        "disputed": "yellow",
        "archived": "grey",
        "superseded": "red",
        "open": "red",
        "resolved": "green",
        "dismissed": "grey",
    }
    return colors.get(status, "white")


def status_badge(status: str) -> str:
    color = status_color(status)
    return f"[{color}]{status}[/{color}]"


def render_fact_table(facts: list[dict]) -> Table:
    table = Table(title="Facts", show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Subject", style="cyan")
    table.add_column("Predicate", style="magenta")
    table.add_column("Object", style="white")
    table.add_column("Confidence", justify="right")
    table.add_column("Status")
    table.add_column("Updated")

    for f in facts:
        fid = f.get("id", "")[:8]
        conf = f.get("confidence", 0)
        conf_bar = _confidence_bar(conf)
        status = f.get("status", "active")
        table.add_row(
            fid,
            f.get("subject", ""),
            f.get("predicate", ""),
            f.get("object", ""),
            conf_bar,
            status_badge(status),
            f.get("updated_at", "")[:16],
        )
    return table


def render_fact_panel(fact: dict) -> Panel:
    lines = []
    for key in ["id", "subject", "predicate", "object", "source", "confidence", "status", "created_at", "updated_at"]:
        val = fact.get(key, "")
        if key == "status":
            val = status_badge(str(val))
        lines.append(f"[bold]{key}[/bold]: {val}")

    return Panel("\n".join(lines), title=f"Fact {fact.get('id', '?')[:8]}", border_style="blue")


def render_contradiction_table(contradictions: list[dict]) -> Table:
    table = Table(title="Contradictions", show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Fact A", style="cyan", max_width=30)
    table.add_column("Fact B", style="magenta", max_width=30)
    table.add_column("Reason", style="white")
    table.add_column("State")

    for c in contradictions:
        fa = f"{c.get('fact_a_subject','')} | {c.get('fact_a_predicate','')} | {c.get('fact_a_object','')}"
        fb = f"{c.get('fact_b_subject','')} | {c.get('fact_b_predicate','')} | {c.get('fact_b_object','')}"
        if len(fa) > 28:
            fa = fa[:25] + "..."
        if len(fb) > 28:
            fb = fb[:25] + "..."
        state = c.get("state", "open")
        table.add_row(
            c.get("id", "")[:8],
            fa,
            fb,
            c.get("reason", ""),
            status_badge(state),
        )
    return table


def render_revision_timeline(revisions: list[dict]) -> Panel:
    lines = []
    for r in revisions:
        timestamp = r.get("timestamp", "")
        change = r.get("change_type", "")
        actor = r.get("actor", "")
        if r.get("before"):
            try:
                before = json.loads(r["before"])
                b_str = f"status={before.get('status','?')}"
            except (json.JSONDecodeError, TypeError):
                b_str = "?"
        else:
            b_str = "none"
        if r.get("after"):
            try:
                after = json.loads(r["after"])
                a_str = f"status={after.get('status','?')}"
            except (json.JSONDecodeError, TypeError):
                a_str = "?"
        else:
            a_str = "none"
        lines.append(
            f"[dim]{timestamp[:16]}[/dim] [bold]{change}[/bold] by {actor} ({b_str} \u2192 {a_str})"
        )

    return Panel("\n".join(lines), title="Revision Timeline", border_style="blue")


def render_help_table() -> Table:
    table = Table(title="Shell Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("/search <terms>", "Search facts by terms"),
        ("/show-fact <id>", "Display full fact details"),
        ("/contradictions", "List open contradictions"),
        ("/resolve <id>", "Resolve a contradiction"),
        ("/merge", "Find and suggest merges"),
        ("/archive <id>", "Archive a fact"),
        ("/explain-why <id>", "Explain contradiction or fact state"),
        ("/trace-source <id>", "Trace fact revision chain"),
        ("/doctor", "Check workspace health"),
        ("/help", "Show this help"),
        ("/exit, /quit", "Exit the shell"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    return table


def render_error(message: str) -> Panel:
    return Panel(f"[red]{message}[/red]", title="Error", border_style="red")


def render_success(message: str) -> Panel:
    return Panel(f"[green]{message}[/green]", title="Success", border_style="green")


def render_info(message: str) -> Panel:
    return Panel(message, title="Info", border_style="blue")


def _confidence_bar(confidence: float) -> str:
    filled = int(confidence * 10)
    bar = "\u2588" * filled + "\u2591" * (10 - filled)
    if confidence >= 0.8:
        color = "green"
    elif confidence >= 0.5:
        color = "yellow"
    else:
        color = "red"
    return f"[{color}]{bar}[/{color}] {confidence:.2f}"
