import sqlite3


def test_query_ranks_exact_and_multi_field_matches_first(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn",
        "--predicate",
        "is",
        "--object",
        "planet",
    )
    run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Tool",
        "--predicate",
        "describes",
        "--object",
        "Saturn",
    )
    run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn Tool",
        "--predicate",
        "supports",
        "--object",
        "Saturn",
    )

    result = run_saturn(tmp_path, "query", "Saturn")

    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert "Saturn Tool | supports | Saturn" in lines[0]
    assert "Saturn | is | planet" in lines[1]


def test_query_returns_success_for_empty_result(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(tmp_path, "query", "missing")

    assert result.returncode == 0
    assert "No matching facts found." in result.stdout


def test_query_rejects_whitespace_only_input(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(tmp_path, "query", "   ")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "query terms must not be empty" in output
    assert "traceback" not in output


def test_query_fails_when_workspace_is_not_initialized(run_saturn, tmp_path):
    result = run_saturn(tmp_path, "query", "Saturn")

    assert result.returncode != 0
    assert "workspace is not initialized" in (result.stdout + result.stderr).lower()


def test_query_requires_search_term(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(tmp_path, "query")

    assert result.returncode != 0
    assert "the following arguments are required: terms" in result.stderr.lower()
    assert "traceback" not in (result.stdout + result.stderr).lower()


def test_query_fails_cleanly_when_workspace_db_is_missing_or_uninitialized(
    run_saturn, tmp_path
):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    result = run_saturn(tmp_path, "query", "Saturn")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace is not initialized" in output or "run `saturn init` first" in output
    assert "traceback" not in output


def test_query_fails_cleanly_when_workspace_db_has_invalid_schema(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    connection = sqlite3.connect(workspace_dir / "saturn.db")
    connection.execute("CREATE TABLE facts (id TEXT PRIMARY KEY)")
    connection.execute(
        "CREATE TABLE schema_meta (version INTEGER NOT NULL, applied_at TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO schema_meta(version, applied_at) VALUES (?, ?)",
        (999, "2026-01-01T00:00:00+00:00"),
    )
    connection.commit()
    connection.close()

    result = run_saturn(tmp_path, "query", "Saturn")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace is not initialized" in output or "run `saturn init` first" in output
    assert "traceback" not in output


def test_query_fails_cleanly_when_workspace_db_has_invalid_schema_shape(
    run_saturn, tmp_path
):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    connection = sqlite3.connect(workspace_dir / "saturn.db")
    connection.execute("CREATE TABLE facts (id TEXT PRIMARY KEY)")
    connection.execute(
        "CREATE TABLE schema_meta (version INTEGER NOT NULL, applied_at TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO schema_meta(version, applied_at) VALUES (?, ?)",
        (1, "2026-01-01T00:00:00+00:00"),
    )
    connection.commit()
    connection.close()

    result = run_saturn(tmp_path, "query", "Saturn")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace is not initialized" in output or "run `saturn init` first" in output
    assert "traceback" not in output


def test_query_excludes_archived_facts(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    run_saturn(tmp_path, "facts", "add", "--subject", "Saturn", "--predicate", "is", "--object", "planet")

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    fact_id = conn.execute("SELECT id FROM facts WHERE subject = 'Saturn'").fetchone()[0]
    conn.execute("UPDATE facts SET status = 'archived' WHERE id = ?", (fact_id,))
    conn.commit()
    conn.close()

    result = run_saturn(tmp_path, "query", "Saturn")
    assert result.returncode == 0
    assert "No matching facts found" in result.stdout


def test_query_excludes_superseded_facts(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    run_saturn(tmp_path, "facts", "add", "--subject", "Saturn", "--predicate", "is", "--object", "planet")

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    fact_id = conn.execute("SELECT id FROM facts WHERE subject = 'Saturn'").fetchone()[0]
    conn.execute("UPDATE facts SET status = 'superseded' WHERE id = ?", (fact_id,))
    conn.commit()
    conn.close()

    result = run_saturn(tmp_path, "query", "Saturn")
    assert result.returncode == 0
    assert "No matching facts found" in result.stdout


def test_query_include_archived_flag(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    run_saturn(tmp_path, "facts", "add", "--subject", "Saturn", "--predicate", "is", "--object", "planet")

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    fact_id = conn.execute("SELECT id FROM facts WHERE subject = 'Saturn'").fetchone()[0]
    conn.execute("UPDATE facts SET status = 'archived' WHERE id = ?", (fact_id,))
    conn.commit()
    conn.close()

    result = run_saturn(tmp_path, "query", "Saturn", "--include-archived")
    assert result.returncode == 0
    assert "Saturn | is | planet" in result.stdout
