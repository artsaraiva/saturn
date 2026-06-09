from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Any
import uuid
from datetime import UTC, datetime

from saturn.config import WorkspaceConfig
from saturn.db import connect


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def suggest_merges(
    config: WorkspaceConfig,
    min_similarity: float = 0.6,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Scan active facts and create merge groups for potential duplicates.

    Returns list of newly created merge groups (empty list if none found).
    """
    from collections import defaultdict

    with connect(config.db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE status = 'active' ORDER BY subject, predicate"
        ).fetchall()

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["subject"], r["predicate"])].append(dict(r))

    with connect(config.db_path) as conn:
        existing_rows = conn.execute(
            "SELECT member_fact_ids FROM merge_groups WHERE canonical_fact_id IS NULL AND merge_strategy IS NULL"
        ).fetchall()
    already_grouped: set[str] = set()
    for r in existing_rows:
        try:
            already_grouped.update(json.loads(r["member_fact_ids"]))
        except (json.JSONDecodeError, TypeError):
            pass

    created: list[dict[str, Any]] = []

    for (subject, predicate), facts in groups.items():
        if len(facts) < 2:
            continue

        merged_ids: set[str] = set()
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                a, b = facts[i], facts[j]
                if a["id"] in already_grouped or b["id"] in already_grouped:
                    continue
                if a["id"] in merged_ids or b["id"] in merged_ids:
                    continue
                sim = _text_similarity(a["object"], b["object"])
                if sim >= min_similarity:
                    merged_ids.add(a["id"])
                    merged_ids.add(b["id"])

        if not merged_ids:
            continue

        group_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        with connect(config.db_path) as conn:
            conn.execute(
                "INSERT INTO merge_groups (id, member_fact_ids, canonical_fact_id, merge_strategy, approved_by, approved_at, created_at) "
                "VALUES (?, ?, NULL, NULL, NULL, NULL, ?)",
                (group_id, json.dumps(sorted(merged_ids)), now),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM merge_groups WHERE id = ?", (group_id,)).fetchone()
            created.append(dict(row))

        if len(created) >= limit:
            break

    return created


def get_merge_group(config: WorkspaceConfig, group_id: str) -> dict[str, Any] | None:
    """Get a merge group by ID with full fact details."""
    with connect(config.db_path) as conn:
        row = conn.execute("SELECT * FROM merge_groups WHERE id = ?", (group_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        try:
            member_ids = json.loads(row["member_fact_ids"])
            facts = []
            for fid in member_ids:
                fr = conn.execute("SELECT * FROM facts WHERE id = ?", (fid,)).fetchone()
                if fr:
                    facts.append(dict(fr))
            result["member_facts"] = facts
        except (json.JSONDecodeError, TypeError):
            result["member_facts"] = []
        return result


def list_merge_groups(config: WorkspaceConfig, all_: bool = False) -> list[dict[str, Any]]:
    """List merge groups. By default, only pending (unresolved) groups."""
    with connect(config.db_path) as conn:
        if all_:
            rows = conn.execute("SELECT * FROM merge_groups ORDER BY created_at DESC LIMIT 50").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM merge_groups WHERE canonical_fact_id IS NULL AND merge_strategy IS NULL "
                "ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
        return [dict(r) for r in rows]


def apply_merge(config: WorkspaceConfig, group_id: str, keep_fact_id: str, actor: str = "cli") -> dict[str, Any]:
    """Approve a merge: archive non-canonical members, mark group as resolved.

    Returns updated merge group.
    """
    from saturn.facts import archive_fact

    with connect(config.db_path) as conn:
        group = conn.execute("SELECT * FROM merge_groups WHERE id = ?", (group_id,)).fetchone()
        if group is None:
            raise ValueError(f"Merge group not found: {group_id}")
        if group["canonical_fact_id"] is not None:
            raise ValueError(f"Merge group {group_id[:8]} already resolved")

        try:
            member_ids = json.loads(group["member_fact_ids"])
        except (json.JSONDecodeError, TypeError):
            member_ids = []

        if keep_fact_id not in member_ids:
            raise ValueError(f"keep_fact_id {keep_fact_id} is not a member of this group")

        for fid in member_ids:
            if fid != keep_fact_id:
                archive_fact(conn, fact_id=fid, actor=actor)

        now = datetime.now(UTC).isoformat()
        conn.execute(
            "UPDATE merge_groups SET canonical_fact_id = ?, merge_strategy = 'keep', approved_by = ?, approved_at = ? WHERE id = ?",
            (keep_fact_id, actor, now, group_id),
        )
        conn.commit()

        return dict(conn.execute("SELECT * FROM merge_groups WHERE id = ?", (group_id,)).fetchone())


def reject_merge(config: WorkspaceConfig, group_id: str, actor: str = "cli") -> dict[str, Any]:
    """Reject a merge: mark group as dismissed without archiving anything."""
    with connect(config.db_path) as conn:
        group = conn.execute("SELECT * FROM merge_groups WHERE id = ?", (group_id,)).fetchone()
        if group is None:
            raise ValueError(f"Merge group not found: {group_id}")

        now = datetime.now(UTC).isoformat()
        conn.execute(
            "UPDATE merge_groups SET merge_strategy = 'reject', approved_by = ?, approved_at = ? WHERE id = ?",
            (actor, now, group_id),
        )
        conn.commit()

        return dict(conn.execute("SELECT * FROM merge_groups WHERE id = ?", (group_id,)).fetchone())
