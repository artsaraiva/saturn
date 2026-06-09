from __future__ import annotations

import argparse
from pathlib import Path
import sys

from saturn.config import (
    WorkspaceNotInitializedError,
    load_config,
    require_config,
    resolve_workspace,
    write_default_config,
)
from saturn.db import (
    InvalidDatabaseError,
    UnsupportedSchemaError,
    connect,
    initialize_database,
    require_initialized_database,
)
from saturn.doctor import bootstrap_project_status_docs, run_doctor
from saturn.facts import (
    archive_fact,
    build_fact_input,
    insert_fact,
    search_facts,
    update_fact,
)
from saturn.ingest import IngestResult, run_ingest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="saturn")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")

    facts_parser = subparsers.add_parser("facts")
    facts_subparsers = facts_parser.add_subparsers(dest="facts_command", required=True)
    facts_add_parser = facts_subparsers.add_parser("add")
    facts_add_parser.add_argument("--subject", required=True)
    facts_add_parser.add_argument("--predicate", required=True)
    facts_add_parser.add_argument("--object", dest="object_", required=True)
    facts_add_parser.add_argument("--source")
    facts_add_parser.add_argument("--confidence", type=float)

    facts_update_parser = facts_subparsers.add_parser("update")
    facts_update_parser.add_argument("fact_id")
    facts_update_parser.add_argument("--subject")
    facts_update_parser.add_argument("--predicate")
    facts_update_parser.add_argument("--object", dest="object_")
    facts_update_parser.add_argument("--source")
    facts_update_parser.add_argument("--confidence", type=float)

    facts_archive_parser = facts_subparsers.add_parser("archive")
    facts_archive_parser.add_argument("fact_id")

    daemon_parser = subparsers.add_parser("daemon")
    daemon_subparsers = daemon_parser.add_subparsers(dest="daemon_command", required=True)

    daemon_start = daemon_subparsers.add_parser("start")
    daemon_start.add_argument("--host", default="127.0.0.1")
    daemon_start.add_argument("--port", type=int, default=8468)

    daemon_subparsers.add_parser("stop")
    daemon_subparsers.add_parser("status")

    daemon_logs = daemon_subparsers.add_parser("logs")
    daemon_logs.add_argument("--lines", type=int, default=50)

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("terms")
    query_parser.add_argument("--include-archived", action="store_true")

    subparsers.add_parser("shell")

    subparsers.add_parser("doctor")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("path", help="File or directory to ingest")
    ingest_parser.add_argument("--source", help="Override source for all facts")
    ingest_parser.add_argument("--dry-run", action="store_true", help="Preview without storing")
    ingest_parser.add_argument("--verbose", action="store_true", help="Show per-fact details")
    ingest_parser.add_argument("--format", choices=["csv", "tsv", "json", "txt"],
                                help="Force input format (default: auto-detect by extension)")

    contradictions_parser = subparsers.add_parser("contradictions")
    contradictions_subparsers = contradictions_parser.add_subparsers(dest="contradictions_command", required=True)

    contradictions_list_parser = contradictions_subparsers.add_parser("list")
    contradictions_list_parser.add_argument("--all", action="store_true")

    contradictions_resolve_parser = contradictions_subparsers.add_parser("resolve")
    contradictions_resolve_parser.add_argument("contradiction_id")
    contradictions_resolve_parser.add_argument("--action", required=True, choices=["keep_a", "keep_b", "merge", "dismiss", "defer"])
    contradictions_resolve_parser.add_argument("--object", dest="merged_object")
    revisions_parser = subparsers.add_parser("revisions")
    revisions_subparsers = revisions_parser.add_subparsers(dest="revisions_command", required=True)

    revisions_list_parser = revisions_subparsers.add_parser("list")
    revisions_list_parser.add_argument("--entity-type", choices=["fact", "contradiction"])
    revisions_list_parser.add_argument("--entity-id")
    revisions_list_parser.add_argument("--limit", type=int, default=50)

    revisions_show_parser = revisions_subparsers.add_parser("show")
    revisions_show_parser.add_argument("revision_id")

    maintain_parser = subparsers.add_parser("maintain")
    maintain_sub = maintain_parser.add_subparsers(dest="maintain_command", required=True)
    run_parser = maintain_sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    run_parser.add_argument("--archive-days", type=int, default=90, help="Archive facts older than N days (default: 90)")

    export_parser = subparsers.add_parser("export")
    export_sub = export_parser.add_subparsers(dest="export_command", required=True)
    graph_parser = export_sub.add_parser("graph")
    graph_parser.add_argument("--format", choices=["json", "dot"], default="json")
    graph_parser.add_argument("--output", "-o", help="Output file path (default: stdout)")

    wiki_parser = subparsers.add_parser("wiki")
    wiki_sub = wiki_parser.add_subparsers(dest="wiki_command", required=True)
    wiki_build_parser = wiki_sub.add_parser("build")
    wiki_build_parser.add_argument("--out", help="Output directory for wiki files")
    wiki_serve_parser = wiki_sub.add_parser("serve")
    wiki_serve_parser.add_argument("--port", type=int, default=8080)

    return parser


