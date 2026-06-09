from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from saturn.config import WorkspaceNotInitializedError, load_config, require_config
from saturn.db import connect, require_initialized_database
from saturn.facts import archive_fact
from saturn.contradictions import list_contradictions, resolve_contradiction
from saturn.revisions import list_revisions
from saturn.doctor import run_doctor
from saturn.shell.renderers import (
    render_contradiction_table,
    render_error,
    render_fact_panel,
    render_fact_table,
    render_help_table,
    render_info,
    render_revision_timeline,
    render_success,
    status_badge,
)


def handle_search(workspace: Path, terms: str, console: Console) -> None:
    if not terms.strip():
        console.print(render_error("Search terms required. Usage: /search <terms>"))
        return
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return

    with connect(config.db_path) as conn:
        exact = terms.strip().lower()
        partial = exact
        rows = conn.execute(
            f"""
            SELECT *
            FROM facts
            WHERE (instr(lower(subject), ?) > 0
               OR instr(lower(predicate), ?) > 0
               OR instr(lower(object), ?) > 0)
              AND status NOT IN ('archived', 'superseded')
            ORDER BY updated_at DESC
            LIMIT 50
            """,
            (partial, partial, partial),
        ).fetchall()

    if not rows:
        console.print(render_info("No matching facts found."))
        return

    console.print(render_fact_table([dict(r) for r in rows]))


def handle_show_fact(workspace: Path, fact_id: str, console: Console) -> None:
    if not fact_id.strip():
        console.print(render_error("Fact ID required. Usage: /show-fact <id>"))
        return
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
        with connect(config.db_path) as conn:
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return

    if row is None:
        console.print(render_error(f"Fact not found: {fact_id}"))
        return

    console.print(render_fact_panel(dict(row)))


def handle_contradictions(workspace: Path, include_all: bool, console: Console) -> None:
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
        state = None if include_all else "open"
        with connect(config.db_path) as conn:
            contradictions = list_contradictions(conn, state=state)
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return

    if not contradictions:
        console.print(render_info("No contradictions found."))
        return

    console.print(render_contradiction_table([dict(c) for c in contradictions]))


def handle_resolve(workspace: Path, cid: str, action: str, merged_object: str | None, console: Console) -> None:
    if not cid or not action:
        console.print(render_error("Usage: /resolve <id> --action keep_a|keep_b|merge|dismiss|defer"))
        return
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
        with connect(config.db_path) as conn:
            resolve_contradiction(conn, cid, action, merged_object=merged_object, actor="shell")
            row = conn.execute("SELECT * FROM contradictions WHERE id = ?", (cid,)).fetchone()
            state = row["state"] if row else "?"
    except (WorkspaceNotInitializedError, ValueError) as e:
        console.print(render_error(str(e)))
        return

    console.print(render_success(f"Resolved contradiction {cid[:8]} with action: {action} (state: {state})"))


def handle_merge(workspace: Path, args: list[str], console: Console) -> None:
    from saturn.merge import (
        apply_merge,
        get_merge_group,
        list_merge_groups,
        reject_merge,
        suggest_merges,
    )
    from rich.table import Table

    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return

    if not args:
        groups = list_merge_groups(config)
        if not groups:
            console.print(render_info("No pending merge candidates."))
            return
        table = Table(title="Merge Candidates", show_lines=True)
        table.add_column("ID", style="dim", width=10)
        table.add_column("Members")
        table.add_column("Created")
        for g in groups:
            try:
                members = json.loads(g["member_fact_ids"])
            except (json.JSONDecodeError, TypeError):
                members = []
            table.add_row(g["id"][:8], str(len(members)), g["created_at"][:16])
        console.print(table)
        return

    subcmd = args[0]

    if subcmd == "approve" and len(args) >= 3 and args[1] == "--keep":
        gid = args[2]
        keep_idx = args.index("--keep") + 1
        if keep_idx >= len(args):
            console.print(render_error("Usage: /merge approve <group-id> --keep <fact-id>"))
            return
        keep_fid = args[keep_idx]
        try:
            result = apply_merge(config, gid, keep_fact_id=keep_fid, actor="shell")
            console.print(render_success(f"Approved merge {gid[:8]}, canonical: {keep_fid[:8]}"))
        except ValueError as e:
            console.print(render_error(str(e)))
        return

    if subcmd == "reject" and len(args) >= 2:
        gid = args[1]
        try:
            reject_merge(config, gid, actor="shell")
            console.print(render_success(f"Rejected merge group {gid[:8]}"))
        except ValueError as e:
            console.print(render_error(str(e)))
        return

    group = get_merge_group(config, subcmd)
    if group is None:
        console.print(render_error(f"Merge group not found: {subcmd}"))
        return

    facts = group.get("member_facts", [])
    if facts:
        console.print(render_fact_table(facts))
    console.print(f"[cyan]Group:[/cyan] {group['id']}")
    console.print(f"[cyan]Created:[/cyan] {group['created_at'][:16]}")


def handle_archive(workspace: Path, fact_id: str, console: Console) -> None:
    if not fact_id.strip():
        console.print(render_error("Fact ID required. Usage: /archive <id>"))
        return
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
        with connect(config.db_path) as conn:
            archive_fact(conn, fact_id=fact_id, actor="shell")
    except (WorkspaceNotInitializedError, ValueError) as e:
        console.print(render_error(str(e)))
        return

    console.print(render_success(f"Archived fact {fact_id[:8]}"))


def handle_explain_why(workspace: Path, entity_id: str, console: Console) -> None:
    if not entity_id.strip():
        console.print(render_error("ID required. Usage: /explain-why <contradiction_id|fact_id>"))
        return
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
        with connect(config.db_path) as conn:
            contra = conn.execute("SELECT * FROM contradictions WHERE id = ?", (entity_id,)).fetchone()
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return

    if contra:
        console.print(Panel(
            f"[bold]Contradiction:[/bold] {entity_id[:8]}\n"
            f"[bold]Reason:[/bold] {contra['reason']}\n"
            f"[bold]Score:[/bold] {contra['score']}\n"
            f"[bold]State:[/bold] {status_badge(contra['state'])}\n\n"
            f"Same subject + same predicate + different object = contradiction detected automatically.",
            title="Explain Why",
            border_style="yellow",
        ))
    else:
        with connect(config.db_path) as conn:
            fact = conn.execute("SELECT * FROM facts WHERE id = ?", (entity_id,)).fetchone()
        if fact:
            console.print(render_fact_panel(dict(fact)))
        else:
            console.print(render_error(f"Not found: {entity_id}"))


def handle_trace_source(workspace: Path, fact_id: str, console: Console) -> None:
    if not fact_id.strip():
        console.print(render_error("Fact ID required. Usage: /trace-source <id>"))
        return
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
        with connect(config.db_path) as conn:
            revisions = list_revisions(conn, entity_type="fact", entity_id=fact_id, limit=50)
    except WorkspaceNotInitializedError:
        console.print(render_error("Workspace not initialized. Run `saturn init` first."))
        return

    if not revisions:
        console.print(render_info(f"No revisions found for fact {fact_id[:8]}"))
        return

    console.print(render_revision_timeline([dict(r) for r in revisions]))


def handle_doctor(workspace: Path, console: Console) -> None:
    try:
        config = require_config(workspace)
    except WorkspaceNotInitializedError as e:
        console.print(render_error(str(e)))
        return
    result = run_doctor(config)
    if result.ok:
        console.print(render_success("\n".join(result.messages)))
    else:
        console.print(render_error("\n".join(result.messages)))


def handle_help(console: Console) -> None:
    console.print(render_help_table())
