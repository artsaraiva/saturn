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
    return config


@pytest.fixture
def with_duplicates(init_workspace):
    """Two facts with same subject+predicate, similar objects."""
    config = init_workspace
    with connect(config.db_path) as conn:
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f1', 'Saturn', 'is', 'a memory engine', 0.9, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f2', 'Saturn', 'is', 'a memory quality engine', 0.85, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f3', 'Python', 'is', 'a language', 0.8, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.commit()
    return config


def test_suggest_merges_finds_duplicates(with_duplicates):
    from saturn.merge import suggest_merges
    groups = suggest_merges(with_duplicates, min_similarity=0.5)
    assert len(groups) >= 1
    members = json.loads(groups[0]["member_fact_ids"])
    assert "f1" in members
    assert "f2" in members


def test_suggest_merges_respects_threshold(with_duplicates):
    from saturn.merge import suggest_merges
    groups = suggest_merges(with_duplicates, min_similarity=0.99)
    assert len(groups) == 0


def test_suggest_merges_skips_existing_groups(with_duplicates):
    from saturn.merge import suggest_merges
    config = with_duplicates
    groups1 = suggest_merges(config, min_similarity=0.5)
    assert len(groups1) >= 1
    groups2 = suggest_merges(config, min_similarity=0.5)
    assert len(groups2) == 0


def test_suggest_merges_no_duplicates(init_workspace):
    from saturn.merge import suggest_merges
    config = init_workspace
    with connect(config.db_path) as conn:
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f1', 'Saturn', 'is', 'a memory engine', 0.9, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.execute(
            "INSERT INTO facts (id, subject, predicate, object, confidence, status, created_at, updated_at) "
            "VALUES ('f2', 'Earth', 'is', 'a planet', 0.9, 'active', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.commit()
    groups = suggest_merges(config, min_similarity=0.5)
    assert len(groups) == 0


def test_apply_merge_archives_other_facts(with_duplicates):
    from saturn.merge import suggest_merges, apply_merge
    config = with_duplicates
    groups = suggest_merges(config, min_similarity=0.5)
    assert len(groups) >= 1

    gid = groups[0]["id"]
    result = apply_merge(config, gid, keep_fact_id="f1", actor="test")

    assert result["canonical_fact_id"] == "f1"
    assert result["merge_strategy"] == "keep"

    with connect(config.db_path) as conn:
        f1 = dict(conn.execute("SELECT * FROM facts WHERE id = 'f1'").fetchone())
        f2 = dict(conn.execute("SELECT * FROM facts WHERE id = 'f2'").fetchone())
        assert f1["status"] == "active"
        assert f2["status"] == "archived"


def test_apply_merge_invalid_keep_fact(with_duplicates):
    from saturn.merge import suggest_merges, apply_merge
    config = with_duplicates
    groups = suggest_merges(config, min_similarity=0.5)
    gid = groups[0]["id"]
    with pytest.raises(ValueError, match="not a member"):
        apply_merge(config, gid, keep_fact_id="nonexistent")


def test_apply_merge_already_resolved(with_duplicates):
    from saturn.merge import suggest_merges, apply_merge
    config = with_duplicates
    groups = suggest_merges(config, min_similarity=0.5)
    gid = groups[0]["id"]
    apply_merge(config, gid, keep_fact_id="f1", actor="test")
    with pytest.raises(ValueError, match="already resolved"):
        apply_merge(config, gid, keep_fact_id="f1", actor="test")


def test_reject_merge_marks_dismissed(with_duplicates):
    from saturn.merge import suggest_merges, reject_merge
    config = with_duplicates
    groups = suggest_merges(config, min_similarity=0.5)
    gid = groups[0]["id"]
    result = reject_merge(config, gid, actor="test")
    assert result["merge_strategy"] == "reject"

    with connect(config.db_path) as conn:
        f1 = dict(conn.execute("SELECT status FROM facts WHERE id = 'f1'").fetchone())
        assert f1["status"] == "active"


def test_list_merge_groups(with_duplicates):
    from saturn.merge import suggest_merges, list_merge_groups, apply_merge
    config = with_duplicates
    suggest_merges(config, min_similarity=0.5)

    pending = list_merge_groups(config)
    assert len(pending) >= 1

    all_groups = list_merge_groups(config, all_=True)
    assert len(all_groups) >= 1


def test_get_merge_group(with_duplicates):
    from saturn.merge import suggest_merges, get_merge_group
    config = with_duplicates
    groups = suggest_merges(config, min_similarity=0.5)
    gid = groups[0]["id"]
    detail = get_merge_group(config, gid)
    assert detail is not None
    assert "member_facts" in detail
    assert len(detail["member_facts"]) >= 2
