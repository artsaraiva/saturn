import pytest
import sqlite3
from saturn.db import connect
from saturn.revisions import insert_revision, list_revisions, get_revision


def test_insert_revision_creates_row(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        revision_id = insert_revision(
            conn,
            entity_type="fact",
            entity_id="fact-123",
            change_type="created",
            before=None,
            after={"subject": "Saturn", "predicate": "is", "object": "planet"},
            actor="cli",
        )

        row = conn.execute(
            "SELECT entity_type, entity_id, change_type, before, after, actor FROM revisions WHERE id = ?",
            (revision_id,),
        ).fetchone()

        assert row["entity_type"] == "fact"
        assert row["entity_id"] == "fact-123"
        assert row["change_type"] == "created"
        assert row["before"] is None
        assert '"subject": "Saturn"' in row["after"]
        assert row["actor"] == "cli"


def test_list_revisions_returns_newest_first(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_revision(conn, "fact", "f1", "created", None, {"s": "A"}, "cli")
        insert_revision(conn, "fact", "f2", "created", None, {"s": "B"}, "cli")
        insert_revision(conn, "fact", "f1", "updated", {"s": "A"}, {"s": "A2"}, "cli")

        revisions = list_revisions(conn, entity_type="fact")

        assert len(revisions) == 3
        assert revisions[0]["entity_id"] == "f1"
        assert revisions[0]["change_type"] == "updated"
        assert revisions[1]["entity_id"] == "f2"
        assert revisions[2]["entity_id"] == "f1"
        assert revisions[2]["change_type"] == "created"


def test_list_revisions_filters_by_entity_id(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_revision(conn, "fact", "f1", "created", None, {"s": "A"}, "cli")
        insert_revision(conn, "fact", "f2", "created", None, {"s": "B"}, "cli")

        revisions = list_revisions(conn, entity_type="fact", entity_id="f1")

        assert len(revisions) == 1
        assert revisions[0]["entity_id"] == "f1"


def test_get_revision_returns_full_details(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        revision_id = insert_revision(
            conn,
            "fact",
            "f1",
            "updated",
            {"subject": "Old"},
            {"subject": "New"},
            "cli",
        )

        revision = get_revision(conn, revision_id)

        assert revision["id"] == revision_id
        assert revision["entity_type"] == "fact"
        assert revision["change_type"] == "updated"
        assert '"subject": "Old"' in revision["before"]
        assert '"subject": "New"' in revision["after"]


def test_insert_revision_rejects_empty_entity_type(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        with pytest.raises(ValueError, match="entity_type must not be empty"):
            insert_revision(conn, "  ", "f1", "created", None, {"s": "A"}, "cli")


def test_get_timeline_returns_ordered_revisions(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.db import connect
    from saturn.revisions import insert_revision, get_timeline

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_revision(conn, "fact", "f1", "created", None, {"s": "A"}, "cli")
        insert_revision(conn, "fact", "f1", "updated", {"s": "A"}, {"s": "B"}, "cli")

        timeline = get_timeline(conn, entity_id="f1")
        assert len(timeline) == 2
        assert timeline[0]["change_type"] == "updated"


def test_get_timeline_filters_by_actor(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.db import connect
    from saturn.revisions import insert_revision, get_timeline

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_revision(conn, "fact", "f1", "created", None, {"s": "A"}, "cli")
        insert_revision(conn, "fact", "f1", "updated", {"s": "A"}, {"s": "B"}, "maintain")

        timeline = get_timeline(conn, entity_id="f1", actor="cli")
        assert len(timeline) == 1
        assert timeline[0]["actor"] == "cli"


def test_get_timeline_filters_by_change_type(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.db import connect
    from saturn.revisions import insert_revision, get_timeline

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        insert_revision(conn, "fact", "f1", "created", None, {"s": "A"}, "cli")
        insert_revision(conn, "fact", "f1", "updated", {"s": "A"}, {"s": "B"}, "cli")

        timeline = get_timeline(conn, entity_id="f1", change_type="created")
        assert len(timeline) == 1
        assert timeline[0]["change_type"] == "created"


def test_get_timeline_filters_by_date_range(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.db import connect
    from saturn.revisions import get_timeline
    from datetime import UTC, datetime, timedelta

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        import uuid
        now = datetime.now(UTC)
        rid1 = str(uuid.uuid4())
        rid2 = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO revisions (id, entity_type, entity_id, change_type, before, after, actor, timestamp) "
            "VALUES (?, 'fact', 'f1', 'created', NULL, '{}', 'cli', ?)",
            (rid1, (now - timedelta(days=10)).isoformat()),
        )
        conn.execute(
            "INSERT INTO revisions (id, entity_type, entity_id, change_type, before, after, actor, timestamp) "
            "VALUES (?, 'fact', 'f1', 'updated', '{}', '{}', 'cli', ?)",
            (rid2, (now - timedelta(days=1)).isoformat()),
        )
        conn.commit()

        since = (now - timedelta(days=5)).isoformat()
        timeline = get_timeline(conn, entity_id="f1", since=since)
        assert len(timeline) == 1
        assert timeline[0]["change_type"] == "updated"


def test_get_timeline_pagination(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.db import connect
    from saturn.revisions import insert_revision, get_timeline

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        for i in range(5):
            insert_revision(conn, "fact", "f1", "created", None, {"s": str(i)}, "cli")

        page1 = get_timeline(conn, entity_id="f1", limit=2, offset=0)
        assert len(page1) == 2

        page2 = get_timeline(conn, entity_id="f1", limit=2, offset=2)
        assert len(page2) == 2
        assert page1[0]["id"] != page2[0]["id"]


def test_get_timeline_empty_for_nonexistent_entity(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")
    from saturn.db import connect
    from saturn.revisions import get_timeline

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        timeline = get_timeline(conn, entity_id="nonexistent")
        assert len(timeline) == 0


def test_insert_fact_creates_revision(run_saturn, tmp_path):
    run_saturn(tmp_path, "init")

    from saturn.facts import build_fact_input, insert_fact
    from saturn.revisions import list_revisions

    with connect(tmp_path / ".saturn" / "saturn.db") as conn:
        fact = build_fact_input("Saturn", "is", "planet", None, 0.8)
        fact_id = insert_fact(conn, fact)

        revisions = list_revisions(conn, entity_type="fact", entity_id=fact_id)

        assert len(revisions) == 1
        assert revisions[0]["change_type"] == "created"
        assert revisions[0]["before"] is None
        assert '"subject": "Saturn"' in revisions[0]["after"]
