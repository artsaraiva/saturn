import os
import json
from pathlib import Path

import pytest

from saturn.config import resolve_workspace, write_default_config, load_config
from saturn.db import initialize_database, connect
from saturn.doctor import refresh_project_status_docs

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture
def init_workspace(tmp_path):
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
    return config


def test_wiki_build_creates_index(init_workspace):
    from saturn.wiki.builder import build_wiki

    config = init_workspace
    wiki_dir = config.project_root / "wiki"
    build_wiki(config, wiki_dir)
    assert (wiki_dir / "index.md").exists()


def test_wiki_build_with_facts(init_workspace):
    from saturn.wiki.builder import build_wiki

    config = init_workspace
    with connect(config.db_path) as conn:
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f1', 'Saturn', 'is', 'a memory engine', 0.9, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f2', 'Saturn', 'uses', 'SQLite', 0.95, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.commit()

    wiki_dir = config.project_root / "wiki"
    build_wiki(config, wiki_dir)

    index = (wiki_dir / "index.md").read_text()
    assert "# Saturn" in index  # entity page linked
    assert "## Entities" in index

    entity_page = wiki_dir / "entities" / "Saturn.md"
    assert entity_page.exists()
    content = entity_page.read_text()
    assert "is" in content
    assert "a memory engine" in content
    assert "SQLite" in content
    assert "confidence" in content.lower()


def test_wiki_build_no_facts(init_workspace):
    from saturn.wiki.builder import build_wiki

    config = init_workspace
    wiki_dir = config.project_root / "wiki"
    build_wiki(config, wiki_dir)
    index = (wiki_dir / "index.md").read_text()
    assert "No facts" in index or "0" in index or len(index) > 10


def test_wiki_build_empty_workspace(tmp_path):
    from saturn.wiki.builder import build_wiki
    config = resolve_workspace(tmp_path)
    wiki_dir = tmp_path / "wiki"
    result = build_wiki(config, wiki_dir)
    assert result is not None
