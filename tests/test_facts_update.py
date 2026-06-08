import sqlite3
from saturn.db import connect
from saturn.facts import build_fact_input, insert_fact, update_fact
from saturn.revisions import list_revisions


def test_update_fact_changes_subject(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        update_fact(conn, fact_id, subject="Jupiter")
        row = conn.execute("SELECT subject FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row["subject"] == "Jupiter"


def test_update_fact_changes_multiple_fields(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        update_fact(conn, fact_id, subject="Jupiter", object="gas giant", confidence=0.9)
        row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
        assert row["subject"] == "Jupiter"
        assert row["object"] == "gas giant"
        assert row["confidence"] == 0.9


def test_update_fact_creates_revision(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        update_fact(conn, fact_id, object="gas giant")
        revisions = list_revisions(conn, entity_type="fact", entity_id=fact_id)
        assert len(revisions) == 2
        assert revisions[0]["change_type"] == "updated"
        assert '"object": "planet"' in revisions[0]["before"]
        assert '"object": "gas giant"' in revisions[0]["after"]


def test_update_fact_rejects_archived(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        conn.execute("UPDATE facts SET status = 'archived' WHERE id = ?", (fact_id,))
        conn.commit()
        try:
            update_fact(conn, fact_id, object="gas giant")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "archived" in str(e).lower()


def test_update_fact_rejects_superseded(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)
        conn.execute("UPDATE facts SET status = 'superseded' WHERE id = ?", (fact_id,))
        conn.commit()
        try:
            update_fact(conn, fact_id, object="gas giant")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "superseded" in str(e).lower()


def test_update_fact_not_found(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        try:
            update_fact(conn, "nonexistent", object="gas giant")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not found" in str(e).lower()
