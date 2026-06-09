from __future__ import annotations

import shlex
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console

from saturn.config import WorkspaceNotInitializedError, require_config
from saturn.shell.completer import SaturnCompleter
from saturn.shell.handlers import (
    handle_archive,
    handle_contradictions,
    handle_doctor,
    handle_explain_why,
    handle_help,
    handle_merge,
    handle_resolve,
    handle_search,
    handle_show_fact,
    handle_trace_source,
)
from saturn.shell.history import load_history
from saturn.shell.renderers import render_error

SHELL_STYLE = Style.from_dict(
    {
        "prompt": "ansigreen bold",
    }
)


def run_shell(workspace: Path) -> int:
    console = Console()
    try:
        require_config(workspace)
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return 1

    history = load_history(workspace)
    completer = SaturnCompleter(workspace)
    session = PromptSession(history=history, completer=completer, style=SHELL_STYLE)

    console.print("[bold cyan]Saturn Shell[/bold cyan] \u2014 type [green]/help[/green] for commands, [green]/exit[/green] to quit")
    console.print()

    while True:
        try:
            line = session.prompt([("class:prompt", "saturn> ")])
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        line = line.strip()
        if not line:
            continue

        try:
            parts = shlex.split(line)
        except ValueError:
            console.print(render_error("Invalid quoting"))
            continue

        if not parts[0].startswith("/"):
            console.print(render_error(f"Unknown command. Slash commands start with /. Type /help for available commands."))
            continue

        command = parts[0][1:].lower()
        args = parts[1:]

        if command in ("exit", "quit"):
            break
        elif command == "help":
            handle_help(console)
        elif command == "search":
            handle_search(workspace, " ".join(args), console)
        elif command == "show-fact":
            handle_show_fact(workspace, args[0] if args else "", console)
        elif command == "contradictions":
            include_all = "--all" in args
            handle_contradictions(workspace, include_all, console)
        elif command == "resolve":
            action = None
            merged = None
            cid = ""
            idx = 0
            while idx < len(args):
                if args[idx] == "--action" and idx + 1 < len(args):
                    action = args[idx + 1]
                    idx += 2
                elif args[idx] == "--object" and idx + 1 < len(args):
                    merged = args[idx + 1]
                    idx += 2
                else:
                    cid = args[idx]
                    idx += 1
            handle_resolve(workspace, cid, action, merged, console)
        elif command == "merge":
            handle_merge(workspace, console)
        elif command == "archive":
            handle_archive(workspace, args[0] if args else "", console)
        elif command == "explain-why":
            handle_explain_why(workspace, args[0] if args else "", console)
        elif command == "trace-source":
            handle_trace_source(workspace, args[0] if args else "", console)
        elif command == "doctor":
            handle_doctor(workspace, console)
        else:
            console.print(render_error(f"Unknown command: /{command}. Type /help for available commands."))

    console.print("[cyan]Goodbye.[/cyan]")
    return 0
