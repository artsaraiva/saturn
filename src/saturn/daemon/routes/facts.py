from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from saturn.config import WorkspaceNotInitializedError, require_config
from saturn.db import connect, require_initialized_database
from saturn.facts import (
    archive_fact,
    build_fact_input,
    insert_fact,
    update_fact,
)

router = APIRouter(prefix="/facts", tags=["facts"])


def _get_config(request: Request):
    workspace = getattr(request.app.state, "workspace", None) or Path.cwd()
    try:
        return require_config(workspace)
    except WorkspaceNotInitializedError:
        raise HTTPException(status_code=400, detail="Workspace not initialized. Run `saturn init` first.")


def _ensure_db(config):
    try:
        require_initialized_database(config.db_path, config.schema_version)
    except WorkspaceNotInitializedError:
        raise HTTPException(status_code=400, detail="Workspace not initialized. Run `saturn init` first.")


@router.post("", status_code=201)
async def create_fact(request: Request, body: dict) -> dict:
    config = _get_config(request)
    _ensure_db(config)
    try:
        fact_input = build_fact_input(
            subject=body.get("subject", ""),
            predicate=body.get("predicate", ""),
            object_=body.get("object", ""),
            source=body.get("source"),
            confidence=body.get("confidence"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    def _insert():
        with connect(config.db_path) as conn:
            fact_id = insert_fact(conn, fact_input)
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            return dict(row)

    result = await asyncio.to_thread(_insert)
    return result


@router.get("")
async def list_facts(request: Request, status: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
    config = _get_config(request)
    _ensure_db(config)

    def _list():
        with connect(config.db_path) as conn:
            sql = "SELECT * FROM facts WHERE 1=1"
            params = []
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.append(limit)
            params.append(offset)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    return await asyncio.to_thread(_list)


@router.get("/{fact_id}")
async def get_fact(request: Request, fact_id: str) -> dict:
    config = _get_config(request)
    _ensure_db(config)

    def _get():
        with connect(config.db_path) as conn:
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Fact not found")
            return dict(row)

    return await asyncio.to_thread(_get)


@router.patch("/{fact_id}")
async def update_fact_route(request: Request, fact_id: str, body: dict) -> dict:
    config = _get_config(request)
    _ensure_db(config)

    def _update():
        with connect(config.db_path) as conn:
            try:
                update_fact(
                    conn,
                    fact_id=fact_id,
                    subject=body.get("subject"),
                    predicate=body.get("predicate"),
                    object=body.get("object"),
                    source=body.get("source"),
                    confidence=body.get("confidence"),
                    actor="api",
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Fact not found")
            return dict(row)

    return await asyncio.to_thread(_update)


@router.post("/{fact_id}/archive")
async def archive_fact_route(request: Request, fact_id: str) -> dict:
    config = _get_config(request)
    _ensure_db(config)

    def _archive():
        with connect(config.db_path) as conn:
            try:
                archive_fact(conn, fact_id=fact_id, actor="api")
            except ValueError as e:
                if "already archived" in str(e):
                    raise HTTPException(status_code=409, detail=str(e))
                raise HTTPException(status_code=404, detail=str(e))
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            return dict(row)

    return await asyncio.to_thread(_archive)
