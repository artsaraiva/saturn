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
async def test_ingest_csv(init_workspace, tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("subject,predicate,object\nSaturn,is,great\n", encoding="utf-8")
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ingest", json={"path": str(csv_file)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["total_facts"] == 1


@pytest.mark.asyncio
async def test_ingest_missing_path(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ingest", json={"path": "/nonexistent/file.csv"})
    assert resp.status_code == 200
    assert resp.json()["stats"]["errors"] >= 1


@pytest.mark.asyncio
async def test_ingest_no_path(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ingest", json={})
    assert resp.status_code == 400
