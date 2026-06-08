import sqlite3
from saturn.db import connect
from saturn.facts import build_fact_input, insert_fact, archive_fact
from saturn.revisions import list_revisions


def test_archive_fact_sets_status(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        archive_fact(conn, fact_id)
        row = conn.execute("SELECT status FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row["status"] == "archived"


def test_archive_fact_creates_revision(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        archive_fact(conn, fact_id)
        revisions = list_revisions(conn, entity_type="fact", entity_id=fact_id)
        assert len(revisions) == 2  # created + archived
        assert revisions[0]["change_type"] == "archived"
        assert '"status": "active"' in revisions[0]["before"]
        assert revisions[0]["after"] is None


def test_archive_fact_rejects_already_archived(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        archive_fact(conn, fact_id)
        try:
            archive_fact(conn, fact_id)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already archived" in str(e).lower()


def test_archive_fact_not_found(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        try:
            archive_fact(conn, "nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not found" in str(e).lower()
