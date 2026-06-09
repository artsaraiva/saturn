from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from saturn.config import WorkspaceNotInitializedError, require_config
from saturn.ingest import IngestResult, run_ingest

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("")
async def ingest_route(request: Request, body: dict) -> dict:
    workspace = getattr(request.app.state, "workspace", None) or Path.cwd()
    try:
        config = require_config(workspace)
    except WorkspaceNotInitializedError:
        raise HTTPException(status_code=400, detail="Workspace not initialized.")

    path_str = body.get("path", "").strip()
    if not path_str:
        raise HTTPException(status_code=400, detail="path is required")

    def _ingest():
        result: IngestResult = run_ingest(
            path_str,
            source=body.get("source"),
            dry_run=body.get("dry_run", False),
            verbose=body.get("verbose", False),
            format=body.get("format"),
            config=config,
        )
        return {
            "stats": {
                "total_files": result.stats.total_files,
                "total_facts": result.stats.total_facts,
                "errors": result.stats.errors,
                "skipped": result.stats.skipped,
            },
            "messages": result.messages,
        }

    return await asyncio.to_thread(_ingest)
