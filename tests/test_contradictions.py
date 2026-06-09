import sqlite3
from saturn.db import connect
from saturn.facts import build_fact_input, insert_fact
from saturn.contradictions import detect_contradictions, list_contradictions, resolve_contradiction
from saturn.revisions import list_revisions


def test_detect_contradiction_on_insert(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1 = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact1_id = insert_fact(conn, fact1)
        fact2 = build_fact_input("Saturn", "is", "star", None, 0.8)
        fact2_id = insert_fact(conn, fact2)
        contradictions = list_contradictions(conn, state="open")
        assert len(contradictions) == 1
        assert contradictions[0]["fact_a_id"] == fact1_id
        assert contradictions[0]["fact_b_id"] == fact2_id
        assert contradictions[0]["state"] == "open"


def test_no_contradiction_when_object_matches(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.9))
        assert len(list_contradictions(conn, state="open")) == 0


def test_no_contradiction_when_subject_differs(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        insert_fact(conn, build_fact_input("Jupiter", "is", "star", None, 0.8))
        assert len(list_contradictions(conn, state="open")) == 0


def test_no_contradiction_when_predicate_differs(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        insert_fact(conn, build_fact_input("Saturn", "has", "rings", None, 0.8))
        assert len(list_contradictions(conn, state="open")) == 0


def test_detect_contradiction_on_update(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.facts import update_fact
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        fact2_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        update_fact(conn, fact2_id, object="star")
        contradictions = list_contradictions(conn, state="open")
        assert len(contradictions) == 1
        assert contradictions[0]["fact_a_id"] == fact1_id
        assert contradictions[0]["fact_b_id"] == fact2_id


def test_resolve_keep_a(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        fact2_id = insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="keep_a", actor="cli")
        f1 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact1_id,)).fetchone()
        f2 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact2_id,)).fetchone()
        c = conn.execute("SELECT state, resolution_type FROM contradictions WHERE id = ?", (cid,)).fetchone()
        assert f1["status"] == "active"
        assert f2["status"] == "superseded"
        assert c["state"] == "resolved"
        assert c["resolution_type"] == "keep_a"


def test_resolve_keep_b(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        fact2_id = insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="keep_b", actor="cli")
        f1 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact1_id,)).fetchone()
        f2 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact2_id,)).fetchone()
        assert f1["status"] == "superseded"
        assert f2["status"] == "active"


def test_resolve_merge(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        fact2_id = insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="merge", merged_object="planet with rings", actor="cli")
        f1 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact1_id,)).fetchone()
        f2 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact2_id,)).fetchone()
        assert f1["status"] == "superseded"
        assert f2["status"] == "superseded"
        merged = conn.execute("SELECT * FROM facts WHERE subject = 'Saturn' AND status = 'active'").fetchone()
        assert merged is not None
        assert merged["object"] == "planet with rings"


def test_resolve_dismiss(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        fact2_id = insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="dismiss", actor="cli")
        f1 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact1_id,)).fetchone()
        f2 = conn.execute("SELECT status FROM facts WHERE id = ?", (fact2_id,)).fetchone()
        c = conn.execute("SELECT state FROM contradictions WHERE id = ?", (cid,)).fetchone()
        assert f1["status"] == "active"
        assert f2["status"] == "active"
        assert c["state"] == "dismissed"


def test_resolve_defer(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="defer", actor="cli")
        c = conn.execute("SELECT state FROM contradictions WHERE id = ?", (cid,)).fetchone()
        assert c["state"] == "open"


def test_resolve_rejects_non_open(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="keep_a", actor="cli")
        try:
            resolve_contradiction(conn, cid, action="keep_b", actor="cli")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already resolved" in str(e).lower() or "already" in str(e).lower()


def test_resolve_rejects_invalid_action(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        try:
            resolve_contradiction(conn, cid, action="invalid", actor="cli")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "invalid action" in str(e).lower()


def test_resolve_creates_revisions(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact1_id = insert_fact(conn, build_fact_input("Saturn", "is", "planet", None, 0.8))
        fact2_id = insert_fact(conn, build_fact_input("Saturn", "is", "star", None, 0.8))
        cid = list_contradictions(conn, state="open")[0]["id"]
        resolve_contradiction(conn, cid, action="keep_a", actor="cli")
        c_revs = list_revisions(conn, entity_type="contradiction", entity_id=cid)
        f2_revs = list_revisions(conn, entity_type="fact", entity_id=fact2_id)
        assert len(c_revs) == 1
        assert c_revs[0]["change_type"] == "resolved"
        assert len(f2_revs) == 2
        assert f2_revs[0]["change_type"] == "superseded"
