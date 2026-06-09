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
async def test_list_contradictions(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "Earth", "predicate": "is", "object": "flat",
        })
        await client.post("/api/facts", json={
            "subject": "Earth", "predicate": "is", "object": "round",
        })
        resp = await client.get("/api/contradictions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["state"] == "open"


@pytest.mark.asyncio
async def test_resolve_keep_a(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "A",
        })
        await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "B",
        })
        list_resp = await client.get("/api/contradictions")
        c_id = list_resp.json()[0]["id"]
        resp = await client.post(f"/api/contradictions/{c_id}/resolve", json={"action": "keep_a"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "resolved"


@pytest.mark.asyncio
async def test_resolve_invalid_action(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "A",
        })
        await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "B",
        })
        list_resp = await client.get("/api/contradictions")
        c_id = list_resp.json()[0]["id"]
        resp = await client.post(f"/api/contradictions/{c_id}/resolve", json={"action": "invalid"})
    assert resp.status_code == 400
