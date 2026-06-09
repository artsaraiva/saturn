from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from saturn.config import WorkspaceNotInitializedError, require_config
from saturn.db import connect, require_initialized_database
from saturn.revisions import get_revision, list_revisions

router = APIRouter(prefix="/revisions", tags=["revisions"])


def _get_config(request: Request):
    workspace = getattr(request.app.state, "workspace", None) or Path.cwd()
    try:
        return require_config(workspace)
    except WorkspaceNotInitializedError:
        raise HTTPException(status_code=400, detail="Workspace not initialized.")


@router.get("")
async def get_revisions(
    request: Request,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    config = _get_config(request)
    require_initialized_database(config.db_path, config.schema_version)

    def _list():
        with connect(config.db_path) as conn:
            rows = list_revisions(conn, entity_type=entity_type, entity_id=entity_id, limit=limit)
            return [dict(r) for r in rows]

    return await asyncio.to_thread(_list)


@router.get("/{revision_id}")
async def get_revision_route(request: Request, revision_id: str) -> dict:
    config = _get_config(request)
    require_initialized_database(config.db_path, config.schema_version)

    def _get():
        with connect(config.db_path) as conn:
            row = get_revision(conn, revision_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Revision not found")
            return dict(row)

    return await asyncio.to_thread(_get)
