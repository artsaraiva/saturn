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
            "VALUES ('f2', 'Saturn', 'is', 'a data tool', 0.7, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f3', 'Python', 'is', 'a language', 0.8, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.commit()
    return config


def test_maintain_run_detects_contradictions(init_workspace):
    from saturn.maintain import run_maintenance
    config = init_workspace
    result = run_maintenance(config)
    assert result["contradictions_found"] >= 1


def test_maintain_run_no_changes(init_workspace):
    from saturn.maintain import run_maintenance
    config = init_workspace
    result1 = run_maintenance(config)
    assert result1["contradictions_found"] >= 1
    result2 = run_maintenance(config)
    assert result2["contradictions_found"] == 0 or result2["contradictions_found"] == result1["contradictions_found"]


def test_maintain_run_dry_run(init_workspace):
    from saturn.maintain import run_maintenance
    config = init_workspace
    result = run_maintenance(config, dry_run=True)
    assert result["contradictions_found"] >= 1
    with connect(config.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM contradictions").fetchone()["c"]
    assert count == 0


def test_maintain_run_archives_stale(init_workspace):
    from saturn.maintain import run_maintenance
    config = init_workspace
    with connect(config.db_path) as conn:
        conn.execute(
            "UPDATE facts SET updated_at = '2020-01-01T00:00:00' WHERE id = 'f3'"
        )
        conn.commit()
    result = run_maintenance(config, archive_days=30)
    assert result["archived"] >= 1
    with connect(config.db_path) as conn:
        row = conn.execute("SELECT status FROM facts WHERE id = 'f3'").fetchone()
    assert row["status"] == "archived"