def handle_init() -> int:
    project_root = Path.cwd()
    workspace = resolve_workspace(project_root)
    if not workspace.config_path.exists():
        write_default_config(workspace)
    config = load_config(project_root)
    initialize_database(config.db_path, config.schema_version)
    bootstrap_project_status_docs(project_root)
    print(f"Initialized Saturn workspace at {config.workspace_dir}")
    return 0


def handle_facts_add(args: argparse.Namespace) -> int:
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    fact = build_fact_input(
        args.subject,
        args.predicate,
        args.object_,
        args.source,
        args.confidence,
    )
    with connect(config.db_path) as connection:
        fact_id = insert_fact(connection, fact)
    print(f"Stored fact {fact_id}")
    return 0


def handle_facts_update(args: argparse.Namespace) -> int:
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        update_fact(connection, fact_id=args.fact_id, subject=args.subject,
                     predicate=args.predicate, object=args.object_,
                     source=args.source, confidence=args.confidence, actor="cli")
    print(f"Updated fact {args.fact_id}")
    return 0


def handle_facts_archive(args: argparse.Namespace) -> int:
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        archive_fact(connection, fact_id=args.fact_id, actor="cli")
    print(f"Archived fact {args.fact_id}")
    return 0


def handle_query(args: argparse.Namespace) -> int:
    if not args.terms.strip():
        raise ValueError("Query terms must not be empty.")
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        rows = search_facts(connection, args.terms, include_archived=args.include_archived)

    if not rows:
        print("No matching facts found.")
        return 0

    for row in rows:
        print(f"{row.subject} | {row.predicate} | {row.object}")
    return 0


def handle_doctor() -> int:
    project_root = Path.cwd()
    workspace = resolve_workspace(project_root)
    config = load_config(project_root) if workspace.config_path.exists() else workspace
    result = run_doctor(config)
    for message in result.messages:
        print(message)
    return 0 if result.ok else 1


def handle_ingest(args: argparse.Namespace) -> int:
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    result = run_ingest(
        args.path,
        source=args.source,
        dry_run=args.dry_run,
        verbose=args.verbose,
        format=args.format,
        config=config,
    )
    for message in result.messages:
        print(message)

    s = result.stats
    total = s.total_files
    if s.errors > 0 or s.skipped > 0:
        parts = [f"Processed {s.total_files} file(s), {s.total_facts} fact(s)"]
        if s.errors:
            parts.append(f"{s.errors} error(s)")
        if s.skipped:
            parts.append(f"{s.skipped} skipped")
        print(", ".join(parts))
        return 1
    if total == 0:
        print("No supported files found.")
        return 1
    print(f"Ingested {s.total_facts} fact(s) from {s.total_files} file(s).")
    return 0


def handle_daemon(args: argparse.Namespace) -> int:
    from saturn.daemon.lifecycle import start, stop, status, logs
    project_root = Path.cwd()
    if args.daemon_command == "start":
        print(start(project_root, host=args.host, port=args.port))
    elif args.daemon_command == "stop":
        print(stop(project_root))
    elif args.daemon_command == "status":
        print(status(project_root))
    elif args.daemon_command == "logs":
        print(logs(project_root, lines=args.lines))
    return 0


def handle_contradictions_list(args: argparse.Namespace) -> int:
    from saturn.contradictions import list_contradictions
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        state = None if args.all else "open"
        contradictions = list_contradictions(connection, state=state)
    if not contradictions:
        print("No contradictions found.")
        return 0
    print(f"{'ID':<8} | {'Fact A':<30} | {'Fact B':<30} | {'State':<10} | Created")
    print("-" * 100)
    for c in contradictions:
        fa = f"{c['fact_a_subject']} | {c['fact_a_predicate']} | {c['fact_a_object']}"
        fb = f"{c['fact_b_subject']} | {c['fact_b_predicate']} | {c['fact_b_object']}"
        if len(fa) > 28: fa = fa[:25] + "..."
        if len(fb) > 28: fb = fb[:25] + "..."
        print(f"{c['id']} | {fa:<30} | {fb:<30} | {c['state']:<10} | {c['resolved_at'] or 'N/A'}")
    return 0

