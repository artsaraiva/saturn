from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from saturn.config import WorkspaceConfig
from saturn.db import connect


def build_wiki(config: WorkspaceConfig, wiki_dir: Path | None = None) -> Path:
    """Generate static markdown wiki from stored facts."""
    if wiki_dir is None:
        wiki_dir = config.project_root / "wiki"

    entities_dir = wiki_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    try:
        with connect(config.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM facts WHERE status NOT IN ('archived', 'superseded') ORDER BY subject, predicate"
            ).fetchall()
    except Exception:
        rows = []

    by_subject: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_subject[r["subject"]].append(dict(r))

    for subject, facts in sorted(by_subject.items()):
        lines = [f"# {subject}\n"]
        lines.append(f"**{len(facts)} fact(s)**\n")
        lines.append("| Predicate | Object | Confidence | Status | Updated |")
        lines.append("|-----------|--------|------------|--------|---------|")
        for f in facts:
            conf = f"{f['confidence']:.0%}" if f.get("confidence") else "\u2014"
            status = f["status"]
            updated = (f.get("updated_at") or "\u2014")[:10]
            obj = f["object"].replace("|", "\\|")
            lines.append(f"| {f['predicate']} | {obj} | {conf} | {status} | {updated} |")
        lines.append("")
        (entities_dir / f"{subject}.md").write_text("\n".join(lines), encoding="utf-8")

    index_lines = ["# Saturn Wiki\n"]
    index_lines.append(f"**{sum(len(v) for v in by_subject.values())} active fact(s)** across **{len(by_subject)} entity/entities**\n")

    if by_subject:
        index_lines.append("## Entities\n")
        for subject in sorted(by_subject):
            count = len(by_subject[subject])
            index_lines.append(f"- [{subject}](entities/{subject}.md) \u2014 {count} fact(s)")
        index_lines.append("")
    else:
        index_lines.append("_No facts stored yet. Run `saturn facts add` or `saturn ingest` to populate._\n")

    (wiki_dir / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

    return wiki_dir


def serve_wiki(config: WorkspaceConfig, wiki_dir: Path | None = None, port: int = 8080) -> None:
    """Start a simple HTTP server for the wiki."""
    if wiki_dir is None:
        wiki_dir = config.project_root / "wiki"
    import http.server
    import socketserver

    handler = http.server.SimpleHTTPRequestHandler

    class WikiHandler(handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(wiki_dir), **kwargs)

    print(f"Serving wiki at http://localhost:{port}")
    with socketserver.TCPServer(("", port), WikiHandler) as httpd:
        httpd.serve_forever()
