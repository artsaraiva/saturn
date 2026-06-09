from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

from saturn.config import load_config, require_config, WorkspaceNotInitializedError
from saturn.db import connect, require_initialized_database
from saturn.facts import FactInput, build_fact_input, insert_fact, search_facts
from saturn.contradictions import list_contradictions, resolve_contradiction
from saturn.revisions import list_revisions
from saturn.doctor import run_doctor


server = Server("saturn")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="saturn_store_fact",
            description="Store a new fact with source and confidence",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subject of the fact"},
                    "predicate": {"type": "string", "description": "Predicate/relationship"},
                    "object": {"type": "string", "description": "Object of the fact"},
                    "source": {"type": "string", "description": "Source of this fact"},
                    "confidence": {"type": "number", "description": "Confidence 0.0-1.0"},
                },
                "required": ["subject", "predicate", "object"],
            },
        ),
        Tool(
            name="saturn_query",
            description="Query Saturn for relevant facts",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "max_results": {"type": "number", "description": "Maximum results"},
                    "min_confidence": {"type": "number", "description": "Minimum confidence filter"},
                    "include_disputed": {"type": "boolean", "description": "Include disputed facts"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="saturn_get_contradictions",
            description="Get open contradictions needing resolution",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "open/resolved/all"},
                    "limit": {"type": "number", "description": "Max results"},
                },
            },
        ),
        Tool(
            name="saturn_resolve_contradiction",
            description="Resolve a contradiction between two facts",
            inputSchema={
                "type": "object",
                "properties": {
                    "contradiction_id": {"type": "string", "description": "Contradiction ID"},
                    "action": {
                        "type": "string",
                        "description": "keep_a/keep_b/merge/dismiss/defer",
                        "enum": ["keep_a", "keep_b", "merge", "dismiss", "defer"],
                    },
                    "object": {"type": "string", "description": "Merged object (required for merge action)"},
                },
                "required": ["contradiction_id", "action"],
            },
        ),
        Tool(
            name="saturn_maintain",
            description="Trigger maintenance operations (stub in this slice)",
            inputSchema={
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Operations to run",
                    },
                    "dry_run": {"type": "boolean"},
                },
            },
        ),
        Tool(
            name="saturn_health",
            description="Get memory health metrics",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    workspace = Path.cwd()
    try:
        config = require_config(workspace)
        require_initialized_database(config.db_path, config.schema_version)
    except WorkspaceNotInitializedError:
        return [TextContent(type="text", text='{"error": "Workspace not initialized. Run `saturn init` first."}')]

    if name == "saturn_store_fact":
        args = arguments or {}
        try:
            fact_input = build_fact_input(
                subject=args.get("subject", ""),
                predicate=args.get("predicate", ""),
                object_=args.get("object", ""),
                source=args.get("source"),
                confidence=args.get("confidence"),
            )
        except ValueError as e:
            return [TextContent(type="text", text=f'{{"error": "{e}"}}')]
        with connect(config.db_path) as conn:
            fact_id = insert_fact(conn, fact_input)
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
        return [TextContent(type="text", text=str(dict(row)).replace("'", '"'))]

    elif name == "saturn_query":
        args = arguments or {}
        query = args.get("query", "").strip()
        if not query:
            return [TextContent(type="text", text='{"error": "Query is required"}')]
        with connect(config.db_path) as conn:
            rows = search_facts(conn, query)
        results = [asdict(r) for r in rows]
        max_results = args.get("max_results") or len(results)
        results = results[: int(max_results)]
        return [TextContent(type="text", text=str(results).replace("'", '"'))]

    elif name == "saturn_get_contradictions":
        args = arguments or {}
        state = args.get("state")
        if state == "all":
            state = None
        limit = args.get("limit", 50)
        with connect(config.db_path) as conn:
            rows = list_contradictions(conn, state=state, limit=int(limit))
        return [TextContent(type="text", text=str([dict(r) for r in rows]).replace("'", '"'))]

    elif name == "saturn_resolve_contradiction":
        args = arguments or {}
        c_id = args.get("contradiction_id", "")
        action = args.get("action", "")
        if not c_id or not action:
            return [TextContent(type="text", text='{"error": "contradiction_id and action are required"}')]
        try:
            with connect(config.db_path) as conn:
                resolve_contradiction(conn, c_id, action, merged_object=args.get("object"), actor="mcp")
            return [TextContent(type="text", text=f'{{"status": "resolved", "contradiction_id": "{c_id}", "action": "{action}"}}')]
        except ValueError as e:
            return [TextContent(type="text", text=f'{{"error": "{e}"}}')]

    elif name == "saturn_maintain":
        return [TextContent(type="text", text='{"status": "not_implemented", "message": "Maintenance not yet implemented"}')]

    elif name == "saturn_health":
        result = run_doctor(config)
        return [TextContent(type="text", text=str({"status": "ok" if result.ok else "unhealthy", "messages": result.messages}).replace("'", '"'))]

    return [TextContent(type="text", text=f'{{"error": "Unknown tool: {name}"}}')]


def main():
    import anyio
    from mcp.server.stdio import stdio_server

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="saturn",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    anyio.run(_run)


if __name__ == "__main__":
    main()
