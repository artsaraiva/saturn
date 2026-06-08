from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import sqlite3
import uuid


@dataclass(frozen=True)
class FactInput:
    subject: str
    predicate: str
    object: str
    source: str | None
    confidence: float


@dataclass(frozen=True)
class FactRecord:
    subject: str
    predicate: str
    object: str
    source: str | None
    confidence: float
    updated_at: str


def normalize_text(value: str) -> str:
    return value.strip()


def validate_required_text(field_name: str, value: str) -> str:
    normalized = normalize_text(value)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def validate_confidence(confidence: float | None) -> float:
    if confidence is None:
        return 0.8
    if 0.0 <= confidence <= 1.0:
        return confidence
    raise ValueError("confidence must be between 0.0 and 1.0")


def build_fact_input(
    subject: str,
    predicate: str,
    object_: str,
    source: str | None,
    confidence: float | None,
) -> FactInput:
    return FactInput(
        subject=validate_required_text("subject", subject),
        predicate=validate_required_text("predicate", predicate),
        object=validate_required_text("object", object_),
        source=normalize_text(source) if source else None,
        confidence=validate_confidence(confidence),
    )


def insert_fact(connection, fact: FactInput) -> str:
    from saturn.revisions import insert_revision

    fact_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO facts(id, subject, predicate, object, source, confidence, status, created_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """,
        (
            fact_id,
            fact.subject,
            fact.predicate,
            fact.object,
            fact.source,
            fact.confidence,
            now,
            now,
        ),
    )
    insert_revision(
        connection,
        entity_type="fact",
        entity_id=fact_id,
        change_type="created",
        before=None,
        after={
            "subject": fact.subject,
            "predicate": fact.predicate,
            "object": fact.object,
            "source": fact.source,
            "confidence": fact.confidence,
            "status": "active",
        },
        actor="cli",
    )
    return fact_id


def update_fact(
    connection: sqlite3.Connection,
    fact_id: str,
    subject: str | None = None,
    predicate: str | None = None,
    object: str | None = None,
    source: str | None = None,
    confidence: float | None = None,
    actor: str = "cli",
) -> None:
    from saturn.revisions import insert_revision

    row = connection.execute(
        "SELECT subject, predicate, object, source, confidence, status FROM facts WHERE id = ?",
        (fact_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Fact not found: {fact_id}")

    status = row["status"]
    if status in ("archived", "superseded"):
        raise ValueError(f"Cannot update fact with status '{status}'")

    before = {
        "subject": row["subject"],
        "predicate": row["predicate"],
        "object": row["object"],
        "source": row["source"],
        "confidence": row["confidence"],
        "status": row["status"],
    }

    updates: dict[str, object] = {}
    if subject is not None:
        updates["subject"] = normalize_text(subject)
    if predicate is not None:
        updates["predicate"] = normalize_text(predicate)
    if object is not None:
        updates["object"] = normalize_text(object)
    if source is not None:
        updates["source"] = normalize_text(source)
    if confidence is not None:
        updates["confidence"] = confidence

    if not updates:
        return

    now = datetime.now(UTC).isoformat()
    set_clauses = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [now, fact_id]
    connection.execute(
        f"UPDATE facts SET {set_clauses}, updated_at = ? WHERE id = ?",
        values,
    )

    after = {**before, **updates}

    insert_revision(
        connection,
        entity_type="fact",
        entity_id=fact_id,
        change_type="updated",
        before=before,
        after=after,
        actor=actor,
    )
    connection.commit()


def search_facts(connection, raw_query: str) -> list[FactRecord]:
    exact = raw_query.strip().lower()
    partial = exact
    rows = connection.execute(
        """
        SELECT
          subject,
          predicate,
          object,
          source,
          confidence,
          updated_at,
          (
            CASE WHEN lower(subject) = ? THEN 20 ELSE 0 END +
            CASE WHEN lower(predicate) = ? THEN 20 ELSE 0 END +
            CASE WHEN lower(object) = ? THEN 20 ELSE 0 END +
            CASE WHEN instr(lower(subject), ?) > 0 THEN 5 ELSE 0 END +
            CASE WHEN instr(lower(predicate), ?) > 0 THEN 5 ELSE 0 END +
            CASE WHEN instr(lower(object), ?) > 0 THEN 5 ELSE 0 END
          ) AS match_score
        FROM facts
        WHERE instr(lower(subject), ?) > 0
           OR instr(lower(predicate), ?) > 0
           OR instr(lower(object), ?) > 0
        ORDER BY
          match_score DESC,
          CASE WHEN lower(subject) = ? THEN 1 ELSE 0 END DESC,
          CASE WHEN lower(predicate) = ? THEN 1 ELSE 0 END DESC,
          CASE WHEN lower(object) = ? THEN 1 ELSE 0 END DESC,
          updated_at DESC
        """,
        (
            exact,
            exact,
            exact,
            partial,
            partial,
            partial,
            partial,
            partial,
            partial,
            exact,
            exact,
            exact,
        ),
    ).fetchall()
    return [
        FactRecord(
            row["subject"],
            row["predicate"],
            row["object"],
            row["source"],
            row["confidence"],
            row["updated_at"],
        )
        for row in rows
    ]
