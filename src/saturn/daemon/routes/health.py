from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from saturn.config import WorkspaceNotInitializedError, load_config, resolve_workspace
from saturn.db import InvalidDatabaseError, connect, read_schema_version
from saturn.doctor import run_doctor

router = APIRouter(tags=["health"])


@router.get("/health")
async def get_health(request: Request) -> dict:
    workspace = getattr(request.app.state, "workspace", None) or Path.cwd()
    try:
        config = load_config(workspace)
        if not config.db_path.exists():
            return {"status": "uninitialized"}
        with connect(config.db_path) as conn:
            version = read_schema_version(conn)
            fact_count = conn.execute("SELECT COUNT(*) AS c FROM facts").fetchone()["c"]
            contradiction_count = conn.execute("SELECT COUNT(*) AS c FROM contradictions WHERE state='open'").fetchone()["c"]
        return {
            "status": "ok",
            "schema_version": version,
            "fact_count": fact_count,
            "open_contradictions": contradiction_count,
        }
    except (WorkspaceNotInitializedError, InvalidDatabaseError, FileNotFoundError):
        return {"status": "uninitialized"}
