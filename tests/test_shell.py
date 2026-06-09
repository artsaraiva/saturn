import os
import subprocess
import sys
import time

import pytest

from saturn.config import resolve_workspace, write_default_config, load_config
from saturn.db import initialize_database

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


def _run_shell(cwd, commands: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    src_path = os.path.join(REPO_ROOT, "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    stdin = "\n".join(commands) + "\n/exit\n"
    return subprocess.run(
        [sys.executable, "-m", "saturn", "shell"],
        cwd=cwd,
        input=stdin,
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )


@pytest.fixture
def init_workspace(tmp_path):
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
    return tmp_path


def test_shell_help_shows_commands(init_workspace):
    result = _run_shell(init_workspace, ["/help"])
    assert "/search" in result.stdout
    assert "/contradictions" in result.stdout
    assert "/resolve" in result.stdout


def test_shell_search_returns_output(init_workspace):
    result = _run_shell(init_workspace, [
        "/search Saturn",
    ])
    output = result.stdout + result.stderr
    assert "Saturn" in output or "Facts" in output or "No matching" in output
    assert result.returncode == 0


def test_shell_search_and_show(init_workspace):
    from saturn.daemon.app import create_app
    from httpx import AsyncClient, ASGITransport
    import asyncio

    async def _add():
        app = create_app(init_workspace)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/facts", json={
                "subject": "Earth", "predicate": "is", "object": "a planet",
            })
            return resp.json()["id"]

    fid = asyncio.run(_add())

    result = _run_shell(init_workspace, [
        "/show-fact " + fid,
    ])
    assert "Earth" in result.stdout
    assert "a planet" in result.stdout


def test_shell_contradictions(init_workspace):
    from saturn.daemon.app import create_app
    from httpx import AsyncClient, ASGITransport
    import asyncio

    async def _setup():
        app = create_app(init_workspace)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/facts", json={
                "subject": "X", "predicate": "is", "object": "A",
            })
            await client.post("/api/facts", json={
                "subject": "X", "predicate": "is", "object": "B",
            })

    asyncio.run(_setup())

    result = _run_shell(init_workspace, [
        "/contradictions",
    ])
    assert "open" in result.stdout.lower()


def test_shell_doctor(init_workspace):
    result = _run_shell(init_workspace, ["/doctor"])
    assert "OK" in result.stdout or "ok" in result.stdout.lower()


def test_shell_uninitialized_shows_error(tmp_path):
    result = _run_shell(tmp_path, ["/search test"])
    assert "not initialized" in (result.stdout + result.stderr).lower()


def test_shell_unknown_command(init_workspace):
    result = _run_shell(init_workspace, ["/foobar"])
    assert "unknown" in (result.stdout + result.stderr).lower()


def test_shell_merge_shows_candidates(init_workspace):
    from saturn.daemon.app import create_app
    from httpx import AsyncClient, ASGITransport
    import asyncio

    async def _setup():
        app = create_app(init_workspace)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/facts", json={
                "subject": "MergeTest", "predicate": "has_color", "object": "red",
            })
            await client.post("/api/facts", json={
                "subject": "MergeTest", "predicate": "has_color", "object": "blue",
            })

    asyncio.run(_setup())

    result = _run_shell(init_workspace, ["/merge"])
    output = result.stdout + result.stderr
    assert "MergeTest" in output
