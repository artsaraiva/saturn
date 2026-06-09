import json
import os
import subprocess
import sys
import time
from pathlib import Path
import pytest

from saturn.config import resolve_workspace, write_default_config, load_config
from saturn.db import initialize_database, connect


@pytest.fixture
def init_workspace(tmp_path):
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
    return tmp_path


def _mcp_json(method: str, params: dict | None = None, id: int | None = None) -> str:
    if id is not None:
        req = {"jsonrpc": "2.0", "id": id, "method": method}
    else:
        req = {"jsonrpc": "2.0", "method": method}
    if params:
        req["params"] = params
    return json.dumps(req)


def test_mcp_list_tools(init_workspace):
    cwd = str(init_workspace)
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, %r)
from saturn.daemon.mcp_server import main
main()
""" % src_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )

    init_req = _mcp_json("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0.1.0"},
    }, id=1)
    notif = _mcp_json("notifications/initialized")
    list_req = _mcp_json("tools/list", id=2)
    stdin_data = init_req + "\n" + notif + "\n" + list_req + "\n"
    out, err = proc.communicate(input=stdin_data, timeout=5)
    lines = out.strip().split("\n")
    assert len(lines) >= 2
    result = json.loads(lines[1])
    tools = result.get("result", {}).get("tools", [])
    tool_names = [t["name"] for t in tools]
    assert "saturn_store_fact" in tool_names
    assert "saturn_query" in tool_names
    assert "saturn_get_contradictions" in tool_names
    assert "saturn_resolve_contradiction" in tool_names
    assert "saturn_maintain" in tool_names
    assert "saturn_health" in tool_names


def test_mcp_store_and_query(init_workspace):
    cwd = str(init_workspace)
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    init_req = _mcp_json("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0.1.0"},
    }, id=1)
    notif = _mcp_json("notifications/initialized")
    store_req = _mcp_json("tools/call", {
        "name": "saturn_store_fact",
        "arguments": {
            "subject": "MCP", "predicate": "is", "object": "working",
            "source": "test", "confidence": 0.9,
        },
    }, id=2)

    proc = subprocess.Popen(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, %r)
from saturn.daemon.mcp_server import main
main()
""" % src_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )

    stdin_data = init_req + "\n" + notif + "\n" + store_req + "\n"
    out, err = proc.communicate(input=stdin_data, timeout=5)
    lines = out.strip().split("\n")
    store_result = json.loads(lines[1])
    assert store_result.get("id") == 2
    result_data = json.loads(store_result["result"]["content"][0]["text"])
    assert result_data["subject"] == "MCP"

    proc2 = subprocess.Popen(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, %r)
from saturn.daemon.mcp_server import main
main()
""" % src_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )

    query_req = _mcp_json("tools/call", {
        "name": "saturn_query",
        "arguments": {"query": "MCP"},
    }, id=2)
    stdin_data = init_req + "\n" + notif + "\n" + query_req + "\n"
    out, err = proc2.communicate(input=stdin_data, timeout=5)
    lines = out.strip().split("\n")
    result = json.loads(lines[1])
    facts = json.loads(result["result"]["content"][0]["text"])
    assert len(facts) >= 1
    assert facts[0]["subject"] == "MCP"


def test_mcp_health(init_workspace):
    cwd = str(init_workspace)
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, %r)
from saturn.daemon.mcp_server import main
main()
""" % src_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )

    init_req = _mcp_json("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0.1.0"},
    }, id=1)
    notif = _mcp_json("notifications/initialized")
    health_req = _mcp_json("tools/call", {
        "name": "saturn_health",
        "arguments": {},
    }, id=2)
    stdin_data = init_req + "\n" + notif + "\n" + health_req + "\n"
    out, err = proc.communicate(input=stdin_data, timeout=5)
    lines = out.strip().split("\n")
    assert len(lines) >= 2
    result = json.loads(lines[1])
    result_data = json.loads(result["result"]["content"][0]["text"])
    assert result_data["status"] == "ok"
