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
from saturn.facts import build_fact_input, insert_fact, search_facts


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

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("terms")

    subparsers.add_parser("doctor")
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


def handle_query(args: argparse.Namespace) -> int:
    if not args.terms.strip():
        raise ValueError("Query terms must not be empty.")
    config = require_config(Path.cwd())
    require_initialized_database(config.db_path, config.schema_version)
    with connect(config.db_path) as connection:
        rows = search_facts(connection, args.terms)

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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "init":
            return handle_init()
        if args.command == "facts" and args.facts_command == "add":
            return handle_facts_add(args)
        if args.command == "query":
            return handle_query(args)
        if args.command == "doctor":
            return handle_doctor()
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
