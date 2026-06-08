from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any


from saturn.facts import validate_required_text


def insert_revision(
    connection: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    change_type: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    actor: str = "cli",
) -> str:
    entity_type = validate_required_text("entity_type", entity_type)
    entity_id = validate_required_text("entity_id", entity_id)
    change_type = validate_required_text("change_type", change_type)

    revision_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).isoformat()

    before_json = json.dumps(before) if before is not None else None
    after_json = json.dumps(after) if after is not None else None

    connection.execute(
        """
        INSERT INTO revisions (id, entity_type, entity_id, change_type, before, after, actor, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (revision_id, entity_type, entity_id, change_type, before_json, after_json, actor, timestamp),
    )
    connection.commit()

    return revision_id


def list_revisions(
    connection: sqlite3.Connection,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM revisions WHERE 1=1"
    params: list[Any] = []

    if entity_type is not None:
        query += " AND entity_type = ?"
        params.append(entity_type)

    if entity_id is not None:
        query += " AND entity_id = ?"
        params.append(entity_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    return connection.execute(query, params).fetchall()


def get_revision(connection: sqlite3.Connection, revision_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM revisions WHERE id = ?",
        (revision_id,),
    ).fetchone()
