import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from saturn.config import write_default_config, resolve_workspace
from saturn.db import initialize_database


@pytest.mark.asyncio
async def test_health_ok(tmp_path):
    _init_workspace(tmp_path)
    os.chdir(tmp_path)

    from saturn.daemon.app import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "schema_version" in data
    assert "fact_count" in data


@pytest.mark.asyncio
async def test_health_not_initialized(tmp_path):
    os.chdir(tmp_path)
    from saturn.daemon.app import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uninitialized"


def _init_workspace(tmp_path: Path) -> None:
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    from saturn.config import load_config
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
