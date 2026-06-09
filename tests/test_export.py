import json
import os
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
    with connect(config.db_path) as conn:
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f1', 'Saturn', 'is', 'a memory engine', 0.9, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f2', 'Saturn', 'uses', 'SQLite', 0.95, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f3', 'Python', 'is', 'a language', 0.8, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.commit()
    return config


def test_export_json_returns_nodes_and_edges(init_workspace):
    from saturn.export.graph import export_json
    config = init_workspace
    result = export_json(config)
    data = json.loads(result)
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 2  # Saturn, Python
    assert len(data["edges"]) >= 3  # 3 facts


def test_export_json_node_structure(init_workspace):
    from saturn.export.graph import export_json
    config = init_workspace
    data = json.loads(export_json(config))
    for node in data["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "fact_count" in node
    for edge in data["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "predicate" in edge
        assert "fact_id" in edge


def test_export_dot_returns_graphviz_format(init_workspace):
    from saturn.export.graph import export_dot
    config = init_workspace
    dot = export_dot(config)
    assert dot.startswith("digraph")
    assert "Saturn" in dot
    assert "Python" in dot


def test_export_empty_workspace(tmp_path):
    from saturn.export.graph import export_json, export_dot
    config = resolve_workspace(tmp_path)
    result = export_json(config)
    assert json.loads(result) == {"nodes": [], "edges": []}
    dot = export_dot(config)
    assert "digraph Saturn" in dot
