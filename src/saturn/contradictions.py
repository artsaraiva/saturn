from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any


def detect_contradictions(connection: sqlite3.Connection, fact_id: str) -> list[str]:
    """Detect contradictions for a fact. Returns contradiction IDs."""
    fact = connection.execute(
        "SELECT * FROM facts WHERE id = ?", (fact_id,)
    ).fetchone()

    if fact is None:
        return []

    matches = connection.execute(
        """
        SELECT id FROM facts
        WHERE subject = ? AND predicate = ? AND object != ?
          AND status IN ('active', 'disputed')
          AND id != ?
        """,
        (fact["subject"], fact["predicate"], fact["object"], fact_id),
    ).fetchall()

    contradiction_ids = []

    for match in matches:
        existing = connection.execute(
            """
            SELECT 1 FROM contradictions
            WHERE (fact_a_id = ? AND fact_b_id = ?)
               OR (fact_a_id = ? AND fact_b_id = ?)
            """,
            (match["id"], fact_id, fact_id, match["id"]),
        ).fetchone()

        if existing is None:
            contradiction_id = insert_contradiction(
                connection,
                fact_a_id=match["id"],
                fact_b_id=fact_id,
                reason="Same subject and predicate, different object",
                score=1.0,
            )
            contradiction_ids.append(contradiction_id)

    return contradiction_ids


def insert_contradiction(
    connection: sqlite3.Connection,
    fact_a_id: str,
    fact_b_id: str,
    reason: str,
    score: float = 1.0,
) -> str:
    contradiction_id = str(uuid.uuid4())

    connection.execute(
        """
        INSERT INTO contradictions (id, fact_a_id, fact_b_id, reason, score, state)
        VALUES (?, ?, ?, ?, ?, 'open')
        """,
        (contradiction_id, fact_a_id, fact_b_id, reason, score),
    )

    connection.execute(
        "UPDATE facts SET status = 'disputed' WHERE id IN (?, ?)",
        (fact_a_id, fact_b_id),
    )

    connection.commit()
    return contradiction_id


def list_contradictions(
    connection: sqlite3.Connection,
    state: str | None = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    query = """
        SELECT c.*,
               fa.subject AS fact_a_subject, fa.predicate AS fact_a_predicate, fa.object AS fact_a_object,
               fb.subject AS fact_b_subject, fb.predicate AS fact_b_predicate, fb.object AS fact_b_object
        FROM contradictions c
        JOIN facts fa ON c.fact_a_id = fa.id
        JOIN facts fb ON c.fact_b_id = fb.id
        WHERE 1=1
    """
    params: list[Any] = []

    if state is not None:
        query += " AND c.state = ?"
        params.append(state)

    query += " ORDER BY c.resolved_at IS NULL DESC, c.resolved_at DESC LIMIT ?"
    params.append(limit)

    return connection.execute(query, params).fetchall()
