from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from saturn.config import require_config, WorkspaceNotInitializedError
from saturn.db import connect, require_initialized_database
from saturn.facts import search_facts

router = APIRouter(prefix="/query", tags=["query"])


@router.post("")
async def query_facts(request: Request, body: dict) -> list[dict]:
    workspace = getattr(request.app.state, "workspace", None) or Path.cwd()
    try:
        config = require_config(workspace)
    except WorkspaceNotInitializedError:
        raise HTTPException(status_code=400, detail="Workspace not initialized.")
    require_initialized_database(config.db_path, config.schema_version)

    terms = body.get("terms", "").strip()
    if not terms:
        raise HTTPException(status_code=400, detail="Query terms must not be empty.")

    def _search():
        with connect(config.db_path) as conn:
            rows = search_facts(
                conn,
                terms,
                include_archived=body.get("include_archived", False),
            )
            return [asdict(r) for r in rows]

    results = await asyncio.to_thread(_search)
    return results
