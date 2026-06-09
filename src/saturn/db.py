from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from saturn.config import WorkspaceNotInitializedError


class UnsupportedSchemaError(RuntimeError):
    pass


class InvalidDatabaseError(RuntimeError):
    pass


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS facts (
  id TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object TEXT NOT NULL,
  source TEXT,
  confidence REAL NOT NULL DEFAULT 0.8,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revisions (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  change_type TEXT NOT NULL,
  before TEXT,
  after TEXT,
  actor TEXT NOT NULL DEFAULT 'cli',
  timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contradictions (
  id TEXT PRIMARY KEY,
  fact_a_id TEXT NOT NULL REFERENCES facts(id),
  fact_b_id TEXT NOT NULL REFERENCES facts(id),
  reason TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 1.0,
  state TEXT NOT NULL DEFAULT 'open',
  resolution_type TEXT,
  resolved_by TEXT,
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS merge_groups (
  id TEXT PRIMARY KEY,
  member_fact_ids TEXT NOT NULL,
  canonical_fact_id TEXT,
  merge_strategy TEXT,
  approved_by TEXT,
  approved_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_meta (
  version INTEGER NOT NULL,
  applied_at TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE facts ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
    )
    connection.execute("""
        CREATE TABLE IF NOT EXISTS revisions (
          id TEXT PRIMARY KEY,
          entity_type TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          change_type TEXT NOT NULL,
          before TEXT,
          after TEXT,
          actor TEXT NOT NULL DEFAULT 'cli',
          timestamp TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS contradictions (
          id TEXT PRIMARY KEY,
          fact_a_id TEXT NOT NULL REFERENCES facts(id),
          fact_b_id TEXT NOT NULL REFERENCES facts(id),
          reason TEXT NOT NULL,
          score REAL NOT NULL DEFAULT 1.0,
          state TEXT NOT NULL DEFAULT 'open',
          resolution_type TEXT,
          resolved_by TEXT,
          resolved_at TEXT
        )
    """)
    connection.execute(
        "UPDATE schema_meta SET version = 2"
    )
    connection.commit()


def migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS merge_groups (
          id TEXT PRIMARY KEY,
          member_fact_ids TEXT NOT NULL,
          canonical_fact_id TEXT,
          merge_strategy TEXT,
          approved_by TEXT,
          approved_at TEXT,
          created_at TEXT NOT NULL
        )
    """)
    connection.execute("UPDATE schema_meta SET version = 3")
    connection.commit()


def initialize_database(db_path: Path, schema_version: int) -> None:
    try:
        with connect(db_path) as connection:
            schema_meta_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'"
            ).fetchone()
            if schema_meta_exists:
                current = connection.execute(
                    "SELECT COUNT(*) AS count FROM schema_meta"
                ).fetchone()["count"]
                if current > 0:
                    actual_version = connection.execute(
                        "SELECT version FROM schema_meta LIMIT 1"
                    ).fetchone()["version"]
                    if actual_version == 1 and schema_version >= 2:
                        migrate_v1_to_v2(connection)
                        actual_version = 2
                    if actual_version == 2 and schema_version >= 3:
                        migrate_v2_to_v3(connection)
                        actual_version = 3
                    if actual_version != schema_version:
                        raise ValueError(
                            "Database schema version mismatch: "
                            f"found {actual_version}, expected {schema_version}"
                        )
                verify_database_shape(connection)

            connection.executescript(SCHEMA_SQL)
            current = connection.execute(
                "SELECT COUNT(*) AS count FROM schema_meta"
            ).fetchone()["count"]
            if current == 0:
                connection.execute(
                    "INSERT INTO schema_meta(version, applied_at) VALUES(?, ?)",
                    (schema_version, datetime.now(UTC).isoformat()),
                )
            connection.commit()
    except sqlite3.Error as error:
        raise InvalidDatabaseError("Workspace database is invalid.") from error


def read_schema_version(connection) -> int:
    row = connection.execute(
        "SELECT version FROM schema_meta ORDER BY applied_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise UnsupportedSchemaError("Schema metadata is missing.")
    return int(row["version"])


def verify_supported_schema(connection, expected_version: int) -> None:
    version = read_schema_version(connection)
    if version != expected_version:
        raise UnsupportedSchemaError(
            f"Unsupported schema version {version}. Expected {expected_version}."
        )


def verify_database_shape(connection) -> None:
    required_columns = {
        "facts": {
            "id",
            "subject",
            "predicate",
            "object",
            "source",
            "confidence",
            "status",
            "created_at",
            "updated_at",
        },
        "schema_meta": {"version", "applied_at"},
        "revisions": {
            "id",
            "entity_type",
            "entity_id",
            "change_type",
            "before",
            "after",
            "actor",
            "timestamp",
        },
        "contradictions": {
            "id",
            "fact_a_id",
            "fact_b_id",
            "reason",
            "score",
            "state",
            "resolution_type",
            "resolved_by",
            "resolved_at",
        },
        "merge_groups": {
            "id",
            "member_fact_ids",
            "canonical_fact_id",
            "merge_strategy",
            "approved_by",
            "approved_at",
            "created_at",
        },
    }
    for table_name, expected_columns in required_columns.items():
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if row is None:
            raise InvalidDatabaseError("Workspace database is invalid.")

        actual_columns = {
            row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})")
        }
        if not expected_columns.issubset(actual_columns):
            raise InvalidDatabaseError("Workspace database is invalid.")


def require_initialized_database(db_path: Path, schema_version: int) -> None:
    if not db_path.exists():
        raise WorkspaceNotInitializedError(
            "Workspace is not initialized. Run `saturn init` first."
        )

    try:
        with connect(db_path) as connection:
            verify_database_shape(connection)

            row = connection.execute("SELECT version FROM schema_meta LIMIT 1").fetchone()
            if row is None or row["version"] != schema_version:
                raise WorkspaceNotInitializedError(
                    "Workspace is not initialized. Run `saturn init` first."
                )
    except InvalidDatabaseError as error:
        raise WorkspaceNotInitializedError(
            "Workspace is not initialized. Run `saturn init` first."
        ) from error
    except sqlite3.Error as error:
        raise WorkspaceNotInitializedError(
            "Workspace is not initialized. Run `saturn init` first."
        ) from error