def handle_contradictions_resolve(args: argparse.Namespace) -> int:
    from saturn.contradictions import resolve_contradiction
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        resolve_contradiction(connection, contradiction_id=args.contradiction_id,
                              action=args.action, merged_object=args.merged_object, actor="cli")
    print(f"Resolved contradiction {args.contradiction_id} with action: {args.action}")
    return 0


def handle_revisions_list(args: argparse.Namespace) -> int:
    from saturn.revisions import list_revisions
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        revisions = list_revisions(connection, entity_type=args.entity_type,
                                    entity_id=args.entity_id, limit=args.limit)
    if not revisions:
        print("No revisions found.")
        return 0

    print(f"{'ID':<8} | {'Entity Type':<15} | {'Entity ID':<8} | {'Change Type':<12} | {'Actor':<10} | Timestamp")
    print("-" * 90)
    for r in revisions:
        print(f"{r['id']} | {r['entity_type']:<15} | {r['entity_id'][:8]:<8} | {r['change_type']:<12} | {r['actor']:<10} | {r['timestamp']}")
    return 0


def handle_shell() -> int:
    from saturn.shell.app import run_shell
    return run_shell(Path.cwd())


def handle_maintain(args: argparse.Namespace) -> int:
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    from saturn.maintain import run_maintenance
    if args.maintain_command == "run":
        stats = run_maintenance(config, dry_run=args.dry_run, archive_days=args.archive_days)
        print(f"Maintenance complete:")
        print(f"  Contradictions found: {stats['contradictions_found']}")
        print(f"  Archived: {stats['archived']}")
        if stats['errors']:
            print(f"  Errors: {stats['errors']}")
    return 0


def handle_export(args: argparse.Namespace) -> int:
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    from saturn.export.graph import export_json, export_dot
    if args.export_command == "graph":
        if args.format == "json":
            output = export_json(config)
        else:
            output = export_dot(config)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Exported to {args.output}")
        else:
            print(output)
    return 0


def handle_wiki(args: argparse.Namespace) -> int:
    from saturn.wiki.builder import build_wiki, serve_wiki
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    if args.wiki_command == "build":
        wiki_dir = Path(args.out) if args.out else None
        out = build_wiki(config, wiki_dir)
        print(f"Wiki generated at {out}")
    elif args.wiki_command == "serve":
        serve_wiki(config, port=args.port)
    return 0


def handle_revisions_show(args: argparse.Namespace) -> int:
    import json
    from saturn.revisions import get_revision
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        revision = get_revision(connection, args.revision_id)
    if revision is None:
        print(f"Revision not found: {args.revision_id}")
        return 1
    print(f"Revision: {revision['id']}")
    print(f"Entity: {revision['entity_type']} {revision['entity_id']}")
    print(f"Change: {revision['change_type']}")
    print(f"Actor: {revision['actor']}")
    print(f"Timestamp: {revision['timestamp']}")
    print()
    if revision['before'] is not None:
        print("Before:")
        print(json.dumps(json.loads(revision['before']), indent=2))
        print()
    if revision['after'] is not None:
        print("After:")
        print(json.dumps(json.loads(revision['after']), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "init":
            return handle_init()
        if args.command == "facts":
            if args.facts_command == "add":
                return handle_facts_add(args)
            if args.facts_command == "update":
                return handle_facts_update(args)
            if args.facts_command == "archive":
                return handle_facts_archive(args)
        if args.command == "query":
            return handle_query(args)
        if args.command == "doctor":
            return handle_doctor()
        if args.command == "ingest":
            return handle_ingest(args)
        if args.command == "contradictions":
            if args.contradictions_command == "list":
                return handle_contradictions_list(args)
            if args.contradictions_command == "resolve":
                return handle_contradictions_resolve(args)
        if args.command == "revisions":
            if args.revisions_command == "list":
                return handle_revisions_list(args)
            if args.revisions_command == "show":
                return handle_revisions_show(args)
        if args.command == "daemon":
            return handle_daemon(args)
        if args.command == "shell":
            return handle_shell()
        if args.command == "maintain":
            return handle_maintain(args)
        if args.command == "export":
            return handle_export(args)
        if args.command == "wiki":
            return handle_wiki(args)
        return 0
    except WorkspaceNotInitializedError as error:
        print(str(error))
        return 1
    except UnsupportedSchemaError as error:
        print(str(error))
        return 1
    except InvalidDatabaseError as error:
        print(str(error))
        return 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
