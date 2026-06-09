from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from saturn.config import WorkspaceNotInitializedError, require_config
from saturn.db import connect, require_initialized_database
from saturn.contradictions import list_contradictions, resolve_contradiction

router = APIRouter(prefix="/contradictions", tags=["contradictions"])


def _get_config(request: Request):
    workspace = getattr(request.app.state, "workspace", None) or Path.cwd()
    try:
        return require_config(workspace)
    except WorkspaceNotInitializedError:
        raise HTTPException(status_code=400, detail="Workspace not initialized.")


@router.get("")
async def get_contradictions(request: Request, state: str | None = None, limit: int = 100) -> list[dict]:
    config = _get_config(request)
    require_initialized_database(config.db_path, config.schema_version)

    def _list():
        with connect(config.db_path) as conn:
            rows = list_contradictions(conn, state=state, limit=limit)
            return [dict(r) for r in rows]

    return await asyncio.to_thread(_list)


@router.get("/{contradiction_id}")
async def get_contradiction(request: Request, contradiction_id: str) -> dict:
    config = _get_config(request)
    require_initialized_database(config.db_path, config.schema_version)

    def _get():
        with connect(config.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM contradictions WHERE id = ?", (contradiction_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Contradiction not found")
            return dict(row)

    return await asyncio.to_thread(_get)


@router.post("/{contradiction_id}/resolve")
async def resolve_contradiction_route(request: Request, contradiction_id: str, body: dict) -> dict:
    config = _get_config(request)
    require_initialized_database(config.db_path, config.schema_version)
    action = body.get("action")
    if not action:
        raise HTTPException(status_code=400, detail="action is required")

    def _resolve():
        with connect(config.db_path) as conn:
            try:
                resolve_contradiction(
                    conn,
                    contradiction_id=contradiction_id,
                    action=action,
                    merged_object=body.get("object"),
                    actor="api",
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            row = conn.execute(
                "SELECT * FROM contradictions WHERE id = ?", (contradiction_id,)
            ).fetchone()
            return dict(row)

    return await asyncio.to_thread(_resolve)
