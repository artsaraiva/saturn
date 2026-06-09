from __future__ import annotations

from collections import defaultdict
import json

from saturn.config import WorkspaceConfig
from saturn.db import connect


def export_json(config: WorkspaceConfig) -> str:
    """Export knowledge graph as JSON (nodes + edges)."""
    try:
        with connect(config.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE status NOT IN ('archived', 'superseded') ORDER BY subject"
            ).fetchall()
    except Exception:
        return json.dumps({"nodes": [], "edges": []})

    entities: dict[str, int] = defaultdict(int)
    edges = []
    for r in rows:
        f = dict(r)
        entities[f["subject"]] += 1
        entities[f["object"]] += 1
        edges.append({
            "source": f["subject"],
            "target": f["object"],
            "predicate": f["predicate"],
            "fact_id": f["id"],
            "confidence": f.get("confidence"),
            "status": f.get("status", "active"),
        })

    nodes = [
        {"id": name, "label": name, "fact_count": count}
        for name, count in sorted(entities.items())
    ]

    return json.dumps({"nodes": nodes, "edges": edges}, indent=2)


def export_dot(config: WorkspaceConfig) -> str:
    """Export knowledge graph as Graphviz DOT format."""
    try:
        with connect(config.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE status NOT IN ('archived', 'superseded') ORDER BY subject"
            ).fetchall()
    except Exception:
        rows = []

    lines = ['digraph Saturn {', '  rankdir=LR;', '  node [shape=box, style=rounded];', '']
    for r in rows:
        f = dict(r)
        subject = f["subject"].replace('"', '\\"')
        obj = f["object"].replace('"', '\\"')
        predicate = f["predicate"].replace('"', '\\"')
        label = f"{predicate} [{f.get('confidence', 0):.0%}]"
        lines.append(f'  "{subject}" -> "{obj}" [label="{label}"];')
    lines.append('}')
    return "\n".join(lines)
