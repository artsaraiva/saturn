import sqlite3


def test_init_creates_workspace_files(run_saturn, tmp_path):
    result = run_saturn(tmp_path, "init")

    assert result.returncode == 0
    assert (tmp_path / ".saturn" / "config.toml").exists()
    assert (tmp_path / ".saturn" / "saturn.db").exists()
    assert (tmp_path / "docs" / "superpowers" / "project-status.md").exists()
    assert (tmp_path / "docs" / "superpowers" / "project-status.json").exists()

    with sqlite3.connect(tmp_path / ".saturn" / "saturn.db") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        schema_version = connection.execute(
            "SELECT version FROM schema_meta"
        ).fetchone()[0]

    assert "facts" in tables
    assert "schema_meta" in tables
    assert schema_version == 1


def test_init_does_not_overwrite_existing_project_status_docs(run_saturn, tmp_path):
    status_dir = tmp_path / "docs" / "superpowers"
    status_dir.mkdir(parents=True)
    markdown_file = status_dir / "project-status.md"
    json_file = status_dir / "project-status.json"
    markdown_file.write_text("keep me\n", encoding="utf-8")
    json_file.write_text('{"keep": true}\n', encoding="utf-8")

    result = run_saturn(tmp_path, "init")

    assert result.returncode == 0
    assert markdown_file.read_text(encoding="utf-8") == "keep me\n"
    assert json_file.read_text(encoding="utf-8") == '{"keep": true}\n'


def test_init_uses_existing_configured_database_path(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 999\n'
        'db_path = "state/custom.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    result = run_saturn(tmp_path, "init")

    assert result.returncode == 0
    assert (tmp_path / "state" / "custom.db").exists()
    assert not (tmp_path / ".saturn" / "saturn.db").exists()

    with sqlite3.connect(tmp_path / "state" / "custom.db") as connection:
        schema_version = connection.execute(
            "SELECT version FROM schema_meta"
        ).fetchone()[0]

    assert schema_version == 1


def test_init_fails_when_database_schema_version_does_not_match_config(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    with sqlite3.connect(workspace_dir / "saturn.db") as connection:
        connection.execute(
            "CREATE TABLE facts ("
            "id TEXT PRIMARY KEY, "
            "subject TEXT NOT NULL, "
            "predicate TEXT NOT NULL, "
            "object TEXT NOT NULL, "
            "source TEXT, "
            "confidence REAL NOT NULL DEFAULT 0.8, "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL"
            ")"
        )
        connection.execute(
            "CREATE TABLE schema_meta (version INTEGER NOT NULL, applied_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO schema_meta(version, applied_at) VALUES(?, ?)",
            (999, "2026-01-01T00:00:00+00:00"),
        )
        connection.commit()

    result = run_saturn(tmp_path, "init")

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "schema version" in output
    assert "999" in output
    assert "1" in output

    with sqlite3.connect(workspace_dir / "saturn.db") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        schema_rows = connection.execute(
            "SELECT version FROM schema_meta"
        ).fetchall()

    assert tables == {"facts", "schema_meta"}
    assert schema_rows == [(999,)]


def test_init_fails_cleanly_for_invalid_existing_database_file(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    db_path = workspace_dir / "saturn.db"
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )
    db_path.write_text("not a sqlite database", encoding="utf-8")

    result = run_saturn(tmp_path, "init")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace database is invalid" in output
    assert "traceback" not in output


def test_init_fails_cleanly_for_malformed_existing_schema_meta(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    with sqlite3.connect(workspace_dir / "saturn.db") as connection:
        connection.execute("CREATE TABLE schema_meta (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_meta(version) VALUES(1)")
        connection.commit()

    result = run_saturn(tmp_path, "init")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace database is invalid" in output
    assert "traceback" not in output


def test_init_fails_cleanly_for_malformed_or_incomplete_config(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    result = run_saturn(tmp_path, "init")

    assert result.returncode != 0
    assert "invalid config" in result.stderr.lower()
