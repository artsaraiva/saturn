from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from saturn.config import WorkspaceConfig
from saturn.db import connect
from saturn.merge import suggest_merges


def run_maintenance(
    config: WorkspaceConfig,
    dry_run: bool = False,
    archive_days: int = 90,
) -> dict:
    """Run the full maintenance pipeline: dedup, contradict, archive.

    Returns stats dict with keys:
        contradictions_found, archived, errors
    """
    stats = {"contradictions_found": 0, "archived": 0, "errors": 0, "merges_suggested": 0}

    with connect(config.db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE status = 'active'"
        ).fetchall()

        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            groups[(r["subject"], r["predicate"])].append(dict(r))

        from saturn.contradictions import insert_contradiction

        for (subject, predicate), facts in groups.items():
            if len(facts) < 2:
                continue
            for i in range(len(facts)):
                for j in range(i + 1, len(facts)):
                    a, b = facts[i], facts[j]
                    if a["object"] == b["object"]:
                        continue
                    existing = conn.execute(
                        "SELECT id FROM contradictions WHERE "
                        "(fact_a_id = ? AND fact_b_id = ? OR fact_a_id = ? AND fact_b_id = ?) "
                        "AND state = 'open'",
                        (a["id"], b["id"], b["id"], a["id"]),
                    ).fetchone()
                    if existing:
                        continue
                    if not dry_run:
                        insert_contradiction(
                            conn,
                            fact_a_id=a["id"],
                            fact_b_id=b["id"],
                            reason="Same subject+predicate, different object",
                            score=0.7,
                        )
                    stats["contradictions_found"] += 1

        cutoff = (datetime.now(UTC) - timedelta(days=archive_days)).isoformat()
        stale = conn.execute(
            "SELECT id FROM facts WHERE status = 'active' AND updated_at < ?",
            (cutoff,),
        ).fetchall()

        for row in stale:
            if not dry_run:
                from saturn.facts import archive_fact
                archive_fact(conn, fact_id=row["id"], actor="maintain")
            stats["archived"] += 1

    # 3. Merge suggestion
    try:
        merge_groups = suggest_merges(config, min_similarity=0.6)
        stats["merges_suggested"] = len(merge_groups)
    except Exception:
        stats["merges_suggested"] = 0
        stats["errors"] += 1

    return stats
