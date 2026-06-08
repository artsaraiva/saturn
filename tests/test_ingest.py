import csv
import json
import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

CSV_DATA = """\
subject,predicate,object,source,confidence
Saturn,is,memory quality engine,spec,0.9
Saturn,uses,SQLite,architecture,0.8
Saturn,supports,CLI,design,0.7
"""


def test_ingest_csv_file(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(CSV_DATA, encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path))
    assert result.returncode == 0
    assert "3 fact(s) from 1 file(s)" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    rows = conn.execute("SELECT subject, predicate, object, confidence FROM facts").fetchall()
    conn.close()
    assert len(rows) == 3
    assert ("Saturn", "is", "memory quality engine", 0.9) in rows
    assert ("Saturn", "uses", "SQLite", 0.8) in rows
    assert ("Saturn", "supports", "CLI", 0.7) in rows


# ---------------------------------------------------------------------------
# TSV
# ---------------------------------------------------------------------------

TSV_DATA = "subject\tpredicate\tobject\nTool\tdescribes\tSaturn\n"


def test_ingest_tsv_file(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    tsv_path = tmp_path / "test.tsv"
    tsv_path.write_text(TSV_DATA, encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(tsv_path))
    assert result.returncode == 0
    assert "1 fact(s) from 1 file(s)" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    row = conn.execute(
        "SELECT subject, predicate, object FROM facts"
    ).fetchone()
    conn.close()
    assert row == ("Tool", "describes", "Saturn")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

JSON_DATA = [
    {"subject": "Test", "predicate": "is", "object": "working", "confidence": 0.95},
    {"subject": "Test", "predicate": "has", "object": "tests", "source": "qa"},
]


def test_ingest_json_file(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    json_path = tmp_path / "test.json"
    json_path.write_text(json.dumps(JSON_DATA), encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(json_path))
    assert result.returncode == 0
    assert "2 fact(s) from 1 file(s)" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    rows = conn.execute(
        "SELECT subject, predicate, object, source, confidence FROM facts"
    ).fetchall()
    conn.close()
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# Plain text
# ---------------------------------------------------------------------------

TEXT_DATA = "First line of notes\nSecond line\nThird entry\n"


def test_ingest_text_file(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    text_path = tmp_path / "notes.txt"
    text_path.write_text(TEXT_DATA, encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(text_path))
    assert result.returncode == 0
    assert "3 fact(s) from 1 file(s)" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    rows = conn.execute(
        "SELECT subject, predicate, object FROM facts"
    ).fetchall()
    conn.close()
    assert ("notes", "contains", "First line of notes") in rows
    assert ("notes", "contains", "Second line") in rows
    assert ("notes", "contains", "Third entry") in rows


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------


def test_ingest_directory(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "a.csv").write_text("subject,predicate,object\nX,is,Y\n", encoding="utf-8")
    (data_dir / "b.csv").write_text("subject,predicate,object\nA,has,B\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(data_dir))
    assert result.returncode == 0
    assert "2 fact(s) from 2 file(s)" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    conn.close()
    assert count == 2


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_ingest_dry_run(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(CSV_DATA, encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path), "--dry-run")
    assert result.returncode == 0
    assert "DRY-RUN" in result.stdout
    assert "3 fact(s) would be stored" in result.stdout

    # Nothing should have been stored
    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    conn.close()
    assert count == 0


def test_ingest_dry_run_verbose(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(CSV_DATA, encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path), "--dry-run", "--verbose")
    assert result.returncode == 0
    assert "DRY-RUN" in result.stdout
    assert "Saturn | is | memory quality engine" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    conn.close()
    assert count == 0


# ---------------------------------------------------------------------------
# Source override
# ---------------------------------------------------------------------------


def test_ingest_source_override(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("subject,predicate,object\nSaturn,is,great\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path), "--source", "my-custom-source")
    assert result.returncode == 0

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    row = conn.execute("SELECT source FROM facts").fetchone()
    conn.close()
    assert row[0] == "my-custom-source"


# ---------------------------------------------------------------------------
# Verbose output
# ---------------------------------------------------------------------------


def test_ingest_verbose_output(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("subject,predicate,object\nX,is,Y\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path), "--verbose")
    assert result.returncode == 0
    assert "STORED" in result.stdout
    assert "X | is | Y" in result.stdout


# ---------------------------------------------------------------------------
# Workspace not initialized
# ---------------------------------------------------------------------------


def test_ingest_fails_without_init(run_saturn, tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("subject,predicate,object\nX,is,Y\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path))
    assert result.returncode != 0
    assert "workspace is not initialized" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# Non-existent file
# ---------------------------------------------------------------------------


def test_ingest_non_existent_file(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    result = run_saturn(tmp_path, "ingest", str(tmp_path / "nonexistent.csv"))
    assert result.returncode != 0
    assert "path does not exist" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# Unsupported format
# ---------------------------------------------------------------------------


def test_ingest_unsupported_format(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    docx_path = tmp_path / "notes.docx"
    docx_path.write_text("fake docx", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(docx_path))
    assert result.returncode != 0
    assert "unsupported file extension" in result.stdout.lower()


def test_ingest_unsupported_forced_format(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("subject,predicate,object\nX,is,Y\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path), "--format", "json")
    assert result.returncode != 0
    assert "error" in result.stdout.lower()
    assert "processed" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Mixed success/failure
# ---------------------------------------------------------------------------


def test_ingest_mixed_success_failure(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    data_dir = tmp_path / "mix"
    data_dir.mkdir()
    (data_dir / "good.csv").write_text("subject,predicate,object\nOk,works,well\n", encoding="utf-8")
    bad_csv = data_dir / "bad.csv"
    bad_csv.write_text("subject,predicate\nmissing,object-column\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(data_dir))
    assert result.returncode != 0
    assert "error(s)" in result.stdout
    assert "STORED" in result.stdout
    assert "1 fact(s)" in result.stdout

    conn = sqlite3.connect(tmp_path / ".saturn" / "saturn.db")
    count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    conn.close()
    assert count == 1  # only the good one


# ---------------------------------------------------------------------------
# Empty file / no facts in directory
# ---------------------------------------------------------------------------


def test_ingest_empty_directory(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = run_saturn(tmp_path, "ingest", str(empty_dir))
    assert result.returncode != 0
    assert "No supported files found" in result.stdout

# ---------------------------------------------------------------------------
# CSV missing required columns
# ---------------------------------------------------------------------------


def test_ingest_csv_missing_columns_error(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("subject,predicate\nX,is\n", encoding="utf-8")

    result = run_saturn(tmp_path, "ingest", str(csv_path))
    assert result.returncode != 0
    assert "missing required columns" in result.stdout.lower()
