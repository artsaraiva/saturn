from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from saturn.config import write_default_config, resolve_workspace, load_config
from saturn.db import initialize_database


@pytest.fixture
def init_workspace(tmp_path):
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
    return tmp_path


@pytest.mark.asyncio
async def test_query_returns_results(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "Saturn", "predicate": "is", "object": "a memory engine",
        })
        await client.post("/api/facts", json={
            "subject": "Saturn", "predicate": "runs", "object": "on SQLite",
        })
        resp = await client.post("/api/query", json={"terms": "Saturn"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_query_empty_terms(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/query", json={"terms": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_query_no_results(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/query", json={"terms": "zzzznonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []
