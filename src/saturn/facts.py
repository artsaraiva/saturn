from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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
