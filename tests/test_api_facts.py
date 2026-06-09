# tests/test_api_facts.py
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
async def test_create_fact(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/facts", json={
            "subject": "Saturn", "predicate": "is", "object": "a memory engine",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == "Saturn"
    assert data["predicate"] == "is"
    assert data["object"] == "a memory engine"
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_fact_missing_field(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/facts", json={"subject": "Saturn"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_facts(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/facts", json={
            "subject": "A", "predicate": "is", "object": "X",
        })
        await client.post("/api/facts", json={
            "subject": "B", "predicate": "is", "object": "Y",
        })
        resp = await client.get("/api/facts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_fact(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "Y",
        })
        fact_id = create.json()["id"]
        resp = await client.get(f"/api/facts/{fact_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == fact_id


@pytest.mark.asyncio
async def test_get_fact_not_found(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/facts/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_fact(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "Y",
        })
        fact_id = create.json()["id"]
        resp = await client.patch(f"/api/facts/{fact_id}", json={"object": "Z"})
    assert resp.status_code == 200
    assert resp.json()["object"] == "Z"


@pytest.mark.asyncio
async def test_archive_fact(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "Y",
        })
        fact_id = create.json()["id"]
        resp = await client.post(f"/api/facts/{fact_id}/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_already_archived(init_workspace):
    from saturn.daemon.app import create_app
    app = create_app(init_workspace)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post("/api/facts", json={
            "subject": "X", "predicate": "is", "object": "Y",
        })
        fact_id = create.json()["id"]
        await client.post(f"/api/facts/{fact_id}/archive")
        resp = await client.post(f"/api/facts/{fact_id}/archive")
    assert resp.status_code == 409
