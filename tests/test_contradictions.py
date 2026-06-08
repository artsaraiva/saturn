import sqlite3
from saturn.db import connect
from saturn.facts import build_fact_input, insert_fact
from saturn.contradictions import detect_contradictions, list_contradictions


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
