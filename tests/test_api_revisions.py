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
async def test_list_revisions(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "A", "predicate": "is", "object": "B",
        })
        resp = await client.get("/api/revisions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["entity_type"] == "fact"


@pytest.mark.asyncio
async def test_get_revision(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "A", "predicate": "is", "object": "B",
        })
        list_resp = await client.get("/api/revisions")
        rev_id = list_resp.json()[0]["id"]
        resp = await client.get(f"/api/revisions/{rev_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == rev_id


@pytest.mark.asyncio
async def test_get_revision_not_found(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/revisions/nonexistent")
    assert resp.status_code == 404
