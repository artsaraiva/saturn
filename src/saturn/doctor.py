from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from saturn.config import WorkspaceConfig
from saturn.db import (
    InvalidDatabaseError,
    connect,
    verify_database_shape,
    verify_supported_schema,
)


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    messages: list[str]


def refresh_project_status_docs(project_root: Path) -> None:
    status_dir = project_root / "docs" / "superpowers"
    status_dir.mkdir(parents=True, exist_ok=True)

    markdown = """# Saturn Project Status

- Current phase: Phase 1
- Active milestone: CLI-first prototype
- Implemented slices:
  - `saturn init`
  - `saturn facts add`
  - `saturn query`
  - `saturn doctor`
- Not-started slices:
  - bulk ingestion
  - revisions and richer fact metadata
  - deduplication and contradiction records
  - daemon and MCP interfaces
  - wiki projection and graph export
- Blockers: none
- Open decisions: none for this slice
- Recommended next tasks:
  - add bulk ingestion from files
  - add revisions table
  - add contradiction workflows
"""

    payload = {
        "current_phase": "Phase 1",
        "active_milestone": "CLI-first prototype",
        "implemented_slices": [
            "saturn init",
            "saturn facts add",
            "saturn query",
            "saturn doctor",
        ],
        "not_started_slices": [
            "bulk ingestion",
            "revisions and richer fact metadata",
            "deduplication and contradiction records",
            "daemon and MCP interfaces",
            "wiki projection and graph export",
        ],
        "blockers": [],
        "open_decisions": [],
        "recommended_next_tasks": [
            "add bulk ingestion from files",
            "add revisions table",
            "add contradiction workflows",
        ],
    }

    (status_dir / "project-status.md").write_text(markdown, encoding="utf-8")
    (status_dir / "project-status.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def bootstrap_project_status_docs(project_root: Path) -> None:
    status_dir = project_root / "docs" / "superpowers"
    status_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = status_dir / "project-status.md"
    json_path = status_dir / "project-status.json"

    if not markdown_path.exists():
        markdown_path.write_text(
            "# Saturn Project Status\n\n"
            "- Current phase: Phase 1\n"
            "- Active milestone: CLI-first prototype\n"
            "- Implemented slices: workspace bootstrap in progress\n",
            encoding="utf-8",
        )

    if not json_path.exists():
        json_path.write_text(
            json.dumps(
                {
                    "current_phase": "Phase 1",
                    "active_milestone": "CLI-first prototype",
                    "implemented_slices": ["workspace bootstrap in progress"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def run_doctor(config: WorkspaceConfig) -> DoctorResult:
    messages: list[str] = []
    if not config.config_path.exists():
        return DoctorResult(
            False, ["Workspace is not initialized. Run `saturn init` first."]
        )
    if not config.db_path.exists():
        return DoctorResult(False, ["Database file is missing."])

    try:
        with connect(config.db_path) as connection:
            verify_database_shape(connection)
            verify_supported_schema(connection, config.schema_version)
    except sqlite3.Error:
        return DoctorResult(False, ["Workspace database is invalid."])
    except InvalidDatabaseError as error:
        return DoctorResult(False, [str(error)])

    refresh_project_status_docs(config.project_root)
    messages.append("Workspace health: OK")
    return DoctorResult(True, messages)
