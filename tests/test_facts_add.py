import sqlite3


def test_facts_add_persists_a_row(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn",
        "--predicate",
        "is",
        "--object",
        "a memory quality engine",
    )

    assert result.returncode == 0

    connection = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    row = connection.execute(
        "SELECT subject, predicate, object, confidence FROM facts"
    ).fetchone()
    assert row == ("Saturn", "is", "a memory quality engine", 0.8)


def test_facts_add_rejects_missing_required_fields(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(tmp_path, "facts", "add", "--subject", "Saturn")

    assert result.returncode != 0
    assert "--predicate" in result.stderr or "predicate" in result.stdout.lower()


def test_facts_add_fails_when_workspace_is_not_initialized(run_saturn, tmp_path):
    result = run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn",
        "--predicate",
        "is",
        "--object",
        "a memory quality engine",
    )

    assert result.returncode != 0
    assert "workspace is not initialized" in (result.stdout + result.stderr).lower()


def test_facts_add_fails_cleanly_when_workspace_db_is_missing_or_uninitialized(
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

    result = run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn",
        "--predicate",
        "is",
        "--object",
        "a memory quality engine",
    )

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace is not initialized" in output or "run `saturn init` first" in output
    assert "traceback" not in output


def test_facts_add_fails_cleanly_when_workspace_db_has_invalid_schema_shape(
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

    result = run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn",
        "--predicate",
        "is",
        "--object",
        "a memory quality engine",
    )

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace is not initialized" in output or "run `saturn init` first" in output
    assert "traceback" not in output


def test_facts_add_rejects_trimmed_empty_required_field(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "   ",
        "--predicate",
        "is",
        "--object",
        "a memory quality engine",
    )

    assert result.returncode != 0
    assert "subject" in (result.stdout + result.stderr).lower()


def test_facts_add_rejects_invalid_confidence(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    result = run_saturn(
        tmp_path,
        "facts",
        "add",
        "--subject",
        "Saturn",
        "--predicate",
        "is",
        "--object",
        "a memory quality engine",
        "--confidence",
        "1.1",
    )

    assert result.returncode != 0
    assert "confidence" in (result.stdout + result.stderr).lower()
