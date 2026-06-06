import sqlite3


def test_doctor_reports_missing_config(run_saturn, tmp_path):
    result = run_saturn(tmp_path, "doctor")

    assert result.returncode != 0
    assert "workspace is not initialized" in (result.stdout + result.stderr).lower()


def test_doctor_reports_missing_database(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    (tmp_path / ".saturn" / "saturn.db").unlink()

    result = run_saturn(tmp_path, "doctor")

    assert result.returncode != 0
    assert "database file is missing" in (result.stdout + result.stderr).lower()


def test_doctor_uses_existing_configured_database_path(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    (workspace_dir / "config.toml").write_text(
        'schema_version = 999\n'
        'db_path = "state/custom.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    assert run_saturn(tmp_path, "init").returncode == 0
    assert (tmp_path / "state" / "custom.db").exists()
    assert not (tmp_path / ".saturn" / "saturn.db").exists()

    result = run_saturn(tmp_path, "doctor")

    assert result.returncode == 0
    assert "workspace health: ok" in result.stdout.lower()


def test_doctor_reports_unsupported_schema(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    connection = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    connection.execute("DELETE FROM schema_meta")
    connection.execute(
        "INSERT INTO schema_meta(version, applied_at) VALUES(99, '2026-06-06T00:00:00+00:00')"
    )
    connection.commit()
    connection.close()

    result = run_saturn(tmp_path, "doctor")

    assert result.returncode != 0
    assert "unsupported schema version" in (result.stdout + result.stderr).lower()


def test_doctor_fails_cleanly_for_invalid_or_partial_database(run_saturn, tmp_path):
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

    result = run_saturn(tmp_path, "doctor")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace database is invalid" in output
    assert "traceback" not in output


def test_doctor_fails_cleanly_for_invalid_schema_shape(run_saturn, tmp_path):
    workspace_dir = tmp_path / ".saturn"
    workspace_dir.mkdir()
    db_path = workspace_dir / "saturn.db"
    (workspace_dir / "config.toml").write_text(
        'schema_version = 1\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )

    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE facts (id TEXT PRIMARY KEY)")
    connection.execute(
        "CREATE TABLE schema_meta (version INTEGER NOT NULL, applied_at TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO schema_meta(version, applied_at) VALUES(1, '2026-06-06T00:00:00+00:00')"
    )
    connection.commit()
    connection.close()

    result = run_saturn(tmp_path, "doctor")

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "workspace database is invalid" in output
    assert "traceback" not in output


def test_doctor_recreates_missing_project_status_docs(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    (tmp_path / "docs" / "superpowers" / "project-status.md").unlink()
    (tmp_path / "docs" / "superpowers" / "project-status.json").unlink()

    result = run_saturn(tmp_path, "doctor")

    assert result.returncode == 0
    assert (tmp_path / "docs" / "superpowers" / "project-status.md").exists()
    assert (tmp_path / "docs" / "superpowers" / "project-status.json").exists()
